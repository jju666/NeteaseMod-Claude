#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
cleanup-subagent-stop.py - 收尾子代理停止处理器 (v20.2.17)

触发时机: SubagentStop
职责: 当子代理停止时，清理收尾子代理的锁文件

设计原理:
1. 配合 create-cleanup-lock.py 使用
2. SubagentStop 事件触发时，检查并删除锁文件
3. 确保父代理恢复工具拦截状态

锁文件位置: tasks/{task_id}/.cleanup-subagent.lock

退出码:
- 0: 正常执行
"""

import sys
import json
import os
import io

# 修复Windows GBK编码问题
if sys.platform == 'win32':
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def get_latest_task_dir(project_dir):
    """获取最新的任务目录"""
    tasks_dir = os.path.join(project_dir, 'tasks')
    if not os.path.exists(tasks_dir):
        return None

    task_dirs = [
        d for d in os.listdir(tasks_dir)
        if os.path.isdir(os.path.join(tasks_dir, d)) and
        (d.startswith('任务-') or d.startswith('task-'))
    ]

    if not task_dirs:
        return None

    # 按修改时间排序，返回最新的
    latest = max(task_dirs, key=lambda d: os.path.getmtime(os.path.join(tasks_dir, d)))
    return os.path.join(tasks_dir, latest)


def remove_lock_file(task_dir):
    """删除锁文件"""
    try:
        lock_file = os.path.join(task_dir, '.cleanup-subagent.lock')

        if os.path.exists(lock_file):
            os.remove(lock_file)
            sys.stderr.write(f"✅ [cleanup-subagent-stop] 锁文件已删除: {lock_file}\n")
            return True
        else:
            sys.stderr.write(f"[cleanup-subagent-stop] 锁文件不存在，跳过删除\n")
            return False
    except Exception as e:
        sys.stderr.write(f"⚠️ [cleanup-subagent-stop] 锁文件删除失败: {e}\n")
        return False


def main():
    try:
        # 读取 stdin 输入（SubagentStop 事件可能有输入数据）
        try:
            data = json.load(sys.stdin)
        except:
            data = {}

        project_dir = os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd())

        # 1. 获取当前任务目录
        task_dir = get_latest_task_dir(project_dir)
        if not task_dir:
            sys.stderr.write(f"[cleanup-subagent-stop] 无法找到任务目录\n")
            sys.exit(0)

        task_id = os.path.basename(task_dir)

        # 2. 删除锁文件
        if remove_lock_file(task_dir):
            sys.stderr.write(f"✅ [cleanup-subagent-stop] 收尾子代理锁已清理\n")
            sys.stderr.write(f"   任务ID: {task_id}\n")
            sys.stderr.write(f"   父代理工具拦截已恢复\n")

        # 3. 正常退出（SubagentStop Hook 不阻止操作）
        sys.exit(0)

    except Exception as e:
        sys.stderr.write(f"❌ [cleanup-subagent-stop] Hook执行异常: {e}\n")
        import traceback
        traceback.print_exc(file=sys.stderr)

        # 即使失败也放行，避免阻塞正常操作
        sys.exit(0)


if __name__ == '__main__':
    main()
