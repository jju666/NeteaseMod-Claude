#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stop Hook - 任务完成验证与重试强制 (v21.0)
阻止未完成的任务结束,强制继续分析

触发时机: 会话结束前
工作机制:
1. 查找当前活跃任务
2. 检查用户是否确认修复
3. 未确认时阻止会话结束并更新失败计数器
4. 失败≥2次时触发专家审核提醒

核心变更(v21.0):
- 使用 TaskMetaManager 替代文件查找逻辑
- 从 task-meta.json 读取 steps 和 user_confirmed
- 删除 workflow-state.json 检查

退出码:
- 0: 成功,允许结束
- 2: 阻止结束
- 1: 非阻塞错误
"""

import sys
import json
import os
from datetime import datetime
import io

# 修复Windows GBK编码问题:强制使用UTF-8输出
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 导入 TaskMetaManager
HOOK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HOOK_DIR)

try:
    from core.task_meta_manager import TaskMetaManager
except ImportError:
    sys.stderr.write("[ERROR] TaskMetaManager 模块缺失\n")
    sys.exit(0)

# 导入VSCode通知模块
try:
    from utils.notify import notify_info, notify_warning, notify_error
except ImportError:
    # 降级方案:纯文本输出
    def notify_info(msg, detail=""): sys.stderr.write(u"ℹ️ {} {}\n".format(msg, detail))
    def notify_warning(msg, detail=""): sys.stderr.write(u"⚠️ {} {}\n".format(msg, detail))
    def notify_error(msg, detail=""): sys.stderr.write(u"❌ {} {}\n".format(msg, detail))


def check_user_confirmation(task_id, cwd):
    """
    检查用户是否确认任务完成(v21.0版本)

    Returns:
        bool: 用户是否确认
    """
    mgr = TaskMetaManager(cwd)
    task_meta = mgr.load_task_meta(task_id)

    if not task_meta:
        return False

    # 检查步骤状态中的user_confirmed字段
    steps = task_meta.get('steps', {})
    step3 = steps.get('step3_execute', {})

    return step3.get('user_confirmed', False)


def main():
    try:
        # 读取stdin输入
        data = json.load(sys.stdin)

        stop_reason = data.get('stopReason', '')
        cwd = os.getcwd()

        # v21.0: 使用 TaskMetaManager 查找活跃任务
        mgr = TaskMetaManager(cwd)
        task_id = mgr.get_active_task_id()

        if not task_id:
            # 没有活跃任务,正常结束
            sys.exit(0)

        # 加载任务元数据
        task_meta = mgr.load_task_meta(task_id)
        if not task_meta:
            sys.stderr.write(f"[ERROR] 加载任务元数据失败: {task_id}\n")
            sys.exit(0)

        # 检查用户是否确认修复
        user_confirmed = check_user_confirmation(task_id, cwd)

        if not user_confirmed:
            # 用户未确认修复,阻止结束

            # 更新失败计数器
            failure_count = task_meta.get('failure_count', 0) + 1

            # 原子更新任务元数据
            def update_func(meta):
                meta['failure_count'] = failure_count

                # 记录失败历史
                failure_record = {
                    "attempt": failure_count,
                    "timestamp": datetime.now().isoformat(),
                    "stop_reason": stop_reason
                }
                if 'failure_history' not in meta:
                    meta['failure_history'] = []
                meta['failure_history'].append(failure_record)

                return meta

            mgr.atomic_update(task_id, update_func)

            # 📢 通知:任务失败
            try:
                notify_warning(
                    u"任务尝试失败",
                    u"第{}次失败".format(failure_count)
                )
            except:
                pass

            # 检查是否需要触发专家审核
            if failure_count >= 2 and not task_meta.get('expert_review_triggered', False):
                # 标记专家审核触发
                def mark_expert(meta):
                    meta['expert_review_triggered'] = True
                    return meta

                mgr.atomic_update(task_id, mark_expert)

                # 📢 通知:触发专家审核
                try:
                    notify_error(
                        u"触发专家审核",
                        u"失败{}次 → 需要/mc-review".format(failure_count)
                    )
                except:
                    pass

                message = u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ 任务未完成 - 已失败 {} 次
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**任务ID**: {}
**失败次数**: {}

⚠️ **系统强制要求**:

由于已失败2次,现在触发**专家审核流程**!

**你必须**:
1. 立即调用 /mc-review 命令审查当前方案
2. 根据审核报告修改方案
3. 继续实施直到用户确认"已修复"

**任务目录**: tasks/{}

⚠️ 禁止结束会话!必须继续分析!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(failure_count, task_id, failure_count, task_id)
            else:
                message = u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ 任务未完成 - 第 {} 次尝试失败
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**任务ID**: {}
**失败次数**: {}

⚠️ **系统强制要求**:

1. 你必须重新分析问题(查看 tasks/{} 目录)
2. 检查是否遗漏了关键文档或CRITICAL规范
3. 重新设计方案并继续实施
4. 记录本次失败原因和新的分析

⚠️ 禁止结束会话!必须继续分析!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(failure_count, task_id, failure_count, task_id)

            # Stop Hook 官方格式
            output = {
                "decision": "block",
                "reason": f"任务失败{failure_count}次,必须重新分析问题",
                "continue": False,
                "stopReason": message
            }

            print(json.dumps(output, ensure_ascii=False))

            # exit(2) = 阻止操作
            sys.exit(2)

        else:
            # 用户已确认修复,允许归档任务
            def mark_completed(meta):
                meta['status'] = 'completed'
                meta['archived_at'] = datetime.now().isoformat()
                meta['user_confirmed_fixed'] = True
                return meta

            mgr.atomic_update(task_id, mark_completed)

            # 📢 通知:任务完成
            try:
                task_desc = task_meta.get('task_description', '')[:40]
                notify_info(
                    u"任务完成",
                    u"{}".format(task_desc)
                )
            except:
                pass

            sys.exit(0)

    except Exception as e:
        sys.stderr.write("[ERROR] Hook执行失败: {}\n".format(e))
        sys.exit(1)  # 非阻塞错误


if __name__ == '__main__':
    main()
