#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Tests for Semantic Naming Migration (v22.0 Phase 2)

测试v21.0 → v22.0语义化命名转换的正确性

测试场景:
1. v21.0数据转换 - step0/step1/step2/step3 → activation/planning/implementation/finalization
2. v20.x数据转换 - 兼容更早版本
3. 幂等性测试 - 多次转换结果相同
4. steps字典转换 - 嵌套字段正确转换
5. bug_fix_tracking转换 - iterations中的step字段正确转换
"""

import os
import sys
import json
import unittest
import io
from datetime import datetime

# 修复Windows GBK编码问题:强制使用UTF-8输出
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 导入待测试模块
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
HOOKS_DIR = os.path.join(TEMPLATES_DIR, '.claude', 'hooks')
sys.path.insert(0, HOOKS_DIR)

from core.task_meta_manager import TaskMetaManager


class TestSemanticMigration(unittest.TestCase):
    """测试语义化命名迁移"""

    def setUp(self):
        """初始化测试环境"""
        self.mgr = TaskMetaManager()

    def test_v21_to_v22_basic_conversion(self):
        """测试场景1: v21.0基础字段转换"""
        print("\n[测试1] v21.0 → v22.0基础字段转换")

        v21_data = {
            "task_id": "test-001",
            "architecture_version": "v21.0",
            "current_step": "step2_implementation",
            "steps": {
                "step0_activation": {"status": "completed"},
                "step1_plan": {"status": "completed"},
                "step2_implementation": {"status": "in_progress"}
            }
        }

        # 执行转换
        v22_data = self.mgr._convert_to_v22_format(v21_data)

        # 验证结果
        self.assertEqual(v22_data['current_step'], 'implementation')
        self.assertEqual(v22_data['architecture_version'], 'v22.0')
        self.assertIn('activation', v22_data['steps'])
        self.assertIn('planning', v22_data['steps'])
        self.assertIn('implementation', v22_data['steps'])
        self.assertEqual(v22_data['migrated_from'], 'v21.0')

        print("  ✅ 通过 - current_step转换正确")
        print("  ✅ 通过 - steps字典转换正确")
        print("  ✅ 通过 - 版本号更新正确")

    def test_v21_step3_execute_compatibility(self):
        """测试场景2: v21.0 step3_execute兼容性"""
        print("\n[测试2] v21.0 step3_execute → implementation兼容")

        v21_data = {
            "task_id": "test-002",
            "architecture_version": "v21.0",
            "current_step": "step3_execute",
            "steps": {
                "step0_activation": {"status": "completed"},
                "step1_plan": {"status": "completed"},
                "step3_execute": {"status": "in_progress"}
            }
        }

        # 执行转换
        v22_data = self.mgr._convert_to_v22_format(v21_data)

        # 验证结果
        self.assertEqual(v22_data['current_step'], 'implementation')
        self.assertIn('implementation', v22_data['steps'])

        print("  ✅ 通过 - step3_execute正确转换为implementation")

    def test_idempotent_conversion(self):
        """测试场景3: 幂等性 - 多次转换结果相同"""
        print("\n[测试3] 幂等性测试")

        v21_data = {
            "task_id": "test-003",
            "architecture_version": "v21.0",
            "current_step": "step1_plan",
            "steps": {
                "step0_activation": {"status": "completed"},
                "step1_plan": {"status": "in_progress"}
            }
        }

        # 第一次转换
        v22_data_1 = self.mgr._convert_to_v22_format(dict(v21_data))

        # 第二次转换（对已转换的数据再次转换）
        v22_data_2 = self.mgr._convert_to_v22_format(dict(v22_data_1))

        # 第三次转换
        v22_data_3 = self.mgr._convert_to_v22_format(dict(v22_data_2))

        # 验证结果
        self.assertEqual(v22_data_1['current_step'], v22_data_2['current_step'])
        self.assertEqual(v22_data_2['current_step'], v22_data_3['current_step'])
        self.assertEqual(v22_data_1['current_step'], 'planning')

        print("  ✅ 通过 - 多次转换结果一致")
        print(f"  current_step: {v22_data_1['current_step']} → {v22_data_2['current_step']} → {v22_data_3['current_step']}")

    def test_bug_fix_tracking_conversion(self):
        """测试场景4: bug_fix_tracking中的step字段转换"""
        print("\n[测试4] bug_fix_tracking.iterations转换")

        v21_data = {
            "task_id": "test-004",
            "architecture_version": "v21.0",
            "current_step": "step2_implementation",
            "bug_fix_tracking": {
                "iterations": [
                    {
                        "round": 1,
                        "step": "step2_implementation",
                        "code_changes": ["file1.js", "file2.js"]
                    },
                    {
                        "round": 2,
                        "step": "step2_implementation",
                        "code_changes": ["file3.js"]
                    }
                ]
            }
        }

        # 执行转换
        v22_data = self.mgr._convert_to_v22_format(v21_data)

        # 验证结果
        iterations = v22_data['bug_fix_tracking']['iterations']
        self.assertEqual(iterations[0]['step'], 'implementation')
        self.assertEqual(iterations[1]['step'], 'implementation')

        print("  ✅ 通过 - iterations中的step字段正确转换")
        print(f"  第1轮: {iterations[0]['step']}")
        print(f"  第2轮: {iterations[1]['step']}")

    def test_complete_workflow_data(self):
        """测试场景5: 完整工作流数据转换"""
        print("\n[测试5] 完整工作流数据转换")

        v21_complete = {
            "task_id": "20251115-修复玩家死亡BUG",
            "architecture_version": "v21.0",
            "task_type": "bug_fix",
            "current_step": "step3_finalization",
            "steps": {
                "step0_activation": {
                    "status": "completed",
                    "started_at": "2025-11-15T10:00:00",
                    "completed_at": "2025-11-15T10:00:01"
                },
                "step1_plan": {
                    "status": "completed",
                    "started_at": "2025-11-15T10:00:01",
                    "completed_at": "2025-11-15T10:05:00",
                    "plan_content": "修复玩家死亡背包物品未掉落的问题",
                    "expert_review": {
                        "approved": True,
                        "issues": []
                    }
                },
                "step2_implementation": {
                    "status": "completed",
                    "started_at": "2025-11-15T10:05:00",
                    "completed_at": "2025-11-15T10:15:00"
                },
                "step3_finalization": {
                    "status": "in_progress",
                    "started_at": "2025-11-15T10:15:00"
                }
            },
            "bug_fix_tracking": {
                "iterations": [
                    {"round": 1, "step": "step2_implementation", "code_changes": ["player_death.js"]},
                    {"round": 2, "step": "step2_implementation", "code_changes": ["inventory.js"]}
                ]
            }
        }

        # 执行转换
        v22_complete = self.mgr._convert_to_v22_format(v21_complete)

        # 验证所有关键字段
        self.assertEqual(v22_complete['current_step'], 'finalization')
        self.assertIn('activation', v22_complete['steps'])
        self.assertIn('planning', v22_complete['steps'])
        self.assertIn('implementation', v22_complete['steps'])
        self.assertIn('finalization', v22_complete['steps'])

        # 验证planning步骤的内容完整性
        planning = v22_complete['steps']['planning']
        self.assertEqual(planning['status'], 'completed')
        self.assertIn('expert_review', planning)

        # 验证bug_fix_tracking
        iterations = v22_complete['bug_fix_tracking']['iterations']
        self.assertEqual(iterations[0]['step'], 'implementation')
        self.assertEqual(iterations[1]['step'], 'implementation')

        print("  ✅ 通过 - current_step: finalization")
        print("  ✅ 通过 - 所有步骤字段正确转换")
        print("  ✅ 通过 - planning内容完整")
        print("  ✅ 通过 - bug_fix_tracking正确转换")

    def test_unknown_step_preservation(self):
        """测试场景6: 未知步骤名保留原样"""
        print("\n[测试6] 未知步骤名保留测试")

        v21_data = {
            "task_id": "test-006",
            "architecture_version": "v21.0",
            "current_step": "custom_step_xyz",  # 未知步骤
            "steps": {
                "custom_step_xyz": {"status": "in_progress"},
                "step1_plan": {"status": "completed"}
            }
        }

        # 执行转换
        v22_data = self.mgr._convert_to_v22_format(v21_data)

        # 验证结果 - 未知步骤应保留原样
        self.assertEqual(v22_data['current_step'], 'custom_step_xyz')
        self.assertIn('custom_step_xyz', v22_data['steps'])
        self.assertIn('planning', v22_data['steps'])  # 已知步骤正常转换

        print("  ✅ 通过 - 未知步骤名保留: custom_step_xyz")
        print("  ✅ 通过 - 已知步骤正常转换: step1_plan → planning")


if __name__ == '__main__':
    print("=" * 60)
    print("语义化命名迁移单元测试 (v22.0 Phase 2)")
    print("=" * 60)

    # 运行测试
    unittest.main(verbosity=2)
