#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
IterationTracker Hook - 迭代追踪与专家触发系统 (v20.3.0)

触发时机:
1. user-prompt-submit: 用户反馈识别
2. post-tool-use: 工具失败识别 (v20.3新增)

职责:
1. 意图分类 (bug_fix/feature_implementation/general)
2. 反馈识别 (用户反馈 OR 工具失败)
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

def classify_intent(user_input: str, tool_error=None) -> dict:
    """
    意图分类器 - 识别任务类型和反馈特征 (v20.3: 支持工具失败识别)

    参数:
        user_input: 用户输入文本
        tool_error: 工具错误信息（可选，v20.3新增）

    返回:
    {
        "task_type": "bug_fix" | "feature_implementation" | "general",
        "is_feedback": bool,
        "sentiment": "positive" | "negative" | "frustrated" | "neutral",
        "confidence": float,
        "feedback_source": "user" | "tool_error"  # v20.3新增
    }
    """

    intent = {
        "task_type": "general",
        "is_feedback": False,
        "sentiment": "neutral",
        "confidence": 0.0,
        "feedback_source": "user",
        "is_confirmation": False  # v20.3: 用户确认标志
    }

    # === v20.3新增：工具失败识别 ===
    if tool_error:
        # 工具失败视为负面反馈
        intent["is_feedback"] = True
        intent["sentiment"] = "negative"
        intent["confidence"] = 0.95
        intent["feedback_source"] = "tool_error"

        # 根据错误类型推断任务类型
        if re.search(r'(?:File has been|unexpectedly modified|conflict)', tool_error, re.IGNORECASE):
            # 文件修改冲突 → 可能是Bug修复时反复修改
            intent["task_type"] = "bug_fix"
        elif re.search(r'(?:not found|missing|does not exist)', tool_error, re.IGNORECASE):
            # 文件不存在 → 可能是新功能开发
            intent["task_type"] = "feature_implementation"

        return intent

    # === 原有逻辑：用户反馈识别 ===

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
        r'(?:好了|成功|搞定|修复了|解决了|已修复)',
        r'(?:没问题|可以了|work|正常|完成了)'
    ]

    # v20.3: 用户确认关键词（用于设置user_confirmed标志）
    confirmation_keywords = [
        r'(?:已修复|修复完成|已解决|解决了)',
        r'(?:好了|可以了|没问题了|work了)',
        r'(?:/mc-confirm)'  # 显式确认命令
    ]

    # v20.2.7: 收尾意愿关键词（新增）
    cleanup_intent_patterns = {
        "proceed": [
            r'(?:需要|执行|开始|进行).*收尾',
            r'(?:收尾|清理|归档)',
        ],
        "skip": [
            r'(?:直接|立即|现在).*结束',
            r'跳过.*收尾',
            r'不需要.*收尾',
        ]
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

    # v20.3: 检测用户确认
    for pattern in confirmation_keywords:
        if re.search(pattern, user_input, re.IGNORECASE):
            intent["is_confirmation"] = True
            intent["is_feedback"] = True  # 确认也是一种反馈
            intent["sentiment"] = "positive"  # 确认意味着正面结果
            break

    # v20.2.7: 检测收尾意愿
    for action, patterns in cleanup_intent_patterns.items():
        for pattern in patterns:
            if re.search(pattern, user_input, re.IGNORECASE):
                intent["is_cleanup_response"] = True
                intent["cleanup_intent"] = action  # "proceed" or "skip"
                break
        if intent.get("is_cleanup_response"):
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


def atomic_update_json(file_path, update_func, max_retries=5, retry_delay=0.05):
    """原子更新JSON文件 (v20.2.6增强: 使用msvcrt实现可靠文件锁)

    参数:
        file_path: JSON文件路径
        update_func: 更新函数，接收当前数据，返回新数据
        max_retries: 最大重试次数
        retry_delay: 重试间隔秒数

    返回:
        bool: 成功返回True

    v20.2.6变更:
    - Windows: 优先使用msvcrt.locking()实现系统级文件锁
    - 降级: 使用.lock文件机制（兼容旧版本Python或非Windows平台）
    - Unix/Linux: 使用O_EXCL标志
    """
    import time

    # === v20.2.6: 尝试使用msvcrt（Windows系统级文件锁）===
    if sys.platform == 'win32':
        try:
            import msvcrt
            return _atomic_update_with_msvcrt(file_path, update_func, max_retries, retry_delay)
        except ImportError:
            # msvcrt不可用（非CPython或旧版本），降级到.lock文件机制
            pass

    # === 降级方案: 使用.lock文件机制 ===
    lock_file = file_path + '.lock'

    for attempt in range(max_retries):
        try:
            # 尝试创建锁文件（文件存在则失败，实现互斥）
            if sys.platform == 'win32':
                # Windows: 使用文件存在性检查
                if os.path.exists(lock_file):
                    raise FileExistsError("Lock file exists")
                # 创建锁文件
                with open(lock_file, 'w') as f:
                    f.write(str(os.getpid()))
            else:
                # Unix/Linux: 使用O_EXCL标志
                fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
                os.close(fd)

            try:
                # 获得锁，执行更新
                data = load_json(file_path)
                if data is None:
                    data = {}

                updated_data = update_func(data)
                save_json(file_path, updated_data)
                return True

            finally:
                # 释放锁
                try:
                    os.remove(lock_file)
                except:
                    pass

        except (FileExistsError, OSError) as e:
            # 锁被占用，等待后重试
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))  # 指数退避
            else:
                sys.stderr.write(u"[ERROR] 文件锁获取失败，已重试{}次\n".format(max_retries))
                return False
        except Exception as e:
            sys.stderr.write(u"[ERROR] 原子更新失败: {}\n".format(e))
            # 清理锁文件
            try:
                os.remove(lock_file)
            except:
                pass
            return False

    return False


