"""
Stage Validator - 阶段验证引擎 (v3.0 Final)
职责: 整合四层验证，作为统一PreToolUse的核心验证引擎

核心变更(v3.0 Final):
- 语义化步骤命名: planning, implementation, finalization
- 使用 TaskMetaManager 替代 StateManager
- validate() 参数从 workflow_state 改为 task_meta
- 子代理检查直接使用 TaskMetaManager.check_subagent_lock()

四层验证架构:
1. 第一层: 阶段-工具基础验证（工具类型是否允许）
2. 第二层: 前置条件检查（前序步骤是否完成）
3. 第三层: 文件路径验证（白名单/黑名单）
4. 第四层: 操作语义分析（区分Write代码vs文档，检查危险命令等）
"""

import sys
import os
from typing import Dict, Optional
from . import tool_matrix
from .path_validator import PathValidator
from .semantic_analyzer import SemanticAnalyzer
from .task_meta_manager import TaskMetaManager

# DEBUG模式控制（设置环境变量CLAUDE_HOOK_DEBUG=1启用调试日志）
DEBUG = os.getenv("CLAUDE_HOOK_DEBUG", "0") == "1"


class StageValidator:
    """阶段验证引擎 - 四层验证整合 (v2.0)"""

    # ✅ Phase 3: 工具名称归一化映射（处理Claude Code工具别名/变体）
    TOOL_ALIASES = {
        "Update": "Edit",     # Claude Code v2.0中Update是Edit的别名
        "Patch": "Edit",      # 可能的Edit别名
        # 根据实际使用情况补充其他别名
    }

    def __init__(self, cwd: Optional[str] = None):
        self.cwd = cwd
        self.path_validator = PathValidator(cwd)
        self.semantic_analyzer = SemanticAnalyzer(self.path_validator)
        self.task_meta_manager = TaskMetaManager(cwd)

    def validate(
        self,
        current_step: str,
        tool_name: str,
        tool_input: Dict,
        task_meta: Dict
    ) -> Dict:
        """
        四层验证主入口 (v2.0)

        Args:
            current_step: 当前工作流阶段
            tool_name: 工具名称
            tool_input: 工具输入参数
            task_meta: 任务元数据（v2.0唯一数据源）

        Returns:
            {
                "allowed": bool,
                "reason": str,
                "suggestion": str (可选)
            }
        """
        # ✅ Phase 3: 工具名称归一化（处理别名）
        original_tool_name = tool_name
        normalized_tool_name = self.TOOL_ALIASES.get(tool_name, tool_name)

        if normalized_tool_name != original_tool_name and DEBUG:
            sys.stderr.write(f"[StageValidator] 工具名称归一化: {original_tool_name} → {normalized_tool_name}\n")

        # 使用归一化后的工具名称进行验证
        tool_name = normalized_tool_name

        # 获取阶段配置
        stage_config = tool_matrix.get_stage_config(current_step)
        if not stage_config:
            # 未知阶段，放行（兜底逻辑）
            sys.stderr.write(f"[警告] 未知阶段: {current_step}\n")
            return {"allowed": True, "reason": "未知阶段，默认放行"}

        # ========== 第一层: 阶段-工具基础验证 ==========
        layer1_result = self._validate_layer1_tool_type(
            current_step, tool_name, stage_config, task_meta
        )
        if not layer1_result["allowed"]:
            return layer1_result

        # ========== 第二层: 前置条件检查 ==========
        layer2_result = self._validate_layer2_preconditions(
            current_step, stage_config, task_meta
        )
        if not layer2_result["allowed"]:
            return layer2_result

        # ========== 第三层: 文件路径验证 ==========
        if tool_name in ["Read", "Write", "Edit"]:
            file_path = tool_input.get("file_path", "")
            if file_path:
                layer3_result = self._validate_layer3_path(
                    current_step, tool_name, file_path, stage_config, task_meta
                )
                if not layer3_result["allowed"]:
                    return layer3_result

        # ========== 第四层: 操作语义分析 ==========
        layer4_result = self._validate_layer4_semantic(
            current_step, tool_name, tool_input, task_meta, stage_config
        )
        if not layer4_result["allowed"]:
            return layer4_result

        # ========== 全部验证通过 ==========
        return {"allowed": True, "reason": "四层验证全部通过"}

    # ========== 第一层: 阶段-工具基础验证 ==========

    def _validate_layer1_tool_type(
        self,
        current_step: str,
        tool_name: str,
        stage_config: Dict,
        task_meta: Dict
    ) -> Dict:
        """
        第一层验证: 检查工具类型是否被允许 (v2.0)
        """
        # ✅ Phase 1: 诊断日志（仅DEBUG模式）
        if DEBUG:
            sys.stderr.write(f"[Layer1] 工具类型验证: tool_name={tool_name}, current_step={current_step}\n")

        # 1. 检查是否在子代理上下文中
        task_id = task_meta.get('task_id')
        is_subagent = self.task_meta_manager.check_subagent_lock(task_id) if task_id else False

        # 2. 如果是子代理，使用子代理规则
        if is_subagent and current_step == "finalization":
            subagent_rules = stage_config.get('subagent_rules', {})
            allowed_tools = subagent_rules.get('allowed_tools', [])

            if DEBUG:
                sys.stderr.write(f"[Layer1] 子代理模式: allowed_tools={allowed_tools}\n")

            if tool_name not in allowed_tools:
                if DEBUG:
                    sys.stderr.write(f"[Layer1] 拒绝: {tool_name} 不在子代理白名单中\n")
                return {
                    "allowed": False,
                    "reason": f"收尾子代理不允许使用工具: {tool_name}",
                    "suggestion": f"子代理只能使用: {', '.join(allowed_tools)}"
                }
            return {"allowed": True, "reason": "子代理工具类型验证通过"}

        # 3. 父代理或非finalization阶段，使用标准规则
        allowed_tools = stage_config.get('allowed_tools', [])

        if DEBUG:
            sys.stderr.write(f"[Layer1] 标准模式: allowed_tools={allowed_tools}\n")
            sys.stderr.write(f"[Layer1] 检查: {tool_name} in {allowed_tools} = {tool_name in allowed_tools}\n")

        if tool_name not in allowed_tools:
            display_name = stage_config.get('display_name', current_step)
            if DEBUG:
                sys.stderr.write(f"[Layer1] 拒绝: {tool_name} 不在白名单中\n")
            return {
                "allowed": False,
                "reason": f"阶段 {display_name} 不允许使用工具: {tool_name}",
                "suggestion": self._suggest_correct_tool(current_step, allowed_tools)
            }

        if DEBUG:
            sys.stderr.write(f"[Layer1] 通过: {tool_name} 在白名单中\n")
        return {"allowed": True, "reason": "工具类型验证通过"}

    # ========== 第二层: 前置条件检查 ==========

    def _validate_layer2_preconditions(
        self,
        current_step: str,
        stage_config: Dict,
        task_meta: Dict
    ) -> Dict:
        """
        第二层验证: 检查前置条件是否满足 (v2.0)
        """
        preconditions = stage_config.get('preconditions', [])

        for precondition in preconditions:
            # 解析前置条件（v3.0 Final: 语义化命名）
            if precondition == "planning_completed":
                if not self._is_step_completed("planning", task_meta):
                    return {
                        "allowed": False,
                        "reason": "前置条件未满足: Planning（方案制定阶段）尚未完成",
                        "suggestion": "请先完成文档研究，明确说明研究结论后继续"
                    }

            elif precondition == "user_confirmed":
                if not task_meta.get('steps', {}).get('implementation', {}).get('user_confirmed', False):
                    return {
                        "allowed": False,
                        "reason": "前置条件未满足: 用户尚未确认修复完成",
                        "suggestion": "请等待用户输入 '/mc-confirm' 或 '已修复' 确认任务完成"
                    }

        return {"allowed": True, "reason": "前置条件检查通过"}

    # ========== 第三层: 文件路径验证 ==========

    def _validate_layer3_path(
        self,
        current_step: str,
        tool_name: str,
        file_path: str,
        stage_config: Dict,
        task_meta: Dict
    ) -> Dict:
        """
        第三层验证: 检查文件路径是否符合规则 (v2.0)
        """
        # 1. 检查是否在子代理上下文中
        task_id = task_meta.get('task_id')
        is_subagent = self.task_meta_manager.check_subagent_lock(task_id) if task_id else False

        # 2. 获取路径规则
        if is_subagent and current_step == "finalization":
            # 子代理使用子代理规则
            subagent_rules = stage_config.get('subagent_rules', {})
            path_rules = subagent_rules.get('path_rules', {}).get(tool_name, {})
        else:
            # 标准规则
            path_rules = tool_matrix.get_path_rules(current_step, tool_name)

        if not path_rules:
            # 无路径规则，放行
            return {"allowed": True, "reason": "无需路径验证"}

        # 3. 执行路径验证
        return self.path_validator.validate(
            current_step, tool_name, file_path, path_rules
        )

    # ========== 第四层: 操作语义分析 ==========

    def _validate_layer4_semantic(
        self,
        current_step: str,
        tool_name: str,
        tool_input: Dict,
        task_meta: Dict,
        stage_config: Dict
    ) -> Dict:
        """
        第四层验证: 操作语义分析（最细粒度） (v3.0 Final增强)

        v3.0 Final语义化命名:
        - planning强制方案制定阶段：由第一层白名单统一拦截，此处不再重复检查
        - implementation执行阶段：检查文档阅读数量（语义验证，非工具拦截）

        ✅ Phase 2改进: 移除Planning阶段的黑名单逻辑，统一使用第一层白名单验证
        """
        # ========== Phase 2: 已移除Planning阶段黑名单检查 ==========
        # 原黑名单逻辑（已删除）:
        #   - if tool_name in ["Write", "Edit"]: ... (冗余，已由第一层白名单拦截)
        #   - if tool_name == "Bash": ... (冗余，已由第一层白名单拦截)
        #
        # 设计原则: 第一层白名单是唯一的工具拦截机制，第四层只做语义验证

        # ========== v3.0 Final: Implementation执行阶段检查研究深度 ==========
        if current_step == "implementation":
            if tool_name in ["Write", "Edit"]:
                # 🔥 v22.1快速返回：BUG修复任务无强制文档要求
                task_type = task_meta.get('task_type', 'general')
                required_docs = task_meta.get('steps', {}).get('planning', {}).get('required_doc_count', 3)

                if task_type == 'bug_fix' and required_docs == 0:
                    sys.stderr.write("[StageValidator v22.1] BUG修复任务豁免文档要求，允许修改\n")
                    return {"allowed": True, "reason": "BUG修复任务无强制文档要求"}

                # 标准流程：检查文档数量
                docs_read = task_meta.get('metrics', {}).get('docs_read', [])
                docs_count = len(docs_read)

                # 🔥 P0修复：添加降级验证机制（Phase 1紧急修复）
                if docs_count == 0 and required_docs > 0:
                    # PostToolUse可能失效，使用降级验证
                    tools_used = task_meta.get('metrics', {}).get('tools_used', [])
                    read_operations = [t for t in tools_used if t.get('tool') == 'Read' and t.get('success')]

                    if len(read_operations) >= required_docs:
                        # 检测到足够的Read操作，PostToolUse疑似失效
                        sys.stderr.write(f"[WARNING] PostToolUse Hook疑似失效，使用降级验证\n")
                        sys.stderr.write(f"[WARNING] 检测到{len(read_operations)}次成功的Read操作，允许继续\n")
                        return {"allowed": True, "reason": "降级验证通过（PostToolUse失效保护）"}

                    # 🔥 P0修复：general任务豁免文档要求
                    task_type = task_meta.get('task_type', 'general')
                    if task_type == 'general':
                        sys.stderr.write(f"[INFO] general任务类型，豁免文档要求\n")
                        return {"allowed": True, "reason": "general任务无强制文档要求"}

                if docs_count < required_docs:
                    gameplay_pack = task_meta.get('gameplay_pack_matched')
                    mode_desc = "玩法包模式" if gameplay_pack else "标准模式"

                    return {
                        "allowed": False,
                        "reason": f"研究深度不足：仅查阅{docs_count}个文档，需要至少{required_docs}个",
                        "suggestion": f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 研究深度不足 - 修改被拒绝
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

当前模式: {mode_desc}
已查阅文档: {docs_count}/{required_docs}

❌ 问题: 修改决策需要基于充分的文档研究

✅ 解决方案:
1. 返回planning阶段
2. 继续查阅至少 {required_docs - docs_count} 个相关文档
3. 重点查阅:
   - CRITICAL规范文档（确保合规）
   - 相关系统实现文档
   - 问题排查指南

完成文档查阅后，Hook会自动允许修改操作。

💡 提示: 充分的文档研究能避免违反CRITICAL规范，
         减少返工迭代，提高修复成功率。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
                    }

        # ========== v3.0 Final: 标准语义分析 ==========
        # 1. 检查是否在子代理上下文中
        task_id = task_meta.get('task_id')
        is_subagent = self.task_meta_manager.check_subagent_lock(task_id) if task_id else False

        # 2. 获取语义规则
        if is_subagent and current_step == "finalization":
            # 子代理使用子代理规则
            subagent_rules = stage_config.get('subagent_rules', {})
            semantic_rules = subagent_rules.get('semantic_rules', {}).get(tool_name, {})
        else:
            # 标准规则
            semantic_rules = tool_matrix.get_semantic_rules(current_step, tool_name)

        if not semantic_rules:
            # 无语义规则，放行
            return {"allowed": True, "reason": "无需语义分析"}

        # 3. 执行语义分析
        return self.semantic_analyzer.analyze(
            current_step, tool_name, tool_input, task_meta, semantic_rules, is_subagent
        )

    # ========== 辅助方法 ==========

    def _is_step_completed(self, step_name: str, task_meta: Dict) -> bool:
        """检查步骤是否已完成 (v2.0)"""
        steps = task_meta.get('steps', {})
        step_info = steps.get(step_name, {})
        return step_info.get('status') == 'completed'

    def _suggest_correct_tool(self, current_step: str, allowed_tools: list) -> str:
        """生成正确工具的建议"""
        stage_config = tool_matrix.get_stage_config(current_step)
        display_name = stage_config.get('display_name', current_step)
        description = stage_config.get('description', '')

        suggestion = f"""
阶段 {display_name}:
- 描述: {description}
- 允许的工具: {', '.join(allowed_tools)}
"""

        # 特殊阶段的额外提示（v3.0 Final: 语义化命名）
        if current_step == "planning":
            suggestion += "\n请查阅至少3个相关文档，理解问题根因和技术约束，明确说明研究结论后继续"
        elif current_step == "finalization":
            suggestion += "\n请使用 Task 工具启动收尾子代理"

        return suggestion.strip()
