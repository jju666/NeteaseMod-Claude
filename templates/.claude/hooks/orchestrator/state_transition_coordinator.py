#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
State Transition Coordinator - 状态转移协调器 (v25.0)

统一状态转移逻辑协调，处理Planning和Implementation阶段的用户反馈。

核心功能：
1. 用户反馈意图识别（调用LLMIntentAnalyzer）
2. Planning→Implementation转移
3. Implementation→Finalization转移
4. Planning回退逻辑（Implementation→Planning）
5. Planning拒绝处理（多次拒绝机制）
6. 前置条件验证（文档数量、专家审查）
7. 状态转移执行（调用StateMachineCoordinator）

作者: NeteaseMod-Claude工作流系统
版本: v25.0
日期: 2025-11-20
"""

import sys
import os
from datetime import datetime


class StateTransitionCoordinator:
    """
    状态转移协调器 (v25.0 LLM驱动)

    负责所有状态转移逻辑的协调，包括：
    - LLM意图分析
    - 前置条件验证
    - 状态转移执行
    - 用户消息生成
    """

    def __init__(self, cwd, session_id):
        """
        初始化状态转移协调器

        Args:
            cwd: 工作目录
            session_id: 当前会话ID
        """
        self.cwd = cwd
        self.session_id = session_id
        self.meta_manager = self._get_task_meta_manager()
        self.intent_analyzer = self._get_intent_analyzer()
        self.state_machine = self._get_state_machine()

    def handle_user_feedback(self, user_input):
        """
        处理用户反馈（主入口）

        Args:
            user_input: 用户输入文本

        Returns:
            Optional[dict]: 转移结果字典，无转移返回None
                {
                    'continue': True/False,
                    'additionalContext': str  # 用户消息
                }

        Examples:
            >>> coordinator = StateTransitionCoordinator('/path/to/project', 'session123')
            >>> result = coordinator.handle_user_feedback("同意")
            >>> result['continue']
            True
        """
        if not self.meta_manager:
            return None

        # 获取当前会话绑定的任务
        active_task = self.meta_manager.get_active_task_by_session(self.session_id)
        if not active_task:
            return None

        task_id = active_task['task_id']
        meta_data = self.meta_manager.load_task_meta(task_id)
        if not meta_data:
            return None

        current_step = meta_data.get('current_step', '')

        # 根据当前阶段分发处理
        if current_step == 'planning':
            return self._handle_planning_feedback(task_id, meta_data, user_input)
        elif current_step == 'implementation':
            return self._handle_implementation_feedback(task_id, meta_data, user_input)
        else:
            # 其他阶段暂不处理
            return None

    # ==================== Planning阶段处理 ====================

    def _handle_planning_feedback(self, task_id, meta_data, user_input):
        """
        Planning阶段反馈处理

        Args:
            task_id: 任务ID
            meta_data: 任务元数据
            user_input: 用户输入

        Returns:
            dict: 处理结果
        """
        # 🔥 v30.1修复：ABC选项前置检测（优先级最高）
        # 问题根因：之前ABC检测在_fallback_planning_keywords()中（Line 502-523），
        #          但该方法只在LLM失败时调用，导致"A"被LLM成功分析但误判后无法触发
        # 解决方案：在LLM分析之前提前检测ABC单字母输入，确保用户选择能被正确识别
        import re
        option_pattern = r'^\s*([ABC])\s*$'  # 严格匹配单字母（去除前后空白）
        option_match = re.search(option_pattern, user_input, re.IGNORECASE)

        if option_match:
            option_letter = option_match.group(1).upper()
            sys.stderr.write(u"[INFO v30.1] ABC前置检测: 用户选择选项 {}\n".format(option_letter))

            if option_letter == 'A':
                # A选项 → 同意方案
                sys.stderr.write(u"[INFO v30.1] 选项A → 尝试转移到Implementation阶段\n")
                return self._transition_planning_to_implementation(task_id, meta_data, user_input)
            elif option_letter in ['B', 'C']:
                # B/C选项 → 拒绝方案
                sys.stderr.write(u"[INFO v30.1] 选项{} → 拒绝方案，重新规划\n".format(option_letter))
                return self._handle_planning_rejection(task_id, meta_data, user_input)

        # 未检测到ABC选项，继续原有的LLM分析流程
        sys.stderr.write(u"[DEBUG v30.1] 未检测到ABC选项，启动LLM意图分析\n")

        if not self.intent_analyzer:
            return self._generate_llm_failure_prompt('planning')

        # 1. LLM意图分析
        intent_result = self.intent_analyzer.analyze_planning_intent(
            user_input, meta_data
        )

        if not intent_result['success']:
            # LLM分析失败，降级到关键词匹配
            return self._fallback_planning_keywords(task_id, meta_data, user_input)

        intent = intent_result['intent']
        sys.stderr.write(u"[INFO] Planning意图: {}\n".format(intent))

        # 2. 根据意图路由（v26.1简化：删除restart意图，统一使用reject）
        if intent == 'agree':
            return self._transition_planning_to_implementation(
                task_id, meta_data, user_input
            )
        elif intent == 'reject':
            return self._handle_planning_rejection(
                task_id, meta_data, user_input
            )
        else:
            # v29.0：默认为调整建议，让AI继续迭代方案
            sys.stderr.write(u"[INFO v29.0] Planning阶段：用户提供调整建议\n")

            # 生成仪表盘
            try:
                from utils.dashboard_generator import generate_context_dashboard
                dashboard = generate_context_dashboard(meta_data)
            except Exception as e:
                sys.stderr.write(u"[WARN] 仪表盘生成失败: {}\n".format(e))
                dashboard = u""

            # 引导消息
            guidance = u"""用户提供了反馈，请根据反馈继续完善方案，然后重新展示完整方案并等待用户明确确认（"同意"/"可以"/"确认"）。

