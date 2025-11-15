#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Session Start Hook - 会话启动钩子 (v21.0)

职责:
1. 加载活跃任务的 task-meta.json
2. 更新会话启动时间
3. 简化恢复逻辑(无需重建 workflow-state.json)

核心变更(v21.0):
- 删除 workflow-state.json 重建逻辑
- 仅更新 session_started_at 时间戳
- 大幅简化代码(从300行 → 70行)
"""

import sys
import json
import os
from datetime import datetime

# 导入 TaskMetaManager
HOOK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HOOK_DIR)

try:
    from core.task_meta_manager import TaskMetaManager
except ImportError:
    sys.stderr.write("[WARN] TaskMetaManager 模块缺失\n")
    TaskMetaManager = None


def main():
    """主入口"""
    cwd = os.getcwd()

    if not TaskMetaManager:
        sys.stderr.write("[ERROR] TaskMetaManager 模块不可用,跳过会话恢复\n")
        sys.exit(0)

    mgr = TaskMetaManager(cwd)

    # 获取活跃任务
    task_id = mgr.get_active_task_id()
    if not task_id:
        sys.stderr.write("[INFO v21.0] 无活跃任务,跳过会话恢复\n")
        sys.exit(0)

    # 加载任务元数据
    task_meta = mgr.load_task_meta(task_id)
    if not task_meta:
        sys.stderr.write(f"[ERROR] 加载任务元数据失败: {task_id}\n")
        sys.exit(0)

    # 更新会话启动时间
    task_meta['session_started_at'] = datetime.now().isoformat()

    # 保存更新
    if mgr.save_task_meta(task_id, task_meta):
        sys.stderr.write(f"[INFO v21.0] 会话已恢复: {task_id}\n")
        sys.stderr.write(f"[INFO v21.0] 当前步骤: {task_meta.get('current_step', 'unknown')}\n")
    else:
        sys.stderr.write(f"[ERROR] 保存任务元数据失败: {task_id}\n")

    sys.exit(0)


if __name__ == "__main__":
    main()