def _atomic_update_with_msvcrt(file_path, update_func, max_retries=5, retry_delay=0.05):
    """使用msvcrt实现原子更新 (v20.2.6新增)

    Windows系统级文件锁，比.lock文件机制更可靠
    """
    import msvcrt
    import time

    for attempt in range(max_retries):
        try:
            # 打开文件（如果不存在则创建）
            if not os.path.exists(file_path):
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump({}, f)

            with open(file_path, 'r+', encoding='utf-8') as f:
                try:
                    # 获取排他锁（非阻塞）
                    msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)

                    # 读取-更新-写入
                    f.seek(0)
                    try:
                        data = json.load(f)
                    except:
                        data = {}

                    updated_data = update_func(data)

                    f.seek(0)
                    f.truncate()
                    json.dump(updated_data, f, indent=2, ensure_ascii=False)

                    return True

                finally:
                    # 释放锁
                    try:
                        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                    except:
                        pass

        except IOError:
            # 锁被占用，重试
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))  # 指数退避
            else:
                sys.stderr.write(u"[ERROR] msvcrt文件锁获取失败，已重试{}次\n".format(max_retries))
                return False
        except Exception as e:
            sys.stderr.write(u"[ERROR] msvcrt原子更新失败: {}\n".format(e))
            return False

    return False


def find_latest_task_meta(cwd):
    """降级方案: 扫描tasks目录找最新任务的元数据 (v20.3新增)"""
    tasks_dir = os.path.join(cwd, 'tasks')
    if not os.path.exists(tasks_dir):
        return None

    try:
        task_dirs = [
            d for d in os.listdir(tasks_dir)
            if os.path.isdir(os.path.join(tasks_dir, d)) and
            (d.startswith('task-') or d.startswith(u'任务-'))
        ]

        if not task_dirs:
            return None

        # 按修改时间排序，取最新的
        task_dirs_with_time = []
        for task_dir in task_dirs:
            task_path = os.path.join(tasks_dir, task_dir)
            mtime = os.path.getmtime(task_path)
            task_dirs_with_time.append((task_dir, mtime))

        task_dirs_with_time.sort(key=lambda x: x[1], reverse=True)
        latest_task_dir = task_dirs_with_time[0][0]

        meta_path = os.path.join(tasks_dir, latest_task_dir, '.task-meta.json')
        if os.path.exists(meta_path):
            return meta_path
    except Exception as e:
        sys.stderr.write(u"[WARN] 降级方案失败: {}\n".format(e))

    return None