⚠️ 提醒：当前处于Planning阶段，禁止使用Write/Edit工具修改代码。"""

            return {
                'continue': True,
                'systemMessage': dashboard + u"\n\n" + guidance if dashboard else guidance
            }

    def _transition_planning_to_implementation(
        self, task_id, meta_data, user_input
    ):
        """
        Planning→Implementation转移

        Args:
            task_id: 任务ID
            meta_data: 任务元数据
            user_input: 用户输入

        Returns:
            dict: 转移结果
        """
        # 1. 前置条件验证
        validation_result = self._validate_planning_transition(meta_data)
        if not validation_result['valid']:
            # 生成仪表盘
            try:
                from utils.dashboard_generator import generate_context_dashboard
                dashboard = generate_context_dashboard(meta_data)
                block_message = dashboard + u"\n\n" + validation_result['block_message']
            except Exception as e:
                sys.stderr.write(u"[WARN] 仪表盘生成失败: {}\n".format(e))
                block_message = validation_result['block_message']

            return {
                'continue': False,
                'systemMessage': block_message
            }

        # 2. 设置用户确认标志（P0修复：validate_transition_requirements需要此字段）
        def set_user_confirmed(meta):
            if 'planning' in meta.get('steps', {}):
                meta['steps']['planning']['user_confirmed'] = True
            return meta

        self.meta_manager.atomic_update(task_id, set_user_confirmed)

        # 3. 执行状态转移（现在 user_confirmed 已经设置）
        if self.state_machine:
            transition_result = self.state_machine.transition(
                task_id=task_id,
                from_step='planning',
                to_step='implementation',
                trigger='user_agreed',
                details={'user_input': user_input}
            )

            if not transition_result.success:
                return {
                    'continue': False,
                    'systemMessage': u"⚠️ 状态转移失败: {}".format(transition_result.error)
                }

        # 3. 生成成功消息和仪表盘
        updated_meta = self.meta_manager.load_task_meta(task_id)
        try:
            from utils.dashboard_generator import generate_context_dashboard
            dashboard = generate_context_dashboard(updated_meta)
            message = self._format_transition_message('planning', 'implementation')
            full_message = dashboard + u"\n\n" + message
        except Exception as e:
            sys.stderr.write(u"[WARN] 仪表盘生成失败: {}\n".format(e))
            full_message = self._format_transition_message('planning', 'implementation')

        return {
            'continue': True,
            'systemMessage': full_message
        }

    def _validate_planning_transition(self, meta_data):
        """
        验证Planning→Implementation前置条件

        检查：
        1. 文档数量（非BUG修复任务: ≥3个）
        2. 专家审查（BUG修复任务: required）

        Args:
            meta_data: 任务元数据

        Returns:
            dict: 验证结果
                {
                    'valid': True/False,
                    'block_message': str  # valid=False时的阻止消息
                }
        """
        task_type = meta_data.get('task_type', 'general')
        planning_step = meta_data.get('steps', {}).get('planning', {})
        docs_read = meta_data.get('metrics', {}).get('docs_read', [])
        required_docs = planning_step.get('required_doc_count', 1)

        # 检查1：文档数量（非BUG修复任务）
        if required_docs > 0 and len(docs_read) < required_docs:
            return {
                'valid': False,
                'block_message': self._format_doc_count_block_message(
                    len(docs_read), required_docs
                )
            }

        # 检查2：专家审查（BUG修复任务）
        # 🔥 P1-2修复：根据task_type直接判断，而不是依赖expert_review_required字段
        # 这样即使字段丢失也能正确验证
        if task_type == 'bug_fix':
            expert_review_completed = planning_step.get('expert_review_completed', False)
            if not expert_review_completed:
                return {
                    'valid': False,
                    'block_message': self._format_expert_review_block_message()
                }

            # v30.2回滚：删除approved检查
            # 原因：approved=false只是对历史版本的评价，AI已经根据审查意见调整了方案
            # 用户看到的是调整后的新方案，不应被历史审查结果阻止

        return {'valid': True}

    def _handle_planning_rejection(
        self, task_id, meta_data, user_input
    ):
        """
        Planning阶段拒绝处理 - v26.0改进：支持Planning→Planning迭代循环

        拒绝响应机制：
        - 每次拒绝：重置确认状态，允许Planning阶段循环
        - BUG修复任务：每次拒绝都重置专家审查（确保新方案被审查）
        - 其他任务：提供重新制定方案的明确指引

        Args:
            task_id: 任务ID
            meta_data: 任务元数据
            user_input: 用户输入

        Returns:
            dict: 处理结果
        """
        planning_step = meta_data.get('steps', {}).get('planning', {})

        # 初始化拒绝追踪
        if 'rejection_count' not in planning_step:
            planning_step['rejection_count'] = 0
        if 'rejection_history' not in planning_step:
            planning_step['rejection_history'] = []

        # 记录拒绝
        planning_step['rejection_count'] += 1
        planning_step['rejection_history'].append({
            'timestamp': datetime.now().isoformat(),
            'user_feedback': user_input,
            'rejection_count': planning_step['rejection_count'],
            'detection_method': 'llm'
        })

        # v26.0改进：新增planning_round字段跟踪迭代轮次
        planning_round = planning_step.get('planning_round', 1)
        planning_step['planning_round'] = planning_round + 1

        # 重置确认状态（允许Planning阶段循环）
        planning_step['user_confirmed'] = False
        planning_step['status'] = 'in_progress'

        rejection_count = planning_step['rejection_count']
        task_type = meta_data.get('task_type', 'general')
        expert_review_required = planning_step.get('expert_review_required', False)

        # v26.0改进：BUG修复任务每次拒绝都重置专家审查（确保新方案被审查）
        if task_type == 'bug_fix' and expert_review_required:
            planning_step['expert_review_completed'] = False
            planning_step['expert_review_result'] = None

        # 原子更新metadata
        def update_fn(meta):
            meta['steps']['planning'] = planning_step
            # v26.0关键改进：保持current_step='planning'（允许循环）
            meta['current_step'] = 'planning'
            return meta

        self.meta_manager.atomic_update(task_id, update_fn)

        # v26.0可选：记录Planning→Planning转移（用于审计）
        if self.state_machine:
            try:
                self.state_machine.transition(
                    task_id=task_id,
                    from_step='planning',
                    to_step='planning',
                    trigger='user_rejected',
                    details={
                        'user_input': user_input,
                        'rejection_count': rejection_count,
                        'planning_round': planning_step['planning_round']
                    }
                )
            except Exception as e:
                # 转移记录失败不影响主流程
                sys.stderr.write(u"[WARN] Planning→Planning转移记录失败: {}\n".format(e))

        # v26.1改进：检测强烈否定关键词，动态调整消息语气
        strong_rejection_keywords = [u'重来', u'完全不对', u'重新开始', u'换个思路', u'方案错了']
        is_strong_rejection = any(kw in user_input.lower() for kw in strong_rejection_keywords)

        # 生成拒绝响应消息（v26.1优化：根据强烈程度调整语气）
        if is_strong_rejection:
            # 强烈否定：更强烈的语气和指引
            message_prefix = u"🔄 方案完全否定 → 重新开始Planning (第{planning_round}轮)"
            system_hint = u"**系统判断**: 你完全否定了当前方案，AI将忽略之前的思路重新开始。"

            if task_type == 'bug_fix' and expert_review_required:
                next_steps = u"""1. AI将**完全重新分析**问题根本原因（忽略之前的方案）
