#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified PostToolUse Updater - 统一PostToolUse更新器
Version: v2.0

职责:
1. 纯粹的状态更新器(零决策逻辑)
2. 记录工具执行结果到 task-meta.json
3. 检测步骤完成条件,自动推进工作流
4. 检测循环模式,触发专家审查
5. 使用文件锁避免并发冲突

核心变更(v2.0):
- 删除 workflow-state.json 所有逻辑
- 直接更新 task-meta.json(唯一数据源)
- 使用 TaskMetaManager 的原子更新 API
"""

import sys
import json
import os
from datetime import datetime
from typing import Dict, Optional, Tuple

# 🔥 v25.0修复: Windows编码完整容错策略
# v3.0 Final Bug Fix: Windows UTF-8编码支持（emoji输出）
if sys.platform == 'win32':
    import io
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='replace')
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加core模块到sys.path
HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_HOOK_DIR = os.path.dirname(HOOK_DIR)
sys.path.insert(0, PARENT_HOOK_DIR)

try:
    from core.task_meta_manager import TaskMetaManager
    from core.expert_trigger import ExpertTrigger
except ImportError as e:
    sys.stderr.write(f"[ERROR] 无法导入核心模块: {e}\n")
    # 兜底:静默退出
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": ""
        },
        "suppressOutput": True
    }, ensure_ascii=False))
    sys.exit(0)


def silent_exit(message: str = ""):
    """静默退出 (v3.0 Final增强: 可选用户提示)

    Args:
        message: 可选的用户可见消息
    """
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": message
        },
        "suppressOutput": not bool(message)  # 如果有消息则显示
    }
    print(json.dumps(output, ensure_ascii=False))
    sys.exit(0)


def update_metrics(task_meta: Dict, tool_name: str, tool_input: Dict, is_error: bool):
    """
    更新任务度量指标

    Args:
        task_meta: 任务元数据
        tool_name: 工具名称
        tool_input: 工具输入参数
        is_error: 是否发生错误
    """
    # 🔥 P2修复：从task_meta提取task_id（用于诊断日志）
    task_id = task_meta.get('task_id', 'unknown')

    # 初始化 metrics 字段
    if 'metrics' not in task_meta:
        task_meta['metrics'] = {
            'tools_used': [],
            'code_changes': [],
            'docs_read': [],
            'failed_operations': []
        }

    metrics = task_meta['metrics']

    # 记录工具使用
    metrics['tools_used'].append({
        'tool': tool_name,
        'timestamp': datetime.now().isoformat(),
        'success': not is_error
    })

    # 记录代码修改
    # ✅ Phase 4 Bug Fix: 兼容Claude Code v2.0的Update工具名
    # 原工具名: Edit, Write
    # 新增工具名: Update (v2.0统一工具名), NotebookEdit (Jupyter notebook)
    if tool_name in ['Edit', 'Write', 'Update', 'NotebookEdit']:
        file_path = tool_input.get('file_path', '')
        if file_path:
            metrics['code_changes'].append({
                'file': file_path,
                'tool': tool_name,
                'timestamp': datetime.now().isoformat(),
                'success': not is_error
            })

    # 【v23.1新增】P1 BUG修复：检测Bash工具中的文件修改
    # 基于任务-1117-234152测试发现：AI使用Bash命令（python脚本）修改文件，导致code_changes丢失
    # 方案：检测Bash命令中的文件修改关键词，尝试识别被修改的文件
    elif tool_name == 'Bash' and not is_error:
        command = tool_input.get('command', '')
        if command:
            # 启发式检测：命令中包含文件修改关键词
            file_mod_patterns = [
                'python',  # Python脚本可能修改文件
                'sed ',    # sed命令
                'awk ',    # awk命令
                'echo.*>>',  # 重定向追加
                'echo.*>',   # 重定向覆盖
                'cat.*>',    # cat重定向
                'tee '       # tee命令
            ]

            # 检查是否包含文件修改模式
            import re
            has_file_mod = any(re.search(pattern, command, re.IGNORECASE) for pattern in file_mod_patterns)

            if has_file_mod:
                # 尝试提取文件路径（简单的启发式规则）
                # 1. 提取.py文件路径
                py_files = re.findall(r'([^\s"\']+\.py)', command)
                # 2. 提取其他常见文件扩展名
                other_files = re.findall(r'([^\s"\']+\.(?:js|ts|jsx|tsx|java|cpp|c|h|go|rs|rb|php))', command)

                files_found = py_files + other_files
                if files_found:
                    for file_path in files_found:
                        # 避免重复记录
                        if not any(c.get('file') == file_path for c in metrics['code_changes']):
                            metrics['code_changes'].append({
                                'file': file_path,
                                'tool': 'Bash',
                                'timestamp': datetime.now().isoformat(),
                                'success': True,
                                'note': 'detected_from_bash_command'
                            })

    # 记录文档阅读（P1增强：添加详细诊断日志 + 文件日志）
    if tool_name == 'Read':
        file_path = tool_input.get('file_path', '')

        # 🔍 P1诊断：写入文件日志（stderr可能被抑制）
        DEBUG_LOG = os.path.join(os.getcwd(), 'posttooluse-debug.log')
        try:
            with open(DEBUG_LOG, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"[{datetime.now().isoformat()}] Read操作检测\n")

                # 🔥 修复：分步写入,避免单行编码错误导致全部丢失
                try:
                    f.write(f"  - task_id: {task_id}\n")
                except Exception as e:
                    f.write(f"  - task_id: [ERROR: {type(e).__name__}]\n")

                try:
                    # 使用repr()确保中文路径正确显示
                    f.write(f"  - file_path: {repr(file_path)}\n")
                except Exception as e:
                    f.write(f"  - file_path: [ERROR: {type(e).__name__}]\n")

                try:
                    f.write(f"  - type: {type(file_path)}\n")
                    f.write(f"  - len: {len(file_path) if file_path else 'None'}\n")
                except Exception as e:
                    f.write(f"  - metadata: [ERROR: {type(e).__name__}]\n")

                try:
                    f.write(f"  - 'markdown' in path: {'markdown' in file_path if file_path else False}\n")
                    f.write(f"  - '.md' in path: {'.md' in file_path if file_path else False}\n")
                except Exception as e:
                    f.write(f"  - checks: [ERROR: {type(e).__name__}]\n")

        except Exception as log_err:
            # 如果文件打开失败,尝试写入错误到stderr
            sys.stderr.write(f"[CRITICAL] DEBUG_LOG写入失败: {type(log_err).__name__}: {log_err}\n")

        # 🔍 P1诊断：详细记录匹配过程（stderr，可能不可见）
        sys.stderr.write(f"[PostToolUse-DEBUG] Read操作检测\n")
        sys.stderr.write(f"  - file_path: {file_path}\n")
        sys.stderr.write(f"  - 包含'markdown': {'markdown' in file_path if file_path else False}\n")
        sys.stderr.write(f"  - 包含'.md': {'.md' in file_path if file_path else False}\n")

        # 增强路径匹配逻辑（更宽松的条件）
        is_doc = False
        if file_path:
            path_lower = file_path.lower()
            is_doc = (
                'markdown' in path_lower or
                '.md' in path_lower or
                path_lower.endswith('.md') or
                '/markdown/' in path_lower or
                '\\markdown\\' in path_lower
            )

        if is_doc:
            # 🔥 P3修复：添加去重逻辑，防止重复添加同一文档
            existing_files = [d['file'] for d in metrics['docs_read']]
            if file_path not in existing_files:
                metrics['docs_read'].append({
                    'file': file_path,
                    'timestamp': datetime.now().isoformat()
                })
                sys.stderr.write(f"[PostToolUse-DEBUG] ✅ 文档已添加到docs_read（当前总数：{len(metrics['docs_read'])}）\n")
                # 写入成功记录到文件
                try:
                    with open(DEBUG_LOG, 'a', encoding='utf-8') as f:
                        f.write(f"  - 结果: ✅ 已添加到docs_read（总数：{len(metrics['docs_read'])}）\n")
                except:
                    pass
            else:
                sys.stderr.write(f"[PostToolUse-DEBUG] ⚠️ 文档已存在，跳过（当前总数：{len(metrics['docs_read'])}）\n")
                # 写入重复记录到文件
                try:
                    with open(DEBUG_LOG, 'a', encoding='utf-8') as f:
                        f.write(f"  - 结果: ⚠️ 文档已存在，跳过（总数：{len(metrics['docs_read'])}）\n")
                except:
                    pass
        else:
            sys.stderr.write(f"[PostToolUse-DEBUG] ⚠️ 文档未记录（不符合条件）\n")
            # 写入失败记录到文件
            try:
                with open(DEBUG_LOG, 'a', encoding='utf-8') as f:
                    f.write(f"  - 结果: ⚠️ 未记录（不符合条件）\n")
            except:
                pass

    # 记录失败操作
    if is_error:
        metrics['failed_operations'].append({
            'tool': tool_name,
            'input': tool_input,
            'timestamp': datetime.now().isoformat()
        })


# detect_loop_indicators() 函数已废弃 - 已被 ExpertTrigger.should_trigger() 替代（第356-367行）

def update_bug_fix_tracking(task_meta: Dict, tool_name: str, tool_input: Dict, is_error: bool):
    """
    更新BUG修复追踪状态

    Args:
        task_meta: 任务元数据
        tool_name: 工具名称
        tool_input: 工具输入参数
        is_error: 是否发生错误
    """
    bug_fix_tracking = task_meta.get('bug_fix_tracking', {})
    if not bug_fix_tracking.get('enabled'):
        return

    loop_indicators = bug_fix_tracking.setdefault('loop_indicators', {
        'same_file_edit_count': 0,
        'failed_test_count': 0,
        'negative_feedback_count': 0
    })

    # 更新同文件修改计数
    if tool_name in ['Edit', 'Write']:
        file_path = tool_input.get('file_path', '')
        metrics = task_meta.get('metrics', {})
        code_changes = metrics.get('code_changes', [])

        # 计算同一文件的修改次数
        same_file_count = sum(1 for change in code_changes if change.get('file') == file_path)
        loop_indicators['same_file_edit_count'] = max(loop_indicators['same_file_edit_count'], same_file_count)

    # 更新测试失败计数
    if tool_name == 'Bash' and is_error:
        bash_cmd = tool_input.get('command', '')
        if 'test' in bash_cmd.lower() or 'pytest' in bash_cmd.lower():
            loop_indicators['failed_test_count'] += 1


def main():
    """主入口"""
    # ✅ Phase 6 Enhancement: 启动诊断日志
    sys.stderr.write("=" * 60 + "\n")
    sys.stderr.write("[PostToolUse] Hook启动\n")
    sys.stderr.write(f"[PostToolUse] cwd: {os.getcwd()}\n")
    sys.stderr.write(f"[PostToolUse] 时间: {datetime.now().isoformat()}\n")
    sys.stderr.write("=" * 60 + "\n")

    # 1. 解析输入
    try:
        stdin_data = sys.stdin.read()
        sys.stderr.write(f"[PostToolUse] 接收到stdin数据: {len(stdin_data)} bytes\n")
        event_data = json.loads(stdin_data)
        sys.stderr.write(f"[PostToolUse] JSON解析成功\n")
    except json.JSONDecodeError as e:
        sys.stderr.write(f"[ERROR] JSON解析失败: {e}\n")
        sys.stderr.write(f"[DEBUG] stdin内容: {stdin_data[:500]}...\n")
        silent_exit()
        return

    tool_name = event_data.get("tool_name", "")
    tool_input = event_data.get("tool_input", {})
    tool_result = event_data.get("tool_response", "")
    is_error = event_data.get("is_error", False)

    # ✅ Phase 4 Enhancement: 增强错误诊断
    # 检查空工具名并输出调试信息
    if not tool_name:
        sys.stderr.write("[ERROR] PostToolUse Hook: tool_name字段缺失或为空\n")
        sys.stderr.write(f"[DEBUG] event_data keys: {list(event_data.keys())}\n")
        sys.stderr.write(f"[DEBUG] event_data preview: {str(event_data)[:500]}...\n")

        # 容错：尝试旧版本的camelCase字段名（向后兼容）
        if 'toolName' in event_data:
            tool_name = event_data['toolName']
            tool_input = event_data.get('toolInput', {})
            tool_result = event_data.get('toolResult', "")
            is_error = event_data.get('isError', False)
            sys.stderr.write(f"[WARN] 使用旧版本camelCase字段名: toolName={tool_name}\n")
        else:
            sys.stderr.write("[ERROR] 无法提取工具名（snake_case和camelCase均不存在），跳过metrics更新\n")
            silent_exit()
            return

    # 可选：调试模式下输出工具名（通过环境变量MODSDK_DEBUG=1启用）
    if os.getenv('MODSDK_DEBUG') == '1':
        sys.stderr.write(f"[DEBUG] PostToolUse: tool={tool_name}, input_keys={list(tool_input.keys())}\n")

    # 🔥 v22.3.10: Task工具诊断 - 记录完整的tool_response
    if tool_name == 'Task':
        sys.stderr.write("=" * 60 + "\n")
        sys.stderr.write("[DIAGNOSTIC] Task工具执行完成\n")
        sys.stderr.write(f"tool_input keys: {list(tool_input.keys())}\n")
        sys.stderr.write(f"tool_response type: {type(tool_result)}\n")

        # 将完整的 tool_response 记录到文件
        try:
            task_response_log = os.path.join(os.getcwd(), "task-tool-response-debug.log")
            with open(task_response_log, 'a', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write(f"[{datetime.now().isoformat()}] Task工具执行\n")
                f.write(f"tool_input: {json.dumps(tool_input, ensure_ascii=False, indent=2)}\n")
                f.write(f"tool_response type: {type(tool_result)}\n")
                f.write(f"tool_response length: {len(str(tool_result))}\n")
                f.write(f"tool_response content:\n{json.dumps(tool_result, ensure_ascii=False, indent=2)}\n")
                f.write("=" * 80 + "\n\n")
            sys.stderr.write(f"[DIAGNOSTIC] tool_response已记录到: {task_response_log}\n")
        except Exception as e:
            sys.stderr.write(f"[ERROR] 记录task_response失败: {e}\n")

        sys.stderr.write("=" * 60 + "\n")

    # 2. 获取工作目录
    cwd = os.getcwd()

    # 3. 初始化 TaskMetaManager
    mgr = TaskMetaManager(cwd)

    # 4. v3.1改动：根据session_id获取绑定任务
    session_id = event_data.get('session_id')
    if not session_id:
        sys.stderr.write("[WARN] PostToolUse缺少session_id，降级到全局模式\n")
        task_id = mgr.get_active_task_id()
        if not task_id:
            silent_exit()
            return
    else:
        task_binding = mgr.get_active_task_by_session(session_id)
        if not task_binding:
            # 无绑定任务，跳过
            silent_exit()
            return
        task_id = task_binding['task_id']

    # 5. 原子更新任务元数据
    def update_func(task_meta: Dict) -> Dict:
        """更新函数(在锁内执行)"""
        # 更新度量指标
        update_metrics(task_meta, tool_name, tool_input, is_error)

        # 更新BUG修复追踪
        update_bug_fix_tracking(task_meta, tool_name, tool_input, is_error)

        # 使用ExpertTrigger检测循环并标记（替代简化版detect_loop_indicators）
        expert_trigger = ExpertTrigger()
        if expert_trigger.should_trigger(task_meta):
            if not task_meta.get('expert_triggered', False):
                task_meta['expert_triggered'] = True
                expert_prompt = expert_trigger.generate_prompt(task_meta)
                sys.stderr.write("[PostToolUse] 专家审查系统已触发\n")
                sys.stderr.write(expert_prompt)
                # 将专家提示保存到task_meta供后续使用
                if 'expert_review' not in task_meta:
                    task_meta['expert_review'] = {}
                task_meta['expert_review']['prompt'] = expert_prompt
                task_meta['expert_review']['triggered_at'] = datetime.now().isoformat()

        return task_meta

    updated_meta = mgr.atomic_update(task_id, update_func)

    if not updated_meta:
        sys.stderr.write("[ERROR] 原子更新失败\n")
        # 🔥 P4修复：记录atomic_update失败到文件日志
        DEBUG_LOG = os.path.join(os.getcwd(), 'posttooluse-debug.log')
        try:
            with open(DEBUG_LOG, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"[{datetime.now().isoformat()}] ❌ atomic_update失败！\n")
                f.write(f"  - task_id: {task_id}\n")
                f.write(f"  - tool_name: {tool_name}\n")
                f.write(f"{'='*60}\n")
        except:
            pass
        silent_exit()
        return
    else:
        # 🔥 P4修复：记录atomic_update成功
        DEBUG_LOG = os.path.join(os.getcwd(), 'posttooluse-debug.log')
        try:
            with open(DEBUG_LOG, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"[{datetime.now().isoformat()}] ✅ atomic_update成功！\n")
                f.write(f"  - task_id: {task_id}\n")
                f.write(f"  - docs_read count: {len(updated_meta.get('metrics', {}).get('docs_read', []))}\n")
                f.write(f"{'='*60}\n")
        except:
            pass

    # v3.0 Final新增: 为代码修改生成用户可见提示（Phase 3增强：添加文件路径）
    user_message = ""
    current_step = updated_meta.get('current_step', '')

    if tool_name in ['Write', 'Edit'] and current_step == 'implementation' and not is_error:
        # 获取文件路径
        file_path = tool_input.get('file_path', '')

        # 获取轮次和修改次数信息
        bug_fix = updated_meta.get('bug_fix_tracking', {})
        feature = updated_meta.get('feature_tracking', {})

        if bug_fix.get('enabled'):
            current_round = len(bug_fix.get('iterations', [])) + 1
        elif feature.get('enabled'):
            current_round = len(feature.get('iterations', [])) + 1
        else:
            current_round = 1

        total_changes = len(updated_meta.get('metrics', {}).get('code_changes', []))

        # 生成带文件路径的消息（v3.0 Final Phase 3增强）
        if file_path:
            # 提取文件名（去除路径前缀）
            # Bug Fix: 删除局部import os（文件顶部已导入）
            file_name = os.path.basename(file_path)
            user_message = f"💾 代码修改已记录: {file_name} (第{current_round}轮, 共{total_changes}次修改)"
        else:
            user_message = f"💾 代码修改已记录 (第{current_round}轮, 共{total_changes}次修改)"

    # 6. 退出（带可选提示）
    silent_exit(user_message)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # [v3.0 Final增强] 详细错误诊断
        sys.stderr.write("=" * 80 + "\n")
        sys.stderr.write("[HOOK ERROR] PostToolUse Hook 执行失败\n")
        sys.stderr.write("=" * 80 + "\n")
        sys.stderr.write(f"错误类型: {type(e).__name__}\n")
        sys.stderr.write(f"错误消息: {str(e)}\n")
        sys.stderr.write("\n完整堆栈:\n")
        import traceback
        traceback.print_exc(file=sys.stderr)

        # 输出上下文信息
        sys.stderr.write("\n上下文信息:\n")
        try:
            cwd = os.getcwd()
            sys.stderr.write(f"  cwd: {cwd}\n")
            sys.stderr.write(f"  PARENT_HOOK_DIR: {PARENT_HOOK_DIR}\n")
            sys.stderr.write(f"  sys.path[0:3]: {sys.path[:3]}\n")

            # 检查核心模块
            try:
                from core.task_meta_manager import TaskMetaManager as TMM
                sys.stderr.write(f"  TaskMetaManager可用: True\n")
            except ImportError as ie:
                sys.stderr.write(f"  TaskMetaManager可用: False ({ie})\n")

            # 检查活跃任务
            active_file = os.path.join(cwd, '.claude', '.task-active.json')
            sys.stderr.write(f"  .task-active.json存在: {os.path.exists(active_file)}\n")

            # 检查task-meta.json
            mgr = TaskMetaManager(cwd)
            task_id = mgr.get_active_task_id()
            if task_id:
                meta_path = mgr._get_meta_path(task_id)
                sys.stderr.write(f"  task-meta.json路径: {meta_path}\n")
                sys.stderr.write(f"  task-meta.json存在: {os.path.exists(meta_path)}\n")
        except Exception as ctx_err:
            sys.stderr.write(f"  (上下文信息收集失败: {ctx_err})\n")

        sys.stderr.write("=" * 80 + "\n")

        # 降级：静默退出（避免完全阻塞工作流）
        silent_exit()
