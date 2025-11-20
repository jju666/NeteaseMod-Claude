#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整模拟Implementation阶段UserPromptSubmit Hook执行
"""
import sys
import os
import io
import json

# 修复Windows编码
if sys.platform == 'win32':
    if not isinstance(sys.stdout, io.TextIOWrapper):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        except (AttributeError, ValueError):
            pass

# 添加hooks路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.claude', 'hooks'))

print("=" * 60)
print("Implementation Hook完整执行模拟")
print("=" * 60)

# 加载task-meta.json
base_dir = os.path.dirname(os.path.abspath(__file__))
task_meta_path = os.path.join(base_dir, "tasks", "任务-1120-020531-修复玩家死亡复活", ".task-meta.json")
print(f"\n加载task-meta.json: {task_meta_path}")

if not os.path.exists(task_meta_path):
    print(f"[ERROR] 文件不存在: {task_meta_path}")
    sys.exit(1)

with open(task_meta_path, 'r', encoding='utf-8') as f:
    meta_data = json.load(f)

print(f"  当前阶段: {meta_data['current_step']}")
print(f"  代码修改次数: {len(meta_data.get('metrics', {}).get('code_changes', []))}")

# 导入必要模块
from core.claude_semantic_analyzer import analyze_user_intent, ANTHROPIC_AVAILABLE

print(f"\n[OK] ANTHROPIC_AVAILABLE = {ANTHROPIC_AVAILABLE}")

# 模拟用户输入
user_input = "我测试没问题了"
print(f"\n用户输入: '{user_input}'")

# 构建上下文
context = {
    'current_step': 'implementation',
    'code_changes': len(meta_data.get('metrics', {}).get('code_changes', [])),
    'iteration': len(meta_data.get('steps', {}).get('implementation', {}).get('iterations', []))
}

print(f"\n上下文: {context}")

# 执行LLM分析
print("\n" + "=" * 60)
print("开始LLM分析")
print("=" * 60)

llm_analysis_success = False

if ANTHROPIC_AVAILABLE:
    try:
        print("[INFO] 调用Claude API进行语义分析...")
        llm_result = analyze_user_intent(user_input, context)

        print(f"\nLLM返回结果:")
        print(f"  success: {llm_result['success']}")
        print(f"  intent: {llm_result['intent']}")
        print(f"  confidence: {llm_result['confidence']:.0%}")
        print(f"  reasoning: {llm_result.get('reasoning', '')[:100]}")

        if llm_result['success'] and llm_result['confidence'] >= 0.8:
            llm_analysis_success = True
            intent = llm_result['intent']

            print(f"\n[OK] LLM分析成功，置信度达标")

            # 映射意图到标志（模拟Hook代码）
            if intent == 'complete_success':
                has_success = True
                has_failure = False
                has_planning_required = False
                print(f"[INFO] 设置标志: has_success=True")
                print(f"[INFO] LLM判定: 完全成功 → 应该进入收尾阶段")
            elif intent == 'partial_success' or intent == 'failure' or intent == 'continuation_request':
                has_success = False
                has_failure = True
                has_planning_required = False
                print(f"[INFO] 设置标志: has_failure=True")
            elif intent == 'planning_required':
                has_success = False
                has_failure = False
                has_planning_required = True
                print(f"[INFO] 设置标志: has_planning_required=True")
            else:
                llm_analysis_success = False
                print(f"[WARN] 未知意图: {intent}")
        else:
            print(f"[WARN] LLM分析置信度不足或失败")
            if not llm_result['success']:
                print(f"  错误: {llm_result.get('error', '未知')}")
            else:
                print(f"  置信度: {llm_result['confidence']:.0%} (< 80%)")

    except Exception as e:
        print(f"[ERROR] LLM分析异常: {e}")
        import traceback
        traceback.print_exc()
        llm_analysis_success = False

# 检查结果
print("\n" + "=" * 60)
print("分析结果总结")
print("=" * 60)

if llm_analysis_success:
    print(f"[OK] LLM分析成功")
    print(f"[OK] has_success = {has_success}")
    print(f"[OK] has_failure = {has_failure}")
    print(f"[OK] has_planning_required = {has_planning_required}")

    if has_success:
        print("\n[ACTION] 应该执行以下操作:")
        print("  1. 检查是否有PARTIAL_SUCCESS_KEYWORDS")
        print("  2. 如果没有，转移到finalization状态")
        print("  3. 更新task-meta.json")
        print("  4. 记录state_transitions")
        print("\n[QUESTION] 为什么实际运行时没有转移状态？")
    else:
        print("\n[INFO] has_success=False，不会转移到finalization")
else:
    print(f"[FAIL] LLM分析失败")
    print(f"[INFO] Hook会返回meta_data，不做状态转移")

print("\n" + "=" * 60)
print("诊断完成")
print("=" * 60)
