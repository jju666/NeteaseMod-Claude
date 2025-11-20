#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断Hook系统状态
"""
import sys
import os
import io

# 修复Windows编码问题
if sys.platform == 'win32':
    if not isinstance(sys.stdout, io.TextIOWrapper):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        except (AttributeError, ValueError):
            pass
    if not isinstance(sys.stderr, io.TextIOWrapper):
        try:
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
        except (AttributeError, ValueError):
            pass

# 添加hooks路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.claude', 'hooks'))

print("=" * 60)
print("Hook系统诊断")
print("=" * 60)

# 检查claude_semantic_analyzer
print("\n1. 检查claude_semantic_analyzer模块")
try:
    from core.claude_semantic_analyzer import ClaudeSemanticAnalyzer, analyze_user_intent, ANTHROPIC_AVAILABLE
    print("  [OK] claude_semantic_analyzer导入成功")
    print(f"  [OK] ANTHROPIC_AVAILABLE = {ANTHROPIC_AVAILABLE}")

    if ANTHROPIC_AVAILABLE:
        print("  [OK] anthropic SDK可用")

        # 检查API密钥
        import anthropic
        api_key = os.environ.get('ANTHROPIC_API_KEY') or os.environ.get('ANTHROPIC_AUTH_TOKEN')
        if api_key:
            print(f"  [OK] API密钥已配置 (长度: {len(api_key)})")
        else:
            print("  [FAIL] API密钥未配置")
    else:
        print("  [FAIL] anthropic SDK不可用")
except ImportError as e:
    print(f"  [FAIL] claude_semantic_analyzer导入失败: {e}")

# 检查state_transition_validator
print("\n2. 检查state_transition_validator模块")
try:
    from core.state_transition_validator import validate_state_transition
    print("  [OK] state_transition_validator导入成功")
except ImportError as e:
    print(f"  [FAIL] state_transition_validator导入失败: {e}")

# 检查user_prompt_handler
print("\n3. 检查user_prompt_handler模块")
try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.claude', 'hooks', 'orchestrator'))
    from user_prompt_handler import CLAUDE_ANALYZER_AVAILABLE, STATE_VALIDATOR_AVAILABLE
    print(f"  [OK] user_prompt_handler导入成功")
    print(f"  [OK] CLAUDE_ANALYZER_AVAILABLE = {CLAUDE_ANALYZER_AVAILABLE}")
    print(f"  [OK] STATE_VALIDATOR_AVAILABLE = {STATE_VALIDATOR_AVAILABLE}")
except ImportError as e:
    print(f"  [FAIL] user_prompt_handler导入失败: {e}")

# 测试LLM分析（Planning阶段实际prompt）
print("\n4. 测试Planning阶段LLM语义分析")
try:
    from core.claude_semantic_analyzer import get_analyzer
    import json

    test_input = "你可以继续了"
    print(f"  测试输入: '{test_input}'")

    # 使用Planning阶段的实际prompt
    planning_prompt = """你是一个任务状态分析专家。用户正在Planning（方案制定）阶段，请分析用户的反馈意图。

**当前任务上下文**:
- 当前阶段: planning
- 专家审查已完成: 是
- 文档查阅: 0/0

**用户反馈**: "{user_input}"

**请判断用户意图（只输出JSON，不要其他内容）**:

可选意图类型:
- agree: 用户同意当前方案，希望推进到Implementation阶段
- reject: 用户对方案有疑虑或不满意，希望调整方案
- restart: 用户完全否定方案，希望重新开始

**分析要点**:
1. "同意"、"可以"、"没问题"、"确认"、"好的"、"继续"、"可以继续"、"你可以继续了"、"开始吧"等表示agree
2. "不同意"、"有问题"、"需要调整"等表示reject
3. "重来"、"重新开始"、"完全不对"等表示restart
4. 注意转折词：如果有"但是"等转折，通常是reject而非agree

输出格式:
{{
  "intent": "意图类型(agree/reject/restart)",
  "confidence": 0.0-1.0,
  "reasoning": "一句话说明判断理由"
}}
""".format(user_input=test_input)

    analyzer = get_analyzer()
    client = analyzer.client

    print("  调用Claude API（使用Planning实际prompt）...")

    response = client.messages.create(
        model=analyzer.model,
        max_tokens=analyzer.max_tokens,
        timeout=analyzer.timeout_seconds,
        messages=[{"role": "user", "content": planning_prompt}]
    )

    response_text = response.content[0].text.strip()
    json_text = analyzer._extract_json(response_text)
    llm_result = json.loads(json_text)

    intent = llm_result.get('intent', 'unknown')
    confidence = llm_result.get('confidence', 0.0)
    reasoning = llm_result.get('reasoning', '')

    print(f"  [OK] Planning LLM分析完成")
    print(f"     - intent: {intent}")
    print(f"     - confidence: {confidence:.0%}")
    print(f"     - reasoning: {reasoning[:100]}")

    if intent == 'agree' and confidence >= 0.8:
        print(f"  [OK] '你可以继续了' 将被识别为agree，可触发Planning->Implementation转移")
    else:
        print(f"  [WARN] '你可以继续了' 可能无法触发状态转移")

except Exception as e:
    print(f"  [FAIL] Planning LLM分析失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("诊断完成")
print("=" * 60)