2. 制定**全新的修复方案**
3. **【必须】重新启动Task专家审查**
4. 等待审查结果并调整
5. 再次向你确认方案"""
            else:
                next_steps = u"""1. AI将**完全重新分析**任务需求（忽略之前的方案）
2. 重新查阅相关文档（如需要）
3. 制定**全新的实现方案**
4. 再次向你确认方案"""
        else:
            # 普通拒绝：温和的语气和指引
            message_prefix = u"⚠️ 方案被拒绝 → 继续Planning (第{planning_round}轮)"
            system_hint = u""

            if task_type == 'bug_fix' and expert_review_required:
                next_steps = u"""1. AI将根据你的反馈重新调整方案
2. **【必须】重新启动Task专家审查**（因为方案已调整）
3. 等待审查结果并继续调整
4. 再次向你确认方案"""
            else:
                next_steps = u"""1. AI将根据你的反馈重新调整方案
2. 重新查阅相关文档（如需要）
3. 再次向你确认方案"""

        message = u"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{message_prefix}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**你的反馈**: {user_feedback}

{system_hint}

**下一步**:
{next_steps}

**提示**:
- 如有更多上下文信息，请现在提供
- 调整完成后，请明确输入"同意"或"可以"推进到Implementation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(
            message_prefix=message_prefix.format(planning_round=planning_step['planning_round']),
            user_feedback=user_input[:100],
            system_hint=system_hint,
            next_steps=next_steps
        )

        # 生成仪表盘
        updated_meta = self.meta_manager.load_task_meta(task_id)
        try:
            from utils.dashboard_generator import generate_context_dashboard
            dashboard = generate_context_dashboard(updated_meta)
            full_message = dashboard + u"\n\n" + message
        except Exception as e:
            sys.stderr.write(u"[WARN] 仪表盘生成失败: {}\n".format(e))
            full_message = message

        return {
            'continue': True,  # v26.0关键改进：继续允许AI工作（Planning循环）
            'systemMessage': full_message
        }

    def _fallback_planning_keywords(self, task_id, meta_data, user_input):
        """
        Planning阶段关键词匹配降级方案（v29.3：新增ABC选项检测）

        Args:
            task_id: 任务ID
            meta_data: 任务元数据
            user_input: 用户输入

        Returns:
            dict: 处理结果
        """
        # ==================== 🔥 新增：ABC选项识别（最高优先级）====================
        # v29.3：对齐Implementation阶段ABCD选项设计
        import re
        option_pattern = r'(?:选项)?\s*([ABC])'
        option_match = re.search(option_pattern, user_input, re.IGNORECASE)

        if option_match:
            option_letter = option_match.group(1).upper()

            sys.stderr.write(u"[INFO v29.3] 关键词降级: 检测到ABC选项 {}\n".format(option_letter))

            # A选项 → 同意方案
            if option_letter == 'A':
                return self._transition_planning_to_implementation(
                    task_id, meta_data, user_input
                )
            # B/C选项 → 拒绝方案（系统会根据关键词自动判断强烈程度）
            elif option_letter in ['B', 'C']:
                return self._handle_planning_rejection(
                    task_id, meta_data, user_input
                )
        # ==================== ABC选项识别结束 ====================

        user_input_lower = user_input.lower()

        # 同意关键词（v29.1优化：删除"可以"和"继续"，避免误判）
        agree_keywords = ['同意', '确认', '没问题', '好的', '行', 'ok', 'yes']
        # 注意：删除"可以"和"继续"，因为它们太模糊：
        # - "我觉得可以检查一下" → 不是同意方案
        # - "可以继续实施" → 才是同意方案（但LLM应该能识别）
        if any(kw in user_input_lower for kw in agree_keywords):
            if '不同意' not in user_input_lower and '不可以' not in user_input_lower:
                return self._transition_planning_to_implementation(
                    task_id, meta_data, user_input
                )

        # 拒绝关键词（v26.1：合并restart关键词，统一处理）
        reject_keywords = [
            '不同意', '有问题', '需要调整', '不行', '不对',
            '重来', '重新开始', '完全不对'  # 原restart关键词
        ]
        if any(kw in user_input_lower for kw in reject_keywords):
            return self._handle_planning_rejection(
                task_id, meta_data, user_input
            )

        # 无法识别，返回提示
        return self._generate_llm_failure_prompt('planning')

    # ==================== Implementation阶段处理 ====================

    def _handle_implementation_feedback(
        self, task_id, meta_data, user_input
    ):
        """
        Implementation阶段反馈处理

        Args:
            task_id: 任务ID
            meta_data: 任务元数据
            user_input: 用户输入

        Returns:
            dict: 处理结果
        """
        if not self.intent_analyzer:
            return self._generate_llm_failure_prompt('implementation')

        # 1. LLM意图分析
        intent_result = self.intent_analyzer.analyze_implementation_intent(
            user_input, meta_data
        )

        if not intent_result['success']:
            return self._generate_llm_failure_prompt('implementation')

        intent = intent_result['intent']
        sys.stderr.write(u"[INFO] Implementation意图: {}\n".format(intent))

        # 2. 根据意图路由 (v25.2: 新增observation_only)
        if intent == 'complete_success':
            return self._transition_implementation_to_finalization(
                task_id, meta_data, user_input
            )
        elif intent == 'partial_success' or intent == 'continuation_request':
            return self._handle_partial_success(
                task_id, meta_data, user_input
            )
        elif intent == 'failure':
            return self._handle_implementation_failure(
                task_id, meta_data, user_input
            )
        elif intent == 'planning_required':
            return self._transition_implementation_to_planning(
                task_id, meta_data, user_input
            )
        elif intent == 'observation_only':
            # v25.2新增: 处理纯描述反馈（用户未明确表态）
            return self._handle_observation_only(
                task_id, meta_data, user_input
            )
        else:
            return None

    def _transition_implementation_to_finalization(
        self, task_id, meta_data, user_input
    ):
        """
        Implementation→Finalization转移

        Args:
            task_id: 任务ID
            meta_data: 任务元数据
            user_input: 用户输入

        Returns:
            dict: 转移结果
        """
        # 设置用户确认标志（P0修复：validate_transition_requirements需要此字段）
        def set_user_confirmed(meta):
            if 'implementation' in meta.get('steps', {}):
                meta['steps']['implementation']['user_confirmed'] = True
            return meta

        self.meta_manager.atomic_update(task_id, set_user_confirmed)

        # 执行状态转移（现在 user_confirmed 已经设置）
        if self.state_machine:
            transition_result = self.state_machine.transition(
                task_id=task_id,
                from_step='implementation',
                to_step='finalization',
                trigger='explicit_success',
                details={'user_input': user_input}
            )

            if not transition_result.success:
                return {
                    'continue': False,
                    'systemMessage': u"⚠️ 状态转移失败: {}".format(transition_result.error)
                }

        # 生成成功消息和仪表盘
        updated_meta = self.meta_manager.load_task_meta(task_id)
        try:
            from utils.dashboard_generator import generate_context_dashboard
            dashboard = generate_context_dashboard(updated_meta)
            message = self._format_transition_message('implementation', 'finalization')
            full_message = dashboard + u"\n\n" + message
        except Exception as e:
            sys.stderr.write(u"[WARN] 仪表盘生成失败: {}\n".format(e))
            full_message = self._format_transition_message('implementation', 'finalization')

        return {
            'continue': True,
            'systemMessage': full_message
        }

    def _transition_implementation_to_planning(
        self, task_id, meta_data, user_input
    ):
        """
        Implementation→Planning回退

        触发条件：
        - 用户反馈方案性错误（"方案错了"、"思路不对"）
        - 循环修复≥3次（partial_success ≥3次）

        Args:
            task_id: 任务ID
            meta_data: 任务元数据
            user_input: 用户输入

        Returns:
            dict: 回退结果
        """
        # 执行状态转移
        # 🔥 P0-2修复：只调用一次transition()，_apply_transition()会根据trigger自动调用_reset_planning_step
        if self.state_machine:
            transition_result = self.state_machine.transition(
                task_id=task_id,
                from_step='implementation',
                to_step='planning',
                trigger='planning_required',
                details={'user_input': user_input}
            )

            if not transition_result.success:
                return {
                    'continue': False,
                    'systemMessage': u"⚠️ 状态转移失败: {}".format(transition_result.error)
                }

        # v26.0优化：根据任务类型显示不同的专家审查要求和撤销指引
        task_type = meta_data.get('task_type', 'general')

        if task_type == 'bug_fix':
            # BUG修复任务：强制要求专家审查
            next_steps = u"""1. AI将重新分析问题根本原因
