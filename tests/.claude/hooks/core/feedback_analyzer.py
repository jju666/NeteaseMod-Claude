#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FeedbackAnalyzer - LLM驱动的用户反馈语义分析器 (v24.0)

职责:
1. 使用 Claude API 分析用户反馈的语义
2. 识别修复成功/失败/部分成功
3. 提取成功部分和问题部分
4. 判断整体状态和下一步行动
5. 提供降级机制（API失败时）

替代: v23.2 的关键词匹配方案（作为 fallback）
"""

import json
import time
import os
import sys
import hashlib
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class FeedbackAnalysis:
    """LLM分析结果（结构化）"""

    # 核心判断
    overall_status: str  # complete_success, partial_success, failure, regression, needs_clarification

    # 详细分析
    success_parts: List[str]  # 成功解决的部分（具体描述）
    issue_parts: List[str]    # 仍存在的问题/新问题（具体描述）
    sentiment: str            # satisfied, neutral, dissatisfied

    # 置信度和建议
    confidence: float         # 分析置信度 0.0-1.0
    next_action: str          # continue_implementation, move_to_finalization, back_to_planning, ask_for_clarification
    reasoning: str            # 分析推理过程（方便调试和审核）

    # 映射到现有feedback_type（兼容性）
    feedback_type: str

    # 元数据
    analyzed_at: str
    model_used: str
    tokens_used: int
    api_latency_ms: int


class FeedbackAnalyzer:
    """LLM驱动的用户反馈语义分析器"""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-haiku-20241022"):
        """
        初始化分析器

        Args:
            api_key: Anthropic API密钥（可选，未提供则从环境变量读取）
            model: 使用的模型（默认 Haiku）
        """
        self.model = model
        self.cache = {}  # 简单缓存：{hash(feedback): FeedbackAnalysis}

        # 获取API密钥（支持两种环境变量名）
        if api_key:
            self.api_key = api_key
        else:
            self.api_key = self._get_api_key_from_env()

        # 初始化 Anthropic 客户端
        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=self.api_key)
            self.available = True
        except ImportError:
            sys.stderr.write("[ERROR] Anthropic SDK未安装，请运行: pip install anthropic\n")
            self.available = False
        except Exception as e:
            sys.stderr.write(f"[ERROR] 初始化Anthropic客户端失败: {e}\n")
            self.available = False

    def _get_api_key_from_env(self) -> str:
        """
        从环境变量获取API密钥（支持两种变量名）

        优先级: ANTHROPIC_API_KEY > ANTHROPIC_AUTH_TOKEN

        Returns:
            str: API密钥

        Raises:
            ValueError: 未找到API密钥
        """
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            return api_key

        api_key = os.getenv("ANTHROPIC_AUTH_TOKEN")
        if api_key:
            sys.stderr.write("[INFO] 使用 ANTHROPIC_AUTH_TOKEN 环境变量\n")
            return api_key

        raise ValueError(
            "未找到API密钥。请设置以下环境变量之一:\n"
            "  - ANTHROPIC_API_KEY (推荐)\n"
            "  - ANTHROPIC_AUTH_TOKEN\n"
        )

    def analyze(self,
                user_feedback: str,
                current_step: str,
                task_type: str = "general",
                task_description: str = "",
                code_changes: Optional[List[dict]] = None,
                previous_feedback: Optional[List[dict]] = None,
                use_cache: bool = True) -> FeedbackAnalysis:
        """
        分析用户反馈，返回结构化理解

        Args:
            user_feedback: 用户原始反馈
            current_step: 当前阶段 (activation/planning/implementation/finalization)
            task_type: 任务类型 (bug_fix/feature_development/general)
            task_description: 任务描述
            code_changes: 代码修改记录
            previous_feedback: 历史反馈
            use_cache: 是否使用缓存

        Returns:
            FeedbackAnalysis: 结构化分析结果
        """
        # 检查可用性
        if not self.available:
            return self._fallback_analysis(user_feedback, "Anthropic客户端不可用")

        # 缓存检查
        if use_cache:
            cache_key = self._get_cache_key(user_feedback, current_step)
            if cache_key in self.cache:
                sys.stderr.write("[INFO] 使用缓存的分析结果\n")
                return self.cache[cache_key]

        # 构建提示词
        prompt = self._build_prompt(
            user_feedback=user_feedback,
            current_step=current_step,
            task_type=task_type,
            task_description=task_description,
            code_changes=code_changes or [],
            previous_feedback=previous_feedback or []
        )

        # 调用 Claude API
        start_time = time.time()
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                temperature=0.0,  # 确定性输出
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            api_latency_ms = int((time.time() - start_time) * 1000)

            # 解析JSON响应
            result_text = response.content[0].text
            result_json = self._extract_json(result_text)

            # 映射到现有feedback_type
            feedback_type = self._map_to_feedback_type(result_json["overall_status"])

            # 构建FeedbackAnalysis对象
            analysis = FeedbackAnalysis(
                overall_status=result_json.get("overall_status", "needs_clarification"),
                success_parts=result_json.get("success_parts", []),
                issue_parts=result_json.get("issue_parts", []),
                sentiment=result_json.get("sentiment", "neutral"),
                confidence=float(result_json.get("confidence", 0.5)),
                next_action=result_json.get("next_action", "continue_implementation"),
                reasoning=result_json.get("reasoning", ""),
                feedback_type=feedback_type,
                analyzed_at=datetime.now().isoformat(),
                model_used=self.model,
                tokens_used=response.usage.input_tokens + response.usage.output_tokens,
                api_latency_ms=api_latency_ms
            )

            # 缓存结果
            if use_cache:
                self.cache[cache_key] = analysis

            sys.stderr.write(
                f"[INFO] LLM分析完成: {analysis.overall_status} "
                f"(置信度: {analysis.confidence:.0%}, 延迟: {api_latency_ms}ms, "
                f"tokens: {analysis.tokens_used})\n"
            )

            return analysis

        except Exception as e:
            # 降级策略：返回默认分析 + 记录错误
            sys.stderr.write(f"[ERROR] LLM分析失败，使用降级策略: {e}\n")
            return self._fallback_analysis(user_feedback, str(e))

    def _build_prompt(self, **kwargs) -> str:
        """
        构建提示词

        Args:
            user_feedback: 用户反馈
            current_step: 当前阶段
            task_type: 任务类型
            task_description: 任务描述
            code_changes: 代码修改
            previous_feedback: 历史反馈

        Returns:
            str: 完整的提示词
        """
        # 格式化代码修改摘要
        code_changes_summary = self._format_code_changes(kwargs["code_changes"])

        # 格式化历史反馈摘要
        previous_feedback_summary = self._format_previous_feedback(kwargs["previous_feedback"])

        # 加载提示词模板（从文件或内联）
        prompt_template = self._load_prompt_template()

        # 填充模板
        prompt = prompt_template.format(
            current_step=kwargs["current_step"],
            task_type=kwargs["task_type"],
            task_description=kwargs.get("task_description", "(未提供)"),
            code_changes_summary=code_changes_summary,
            previous_feedback_summary=previous_feedback_summary,
            user_feedback=kwargs["user_feedback"]
        )

        return prompt

    def _load_prompt_template(self) -> str:
        """
        加载提示词模板

        优先从文件加载，如果文件不存在则使用内联模板

        Returns:
            str: 提示词模板
        """
        # 尝试从文件加载
        hook_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        prompt_file = os.path.join(hook_dir, "prompts", "feedback_analysis_v1.txt")

        if os.path.exists(prompt_file):
            try:
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                sys.stderr.write(f"[WARN] 加载提示词模板失败，使用内联模板: {e}\n")

        # 内联模板（fallback）
        return """你是一个专业的软件开发任务反馈分析助手。你的任务是分析用户对代码修复的反馈，准确判断修复状态。

