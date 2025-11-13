#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generate Docs from Conversation - 从会话历史生成文档 (v20.2.7)

职责:
1. 读取任务目录下的 .conversation.jsonl
2. 分析会话历史，提取关键信息
3. 生成 context.md（问题上下文、分析过程）
4. 生成 solution.md（解决方案、代码修改、技术决策）

使用场景:
- 收尾阶段自动生成归档文档
- 跨会话补充归档（从历史数据重建）
"""

import sys
import json
import os
from datetime import datetime
import io

# Windows编码修复
if sys.platform == 'win32':
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='replace')
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def load_conversation(task_dir):
    """加载会话历史"""
    conversation_file = os.path.join(task_dir, '.conversation.jsonl')

    if not os.path.exists(conversation_file):
        return None

    conversation = []
    try:
        with open(conversation_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    conversation.append(json.loads(line))
        return conversation
    except Exception as e:
        sys.stderr.write(u"[ERROR] 读取会话历史失败: {}\n".format(e))
        return None

def extract_problem_description(conversation):
    """提取问题描述（从初始用户输入）"""
    for entry in conversation:
        if entry.get('role') == 'user' and entry.get('event_type') == 'task_init':
            return entry.get('content', '').replace('/mc ', '').strip()
    return u"未记录"

def extract_analysis_process(conversation):
    """提取分析过程（从Read工具调用）"""
    analysis = []

    for entry in conversation:
        if entry.get('role') == 'tool' and entry.get('tool_name') == 'Read':
            tool_input = entry.get('tool_input', {})
            file_path = tool_input.get('file_path', '')

            # 只记录文档阅读（.md文件）
            if file_path.endswith('.md'):
                analysis.append({
                    'timestamp': entry.get('timestamp'),
                    'file': file_path,
                    'purpose': u"查阅文档"
                })

    return analysis

def extract_code_changes(conversation):
    """提取代码修改（从Edit/Write工具调用）"""
    changes = []

    for entry in conversation:
        tool_name = entry.get('tool_name')
        if entry.get('role') == 'tool' and tool_name in ['Edit', 'Write']:
            tool_input = entry.get('tool_input', {})
            file_path = tool_input.get('file_path', '')

            if file_path:
                changes.append({
                    'timestamp': entry.get('timestamp'),
                    'operation': tool_name,
                    'file': file_path,
                    'result_summary': entry.get('tool_result_summary', '')
                })

    return changes

def extract_user_feedback(conversation):
    """提取用户反馈（从user_feedback事件）"""
    feedbacks = []

    for entry in conversation:
        if entry.get('role') == 'user' and entry.get('event_type') == 'feedback':
            feedbacks.append({
                'timestamp': entry.get('timestamp'),
                'content': entry.get('content', ''),
                'sentiment': entry.get('sentiment', 'neutral')
            })

    return feedbacks

def format_timestamp(iso_timestamp):
    """格式化时间戳"""
    try:
        dt = datetime.fromisoformat(iso_timestamp)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return iso_timestamp

def generate_context_md(conversation, task_meta):
    """生成 context.md"""

    problem = extract_problem_description(conversation)
    analysis = extract_analysis_process(conversation)

    content = u"""# 任务上下文

## 问题描述

{}

## 分析过程

""".format(problem)

    if analysis:
        for idx, item in enumerate(analysis, 1):
            content += u"{}. **{}** - {}\n".format(
                idx,
                os.path.basename(item['file']),
                format_timestamp(item['timestamp'])
            )
            content += u"   - 路径: `{}`\n".format(item['file'])
            content += u"   - 目的: {}\n\n".format(item['purpose'])
    else:
        content += u"_（无文档阅读记录）_\n\n"

    # 添加任务元数据
    content += u"""
## 任务元数据

- **任务ID**: {}
- **创建时间**: {}
- **任务类型**: {}
- **文档阅读**: {}个
- **代码修改**: {}次

""".format(
        task_meta.get('task_id', 'Unknown'),
        format_timestamp(task_meta.get('created_at', '')),
        task_meta.get('task_type', 'general'),
        len(analysis),
        task_meta.get('metrics', {}).get('code_changes_count', 0)
    )

    return content

def generate_solution_md(conversation, task_meta):
    """生成 solution.md"""

    changes = extract_code_changes(conversation)
    feedbacks = extract_user_feedback(conversation)

    content = u"""# 解决方案

