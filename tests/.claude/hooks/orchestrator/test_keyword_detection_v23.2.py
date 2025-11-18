#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试脚本：验证v23.2关键词检测修复

测试内容：
1. 转折词检测：防止"正常了，但是有问题"被误判为成功
2. 完全成功检测：确保明确的成功表达能被识别
3. 部分成功检测：识别包含成功+转折的反馈
"""

import sys
import os

# 添加hooks目录到Python路径
HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HOOK_DIR)

# 导入需要测试的函数
from user_prompt_handler import match_keyword_safely

# 定义测试用的关键词列表（复制自user_prompt_handler.py）
FIXED_KEYWORDS = [
    '修复了', '已修复', '完成', '已完成', '好了', '可以了', '成功', '搞定', '搞定了', '解决了',
    'done', 'fixed', 'ok了', 'fixed了',
    '没问题了', '没问题', '确定', '行', '行了', 'ok', 'okay', 'OK', 'OKAY',
    '没事了', '没事', '没毛病',
    '修好了', '解决', '完美', '完美了', '满意',
    '没问题的', '可以的', '行的', '验证通过',
    '完全修复', '全部解决', '全部修复', '没有问题了', '一切正常', '全部通过',
    '完全正常', '彻底解决', '彻底修复', '完全好了', '全都修复了', '都修复了',
    '全修复了', '都好了', '全好了'
]

PARTIAL_SUCCESS_KEYWORDS = [
    '部分', '有些', '一部分', '某些', '有的', '个别',
    '但是', '但', '不过', '然而', '可是', '只是', '就是',
    'but', 'however', 'though', 'yet', 'although',
    '还有', '还是', '仍然', '依然', '还在', '还没',
    '新问题', '新的问题', '另一个问题', '其他问题'
]

def test_conjunction_detection():
    """测试转折词检测"""
    print("=" * 60)
    print("测试1：转折词检测（防止误判）")
    print("=" * 60)

    test_cases = [
        {
            'input': '测试结果反馈，确实正常进入运行状态了，但是全部玩家都没有进入到对局地图内。',
            'expected': False,  # 不应该被识别为成功（有转折）
            'reason': '包含"正常"但有转折词"但是"'
        },
        {
            'input': '修复了状态机问题，不过玩家传送还有bug',
            'expected': False,
            'reason': '包含"修复了"但有转折词"不过"'
        },
        {
            'input': '成功启动了，however there is a crash',
            'expected': False,
            'reason': '包含"成功"但有英文转折词"however"'
        },
        {
            'input': '状态机正常工作了，只是玩家没传送',
            'expected': False,
            'reason': '包含"正常"但有转折词"只是"'
        }
    ]

    passed = 0
    failed = 0

    for case in test_cases:
        result = match_keyword_safely(case['input'], FIXED_KEYWORDS)
        status = "✅ PASS" if result == case['expected'] else "❌ FAIL"

        if result == case['expected']:
            passed += 1
        else:
            failed += 1

        print(f"\n{status}")
        print(f"输入: {case['input']}")
        print(f"期望: {case['expected']} (不识别为成功)")
        print(f"结果: {result}")
        print(f"原因: {case['reason']}")

    print(f"\n测试1总结: {passed}个通过, {failed}个失败")
    return failed == 0

def test_complete_success_detection():
    """测试完全成功检测"""
    print("\n" + "=" * 60)
    print("测试2：完全成功检测（确保正常识别）")
    print("=" * 60)

    test_cases = [
        {
            'input': '完全修复了，所有问题都解决了',
            'expected': True,
            'reason': '明确的完全成功表达'
        },
        {
            'input': '全部修复了，测试通过',
            'expected': True,
            'reason': '明确的完全成功表达'
        },
        {
            'input': '修复了，测试通过，一切正常',
            'expected': True,
            'reason': '明确的成功表达，无转折词'
        },
        {
            'input': '都修复了，验证通过',
            'expected': True,
            'reason': '明确的完全成功表达'
        }
    ]

    passed = 0
    failed = 0

    for case in test_cases:
        result = match_keyword_safely(case['input'], FIXED_KEYWORDS)
        status = "✅ PASS" if result == case['expected'] else "❌ FAIL"

        if result == case['expected']:
            passed += 1
        else:
            failed += 1

        print(f"\n{status}")
        print(f"输入: {case['input']}")
        print(f"期望: {case['expected']} (识别为成功)")
        print(f"结果: {result}")
        print(f"原因: {case['reason']}")

    print(f"\n测试2总结: {passed}个通过, {failed}个失败")
    return failed == 0

def test_partial_success_detection():
    """测试部分成功检测"""
    print("\n" + "=" * 60)
    print("测试3：部分成功检测（组合检测）")
    print("=" * 60)

    test_cases = [
        {
            'input': '测试结果反馈，确实正常进入运行状态了，但是全部玩家都没有进入到对局地图内。',
            'has_success': False,  # 强转折词"但是"会阻止成功识别
            'has_partial': True,   # 有部分成功指示词
            'reason': '包含成功词但有强转折词"但是"，不识别为成功；有"但是"，识别为部分成功'
        },
        {
            'input': '修复了A问题，还有B问题',
            'has_success': True,   # 匹配"修复了"，没有强转折词
            'has_partial': True,   # 有弱指示词"还有"
            'reason': '匹配"修复了"（无强转折词），有"还有"→ 组合判断为部分成功'
        },
        {
            'input': '部分修复了，还在调试',
            'has_success': True,   # 匹配"修复了"，没有强转折词
            'has_partial': True,   # 有弱指示词"部分"、"还在"
            'reason': '匹配"修复了"（无强转折词），有"部分"、"还在"→ 组合判断为部分成功'
        },
        {
            'input': '完全修复了，测试通过',
            'has_success': True,   # 匹配"修复了"、"完全修复"
            'has_partial': False,  # 无部分成功指示词
            'reason': '匹配成功关键词，无转折词和部分成功指示词 → 完全成功'
        }
    ]

    passed = 0
    failed = 0

    for case in test_cases:
        has_success = match_keyword_safely(case['input'], FIXED_KEYWORDS)
        input_lower = case['input'].lower()
        has_partial = any(kw in input_lower for kw in PARTIAL_SUCCESS_KEYWORDS)

        success_match = (has_success == case['has_success'])
        partial_match = (has_partial == case['has_partial'])
        all_match = success_match and partial_match

        status = "✅ PASS" if all_match else "❌ FAIL"

        if all_match:
            passed += 1
        else:
            failed += 1

        print(f"\n{status}")
        print(f"输入: {case['input']}")
        print(f"期望: has_success={case['has_success']}, has_partial={case['has_partial']}")
        print(f"结果: has_success={has_success}, has_partial={has_partial}")
        print(f"原因: {case['reason']}")

    print(f"\n测试3总结: {passed}个通过, {failed}个失败")
    return failed == 0

def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("开始测试 v23.2 关键词检测修复")
    print("=" * 60)

    test1_passed = test_conjunction_detection()
    test2_passed = test_complete_success_detection()
    test3_passed = test_partial_success_detection()

    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"测试1（转折词检测）: {'✅ PASS' if test1_passed else '❌ FAIL'}")
    print(f"测试2（完全成功检测）: {'✅ PASS' if test2_passed else '❌ FAIL'}")
    print(f"测试3（部分成功检测）: {'✅ PASS' if test3_passed else '❌ FAIL'}")

    if test1_passed and test2_passed and test3_passed:
        print("\n🎉 所有测试通过！v23.2修复成功！")
        return 0
    else:
        print("\n⚠️ 部分测试失败，需要进一步调试")
        return 1

if __name__ == '__main__':
    sys.exit(main())
