#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified PreToolUse Enforcer - 统一PreToolUse强制器
Version: v2.0

职责:
1. 拦截所有工具调用(Read/Write/Edit/Bash/Task/Grep/Glob/WebFetch/WebSearch)
2. 执行四层验证(阶段-工具-路径-语义)
3. 违规立即DENY,零容忍
4. 放行后允许工具执行

核心变更(v2.0):
- 使用 TaskMetaManager 替代 StateManager
- 从 task-meta.json 加载状态(唯一数据源)
- 所有 workflow_state 引用改为 task_meta
"""

import sys
import json
import os
import io
from datetime import datetime

# Windows UTF-8编码修复（防止中文乱码）
if sys.platform == 'win32':
    # 🔥 v22.3.8修复：添加stdin的UTF-8编码设置（解决Task工具JSON解析失败问题）
    # 参考：https://code.claude.com/docs/en/hooks (Windows中文处理)
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
    # 强制stdout/stderr使用UTF-8编码
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# DEBUG模式控制（设置环境变量CLAUDE_HOOK_DEBUG=1启用调试日志）
DEBUG = os.getenv("CLAUDE_HOOK_DEBUG", "0") == "1"

# 🔥 v22.3.2: 文件日志功能（用于诊断Task标记注入）
DEBUG_LOG_FILE = os.path.join(os.getcwd(), 'pretooluse-debug.log')

def log_to_file(message):
    """写入诊断日志到文件（v22.3.2）"""
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        # 处理Windows路径中的Unicode代理字符
        with open(DEBUG_LOG_FILE, 'a', encoding='utf-8', errors='replace') as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception as e:
        # 如果仍然失败,尝试写入错误信息
        try:
            with open(DEBUG_LOG_FILE, 'a', encoding='utf-8', errors='replace') as f:
                f.write(f"[{timestamp}] [LOG_ERROR] {str(e)}\n")
        except:
            pass  # 完全失败则忽略

# 添加core模块到sys.path
HOOK_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_HOOK_DIR = os.path.dirname(HOOK_DIR)
sys.path.insert(0, PARENT_HOOK_DIR)

try:
    from core.stage_validator import StageValidator
    from core.task_meta_manager import TaskMetaManager
except ImportError as e:
    sys.stderr.write(f"[ERROR] 无法导入core模块: {e}\n")
    sys.stderr.write(f"[ERROR] PARENT_HOOK_DIR={PARENT_HOOK_DIR}, sys.path={sys.path}\n")
    # 兜底:允许继续(避免完全阻塞工作流)
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": f"核心模块加载失败,默认放行: {e}"
        },
        "suppressOutput": False
    }, ensure_ascii=False))
    sys.exit(0)


def main():
    """主入口（v3.0 Final增强错误诊断）"""
    try:
        # 1. 解析输入
        try:
            event_data = json.loads(sys.stdin.read())
        except json.JSONDecodeError as e:
            sys.stderr.write(f"[ERROR] JSON解析失败: {e}\n")
            allow_and_exit("JSON解析失败,默认放行")
            return

        tool_name = event_data.get("tool_name", "")
        tool_input = event_data.get("tool_input", {})

        # 🔥 v22.3.4: Task工具强制日志（不依赖DEBUG模式）
        if tool_name == 'Task':
            session_id = event_data.get("session_id", "N/A")
            log_to_file(f"========== TASK工具调用检测 ==========")
            log_to_file(f"timestamp: {datetime.now()}")
            log_to_file(f"session_id: {session_id}")
            log_to_file(f"tool_input keys: {list(tool_input.keys())}")
            log_to_file(f"description: {tool_input.get('description', 'N/A')}")
            log_to_file(f"subagent_type: {tool_input.get('subagent_type', 'N/A')}")
            log_to_file(f"prompt length: {len(tool_input.get('prompt', ''))}")

        # ✅ Phase 1: 诊断日志 - 记录原始工具名（仅DEBUG模式）
        if DEBUG:
            sys.stderr.write(f"[PreToolUse] 接收到工具调用: {tool_name}\n")
            sys.stderr.write(f"[PreToolUse] 工具参数: {json.dumps(tool_input, ensure_ascii=False)[:200]}...\n")

        # 2. 获取工作目录
        cwd = os.getcwd()

        # 3. 初始化 TaskMetaManager
        mgr = TaskMetaManager(cwd)

        # 4. 获取当前会话ID（v3.1: 会话隔离）
        session_id = event_data.get('session_id')
        if not session_id:
            # 缺少session_id，降级到旧逻辑
            sys.stderr.write("[WARN] PreToolUse缺少session_id，降级到全局模式\n")
            task_id = mgr.get_active_task_id()
            if not task_id:
                allow_and_exit("无活跃任务,默认放行", suppress=True)
                return
            # 加载任务元数据
            task_meta = mgr.load_task_meta(task_id)
            if not task_meta:
                allow_and_exit("任务元数据不存在,默认放行", suppress=True)
                return
            current_step = task_meta.get('current_step', 'implementation')
        else:
            # 5. 根据session_id获取绑定任务（v3.1: 核心改动）
            task_binding = mgr.get_active_task_by_session(session_id)

            # 🔥 v22.3.4: Task工具特殊诊断
            if tool_name == 'Task':
                log_to_file(f"session绑定查找结果: {task_binding}")
                if not task_binding:
                    log_to_file(f"❌ 未找到session绑定！将提前退出，不执行标记注入")
                    log_to_file(f"session_id: {session_id}")
                    log_to_file(f"检查.task-active.json是否包含此session_id")

            if not task_binding:
                # 当前会话无绑定任务，放行所有工具
                allow_and_exit("当前会话无绑定任务,默认放行", suppress=True)
                return

            # 6. 提取任务ID
            task_id = task_binding['task_id']

            # 7. 从唯一数据源（task-meta.json）加载任务状态
            # 🔥 v25.2修复：遵循单一数据源原则，current_step必须从task-meta.json读取
            # 问题根因：之前从.task-active.json缓存读取current_step，导致状态转移后读取到过期缓存
            # 解决方案：直接从task-meta.json（唯一真实数据源）读取current_step
            task_meta = mgr.load_task_meta(task_id)
            if not task_meta:
                allow_and_exit("任务元数据不存在,默认放行", suppress=True)
                return

            # 8. 从唯一数据源读取当前阶段
            current_step = task_meta.get('current_step', 'implementation')

        # ✅ Phase 1: 诊断日志 - 记录任务状态（仅DEBUG模式）
        if DEBUG:
            sys.stderr.write(f"[PreToolUse] 任务ID: {task_id}\n")
            sys.stderr.write(f"[PreToolUse] 当前阶段: {current_step}\n")

        # 🔥 v22.2新增：Task工具标记注入（强制性Hook）
        # 用于确保专家审查子代理输出包含SUBAGENT_RESULT标记
        # 🔥 v22.3.2: 添加文件日志诊断
        log_to_file("=" * 80)
        log_to_file("PreToolUse Hook v22.3.2 - Task标记注入检查")
        log_to_file(f"tool_name={tool_name}")
        log_to_file(f"current_step={current_step}")
        log_to_file(f"task_type={task_meta.get('task_type')}")

        if DEBUG:
            sys.stderr.write(f"[PreToolUse v22.2] 检查Task注入条件:\n")
            sys.stderr.write(f"  tool_name={tool_name}\n")
            sys.stderr.write(f"  current_step={current_step}\n")
            sys.stderr.write(f"  task_type={task_meta.get('task_type')}\n")

        # v27.0新增：澄清需求检测函数
        def is_clarification_request(tool_input):
            """
            检测TodoWrite是否为澄清需求而非展示方案 (v27.0新增)

            澄清特征:
            1. description包含疑问词：如何、什么、哪里、为什么、是否、请问
            2. todos列表为空或很少（<3个）
            3. 没有明确的"实施步骤"、"修复方案"关键词

            展示方案特征:
            1. todos包含具体实施步骤（≥3个）
            2. description包含"修复方案"、"实施步骤"、"请确认"

            Args:
                tool_input: TodoWrite工具的输入参数

            Returns:
                bool: True=澄清需求（放行），False=展示方案（阻止）
            """
            description = tool_input.get('description', '')
            todos = tool_input.get('todos', [])

            # 疑问词列表
            QUESTION_WORDS = [u'如何', u'什么', u'哪里', u'为什么', u'是否', u'请问', u'能否', u'可否', u'？', u'?']

            # 方案确认关键词（展示方案的强特征）
            CONFIRMATION_WORDS = [u'请确认', u'是否同意', u'是否可以', u'确认方案', u'同意上述方案', u'是否认同']

            # 检查1: 是否包含疑问词
            has_question = any(word in description for word in QUESTION_WORDS)

            # 检查2: 是否包含确认请求（展示方案的强信号）
            has_confirmation = any(word in description for word in CONFIRMATION_WORDS)

            # 检查3: todos数量（澄清需求通常todos很少或为空）
            few_todos = len(todos) < 3

            # 检查4: description是否包含"修复方案"、"实施步骤"等方案关键词
            PLAN_KEYWORDS = [u'修复方案', u'实施步骤', u'执行计划', u'下一步操作']
            has_plan = any(word in description for word in PLAN_KEYWORDS)

            # 判断逻辑:
            # 1. 有疑问词 且 无确认请求 且 todos很少 且 无方案关键词 → 澄清需求
            # 2. 有确认请求 或 有方案关键词 或 todos≥3 → 展示方案

            if has_confirmation or has_plan:
                return False  # 明确是展示方案

            if has_question and few_todos:
                return True  # 可能是澄清需求

            return False  # 默认不放行

        # 🔥 v26.1新增：Planning阶段TodoWrite拦截（强制专家审查）
        if tool_name == 'TodoWrite' and current_step == 'planning' and task_meta.get('task_type') == 'bug_fix':
            planning = task_meta.get('steps', {}).get('planning', {})
            expert_review_required = planning.get('expert_review_required', False)
            expert_review_completed = planning.get('expert_review_completed', False)

            # 如果需要专家审查但未完成，阻止TodoWrite
            if expert_review_required and not expert_review_completed:
                # ✅ v27.3修复：Planning阶段一律禁止TodoWrite，不允许任何例外
                # 删除is_clarification_request检测（判断逻辑不可靠，AI可轻易绕过）

                # 原因：
                # 1. AI可能在TodoWrite中夹带方案展示（如"我制定了方案XXX。但有个问题：你期望的行为是什么？"）
                # 2. 澄清需求应通过普通对话实现，不需要TodoWrite工具
                # 3. TodoWrite的主要作用是展示任务列表，Planning阶段不应使用

                log_to_file("v27.3 TodoWrite拦截: Planning阶段一律禁止TodoWrite（无例外）")

                # 展示方案，阻止
                warning_message = u"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ PreToolUse Hook - TodoWrite被阻止
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**检测到的问题**:
- 当前阶段: Planning（BUG修复任务）
- 专家审查状态: ❌ 未完成
- 尝试操作: 使用TodoWrite

**为什么阻止你**:
BUG修复任务在Planning阶段必须先完成专家审查，
然后才能使用TodoWrite向用户展示方案。

**如果你想澄清需求**:
- ✅ 直接在回复中提问，不需要使用TodoWrite
- ✅ 例如："请问你期望的XXX行为是什么？"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ **正确流程**:

1. 分析代码并制定修复方案
2. **立即使用Task工具启动专家审查**:
   Task(
     subagent_type="general-purpose",
     description="BUG修复方案专家审查",
     prompt="请审查以下BUG修复方案：..."
   )
3. 等待审查结果并调整方案（如需要）
4. 然后才能使用TodoWrite向用户确认

⚠️ **强制要求**: 不可跳过专家审查！

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
                sys.stderr.write(warning_message)
                log_to_file("v26.1 TodoWrite拦截: Planning阶段未完成专家审查")

                # 返回JSON格式的拒绝决策
                print(json.dumps({
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": "Planning阶段必须先完成专家审查才能使用TodoWrite"
                    },
                    "systemMessage": warning_message,
                    "suppressOutput": False
                }, ensure_ascii=False))
                sys.exit(0)

        if tool_name == 'Task' and current_step == 'planning' and task_meta.get('task_type') == 'bug_fix':
            # 🔥 v26.0新增：检查本轮是否已完成专家审查（防止重复审查）
            planning = task_meta.get('steps', {}).get('planning', {})
            expert_review_completed = planning.get('expert_review_completed', False)
            planning_round = planning.get('planning_round', 1)

            log_to_file(f"v26.0重复审查检查: expert_review_completed={expert_review_completed}, planning_round={planning_round}")

            # ✅ 如果本轮已完成审查，阻止重复审查
            if expert_review_completed:
                log_to_file("❌ 本轮planning已执行过专家审查，阻止重复审查")

                deny_message = f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ PreToolUse Hook - 阻止重复专家审查
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**检测到的问题**:
- 当前阶段: Planning（第{planning_round}轮）
- 本轮专家审查状态: ✅ 已完成
- 尝试操作: 再次启动专家审查

**为什么阻止你**:
v26.0单次审查模式规定，每轮Planning阶段只允许执行1次专家审查，
以避免上下文浪费和过度修复问题。

**专家审查历史**:
- 总审查次数: {planning.get('expert_review_count', 0)}次
- 本轮审查结果: {planning.get('expert_review_result', '未知')}
- 最近审查时间: {planning.get('last_expert_review', {}).get('timestamp', '未知')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ **正确流程**:

1. 根据专家建议调整修复方案（无需重新审查）
2. 向用户展示调整后的方案
3. 等待用户确认后进入Implementation阶段

💡 **提示**:
- 专家建议仅供参考，无需强制执行
- 如认为建议不适用，可直接向用户确认方案
- 如需再次审查，可在Implementation后返回Planning时执行

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
                sys.stderr.write(deny_message)
                log_to_file("决策: 阻止重复审查，exit(2)")
                sys.exit(2)  # 阻止工具调用

            # 本轮未审查，继续检查是否为专家审查任务
            description = tool_input.get('description', '')
            subagent_type = tool_input.get('subagent_type', '')
            prompt = tool_input.get('prompt', '')

            # 🔥 v22.3.5: 详细的诊断日志
            log_to_file(f"✓ Task条件匹配！本轮未审查，继续处理")
            log_to_file(f"  description: {description[:50]}...")
            log_to_file(f"  subagent_type: {subagent_type}")
            log_to_file(f"  prompt length: {len(prompt)}")

            if DEBUG:
                sys.stderr.write(f"[PreToolUse v26.0] Task条件匹配！本轮未审查\n")
                sys.stderr.write(f"  subagent_type={subagent_type}\n")

            # 🔥 v22.3.5: 多维度判断专家审查任务（不依赖description编码）
            # 原因：description字段在Claude Code内部处理时可能包含Unicode代理字符
            #       导致关键词匹配失败，改用更可靠的字段组合

            review_keywords = ['审查', 'review', '评审', '检查', '验证', 'verify']
            is_review_task = False

            # 方法1: 检查subagent_type（ASCII字符串，最可靠）
            if subagent_type == 'general-purpose':
                log_to_file(f"✓ subagent_type匹配 (general-purpose)")

                # 方法2: 在prompt中查找关键词（double check）
                # prompt字段更长，即使部分损坏也能匹配
                prompt_lower = prompt.lower()
                matched_keywords = [kw for kw in review_keywords if kw in prompt_lower]

                if matched_keywords:
                    is_review_task = True
                    log_to_file(f"✓ prompt中找到关键词: {matched_keywords}")
                else:
                    # 如果prompt关键词也找不到，尝试字节匹配（终极fallback）
                    try:
                        prompt_bytes = prompt.encode('utf-8', errors='replace')
                        for kw in review_keywords:
                            kw_bytes = kw.encode('utf-8', errors='replace')
                            if kw_bytes in prompt_bytes:
                                is_review_task = True
                                log_to_file(f"✓ prompt字节匹配成功: {kw}")
                                break
                    except Exception as e:
                        log_to_file(f"⚠️ prompt字节匹配异常: {e}")

                    if not is_review_task:
                        log_to_file(f"⚠️ prompt中未找到审查关键词，但subagent_type匹配")
                        log_to_file(f"  prompt前200字符: {prompt[:200]}")

                        # 🔥 v22.3.6: 默认策略（最终兜底）
                        # 条件：bug_fix + planning + Task(general-purpose) → 极大概率是专家审查
                        log_to_file(f"✓ 应用默认策略: bug_fix + planning + general-purpose → 专家审查")
                        is_review_task = True
            else:
                log_to_file(f"✗ subagent_type不匹配: {subagent_type}")

            log_to_file(f"最终判定: is_review_task={is_review_task}")

            if is_review_task:
                log_to_file("✓✓ 检测到专家审查任务，开始注入SUBAGENT_RESULT标记")
                sys.stderr.write("[INFO v22.2] 检测到专家审查任务，强制注入SUBAGENT_RESULT标记要求\n")

                # 获取原始prompt
                original_prompt = tool_input.get('prompt', '')
                log_to_file(f"原始prompt长度: {len(original_prompt)}")
                log_to_file(f"原始prompt前200字符: {original_prompt[:200]}")

                # 构建标记要求指令
                marker_instruction = """

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 系统要求（必须遵守）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