## 代码修改

"""

    if changes:
        # 按文件分组
        files_changed = {}
        for change in changes:
            file_path = change['file']
            if file_path not in files_changed:
                files_changed[file_path] = []
            files_changed[file_path].append(change)

        for file_path, file_changes in files_changed.items():
            content += u"### {}\n\n".format(os.path.basename(file_path))
            content += u"**路径**: `{}`\n\n".format(file_path)
            content += u"**修改次数**: {}\n\n".format(len(file_changes))

            content += u"**修改历史**:\n\n"
            for idx, change in enumerate(file_changes, 1):
                content += u"{}. **{}** - {}\n".format(
                    idx,
                    change['operation'],
                    format_timestamp(change['timestamp'])
                )
                if change.get('result_summary'):
                    content += u"   - 结果: {}\n".format(change['result_summary'][:100])
            content += u"\n"
    else:
        content += u"_（无代码修改记录）_\n\n"

    # 测试验证
    content += u"""
## 测试验证

"""

    if feedbacks:
        content += u"### 用户反馈\n\n"
        for idx, feedback in enumerate(feedbacks, 1):
            sentiment_emoji = {
                'positive': u'✅',
                'negative': u'❌',
                'neutral': u'ℹ️'
            }.get(feedback['sentiment'], u'ℹ️')

            content += u"{}. {} **{}**\n".format(
                idx,
                sentiment_emoji,
                format_timestamp(feedback['timestamp'])
            )
            content += u"   - {}\n\n".format(feedback['content'])
    else:
        content += u"_（无用户反馈记录）_\n\n"

    # 技术决策（从task-meta.json提取）
    content += u"""
## 技术决策

"""

    technical_decisions = task_meta.get('technical_decisions', [])
    if technical_decisions:
        for idx, decision in enumerate(technical_decisions, 1):
            content += u"{}. **{}**\n".format(idx, decision.get('decision', '未知'))
            content += u"   - 理由: {}\n".format(decision.get('reason', ''))
            if 'reference' in decision:
                content += u"   - 参考: {}\n".format(decision['reference'])
            content += u"\n"
    else:
        content += u"_（无技术决策记录）_\n\n"

    return content

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print(u"用法: python generate-docs-from-conversation.py <task_dir>")
        sys.exit(1)

    task_dir = sys.argv[1]

    if not os.path.exists(task_dir):
        sys.stderr.write(u"[ERROR] 任务目录不存在: {}\n".format(task_dir))
        sys.exit(1)

    # 加载会话历史
    conversation = load_conversation(task_dir)
    if not conversation:
        sys.stderr.write(u"[ERROR] 无法加载会话历史或会话为空\n")
        sys.exit(1)

    # 加载任务元数据
    meta_file = os.path.join(task_dir, '.task-meta.json')
    task_meta = {}
    if os.path.exists(meta_file):
        try:
            with open(meta_file, 'r', encoding='utf-8') as f:
                task_meta = json.load(f)
        except Exception as e:
            sys.stderr.write(u"[WARN] 读取任务元数据失败: {}\n".format(e))

    # 生成文档
    context_md = generate_context_md(conversation, task_meta)
    solution_md = generate_solution_md(conversation, task_meta)

    # 写入文件
    context_file = os.path.join(task_dir, 'context.md')
    solution_file = os.path.join(task_dir, 'solution.md')

    try:
        with open(context_file, 'w', encoding='utf-8') as f:
            f.write(context_md)
        print(u"✅ 已生成: {}".format(context_file))
    except Exception as e:
        sys.stderr.write(u"[ERROR] 写入context.md失败: {}\n".format(e))

    try:
        with open(solution_file, 'w', encoding='utf-8') as f:
            f.write(solution_md)
        print(u"✅ 已生成: {}".format(solution_file))
    except Exception as e:
        sys.stderr.write(u"[ERROR] 写入solution.md失败: {}\n".format(e))

    print(u"\n文档生成完成！")
    print(u"- context.md: {}行".format(context_md.count('\n')))
    print(u"- solution.md: {}行".format(solution_md.count('\n')))
    print(u"- 会话条目: {}条".format(len(conversation)))

if __name__ == '__main__':
    main()
