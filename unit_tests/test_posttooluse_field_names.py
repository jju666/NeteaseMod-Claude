#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PostToolUse Hook 字段名修复验证测试
用于验证 BUG 修复：posttooluse_updater.py 应使用 snake_case 字段名

测试目标:
1. 验证 PostToolUse Hook 能正确读取 snake_case 字段名（tool_name, tool_input等）
2. 验证 Read 工具调用后，metrics.docs_read 正常更新
3. 验证向后兼容：旧版本 camelCase 字段名仍能工作（但会有警告）
"""

import json
import os
import sys
import subprocess
import tempfile
from pathlib import Path

# Windows UTF-8 支持
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 测试配置
HOOK_SCRIPT = Path(__file__).parent.parent / "templates" / ".claude" / "hooks" / "orchestrator" / "posttooluse_updater.py"
TEST_TASK_DIR = Path(tempfile.gettempdir()) / "modsdk_test_task"


def setup_test_environment():
    """创建测试环境"""
    # 创建测试任务目录
    tasks_dir = TEST_TASK_DIR / "tasks" / "test-task-001"
    tasks_dir.mkdir(parents=True, exist_ok=True)

    # 创建初始 task-meta.json
    task_meta = {
        "task_id": "test-task-001",
        "task_type": "general",
        "current_step": "implementation",
        "architecture_version": "v3.0 Final",
        "steps": {
            "activation": {"status": "completed"},
            "planning": {
                "status": "completed",
                "required_doc_count": 3
            },
            "implementation": {"status": "in_progress"},
            "finalization": {"status": "pending"}
        },
        "metrics": {
            "tools_used": [],
            "code_changes": [],
            "docs_read": [],
            "failed_operations": []
        }
    }

    meta_path = tasks_dir / ".task-meta.json"
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(task_meta, f, ensure_ascii=False, indent=2)

    # 创建 .task-active.json
    active_path = TEST_TASK_DIR / ".claude" / ".task-active.json"
    active_path.parent.mkdir(parents=True, exist_ok=True)
    with open(active_path, 'w', encoding='utf-8') as f:
        json.dump({"task_id": "test-task-001"}, f)

    return task_meta


def cleanup_test_environment():
    """清理测试环境"""
    import shutil
    if TEST_TASK_DIR.exists():
        shutil.rmtree(TEST_TASK_DIR)


def run_hook(hook_input_data, cwd=None):
    """运行 PostToolUse Hook 并返回结果"""
    if cwd is None:
        cwd = str(TEST_TASK_DIR)

    result = subprocess.run(
        ["python", str(HOOK_SCRIPT)],
        input=json.dumps(hook_input_data),
        capture_output=True,
        text=True,
        cwd=cwd,
        encoding='utf-8'
    )

    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode
    }


def load_task_meta():
    """读取 task-meta.json"""
    meta_path = TEST_TASK_DIR / "tasks" / "test-task-001" / ".task-meta.json"
    with open(meta_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def test_snake_case_fields():
    """测试1: 验证正确的 snake_case 字段名"""
    print("\n【测试1】验证 snake_case 字段名（修复后的正确格式）")
    print("=" * 60)

    # 模拟 PostToolUse Hook 输入（使用 snake_case）
    hook_input = {
        "session_id": "test-session",
        "transcript_path": "/tmp/transcript.jsonl",
        "cwd": str(TEST_TASK_DIR),
        "permission_mode": "default",
        "hook_event_name": "PostToolUse",
        "tool_name": "Read",  # ✅ 正确：snake_case
        "tool_input": {      # ✅ 正确：snake_case
            "file_path": "markdown/开发规范.md"
        },
        "tool_response": {   # ✅ 正确：tool_response
            "success": True
        },
        "is_error": False    # ✅ 正确：snake_case
    }

    result = run_hook(hook_input)

    # 验证 Hook 执行成功
    assert result["returncode"] == 0, f"Hook执行失败: {result['stderr']}"
    print("✅ Hook执行成功（退出码0）")

    # 验证没有错误日志
    assert "ERROR" not in result["stderr"], f"发现错误日志: {result['stderr']}"
    print("✅ 无错误日志")

    # 验证 metrics.docs_read 被更新
    task_meta = load_task_meta()
    docs_read = task_meta["metrics"]["docs_read"]

    assert len(docs_read) == 1, f"docs_read 应该包含1条记录，实际: {len(docs_read)}"
    assert docs_read[0]["file"] == "markdown/开发规范.md", f"文件路径不匹配: {docs_read[0]['file']}"
    print(f"✅ docs_read 正确更新: {docs_read[0]['file']}")

    # 验证 tools_used 也被更新
    tools_used = task_meta["metrics"]["tools_used"]
    assert len(tools_used) == 1, f"tools_used 应该包含1条记录"
    assert tools_used[0]["tool"] == "Read", f"工具名不匹配"
    print(f"✅ tools_used 正确更新")

    print("\n【测试1通过】✅ snake_case 字段名工作正常\n")
    return True


def test_camelcase_backward_compatibility():
    """测试2: 验证向后兼容性（旧版本 camelCase 字段名）"""
    print("\n【测试2】验证向后兼容性（camelCase 字段名应该仍能工作）")
    print("=" * 60)

    # 重置测试环境
    cleanup_test_environment()
    setup_test_environment()

    # 模拟旧版本 PostToolUse Hook 输入（使用 camelCase）
    hook_input = {
        "session_id": "test-session",
        "transcript_path": "/tmp/transcript.jsonl",
        "cwd": str(TEST_TASK_DIR),
        "permission_mode": "default",
        "hook_event_name": "PostToolUse",
        "toolName": "Read",     # ⚠️ 旧版本：camelCase
        "toolInput": {          # ⚠️ 旧版本：camelCase
            "file_path": "markdown/问题排查.md"
        },
        "toolResult": {         # ⚠️ 旧版本：toolResult
            "success": True
        },
        "isError": False        # ⚠️ 旧版本：camelCase
    }

    result = run_hook(hook_input)

    # 验证 Hook 执行成功（应该通过容错逻辑）
    assert result["returncode"] == 0, f"Hook执行失败: {result['stderr']}"
    print("✅ Hook执行成功（容错逻辑生效）")

    # 验证有警告日志（提示使用了旧版本字段名）
    assert "WARN" in result["stderr"], "应该有警告日志提示使用旧版本字段名"
    assert "camelCase" in result["stderr"], f"警告消息应该提到camelCase: {result['stderr']}"
    print(f"✅ 警告日志正确: {result['stderr'].strip()}")

    # 验证 metrics.docs_read 仍然被更新
    task_meta = load_task_meta()
    docs_read = task_meta["metrics"]["docs_read"]

    assert len(docs_read) == 1, f"docs_read 应该包含1条记录（即使使用旧字段名）"
    assert docs_read[0]["file"] == "markdown/问题排查.md"
    print(f"✅ 旧字段名仍能工作: {docs_read[0]['file']}")

    print("\n【测试2通过】✅ 向后兼容性正常\n")
    return True


def test_multiple_reads():
    """测试3: 验证多次 Read 调用累积记录"""
    print("\n【测试3】验证多次 Read 调用能累积记录到 docs_read")
    print("=" * 60)

    # 重置测试环境
    cleanup_test_environment()
    setup_test_environment()

    markdown_files = [
        "markdown/开发规范.md",
        "markdown/问题排查.md",
        "markdown/快速开始.md"
    ]

    for i, file_path in enumerate(markdown_files, 1):
        hook_input = {
            "session_id": "test-session",
            "cwd": str(TEST_TASK_DIR),
            "hook_event_name": "PostToolUse",
            "tool_name": "Read",
            "tool_input": {"file_path": file_path},
            "tool_response": {"success": True},
            "is_error": False
        }

        result = run_hook(hook_input)
        assert result["returncode"] == 0

        task_meta = load_task_meta()
        docs_read = task_meta["metrics"]["docs_read"]

        assert len(docs_read) == i, f"第{i}次Read后应该有{i}条记录，实际: {len(docs_read)}"
        print(f"  ✅ 第{i}次 Read: {file_path} → docs_read.length = {len(docs_read)}")

    # 最终验证
    task_meta = load_task_meta()
    docs_read = task_meta["metrics"]["docs_read"]

    assert len(docs_read) == 3, "最终应该有3条记录"
    assert all(doc["file"] in markdown_files for doc in docs_read)

    print(f"\n✅ 累积记录正确: {[doc['file'] for doc in docs_read]}")
    print("\n【测试3通过】✅ 多次Read累积记录正常\n")
    return True


def test_non_markdown_ignored():
    """测试4: 验证非markdown文件不会被记录到 docs_read"""
    print("\n【测试4】验证非markdown文件不记录到 docs_read")
    print("=" * 60)

    # 重置测试环境
    cleanup_test_environment()
    setup_test_environment()

    # 读取Python文件（不应该记录）
    hook_input = {
        "session_id": "test-session",
        "cwd": str(TEST_TASK_DIR),
        "hook_event_name": "PostToolUse",
        "tool_name": "Read",
        "tool_input": {"file_path": "behavior_packs/test.py"},
        "tool_response": {"success": True},
        "is_error": False
    }

    result = run_hook(hook_input)
    assert result["returncode"] == 0

    task_meta = load_task_meta()
    docs_read = task_meta["metrics"]["docs_read"]

    assert len(docs_read) == 0, f"Python文件不应该记录到docs_read，实际: {len(docs_read)}"
    print("✅ Python文件未记录到 docs_read")

    # tools_used 应该仍然记录
    tools_used = task_meta["metrics"]["tools_used"]
    assert len(tools_used) == 1
    assert tools_used[0]["tool"] == "Read"
    print("✅ tools_used 仍然记录了Read工具")

    print("\n【测试4通过】✅ 非markdown文件过滤正常\n")
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("PostToolUse Hook 字段名修复验证测试套件")
    print("=" * 60)

    try:
        # 设置测试环境
        setup_test_environment()

        # 运行测试
        tests = [
            ("snake_case 字段名", test_snake_case_fields),
            ("camelCase 向后兼容", test_camelcase_backward_compatibility),
            ("多次Read累积", test_multiple_reads),
            ("非markdown过滤", test_non_markdown_ignored)
        ]

        results = []
        for name, test_func in tests:
            try:
                test_func()
                results.append((name, True, None))
            except Exception as e:
                results.append((name, False, str(e)))
                print(f"❌ 测试失败: {name}")
                print(f"   错误: {e}\n")

        # 打印总结
        print("\n" + "=" * 60)
        print("测试总结")
        print("=" * 60)

        passed = sum(1 for _, success, _ in results if success)
        total = len(results)

        for name, success, error in results:
            status = "✅ 通过" if success else "❌ 失败"
            print(f"{status}: {name}")
            if error:
                print(f"       错误: {error}")

        print(f"\n总计: {passed}/{total} 测试通过")

        if passed == total:
            print("\n🎉 所有测试通过！BUG修复验证成功！")
            return 0
        else:
            print(f"\n⚠️ 有 {total - passed} 个测试失败")
            return 1

    finally:
        # 清理测试环境
        cleanup_test_environment()


if __name__ == "__main__":
    sys.exit(run_all_tests())