2. 制定新的修复方案
3. **【必须】立即使用Task工具启动专家审查**
4. 等待审查结果并根据建议调整方案
5. 然后向用户确认调整后的方案

⚠️ **强制要求**: 回退后必须重新审查，防止重复相同错误"""
        else:
            # 其他任务：可选专家审查
            next_steps = u"""1. AI将重新分析问题根本原因
2. 制定新的修复方案
3. 启动专家审查（如需要）
4. 等待你确认新方案"""

        # v26.0关键改进：明确告知用户如何撤销Implementation阶段的代码修改
        message = u"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 检测到方案性错误 → 回到 Planning
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**你的反馈**: {}

**当前状态**:
- 已回退到Planning阶段
- ⚠️ Planning阶段禁止修改代码（保持架构规则一致性）
- Implementation阶段的代码修改保持不变

**如何撤销刚才的代码修改**:
1. 方案1（推荐）: 使用git命令撤销
   • 查看修改状态: `git status`
   • 撤销工作区修改: `git checkout .`
   • 撤销暂存区修改: `git reset HEAD .`

2. 方案2: 手动恢复文件（如果未使用git）
   • 根据你的记忆或备份恢复文件

3. 方案3: 重新进入Implementation阶段后再修复
   • 继续Planning流程，确认新方案后进入Implementation
   • 在Implementation阶段再修复或重写代码

**AI的下一步**:
{}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(user_input[:100], next_steps)

        # 生成仪表盘
        updated_meta = self.meta_manager.load_task_meta(task_id)
        try:
            from utils.dashboard_generator import generate_context_dashboard
            dashboard = generate_context_dashboard(updated_meta)
            full_message = dashboard + u"\n\n" + message
        except Exception as e:
            sys.stderr.write(u"[WARN] 仪表盘生成失败: {}\n".format(e))
            full_message = message

        return {
            'continue': True,
            'systemMessage': full_message
        }

    def _handle_partial_success(
        self, task_id, meta_data, user_input
    ):
        """
        部分成功处理

        Args:
            task_id: 任务ID
            meta_data: 任务元数据
            user_input: 用户输入

        Returns:
            dict: 处理结果
        """
        # 记录部分成功反馈
        implementation_step = meta_data.get('steps', {}).get('implementation', {})
        if 'test_feedback_history' not in implementation_step:
            implementation_step['test_feedback_history'] = []

        feedback_history = implementation_step['test_feedback_history']
        code_changes = meta_data.get('metrics', {}).get('code_changes', [])

        feedback_entry = {
            'timestamp': datetime.now().isoformat(),
            'user_feedback': user_input,
            'feedback_type': 'partial_success',
            'code_changes_count': len(code_changes)
        }
        feedback_history.append(feedback_entry)

        # 检测循环：partial_success ≥3次 → 回到Planning
        partial_count = sum(1 for f in feedback_history
                           if f.get('feedback_type') in ['partial_success', 'explicit_failure'])

        # 保存元数据
        def update_fn(meta):
            meta['steps']['implementation']['test_feedback_history'] = feedback_history
            return meta

        self.meta_manager.atomic_update(task_id, update_fn)

        if partial_count >= 3:
            # 循环检测，回到Planning
            return self._transition_implementation_to_planning(
                task_id, meta_data, user_input
            )
        else:
            # 部分成功，继续Implementation (v25.4激进模式友好提示)
            message = u"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 检测到部分成功 (第{}轮反馈)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**你的反馈**: {}

**系统推断**:
- ✅ 部分问题已修复
- ❌ 仍有问题需要解决

**当前阶段**: Implementation (实施)
**下一步**: AI将根据你的描述推断问题并继续调整代码

💡 提示:
- 如果方向错误，请明确告知： D. "方案错了" / "思路不对" / "方向错了"
- 如果只是实现细节问题，我将继续在当前方案下修改
- 随时可以打断我重新规划
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(partial_count, user_input[:80])

            # 生成仪表盘
            updated_meta = self.meta_manager.load_task_meta(task_id)
            try:
                from utils.dashboard_generator import generate_context_dashboard
                dashboard = generate_context_dashboard(updated_meta)
                full_message = dashboard + u"\n\n" + message
            except Exception as e:
                sys.stderr.write(u"[WARN] 仪表盘生成失败: {}\n".format(e))
                full_message = message

            return {
                'continue': True,
                'systemMessage': full_message
            }

    def _handle_observation_only(
        self, task_id, meta_data, user_input
    ):
        """
        处理纯描述反馈 (v25.3优化)

        当用户仅描述测试结果或现象，但未明确表态"成功"或"失败"时触发。

        v25.3新增：误判检测，避免明确意图被错误兜底

        处理策略：
        1. 生成任务上下文仪表盘
        2. 显示用户反馈内容
        3. 提示用户明确表态（成功/失败/部分成功）
        4. 阻止状态转移（使用"decision": "block"）

        Args:
            task_id: 任务ID
            meta_data: 任务元数据
            user_input: 用户输入（纯描述性反馈）

        Returns:
            dict: 处理结果（符合UserPromptSubmit Hook规范）
                {
                    "decision": "block",  # 阻止状态转移
                    "reason": str,
                    "systemMessage": str,  # 用户和Claude可见
                    "hookSpecificOutput": {
                        "hookEventName": "UserPromptSubmit",
                        "additionalContext": str  # 仅Claude可见
                    }
                }
        """
        sys.stderr.write(u"[INFO] 检测到observation_only，引导用户明确表态\n")

        # 🔥 v25.3新增：误判检测，避免明确意图被错误兜底
        # 如果用户输入包含强关键词，可能是关键词匹配失败导致的误判
        strong_keywords = [
            u'修复成功', u'部分成功', u'修复失败', u'方案错误',  # 🔥 v25.3新增：选项标签
            u'方案', u'错', u'思路', u'修复', u'成功', u'失败', u'问题', u'BUG'
        ]
        has_strong_keyword = any(kw in user_input.lower() for kw in strong_keywords)

        # 1. 生成任务上下文仪表盘
        try:
            from utils.dashboard_generator import generate_context_dashboard
            dashboard = generate_context_dashboard(meta_data)
        except Exception as e:
            sys.stderr.write(u"[WARN] 仪表盘生成失败: {}\n".format(e))
            dashboard = u"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n📊 任务上下文信息暂时不可用\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

        # 2. 生成用户提示消息（v25.3优化：区分真实observation_only和疑似误判）
        if has_strong_keyword:
            # 疑似误判：用户输入包含明确关键词
            sys.stderr.write(u"[WARN] observation_only误判风险：用户输入包含强关键词\n")
            sys.stderr.write(u"[WARN] 用户输入: {}\n".format(user_input[:200]))
            sys.stderr.write(u"[WARN] 建议检查关键词列表或LLM Prompt是否完整\n")

            prompt_message = u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ℹ️ 系统暂时无法理解您的反馈
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**您的反馈**: {}

**系统检测**: 您的反馈包含明确的关键词，但系统未能正确识别意图。

**可能原因**:
- 表达方式与预设关键词有细微差异
- 系统正在改进语义理解能力

**请尝试以下方式重新表达**（任选其一）:
  A. ✅ 修复成功 → 直接输入："A" 或 "修复了" 或 "修复成功" 或 "都正确了"
  B. ⚠️ 部分成功 → 直接输入："B" 或 "基本正确，但还有XX问题" 或 "部分成功"
  C. ❌ 修复失败 → 直接输入："C" 或 "没修复" 或 "修复失败"
  D. 🔄 方案错误 → 直接输入："D" 或 "方案错了" 或 "方案错误" 或 "思路不对"

💡 **快捷方式**: 直接输入选项字母（A/B/C/D）最可靠
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(user_input[:200] if len(user_input) > 200 else user_input)

        else:
            # 真正的纯描述（如"羊毛给了但没删除"）
            prompt_message = u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ℹ️ 检测到测试结果描述（未明确表态）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**你的反馈**:
{}

**系统判断**: 你描述了测试结果或观察到的现象，但没有明确表态修复是"成功"还是"失败"。

**请明确告知**:
  A. ✅ 修复成功 → "修复了"、"都正确了"、"搞定了"
  B. ⚠️ 部分成功 → "基本正确，但还有XX问题"
  C. ❌ 修复失败 → "没修复"、"还是有问题"
  D. 🔄 方案错误 → "需要调整"、"方案有问题"、"思路不对"

💡 提示: 明确的反馈能帮助AI更准确地判断下一步行动。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(user_input[:200] if len(user_input) > 200 else user_input)

        # 3. 生成Claude专用上下文（additionalContext）
        claude_context = u"""
