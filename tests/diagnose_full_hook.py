#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整模拟UserPromptSubmit Hook执行流程
"""
import sys
import os
import io
import json

# 修复Windows编码
if sys.platform == 'win32':
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='replace')
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加hooks路径
base_dir = os.path.dirname(os.path.abspath(__file__))
hook_dir = os.path.join(base_dir, '.claude', 'hooks')
sys.path.insert(0, hook_dir)
sys.path.insert(0, os.path.dirname(hook_dir))

print("=" * 60, file=sys.stderr)
print("模拟UserPromptSubmit Hook完整执行", file=sys.stderr)
print("=" * 60, file=sys.stderr)

# 导入TaskMetaManager
try:
    from core.task_meta_manager import TaskMetaManager
    print("[OK] TaskMetaManager导入成功", file=sys.stderr)
except ImportError as e:
    print(f"[FAIL] TaskMetaManager导入失败: {e}", file=sys.stderr)
    sys.exit(1)

# 设置CWD
cwd = base_dir
os.environ['CLAUDE_PROJECT_DIR'] = cwd

# 模拟session_id
session_id = "test-session-diagnose"

# 获取当前绑定的任务
meta_manager = TaskMetaManager(cwd)
print(f"\n[INFO] 工作目录: {cwd}", file=sys.stderr)

# 手动绑定任务（如果没有绑定）
task_id = "任务-1120-020531-修复玩家死亡复活"
try:
    # 先解除所有绑定
    meta_manager.unbind_task_from_session(session_id)
    # 绑定测试任务
    meta_manager.bind_task_to_session(task_id, session_id)
    print(f"[OK] 已绑定任务: {task_id}", file=sys.stderr)
except Exception as e:
    print(f"[WARN] 绑定任务失败: {e}", file=sys.stderr)

# 检查当前任务
active_task = meta_manager.get_active_task_by_session(session_id)
if not active_task:
    print(f"[FAIL] 无法获取active_task", file=sys.stderr)
    sys.exit(1)

print(f"[OK] 当前任务: {active_task['task_id']}", file=sys.stderr)
print(f"[OK] 当前阶段: {active_task.get('current_step', 'unknown')}", file=sys.stderr)

# 读取当前task-meta.json
meta_path = meta_manager._get_meta_path(task_id)
print(f"\n[INFO] task-meta.json路径: {meta_path}", file=sys.stderr)

with open(meta_path, 'r', encoding='utf-8') as f:
    original_meta = json.load(f)

print(f"[INFO] 原始状态:", file=sys.stderr)
print(f"  - current_step: {original_meta.get('current_step')}", file=sys.stderr)
print(f"  - implementation.status: {original_meta.get('steps', {}).get('implementation', {}).get('status')}", file=sys.stderr)
print(f"  - implementation.user_confirmed: {original_meta.get('steps', {}).get('implementation', {}).get('user_confirmed')}", file=sys.stderr)
print(f"  - state_transitions count: {len(original_meta.get('state_transitions', []))}", file=sys.stderr)

# 模拟用户输入
user_input = "我测试没问题了"
print(f"\n[INFO] 用户输入: '{user_input}'", file=sys.stderr)

# 导入handle_state_transition
sys.path.insert(0, os.path.join(hook_dir, 'orchestrator'))

try:
    # 注意：这里需要手动import所有依赖，因为user_prompt_handler.py有很多全局导入
    print("[INFO] 导入user_prompt_handler模块...", file=sys.stderr)

    # 直接执行handle_state_transition函数
    # 为了避免复杂的模块导入问题，我们直接读取并执行相关函数

    # 使用exec来执行handle_state_transition
    import importlib.util
    spec = importlib.util.spec_from_file_location("user_prompt_handler",
                                                    os.path.join(hook_dir, 'orchestrator', 'user_prompt_handler.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    print("[OK] user_prompt_handler模块导入成功", file=sys.stderr)

    # 调用handle_state_transition
    print("\n" + "=" * 60, file=sys.stderr)
    print("开始执行handle_state_transition", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    result = module.handle_state_transition(user_input, cwd, session_id)

    print("\n" + "=" * 60, file=sys.stderr)
    print("handle_state_transition执行完成", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    if result:
        print(f"[OK] 返回值: {type(result)}", file=sys.stderr)
        print(f"[OK] 返回内容: {json.dumps(result, ensure_ascii=False, indent=2)[:500]}", file=sys.stderr)
    else:
        print(f"[WARN] 返回值为None", file=sys.stderr)

    # 读取更新后的task-meta.json
    with open(meta_path, 'r', encoding='utf-8') as f:
        updated_meta = json.load(f)

    print(f"\n[INFO] 更新后状态:", file=sys.stderr)
    print(f"  - current_step: {updated_meta.get('current_step')}", file=sys.stderr)
    print(f"  - implementation.status: {updated_meta.get('steps', {}).get('implementation', {}).get('status')}", file=sys.stderr)
    print(f"  - implementation.user_confirmed: {updated_meta.get('steps', {}).get('implementation', {}).get('user_confirmed')}", file=sys.stderr)
    print(f"  - state_transitions count: {len(updated_meta.get('state_transitions', []))}", file=sys.stderr)

    # 检查是否发生了状态转移
    if updated_meta.get('current_step') == 'finalization':
        print(f"\n[OK] 状态转移成功: implementation -> finalization", file=sys.stderr)
    else:
        print(f"\n[FAIL] 状态未转移，仍然是: {updated_meta.get('current_step')}", file=sys.stderr)

except Exception as e:
    print(f"[ERROR] 执行失败: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)

print("\n" + "=" * 60, file=sys.stderr)
print("诊断完成", file=sys.stderr)
print("=" * 60, file=sys.stderr)
