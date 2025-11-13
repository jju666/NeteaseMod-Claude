#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unified Workflow Driver - 统一工作流驱动器 (v20.0.3)

触发时机: PostToolUse (Read/Write/Edit/Bash)
职责:
1. 快速检查 .task-active.json,无活跃任务则跳过
2. 根据工具类型分发处理
3. 更新任务状态机
4. 检查步骤完成条件
5. 注入下一步指令(防重复注入)

退出码:
- 0: 成功
"""

import sys
import json
import os
from datetime import datetime
import io

# Windows编码修复
if sys.platform == 'win32':
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Import logger
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

# Import notification module (v20.1)
try:
    from vscode_notify import notify_info
except ImportError:
    def notify_info(msg, detail=""): pass

def load_json(file_path):
    """加载JSON文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None

def save_json(file_path, data):
    """保存JSON文件"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except:
        return False

def update_docs_read(meta, file_path):
    """更新文档阅读记录"""
    if not file_path.endswith('.md'):
        return False

    # 排除不计入的文档
    excluded = ['README.md', 'CHANGELOG.md', u'索引.md', u'项目状态.md', u'文档待补充清单.md']
    if any(pattern in file_path for pattern in excluded):
        return False

    docs_read = meta.get("metrics", {}).get("docs_read", [])
    if file_path not in docs_read:
        docs_read.append(file_path)
        meta["metrics"]["docs_read"] = docs_read
        meta["metrics"]["docs_read_count"] = len(docs_read)

        # 同步到step2_docs
        if "step2_docs" in meta["workflow_state"]["steps"]:
            meta["workflow_state"]["steps"]["step2_docs"]["docs_read"] = docs_read

        return True
    return False

def update_code_changes(meta, tool_data):
    """记录代码修改"""
    file_path = tool_data.get("tool_input", {}).get("file_path", "")
    if not file_path:
        return False

    change_record = {
        "file": file_path,
        "timestamp": datetime.now().isoformat(),
        "operation": tool_data.get("tool_name", "Unknown")
    }

    if "code_changes" not in meta["metrics"]:
        meta["metrics"]["code_changes"] = []

    meta["metrics"]["code_changes"].append(change_record)
    meta["metrics"]["code_changes_count"] = len(meta["metrics"]["code_changes"])
    return True

def check_test_failure(result_str):
    """检测测试失败"""
    failure_indicators = [
        'error', 'Error', 'ERROR',
        'failed', 'Failed', 'FAILED',
        'traceback', 'Traceback',
        'exception', 'Exception'
    ]
    return any(indicator in result_str for indicator in failure_indicators)

# ==================== v20.2 新增：循环检测与专家触发 ====================

def check_expert_trigger(meta, cwd):
    """
    循环检测器 - 判断是否触发专家审查

    返回:
    {
        "should_trigger": bool,
        "loop_type": "bug_fix_loop" | "requirement_mismatch" | None,
        "confidence": float,
        "evidence": dict
    }
    """

    # 读取workflow-state以获取tracking_state
    workflow_state_path = os.path.join(cwd, '.claude', 'workflow-state.json')
    workflow_state = load_json(workflow_state_path)

    if not workflow_state:
        return {"should_trigger": False, "loop_type": None}

    # === Bug修复循环检测 ===
    if workflow_state.get("bug_fix_tracking", {}).get("enabled"):
        tracking = workflow_state["bug_fix_tracking"]
        indicators = tracking.get("loop_indicators", {})
        iterations_count = len(tracking.get("iterations", []))

        # 触发条件:
        # 1. 至少2次迭代
        # 2. 至少2次负面反馈
        # 3. 至少2次同文件修改
        negative_count = indicators.get("negative_feedback_count", 0)
        same_file_count = indicators.get("same_file_edit_count", 0)

        if (iterations_count >= 2 and
            negative_count >= 2 and
            same_file_count >= 2):

            return {
                "should_trigger": True,
                "loop_type": "bug_fix_loop",
                "confidence": 0.9,
                "evidence": {
                    "iterations": iterations_count,
                    "negative_feedback": negative_count,
                    "same_file_edits": same_file_count,
                    "pattern": u"表象修复循环 - 反复修改同一位置但未解决根本问题"
                }
            }

    # === 需求实现循环检测 ===
    if workflow_state.get("feature_tracking", {}).get("enabled"):
        tracking = workflow_state["feature_tracking"]
        iterations_count = len(tracking.get("iterations", []))
        requirement_changes = len(tracking.get("requirement_changes", []))

        # 触发条件:
        # 1. 至少2次迭代
        # 2. 至少2次不满意反馈
        dissatisfied_count = sum(
            1 for iter in tracking.get("iterations", [])
            if iter.get("user_satisfaction") == "dissatisfied"
        )

        if (iterations_count >= 2 and dissatisfied_count >= 2):

            return {
                "should_trigger": True,
                "loop_type": "requirement_mismatch",
                "confidence": 0.85,
                "evidence": {
                    "iterations": iterations_count,
                    "dissatisfied_count": dissatisfied_count,
                    "requirement_changes": requirement_changes,
                    "pattern": u"需求理解偏差 - 实现方向与用户期望不一致"
                }
            }

    return {
        "should_trigger": False,
        "loop_type": None,
        "confidence": 0.0,
        "evidence": {}
    }


def launch_meta_expert(expert_check, meta, cwd, logger):
    """
    启动Meta-Expert专家分析

    流程:
    1. 读取完整的迭代历史
    2. 构建专家分析prompt
    3. 注入到对话上下文
    4. 等待AI生成分析报告
    """

    loop_type = expert_check["loop_type"]
    evidence = expert_check["evidence"]

    # 读取workflow-state获取完整历史
    workflow_state_path = os.path.join(cwd, '.claude', 'workflow-state.json')
    workflow_state = load_json(workflow_state_path)

    if not workflow_state:
        logger.error(u"无法读取workflow-state")
        return None

    # 构建历史摘要
    history_summary = ""

    if loop_type == "bug_fix_loop":
        tracking = workflow_state.get("bug_fix_tracking", {})
        history_summary = u"## 迭代历史\n\n"

        for iter in tracking.get("iterations", []):
            history_summary += u"### 迭代 {}\n".format(iter["iteration_id"])
            history_summary += u"- 时间: {}\n".format(iter["timestamp"])
            history_summary += u"- 用户反馈: {}\n".format(iter.get("user_feedback", "无"))
            history_summary += u"- 情感: {}\n".format(iter.get("feedback_sentiment", "neutral"))
            history_summary += u"- 修改文件:\n"
            for change in iter.get("changes_made", []):
                history_summary += u"  - {}: {}\n".format(change["file"], change["change_summary"])
            history_summary += u"\n"

    elif loop_type == "requirement_mismatch":
        tracking = workflow_state.get("feature_tracking", {})
        history_summary = u"## 需求调整历史\n\n"

        for iter in tracking.get("iterations", []):
            history_summary += u"### 迭代 {}\n".format(iter["iteration_id"])
            history_summary += u"- 时间: {}\n".format(iter["timestamp"])
            history_summary += u"- 用户满意度: {}\n".format(iter.get("user_satisfaction", "neutral"))
            history_summary += u"- 调整请求: {}\n\n".format(iter.get("adjustment_request", "无"))

    # 构建专家分析prompt
    expert_prompt = u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 专家审查系统已触发
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 检测到的问题模式

**循环类型**: {}
**置信度**: {:.0%}
**证据**:
{}

{}

## 你的任务

你现在需要从**战略高度**分析问题，而非继续尝试修复。

### 场景A: Bug修复循环
如果是Bug修复循环，请回答：

1. **根因分析**: 为什么反复修改仍失败?
   - 是否陷入表象修复?
   - 是否存在架构层面的缺陷?
   - 是否对问题的理解有误?

2. **失败模式**: 历史修改中有哪些共同的错误假设?

3. **备选路径**: 除了当前方向，还有哪3-5种可能的解决思路?
   - 路径A: [名称] - [优点] - [缺点] - [适用场景]
   - 路径B: ...

4. **推荐策略**: 推荐哪种路径，以及如何验证?

### 场景B: 需求理解偏差
如果是需求调整循环，请回答：

1. **需求分析**: 用户真正想要什么?(可能与表面需求不同)

2. **差距诊断**: 当前实现与用户期望的本质差距在哪?

3. **方案对比**: 提供3-5种实现策略，标注优缺点
   - 方案A: [名称] - [优点] - [缺点] - [预计工作量]
   - 方案B: ...

4. **澄清问题**: 列出需要向用户确认的5个关键问题

## 输出格式

使用以下Markdown格式输出：

# 🎯 专家诊断报告

## 1. 问题根因

[深度分析...]

## 2. 备选方案

### 方案A: [名称]
- **优点**: ...
- **缺点**: ...
- **适用场景**: ...
- **预计工作量**: ...

### 方案B: [名称]
...

## 3. 推荐策略

[具体建议，包括实施步骤和验证方法]

## 4. 需要向用户澄清的问题

1. [问题1]
2. [问题2]
...

## 重要提醒

- ❌ 不要直接修改代码
- ❌ 不要假设问题已被准确定位
- ✅ 从高维度分析问题本质
- ✅ 提供多种备选方案
- ✅ 明确指出需要澄清的点

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

请立即开始分析。
""".format(
        loop_type,
        expert_check["confidence"],
        u"\n".join([u"- {}: {}".format(k, v) for k, v in evidence.items()]),
        history_summary
    )

    # 标记专家已触发
    meta["metrics"]["expert_review_triggered"] = True
    meta["metrics"]["expert_triggered_at"] = datetime.now().isoformat()

    # 保存到.task-meta.json
    task_dir = meta.get("task_id")
    if task_dir:
        meta_path = os.path.join(cwd, 'tasks', task_dir, '.task-meta.json')
        save_json(meta_path, meta)

    logger.info(u"专家审查已触发", {
        "loop_type": loop_type,
        "confidence": expert_check["confidence"]
    })

    return expert_prompt

