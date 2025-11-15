#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SessionStart Hook - 会话生命周期管理器 (v20.0.3)

触发时机: 每次会话启动时
职责:
1. 检测会话来源(startup/resume/clear/compact)
2. 查找最近修改的任务目录
3. 加载.task-meta.json到 .claude/.task-active.json
4. 如果是resume,分析任务状态并注入恢复提示
5. 写入环境变量供后续hooks使用

退出码:
- 0: 成功
"""

import sys
import json
import os
from datetime import datetime
from pathlib import Path
import io

# 修复Windows GBK编码问题
if sys.platform == 'win32':
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 导入统一日志记录器
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

def find_latest_task(project_path):
    """查找最近修改的任务目录"""
    tasks_dir = Path(project_path) / "tasks"
    if not tasks_dir.exists():
        return None

    task_dirs = [
        d for d in tasks_dir.iterdir()
        if d.is_dir() and (d.name.startswith("task-") or d.name.startswith(u"任务-"))
    ]

    if not task_dirs:
        return None

    # 返回最近修改的任务目录
    latest_task = max(task_dirs, key=lambda d: d.stat().st_mtime)
    return str(latest_task)

def load_task_meta(task_dir):
    """加载任务元数据"""
    meta_file = os.path.join(task_dir, '.task-meta.json')
    if not os.path.exists(meta_file):
        return None

    try:
        with open(meta_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        sys.stderr.write(u"[ERROR] 加载任务元数据失败: {}\n".format(e))
        return None

def restore_tracking_state(meta, cwd):
    """
    恢复迭代追踪状态到workflow-state.json
    返回恢复的迭代数量
    """
    tracking_state = meta.get("tracking_state", {})
    if not tracking_state:
        return 0

    workflow_state_path = os.path.join(cwd, '.claude', 'workflow-state.json')

    try:
        # 读取现有workflow-state
        if os.path.exists(workflow_state_path):
            with open(workflow_state_path, 'r', encoding='utf-8') as f:
                workflow_state = json.load(f)
        else:
            workflow_state = {}

        # 恢复bug_fix_tracking
        iterations_count = 0
        if tracking_state.get("bug_fix_tracking"):
            workflow_state["bug_fix_tracking"] = tracking_state["bug_fix_tracking"]
            iterations_count = len(tracking_state["bug_fix_tracking"].get("iterations", []))

        # 恢复feature_tracking
        if tracking_state.get("feature_tracking"):
            workflow_state["feature_tracking"] = tracking_state["feature_tracking"]
            iterations_count = len(tracking_state["feature_tracking"].get("iterations", []))

        # 设置任务类型
        if "task_type" in meta:
            workflow_state["task_type"] = meta["task_type"]

        # 标记为恢复的会话
        workflow_state["resumed_from_task"] = meta["task_id"]
        workflow_state["session_start_time"] = datetime.now().isoformat()

        # 保存更新后的workflow-state
        with open(workflow_state_path, 'w', encoding='utf-8') as f:
            json.dump(workflow_state, f, indent=2, ensure_ascii=False)

        return iterations_count

    except Exception as e:
        sys.stderr.write(u"[ERROR] 恢复追踪状态失败: {}\n".format(e))
        return 0

def write_json(file_path, data):
    """写入JSON文件"""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        sys.stderr.write(u"[ERROR] 写入JSON失败: {}\n".format(e))
        return False

def generate_smart_resume_prompt(meta):
    """根据任务状态生成智能恢复提示"""
    task_desc = meta["task_description"]
    current_step = meta["workflow_state"]["current_step"]
    failure_count = meta["metrics"]["failure_count"]
    docs_read = len(meta["metrics"]["docs_read"])

    step_names = {
        "step0_context": u"步骤0: 理解项目上下文",
        "step1_understand": u"步骤1: 理解任务需求",
        "step2_docs": u"步骤2: 查阅文档",
        "step3_execute": u"步骤3: 执行实施",
        "step4_cleanup": u"步骤4: 收尾归档"
    }

    base_prompt = u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 任务恢复: {}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**任务ID**: {}
**上次状态**: {}
**文档已读**: {}个
""".format(task_desc, meta["task_id"], step_names.get(current_step, current_step), docs_read)

    # 根据步骤和状态添加具体建议
    if current_step == "step3_execute" and failure_count > 0:
        last_error = meta["workflow_state"]["steps"]["step3_execute"].get("last_error", u"未知错误")
        base_prompt += u"""
**失败次数**: {}/3
**最近错误**: {}

**建议行动**:
1. 分析上次失败的根本原因
2. 检查是否违反CRITICAL规范
3. 重新实现并运行测试

**如何进入步骤4**:
当功能实现且测试通过后,请输入: "已修复" 或 "测试通过"
""".format(failure_count, last_error)

    elif current_step == "step2_docs":
        min_docs = meta["workflow_state"]["steps"]["step2_docs"].get("min_docs", 3)
        base_prompt += u"""
**文档进度**: {}/{}个

**建议行动**:
继续阅读文档,还需{}个文档即可进入步骤3

**已读文档**:
{}
""".format(docs_read, min_docs, max(0, min_docs - docs_read),
           '\n'.join(['- ' + doc for doc in meta["metrics"]["docs_read"]]))

    elif current_step == "step4_cleanup":
        base_prompt += u"""
**收尾进度**: 进行中

**建议行动**:
1. 补充文档 (≤2个待补充文档自动完善)
2. 清理DEBUG代码
3. 归档任务到 solution.md

**完成后**: 输入 "收尾完成" 或 "任务完成"
"""

    base_prompt += u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    return base_prompt

