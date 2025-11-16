#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stop Hook - 轮次边界与任务验证 (v3.0 Final - 语义化重构)
阻止未完成的任务结束,强制继续分析

触发时机: 会话结束前
工作机制:
1. 主动等待PostToolUse完成(Race Condition优化)
2. 查找当前活跃任务
3. 检查用户是否确认修复
4. 未确认时阻止会话结束并更新失败计数器
5. 失败≥2次时触发专家审核提醒

核心变更(v3.0 Final):
- [Phase 1] wait_for_posttooluse_completion(): 文件修改时间主动等待
- [Phase 1] Race Condition延迟从固定200ms → 动态50-100ms
- [Phase 1] 删除超时通知功能(简化系统)
- [Phase 2] 语义化命名: step3_execute → implementation

退出码:
- 0: 成功,允许结束
- 2: 阻止结束
- 1: 非阻塞错误
"""

import sys
import json
import os
import time
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


def wait_for_posttooluse_completion(meta_path, max_wait=0.5):
    """
    主动等待PostToolUse完成写入 (v3.0 Final Phase 1核心优化)

    Race Condition问题:
    - PostToolUse和Stop Hook并行运行
    - 如果Stop在PostToolUse写入前读取,会漏掉最后一次代码修改

    解决策略:
    1. 记录初始文件修改时间
    2. 每50ms轮询一次文件修改时间
    3. 检测到文件更新后,再等待一个周期确保写入完成
    4. 最大等待500ms后超时,使用现有数据

    Args:
        meta_path: task-meta.json文件路径
        max_wait: 最大等待时间(秒),默认0.5秒

    Returns:
        bool: True表示检测到文件更新, False表示超时

    性能对比 (v2.0 vs v3.0 Final):
    - AI未修改代码: 200ms → 50ms (⬆️ 75%)
    - PostToolUse正常完成: 200ms → 50-100ms (⬆️ 50%+)
    - PostToolUse耗时300ms: 200ms(有风险) → 350ms(安全) (✅ 更可靠)
    """
    if not os.path.exists(meta_path):
        return False

    try:
        initial_mtime = os.path.getmtime(meta_path)
    except OSError:
        return False

    waited = 0
    poll_interval = 0.05  # 50ms轮询

    while waited < max_wait:
        time.sleep(poll_interval)
        waited += poll_interval

        try:
            current_mtime = os.path.getmtime(meta_path)
            if current_mtime > initial_mtime:
                # 文件已更新,再等待一个周期确保写入完成
                time.sleep(poll_interval)

                # 调试日志(仅在开发模式)
                if os.getenv('MODSDK_DEBUG') == '1':
                    sys.stderr.write(
                        "[Stop Hook] 检测到文件更新, 等待时间: {:.0f}ms\n".format(waited * 1000)
                    )

                return True
        except OSError:
            # 文件被删除或无法访问,继续等待
            continue

    # 超时,使用现有数据(大部分情况是AI没有调用Write/Edit)
    if os.getenv('MODSDK_DEBUG') == '1':
        sys.stderr.write(
            "[Stop Hook] 等待超时({:.0f}ms), 使用现有数据\n".format(max_wait * 1000)
        )

    return False


def check_user_confirmation(task_id, cwd):
    """
    检查用户是否确认任务完成(v3.0 Final版本 - 语义化命名)

    Returns:
        bool: 用户是否确认
    """
    mgr = TaskMetaManager(cwd)
    task_meta = mgr.load_task_meta(task_id)

    if not task_meta:
        return False

    # 检查步骤状态中的user_confirmed字段(v3.0 Final: implementation语义化命名)
    steps = task_meta.get('steps', {})
    implementation = steps.get('implementation', {})

    return implementation.get('user_confirmed', False)


def _get_current_round(task_meta):
    """
    获取当前轮次（v3.0 Final Bug Fix新增）

    Args:
        task_meta: 任务元数据

    Returns:
        int: 当前轮次
    """
    bug_fix = task_meta.get('bug_fix_tracking', {})
    feature = task_meta.get('feature_tracking', {})

    if bug_fix.get('enabled'):
        return len(bug_fix.get('iterations', [])) + 1
    elif feature.get('enabled'):
        return len(feature.get('iterations', [])) + 1
    else:
        return 1


def _format_code_changes(code_changes):
    """
    格式化代码修改列表为用户可读格式（v3.0 Final Bug Fix新增）

    Args:
        code_changes: code_changes数组

    Returns:
        str: 格式化的修改摘要
    """
    if not code_changes:
        return "  (无修改记录)"

    lines = []
    # 按文件分组
    files = {}
    for change in code_changes:
        file_path = change.get('file', 'unknown')
        tool = change.get('tool', 'Unknown')

        if file_path not in files:
            files[file_path] = []
        files[file_path].append(tool)

    # 生成摘要
    for idx, (file_path, tools) in enumerate(files.items(), 1):
        # 提取文件名
        import os
        file_name = os.path.basename(file_path)
        tool_summary = ", ".join(set(tools))
        lines.append(u"  {}. {} ({})".format(idx, file_name, tool_summary))

    return "\n".join(lines)


def main():
    try:
        # 读取stdin输入
        data = json.load(sys.stdin)

        stop_reason = data.get('stopReason', '')
        cwd = os.getcwd()

        # v3.1改动：根据session_id获取绑定任务
        mgr = TaskMetaManager(cwd)
        session_id = data.get('session_id')

        if not session_id:
            sys.stderr.write("[WARN] Stop缺少session_id，降级到全局模式\n")
            task_id = mgr.get_active_task_id()
            if not task_id:
                sys.exit(0)
        else:
            task_binding = mgr.get_active_task_by_session(session_id)
            if not task_binding:
                # 无绑定任务，放行Stop
                sys.exit(0)
            task_id = task_binding['task_id']

        # [v3.0 Final Phase 1优化] 主动等待PostToolUse完成
        meta_path = mgr._get_meta_path(task_id)
        file_updated = wait_for_posttooluse_completion(meta_path, max_wait=0.5)

        # 加载任务元数据(确保读取最新数据)
        task_meta = mgr.load_task_meta(task_id)
        if not task_meta:
            sys.stderr.write(f"[ERROR] 加载任务元数据失败: {task_id}\n")
            sys.exit(0)

        # [v3.0 Final Phase 2新增] 检查Planning阶段是否需要用户确认
        current_step = task_meta.get('current_step', '')
        steps = task_meta.get('steps', {})
        planning = steps.get('planning', {})

        if current_step == 'planning' and not planning.get('user_confirmed', False):
            # Planning阶段未确认，生成方案摘要并阻止会话
            task_desc = task_meta.get('task_description', '未知任务')
            expert_review = planning.get('expert_review', {})

            # 构建方案摘要消息
            message = u"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🛑 停止会话 - 等待方案确认
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**任务ID**: {}
**当前阶段**: Planning (方案制定)

""".format(task_id[:30])

            # 添加方案描述
            solution_summary = planning.get('solution_summary', '')
            if solution_summary:
                message += u"📋 **方案摘要**:\n{}\n\n".format(solution_summary)

            # 添加专家审查结果
            if expert_review:
                review_result = expert_review.get('result', '')
                review_score = expert_review.get('score', 0)

                if review_result == 'approved':
                    message += u"✅ **专家审查**: 通过\n"
                    if review_score:
                        message += u"**审核评分**: {}/10\n\n".format(review_score)
                    message += u"🎉 方案已通过专家审查！\n\n"
                else:
                    message += u"⚠️ **专家审查**: 发现问题\n\n"
                    issues = expert_review.get('issues', [])
                    if issues:
                        message += u"🔍 **发现的问题**:\n"
                        for idx, issue in enumerate(issues, 1):
                            message += u"  {}. {}\n".format(idx, issue)
                        message += u"\n"

                    suggestions = expert_review.get('suggestions', [])
                    if suggestions:
                        message += u"💡 **改进建议**:\n"
                        for idx, suggestion in enumerate(suggestions, 1):
                            message += u"  {}. {}\n".format(idx, suggestion)
                        message += u"\n"

            # 添加确认提示
            message += u"""**下一步**:
1. 如果同意方案，请输入"同意"或"可以"
2. 如果需要调整，请描述调整建议
3. 如果完全否定，请输入"重来"

❓ **请确认是否同意该方案？**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

            # Stop Hook 官方格式 - 阻止会话
            output = {
                "decision": "block",
                "reason": "Planning阶段等待用户确认方案",
                "continue": False,
                "stopReason": message
            }

            print(json.dumps(output, ensure_ascii=False))
            sys.exit(2)  # 阻止操作

        # 检查用户是否确认修复（Implementation阶段）
        user_confirmed = check_user_confirmation(task_id, cwd)

        if not user_confirmed:
            # v3.0 Final Bug Fix: 用户未确认修复 ≠ 任务失败
            # 这是正常的轮次循环，不应增加failure_count
            # failure_count只应在UserPromptSubmit检测到负面反馈时增加

            # 获取当前轮次和修改摘要（v22.0 Phase 3用户可见性增强）
            metrics = task_meta.get('metrics', {})
            code_changes = metrics.get('code_changes', [])

            # 主动等待PostToolUse完成（Race Condition优化）

            # 🔥 P5修复：PostToolUse Hook未触发时的fallback机制
            if not code_changes:
                # 检查git status看是否有实际的代码修改
                try:
                    import subprocess
                    result = subprocess.run(
                        ['git', 'diff', '--name-only', 'HEAD'],
                        capture_output=True,
                        text=True,
                        timeout=3,
                        cwd=cwd
                    )

                    if result.returncode == 0 and result.stdout.strip():
                        # 有未提交的修改，补记录到task-meta.json
                        modified_files = result.stdout.strip().split('\n')

                        def补记录代码修改(meta):
                            metrics = meta.setdefault('metrics', {})
                            code_changes_list = metrics.setdefault('code_changes', [])

                            for file_path in modified_files:
                                # 检查是否已存在
                                if not any(c.get('file') == file_path for c in code_changes_list):
                                    code_changes_list.append({
                                        'file': file_path,
                                        'tool': 'Update',  # 假设是Update工具
                                        'timestamp': datetime.now().isoformat(),
                                        'success': True,
                                        'fallback_recorded': True  # 标记为补记录
                                    })
                                    sys.stderr.write(f"[Stop Hook Fallback] 补记录代码修改: {file_path}\n")

                            return meta

                        task_meta = mgr.atomic_update(task_id, 补记录代码修改)
                        if task_meta:
                            code_changes = task_meta.get('metrics', {}).get('code_changes', [])
                            sys.stderr.write(f"[Stop Hook Fallback] 补记录完成，共 {len(code_changes)} 个文件\n")
                except Exception as e:
                    sys.stderr.write(f"[Stop Hook Fallback] git检查失败: {e}\n")

            if code_changes:
                # 如果有代码修改记录，显示摘要
                current_round = _get_current_round(task_meta)

                message = u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🛑 第 {} 轮修改完成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**任务ID**: {}

📋 **修改摘要**:
{}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🧪 **请测试修改效果，并提供反馈**:

反馈示例:
  - "修复了" / "完成" → 进入Finalization
  - "没修复" / "需要调整" → 回滚到Planning重新分析
  - "继续" / 继续描述问题 → 保持Implementation继续修改

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(current_round, task_id, _format_code_changes(code_changes))
            else:
                # 如果没有代码修改记录，可能是PostToolUse失败或AI未修改代码
                message = u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🛑 停止会话 - 等待用户反馈
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**任务ID**: {}
**当前阶段**: Implementation (实施)

⚠️ **注意**: 未检测到代码修改记录。

这可能是因为:
1. AI正在分析问题，尚未开始修改代码
2. PostToolUse Hook记录失败（技术问题）

**下一步**:
1. 如果AI已完成分析和方案制定，可以继续实施代码修改
2. 如果需要重新分析，请描述问题
3. 如果遇到技术问题，请联系管理员

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(task_id)

            # Stop Hook 官方格式
            # ✅ Phase 5 Bug Fix: 移除未定义的failure_count引用
            # 根据v3.0 Final设计，用户未确认 ≠ 任务失败，不应显示failure_count
            output = {
                "decision": "block",
                "reason": "Implementation阶段等待用户反馈",
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
        # [v3.0 Final增强] 详细错误诊断
        sys.stderr.write("=" * 80 + "\n")
        sys.stderr.write("[HOOK ERROR] Stop Hook 执行失败\n")
        sys.stderr.write("=" * 80 + "\n")
        sys.stderr.write(u"错误类型: {}\n".format(type(e).__name__))
        sys.stderr.write(u"错误消息: {}\n".format(str(e)))
        sys.stderr.write("\n完整堆栈:\n")
        import traceback
        traceback.print_exc(file=sys.stderr)

        # 输出上下文信息
        sys.stderr.write("\n上下文信息:\n")
        try:
            cwd = os.getcwd()
            sys.stderr.write(u"  cwd: {}\n".format(cwd))
            sys.stderr.write(u"  HOOK_DIR: {}\n".format(HOOK_DIR))
            sys.stderr.write(u"  sys.path[0:3]: {}\n".format(sys.path[:3]))

            # 检查核心模块
            try:
                from core.task_meta_manager import TaskMetaManager as TMM
                sys.stderr.write(u"  TaskMetaManager可用: True\n")
            except ImportError as ie:
                sys.stderr.write(u"  TaskMetaManager可用: False ({})\n".format(ie))

            # 检查活跃任务
            active_file = os.path.join(cwd, '.claude', '.task-active.json')
            sys.stderr.write(u"  .task-active.json存在: {}\n".format(os.path.exists(active_file)))

            # 检查task-meta.json
            mgr = TaskMetaManager(cwd)
            task_id = mgr.get_active_task_id()
            if task_id:
                meta_path = mgr._get_meta_path(task_id)
                sys.stderr.write(u"  task-meta.json路径: {}\n".format(meta_path))
                sys.stderr.write(u"  task-meta.json存在: {}\n".format(os.path.exists(meta_path)))
        except Exception as ctx_err:
            sys.stderr.write(u"  (上下文信息收集失败: {})\n".format(ctx_err))

        sys.stderr.write("=" * 80 + "\n")

        # 降级：允许会话结束（避免完全阻塞用户）
        sys.exit(1)  # 非阻塞错误


if __name__ == '__main__':
    main()
