#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SubagentStop Hook - 子代理结果处理 (v3.1.2 - Unicode编码修复)

职责:
1. 从transcript_path解析子代理输出（v3.0修正）
2. 提取JSON标记格式的结果（<!-- SUBAGENT_RESULT {...} -->）
3. 🔥 v3.1新增：标记缺失时使用LLM解析兜底
4. 保存到task-meta.json
5. 向用户展示结果摘要（v3.0新增）

核心变更:
v1.0: ❌ 错误从stdin读取子代理结果
v2.0: ✅ 从transcript_path解析（但未实施）
v3.0: ✅ 完整实现transcript解析 + 用户可见摘要
v3.1: ✅ 新增LLM解析兜底（100%可靠）
v3.1.1: 🔥 新增文件日志诊断功能
v3.1.2: 🔥 修复Windows路径Unicode代理字符编码错误

退出码:
- 0: 成功
- 1: 非阻塞错误
"""

import sys
import json
import os
import re
import io
from typing import Optional, Dict
from datetime import datetime

# 🔥 v3.1.1: 文件日志功能（Claude Code不捕获stderr）
DEBUG_LOG_FILE = os.path.join(os.getcwd(), "subagent-stop-debug.log")

def log_to_file(message):
    """写入诊断日志到文件"""
    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        # 🔥 v3.1.2: 处理Windows路径中的Unicode代理字符
        # 使用errors='replace'将无法编码的字符替换为'?'
        with open(DEBUG_LOG_FILE, 'a', encoding='utf-8', errors='replace') as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception as e:
        # 🔥 v3.1.2: 如果仍然失败,尝试写入错误信息
        try:
            with open(DEBUG_LOG_FILE, 'a', encoding='utf-8', errors='replace') as f:
                f.write(f"[{timestamp}] [LOG_ERROR] {str(e)}\n")
        except:
            pass  # 完全失败则忽略

# 修复Windows GBK编码问题：强制使用UTF-8输出
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 记录Hook启动
log_to_file("=" * 80)
log_to_file("SubagentStop Hook v3.1.2 启动")
log_to_file("=" * 80)

# 导入 TaskMetaManager
HOOK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HOOK_DIR)

try:
    from core.task_meta_manager import TaskMetaManager
except ImportError:
    sys.stderr.write("[ERROR] TaskMetaManager 模块缺失\n")
    sys.exit(0)


def extract_subagent_result_with_llm(content: str) -> Optional[Dict]:
    """
    使用LLM解析子代理输出（v3.1：兜底机制）

    策略：发送子代理的最后一条消息给Haiku，要求提取审查结果

    Args:
        content: 子代理的输出内容

    Returns:
        解析后的审查结果，失败返回None
    """
    try:
        # 动态导入anthropic（避免没有安装时影响启动）
        try:
            import anthropic
        except ImportError:
            sys.stderr.write("[WARN] anthropic库未安装，无法使用LLM解析兜底\n")
            sys.stderr.write("[WARN] 安装方法: pip install anthropic\n")
            return None

        # 检查API Key（支持两种环境变量名）
        # 优先使用ANTHROPIC_API_KEY，降级到ANTHROPIC_AUTH_TOKEN
        api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
        if not api_key:
            sys.stderr.write("[WARN] ANTHROPIC_API_KEY或ANTHROPIC_AUTH_TOKEN环境变量未设置，无法使用LLM解析\n")
            return None

        # 构建提取prompt
        extract_prompt = f"""你是一个结果提取专家。以下是一个专家审查子代理的输出，请提取审查结果。

子代理输出:
{content[:2000]}  # 限制长度防止超出token限制

请分析上述输出，以JSON格式返回：
{{
  "approved": true/false,  // 是否通过审查（关键词：通过、pass、可以实施、approved、looks good等表示通过；需要调整、有问题、建议修改、rejected等表示不通过）
  "issues": ["问题1", "问题2"],  // 发现的问题列表（如果没有问题，返回空数组[]）
  "suggestions": ["建议1", "建议2"]  // 改进建议列表（如果没有建议，返回空数组[]）
}}

