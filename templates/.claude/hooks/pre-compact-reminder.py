#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Pre-Compact Reminder Hook - 上下文压缩前注入工作流规则
触发时机: 上下文压缩前（PreCompact事件）
职责: 读取当前工作流状态，注入核心规则和任务描述，确保压缩后AI仍记得工作流要求
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
    """主函数：注入工作流规则到压缩前的上下文"""
    try:
        # 1. 读取Hook输入（stdin传入的JSON）
        hook_input = json.load(sys.stdin)
        project_path = hook_input.get('cwd', os.getcwd())

        # 2. 读取工作流状态
        state_file = os.path.join(project_path, '.claude', 'workflow-state.json')
        if not os.path.exists(state_file):
            # 状态文件不存在，可能不是/mc任务，不注入
            sys.exit(0)

        with open(state_file, 'r', encoding='utf-8') as f:
            state = json.load(f)

        # 3. 提取关键状态信息
        task_desc = state.get('task_description', '未知任务')
        current_step = state.get('current_step', 1)
        steps = state.get('steps_completed', {})

        step2_completed = steps.get('step2_doc_reading', False)
        doc_count = steps.get('step2_doc_count', 0)
        cleanup_completed = steps.get('cleanup_completed', False)

        docs_read = state.get('docs_read', [])

        # 4. 构建工作流规则提醒（注入到压缩后的上下文）
        reminder = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 上下文压缩警告: 工作流状态恢复
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**当前任务**: {task_desc}
**当前步骤**: 步骤{current_step}

**步骤完成状态**:
- 步骤2（文档查阅）: {"✅ 已完成" if step2_completed else f"❌ 未完成 ({doc_count}/3 文档)"}
- 收尾工作: {"✅ 已完成" if cleanup_completed else "❌ 未完成"}

**已读取的文档** ({doc_count}个):
{chr(10).join([f"  - {doc}" for doc in docs_read[:5]])}
{"  ... (共" + str(len(docs_read)) + "个文档)" if len(docs_read) > 5 else ""}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**核心规则** (无论上下文如何压缩，必须遵守):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. **步骤2必须完成**: Read ≥3个.md文档 (Hook会强制检查)
   - 位置: .claude/core-docs/ 或 markdown/
   - 禁止: Search/Read Python代码（.py文件）

2. **禁止跳过步骤2**: Hook会阻止在步骤2完成前Read Python代码

3. **收尾工作必须完成**:
   - 文档更新（自动补充≤2个文档）
   - DEBUG清理
   - 任务归档（tasks/目录）

4. **CRITICAL规范检查** (4项强制规范):
   - 规范1: 双端隔离原则（禁止跨端GetSystem）
   - 规范2: System生命周期限制（禁止__init__中调用API）
   - 规范3: EventData序列化限制（禁止使用tuple）
   - 规范4: AOI感应区范围限制（≤2000格）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**下一步行动**:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""

        # 5. 根据当前步骤添加具体指导
        if not step2_completed:
            reminder += f"""
**当前步骤{current_step}要求**:
- 📚 至少Read 3个markdown文档（当前{doc_count}/3）
- 🔍 提取关键原则（禁止/应该/原因）
- 📋 输出步骤2检查点报告

**建议查阅的文档**:
- .claude/core-docs/核心工作流文档/开发规范.md
- .claude/core-docs/概念参考/MODSDK核心概念.md
- markdown/systems/[相关System].md
"""
        elif not cleanup_completed:
            reminder += f"""
**当前步骤{current_step}要求**:
- 🔧 执行代码修改
- ✅ 验证修复效果
- 📝 完成收尾工作（文档更新、DEBUG清理、任务归档）

⚠️ **用户确认"已修复"后才能执行收尾工作**
"""
        else:
            reminder += """
**任务已完成**:
- ✅ 所有步骤已完成
- ✅ 收尾工作已完成
- 🎉 任务可以结束
"""

        reminder += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ **重要提醒**: 上述规则由Hook强制执行，违反规则会被阻止！
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

        # 6. 输出提醒内容（通过stdout注入到上下文）
        print(reminder)

        # 7. 允许压缩继续
        sys.exit(0)

    except Exception as e:
        # 异常情况下允许压缩继续
        print(f"⚠️ Hook执行异常: {str(e)}", file=sys.stderr)
        sys.exit(0)

if __name__ == '__main__':
    main()