# ==================== v20.2 结束 ====================

def check_step_completed(step_name, meta):
    """Check if workflow step is completed (v20.1: removed step2)"""
    steps = meta["workflow_state"]["steps"]

    if step_name == "step0_context":
        docs_read = meta.get("metrics", {}).get("docs_read", [])
        return any("CLAUDE.md" in doc.upper() for doc in docs_read)

    elif step_name == "step1_understand":
        return meta.get("metrics", {}).get("docs_read_count", 0) > 0

    elif step_name == "step3_execute":
        return steps["step3_execute"].get("user_confirmed", False)

    elif step_name == "step4_cleanup":
        return steps["step4_cleanup"]["status"] == "completed"

    return False

def get_next_step(current_step):
    """Get next step in workflow (v20.1: removed step2)"""
    step_order = ["step0_context", "step1_understand", "step3_execute", "step4_cleanup"]
    try:
        current_idx = step_order.index(current_step)
        if current_idx < len(step_order) - 1:
            return step_order[current_idx + 1]
    except ValueError:
        pass
    return None

def trigger_doc_update_agent(meta, cwd):
    """触发文档更新子代理 (v20.0.4)"""
    import subprocess

    logger = HookLogger("doc-update-agent-trigger")
    logger.start()

    try:
        # 构建子代理任务描述
        task_desc = meta.get("task_description", "Unknown Task")
        docs_read = meta.get("metrics", {}).get("docs_read", [])
        code_changes = meta.get("metrics", {}).get("code_changes", [])

        agent_prompt = u"""
🤖 子代理任务：自动文档更新与收尾工作

**任务上下文**:
- 主任务: {}
- 已阅读文档: {}个
- 代码修改: {}处

**你的职责**:
1. 搜索 markdown/ 目录下所有包含"待补充"或"TODO"标记的文档
2. 分析标记的上下文，判断是否与本次任务相关
3. 如果相关文档≤2个，使用Edit工具更新这些文档的内容
4. 如果相关文档>2个，将列表追加到 markdown/文档待补充清单.md
5. 搜索代码中的DEBUG/临时调试语句，建议清理
6. 输出收尾报告

**执行步骤**:

Step 1: 搜索待补充标记
```bash
# 使用Grep搜索markdown目录
Grep("待补充|TODO", path="markdown/", output_mode="files_with_matches", -i=True)
```

Step 2: 分析相关性
- 阅读搜索到的文档片段（使用Grep -C 3获取上下文）
- 判断是否与主任务"{}"相关

Step 3: 执行更新
- 如果≤2个相关文档：
  - 使用Read读取完整文档
  - 根据任务内容补充"待补充"部分
  - 使用Edit更新文档
- 如果>2个相关文档：
  - 生成待补充清单
  - 追加到 markdown/文档待补充清单.md

Step 4: DEBUG clean check
```bash
Grep("DEBUG|print.*debug|console.log.*test", path=".", glob="*.py", output_mode="content", -n=True)
```

Step 5: Mark step4 completed (CRITICAL - triggers archive)
Use Write tool to update task metadata:
1. Read latest task's .task-meta.json
2. Set workflow_state.steps.step4_cleanup.status = "completed"
3. Write back the updated JSON

Step 6: Output completion report
Format:
```
==============================================
Cleanup Work Completion Report
==============================================

Docs updated: [file list]
DEBUG cleanup: [count] found, [locations]
Task archive: tasks/task-XXX/
  - context.md: OK
  - solution.md: OK
Step4 marked: COMPLETED (archive hook will trigger)
==============================================
```

**IMPORTANT**:
- You are an independent subagent with full tool access
- Do NOT ask user, complete all steps autonomously
- MUST execute Step 5 to mark step4_cleanup completed
- After marking, post-archive-hook will auto-move task directory
- Keep output concise, focus on execution
""".format(
            task_desc,
            len(docs_read),
            len(code_changes),
            task_desc
        )

        # 写入临时任务文件
        agent_task_file = os.path.join(cwd, '.claude', '.agent-doc-update.txt')
        with open(agent_task_file, 'w', encoding='utf-8') as f:
            f.write(agent_prompt)

        logger.info(u"子代理任务文件已创建", {"file": agent_task_file})

        # 注入子代理调用指令
        message = u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 启动文档更新子代理
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

