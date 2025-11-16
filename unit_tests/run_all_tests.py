#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v3.0 Final 完整测试套件运行器
自动执行所有单元测试并生成测试报告

使用方法:
    python unit_tests/run_all_tests.py

输出:
    - 控制台: 彩色测试结果
    - test_report.txt: 详细测试报告
"""

import sys
import os
import unittest
import io
from datetime import datetime

# 添加项目根目录到路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# 导入所有测试模块
from unit_tests.test_tool_matrix import TestToolMatrixV3, TestBackwardCompatibility
from unit_tests.test_subagent_stop import TestSubagentStopV3
from unit_tests.test_yaml_rules import (
    TestYAMLRulesExistence,
    TestActivationYAML,
    TestPlanningYAML,
    TestImplementationYAML,
    TestFinalizationYAML
)


class ColoredTextTestResult(unittest.TextTestResult):
    """彩色输出的测试结果"""

    # ANSI颜色码
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

    def addSuccess(self, test):
        super().addSuccess(test)
        self.stream.write(f"{self.GREEN}✓{self.RESET} ")
        self.stream.flush()

    def addError(self, test, err):
        super().addError(test, err)
        self.stream.write(f"{self.RED}E{self.RESET} ")
        self.stream.flush()

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.stream.write(f"{self.YELLOW}F{self.RESET} ")
        self.stream.flush()

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.stream.write(f"{self.BLUE}S{self.RESET} ")
        self.stream.flush()


class ColoredTextTestRunner(unittest.TextTestRunner):
    """彩色输出的测试运行器"""
    resultclass = ColoredTextTestResult


def main():
    """主测试入口"""
    print("=" * 70)
    print("NeteaseMod-Claude v3.0 Final 自动化测试套件")
    print("=" * 70)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加所有测试
    test_classes = [
        # Tool Matrix测试
        TestToolMatrixV3,
        TestBackwardCompatibility,
        # SubagentStop测试
        TestSubagentStopV3,
        # YAML规则测试
        TestYAMLRulesExistence,
        TestActivationYAML,
        TestPlanningYAML,
        TestImplementationYAML,
        TestFinalizationYAML,
    ]

    for test_class in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(test_class))

    # 运行测试并捕获输出
    stream = io.StringIO()
    runner = ColoredTextTestRunner(stream=sys.stdout, verbosity=2)
    result = runner.run(suite)

    # 生成测试报告
    report_path = os.path.join(PROJECT_ROOT, "test_report.txt")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("NeteaseMod-Claude v3.0 Final 测试报告\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # 统计信息
        f.write("测试统计:\n")
        f.write(f"  总测试数: {result.testsRun}\n")
        f.write(f"  成功: {result.testsRun - len(result.failures) - len(result.errors)}\n")
        f.write(f"  失败: {len(result.failures)}\n")
        f.write(f"  错误: {len(result.errors)}\n")
        f.write(f"  跳过: {len(result.skipped)}\n\n")

        # 失败详情
        if result.failures:
            f.write("=" * 70 + "\n")
            f.write("失败测试详情:\n")
            f.write("=" * 70 + "\n\n")
            for test, traceback in result.failures:
                f.write(f"测试: {test}\n")
                f.write(f"{traceback}\n\n")

        # 错误详情
        if result.errors:
            f.write("=" * 70 + "\n")
            f.write("错误测试详情:\n")
            f.write("=" * 70 + "\n\n")
            for test, traceback in result.errors:
                f.write(f"测试: {test}\n")
                f.write(f"{traceback}\n\n")

    # 输出总结
    print("\n" + "=" * 70)
    print("测试总结:")
    print("=" * 70)
    print(f"总测试数: {result.testsRun}")
    print(f"✓ 成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    if result.failures:
        print(f"✗ 失败: {len(result.failures)}")
    if result.errors:
        print(f"✗ 错误: {len(result.errors)}")
    if result.skipped:
        print(f"○ 跳过: {len(result.skipped)}")
    print(f"\n详细报告已保存到: {report_path}")
    print("=" * 70)

    # 返回退出码
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
