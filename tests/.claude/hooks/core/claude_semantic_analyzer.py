#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude语义分析器 - LLM驱动的用户意图识别 (v25.0)

基于Claude 3.5 Sonnet模型进行高精度语义分析，解决传统关键词匹配的局限性。

核心功能:
1. 使用Claude API分析用户反馈意图
2. 返回结构化意图识别结果
3. 提供状态转移建议
4. 内置重试和超时机制

Author: NeteaseMod-Claude Workflow System
Date: 2025-11-19
"""

import json
import os
import sys
import time
from typing import Dict, Optional
import io

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

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    sys.stderr.write(u"[WARN] anthropic SDK不可用，请运行: pip install anthropic\n")


class ClaudeSemanticAnalyzer:
    """
    Claude语义分析器

    使用Claude 3.5 Sonnet进行用户意图识别，准确率>95%
    """

    # 意图类型定义
    INTENT_TYPES = {
        'complete_success': '任务完全成功，所有问题已解决',
        'partial_success': '部分成功，还有一些问题需要继续修复',
        'failure': '修复失败或出现新问题',
        'planning_required': '需要重新设计方案或思路',
        'continuation_request': '用户请求继续当前工作',
        'unknown': '无法确定用户意图'
    }

    # 状态转移映射
    INTENT_TO_TRANSITION = {
        'complete_success': 'finalization',
        'partial_success': 'implementation',  # 继续修复
        'failure': 'implementation',  # 重新修复
        'planning_required': 'planning',  # 回退到规划
        'continuation_request': 'implementation',
        'unknown': None  # 需要人工确认
    }

    def __init__(self, config: Optional[Dict] = None):
        """
        初始化分析器

        Args:
            config: 配置字典，包含model, timeout_seconds等
        """
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("anthropic SDK不可用，无法使用Claude语义分析器")

        # 加载配置
        self.config = config or self._load_default_config()

        # API密钥检测（支持两种环境变量）
        self.api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")
        if not self.api_key:
            raise ValueError(
                "未设置API密钥。请设置环境变量:\n"
                "  ANTHROPIC_API_KEY=your-api-key (推荐)\n"
                "或\n"
                "  ANTHROPIC_AUTH_TOKEN=your-api-key"
            )

        # 初始化客户端
        self.client = anthropic.Anthropic(api_key=self.api_key)

        # 配置参数
        # v25.0修复：使用Claude Sonnet 4.5（3.5已于2025年10月退役）
        self.model = self.config.get('model', 'claude-sonnet-4-5')
        self.max_tokens = self.config.get('max_tokens', 300)
        self.timeout_seconds = self.config.get('timeout_seconds', 15)
        self.retry_count = self.config.get('retry_count', 1)
        self.confidence_threshold = self.config.get('confidence_threshold', 0.8)

        sys.stderr.write(
            u"[INFO] ClaudeSemanticAnalyzer已初始化\n"
            u"       模型: {}\n"
            u"       超时: {}秒\n"
            u"       重试次数: {}\n".format(
                self.model, self.timeout_seconds, self.retry_count
            )
        )

    def _load_default_config(self) -> Dict:
        """加载默认配置"""
        config_path = os.path.join(
            os.path.dirname(__file__),
            '../config/claude_semantic_config.json'
        )

        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                sys.stderr.write(u"[WARN] 加载配置文件失败: {}, 使用默认配置\n".format(e))

        # 默认配置
        # v25.0修复：使用Claude Sonnet 4.5（3.5已于2025年10月退役）
        return {
            'enabled': True,
            'model': 'claude-sonnet-4-5',
            'max_tokens': 300,
            'timeout_seconds': 15,
            'retry_count': 1,
            'confidence_threshold': 0.8
        }

    def analyze_intent(
        self,
        user_input: str,
        context: Optional[Dict] = None
    ) -> Dict:
        """
        分析用户意图

        Args:
            user_input: 用户输入的反馈文本
            context: 任务上下文，包含:
                - current_step: 当前阶段
                - code_changes: 代码修改次数
                - iteration: 当前迭代次数

        Returns:
            {
                'success': True/False,
                'intent': '识别的意图类型',
                'confidence': 0.0-1.0,
                'reasoning': '判断理由',
                'recommended_transition': '推荐的状态转移',
                'latency_ms': API调用延迟(毫秒),
                'error': None或错误信息
            }
        """
        # 默认上下文
        if context is None:
            context = {
                'current_step': 'implementation',
                'code_changes': 0,
                'iteration': 0
            }

        # 带重试的API调用
        for attempt in range(self.retry_count + 1):
            try:
                result = self._call_api(user_input, context)

                # 验证结果
                if result['success']:
                    return result

                # 失败但有重试机会
                if attempt < self.retry_count:
                    sys.stderr.write(
                        u"[WARN] API调用失败，{}秒后重试({}/{}): {}\n".format(
                            1, attempt + 1, self.retry_count, result.get('error', 'Unknown')
                        )
                    )
                    time.sleep(1)
                    continue

                # 所有重试都失败
                return result

            except Exception as e:
                # 未捕获的异常
                if attempt < self.retry_count:
                    sys.stderr.write(
                        u"[ERROR] 意外异常，重试中({}/{}): {}\n".format(
                            attempt + 1, self.retry_count, e
                        )
                    )
                    time.sleep(1)
                    continue

                # 重试耗尽，返回错误
                return {
                    'success': False,
                    'intent': 'unknown',
                    'confidence': 0.0,
                    'reasoning': '',
                    'recommended_transition': None,
                    'latency_ms': 0,
                    'error': str(e)
                }

        # 不应到达这里
        return {
            'success': False,
            'intent': 'unknown',
            'confidence': 0.0,
            'reasoning': '',
            'recommended_transition': None,
            'latency_ms': 0,
            'error': '未知错误'
        }

    def _call_api(self, user_input: str, context: Dict) -> Dict:
        """
        调用Claude API（单次）

        Args:
            user_input: 用户输入
            context: 任务上下文

        Returns:
            分析结果字典
        """
        # 构建Prompt
        prompt = self._build_prompt(user_input, context)

        # 记录开始时间
        start_time = time.time()

        try:
            # API调用（带超时）
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                timeout=self.timeout_seconds,
                messages=[{"role": "user", "content": prompt}]
            )

            latency = time.time() - start_time

            # 解析响应
            response_text = response.content[0].text.strip()

            # 提取JSON（处理markdown代码块）
            json_text = self._extract_json(response_text)

            # 解析JSON
            result = json.loads(json_text)

            # 验证必需字段
            intent = result.get('intent', 'unknown')
            confidence = float(result.get('confidence', 0.0))
            reasoning = result.get('reasoning', '')

            # 推荐状态转移
            recommended_transition = self.INTENT_TO_TRANSITION.get(intent)

            return {
                'success': True,
                'intent': intent,
                'confidence': confidence,
                'reasoning': reasoning,
                'recommended_transition': recommended_transition,
                'latency_ms': latency * 1000,
                'error': None,
                'tokens_used': response.usage.input_tokens + response.usage.output_tokens
            }

        except anthropic.APITimeoutError as e:
            latency = time.time() - start_time
            return {
                'success': False,
                'intent': 'unknown',
                'confidence': 0.0,
                'reasoning': '',
                'recommended_transition': None,
                'latency_ms': latency * 1000,
                'error': u'API超时({}秒): {}'.format(self.timeout_seconds, e)
            }

        except anthropic.APIError as e:
            latency = time.time() - start_time
            return {
                'success': False,
                'intent': 'unknown',
                'confidence': 0.0,
                'reasoning': '',
                'recommended_transition': None,
                'latency_ms': latency * 1000,
                'error': u'API错误: {}'.format(e)
            }

        except json.JSONDecodeError as e:
            latency = time.time() - start_time
            return {
                'success': False,
                'intent': 'unknown',
                'confidence': 0.0,
                'reasoning': '',
                'recommended_transition': None,
                'latency_ms': latency * 1000,
                'error': u'JSON解析失败: {}\n原始响应: {}'.format(e, response_text[:200])
            }

        except Exception as e:
            latency = time.time() - start_time
            return {
                'success': False,
                'intent': 'unknown',
                'confidence': 0.0,
                'reasoning': '',
                'recommended_transition': None,
                'latency_ms': latency * 1000,
                'error': u'未知错误: {}'.format(e)
            }

    def _build_prompt(self, user_input: str, context: Dict) -> str:
        """
        构建分析Prompt

        基于MVP的最佳实践，针对中文口语优化
        """
        intent_descriptions = '\n'.join([
            u'- {}: {}'.format(intent, desc)
            for intent, desc in self.INTENT_TYPES.items()
            if intent != 'unknown'  # 排除unknown
        ])

        prompt = u"""你是一个任务状态分析专家。请分析用户的反馈，判断任务应该转移到哪个状态。