在你的回复末尾**必须**包含以下JSON标记（用于系统自动解析审查结果）：

<!-- SUBAGENT_RESULT
{
  "approved": true,  // 或false（审查是否通过）
  "issues": ["问题1", "问题2"],  // 发现的问题列表（如果有）
  "suggestions": ["建议1", "建议2"]  // 改进建议列表（如果有）
}
-->

**重要说明**：
- approved: 如果方案可以实施，设置为true；如果需要调整，设置为false
- issues: 列出所有发现的技术问题或CRITICAL规范违规
- suggestions: 列出具体的改进建议

**示例（审查通过）**：
<!-- SUBAGENT_RESULT {"approved": true, "issues": [], "suggestions": ["建议添加边界检查"]} -->

**示例（审查不通过）**：
<!-- SUBAGENT_RESULT {"approved": false, "issues": ["缺少空值检查"], "suggestions": ["在第42行添加if item is None判断"]} -->

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

                # 注入标记要求到prompt末尾
                updated_prompt = original_prompt + marker_instruction
                log_to_file(f"注入后prompt长度: {len(updated_prompt)}")
                log_to_file(f"标记指令已添加到prompt末尾")

                # 🔥 v22.3.7: 保留所有原始参数，只修改prompt
                # BUG修复: 之前只传递了prompt，导致subagent_type等参数丢失
                # 参考官方文档: https://docs.claude.com/en/docs/claude-code/hooks
                updated_tool_input = tool_input.copy()  # 复制所有原始参数
                updated_tool_input['prompt'] = updated_prompt  # 只修改prompt字段

                # 增强诊断日志（v22.3.7）
                log_to_file(f"原始tool_input keys: {list(tool_input.keys())}")
                log_to_file(f"updatedInput keys: {list(updated_tool_input.keys())}")
                log_to_file(f"updatedInput.subagent_type: {updated_tool_input.get('subagent_type')}")
                log_to_file(f"updatedInput.description: {updated_tool_input.get('description')[:50] if updated_tool_input.get('description') else 'N/A'}...")

                output = {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "allow",
                        "permissionDecisionReason": "专家审查任务，已注入标记要求",
                        "updatedInput": updated_tool_input  # ✅ 保留所有参数！
                    },
                    "suppressOutput": True  # 不显示给用户（透明操作）
                }

                log_to_file(f"准备输出updatedInput")
                log_to_file(f"updatedInput.prompt长度: {len(output['hookSpecificOutput']['updatedInput']['prompt'])}")
                log_to_file(f"Hook输出: permissionDecision=allow, suppressOutput=True")

                print(json.dumps(output, ensure_ascii=False))
                sys.stderr.write("[INFO v22.2] Task工具prompt已修改，标记要求已注入\n")
                log_to_file("✓✓✓ 标记注入完成,Hook已退出")
                log_to_file("=" * 80)
                sys.exit(0)  # 放行并退出

        # 🔥 v23.0新增: Finalization倒计时机制（100%启动Task子代理保障）
        if current_step == 'finalization' and tool_name != 'Task':
            # 检查是否在子代理上下文中
            is_subagent = mgr.check_subagent_lock(task_id) if task_id else False

            if not is_subagent:
                # 父代理在finalization阶段，统计非Task工具调用次数
                metrics = task_meta.get('metrics', {})
                tools_used = metrics.get('tools_used', [])

                # 统计finalization阶段的非Task工具调用
                finalization_started_at = task_meta.get('steps', {}).get('finalization', {}).get('started_at')
                non_task_tool_count = 0

                if finalization_started_at:
                    # 统计finalization开始后的非Task工具调用
                    for tool_record in tools_used:
                        tool_timestamp = tool_record.get('timestamp', '')
                        tool_used = tool_record.get('tool', '')
                        if tool_timestamp >= finalization_started_at and tool_used != 'Task':
                            non_task_tool_count += 1

                # 包含当前工具
                non_task_tool_count += 1

                if non_task_tool_count >= 5:
                    # 超过5次非Task调用，强制阻止
                    sys.stderr.write(f"[PreToolUse v23.0] Finalization倒计时触发: {non_task_tool_count}次非Task调用\n")

                    deny_message = u"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚨 PreToolUse Hook 强制阻止 - 必须启动收尾子代理
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**检测到的问题**:
- 当前阶段: Finalization (收尾归档)
- 已使用{}次非Task工具 (Read/Grep/Glob)
- 但仍未启动收尾子代理

