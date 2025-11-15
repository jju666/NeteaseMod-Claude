#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified PreToolUse Enforcer - 统一PreToolUse强制器
Version: v21.0

职责:
1. 拦截所有工具调用(Read/Write/Edit/Bash/Task/Grep/Glob/WebFetch/WebSearch)
2. 执行四层验证(阶段-工具-路径-语义)
3. 违规立即DENY,零容忍
4. 放行后允许工具执行

核心变更(v21.0):
- 使用 TaskMetaManager 替代 StateManager
- 从 task-meta.json 加载状态(唯一数据源)
- 所有 workflow_state 引用改为 task_meta
"""

import sys
import json
import os

# 添加core模块到sys.path
HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_HOOK_DIR = os.path.dirname(HOOK_DIR)
sys.path.insert(0, PARENT_HOOK_DIR)

try:
    from core.stage_validator import StageValidator
    from core.task_meta_manager import TaskMetaManager
except ImportError as e:
    sys.stderr.write(f"[ERROR] 无法导入core模块: {e}\n")
    sys.stderr.write(f"[ERROR] PARENT_HOOK_DIR={PARENT_HOOK_DIR}, sys.path={sys.path}\n")
    # 兜底:允许继续(避免完全阻塞工作流)
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": f"核心模块加载失败,默认放行: {e}"
        },
        "suppressOutput": False
    }, ensure_ascii=False))
    sys.exit(0)


def main():
    """主入口"""
    # 1. 解析输入
    try:
        event_data = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        sys.stderr.write(f"[ERROR] JSON解析失败: {e}\n")
        allow_and_exit("JSON解析失败,默认放行")
        return

    tool_name = event_data.get("toolName", "")
    tool_input = event_data.get("toolInput", {})

    # 2. 获取工作目录
    cwd = os.getcwd()

    # 3. 初始化 TaskMetaManager
    mgr = TaskMetaManager(cwd)

    # 4. 获取活跃任务ID
    task_id = mgr.get_active_task_id()
    if not task_id:
        allow_and_exit("无活跃任务,默认放行", suppress=True)
        return

    # 5. 加载任务元数据(v21.0: 唯一数据源)
    task_meta = mgr.load_task_meta(task_id)
    if not task_meta:
        allow_and_exit("任务元数据不存在,默认放行", suppress=True)
        return

    # 6. 获取当前步骤
    current_step = task_meta.get('current_step', 'step3_execute')

    # 7. 执行四层验证
    try:
        validator = StageValidator(cwd)
        validation_result = validator.validate(
            current_step, tool_name, tool_input, task_meta
        )
    except Exception as e:
        sys.stderr.write(f"[ERROR] 验证过程异常: {e}\n")
        import traceback
        traceback.print_exc()
        # 异常情况下放行(避免完全阻塞)
        allow_and_exit(f"验证异常,默认放行: {e}", suppress=False)
        return

    # 8. 决策
    if validation_result.get("allowed", False):
        # 验证通过,放行
        allow_and_exit(validation_result.get("reason", "验证通过"), suppress=True)
    else:
        # 验证失败,拦截
        deny_and_exit(
            tool_name,
            current_step,
            validation_result.get("reason", "验证失败"),
            validation_result.get("suggestion", "")
        )


def allow_and_exit(reason: str, suppress: bool = True):
    """放行并退出"""
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": reason
        },
        "suppressOutput": suppress
    }
    print(json.dumps(output, ensure_ascii=False))
    sys.exit(0)


def deny_and_exit(tool_name: str, current_step: str, reason: str, suggestion: str):
    """拦截并退出"""
    # 构建拒绝消息
    denial_message = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚫 工具调用被拒绝: {tool_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ 当前阶段: {current_step}
❌ 拒绝原因: {reason}
"""

    if suggestion:
        denial_message += f"""
✅ 正确做法:
{suggestion}
"""

    denial_message += """
⚠️ 工作流强制执行 - 违规操作已被阻止
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": denial_message
        }
    }
    print(json.dumps(output, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