def main():
    logger = HookLogger("session-start-hook")
    logger.start()

    try:
        # 读取stdin输入
        data = json.load(sys.stdin)
        source = data.get('source', 'unknown')
        transcript_path = data.get('transcript_path', '')
        cwd = os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd())

        logger.info(u"会话启动", {"source": source, "cwd": cwd})

        # 查找最近的任务
        latest_task_dir = find_latest_task(cwd)

        if not latest_task_dir:
            logger.decision("skip", u"未找到任务目录,跳过")
            output = {"continue": True}
            print(json.dumps(output, ensure_ascii=False))
            logger.finish(success=True, message=u"无任务")
            sys.exit(0)

        # 加载任务状态
        meta = load_task_meta(latest_task_dir)
        if not meta:
            logger.error(u"加载任务元数据失败")
            output = {"continue": True}
            print(json.dumps(output, ensure_ascii=False))
            logger.finish(success=False, message=u"元数据损坏")
            sys.exit(0)

        # 写入活跃任务标志
        active_flag = {
            "active_task_id": meta["task_id"],
            "task_dir": latest_task_dir,
            "current_step": meta["workflow_state"]["current_step"],
            "session_source": source,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        active_flag_path = os.path.join(cwd, '.claude', '.task-active.json')
        write_json(active_flag_path, active_flag)

        logger.info(u"活跃任务已加载", {
            "task_id": meta["task_id"],
            "current_step": meta["workflow_state"]["current_step"]
        })

        # 恢复迭代追踪状态
        iterations_restored = restore_tracking_state(meta, cwd)
        if iterations_restored > 0:
            logger.info(u"恢复迭代追踪", {"iterations": iterations_restored})

        # 如果是恢复会话,注入智能恢复提示
        if source == 'resume':
            resume_prompt = generate_smart_resume_prompt(meta)

            # 如果有历史迭代,添加专家警告
            if iterations_restored >= 2:
                expert_warning = u"""
⚠️ **专家审查警告**
该任务已有 {} 次迭代历史
如果问题仍未解决,专家审查可能会被触发进行深度分析
""".format(iterations_restored)
                resume_prompt += expert_warning

            output = {
                "continue": True,
                "injectedContext": resume_prompt
            }

            print(json.dumps(output, ensure_ascii=False))
            logger.finish(success=True, message=u"恢复提示已注入")
        else:
            output = {"continue": True}
            print(json.dumps(output, ensure_ascii=False))
            logger.finish(success=True, message=u"活跃任务已加载")

        sys.exit(0)

    except Exception as e:
        logger.error(u"Hook执行失败", e)
        import traceback
        traceback.print_exc(file=sys.stderr)
        output = {"continue": True}
        print(json.dumps(output, ensure_ascii=False))
        logger.finish(success=False, message=u"执行异常")
        sys.exit(0)

if __name__ == '__main__':
    main()
