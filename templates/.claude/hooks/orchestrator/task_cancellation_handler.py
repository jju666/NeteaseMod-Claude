#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task Cancellation Handler - 任务取消/失败处理器 (v21.0)

职责:
1. 检测任务取消/失败意图 (/mc-cancel, /mc-fail)
2. 归档失败任务到 tasks/已失败/
3. 清理运行时状态文件
4. 生成取消确认消息

核心变更(v21.0):
- 使用 TaskMetaManager 替代 StateManager
- 使用 atomic_update() 更新任务元数据
- 使用 clear_active_task() 清理状态
- 删除 workflow-state.json 相关逻辑

触发时机: UserPromptSubmit Hook (在任务初始化之前)
"""

import sys
import json
import os
import shutil
from datetime import datetime
from typing import Optional, Tuple, Dict

# 添加core模块到sys.path
HOOK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HOOK_DIR)

try:
    from core.task_meta_manager import TaskMetaManager
except ImportError as e:
    sys.stderr.write(f"[ERROR] 无法导入TaskMetaManager: {e}\n")


def detect_cancellation_intent(user_input: str) -> Tuple[bool, str, Optional[str]]:
    """
    检测用户取消/失败意图

    Args:
        user_input: 用户输入文本

    Returns:
        (is_cancellation, cancel_type, reason)
        - is_cancellation: 是否是取消操作
        - cancel_type: "cancel" | "fail"
        - reason: 失败原因（仅fail类型有效）
    """
    import re

    user_input_lower = user_input.lower().strip()

    # 检测 /mc-cancel 命令
    if '/mc-cancel' in user_input_lower or '/mc cancel' in user_input_lower:
        return True, "cancel", None

    # 检测取消关键词（中英文）
    cancel_keywords = [
        '取消任务', '放弃任务', 'cancel task', 'abandon task',
        '不做了', '停止任务', '终止任务'
    ]

    for keyword in cancel_keywords:
        if keyword in user_input_lower:
            return True, "cancel", None

    # 检测 /mc-fail 命令
    fail_match = re.search(r'/mc-fail\s+(.+)', user_input, re.IGNORECASE)
    if fail_match:
        reason = fail_match.group(1).strip()
        return True, "fail", reason

    # 检测失败声明关键词
    fail_patterns = [
        r'标记.*失败',
        r'任务失败',
        r'task.*failed',
        r'无法完成',
        r'不能解决'
    ]

    for pattern in fail_patterns:
        match = re.search(pattern, user_input_lower)
        if match:
            # 尝试提取原因（简单提取整句话）
            reason = user_input[:100]  # 截取前100字符作为原因
            return True, "fail", reason

    return False, "", None


def cancel_or_fail_task(
    cancel_type: str,
    reason: Optional[str],
    cwd: str
) -> str:
    """
    执行任务取消或失败归档 (v21.0)

    Args:
        cancel_type: "cancel" | "fail"
        reason: 失败原因
        cwd: 工作目录

    Returns:
        确认消息文本
    """
    # 1. 初始化 TaskMetaManager
    mgr = TaskMetaManager(cwd)

    # 2. 获取活跃任务ID
    task_id = mgr.get_active_task_id()
    if not task_id:
        return """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 无活跃任务
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

当前没有进行中的任务，无法执行取消操作。

**提示**: 使用 `/mc 任务描述` 创建新任务
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    # 3. 加载任务元数据
    task_meta = mgr.load_task_meta(task_id)
    if not task_meta:
        # 任务元数据不存在，但仍清理活跃标记
        mgr.clear_active_task()
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 任务元数据缺失
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**任务ID**: {task_id}
**问题**: 任务元数据不存在，但活跃标记已清理

已清理运行时状态，可以创建新任务。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    current_step = task_meta.get('current_step', 'unknown')
    task_description = task_meta.get('task_description', '')

    # 4. 确定任务目录
    task_dir = mgr.get_task_dir(task_id)

    if not os.path.exists(task_dir):
        sys.stderr.write(f"[WARN] 任务目录不存在: {task_dir}\n")
        # 仍然清理状态文件
        mgr.clear_active_task()
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 任务目录缺失
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**任务ID**: {task_id}
**问题**: 任务目录不存在，但状态文件已清理