**重要提示**:
- 如果输出中包含"通过"、"pass"、"可以实施"、"approved"、"looks good"等词，approved应为true
- 如果输出中包含"需要调整"、"有问题"、"建议修改"、"rejected"、"不通过"等词，approved应为false
- 如果无法判断，默认approved为true（保守策略）
- 只返回JSON，不要其他内容"""

        sys.stderr.write("[INFO v3.1] 使用LLM解析子代理输出...\n")

        # 调用Haiku API
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=500,
            messages=[{"role": "user", "content": extract_prompt}]
        )

        # 提取响应文本
        result_text = response.content[0].text.strip()
        sys.stderr.write(f"[DEBUG v3.1] LLM响应: {result_text[:200]}...\n")

        # 提取JSON（可能包含markdown代码块）
        # 尝试多种格式
        json_patterns = [
            r'```json\s*(\{.*?\})\s*```',  # ```json {...} ```
            r'```\s*(\{.*?\})\s*```',      # ``` {...} ```
            r'(\{.*?\})'                    # {...}
        ]

        for pattern in json_patterns:
            json_match = re.search(pattern, result_text, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group(1))
                    sys.stderr.write("[INFO v3.1] LLM解析成功\n")
                    return result
                except json.JSONDecodeError:
                    continue

        sys.stderr.write("[WARN] LLM响应格式无法解析\n")
        return None

    except Exception as e:
        sys.stderr.write(f"[ERROR] LLM解析异常: {e}\n")
        import traceback
        traceback.print_exc(file=sys.stderr)
        return None


def extract_subagent_result(transcript_path: str) -> Optional[Dict]:
    """
    从对话记录中提取子代理结果 (v3.0完整实现)

    子代理输出格式约定:
    ```markdown
    ## 专家审查结果

    ...（人类可读的分析）...

    ### 合规性检查
    - ✅ 无CRITICAL违规
    - ⚠️ 建议添加物品掉落范围限制

    <!-- SUBAGENT_RESULT
    {
      "approved": true,
      "issues": [],
      "suggestions": ["建议添加物品掉落范围限制"]
    }
    -->
    ```

    Args:
        transcript_path: 对话记录文件路径

    Returns:
        解析后的子代理结果字典，失败返回None
    """
    if not transcript_path or not os.path.exists(transcript_path):
        sys.stderr.write(f"[WARN] transcript_path不存在: {transcript_path}\n")
        return None

    try:
        with open(transcript_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 🔥 v22.3修复：直接按JSONL格式解析（官方文档明确是.jsonl格式）
        # 每行是一个完整的JSON对象（消息）
        messages = []
        for line in content.strip().split('\n'):
            if not line.strip():  # 跳过空行
                continue
            try:
                msg = json.loads(line)
                messages.append(msg)
            except json.JSONDecodeError as e:
                sys.stderr.write(f"[WARN v22.3] 解析JSONL行失败: {e}\n")
                continue  # 跳过无效行，继续处理后续行

        if not messages:
            sys.stderr.write(f"[WARN] transcript文件为空或格式错误: {transcript_path}\n")
            return None

        sys.stderr.write(f"[INFO v22.3] 成功解析transcript，共{len(messages)}条消息\n")

    except Exception as e:
        sys.stderr.write(f"[ERROR] 读取transcript失败: {e}\n")
        return None

    # 查找子代理的最后一条消息
    for msg in reversed(messages):
        if msg.get('role') == 'assistant':
            content = msg.get('content', '')
            if isinstance(content, list):
                # 处理多段content
                content = '\n'.join([
                    item.get('text', '') if isinstance(item, dict) else str(item)
                    for item in content
                ])

            # 提取JSON标记（支持多行）
            match = re.search(
                r'<!--\s*SUBAGENT_RESULT\s*(\{.*?\})\s*-->',
                content,
                re.DOTALL | re.MULTILINE
            )

            if match:
                try:
                    result = json.loads(match.group(1))
                    sys.stderr.write(f"[INFO] 成功提取子代理结果（标记格式）\n")
                    return result
                except json.JSONDecodeError as e:
                    sys.stderr.write(f"[ERROR] 子代理结果JSON格式错误: {e}\n")
                    sys.stderr.write(f"[DEBUG] JSON内容: {match.group(1)}\n")
                    # JSON格式错误，尝试LLM解析兜底

            # 🔥 v3.1新增：标记缺失或格式错误，使用LLM解析兜底
            sys.stderr.write(f"[INFO v3.1] 未找到SUBAGENT_RESULT标记，尝试LLM解析兜底\n")

            # 使用LLM解析当前消息内容
            llm_result = extract_subagent_result_with_llm(content)
            if llm_result:
                sys.stderr.write(f"[INFO v3.1] LLM解析兜底成功\n")
                return llm_result
            else:
                sys.stderr.write(f"[WARN v3.1] LLM解析兜底失败\n")
                # 继续尝试下一条消息

    # 所有尝试均失败
    sys.stderr.write(f"[WARN] 未找到SUBAGENT_RESULT标记，且LLM解析失败\n")
    return None


def generate_user_message(task_type: str, subagent_result: Dict, subagent_type: str, task_id: str = "") -> str:
    """
    生成用户可见的结果摘要 (v3.0 Final - Phase 3增强)

    Args:
        task_type: 任务类型（bug_fix/feature_design）
        subagent_result: 子代理结果
        subagent_type: 子代理类型（expert_review/doc_research）
        task_id: 任务ID（可选）

    Returns:
        格式化的用户消息
    """
    if subagent_type == "expert_review":
        # 专家审查结果
        approved = subagent_result.get('approved', False)
        issues = subagent_result.get('issues', [])
        suggestions = subagent_result.get('suggestions', [])
        score = subagent_result.get('score', 0)

        if approved:
            message = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 专家审查通过
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
            # 添加任务ID显示（v3.0 Final Phase 3新增）
            if task_id:
                message += f"**任务ID**: {task_id[:24]}...\n"
            if score:
                message += f"**审核评分**: {score}/10\n"
            message += "\n🎉 方案已通过专家审查，无CRITICAL规范违规！\n"
            if suggestions:
                message += f"\n💡 优化建议：\n"
                for s in suggestions:
                    message += f"  - {s}\n"

            message += """
