#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
版本号统一脚本 - 将所有v22.0替换为v3.0 Final

使用方法:
    python unit_tests/unify_version.py
"""

import os
import re
import sys
import io

# 修复Windows GBK编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 需要替换的文件模式
FILE_PATTERNS = [
    "templates/.claude/hooks/**/*.py",
    "templates/.claude/commands/*.md.template",
]

# 版本替换映射
VERSION_REPLACEMENTS = [
    (r'v22\.0', 'v3.0 Final'),
    (r'"v22\.0"', '"v3.0 Final"'),
    (r'v21\.0', 'v2.0'),
    (r'v20\.x', 'v1.0'),
]


def unify_version_in_file(filepath):
    """统一单个文件的版本号"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        modified = False

        for pattern, replacement in VERSION_REPLACEMENTS:
            new_content = re.sub(pattern, replacement, content)
            if new_content != content:
                modified = True
                content = new_content

        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ {filepath}")
            return True
        else:
            return False

    except Exception as e:
        print(f"✗ {filepath}: {e}")
        return False


def main():
    """主入口"""
    print("=" * 70)
    print("统一版本命名: v22.0 → v3.0 Final")
    print("=" * 70)
    print()

    hooks_dir = os.path.join(PROJECT_ROOT, "templates", ".claude", "hooks")
    commands_dir = os.path.join(PROJECT_ROOT, "templates", ".claude", "commands")

    modified_files = []

    # 处理所有hook Python文件
    for root, dirs, files in os.walk(hooks_dir):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                if unify_version_in_file(filepath):
                    modified_files.append(filepath)

    # 处理命令模板
    for file in os.listdir(commands_dir):
        if file.endswith('.md.template'):
            filepath = os.path.join(commands_dir, file)
            if unify_version_in_file(filepath):
                modified_files.append(filepath)

    # 输出总结
    print()
    print("=" * 70)
    print(f"总计修改: {len(modified_files)} 个文件")
    print("=" * 70)

    if modified_files:
        print("\n修改的文件列表:")
        for filepath in modified_files:
            rel_path = os.path.relpath(filepath, PROJECT_ROOT)
            print(f"  - {rel_path}")

    print("\n版本统一完成!")


if __name__ == '__main__':
    main()