# 任务上下文
- 当前阶段: {current_step}
- 任务类型: {task_type}
- 任务描述: {task_description}

# 本轮代码修改
{code_changes_summary}

# 历史反馈（最近3条）
{previous_feedback_summary}

# 用户最新反馈
"{user_feedback}"

# 分析要求
请仔细分析用户反馈，提取以下结构化信息：

1. **整体状态判断**：
   - complete_success: 用户明确表示所有问题都解决了
   - partial_success: 用户表示部分问题解决，但还有其他问题
   - failure: 用户表示问题未解决或修复失败
   - regression: 用户表示修复了某个问题但引入了新问题
   - needs_clarification: 用户的反馈模糊，无法确定状态

2. **成功部分**：列出用户提到的已解决的问题（具体描述）

3. **问题部分**：列出用户提到的仍存在的问题或新发现的问题（具体描述）

4. **用户情绪**：
   - satisfied: 用户满意（如"很好"、"完美"）
   - neutral: 用户中性（仅陈述事实）
   - dissatisfied: 用户不满（如"还是不行"、"没用"）

5. **置信度**：你对分析结果的置信度（0.0-1.0）

6. **下一步建议**：
   - continue_implementation: 继续修复剩余问题
   - move_to_finalization: 进入收尾归档
   - back_to_planning: 回到方案设计（方案性错误）
   - ask_for_clarification: 请求用户澄清