def get_active_task_meta_path(cwd, max_retries=3, retry_delay=0.1):
    """获取当前活跃任务的元数据路径 (v20.3: 增加重试机制解决并行竞态)

    参数:
        cwd: 项目根目录
        max_retries: 最大重试次数（应对并行Hook竞态条件）
        retry_delay: 重试间隔秒数

    返回:
        str: .task-meta.json 文件路径，或 None
    """
    import time

    workflow_state_path = os.path.join(cwd, '.claude', 'workflow-state.json')

    # 重试机制：应对user-prompt-submit-hook.py并行写入延迟
    for attempt in range(max_retries):
        workflow_state = load_json(workflow_state_path)

        if workflow_state:
            task_id = workflow_state.get("task_id")
            if task_id:
                meta_path = os.path.join(cwd, 'tasks', task_id, '.task-meta.json')
                if os.path.exists(meta_path):
                    return meta_path

        # 如果不是最后一次尝试，等待后重试
        if attempt < max_retries - 1:
            sys.stderr.write(u"[RETRY] workflow-state.json未就绪，等待{}秒后重试 ({}/{})\n".format(
                retry_delay, attempt + 1, max_retries
            ))
            time.sleep(retry_delay)

    # 所有重试失败，启用降级方案：直接扫描tasks目录
    sys.stderr.write(u"[FALLBACK] workflow-state.json不可用，使用降级方案扫描tasks目录\n")
    return find_latest_task_meta(cwd)


