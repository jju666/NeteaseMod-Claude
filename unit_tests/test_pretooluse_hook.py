#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PreToolUse Hook 单元测试
测试修复后的字段名称和验证逻辑
"""

import json
import subprocess
import sys
import os

# 测试用例
TEST_CASES = [
    {
        "name": "Planning阶段允许Read工具",
        "input": {
            "session_id": "test-session",
            "transcript_path": "/tmp/test.jsonl",
            "cwd": os.getcwd(),
            "permission_mode": "default",
            "hook_event_name": "PreToolUse",
            "tool_name": "Read",  # ✅ 正确：下划线命名
            "tool_input": {
                "file_path": "/test/file.py"
            }
        },
        "expected_decision": "allow",
        "description": "Planning阶段应该允许Read工具"
    },
    {
        "name": "Planning阶段拒绝Write工具",
        "input": {
            "session_id": "test-session",
            "transcript_path": "/tmp/test.jsonl",
            "cwd": os.getcwd(),
            "permission_mode": "default",
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",  # ✅ 正确：下划线命名
            "tool_input": {
                "file_path": "/test/file.py",
                "content": "test"
            }
        },
        "expected_decision": "deny",
        "description": "Planning阶段应该拒绝Write工具"
    },
    {
        "name": "Implementation阶段允许Edit工具",
        "input": {
            "session_id": "test-session",
            "transcript_path": "/tmp/test.jsonl",
            "cwd": os.getcwd(),
            "permission_mode": "default",
            "hook_event_name": "PreToolUse",
            "tool_name": "Edit",
            "tool_input": {
                "file_path": "/test/file.py",
                "old_string": "old",
                "new_string": "new"
            }
        },
        "expected_decision": "allow",
        "description": "Implementation阶段应该允许Edit工具"
    },
    {
        "name": "工具名称归一化测试",
        "input": {
            "session_id": "test-session",
            "transcript_path": "/tmp/test.jsonl",
            "cwd": os.getcwd(),
            "permission_mode": "default",
            "hook_event_name": "PreToolUse",
            "tool_name": "Update",  # Update应该被归一化为Edit
            "tool_input": {
                "file_path": "/test/file.py",
                "old_string": "old",
                "new_string": "new"
            }
        },
        "expected_decision": "allow",
        "description": "Update工具应该被归一化为Edit并允许"
    }
]


def run_hook_test(hook_script, test_case):
    """运行单个测试用例"""
    print(f"\n{'='*60}")
    print(f"测试: {test_case['name']}")
    print(f"描述: {test_case['description']}")
    print(f"{'='*60}")

    # 准备输入JSON
    input_json = json.dumps(test_case['input'], ensure_ascii=False)

    # 执行Hook脚本
    try:
        result = subprocess.run(
            ["python", hook_script],
            input=input_json,
            capture_output=True,
            text=True,
            timeout=10
        )

        # 解析结果
        exit_code = result.returncode
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        print(f"Exit Code: {exit_code}")

        # 判断决策
        actual_decision = None
        if exit_code == 0:
            # 尝试解析JSON输出
            try:
                output_json = json.loads(stdout)
                permission_decision = output_json.get("hookSpecificOutput", {}).get("permissionDecision", "")
                actual_decision = permission_decision
            except json.JSONDecodeError:
                actual_decision = "allow"  # exit 0默认为allow
        elif exit_code == 2:
            actual_decision = "deny"
        else:
            actual_decision = "error"

        # 验证结果
        expected = test_case['expected_decision']
        if actual_decision == expected:
            print(f"✅ 通过 - 决策符合预期: {actual_decision}")
            return True
        else:
            print(f"❌ 失败 - 预期: {expected}, 实际: {actual_decision}")
            if stderr:
                print(f"\nStderr输出:")
                print(stderr)
            if stdout:
                print(f"\nStdout输出:")
                print(stdout)
            return False

    except subprocess.TimeoutExpired:
        print(f"❌ 失败 - Hook执行超时")
        return False
    except Exception as e:
        print(f"❌ 失败 - 异常: {e}")
        return False


def main():
    """主测试函数"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║          PreToolUse Hook 单元测试 (字段名称修复验证)          ║
╚══════════════════════════════════════════════════════════════╝
    """)

    # Hook脚本路径
    hook_script = os.path.join(
        os.path.dirname(__file__),
        "..", "tests", ".claude", "hooks", "orchestrator", "pretooluse_enforcer.py"
    )
    hook_script = os.path.abspath(hook_script)

    if not os.path.exists(hook_script):
        print(f"❌ Hook脚本不存在: {hook_script}")
        return 1

    print(f"Hook脚本路径: {hook_script}\n")

    # 运行所有测试用例
    passed = 0
    failed = 0

    for test_case in TEST_CASES:
        if run_hook_test(hook_script, test_case):
            passed += 1
        else:
            failed += 1

    # 输出测试摘要
    print(f"\n{'='*60}")
    print(f"测试摘要")
    print(f"{'='*60}")
    print(f"总计: {passed + failed}")
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")
    print(f"{'='*60}\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