【系统上下文 - 仅Claude可见】

用户意图分析结果: observation_only
- 用户描述了测试结果或现象
- 未明确表态"成功"或"失败"
- 需要引导用户明确反馈

当前阶段: {}
任务ID: {}

**你的任务**:
1. 理解用户描述的测试结果
2. 等待用户明确表态（成功/失败/部分成功）
3. 不要主动进行状态转移或代码修改
4. 可以友好地询问用户对修复结果的评价
""".format(
            meta_data.get('current_step', 'implementation'),
            task_id
        )

        # 4. 返回符合规范的结果（符合仪表盘功能实现指南 + HOOK正确用法文档）
        return {
            "decision": "block",  # ✅ 阻止UserPromptSubmit处理
            "reason": u"用户未明确表态成功或失败，需要引导明确反馈",
            "systemMessage": dashboard + u"\n\n" + prompt_message,  # ✅ 用户和Claude都可见
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": claude_context  # ✅ 仅Claude可见
            }
        }

    def _handle_implementation_failure(
        self, task_id, meta_data, user_input
    ):
        """
        Implementation阶段失败处理

        Args:
            task_id: 任务ID
            meta_data: 任务元数据
            user_input: 用户输入

        Returns:
            dict: 处理结果
        """
        # 完全失败，回到Planning
        return self._transition_implementation_to_planning(
            task_id, meta_data, user_input
        )

    # ==================== 消息生成 ====================

    def _format_transition_message(self, from_step, to_step):
        """
        生成状态转移消息

        Args:
            from_step: 源状态
            to_step: 目标状态

        Returns:
            str: 转移消息（Markdown格式）
        """
        transition_map = {
            ('planning', 'implementation'): u"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 状态转移: Planning → Implementation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

你已确认方案，工作流进入代码实施阶段。

**当前阶段**: Implementation (实施)
**允许操作**: Write, Edit, NotebookEdit 等代码修改工具

AI将开始实施代码修改。每轮修改完成后，请测试并反馈结果。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""",
            ('implementation', 'finalization'): u"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 状态转移: Implementation → Finalization
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

