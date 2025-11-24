# -*- coding: utf-8 -*-
"""
仪表盘生成器 - 统一的任务状态可视化模块

用途：为各个Hook提供一致的仪表盘显示
版本：v1.0
创建：2025-11-20
"""

def generate_context_dashboard(task_meta):
    """
    生成上下文仪表盘（用于每次用户输入时注入）

    Args:
        task_meta: 任务元数据字典（来自task-meta.json）

    Returns:
        str: 仪表盘字符串（Unicode格式）
    """
    task_id = task_meta.get('task_id', 'unknown')
    current_step = task_meta.get('current_step', 'unknown')
    task_type = task_meta.get('task_type', 'general')

    # 生成进度条
    progress_bar = _generate_progress_bar(task_meta)

    # 获取当前阶段的状态
    step_status = _get_step_status(task_meta, current_step)

    # 获取下一步建议
    next_action = _get_next_action(task_meta, current_step)

    dashboard = u"""
╭─── 任务状态仪表盘 ───────────────────╮
│ 任务ID: {}
│ 当前阶段: {} {}
│ 进度: {}
│
{}
│
│ 💡 下一步: {}
╰─────────────────────────────────────╯
""".format(
        task_id[:40],  # 截断过长ID
        _get_step_emoji(current_step),
        _get_step_name(current_step),
        progress_bar,
        step_status,
        next_action
    )

    return dashboard


def generate_transition_dashboard(from_step, to_step, task_meta):
    """
    生成状态转移确认仪表盘

    Args:
        from_step: 原阶段名称
        to_step: 目标阶段名称
        task_meta: 任务元数据

    Returns:
        str: 状态转移确认信息
    """
    progress_bar = _generate_progress_bar(task_meta)

    # 获取新阶段的权限和建议
    permissions = _get_step_permissions(to_step)
    iteration_count = len(task_meta.get('bug_fix_tracking', {}).get('iterations', []))

    dashboard = u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 状态转移成功: {} → {}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

进度: {}

{}

**当前轮次**: 第 {} 轮
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(
        _get_step_name(from_step),
        _get_step_name(to_step),
        progress_bar,
        permissions,
        iteration_count + 1 if to_step == 'implementation' else 1
    )

    return dashboard


def generate_permission_denial(tool_name, current_step, reason):
    """
    生成工具权限拒绝提示

    Args:
        tool_name: 被阻止的工具名称
        current_step: 当前阶段
        reason: 拒绝原因

    Returns:
        str: 详细的拒绝提示信息
    """
    allowed_tools = _get_allowed_tools(current_step)

    denial_msg = u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⛔ 工具调用被拒绝
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**当前阶段**: {} ({})
**尝试工具**: {}

**为什么阻止**:
{}

**你现在可以使用的工具**:
{}

**下一步**:
{}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(
        _get_step_name(current_step),
        current_step,
        tool_name,
        reason,
        allowed_tools,
        _get_next_step_hint(current_step)
    )

    return denial_msg


def generate_loop_detection_hint(iterations):
    """
    生成循环检测提示

    Args:
        iterations: 迭代历史列表

    Returns:
        str: 循环检测提示信息
    """
    iteration_count = len(iterations)

    # 格式化迭代历史
    history_lines = []
    for i, iteration in enumerate(iterations[-3:], 1):  # 只显示最近3次
        file_path = iteration.get('file_path', 'unknown')
        result = iteration.get('result', 'unknown')
        history_lines.append(u"  • 第{}轮: 修改 {} ({})".format(
            iteration_count - 3 + i,
            file_path.split('/')[-1] if '/' in file_path else file_path,
            result
        ))

    history_text = u"\n".join(history_lines) if history_lines else u"  (无迭代历史)"

    hint = u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 检测到循环修复模式 - 建议启动专家审查
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**检测原因**:
已进行 {} 轮修改，但问题可能仍未解决。
这通常表明根因分析可能不够深入。

**最近迭代历史**:
{}

**建议操作**:
启动专家审查子代理，重新分析问题根因：

