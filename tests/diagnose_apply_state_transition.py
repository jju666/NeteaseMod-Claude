#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整模拟apply_state_transition函数执行，找出为什么has_success分支没有被执行
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
print("模拟apply_state_transition函数执行")
print("=" * 60)

# 加载task-meta.json
base_dir = os.path.dirname(os.path.abspath(__file__))
task_meta_path = os.path.join(base_dir, "tasks", "任务-1120-020531-修复玩家死亡复活", ".task-meta.json")

print(f"\n加载task-meta.json: {task_meta_path}")
with open(task_meta_path, 'r', encoding='utf-8') as f:
    meta_data = json.load(f)

current_step = meta_data.get('current_step', '')
print(f"  当前阶段: {current_step}")

if current_step != 'implementation':
    print(f"\n[ERROR] 当前阶段不是implementation，无法模拟")
    sys.exit(1)

# 导入必要模块
from core.claude_semantic_analyzer import analyze_user_intent, ANTHROPIC_AVAILABLE

# 定义用户输入
user_input = "我测试没问题了"
user_input_lower = user_input.lower()

print(f"\n用户输入: '{user_input}'")
print(f"  小写后: '{user_input_lower}'")

# ========== 步骤1: LLM分析 ==========
print("\n" + "=" * 60)
print("步骤1: LLM语义分析")
print("=" * 60)

context = {
    'current_step': 'implementation',
    'code_changes': len(meta_data.get('metrics', {}).get('code_changes', [])),
    'iteration': len(meta_data.get('steps', {}).get('implementation', {}).get('iterations', []))
}

llm_analysis_success = False
has_success = None
has_failure = None
has_planning_required = None

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

            # 映射意图到标志
            if intent == 'complete_success':
                has_success = True
                has_failure = False
                has_planning_required = False
                print(f"[INFO] 设置标志: has_success=True, has_failure=False, has_planning_required=False")
            elif intent == 'partial_success' or intent == 'failure' or intent == 'continuation_request':
                has_success = False
                has_failure = True
                has_planning_required = False
                print(f"[INFO] 设置标志: has_success=False, has_failure=True, has_planning_required=False")
            elif intent == 'planning_required':
                has_success = False
                has_failure = False
                has_planning_required = True
                print(f"[INFO] 设置标志: has_success=False, has_failure=False, has_planning_required=True")
            else:
                llm_analysis_success = False
                print(f"[WARN] 未知意图: {intent}")
        else:
            print(f"[WARN] LLM分析置信度不足或失败")
    except Exception as e:
        print(f"[ERROR] LLM分析异常: {e}")
        llm_analysis_success = False
else:
    print(f"[ERROR] ANTHROPIC_AVAILABLE=False，无法执行LLM分析")

# ========== 步骤2: 检查条件分支 ==========
print("\n" + "=" * 60)
print("步骤2: 检查条件分支")
print("=" * 60)

if not llm_analysis_success:
    print("[FAIL] LLM分析失败，代码会提前返回meta_data")
    print("  → 不会执行状态转移")
    sys.exit(0)

print(f"[OK] LLM分析成功")
print(f"\n关键变量:")
print(f"  has_planning_required = {has_planning_required}")
print(f"  has_failure = {has_failure}")
print(f"  has_success = {has_success}")

# ========== 步骤3: 模拟条件判断 ==========
print("\n" + "=" * 60)
print("步骤3: 模拟条件判断")
print("=" * 60)

# Line 1308: if has_planning_required:
print(f"\n检查: if has_planning_required:")
if has_planning_required:
    print(f"  → TRUE: 会进入planning_required分支")
    print(f"  → 状态转移: implementation → planning")
    print(f"  → 不会进入has_success分支")
    sys.exit(0)
else:
    print(f"  → FALSE: 不进入")

# Line 1383: elif has_failure:
print(f"\n检查: elif has_failure:")
if has_failure:
    print(f"  → TRUE: 会进入has_failure分支")
    print(f"  → 可能是部分成功或完全失败")
    print(f"  → 不会进入has_success分支")
    sys.exit(0)
else:
    print(f"  → FALSE: 不进入")

# Line 1573: elif has_success:
print(f"\n检查: elif has_success:")
if has_success:
    print(f"  → TRUE: 会进入has_success分支")

    # Line 1575: 检查PARTIAL_SUCCESS_KEYWORDS
    PARTIAL_SUCCESS_KEYWORDS = [
        '部分', '有些', '一部分', '某些', '有的', '个别',
        '但是', '但', '不过', '然而', '可是', '只是', '就是',
        'but', 'however', 'though', 'yet', 'although',
        '还有', '还是', '仍然', '依然', '还在', '还没',
        '新问题', '新的问题', '另一个问题', '其他问题'
    ]

    has_partial_indicator = any(kw in user_input_lower for kw in PARTIAL_SUCCESS_KEYWORDS)

    print(f"\n  检查: has_partial_indicator = any(kw in user_input_lower for kw in PARTIAL_SUCCESS_KEYWORDS)")
    print(f"    → has_partial_indicator = {has_partial_indicator}")

    if has_partial_indicator:
        print(f"    → TRUE: 会进入部分成功分支（Line 1577）")
        print(f"    → 不会转移状态，保持implementation")
        # 匹配的关键词
        matched = [kw for kw in PARTIAL_SUCCESS_KEYWORDS if kw in user_input_lower]
        print(f"    → 匹配的关键词: {matched}")
    else:
        print(f"    → FALSE: 会进入完全成功分支（Line 1620）")
        print(f"    → 状态转移: implementation → finalization")
        print(f"    → result['occurred'] = True")
        print(f"    → ✅ 应该成功转移状态！")
else:
    print(f"  → FALSE: 不进入has_success分支")
    print(f"  → 会进入else分支（Line 1703，智能反馈检测）")
    print(f"  → 可能不会转移状态")

print("\n" + "=" * 60)
print("诊断完成")
print("=" * 60)
