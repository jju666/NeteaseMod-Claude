"""
Expert Trigger - 专家触发器
职责:
1. 检测循环模式（BUG修复循环、需求不匹配循环）
2. 生成专家分析Prompt
3. 返回触发决策
"""

from datetime import datetime
from typing import Dict, Optional


class ExpertTrigger:
    """专家触发器 - 循环检测与专家审查"""

    def should_trigger(self, workflow_state: Dict) -> bool:
        """
        判断是否应该触发专家审查

        Args:
            workflow_state: 工作流状态

        Returns:
            是否触发专家
        """
        # 1. 检查是否已经触发过专家（避免重复触发）
        if workflow_state.get('expert_triggered', False):
            return False

        # 2. 只在step3_execute阶段触发
        current_step = workflow_state.get('current_step', '')
        if current_step != 'step3_execute':
            return False

        # 3. 根据任务类型检测循环
        task_type = workflow_state.get('task_type', 'general')

        if task_type == 'bug_fix':
            return self._detect_bug_fix_loop(workflow_state)
        elif task_type == 'feature_development':
            return self._detect_feature_loop(workflow_state)
        else:
            # 其他任务类型暂不触发专家
            return False

    def _detect_bug_fix_loop(self, workflow_state: Dict) -> bool:
        """
        检测BUG修复循环

        触发条件:
        - 至少2次迭代
        - 至少2次负面反馈
        - 至少2次同文件修改
        """
        bug_tracking = workflow_state.get('bug_fix_tracking', {})
        if not bug_tracking.get('enabled', False):
            return False

        iterations = bug_tracking.get('iterations', [])
        indicators = bug_tracking.get('loop_indicators', {})

        iterations_count = len(iterations)
        negative_count = indicators.get('negative_feedback_count', 0)
        same_file_count = indicators.get('same_file_edit_count', 0)

        # 触发阈值
        return (
            iterations_count >= 2 and
            negative_count >= 2 and
            same_file_count >= 2
        )

    def _detect_feature_loop(self, workflow_state: Dict) -> bool:
        """
        检测功能开发循环

        触发条件:
        - 至少3次迭代
        - 至少2次不满意反馈
        """
        feature_tracking = workflow_state.get('feature_tracking', {})
        if not feature_tracking.get('enabled', False):
            return False

        iterations = feature_tracking.get('iterations', [])
        iterations_count = len(iterations)

        # 统计不满意反馈
        dissatisfied_count = sum(
            1 for iter in iterations
            if iter.get('user_satisfaction') == 'dissatisfied'
        )

        # 触发阈值
        return (
            iterations_count >= 3 and
            dissatisfied_count >= 2
        )

    def generate_prompt(self, workflow_state: Dict) -> str:
        """
        生成专家分析Prompt

        Args:
            workflow_state: 工作流状态

        Returns:
            专家Prompt文本
        """
        task_type = workflow_state.get('task_type', 'general')

        if task_type == 'bug_fix':
            return self._generate_bug_fix_prompt(workflow_state)
        elif task_type == 'feature_development':
            return self._generate_feature_prompt(workflow_state)
        else:
            return ""

    def _generate_bug_fix_prompt(self, workflow_state: Dict) -> str:
        """生成BUG修复专家Prompt"""
        bug_tracking = workflow_state.get('bug_fix_tracking', {})
        iterations = bug_tracking.get('iterations', [])
        indicators = bug_tracking.get('loop_indicators', {})

        # 构建迭代历史摘要
        history_summary = self._build_iteration_history(iterations)

        # 证据数据
        iterations_count = len(iterations)
        negative_count = indicators.get('negative_feedback_count', 0)
        same_file_count = indicators.get('same_file_edit_count', 0)
        failed_test_count = indicators.get('failed_test_count', 0)

        prompt = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 专家审查系统已触发
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 检测到的问题模式

**循环类型**: bug_fix_loop（BUG修复循环）
**置信度**: 90%
**证据**:
- 迭代次数: {iterations_count}
- 负面反馈次数: {negative_count}
- 同文件修改次数: {same_file_count}
- 测试失败次数: {failed_test_count}
- 问题模式: 表象修复循环 - 反复修改同一位置但未解决根本问题

{history_summary}

## 你的任务

你现在需要从**战略高度**分析问题，而非继续尝试修复。

### 分析框架

1. **根因分析**: 为什么反复修改仍失败？
   - 是否陷入表象修复？
   - 是否存在架构层面的缺陷？
   - 是否对问题的理解有误？
   - 是否存在多个相互影响的BUG？

2. **失败模式**: 历史修改中有哪些共同的错误假设？
   - 分析每次迭代的假设和验证结果
   - 找出重复出现的思维误区