你确认修复成功，工作流进入收尾归档阶段。

**当前阶段**: Finalization (收尾)
**自动操作**:
- 清理临时文件
- 生成任务摘要
- 归档到 tasks/{task_id}/

AI将自动完成任务归档。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        }

        return transition_map.get((from_step, to_step), u"状态转移: {} → {}".format(from_step, to_step))

    def _format_doc_count_block_message(self, docs_read, required_docs):
        """
        生成文档数量不足阻止消息

        Args:
            docs_read: 已读文档数
            required_docs: 要求文档数

        Returns:
            str: 阻止消息（Markdown格式）
        """
        remaining = required_docs - docs_read
        return u"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 无法进入Implementation阶段
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

当前文档查阅: {docs_read}/{required_docs}

❌ 问题: Planning阶段要求至少查阅{required_docs}个相关文档

✅ 解决方案:
1. 继续使用Read工具查阅{remaining}个文档
2. 重点查阅:
   - CRITICAL规范（markdown/core/开发规范.md）
   - 相关系统实现文档
   - 问题排查指南

完成文档查阅后，再次输入"同意"即可推进。

💡 提示: 充分的文档研究能避免违反CRITICAL规范，提高修复成功率。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(docs_read=docs_read, required_docs=required_docs, remaining=remaining)

    def _format_expert_review_block_message(self):
        """
        生成专家审查未完成阻止消息

        Returns:
            str: 阻止消息（Markdown格式）
        """
        return u"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 无法进入Implementation阶段
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