已清理运行时状态，可以创建新任务。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    # 5. 创建失败归档目录
    if cancel_type == "cancel":
        failed_root = os.path.join(cwd, 'tasks', '已取消')
        status_display = "已取消"
        status_emoji = "🚫"
    else:
        failed_root = os.path.join(cwd, 'tasks', '已失败')
        status_display = "已失败"
        status_emoji = "❌"

    os.makedirs(failed_root, exist_ok=True)

    # 6. 更新 task_meta（使用原子更新）
    def update_func(meta: Dict) -> Dict:
        meta['archived'] = True
        meta['failed'] = True
        meta['cancel_type'] = cancel_type
        meta['failure_reason'] = reason or (f"用户{status_display}")
        meta['failed_at'] = datetime.now().isoformat()
        meta['final_step'] = current_step
        return meta

    updated_meta = mgr.atomic_update(task_id, update_func)

    if not updated_meta:
        sys.stderr.write(f"[ERROR] 更新任务元数据失败: {task_id}\n")

    # 7. 移动到失败目录
    failed_task_dir = os.path.join(failed_root, task_id)

    try:
        # 如果目标已存在（之前失败的同名任务），先删除
        if os.path.exists(failed_task_dir):
            sys.stderr.write(f"[WARN] 目标已存在，覆盖: {failed_task_dir}\n")
            shutil.rmtree(failed_task_dir)

        # 移动目录
        shutil.move(task_dir, failed_task_dir)
        sys.stderr.write(f"[INFO] 任务已归档到: {failed_task_dir}\n")

    except Exception as e:
        sys.stderr.write(f"[ERROR] 归档失败: {e}\n")
        return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ 归档失败
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**任务ID**: {task_id}
**错误**: {e}

**建议**: 手动移动任务目录
- 源路径: {task_dir}
- 目标路径: {failed_task_dir}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    # 8. 清理运行时状态（v21.0: 使用 clear_active_task）
    mgr.clear_active_task()

    # 9. 生成确认消息
    confirmation_message = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{status_emoji} 任务{status_display}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**任务ID**: {task_id}
**任务描述**: {task_description}
**最终步骤**: {current_step}
**归档路径**: tasks/{os.path.basename(failed_root)}/{task_id}/
"""

    if reason:
        confirmation_message += f"""
**{status_display}原因**: {reason}
"""

    # 统计信息
    metrics = task_meta.get('metrics', {})
    docs_read_count = len(metrics.get('docs_read', []))
    code_changes_count = len(metrics.get('code_changes', []))

    confirmation_message += f"""
**任务统计**:
- 阅读文档: {docs_read_count} 个
- 代码修改: {code_changes_count} 次
- 用时: {calculate_duration(task_meta)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ 运行时状态已清理，可以开始新任务

**提示**:
- 查看{status_display}任务: tasks/{os.path.basename(failed_root)}/{task_id}/
- 创建新任务: /mc 任务描述
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    return confirmation_message


def calculate_duration(task_meta: Dict) -> str:
    """计算任务持续时间"""
    try:
        created_at = task_meta.get('created_at')
        failed_at = task_meta.get('failed_at')

        if not created_at or not failed_at:
            return "未知"

        from datetime import datetime
        start = datetime.fromisoformat(created_at)
        end = datetime.fromisoformat(failed_at)
        duration = end - start

        # 格式化输出
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60

        if hours > 0:
            return f"{hours}小时{minutes}分钟"
        elif minutes > 0:
            return f"{minutes}分钟"
        else:
            return f"{total_seconds}秒"

    except Exception as e:
        sys.stderr.write(f"[WARN] 计算时长失败: {e}\n")
        return "未知"


def handle_cancellation_from_user_prompt(user_input: str, cwd: str) -> Optional[str]:
    """
    从UserPromptSubmit Hook调用的入口函数 (v21.0)

    Args:
        user_input: 用户输入
        cwd: 工作目录

    Returns:
        如果是取消操作，返回确认消息；否则返回None
    """
    # 1. 检测取消意图
    is_cancellation, cancel_type, reason = detect_cancellation_intent(user_input)

    if not is_cancellation:
        return None

    # 2. 执行取消/失败
    confirmation_message = cancel_or_fail_task(cancel_type, reason, cwd)

    return confirmation_message


# ============== 独立运行模式（用于测试）==============

def main():
    """独立运行入口（测试用）"""
    try:
        # 读取stdin输入
        data = json.load(sys.stdin)

        prompt = data.get('prompt', '')
        cwd = os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd())

        # 处理取消
        confirmation = handle_cancellation_from_user_prompt(prompt, cwd)

        if confirmation:
            # 输出控制JSON
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": confirmation
                },
                "continue": False,  # 阻止继续执行
                "stopReason": "task_cancelled"
            }
            print(json.dumps(output, ensure_ascii=False))
            sys.exit(0)
        else:
            # 非取消操作，放行
            output = {"continue": True}
            print(json.dumps(output, ensure_ascii=False))
            sys.exit(0)

    except Exception as e:
        sys.stderr.write(f"[ERROR] Hook执行失败: {e}\n")
        import traceback
        traceback.print_exc(file=sys.stderr)

        # 错误时放行（避免阻塞工作流）
        output = {"continue": True}
        print(json.dumps(output, ensure_ascii=False))
        sys.exit(1)


if __name__ == '__main__':
    main()
