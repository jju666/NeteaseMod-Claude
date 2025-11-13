#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SessionEnd Hook - 会话结束归档器 (v20.2.0)

触发时机: Claude Code关闭时
职责:
1. 保存会话最终快照到 tasks/{task_id}/session-{id}.json
2. 更新 .task-meta.json 的session_history
3. 标记会话状态为 interrupted/completed

退出码:
- 0: 成功
"""

import sys
import json
import os
from datetime import datetime
from pathlib import Path
import io

# 修复Windows GBK编码问题
if sys.platform == 'win32':
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 导入统一日志记录器
try:
    from hook_logger import HookLogger
except ImportError:
    class HookLogger:
        def __init__(self, name): self.name = name
        def start(self): pass
        def finish(self, success=True, message=""): pass
        def info(self, msg, data=None): pass
        def error(self, msg, err=None): pass


def load_json(file_path):
    """加载JSON文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return None


def save_json(file_path, data):
    """保存JSON文件"""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        sys.stderr.write(u"[ERROR] 保存JSON失败: {}\n".format(e))
        return False


def finalize_session(cwd, logger):
    """
    结束当前会话，保存快照

    流程:
    1. 读取workflow-state.json
    2. 检查是否关联任务
    3. 保存会话快照到 tasks/{task_id}/session-{id}.json
    4. 更新.task-meta.json的session_history
    """

    workflow_state_path = os.path.join(cwd, '.claude', 'workflow-state.json')
    workflow_state = load_json(workflow_state_path)

    if not workflow_state:
        logger.info(u"workflow-state.json不存在，跳过归档")
        return

    # 检查是否关联任务
    task_id = workflow_state.get("task_id")
    if not task_id:
        logger.info(u"无关联任务，跳过归档")
        return

    task_dir = os.path.join(cwd, 'tasks', task_id)
    if not os.path.exists(task_dir):
        logger.error(u"任务目录不存在: {}".format(task_dir))
        return

    # 生成session_id (如果没有)
    session_id = workflow_state.get("session_id")
    if not session_id:
        session_id = u"session-{}".format(datetime.now().strftime('%Y%m%d-%H%M%S'))

    # 保存最终快照
    snapshot_file = os.path.join(task_dir, u"{}.json".format(session_id))

    snapshot_data = {
        "session_id": session_id,
        "started_at": workflow_state.get("session_start_time", datetime.now().isoformat()),
        "ended_at": datetime.now().isoformat(),
        "final_state": workflow_state,
        "status": "interrupted"  # 默认为中断状态
    }

    save_json(snapshot_file, snapshot_data)
    logger.info(u"已保存会话快照", {"file": snapshot_file})

    # 更新任务元数据
    meta_path = os.path.join(task_dir, '.task-meta.json')
    task_meta = load_json(meta_path)

    if not task_meta:
        logger.error(u"无法加载task-meta.json")
        return

    # 更新session_history
    if "session_history" not in task_meta:
        task_meta["session_history"] = []

    # 查找并更新当前会话
    session_found = False
    for session in task_meta["session_history"]:
        if session["session_id"] == session_id:
            session["ended_at"] = datetime.now().isoformat()
            session["status"] = "interrupted"
            session["snapshot_file"] = u"{}.json".format(session_id)
            session_found = True
            break

    # 如果没找到，添加新会话记录
    if not session_found:
        task_meta["session_history"].append({
            "session_id": session_id,
            "started_at": workflow_state.get("session_start_time", datetime.now().isoformat()),
            "ended_at": datetime.now().isoformat(),
            "status": "interrupted",
            "snapshot_file": u"{}.json".format(session_id)
        })

    # 保存更新
    save_json(meta_path, task_meta)
    logger.info(u"已更新session_history")


def main():
    logger = HookLogger("session-end-hook")
    logger.start()

    try:
        cwd = os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd())

        # 结束会话
        finalize_session(cwd, logger)

        logger.finish(success=True, message=u"会话已归档")
        sys.exit(0)

    except Exception as e:
        logger.error(u"Hook执行失败", e)
        import traceback
        traceback.print_exc(file=sys.stderr)

        logger.finish(success=False, message=u"执行异常")
        sys.exit(0)


if __name__ == '__main__':
    main()