**为什么阻止你**:
Finalization阶段的收尾工作(文档更新、任务归档)
**必须由子代理执行**，以确保隔离性和可追溯性。

你已使用{}次分析工具，这已经足够了解任务状态。
现在**必须立即启动Task工具**。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚡ **你必须立即执行（这是强制要求）**:

Task(
  subagent_type="general-purpose",
  description="任务收尾归档",
  prompt='''
请完成以下收尾工作:

1. 读取 .task-meta.json 获取完整任务历史:
   - 分析 state_transitions (所有状态转移)
   - 分析 steps.planning.iterations (所有Planning迭代)
   - 分析 steps.implementation.iterations (所有Implementation迭代)

2. 生成 context.md (任务上下文文档):
   - 任务概述
   - 执行历程(每次迭代的详情)
   - 关键决策点
   - 完整时间线

3. 生成 solution.md (最终解决方案):
   - 问题描述
   - 最终方案
   - 实施细节
   - 测试验证
   - 经验总结

4. 更新 .task-meta.json:
   - 设置 finalization.status = 'completed'
   - 设置 finalization.completed_at
   - 设置 archived = true
   - 设置 session_ended_at

5. 输出结果标记:
<!-- SUBAGENT_RESULT {{"completed": true, "documents_generated": ["context.md", "solution.md"], "meta_updated": true}} -->
'''
)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ **禁止的操作**:
- 不允许继续使用Read/Grep/Glob工具
- 不允许直接Write/Edit文档(必须通过子代理)
- 不允许尝试"绕过"这个要求

