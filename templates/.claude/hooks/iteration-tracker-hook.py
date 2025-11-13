#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
IterationTracker Hook - 迭代追踪与专家触发系统 (v20.2.0)

触发时机: 每次用户输入后 (user-prompt-submit)
职责:
1. 意图分类 (bug_fix/feature_implementation/general)
2. 反馈识别 (是否为失败反馈)
3. 情感分析 (positive/negative/frustrated)
4. 更新迭代计数器 (跨会话累计)
5. 同步到 .task-meta.json (持久化)
6. 循环检测与专家触发

退出码:
- 0: 成功
"""

import sys
import json
import os
import re
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


# ==================== 意图分类器 ====================

def classify_intent(user_input: str) -> dict:
    """
    意图分类器 - 识别任务类型和反馈特征

    返回:
    {
        "task_type": "bug_fix" | "feature_implementation" | "general",
        "is_feedback": bool,
        "sentiment": "positive" | "negative" | "frustrated" | "neutral",
        "confidence": float
    }
    """

    # === 规则1: Bug修复特征 ===
    bug_keywords = [
        r'(?:修复|fix|bug|错误|报错|崩溃|不work|不生效)',
        r'(?:还是|仍然|依然).*(?:不行|失败|有问题)',
        r'测试.*(?:失败|不通过|有问题)'
    ]

    # === 规则2: 反馈特征 ===
    feedback_keywords = [
        r'(?:还是|仍然|依然|又|再次).*(?:不行|有问题|失败)',
        r'(?:不对|不是|不太对|不太行)',
        r'(?:能不能|可以|希望|想要).*(?:改成|换成|调整)',
        r'(?:又|还|还有).*(?:问题|错误|Bug)',
        r'(?:测试|试了|运行).*(?:失败|不行|有问题)'
    ]

    # === 规则3: 需求实现特征 ===
    feature_keywords = [
        r'(?:实现|开发|添加|新增|创建).*(?:功能|系统|玩法)',
        r'(?:我想要|需要|希望有).*(?:一个|系统|功能)'
    ]

    # === 情感分析 ===
    negative_sentiment = [
        r'(?:还是不行|完全不work|根本没用)',
        r'(?:怎么|为什么).*(?:还是|仍然)',
        r'(?:又出|又有|又是).*(?:问题|错误)'
    ]

    frustrated_sentiment = [
        r'(?:沮丧|无语|崩溃|绝望)',
        r'(?:一直|总是|每次).*(?:失败|不行)',
        r'(?:怎么办|没办法|搞不定)'
    ]

    positive_sentiment = [
        r'(?:好了|成功|搞定|修复了|解决了)',
        r'(?:没问题|可以了|work|正常)'
    ]

    intent = {
        "task_type": "general",
        "is_feedback": False,
        "sentiment": "neutral",
        "confidence": 0.0
    }

    # === 分类逻辑 ===
    for pattern in bug_keywords:
        if re.search(pattern, user_input, re.IGNORECASE):
            intent["task_type"] = "bug_fix"
            intent["confidence"] = 0.8
            break

    for pattern in feature_keywords:
        if re.search(pattern, user_input, re.IGNORECASE):
            intent["task_type"] = "feature_implementation"
            intent["confidence"] = 0.7
            break

    # 判断是否为反馈
    for pattern in feedback_keywords:
        if re.search(pattern, user_input, re.IGNORECASE):
            intent["is_feedback"] = True
            intent["confidence"] = max(intent["confidence"], 0.9)
            break

    # 情感分析
    for pattern in frustrated_sentiment:
        if re.search(pattern, user_input, re.IGNORECASE):
            intent["sentiment"] = "frustrated"
            break

    if intent["sentiment"] == "neutral":
        for pattern in negative_sentiment:
            if re.search(pattern, user_input, re.IGNORECASE):
                intent["sentiment"] = "negative"
                break

    if intent["sentiment"] == "neutral":
        for pattern in positive_sentiment:
            if re.search(pattern, user_input, re.IGNORECASE):
                intent["sentiment"] = "positive"
                break

    return intent


# ==================== 状态更新器 ====================

def load_json(file_path):
    """加载JSON文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return None


def save_json(file_path, data):
    """保存JSON文件"""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        sys.stderr.write(u"[ERROR] 保存JSON失败: {}\n".format(e))
        return False


def get_active_task_meta_path(cwd):
    """获取当前活跃任务的元数据路径"""
    workflow_state_path = os.path.join(cwd, '.claude', 'workflow-state.json')
    workflow_state = load_json(workflow_state_path)

    if not workflow_state:
        return None

    task_id = workflow_state.get("task_id")
    if not task_id:
        return None

    meta_path = os.path.join(cwd, 'tasks', task_id, '.task-meta.json')
    if not os.path.exists(meta_path):
        return None

    return meta_path


