"""
Semantic Analyzer - 操作语义分析器
职责:
1. 区分同一工具的不同用途（Write代码 vs Write文档）
2. 检查操作前置条件（Write前必须Read）
3. 危险命令检测
4. 子代理上下文识别
"""

import re
import sys
from typing import Dict, Optional
from .path_validator import PathValidator


class SemanticAnalyzer:
    """操作语义分析器 - 第四层验证（最细粒度）"""

    def __init__(self, path_validator: PathValidator):
        self.path_validator = path_validator

    def analyze(
        self,
        current_step: str,
        tool_name: str,
        tool_input: Dict,
        workflow_state: Dict,
        semantic_rules: Dict,
        is_subagent: bool = False
    ) -> Dict:
        """
        语义级别分析

        Args:
            current_step: 当前阶段
            tool_name: 工具名称
            tool_input: 工具输入参数
            workflow_state: 工作流状态
            semantic_rules: 语义规则配置
            is_subagent: 是否在子代理上下文中

        Returns:
            {"allowed": bool, "reason": str, "suggestion": str}
        """
        # 1. 检查工具是否被明确禁止
        if semantic_rules.get('forbidden', False):
            return {
                "allowed": False,
                "reason": semantic_rules.get('reason', f"{tool_name}工具在{current_step}阶段被禁止"),
                "suggestion": f"阶段 {current_step} 不允许使用 {tool_name} 工具"
            }

        # 2. 检查是否在父代理中被禁止（Step4特殊规则）
        if semantic_rules.get('forbidden_in_parent', False) and not is_subagent:
            return {
                "allowed": False,
                "reason": semantic_rules.get('reason', f"{tool_name}工具在父代理中被禁止"),
                "suggestion": "请使用Task工具启动收尾子代理"
            }

        # 3. 按工具类型分发分析
        if tool_name == "Write":
            return self._analyze_write(current_step, tool_input, workflow_state, semantic_rules, is_subagent)
        elif tool_name == "Edit":
            return self._analyze_edit(current_step, tool_input, workflow_state, semantic_rules, is_subagent)
        elif tool_name == "Bash":
            return self._analyze_bash(current_step, tool_input, workflow_state, semantic_rules)
        elif tool_name == "Read":
            return self._analyze_read(current_step, tool_input, workflow_state, semantic_rules)
        elif tool_name == "Task":
            return self._analyze_task(current_step, tool_input, workflow_state, semantic_rules)

        # 4. 其他工具默认通过
        return {"allowed": True, "reason": "无需语义分析"}

    # ============== Write 语义分析 ==============

    def _analyze_write(
        self,
        current_step: str,
        tool_input: Dict,
        workflow_state: Dict,
        semantic_rules: Dict,
        is_subagent: bool
    ) -> Dict:
        """Write工具语义分析"""
        file_path = tool_input.get("file_path", "")

        # （v3.0 Final: planning 的 Write 禁止由 stage_validator Layer 4 统一处理）

        # 2. Finalization父代理禁止Write
        if current_step == "finalization" and not is_subagent:
            return {
                "allowed": False,
                "reason": "finalization父代理禁止直接Write",
                "suggestion": "请使用Task工具启动收尾子代理"
            }

        # 3. 检查是否为元数据文件
        if self.path_validator.is_metadata_file(file_path):
            # 只有子代理可以写元数据
            if not is_subagent:
                return {
                    "allowed": False,
                    "reason": f"禁止手动修改元数据文件: {file_path}",
                    "suggestion": "元数据由系统自动维护"
                }

        # 4. Implementation阶段:检查Write代码前是否Read过
        if current_step == "implementation":
            if self.path_validator.is_code_file(file_path):
                # 检查是否先Read过该文件
                requires_read_first = semantic_rules.get('requires_read_first', False)
                if requires_read_first:
                    if not self._has_read_file_before(file_path, workflow_state):
                        return {
                            "allowed": False,
                            "reason": f"写入代码文件前必须先Read: {file_path}",
                            "suggestion": f"请先使用 Read('{file_path}') 阅读文件内容，了解现有实现"
                        }

        return {"allowed": True, "reason": "Write语义验证通过"}

    # ============== Edit 语义分析 ==============

    def _analyze_edit(
        self,
        current_step: str,
        tool_input: Dict,
        workflow_state: Dict,
        semantic_rules: Dict,
        is_subagent: bool
    ) -> Dict:
        """Edit工具语义分析"""
        file_path = tool_input.get("file_path", "")

        # （v3.0 Final: planning 的 Edit 禁止由 stage_validator Layer 4 统一处理）

        # 2. Finalization父代理禁止Edit
        if current_step == "finalization" and not is_subagent:
            return {
                "allowed": False,
                "reason": "finalization父代理禁止直接Edit",
                "suggestion": "请使用Task工具启动收尾子代理"
            }

        # 3. 禁止编辑元数据文件
        if self.path_validator.is_metadata_file(file_path):
            if not is_subagent:
                return {
                    "allowed": False,
                    "reason": f"禁止手动修改元数据文件: {file_path}",
                    "suggestion": "元数据由系统自动维护"
                }

        # 4. Implementation阶段:检查同文件编辑次数（触发专家检测）
        if current_step == "implementation":
            max_edits = semantic_rules.get('max_same_file_edits', 999)
            same_file_count = self._count_same_file_edits(file_path, workflow_state)

            # 注意：这里不强制拦截，只是警告（专家系统会在PostToolUse触发）
            if same_file_count >= max_edits:
                sys.stderr.write(
                    f"[警告] 文件 {file_path} 已被编辑 {same_file_count} 次，"
                    f"可能陷入循环，专家系统将在下次工具调用后触发\n"
                )

        return {"allowed": True, "reason": "Edit语义验证通过"}

    # ============== Bash 语义分析 ==============

    def _analyze_bash(
        self,
        current_step: str,
        tool_input: Dict,
        workflow_state: Dict,
        semantic_rules: Dict
    ) -> Dict:
        """Bash工具语义分析"""
        command = tool_input.get("command", "")

        # （v3.0 Final: planning 的 Bash 禁止由 stage_validator Layer 4 统一处理）

        # 2. 危险命令检测
        dangerous_patterns = [
            (r"rm\s+-rf\s+/", "删除根目录"),
            (r"git\s+push\s+--force", "强制推送"),
            (r"sudo\b", "提权命令"),
            (r"mkfs\b", "格式化磁盘"),
            (r"dd\s+if=", "直接磁盘操作"),
            (r":(){ :|:& };:", "Fork炸弹"),
            (r">\s*/dev/sd", "直接写入磁盘设备")
        ]

        for pattern, description in dangerous_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return {
                    "allowed": False,
                    "reason": f"检测到危险命令: {description}",
                    "suggestion": "为了安全，该命令已被阻止"
                }

        # 3. 检查命令白名单（Implementation阶段）
        if current_step == "implementation":
            allowed_patterns = semantic_rules.get('allowed_commands_patterns', [])
            if allowed_patterns:
                # 如果定义了白名单，检查是否匹配
                if not any(re.match(pattern, command) for pattern in allowed_patterns):
                    # 不在白名单中，但不一定拦截，给出警告
                    sys.stderr.write(
                        f"[警告] 命令可能不符合规范: {command}\n"
                        f"建议使用: {', '.join(allowed_patterns[:2])}\n"
                    )

        return {"allowed": True, "reason": "Bash语义验证通过"}

    # ============== Read 语义分析 ==============

    def _analyze_read(
        self,
        current_step: str,
        tool_input: Dict,
        workflow_state: Dict,
        semantic_rules: Dict
    ) -> Dict:
        """Read工具语义分析"""
        file_path = tool_input.get("file_path", "")

        # （v3.0 Final: Read 操作的语义规则现在主要由 path_rules 和通用的 semantic_rules 控制）

        return {"allowed": True, "reason": "Read语义验证通过"}

    # ============== Task 语义分析 ==============

    def _analyze_task(
        self,
        current_step: str,
        tool_input: Dict,
        workflow_state: Dict,
        semantic_rules: Dict
    ) -> Dict:
        """Task工具语义分析"""
        # 1. 只有Finalization阶段可以使用Task启动收尾子代理
        if current_step != "finalization":
            # 其他阶段使用Task没有特殊限制
            return {"allowed": True, "reason": "Task工具验证通过"}

        # 2. Finalization阶段:检查是否已经启动过子代理
        max_launches = semantic_rules.get('max_launches', 999)
        task_dir = workflow_state.get('task_id', '')
        if task_dir:
            # 检查锁文件是否存在
            import os
            cwd = os.getcwd()
            lock_file = os.path.join(cwd, 'tasks', task_dir, '.cleanup-subagent.lock')
            if os.path.exists(lock_file):
                return {
                    "allowed": False,
                    "reason": "收尾子代理已经在运行中",
                    "suggestion": "请等待子代理完成"
                }

        # 3. 检查子代理参数（Step4要求特定参数）
        required_params = semantic_rules.get('required_params', {})
        if required_params:
            subagent_type = tool_input.get('subagent_type', '')
            description = tool_input.get('description', '')

            if 'subagent_type' in required_params:
                if subagent_type != required_params['subagent_type']:
                    return {
                        "allowed": False,
                        "reason": f"subagent_type必须为: {required_params['subagent_type']}",
                        "suggestion": "请按照Hook提示使用正确的参数启动子代理"
                    }

            if 'description_pattern' in required_params:
                pattern = required_params['description_pattern']
                if not re.search(pattern, description):
                    return {
                        "allowed": False,
                        "reason": "Task描述不符合收尾子代理要求",
                        "suggestion": "请使用 description='文档更新与收尾工作'"
                    }

        return {"allowed": True, "reason": "Task工具验证通过"}

    # ============== 辅助方法 ==============

    def _has_read_file_before(self, file_path: str, workflow_state: Dict) -> bool:
        """检查是否在Write/Edit之前Read过该文件"""
        # 从workflow_state的metrics中查找docs_read或code_changes
        # 简化实现：如果file_path在docs_read或最近的tool调用历史中，认为已读过
        metrics = workflow_state.get('metrics', {})
        docs_read = metrics.get('docs_read', [])

        # 规范化路径进行比较
        normalized_target = self.path_validator._normalize_path(file_path)

        for doc in docs_read:
            normalized_doc = self.path_validator._normalize_path(doc)
            if normalized_doc == normalized_target:
                return True

        return False

    def _count_same_file_edits(self, file_path: str, workflow_state: Dict) -> int:
        """统计同一文件的编辑次数"""
        metrics = workflow_state.get('metrics', {})
        code_changes = metrics.get('code_changes', [])

        # 规范化路径进行比较
        normalized_target = self.path_validator._normalize_path(file_path)

        count = 0
        for change in code_changes:
            change_file = change.get('file', '')
            normalized_change = self.path_validator._normalize_path(change_file)
            if normalized_change == normalized_target:
                count += 1

        return count
