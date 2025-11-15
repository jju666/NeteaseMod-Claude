#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Conversation Recorder - 会话历史记录器 (v20.2.7)

触发时机: PostToolUse (所有工具)
职责:
1. 记录每次工具调用到 .conversation.jsonl
2. 记录工具输入、输出摘要
3. 支持后续从完整历史生成context.md和solution.md

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
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='replace')
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def load_json(file_path):
    """加载JSON文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None

def summarize_tool_result(result, max_length=200):
    """摘要工具输出结果（避免会话文件过大）"""
    try:
        if isinstance(result, dict):
            # 提取关键信息
            if 'error' in result:
                return u"错误: {}".format(str(result['error'])[:max_length])
            elif 'output' in result:
                return str(result['output'])[:max_length]
            else:
                return json.dumps(result, ensure_ascii=False)[:max_length]
        else:
            return str(result)[:max_length]
    except:
        return u"[无法摘要]"

def record_conversation_entry(task_dir, tool_name, tool_input, tool_result):
    """记录会话条目到 .conversation.jsonl"""
    conversation_file = os.path.join(task_dir, '.conversation.jsonl')

    # 如果文件不存在，跳过（说明不是活跃任务或未初始化）
    if not os.path.exists(conversation_file):
        return False

    try:
        # 提取关键输入参数
        input_summary = {}
        if isinstance(tool_input, dict):
            # 只记录关键字段，避免过大
            key_fields = ['file_path', 'command', 'pattern', 'url', 'description']
            for field in key_fields:
                if field in tool_input:
                    value = tool_input[field]
                    # 限制长度
                    if isinstance(value, str) and len(value) > 100:
                        input_summary[field] = value[:100] + "..."
                    else:
                        input_summary[field] = value

        # 构建条目
        entry = {
            "timestamp": datetime.now().isoformat(),
            "role": "tool",
            "tool_name": tool_name,
            "tool_input": input_summary,
            "tool_result_summary": summarize_tool_result(tool_result)
        }

        # 追加到文件
        with open(conversation_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

        return True
    except Exception as e:
        sys.stderr.write(u"[WARN] 记录会话条目失败: {}\n".format(e))
        return False

def main():
    try:
        # 读取stdin输入
        data = json.load(sys.stdin)
        tool_name = data.get('tool_name', '')
        tool_input = data.get('tool_input', {})
        tool_result = data.get('result', {})

        cwd = os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd())

        # 快速检查: 是否有活跃任务
        active_flag_path = os.path.join(cwd, '.claude', '.task-active.json')
        if not os.path.exists(active_flag_path):
            # 无活跃任务，放行
            output = {"continue": True}
            print(json.dumps(output, ensure_ascii=False))
            sys.exit(0)

        # 加载活跃任务
        active_flag = load_json(active_flag_path)
        if not active_flag:
            output = {"continue": True}
            print(json.dumps(output, ensure_ascii=False))
            sys.exit(0)

        task_dir = active_flag.get("task_dir")
        if not task_dir:
            output = {"continue": True}
            print(json.dumps(output, ensure_ascii=False))
            sys.exit(0)

        # 记录会话条目
        if record_conversation_entry(task_dir, tool_name, tool_input, tool_result):
            sys.stderr.write(u"[DEBUG] 已记录工具调用: {} @ {}\n".format(
                tool_name,
                datetime.now().strftime('%H:%M:%S')
            ))

        # 放行
        output = {"continue": True}
        print(json.dumps(output, ensure_ascii=False))
        sys.exit(0)

    except Exception as e:
        sys.stderr.write(u"[ERROR] conversation-recorder执行失败: {}\n".format(e))
        import traceback
        traceback.print_exc(file=sys.stderr)

        # 错误不应阻塞主流程
        output = {"continue": True}
        print(json.dumps(output, ensure_ascii=False))
        sys.exit(0)

if __name__ == '__main__':
    main()
