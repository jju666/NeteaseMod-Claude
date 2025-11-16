#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Session End Hook - 会话结束钩子 (v2.0)

职责:
1. 更新会话结束时间
2. 不删除任何文件(task-meta.json 保留)

核心变更(v2.0):
- 删除 workflow-state.json 清理逻辑
- 仅更新时间戳
- 简化代码(从170行 → 55行)
"""

import sys
import os
import json
from datetime import datetime

HOOK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HOOK_DIR)

try:
    from core.task_meta_manager import TaskMetaManager
except ImportError:
    sys.stderr.write("[WARN] TaskMetaManager 模块缺失\n")
    sys.exit(0)


def main():
    """主入口（v3.1: 支持会话隔离）"""
    # 读取Hook输入
    hook_input = json.load(sys.stdin)
    cwd = hook_input.get('cwd', os.getcwd())
    session_id = hook_input.get('session_id')

    if not session_id:
        # v3.1纯粹架构：要求session_id
        sys.stderr.write("[ERROR] SessionEnd缺少session_id，v3.1架构要求session_id\n")
        sys.exit(0)

    mgr = TaskMetaManager(cwd)
    binding = mgr.get_active_task_by_session(session_id)
    if not binding:
        sys.stderr.write("[INFO v2.0] 当前会话无绑定任务,跳过会话结束处理\n")
        sys.exit(0)

    task_id = binding['task_id']

    # 原子更新会话结束时间
    def update_func(task_meta):
        task_meta['session_ended_at'] = datetime.now().isoformat()
        return task_meta

    updated = mgr.atomic_update(task_id, update_func)

    if updated:
        sys.stderr.write(f"[INFO v2.0] 会话已结束: {task_id}\n")
    else:
        sys.stderr.write(f"[ERROR] 更新任务元数据失败: {task_id}\n")

    sys.exit(0)


if __name__ == "__main__":
    main()
