#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Post Archive Hook - 任务归档后处理 (v20.2.0 - 100%可靠版本)

触发时机:
1. PostToolUse (Bash工具执行后,检测.task-meta.json变化)
2. Stop Hook (会话结束前最终兜底检查)

职责:
1. 检测 step4_cleanup 是否刚完成
2. 移动任务目录到 tasks/已归档/
3. 标记归档完成,防止重复执行
4. 触发文档同步Agent

设计理念 (v20.2改进):
- ✅ 双触发点保证: PostToolUse + Stop Hook
- ✅ 幂等性设计: 多次执行不会重复移动
- ✅ 原子性标记: 使用.archive-lock防止并发问题
- ✅ 失败自动重试: Stop Hook作为最后兜底

v20.2.0 改进:
- 🔥 使用文件锁防止并发问题
- 🔥 Stop Hook兜底机制
- 🔥 详细日志记录每次检查
"""

import sys
import json
import os
import shutil
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

def find_latest_task_dir(project_path):
    """查找最新任务目录"""
    from pathlib import Path

    tasks_dir = Path(project_path) / "tasks"
    if not tasks_dir.exists():
        return None

    task_dirs = [
        d for d in tasks_dir.iterdir()
        if d.is_dir() and (d.name.startswith("task-") or d.name.startswith(u"任务-"))
    ]

    if not task_dirs:
        return None

    # 返回最新修改的任务目录
    latest_task = max(task_dirs, key=lambda d: d.stat().st_mtime)
    return latest_task

def acquire_archive_lock(task_dir):
    """获取归档锁,防止并发执行"""
    from pathlib import Path
    lock_file = Path(task_dir) / ".archive-lock"

    if lock_file.exists():
        # 检查锁文件是否过期(超过1分钟)
        import time
        if time.time() - lock_file.stat().st_mtime > 60:
            lock_file.unlink()  # 删除过期锁
        else:
            return False  # 锁被占用

    try:
        lock_file.touch()
        return True
    except:
        return False

def release_archive_lock(task_dir):
    """释放归档锁"""
    from pathlib import Path
    lock_file = Path(task_dir) / ".archive-lock"
    if lock_file.exists():
        try:
            lock_file.unlink()
        except:
            pass

def check_if_just_completed(meta_file):
    """检查任务是否刚完成(避免重复触发)"""
    try:
        with open(meta_file, 'r', encoding='utf-8') as f:
            meta = json.load(f)

        # 检查是否已归档
        if meta.get("archived", False):
            return False, None

        # 检查step4是否完成
        step4_status = meta.get("workflow_state", {}).get("steps", {}).get("step4_cleanup", {}).get("status")
        if step4_status != "completed":
            return False, None

        return True, meta
    except:
        return False, None

def move_to_archive(task_dir, project_path):
    """移动任务到已归档目录"""
    from pathlib import Path

    archived_root = Path(project_path) / "tasks" / u"已归档"
    archived_root.mkdir(exist_ok=True)

    task_name = task_dir.name
    archived_path = archived_root / task_name

    # 如果目标已存在,添加时间戳后缀
    if archived_path.exists():
        timestamp = datetime.now().strftime('%H%M%S')
        archived_path = archived_root / f"{task_name}-{timestamp}"

    try:
        shutil.move(str(task_dir), str(archived_path))
        return archived_path
    except Exception as e:
        raise Exception(f"移动目录失败: {e}")

def mark_as_archived(archived_path):
    """标记任务为已归档"""
    meta_file = archived_path / ".task-meta.json"
    try:
        with open(meta_file, 'r', encoding='utf-8') as f:
            meta = json.load(f)

        meta["archived"] = True
        meta["archived_at"] = datetime.now().isoformat()

        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

        return True
    except:
        return False

def generate_doc_snapshot(project_path):
    """生成归档前文档快照 (v20.1.1)"""
    from pathlib import Path

    markdown_dir = Path(project_path) / "markdown"
    snapshot = {}

    if markdown_dir.exists():
        for md_file in markdown_dir.glob("**/*.md"):
            try:
                snapshot[str(md_file)] = {
                    "mtime": md_file.stat().st_mtime,
                    "size": md_file.stat().st_size
                }
            except:
                pass

    return snapshot

def save_doc_snapshot(snapshot, project_path):
    """保存文档快照到.claude目录"""
    from pathlib import Path

    snapshot_file = Path(project_path) / ".claude" / ".doc-snapshot.json"
    try:
        with open(snapshot_file, 'w', encoding='utf-8') as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False)
        return True
    except:
        return False

def generate_doc_sync_prompt(meta, archived_path):
    """生成文档同步Agent的提示词 (v20.1.1 增强版 - 强制文档创建)"""
    task_desc = meta.get("task_description", "未知任务")
    task_id = meta.get("task_id", "unknown")

    # 读取任务文件
    context_file = archived_path / "context.md"
    solution_file = archived_path / "solution.md"

    context_content = ""
    solution_content = ""

    try:
        if context_file.exists():
            with open(context_file, 'r', encoding='utf-8') as f:
                context_content = f.read()
    except:
        pass

    try:
        if solution_file.exists():
            with open(solution_file, 'r', encoding='utf-8') as f:
                solution_content = f.read()
    except:
        pass

    # 生成Agent提示词
    prompt = f"""
