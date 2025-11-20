#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
增强型关键词匹配系统 (v24.2)

特性:
1. 扩展关键词库 - 覆盖更多自然语言变体
2. 模糊匹配 - 基于编辑距离的相似度算法
3. 语义分组 - 关键词分组为语义簇
4. 上下文感知 - 增强的否定词和转折词检测
5. 评分系统 - 计算整体语义倾向
"""

import re
from typing import List, Tuple, Dict

# ========== 扩展关键词库 ==========

# 完全成功表达 (完全修复/解决)
COMPLETE_SUCCESS_KEYWORDS = {
    # 原有核心词
    '修复了', '已修复', '完成', '已完成', '好了', '可以了', '成功', '搞定', '搞定了', '解决了',
    'done', 'fixed', 'ok了', 'fixed了',

    # 【v24.2扩展】常见口语变体
    '弄好了', '弄完了', '修好了', '修好啦', '搞好了', '搞好啦', '整好了', '整好啦',
    '做好了', '做完了', '做好啦', '做完啦', '改好了', '改完了', '改好啦', '改完啦',
    '搞定啦', '搞掂了', '搞掂啦', '弄掂了', '弄掂啦',

    # 【v24.2扩展】明确的完成表达
    '没问题了', '没问题', '没毛病', '没事了', '没事', '没啥问题', '没什么问题',
    '都好了', '全好了', '全修复了', '都修复了', '全部修复', '全部解决', '全部搞定',
    '完全修复', '完全解决', '完全搞定', '完全好了', '完全没问题',
    '彻底解决', '彻底修复', '彻底搞定',

    # 【v24.2扩展】确认和肯定
    '可以的', '行的', '行了', '行', '中', '中了', '得了', '成了',
    'ok', 'okay', 'OK', 'OKAY', '验证通过', '测试通过', '通过了',
    '满意', '完美', '完美了', '非常好', '很好',

    # 【v24.2扩展】"没有X"模式
    '没有问题', '没有bug', '没有错误', '没有异常', '没有故障',
    '不存在问题', '不存在bug',

    # 【v24.2扩展】"一切X"模式
    '一切正常', '一切ok', '一切都好', '一切都行',
    '全部正常', '完全正常', '都正常',

    # 【v24.3修复】"正确"相关表达
    '都正确了', '全部正确', '完全正确', '正确了',
    '都对了', '全对了', '没错了', '对了',
}

# 部分成功/继续修改 (还有问题，但部分解决)
PARTIAL_SUCCESS_KEYWORDS = {
    '部分', '有些', '一部分', '某些', '有的', '个别',
    '部分修复', '部分解决', '解决了一部分', '修复了一部分',
    '有些好了', '有的好了',
}

# 失败/未修复
FAILURE_KEYWORDS = {
    '没修复', '未修复', '还有问题', '还存在问题', '没解决', '未解决',
    '失败', '没用', '不行', '有bug', '还有bug', '还是有问题',

    # 【v24.2扩展】
    '没搞定', '没弄好', '没修好', '没改好', '没做好',
    '还是不行', '还是不对', '还是有bug', '还是失败',
    '依然有问题', '仍然有问题', '依旧有问题',
    '新问题', '新的问题', '另一个问题', '其他问题', '别的问题',
}

# 转折词 (表示反转/但是)
CONJUNCTION_WORDS = {
    '但是', '但', '不过', '然而', '可是', '可', '只是', '就是', '却',
    '可惜', '遗憾', '不幸', '可惜的是', '遗憾的是',
    'but', 'however', 'though', 'yet', 'although', 'unfortunately',

    # 【v24.2扩展】更多转折表达
    '只不过', '然而', '话说回来', '说回来', '问题是',
    '不足的是', '问题在于', '缺陷是', '缺点是',
}

# 后续问题词 (表示有新问题)
FOLLOWUP_ISSUE_WORDS = {
    '还有', '还是', '仍然', '依然', '还在', '还没', '依旧', '仍旧',
    '又', '又出现', '又发现', '新增', '新的', '额外',
    '另外', '此外', '除此之外',
}

# 否定词前缀
NEGATION_PREFIXES = {
    '不', '没', '未', '无', '非', '别', '勿', '莫',
    'not', 'no', "don't", "didn't", "doesn't", "cannot", "can't",
}

# 方案性错误 (需要重新设计)
PLANNING_ERROR_KEYWORDS = {
    '方案错了', '思路不对', '重新设计', '重新分析根因',
    '根本原因错了', '需要换思路', '这个方法不行',
    '完全错误', '理解错了', '分析错误', '方向错了',

    # 【v24.2扩展】
    '思路错了', '路线不对', '方向不对', '根本不对',
    '完全偏了', '偏离了', '走错了', '南辕北辙',
}


# ========== 语义分组 ==========

class SemanticGroup:
    """语义分组 - 将相似含义的关键词归为一组"""

    # 完成类动词组
    COMPLETION_VERBS = {
        '修复', '解决', '完成', '搞定', '弄好', '修好', '做好', '改好', '整好', '搞掂', '弄掂',
        'fixed', 'done', 'solved', 'completed', 'finished',
    }

    # 状态形容词组
    STATUS_ADJECTIVES = {
        '好', '正常', '完美', '满意', '行', '可以', '中', 'ok', 'okay', 'fine', 'good',
    }

    # 无问题表达组
    NO_PROBLEM_PHRASES = {
        '没问题', '没事', '没毛病', '没啥问题', '没什么问题',
        '不存在问题', '没有问题', '没有bug', '没有错误',
        'no problem', 'no issue', 'no bug',
    }


# ========== 增强匹配函数 ==========

def calculate_edit_distance(s1: str, s2: str) -> int:
    """计算Levenshtein编辑距离"""
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i-1] == s2[j-1]:
                dp[i][j] = dp[i-1][j-1]
            else:
                dp[i][j] = min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1]) + 1

    return dp[m][n]


def fuzzy_match_keyword(text: str, keyword: str, threshold: float = 0.85) -> bool:
    """
    模糊匹配关键词

    Args:
        text: 输入文本
        keyword: 关键词
        threshold: 相似度阈值 (0-1)

    Returns:
        bool: 是否匹配
    """
    text_lower = text.lower().strip()
    kw_lower = keyword.lower().strip()

    # 1. 精确匹配
    if kw_lower in text_lower:
        return True

    # 2. 模糊匹配 - 对短词(<=4字符)进行编辑距离匹配
    if len(kw_lower) <= 4:
        # 扫描文本中所有相同长度的子串
        for i in range(len(text_lower) - len(kw_lower) + 1):
            substr = text_lower[i:i+len(kw_lower)]
            distance = calculate_edit_distance(substr, kw_lower)
            similarity = 1 - (distance / len(kw_lower))
            if similarity >= threshold:
                return True

    return False


def has_negation_prefix(text: str, keyword: str) -> bool:
    """
    检查关键词前是否有否定词

    Args:
        text: 输入文本
        keyword: 关键词

    Returns:
        bool: 是否有否定前缀
    """
    text_lower = text.lower()
    kw_pos = text_lower.find(keyword.lower())

    if kw_pos == -1:
        return False

    # 检查前5个字符
    prefix = text_lower[max(0, kw_pos-5):kw_pos]

    for neg in NEGATION_PREFIXES:
        if neg in prefix:
            return True

    return False


def detect_conjunction(text: str, keyword: str, window: int = 80) -> bool:
    """
    检测关键词后是否有转折词

    Args:
        text: 输入文本
        keyword: 关键词
        window: 检查窗口大小（字符数）

    Returns:
        bool: 是否有转折词
    """
    text_lower = text.lower()
    kw_pos = text_lower.find(keyword.lower())

    if kw_pos == -1:
        return False

    # 检查关键词后的窗口
    text_after = text_lower[kw_pos + len(keyword):kw_pos + len(keyword) + window]

    for conj in CONJUNCTION_WORDS:
        if conj in text_after:
            return True

    return False


def detect_followup_issues(text: str, keyword: str, window: int = 80) -> bool:
    """
    检测关键词后是否有后续问题表达

    Args:
        text: 输入文本
        keyword: 关键词
        window: 检查窗口大小

    Returns:
        bool: 是否有后续问题
    """
    text_lower = text.lower()
    kw_pos = text_lower.find(keyword.lower())

    if kw_pos == -1:
        return False

    text_after = text_lower[kw_pos + len(keyword):kw_pos + len(keyword) + window]

    # 检查后续问题词
    for word in FOLLOWUP_ISSUE_WORDS:
        if word in text_after:
            # 进一步检查是否提到问题/bug/错误等
            if any(issue in text_after for issue in ['问题', 'bug', '错误', '异常', '故障', '不行', '失败']):
                return True

    return False


def calculate_semantic_score(text: str) -> Dict[str, float]:
    """
    计算文本的语义倾向评分

    Returns:
        Dict[str, float]: {
            'complete_success': 完全成功分数 (0-1),
            'partial_success': 部分成功分数 (0-1),
            'failure': 失败分数 (0-1),
            'planning_error': 方案错误分数 (0-1),
        }
    """
    text_lower = text.lower().strip()

    scores = {
        'complete_success': 0.0,
        'partial_success': 0.0,
        'failure': 0.0,
        'planning_error': 0.0,
    }

    # 计数器
    complete_matches = 0
    partial_matches = 0
    failure_matches = 0
    planning_error_matches = 0

    # 扫描完全成功关键词
    for kw in COMPLETE_SUCCESS_KEYWORDS:
        if fuzzy_match_keyword(text, kw):
            # 检查否定和转折
            if not has_negation_prefix(text, kw) and \
               not detect_conjunction(text, kw) and \
               not detect_followup_issues(text, kw):
                complete_matches += 1

    # 扫描部分成功关键词
    for kw in PARTIAL_SUCCESS_KEYWORDS:
        if fuzzy_match_keyword(text, kw):
            partial_matches += 1

    # 扫描失败关键词
    for kw in FAILURE_KEYWORDS:
        if fuzzy_match_keyword(text, kw):
            failure_matches += 1

    # 扫描方案错误关键词
    for kw in PLANNING_ERROR_KEYWORDS:
        if fuzzy_match_keyword(text, kw):
            planning_error_matches += 1

    # 归一化评分
    total_matches = complete_matches + partial_matches + failure_matches + planning_error_matches

    if total_matches > 0:
        scores['complete_success'] = complete_matches / total_matches
        scores['partial_success'] = partial_matches / total_matches
        scores['failure'] = failure_matches / total_matches
        scores['planning_error'] = planning_error_matches / total_matches

    # 【v24.2增强】考虑上下文权重
    # 如果有明确的转折词或后续问题，降低成功分数
    if any(conj in text_lower for conj in CONJUNCTION_WORDS):
        scores['complete_success'] *= 0.5

    if any(word in text_lower for word in FOLLOWUP_ISSUE_WORDS):
        if any(issue in text_lower for issue in ['问题', 'bug', '错误']):
            scores['complete_success'] *= 0.3
            scores['failure'] = max(scores['failure'], 0.6)

    return scores


def match_with_confidence(text: str, intent: str) -> Tuple[bool, float]:
    """
    匹配并返回置信度

    Args:
        text: 输入文本
        intent: 意图类型 ('complete_success' | 'partial_success' | 'failure' | 'planning_error')

    Returns:
        Tuple[bool, float]: (是否匹配, 置信度)
    """
    scores = calculate_semantic_score(text)
    score = scores.get(intent, 0.0)

    # 置信度阈值
    CONFIDENCE_THRESHOLD = 0.6

    matched = score >= CONFIDENCE_THRESHOLD

    return matched, score


# ========== 兼容性接口 ==========

def match_keyword_safely_enhanced(text: str, keywords: set) -> bool:
    """
    增强版关键词匹配（兼容原有接口）

    Args:
        text: 输入文本
        keywords: 关键词集合

    Returns:
        bool: 是否匹配
    """
    text_lower = text.lower().strip()

    for kw in keywords:
        if fuzzy_match_keyword(text, kw):
            # 检查否定和转折
            if not has_negation_prefix(text, kw) and \
               not detect_conjunction(text, kw) and \
               not detect_followup_issues(text, kw):
                return True

    return False


# ========== 测试接口 ==========

def analyze_user_feedback(text: str) -> Dict:
    """
    分析用户反馈并返回详细结果

    Args:
        text: 用户输入文本

    Returns:
        Dict: {
            'intent': 主要意图,
            'confidence': 置信度,
            'scores': 所有分数,
            'recommendation': 推荐的状态转移
        }
    """
    scores = calculate_semantic_score(text)

    # 找出最高分数的意图
    max_intent = max(scores.items(), key=lambda x: x[1])
    intent, confidence = max_intent

    # 推荐状态转移
    recommendation = 'unknown'
    if intent == 'complete_success' and confidence >= 0.6:
        recommendation = 'transition_to_finalization'
    elif intent == 'partial_success' or (intent == 'failure' and confidence < 0.7):
        recommendation = 'continue_implementation'
    elif intent == 'failure' and confidence >= 0.7:
        recommendation = 'continue_implementation'
    elif intent == 'planning_error' and confidence >= 0.6:
        recommendation = 'back_to_planning'

    return {
        'intent': intent,
        'confidence': confidence,
        'scores': scores,
        'recommendation': recommendation,
        'text_analyzed': text,
    }


if __name__ == '__main__':
    # 测试用例
    test_cases = [
        "已修复",
        "搞定了",
        "弄好了",
        "修复了，但是还有新问题",
        "部分修复了",
        "还有问题",
        "方案错了，需要重新设计",
        "完全搞定，没问题了",
        "修好啦，测试通过",
        "还是不行，依然有bug",
    ]

    print("=" * 60)
    print("增强型关键词匹配系统测试")
    print("=" * 60)

    for text in test_cases:
        result = analyze_user_feedback(text)
        print(f"\n输入: {text}")
        print(f"意图: {result['intent']} (置信度: {result['confidence']:.2f})")
        print(f"推荐: {result['recommendation']}")
        print(f"详细分数: {result['scores']}")