当前任务类型: BUG修复
专家审查状态: 未完成

❌ 问题: BUG修复任务必须先完成专家审查才能进入Implementation阶段

✅ 解决方案:
1. 使用 Task 工具启动专家审查子代理：
   - subagent_type: "general-purpose"
   - description: "BUG修复方案审查"
   - prompt: 详细描述你的方案

2. 等待子代理完成审查并返回结果

3. 根据审查结果调整方案（如需要）

4. 重新输入"同意"推进到Implementation阶段

💡 提示: 专家审查能有效避免循环修复，提高一次性修复成功率。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    def _format_first_rejection_message(self, user_input):
        """
        生成第1次拒绝消息

        Args:
            user_input: 用户输入

        Returns:
            str: 拒绝消息（Markdown格式）
        """
        return u"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 检测到用户疑虑（第1次）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**用户反馈**: {user_feedback}

**系统判断**: 你没有明确输入"同意"，我理解为你对当前方案有疑虑。

✅ **建议**:
1. 根据用户反馈重新分析问题
2. 调整方案或收集更多信息
3. 制定新方案后再次向用户确认

💡 如果方案经过调整，建议启动新一轮专家审查验证。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(user_feedback=user_input[:100])

    def _format_multiple_rejection_message(
        self, user_input, rejection_count, meta_data
    ):
        """
        生成多次拒绝消息（≥2次）

        Args:
            user_input: 用户输入
            rejection_count: 拒绝次数
            meta_data: 任务元数据

        Returns:
            str: 拒绝消息（Markdown格式）
        """
        task_type = meta_data.get('task_type', 'general')
        planning_step = meta_data.get('steps', {}).get('planning', {})
        expert_review_required = planning_step.get('expert_review_required', False)

        if task_type == 'bug_fix' and expert_review_required:
            current_review_count = planning_step.get('expert_review_count', 1)
            next_review_count = current_review_count + 1
            old_result = planning_step.get('expert_review_result', '需要调整')

            return u"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚨 多次拒绝检测（第{rejection_count}次）- 强制重新审查
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**用户反馈**: {user_feedback}