def record_user_feedback_to_conversation(task_dir, user_input, intent):
    """v20.2.7: 记录用户反馈到会话历史"""
    conversation_file = os.path.join(task_dir, '.conversation.jsonl')

    if not os.path.exists(conversation_file):
        return False

    try:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "role": "user",
            "content": user_input,
            "event_type": "feedback",
            "sentiment": intent.get("sentiment", "neutral"),
            "is_confirmation": intent.get("is_confirmation", False)
        }

        with open(conversation_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

        return True
    except Exception as e:
        sys.stderr.write(u"[WARN] 记录用户反馈到会话历史失败: {}\n".format(e))
        return False

def update_tracking_state(intent: dict, user_input: str, cwd: str, logger):
    """
    更新迭代追踪状态 (v20.3: 使用原子更新防止并行冲突)

    策略:
    1. 更新 workflow-state.json (会话级) - 使用原子更新
    2. 同步到 .task-meta.json (持久化) - 使用原子更新
    3. v20.2.7: 记录用户反馈到 .conversation.jsonl
    """

    workflow_state_path = os.path.join(cwd, '.claude', 'workflow-state.json')

    # v20.3: 使用原子更新函数代替直接读写
    def update_workflow_state_data(state):
        """更新函数：添加追踪数据到workflow_state"""
        if not state:
            logger.info(u"workflow-state.json为空，跳过追踪")
            return state

        # === 初始化任务类型 ===
        if "task_type" not in state:
            state["task_type"] = intent["task_type"]

        # === v20.3: 用户确认检测 ===
        if intent.get("is_confirmation", False):
            # 更新 step3_execute.user_confirmed 标志
            if "steps" in state and "step3_execute" in state["steps"]:
                state["steps"]["step3_execute"]["user_confirmed"] = True
                state["steps"]["step3_execute"]["confirmed_at"] = datetime.now().isoformat()
                logger.info(u"用户确认修复完成，已设置 user_confirmed=True")

        # === v20.2.7: 收尾意愿检测（新增）===
        if intent.get("is_cleanup_response", False):
            cleanup_action = intent.get("cleanup_intent")  # "proceed" or "skip"

            state['cleanup_intent_received'] = True
            state['cleanup_intent_action'] = cleanup_action
            state['cleanup_intent_at'] = datetime.now().isoformat()

            logger.info(u"收到用户收尾意愿", {"action": cleanup_action})

            # 重置"已询问"标记（允许Stop Hook放行）
            state['asked_cleanup_intent'] = False

            if cleanup_action == "proceed":
                # 立即推进到 step4_cleanup
                if "steps" in state and "step4_cleanup" in state["steps"]:
                    # 标记 step3 完成
                    if "step3_execute" in state["steps"]:
                        state["steps"]["step3_execute"]["status"] = "completed"
                        state["steps"]["step3_execute"]["completed_at"] = datetime.now().isoformat()

                    # 推进到 step4
                    state['current_step'] = 'step4_cleanup'
                    state["steps"]["step4_cleanup"]["status"] = "in_progress"
                    state["steps"]["step4_cleanup"]["started_at"] = datetime.now().isoformat()
                    logger.info(u"收尾意愿：进入step4_cleanup")

            elif cleanup_action == "skip":
                # 标记 step4 为 completed（允许结束）
                if "steps" in state and "step4_cleanup" in state["steps"]:
                    state["steps"]["step4_cleanup"]["status"] = "completed"
                    state["steps"]["step4_cleanup"]["skipped"] = True
                    state["steps"]["step4_cleanup"]["completed_at"] = datetime.now().isoformat()
                    logger.info(u"收尾意愿：跳过step4，标记为completed")

        # === Bug修复追踪 ===
        if intent["task_type"] == "bug_fix" or state.get("task_type") == "bug_fix":
            if "bug_fix_tracking" not in state:
                state["bug_fix_tracking"] = {
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
                tracking = state["bug_fix_tracking"]
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
        elif intent["task_type"] == "feature_implementation" or state.get("task_type") == "feature_implementation":
            if "feature_tracking" not in state:
                state["feature_tracking"] = {
                    "enabled": True,
                    "feature_description": user_input[:200],
                    "iterations": [],
                    "requirement_changes": [],
                    "expert_triggered": False
                }

            if intent["is_feedback"]:
                tracking = state["feature_tracking"]
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

        return state

    # 执行原子更新 workflow-state.json
    success = atomic_update_json(workflow_state_path, update_workflow_state_data)
    if not success:
        logger.error(u"workflow-state.json原子更新失败")
        return

    # 重新加载更新后的状态（用于后续同步）
    workflow_state = load_json(workflow_state_path)
    if not workflow_state:
        return

    # === v20.2.6: 完整同步到 .task-meta.json ===
    # 修复: 原来只同步tracking_state，导致steps.step3_execute.user_confirmed未同步
    meta_path = get_active_task_meta_path(cwd)
    if meta_path:
        def update_task_meta_data(task_meta):
            """更新函数：完整同步workflow_state到task_meta (v20.2.6修复)"""
            if not task_meta:
                return task_meta

            # v20.2.6核心修复: 完整同步workflow_state（包括steps）
            if "workflow_state" not in task_meta:
                task_meta["workflow_state"] = {}

            # 同步所有关键字段
            task_meta["workflow_state"]["steps"] = workflow_state.get("steps", {})
            task_meta["workflow_state"]["current_step"] = workflow_state.get("current_step", "unknown")
            task_meta["workflow_state"]["bug_fix_tracking"] = workflow_state.get("bug_fix_tracking")
            task_meta["workflow_state"]["feature_tracking"] = workflow_state.get("feature_tracking")

            # 保留tracking_state（向后兼容）
            if "tracking_state" not in task_meta:
                task_meta["tracking_state"] = {}
            task_meta["tracking_state"]["bug_fix_tracking"] = workflow_state.get("bug_fix_tracking")
            task_meta["tracking_state"]["feature_tracking"] = workflow_state.get("feature_tracking")

            task_meta["task_type"] = workflow_state.get("task_type", "general")
            task_meta["updated_at"] = datetime.now().isoformat()

            return task_meta

        # 执行原子更新 task-meta.json (v20.2.6: 增加重试机制)
        max_retries = 3
        success = False
        for retry in range(max_retries):
            success = atomic_update_json(meta_path, update_task_meta_data)
            if success:
                logger.info(u"✅ 已同步到task-meta.json", {
                    "retry_count": retry,
                    "meta_path": meta_path
                })
                break
            else:
                if retry < max_retries - 1:
                    import time
                    time.sleep(0.1 * (retry + 1))  # 指数退避
                    logger.warning(u"task-meta.json同步失败，重试中...", {"retry": retry + 1})

        if not success:
            logger.error(u"❌ task-meta.json原子更新失败（已重试{}次）".format(max_retries))


# ==================== 主函数 ====================

def main():
    logger = HookLogger("iteration-tracker-hook")
    logger.start()

    try:
        # 读取stdin输入
        data = json.load(sys.stdin)
        user_input = data.get('prompt', '')
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

            # v20.2.7: 如果是反馈，记录到会话历史
            if intent["is_feedback"]:
                # 获取任务目录
                meta_path = get_active_task_meta_path(cwd)
                if meta_path:
                    task_dir = os.path.dirname(meta_path)
                    if record_user_feedback_to_conversation(task_dir, user_input, intent):
                        logger.info(u"已记录用户反馈到会话历史")

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
