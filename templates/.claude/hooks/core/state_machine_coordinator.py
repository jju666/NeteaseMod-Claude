#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
State Machine Coordinator - 状态机协调器 (v25.0)

统一状态转移入口，确保100%合法转移。

核心功能：
1. 封装所有状态转移逻辑（Planning→Implementation, Implementation→Finalization等）
2. 调用StateTransitionValidator验证合法性
3. 调用validate_transition_requirements验证前置条件
4. 保存历史快照（_snapshot_step_state）
5. 通过TaskMetaManager.atomic_update执行原子更新
6. 记录转移日志（_log_state_transition）

作者: NeteaseMod-Claude工作流系统
版本: v25.0
日期: 2025-11-20
"""

import sys
import os
from datetime import datetime


class TransitionResult:
    """
    状态转移结果

    Attributes:
        success: 转移是否成功
        error: 错误信息（success=False时）
        from_step: 源状态
        to_step: 目标状态
    """

    def __init__(self, success, error=None, from_step=None, to_step=None):
        self.success = success
        self.error = error
        self.from_step = from_step
        self.to_step = to_step

    def __repr__(self):
        if self.success:
            return f"TransitionResult(success=True, {self.from_step}→{self.to_step})"
        else:
            return f"TransitionResult(success=False, error={self.error})"


class StateMachineCoordinator:
    """
    状态机协调器 - 统一状态转移入口 (v25.0)

    特性：
    - 100%合法转移验证（硬编码VALID_TRANSITIONS表）
    - 前置条件检查（文档数量、专家审查）
    - 原子更新（TaskMetaManager.atomic_update）
    - 历史留痕（_snapshot_step_state）
    - 转移日志（_log_state_transition）
    """

    def __init__(self, cwd):
        """
        初始化状态机协调器

        Args:
            cwd: 工作目录
        """
        self.cwd = cwd
        self.meta_manager = self._get_task_meta_manager()
        self.validator = self._get_state_transition_validator()

    def transition(
        self,
        task_id,
        from_step,
        to_step,
        trigger,
        details
    ):
        """
        统一状态转移方法

        流程：
        1. 加载元数据
        2. 调用StateTransitionValidator验证合法性
        3. 调用validate_transition_requirements验证前置条件
        4. 保存历史快照（_snapshot_step_state）
        5. 通过TaskMetaManager.atomic_update执行原子更新
        6. 记录转移日志（_log_state_transition）

        Args:
            task_id: 任务ID
            from_step: 源状态（planning/implementation/finalization）
            to_step: 目标状态
            trigger: 触发原因（user_agreed/test_passed/expert_review_completed等）
            details: 转移详情字典（user_input等）

        Returns:
            TransitionResult: 转移结果对象

        Examples:
            >>> coordinator = StateMachineCoordinator('/path/to/project')
            >>> result = coordinator.transition(
            ...     task_id='任务-1120-123456-测试',
            ...     from_step='planning',
            ...     to_step='implementation',
            ...     trigger='user_agreed',
            ...     details={'user_input': '同意'}
            ... )
            >>> result.success
            True
        """
        if not self.meta_manager:
            return TransitionResult(
                success=False,
                error='TaskMetaManager不可用'
            )

        # 1. 加载元数据
        try:
            meta_data = self.meta_manager.load_task_meta(task_id)
            if not meta_data:
                return TransitionResult(
                    success=False,
                    error=f'任务元数据不存在: {task_id}'
                )
        except Exception as e:
            return TransitionResult(
                success=False,
                error=f'加载元数据失败: {e}'
            )

        # 2. 验证转移合法性（StateTransitionValidator）
        if self.validator:
            try:
                from core.state_transition_validator import validate_state_transition
                validate_state_transition(
                    from_step=from_step,
                    to_step=to_step,
                    strict=True
                )
            except Exception as e:
                return TransitionResult(
                    success=False,
                    error=f'状态转移验证失败: {e}',
                    from_step=from_step,
                    to_step=to_step
                )

        # 3. 验证前置条件（validate_transition_requirements）
        try:
            from core.state_transition_validator import validate_transition_requirements
            validate_transition_requirements(
                from_step=from_step,
                to_step=to_step,
                meta_data=meta_data,
                strict=True
            )
        except Exception as e:
            return TransitionResult(
                success=False,
                error=f'前置条件验证失败: {e}',
                from_step=from_step,
                to_step=to_step
            )

        # 4. 通过atomic_update执行原子状态转移
        try:
            def apply_fn(meta):
                return self._apply_transition(meta, from_step, to_step, trigger, details)

            self.meta_manager.atomic_update(task_id, apply_fn)

            return TransitionResult(
                success=True,
                from_step=from_step,
                to_step=to_step
            )
        except Exception as e:
            return TransitionResult(
                success=False,
                error=f'状态转移执行失败: {e}',
                from_step=from_step,
                to_step=to_step
            )

    def _get_task_meta_manager(self):
        """
        获取TaskMetaManager实例

        Returns:
            TaskMetaManager实例，失败返回None
        """
        try:
            # 动态导入，避免循环依赖
            from core.task_meta_manager import TaskMetaManager
            return TaskMetaManager(self.cwd)
        except ImportError:
            sys.stderr.write(u"[ERROR] TaskMetaManager不可用\n")
            return None

    def _get_state_transition_validator(self):
        """
        获取StateTransitionValidator模块

        Returns:
            module或None
        """
        try:
            from core import state_transition_validator
            return state_transition_validator
        except ImportError:
            sys.stderr.write(u"[WARN] StateTransitionValidator不可用，跳过状态转移验证\n")
            return None

    def _apply_transition(self, meta_data, from_step, to_step, trigger, details):
        """
        应用状态转移（atomic_update回调函数）

        Args:
            meta_data: 任务元数据
            from_step: 源状态
            to_step: 目标状态
            trigger: 触发原因
            details: 转移详情

        Returns:
            dict: 更新后的元数据
        """
        # 1. 保存历史快照（源步骤）
        if from_step:
            self._snapshot_step_state(meta_data, from_step)

        # 2. 记录转移日志（在状态转移前记录）
        self._log_state_transition(meta_data, from_step, to_step, trigger, details)

        # 2.5 🔥 P0-2修复：如果回退到Planning，自动重置Planning步骤
        if to_step == 'planning' and trigger in ['planning_required', 'explicit_failure', 'loop_detected']:
            self._reset_planning_step(meta_data, reason=trigger)
            # _reset_planning_step已经更新了current_step和status，直接返回
            meta_data['current_step'] = to_step  # 确保current_step正确
            return meta_data

        # 3. 更新current_step
        meta_data['current_step'] = to_step

        # 4. 更新源步骤状态（status='completed'）
        if from_step and from_step in meta_data.get('steps', {}):
            meta_data['steps'][from_step]['status'] = 'completed'
            meta_data['steps'][from_step]['completed_at'] = datetime.now().isoformat()

        # 5. 更新目标步骤状态（status='in_progress'）
        if to_step and to_step in meta_data.get('steps', {}):
            meta_data['steps'][to_step]['status'] = 'in_progress'
            if 'started_at' not in meta_data['steps'][to_step]:
                meta_data['steps'][to_step]['started_at'] = datetime.now().isoformat()

        # 6. 🔥 v25.2修复：已移除缓存同步逻辑
        # 问题根因：v25.1的缓存同步方案违反单一数据源原则
        # 新方案：PreToolUse直接从task-meta.json读取current_step，无需缓存同步
        # 收益：简化架构，删除~110行复杂代码，零缓存不一致风险

        return meta_data

    # ==================== 辅助函数（从user_prompt_handler.py迁移） ====================

    def _snapshot_step_state(self, meta_data, step_name):
        """
        将当前步骤状态保存为历史快照 (v23.0新增)

        实现完整的历史留痕机制,每次状态转移前保存当前状态快照到iterations数组,
        确保所有信息追加而非覆盖,方便收尾子代理分析完整历史生成归档文档。

        Args:
            meta_data: 任务元数据字典
            step_name: 步骤名称 ('planning' | 'implementation' | 'finalization')

        Returns:
            dict: 创建的快照对象,如果失败返回None
        """
        if 'steps' not in meta_data:
            return None

        step_data = meta_data['steps'].get(step_name)
        if not step_data:
            return None

        # 初始化iterations数组
        if 'iterations' not in step_data:
            step_data['iterations'] = []

        # 计算迭代ID
        iteration_id = len(step_data['iterations']) + 1

        # 创建快照(基础结构)
        snapshot = {
            "iteration_id": iteration_id,
            "timestamp": datetime.now().isoformat(),
            "status": step_data.get('status', 'unknown'),
            "config": {},   # 配置字段(required_doc_count, expert_review_required等)
            "process": {},  # 过程字段(docs_read_count, tools_used等)
            "outcome": {}   # 结果字段(user_confirmed, solution_proposal等)
        }

        # 定义字段分类
        config_fields = ['required_doc_count', 'expert_review_required', 'task_type']
        process_fields = ['expert_review_triggered', 'expert_review_count']
        outcome_fields = [
            'user_confirmed', 'solution_proposal', 'expert_review_result',
            'expert_review_completed', 'confirmed_at', 'completed_at',
            'started_at', 'resumed_at', 'resumed_reason'
        ]

        # 提取配置字段
        for field in config_fields:
            if field in step_data:
                snapshot['config'][field] = step_data[field]

        # 提取过程字段
        for field in process_fields:
            if field in step_data:
                snapshot['process'][field] = step_data[field]

        # 提取结果字段
        for field in outcome_fields:
            if field in step_data:
                snapshot['outcome'][field] = step_data[field]

        # 特殊处理: implementation步骤保存完整的test_feedback_history和code_changes
        if step_name == 'implementation':
            if 'test_feedback_history' in step_data:
                snapshot['test_feedback'] = step_data['test_feedback_history'][:]

            # 从metrics中提取当前iteration的code_changes
            metrics = meta_data.get('metrics', {})
            code_changes = metrics.get('code_changes', [])
            if code_changes:
                snapshot['code_changes'] = code_changes[:]

        # 追加到历史
        step_data['iterations'].append(snapshot)
        step_data['current_iteration_id'] = iteration_id

        return snapshot

    def _log_state_transition(self, meta_data, from_step, to_step, trigger, details):
        """
        记录状态转移到全局日志 (v23.0新增)

        在state_transitions数组中追加每次状态转移的详细信息,
        包括转移触发原因、用户输入、前置条件检查结果、迭代ID等,
        确保完整可追溯的状态机执行历史。

        Args:
            meta_data: 任务元数据字典
            from_step: 源状态 (None表示任务初始化)
            to_step: 目标状态
            trigger: 触发原因 ('user_agreed' | 'explicit_success' | 'explicit_failure' | 'task_initialized' 等)
            details: 详细信息字典 (包含user_input, code_changes_count等)

        Returns:
            dict: 创建的转移记录对象
        """
        if 'state_transitions' not in meta_data:
            meta_data['state_transitions'] = []

        transition_id = len(meta_data['state_transitions']) + 1

        transition = {
            "id": transition_id,
            "from_step": from_step,
            "to_step": to_step,
            "timestamp": datetime.now().isoformat(),
            "trigger": trigger,
            "details": details
        }

        # 添加前置条件快照(如果是进入Implementation阶段)
        if to_step == 'implementation':
            planning = meta_data.get('steps', {}).get('planning', {})
            transition['preconditions_met'] = {
                "docs_read": len(meta_data.get('metrics', {}).get('docs_read', [])),
                "required_doc_count": planning.get('required_doc_count'),
                "expert_review_completed": planning.get('expert_review_completed'),
                "expert_review_result": planning.get('expert_review_result')
            }

        # 添加迭代ID引用
        if from_step:
            from_step_data = meta_data.get('steps', {}).get(from_step, {})
            if 'current_iteration_id' in from_step_data:
                transition[f"{from_step}_iteration"] = from_step_data['current_iteration_id']

        if to_step:
            to_step_data = meta_data.get('steps', {}).get(to_step, {})
            # 即将开始的新迭代ID
            next_iteration_id = len(to_step_data.get('iterations', [])) + 1
            transition[f"{to_step}_iteration"] = next_iteration_id

        # 标记回滚
        if from_step and to_step:
            step_order = ['planning', 'implementation', 'finalization']
            from_index = step_order.index(from_step) if from_step in step_order else -1
            to_index = step_order.index(to_step) if to_step in step_order else -1
            if to_index >= 0 and from_index > to_index:
                transition['rollback'] = True

        meta_data['state_transitions'].append(transition)

        return transition

    def _reset_planning_step(self, meta_data, reason='rollback'):
        """
        统一的Planning步骤重置逻辑 (v26.0增强：planning_round支持)

        确保回滚到Planning时所有必需字段都被正确初始化,
        特别是required_doc_count和expert_review_*字段,
        从而解决字段丢失导致的"强制阅读文档"等问题。

        v26.0新增：
        - 从implementation返回planning时，planning_round +1（新一轮planning）
        - 重置expert_review_completed为False（允许新一轮审查）
        - 保留expert_reviews数组（完整历史）

        Args:
            meta_data: 任务元数据字典
            reason: 重置原因 ('rollback' | 'planning_required' | 'loop_detected' | 'explicit_failure')

        Returns:
            dict: 重置后的planning步骤数据
        """
        task_type = meta_data.get('task_type', 'general')

        if 'planning' not in meta_data.get('steps', {}):
            meta_data.setdefault('steps', {})['planning'] = {}

        planning = meta_data['steps']['planning']

        # 基础状态重置
        planning['user_confirmed'] = False
        planning['status'] = 'in_progress'
        planning['resumed_at'] = datetime.now().isoformat()

        # 【P0 BUG修复】文档要求初始化(确保字段存在)
        if 'required_doc_count' not in planning:
            planning['required_doc_count'] = 0 if task_type == 'bug_fix' else 3

        # 🔥 v26.0新增：planning_round管理
        if 'planning_round' not in planning:
            planning['planning_round'] = 1  # 首次初始化
        elif reason in ['explicit_failure', 'loop_detected']:
            # 从implementation返回planning时，轮次+1
            planning['planning_round'] += 1
            sys.stderr.write(u"[INFO v26.0] Planning轮次递增: {} → {}\n".format(
                planning['planning_round'] - 1,
                planning['planning_round']
            ))

        # 🔥 v26.0新增：初始化expert_reviews数组（首次）
        if 'expert_reviews' not in planning:
            planning['expert_reviews'] = []

        # 【P0 BUG修复】专家审查状态初始化(bug_fix类型必需)
        if task_type == 'bug_fix':
            planning['expert_review_required'] = True

            # 🔥 v26.0修改：重置expert_review_completed，允许新一轮审查
            planning['expert_review_completed'] = False

            planning['expert_review_result'] = None

            # 保留expert_review_count(累计值,不重置)
            if 'expert_review_count' not in planning:
                planning['expert_review_count'] = 0

        # 拒绝计数初始化(用于循环检测,保留历史值)
        if 'rejection_count' not in planning:
            planning['rejection_count'] = 0
        if 'rejection_history' not in planning:
            planning['rejection_history'] = []

        # 记录重置原因
        planning['resumed_reason'] = reason

        return planning

    # 🔥 v25.2 已删除：_sync_current_step_to_active_tasks() 方法
    # 原因：违反单一数据源原则（v21.0架构）
    # 新方案：PreToolUse直接从task-meta.json读取current_step，无需缓存同步
    # 收益：删除112行复杂代码，简化架构，零缓存不一致风险

# ==================== 导出符号 ====================

__all__ = [
    'StateMachineCoordinator',
    'TransitionResult'
]
