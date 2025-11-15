"""
Stage Validator - 阶段验证引擎 (v21.0)
职责: 整合四层验证，作为统一PreToolUse的核心验证引擎

核心变更(v21.0):
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
from typing import Dict, Optional
from . import tool_matrix
from .path_validator import PathValidator
from .semantic_analyzer import SemanticAnalyzer
from .task_meta_manager import TaskMetaManager


class StageValidator:
    """阶段验证引擎 - 四层验证整合 (v21.0)"""

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
        四层验证主入口 (v21.0)

        Args:
            current_step: 当前工作流阶段
            tool_name: 工具名称
            tool_input: 工具输入参数
            task_meta: 任务元数据（v21.0唯一数据源）

        Returns:
            {
                "allowed": bool,
                "reason": str,
                "suggestion": str (可选)
            }
        """
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
        第一层验证: 检查工具类型是否被允许 (v21.0)
        """
        # 1. 检查是否在子代理上下文中
        task_id = task_meta.get('task_id')
        is_subagent = self.task_meta_manager.check_subagent_lock(task_id) if task_id else False

        # 2. 如果是子代理，使用子代理规则
        if is_subagent and current_step == "step4_cleanup":
            subagent_rules = stage_config.get('subagent_rules', {})
            allowed_tools = subagent_rules.get('allowed_tools', [])

            if tool_name not in allowed_tools:
                return {
                    "allowed": False,
                    "reason": f"收尾子代理不允许使用工具: {tool_name}",
                    "suggestion": f"子代理只能使用: {', '.join(allowed_tools)}"
                }
            return {"allowed": True, "reason": "子代理工具类型验证通过"}

        # 3. 父代理或非Step4阶段，使用标准规则
        allowed_tools = stage_config.get('allowed_tools', [])

        if tool_name not in allowed_tools:
            display_name = stage_config.get('display_name', current_step)
            return {
                "allowed": False,
                "reason": f"阶段 {display_name} 不允许使用工具: {tool_name}",
                "suggestion": self._suggest_correct_tool(current_step, allowed_tools)
            }

        return {"allowed": True, "reason": "工具类型验证通过"}

    # ========== 第二层: 前置条件检查 ==========

    def _validate_layer2_preconditions(
        self,
        current_step: str,
        stage_config: Dict,
        task_meta: Dict
    ) -> Dict:
        """
        第二层验证: 检查前置条件是否满足 (v21.0)
        """
        preconditions = stage_config.get('preconditions', [])

        for precondition in preconditions:
            # 解析前置条件（v21.0: 移除 step0/step1，保留 step2）
            if precondition == "step2_completed":
                if not self._is_step_completed("step2_research", task_meta):
                    return {
                        "allowed": False,
                        "reason": "前置条件未满足: Step2（任务研究阶段）尚未完成",
                        "suggestion": "请先完成文档研究，明确说明研究结论后继续"
                    }

            elif precondition == "user_confirmed":
                if not task_meta.get('steps', {}).get('step3_execute', {}).get('user_confirmed', False):
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
        第三层验证: 检查文件路径是否符合规则 (v21.0)
        """
        # 1. 检查是否在子代理上下文中
        task_id = task_meta.get('task_id')
        is_subagent = self.task_meta_manager.check_subagent_lock(task_id) if task_id else False

        # 2. 获取路径规则
        if is_subagent and current_step == "step4_cleanup":
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
        第四层验证: 操作语义分析（最细粒度） (v21.0/v22.0增强)

        v22.0新增:
        - step2_research强制研究阶段：拦截所有Write/Edit/Bash
        - step3_execute执行阶段：检查文档阅读数量
        """
        # ========== v22.0: Step2研究阶段强制拦截 ==========
        if current_step == "step2_research":
            if tool_name in ["Write", "Edit"]:
                docs_read = task_meta.get('metrics', {}).get('docs_read', [])
                docs_count = len(docs_read)
                required_docs = task_meta.get('steps', {}).get('step2_research', {}).get('required_doc_count', 3)

                return {
                    "allowed": False,
                    "reason": "研究阶段严禁修改文件",
                    "suggestion": f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 当前阶段: 任务研究（Step2 - 强制）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

你现在处于强制研究阶段，需要先完成文档查阅。

📊 进度: 已查阅 {docs_count}/{required_docs} 个文档

下一步操作:
1. 继续使用 Read/Grep/Glob 查阅相关文档
2. 至少查阅 {required_docs} 个文档后
3. 明确说明你的研究结论（包含关键词："研究完成"或"已理解问题根因"）
4. Hook会自动推进到step3执行阶段，届时可以使用Write/Edit修改代码

**当前禁止操作**:
- ❌ Write/Edit任何文件
- ❌ Bash执行命令

**当前允许操作**:
- ✅ Read 阅读文档和代码
- ✅ Grep 搜索相关实现
- ✅ Glob 查找文件

请遵守工作流规范，完成研究后再进行修改。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
                }

            if tool_name == "Bash":
                return {
                    "allowed": False,
                    "reason": "研究阶段禁止执行命令",
                    "suggestion": "请先完成文档查阅，明确说明'研究完成'后再执行测试"
                }

        # ========== v22.0: Step3执行阶段检查研究深度 ==========
        if current_step == "step3_execute":
            if tool_name in ["Write", "Edit"]:
                docs_read = task_meta.get('metrics', {}).get('docs_read', [])
                docs_count = len(docs_read)

                # 获取required_doc_count（玩法包模式为2，标准模式为3）
                required_docs = task_meta.get('steps', {}).get('step2_research', {}).get('required_doc_count', 3)

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
1. 返回step2_research阶段
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

        # ========== v21.0: 标准语义分析 ==========
        # 1. 检查是否在子代理上下文中
        task_id = task_meta.get('task_id')
        is_subagent = self.task_meta_manager.check_subagent_lock(task_id) if task_id else False

        # 2. 获取语义规则
        if is_subagent and current_step == "step4_cleanup":
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
        """检查步骤是否已完成 (v21.0)"""
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

        # 特殊阶段的额外提示（v21.0: 移除 step0/step1/step2_route 提示）
        if current_step == "step2_research":
            suggestion += "\n请查阅至少3个相关文档，理解问题根因和技术约束，明确说明研究结论后继续"
        elif current_step == "step4_cleanup":
            suggestion += "\n请使用 Task 工具启动收尾子代理"

        return suggestion.strip()