检测到步骤4（收尾归档）开始，系统将启动专门的子代理完成以下工作：
- 📝 自动更新markdown文档中的"待补充"内容
- 🧹 检查并清理DEBUG代码
- 📦 整理任务归档

**请使用Task工具启动子代理**：

```
Task(
    subagent_type="general-purpose",
    description="文档更新与收尾工作",
    prompt=Read("{}").content
)
```

子代理将独立完成所有收尾工作，不消耗主会话上下文。
完成后会输出详细报告。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(agent_task_file)

        logger.finish(success=True, message=u"子代理触发指令已注入")
        return message

    except Exception as e:
        logger.error(u"子代理触发失败", e)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return None

def inject_next_step_prompt(next_step, meta, cwd=None):
    """注入下一步指令"""
    step_config = meta["workflow_state"]["steps"][next_step]

    # 特殊处理：步骤4启动子代理
    if next_step == "step4_cleanup" and cwd:
        agent_message = trigger_doc_update_agent(meta, cwd)
        if agent_message:
            output = {
                "continue": True,
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": agent_message
                }
            }
            print(json.dumps(output, ensure_ascii=False))
            return

    # 常规步骤：注入提示
    message = u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 工作流提醒: {}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(step_config.get("description", next_step), step_config["prompt"])

    output = {
        "continue": True,
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": message
        }
    }

    print(json.dumps(output, ensure_ascii=False))

