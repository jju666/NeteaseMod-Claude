#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Enforce Cleanup Hook - 强制执行收尾工作
触发时机: AI尝试停止会话时（Stop事件）
职责: 检查收尾工作是否完成，未完成则阻止停止
"""

import os
import sys
import json
import io

# 修复Windows GBK编码问题：强制使用UTF-8输出
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def main():
    """主函数：检查收尾工作完成状态"""
    try:
        # 1. 读取Hook输入（stdin传入的JSON）
        hook_input = json.load(sys.stdin)
        project_path = hook_input.get('cwd', os.getcwd())

        # 2. 读取工作流状态
        state_file = os.path.join(project_path, '.claude', 'workflow-state.json')
        if not os.path.exists(state_file):
            # 状态文件不存在，可能不是/mc任务，允许停止
            sys.exit(0)

        with open(state_file, 'r', encoding='utf-8') as f:
            state = json.load(f)

        # 3. 检查收尾工作完成状态
        steps = state.get('steps_completed', {})
        cleanup_completed = steps.get('cleanup_completed', False)

        # 4. 如果收尾已完成，允许停止
        if cleanup_completed:
            sys.exit(0)

        # 5. 收尾未完成，阻止停止
        task_desc = state.get('task_description', '未知任务')
        current_step = state.get('current_step', 1)
        doc_count = steps.get('step2_doc_count', 0)
        docs_read = state.get('docs_read', [])

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

        # 6. 输出阻止决策（通过stderr的JSON格式）
        output = {
            "decision": "block",
            "reason": denial_message
        }
        print(json.dumps(output, ensure_ascii=False), file=sys.stderr)

        # 7. 返回退出码2（阻止停止）
        sys.exit(2)

    except Exception as e:
        # 异常情况下允许停止（避免过度阻塞）
        print(f"⚠️ Hook执行异常: {str(e)}", file=sys.stderr)
        sys.exit(0)

if __name__ == '__main__':
    main()
