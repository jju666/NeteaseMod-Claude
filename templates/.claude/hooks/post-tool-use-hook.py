#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PostToolUse Hook - 代码修改追踪器 (v20.2.0)

触发时机: AI调用Edit/Write工具后
职责:
1. 提取代码修改信息 (文件路径、修改类型、修改摘要)
2. 记录到当前迭代的changes_made数组
3. 更新循环指标 (same_file_edit_count)
4. 同步到 .task-meta.json

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


# ==================== 修改信息提取器 ====================

def extract_code_changes(tool_name: str, tool_input: dict) -> dict:
    """从Edit/Write工具提取修改信息"""

    if tool_name == "Edit":
        file_path = tool_input.get("file_path", "")
        old_string = tool_input.get("old_string", "")
        new_string = tool_input.get("new_string", "")

        return {
            "file": file_path,
            "change_type": "edit",
            "change_summary": u"修改了 {} 字符".format(len(old_string)),
            "old_length": len(old_string),
            "new_length": len(new_string)
        }

    elif tool_name == "Write":
        file_path = tool_input.get("file_path", "")
        content = tool_input.get("content", "")

        return {
            "file": file_path,
            "change_type": "write",
            "change_summary": u"创建/覆盖文件 ({} 字节)".format(len(content)),
            "content_length": len(content)
        }

    return None


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


def get_active_task_meta_path(cwd):
    """获取当前活跃任务的元数据路径"""
    workflow_state_path = os.path.join(cwd, '.claude', 'workflow-state.json')
    workflow_state = load_json(workflow_state_path)

    if not workflow_state:
        return None

    task_id = workflow_state.get("task_id")
    if not task_id:
        return None

    meta_path = os.path.join(cwd, 'tasks', task_id, '.task-meta.json')
    if not os.path.exists(meta_path):
        return None

    return meta_path


def update_iteration_changes(tool_name: str, tool_input: dict, cwd: str, logger):
    """
    将代码修改记录到当前迭代

    策略:
    1. 提取修改信息
    2. 添加到当前迭代的changes_made
    3. 更新same_file_edit_count指标
    4. 同步到.task-meta.json
    """

    change = extract_code_changes(tool_name, tool_input)
    if not change:
        return

    # 读取workflow-state
    workflow_state_path = os.path.join(cwd, '.claude', 'workflow-state.json')
    workflow_state = load_json(workflow_state_path)

    if not workflow_state:
        logger.info(u"workflow-state.json不存在，跳过追踪")
        return

    # === Bug修复追踪 ===
    if workflow_state.get("bug_fix_tracking", {}).get("enabled"):
        tracking = workflow_state["bug_fix_tracking"]

        if tracking["iterations"]:
            current_iteration = tracking["iterations"][-1]
            current_iteration["changes_made"].append(change)

            # 更新循环指标: 统计同一文件被修改的次数
            file_path = change["file"]
            file_edit_count = sum(
                1 for iter in tracking["iterations"]
                for c in iter.get("changes_made", [])
                if c["file"] == file_path
            )
            tracking["loop_indicators"]["same_file_edit_count"] = file_edit_count

            logger.info(u"记录Bug修复代码修改", {
                "file": file_path,
                "type": change["change_type"],
                "same_file_edits": file_edit_count
            })

    # === 需求实现追踪 ===
    if workflow_state.get("feature_tracking", {}).get("enabled"):
        tracking = workflow_state["feature_tracking"]

        if tracking["iterations"]:
            current_iteration = tracking["iterations"][-1]
            if "changes_made" not in current_iteration:
                current_iteration["changes_made"] = []
            current_iteration["changes_made"].append(change)

            logger.info(u"记录需求实现代码修改", {
                "file": change["file"],
                "type": change["change_type"]
            })

    # 保存workflow-state
    save_json(workflow_state_path, workflow_state)

    # === 同步到 .task-meta.json ===
    meta_path = get_active_task_meta_path(cwd)
    if meta_path:
        task_meta = load_json(meta_path)
        if task_meta:
            # 更新tracking_state
            if "tracking_state" not in task_meta:
                task_meta["tracking_state"] = {}

            task_meta["tracking_state"]["bug_fix_tracking"] = workflow_state.get("bug_fix_tracking")
            task_meta["tracking_state"]["feature_tracking"] = workflow_state.get("feature_tracking")
            task_meta["updated_at"] = datetime.now().isoformat()

            save_json(meta_path, task_meta)


# ==================== 主函数 ====================

def main():
    logger = HookLogger("post-tool-use-hook")
    logger.start()

    try:
        # 读取stdin输入
        # Hook接收的数据格式:
        # {
        #   "tool_name": "Edit",
        #   "tool_input": {"file_path": "...", "old_string": "...", "new_string": "..."},
        #   "tool_output": "..."
        # }

        data = json.load(sys.stdin)
        tool_name = data.get('tool_name', '')
        tool_input = data.get('tool_input', {})
        cwd = os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd())

        # 只处理Edit和Write工具
        if tool_name not in ["Edit", "Write"]:
            logger.info(u"跳过非代码修改工具: {}".format(tool_name))
            output = {"continue": True}
            print(json.dumps(output, ensure_ascii=False))
            logger.finish(success=True, message=u"跳过")
            sys.exit(0)

        # 更新迭代修改记录
        update_iteration_changes(tool_name, tool_input, cwd, logger)

        # 输出控制JSON (放行)
        output = {"continue": True}
        print(json.dumps(output, ensure_ascii=False))

        logger.finish(success=True, message=u"追踪完成")
        sys.exit(0)

    except Exception as e:
        logger.error(u"Hook执行失败", e)
        import traceback
        traceback.print_exc(file=sys.stderr)

        # 即使失败也放行
        output = {"continue": True}
        print(json.dumps(output, ensure_ascii=False))
        logger.finish(success=False, message=u"执行异常")
        sys.exit(0)


if __name__ == '__main__':
    main()
