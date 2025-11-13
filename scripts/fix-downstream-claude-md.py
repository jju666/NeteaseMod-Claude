#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复下游项目 CLAUDE.md 脚本
功能: 为下游项目的 CLAUDE.md 添加"必须使用 /mc 命令"提醒

使用:
    python scripts/fix-downstream-claude-md.py <project_path>

示例:
    python scripts/fix-downstream-claude-md.py D:/EcWork/NetEaseMapECBedWars
"""

import sys
import os
import re
from datetime import datetime
import io

# 修复Windows GBK编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


CRITICAL_SECTION = """
## ⚠️ **CRITICAL: 工作流规范**

### 🚨 强制使用 `/mc` 命令

**所有开发任务必须使用 `/mc` 命令启动**:

```bash
# ✅ 正确
/mc 实现玩家拾起钻石后在头顶爆炸的功能
/mc 修复System初始化错误

# ❌ 错误
实现玩家拾起钻石后在头顶爆炸的功能  # 缺少 /mc 前缀
```

**原因**:
1. Hook系统只在 `/mc` 命令时激活任务追踪基础设施
2. 没有 `/mc` 前缀会导致:
   - ❌ Hook不会创建任务目录和追踪文件
   - ❌ Hook不会注入玩法包代码实现
   - ❌ Hook不会执行CRITICAL规范检查
   - ❌ AI可能跳过步骤2(查阅文档)
   - ❌ 无法享受Token节省85-90%的优势

**工作流文档**: 详见 [.claude/commands/mc.md](./.claude/commands/mc.md)

---
"""


def backup_file(file_path):
    """备份文件"""
    backup_path = file_path + '.bak'
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(u"✅ 已备份原文件到: {}".format(backup_path))
    return backup_path


def fix_claude_md(file_path):
    """修复 CLAUDE.md"""
    if not os.path.exists(file_path):
        print(u"❌ 文件不存在: {}".format(file_path))
        return False

    # 读取原文件
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查是否已存在CRITICAL章节
    if u'⚠️ **CRITICAL: 工作流规范**' in content:
        print(u"⚠️ 文件已包含CRITICAL章节,跳过修复")
        return False

    # 备份原文件
    backup_file(file_path)

    # 查找插入位置(在第一个 --- 之后)
    lines = content.split('\n')
    insert_index = -1

    # 找到前置信息块的结束位置(第一个 --- 之后)
    found_separator = False
    for i, line in enumerate(lines):
        if line.strip() == '---':
            if found_separator:
                # 第二个 ---,这是插入位置
                insert_index = i + 1
                break
            else:
                found_separator = True

    if insert_index == -1:
        print(u"⚠️ 未找到合适的插入位置,在文件开头插入")
        insert_index = 0

    # 插入CRITICAL章节
    lines.insert(insert_index, CRITICAL_SECTION.strip())
    new_content = '\n'.join(lines)

    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(u"✅ 已成功修复 CLAUDE.md")
    return True


def fix_project(project_path):
    """修复整个项目"""
    print(u"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(u"修复项目: {}".format(project_path))
    print(u"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    # 检查项目是否存在
    if not os.path.exists(project_path):
        print(u"❌ 项目路径不存在: {}".format(project_path))
        return False

    # 查找 CLAUDE.md
    claude_md_path = os.path.join(project_path, 'CLAUDE.md')

    if not os.path.exists(claude_md_path):
        print(u"⚠️ 未找到 CLAUDE.md,跳过此项目")
        return False

    # 修复 CLAUDE.md
    result = fix_claude_md(claude_md_path)

    if result:
        print(u"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(u"✅ 修复完成!")
        print(u"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        print(u"**接下来**:")
        print(u"1. 查看修复后的文件: {}".format(claude_md_path))
        print(u"2. 如有问题,可恢复备份: {}.bak".format(claude_md_path))
        print(u"3. 重新使用 `/mc` 命令启动任务\n")
    else:
        print(u"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(u"⚠️ 无需修复或修复失败")
        print(u"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    return result


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    project_path = sys.argv[1]
    fix_project(project_path)


if __name__ == '__main__':
    main()
