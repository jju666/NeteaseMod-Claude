#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAML Rules Unit Tests - 验证v3.0 Final规则文件
测试范围:
1. 4个YAML文件存在性
2. YAML格式正确性
3. 关键字段完整性
4. 差异化流程配置验证
"""

import sys
import os
import unittest
import yaml

# 规则文件目录
RULES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'templates', '.claude', 'rules'
)


class TestYAMLRulesExistence(unittest.TestCase):
    """YAML规则文件存在性测试"""

    def test_activation_yaml_exists(self):
        """验证activation.yaml存在"""
        path = os.path.join(RULES_DIR, "activation.yaml")
        self.assertTrue(os.path.exists(path), "activation.yaml文件缺失")

    def test_planning_yaml_exists(self):
        """验证planning.yaml存在"""
        path = os.path.join(RULES_DIR, "planning.yaml")
        self.assertTrue(os.path.exists(path), "planning.yaml文件缺失")

    def test_implementation_yaml_exists(self):
        """验证implementation.yaml存在"""
        path = os.path.join(RULES_DIR, "implementation.yaml")
        self.assertTrue(os.path.exists(path), "implementation.yaml文件缺失")

    def test_finalization_yaml_exists(self):
        """验证finalization.yaml存在"""
        path = os.path.join(RULES_DIR, "finalization.yaml")
        self.assertTrue(os.path.exists(path), "finalization.yaml文件缺失")


class TestActivationYAML(unittest.TestCase):
    """Activation阶段YAML测试"""

    @classmethod
    def setUpClass(cls):
        """加载activation.yaml"""
        with open(os.path.join(RULES_DIR, "activation.yaml"), 'r', encoding='utf-8') as f:
            cls.config = yaml.safe_load(f)

    def test_display_name(self):
        """验证display_name"""
        self.assertEqual(self.config["display_name"], "任务激活")

    def test_task_type_detection_exists(self):
        """验证task_type_detection配置存在"""
        self.assertIn("task_type_detection", self.config)

    def test_bug_fix_keywords(self):
        """验证bug_fix关键词"""
        keywords = self.config["task_type_detection"]["bug_fix"]["keywords"]
        self.assertIn("BUG", keywords)
        self.assertIn("修复", keywords)
        self.assertIn("bug", keywords)
        self.assertIn("fix", keywords)

    def test_feature_design_keywords(self):
        """验证feature_design关键词"""
        keywords = self.config["task_type_detection"]["feature_design"]["keywords"]
        self.assertIn("实现", keywords)
        self.assertIn("添加", keywords)
        self.assertIn("功能", keywords)
        self.assertIn("feature", keywords)

    def test_completion_condition(self):
        """验证自动推进配置"""
        completion = self.config["completion_condition"]
        self.assertEqual(completion["type"], "automatic")
        self.assertTrue(completion["auto_advance"])
        self.assertEqual(completion["next_step"], "planning")


class TestPlanningYAML(unittest.TestCase):
    """Planning阶段YAML测试"""

    @classmethod
    def setUpClass(cls):
        """加载planning.yaml"""
        with open(os.path.join(RULES_DIR, "planning.yaml"), 'r', encoding='utf-8') as f:
            cls.config = yaml.safe_load(f)

    def test_display_name(self):
        """验证display_name"""
        self.assertEqual(self.config["display_name"], "方案制定")

    def test_allowed_tools(self):
        """验证允许的工具"""
        tools = self.config["allowed_tools"]
        self.assertIn("Task", tools)
        self.assertIn("Read", tools)
        self.assertIn("Grep", tools)
        self.assertIn("Glob", tools)

    def test_bug_fix_rules(self):
        """验证BUG修复规则"""
        bug_fix = self.config["bug_fix_rules"]
        self.assertEqual(bug_fix["min_doc_count"], 0, "BUG修复无需强制文档")
        self.assertTrue(bug_fix["expert_review_required"], "需要专家审查")
        self.assertIn("方案制定完成", bug_fix["expert_review_trigger"])

    def test_feature_design_rules(self):
        """验证功能设计规则"""
        feature = self.config["feature_design_rules"]
        self.assertEqual(feature["min_doc_count"], 3, "功能设计强制3个文档")
        self.assertTrue(feature["gameplay_pack_matching"], "需要玩法包匹配")
        self.assertTrue(feature["doc_query_subagent"], "需要文档查询子代理")

    def test_completion_condition(self):
        """验证用户确认推进配置"""
        completion = self.config["completion_condition"]
        self.assertEqual(completion["type"], "user_confirmation")
        self.assertFalse(completion["auto_advance"])
        self.assertEqual(completion["next_step"], "implementation")


class TestImplementationYAML(unittest.TestCase):
    """Implementation阶段YAML测试"""

    @classmethod
    def setUpClass(cls):
        """加载implementation.yaml"""
        with open(os.path.join(RULES_DIR, "implementation.yaml"), 'r', encoding='utf-8') as f:
            cls.config = yaml.safe_load(f)

    def test_display_name(self):
        """验证display_name"""
        self.assertEqual(self.config["display_name"], "代码实施")

    def test_allowed_tools(self):
        """验证允许的工具"""
        tools = self.config["allowed_tools"]
        self.assertIn("Write", tools)
        self.assertIn("Edit", tools)
        self.assertIn("Bash", tools)

    def test_round_based_iteration(self):
        """验证轮次循环配置"""
        iteration = self.config["round_based_iteration"]
        self.assertTrue(iteration["enabled"])
        self.assertEqual(iteration["max_rounds"], 10)
        self.assertEqual(iteration["round_boundary"], "Stop")
        self.assertIn("code_changes", iteration["metrics_tracking"])
        self.assertIn("user_feedback", iteration["metrics_tracking"])

    def test_expert_review_trigger(self):
        """验证专家审查触发条件"""
        trigger = self.config["expert_review_trigger"]
        self.assertEqual(trigger["same_file_edits_threshold"], 5)
        self.assertEqual(trigger["consecutive_failures"], 3)
        self.assertEqual(trigger["max_rounds_exceeded"], 10)

    def test_completion_keywords(self):
        """验证完成关键词"""
        completion = self.config["completion_condition"]
        keywords = completion["confirmation_keywords"]
        self.assertIn("/mc-confirm", keywords)
        self.assertIn("已修复", keywords)
        self.assertIn("修复完成", keywords)


class TestFinalizationYAML(unittest.TestCase):
    """Finalization阶段YAML测试"""

    @classmethod
    def setUpClass(cls):
        """加载finalization.yaml"""
        with open(os.path.join(RULES_DIR, "finalization.yaml"), 'r', encoding='utf-8') as f:
            cls.config = yaml.safe_load(f)

    def test_display_name(self):
        """验证display_name"""
        self.assertEqual(self.config["display_name"], "收尾归档")

    def test_parent_allowed_tools(self):
        """验证父代理只能Task+Read"""
        tools = self.config["allowed_tools"]
        self.assertEqual(tools, ["Task", "Read"], "父代理只能Task和Read")

    def test_subagent_allowed_tools(self):
        """验证子代理工具权限"""
        subagent_tools = self.config["subagent_rules"]["allowed_tools"]
        self.assertIn("Write", subagent_tools)
        self.assertIn("Edit", subagent_tools)
        self.assertIn("Read", subagent_tools)
        self.assertIn("Grep", subagent_tools)

    def test_archiving_config(self):
        """验证归档配置"""
        archiving = self.config["archiving"]
        self.assertTrue(archiving["enabled"])
        self.assertEqual(archiving["archive_path"], "tasks/{task_id}/")
        self.assertIn(".task-meta.json", archiving["archive_contents"])
        self.assertIn(".task-active.json", archiving["cleanup_after_archive"])

    def test_completion_condition(self):
        """验证子代理完成触发条件"""
        completion = self.config["completion_condition"]
        self.assertEqual(completion["type"], "subagent_completion")
        self.assertEqual(
            completion["trigger_expr"],
            "steps.finalization.status == 'completed'"
        )
        self.assertFalse(completion["auto_advance"])
        self.assertIsNone(completion["next_step"], "finalization是最后一步")


if __name__ == '__main__':
    unittest.main(verbosity=2)
