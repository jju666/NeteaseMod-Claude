#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
UserPromptSubmit Hook - 任务初始化拦截器 + 状态转移处理器 (v3.0 Final / v22.0)

核心功能:
1. /mc 命令处理 - 创建任务追踪基础设施并注入匹配的玩法包
2. 用户状态转移 - 处理用户确认（"同意"）和反馈（"修复了"/"没修复"）
3. 任务恢复 - 检测并恢复已存在的任务
4. 任务取消 - 处理任务取消和失败标记

触发时机: 用户提交提示词后

退出码:
- 0: 成功，继续执行
- 2: 阻止操作
- 1: 非阻塞错误
"""

import sys
import json
import os
import re
from datetime import datetime
import io

# 修复Windows编码问题：强制使用UTF-8
if sys.platform == 'win32':
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='replace')
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 导入通知模块（修复路径）
try:
    from utils.notify import notify_info, notify_warning, notify_error
except ImportError:
    # 降级方案：纯文本输出
    def notify_info(msg, detail=""): sys.stderr.write(u"ℹ️ {} {}\n".format(msg, detail))
    def notify_warning(msg, detail=""): sys.stderr.write(u"⚠️ {} {}\n".format(msg, detail))
    def notify_error(msg, detail=""): sys.stderr.write(u"❌ {} {}\n".format(msg, detail))

# 导入工作流配置加载器（修复路径）
try:
    from utils.config_loader import get_max_task_desc_length
except ImportError:
    def get_max_task_desc_length(project_path=None):
        return 8  # 默认值

# 导入任务取消处理器（修复相对导入）
try:
    from .task_cancellation_handler import handle_cancellation_from_user_prompt
except ImportError:
    # 降级方案：禁用取消功能
    def handle_cancellation_from_user_prompt(user_input, cwd):
        return None
    sys.stderr.write(u"[WARN] 任务取消功能不可用（task_cancellation_handler模块缺失）\n")

# 导入任务元数据管理器（v3.0 Final单一数据源架构）
HOOK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HOOK_DIR)

try:
    from core.task_meta_manager import TaskMetaManager
except ImportError:
    sys.stderr.write(u"[WARN] TaskMetaManager模块缺失，任务恢复功能可能受限\n")
    TaskMetaManager = None

# v24.2: 导入增强型关键词匹配器
try:
    from core.enhanced_matcher import (
        analyze_user_feedback,
        match_keyword_safely_enhanced,
        COMPLETE_SUCCESS_KEYWORDS,
        FAILURE_KEYWORDS,
        PARTIAL_SUCCESS_KEYWORDS,
        PLANNING_ERROR_KEYWORDS,
    )
    ENHANCED_MATCHER_AVAILABLE = True
    sys.stderr.write(u"[INFO] 增强型关键词匹配器已加载 (v24.2)\n")
except ImportError as e:
    ENHANCED_MATCHER_AVAILABLE = False
    sys.stderr.write(u"[WARN] 增强型关键词匹配器不可用，使用基础匹配: {}\n".format(e))

# v25.0: 导入Claude语义分析器（LLM驱动）
try:
    from core.claude_semantic_analyzer import ClaudeSemanticAnalyzer, analyze_user_intent
    CLAUDE_ANALYZER_AVAILABLE = True
    sys.stderr.write(u"[INFO] Claude语义分析器已加载 (v25.0)\n")
except ImportError as e:
    CLAUDE_ANALYZER_AVAILABLE = False
    sys.stderr.write(u"[WARN] Claude语义分析器不可用: {}\n".format(e))

# v25.0: 导入状态转移验证器（确保100%不脱离状态机）
try:
    from core.state_transition_validator import (
        validate_state_transition,
        validate_transition_requirements,
        get_allowed_transitions,
        IllegalTransitionError,
        MissingCriticalFieldError
    )
    STATE_VALIDATOR_AVAILABLE = True
    sys.stderr.write(u"[INFO] 状态转移验证器已加载 (v25.0)\n")
except ImportError as e:
    STATE_VALIDATOR_AVAILABLE = False
    sys.stderr.write(u"[WARN] 状态转移验证器不可用: {}\n".format(e))

# v25.0 重构: 导入关键词注册表和LLM意图分析器
try:
    from orchestrator.keyword_registry import (
        CONFIRM_KEYWORDS, REJECT_KEYWORDS, RESTART_KEYWORDS,
        FIXED_KEYWORDS, NOT_FIXED_KEYWORDS, PARTIAL_SUCCESS_KEYWORDS,
        PLANNING_REQUIRED_KEYWORDS, AMBIGUOUS_POSITIVE, CONTINUE_KEYWORDS,
        get_keywords, has_negation_prefix, match_keyword_safely
    )
    from orchestrator.llm_intent_analyzer import LLMIntentAnalyzer
    from orchestrator.task_initializer import TaskInitializer
    KEYWORD_REGISTRY_AVAILABLE = True
    LLM_INTENT_ANALYZER_AVAILABLE = True
    TASK_INITIALIZER_AVAILABLE = True
    sys.stderr.write(u"[INFO] v25.0重构模块已加载：关键词注册表、LLM意图分析器、任务初始化器\n")
except ImportError as e:
    KEYWORD_REGISTRY_AVAILABLE = False
    LLM_INTENT_ANALYZER_AVAILABLE = False
    TASK_INITIALIZER_AVAILABLE = False
    sys.stderr.write(u"[ERROR] v25.0重构模块导入失败: {}\n".format(e))
    # 降级方案：关键词将在函数内部定义（向后兼容）

# v25.0 重构: 导入状态机协调器和状态转移协调器
try:
    from core.state_machine_coordinator import StateMachineCoordinator
    from orchestrator.state_transition_coordinator import StateTransitionCoordinator
    STATE_MACHINE_COORDINATOR_AVAILABLE = True
    STATE_TRANSITION_COORDINATOR_AVAILABLE = True
    sys.stderr.write(u"[INFO] v25.0状态机协调器已加载：StateMachineCoordinator、StateTransitionCoordinator\n")
except ImportError as e:
    STATE_MACHINE_COORDINATOR_AVAILABLE = False
    STATE_TRANSITION_COORDINATOR_AVAILABLE = False
    sys.stderr.write(u"[ERROR] v25.0状态机协调器导入失败: {}\n".format(e))
    # 降级方案：使用旧版handle_state_transition（向后兼容）

def ensure_dir(path):
    """确保目录存在

    返回:
        bool: 成功返回True, 失败返回False
    """
    try:
        if not os.path.exists(path):
            os.makedirs(path)
            # 验证目录确实被创建
            if not os.path.exists(path):
                sys.stderr.write(u"[CRITICAL] 目录创建失败但未抛出异常: {}\n".format(path))
                return False
        return True
    except Exception as e:
        sys.stderr.write(u"[CRITICAL] 创建目录失败: {}\n错误: {}\n".format(path, e))
        return False

def has_negation_prefix(text, keyword):
    """检查关键词前是否有否定词（v22.3修复）

    Args:
        text: 用户输入文本
        keyword: 要检查的关键词

    Returns:
        bool: 如果关键词前有否定词返回True
    """
    import re
    # 否定词列表（中英文）
    negation_words = ['不', '没', '别', '非', '未', '无', 'no', 'not', "don't", "doesn't", "didn't"]

    # 在文本中查找关键词的所有出现位置
    pattern = re.escape(keyword)
    for match in re.finditer(pattern, text, re.IGNORECASE):
        keyword_start = match.start()
        # 检查关键词前2个字符内是否有否定词
        prefix_text = text[max(0, keyword_start-3):keyword_start]
        for neg_word in negation_words:
            if neg_word in prefix_text:
                return True
    return False

def match_keyword_safely(text, keywords):
    """安全地匹配关键词（v23.2：词边界+否定词+转折词检测）

    Args:
        text: 用户输入文本
        keywords: 关键词列表

    Returns:
        bool: 如果匹配到关键词且无否定前缀和转折词返回True

    v23.2新增：转折词检测，防止"正常了，但是有问题"被误判为成功
    """
    import re
    text_lower = text.lower().strip()

    # 【v23.2新增】转折词列表
    CONJUNCTIONS = ['但是', '但', '不过', '然而', '可是', '可', '只是', '就是',
                   'but', 'however', 'though', 'yet', 'although']

    for kw in keywords:
        # 使用词边界匹配（避免"不同意"匹配到"同意"）
        # \b在中文环境下不可靠，改用前后字符检测
        kw_lower = kw.lower()

        # 方案1：直接检查是否包含且无否定前缀
        if kw_lower in text_lower:
            # 检查是否有否定前缀
            if has_negation_prefix(text_lower, kw_lower):
                continue

            # 【v23.2新增】检查转折词：如果关键词后面有转折词，不视为明确成功
            kw_pos = text_lower.find(kw_lower)
            text_after = text_lower[kw_pos + len(kw_lower):]

            # 如果关键词后50字符内有转折词，说明有转折，不算明确成功
            has_conjunction = False
            for conj in CONJUNCTIONS:
                if conj in text_after[:50]:
                    has_conjunction = True
                    break

            if has_conjunction:
                continue  # 有转折，跳过这个关键词，继续检查其他关键词

            return True  # 无否定前缀、无转折词，算明确匹配

    return False




def _validate_task_meta_structure(meta):
    """【v24.1新增】验证task-meta数据结构的完整性

    Args:
        meta: task-meta数据字典

    Returns:
        bool: 如果结构有效返回True，否则返回False
    """
    if not isinstance(meta, dict):
        return False

    # 检查必需的顶层字段
    required_keys = ['task_id', 'task_type', 'current_step', 'steps', 'metrics']
    for key in required_keys:
        if key not in meta:
            sys.stderr.write(u"[ERROR] 数据结构验证失败: 缺少必需字段 '{}'\n".format(key))
            return False

    # 检查是否是状态转移结果对象（错误的结构）
    if 'occurred' in meta and 'new_step' in meta and 'old_step' in meta:
        sys.stderr.write(u"[CRITICAL] 检测到状态转移结果对象被错误保存为task-meta！\n")
        sys.stderr.write(u"[CRITICAL] 这是一个BUG，数据已损坏\n")
        return False

    return True


def handle_state_transition(user_input, cwd, session_id=None):
    """处理用户状态转移（v25.0重构：使用StateTransitionCoordinator）

    v25.0重构架构：
    - 优先使用StateTransitionCoordinator（模块化架构）
    - 降级使用handle_state_transition_legacy（向后兼容）

    Args:
        user_input: 用户输入
        cwd: 工作目录
        session_id: 会话ID（v3.1+需要）

    Returns:
        dict: 状态转移结果
            {
                'hookSpecificOutput': {
                    'hookEventName': 'UserPromptSubmit',
                    'additionalContext': str  # 用户消息
                },
                'continue': bool  # 是否继续执行
            }
        或 None（未检测到状态转移）
    """
    # 前置检查
    if not TaskMetaManager:
        return None

    if not session_id:
        # 无session_id，无法处理
        return None

    # v25.0: 优先使用StateTransitionCoordinator
    if STATE_TRANSITION_COORDINATOR_AVAILABLE and STATE_MACHINE_COORDINATOR_AVAILABLE:
        try:
            sys.stderr.write(u"[INFO v25.0] 使用StateTransitionCoordinator处理状态转移\n")

            # 实例化状态转移协调器
            coordinator = StateTransitionCoordinator(cwd, session_id)

            # 调用统一反馈处理方法
            result = coordinator.handle_user_feedback(user_input)

            if result:
                # StateTransitionCoordinator返回格式：
                # {'continue': bool, 'additionalContext': str}
                # 需要转换为UserPromptSubmit格式
                sys.stderr.write(u"[INFO v25.0] StateTransitionCoordinator处理成功\n")

                # 🔥 v27.2修复：确保systemMessage传递给用户（用户可见）
                # 关键：systemMessage字段是用户能看到仪表盘和详细消息的唯一途径
                if not result.get('continue', True):
                    # 阻止状态转移
                    return {
                        "decision": "block",
                        "reason": "状态转移被阻止",
                        "systemMessage": result.get('systemMessage', ''),  # ✅ 添加：用户可见（显示仪表盘和详细原因）
                        "hookSpecificOutput": {
                            "hookEventName": "UserPromptSubmit",
                            "additionalContext": result.get('systemMessage', '') or result.get('additionalContext', '')  # ✅ 保持：Claude上下文注入
                        }
                    }
                else:
                    # 允许继续
                    return {
                        "systemMessage": result.get('systemMessage', ''),  # ✅ 添加：用户可见（显示仪表盘和状态转移消息）
                        "hookSpecificOutput": {
                            "hookEventName": "UserPromptSubmit",
                            "additionalContext": result.get('systemMessage', '') or result.get('additionalContext', '')  # ✅ 保持：Claude上下文注入
                        }
                    }
            else:
                # 未检测到状态转移
                sys.stderr.write(u"[DEBUG v25.0] StateTransitionCoordinator未检测到状态转移\n")
                return None

        except Exception as e:
            sys.stderr.write(u"[ERROR v25.0] StateTransitionCoordinator异常，降级到旧版实现: {}\n".format(e))
            import traceback
            traceback.print_exc(file=sys.stderr)
            # 降级到旧版实现
            pass  # 继续执行下面的降级逻辑

    # v25.0降级方案：StateTransitionCoordinator不可用时返回None
    sys.stderr.write(u"[ERROR v25.0] StateTransitionCoordinator不可用，无法处理状态转移\n")
    sys.stderr.write(u"[ERROR v25.0] 请检查以下模块是否正确安装：\n")
    sys.stderr.write(u"  - core/state_machine_coordinator.py\n")
    sys.stderr.write(u"  - orchestrator/state_transition_coordinator.py\n")
    sys.stderr.write(u"  - orchestrator/llm_intent_analyzer.py\n")
    return None



def generate_task_boundary_notice(task_id, task_desc, task_type):
    """v20.2.17: 生成任务边界说明（防止AI混淆Git历史和任务迭代历史）"""

    task_type_map = {
        "bug_fix": u"🐛 BUG修复",
        "feature_implementation": u"✨ 功能实现",
        "general": u"📝 通用任务"
    }

    task_type_display = task_type_map.get(task_type, u"📝 通用任务")

    return u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 任务边界声明 (v20.2.17)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**这是一个全新的任务**:
- 任务ID: `{task_id}`
- 任务类型: {task_type_display}
- 描述: {task_desc}
- 创建时间: {created_time}
- 当前迭代次数: 0（新任务）

**重要提示**:
1. **Git提交历史 ≠ 本任务的迭代历史**
   - Git历史中的提交可能属于其他任务（已归档或已删除）
   - 即使提交消息相似，也不代表是同一个任务
   - 不要说"看到已有X轮修复"或"这是第X次修复"

2. **迭代计数以 .task-meta.json 为准**
   - 当前迭代次数: 0（新任务）
   - 不要基于Git log计算修复轮数

3. **如果需要参考历史实现**
   - 可以查看Git历史代码作为技术参考
   - 但不应将其理解为"上一次失败的修复"
   - 这是一个全新的开始

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(
        task_id=task_id,
        task_type_display=task_type_display,
        task_desc=task_desc,
        created_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

def extract_slash_command_info(prompt):
    """
    提取SlashCommand展开后的信息 (v3.2修复)

    支持两种格式：
    1. XML标记格式（SlashCommand展开后）：
       <command-name>/mc</command-name>
       <command-args>任务描述</command-args>

    2. 传统格式（直接输入）：
       /mc 任务描述

    Args:
        prompt: Hook接收到的prompt字段

    Returns:
        {
            "is_mc_command": bool,
            "command_args": str or None,
            "format": "xml" | "plain" | "none"
        }
    """
    import re

    # 格式1：检测XML标记（SlashCommand展开后的格式）
    command_name_match = re.search(r'<command-name>(/mc)</command-name>', prompt)

    if command_name_match:
        # 提取 <command-args>...</command-args>
        args_match = re.search(r'<command-args>([^<]+)</command-args>', prompt)

        if args_match:
            return {
                "is_mc_command": True,
                "command_args": args_match.group(1).strip(),
                "format": "xml"
            }
        else:
            # /mc cancel 或无参数情况
            return {
                "is_mc_command": True,
                "command_args": "",
                "format": "xml"
            }

    # 格式2：传统格式检测（直接输入 /mc <任务描述>）
    if prompt.strip().startswith('/mc '):
        return {
            "is_mc_command": True,
            "command_args": prompt.replace('/mc ', '').strip(),
            "format": "plain"
        }

    # 格式3：仅 /mc（无空格）
    if prompt.strip() == '/mc':
        return {
            "is_mc_command": True,
            "command_args": "",
            "format": "plain"
        }

    # 非 /mc 命令
    return {
        "is_mc_command": False,
        "command_args": None,
        "format": "none"
    }

def main():
    """主入口（v3.1增强：会话隔离支持；v3.2修复：SlashCommand格式识别）"""
    try:
        # 读取stdin输入
        data = json.load(sys.stdin)

        prompt = data.get('prompt', '')
        cwd = os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd())
        session_id = data.get('session_id')  # v3.1新增：获取session_id

        if not session_id:
            # 缺少session_id（不应该发生），放行
            sys.stderr.write("[ERROR] UserPromptSubmit缺少session_id\n")
            output = {"continue": True}
            print(json.dumps(output, ensure_ascii=False))
            sys.exit(0)

        # === v3.2: SlashCommand格式解析 ===
        cmd_info = extract_slash_command_info(prompt)

        # Debug日志：命令解析结果
        sys.stderr.write(u"[DEBUG v3.2] 命令检测: is_mc={}, format={}, args={}\n".format(
            cmd_info['is_mc_command'],
            cmd_info['format'],
            cmd_info['command_args'][:40] if cmd_info['command_args'] else 'None'
        ))

        # === v3.1: /mc cancel 检测 ===
        if cmd_info['is_mc_command'] and cmd_info['command_args'].strip() == 'cancel':
            sys.stderr.write(u"[INFO v3.1] 检测到取消命令\n")

            # 解除当前会话的绑定
            if TaskMetaManager:
                mgr = TaskMetaManager(cwd)
                if mgr.unbind_task_from_session(session_id):
                    cancel_message = u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 工作流已解除
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

当前会话的工作流绑定已清除。

**下一步**:
- 你可以正常使用所有工具，不受工作流限制
- 如需重新启动工作流，使用 `/mc <任务描述>`
- 如需恢复已有任务，使用 `/mc <任务路径>`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
                    output = {
                        "hookSpecificOutput": {
                            "hookEventName": "UserPromptSubmit",
                            "additionalContext": cancel_message
                        },
                        "continue": True
                    }
                    print(json.dumps(output, ensure_ascii=False))

                    # VSCode通知
                    try:
                        notify_info(u"✅ 工作流已解除", u"当前会话不再受工作流限制")
                    except:
                        pass

                    sys.exit(0)
                else:
                    # 解除失败（可能本来就没绑定）
                    output = {
                        "hookSpecificOutput": {
                            "hookEventName": "UserPromptSubmit",
                            "additionalContext": u"⚠️ 当前会话没有绑定任务"
                        },
                        "continue": True
                    }
                    print(json.dumps(output, ensure_ascii=False))
                    sys.exit(0)
            else:
                # TaskMetaManager不可用
                sys.stderr.write(u"[ERROR] TaskMetaManager不可用\n")
                output = {"continue": True}
                print(json.dumps(output, ensure_ascii=False))
                sys.exit(0)

        # === v28.0: 为非/mc命令生成仪表盘 ===
        dashboard_for_normal_msg = None
        if not cmd_info['is_mc_command'] and TaskMetaManager:
            try:
                mgr = TaskMetaManager(cwd)
                task_info = mgr.get_active_task_by_session(session_id)

                if task_info:
                    task_id = task_info.get('task_id')
                    task_meta = mgr.load_task_meta(task_id)

                    if task_meta:
                        from utils.dashboard_generator import generate_context_dashboard
                        dashboard_for_normal_msg = generate_context_dashboard(task_meta)
            except Exception as e:
                sys.stderr.write(u"[WARN v28.0] 仪表盘生成失败: {}\n".format(e))

        # === v3.2: 检测是否是 /mc 命令 ===
        if not cmd_info['is_mc_command']:
            # 非 /mc 命令，先检查是否是状态转移关键词（v3.0 Final新增）
            # 注意：状态转移检测仍然使用原始prompt（因为用户可能直接输入"同意"、"修复了"等）
            state_transition_result = handle_state_transition(prompt, cwd, session_id)

            if state_transition_result:
                # 🔥 P1-3修复：StateTransitionCoordinator的结果已包含仪表盘，不需要重复拼接
                # StateTransitionCoordinator在_transition_*方法中已经调用generate_context_dashboard()
                # 并将仪表盘包含在systemMessage中（参见state_transition_coordinator.py:188-201）
                print(json.dumps(state_transition_result, ensure_ascii=False))
                sys.exit(0)
            else:
                # === v28.0: 非状态转移命令，添加仪表盘后放行 ===
                output = {"continue": True}
                if dashboard_for_normal_msg:
                    output['systemMessage'] = dashboard_for_normal_msg
                print(json.dumps(output, ensure_ascii=False))
                sys.exit(0)

        # === v20.3.1: 任务取消/失败检测 ===
        # v3.2修复：使用提取的command_args而非原始prompt
        cancellation_message = handle_cancellation_from_user_prompt(cmd_info['command_args'], cwd)

        if cancellation_message:
            # 输出取消确认消息
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": cancellation_message
                },
                "continue": False,  # 阻止继续执行
                "stopReason": "task_cancelled"
            }
            print(json.dumps(output, ensure_ascii=False))

            # VSCode 通知
            try:
                notify_info(u"✅ 任务已取消/标记失败", u"运行时状态已清理")
            except:
                pass

            sys.exit(0)

        # === 【v25.0重构】使用TaskInitializer统一任务初始化 ===
        if TASK_INITIALIZER_AVAILABLE:
            sys.stderr.write(u"[INFO v25.0] 使用TaskInitializer处理/mc命令\n")

            try:
                # 实例化TaskInitializer
                initializer = TaskInitializer(cwd, session_id)

                # 处理/mc命令（包含任务恢复检测和新任务创建）
                result = initializer.handle_mc_command(cmd_info['command_args'])

                # 输出Hook响应
                output = {
                    "hookSpecificOutput": {
                        "hookEventName": "UserPromptSubmit",
                        "additionalContext": result['additionalContext']
                    },
                    "continue": result['continue']
                }

                # 如果有stopReason，添加到输出中
                if 'stopReason' in result:
                    output['stopReason'] = result['stopReason']

                # 如果有systemMessage，添加到输出中
                if 'systemMessage' in result:
                    output['systemMessage'] = result['systemMessage']

                # === v27.9: 任务创建后生成仪表盘 ===
                # 注意：此时任务已经创建并绑定到会话
                if TaskMetaManager and result['continue']:
                    try:
                        mgr = TaskMetaManager(cwd)
                        task_info = mgr.get_active_task_by_session(session_id)

                        if task_info:
                            task_id = task_info.get('task_id')
                            task_meta = mgr.load_task_meta(task_id)

                            if task_meta:
                                from utils.dashboard_generator import generate_context_dashboard
                                dashboard = generate_context_dashboard(task_meta)
                                # 将仪表盘添加到systemMessage
                                output['systemMessage'] = dashboard
                    except Exception as e:
                        # 仪表盘生成失败不应影响主流程
                        sys.stderr.write(u"[WARN v27.9] 仪表盘生成失败: {}\n".format(e))

                print(json.dumps(output, ensure_ascii=False))
                sys.exit(0)

            except Exception as e:
                sys.stderr.write(u"[ERROR] TaskInitializer处理失败: {}\n".format(e))
                import traceback
                traceback.print_exc(file=sys.stderr)

                # 降级：返回错误提示
                output = {
                    "hookSpecificOutput": {
                        "hookEventName": "UserPromptSubmit",
                        "additionalContext": u"❌ 任务初始化失败: {}\n请检查日志".format(str(e))
                    },
                    "continue": False,
                    "stopReason": "task_init_error"
                }
                print(json.dumps(output, ensure_ascii=False))
                sys.exit(0)

        # === 降级：TASK_INITIALIZER不可用 ===
        # v25.0重构后，不再提供完整的降级实现
        # 如果TaskInitializer模块不可用，说明系统配置有问题，应该修复
        sys.stderr.write(u"[ERROR] TaskInitializer模块不可用\n")
        sys.stderr.write(u"[ERROR] 请检查以下文件是否存在：\n")
        sys.stderr.write(u"  - templates/.claude/hooks/orchestrator/task_initializer.py\n")
        sys.stderr.write(u"  - templates/.claude/hooks/orchestrator/keyword_registry.py\n")
        sys.stderr.write(u"  - templates/.claude/hooks/orchestrator/llm_intent_analyzer.py\n")

        output = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ 任务初始化模块不可用 (v25.0)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**问题**: TaskInitializer模块导入失败

**可能原因**:
1. v25.0重构模块未正确安装
2. 文件路径错误或文件缺失
3. Python导入路径配置问题

**解决方案**:
1. 检查以下文件是否存在：
   - `templates/.claude/hooks/orchestrator/task_initializer.py`
   - `templates/.claude/hooks/orchestrator/keyword_registry.py`
   - `templates/.claude/hooks/orchestrator/llm_intent_analyzer.py`

2. 如果文件缺失，请重新运行 `initmc` 命令部署工作流

3. 查看stderr日志获取详细错误信息

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            },
            "continue": False,
            "stopReason": "task_initializer_unavailable"
        }
        print(json.dumps(output, ensure_ascii=False))
        sys.exit(0)

    except Exception as e:
        # [v3.0 Final增强] 详细错误诊断
        sys.stderr.write("=" * 80 + "\n")
        sys.stderr.write(u"[HOOK ERROR] UserPromptSubmit Hook 执行失败\n")
        sys.stderr.write("=" * 80 + "\n")
        sys.stderr.write(u"错误类型: {}\n".format(type(e).__name__))
        sys.stderr.write(u"错误消息: {}\n".format(str(e)))
        sys.stderr.write("\n完整堆栈:\n")
        import traceback
        traceback.print_exc(file=sys.stderr)

        # 输出上下文信息
        sys.stderr.write("\n上下文信息:\n")
        try:
            cwd = os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd())
            sys.stderr.write(u"  cwd: {}\n".format(cwd))
            sys.stderr.write(u"  HOOK_DIR: {}\n".format(HOOK_DIR))
            sys.stderr.write(u"  sys.path[0:3]: {}\n".format(sys.path[:3]))
            sys.stderr.write(u"  TaskMetaManager可用: {}\n".format(TaskMetaManager is not None))

            # 检查活跃任务文件
            active_file = os.path.join(cwd, '.claude', '.task-active.json')
            sys.stderr.write(u"  .task-active.json存在: {}\n".format(os.path.exists(active_file)))
            if os.path.exists(active_file):
                sys.stderr.write(u"  .task-active.json大小: {} bytes\n".format(os.path.getsize(active_file)))
        except Exception as ctx_err:
            sys.stderr.write(u"  (上下文信息收集失败: {})\n".format(ctx_err))

        sys.stderr.write("=" * 80 + "\n")

        # v2.0: 错误回滚 - 清理不完整的状态文件
        try:
            cwd = os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd())
            active_file = os.path.join(cwd, '.claude', '.task-active.json')

            # 删除损坏的活跃任务标记文件
            if os.path.exists(active_file):
                # 检查文件是否完整
                try:
                    with open(active_file, 'r', encoding='utf-8') as fp:
                        json.load(fp)
                except (json.JSONDecodeError, ValueError):
                    sys.stderr.write(u"[ROLLBACK] 删除损坏的状态文件: {}\n".format(active_file))
                    os.remove(active_file)
        except Exception as rollback_err:
            sys.stderr.write(u"[WARN] 回滚清理失败: {}\n".format(rollback_err))

        # 降级：允许继续执行（避免完全阻塞工作流）
        output = {"continue": True}
        print(json.dumps(output, ensure_ascii=False))
        sys.exit(1)  # 非阻塞错误

if __name__ == '__main__':
    main()
