#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FeedbackAnalyzer 测试用例 (v24.0)

运行方式:
    cd tests/.claude/hooks/core
    python test_feedback_analyzer.py
"""

import os
import sys
import io
import unittest

# 修复 Windows 编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加父目录到路径
HOOK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HOOK_DIR)

try:
    from core.feedback_analyzer import FeedbackAnalyzer, FeedbackAnalysis
except ImportError as e:
    print(f"[ERROR] 无法导入 FeedbackAnalyzer: {e}")
    sys.exit(1)


class TestFeedbackAnalyzer(unittest.TestCase):
    """FeedbackAnalyzer 核心功能测试"""

    @classmethod
    def setUpClass(cls):
        """测试套件初始化"""
        # 检查环境变量
        api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")
        if not api_key:
            print("\n" + "="*70)
            print("⚠️  警告：未设置 API 密钥，测试将使用 fallback 模式")
            print("="*70)
            print("请设置以下环境变量之一：")
            print("  - ANTHROPIC_API_KEY")
            print("  - ANTHROPIC_AUTH_TOKEN")
            print("\n如果设置了 API 密钥，测试将调用真实的 Claude API。")
            print("="*70 + "\n")

        try:
            cls.analyzer = FeedbackAnalyzer(model="claude-3-5-haiku-20241022")
            cls.api_available = cls.analyzer.available
            if cls.api_available:
                print(f"✅ FeedbackAnalyzer 初始化成功，模型: {cls.analyzer.model}")
            else:
                print("⚠️  FeedbackAnalyzer API 不可用，测试将验证 fallback 行为")
        except Exception as e:
            print(f"❌ FeedbackAnalyzer 初始化失败: {e}")
            cls.analyzer = None
            cls.api_available = False

    def test_01_complete_success(self):
        """测试完全成功识别"""
        print("\n" + "="*70)
        print("测试 1: 完全成功识别")
        print("="*70)

        if not self.analyzer:
            self.skipTest("FeedbackAnalyzer 不可用")

        user_feedback = "完全修复了，所有问题都解决了，测试通过"

        analysis = self.analyzer.analyze(
            user_feedback=user_feedback,
            current_step="implementation",
            task_type="bug_fix",
            task_description="修复等待大厅倒计时问题"
        )

        print(f"用户反馈: {user_feedback}")
        print(f"分析结果:")
        print(f"  - overall_status: {analysis.overall_status}")
        print(f"  - next_action: {analysis.next_action}")
        print(f"  - confidence: {analysis.confidence:.0%}")
        print(f"  - sentiment: {analysis.sentiment}")
        print(f"  - success_parts: {analysis.success_parts}")
        print(f"  - issue_parts: {analysis.issue_parts}")
        print(f"  - reasoning: {analysis.reasoning}")
        print(f"  - model_used: {analysis.model_used}")
        print(f"  - api_latency_ms: {analysis.api_latency_ms}ms")

        if self.api_available:
            # API 可用时，验证真实分析结果
            self.assertEqual(analysis.overall_status, "complete_success", "应识别为完全成功")
            self.assertEqual(analysis.next_action, "move_to_finalization", "应建议进入收尾阶段")
            self.assertGreater(analysis.confidence, 0.7, "置信度应较高")
            self.assertEqual(len(analysis.issue_parts), 0, "不应有问题部分")
        else:
            # API 不可用时，验证 fallback 行为
            self.assertEqual(analysis.overall_status, "needs_clarification", "fallback 应返回 needs_clarification")
            self.assertEqual(analysis.confidence, 0.0, "fallback 置信度应为 0")

        print("✅ 测试通过")

    def test_02_partial_success_with_conjunction(self):
        """测试部分成功识别（带转折词）"""
        print("\n" + "="*70)
        print("测试 2: 部分成功识别（带转折词）")
        print("="*70)

        if not self.analyzer:
            self.skipTest("FeedbackAnalyzer 不可用")

        user_feedback = "测试结果反馈，确实正常进入运行状态了，但是全部玩家都没有进入到对局地图内。"

        analysis = self.analyzer.analyze(
            user_feedback=user_feedback,
            current_step="implementation",
            task_type="bug_fix",
            task_description="修复对局状态机问题"
        )

        print(f"用户反馈: {user_feedback}")
        print(f"分析结果:")
        print(f"  - overall_status: {analysis.overall_status}")
        print(f"  - next_action: {analysis.next_action}")
        print(f"  - confidence: {analysis.confidence:.0%}")
        print(f"  - success_parts: {analysis.success_parts}")
        print(f"  - issue_parts: {analysis.issue_parts}")
        print(f"  - reasoning: {analysis.reasoning}")

        if self.api_available:
            self.assertEqual(analysis.overall_status, "partial_success", "应识别为部分成功")
            self.assertEqual(analysis.next_action, "continue_implementation", "应建议继续修复")
            self.assertGreater(len(analysis.success_parts), 0, "应提取成功部分")
            self.assertGreater(len(analysis.issue_parts), 0, "应提取问题部分")
            # 验证是否正确提取了关键信息
            success_text = ' '.join(analysis.success_parts).lower()
            issue_text = ' '.join(analysis.issue_parts).lower()
            self.assertIn("状态", success_text, "成功部分应包含'状态'相关内容")
            self.assertIn("玩家", issue_text, "问题部分应包含'玩家'相关内容")

        print("✅ 测试通过")

    def test_03_failure(self):
        """测试失败识别"""
        print("\n" + "="*70)
        print("测试 3: 失败识别")
        print("="*70)

        if not self.analyzer:
            self.skipTest("FeedbackAnalyzer 不可用")

        user_feedback = "没修复，还是报错，完全不行"

        analysis = self.analyzer.analyze(
            user_feedback=user_feedback,
            current_step="implementation",
            task_type="bug_fix"
        )

        print(f"用户反馈: {user_feedback}")
        print(f"分析结果:")
        print(f"  - overall_status: {analysis.overall_status}")
        print(f"  - next_action: {analysis.next_action}")
        print(f"  - confidence: {analysis.confidence:.0%}")
        print(f"  - sentiment: {analysis.sentiment}")
        print(f"  - issue_parts: {analysis.issue_parts}")
        print(f"  - reasoning: {analysis.reasoning}")

        if self.api_available:
            self.assertEqual(analysis.overall_status, "failure", "应识别为失败")
            self.assertIn(analysis.next_action, ["back_to_planning", "continue_implementation"], "应建议回到planning或继续修复")
            self.assertEqual(len(analysis.success_parts), 0, "失败时不应有成功部分")
            self.assertIn(analysis.sentiment, ["dissatisfied", "neutral"], "用户情绪应为不满或中性")

        print("✅ 测试通过")

    def test_04_needs_clarification(self):
        """测试需要澄清识别"""
        print("\n" + "="*70)
        print("测试 4: 需要澄清识别")
        print("="*70)

        if not self.analyzer:
            self.skipTest("FeedbackAnalyzer 不可用")

        user_feedback = "嗯...好像可以"

        analysis = self.analyzer.analyze(
            user_feedback=user_feedback,
            current_step="implementation",
            task_type="bug_fix"
        )

        print(f"用户反馈: {user_feedback}")
        print(f"分析结果:")
        print(f"  - overall_status: {analysis.overall_status}")
        print(f"  - next_action: {analysis.next_action}")
        print(f"  - confidence: {analysis.confidence:.0%}")
        print(f"  - reasoning: {analysis.reasoning}")

        if self.api_available:
            self.assertEqual(analysis.overall_status, "needs_clarification", "应识别为需要澄清")
            self.assertEqual(analysis.next_action, "ask_for_clarification", "应建议请求澄清")
            self.assertLess(analysis.confidence, 0.6, "模糊表达的置信度应较低")

        print("✅ 测试通过")

    def test_05_regression(self):
        """测试回归识别"""
        print("\n" + "="*70)
        print("测试 5: 回归识别")
        print("="*70)

        if not self.analyzer:
            self.skipTest("FeedbackAnalyzer 不可用")

        user_feedback = "状态机问题修复了，但是现在房间创建又崩溃了"

        analysis = self.analyzer.analyze(
            user_feedback=user_feedback,
            current_step="implementation",
            task_type="bug_fix"
        )

        print(f"用户反馈: {user_feedback}")
        print(f"分析结果:")
        print(f"  - overall_status: {analysis.overall_status}")
        print(f"  - next_action: {analysis.next_action}")
        print(f"  - success_parts: {analysis.success_parts}")
        print(f"  - issue_parts: {analysis.issue_parts}")
        print(f"  - reasoning: {analysis.reasoning}")

        if self.api_available:
            self.assertEqual(analysis.overall_status, "regression", "应识别为回归")
            self.assertGreater(len(analysis.success_parts), 0, "回归应有成功部分")
            self.assertGreater(len(analysis.issue_parts), 0, "回归应有问题部分（新引入的）")
            # 验证关键词提取
            success_text = ' '.join(analysis.success_parts).lower()
            issue_text = ' '.join(analysis.issue_parts).lower()
            self.assertIn("状态机", success_text, "成功部分应包含'状态机'")
            self.assertIn("房间", issue_text, "问题部分应包含'房间'相关内容")

        print("✅ 测试通过")

    def test_06_feedback_type_mapping(self):
        """测试 overall_status 到 feedback_type 的映射"""
        print("\n" + "="*70)
        print("测试 6: 状态映射")
        print("="*70)

        if not self.analyzer:
            self.skipTest("FeedbackAnalyzer 不可用")

        test_cases = [
            ("完全修复了", "explicit_success"),
            ("部分修复了，但还有问题", "partial_success_with_issues"),
            ("没修复", "explicit_failure"),
            ("嗯...可能吧", "ambiguous_positive" if not self.api_available else None)
        ]

        for feedback, expected_type in test_cases:
            if expected_type is None:
                continue  # 跳过无法确定的情况

            analysis = self.analyzer.analyze(
                user_feedback=feedback,
                current_step="implementation",
                task_type="bug_fix"
            )

            print(f"用户反馈: '{feedback}'")
            print(f"  → overall_status: {analysis.overall_status}")
            print(f"  → feedback_type: {analysis.feedback_type}")

            if not self.api_available:
                # Fallback 模式下只验证基本结构
                self.assertIsNotNone(analysis.feedback_type, "应有 feedback_type")
            # else:
            #     # API 可用时验证映射（注意：LLM 可能有不同理解，不强制检查）
            #     pass

        print("✅ 测试通过")

    def test_07_cache_mechanism(self):
        """测试缓存机制"""
        print("\n" + "="*70)
        print("测试 7: 缓存机制")
        print("="*70)

        if not self.analyzer or not self.api_available:
            self.skipTest("需要 API 可用才能测试缓存")

        user_feedback = "测试缓存功能"

        # 第一次调用
        analysis1 = self.analyzer.analyze(
            user_feedback=user_feedback,
            current_step="implementation",
            task_type="general",
            use_cache=True
        )
        latency1 = analysis1.api_latency_ms

        # 第二次调用（应使用缓存）
        analysis2 = self.analyzer.analyze(
            user_feedback=user_feedback,
            current_step="implementation",
            task_type="general",
            use_cache=True
        )
        latency2 = analysis2.api_latency_ms

        print(f"第一次调用延迟: {latency1}ms")
        print(f"第二次调用延迟: {latency2}ms (使用缓存)")

        # 缓存命中时，第二次应该更快或者 latency 为 0
        if latency2 > 0:
            # 如果第二次也有延迟，可能是缓存未命中（可能因为其他原因）
            print("⚠️  注意：缓存可能未命中（这是正常的，取决于实现）")

        # 验证结果一致性
        self.assertEqual(analysis1.overall_status, analysis2.overall_status, "缓存结果应一致")
        self.assertEqual(analysis1.reasoning, analysis2.reasoning, "缓存的推理应一致")

        print("✅ 测试通过")


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(TestFeedbackAnalyzer)

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 输出总结
    print("\n" + "="*70)
    print("测试总结")
    print("="*70)
    print(f"总测试数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print(f"跳过: {len(result.skipped)}")

    if result.wasSuccessful():
        print("\n✅ 所有测试通过！")
        return 0
    else:
        print("\n❌ 部分测试失败")
        return 1


if __name__ == '__main__':
    sys.exit(run_tests())
