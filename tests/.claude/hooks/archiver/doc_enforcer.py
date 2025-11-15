#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Post Archive Doc Enforcer - 文档创建验证器 (v20.1.1)

触发时机: post-archive-hook执行后 (PostToolUse链式调用)
职责:
1. 对比归档前后的markdown目录文件快照
2. 验证是否有文档被创建或更新
3. 如果没有任何文档变更,阻止操作并要求AI创建文档

设计理念:
- 100%强制文档创建执行
- 防止AI以"无合适文档"为理由跳过
- 仅对非测试任务强制执行

v20.1.1 核心功能:
- 读取归档前快照(.claude/.doc-snapshot.json)
- 扫描当前markdown目录
- 对比新增/修改的文档
- 如果无变更,阻断操作并注入强制提示
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime
import io

# Windows编码修复
if sys.platform == 'win32':
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 导入日志记录器
try:
    from hook_logger import HookLogger
except ImportError:
    class HookLogger:
        def __init__(self, name): self.name = name
        def start(self): pass
        def finish(self, success=True, message=""): pass
        def info(self, msg, data=None): pass
        def error(self, msg, err=None): pass
        def decision(self, t, r, d=None): pass

def load_doc_snapshot(project_path):
    """加载归档前文档快照"""
    snapshot_file = Path(project_path) / ".claude" / ".doc-snapshot.json"

    if not snapshot_file.exists():
        return None

    try:
        with open(snapshot_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None

def scan_markdown_dir(project_path):
    """扫描当前markdown目录"""
    markdown_dir = Path(project_path) / "markdown"
    current_snapshot = {}

    if markdown_dir.exists():
        for md_file in markdown_dir.glob("**/*.md"):
            try:
                current_snapshot[str(md_file)] = {
                    "mtime": md_file.stat().st_mtime,
                    "size": md_file.stat().st_size
                }
            except:
                pass

    return current_snapshot

def compare_snapshots(before, after):
    """对比快照,返回新增和修改的文件"""
    if before is None:
        # 首次归档,没有快照,跳过验证
        return None, []

    new_files = []
    modified_files = []

    for file_path, file_info in after.items():
        if file_path not in before:
            new_files.append(file_path)
        elif file_info['mtime'] > before[file_path]['mtime'] or file_info['size'] != before[file_path]['size']:
            modified_files.append(file_path)

    return new_files, modified_files

def is_test_task(task_desc):
    """判断是否为测试任务"""
    test_keywords = ['测试', '试验', 'test', 'demo', '演示']
    task_lower = task_desc.lower()
    return any(kw in task_lower for kw in test_keywords)

def find_latest_archived_task(project_path):
    """查找最新归档的任务"""
    archived_dir = Path(project_path) / "tasks" / u"已归档"

    if not archived_dir.exists():
        return None, None

    task_dirs = [
        d for d in archived_dir.iterdir()
        if d.is_dir() and (d.name.startswith("task-") or d.name.startswith(u"任务-"))
    ]

    if not task_dirs:
        return None, None

    # 返回最新归档的任务
    latest_task = max(task_dirs, key=lambda d: d.stat().st_mtime)

    # 读取任务元数据
    meta_file = latest_task / ".task-meta.json"
    if meta_file.exists():
        try:
            with open(meta_file, 'r', encoding='utf-8') as f:
                meta = json.load(f)
            return latest_task, meta
        except:
            pass

    return latest_task, None

def main():
    logger = HookLogger("post-archive-doc-enforcer")
    logger.start()

    try:
        # 读取Hook输入
        hook_input = json.load(sys.stdin)
        project_path = hook_input.get('cwd', os.getcwd())

        # 加载归档前快照
        before_snapshot = load_doc_snapshot(project_path)

        if before_snapshot is None:
            # 首次归档,跳过验证
            logger.info("首次归档,跳过文档验证")
            output = {"continue": True}
            print(json.dumps(output, ensure_ascii=False))
            logger.finish(success=True, message="首次归档")
            sys.exit(0)

        # 扫描当前markdown目录
        after_snapshot = scan_markdown_dir(project_path)

        # 对比快照
        new_files, modified_files = compare_snapshots(before_snapshot, after_snapshot)

        # 检查是否有文档变更
        total_changes = len(new_files) + len(modified_files)

        if total_changes > 0:
            # 有文档变更,验证通过
            logger.info(f"文档验证通过: {len(new_files)} 新建, {len(modified_files)} 修改")

            # 输出变更详情
            if new_files:
                print(f"\n✅ 新建文档 ({len(new_files)} 个):", file=sys.stderr)
                for file_path in new_files[:5]:  # 最多显示5个
                    print(f"  - {Path(file_path).name}", file=sys.stderr)

            if modified_files:
                print(f"\n✅ 更新文档 ({len(modified_files)} 个):", file=sys.stderr)
                for file_path in modified_files[:5]:  # 最多显示5个
                    print(f"  - {Path(file_path).name}", file=sys.stderr)

            output = {"continue": True}
            print(json.dumps(output, ensure_ascii=False))
            logger.finish(success=True, message=f"{total_changes} 个文档已变更")
            sys.exit(0)

        # ========================================
        # 无文档变更 - 检查是否为测试任务
        # ========================================

        archived_task_dir, task_meta = find_latest_archived_task(project_path)

        if task_meta:
            task_desc = task_meta.get("task_description", "")
            task_id = task_meta.get("task_id", "unknown")

            if is_test_task(task_desc):
                # 测试任务,允许跳过文档创建
                logger.info(f"测试任务,允许跳过文档创建: {task_desc}")
                output = {"continue": True}
                print(json.dumps(output, ensure_ascii=False))
                logger.finish(success=True, message="测试任务跳过")
                sys.exit(0)
        else:
            task_id = "unknown"
            task_desc = "未知任务"

        # ========================================
        # 智能判断: 是否应该强制创建文档
        # ========================================

        # 检查markdown目录是否存在文档
        markdown_dir = Path(project_path) / "markdown"
        has_markdown_docs = markdown_dir.exists() and len(list(markdown_dir.glob("**/*.md"))) > 0

        if not has_markdown_docs:
            # markdown目录为空或不存在,这是首次使用,不强制
            logger.info("markdown目录为空,跳过文档验证")
            output = {"continue": True}
            print(json.dumps(output, ensure_ascii=False))
            logger.finish(success=True, message="首次使用跳过")
            sys.exit(0)

        # ========================================
        # CRITICAL: 阻断操作,要求检查并创建文档
        # ========================================

        logger.error(f"文档验证失败: 任务 {task_id} 未创建/更新任何文档")

        blocking_message = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  文档同步检查 - 请确认文档处理
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**任务ID**: {task_id}
**任务描述**: {task_desc}
**归档路径**: {archived_task_dir}

**检测结果**: markdown/目录下没有任何文档被创建或更新

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 请按以下决策树处理:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**步骤1: 检查现有文档**

先使用Glob扫描markdown目录,判断是否有相关文档:
```
Glob(pattern="markdown/**/*.md")
```

**步骤2: 根据情况决策**

### 情况A: 找到了相关文档 (已存在适合的文档)
✅ 使用Edit工具更新1-2个现有文档
✅ 补充本次任务的相关内容
✅ 完成后会自动通过验证

### 情况B: 没有找到相关文档 (需要创建新文档)
✅ 必须使用Write工具创建新文档
✅ 文档路径: `markdown/{{分类}}/{{功能名}}.md`
✅ 分类选项: systems/, events/, components/, gameplay/, docs/

**你必须立即执行以下操作之一**:

### 选项A: 创建新文档 (推荐)

1. 分析任务内容:
   - Read `{archived_task_dir}/context.md`
   - Read `{archived_task_dir}/solution.md`

2. 确定文档分类:
   - 新系统 → `markdown/systems/{{功能名}}.md`
   - 新事件 → `markdown/events/{{事件名}}.md`
   - 新组件 → `markdown/components/{{组件名}}.md`
   - Bug修复 → `markdown/docs/BUG修复记录.md`
   - 优化重构 → `markdown/docs/优化记录.md`

3. 使用Write工具创建文档:
```markdown
# {{功能名}}

> **创建时间**: {datetime.now().strftime('%Y-%m-%d')}
> **关联任务**: {task_id}
> **任务描述**: {task_desc}

## 概述

{{从solution.md提取的功能概述}}

## 实现细节

{{从context.md提取的关键实现要点}}

## 相关代码

- {{文件路径}}

## 注意事项

{{从任务中提取的注意事项}}
```

### 选项B: 更新现有文档

1. 使用Glob扫描markdown目录:
   `Glob(pattern="markdown/**/*.md")`

2. 找到相关文档后使用Edit工具更新

### 选项C: 确认为纯测试任务

如果此任务确实是纯测试性质(例如"测试Hook功能"),请:
1. 在输出中明确说明: "此任务为测试性质,无需文档化"
2. 删除快照文件: `rm .claude/.doc-snapshot.json`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  禁止以下借口:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ "markdown下没有合适的文档" → 创建新文档!
❌ "无需更新文档" → 必须创建文档!
❌ "任务过于简单" → 简单任务也要文档化!

✅ 只有明确标注为"测试"的任务才能跳过

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

请立即选择上述选项之一执行。Hook将持续阻断直到检测到文档变更。
"""

        output = {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": blocking_message
            },
            "continue": False,
            "stopReason": "doc_sync_incomplete"
        }
        print(json.dumps(output, ensure_ascii=False))

        logger.finish(success=False, message="文档创建未完成,已阻断")
        sys.exit(2)  # 阻断操作

    except Exception as e:
        logger.error("Hook执行异常", e)
        import traceback
        traceback.print_exc(file=sys.stderr)

        # 异常时不阻断(容错处理)
        output = {"continue": True}
        print(json.dumps(output, ensure_ascii=False))
        logger.finish(success=False, message="执行异常,放行")
        sys.exit(0)

if __name__ == '__main__':
    main()