✅ **允许的操作**:
- Task工具（启动收尾子代理）← 唯一选择

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 **理解这个机制**:
这确保收尾工作的质量控制和隔离执行。
5次分析工具已经足够，现在必须执行收尾。

⚠️ **这是技术强制阻止，不是建议**。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(non_task_tool_count, non_task_tool_count)

                    # 🔥 v24.3修复：PreToolUse阻止机制修复
                    # 根据《HOOK正确用法文档.md》第78-101行和第159行：
                    # - 方法1（推荐）: stderr + exit 2（简单阻止，不输出JSON）
                    # - 方法2: JSON + exit 0（支持参数修改和用户确认）
                    # ⚠️ Exit code 2会**忽略JSON输出**，两者不能混用
                    #
                    # 当前场景：简单阻止（无需参数修改），选择方法1
                    sys.stderr.write(deny_message)
                    sys.stderr.flush()
                    sys.exit(2)  # 阻止操作（方法1：纯exit 2）

        # 6.5 v24.0新增：Planning阶段user_confirmed检查（修复#issue-认同后仍修改代码）
        # 场景：用户说"认同"但Hook误判为"疑虑"，planning.user_confirmed=false
        # 问题：Claude忽略警告，自行判断进入Implementation阶段，尝试修改代码
        # 解决：PreToolUse强制检查user_confirmed状态，阻止未确认的代码修改
        if current_step == 'planning':
            CODE_MODIFICATION_TOOLS = ['Write', 'Edit', 'NotebookEdit']
            if tool_name in CODE_MODIFICATION_TOOLS:
                planning_step = task_meta.get('steps', {}).get('planning', {})
                user_confirmed = planning_step.get('user_confirmed', False)
                expert_review_completed = planning_step.get('expert_review_completed', False)
                expert_review_required = planning_step.get('expert_review_required', False)

                if not user_confirmed:
                    # 构建拒绝原因（根据任务类型定制消息）
                    task_type = task_meta.get('task_type', 'general')
                    denial_reason = """
Planning阶段禁止直接修改代码（user_confirmed=false）

❌ 检测到问题：
你尝试在Planning阶段使用{}工具修改代码，但用户尚未明确确认方案。

✅ 正确流程：
""".format(tool_name)

                    if task_type == 'bug_fix' and expert_review_required:
                        if not expert_review_completed:
                            denial_reason += """1. 【必须】使用Task工具启动专家审查子代理
   - 验证你的BUG根本原因分析是否正确
   - 确认修复方案不会引入新问题

2. 等待子代理完成审查并返回结果

3. 根据审查结果调整方案（如需要）

4. 向用户展示最终方案，等待用户明确输入"同意"

5. 用户确认后，Hook会自动更新user_confirmed=true

6. 然后你才能使用Write/Edit/NotebookEdit修改代码"""
                        else:
                            denial_reason += """1. 向用户展示你的修复方案（包含专家审查结果）

2. 等待用户明确输入"同意"/"认同"/"确认"等关键词

3. 用户确认后，Hook会自动更新user_confirmed=true

4. 然后你才能使用Write/Edit/NotebookEdit修改代码

💡 提示：如果用户已经表示认同但未明确说"同意"，
         请提醒用户明确输入"同意"以推进流程。"""
                    else:
                        denial_reason += """1. 向用户展示你的实现方案

2. 等待用户明确输入"同意"/"认同"/"确认"等关键词

3. 用户确认后，Hook会自动更新user_confirmed=true，并转移到Implementation阶段

4. 然后你才能使用Write/Edit/NotebookEdit修改代码"""

                    # v1.1新增：使用仪表盘生成器
                    sys.stderr.write("[PreToolUse v24.0] Planning阶段代码修改被拒绝: user_confirmed=false\n")

                    try:
                        from utils.dashboard_generator import generate_permission_denial
                        enhanced_denial = generate_permission_denial(
                            tool_name=tool_name,
                            current_step=current_step,
                            reason=denial_reason
                        )

                        # 使用JSON响应（符合Hook规范）
                        # v28.0修复：完整拒绝说明显示给用户
                        response = {
                            "hookSpecificOutput": {
                                "hookEventName": "PreToolUse",
                                "permissionDecision": "deny",
                                "permissionDecisionReason": denial_reason  # 简短原因
                            },
                            "systemMessage": enhanced_denial  # ✅ 完整拒绝说明（用户可见）
                        }
                        print(json.dumps(response, ensure_ascii=False))
                        sys.exit(0)  # JSON响应使用exit 0
                    except Exception as e:
                        sys.stderr.write(u"[WARN] 仪表盘生成失败: {}\n".format(e))
                        # 降级：使用原来的deny_and_exit
                        deny_and_exit(
                            tool_name,
                            current_step,
                            denial_reason,
                            "请先向用户确认方案，等待用户明确同意后再修改代码"
                        )

        # 7. 执行四层验证
        try:
            validator = StageValidator(cwd)
            validation_result = validator.validate(
                current_step, tool_name, tool_input, task_meta
            )

            # ✅ Phase 1: 诊断日志 - 记录验证结果（仅DEBUG模式）
            if DEBUG:
                sys.stderr.write(f"[PreToolUse] 验证结果: allowed={validation_result.get('allowed', False)}\n")
                if not validation_result.get("allowed", False):
                    sys.stderr.write(f"[PreToolUse] 拒绝原因: {validation_result.get('reason', 'N/A')}\n")

        except Exception as e:
            sys.stderr.write(f"[ERROR] 验证过程异常: {e}\n")
            import traceback
            traceback.print_exc()
            # 异常情况下放行(避免完全阻塞)
            sys.stderr.write(f"[PreToolUse] 降级处理: 默认放行\n")
            allow_and_exit(f"验证异常,默认放行: {e}", suppress=False)
            return

        # 8. 决策
        if validation_result.get("allowed", False):
            # 验证通过,放行
            if DEBUG:
                sys.stderr.write(f"[PreToolUse] 决策: 放行工具 {tool_name}\n")
            allow_and_exit(validation_result.get("reason", "验证通过"), suppress=True)
        else:
            # 验证失败,拦截
            if DEBUG:
                sys.stderr.write(f"[PreToolUse] 决策: 拦截工具 {tool_name}\n")
            deny_and_exit(
                tool_name,
                current_step,
                validation_result.get("reason", "验证失败"),
                validation_result.get("suggestion", "")
            )

    except Exception as e:
        # [v3.0 Final增强] 详细错误诊断
        sys.stderr.write("=" * 80 + "\n")
        sys.stderr.write("[HOOK ERROR] PreToolUse Hook 执行失败\n")
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
                from core.stage_validator import StageValidator as SV
                sys.stderr.write(f"  StageValidator可用: True\n")
            except ImportError as ie:
                sys.stderr.write(f"  StageValidator可用: False ({ie})\n")

            try:
                from core.task_meta_manager import TaskMetaManager as TMM
                sys.stderr.write(f"  TaskMetaManager可用: True\n")
            except ImportError as ie:
                sys.stderr.write(f"  TaskMetaManager可用: False ({ie})\n")

            # 检查活跃任务
            active_file = os.path.join(cwd, '.claude', '.task-active.json')
            sys.stderr.write(f"  .task-active.json存在: {os.path.exists(active_file)}\n")
        except Exception as ctx_err:
            sys.stderr.write(f"  (上下文信息收集失败: {ctx_err})\n")

        sys.stderr.write("=" * 80 + "\n")

        # 降级：允许继续执行（避免完全阻塞工作流）
        allow_and_exit(f"Hook执行异常,默认放行: {str(e)}", suppress=False)