# 任务归档文档同步 (v20.1.1 强制文档创建)

**归档任务ID**: {task_id}
**任务描述**: {task_desc}
**归档路径**: {archived_path}

---

## 📋 你的任务 (CRITICAL: 必须创建/更新文档)

分析这个已完成任务的内容,更新或创建下游项目的相关文档。

### 步骤1: 分析任务内容
阅读以下文件:
- `{context_file}` (任务上下文)
- `{solution_file}` (解决方案)

### 步骤2: 识别影响范围
确定这个任务涉及了哪些方面:
- 新功能/特性?
- Bug修复?
- 重构/优化?
- 文档更新?
- 配置变更?

### 步骤3: 检查现有文档结构 (CRITICAL: 必须先执行)

**使用Glob工具扫描markdown目录**:
```python
# 1. 扫描所有markdown文档
Glob(pattern="markdown/**/*.md")

# 2. 分析文档结构,判断是否有合适的现有文档
# 3. 确定是更新现有文档还是创建新文档
```

### 步骤4: 更新或创建文档 (CRITICAL: 必须执行,不能跳过)

**决策树**:

#### 情况A: markdown下存在相关文档(≤2个)
- ✅ 使用Edit工具更新这些文档
- 补充任务相关内容到合适的章节
- 保持文档风格一致

#### 情况B: markdown下不存在相关文档 (CRITICAL)
- ✅ **必须创建新的markdown文档**
- 文档路径格式: `markdown/{{分类}}/{{功能名}}.md`
- 分类选项: `systems/`, `events/`, `components/`, `gameplay/`, `docs/`
- 例如:
  - 新系统 → `markdown/systems/商店系统.md`
  - 新事件 → `markdown/events/购买事件.md`
  - Bug修复 → `markdown/docs/BUG修复记录.md`

**新文档模板** (创建新文档时必须使用):
```markdown
# {{功能名}}

> **创建时间**: {datetime.now().strftime('%Y-%m-%d')}
> **关联任务**: {task_id}
> **任务描述**: {task_desc}

## 概述

{{从solution.md提取的功能概述,2-3句话}}

## 实现细节

{{从context.md提取的关键实现要点}}

### 代码位置

{{相关代码文件路径}}

### 核心逻辑

{{关键实现逻辑说明}}

## 使用方法

{{如果是功能文档,说明如何使用}}

## 相关API

{{如果涉及API调用,列出关键API}}

## 注意事项

{{从任务中提取的注意事项、已知问题等}}

## 参考资料

- 任务归档: `{archived_path}`
```

**CRITICAL强制规则**:
1. ⚠️ **如果任务涉及新功能/系统/组件,必须创建对应文档**
2. ⚠️ **不能以"无合适文档"为理由跳过文档创建**
3. ⚠️ **只有纯测试性质的任务才能不创建文档**
4. ⚠️ **创建的新文档必须包含完整内容,不能只是空壳**
5. ✅ 最多创建或更新2个文档(避免过度创建)

### 步骤5: 验证文档完整性

创建/更新文档后,检查:
- [ ] 文档内容是否完整(不是空壳)
- [ ] 是否包含任务ID和创建时间
- [ ] 是否提取了关键实现细节
- [ ] 文档路径是否正确(markdown/{{分类}}/)

---

## 📄 任务内容摘要

### Context.md 内容:
```
{context_content[:800]}
{"..." if len(context_content) > 800 else ""}
```

### Solution.md 内容:
```
{solution_content[:800]}
{"..." if len(solution_content) > 800 else ""}
```

---

## ⚠️ 最后提醒

**你必须至少执行以下操作之一**:
1. 使用Edit更新1-2个现有markdown文档
2. 使用Write创建1-2个新的markdown文档
3. 如果确实是纯测试任务,在输出中明确说明"此任务为测试性质,无需文档化"