**系统判断**: 你已{rejection_count}次未同意方案，说明方案可能存在根本性问题。

🔄 **系统已重置专家审查状态**:
- expert_review_completed: true → false
- expert_review_result: "{old_result}" → null
- 审查计数: {current_count} → 即将第{next_count}次

⚡ **下一步操作（强制）**:

1. 🔍 **彻底重新分析问题**
2. 🔧 **制定调整后的新方案**
3. 🚀 **【必须】使用Task工具启动第{next_count}次专家审查**
4. ✅ **等待审查结果，再次向用户确认**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(
                rejection_count=rejection_count,
                user_feedback=user_input[:100],
                old_result=old_result,
                current_count=current_review_count,
                next_count=next_review_count
            )
        else:
            return u"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔴 严重循环警告（第{rejection_count}次拒绝）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**用户反馈**: {user_feedback}

**系统警告**: 已连续{rejection_count}次未同意方案，极可能存在理解偏差！

⚠️ **建议操作**:
1. 仔细阅读用户的所有反馈历史
2. 确认是否理解了用户的真实需求
3. **如果仍不确定，直接询问用户期望的修复方向**
4. 完全重新制定方案

💡 **重要**: 如果用户反馈模糊，请主动提问澄清！

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(
                rejection_count=rejection_count,
                user_feedback=user_input[:100]
            )

    def _generate_llm_failure_prompt(self, stage):
        """
        生成LLM分析失败提示

        Args:
            stage: 阶段名称（planning/implementation）

        Returns:
            dict: 提示结果
        """
        if stage == 'planning':
            message = u"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  Planning阶段语义分析不可用
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

原因: API超时/网络错误/低置信度

请明确您的意图，选择以下之一:

  1. 同意当前方案，推进到Implementation阶段
     → 输入: "同意" 或 "确认" 或 "可以" 或 "继续"

  2. 对方案有疑虑，需要调整
     → 输入: "不同意" 或 "需要调整" 或 "有问题"

  3. 完全否定方案，重新开始
     → 输入: "重来" 或 "重新开始"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            message = u"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  Implementation阶段语义分析不可用
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

原因: API超时/网络错误/低置信度

请明确您的意图，选择以下之一:

  1. 任务完全成功
     → 输入: "完全成功" 或 "都正确了" 或 "修复了"

  2. 部分成功，需继续修复
     → 输入: "部分成功" 或 "还有问题" 或 "基本正确,但..."

  3. 修复失败
     → 输入: "修复失败" 或 "没修复"

  4. 需要重新设计方案
     → 输入: "重新设计" 或 "换个思路" 或 "根本原因没找到"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

        return {
            'continue': False,
            'systemMessage': message
        }

    # ==================== 辅助方法 ====================

    def _get_task_meta_manager(self):
        """获取TaskMetaManager实例"""
        try:
            from core.task_meta_manager import TaskMetaManager
            return TaskMetaManager(self.cwd)
        except ImportError:
            sys.stderr.write(u"[ERROR] TaskMetaManager不可用\n")
            return None

    def _get_intent_analyzer(self):
        """获取LLMIntentAnalyzer实例（v29.3：新增可用性验证）"""
        try:
            from orchestrator.llm_intent_analyzer import LLMIntentAnalyzer
            analyzer = LLMIntentAnalyzer(self.cwd)

            # 🔥 v29.3新增：验证analyzer是否真正可用
            if analyzer.analyzer is None:
                sys.stderr.write(u"[ERROR] LLMIntentAnalyzer.analyzer不可用（ClaudeSemanticAnalyzer初始化失败）\n")
                sys.stderr.write(u"[INFO] 可能原因：\n")
                sys.stderr.write(u"  1. ANTHROPIC_API_KEY环境变量未设置\n")
                sys.stderr.write(u"  2. claude_semantic_config.json配置错误\n")
                sys.stderr.write(u"  3. ClaudeSemanticAnalyzer模块导入失败\n")
                return None

            return analyzer
        except ImportError:
            sys.stderr.write(u"[ERROR] LLMIntentAnalyzer不可用\n")
            return None

    def _get_state_machine(self):
        """获取StateMachineCoordinator实例"""
        try:
            from core.state_machine_coordinator import StateMachineCoordinator
            return StateMachineCoordinator(self.cwd)
        except ImportError:
            sys.stderr.write(u"[ERROR] StateMachineCoordinator不可用\n")
            return None


# ==================== 导出符号 ====================

__all__ = [
    'StateTransitionCoordinator'
]