def allow_and_exit(reason: str, suppress: bool = True):
    """放行并退出"""
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": reason
        },
        "suppressOutput": suppress
    }
    print(json.dumps(output, ensure_ascii=False))
    sys.exit(0)


def deny_and_exit(tool_name: str, current_step: str, reason: str, suggestion: str):
    """
    拦截并退出（根据Claude Code官方文档）

    关键修复（Phase 8.1）:
    - 返回 exit code 2 以阻止工具调用
    - 错误消息输出到stderr（会显示给Claude和用户）
    - 不使用JSON输出（exit code 2本身就是信号）

    官方文档: https://code.claude.com/docs/en/hooks
    """
    # 阶段显示映射
    STAGE_DISPLAY = {
        'activation': '📌 任务激活',
        'planning': '📝 方案制定',
        'implementation': '⚙️ 代码实施',
        'finalization': '📦 收尾归档'
    }

    stage_name = STAGE_DISPLAY.get(current_step, f"❓ {current_step}")

    # 构建错误消息（输出到stderr）
    denial_message = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⛔ 工具调用被拒绝
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
当前阶段: {stage_name}
尝试工具: {tool_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ 拒绝原因:
{reason}
"""

    if suggestion:
        denial_message += f"""
✅ 正确做法:
{suggestion}
"""

    denial_message += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 工作流强制执行 - 违规操作已被阻止
请按照上述"正确做法"继续操作
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    # ✅ Phase 8.1关键修复: 输出到stderr并返回exit code 2
    sys.stderr.write(denial_message)
    sys.stderr.flush()  # 确保消息立即输出
    sys.exit(2)  # exit code 2 = 阻止工具调用


if __name__ == "__main__":
    main()
