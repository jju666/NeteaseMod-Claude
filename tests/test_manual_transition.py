#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动触发Implementation→Finalization状态转移测试
"""
import sys
import os
import json

# 添加hooks路径
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(base_dir, '.claude', 'hooks'))

from core.task_meta_manager import TaskMetaManager
from datetime import datetime

# 设置工作目录
cwd = base_dir
os.environ['CLAUDE_PROJECT_DIR'] = cwd

task_id = "任务-1120-020531-修复玩家死亡复活"
meta_manager = TaskMetaManager(cwd)

print("=" * 60)
print("手动触发Implementation→Finalization状态转移")
print("=" * 60)

# 定义转移函数
def manual_transition(meta_data):
    """手动执行状态转移"""
    current_step = meta_data.get('current_step', '')

    print(f"\n[INFO] 当前阶段: {current_step}")

    if current_step != 'implementation':
        print(f"[ERROR] 当前阶段不是implementation，无法转移")
        return meta_data

    # 执行状态转移
    print(f"[INFO] 开始状态转移...")

    # 1. 更新current_step
    meta_data['current_step'] = 'finalization'
    print(f"[OK] current_step更新为finalization")

    # 2. 更新implementation状态
    if 'steps' not in meta_data:
        meta_data['steps'] = {}
    if 'implementation' not in meta_data['steps']:
        meta_data['steps']['implementation'] = {}

    meta_data['steps']['implementation']['user_confirmed'] = True
    meta_data['steps']['implementation']['confirmed_at'] = datetime.now().isoformat()
    meta_data['steps']['implementation']['status'] = 'completed'
    meta_data['steps']['implementation']['completed_at'] = datetime.now().isoformat()
    print(f"[OK] implementation状态更新为completed")

    # 3. 启动finalization阶段
    if 'finalization' not in meta_data['steps']:
        meta_data['steps']['finalization'] = {}
    meta_data['steps']['finalization']['status'] = 'in_progress'
    meta_data['steps']['finalization']['started_at'] = datetime.now().isoformat()
    print(f"[OK] finalization阶段启动")

    # 4. 记录状态转移
    if 'state_transitions' not in meta_data:
        meta_data['state_transitions'] = []

    next_id = max([t.get('id', 0) for t in meta_data['state_transitions']], default=0) + 1

    transition_record = {
        'id': next_id,
        'from_step': 'implementation',
        'to_step': 'finalization',
        'timestamp': datetime.now().isoformat(),
        'trigger': 'manual_test',
        'details': {
            'user_input': '我测试没问题了',
            'feedback_type': 'explicit_success',
            'test_mode': True
        }
    }

    meta_data['state_transitions'].append(transition_record)
    print(f"[OK] 状态转移记录已添加（ID={next_id}）")

    # 5. 添加反馈记录
    if 'test_feedback_history' not in meta_data['steps']['implementation']:
        meta_data['steps']['implementation']['test_feedback_history'] = []

    feedback_entry = {
        'timestamp': datetime.now().isoformat(),
        'user_feedback': '我测试没问题了',
        'feedback_type': 'explicit_success',
        'clarification_requested': False,
        'code_changes_count': len(meta_data.get('metrics', {}).get('code_changes', []))
    }
    meta_data['steps']['implementation']['test_feedback_history'].append(feedback_entry)
    print(f"[OK] 反馈记录已添加")

    # 6. 更新updated_at
    meta_data['updated_at'] = datetime.now().isoformat()

    return meta_data

# 执行原子更新
try:
    print(f"\n[INFO] 执行原子更新...")
    updated_meta = meta_manager.atomic_update(task_id, manual_transition)

    if updated_meta:
        print(f"\n[SUCCESS] 状态转移成功！")
        print(f"\n更新后状态:")
        print(f"  - current_step: {updated_meta.get('current_step')}")
        print(f"  - implementation.status: {updated_meta.get('steps', {}).get('implementation', {}).get('status')}")
        print(f"  - implementation.user_confirmed: {updated_meta.get('steps', {}).get('implementation', {}).get('user_confirmed')}")
        print(f"  - finalization.status: {updated_meta.get('steps', {}).get('finalization', {}).get('status')}")
        print(f"  - state_transitions count: {len(updated_meta.get('state_transitions', []))}")

        # 显示最后一个状态转移记录
        last_transition = updated_meta.get('state_transitions', [])[-1]
        print(f"\n最后一个状态转移记录:")
        print(f"  - id: {last_transition.get('id')}")
        print(f"  - from_step: {last_transition.get('from_step')}")
        print(f"  - to_step: {last_transition.get('to_step')}")
        print(f"  - trigger: {last_transition.get('trigger')}")
    else:
        print(f"\n[FAIL] 原子更新失败")

except Exception as e:
    print(f"\n[ERROR] 执行失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
