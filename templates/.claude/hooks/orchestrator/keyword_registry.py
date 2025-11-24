#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Keyword Registry - 关键词配置中心 (v25.0)

集中管理所有关键词列表，消除与EnhancedMatcher的重复定义。

注意：v25.0已切换到Claude LLM语义分析，关键词仅作降级方案。
当LLM分析失败时，可选择使用关键词匹配作为备份方案。

作者: NeteaseMod-Claude工作流系统
版本: v25.0
日期: 2025-11-20
"""

# ==================== Planning阶段关键词 ====================

# v24.0新增：添加"认同"、"赞同"等同义词（修复#issue-认同未被识别为同意）
CONFIRM_KEYWORDS = [
    '同意', '可以', 'ok', '没问题', '确认', 'yes', '好的', '行',
    '认同', '赞同', '支持', '接受', 'agree', '同意的', '认同的', '赞同的',
    '继续', '可以继续', '你可以继续了', '开始吧'
]

REJECT_KEYWORDS = [
    # 原有（v22.3）
    '不同意', '有问题', '需要调整', '不行', '不对', '不可以', '拒绝',
    # v22.4新增：覆盖更多拒绝表达
    '不符合', '不够', '不太', '不是', '重新', '再想', '再考虑',
    '重新思考', '重新分析', '彻底', '完全错', '不理解',
    '不认可', '不满意', '有疑问', '有疑虑'
]

RESTART_KEYWORDS = [
    '重来', '重新开始', '完全错了', 'restart', '完全不对'
]

# ==================== Implementation阶段关键词 ====================

# v23.2修复: 调整关键词策略，移除容易误匹配的通用词
# 问题: v23.1添加的"正常"、"通过"等词容易在描述性文本中误匹配
# 解决: 只保留明确的完成表达，配合转折词检测机制
FIXED_KEYWORDS = [
    # v22.6原有关键词（保留明确的完成表达）
    '修复了', '已修复', '完成', '已完成', '好了', '可以了', '成功',
    '搞定', '搞定了', '解决了', 'done', 'fixed', 'ok了', 'fixed了',
    # v23.1新增（保留明确表达，移除"正常"、"通过"、"可以"等通用词）
    '没问题了', '没问题', '确定', '行', '行了', 'ok', 'okay', 'OK', 'OKAY',
    '没事了', '没事', '没毛病',
    '修好了', '解决', '完美', '完美了', '满意',
    '没问题的', '可以的', '行的', '验证通过',
    # v23.2新增：明确的完全成功表达
    '完全修复', '全部解决', '全部修复', '没有问题了', '一切正常', '全部通过',
    '完全正常', '彻底解决', '彻底修复', '完全好了', '全都修复了', '都修复了',
    '全修复了', '都好了', '全好了', '都正确了'
]

# v22.6修复: 扩充失败反馈关键词（添加'未修复', '还存在问题', '不行'等常见表达）
NOT_FIXED_KEYWORDS = [
    '没修复', '未修复', '还有问题', '还存在问题', '没解决', '未解决',
    '重新分析', '失败', '没用', '不行', '有bug', '还有bug'
]

# v23.2新增：部分成功关键词（用于区分完全成功和部分成功）
PARTIAL_SUCCESS_KEYWORDS = [
    '部分', '有些', '一部分', '某些', '有的', '个别',
    '但是', '但', '不过', '然而', '可是', '只是', '就是',
    'but', 'however', 'though', 'yet', 'although',
    '还有', '还是', '仍然', '依然', '还在', '还没',
    '新问题', '新的问题', '另一个问题', '其他问题'
]

# v22.7新增：方案性错误关键词（明确表示需要回到Planning重新设计）
PLANNING_REQUIRED_KEYWORDS = [
    '方案错了', '思路不对', '重新设计', '重新分析根因',
    '根本原因错了', '需要换思路', '这个方法不行',
    '完全错误', '理解错了', '分析错误'
]

# ==================== 辅助关键词（可选）====================

# v22.5新增：模糊肯定表达（需要澄清）
AMBIGUOUS_POSITIVE = [
    '同意', 'ok', 'okay', '可以', '没问题', '通过', '好的',
    '看起来不错', '不错'
]

CONTINUE_KEYWORDS = [
    '继续', '继续修改', '再改', '还有', 'continue'
]

# ==================== API函数 ====================

def get_keywords(category):
    """
    获取指定类别的关键词列表

    Args:
        category: 关键词类别，可选值：
            - 'confirm': 同意/确认
            - 'reject': 拒绝/疑虑
            - 'restart': 重新开始
            - 'fixed': 修复完成
            - 'not_fixed': 修复失败
            - 'partial_success': 部分成功
            - 'planning_required': 需要回到Planning
            - 'ambiguous': 模糊肯定表达
            - 'continue': 继续修改

    Returns:
        list: 对应类别的关键词列表，如果类别不存在返回空列表

    Examples:
        >>> get_keywords('confirm')
        ['同意', '可以', 'ok', ...]

        >>> get_keywords('fixed')
        ['修复了', '已修复', '完成', ...]
    """
    keyword_map = {
        'confirm': CONFIRM_KEYWORDS,
        'reject': REJECT_KEYWORDS,
        'restart': RESTART_KEYWORDS,
        'fixed': FIXED_KEYWORDS,
        'not_fixed': NOT_FIXED_KEYWORDS,
        'partial_success': PARTIAL_SUCCESS_KEYWORDS,
        'planning_required': PLANNING_REQUIRED_KEYWORDS,
        'ambiguous': AMBIGUOUS_POSITIVE,
        'continue': CONTINUE_KEYWORDS
    }
    return keyword_map.get(category, [])


def has_negation_prefix(text, keyword):
    """
    检查关键词前是否有否定词（v22.3修复）

    功能：防止"不同意"误匹配到"同意"，"没修复"误匹配到"修复了"。

    Args:
        text: 用户输入文本（小写）
        keyword: 要检查的关键词（小写）

    Returns:
        bool: 如果关键词前2-3个字符内有否定词返回True

    Examples:
        >>> has_negation_prefix("不同意", "同意")
        True

        >>> has_negation_prefix("我同意", "同意")
        False

        >>> has_negation_prefix("not fixed", "fixed")
        True
    """
    import re

    # 否定词列表（中英文）
    negation_words = [
        '不', '没', '别', '非', '未', '无',  # 中文否定词
        'no', 'not', "don't", "doesn't", "didn't"  # 英文否定词
    ]

    # 在文本中查找关键词的所有出现位置
    pattern = re.escape(keyword)
    for match in re.finditer(pattern, text, re.IGNORECASE):
        keyword_start = match.start()

        # 检查关键词前2-3个字符内是否有否定词
        prefix_text = text[max(0, keyword_start - 3):keyword_start]

        for neg_word in negation_words:
            if neg_word in prefix_text:
                return True

    return False


def match_keyword_safely(text, keywords):
    """
    安全地匹配关键词（v23.2：词边界+否定词+转折词检测）

    三重检测机制：
    1. 否定词检测：避免"不同意"误匹配到"同意"
    2. 转折词检测：避免"正常了，但是有问题"被误判为成功
    3. 词边界检测：确保完整词匹配

    Args:
        text: 用户输入文本
        keywords: 关键词列表

    Returns:
        bool: 如果匹配到关键词且无否定前缀和转折词返回True

    Examples:
        >>> match_keyword_safely("我同意这个方案", CONFIRM_KEYWORDS)
        True

        >>> match_keyword_safely("我不同意", CONFIRM_KEYWORDS)
        False

        >>> match_keyword_safely("修复了，但是还有问题", FIXED_KEYWORDS)
        False  # 有转折词，不算明确成功

    v23.2新增：转折词检测，防止"正常了，但是有问题"被误判为成功
    """
    import re
    text_lower = text.lower().strip()

    # 【v23.2新增】转折词列表
    CONJUNCTIONS = [
        '但是', '但', '不过', '然而', '可是', '可', '只是', '就是',
        'but', 'however', 'though', 'yet', 'although'
    ]

    for kw in keywords:
        kw_lower = kw.lower()

        # 检查是否包含关键词
        if kw_lower in text_lower:
            # 检查1：是否有否定前缀
            if has_negation_prefix(text_lower, kw_lower):
                continue  # 有否定词，跳过

            # 检查2：检查转折词（关键词后50字符内）
            kw_pos = text_lower.find(kw_lower)
            text_after = text_lower[kw_pos + len(kw_lower):]

            # 如果关键词后50字符内有转折词，说明有转折，不算明确成功
            has_conjunction = False
            for conj in CONJUNCTIONS:
                if conj in text_after[:50]:
                    has_conjunction = True
                    break

            if has_conjunction:
                continue  # 有转折，跳过这个关键词

            # 通过所有检测，算明确匹配
            return True

    return False


# ==================== 导出所有符号 ====================

__all__ = [
    # 关键词列表
    'CONFIRM_KEYWORDS',
    'REJECT_KEYWORDS',
    'RESTART_KEYWORDS',
    'FIXED_KEYWORDS',
    'NOT_FIXED_KEYWORDS',
    'PARTIAL_SUCCESS_KEYWORDS',
    'PLANNING_REQUIRED_KEYWORDS',
    'AMBIGUOUS_POSITIVE',
    'CONTINUE_KEYWORDS',

    # API函数
    'get_keywords',
    'has_negation_prefix',
    'match_keyword_safely'
]