def update_tracking_state(intent: dict, user_input: str, cwd: str, logger):
    """
    更新迭代追踪状态

    策略:
    1. 更新 workflow-state.json (会话级)
    2. 同步到 .task-meta.json (持久化)
    """

    workflow_state_path = os.path.join(cwd, '.claude', 'workflow-state.json')
    workflow_state = load_json(workflow_state_path)

    if not workflow_state:
        logger.info(u"workflow-state.json不存在，跳过追踪")
        return

    # === 初始化任务类型 ===
    if "task_type" not in workflow_state:
        workflow_state["task_type"] = intent["task_type"]

    # === Bug修复追踪 ===
    if intent["task_type"] == "bug_fix" or workflow_state.get("task_type") == "bug_fix":
        if "bug_fix_tracking" not in workflow_state:
            workflow_state["bug_fix_tracking"] = {
                "enabled": True,
                "bug_description": user_input[:100],
                "iterations": [],
                "loop_indicators": {
                    "same_file_edit_count": 0,
                    "failed_test_count": 0,
                    "negative_feedback_count": 0,
                    "time_spent_minutes": 0
                },
                "expert_triggered": False
            }

        # 如果是反馈，记录新迭代
        if intent["is_feedback"]:
            tracking = workflow_state["bug_fix_tracking"]
            iteration_id = len(tracking["iterations"]) + 1

            tracking["iterations"].append({
                "iteration_id": iteration_id,
                "timestamp": datetime.now().isoformat(),
                "trigger": "user_feedback",
                "user_feedback": user_input,
                "feedback_sentiment": intent["sentiment"],
                "changes_made": [],  # 将在post-tool-use中填充
                "test_result": "pending"
            })

            # 更新循环指标
            if intent["sentiment"] in ["negative", "frustrated"]:
                tracking["loop_indicators"]["negative_feedback_count"] += 1
                tracking["loop_indicators"]["failed_test_count"] += 1

            logger.info(u"记录Bug修复迭代", {
                "iteration_id": iteration_id,
                "sentiment": intent["sentiment"]
            })

    # === 需求实现追踪 ===
    elif intent["task_type"] == "feature_implementation" or workflow_state.get("task_type") == "feature_implementation":
        if "feature_tracking" not in workflow_state:
            workflow_state["feature_tracking"] = {
                "enabled": True,
                "feature_description": user_input[:200],
                "iterations": [],
                "requirement_changes": [],
                "expert_triggered": False
            }

        if intent["is_feedback"]:
            tracking = workflow_state["feature_tracking"]
            iteration_id = len(tracking["iterations"]) + 1

            # 检测需求变化
            if re.search(r'(?:改成|换成|调整|不是.*是)', user_input):
                tracking["requirement_changes"].append({
                    "timestamp": datetime.now().isoformat(),
                    "adjustment": user_input,
                    "change_type": "scope_adjustment"
                })

            tracking["iterations"].append({
                "iteration_id": iteration_id,
                "timestamp": datetime.now().isoformat(),
                "user_satisfaction": "dissatisfied" if intent["sentiment"] in ["negative", "frustrated"] else "neutral",
                "adjustment_request": user_input,
                "changes_made": []
            })

            logger.info(u"记录需求调整迭代", {
                "iteration_id": iteration_id,
                "satisfaction": "dissatisfied" if intent["sentiment"] == "negative" else "neutral"
            })

    # 保存workflow-state
    save_json(workflow_state_path, workflow_state)

    # === 同步到 .task-meta.json ===
    meta_path = get_active_task_meta_path(cwd)
    if meta_path:
        task_meta = load_json(meta_path)
        if task_meta:
            # 更新tracking_state
            if "tracking_state" not in task_meta:
                task_meta["tracking_state"] = {}

            task_meta["tracking_state"]["bug_fix_tracking"] = workflow_state.get("bug_fix_tracking")
            task_meta["tracking_state"]["feature_tracking"] = workflow_state.get("feature_tracking")
            task_meta["task_type"] = workflow_state.get("task_type", "general")
            task_meta["updated_at"] = datetime.now().isoformat()

            save_json(meta_path, task_meta)
            logger.info(u"已同步到task-meta.json")


# ==================== 主函数 ====================

def main():
    logger = HookLogger("iteration-tracker-hook")
    logger.start()

    try:
        # 读取stdin输入
        data = json.load(sys.stdin)
        user_input = data.get('user_prompt', '')
        cwd = os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd())

        # 意图分类
        intent = classify_intent(user_input)

        logger.info(u"意图分类", {
            "task_type": intent["task_type"],
            "is_feedback": intent["is_feedback"],
            "sentiment": intent["sentiment"],
            "confidence": intent["confidence"]
        })

        # 更新追踪状态
        if intent["is_feedback"] or intent["task_type"] in ["bug_fix", "feature_implementation"]:
            update_tracking_state(intent, user_input, cwd, logger)

        # 输出控制JSON (放行)
        output = {"continue": True}
        print(json.dumps(output, ensure_ascii=False))

        logger.finish(success=True, message=u"追踪完成")
        sys.exit(0)

    except Exception as e:
        logger.error(u"Hook执行失败", e)
        import traceback
        traceback.print_exc(file=sys.stderr)

        # 即使失败也放行
        output = {"continue": True}
        print(json.dumps(output, ensure_ascii=False))
        logger.finish(success=False, message=u"执行异常")
        sys.exit(0)


if __name__ == '__main__':
    main()
