#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LLM Intent Analyzer - LLM意图分析器 (v25.4)

统一LLM调用抽象层，提供Planning和Implementation阶段的用户意图识别。

核心功能：
1. Planning阶段意图分析（agree/reject/restart）
2. Implementation阶段意图分析（6种意图类型，新增observation_only）
3. LLM Prompt模板管理（从配置文件加载）
4. Claude API调用封装（超时、重试、降级）
5. 分层置信度验证（v25.2：0.70阈值 + 关键词降级）
6. 转折词识别（v25.2新增）
7. ABCD选项识别（v25.3新增：支持"D方案错误"等选项标签）
8. 激进模式（v25.4新增：模糊输入默认partial_success，信任AI判断）

作者: NeteaseMod-Claude工作流系统
版本: v25.4
日期: 2025-11-20, Updated: 2025-11-22 (v25.4)
"""

import sys
import os
import json
import re


class LLMIntentAnalyzer:
    """
    LLM意图分析器 (v25.2)

    使用Claude Sonnet 4.5进行用户意图语义分析，替代传统关键词匹配。

    特性：
    - 96.15%准确率（vs 传统关键词85%）
    - 100%决策覆盖（LLM主判 + 关键词降级 + observation_only兜底）
    - 分层置信度验证（0.70阈值 + 0.50-0.69降级）
    - 转折词优先级规则（v25.2新增）
    - 6种意图类型（新增observation_only）
    """

    def __init__(self, cwd):
        """
        初始化LLM意图分析器

        Args:
            cwd: 工作目录（用于加载配置文件）
        """
        self.cwd = cwd
        self.analyzer = self._get_claude_analyzer()
        self.prompt_templates = self._load_prompt_templates()

    def analyze_planning_intent(self, user_input, meta_data):
        """
        Planning阶段意图分析

        Args:
            user_input: 用户输入文本
            meta_data: 任务元数据（包含current_step、expert_review_completed等）

        Returns:
            dict: 分析结果
                {
                    'success': True/False,
                    'intent': 'agree' | 'reject' | 'restart',
                    'confidence': 0.0-1.0,
                    'reasoning': str,
                    'reason': str  # success=False时的原因
                }

        Examples:
            >>> analyzer = LLMIntentAnalyzer('/path/to/project')
            >>> result = analyzer.analyze_planning_intent("同意", meta_data)
            >>> result['intent']
            'agree'
        """
        # 1. 检查analyzer是否可用
        if not self.analyzer:
            return {
                'success': False,
                'reason': 'claude_analyzer_not_available'
            }

        # 2. 构建上下文
        # v29.3：删除冗余的ABC选项检测，统一由_fallback_planning_keywords()处理
        planning_step = meta_data.get('steps', {}).get('planning', {})
        context = {
            'current_step': meta_data.get('current_step', 'planning'),
            'expert_review_completed': planning_step.get('expert_review_completed', False),
            'expert_review': "是" if planning_step.get('expert_review_completed', False) else "否",
            'docs_read': len(meta_data.get('metrics', {}).get('docs_read', [])),
            'required_doc_count': planning_step.get('required_doc_count', 0)
        }

        # 3. 加载Prompt模板
        prompt_template = self.prompt_templates.get('planning_stage', {}).get('prompt_template', '')
        if not prompt_template:
            return {
                'success': False,
                'reason': 'prompt_template_missing'
            }

        # 4. 渲染Prompt
        prompt = self._render_prompt(prompt_template, context, user_input)

        # 5. 调用Claude API
        try:
            sys.stderr.write(u"[INFO] 调用Claude API分析Planning阶段用户意图...\n")
            llm_result = self._call_claude_api(prompt)

            intent = llm_result.get('intent', 'unknown')
            confidence = llm_result.get('confidence', 0.0)
            reasoning = llm_result.get('reasoning', '')

            sys.stderr.write(u"[DEBUG] Planning LLM分析结果:\n")
            sys.stderr.write(u"  - 意图: {}\n".format(intent))
            sys.stderr.write(u"  - 置信度: {:.0%}\n".format(confidence))
            sys.stderr.write(u"  - 理由: {}\n".format(reasoning[:100]))

            # 6. 验证置信度
            confidence_threshold = self.prompt_templates.get('llm_config', {}).get('confidence_threshold', 0.8)

            if confidence >= confidence_threshold:
                return {
                    'success': True,
                    'intent': intent,
                    'confidence': confidence,
                    'reasoning': reasoning
                }
            else:
                sys.stderr.write(u"[WARN] Planning LLM置信度不足: {:.0%}\n".format(confidence))
                return {
                    'success': False,
                    'reason': 'low_confidence',
                    'confidence': confidence
                }

        except Exception as e:
            sys.stderr.write(u"[ERROR] Planning LLM分析异常: {}\n".format(e))
            import traceback
            traceback.print_exc(file=sys.stderr)
            return {
                'success': False,
                'reason': str(e)
            }

    def analyze_implementation_intent(self, user_input, meta_data):
        """
        Implementation阶段意图分析 (v25.2: 使用分层验证)

        新增特性：
        - 分层置信度验证（0.70阈值）
        - 关键词降级策略（LLM失败时）
        - 100%决策覆盖（LLM + 关键词 + observation_only兜底）

        Args:
            user_input: 用户输入文本
            meta_data: 任务元数据

        Returns:
            dict: 分析结果
                {
                    'success': True,
                    'intent': 'complete_success' | 'partial_success' | 'failure'
                             | 'planning_required' | 'continuation_request' | 'observation_only',
                    'confidence': 0.0-1.0,
                    'reasoning': str,
                    'fallback_used': True/False (如果使用了关键词降级),
                    'reason': str  # success=False时的原因（仅API错误）
                }
        """
        # 1. 检查analyzer是否可用
        if not self.analyzer:
            sys.stderr.write(u"[ERROR] Claude分析器不可用，启动关键词降级\n")
            return self._fallback_to_keywords(user_input, meta_data)

        # 2. 调用ClaudeSemanticAnalyzer.analyze_user_intent()
        try:
            from core.claude_semantic_analyzer import analyze_user_intent

            sys.stderr.write(u"[INFO] 调用ClaudeSemanticAnalyzer分析Implementation阶段用户意图...\n")

            # v25.2修复: analyze_user_intent签名是(user_input, context)
            # meta_data中已包含current_step，直接传递即可
            result = analyze_user_intent(
                user_input,
                context=meta_data
            )

            # 3. 验证结果（如果API返回None）
            if not result:
                sys.stderr.write(u"[ERROR] LLM返回None，启动关键词降级\n")
                return self._fallback_to_keywords(user_input, meta_data)

            intent = result.get('intent', 'unknown')
            confidence = result.get('confidence', 0.0)
            reasoning = result.get('reasoning', '')

            sys.stderr.write(u"[DEBUG] Implementation LLM分析结果:\n")
            sys.stderr.write(u"  - 意图: {}\n".format(intent))
            sys.stderr.write(u"  - 置信度: {:.0%}\n".format(confidence))
            sys.stderr.write(u"  - 理由: {}\n".format(reasoning[:100] if reasoning else ''))

            # 4. 使用新的分层验证逻辑 (v25.2)
            validation = self._validate_llm_result(result)

            if validation['valid']:
                # LLM结果通过验证
                return {
                    'success': True,
                    'intent': validation['intent'],
                    'confidence': validation['confidence'],
                    'reasoning': validation['reasoning'],
                    'fallback_used': False
                }
            elif validation['fallback_reason'] == 'low_confidence':
                # 置信度不足，启动关键词降级
                sys.stderr.write(u"[INFO] 启动关键词降级（LLM置信度不足）\n")
                return self._fallback_to_keywords(user_input, meta_data)
            else:
                # API错误，启动关键词降级
                sys.stderr.write(u"[ERROR] LLM API错误: {}，启动关键词降级\n".format(
                    validation.get('original_reason', 'unknown')
                ))
                return self._fallback_to_keywords(user_input, meta_data)

        except ImportError:
            sys.stderr.write(u"[ERROR] ClaudeSemanticAnalyzer模块导入失败，启动关键词降级\n")
            return self._fallback_to_keywords(user_input, meta_data)
        except Exception as e:
            sys.stderr.write(u"[ERROR] Implementation LLM分析异常: {}，启动关键词降级\n".format(e))
            import traceback
            traceback.print_exc(file=sys.stderr)
            return self._fallback_to_keywords(user_input, meta_data)

    def _validate_llm_result(self, intent_result):
        """
        分层验证LLM结果 (v25.2新增)

        验证规则：
        1. LLM API失败 → {'valid': False, 'fallback_reason': 'api_error'}
        2. 置信度≥0.70 → {'valid': True, 'intent': intent}
        3. 0.50≤置信度<0.70 且intent=observation_only → {'valid': True}
        4. 置信度<0.70 且intent≠observation_only → {'valid': False, 'fallback_reason': 'low_confidence'}

        Args:
            intent_result: ClaudeSemanticAnalyzer返回的结果
                {
                    'success': True/False,
                    'intent': str,
                    'confidence': float,
                    'reasoning': str
                }

        Returns:
            dict: 验证结果
                {
                    'valid': True/False,
                    'intent': str (如果valid=True),
                    'fallback_reason': str (如果valid=False)
                }
        """
        # 1. 检查API调用是否成功
        if not intent_result.get('success', False):
            return {
                'valid': False,
                'fallback_reason': 'api_error',
                'original_reason': intent_result.get('reason', 'unknown')
            }

        # 2. 提取结果
        confidence = intent_result.get('confidence', 0.0)
        intent = intent_result.get('intent', 'unknown')
        reasoning = intent_result.get('reasoning', '')

        # 3. 分层验证
        if confidence >= 0.70:
            # 高置信度，直接采纳
            sys.stderr.write(u"[INFO] LLM结果验证通过: {}(置信度{:.0%})\n".format(intent, confidence))
            return {
                'valid': True,
                'intent': intent,
                'confidence': confidence,
                'reasoning': reasoning
            }
        elif confidence >= 0.50 and intent == 'observation_only':
            # 中等置信度，但判断为observation_only，可以接受
            sys.stderr.write(u"[INFO] LLM结果验证通过: observation_only(置信度{:.0%}，中等但合理)\n".format(confidence))
            return {
                'valid': True,
                'intent': intent,
                'confidence': confidence,
                'reasoning': reasoning
            }
        else:
            # 置信度不足，需要降级
            sys.stderr.write(u"[WARN] LLM置信度不足: {}(置信度{:.0%} < 0.70)，启动关键词降级\n".format(intent, confidence))
            return {
                'valid': False,
                'fallback_reason': 'low_confidence',
                'original_intent': intent,
                'original_confidence': confidence
            }

    def _fallback_to_keywords(self, user_input, meta_data):
        """
        关键词匹配降级方案 (v25.4激进模式)

        当LLM置信度<0.70时，使用关键词匹配作为降级策略。

        降级规则（v25.4激进模式）：
        0. ABCD选项识别 → 直接映射到对应意图 (confidence 0.90) [最高优先级]
        1. 转折词 + 成功词 → partial_success (confidence 0.75)
        2. 选项标签关键词 → 对应意图 (confidence 0.85)
        3. 纯成功词（无转折） → complete_success (confidence 0.75)
        4. 明确失败词 → failure (confidence 0.75)
        5. 规划关键词 → planning_required (confidence 0.75)
        6. 继续关键词 → continuation_request (confidence 0.75)
        7. 🔥 强负面关键词 → observation_only (confidence 0.60) [需要用户明确]
        8. 🔥 默认：partial_success (confidence 0.65) [激进模式，信任AI判断]

        Args:
            user_input: 用户输入文本
            meta_data: 任务元数据

        Returns:
            dict: 降级分析结果
                {
                    'success': True,
                    'intent': str,
                    'confidence': float,
                    'reasoning': str,
                    'fallback_used': True,
                    'aggressive_mode': True/False  # 标记是否使用激进模式
                }
        """
        user_input_lower = user_input.lower()

        # ==================== 0. ABCD选项识别（v25.3新增，最高优先级）====================
        # 匹配: "A"、"选项A"、"A修复了"、"D方案错误"等
        option_pattern = r'(?:选项)?\s*([ABCD])'
        option_match = re.search(option_pattern, user_input, re.IGNORECASE)

        if option_match:
            option_letter = option_match.group(1).upper()

            option_to_intent = {
                'A': 'complete_success',
                'B': 'partial_success',
                'C': 'failure',
                'D': 'planning_required'
            }

            intent = option_to_intent.get(option_letter)
            if intent:
                sys.stderr.write(u"[INFO] 关键词降级: 检测到ABCD选项 {}({})\n".format(option_letter, intent))
                return {
                    'success': True,
                    'intent': intent,
                    'confidence': 0.90,  # 用户明确选择了选项，高置信度
                    'reasoning': u'关键词降级: 检测到ABCD选项 {}({})'.format(option_letter, intent),
                    'fallback_used': True
                }

        # ==================== 转折词列表 ====================
        CONJUNCTIONS = [
            u'但是', u'但', u'不过', u'可是', u'然而', u'只是', u'就是', u'还有',
            u'还没', u'还得', u'还要', u'只能', u'仅仅'
        ]

        # ==================== 关键词分组（v25.3更新：添加选项标签）====================

        # Complete Success（A选项）
        COMPLETE_KEYWORDS = [
            u'修复成功',  # 🔥 v25.3新增：选项A标签
            u'都正确了', u'修复了', u'搞定了', u'好了', u'没问题了', u'全部修好了',
            u'完全正确', u'正确了', u'成功了', u'通过', u'完成了', u'解决了'
        ]

        # Partial Success（B选项）
        PARTIAL_KEYWORDS = [
            u'部分成功',  # 🔥 v25.3新增：选项B标签
            u'基本正确', u'基本可以', u'大部分', u'还有', u'部分修复'
        ]

        # Failure（C选项）
        FAILURE_KEYWORDS = [
            u'修复失败',  # 🔥 v25.3新增：选项C标签
            u'没修复', u'还是有问题', u'失败了', u'不行', u'根本没用',
            u'没用', u'有问题', u'有BUG', u'有bug'
        ]

        # Planning Required（D选项）
        PLANNING_KEYWORDS = [
            u'方案错误',  # 🔥 v25.3新增：选项D标签
            u'方案错', u'方案有问题', u'方案不对',  # 🔥 v25.3模糊化："方案错了"/"方案错误"都能匹配"方案错"
            u'思路不对', u'思路错', u'思路有问题',
            u'需要调整', u'重新设计', u'换个思路', u'重新规划',
            u'根本原因', u'架构问题'
        ]

        # Continuation
        CONTINUATION_KEYWORDS = [
            u'继续', u'继续修改', u'接着来', u'继续搞', u'继续处理'
        ]

        # ==================== 1. 检测转折词 ====================
        has_conjunction = any(conj in user_input_lower for conj in CONJUNCTIONS)

        # ==================== 2. 转折词 + 成功词 → partial_success ====================
        if has_conjunction:
            if any(kw in user_input_lower for kw in [u'正确', u'成功', u'修复', u'好了', u'搞定']):
                return {
                    'success': True,
                    'intent': 'partial_success',
                    'confidence': 0.75,
                    'reasoning': u'关键词降级: 检测到转折词 + 成功词',
                    'fallback_used': True
                }

        # ==================== 3. 规划关键词（包含选项D标签）====================
        if any(kw in user_input_lower for kw in PLANNING_KEYWORDS):
            return {
                'success': True,
                'intent': 'planning_required',
                'confidence': 0.75,
                'reasoning': u'关键词降级: 检测到规划关键词',
                'fallback_used': True
            }

        # ==================== 4. 纯成功词（无转折，包含选项A标签）====================
        if any(kw in user_input_lower for kw in COMPLETE_KEYWORDS):
            return {
                'success': True,
                'intent': 'complete_success',
                'confidence': 0.75,
                'reasoning': u'关键词降级: 检测到成功关键词',
                'fallback_used': True
            }

        # ==================== 5. 部分成功词（选项B标签）====================
        if any(kw in user_input_lower for kw in PARTIAL_KEYWORDS):
            return {
                'success': True,
                'intent': 'partial_success',
                'confidence': 0.75,
                'reasoning': u'关键词降级: 检测到部分成功关键词',
                'fallback_used': True
            }

        # ==================== 6. 失败词（包含选项C标签）====================
        if any(kw in user_input_lower for kw in FAILURE_KEYWORDS):
            return {
                'success': True,
                'intent': 'failure',
                'confidence': 0.75,
                'reasoning': u'关键词降级: 检测到失败关键词',
                'fallback_used': True
            }

        # ==================== 7. 继续关键词 ====================
        if any(kw in user_input_lower for kw in CONTINUATION_KEYWORDS):
            return {
                'success': True,
                'intent': 'continuation_request',
                'confidence': 0.75,
                'reasoning': u'关键词降级: 检测到继续关键词',
                'fallback_used': True
            }

        # ==================== 8. 强负面关键词（v25.4新增）====================
        # 用于检测可能需要回到Planning阶段的强烈信号
        STRONG_NEGATIVE_KEYWORDS = [
            u'完全错了', u'完全不对', u'方向错了', u'架构问题',
            u'根本原因', u'重新开始', u'重新设计', u'完全失败',
            u'一点效果都没有', u'完全没用', u'完全没生效'
        ]

        has_strong_negative = any(kw in user_input_lower for kw in STRONG_NEGATIVE_KEYWORDS)

        if has_strong_negative:
            # 可能是planning_required，需要用户明确表态
            sys.stderr.write(u"[WARN] 关键词降级: 检测到强负面关键词，需要用户明确表态\n")
            sys.stderr.write(u"[WARN] 用户输入: {}\n".format(user_input[:200] if len(user_input) > 200 else user_input))
            return {
                'success': True,
                'intent': 'observation_only',
                'confidence': 0.60,
                'reasoning': u'关键词降级: 检测到强负面关键词，需要明确表态',
                'fallback_used': True
            }

        # ==================== 9. 默认：partial_success（v25.4激进模式）====================
        # 🔥 信任AI判断：模糊输入默认为partial_success，让AI根据描述继续修改
        sys.stderr.write(u"[INFO] 关键词降级: 模糊输入，默认判断为partial_success（激进模式）\n")
        sys.stderr.write(u"[INFO] 用户输入: {}\n".format(user_input[:200] if len(user_input) > 200 else user_input))
        sys.stderr.write(u"[INFO] AI将根据你的描述推断问题并继续修改\n")
        return {
            'success': True,
            'intent': 'partial_success',  # 🔥 v25.4: 改为partial_success
            'confidence': 0.65,  # 略低于明确关键词的0.75
            'reasoning': u'关键词降级: 模糊输入默认为partial_success，AI将根据描述继续修改',
            'fallback_used': True,
            'aggressive_mode': True  # 🔥 标记为激进模式
        }

    def _get_claude_analyzer(self):
        """
        获取Claude分析器实例

        Returns:
            ClaudeSemanticAnalyzer实例，如果不可用返回None
        """
        try:
            from core.claude_semantic_analyzer import get_analyzer
            return get_analyzer()
        except ImportError:
            sys.stderr.write(u"[WARN] ClaudeSemanticAnalyzer不可用\n")
            return None

    def _load_prompt_templates(self):
        """
        从配置文件加载Prompt模板

        Returns:
            dict: Prompt模板字典，加载失败时返回默认模板
        """
        config_path = os.path.join(
            self.cwd, '.claude', 'hooks', 'config', 'llm_prompts.json'
        )

        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                sys.stderr.write(u"[WARN] llm_prompts.json不存在，使用默认模板\n")
                return self._get_default_prompt_templates()
        except Exception as e:
            sys.stderr.write(u"[ERROR] 加载Prompt模板失败: {}\n".format(e))
            return self._get_default_prompt_templates()

    def _render_prompt(self, template, context, user_input):
        """
        渲染Prompt模板

        Args:
            template: Prompt模板字符串
            context: 上下文变量字典
            user_input: 用户输入

        Returns:
            str: 渲染后的Prompt
        """
        try:
            return template.format(
                current_step=context.get('current_step', 'unknown'),
                expert_review=context.get('expert_review', '未知'),
                docs_read=context.get('docs_read', 0),
                required_docs=context.get('required_doc_count', 0),
                user_input=user_input
            )
        except KeyError as e:
            sys.stderr.write(u"[ERROR] Prompt模板变量缺失: {}\n".format(e))
            return template

    def _call_claude_api(self, prompt):
        """
        调用Claude API

        Args:
            prompt: 渲染后的Prompt

        Returns:
            dict: API响应JSON
                {
                    'intent': str,
                    'confidence': float,
                    'reasoning': str
                }

        Raises:
            Exception: API调用失败
        """
        if not self.analyzer:
            raise Exception("Claude分析器未初始化")

        import anthropic

        client = self.analyzer.client

        response = client.messages.create(
            model=self.analyzer.model,
            max_tokens=self.analyzer.max_tokens,
            timeout=self.analyzer.timeout_seconds,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = response.content[0].text.strip()

        # 提取JSON
        json_text = self.analyzer._extract_json(response_text)
        return json.loads(json_text)

    def _get_default_prompt_templates(self):
        """
        默认Prompt模板（硬编码降级方案）

        Returns:
            dict: 默认模板字典
        """
        return {
            'planning_stage': {
                'prompt_template': '''你是一个任务状态分析专家。用户正在Planning（方案制定）阶段，请分析用户的反馈意图。

**当前任务上下文**:
- 当前阶段: {current_step}
- 专家审查已完成: {expert_review}
- 文档查阅: {docs_read}/{required_docs}

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
}}'''
            },
            'implementation_stage': {
                'analysis_method': '使用ClaudeSemanticAnalyzer.analyze_user_intent()进行分析'
            },
            'llm_config': {
                'confidence_threshold': 0.8
            }
        }


# ==================== 导出符号 ====================

__all__ = [
    'LLMIntentAnalyzer'
]
