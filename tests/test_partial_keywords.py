#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试"我测试没问题了"是否会被PARTIAL_SUCCESS_KEYWORDS误判
"""
import sys
import io

# 修复Windows编码
if sys.platform == 'win32':
    if not isinstance(sys.stdout, io.TextIOWrapper):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        except (AttributeError, ValueError):
            pass

PARTIAL_SUCCESS_KEYWORDS = [
    '部分', '有些', '一部分', '某些', '有的', '个别',
    '但是', '但', '不过', '然而', '可是', '只是', '就是',
    'but', 'however', 'though', 'yet', 'although',
    '还有', '还是', '仍然', '依然', '还在', '还没',
    '新问题', '新的问题', '另一个问题', '其他问题'
]

test_inputs = [
    "我测试没问题了",
    "测试没问题了",
    "没问题了",
    "全部修复了",
    "都正确了"
]

print("=" * 60)
print("测试PARTIAL_SUCCESS_KEYWORDS误判")
print("=" * 60)

for test_input in test_inputs:
    user_input_lower = test_input.lower()

    # 模拟Hook中的检查逻辑
    has_partial_indicator = any(kw in user_input_lower for kw in PARTIAL_SUCCESS_KEYWORDS)

    print(f"\n输入: '{test_input}'")
    print(f"  小写后: '{user_input_lower}'")
    print(f"  has_partial_indicator: {has_partial_indicator}")

    if has_partial_indicator:
        # 找出匹配的关键词
        matched = [kw for kw in PARTIAL_SUCCESS_KEYWORDS if kw in user_input_lower]
        print(f"  ❌ 会被误判为部分成功！")
        print(f"  匹配的关键词: {matched}")
    else:
        print(f"  ✅ 不会被误判，可以转移到finalization")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
