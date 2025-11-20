#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Implementation阶段LLM语义识别 - "我测试没问题了"
"""
import sys
import os
import io

# 修复Windows编码
if sys.platform == 'win32':
    if not isinstance(sys.stdout, io.TextIOWrapper):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        except (AttributeError, ValueError):
            pass

# 添加hooks路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.claude', 'hooks'))

from core.claude_semantic_analyzer import analyze_user_intent

print("=" * 60)
print("测试Implementation阶段LLM识别")
print("=" * 60)

# 测试输入
test_inputs = [
    "我测试没问题了",
    "都正确了",
    "修复了",
    "全部搞定",
    "测试通过了"
]

context = {
    'current_step': 'implementation',
    'code_changes': 3,
    'iteration': 1
}

for test_input in test_inputs:
    print(f"\n测试输入: '{test_input}'")

    try:
        result = analyze_user_intent(test_input, context)

        intent = result.get('intent', 'unknown')
        confidence = result.get('confidence', 0)
        reasoning = result.get('reasoning', '')

        print(f"  intent: {intent}")
        print(f"  confidence: {confidence:.0%}")
        print(f"  reasoning: {reasoning[:80]}")

        # 判断是否会触发finalization转移
        if intent == 'complete_success' and confidence >= 0.8:
            print(f"  ✅ 会触发 Implementation → Finalization")
        else:
            print(f"  ❌ 不会触发状态转移 (intent={intent}, conf={confidence:.0%})")

    except Exception as e:
        print(f"  ❌ 分析失败: {e}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
