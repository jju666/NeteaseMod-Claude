#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Track Document Reading Hook - 追踪文档阅读进度 (v20.0)
触发时机: Read工具调用后（PostToolUse事件）
职责: 统计.md文件阅读数量，更新任务状态

v20.0 变更:
- 同时更新 .task-meta.json (新格式) 和 workflow-state.json (兼容旧格式)
- 支持任务目录内的 .task-meta.json 状态文件
"""

import os
import sys
import json
from datetime import datetime
import io

# 修复Windows GBK编码问题：强制使用UTF-8输出
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 导入通知模块
try:
    from vscode_notify import notify_info, notify_warning
except ImportError:
    def notify_info(msg, detail=""): pass
    def notify_warning(msg, detail=""): pass

def find_task_meta_file(project_path):
    """
    查找最新任务的 .task-meta.json 文件

    Args:
        project_path: 项目根目录

    Returns:
        str: .task-meta.json 文件路径,如果未找到返回None
    """
    from pathlib import Path

    tasks_dir = Path(project_path) / "tasks"
    if not tasks_dir.exists():
        return None

    # 查找所有任务目录
    task_dirs = [
        d for d in tasks_dir.iterdir()
        if d.is_dir() and (d.name.startswith("task-") or d.name.startswith(u"任务-"))
    ]

    if not task_dirs:
        return None

    # 返回最新修改的任务目录的 .task-meta.json
    latest_task = max(task_dirs, key=lambda d: d.stat().st_mtime)
    meta_file = latest_task / ".task-meta.json"

    if meta_file.exists():
        return str(meta_file)

    return None

def main():
    """主函数：追踪文档阅读"""
    try:
        # 1. 读取Hook输入（stdin传入的JSON）
        hook_input = json.load(sys.stdin)

        tool_name = hook_input.get('toolName', '')
        tool_params = hook_input.get('parameters', {})
        project_path = hook_input.get('cwd', os.getcwd())

        # 2. 只追踪Read工具
        if tool_name != 'Read':
            sys.exit(0)

        # 3. 获取读取的文件路径
        file_path = tool_params.get('file_path', '')
        if not file_path:
            sys.exit(0)

        # 4. 只追踪.md文件
        if not file_path.endswith('.md'):
            sys.exit(0)

        # 5. 排除不应计入的文档（如README、索引等）
        excluded_patterns = [
            'README.md',
            '索引.md',
            '项目状态.md',
            '文档待补充清单.md',
            'CHANGELOG.md'
        ]
        if any(pattern in file_path for pattern in excluded_patterns):
            sys.exit(0)

        # 6. 查找任务目录和 .task-meta.json (v20.0)
        task_meta_file = find_task_meta_file(project_path)
        task_meta = None
        if task_meta_file:
            try:
                with open(task_meta_file, 'r', encoding='utf-8') as f:
                    task_meta = json.load(f)
            except:
                pass

        # 7. 读取工作流状态 (兼容v19.x)
        state_file = os.path.join(project_path, '.claude', 'workflow-state.json')
        state = None
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
            except:
                pass

        # 如果两个状态文件都不存在，退出
        if not task_meta and not state:
            sys.exit(0)

        # 8. 更新 .task-meta.json (v20.0新格式)
        if task_meta:
            docs_read = task_meta.get('metrics', {}).get('docs_read', [])
            if file_path not in docs_read:
                docs_read.append(file_path)
                task_meta['metrics']['docs_read'] = docs_read
                task_meta['metrics']['docs_read_count'] = len(docs_read)
                task_meta['updated_at'] = datetime.now().isoformat()

                # 更新步骤2的docs_read列表
                if 'step2_docs' in task_meta['workflow_state']['steps']:
                    task_meta['workflow_state']['steps']['step2_docs']['docs_read'] = docs_read

                # 保存 .task-meta.json
                with open(task_meta_file, 'w', encoding='utf-8') as f:
                    json.dump(task_meta, f, indent=2, ensure_ascii=False)

                doc_count = len(docs_read)
                sys.stderr.write(u"[INFO] 文档追踪: {} (总计: {})\n".format(file_path, doc_count))

        # 9. 同时更新 workflow-state.json (兼容v19.x)
        if state:
            docs_read = state.get('docs_read', [])
            if file_path not in docs_read:
                docs_read.append(file_path)
                state['docs_read'] = docs_read

            doc_count = len(docs_read)
            state['steps_completed']['step2_doc_count'] = doc_count

            # 如果文档数≥3，自动标记步骤2完成
            if doc_count >= 3:
                if not state['steps_completed']['step2_doc_reading']:
                    state['steps_completed']['step2_doc_reading'] = True
                    state['current_step'] = 3

                    # 📢 通知：步骤2完成，进入步骤3
                    try:
                        notify_info(
                            u"步骤2完成：查阅文档",
                            u"已阅读{}个文档 → 进入步骤3".format(doc_count)
                        )
                    except:
                        pass

            state['last_updated'] = datetime.now().isoformat()

            # 保存 workflow-state.json
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)

        # 12. 允许工具继续执行
        sys.exit(0)

    except Exception as e:
        # 异常情况下允许继续
        print(f"⚠️ Hook执行异常: {str(e)}", file=sys.stderr)
        sys.exit(0)

if __name__ == '__main__':
    main()
