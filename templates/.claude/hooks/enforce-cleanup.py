#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Enforce Cleanup Hook - 强制执行收尾工作 (v20.2.7)
触发时机: AI尝试停止会话时（Stop事件）
职责: 检查收尾工作是否完成，未完成则阻止停止

v20.2.7 变更（防止重复询问）:
- ✅ 增加 asked_cleanup_intent 状态标记（防止重复询问）
- ✅ 询问收尾意愿后10分钟内静默等待
- ✅ 使用标准 Stop Hook 输出格式（exit 2 + systemMessage）
- ✅ 修复官方文档规范：不使用 injectedContext

v20.2.6 变更（关键修复）:
- ✅ 改为优先读取 workflow-state.json（运行时唯一数据源）
- ✅ 降级读取 .task-meta.json（向后兼容）
- ✅ 添加详细日志记录到 .claude/logs/hooks.log
- ✅ 实现智能收尾询问逻辑（用户确认修复后询问是否收尾）

修复问题:
- 修复 BUG修复工作流执行问题分析报告.md 中的问题#2（重复询问）
- 解决 user_confirmed 状态读取错误导致收尾未执行的问题
"""

import os
import sys
import json
import io
import re

# Fix Windows GBK encoding issue: force UTF-8 output
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Import hook logger (v20.2.6)
try:
    from hook_logger import HookLogger
except ImportError:
    class HookLogger:
        def __init__(self, *args, **kwargs): pass
        def start(self): pass
        def info(self, msg, data=None): pass
        def warning(self, msg, data=None): pass
        def error(self, msg, err=None): pass
        def finish(self, success=True, message=""): pass

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


def validate_cleanup_tasks(task_dir_path, project_path):
    """
    验证3项收尾任务是否完成 (v20.3新增)

    返回:
    {
        "all_completed": bool,
        "missing_tasks": list,
        "details": dict
    }
    """
    from pathlib import Path
    import subprocess

    task_dir = Path(task_dir_path)
    results = {
        "all_completed": True,
        "missing_tasks": [],
        "details": {}
    }

    # === 任务1: 任务归档文件检查 ===
    context_md = task_dir / "context.md"
    solution_md = task_dir / "solution.md"

    if not context_md.exists():
        results["all_completed"] = False
        results["missing_tasks"].append("context.md未创建")
        results["details"]["context_md"] = "缺失"
    else:
        # 检查文件不为空
        if context_md.stat().st_size < 100:
            results["all_completed"] = False
            results["missing_tasks"].append("context.md内容过少")
            results["details"]["context_md"] = u"过少({} bytes)".format(context_md.stat().st_size)
        else:
            results["details"]["context_md"] = "完成"

    if not solution_md.exists():
        results["all_completed"] = False
        results["missing_tasks"].append("solution.md未创建")
        results["details"]["solution_md"] = "缺失"
    else:
        if solution_md.stat().st_size < 100:
            results["all_completed"] = False
            results["missing_tasks"].append("solution.md内容过少")
            results["details"]["solution_md"] = u"过少({} bytes)".format(solution_md.stat().st_size)
        else:
            results["details"]["solution_md"] = "完成"

    # === 任务2: DEBUG代码检查 ===
    # 使用简单的文件扫描代替复杂的grep（避免Hook执行时间过长）
    debug_found = False
    behavior_packs = Path(project_path) / "behavior_packs"

    if behavior_packs.exists():
        for py_file in behavior_packs.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if re.search(r'\bDEBUG\b|print.*debug|console\.log.*test', content, re.IGNORECASE):
                        debug_found = True
                        results["all_completed"] = False
                        results["missing_tasks"].append(u"发现DEBUG代码: {}".format(py_file.name))
                        break
            except:
                pass

    if not debug_found:
        results["details"]["debug_cleanup"] = "完成"
    else:
        results["details"]["debug_cleanup"] = "未完成"

    # === 任务3: 文档更新检查 ===
    # 检查markdown目录中是否还有"待补充"标记
    markdown_dir = Path(project_path) / "markdown"
    pending_docs_count = 0

    if markdown_dir.exists():
        for md_file in markdown_dir.rglob("*.md"):
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if u"待补充" in content or "TODO" in content:
                        pending_docs_count += 1
            except:
                pass

    if pending_docs_count > 2:
        results["all_completed"] = False
        results["missing_tasks"].append(u"仍有{}个待补充文档".format(pending_docs_count))
        results["details"]["docs_update"] = u"未完成({})".format(pending_docs_count)
    else:
        results["details"]["docs_update"] = u"完成(≤2个待补充)"

    return results

def main():
    """主函数：检查收尾工作完成状态"""
    logger = HookLogger("enforce-cleanup")
    logger.start()

    try:
        # 1. 读取Hook输入（stdin传入的JSON）
        hook_input = json.load(sys.stdin)
        project_path = hook_input.get('cwd', os.getcwd())

        logger.info("Stop Hook触发", {"project_path": project_path})

        # 2. v20.2.6: 优先读取 workflow-state.json（运行时唯一数据源）
        workflow_state_file = os.path.join(project_path, '.claude', 'workflow-state.json')
        workflow_state = None

        if os.path.exists(workflow_state_file):
            try:
                with open(workflow_state_file, 'r', encoding='utf-8') as f:
                    workflow_state = json.load(f)
                logger.info("成功读取workflow-state.json", {"source": "workflow-state.json"})
            except Exception as e:
                logger.error("workflow-state.json读取失败", err=e)

        # 3. v20.2.6: 从 workflow_state 读取关键状态
        if workflow_state:
            current_step = workflow_state.get('current_step', 'unknown')
            steps = workflow_state.get('steps', {})
            step3_data = steps.get('step3_execute', {})
            step4_data = steps.get('step4_cleanup', {})

            # ✅ 核心修复：直接从 workflow_state 读取 user_confirmed
            user_confirmed = step3_data.get('user_confirmed', False)
            step4_status = step4_data.get('status', 'pending')

            logger.info("状态读取", {
                "current_step": current_step,
                "user_confirmed": user_confirmed,
                "step4_status": step4_status
            })

            # 如果步骤4已完成，允许停止
            if step4_status == 'completed':
                logger.info("收尾已完成，允许停止")
                logger.finish(success=True, message="允许会话结束")
                sys.exit(0)

            # v20.2.6: 实现智能收尾询问逻辑
            task_type = workflow_state.get('task_type', 'general')

            # 情况1: BUG修复任务 + 用户未确认修复
            if task_type == 'bug_fix' and not user_confirmed:
                logger.warning("BUG修复未确认", {"user_confirmed": False})
                # BUG修复任务必须等待用户确认
                denial_message_prefix = u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚫 **BUG修复任务未确认，禁止结束会话**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**问题**: 用户尚未明确确认修复完成
**当前状态**: user_confirmed = false

⚠️ **强制要求**:
- 必须等待用户输入"已修复"、"/mc-confirm"或明确的成功反馈
- 禁止AI主动认为任务完成
- 禁止在未验证前结束会话

**如果修复已完成但用户未确认**:
1. 提醒用户测试验证
2. 等待用户明确反馈
3. 收到确认后才能进入收尾阶段

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
                notify_warning(
                    "BUG修复未确认",
                    "等待用户输入'已修复'或'/mc-confirm'"
                )

                output = {
                    "continue": False,
                    "stopReason": "bug_fix_not_confirmed",
                    "injectedContext": denial_message_prefix
                }
                print(json.dumps(output, ensure_ascii=False))
                logger.finish(success=True, message="阻止结束：等待用户确认")
                sys.exit(0)

            # 情况2: 用户已确认修复 + 收尾未完成 -> 询问是否收尾
            if user_confirmed and step4_status != 'completed':
                logger.info("用户已确认修复，检查收尾询问状态", {
                    "user_confirmed": True,
                    "step4_status": step4_status
                })

                # v20.2.7: 检查是否已询问过收尾意愿（防止重复询问）
                asked_cleanup = workflow_state.get('asked_cleanup_intent', False)
                asked_at_str = workflow_state.get('asked_cleanup_at', None)

                if not asked_cleanup:
                    # 第一次询问，设置标记
                    from datetime import datetime
                    workflow_state['asked_cleanup_intent'] = True
                    workflow_state['asked_cleanup_at'] = datetime.now().isoformat()

                    # 立即保存（避免重复询问）
                    try:
                        with open(workflow_state_file, 'w', encoding='utf-8') as f:
                            json.dump(workflow_state, f, indent=2, ensure_ascii=False)
                        logger.info("首次询问收尾意愿，已设置标记", {
                            "asked_at": workflow_state['asked_cleanup_at']
                        })
                    except Exception as e:
                        logger.error("保存状态失败", err=e)

                    task_desc = workflow_state.get('task_description', '未知任务')

                    # v20.2.7: 使用 systemMessage（官方文档规范）
                    cleanup_prompt = u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ **任务修复已确认！**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**任务**: {task_desc}
**状态**: 用户已确认修复完成

**📋 是否需要执行收尾工作？**

收尾工作包括：
1. **📝 文档更新** - 检查并补充待完善的文档
2. **🧹 DEBUG清理** - 删除临时调试代码和注释
3. **📦 任务归档** - 创建任务文档（context.md、solution.md）

**请选择：**
- 回复"需要收尾"或"执行收尾" → 进入收尾流程
- 回复"直接结束"或"跳过收尾" → 立即结束会话（收尾工作可后续补充）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(task_desc=task_desc)

                    notify_warning(
                        "任务修复已确认",
                        "是否需要执行收尾工作？"
                    )

                    # v20.2.7: 使用官方规范输出格式
                    output = {
                        "stopReason": "awaiting_cleanup_decision",
                        "systemMessage": cleanup_prompt
                    }
                    print(json.dumps(output, ensure_ascii=False))
                    logger.finish(success=True, message="首次询问收尾意愿")
                    sys.exit(2)  # Exit 2 阻止会话结束

                else:
                    # 已询问过，静默等待用户回复
                    from datetime import datetime
                    asked_at = datetime.fromisoformat(asked_at_str)
                    wait_seconds = (datetime.now() - asked_at).total_seconds()

                    logger.info("收尾意愿已询问，静默等待用户回复", {
                        "asked_at": asked_at_str,
                        "wait_seconds": int(wait_seconds)
                    })

                    if wait_seconds < 600:  # 10分钟内，静默阻止
                        output = {
                            "stopReason": "awaiting_cleanup_decision_silent",
                            "systemMessage": ""  # 不注入内容（避免重复提示）
                        }
                        print(json.dumps(output, ensure_ascii=False))
                        logger.finish(success=True, message="静默等待用户回复（已询问{}秒）".format(int(wait_seconds)))
                        sys.exit(2)  # Exit 2 阻止会话结束

                    else:
                        # 超过10分钟，视为用户未看到，重置询问状态允许重新询问
                        logger.warning("等待超时（{}秒），重置询问状态".format(int(wait_seconds)))
                        workflow_state['asked_cleanup_intent'] = False
                        try:
                            with open(workflow_state_file, 'w', encoding='utf-8') as f:
                                json.dump(workflow_state, f, indent=2, ensure_ascii=False)
                        except:
                            pass
                        # 重新执行询问逻辑（递归调用自身）
                        # 这里简化处理：允许结束并在下次触发时重新询问
                        sys.exit(2)

            # 情况3: 其他情况（正常任务或收尾进行中）-> 允许停止
            logger.info("允许停止（正常流程）")
            logger.finish(success=True, message="允许会话结束")
            sys.exit(0)

        # 4. 降级：读取 .task-meta.json（向后兼容v20.0）
        else:
            logger.info("workflow-state.json不存在，尝试降级读取task-meta.json")
            task_meta_file = find_task_meta_file(project_path)
            task_meta = None
            if task_meta_file:
                try:
                    with open(task_meta_file, 'r', encoding='utf-8') as f:
                        task_meta = json.load(f)
                    logger.info("成功读取task-meta.json (降级模式)", {"file": task_meta_file})
                except Exception as e:
                    logger.error("task-meta.json读取失败", err=e)

        # 5. v20.0兼容：处理 task-meta.json 格式
        if task_meta:
            current_step = task_meta['workflow_state']['current_step']
            step3_data = task_meta['workflow_state']['steps'].get('step3_execute', {})
            step4_status = task_meta['workflow_state']['steps']['step4_cleanup']['status']

            # v20.3: 检查用户是否确认修复完成
            user_confirmed = step3_data.get('user_confirmed', False)

            # 如果步骤4已完成，允许停止
            if step4_status == 'completed':
                logger.info("收尾已完成（task-meta模式）")
                logger.finish(success=True, message="允许会话结束")
                sys.exit(0)

            # v20.3: 如果用户未确认修复，强制阻止（除非是BUG修复任务）
            task_type = task_meta.get('task_type', 'general')
            if task_type == 'bug_fix' and not user_confirmed:
                logger.warning("BUG修复未确认（task-meta模式）")
                # [使用原有的阻止逻辑...]
                denial_message_prefix = u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚫 **BUG修复任务未确认，禁止结束会话**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**问题**: 用户尚未明确确认修复完成
**当前状态**: user_confirmed = false

⚠️ **强制要求**:
- 必须等待用户输入"已修复"、"/mc-confirm"或明确的成功反馈
- 禁止AI主动认为任务完成
- 禁止在未验证前结束会话

**如果修复已完成但用户未确认**:
1. 提醒用户测试验证
2. 等待用户明确反馈
3. 收到确认后才能进入收尾阶段

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
                notify_warning(
                    "BUG修复未确认",
                    "等待用户输入'已修复'或'/mc-confirm'"
                )

                output = {
                    "continue": False,
                    "stopReason": "bug_fix_not_confirmed",
                    "injectedContext": denial_message_prefix
                }
                print(json.dumps(output, ensure_ascii=False))
                logger.finish(success=True, message="阻止结束：等待用户确认")
                sys.exit(0)

            # v20.3: 如果step4_status不是completed，进行详细验证
            task_dir = os.path.dirname(task_meta_file)
            validation = validate_cleanup_tasks(task_dir, project_path)

            # 如果实际已经完成所有任务但status未更新，自动更新并允许停止
            if validation["all_completed"]:
                task_meta['workflow_state']['steps']['step4_cleanup']['status'] = 'completed'
                with open(task_meta_file, 'w', encoding='utf-8') as f:
                    json.dump(task_meta, f, indent=2, ensure_ascii=False)
                sys.exit(0)

            task_desc = task_meta['task_description']
            doc_count = task_meta['metrics']['docs_read_count']
            docs_read = task_meta['metrics']['docs_read']

            # v20.3: 附加验证详情到denial_message
            validation_details = validation

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
            validation_details = None  # v19.x不支持详细验证

        # 5. 收尾未完成，阻止停止

        # v20.3: 构建验证状态摘要
        validation_summary = ""
        if validation_details:
            validation_summary = u"\n**📊 收尾任务完成状态** (v20.3):\n"
            for task_name, status in validation_details["details"].items():
                icon = u"✅" if status == u"完成" else u"❌"
                validation_summary += u"  {} {}: {}\n".format(icon, task_name, status)

            if validation_details["missing_tasks"]:
                validation_summary += u"\n**⚠️ 待完成项**:\n"
                for missing in validation_details["missing_tasks"]:
                    validation_summary += u"  - {}\n".format(missing)

        denial_message = u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ **任务未完成，请完成收尾工作**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**当前任务**: {}
**当前步骤**: 步骤{}
**文档阅读**: {}个文档已读
{}
**📋 收尾清单** (用户明确"已修复"后才执行):""".format(
            task_desc, current_step, doc_count, validation_summary
        )

        denial_message += """

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

        # 6. Output blocking decision (v20.3: 使用标准字段)
        # 根据Claude Code规范：
        # - "continue": false 是通用字段，优先级最高
        # - "decision": "block" 是Stop Hook专用字段（可选）
        # - 通过stdout输出JSON，Exit 0（stderr自动反馈机制已废弃）
        output = {
            "continue": False,  # 标准字段，强制阻止会话结束
            "stopReason": "task_incomplete",
            "injectedContext": denial_message
        }
        print(json.dumps(output, ensure_ascii=False))

        # 7. Return exit code 0 (配合continue:false工作)
        sys.exit(0)

    except Exception as e:
        # v20.2.6: 异常情况下允许停止（避免过度阻塞），但记录详细日志
        logger.error("Stop Hook执行异常", err=e, data={
            "exception_type": type(e).__name__,
            "exception_message": str(e)
        })
        logger.finish(success=False, message="异常：允许停止避免阻塞")
        print(f"⚠️ Hook执行异常: {str(e)}", file=sys.stderr)
        sys.exit(0)

if __name__ == '__main__':
    main()