3. **备选路径**: 除了当前方向，还有哪3-5种可能的解决思路？
   - **路径A**: [名称] - [优点] - [缺点] - [适用场景] - [预计工作量]
   - **路径B**: [名称] - [优点] - [缺点] - [适用场景] - [预计工作量]
   - **路径C**: [名称] - [优点] - [缺点] - [适用场景] - [预计工作量]
   - ...

4. **推荐策略**: 推荐哪种路径，以及如何验证？
   - 明确推荐理由
   - 给出具体实施步骤
   - 设计验证方法

5. **需要向用户澄清的问题**: 列出关键问题
   - 用于排除假设
   - 获取更多上下文

## 输出格式

使用以下Markdown格式输出：

# 🎯 专家诊断报告

## 1. 问题根因

[深度分析...]

## 2. 失败模式分析

[历史修改的错误假设分析...]

## 3. 备选方案

### 方案A: [名称]
- **优点**: ...
- **缺点**: ...
- **适用场景**: ...
- **预计工作量**: ...

### 方案B: [名称]
...

## 4. 推荐策略

[具体建议，包括实施步骤和验证方法]

## 5. 需要向用户澄清的问题

1. [问题1]
2. [问题2]
...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**请立即开始分析，不要继续尝试修复。**
"""
        return prompt

    def _generate_feature_prompt(self, workflow_state: Dict) -> str:
        """生成功能开发专家Prompt"""
        feature_tracking = workflow_state.get('feature_tracking', {})
        iterations = feature_tracking.get('iterations', [])

        # 构建迭代历史摘要
        history_summary = self._build_iteration_history(iterations)

        # 证据数据
        iterations_count = len(iterations)
        dissatisfied_count = sum(
            1 for iter in iterations
            if iter.get('user_satisfaction') == 'dissatisfied'
        )

        prompt = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 专家审查系统已触发
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 检测到的问题模式

**循环类型**: requirement_mismatch（需求理解偏差）
**置信度**: 85%
**证据**:
- 迭代次数: {iterations_count}
- 不满意反馈次数: {dissatisfied_count}
- 问题模式: 实现方向与用户期望不一致

{history_summary}

## 你的任务

你现在需要重新审视需求理解，而非继续开发。

### 分析框架

1. **需求差距分析**: 用户期望 vs 实际实现的差异在哪里？
   - 功能范围理解是否有偏差？
   - 交互方式是否符合预期？
   - 性能/体验指标是否达标？

2. **沟通模式**: 历史反馈中有哪些关键信息被忽略？
   - 分析用户反馈的真实诉求
   - 找出理解偏差的根源

3. **备选实现方案**: 列出3-5种不同的实现思路
   - **方案A**: [名称] - [优点] - [缺点] - [适用场景]
   - **方案B**: ...

4. **推荐策略**: 如何确保下一步实现符合用户期望？

5. **需要向用户澄清的问题**: 列出关键问题
   - 明确功能范围
   - 确认优先级
   - 获取验收标准

## 输出格式

# 🎯 专家诊断报告

## 1. 需求差距分析

[分析...]

## 2. 备选实现方案

### 方案A: [名称]
...

## 3. 推荐策略

[具体建议]

## 4. 需要向用户澄清的问题

1. [问题1]
2. [问题2]
...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**请立即开始分析，暂停功能开发。**
"""
        return prompt

    def _build_iteration_history(self, iterations: list) -> str:
        """构建迭代历史摘要"""
        if not iterations:
            return "## 迭代历史\n\n（暂无迭代记录）"

        history = "## 迭代历史\n\n"

        for iter in iterations:
            iteration_id = iter.get('iteration_id', 0)
            timestamp = iter.get('timestamp', '')
            user_feedback = iter.get('user_feedback', '无')
            sentiment = iter.get('feedback_sentiment', 'neutral')
            changes_made = iter.get('changes_made', [])
            test_result = iter.get('test_result', 'pending')

            # 格式化时间
            try:
                dt = datetime.fromisoformat(timestamp)
                formatted_time = dt.strftime('%Y-%m-%d %H:%M')
            except:
                formatted_time = timestamp

            # 情感emoji
            sentiment_emoji = {
                'positive': '✅',
                'negative': '❌',
                'frustrated': '😤',
                'neutral': '➖'
            }.get(sentiment, '❓')

            history += f"### 迭代 {iteration_id}\n"
            history += f"- **时间**: {formatted_time}\n"
            history += f"- **用户反馈**: {sentiment_emoji} {user_feedback}\n"
            history += f"- **情感**: {sentiment}\n"
            history += f"- **测试结果**: {test_result}\n"

            if changes_made:
                history += "- **修改文件**:\n"
                for change in changes_made[:3]:  # 最多显示3个
                    file_path = change.get('file', 'unknown')
                    operation = change.get('operation', 'unknown')
                    history += f"  - {file_path} ({operation})\n"
                if len(changes_made) > 3:
                    history += f"  - ... 及其他 {len(changes_made) - 3} 个文件\n"

            history += "\n"

        return history
