#!/usr/bin/env python3
"""
NeteaseMod-Claude Hook: 修改日志自动记录
触发时机: PostToolUse (Edit/Write 成功后)
功能: 自动记录文件修改到当前任务目录
作者: NeteaseMod-Claude Workflow
版本: v18.3.0
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path
import io

# 修复Windows GBK编码问题：强制使用UTF-8输出
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 导入通知模块
try:
    from vscode_notify import notify_info
except ImportError:
    def notify_info(msg, detail=""): pass

def main():
    """主函数：从stdin读取JSON,记录修改日志"""
    try:
        # 从stdin读取JSON输入
        input_data = json.load(sys.stdin)

        # 提取关键字段
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        # 只记录Edit和Write工具
        if tool_name not in ["Edit", "Write"]:
            sys.exit(0)

        # 获取文件路径
        file_path = tool_input.get("file_path", "")
        if not file_path:
            sys.exit(0)

        # 查找当前任务目录（tasks/task-*）
        task_dir = find_current_task_dir()
        if not task_dir:
            # 未找到任务目录，跳过记录（微任务场景）
            sys.exit(0)

        # 记录修改日志
        log_change(task_dir, tool_name, file_path, tool_input)

        # 📢 通知：任务文档更新
        # 当修改 context.md 或 solution.md 时发送通知
        if "context.md" in file_path or "solution.md" in file_path:
            try:
                doc_name = "任务上下文" if "context.md" in file_path else "解决方案"
                notify_info(
                    u"任务文档更新",
                    u"已更新: {}".format(doc_name)
                )
            except:
                pass

        sys.exit(0)

    except Exception as e:
        # 异常时不影响主流程，只输出警告
        print(f"⚠️ log-changes Hook执行异常（已跳过）: {str(e)}", file=sys.stderr)
        sys.exit(0)


def find_current_task_dir():
    """
    查找当前任务目录

    Returns:
        str: 任务目录路径，如果未找到返回None
    """
    try:
        # 获取项目根目录
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
        tasks_dir = Path(project_dir) / "tasks"

        if not tasks_dir.exists():
            return None

        # 查找最近修改的任务目录（假设是当前任务）
        task_dirs = [
            d for d in tasks_dir.iterdir()
            if d.is_dir() and d.name.startswith("task-")
        ]

        if not task_dirs:
            return None

        # 返回最新的任务目录
        latest_task = max(task_dirs, key=lambda d: d.stat().st_mtime)
        return str(latest_task)

    except Exception:
        return None


def log_change(task_dir, tool_name, file_path, tool_input):
    """
    记录修改日志到change-log.md

    Args:
        task_dir: 任务目录路径
        tool_name: 工具名称（Edit/Write）
        file_path: 修改的文件路径
        tool_input: 工具输入参数
    """
    try:
        log_file = Path(task_dir) / "change-log.md"

        # 提取修改信息
        old_string = tool_input.get("old_string", "")
        new_string = tool_input.get("new_string", "")
        content = tool_input.get("content", "")

        # 计算修改量
        if tool_name == "Edit":
            added = len(new_string)
            removed = len(old_string)
            change_type = "修改"
        else:  # Write
            added = len(content)
            removed = 0
            change_type = "创建/覆盖"

        # 格式化日志
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"""
## [{timestamp}] {change_type}

**文件**: `{file_path}`
**操作**: {tool_name}
**变更**: +{added} 字符, -{removed} 字符

---
"""

        # 追加到日志文件
        with open(log_file, "a", encoding="utf-8") as f:
            # 如果是新文件，添加标题
            if not log_file.exists() or log_file.stat().st_size == 0:
                f.write("# 任务修改日志\n\n")
                f.write("> 本文件由 `log-changes.py` Hook 自动生成\n\n")

            f.write(log_entry)

    except Exception as e:
        # 记录失败不影响主流程
        pass


if __name__ == "__main__":
    main()