7. **分析推理**：简要说明你的判断依据

# 输出格式
请以JSON格式输出，严格遵循以下schema：

{{
  "overall_status": "complete_success",
  "success_parts": ["具体成功部分1", "具体成功部分2"],
  "issue_parts": ["具体问题1", "具体问题2"],
  "sentiment": "satisfied",
  "confidence": 0.95,
  "next_action": "move_to_finalization",
  "reasoning": "用户明确提到'完全修复'和'测试通过'，未提及任何剩余问题，因此判断为complete_success。用户语气积极满意，建议进入收尾阶段。"
}}

# 重要提示
- 关注转折词（"但是"、"不过"、"however"）：转折词后通常是问题部分
- 区分"部分成功"和"完全成功"：只要提到剩余问题，就是部分成功
- 注意隐含信息：如"测试通过"通常意味着成功
- 如果不确定，降低confidence值，建议ask_for_clarification
- 只输出JSON，不要添加其他解释文字
"""

    def _format_code_changes(self, code_changes: List[dict]) -> str:
        """
        格式化代码修改摘要

        Args:
            code_changes: 代码修改列表

        Returns:
            str: 格式化的摘要
        """
        if not code_changes:
            return "(本轮未修改代码)"

        # 提取文件名（去重）
        files = set()
        for change in code_changes[-5:]:  # 只看最近5次修改
            file_path = change.get('file', '')
            if file_path:
                # 提取文件名（不含路径）
                file_name = os.path.basename(file_path)
                files.add(file_name)

        if files:
            return f"修改了 {len(files)} 个文件: {', '.join(sorted(files))}"
        else:
            return f"进行了 {len(code_changes)} 次代码修改"

    def _format_previous_feedback(self, previous_feedback: List[dict]) -> str:
        """
        格式化历史反馈摘要

        Args:
            previous_feedback: 历史反馈列表

        Returns:
            str: 格式化的摘要
        """
        if not previous_feedback:
            return "(无历史反馈)"

        # 只看最近3条
        recent_feedback = previous_feedback[-3:]

        lines = []
        for i, feedback in enumerate(recent_feedback, 1):
            user_text = feedback.get('user_feedback', '')[:50]  # 限制长度
            feedback_type = feedback.get('feedback_type', 'unknown')
            timestamp = feedback.get('timestamp', '')[:10]  # 只要日期

            lines.append(f"{i}. [{timestamp}] 用户: '{user_text}...' → 分析: {feedback_type}")

        return "\n".join(lines)

    def _extract_json(self, text: str) -> dict:
        """
        从文本中提取JSON

        支持多种格式:
        1. 直接JSON
        2. Markdown代码块包裹: ```json ... ```
        3. 简单代码块: ``` ... ```

        Args:
            text: 文本

        Returns:
            dict: 解析后的JSON对象

        Raises:
            ValueError: 无法提取或解析JSON
        """
        import re

        text = text.strip()

        # 1. 直接JSON
        if text.startswith("{"):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass  # 继续尝试其他方法

        # 2. Markdown代码块包裹 (```json ... ```)
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 3. 简单代码块 (``` ... ```)
        json_match = re.search(r'```\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 4. 尝试从整个文本中提取第一个JSON对象
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        raise ValueError(f"无法从文本中提取有效的JSON:\n{text[:200]}...")

    def _map_to_feedback_type(self, overall_status: str) -> str:
        """
        映射LLM分析结果到现有feedback_type

        Args:
            overall_status: LLM输出的overall_status

        Returns:
            str: 现有系统的feedback_type
        """
        mapping = {
            "complete_success": "explicit_success",
            "partial_success": "partial_success_with_issues",
            "failure": "explicit_failure",
            "regression": "partial_success_with_issues",  # 回归也算部分成功
            "needs_clarification": "ambiguous_positive"
        }
        return mapping.get(overall_status, "continuation_request")

    def _fallback_analysis(self, user_feedback: str, error: str) -> FeedbackAnalysis:
        """
        降级策略：API失败时的默认分析

        Args:
            user_feedback: 用户反馈
            error: 错误信息

        Returns:
            FeedbackAnalysis: 保守的分析结果
        """
        # 记录错误到日志
        sys.stderr.write(f"[FALLBACK] LLM分析失败，返回保守结果。错误: {error}\n")

        # 返回保守的分析结果（建议请求澄清）
        return FeedbackAnalysis(
            overall_status="needs_clarification",
            success_parts=[],
            issue_parts=[],
            sentiment="neutral",
            confidence=0.0,
            next_action="ask_for_clarification",
            reasoning=f"LLM分析失败，无法准确判断。错误: {error}",
            feedback_type="continuation_request",
            analyzed_at=datetime.now().isoformat(),
            model_used="fallback",
            tokens_used=0,
            api_latency_ms=0
        )

    def _get_cache_key(self, user_feedback: str, current_step: str) -> str:
        """
        生成缓存键

        Args:
            user_feedback: 用户反馈
            current_step: 当前阶段

        Returns:
            str: 缓存键（MD5 hash）
        """
        key_str = f"{current_step}:{user_feedback}"
        return hashlib.md5(key_str.encode('utf-8')).hexdigest()


# ============== 工厂函数 ==============

def create_feedback_analyzer(config: Optional[Dict] = None) -> Optional[FeedbackAnalyzer]:
    """
    工厂函数：创建FeedbackAnalyzer实例

    Args:
        config: 配置字典（可选）

    Returns:
        FeedbackAnalyzer或None（如果配置禁用或初始化失败）
    """
    if config is None:
        config = {}

    # 检查是否启用
    if not config.get('enabled', True):
        sys.stderr.write("[INFO] FeedbackAnalyzer已禁用（配置）\n")
        return None

    try:
        model = config.get('model', 'claude-3-5-haiku-20241022')
        analyzer = FeedbackAnalyzer(model=model)

        if not analyzer.available:
            sys.stderr.write("[WARN] FeedbackAnalyzer不可用，将使用关键词匹配\n")
            return None

        return analyzer

    except Exception as e:
        sys.stderr.write(f"[ERROR] 创建FeedbackAnalyzer失败: {e}\n")
        return None
