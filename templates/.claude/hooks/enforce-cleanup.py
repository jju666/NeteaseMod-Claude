#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Enforce Cleanup Hook - 强制执行收尾工作 (v20.0)
触发时机: AI尝试停止会话时（Stop事件）
职责: 检查收尾工作是否完成，未完成则阻止停止

v20.0 变更:
- 优先检查 .task-meta.json (新格式)
- 降级检查 workflow-state.json (兼容v19.x)
- 检查 step4_cleanup 步骤状态
"""

import os
import sys
import json
import io

# Fix Windows GBK encoding issue: force UTF-8 output
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Import notification module (v20.1)
try:
    from vscode_notify import notify_warning
except ImportError:
    def notify_warning(msg, detail=""): pass

def find_task_meta_file(project_path):
    """查找最新任务的 .task-meta.json 文件"""
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

    latest_task = max(task_dirs, key=lambda d: d.stat().st_mtime)
    meta_file = latest_task / ".task-meta.json"

    if meta_file.exists():
        return str(meta_file)

    return None

def main():
    """主函数：检查收尾工作完成状态"""
    try:
        # 1. 读取Hook输入（stdin传入的JSON）
        hook_input = json.load(sys.stdin)
        project_path = hook_input.get('cwd', os.getcwd())

        # 2. 查找 .task-meta.json (v20.0优先)
        task_meta_file = find_task_meta_file(project_path)
        task_meta = None
        if task_meta_file:
            try:
                with open(task_meta_file, 'r', encoding='utf-8') as f:
                    task_meta = json.load(f)
            except:
                pass

        # 3. 检查收尾工作完成状态 (v20.0格式)
        if task_meta:
            current_step = task_meta['workflow_state']['current_step']
            step4_status = task_meta['workflow_state']['steps']['step4_cleanup']['status']

            # 如果步骤4已完成，允许停止
            if step4_status == 'completed':
                sys.exit(0)

            task_desc = task_meta['task_description']
            doc_count = task_meta['metrics']['docs_read_count']
            docs_read = task_meta['metrics']['docs_read']

        else:
            # 4. 降级：读取 workflow-state.json (兼容v19.x)
            state_file = os.path.join(project_path, '.claude', 'workflow-state.json')
            if not os.path.exists(state_file):
                # 状态文件不存在，可能不是/mc任务，允许停止
                sys.exit(0)

            with open(state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)

            steps = state.get('steps_completed', {})
            cleanup_completed = steps.get('cleanup_completed', False)

            # 如果收尾已完成，允许停止
            if cleanup_completed:
                sys.exit(0)

            task_desc = state.get('task_description', '未知任务')
            current_step = state.get('current_step', 1)
            doc_count = steps.get('step2_doc_count', 0)
            docs_read = state.get('docs_read', [])

        # 5. 收尾未完成，阻止停止

        denial_message = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ **任务未完成，请完成收尾工作**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**当前任务**: {task_desc}
**当前步骤**: 步骤{current_step}
**文档阅读**: {doc_count}个文档已读

**📋 收尾清单** (用户明确"已修复"后才执行):

1. **📝 文档更新（自动补充≤2个文档）**:
   - 检查是否有"⚠️ **待补充**"标记的文档
   - 如果≤2个待补充文档，自动完善
   - 如果>2个，添加到"文档待补充清单.md"

2. **🧹 DEBUG清理**:
   - 搜索并删除所有DEBUG相关代码
   - 确认没有临时调试语句

3. **📦 任务归档**:
   - 创建/更新 tasks/task-XXX-{task_desc.replace(' ', '-')[:20]}/
   - 编写 context.md（任务上下文）
   - 编写 solution.md（解决方案）

**⚠️ 重要提醒**:
- 如果用户尚未确认"已修复"，请先等待用户验证
- 如果仅是中途询问，可以暂时允许停止（但收尾未完成）
- 完成所有收尾工作后，执行以下命令标记完成:

```python
import json
state_file = '.claude/workflow-state.json'
with open(state_file, 'r', encoding='utf-8') as f:
    state = json.load(f)
state['steps_completed']['cleanup_completed'] = True
with open(state_file, 'w', encoding='utf-8') as f:
    json.dump(state, f, indent=2)
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

        # v20.1: Desktop notification
        notify_warning(
            "Task not complete, please finish cleanup work",
            "Current step: {}".format(current_step)
        )

        # 6. Output blocking decision
        output = {
            "decision": "block",
            "reason": denial_message
        }
        print(json.dumps(output, ensure_ascii=False), file=sys.stderr)

        # 7. Return exit code 2
        sys.exit(2)

    except Exception as e:
        # 异常情况下允许停止（避免过度阻塞）
        print(f"⚠️ Hook执行异常: {str(e)}", file=sys.stderr)
        sys.exit(0)

if __name__ == '__main__':
    main()
