#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Hook 3: SubagentStop - 专家审核结果验证
评分<8分时阻止审核结束，要求修改方案

触发时机: 子代理（如 /mc-review）结束时
工作机制:
1. 拦截 /mc-review 审核结果
2. 提取审核评分（正则匹配）
3. 评分<8分时阻止审核结束
4. 更新任务元数据

退出码:
- 0: 成功，允许结束
- 2: 阻止结束
- 1: 非阻塞错误
"""

import sys
import json
import os
import re
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

def extract_review_score(subagent_output):
    """从审核输出中提取评分"""
    # 匹配 "**总分**: X/10" 或 "总分: X/10" 格式
    patterns = [
        r'\*\*总分\*\*[:\s]*(\d+(?:\.\d+)?)\s*/\s*10',
        r'总分[:\s]*(\d+(?:\.\d+)?)\s*/\s*10',
        r'Score[:\s]*(\d+(?:\.\d+)?)\s*/\s*10'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, subagent_output, re.IGNORECASE)
        if match:
            return float(match.group(1))
    
    return None

def main():
    try:
        # 读取stdin输入
        data = json.load(sys.stdin)
        
        subagent_output = data.get('subagentOutput', '')
        subagent_task = data.get('subagentTask', '')
        cwd = os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd())
        
        # 只拦截 /mc-review 命令
        if '/mc-review' not in subagent_task:
            sys.exit(0)
        
        # 查找活跃任务
        task_info = find_active_task(cwd)
        
        if task_info is None:
            sys.exit(0)
        
        task_dir, meta = task_info
        task_id = meta['task_id']
        
        # 提取审核评分
        score = extract_review_score(subagent_output)
        
        if score is None:
            # 无法提取评分，放行（但记录警告）
            sys.stderr.write(u"⚠️ 无法提取审核评分，放行\n")
            sys.exit(0)
        
        # 更新元数据
        meta['expert_review_score'] = score
        with open(os.path.join(task_dir, '.task-meta.json'), 'w', encoding='utf-8') as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
        
        # 检查评分
        if score < 8.0:
            # 评分过低，阻止审核结束
            message = u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ 专家审核评分过低: {}/10
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**任务ID**: {}
**审核评分**: {}/10

⚠️ **系统强制要求**:

评分<8分，方案质量不合格！

**你必须**:
1. 仔细阅读审核报告中的"严重问题"和"优化建议"
2. 根据建议修改方案
3. 重新执行 /mc-review 审查修改后的方案
4. 直到评分≥8分才能继续实施

⚠️ 禁止跳过审核！必须达到质量标准！
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(score, task_id, score)
            
            # SubagentStop Hook 官方格式（v20.2.17修复）
            # 注意：SubagentStop Hook 不支持 additionalContext/injectedContext
            output = {
                "decision": "block",
                "reason": f"专家审核评分过低（{score}/10），需要≥8分才能继续",
                "continue": False,
                "stopReason": message  # 用户可见的完整提示
            }

            print(json.dumps(output, ensure_ascii=False))

            # 弹窗通知评分不合格
            notify_error(
                "❌ 专家审核未通过",
                "评分: {}/10 (需要≥8分) | 任务ID: {}".format(score, task_id)
            )

            sys.exit(2)

        else:
            # 评分合格，放行
            # 弹窗通知审核通过
            notify_info(
                "✅ 专家审核通过",
                "评分: {}/10 | 任务ID: {}".format(score, task_id)
            )
            sys.exit(0)
    
    except Exception as e:
        sys.stderr.write("[ERROR] Hook执行失败: {}\n".format(e))
        sys.exit(1)  # 非阻塞错误

if __name__ == '__main__':
    main()
