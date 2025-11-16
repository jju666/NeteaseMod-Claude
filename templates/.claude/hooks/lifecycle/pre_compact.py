#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PreCompact Hook - 压缩前保存任务状态 (v3.1)

职责:
1. 检测当前会话是否有绑定任务
2. 保存任务状态到 .task-meta.json
3. 提示用户压缩后将自动恢复

触发时机: 用户执行 /compact 之前
"""

import sys
import json
import os
from datetime import datetime

# 添加core模块到sys.path
HOOK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HOOK_DIR)

try:
    from core.task_meta_manager import TaskMetaManager
except ImportError:
    sys.stderr.write("[ERROR] TaskMetaManager 模块缺失\n")
    TaskMetaManager = None


def main():
    """主入口"""
    try:
        # 读取Hook输入
        data = json.load(sys.stdin)

        session_id = data.get('session_id')
        trigger = data.get('trigger')  # manual或auto

        if not session_id:
            sys.stderr.write("[WARN] PreCompact缺少session_id\n")
            sys.exit(0)

        # 获取工作目录
        cwd = os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd())

        if not TaskMetaManager:
            sys.stderr.write("[ERROR] TaskMetaManager不可用，跳过压缩前保存\n")
            sys.exit(0)

        mgr = TaskMetaManager(cwd)

        # 检查当前会话是否有绑定任务
        task_binding = mgr.get_active_task_by_session(session_id)

        if not task_binding:
            # 无绑定任务，跳过
            sys.stderr.write(u"[INFO] PreCompact: 当前会话无绑定任务，跳过\n")
            sys.exit(0)

        task_id = task_binding['task_id']
        current_step = task_binding['current_step']

        # 加载任务元数据
        task_meta = mgr.load_task_meta(task_id)
        if not task_meta:
            sys.stderr.write(u"[WARN] PreCompact: 加载任务元数据失败\n")
            sys.exit(0)

        # 记录压缩时间
        task_meta['last_compact_at'] = datetime.now().isoformat()

        # 保存更新后的元数据
        if mgr.save_task_meta(task_id, task_meta):
            sys.stderr.write(u"[INFO v3.1] PreCompact: 任务状态已保存\n")
            sys.stderr.write(u"  任务ID: {}\n".format(task_id[:40]))
            sys.stderr.write(u"  当前阶段: {}\n".format(current_step))
            sys.stderr.write(u"  压缩后将自动恢复工作流\n")
        else:
            sys.stderr.write(u"[ERROR] PreCompact: 保存任务元数据失败\n")

        # 成功退出
        sys.exit(0)

    except Exception as e:
        sys.stderr.write(u"[ERROR] PreCompact Hook执行失败: {}\n".format(e))
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
