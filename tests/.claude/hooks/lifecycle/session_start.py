#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Session Start Hook - 会话启动钩子 (v3.0 Final)

职责:
1. 加载活跃任务的 task-meta.json
2. 更新会话启动时间
3. 显示状态仪表盘（v3.0 Final新增）

核心变更:
v2.0:
- 删除 workflow-state.json 重建逻辑
- 仅更新 session_started_at 时间戳
- 大幅简化代码(从300行 → 70行)

v3.0 Final (Phase 3):
- 增加状态仪表盘输出
- 显示任务进度、当前阶段、轮次信息
"""

import sys
import json
import os
from datetime import datetime
import io

# 🔥 v25.0新增: Windows编码完整容错策略（修复仪表盘中文显示问题）
if sys.platform == 'win32':
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='replace')
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 导入 TaskMetaManager
HOOK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HOOK_DIR)

try:
    from core.task_meta_manager import TaskMetaManager
except ImportError:
    sys.stderr.write("[WARN] TaskMetaManager 模块缺失\n")
    TaskMetaManager = None


def generate_status_dashboard(task_id, task_meta):
    """生成状态仪表盘 (v3.0 Final新增)

    Args:
        task_id: 任务ID
        task_meta: 任务元数据

    Returns:
        str: 格式化的仪表盘输出
    """
    current_step = task_meta.get('current_step', 'unknown')
    task_type = task_meta.get('task_type', 'general')
    task_description = task_meta.get('task_description', '')

    # 语义化4步状态机
    STEPS = ['activation', 'planning', 'implementation', 'finalization']
    STEP_NAMES = {
        'activation': '激活',
        'planning': '方案',
        'implementation': '实施',
        'finalization': '收尾'
    }

    # 计算当前步骤索引
    try:
        current_idx = STEPS.index(current_step)
    except ValueError:
        # 未知步骤，默认显示为planning
        current_idx = 1
        current_step = 'planning'

    # 生成进度图标
    progress_icons = []
    for i, step in enumerate(STEPS):
        if i < current_idx:
            progress_icons.append('✅')
        elif i == current_idx:
            progress_icons.append('🔄')
        else:
            progress_icons.append('⏳')

    # 生成进度条
    progress_bar = ' → '.join([
        f"{icon} {STEP_NAMES[step]}"
        for icon, step in zip(progress_icons, STEPS)
    ])

    # 任务类型显示
    task_type_display = {
        'bug_fix': '🐛 BUG修复',
        'feature_implementation': '⭐ 功能设计',
        'general': '📝 通用任务'
    }.get(task_type, '📝 通用任务')

    # 额外信息（Implementation阶段显示轮次）
    extra_info = ""
    if current_step == 'implementation':
        # 从bug_fix_tracking或feature_tracking获取轮次信息
        bug_fix = task_meta.get('bug_fix_tracking', {})
        feature = task_meta.get('feature_tracking', {})

        if bug_fix.get('enabled'):
            current_round = len(bug_fix.get('iterations', [])) + 1
            extra_info = f"\n当前轮次: 第 {current_round} 轮"
        elif feature.get('enabled'):
            current_round = len(feature.get('iterations', [])) + 1
            extra_info = f"\n当前轮次: 第 {current_round} 轮"

    # 构造仪表盘
    dashboard = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 MODSDK工作流状态
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
任务ID: {task_id[:24]}{'...' if len(task_id) > 24 else ''}
任务类型: {task_type_display}
任务描述: {task_description[:40]}{'...' if len(task_description) > 40 else ''}

当前阶段: {current_step} ({STEP_NAMES.get(current_step, current_step)}){extra_info}

进度: {progress_bar}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    return dashboard


def generate_compact_recovery_prompt(task_id, task_meta, current_step):
    """生成压缩恢复提示（v3.1新增）

    Args:
        task_id: 任务ID
        task_meta: 任务元数据
        current_step: 当前步骤

    Returns:
        str: 格式化的恢复提示
    """
    task_type = task_meta.get('task_type', 'general')
    task_description = task_meta.get('task_description', '')

    # 任务类型显示
    task_type_display = {
        'bug_fix': '🐛 BUG修复',
        'feature_implementation': '⭐ 功能设计',
        'general': '📝 通用任务'
    }.get(task_type, '📝 通用任务')

    # 语义化步骤名称
    STEP_NAMES = {
        'activation': '激活',
        'planning': '方案',
        'implementation': '实施',
        'finalization': '收尾'
    }
    step_name = STEP_NAMES.get(current_step, current_step)

    # 获取最近的代码修改
    code_changes = task_meta.get('metrics', {}).get('code_changes', [])
    recent_changes = code_changes[-3:] if len(code_changes) > 3 else code_changes

    changes_summary = ""
    if recent_changes:
        changes_summary = "## 📝 最近修改\n\n"
        for idx, change in enumerate(recent_changes, 1):
            changes_summary += f"{idx}. {change.get('file', 'unknown')} ({change.get('tool', 'unknown')})\n"
        changes_summary += "\n"

    # 获取当前阶段的提示
    stage_prompt = task_meta.get('steps', {}).get(current_step, {}).get('prompt', '')

    # 构造恢复提示
    recovery_prompt = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 压缩恢复：工作流已自动恢复
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**任务ID**: {task_id[:40]}{'...' if len(task_id) > 40 else ''}
**任务类型**: {task_type_display}
**任务描述**: {task_description[:60]}{'...' if len(task_description) > 60 else ''}

**当前阶段**: {step_name} ({current_step})
**已完成轮次**: {len(task_meta.get('bug_fix_tracking', {}).get('iterations', []))}次

{changes_summary}

## 🎯 继续工作

{stage_prompt}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 **提示**: 工作流状态已从任务元数据恢复，可以继续任务。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    return recovery_prompt


def main():
    """主入口（v3.1增强）"""
    try:
        # 读取Hook输入
        data = json.load(sys.stdin)

        source = data.get('source')  # startup/compact/clear/resume
        session_id = data.get('session_id')

        if not session_id:
            sys.stderr.write("[WARN] SessionStart缺少session_id\n")
            sys.exit(0)

        # 获取工作目录
        cwd = os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd())

        if not TaskMetaManager:
            sys.stderr.write("[ERROR] TaskMetaManager 模块不可用\n")
            sys.exit(0)

        mgr = TaskMetaManager(cwd)

        # v3.1核心改动：根据session_id获取绑定任务
        task_binding = mgr.get_active_task_by_session(session_id)

        if not task_binding:
            # 无绑定任务，跳过
            sys.stderr.write(u"[INFO v3.1] SessionStart: 当前会话无绑定任务\n")
            sys.exit(0)

        task_id = task_binding['task_id']
        current_step = task_binding['current_step']

        # 加载任务元数据
        task_meta = mgr.load_task_meta(task_id)
        if not task_meta:
            sys.stderr.write(f"[ERROR] 加载任务元数据失败: {task_id}\n")
            sys.exit(0)

        # ========== v3.1新增：压缩恢复逻辑 ==========
        if source == "compact":
            # 🔥 v27.0修复：直接输出纯文本（根据官网Claude建议）
            recovery_prompt = generate_compact_recovery_prompt(task_id, task_meta, current_step)

            sys.stdout.flush()
            print(recovery_prompt, flush=True)
            sys.exit(0)

        # ========== v23.0新增：Finalization阶段提示（确保100%启动Task子代理） ==========
        if current_step == 'finalization':
            # 【v24.3修复】双重校验：确保 .task-meta.json 也确认状态
            actual_step = task_meta.get('current_step')
            finalization_status = task_meta.get('steps', {}).get('finalization', {}).get('status')

            # 状态一致性校验
            if actual_step != 'finalization' or finalization_status not in ['in_progress', None]:
                # 🔥 v26.1修复：移除 stderr 输出，避免干扰 JSON 解析
                # sys.stderr.write(
                #     u"[WARN v24.3] .task-active.json 与 .task-meta.json 状态不一致\n"
                #     u"  - .task-active.json: current_step={}\n"
                #     u"  - .task-meta.json: current_step={}, finalization.status={}\n"
                #     u"  → 跳过子代理启动，等待状态同步\n".format(
                #         current_step, actual_step, finalization_status
                #     )
                # )
                # 同步状态到 .task-active.json
                if actual_step and actual_step != current_step:
                    active_tasks[session_id]['current_step'] = actual_step
                    mgr.save_active_task({'active_tasks': active_tasks})
                sys.exit(0)

            # 检查是否在子代理上下文中
            is_subagent = mgr.check_subagent_lock(task_id) if task_id else False

            if not is_subagent:
                # 父代理在finalization阶段，但未启动子代理
                # 🔥 v27.0修复：直接输出纯文本（根据官网Claude建议）

                finalization_prompt = u"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ Finalization阶段 - 必须启动收尾子代理
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**当前状态**:
- 任务ID: {task_id}
- 当前阶段: Finalization (收尾归档)
- 子代理状态: 未启动

**下一步必须操作**:
启动Task工具创建收尾子代理，负责文档更新和任务归档。

⚡ **立即执行**:

Task(
  subagent_type="general-purpose",
  description="任务收尾归档",
  prompt='''
请完成以下收尾工作:

1. 读取 .task-meta.json 获取完整任务历史:
   - 分析 state_transitions (所有状态转移)
   - 分析 steps.planning.iterations (所有Planning迭代)
   - 分析 steps.implementation.iterations (所有Implementation迭代)

2. 生成 context.md (任务上下文文档):
   - 任务概述
   - 执行历程(每次迭代的详情)
   - 关键决策点
   - 完整时间线

3. 生成 solution.md (最终解决方案):
   - 问题描述
   - 最终方案
   - 实施细节
   - 测试验证
   - 经验总结

4. 更新 .task-meta.json:
   - 设置 finalization.status = 'completed'
   - 设置 finalization.completed_at
   - 设置 archived = true
   - 设置 session_ended_at

5. 输出结果标记:
<!-- SUBAGENT_RESULT {{"completed": true, "documents_generated": ["context.md", "solution.md"], "meta_updated": true}} -->
'''
)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 **为什么需要子代理**:
- 确保收尾工作的隔离执行和质量控制
- 基于完整历史(state_transitions + iterations)生成归档文档
- 避免父代理直接修改元数据导致的不一致

⚠️ **重要**:
- 你只能使用Task工具（其他工具会被PreToolUse Hook阻止）
- 收尾子代理有完整权限访问所有必需工具
- 5次非Task工具调用后将被强制阻止

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(task_id=task_id[:40] + ('...' if len(task_id) > 40 else ''))

                sys.stdout.flush()
                print(finalization_prompt, flush=True)
                sys.exit(0)

        # ========== 原有逻辑：显示状态仪表盘 ==========

        # 更新会话启动时间
        task_meta['session_started_at'] = datetime.now().isoformat()

        # 保存更新
        # 🔥 v25.0修复：移除 stderr 日志，避免干扰 JSON 输出
        # Claude Code 要求 Hook 输出必须以 { 开头，stderr 会导致解析失败
        if not mgr.save_task_meta(task_id, task_meta):
            # 保存失败时直接退出，避免后续错误
            sys.exit(1)

        # 🔥 v27.0 关键修复：根据官网Claude建议，SessionStart Hook 应该直接输出纯文本
        # 不要输出 JSON！纯文本会直接显示给用户
        dashboard = generate_status_dashboard(task_id, task_meta)

        # 直接输出纯文本仪表盘
        sys.stdout.flush()
        print(dashboard, flush=True)

        sys.exit(0)

    except Exception as e:
        sys.stderr.write(u"[ERROR] SessionStart Hook执行失败: {}\n".format(e))
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
