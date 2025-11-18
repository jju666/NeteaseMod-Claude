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

        # 2. 读取任务元数据（v2.0: 使用 task-meta.json 替代 workflow-state.json）
        active_file = os.path.join(project_path, '.claude', '.task-active.json')
        if not os.path.exists(active_file):
            # 无活跃任务，不注入
            sys.exit(0)

        # 读取活跃任务信息
        with open(active_file, 'r', encoding='utf-8') as f:
            active_task = json.load(f)

        task_id = active_task.get('task_id')
        if not task_id:
            sys.exit(0)

        # 读取任务元数据
        meta_file = os.path.join(project_path, 'tasks', task_id, '.task-meta.json')
        if not os.path.exists(meta_file):
            sys.exit(0)

        with open(meta_file, 'r', encoding='utf-8') as f:
            task_meta = json.load(f)

        # v3.0 Final: 检查是否是BUG修复任务且未确认
        task_type = task_meta.get('task_type', 'general')
        impl_data = task_meta.get('steps', {}).get('implementation', {})
        user_confirmed = impl_data.get('user_confirmed', False)

        if task_type == 'bug_fix' and not user_confirmed:
            # BUG修复任务未确认，强制阻止压缩
            warning = u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚫 禁止上下文压缩：BUG修复任务未确认
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**问题**: 用户尚未确认修复完成
**当前状态**: user_confirmed = false

⚠️ **禁止操作**:
- 禁止压缩上下文
- 禁止使用 /compact 或 /export
- 禁止结束会话

⚠️ **必须操作**:
- 等待用户输入"已修复"或"/mc-confirm"
- 继续修复直到用户明确确认
- 如果用户未给出明确的测试验证反馈，禁止认为任务完成

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            # PreCompact Hook 标准输出方式（符合 hook用法.md）
            # PreCompact 无法阻止压缩操作（退出码2不适用），只能注入警告
            # stdout 会在记录模式中显示给用户（退出码0行为）
            print(warning)
            sys.exit(0)

        # 3. 提取关键状态信息（v3.0 Final: 从 task_meta 读取，语义化命名）
        task_desc = task_meta.get('task_description', '未知任务')
        current_step = task_meta.get('current_step', 'planning')

        # 检查 planning 是否完成
        planning_data = task_meta.get('steps', {}).get('planning', {})
        planning_completed = (planning_data.get('status') == 'completed')

        # 检查文档阅读数量
        metrics = task_meta.get('metrics', {})
        docs_read = metrics.get('docs_read', [])
        doc_count = len(docs_read)

        # 检查收尾是否完成
        finalization_data = task_meta.get('steps', {}).get('finalization', {})
        finalization_completed = (finalization_data.get('status') == 'completed')

        # 4. 构建工作流规则提醒（注入到压缩后的上下文）（v3.0 Final: 语义化命名）
        reminder = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 上下文压缩警告: 工作流状态恢复 (v3.0 Final)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**当前任务**: {task_desc}
**当前步骤**: {current_step}

**步骤完成状态**:
- Planning（方案制定）: {"✅ 已完成" if planning_completed else f"❌ 未完成 ({doc_count}/3 文档)"}
- Implementation（代码实施）: {"✅ 已确认" if user_confirmed else "⏳ 进行中"}
- Finalization（收尾归档）: {"✅ 已完成" if finalization_completed else "⏳ 待执行"}

**已读取的文档** ({doc_count}个):
{chr(10).join([f"  - {doc}" for doc in docs_read[:5]])}
{"  ... (共" + str(len(docs_read)) + "个文档)" if len(docs_read) > 5 else ""}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**核心规则** (无论上下文如何压缩，必须遵守):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. **Planning 方案制定阶段必须完成**: Read ≥3个相关文档 (Hook强制检查)
   - 理解问题根因和技术约束
   - 明确说明研究结论后自动推进到 Implementation

2. **Implementation 代码实施阶段**:
   - 基于充分的文档研究实施代码修改
   - 必须等待用户明确确认"已修复"才能进入 Finalization

3. **Finalization 收尾工作**:
   - 父代理必须启动收尾子代理（禁止直接修改）
   - 子代理负责文档更新、DEBUG清理、任务归档

4. **CRITICAL规范检查** (自动拦截违规):
   - 双端隔离原则（禁止跨端调用）
   - System生命周期限制
   - EventData序列化限制
   - AOI感应区范围限制

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**下一步行动**:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""

        # 5. 根据当前步骤添加具体指导（v3.0 Final: 语义化命名）
        if not planning_completed:
            required_docs = planning_data.get('required_doc_count', 3)
            reminder += f"""
**当前: Planning 方案制定阶段**:
- 📚 至少Read {required_docs}个相关文档（当前{doc_count}/{required_docs}）
- 🔍 理解问题根因和技术约束
- 📋 明确说明研究结论（包含关键词："研究完成"或"已理解问题根因"）
- ✅ Hook检测到确认关键词后自动推进到 Implementation

**建议操作**:
使用 Read/Grep/Glob 查阅项目文档和代码，深入理解问题。
"""
        elif not user_confirmed:
            reminder += f"""
**当前: Implementation 代码实施阶段**:
- 🔧 基于Planning研究结果实施代码修改
- 🧪 测试验证修复效果
- ⏳ 等待用户输入 '/mc-confirm' 或 '已修复' 确认

⚠️ **重要**: 必须等待用户明确确认，不要自行判断完成
"""
        elif not finalization_completed:
            reminder += """
**当前: Finalization 收尾阶段**:
- 🚀 使用 Task 工具启动收尾子代理
- 📝 子代理负责文档更新、DEBUG清理、任务归档
- ❌ 父代理禁止直接使用 Write/Edit 工具

⚠️ **重要**: 必须通过子代理完成收尾工作
"""
        else:
            reminder += """
**任务已完成**:
- ✅ Planning 方案制定完成
- ✅ Implementation 用户已确认
- ✅ Finalization 收尾完成
- 🎉 任务可以归档
"""

        reminder += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ **重要提醒**: 上述规则由Hook强制执行，违反规则会被阻止！
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

        # 6. 输出提醒内容（通过stdout注入到压缩后的上下文）
        # PreCompact Hook 标准行为：stdout 会被添加到压缩后的上下文中
        # 这确保AI在上下文压缩后仍然记得工作流规则
        print(reminder)

        # 7. 允许压缩继续
        sys.exit(0)

    except Exception as e:
        # 异常情况下允许压缩继续
        print(f"⚠️ Hook执行异常: {str(e)}", file=sys.stderr)
        sys.exit(0)

if __name__ == '__main__':
    main()