def detect_failure_pattern(meta):
    """Detect failure patterns (v20.1)"""
    failures = meta["metrics"].get("failures", [])

    if len(failures) < 2:
        return "single_failure"

    recent_failures = failures[-3:]
    error_messages = [f.get("error", "")[:100] for f in recent_failures]

    if len(set(error_messages)) == 1:
        return "repeated_same_error"

    return "varied_errors"

def should_trigger_expert_diagnosis(meta):
    """Check if expert diagnosis should be triggered (v20.1)"""

    if meta["metrics"]["expert_review_triggered"]:
        return False, None

    task_type = meta.get("task_type", "feature")
    complexity = meta.get("task_complexity", "standard")
    failure_count = meta["metrics"]["failure_count"]
    failure_pattern = detect_failure_pattern(meta)

    if failure_pattern == "repeated_same_error" and failure_count >= 3:
        return True, "Repeated same error 3 times"

    if task_type in ["feature", "bugfix"] and failure_count >= 5:
        return True, "Task failed {} times".format(failure_count)

    if task_type == "feature":
        critical_count = meta["metrics"].get("critical_violation_count", 0)
        if critical_count >= 4:
            return True, "CRITICAL violations {} times, may misunderstand rules".format(critical_count)

    if task_type == "bugfix" and failure_count >= 3:
        return True, "Bugfix failed 3 times, may be mislocated"

    if complexity == "complex":
        time_in_step3 = meta["workflow_state"]["steps"]["step3_execute"].get("elapsed_minutes", 0)
        if time_in_step3 >= 30 and failure_count >= 2:
            return True, "Complex task taking too long with difficulties"

    return False, None

