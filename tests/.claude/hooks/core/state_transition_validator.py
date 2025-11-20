#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
状态转移验证器 - 确保状态机100%合法转移 (v25.0)

基于Hook状态机功能实现文档定义的状态转移表，提供强制验证机制。

核心功能:
1. 硬编码合法状态转移表
2. 转移前强制验证
3. 详细错误信息
4. 阻止非法转移

Author: NeteaseMod-Claude Workflow System
Date: 2025-11-19
"""

import sys
import io
from typing import Optional, Set, Dict, List

# 修复Windows编码问题（避免重复包装）
if sys.platform == 'win32':
    # 检查是否已经被包装过（避免重复包装导致I/O错误）
    if not isinstance(sys.stdout, io.TextIOWrapper):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        except (AttributeError, ValueError):
            pass  # 已经被包装或不支持
    if not isinstance(sys.stderr, io.TextIOWrapper):
        try:
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
        except (AttributeError, ValueError):
            pass  # 已经被包装或不支持


# ===== 异常类定义 =====

class StateTransitionError(Exception):
    """状态转移错误基类"""
    pass


class IllegalTransitionError(StateTransitionError):
    """非法状态转移错误"""
    def __init__(self, from_step: str, to_step: str, reason: str = ""):
        self.from_step = from_step
        self.to_step = to_step
        self.reason = reason
        message = u"非法状态转移: {} → {}".format(from_step, to_step)
        if reason:
            message += u" (原因: {})".format(reason)
        super().__init__(message)


class MissingCriticalFieldError(StateTransitionError):
    """缺少关键字段错误"""
    def __init__(self, field: str, transition: str = ""):
        self.field = field
        self.transition = transition
        message = u"缺少关键字段: {}".format(field)
        if transition:
            message += u" (转移: {})".format(transition)
        super().__init__(message)


# ===== 状态转移表 =====

# 四个合法状态
VALID_STATES: Set[str] = {
    'activation',
    'planning',
    'implementation',
    'finalization'
}

# 状态转移表（基于Hook状态机功能实现.md第379-387行）
VALID_TRANSITIONS: Dict[str, Set[str]] = {
    'activation': {
        'planning'  # 任务类型识别完成 → Planning
    },
    'planning': {
        'implementation',  # 专家审查通过/文档查阅完成 + 用户确认 → Implementation
        'planning'  # 允许在Planning阶段内循环（重新审查）
    },
    'implementation': {
        'finalization',    # 用户确认修复完成 → Finalization
        'planning',        # 用户要求重新设计 → 回退Planning
        'implementation'   # 用户请求继续/新一轮迭代 → 保持Implementation
    },
    'finalization': {
        # 终态，不允许转移到其他状态
    }
}

# 转移条件说明
TRANSITION_REQUIREMENTS: Dict[str, Dict] = {
    'activation->planning': {
        'description': '任务类型识别完成',
        'required_fields': []  # 自动推进，无需特殊字段
    },
    'planning->implementation': {
        'description': 'BUG修复：专家审查通过 + 用户确认；功能设计：查阅3文档 + 用户确认',
        'required_fields': [
            'steps.planning.user_confirmed',  # 必须为True
            'steps.planning.expert_review_completed'  # BUG修复时必须为True
        ]
    },
    'implementation->finalization': {
        'description': '用户确认修复完成（"都正确了"/"修复了"等）',
        'required_fields': [
            'steps.implementation.user_confirmed'  # 必须为True
        ]
    },
    'implementation->planning': {
        'description': '用户反馈需要重新设计方案（"根本原因没找到"等）',
        'required_fields': []  # 允许回退，无需特殊条件
    },
    'implementation->implementation': {
        'description': '用户请求继续修复或开始新迭代',
        'required_fields': []  # 自由循环
    },
    'planning->planning': {
        'description': 'Planning阶段内部循环（重新审查）',
        'required_fields': []
    }
}


# ===== 验证函数 =====

def validate_state_transition(
    from_step: str,
    to_step: str,
    strict: bool = True
) -> bool:
    """
    验证状态转移是否合法

    Args:
        from_step: 当前状态
        to_step: 目标状态
        strict: 严格模式（True时抛出异常，False时返回bool）

    Returns:
        bool: 转移合法返回True，非法返回False（仅strict=False时）

    Raises:
        IllegalTransitionError: 非法转移（仅strict=True时）
    """
    # 验证状态名称合法性
    if from_step not in VALID_STATES:
        error = u"源状态不合法: {}（合法状态: {}）".format(
            from_step, ', '.join(VALID_STATES)
        )
        if strict:
            raise IllegalTransitionError(from_step, to_step, error)
        return False

    if to_step not in VALID_STATES:
        error = u"目标状态不合法: {}（合法状态: {}）".format(
            to_step, ', '.join(VALID_STATES)
        )
        if strict:
            raise IllegalTransitionError(from_step, to_step, error)
        return False

    # 验证转移是否在允许列表中
    allowed_transitions = VALID_TRANSITIONS.get(from_step, set())

    if to_step not in allowed_transitions:
        error = u"不允许的转移。{} 仅允许转移到: {}".format(
            from_step,
            ', '.join(allowed_transitions) if allowed_transitions else '无（终态）'
        )
        if strict:
            raise IllegalTransitionError(from_step, to_step, error)
        return False

    return True


def validate_transition_requirements(
    from_step: str,
    to_step: str,
    meta_data: Dict,
    strict: bool = True
) -> bool:
    """
    验证转移条件是否满足（检查required_fields）

    Args:
        from_step: 当前状态
        to_step: 目标状态
        meta_data: task-meta.json数据
        strict: 严格模式（True时抛出异常，False时返回bool）

    Returns:
        bool: 条件满足返回True，不满足返回False（仅strict=False时）

    Raises:
        MissingCriticalFieldError: 缺少必需字段（仅strict=True时）
    """
    # 先验证转移本身是否合法
    if not validate_state_transition(from_step, to_step, strict=False):
        # 转移不合法，直接返回（已在validate_state_transition中处理）
        return False

    # 获取转移要求
    transition_key = u"{}->{}".format(from_step, to_step)
    requirements = TRANSITION_REQUIREMENTS.get(transition_key, {})
    required_fields = requirements.get('required_fields', [])

    # 检查每个必需字段
    for field_path in required_fields:
        if not _check_field_exists_and_true(meta_data, field_path):
            error = u"字段 {} 不存在或为False（转移要求: {}）".format(
                field_path,
                requirements.get('description', '无说明')
            )
            if strict:
                raise MissingCriticalFieldError(field_path, transition_key)
            return False

    return True


def get_allowed_transitions(current_step: str) -> Set[str]:
    """
    获取当前状态允许的目标状态

    Args:
        current_step: 当前状态

    Returns:
        Set[str]: 允许转移到的状态集合
    """
    if current_step not in VALID_STATES:
        sys.stderr.write(u"[WARN] 无效的当前状态: {}\n".format(current_step))
        return set()

    return VALID_TRANSITIONS.get(current_step, set())


def get_transition_description(from_step: str, to_step: str) -> str:
    """
    获取转移条件描述

    Args:
        from_step: 当前状态
        to_step: 目标状态

    Returns:
        str: 转移条件描述
    """
    transition_key = u"{}->{}".format(from_step, to_step)
    requirements = TRANSITION_REQUIREMENTS.get(transition_key, {})
    return requirements.get('description', u'未定义')


def is_terminal_state(state: str) -> bool:
    """
    判断是否为终态

    Args:
        state: 状态名称

    Returns:
        bool: 是终态返回True
    """
    return state == 'finalization'


# ===== 辅助函数 =====

def _check_field_exists_and_true(data: Dict, field_path: str) -> bool:
    """
    检查嵌套字段是否存在且为True

    Args:
        data: 数据字典
        field_path: 字段路径（如"steps.planning.user_confirmed"）

    Returns:
        bool: 字段存在且为True返回True
    """
    keys = field_path.split('.')
    current = data

    for key in keys:
        if not isinstance(current, dict):
            return False

        if key not in current:
            return False

        current = current[key]

    # 最终值必须为True
    return current is True


# ===== 便捷函数 =====

def safe_transition(
    from_step: str,
    to_step: str,
    meta_data: Optional[Dict] = None
) -> tuple:
    """
    安全的状态转移检查（不抛出异常）

    Args:
        from_step: 当前状态
        to_step: 目标状态
        meta_data: task-meta.json数据（可选，仅检查转移要求时需要）

    Returns:
        (bool, str): (是否允许, 错误信息)
    """
    try:
        # 验证转移合法性
        validate_state_transition(from_step, to_step, strict=True)

        # 如果提供了meta_data，验证转移条件
        if meta_data is not None:
            validate_transition_requirements(from_step, to_step, meta_data, strict=True)

        return (True, '')

    except StateTransitionError as e:
        return (False, str(e))


# ===== 测试代码 =====

if __name__ == '__main__':
    """
    测试代码

    运行: python state_transition_validator.py
    """
    print("=== 状态转移验证器测试 ===\n")

    # 测试用例
    test_cases = [
        # (from, to, 期望结果)
        ('activation', 'planning', True),
        ('planning', 'implementation', True),
        ('implementation', 'finalization', True),
        ('implementation', 'planning', True),  # 允许回退
        ('implementation', 'implementation', True),  # 允许循环
        ('finalization', 'planning', False),  # 终态不允许转移
        ('activation', 'finalization', False),  # 跳跃不允许
        ('planning', 'finalization', False),  # 跳跃不允许
        ('invalid_state', 'planning', False),  # 无效状态
    ]

    print("1. 基础转移验证:")
    for from_step, to_step, expected in test_cases:
        result = validate_state_transition(from_step, to_step, strict=False)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        print(u"   {} → {}: {} (期望: {}, 实际: {})".format(
            from_step, to_step, status, expected, result
        ))

    print(u"\n2. 获取允许的转移:")
    for state in VALID_STATES:
        allowed = get_allowed_transitions(state)
        print(u"   {}: {}".format(
            state,
            ', '.join(allowed) if allowed else '无（终态）'
        ))

    print(u"\n3. 转移条件描述:")
    for transition_key, requirements in TRANSITION_REQUIREMENTS.items():
        print(u"   {}: {}".format(
            transition_key,
            requirements['description']
        ))

    print(u"\n4. 条件验证测试:")
    # 模拟task-meta.json
    mock_meta = {
        'steps': {
            'planning': {
                'user_confirmed': True,
                'expert_review_completed': True
            },
            'implementation': {
                'user_confirmed': False  # 未确认
            }
        }
    }

    # planning → implementation（应该通过）
    try:
        validate_transition_requirements('planning', 'implementation', mock_meta, strict=True)
        print(u"   ✅ planning → implementation: 条件满足")
    except MissingCriticalFieldError as e:
        print(u"   ❌ planning → implementation: {}".format(e))

    # implementation → finalization（应该失败，因为user_confirmed=False）
    try:
        validate_transition_requirements('implementation', 'finalization', mock_meta, strict=True)
        print(u"   ❌ implementation → finalization: 应该失败但通过了")
    except MissingCriticalFieldError as e:
        print(u"   ✅ implementation → finalization: 正确拦截 - {}".format(e))

    print("\n=== 测试完成 ===")
