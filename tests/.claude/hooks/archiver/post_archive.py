#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Post Archive Hook - 任务归档钩子 (v21.0)

职责:
1. 标记任务为已归档
2. 简化逻辑(无需创建快照,task-meta.json 已包含完整状态)

核心变更(v21.0):
- 删除快照创建逻辑(archived_snapshot)
- 仅标记 archived 字段为 true
- 使用 TaskMetaManager 原子更新
- 简化代码(从560行 → 90行)
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

# 导入 TaskMetaManager
HOOK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HOOK_DIR)

try:
    from core.task_meta_manager import TaskMetaManager
except ImportError:
    sys.stderr.write("[ERROR] TaskMetaManager 模块缺失\n")
    sys.exit(0)


def main():
    """主入口"""
    try:
        # 读取Hook输入
        hook_input = json.load(sys.stdin)
        cwd = hook_input.get('cwd', os.getcwd())

        # 初始化 TaskMetaManager
        mgr = TaskMetaManager(cwd)

        # 获取活跃任务
        task_id = mgr.get_active_task_id()
        if not task_id:
            sys.stderr.write("[INFO v21.0] 无活跃任务,跳过归档\n")
            output = {"continue": True}
            print(json.dumps(output, ensure_ascii=False))
            sys.exit(0)

        # 加载任务元数据
        task_meta = mgr.load_task_meta(task_id)
        if not task_meta:
            sys.stderr.write(f"[ERROR] 加载任务元数据失败: {task_id}\n")
            output = {"continue": True}
            print(json.dumps(output, ensure_ascii=False))
            sys.exit(0)

        # 检查是否已归档
        if task_meta.get('archived', False):
            sys.stderr.write(f"[INFO v21.0] 任务已归档,跳过: {task_id}\n")
            output = {"continue": True}
            print(json.dumps(output, ensure_ascii=False))
            sys.exit(0)

        # 原子更新:标记为已归档
        def mark_archived(meta):
            meta['archived'] = True
            meta['archived_at'] = datetime.now().isoformat()
            return meta

        updated = mgr.atomic_update(task_id, mark_archived)

        if updated:
            sys.stderr.write(f"[INFO v21.0] 任务已归档: {task_id}\n")

            # 清除活跃任务标记
            mgr.clear_active_task()

            # 构建归档成功消息
            success_message = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 任务归档完成 (v21.0)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**任务ID**: {task_id}
**归档时间**: {updated.get('archived_at', '')}

任务元数据已标记为已归档,可以在tasks/{task_id}目录查看。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PostArchive",
                    "additionalContext": success_message
                },
                "continue": True
            }
            print(json.dumps(output, ensure_ascii=False))
        else:
            sys.stderr.write(f"[ERROR] 归档失败: {task_id}\n")
            output = {"continue": True}
            print(json.dumps(output, ensure_ascii=False))

        sys.exit(0)

    except Exception as e:
        sys.stderr.write(f"[ERROR] Hook执行失败: {e}\n")
        import traceback
        traceback.print_exc(file=sys.stderr)
        output = {"continue": True}
        print(json.dumps(output, ensure_ascii=False))
        sys.exit(0)


if __name__ == '__main__':
    main()
