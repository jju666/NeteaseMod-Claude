#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tool Matrix Unit Tests - 验证v3.0 Final状态机配置
测试范围:
1. 4步语义化状态机 (activation/planning/implementation/finalization)
2. 差异化工作流 (bug_fix vs feature_design)
3. STEP_ORDER顺序验证
4. get_next_step()逻辑验证
"""

import sys
import os
import unittest

# 添加templates/.claude/hooks到路径
HOOK_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'templates', '.claude', 'hooks'
)
sys.path.insert(0, HOOK_DIR)

from core.tool_matrix import (
    STAGE_TOOL_MATRIX,
    STEP_ORDER,
    DIFFERENTIATED_WORKFLOWS,
    get_next_step,
    get_workflow_config,
    get_min_doc_count
)


class TestToolMatrixV3(unittest.TestCase):
    """v3.0 Final Tool Matrix测试"""

    def test_step_order_is_4_steps(self):
        """验证STEP_ORDER包含4个语义化步骤"""
        expected = ["activation", "planning", "implementation", "finalization"]
        self.assertEqual(STEP_ORDER, expected, "STEP_ORDER必须是4步语义化状态机")

    def test_all_stages_exist(self):
        """验证所有4个阶段都在STAGE_TOOL_MATRIX中定义"""
        for stage in STEP_ORDER:
            self.assertIn(stage, STAGE_TOOL_MATRIX, f"缺少{stage}阶段定义")

    def test_activation_stage_config(self):
        """验证activation阶段配置"""
        activation = STAGE_TOOL_MATRIX.get("activation")
        self.assertIsNotNone(activation, "activation阶段未定义")
        self.assertEqual(activation["display_name"], "任务激活")
        self.assertEqual(activation["allowed_tools"], [], "activation阶段AI不应有任何工具")
        self.assertTrue(
            activation["completion_condition"]["auto_advance"],
            "activation应自动推进到planning"
        )
        self.assertEqual(
            activation["completion_condition"]["next_step"],
            "planning"
        )

    def test_planning_stage_config(self):
        """验证planning阶段配置"""
        planning = STAGE_TOOL_MATRIX.get("planning")
        self.assertIsNotNone(planning, "planning阶段未定义")
        self.assertEqual(planning["display_name"], "方案制定")
        self.assertIn("Task", planning["allowed_tools"], "planning应允许Task工具启动子代理")
        self.assertIn("Read", planning["allowed_tools"], "planning应允许Read工具")
        self.assertIn("Grep", planning["allowed_tools"], "planning应允许Grep工具")

    def test_implementation_stage_config(self):
        """验证implementation阶段配置"""
        impl = STAGE_TOOL_MATRIX.get("implementation")
        self.assertIsNotNone(impl, "implementation阶段未定义")
        self.assertEqual(impl["display_name"], "代码实施")
        self.assertIn("Write", impl["allowed_tools"], "implementation应允许Write工具")
        self.assertIn("Edit", impl["allowed_tools"], "implementation应允许Edit工具")
        self.assertIn("Bash", impl["allowed_tools"], "implementation应允许Bash工具")

    def test_finalization_stage_config(self):
        """验证finalization阶段配置"""
        final = STAGE_TOOL_MATRIX.get("finalization")
        self.assertIsNotNone(final, "finalization阶段未定义")
        self.assertEqual(final["display_name"], "收尾归档")
        self.assertEqual(
            final["allowed_tools"],
            ["Task", "Read"],
            "finalization父代理只能Task+Read"
        )

    def test_differentiated_workflows_exist(self):
        """验证差异化工作流配置存在"""
        self.assertIn("bug_fix", DIFFERENTIATED_WORKFLOWS)
        self.assertIn("feature_design", DIFFERENTIATED_WORKFLOWS)

    def test_bug_fix_workflow(self):
        """验证BUG修复工作流配置"""
        bug_fix = DIFFERENTIATED_WORKFLOWS["bug_fix"]["planning"]
        self.assertEqual(bug_fix["min_doc_count"], 0, "BUG修复无需强制文档")
        self.assertTrue(bug_fix["expert_review_required"], "BUG修复需要专家审查")
        self.assertTrue(bug_fix["expert_review_auto_trigger"], "BUG修复自动触发专家审查")

    def test_feature_design_workflow(self):
        """验证功能设计工作流配置"""
        feature = DIFFERENTIATED_WORKFLOWS["feature_design"]["planning"]
        self.assertEqual(feature["min_doc_count"], 3, "功能设计强制3个文档")
        self.assertTrue(feature["gameplay_pack_matching"], "功能设计需要玩法包匹配")
        self.assertTrue(feature["doc_query_subagent"], "功能设计需要文档查询子代理")

    def test_get_next_step_logic(self):
        """验证get_next_step()状态推进逻辑"""
        self.assertEqual(get_next_step("activation"), "planning")
        self.assertEqual(get_next_step("planning"), "implementation")
        self.assertEqual(get_next_step("implementation"), "finalization")
        self.assertIsNone(get_next_step("finalization"), "finalization是最后一步")

    def test_get_workflow_config(self):
        """验证get_workflow_config()函数"""
        bug_config = get_workflow_config("bug_fix", "planning")
        self.assertIsNotNone(bug_config)
        self.assertEqual(bug_config["min_doc_count"], 0)

        feature_config = get_workflow_config("feature_design", "planning")
        self.assertIsNotNone(feature_config)
        self.assertEqual(feature_config["min_doc_count"], 3)

        # 未知任务类型返回feature_design默认值
        default_config = get_workflow_config("unknown_type", "planning")
        self.assertEqual(default_config["min_doc_count"], 3)

    def test_get_min_doc_count(self):
        """验证get_min_doc_count()函数"""
        self.assertEqual(get_min_doc_count("bug_fix"), 0)
        self.assertEqual(get_min_doc_count("feature_design"), 3)
        # 未知类型使用feature_design默认值(保守策略)
        self.assertEqual(get_min_doc_count("unknown_type"), 3, "未知类型使用feature_design默认值")


class TestBackwardCompatibility(unittest.TestCase):
    """向后兼容性测试"""

    def test_step_mapping_exists(self):
        """验证STEP_MAPPING向后兼容v21.0/v22.0"""
        from core.task_meta_manager import TaskMetaManager

        # STEP_MAPPING是TaskMetaManager的类成员变量
        STEP_MAPPING = TaskMetaManager.STEP_MAPPING

        # 检查v21.0旧命名映射
        self.assertEqual(STEP_MAPPING.get("step0_activation"), "activation")
        self.assertEqual(STEP_MAPPING.get("step1_plan"), "planning")
        self.assertEqual(STEP_MAPPING.get("step2_implementation"), "implementation")
        self.assertEqual(STEP_MAPPING.get("step3_finalization"), "finalization")


if __name__ == '__main__':
    unittest.main(verbosity=2)
