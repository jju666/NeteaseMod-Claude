#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Hook 2: Stop - 任务完成验证与重试强制
阻止未完成的任务结束，强制继续分析

触发时机: 会话结束前
工作机制:
1. 查找当前活跃任务
2. 检查用户是否确认修复
3. 未确认时阻止会话结束并更新失败计数器
4. 失败≥2次时触发专家审核提醒

退出码:
- 0: 成功，允许结束
- 2: 阻止结束
- 1: 非阻塞错误
"""

import sys
import json
import os
from datetime import datetime
import io

# 修复Windows GBK编码问题：强制使用UTF-8输出
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 导入VSCode通知模块
try:
    from vscode_notify import notify_info, notify_warning, notify_error
except ImportError:
    # 降级方案：纯文本输出
    def notify_info(msg, detail=""): sys.stderr.write(u"ℹ️ {} {}\n".format(msg, detail))
    def notify_warning(msg, detail=""): sys.stderr.write(u"⚠️ {} {}\n".format(msg, detail))
    def notify_error(msg, detail=""): sys.stderr.write(u"❌ {} {}\n".format(msg, detail))

def find_active_task(cwd):
    """查找当前活跃任务"""
    tasks_dir = os.path.join(cwd, 'tasks')
    if not os.path.exists(tasks_dir):
        return None
    
    # 查找所有task目录（按时间倒序）
    task_dirs = []
    for name in os.listdir(tasks_dir):
        if name.startswith('task-'):
            task_path = os.path.join(tasks_dir, name)
            if os.path.isdir(task_path):
                task_dirs.append(task_path)
    
    task_dirs.sort(reverse=True)
    
    # 查找第一个进行中的任务
    for task_dir in task_dirs:
        meta_file = os.path.join(task_dir, '.task-meta.json')
        if os.path.exists(meta_file):
            with open(meta_file, 'r', encoding='utf-8') as f:
                meta = json.load(f)
                if meta.get('status') == 'in_progress':
                    return task_dir, meta
    
    return None

def check_user_confirmed(task_dir):
    """检查用户是否确认修复"""
    context_file = os.path.join(task_dir, 'context.md')
    if not os.path.exists(context_file):
        return False
    
    with open(context_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检测用户确认关键词
    keywords = [u'已修复', u'修复成功', u'问题解决', 'fixed', 'resolved', u'用户确认: 是']
    
    for keyword in keywords:
        if keyword in content:
            return True
    
    return False

def main():
    try:
        # 读取stdin输入
        data = json.load(sys.stdin)
        
        stop_reason = data.get('stopReason', '')
        cwd = os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd())
        
        # 查找活跃任务
        task_info = find_active_task(cwd)
        
        if task_info is None:
            # 没有活跃任务，正常结束
            sys.exit(0)
        
        task_dir, meta = task_info
        task_id = meta['task_id']
        
        # 检查用户是否确认修复
        user_confirmed = check_user_confirmed(task_dir)
        
        if not user_confirmed:
            # 用户未确认修复，阻止结束
            
            # 更新失败计数器
            failure_count = meta.get('failure_count', 0) + 1
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
            
            # 保存元数据
            with open(os.path.join(task_dir, '.task-meta.json'), 'w', encoding='utf-8') as f:
                json.dump(meta, f, indent=2, ensure_ascii=False)
            
            # 📢 通知：任务失败
            try:
                notify_warning(
                    u"任务尝试失败",
                    u"第{}次失败".format(failure_count)
                )
            except:
                pass

            # 检查是否需要触发专家审核
            if failure_count >= 2 and not meta.get('expert_review_triggered', False):
                # 触发专家审核
                meta['expert_review_triggered'] = True
                with open(os.path.join(task_dir, '.task-meta.json'), 'w', encoding='utf-8') as f:
                    json.dump(meta, f, indent=2, ensure_ascii=False)

                # 📢 通知：触发专家审核
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

由于已失败2次，现在触发**专家审核流程**！

**你必须**:
1. 立即调用 /mc-review 命令审查当前方案
2. 根据审核报告修改方案
3. 继续实施直到用户确认"已修复"

**任务上下文**: tasks/{}/context.md

⚠️ 禁止结束会话！必须继续分析！
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

1. 你必须重新分析问题（查阅 tasks/{}/context.md）
2. 检查是否遗漏了关键文档或CRITICAL规范
3. 重新设计方案并继续实施
4. 在 context.md 中记录本次失败原因和新的分析

⚠️ 禁止结束会话！必须继续分析！
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(failure_count, task_id, failure_count, task_id)
            
            # 输出控制JSON（阻止结束）
            output = {
                "continue": False,
                "stopReason": "task_incomplete",
                "injectedContext": message
            }
            
            print(json.dumps(output, ensure_ascii=False))

            # exit(2) = 阻止操作
            sys.exit(2)
        
        else:
            # 用户已确认修复，允许归档任务
            meta['status'] = 'completed'
            meta['archived_at'] = datetime.now().isoformat()
            meta['user_confirmed_fixed'] = True

            # 📢 通知：任务完成
            try:
                task_desc = meta.get('task_description', '')[:40]
                notify_info(
                    u"任务完成",
                    u"{}".format(task_desc)
                )
            except:
                pass

            with open(os.path.join(task_dir, '.task-meta.json'), 'w', encoding='utf-8') as f:
                json.dump(meta, f, indent=2, ensure_ascii=False)

            sys.exit(0)
    
    except Exception as e:
        sys.stderr.write("[ERROR] Hook执行失败: {}\n".format(e))
        sys.exit(1)  # 非阻塞错误

if __name__ == '__main__':
    main()
