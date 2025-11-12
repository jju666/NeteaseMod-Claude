#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Enforce Step 2 Hook - 强制执行步骤2（文档查阅）
触发时机: Read工具调用前（PreToolUse事件）
职责: 阻止在步骤2完成前读取Python代码文件
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
    """主函数：检查步骤2完成状态"""
    try:
        # 1. 读取Hook输入（stdin传入的JSON）
        hook_input = json.load(sys.stdin)

        tool_name = hook_input.get('toolName', '')
        tool_params = hook_input.get('parameters', {})
        project_path = hook_input.get('cwd', os.getcwd())

        # 2. 只拦截Read工具
        if tool_name != 'Read':
            sys.exit(0)

        # 3. 获取要读取的文件路径
        file_path = tool_params.get('file_path', '')
        if not file_path:
            sys.exit(0)

        # 4. 如果不是Python文件，允许读取
        if not file_path.endswith('.py'):
            sys.exit(0)

        # 5. 读取工作流状态
        state_file = os.path.join(project_path, '.claude', 'workflow-state.json')
        if not os.path.exists(state_file):
            # 状态文件不存在，可能不是/mc任务，允许读取
            sys.exit(0)

        with open(state_file, 'r', encoding='utf-8') as f:
            state = json.load(f)

        # 6. 检查步骤2完成状态
        steps = state.get('steps_completed', {})
        step2_completed = steps.get('step2_doc_reading', False)
        doc_count = steps.get('step2_doc_count', 0)
        current_step = state.get('current_step', 1)

        # 7. 如果步骤2已完成且文档数≥3，允许读取Python文件
        if step2_completed and doc_count >= 3:
            sys.exit(0)

        # 8. 步骤2未完成，拒绝读取Python文件
        task_desc = state.get('task_description', '未知任务')
        docs_read = state.get('docs_read', [])

        denial_message = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ **步骤2未完成，禁止Read Python代码**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**当前任务**: {task_desc}
**当前步骤**: 步骤{current_step}

**当前状态**:
- 已Read文档数量: {doc_count} / 3 (最低要求)
- 步骤2完成状态: {"✅" if step2_completed else "❌"}

**已读取的文档**:
{chr(10).join([f"  - {doc}" for doc in docs_read]) if docs_read else "  (尚未读取任何文档)"}

**📚 你必须先完成步骤2:**
1. **强制要求**: 至少Read 3个markdown文档（来自 `markdown/` 或 `.claude/core-docs/`）
2. **禁止行为**: 在此步骤Search/Read Python代码文件（`.py`结尾的文件）

**💡 建议查阅的文档**:
- .claude/core-docs/核心工作流文档/开发规范.md - CRITICAL规范
- .claude/core-docs/概念参考/MODSDK核心概念.md - 基础概念
- markdown/systems/[相关System].md - 系统架构

**⚠️ 完成步骤2后才能进入步骤3探索代码**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

        # 9. 输出拒绝决策（通过stderr的JSON格式）
        output = {
            "permissionDecision": "deny",
            "reason": denial_message
        }
        print(json.dumps(output, ensure_ascii=False), file=sys.stderr)

        # 10. 返回退出码2（拒绝工具调用）
        sys.exit(2)

    except Exception as e:
        # 异常情况下允许继续（避免过度阻塞）
        print(f"⚠️ Hook执行异常: {str(e)}", file=sys.stderr)
        sys.exit(0)

if __name__ == '__main__':
    main()
