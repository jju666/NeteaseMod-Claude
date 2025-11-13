# -*- coding: utf-8 -*-
"""
修复 user-prompt-submit-hook.py 的状态机初始化
添加 .task-meta.json 和 .task-active.json 创建逻辑
"""

import sys
import io

# Windows编码修复
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 读取文件
file_path = 'templates/.claude/hooks/user-prompt-submit-hook.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 定位插入点：在 "state_file = ..." 之后
insert_marker = """        state_file = os.path.join(cwd, '.claude', 'workflow-state.json')
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(workflow_state, f, indent=2, ensure_ascii=False)

        # 📢 通知1：任务启动 - 步骤1开始"""

replacement = """        # 保存workflow-state.json
        state_file = os.path.join(cwd, '.claude', 'workflow-state.json')
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(workflow_state, f, indent=2, ensure_ascii=False)

        # 创建 .task-meta.json（unified-workflow-driver 需要）
        task_meta = {
            "task_id": task_id,
            "task_description": task_desc,
            "task_type": "feature",  # 默认为功能开发
            "task_complexity": "standard",  # 默认标准复杂度
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "workflow_state": workflow_state,
            "metrics": {
                "docs_read": [],
                "docs_read_count": 0,
                "code_changes": [],
                "code_changes_count": 0,
                "failure_count": 0,
                "failures": [],
                "expert_review_triggered": False
            }
        }

        meta_file = os.path.join(task_dir, '.task-meta.json')
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(task_meta, f, indent=2, ensure_ascii=False)

        # 创建 .task-active.json（unified-workflow-driver 快速检查）
        active_flag = {
            "task_id": task_id,
            "task_dir": task_dir,
            "current_step": "step3_execute",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        active_flag_file = os.path.join(cwd, '.claude', '.task-active.json')
        with open(active_flag_file, 'w', encoding='utf-8') as f:
            json.dump(active_flag, f, indent=2, ensure_ascii=False)

        # 📢 通知1：任务启动 - 步骤3开始（玩法包模式）"""

# 执行替换
if insert_marker in content:
    new_content = content.replace(insert_marker, replacement)

    # 同时更新通知消息
    new_content = new_content.replace(
        'u"步骤1：理解任务 | 玩法包: {}".format(pack_info)',
        'u"步骤3：执行实施 | 玩法包: {}".format(pack_info)'
    )

    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print("✅ 修复完成！")
    print("- 添加了 .task-meta.json 创建逻辑")
    print("- 添加了 .task-active.json 创建逻辑")
    print("- 更新了通知消息（步骤1 → 步骤3）")
else:
    print("❌ 未找到插入点，文件可能已被修改")
    sys.exit(1)
