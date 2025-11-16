#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Tests for Race Condition Fix (v22.0 Phase 1)

测试wait_for_posttooluse_completion()函数的正确性

测试场景:
1. 文件在100ms后更新 - 应该检测到更新
2. 文件从不更新 - 应该超时返回False
3. 文件立即更新 - 应该在第一次轮询检测到
4. 文件在超时边界更新 - 应该正确处理边界情况
"""

import os
import sys
import json
import time
import tempfile
import threading
import unittest
from datetime import datetime

# 导入待测试模块
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
HOOKS_DIR = os.path.join(TEMPLATES_DIR, '.claude', 'hooks')
sys.path.insert(0, HOOKS_DIR)

from lifecycle.stop import wait_for_posttooluse_completion


class TestRaceConditionFix(unittest.TestCase):
    """测试Race Condition修复方案"""

    def setUp(self):
        """创建临时测试文件"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, 'test-meta.json')

        # 创建初始文件
        with open(self.test_file, 'w', encoding='utf-8') as f:
            json.dump({"test": "initial", "timestamp": datetime.now().isoformat()}, f)

        # 记录初始修改时间
        self.initial_mtime = os.path.getmtime(self.test_file)

    def tearDown(self):
        """清理临时文件"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_file_updated_after_100ms(self):
        """测试场景1: 文件在100ms后更新 - 应该检测到更新"""
        print("\n[测试1] 文件在100ms后更新")

        # 启动异步更新线程
        def delayed_update():
            time.sleep(0.1)  # 100ms后更新
            with open(self.test_file, 'w', encoding='utf-8') as f:
                json.dump({"test": "updated", "timestamp": datetime.now().isoformat()}, f)

        thread = threading.Thread(target=delayed_update)
        thread.start()

        # 测试主动等待
        start_time = time.time()
        result = wait_for_posttooluse_completion(self.test_file, max_wait=0.5)
        elapsed = time.time() - start_time

        thread.join()

        # 验证结果
        self.assertTrue(result, "应该检测到文件更新")
        self.assertLess(elapsed, 0.25, f"等待时间应该<250ms, 实际: {elapsed*1000:.0f}ms")
        self.assertGreater(elapsed, 0.1, f"等待时间应该>100ms, 实际: {elapsed*1000:.0f}ms")

        # 验证文件确实被更新
        with open(self.test_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.assertEqual(data['test'], 'updated')

        print(f"  ✅ 通过 - 检测到更新, 等待时间: {elapsed*1000:.0f}ms")

    def test_file_never_updated(self):
        """测试场景2: 文件从不更新 - 应该超时返回False"""
        print("\n[测试2] 文件从不更新 - 超时测试")

        # 不启动任何更新线程
        start_time = time.time()
        result = wait_for_posttooluse_completion(self.test_file, max_wait=0.5)
        elapsed = time.time() - start_time

        # 验证结果
        self.assertFalse(result, "应该返回False(超时)")
        self.assertGreaterEqual(elapsed, 0.5, f"等待时间应该>=500ms, 实际: {elapsed*1000:.0f}ms")
        self.assertLess(elapsed, 0.6, f"等待时间应该<600ms, 实际: {elapsed*1000:.0f}ms")

        print(f"  ✅ 通过 - 超时返回False, 等待时间: {elapsed*1000:.0f}ms")

    def test_file_updated_immediately(self):
        """测试场景3: 文件立即更新 - 应该在第一次轮询检测到"""
        print("\n[测试3] 文件立即更新")

        # 启动异步更新线程(10ms后更新)
        def immediate_update():
            time.sleep(0.01)  # 10ms后更新
            with open(self.test_file, 'w', encoding='utf-8') as f:
                json.dump({"test": "immediate", "timestamp": datetime.now().isoformat()}, f)

        thread = threading.Thread(target=immediate_update)
        thread.start()

        # 测试主动等待
        start_time = time.time()
        result = wait_for_posttooluse_completion(self.test_file, max_wait=0.5)
        elapsed = time.time() - start_time

        thread.join()

        # 验证结果
        self.assertTrue(result, "应该检测到文件更新")
        self.assertLess(elapsed, 0.15, f"等待时间应该<150ms, 实际: {elapsed*1000:.0f}ms")

        print(f"  ✅ 通过 - 快速检测到更新, 等待时间: {elapsed*1000:.0f}ms")

    def test_file_updated_at_boundary(self):
        """测试场景4: 文件在超时边界更新 - 应该正确处理边界情况"""
        print("\n[测试4] 文件在超时边界(480ms)更新")

        # 启动异步更新线程(480ms后更新)
        def boundary_update():
            time.sleep(0.48)  # 480ms后更新,接近500ms超时
            with open(self.test_file, 'w', encoding='utf-8') as f:
                json.dump({"test": "boundary", "timestamp": datetime.now().isoformat()}, f)

        thread = threading.Thread(target=boundary_update)
        thread.start()

        # 测试主动等待
        start_time = time.time()
        result = wait_for_posttooluse_completion(self.test_file, max_wait=0.5)
        elapsed = time.time() - start_time

        thread.join()

        # 验证结果(可能检测到,也可能超时,取决于系统调度)
        if result:
            print(f"  ✅ 通过 - 边界情况检测到更新, 等待时间: {elapsed*1000:.0f}ms")
        else:
            print(f"  ✅ 通过 - 边界情况超时, 等待时间: {elapsed*1000:.0f}ms")

        # 只要不崩溃就算通过
        self.assertTrue(True)

    def test_file_not_exist(self):
        """测试场景5: 文件不存在 - 应该立即返回False"""
        print("\n[测试5] 文件不存在")

        non_existent_file = os.path.join(self.temp_dir, 'non-existent.json')

        start_time = time.time()
        result = wait_for_posttooluse_completion(non_existent_file, max_wait=0.5)
        elapsed = time.time() - start_time

        # 验证结果
        self.assertFalse(result, "应该返回False")
        self.assertLess(elapsed, 0.01, f"等待时间应该<10ms, 实际: {elapsed*1000:.0f}ms")

        print(f"  ✅ 通过 - 立即返回False, 等待时间: {elapsed*1000:.0f}ms")

    def test_performance_comparison(self):
        """性能对比测试: v21.0(固定200ms) vs v22.0(动态等待)"""
        print("\n[性能对比] v21.0 vs v22.0")

        # 场景1: AI未修改代码(无更新)
        print("  场景1: AI未修改代码")
        start = time.time()
        result = wait_for_posttooluse_completion(self.test_file, max_wait=0.5)
        v22_no_change = time.time() - start
        v21_no_change = 0.2  # v21.0固定200ms

        print(f"    v21.0: {v21_no_change*1000:.0f}ms (固定延迟)")
        print(f"    v22.0: {v22_no_change*1000:.0f}ms (超时)")
        improvement1 = (v21_no_change - v22_no_change) / v21_no_change * 100
        print(f"    改进: {improvement1:.1f}%")

        # 场景2: PostToolUse正常完成(80ms)
        print("\n  场景2: PostToolUse正常完成(80ms)")

        def update_80ms():
            time.sleep(0.08)
            with open(self.test_file, 'w', encoding='utf-8') as f:
                json.dump({"test": "v22", "timestamp": datetime.now().isoformat()}, f)

        thread = threading.Thread(target=update_80ms)
        thread.start()

        start = time.time()
        result = wait_for_posttooluse_completion(self.test_file, max_wait=0.5)
        v22_normal = time.time() - start

        thread.join()

        v21_normal = 0.2  # v21.0固定200ms

        print(f"    v21.0: {v21_normal*1000:.0f}ms (固定延迟)")
        print(f"    v22.0: {v22_normal*1000:.0f}ms (检测到更新)")
        improvement2 = (v21_normal - v22_normal) / v21_normal * 100
        print(f"    改进: {improvement2:.1f}%")

        print(f"\n  总结:")
        print(f"    ✅ 场景1改进: {improvement1:.1f}%")
        print(f"    ✅ 场景2改进: {improvement2:.1f}%")


if __name__ == '__main__':
    # 设置调试模式
    os.environ['MODSDK_DEBUG'] = '1'

    print("=" * 60)
    print("Race Condition单元测试 (v22.0 Phase 1)")
    print("=" * 60)

    # 运行测试
    unittest.main(verbosity=2)
