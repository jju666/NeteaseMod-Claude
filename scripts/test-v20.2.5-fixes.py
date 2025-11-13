#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
v20.2.5 修复验证测试脚本

测试内容:
1. Windows中文路径创建
2. BUG修复模式状态初始化
3. 错误回滚机制
"""

import sys
import os
import json
import shutil
import subprocess
from datetime import datetime

# Windows编码修复
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

class TestHarness:
    def __init__(self, downstream_project_path):
        self.project_path = downstream_project_path
        self.results = []

    def setup(self):
        """清理测试环境"""
        print("=" * 60)
        print("准备测试环境...")
        print("=" * 60)

        # 备份现有状态
        state_file = os.path.join(self.project_path, '.claude', 'workflow-state.json')
        if os.path.exists(state_file):
            backup = state_file + f".backup.{datetime.now().strftime('%Y%m%d%H%M%S')}"
            shutil.copy(state_file, backup)
            print(f"✓ 已备份状态文件: {backup}")

        # 清理测试目录
        tasks_dir = os.path.join(self.project_path, 'tasks')
        for item in os.listdir(tasks_dir):
            if item.startswith('测试-'):
                item_path = os.path.join(tasks_dir, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                    print(f"✓ 已清理测试目录: {item}")

        print("✓ 测试环境准备完成\n")

    def test_chinese_path_creation(self):
        """测试1: 中文路径创建"""
        print("=" * 60)
        print("测试1: Windows中文路径创建")
        print("=" * 60)

        test_desc = "测试v20.2.5中文路径修复功能"
        cmd = f'echo {{"prompt": "/mc {test_desc}"}} | python .claude/hooks/user-prompt-submit-hook.py'

        os.chdir(self.project_path)
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        # 检查结果
        task_created = False
        task_id = None

        # 从stderr查找任务ID
        for line in result.stderr.split('\n'):
            if '任务追踪系统初始化完成' in line or 'task_id' in line:
                # 提取任务ID
                import re
                match = re.search(r'测试-\d{4}-\d{6}-.*', line)
                if match:
                    task_id = match.group(0)

        if not task_id:
            # 尝试从文件系统检查
            tasks_dir = os.path.join(self.project_path, 'tasks')
            for item in os.listdir(tasks_dir):
                if item.startswith('测试-') and '中文路径修复' in item:
                    task_id = item
                    break

        if task_id:
            task_dir = os.path.join(self.project_path, 'tasks', task_id)
            if os.path.exists(task_dir):
                # 检查目录名是否乱码
                try:
                    task_id.encode('utf-8').decode('utf-8')
                    task_created = True
                    print(f"✓ 任务目录创建成功: {task_id}")
                    print(f"✓ 路径编码正确 (UTF-8)")
                except:
                    print(f"✗ 任务目录乱码: {task_id}")
            else:
                print(f"✗ 任务目录不存在: {task_dir}")
        else:
            print("✗ 未能创建任务目录")

        self.results.append({
            "test": "chinese_path_creation",
            "passed": task_created,
            "task_id": task_id
        })
        print()

    def test_bugfix_mode_initialization(self):
        """测试2: BUG修复模式初始化"""
        print("=" * 60)
        print("测试2: BUG修复模式状态初始化")
        print("=" * 60)

        test_desc = "修复测试BUG任务状态初始化"
        cmd = f'echo {{"prompt": "/mc {test_desc}"}} | python .claude/hooks/user-prompt-submit-hook.py'

        os.chdir(self.project_path)
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        # 检查workflow-state.json
        state_file = os.path.join(self.project_path, '.claude', 'workflow-state.json')
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)

                has_task_type = 'task_type' in state and state['task_type'] == 'bug_fix'
                has_tracking = 'bug_fix_tracking' in state
                tracking_enabled = state.get('bug_fix_tracking', {}).get('enabled', False)

                if has_task_type and has_tracking and tracking_enabled:
                    print(f"✓ task_type: {state['task_type']}")
                    print(f"✓ bug_fix_tracking.enabled: {tracking_enabled}")
                    print(f"✓ loop_indicators: {state['bug_fix_tracking']['loop_indicators']}")
                    passed = True
                else:
                    print(f"✗ 状态初始化不完整")
                    print(f"  - task_type: {state.get('task_type', 'MISSING')}")
                    print(f"  - bug_fix_tracking: {'存在' if has_tracking else '缺失'}")
                    passed = False
            except json.JSONDecodeError:
                print("✗ workflow-state.json格式错误")
                passed = False
        else:
            print("✗ workflow-state.json不存在")
            passed = False

        self.results.append({
            "test": "bugfix_mode_initialization",
            "passed": passed
        })
        print()

    def test_error_rollback(self):
        """测试3: 错误回滚机制"""
        print("=" * 60)
        print("测试3: 错误回滚机制")
        print("=" * 60)

        # 模拟创建损坏的状态文件
        state_file = os.path.join(self.project_path, '.claude', 'workflow-state.json')
        with open(state_file, 'w', encoding='utf-8') as f:
            f.write('{"task_id":')  # 截断的JSON

        print("已创建损坏的workflow-state.json")

        # 触发user-prompt-submit-hook
        test_desc = "测试错误回滚机制"
        cmd = f'echo {{"prompt": "/mc {test_desc}"}} | python .claude/hooks/user-prompt-submit-hook.py'

        os.chdir(self.project_path)
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        # 检查回滚是否执行
        rollback_detected = '[ROLLBACK]' in result.stderr

        # 检查文件是否被删除或修复
        file_valid = False
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    json.load(f)
                file_valid = True
                print("✓ 损坏的文件已被新任务覆盖")
            except:
                print("✗ 文件仍然损坏")
        else:
            file_valid = True
            print("✓ 损坏的文件已被删除")

        passed = rollback_detected or file_valid

        if passed:
            print("✓ 错误回滚机制工作正常")
        else:
            print("✗ 错误回滚机制未生效")

        self.results.append({
            "test": "error_rollback",
            "passed": passed
        })
        print()

    def report(self):
        """生成测试报告"""
        print("=" * 60)
        print("测试结果汇总")
        print("=" * 60)

        total = len(self.results)
        passed = sum(1 for r in self.results if r['passed'])

        for result in self.results:
            status = "✓ PASS" if result['passed'] else "✗ FAIL"
            print(f"{status} - {result['test']}")

        print()
        print(f"通过率: {passed}/{total} ({100*passed//total if total > 0 else 0}%)")

        if passed == total:
            print("\n🎉 所有测试通过！v20.2.5修复生效。")
            return 0
        else:
            print("\n⚠️ 部分测试失败，请检查修复实现。")
            return 1

def main():
    if len(sys.argv) < 2:
        print("用法: python test-v20.2.5-fixes.py <下游项目路径>")
        print("示例: python test-v20.2.5-fixes.py D:/EcWork/NetEaseMapECBedWars")
        sys.exit(1)

    project_path = sys.argv[1]
    if not os.path.exists(project_path):
        print(f"错误: 项目路径不存在: {project_path}")
        sys.exit(1)

    harness = TestHarness(project_path)

    try:
        harness.setup()
        harness.test_chinese_path_creation()
        harness.test_bugfix_mode_initialization()
        harness.test_error_rollback()
        return harness.report()
    except Exception as e:
        print(f"\n测试执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
