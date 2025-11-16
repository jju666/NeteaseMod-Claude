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

            # 6. 提取任务信息
            task_id = task_binding['task_id']
            current_step = task_binding['current_step']

            # 7. 加载任务元数据（用于验证详细规则）
            task_meta = mgr.load_task_meta(task_id)
            if not task_meta:
                allow_and_exit("任务元数据不存在,默认放行", suppress=True)
                return

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

        if tool_name == 'Task' and current_step == 'planning' and task_meta.get('task_type') == 'bug_fix':
            description = tool_input.get('description', '')
            subagent_type = tool_input.get('subagent_type', '')
            prompt = tool_input.get('prompt', '')

            # 🔥 v22.3.5: 详细的诊断日志
            log_to_file(f"✓ Task条件匹配！")
            log_to_file(f"  description: {description[:50]}...")
            log_to_file(f"  subagent_type: {subagent_type}")
            log_to_file(f"  prompt length: {len(prompt)}")

            if DEBUG:
                sys.stderr.write(f"[PreToolUse v22.3.5] Task条件匹配！\n")
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