def inject_expert_review_warning(meta, trigger_reason=None):
    """Inject expert review warning (v20.1: enhanced)"""
    task_desc = meta["task_description"]
    failure_count = meta["metrics"]["failure_count"]
    last_error = meta["workflow_state"]["steps"]["step3_execute"].get("last_error", u"Unknown error")
    reason = trigger_reason if trigger_reason else "Multiple failures detected"

    sys.stderr.write(u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  Warning: Task encountering difficulties, expert review recommended
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Task**: {}
**Failure Count**: {} times
**Trigger Reason**: {}
**Recent Error**: {}

**Expert Review Process**:
1. System will inject detailed debugging context
2. AI will re-analyze root cause
3. Provide deeper solution

**Continue current approach?**
- Input "trigger expert review" → Start deep analysis
- Input "continue trying" → Keep current approach

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(task_desc, failure_count, reason, last_error))

def main():
    logger = HookLogger("unified-workflow-driver")
    logger.start()

    try:
        # 读取stdin输入
        data = json.load(sys.stdin)
        tool_name = data.get('tool_name', '')
        cwd = os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd())

        # 快速检查: 是否有活跃任务
        active_flag_path = os.path.join(cwd, '.claude', '.task-active.json')
        if not os.path.exists(active_flag_path):
            logger.decision("skip", u"无活跃任务,跳过")
            output = {"continue": True}
            print(json.dumps(output, ensure_ascii=False))
            logger.finish(success=True, message=u"跳过")
            sys.exit(0)

        # 加载活跃任务
        active_flag = load_json(active_flag_path)
        if not active_flag:
            logger.error(u"活跃任务标志损坏")
            output = {"continue": True}
            print(json.dumps(output, ensure_ascii=False))
            sys.exit(0)

        task_dir = active_flag["task_dir"]
        meta_path = os.path.join(task_dir, '.task-meta.json')
        meta = load_json(meta_path)

        if not meta:
            logger.error(u"任务元数据损坏")
            output = {"continue": True}
            print(json.dumps(output, ensure_ascii=False))
            sys.exit(0)

        current_step = meta["workflow_state"]["current_step"]
        last_injection = meta["workflow_state"].get("last_injection_step", None)

        logger.info(u"处理工具调用", {
            "tool": tool_name,
            "task_id": meta["task_id"],
            "current_step": current_step
        })

        # 工具分发处理
        step_changed = False

        if tool_name == "Read":
            # 更新文档阅读记录
            file_path = data.get('tool_input', {}).get('file_path', '')
            if update_docs_read(meta, file_path):
                logger.info(u"文档阅读记录已更新", {"file": file_path})
                step_changed = check_step_completed(current_step, meta)

        elif tool_name in ["Write", "Edit"]:
            # 记录代码修改
            if update_code_changes(meta, data):
                logger.info(u"代码修改已记录")

        elif tool_name == "Bash":
            # 检测测试结果
            result = data.get('result', {})
            result_str = json.dumps(result, ensure_ascii=False)

            if check_test_failure(result_str):
                meta["metrics"]["failure_count"] += 1

                # 记录错误
                if "failures" not in meta["metrics"]:
                    meta["metrics"]["failures"] = []

                error_record = {
                    "timestamp": datetime.now().isoformat(),
                    "error": result_str[:500],  # 限制长度
                    "command": data.get('tool_input', {}).get('command', '')
                }
                meta["metrics"]["failures"].append(error_record)

                # 更新step3的last_error
                if current_step == "step3_execute":
                    meta["workflow_state"]["steps"]["step3_execute"]["last_error"] = result_str[:200]
                    meta["workflow_state"]["steps"]["step3_execute"]["last_error_time"] = datetime.now().isoformat()

                logger.info(u"Detected test failure", {
                    "failure_count": meta["metrics"]["failure_count"]
                })

                # v20.1: Enhanced expert diagnosis trigger logic
                should_trigger, trigger_reason = should_trigger_expert_diagnosis(meta)

                if should_trigger:
                    inject_expert_review_warning(meta, trigger_reason)
                    meta["metrics"]["expert_review_triggered"] = True

                    # Desktop notification
                    try:
                        from vscode_notify import notify_warning
                        notify_warning("Expert diagnosis recommended", trigger_reason)
                    except:
                        pass

                    step_changed = True

        # 更新时间戳
        meta["updated_at"] = datetime.now().isoformat()

        # 检查步骤是否刚刚完成
        if step_changed or check_step_completed(current_step, meta):
            if meta["workflow_state"]["steps"][current_step]["status"] != "completed":
                # 标记当前步骤完成
                meta["workflow_state"]["steps"][current_step]["status"] = "completed"
                meta["workflow_state"]["steps"][current_step]["completed_at"] = datetime.now().isoformat()

                # 获取下一步
                next_step = get_next_step(current_step)

                if next_step and current_step != last_injection:
                    # 更新状态机
                    meta["workflow_state"]["current_step"] = next_step
                    meta["workflow_state"]["steps"][next_step]["status"] = "in_progress"
                    meta["workflow_state"]["last_injection_step"] = next_step

                    # 保存状态机
                    save_json(meta_path, meta)
                    save_json(active_flag_path, {
                        **active_flag,
                        "current_step": next_step,
                        "updated_at": datetime.now().isoformat()
                    })

                    # v20.1: Desktop notification - Step completed
                    next_step_desc = meta["workflow_state"]["steps"][next_step].get("description", next_step)
                    notify_info(
                        "Step completed",
                        "Current: {} → Next: {}".format(current_step, next_step_desc)
                    )

                    # Inject next step prompt
                    inject_next_step_prompt(next_step, meta, cwd)

                    logger.info(u"Step completed", {
                        "from": current_step,
                        "to": next_step
                    })
                    logger.finish(success=True, message=u"步骤{}完成,进入{}".format(current_step, next_step))
                    sys.exit(0)

        # === v20.2 新增：循环检测与专家触发 ===
        expert_check = check_expert_trigger(meta, cwd)

        if expert_check["should_trigger"] and not meta["metrics"].get("expert_review_triggered", False):
            # 触发专家审查
            expert_prompt = launch_meta_expert(expert_check, meta, cwd, logger)

            if expert_prompt:
                # 注入专家分析提示
                output = {
                    "continue": True,
                    "hookSpecificOutput": {
                        "hookEventName": "PostToolUse",
                        "additionalContext": expert_prompt
                    }
                }
                print(json.dumps(output, ensure_ascii=False))

                # 桌面通知
                try:
                    from vscode_notify import notify_warning
                    notify_warning(
                        u"专家审查已触发",
                        u"循环类型: {} | 置信度: {:.0%}".format(
                            expert_check["loop_type"],
                            expert_check["confidence"]
                        )
                    )
                except:
                    pass

                logger.finish(success=True, message=u"专家审查已触发")
                sys.exit(0)

        # 保存状态机(即使没有步骤跃迁,也要保存更新)
        save_json(meta_path, meta)

        # 当前步骤未完成,放行
        logger.decision("continue", u"步骤{}进行中".format(current_step))
        output = {"continue": True}
        print(json.dumps(output, ensure_ascii=False))
        logger.finish(success=True, message=u"放行")
        sys.exit(0)

    except Exception as e:
        logger.error(u"Hook执行失败", e)
        import traceback
        traceback.print_exc(file=sys.stderr)
        output = {"continue": True}
        print(json.dumps(output, ensure_ascii=False))
        logger.finish(success=False, message=u"执行异常")
        sys.exit(0)

if __name__ == "__main__":
    main()