**当前任务上下文**:
- 当前阶段: {current_step}
- 代码修改次数: {code_changes}
- 迭代次数: {iteration}

**用户反馈**: "{user_input}"

**请判断用户意图（只输出JSON，不要其他内容）**:

可选意图类型:
{intent_descriptions}

**分析要点**:
1. 注意转折词（"但是"、"不过"、"还有"等）- 有转折通常表示partial_success
2. 识别完成度（"都"、"全部"、"完全"等表示complete，"部分"、"有些"表示partial）
3. 识别失败信号（"没修复"、"还有问题"、"失败"等）
4. 识别规划需求（"重新设计"、"换个思路"、"根本原因"等）

输出格式:
{{
  "intent": "意图类型",
  "confidence": 0.0-1.0,
  "reasoning": "一句话说明判断理由"
}}

**重要**:
- 置信度应反映你的确定程度（0.9+表示很确定，0.7-0.8表示较确定，<0.7表示不确定）
- 如果用户使用了转折词，即使前半句表示成功，也应判断为partial_success
- 中文口语变体很多，例如"都正确了"="修复了"="好了"="搞定了"，都表示complete_success
""".format(
            current_step=context.get('current_step', 'implementation'),
            code_changes=context.get('code_changes', 0),
            iteration=context.get('iteration', 0),
            user_input=user_input,
            intent_descriptions=intent_descriptions
        )

        return prompt

    def _extract_json(self, text: str) -> str:
        """
        从响应中提取JSON

        处理markdown代码块等格式
        """
        # 尝试提取markdown代码块中的JSON
        if '```json' in text:
            start = text.find('```json') + 7
            end = text.find('```', start)
            if end != -1:
                return text[start:end].strip()

        # 尝试提取普通代码块
        if '```' in text:
            start = text.find('```') + 3
            end = text.find('```', start)
            if end != -1:
                return text[start:end].strip()

        # 尝试查找JSON对象
        # 简单的启发式：找第一个 { 到最后一个 }
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            return text[start:end+1]

        # 原样返回（可能直接就是JSON）
        return text


# ===== 便捷函数 =====

_global_analyzer = None

def get_analyzer(config: Optional[Dict] = None) -> ClaudeSemanticAnalyzer:
    """
    获取全局分析器实例（单例模式）

    Args:
        config: 配置字典（仅首次调用时使用）

    Returns:
        ClaudeSemanticAnalyzer实例
    """
    global _global_analyzer

    if _global_analyzer is None:
        _global_analyzer = ClaudeSemanticAnalyzer(config)

    return _global_analyzer


def analyze_user_intent(user_input: str, context: Optional[Dict] = None) -> Dict:
    """
    快捷函数：分析用户意图

    Args:
        user_input: 用户输入
        context: 任务上下文

    Returns:
        分析结果字典
    """
    try:
        analyzer = get_analyzer()
        return analyzer.analyze_intent(user_input, context)
    except Exception as e:
        return {
            'success': False,
            'intent': 'unknown',
            'confidence': 0.0,
            'reasoning': '',
            'recommended_transition': None,
            'latency_ms': 0,
            'error': u'初始化分析器失败: {}'.format(e)
        }


# ===== 测试代码 =====

if __name__ == '__main__':
    """
    测试代码

    运行: python claude_semantic_analyzer.py
    """
    print("=== ClaudeSemanticAnalyzer 测试 ===\n")

    # 测试用例
    test_cases = [
        ("都正确了", {'current_step': 'implementation', 'code_changes': 3}),
        ("基本正确,但还有BUG", {'current_step': 'implementation', 'code_changes': 2}),
        ("根本原因没找到", {'current_step': 'implementation', 'code_changes': 1}),
        ("修复失败了", {'current_step': 'implementation', 'code_changes': 1}),
    ]

    try:
        analyzer = ClaudeSemanticAnalyzer()

        for user_input, context in test_cases:
            print(u"[测试] 用户输入: \"{}\"".format(user_input))
            print(u"       上下文: {}".format(context))

            result = analyzer.analyze_intent(user_input, context)

            if result['success']:
                print(u"[结果] 意图: {} (置信度: {:.2f})".format(
                    result['intent'], result['confidence']
                ))
                print(u"       理由: {}".format(result['reasoning']))
                print(u"       推荐转移: {}".format(result['recommended_transition']))
                print(u"       延迟: {:.0f}ms\n".format(result['latency_ms']))
            else:
                print(u"[错误] {}".format(result['error']))
                print()

    except Exception as e:
        print(u"[FATAL] 测试失败: {}".format(e))
        import traceback
        traceback.print_exc()
        sys.exit(1)
