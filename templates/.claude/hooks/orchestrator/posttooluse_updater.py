#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified PostToolUse Updater - 统一PostToolUse更新器
Version: v21.0

职责:
1. 纯粹的状态更新器(零决策逻辑)
2. 记录工具执行结果到 task-meta.json
3. 检测步骤完成条件,自动推进工作流
4. 检测循环模式,触发专家审查
5. 使用文件锁避免并发冲突

核心变更(v21.0):
- 删除 workflow-state.json 所有逻辑
- 直接更新 task-meta.json(唯一数据源)
- 使用 TaskMetaManager 的原子更新 API
"""

import sys
import json
import os
from datetime import datetime
from typing import Dict, Optional, Tuple

# 添加core模块到sys.path
HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_HOOK_DIR = os.path.dirname(HOOK_DIR)
sys.path.insert(0, PARENT_HOOK_DIR)

try:
    from core.task_meta_manager import TaskMetaManager
except ImportError as e:
    sys.stderr.write(f"[ERROR] 无法导入 TaskMetaManager: {e}\n")
    # 兜底:静默退出
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": ""
        },
        "suppressOutput": True
    }, ensure_ascii=False))
    sys.exit(0)


def silent_exit():
    """静默退出(不输出任何内容)"""
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": ""
        },
        "suppressOutput": True
    }
    print(json.dumps(output, ensure_ascii=False))
    sys.exit(0)


def update_metrics(task_meta: Dict, tool_name: str, tool_input: Dict, is_error: bool):
    """
    更新任务度量指标

    Args:
        task_meta: 任务元数据
        tool_name: 工具名称
        tool_input: 工具输入参数
        is_error: 是否发生错误
    """
    # 初始化 metrics 字段
    if 'metrics' not in task_meta:
        task_meta['metrics'] = {
            'tools_used': [],
            'code_changes': [],
            'docs_read': [],
            'failed_operations': []
        }

    metrics = task_meta['metrics']

    # 记录工具使用
    metrics['tools_used'].append({
        'tool': tool_name,
        'timestamp': datetime.now().isoformat(),
        'success': not is_error
    })

    # 记录代码修改
    if tool_name in ['Edit', 'Write']:
        file_path = tool_input.get('file_path', '')
        if file_path:
            metrics['code_changes'].append({
                'file': file_path,
                'tool': tool_name,
                'timestamp': datetime.now().isoformat(),
                'success': not is_error
            })

    # 记录文档阅读
    if tool_name == 'Read':
        file_path = tool_input.get('file_path', '')
        if file_path and ('markdown' in file_path or '.md' in file_path):
            metrics['docs_read'].append({
                'file': file_path,
                'timestamp': datetime.now().isoformat()
            })

    # 记录失败操作
    if is_error:
        metrics['failed_operations'].append({
            'tool': tool_name,
            'input': tool_input,
            'timestamp': datetime.now().isoformat()
        })


def detect_loop_indicators(task_meta: Dict) -> bool:
    """
    检测循环指标(用于BUG修复任务)

    Returns:
        bool: 是否触发循环警告
    """
    bug_fix_tracking = task_meta.get('bug_fix_tracking', {})
    if not bug_fix_tracking.get('enabled'):
        return False

    loop_indicators = bug_fix_tracking.get('loop_indicators', {})

    # 检测循环阈值
    same_file_count = loop_indicators.get('same_file_edit_count', 0)
    failed_test_count = loop_indicators.get('failed_test_count', 0)
    negative_feedback = loop_indicators.get('negative_feedback_count', 0)

    # 触发条件:同文件修改3次 或 测试失败2次 或 负面反馈2次
    if same_file_count >= 3 or failed_test_count >= 2 or negative_feedback >= 2:
        return True

    return False


def update_bug_fix_tracking(task_meta: Dict, tool_name: str, tool_input: Dict, is_error: bool):
    """
    更新BUG修复追踪状态

    Args:
        task_meta: 任务元数据
        tool_name: 工具名称
        tool_input: 工具输入参数
        is_error: 是否发生错误
    """
    bug_fix_tracking = task_meta.get('bug_fix_tracking', {})
    if not bug_fix_tracking.get('enabled'):
        return

    loop_indicators = bug_fix_tracking.setdefault('loop_indicators', {
        'same_file_edit_count': 0,
        'failed_test_count': 0,
        'negative_feedback_count': 0
    })

    # 更新同文件修改计数
    if tool_name in ['Edit', 'Write']:
        file_path = tool_input.get('file_path', '')
        metrics = task_meta.get('metrics', {})
        code_changes = metrics.get('code_changes', [])

        # 计算同一文件的修改次数
        same_file_count = sum(1 for change in code_changes if change.get('file') == file_path)
        loop_indicators['same_file_edit_count'] = max(loop_indicators['same_file_edit_count'], same_file_count)

    # 更新测试失败计数
    if tool_name == 'Bash' and is_error:
        bash_cmd = tool_input.get('command', '')
        if 'test' in bash_cmd.lower() or 'pytest' in bash_cmd.lower():
            loop_indicators['failed_test_count'] += 1


def main():
    """主入口"""
    # 1. 解析输入
    try:
        event_data = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        sys.stderr.write(f"[ERROR] JSON解析失败: {e}\n")
        silent_exit()
        return

    tool_name = event_data.get("toolName", "")
    tool_input = event_data.get("toolInput", {})
    tool_result = event_data.get("toolResult", "")
    is_error = event_data.get("isError", False)

    # 2. 获取工作目录
    cwd = os.getcwd()

    # 3. 初始化 TaskMetaManager
    mgr = TaskMetaManager(cwd)

    # 4. 获取活跃任务ID
    task_id = mgr.get_active_task_id()
    if not task_id:
        silent_exit()
        return

    # 5. 原子更新任务元数据
    def update_func(task_meta: Dict) -> Dict:
        """更新函数(在锁内执行)"""
        # 更新度量指标
        update_metrics(task_meta, tool_name, tool_input, is_error)

        # 更新BUG修复追踪
        update_bug_fix_tracking(task_meta, tool_name, tool_input, is_error)

        # 检测循环并标记
        if detect_loop_indicators(task_meta):
            bug_fix_tracking = task_meta.get('bug_fix_tracking', {})
            if not bug_fix_tracking.get('expert_triggered'):
                bug_fix_tracking['expert_triggered'] = True
                sys.stderr.write("[PostToolUse] 检测到循环模式,标记专家触发\n")

        return task_meta

    updated_meta = mgr.atomic_update(task_id, update_func)

    if not updated_meta:
        sys.stderr.write("[ERROR] 原子更新失败\n")
        silent_exit()
        return

    # 6. 静默退出
    silent_exit()


if __name__ == "__main__":
    main()