**完成后必须输出**:
```
📝 文档同步完成报告:
- 已更新文档: [文件路径列表]
- 已创建文档: [文件路径列表]
- 跳过原因: [如果没有创建/更新,必须说明原因]
```

请立即开始执行。
"""

    return prompt

def inject_doc_sync_task(meta, archived_path):
    """注入文档同步任务到对话"""
    prompt = generate_doc_sync_prompt(meta, archived_path)

    injection = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 任务归档完成 - 正在启动文档同步
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**任务已归档到**: `{archived_path}`

**下一步**: 我将启动Task Agent分析任务内容并更新相关文档。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{prompt}
"""

    return injection

def main():
    logger = HookLogger("post-archive-hook")
    logger.start()

    try:
        # 读取Hook输入
        hook_input = json.load(sys.stdin)
        project_path = hook_input.get('cwd', os.getcwd())

        # 识别触发来源 (PostToolUse 或 Stop)
        event_name = hook_input.get('eventName', 'PostToolUse')
        logger.info(f"触发来源: {event_name}")

        # 查找最新任务目录
        task_dir = find_latest_task_dir(project_path)
        if not task_dir:
            logger.info("无活跃任务,跳过")
            output = {"continue": True}
            print(json.dumps(output, ensure_ascii=False))
            sys.exit(0)

        # 检查任务元数据
        meta_file = task_dir / ".task-meta.json"
        if not meta_file.exists():
            logger.info("无任务元数据,跳过")
            output = {"continue": True}
            print(json.dumps(output, ensure_ascii=False))
            sys.exit(0)

        # 检查是否需要归档
        just_completed, meta = check_if_just_completed(str(meta_file))
        if not just_completed:
            logger.info("任务未完成或已归档,跳过")
            output = {"continue": True}
            print(json.dumps(output, ensure_ascii=False))
            sys.exit(0)

        # ═══════════════════════════════════════
        # 获取归档锁 (防止并发执行)
        # ═══════════════════════════════════════
        if not acquire_archive_lock(task_dir):
            logger.info("归档锁被占用,跳过 (可能正在执行)")
            output = {"continue": True}
            print(json.dumps(output, ensure_ascii=False))
            sys.exit(0)

        try:
            # ═══════════════════════════════════════
            # 核心流程: 归档 + 文档同步
            # ═══════════════════════════════════════

            task_id = meta.get("task_id", "unknown")
            logger.info(f"开始归档任务: {task_id}")

            # 0. Generate doc snapshot before archive (v20.1.1)
            logger.info("Generating doc snapshot...")
            snapshot = generate_doc_snapshot(project_path)
            if save_doc_snapshot(snapshot, project_path):
                logger.info(f"Doc snapshot saved: {len(snapshot)} files")

            # 1. 移动到归档目录
            try:
                archived_path = move_to_archive(task_dir, project_path)
                logger.info(f"✅ 任务已移动: {archived_path}")
            except Exception as e:
                logger.error(f"移动失败: {e}")
                release_archive_lock(task_dir)
                output = {"continue": True}
                print(json.dumps(output, ensure_ascii=False))
                sys.exit(0)

            # 2. 标记为已归档
            if not mark_as_archived(archived_path):
                logger.error("标记归档失败")

            # 3. 注入文档同步任务 (仅PostToolUse时注入,Stop时不注入)
            if event_name == "PostToolUse":
                injection = inject_doc_sync_task(meta, archived_path)
                output = {
                    "continue": True,
                    "injectedContext": injection
                }
                logger.info("文档同步任务已注入")
            else:
                # Stop Hook触发,只输出归档成功消息
                output = {
                    "continue": True,
                    "injectedContext": f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 任务归档完成 (Stop Hook兜底)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**任务ID**: {task_id}
**归档路径**: {archived_path}

任务已成功移动到已归档目录。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
                }
                logger.info("Stop Hook归档完成")

            print(json.dumps(output, ensure_ascii=False))
            logger.finish(success=True, message=f"任务{task_id}归档完成")

            # 释放锁
            release_archive_lock(archived_path)
            sys.exit(0)

        except Exception as e:
            release_archive_lock(task_dir)
            raise e

    except Exception as e:
        logger.error("Hook执行失败", e)
        import traceback
        traceback.print_exc(file=sys.stderr)
        logger.finish(success=False, message="执行异常")
        output = {"continue": True}
        print(json.dumps(output, ensure_ascii=False))
        sys.exit(0)  # 不阻断

if __name__ == '__main__':
    main()