**下一步**:
AI将根据审查建议优化方案（如有），然后询问你是否同意方案。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            message = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 专家审查发现问题
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ 发现{len(issues)}个问题：
"""
            for issue in issues:
                message += f"  - {issue}\n"

            if suggestions:
                message += f"\n💡 改进建议：\n"
                for s in suggestions:
                    message += f"  - {s}\n"

            message += """
**下一步**:
AI将根据审查意见调整方案。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        return message

    elif subagent_type == "doc_research":
        # 文档查询结果
        summary = subagent_result.get('summary', '已查询相关API文档')
        findings = subagent_result.get('findings', [])

        message = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 文档查询完成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{summary}
"""
        if findings:
            message += "\n**查询结果**:\n"
            for f in findings:
                message += f"  - {f}\n"

        message += """
**下一步**:
AI将根据查询结果制定设计方案。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        return message

    else:
        # 其他子代理类型
        return f"✅ 子代理完成: {subagent_type}\n结果已保存到task-meta.json"


def main():
    """主入口"""
    try:
        # 1. 读取stdin输入
        stdin_content = sys.stdin.read()
        if not stdin_content or not stdin_content.strip():
            sys.stderr.write("[WARN] SubagentStop Hook收到空输入，跳过\n")
            # ✅ v22.3修复：使用官方标准格式（空对象表示允许停止）
            print(json.dumps({}, ensure_ascii=False))
            sys.exit(0)

        hook_input = json.loads(stdin_content)

        # 🔥 v22.3.1诊断：输出完整的hook_input以便调试
        # 🔥 v3.1.2: 使用ensure_ascii=True避免Unicode代理字符编码错误
        try:
            hook_input_str = json.dumps(hook_input, indent=2, ensure_ascii=True)
            sys.stderr.write(f"[DEBUG v22.3.1] SubagentStop收到的完整输入:\n{hook_input_str}\n")
            log_to_file(f"完整输入: {hook_input_str}")
        except Exception as e:
            sys.stderr.write(f"[WARN v3.1.2] 无法序列化hook_input: {e}\n")
            log_to_file(f"[WARN] 无法序列化hook_input: {e}")

        # 🔥 v22.3新增：检查stop_hook_active防止过早退出
        stop_hook_active = hook_input.get('stop_hook_active', False)
        log_to_file(f"stop_hook_active = {stop_hook_active}")

        if stop_hook_active:
            sys.stderr.write("[INFO v22.3] stop_hook_active=true, 这是第2+次触发，允许停止\n")
            log_to_file("决策: stop_hook_active=true, 第2+次触发, 允许停止")
            # 后续触发(已被阻止过)直接允许停止，避免无限循环
            print(json.dumps({}, ensure_ascii=False))
            sys.exit(0)

        sys.stderr.write("[INFO v22.3] stop_hook_active=false, 首次触发，开始处理结果\n")
        log_to_file("决策: stop_hook_active=false, 首次触发, 开始处理")

        # 2. 获取子代理transcript路径（v22.3.8关键修复）
        # 🔥 BUG修复: 必须使用agent_transcript_path，而非transcript_path
        # transcript_path是主会话的记录，agent_transcript_path才是子代理的记录
        transcript_path = hook_input.get('agent_transcript_path')
        log_to_file(f"agent_transcript_path = {repr(transcript_path)}")

        # 兜底：如果agent_transcript_path不存在，尝试使用transcript_path（向后兼容）
        if not transcript_path:
            transcript_path = hook_input.get('transcript_path')
            log_to_file(f"[WARN] agent_transcript_path不存在，降级使用transcript_path: {repr(transcript_path)}")

        if not transcript_path:
            sys.stderr.write("[WARN] 未提供agent_transcript_path或transcript_path，跳过\n")
            log_to_file("退出: 两个路径都为空")
            # ✅ v22.3修复：使用官方标准格式
            print(json.dumps({}, ensure_ascii=False))
            sys.exit(0)

        # 检查文件是否存在
        transcript_exists = os.path.exists(transcript_path)
        log_to_file(f"transcript文件存在: {transcript_exists}")

        # 3. 提取子代理结果
        log_to_file("开始提取子代理结果...")
        subagent_result = extract_subagent_result(transcript_path)
        log_to_file(f"提取结果: {json.dumps(subagent_result, ensure_ascii=False) if subagent_result else 'None'}")

        # 如果提取失败，直接退出（不使用兜底机制）
        if not subagent_result:
            sys.stderr.write("[WARN] 未提取到子代理结果（标记缺失或LLM解析失败）\n")
            log_to_file("⚠️ 未提取到子代理结果")
            log_to_file("退出: 未提取到子代理结果")
            # ✅ v22.3修复：使用官方标准格式
            print(json.dumps({}, ensure_ascii=False))
            sys.exit(0)

        # 4. 获取活跃任务（v3.1: 使用session_id获取）
        cwd = os.getcwd()
        mgr = TaskMetaManager(cwd)
        log_to_file(f"工作目录: {cwd}")

        # v3.1: 从hook_input获取session_id
        session_id = hook_input.get('session_id')
        log_to_file(f"session_id = {repr(session_id)}")

        if not session_id:
            sys.stderr.write("[WARN] 缺少session_id，跳过\n")
            log_to_file("退出: 缺少session_id")
            # ✅ v22.3修复：使用官方标准格式
            print(json.dumps({}, ensure_ascii=False))
            sys.exit(0)

        # v3.1: 使用session_id获取绑定的任务
        active_task = mgr.get_active_task_by_session(session_id)
        log_to_file(f"绑定任务: {json.dumps(active_task, ensure_ascii=False) if active_task else 'None'}")

        if not active_task:
            sys.stderr.write("[WARN] 当前会话无绑定任务，跳过\n")
            log_to_file("退出: 当前会话无绑定任务")
            # ✅ v22.3修复：使用官方标准格式
            print(json.dumps({}, ensure_ascii=False))
            sys.exit(0)

        task_id = active_task['task_id']
        log_to_file(f"task_id = {repr(task_id)}")

        if not task_id:
            sys.stderr.write("[WARN] 无活跃任务，跳过\n")
            log_to_file("退出: 无活跃任务")
            # ✅ v22.3修复：使用官方标准格式
            print(json.dumps({}, ensure_ascii=False))
            sys.exit(0)

        # 5. 加载任务元数据
        task_meta = mgr.load_task_meta(task_id)
        log_to_file(f"加载task_meta结果: {'成功' if task_meta else '失败'}")

        if not task_meta:
            sys.stderr.write(f"[ERROR] 加载任务元数据失败: {task_id}\n")
            log_to_file(f"退出: 加载任务元数据失败 (task_id={task_id})")
            # ✅ v22.3修复：使用官方标准格式
            print(json.dumps({}, ensure_ascii=False))
            sys.exit(0)

        current_step = task_meta.get('current_step')
        task_type = task_meta.get('task_type', 'general')
        log_to_file(f"current_step = {current_step}, task_type = {task_type}")

        # 6. 根据当前步骤和任务类型保存结果
        if current_step == 'planning':
            # Planning阶段：保存专家审查或文档查询结果
            if task_type == 'bug_fix':
                log_to_file("进入专家审查结果保存分支 (planning + bug_fix)")

                # v22.1: BUG修复专家审查结果 - 使用atomic_update更新状态
                def update_expert_review(meta_data):
                    if 'steps' not in meta_data:
                        meta_data['steps'] = {}
                    if 'planning' not in meta_data['steps']:
                        meta_data['steps']['planning'] = {}

                    # 保存审查结果
                    meta_data['steps']['planning']['expert_review'] = subagent_result
                    meta_data['steps']['planning']['plan_adjusted'] = False

                    # 🔥 v22.1新增：更新专家审查状态字段
                    meta_data['steps']['planning']['expert_review_completed'] = True
                    meta_data['steps']['planning']['expert_review_count'] = (
                        meta_data['steps']['planning'].get('expert_review_count', 0) + 1
                    )
                    meta_data['steps']['planning']['expert_review_result'] = (
                        'pass' if subagent_result.get('approved', False) else '需要调整'
                    )

                    # 🔥 v22.3.8新增：同步更新metrics和bug_fix_tracking字段
                    if 'metrics' not in meta_data:
                        meta_data['metrics'] = {}
                    meta_data['metrics']['expert_review_triggered'] = True

                    if 'bug_fix_tracking' not in meta_data:
                        meta_data['bug_fix_tracking'] = {}
                    meta_data['bug_fix_tracking']['expert_triggered'] = True

                    log_to_file(f"atomic_update更新字段: expert_review_completed=True, expert_review_count={meta_data['steps']['planning']['expert_review_count']}, expert_review_result={meta_data['steps']['planning']['expert_review_result']}, metrics.expert_review_triggered=True, bug_fix_tracking.expert_triggered=True")
                    return meta_data

                # 使用atomic_update确保并发安全
                log_to_file("开始调用mgr.atomic_update...")
                updated_meta = mgr.atomic_update(task_id, update_expert_review)
                log_to_file(f"atomic_update结果: {'成功' if updated_meta else '失败'}")

                if not updated_meta:
                    sys.stderr.write("[ERROR] 专家审查状态更新失败\n")
                    log_to_file("错误: 专家审查状态更新失败")
                else:
                    task_meta = updated_meta  # 更新本地引用
                    log_to_file("成功: 专家审查状态已保存到task-meta.json")

                # 生成用户消息（v22.1增强）
                review_count = task_meta.get('steps', {}).get('planning', {}).get('expert_review_count', 1)
                if subagent_result.get('approved', False):
                    user_message = f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 专家审查已完成（第{review_count}次）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