```
Task(
  subagent_type="general-purpose",
  description="BUG修复方案审查",
  prompt="请审查当前方案，分析为什么多次修改未解决问题..."
)
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(iteration_count, history_text)

    return hint


# ============ 内部辅助函数 ============

def _generate_progress_bar(task_meta):
    """生成进度条"""
    steps = task_meta.get('steps', {})

    activation_status = steps.get('activation', {}).get('status', 'pending')
    planning_status = steps.get('planning', {}).get('status', 'pending')
    implementation_status = steps.get('implementation', {}).get('status', 'pending')
    finalization_status = steps.get('finalization', {}).get('status', 'pending')

    def status_icon(status):
        if status == 'completed':
            return u'✅'
        elif status == 'in_progress':
            return u'🔄'
        else:
            return u'⏳'

    return u"{} 激活 → {} 方案 → {} 实施 → {} 收尾".format(
        status_icon(activation_status),
        status_icon(planning_status),
        status_icon(implementation_status),
        status_icon(finalization_status)
    )


def _get_step_emoji(step):
    """获取阶段对应的emoji"""
    emoji_map = {
        'activation': u'🚀',
        'planning': u'🔄',
        'implementation': u'⚙️',
        'finalization': u'📦'
    }
    return emoji_map.get(step, u'❓')


def _get_step_name(step):
    """获取阶段的中文名称"""
    name_map = {
        'activation': u'激活',
        'planning': u'Planning (方案制定)',
        'implementation': u'Implementation (代码实施)',
        'finalization': u'Finalization (收尾归档)'
    }
    return name_map.get(step, step)


def _get_step_status(task_meta, current_step):
    """获取当前阶段的状态详情"""
    steps = task_meta.get('steps', {})

    if current_step == 'planning':
        planning = steps.get('planning', {})
        expert_required = planning.get('expert_review_required', False)
        expert_completed = planning.get('expert_review_completed', False)
        expert_count = planning.get('expert_review_count', 0)
        expert_result = planning.get('expert_review_result', None)

        task_type = task_meta.get('task_type', 'general')

        expert_status = u'⏳ 未开始'
        if expert_completed:
            expert_status = u'✅ 已完成({})次 - 结果: {}'.format(expert_count, expert_result)
        elif expert_count > 0:
            expert_status = u'🔄 进行中({})次'.format(expert_count)

        return u"""│ 📋 Planning 阶段:
│   • 任务类型: {}
│   • 专家审查: {}
│   • 用户确认: ❌ 未确认
│
│ 📋 反馈指南（请选择或用自然语言）:
│   A. ✅ 同意方案 → "同意"、"可以开始"、"确认"
│   B. 🔄 需要调整 → "需要调整"、"有些问题"、"建议..."
│   C. 🔄 重新开始 → "重来"、"完全不对"、"重新规划""".format(
            task_type,
            expert_status,  # 🔥 修复：使用计算好的expert_status
        )

    elif current_step == 'implementation':
        implementation = steps.get('implementation', {})
        user_confirmed = implementation.get('user_confirmed', False)
        iteration_count = len(task_meta.get('bug_fix_tracking', {}).get('iterations', []))

        return u"""│ ⚙️ Implementation 阶段:
│   • 当前轮次: 第 {} 轮
│   • 用户确认: {}
│
│ 📋 反馈指南（请选择或用自然语言）:
│   A. ✅ 修复成功 → "修复了"、"都正确了"、"搞定了"
│   B. ⚠️ 部分成功 → "基本正确，但还有XX问题"
│   C. ❌ 修复失败 → "没修复"、"还是有问题"
│   D. 🔄 方案错误 → "需要调整"、"方案有问题"、"思路不对""".format(
            iteration_count + 1,
            u'✅ 已确认' if user_confirmed else u'⏳ 待确认'
        )

    elif current_step == 'finalization':
        return u"""│ 📦 Finalization 阶段:
│   • 清理DEBUG代码
│   • 更新文档
│   • 归档任务"""

    return u"│ (阶段信息不可用)"


def _get_next_action(task_meta, current_step):
    """获取下一步操作建议"""
    task_type = task_meta.get('task_type', 'general')
    steps = task_meta.get('steps', {})

    if current_step == 'planning':
        expert_required = steps.get('planning', {}).get('expert_review_required', False)
        expert_completed = steps.get('planning', {}).get('expert_review_completed', False)

        if expert_required and not expert_completed:
            return u'开始分析问题，启动专家审查子代理'
        else:
            return u'查阅相关文档，制定实施方案'

    elif current_step == 'implementation':
        return u'基于确认的方案，实施代码修改'

    elif current_step == 'finalization':
        return u'启动Task子代理完成文档更新和归档'

    return u'继续执行当前阶段任务'


def _get_step_permissions(step):
    """获取阶段的权限说明"""
    if step == 'planning':
        return u"""**Planning阶段权限**:
- ✅ 允许: Read, Grep, Glob, Task, WebFetch
- ❌ 禁止: Write, Edit, Update (需用户确认后)"""

    elif step == 'implementation':
        return u"""**Implementation阶段权限**:
- ✅ 允许: Write, Edit, Update, Bash, Read, Grep
- ⏳ 建议: 小步迭代，每次修改后等待用户反馈"""

    elif step == 'finalization':
        return u"""**Finalization阶段权限**:
- ✅ 强制: 必须使用Task工具启动子代理
- ❌ 禁止: 直接修改代码（除清理DEBUG外）"""

    return u"(权限信息不可用)"


def _get_allowed_tools(step):
    """获取阶段允许的工具列表"""
    tool_map = {
        'planning': [
            u'1. ✅ Read - 阅读代码和文档',
            u'2. ✅ Grep/Glob - 搜索相关代码',
            u'3. ✅ Task - 启动专家审查子代理',
            u'4. ✅ WebFetch - 查询官方文档'
        ],
        'implementation': [
            u'1. ✅ Write/Edit/Update - 修改代码',
            u'2. ✅ Bash - 执行测试和验证',
            u'3. ✅ Read/Grep - 阅读和搜索代码',
            u'4. ✅ Task - 启动辅助子代理'
        ],
        'finalization': [
            u'1. ✅ Task - 启动文档更新子代理（强制）',
            u'2. ✅ Read - 阅读代码确认清理',
            u'3. ⚠️ Write/Edit - 仅限清理DEBUG代码'
        ]
    }

    tools = tool_map.get(step, [])
    return u'\n'.join(tools) if tools else u'  (无工具限制)'


def _get_next_step_hint(step):
    """获取进入下一阶段的提示"""
    if step == 'planning':
        return u"""制定完整方案后，向用户展示并等待确认。
用户输入"同意"/"认同"/"确认"后，Hook会自动推进到Implementation阶段。"""

    elif step == 'implementation':
        return u"""完成修改并测试通过后，等待用户确认。
用户输入"修复了"/"完成了"后，Hook会推进到Finalization阶段。"""

    elif step == 'finalization':
        return u"""使用Task工具启动子代理完成文档更新和归档。"""

    return u"(继续当前阶段工作)"