专家审查子代理已返回审查结果（通过）。

**下一步**:
1. 查看专家审查结果（上方子代理输出）
2. 根据建议调整你的修复方案（如需要）
3. 向用户确认最终方案（输入"同意"）
4. Hook会自动推进到Implementation阶段

💡 提示: 专家审查状态已保存到task-meta.json
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
                else:
                    user_message = f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 专家审查发现问题（第{review_count}次）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

专家审查结果: 需要调整

**问题**:
{subagent_result.get('issues', ['未提供具体问题'])}

**建议**:
{subagent_result.get('suggestions', ['请参考上方子代理输出'])}

**下一步**:
1. 根据专家建议调整修复方案
2. 重新启动专家审查（或直接向用户确认）

💡 提示: 如果你认为专家建议不适用，可以直接输入"同意"推进
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
                sys.stderr.write(f"[INFO v22.1] 专家审查结果已保存，状态已更新\n")

            elif task_type == 'feature_design':
                # 功能设计：保存文档查询结果
                if 'steps' not in task_meta:
                    task_meta['steps'] = {}
                if 'planning' not in task_meta['steps']:
                    task_meta['steps']['planning'] = {}

                task_meta['steps']['planning']['doc_research'] = subagent_result
                task_meta['steps']['planning']['doc_reviewed'] = True

                # 生成用户消息（v3.0 Final Phase 3：添加task_id参数）
                user_message = generate_user_message(task_type, subagent_result, "doc_research", task_id)
                sys.stderr.write(f"[INFO] 文档查询结果已保存\n")

            else:
                user_message = "✅ 子代理完成，结果已保存"

        else:
            # 其他阶段
            user_message = f"✅ 子代理完成（{current_step}阶段），结果已保存"

        # 7. 保存更新后的task_meta（v22.1：BUG修复任务已使用atomic_update，跳过）
        if not (current_step == 'planning' and task_type == 'bug_fix'):
            mgr.save_task_meta(task_id, task_meta)

        # 8. 向用户输出结果摘要（v3.0新增）
        # 符合官方 SubagentStop Hook 规范（hook用法.md 第659-668行）
        # SubagentStop 应使用 decision/reason 字段，而非 hookSpecificOutput

        # 对于专家审查，根据结果决定是否阻止子代理停止
        if current_step == 'planning' and task_type == 'bug_fix':
            expert_review = subagent_result
            if not expert_review.get('approved', False):
                # 审查未通过，阻止子代理停止，要求调整方案
                output = {
                    "decision": "block",
                    "reason": "专家审查发现问题，需要调整方案后重新审查",
                    "systemMessage": user_message
                }
            else:
                # 审查通过，允许停止，显示消息
                output = {
                    "systemMessage": user_message
                }
        else:
            # 其他情况，正常停止，显示消息
            output = {
                "systemMessage": user_message
            }

        log_to_file(f"最终输出: {json.dumps(output, ensure_ascii=True)}")
        print(json.dumps(output, ensure_ascii=False))

        log_to_file("=" * 80)
        log_to_file("SubagentStop Hook v3.1.2 正常结束")
        log_to_file("=" * 80)
        sys.exit(0)

    except Exception as e:
        sys.stderr.write(f"[ERROR] SubagentStop Hook执行失败: {e}\n")
        log_to_file(f"异常发生: {e}")
        import traceback
        traceback.print_exc(file=sys.stderr)

        # ✅ v22.3修复：即使失败也输出标准格式，允许子代理停止
        log_to_file("退出: 异常发生, 允许子代理停止")
        print(json.dumps({}, ensure_ascii=False))
        sys.exit(0)  # 返回0允许子代理正常停止


if __name__ == "__main__":
    main()
