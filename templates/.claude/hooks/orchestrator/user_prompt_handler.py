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

def load_knowledge_base(kb_path):
    """加载玩法知识库"""
    try:
        if not os.path.exists(kb_path):
            return None
        with open(kb_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        sys.stderr.write("[WARNING] 加载知识库失败: {}\n".format(e))
        return None

def calculate_match_score(task_desc, keywords):
    """计算关键词匹配分数"""
    task_lower = task_desc.lower()
    matches = 0
    for keyword in keywords:
        if keyword.lower() in task_lower:
            matches += 1

    if len(keywords) == 0:
        return 0.0

    return float(matches) / len(keywords)

def find_best_gameplay_pattern(task_desc, knowledge_base):
    """查找最匹配的玩法包"""
    if not knowledge_base or 'gameplay_patterns' not in knowledge_base:
        return None

    matched_patterns = []
    for pattern in knowledge_base['gameplay_patterns']:
        score = calculate_match_score(task_desc, pattern.get('keywords', []))
        # v20.3: 降低阈值到10%，提高玩法包匹配召回率
        if score > 0.10:
            matched_patterns.append((pattern, score))

    # 排序并选择最佳匹配
    if matched_patterns:
        matched_patterns.sort(key=lambda x: x[1], reverse=True)
        return matched_patterns[0][0]

    return None

def format_api_info(api):
    """格式化API信息"""
    result = u"**{}** ({})\n".format(api['name'], api['type'])

    if 'trigger' in api:
        result += u"  - 触发时机: {}\n".format(api['trigger'])

    if 'purpose' in api:
        result += u"  - 功能: {}\n".format(api['purpose'])

    if 'fields' in api:
        result += u"  - 字段:\n"
        for field_name, field_desc in api['fields'].items():
            result += u"    - `{}`: {}\n".format(field_name, field_desc)

    if 'params' in api:
        result += u"  - 参数:\n"
        for param_name, param_info in api['params'].items():
            param_type = param_info.get('type', '未知')
            result += u"    - `{}` ({})\n".format(param_name, param_type)
            if 'required' in param_info:
                result += u"      必需字段: {}\n".format(', '.join(param_info['required']))
            if 'example' in param_info:
                result += u"      示例: `{}`\n".format(json.dumps(param_info['example'], ensure_ascii=False))

    if 'common_pitfall' in api:
        result += u"  - ⚠️ 常见陷阱: {}\n".format(api['common_pitfall'])

    return result

def format_gameplay_pack(pattern):
    """格式化玩法包为可读文本"""
    impl_guide = pattern.get('implementation_guide', {})

    # 1. 头部信息
    result = u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 玩法包已加载: {}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**分类**: {} | **难度**: {} | **预计时间**: {}

🎮 **实现原理**:
{}

""".format(
        pattern['name'],
        pattern.get('category', '未分类'),
        pattern.get('difficulty', '未知'),
        pattern.get('estimated_time', '未知'),
        impl_guide.get('principle', '待补充')
    )

    # 2. 完整代码
    code_info = impl_guide.get('complete_code', {})
    if code_info:
        result += u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 完整代码实现 (可直接使用或修改)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**文件路径**: {}

```python
{}
```

""".format(
            code_info.get('file', 'unknown.py'),
            code_info.get('content', '# 代码缺失')
        )

    # 3. 配置指南
    config_guide = impl_guide.get('config_guide', {})
    if config_guide:
        result += u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚙️ 配置说明
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{}

**示例配置**:
```python
{}
```

**字段说明**:
""".format(
            config_guide.get('description', ''),
            json.dumps(config_guide.get('example', {}), indent=4, ensure_ascii=False)
        )

        for field_name, field_desc in config_guide.get('fields', {}).items():
            result += u"- `{}`: {}\n".format(field_name, field_desc)

        result += u"\n"

    # 4. MODSDK API 清单
    modsdk_apis = impl_guide.get('modsdk_apis', [])
    if modsdk_apis:
        result += u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔗 所需 MODSDK API
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
        for idx, api in enumerate(modsdk_apis, 1):
            result += u"{}. {}\n".format(idx, format_api_info(api))

    # 5. 常见问题
    common_issues = impl_guide.get('common_issues', [])
    if common_issues:
        result += u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🐛 常见问题与解决方案
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
        for idx, issue in enumerate(common_issues, 1):
            result += u"""**问题 {}**: {}
**原因**: {}
**解决**: {}

""".format(
                idx,
                issue.get('problem', '未知'),
                issue.get('cause', '未知'),
                issue.get('solution', '未知')
            )

    # 6. 相关玩法
    related = impl_guide.get('related_gameplay', [])
    if related:
        result += u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 相关玩法扩展
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
        for r in related:
            result += u"- **{}**: {}\n".format(r['name'], r.get('similarity', ''))
            if 'extension' in r:
                result += u"  扩展思路: {}\n".format(r['extension'])

        result += u"\n"

    # 7. 底部提示
    result += u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ AI 使用指南
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 上述代码可以直接使用或根据需求修改
2. Hook会自动检查CRITICAL规范,无需担心违规
3. 如遇到错误,Hook会自动推送精确的修复方案
4. 无需再查阅大量文档,专注于实现业务逻辑

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    return result

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
    """安全地匹配关键词（v22.3：词边界+否定词检测）

    Args:
        text: 用户输入文本
        keywords: 关键词列表

    Returns:
        bool: 如果匹配到关键词且无否定前缀返回True
    """
    import re
    text_lower = text.lower().strip()

    for kw in keywords:
        # 使用词边界匹配（避免"不同意"匹配到"同意"）
        # \b在中文环境下不可靠，改用前后字符检测
        kw_lower = kw.lower()

        # 方案1：直接检查是否包含且无否定前缀
        if kw_lower in text_lower:
            # 检查是否有否定前缀
            if not has_negation_prefix(text_lower, kw_lower):
                return True

    return False

def _snapshot_step_state(meta_data, step_name):
    """
    将当前步骤状态保存为历史快照 (v23.0新增)

    实现完整的历史留痕机制,每次状态转移前保存当前状态快照到iterations数组,
    确保所有信息追加而非覆盖,方便收尾子代理分析完整历史生成归档文档。

    Args:
        meta_data: 任务元数据字典
        step_name: 步骤名称 ('planning' | 'implementation' | 'finalization')

    Returns:
        dict: 创建的快照对象,如果失败返回None
    """
    if 'steps' not in meta_data:
        return None

    step_data = meta_data['steps'].get(step_name)
    if not step_data:
        return None

    # 初始化iterations数组
    if 'iterations' not in step_data:
        step_data['iterations'] = []

    # 计算迭代ID
    iteration_id = len(step_data['iterations']) + 1

    # 创建快照(基础结构)
    snapshot = {
        "iteration_id": iteration_id,
        "timestamp": datetime.now().isoformat(),
        "status": step_data.get('status', 'unknown'),
        "config": {},   # 配置字段(required_doc_count, expert_review_required等)
        "process": {},  # 过程字段(docs_read_count, tools_used等)
        "outcome": {}   # 结果字段(user_confirmed, solution_proposal等)
    }

    # 定义字段分类
    config_fields = ['required_doc_count', 'expert_review_required', 'task_type']
    process_fields = ['expert_review_triggered', 'expert_review_count']
    outcome_fields = [
        'user_confirmed', 'solution_proposal', 'expert_review_result',
        'expert_review_completed', 'confirmed_at', 'completed_at',
        'started_at', 'resumed_at', 'resumed_reason'
    ]

    # 提取配置字段
    for field in config_fields:
        if field in step_data:
            snapshot['config'][field] = step_data[field]

    # 提取过程字段
    for field in process_fields:
        if field in step_data:
            snapshot['process'][field] = step_data[field]

    # 提取结果字段
    for field in outcome_fields:
        if field in step_data:
            snapshot['outcome'][field] = step_data[field]

    # 特殊处理: implementation步骤保存完整的test_feedback_history和code_changes
    if step_name == 'implementation':
        if 'test_feedback_history' in step_data:
            snapshot['test_feedback'] = step_data['test_feedback_history'][:]

        # 从metrics中提取当前iteration的code_changes
        metrics = meta_data.get('metrics', {})
        code_changes = metrics.get('code_changes', [])
        if code_changes:
            snapshot['code_changes'] = code_changes[:]

    # 追加到历史
    step_data['iterations'].append(snapshot)
    step_data['current_iteration_id'] = iteration_id

    return snapshot

def _log_state_transition(meta_data, from_step, to_step, trigger, details):
    """
    记录状态转移到全局日志 (v23.0新增)

    在state_transitions数组中追加每次状态转移的详细信息,
    包括转移触发原因、用户输入、前置条件检查结果、迭代ID等,
    确保完整可追溯的状态机执行历史。

    Args:
        meta_data: 任务元数据字典
        from_step: 源状态 (None表示任务初始化)
        to_step: 目标状态
        trigger: 触发原因 ('user_agreed' | 'explicit_success' | 'explicit_failure' | 'task_initialized' 等)
        details: 详细信息字典 (包含user_input, code_changes_count等)

    Returns:
        dict: 创建的转移记录对象
    """
    if 'state_transitions' not in meta_data:
        meta_data['state_transitions'] = []

    transition_id = len(meta_data['state_transitions']) + 1

    transition = {
        "id": transition_id,
        "from_step": from_step,
        "to_step": to_step,
        "timestamp": datetime.now().isoformat(),
        "trigger": trigger,
        "details": details
    }

    # 添加前置条件快照(如果是进入Implementation阶段)
    if to_step == 'implementation':
        planning = meta_data.get('steps', {}).get('planning', {})
        transition['preconditions_met'] = {
            "docs_read": len(meta_data.get('metrics', {}).get('docs_read', [])),
            "required_doc_count": planning.get('required_doc_count'),
            "expert_review_completed": planning.get('expert_review_completed'),
            "expert_review_result": planning.get('expert_review_result')
        }

    # 添加迭代ID引用
    if from_step:
        from_step_data = meta_data.get('steps', {}).get(from_step, {})
        if 'current_iteration_id' in from_step_data:
            transition[f"{from_step}_iteration"] = from_step_data['current_iteration_id']

    if to_step:
        to_step_data = meta_data.get('steps', {}).get(to_step, {})
        # 即将开始的新迭代ID
        next_iteration_id = len(to_step_data.get('iterations', [])) + 1
        transition[f"{to_step}_iteration"] = next_iteration_id

    # 标记回滚
    if from_step and to_step:
        step_order = ['planning', 'implementation', 'finalization']
        from_index = step_order.index(from_step) if from_step in step_order else -1
        to_index = step_order.index(to_step) if to_step in step_order else -1
        if to_index >= 0 and from_index > to_index:
            transition['rollback'] = True

    meta_data['state_transitions'].append(transition)

    return transition

def _reset_planning_step(meta_data, reason='rollback'):
    """
    统一的Planning步骤重置逻辑 (v23.0新增)

    确保回滚到Planning时所有必需字段都被正确初始化,
    特别是required_doc_count和expert_review_*字段,
    从而解决字段丢失导致的"强制阅读文档"等问题。

    Args:
        meta_data: 任务元数据字典
        reason: 重置原因 ('rollback' | 'planning_required' | 'loop_detected' | 'explicit_failure')

    Returns:
        dict: 重置后的planning步骤数据
    """
    task_type = meta_data.get('task_type', 'general')

    if 'planning' not in meta_data.get('steps', {}):
        meta_data.setdefault('steps', {})['planning'] = {}

    planning = meta_data['steps']['planning']

    # 基础状态重置
    planning['user_confirmed'] = False
    planning['status'] = 'in_progress'
    planning['resumed_at'] = datetime.now().isoformat()

    # 【P0 BUG修复】文档要求初始化(确保字段存在)
    if 'required_doc_count' not in planning:
        planning['required_doc_count'] = 0 if task_type == 'bug_fix' else 3

    # 【P0 BUG修复】专家审查状态初始化(bug_fix类型必需)
    if task_type == 'bug_fix':
        planning['expert_review_required'] = True
        planning['expert_review_completed'] = False
        planning['expert_review_result'] = None
        # 保留expert_review_count(累计值,不重置)
        if 'expert_review_count' not in planning:
            planning['expert_review_count'] = 0

    # 拒绝计数初始化(用于循环检测,保留历史值)
    if 'rejection_count' not in planning:
        planning['rejection_count'] = 0
    if 'rejection_history' not in planning:
        planning['rejection_history'] = []

    # 记录重置原因
    planning['resumed_reason'] = reason

    return planning

def handle_state_transition(user_input, cwd, session_id=None):
    """处理用户状态转移（v22.3: 修复关键词匹配bug + 增加拒绝处理）

    Args:
        user_input: 用户输入
        cwd: 工作目录
        session_id: 会话ID（v3.1+需要）
    """
    if not TaskMetaManager:
        return None

    # v3.1: 获取当前会话绑定的任务
    meta_manager = TaskMetaManager(cwd)

    if session_id:
        # v3.1: 使用session_id获取绑定的任务
        active_task = meta_manager.get_active_task_by_session(session_id)
        if not active_task:
            return None
        task_id = active_task['task_id']
    else:
        # 降级处理：无session_id时返回None
        return None

    if not task_id:
        return None

    # 检查任务元数据是否存在
    meta_path = meta_manager._get_meta_path(task_id)
    if not os.path.exists(meta_path):
        return None

    # 用户输入预处理
    user_input_lower = user_input.lower().strip()

    # 定义关键词映射（v22.3：添加REJECT_KEYWORDS；v22.4：扩展REJECT_KEYWORDS）
    CONFIRM_KEYWORDS = ['同意', '可以', 'ok', '没问题', '确认', 'yes', '好的', '行']
    REJECT_KEYWORDS = [
        # 原有（v22.3）
        '不同意', '有问题', '需要调整', '不行', '不对', '不可以', '拒绝',
        # v22.4新增：覆盖更多拒绝表达
        '不符合', '不够', '不太', '不是', '重新', '再想', '再考虑',
        '重新思考', '重新分析', '彻底', '完全错', '不理解',
        '不认可', '不满意', '有疑问', '有疑虑'
    ]
    # v23.1修复: 大幅扩充成功反馈关键词（添加20+个用户实际使用的表达）
    # 基于任务-1117-234152测试发现："没问题了"、"确定"等常见表达缺失导致状态机失效
    FIXED_KEYWORDS = [
        # v22.6原有关键词
        '修复了', '已修复', '完成', '已完成', '好了', '可以了', '成功', '搞定', '搞定了', '解决了',
        'done', 'fixed', 'ok了', 'fixed了',
        # v23.1新增：基于真实用户输入扩充
        '没问题了', '没问题', '确定', '可以', '行', '行了', 'ok', 'okay', 'OK', 'OKAY',
        '通过', '正常', '正常了', '没事了', '没事', '没毛病',
        '修好了', '解决', '完美', '完美了', '满意', '可以了', '没问题了',
        '没问题的', '可以的', '行的', '通过了', '验证通过'
    ]
    # v22.6修复: 扩充失败反馈关键词（添加'未修复', '还存在问题', '不行'等常见表达）
    NOT_FIXED_KEYWORDS = [
        '没修复', '未修复', '还有问题', '还存在问题', '没解决', '未解决', '重新分析', '失败', '没用',
        '不行', '有bug', '还有bug'
    ]
    CONTINUE_KEYWORDS = ['继续', '继续修改', '再改', '还有', 'continue']
    RESTART_KEYWORDS = ['重来', '重新开始', '完全错了', 'restart']
    # v22.5新增：模糊肯定表达（需要澄清）
    AMBIGUOUS_POSITIVE = ['同意', 'ok', 'okay', '可以', '没问题', '通过', '好的', '看起来不错', '不错']
    # v22.7新增：方案性错误关键词（明确表示需要回到Planning重新设计）
    PLANNING_REQUIRED_KEYWORDS = [
        '方案错了', '思路不对', '重新设计', '重新分析根因',
        '根本原因错了', '需要换思路', '这个方法不行',
        '完全错误', '理解错了', '分析错误'
    ]

    # ========== 核心改动：使用闭包 + atomic_update ==========

    # 用于存储转移结果（闭包捕获）
    result = {
        'occurred': False,       # 是否发生状态转移
        'message': '',           # 用户消息
        'new_step': None,        # 新状态
        'old_step': None,        # 旧状态
        'blocked': False,        # 是否被阻止（文档不足等）
        'block_reason': ''       # 阻止原因
    }

    def apply_state_transition(meta_data):
        """原子更新函数：应用状态转移逻辑"""
        current_step = meta_data.get('current_step', '')
        result['old_step'] = current_step

        # ========== Planning → Implementation ==========
        if current_step == 'planning':
            # 【v22.4新增】提前获取planning_step和expert_review状态，用于智能拒绝检测
            planning_step = meta_data.get('steps', {}).get('planning', {})
            expert_review_completed = planning_step.get('expert_review_completed', False)

            # v22.3修复: 使用match_keyword_safely避免"不同意"误匹配到"同意"
            if match_keyword_safely(user_input_lower, CONFIRM_KEYWORDS):
                # 前置检查：文档数量
                task_type = meta_data.get('task_type', 'general')
                docs_read = meta_data.get('metrics', {}).get('docs_read', [])
                required_docs = meta_data.get('steps', {}).get('planning', {}).get('required_doc_count', 1)

                # 前置检查1：文档数量（仅非BUG修复任务）
                if required_docs > 0 and len(docs_read) < required_docs:
                    result['blocked'] = True
                    result['block_reason'] = u"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 无法进入Implementation阶段
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

当前文档查阅: {docs_read}/{required_docs}

❌ 问题: Planning阶段要求至少查阅{required_docs}个相关文档

✅ 解决方案:
1. 继续使用Read工具查阅{remaining}个文档
2. 重点查阅:
   - CRITICAL规范（markdown/core/开发规范.md）
   - 相关系统实现文档
   - 问题排查指南

完成文档查阅后，再次输入"同意"即可推进。

💡 提示: 充分的文档研究能避免违反CRITICAL规范，提高修复成功率。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(
                        docs_read=len(docs_read),
                        required_docs=required_docs,
                        remaining=required_docs - len(docs_read)
                    )
                    sys.stderr.write(u"[UserPromptSubmit] Planning→Implementation转移被拒绝: 文档查阅不足 ({}/{}\n".format(len(docs_read), required_docs))
                    return meta_data  # 原样返回，不修改

                # 🔥 v22.1新增前置检查2：专家审查完成（仅BUG修复任务）
                # 【v22.4优化】planning_step和expert_review_completed已在第406-407行定义
                expert_review_required = planning_step.get('expert_review_required', False)

                if expert_review_required and not expert_review_completed:
                    result['blocked'] = True
                    result['block_reason'] = u"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 无法进入Implementation阶段
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

当前任务类型: BUG修复
专家审查状态: 未完成

❌ 问题: BUG修复任务必须先完成专家审查才能进入Implementation阶段

✅ 解决方案:
1. 使用 Task 工具启动专家审查子代理：
   - subagent_type: "general-purpose"
   - description: "BUG修复方案审查"
   - prompt: 详细描述你的方案，包括：
     * 你对BUG根本原因的分析
     * 计划修改的文件和具体逻辑
     * 潜在风险和验证方法
     * 请专家验证方案正确性

2. 等待子代理完成审查并返回结果

3. 根据审查结果调整方案（如需要）

4. 重新输入"同意"推进到Implementation阶段

💡 提示: 专家审查能有效避免循环修复，提高一次性修复成功率。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
                    sys.stderr.write(u"[UserPromptSubmit v22.1] Planning→Implementation转移被拒绝: 专家审查未完成\n")
                    return meta_data  # 原样返回，不修改

                # 前置检查通过，执行状态转移
                sys.stderr.write(u"[UserPromptSubmit] Planning→Implementation转移检查通过: 文档{}/{}, 专家审查{}\n".format(
                    len(docs_read), required_docs,
                    "已完成" if expert_review_completed else "未要求"
                ))

                # 【v23.0新增】状态转移前保存历史快照
                _snapshot_step_state(meta_data, 'planning')
                _log_state_transition(
                    meta_data,
                    from_step='planning',
                    to_step='implementation',
                    trigger='user_agreed',
                    details={'user_input': user_input}
                )

                # 修改状态
                meta_data['current_step'] = 'implementation'
                result['new_step'] = 'implementation'

                # 更新steps字段
                if 'steps' not in meta_data:
                    meta_data['steps'] = {}

                # 完成Planning
                if 'planning' not in meta_data['steps']:
                    meta_data['steps']['planning'] = {}
                meta_data['steps']['planning']['user_confirmed'] = True
                meta_data['steps']['planning']['confirmed_at'] = datetime.now().isoformat()
                meta_data['steps']['planning']['status'] = 'completed'
                meta_data['steps']['planning']['completed_at'] = datetime.now().isoformat()

                # 启动Implementation
                if 'implementation' not in meta_data['steps']:
                    meta_data['steps']['implementation'] = {}
                meta_data['steps']['implementation']['status'] = 'in_progress'
                meta_data['steps']['implementation']['started_at'] = datetime.now().isoformat()

                result['occurred'] = True
                result['message'] = u"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 状态转移: Planning → Implementation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

你已确认方案，工作流进入代码实施阶段。

**当前阶段**: Implementation (实施)
**允许操作**: Write, Edit, NotebookEdit 等代码修改工具

AI将开始实施代码修改。每轮修改完成后，请测试并反馈结果。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

            # 🔥 【v22.4新增】智能拒绝检测：专家审查完成后，非"同意"非"重来"的输入视为隐式拒绝
            elif expert_review_completed and not match_keyword_safely(user_input_lower, RESTART_KEYWORDS):
                # 用户既没明确同意，也没完全否定，视为对当前方案有疑虑（隐式拒绝）

                # 初始化拒绝追踪字段
                if 'rejection_count' not in planning_step:
                    planning_step['rejection_count'] = 0
                if 'rejection_history' not in planning_step:
                    planning_step['rejection_history'] = []

                # 记录拒绝
                planning_step['rejection_count'] += 1
                planning_step['rejection_history'].append({
                    'timestamp': datetime.now().isoformat(),
                    'user_feedback': user_input,
                    'rejection_count': planning_step['rejection_count'],
                    'detection_method': 'implicit'  # 标记为隐式拒绝
                })

                # 重置确认状态
                planning_step['user_confirmed'] = False
                planning_step['status'] = 'in_progress'

                # 获取任务类型和审查状态
                task_type = meta_data.get('task_type', 'general')
                expert_review_required = planning_step.get('expert_review_required', False)
                rejection_count = planning_step['rejection_count']

                # ========== 三层响应机制 ==========

                # 第1次拒绝：温和建议
                if rejection_count == 1:
                    rejection_message = u"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 检测到用户疑虑（第1次）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**用户反馈**: {user_feedback}

**系统判断**: 你没有明确输入"同意"，我理解为你对当前方案有疑虑。

✅ **建议**:
1. 根据用户反馈重新分析问题
2. 调整方案或收集更多信息
3. 制定新方案后再次向用户确认

💡 如果方案经过调整，建议启动新一轮专家审查验证。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(user_feedback=user_input[:100])

                # 第2次及以上拒绝：强制重置审查状态
                elif rejection_count >= 2 and task_type == 'bug_fix' and expert_review_required:
                    # 【关键】重置专家审查状态，强制重新审查
                    planning_step['expert_review_completed'] = False
                    planning_step['expert_review_result'] = None

                    current_review_count = planning_step.get('expert_review_count', 1)
                    next_review_count = current_review_count + 1

                    rejection_message = u"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚨 多次拒绝检测（第{rejection_count}次）- 强制重新审查
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**用户反馈**: {user_feedback}

**系统判断**: 你已{rejection_count}次未同意方案，说明方案可能存在根本性问题。

🔄 **系统已重置专家审查状态**:
- expert_review_completed: true → false
- expert_review_result: "{old_result}" → null
- 审查计数: {current_count} → 即将第{next_count}次

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚡ **下一步操作（强制）**:

1. 🔍 **彻底重新分析问题**
   - 仔细阅读用户的所有反馈（{rejection_count}次）
   - 确认是否理解了用户的真实需求
   - 如果不确定，直接询问用户期望的修复方向

2. 🔧 **制定调整后的新方案**
   - 结合前次专家审查建议
   - 针对用户反馈的疑虑点重点调整

3. 🚀 **【必须】使用Task工具启动第{next_count}次专家审查**

   Task(
     subagent_type="general-purpose",
     description="BUG修复方案第{next_count}次审查",
     prompt="详细说明：\\n1. 用户{rejection_count}次反馈的核心疑虑\\n2. 上次审查指出的问题\\n3. 我针对这些问题的调整\\n4. 请验证调整是否充分"
   )

4. ✅ **等待审查结果，再次向用户确认**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ **重要说明**:
- 系统已重置 expert_review_completed=false
- 用户下次输入"同意"时，会检查该状态
- 如果仍为false，会阻止进入Implementation
- 你**必须**先通过专家审查，才能推进流程

💡 **为什么强制审查**:
- {rejection_count}次拒绝表明方案可能偏离用户真实需求
- 专家审查能帮助发现深层次问题
- 避免进入无效修改循环，浪费用户时间

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(
                        rejection_count=rejection_count,
                        user_feedback=user_input[:100],
                        old_result=planning_step.get('expert_review_result', '需要调整'),
                        current_count=current_review_count,
                        next_count=next_review_count
                    )

                # 第3次及以上拒绝（非BUG修复或无需审查）
                else:
                    rejection_message = u"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔴 严重循环警告（第{rejection_count}次拒绝）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**用户反馈**: {user_feedback}

**系统警告**: 已连续{rejection_count}次未同意方案，极可能存在理解偏差！

⚠️ **建议操作**:
1. 仔细阅读用户的所有反馈历史
2. 确认是否理解了用户的真实需求
3. **如果仍不确定，直接询问用户期望的修复方向**
4. 完全重新制定方案

💡 **重要**: 如果用户反馈模糊，请主动提问澄清！
不要猜测用户意图，直接询问是最高效的方式。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(
                        rejection_count=rejection_count,
                        user_feedback=user_input[:100]
                    )

                result['occurred'] = True
                result['message'] = rejection_message

                sys.stderr.write(u"[UserPromptSubmit v22.4] Planning阶段隐式拒绝检测 (第{}次): {}\n".format(
                    rejection_count,
                    user_input[:50]
                ))

                # 状态保持Planning，不修改current_step
                return meta_data

            # v22.3新增: Planning阶段用户拒绝方案的处理（保留作为fallback）
            elif match_keyword_safely(user_input_lower, REJECT_KEYWORDS):
                # 用户拒绝当前方案，保持Planning阶段，要求重新分析
                # 【v22.4优化】planning_step已在第406行定义

                # 初始化拒绝追踪字段
                if 'rejection_count' not in planning_step:
                    planning_step['rejection_count'] = 0
                if 'rejection_history' not in planning_step:
                    planning_step['rejection_history'] = []

                # 记录拒绝
                planning_step['rejection_count'] += 1
                planning_step['rejection_history'].append({
                    'timestamp': datetime.now().isoformat(),
                    'user_feedback': user_input,
                    'rejection_count': planning_step['rejection_count']
                })

                # 重置确认状态
                planning_step['user_confirmed'] = False
                planning_step['status'] = 'in_progress'

                # 检查是否需要触发专家审查
                task_type = meta_data.get('task_type', 'general')
                expert_review_required = planning_step.get('expert_review_required', False)
                rejection_count = planning_step['rejection_count']

                # 构建引导消息
                rejection_message = u"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 用户拒绝当前方案 (第{rejection_count}次)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**当前阶段**: Planning (方案制定)
**状态**: 保持Planning，要求重新分析

**用户反馈**: {user_feedback}

""".format(
                    rejection_count=rejection_count,
                    user_feedback=user_input
                )

                # 如果是BUG修复任务且拒绝次数≥2，强烈建议启动专家审查
                if task_type == 'bug_fix' and rejection_count >= 2 and expert_review_required:
                    expert_review_completed = planning_step.get('expert_review_completed', False)

                    if not expert_review_completed:
                        rejection_message += u"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚨 循环拒绝检测
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

你已经{rejection_count}次拒绝方案，可能存在根本性误判。

**强烈建议**:
1. 使用 Task 工具启动专家审查子代理
2. 让专家帮助分析是否存在错误假设
3. 根据专家建议调整分析思路

**专家审查启动方式**: 参考任务初始化时的BUG修复指引

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(rejection_count=rejection_count)
                    else:
                        # ✅ v22.3.10修复：重置专家审查状态，强制100%启动新一轮审查
                        planning_step['expert_review_completed'] = False
                        planning_step['expert_review_result'] = None

                        current_review_count = planning_step.get('expert_review_count', 1)
                        next_review_count = current_review_count + 1

                        rejection_message += u"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 专家审查状态已重置
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

专家审查已完成，但用户仍不满意（拒绝{rejection_count}次）。
系统已重置专家审查状态，强制要求重新审查。

**专家审查计数**: {current_count} → 即将第{next_count}次

**下一步流程** (100%强制启动):
1. 根据用户最新反馈重新分析: "{user_feedback}"
2. 结合前次专家审查建议，调整分析思路
3. 向用户展示调整后的新方案
4. 当你输入"同意"推进时，系统会自动阻止进入Implementation
5. 你必须使用 Task 工具启动新一轮专家审查
6. 审查完成后，再次"同意"才能进入Implementation

**为什么是100%强制**:
- 系统已重置 expert_review_completed=false
- 用户"同意"时会触发专家审查前置检查
- 检查失败会阻止进入Implementation阶段
- 你唯一的选择是启动Task工具进行专家审查

**专家审查启动方式**: 参考任务初始化时的BUG修复指引

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(
                            rejection_count=rejection_count,
                            user_feedback=user_input[:100],
                            current_count=current_review_count,
                            next_count=next_review_count
                        )

                rejection_message += u"""
✅ **下一步**:
1. 根据用户反馈重新分析问题
2. 调整方案或收集更多信息
3. 制定新方案后再次向用户确认

💡 **提示**: 仔细理解用户的疑虑点，针对性地调整方案
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

                result['occurred'] = True
                result['message'] = rejection_message

                sys.stderr.write(u"[UserPromptSubmit v22.3] Planning阶段用户拒绝方案 (第{}次): {}\n".format(
                    rejection_count,
                    user_input[:50]
                ))

                # 状态保持Planning，不修改current_step
                return meta_data

            elif match_keyword_safely(user_input_lower, RESTART_KEYWORDS):
                # 完全否定，回到Activation
                meta_data['current_step'] = 'activation'
                result['new_step'] = 'activation'

                if 'planning' in meta_data.get('steps', {}):
                    meta_data['steps']['planning']['user_confirmed'] = False

                result['occurred'] = True
                result['message'] = u"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 状态回滚: Planning → Activation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

你否定了当前方案，工作流已重置到激活阶段。

**当前阶段**: Activation (激活)
**建议操作**: 重新描述任务需求，或提供更多上下文信息

AI将重新分析问题并制定新方案。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

        # ========== Implementation → Finalization ==========
        elif current_step == 'implementation':
            # 【v23.1.1修正】删除了v23.1错误的入口处快照机制
            # v23.0的设计是对的：在每个状态转移分支前保存快照，而不是入口处
            # 原因：快照应该在状态转移前保存，记录转移前的完整状态

            # 【v22.7新增】双重检测：同时检测成功、失败和方案性错误关键词
            has_success = match_keyword_safely(user_input_lower, FIXED_KEYWORDS)
            has_failure = match_keyword_safely(user_input_lower, NOT_FIXED_KEYWORDS)
            has_planning_required = match_keyword_safely(user_input_lower, PLANNING_REQUIRED_KEYWORDS)

            # 【v22.7新增】优先级1：方案性错误 → 强制回到 Planning
            if has_planning_required:
                # 【v23.1.1修正】恢复v23.0的快照调用（在状态转移前保存）
                _snapshot_step_state(meta_data, 'implementation')

                # 用户明确表示方案错误，无论是否部分成功，都回到 Planning
                meta_data['current_step'] = 'planning'
                result['new_step'] = 'planning'

                # 初始化 test_feedback_history
                if 'implementation' not in meta_data['steps']:
                    meta_data['steps']['implementation'] = {}
                if 'test_feedback_history' not in meta_data['steps']['implementation']:
                    meta_data['steps']['implementation']['test_feedback_history'] = []

                code_changes = meta_data.get('metrics', {}).get('code_changes', [])
                feedback_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'user_feedback': user_input,
                    'feedback_type': 'planning_required',
                    'clarification_requested': False,
                    'code_changes_count': len(code_changes)
                }
                meta_data['steps']['implementation']['test_feedback_history'].append(feedback_entry)

                # 【v23.0新增】使用统一重置函数
                _reset_planning_step(meta_data, reason='planning_required')

                # 重置Implementation状态
                meta_data['steps']['implementation']['status'] = 'pending'
                meta_data['steps']['implementation']['user_confirmed'] = False

                # 【v23.0新增】记录状态转移
                _log_state_transition(
                    meta_data,
                    from_step='implementation',
                    to_step='planning',
                    trigger='planning_required',
                    details={
                        'user_input': user_input,
                        'feedback_type': 'planning_required',
                        'code_changes_count': len(code_changes)
                    }
                )

                result['occurred'] = True
                result['message'] = u"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 检测到方案性错误 → 回到 Planning
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**你的反馈**: {}

**检测到**: 当前方案存在根本性问题，需要重新分析

**当前阶段**: Planning (方案制定)
**下一步**:
1. AI将重新分析问题根本原因
2. 制定新的修复方案
3. 启动专家审查（如需要）
4. 等待你确认新方案

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(user_input[:100])

            # 【v22.7新增】优先级2：失败优先（部分成功或完全失败）
            elif has_failure:
                # 只要包含失败关键词，就不进入 Finalization

                if has_success:
                    # 【v22.7新增】部分成功：同时包含成功和失败关键词
                    # 记录为 partial_success，继续 Implementation

                    if 'implementation' not in meta_data['steps']:
                        meta_data['steps']['implementation'] = {}
                    if 'test_feedback_history' not in meta_data['steps']['implementation']:
                        meta_data['steps']['implementation']['test_feedback_history'] = []

                    feedback_history = meta_data['steps']['implementation']['test_feedback_history']
                    code_changes = meta_data.get('metrics', {}).get('code_changes', [])

                    feedback_entry = {
                        'timestamp': datetime.now().isoformat(),
                        'user_feedback': user_input,
                        'feedback_type': 'partial_success',
                        'clarification_requested': False,
                        'code_changes_count': len(code_changes)
                    }
                    feedback_history.append(feedback_entry)

                    # 【v22.7新增】检测迭代循环：同类型反馈 ≥3次 → 回到 Planning
                    partial_count = sum(1 for f in feedback_history
                                       if f.get('feedback_type') in ['partial_success', 'explicit_failure'])

                    if partial_count >= 3:
                        # 【v23.1.1修正】恢复v23.0的快照调用（在状态转移前保存）
                        _snapshot_step_state(meta_data, 'implementation')

                        # 反复修改仍有问题，可能是方案性错误，回到 Planning
                        meta_data['current_step'] = 'planning'
                        result['new_step'] = 'planning'

                        # 【v23.0新增】使用统一重置函数
                        _reset_planning_step(meta_data, reason='loop_detected')

                        # 重置Implementation状态
                        meta_data['steps']['implementation']['status'] = 'pending'
                        meta_data['steps']['implementation']['user_confirmed'] = False

                        # 【v23.0新增】记录状态转移
                        _log_state_transition(
                            meta_data,
                            from_step='implementation',
                            to_step='planning',
                            trigger='loop_detected',
                            details={
                                'user_input': user_input,
                                'feedback_type': 'partial_success',
                                'partial_count': partial_count,
                                'code_changes_count': len(code_changes)
                            }
                        )

                        result['occurred'] = True
                        result['message'] = u"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 检测到反复修改 (第{}次) → 回到 Planning
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**检测到**: 问题已修改{}次，但仍然存在，可能是方案性错误

**当前阶段**: Planning (方案制定)
**下一步**:
1. AI将重新分析问题根本原因
2. 制定新的修复方案（可能采用完全不同的思路）
3. 启动专家审查验证新方案
4. 等待你确认

💡 提示: 如果问题根本原因分析错误，重复修改实现细节是无效的。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(partial_count, partial_count)
                    else:
                        # 部分成功，保持 Implementation，AI 继续修改
                        # 【v23.1.1新增】记录partial_success的内部迭代
                        _log_state_transition(
                            meta_data,
                            from_step='implementation',
                            to_step='implementation',
                            trigger='partial_success',
                            details={
                                'user_input': user_input,
                                'feedback_type': 'partial_success',
                                'partial_count': partial_count,
                                'code_changes_count': len(code_changes)
                            }
                        )

                        result['occurred'] = True
                        result['message'] = u"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 检测到部分成功 (第{}轮反馈)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**你的反馈**: {}

**检测到**:
- ✅ 部分问题已修复
- ❌ 仍有问题需要解决

**当前阶段**: Implementation (实施)
**下一步**: AI将根据你的反馈继续调整代码

💡 提示:
- 如果问题涉及方案性错误，请明确告知（如："方案错了"、"思路不对"）
- 如果只是实现细节问题，我将继续在当前方案下修改
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(partial_count, user_input[:80])

                        # 不修改状态，保持 Implementation
                        # 注意：此处不 return，继续执行后续逻辑（但不会进入其他分支）

                # 【v22.7重构】优先级2b：完全失败（原 NOT_FIXED_KEYWORDS 分支逻辑）
                else:
                    # 【v23.1.1修正】恢复v23.0的快照调用（在状态转移前保存）
                    _snapshot_step_state(meta_data, 'implementation')

                    # 完全失败：回到 Planning
                    meta_data['current_step'] = 'planning'
                    result['new_step'] = 'planning'

                    if 'steps' not in meta_data['steps']:
                        meta_data['steps'] = {}

                    # 【v22.5原有】记录明确失败反馈
                    if 'implementation' not in meta_data['steps']:
                        meta_data['steps']['implementation'] = {}
                    if 'test_feedback_history' not in meta_data['steps']['implementation']:
                        meta_data['steps']['implementation']['test_feedback_history'] = []

                    code_changes = meta_data.get('metrics', {}).get('code_changes', [])
                    feedback_entry = {
                        'timestamp': datetime.now().isoformat(),
                        'user_feedback': user_input,
                        'feedback_type': 'explicit_failure',
                        'clarification_requested': False,
                        'code_changes_count': len(code_changes)
                    }
                    meta_data['steps']['implementation']['test_feedback_history'].append(feedback_entry)

                    # 【v23.0新增】使用统一重置函数
                    _reset_planning_step(meta_data, reason='explicit_failure')

                    # 重置Implementation状态
                    meta_data['steps']['implementation']['status'] = 'pending'
                    meta_data['steps']['implementation']['user_confirmed'] = False

                    # 记录回滚历史
                    if 'rollback_history' not in meta_data:
                        meta_data['rollback_history'] = []

                    rollback_entry = {
                        'from_step': 'implementation',
                        'to_step': 'planning',
                        'reason': 'user_reported_fix_failed',
                        'timestamp': datetime.now().isoformat(),
                        'code_changes': meta_data.get('metrics', {}).get('code_changes', [])
                    }
                    meta_data['rollback_history'].append(rollback_entry)

                    # 【v23.0新增】记录状态转移
                    _log_state_transition(
                        meta_data,
                        from_step='implementation',
                        to_step='planning',
                        trigger='explicit_failure',
                        details={
                            'user_input': user_input,
                            'feedback_type': 'explicit_failure',
                            'code_changes_count': len(code_changes)
                        }
                    )

                    result['occurred'] = True
                    result['message'] = u"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 状态回滚: Implementation → Planning
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

你反馈修复失败，工作流已回滚到方案制定阶段。

**当前阶段**: Planning (方案)
**已保留**: 所有代码修改历史已记录到 rollback_history
**允许操作**: Read, Grep 等分析工具

AI将重新分析问题并制定新的修复方案。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

            # 【v22.7重构】优先级3：完全成功（原 FIXED_KEYWORDS 分支）
            elif has_success:
                # 【v23.1.1修正】恢复v23.0的快照调用（在状态转移前保存）
                _snapshot_step_state(meta_data, 'implementation')

                # 修复成功，进入收尾
                meta_data['current_step'] = 'finalization'
                result['new_step'] = 'finalization'

                if 'steps' not in meta_data:
                    meta_data['steps'] = {}
                if 'implementation' not in meta_data['steps']:
                    meta_data['steps']['implementation'] = {}

                # 【v22.5新增】记录明确成功反馈
                if 'test_feedback_history' not in meta_data['steps']['implementation']:
                    meta_data['steps']['implementation']['test_feedback_history'] = []

                code_changes = meta_data.get('metrics', {}).get('code_changes', [])
                feedback_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'user_feedback': user_input,
                    'feedback_type': 'explicit_success',
                    'clarification_requested': False,
                    'code_changes_count': len(code_changes)
                }
                meta_data['steps']['implementation']['test_feedback_history'].append(feedback_entry)

                meta_data['steps']['implementation']['user_confirmed'] = True
                meta_data['steps']['implementation']['confirmed_at'] = datetime.now().isoformat()

                # 【v22.7新增】完成Implementation阶段（与Planning→Implementation转移保持一致）
                meta_data['steps']['implementation']['status'] = 'completed'
                meta_data['steps']['implementation']['completed_at'] = datetime.now().isoformat()

                # 【v22.7新增】启动Finalization阶段（与Planning→Implementation转移保持一致）
                if 'finalization' not in meta_data['steps']:
                    meta_data['steps']['finalization'] = {}
                meta_data['steps']['finalization']['status'] = 'in_progress'
                meta_data['steps']['finalization']['started_at'] = datetime.now().isoformat()

                # 【v23.0新增】记录状态转移
                _log_state_transition(
                    meta_data,
                    from_step='implementation',
                    to_step='finalization',
                    trigger='explicit_success',
                    details={
                        'user_input': user_input,
                        'feedback_type': 'explicit_success',
                        'code_changes_count': len(code_changes)
                    }
                )

                result['occurred'] = True
                result['message'] = u"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 状态转移: Implementation → Finalization
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

你确认修复成功，工作流进入收尾归档阶段。

**当前阶段**: Finalization (收尾)
**自动操作**:
- 清理临时文件
- 生成任务摘要
- 归档到 tasks/{task_id}/

AI将自动完成任务归档。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

            # 【v22.7重构】优先级4：智能反馈检测（v22.5原有逻辑）
            else:
                # 【v23.1.1新增】continuation_request分支：保存快照并记录内部迭代
                # 用户输入不匹配任何关键词，视为持续反馈，保持在Implementation阶段

                # 获取代码修改记录
                code_changes = meta_data.get('metrics', {}).get('code_changes', [])
                has_code_changes = len(code_changes) > 0

                # 如果有代码修改，保存快照并记录内部迭代
                if has_code_changes:
                    _snapshot_step_state(meta_data, 'implementation')
                    _log_state_transition(
                        meta_data,
                        from_step='implementation',
                        to_step='implementation',
                        trigger='continuation_request',
                        details={
                            'user_input': user_input,
                            'feedback_type': 'continuation_request',
                            'code_changes_count': len(code_changes)
                        }
                    )

                # 【v22.5新增】智能反馈检测：处理所有非明确成功/失败的输入

                # 获取代码修改记录（重新获取，避免上面修改后的影响）
                code_changes = meta_data.get('metrics', {}).get('code_changes', [])
                has_code_changes = len(code_changes) > 0

                if has_code_changes:
                    # AI已完成代码修改，需要用户明确反馈测试结果

                    # 初始化测试反馈追踪（如果不存在）
                    if 'implementation' not in meta_data['steps']:
                        meta_data['steps']['implementation'] = {}
                    if 'test_feedback_history' not in meta_data['steps']['implementation']:
                        meta_data['steps']['implementation']['test_feedback_history'] = []

                    feedback_history = meta_data['steps']['implementation']['test_feedback_history']

                    # 检测模糊肯定表达
                    if match_keyword_safely(user_input_lower, AMBIGUOUS_POSITIVE):
                        # 记录模糊肯定反馈
                        feedback_entry = {
                            'timestamp': datetime.now().isoformat(),
                            'user_feedback': user_input,
                            'feedback_type': 'ambiguous_positive',
                            'clarification_requested': True,
                            'code_changes_count': len(code_changes)
                        }
                        feedback_history.append(feedback_entry)

                        # 检测循环：用户反复模糊反馈
                        ambiguous_count = sum(1 for f in feedback_history if f.get('feedback_type') == 'ambiguous_positive')

                        if ambiguous_count >= 3:
                            # 严厉警告：可能存在理解偏差
                            result['occurred'] = True
                            result['message'] = u"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚨 重复检测：多次模糊反馈（第{}次）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**检测到**: 你已经{}次使用模糊表达（如"同意"、"可以"），但从未明确反馈测试结果。

**当前状态**: Implementation阶段已完成 {} 次代码修改

**系统警告**:
- 如果你尚未测试，请先测试代码修改效果
- 如果你已经测试但不清楚如何反馈，请阅读下方说明

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 **明确反馈指南**：

✅ **修复成功**（BUG已解决或功能已实现）
   请输入以下任一表达：
   - "修复了" / "完成" / "成功"
   - "好了" / "可以了" / "done" / "fixed"
   → 工作流将进入 Finalization 阶段（收尾归档）

❌ **修复失败**（BUG仍存在或功能不符合预期）
   请输入以下任一表达：
   - "没修复" / "还有问题" / "失败"
   - "需要调整" / "没解决" / "没用"
   → 工作流将回滚到 Planning 阶段（重新分析根因）

🔄 **需要补充**（部分完成，需要继续修改）
   请描述具体的问题或需要补充的内容：
   - 例如："还需要添加XX功能"
   - 例如："YY场景下还有问题"
   → 工作流将保持在 Implementation 阶段继续修改

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ **重要说明**:
为确保任务质量，工作流需要你明确反馈测试结果。
如果你不确定如何测试，请告诉我，我可以提供测试建议。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(ambiguous_count, ambiguous_count, len(code_changes))
                        else:
                            # 首次或第二次模糊反馈：温和引导
                            result['occurred'] = True
                            result['message'] = u"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 需要明确的测试反馈
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**检测到**: 你的反馈是肯定的("{}")，但不够明确。

**当前状态**: Implementation阶段已完成 {} 次代码修改

**下一步**: 请测试代码修改效果，并明确反馈结果

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ **如果修复成功**，请输入：
  - "修复了" / "完成" / "成功" / "好了" / "done" / "fixed"
  → 工作流将进入 Finalization 阶段（收尾归档）

❌ **如果仍有问题**，请输入：
  - "没修复" / "还有问题" / "失败" / "需要调整"
  → 工作流将回滚到 Planning 阶段（重新分析）

🔄 **如果需要继续修改**，请描述：
  - 具体的问题或需要补充的功能
  → 工作流将保持在 Implementation 阶段继续修改

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 **提示**:
如果你尚未测试，请先测试代码修改效果，再返回反馈。
为防止误操作，工作流需要你明确选择一个选项。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(user_input[:20], len(code_changes))

                        # 不修改状态，保持 Implementation，等待明确反馈
                        # 注意：return meta_data 直接返回，不执行后续逻辑

                    else:
                        # 用户输入既不明确完成，也不明确失败，也不是模糊肯定
                        # 可能是继续描述问题或补充需求 → AI继续修改

                        # 记录补充需求反馈
                        feedback_entry = {
                            'timestamp': datetime.now().isoformat(),
                            'user_feedback': user_input,
                            'feedback_type': 'continuation_request',
                            'clarification_requested': False,
                            'code_changes_count': len(code_changes)
                        }
                        feedback_history.append(feedback_entry)

                        result['occurred'] = True
                        result['message'] = u"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💬 收到你的反馈
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**你的反馈**: {}

**当前状态**: Implementation阶段已完成 {} 次代码修改

**AI将根据你的反馈继续调整代码**。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 **提示**:
如果你已经测试完成，请明确反馈结果：
  - ✅ "修复了" / "完成" → 进入收尾阶段
  - ❌ "没修复" / "还有问题" → 重新分析问题

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(user_input[:50], len(code_changes))

                        # 不修改状态，保持 Implementation，AI继续工作
                else:
                    # 没有代码修改记录，可能是AI正在分析阶段
                    # 保持原有的 CONTINUE_KEYWORDS 逻辑（向后兼容）
                    if match_keyword_safely(user_input_lower, CONTINUE_KEYWORDS):
                        result['occurred'] = True
                        result['message'] = u"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
▶️ 继续修改
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

你要求继续修改，工作流保持在实施阶段。

**当前阶段**: Implementation (实施)
**操作**: AI将进入下一轮修改

请继续提供需要调整的具体内容。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
                    # 注意：状态不变，不修改 meta_data

        return meta_data

    # ========== 执行原子更新 ==========
    try:
        updated_meta = meta_manager.atomic_update(task_id, apply_state_transition)

        if not updated_meta:
            sys.stderr.write(u"[ERROR] 状态转移原子更新失败\n")
            return None

        # ========== 处理更新结果 ==========

        # 情况1: 被阻止（文档不足等）
        if result['blocked']:
            return {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": result['block_reason']
                },
                "continue": True
            }

        # 情况2: 发生状态转移或需要显示消息
        if result['occurred']:
            # 同步更新 .task-active.json
            if result['new_step']:  # 状态确实改变了
                meta_manager.set_active_task(task_id, result['new_step'])
                sys.stderr.write(u"[INFO v22.2] 状态转移成功: {} → {}\n".format(
                    result['old_step'], result['new_step']
                ))
            else:  # 状态未变（如"继续修改"）
                sys.stderr.write(u"[INFO v22.2] 用户确认，状态保持: {}\n".format(
                    result['old_step']
                ))

            return {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": result['message']
                },
                "continue": True
            }

        # 情况3: 未检测到状态转移关键词
        return None

    except Exception as e:
        sys.stderr.write(u"[ERROR] 状态转移异常: {}\n".format(e))
        import traceback
        traceback.print_exc(file=sys.stderr)
        return None



def is_bugfix_task(task_desc):
    """v20.2: Detect if task is BUG fix related"""
    import re
    task_lower = task_desc.lower()
    
    # BUG fix keywords (Chinese + English)
    bugfix_patterns = [
        r'(bug|error|exception|issue|problem)',
        r'(fix|repair|resolve|solve)',
        r'(not work|fail|crash|break)',
        r'(报错|错误|异常|问题|崩溃)',
        r'(修复|修改|解决)',
        r'(不工作|失败|不生效|没有效果)',
        r'(返回none|返回null|attributeerror)',
    ]
    
    for pattern in bugfix_patterns:
        if re.search(pattern, task_lower):
            return True
    return False

def format_fallback_guide():
    """降级方案:未匹配到玩法包时的通用指南"""
    return u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ℹ️ 未匹配到玩法包
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

当前任务未匹配到预定义的玩法包。

**建议做法**:
1. 分析任务需求，确定需要使用的MODSDK API
2. 查阅项目中的类似实现代码
3. 编写代码时注意遵守CRITICAL规范
4. Hook会在违规时自动阻断并提供修复建议

**重要提醒**:
- 无需提前阅读大量规范文档
- Hook会在编码时进行实时检查
- 遇到错误时会自动推送解决方案

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

def format_bugfix_guide(task_desc):
    """v22.1: BUG修复流程指引（强制专家审查）"""

    guidance = u"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    guidance += u"🐛 BUG修复工作流 v22.1（强制专家审查）\n"
    guidance += u"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    guidance += u"**当前阶段**: Planning（方案制定）\n"
    guidance += u"**核心策略**: 代码分析 → 方案制定 → **强制专家审查** → 用户确认 → Implementation\n\n"

    guidance += u"### 第1步：代码分析定位BUG\n\n"
    guidance += u"**推荐流程**:\n"
    guidance += u"1. 使用 Grep/Glob 定位相关代码文件\n"
    guidance += u"2. 使用 Read 阅读关键代码逻辑\n"
    guidance += u"3. 分析根本原因（而非表象）\n"
    guidance += u"4. 制定修复方案（明确要修改的文件和逻辑）\n\n"

    guidance += u"**可选**：如果代码逻辑不清楚，可以查阅项目文档理解设计意图\n\n"

    guidance += u"### 第2步：启动专家审查子代理（必须）\n\n"
    guidance += u"**重要**: BUG修复任务必须通过专家审查才能进入Implementation阶段\n\n"
    guidance += u"**操作**: 使用 Task 工具启动专家审查\n"
    guidance += u"```\n"
    guidance += u"Tool: Task\n"
    guidance += u"Parameters:\n"
    guidance += u"  subagent_type: \"general-purpose\"\n"
    guidance += u"  description: \"BUG修复方案审查\"\n"
    guidance += u"  prompt: |\n"
    guidance += u"    你是一位资深代码审查专家。请审查以下BUG修复方案：\n"
    guidance += u"    \n"
    guidance += u"    ## 问题描述\n"
    guidance += u"    [用户报告的BUG现象]\n"
    guidance += u"    \n"
    guidance += u"    ## 根本原因分析\n"
    guidance += u"    [你的分析：为什么会出现这个BUG]\n"
    guidance += u"    \n"
    guidance += u"    ## 修复方案\n"
    guidance += u"    [你计划修改的文件和具体逻辑]\n"
    guidance += u"    \n"
    guidance += u"    ## 潜在风险\n"
    guidance += u"    [这个修改可能引入的新问题]\n"
    guidance += u"    \n"
    guidance += u"    请验证：\n"
    guidance += u"    1. 根本原因分析是否正确（避免表象修复）\n"
    guidance += u"    2. 修复方案是否会引入新问题\n"
    guidance += u"    3. 是否有更好的替代方案\n"
    guidance += u"    \n"
    guidance += u"    请以以下格式返回审查结果：\n"
    guidance += u"    - 审查结论: pass / 需要调整\n"
    guidance += u"    - 问题点: [如果需要调整，说明具体问题]\n"
    guidance += u"    - 改进建议: [具体建议]\n"
    guidance += u"```\n\n"

    guidance += u"### 第3步：根据审查结果调整方案\n\n"
    guidance += u"**操作**: 等待子代理返回审查结果，根据建议调整方案\n\n"

    guidance += u"### 第4步：向用户确认\n\n"
    guidance += u"**触发关键词**: \"同意\" / \"可以\" / \"确认\"\n"
    guidance += u"**效果**: Hook会检查专家审查是否完成，完成后推进到Implementation阶段\n\n"

    guidance += u"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    guidance += u"⚠️ 重要提醒\n"
    guidance += u"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    guidance += u"1. **无需强制查阅文档**：required_doc_count=0\n"
    guidance += u"2. **禁止直接修改代码**：Planning阶段只能分析和制定方案\n"
    guidance += u"3. **强制专家审查**：未完成专家审查无法进入Implementation阶段\n"
    guidance += u"4. **状态持久化**：专家审查状态保存在task-meta.json，不受压缩影响\n\n"

    guidance += u"**立即开始**: 使用代码分析工具定位BUG根本原因\n"
    guidance += u"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

    return guidance

def generate_task_header(task_id, task_type, task_desc, project_name):
    """v20.2.17: 生成任务头部信息（明确显示任务类型）"""

    task_type_map = {
        "bug_fix": u"🐛 BUG修复",
        "feature_implementation": u"✨ 功能实现",
        "general": u"📝 通用任务"
    }

    task_type_display = task_type_map.get(task_type, u"📝 通用任务")

    return u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 任务信息 (v20.2.17)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**任务ID**: `{task_id}`
**任务类型**: {task_type_display}
**项目**: {project_name}
**描述**: {task_desc}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(
        task_id=task_id,
        task_type_display=task_type_display,
        project_name=project_name,
        task_desc=task_desc
    )

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

def detect_existing_task_dir(prompt, cwd):
    """v20.2.16: 检测用户输入中是否包含已存在的任务目录

    判断标准(用户确认):
    1. 用户使用了 /mc 命令
    2. 内容中包含一个能在 tasks/ 目录中找到的任务目录
    3. 满足条件 → resume模式

    返回:
        {
            "is_resume": bool,
            "task_dir": str,  # 绝对路径
            "task_id": str,   # 任务ID (目录名)
            "new_user_input": str  # 去除路径后的用户输入
        }
    """
    import re

    tasks_base_dir = os.path.join(cwd, 'tasks')

    # 如果 tasks/ 目录不存在,直接返回
    if not os.path.exists(tasks_base_dir):
        return {"is_resume": False}

    # 获取所有已存在的任务目录名
    try:
        existing_tasks = [d for d in os.listdir(tasks_base_dir)
                         if os.path.isdir(os.path.join(tasks_base_dir, d))
                         and d.startswith(u'任务-')]
    except Exception as e:
        sys.stderr.write(u"[WARN] 读取tasks目录失败: {}\n".format(e))
        return {"is_resume": False}

    if not existing_tasks:
        return {"is_resume": False}

    # 检测用户输入中是否包含任何已存在的任务目录
    # 支持多种路径格式:
    # 1. 完整绝对路径: D:\path\tasks\任务-XXXX-XXXXXX-描述
    # 2. 相对路径: tasks/任务-XXXX-XXXXXX-描述
    # 3. 仅任务ID: 任务-XXXX-XXXXXX-描述

    for task_id in existing_tasks:
        # 构造多种可能的匹配模式
        patterns = [
            re.escape(task_id),  # 精确匹配任务ID
            re.escape(os.path.join('tasks', task_id).replace('\\', '/')),  # tasks/任务-XXX (Unix风格)
            re.escape(os.path.join('tasks', task_id)),  # tasks\任务-XXX (Windows风格)
        ]

        # 尝试匹配
        for pattern in patterns:
            match = re.search(pattern, prompt, re.IGNORECASE)
            if match:
                task_dir = os.path.join(tasks_base_dir, task_id)

                # 验证 .task-meta.json 存在
                meta_path = os.path.join(task_dir, '.task-meta.json')
                if not os.path.exists(meta_path):
                    sys.stderr.write(u"[WARN] 检测到任务目录但缺少.task-meta.json: {}\n".format(task_dir))
                    continue

                # v20.2.16优化: 更彻底地清理路径
                # 提取新用户输入(去除路径部分)
                new_user_input = prompt

                # 1. 移除 /mc 命令
                new_user_input = new_user_input.replace('/mc', '').strip()

                # 2. 移除匹配到的完整路径部分（而非仅任务ID）
                matched_text = match.group(0)
                new_user_input = new_user_input.replace(matched_text, '').strip()

                # 3. 清理可能残留的路径前缀/后缀
                # 移除 Windows 风格路径前缀 (如 C:\...\tasks\, D:\...\tasks\)
                new_user_input = re.sub(r'^[A-Z]:[\\\/].*?tasks[\\\/]', '', new_user_input, flags=re.IGNORECASE).strip()
                # 移除 Unix 风格路径前缀 (如 /path/tasks/, ./tasks/)
                new_user_input = re.sub(r'^\.?\/.*?tasks\/', '', new_user_input).strip()
                # 移除单独的 tasks/ 或 tasks\ 前缀
                new_user_input = re.sub(r'^tasks[\\\/]', '', new_user_input, flags=re.IGNORECASE).strip()
                # 移除多余的路径分隔符
                new_user_input = re.sub(r'^[\\\/]+', '', new_user_input).strip()

                sys.stderr.write(u"[INFO v20.2.16] 检测到任务恢复意图\n")
                sys.stderr.write(u"  任务ID: {}\n".format(task_id))
                sys.stderr.write(u"  任务目录: {}\n".format(task_dir))
                sys.stderr.write(u"  匹配的文本: {}\n".format(matched_text))
                sys.stderr.write(u"  新用户输入: {}\n".format(new_user_input))

                return {
                    "is_resume": True,
                    "task_dir": task_dir,
                    "task_id": task_id,
                    "new_user_input": new_user_input
                }

    return {"is_resume": False}

def resume_existing_task(task_dir, task_id, new_user_input, cwd, session_id):
    """v3.1: 恢复已有任务的工作流（增加session_id参数）

    职责:
    1. 加载 .task-meta.json（唯一数据源）
    2. 更新恢复信息
    3. 绑定任务到当前会话（v3.1核心改动）
    4. 生成智能恢复提示(包含历史上下文)
    5. 记录恢复事件到 .conversation.jsonl

    Args:
        task_dir: 任务目录路径
        task_id: 任务ID
        new_user_input: 用户输入的新指令
        cwd: 工作目录
        session_id: 会话ID（v3.1新增）

    Returns:
        str: 智能恢复提示文本
    """
    # 使用 TaskMetaManager 加载任务元数据
    if not TaskMetaManager:
        raise Exception("TaskMetaManager 模块缺失，无法恢复任务")

    mgr = TaskMetaManager(cwd)

    # 1. 加载任务元数据（包含完整运行时状态）
    task_meta = mgr.load_task_meta(task_id)
    if not task_meta:
        raise Exception(u"加载 .task-meta.json 失败: 文件不存在或损坏")

    # 2. 更新恢复信息
    task_meta['resumed_at'] = datetime.now().isoformat()
    task_meta['resume_reason'] = new_user_input

    # 保存更新后的元数据
    if not mgr.save_task_meta(task_id, task_meta):
        sys.stderr.write(u"[WARN] 保存任务元数据失败\n")

    sys.stderr.write(u"[INFO v3.1] 任务元数据已加载（单一数据源模式）\n")

    # 3. 绑定任务到当前会话（v3.1核心改动）
    current_step = task_meta.get('current_step', 'implementation')
    if not mgr.bind_task_to_session(task_id, session_id):
        sys.stderr.write(u"[WARN] 绑定任务到会话失败\n")

    sys.stderr.write(u"[INFO v3.1] 任务已绑定到会话 {}\n".format(session_id[:8] + "..."))

    # 4. 记录恢复事件到 .conversation.jsonl
    conversation_file = os.path.join(task_dir, '.conversation.jsonl')
    try:
        with open(conversation_file, 'a', encoding='utf-8') as f:
            entry = {
                "timestamp": datetime.now().isoformat(),
                "role": "system",
                "content": u"任务恢复: {}".format(new_user_input),
                "event_type": "task_resume",
                "new_user_input": new_user_input
            }
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    except Exception as e:
        sys.stderr.write(u"[WARN] 记录会话历史失败: {}\n".format(e))

    # 5. 生成智能恢复提示(包含迭代历史)
    # v2.0: bug_fix_tracking 现在直接在 task_meta 中
    bug_fix_tracking = task_meta.get('bug_fix_tracking', {})
    feature_tracking = task_meta.get('feature_tracking', {})

    # 确定任务类型
    task_type = task_meta.get('task_type', 'unknown')
    if bug_fix_tracking.get('enabled'):
        task_type_display = u"🐛 BUG修复"
        iterations = bug_fix_tracking.get('iterations', [])
        loop_indicators = bug_fix_tracking.get('loop_indicators', {})
    elif feature_tracking.get('enabled'):
        task_type_display = u"✨ 功能实现"
        iterations = feature_tracking.get('iterations', [])
        loop_indicators = {}
    else:
        task_type_display = u"📝 通用任务"
        iterations = []
        loop_indicators = {}

    # 构建恢复提示
    resume_prompt = u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 **任务恢复模式已激活** (v2.0)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**任务ID**: {}
**任务类型**: {}
**原始需求**: {}
**当前步骤**: {}
**已完成迭代**: {}次

""".format(
        task_id,
        task_type_display,
        task_meta.get('task_description', ''),
        task_meta.get('current_step', 'unknown'),
        len(iterations)
    )

    # 历史迭代摘要
    if iterations:
        resume_prompt += u"## 📜 历史迭代摘要\n\n"
        # 只显示最近3次迭代
        recent_iterations = iterations[-3:]
        for it in recent_iterations:
            resume_prompt += u"### 迭代 {}\n".format(it.get('iteration_id', '?'))
            resume_prompt += u"- **时间**: {}\n".format(it.get('timestamp', ''))
            resume_prompt += u"- **用户反馈**: {}\n".format(it.get('user_feedback', ''))
            resume_prompt += u"- **情感**: {}\n\n".format(it.get('feedback_sentiment', ''))

    # 循环风险警告
    if len(iterations) >= 2 and loop_indicators:
        resume_prompt += u"""
⚠️ **循环风险警告**:
- 同文件修改次数: {}
- 负面反馈次数: {}
- 测试失败次数: {}

""".format(
            loop_indicators.get('same_file_edit_count', 0),
            loop_indicators.get('negative_feedback_count', 0),
            loop_indicators.get('failed_test_count', 0)
        )

    # 用户新需求
    if new_user_input:
        resume_prompt += u"""
## 🎯 用户新需求

{}

""".format(new_user_input)

    # 恢复任务建议
    resume_prompt += u"""
## 📋 恢复任务建议

1. ✅ **查看历史会话**:
   ```
   Read("tasks/{}/context.md")  # 查看问题分析(如存在)
   Read("tasks/{}/solution.md")  # 查看已尝试的方案(如存在)
   ```

2. ✅ **查看代码修改历史**:
   - 检查 `.task-meta.json` 中的 `metrics.code_changes`
   - 了解之前修改了哪些文件

3. ✅ **分析失败原因**:
   - 为什么之前的尝试失败了?
   - 是否存在错误的假设?
   - 用户反馈中的关键信息是什么?

4. ✅ **制定新策略**:
   - 基于历史经验调整方案
   - 避免重复已失败的路径
   - 聚焦用户新提出的问题

""".format(task_id, task_id)

    # 专家审查提示
    if len(iterations) >= 1:
        resume_prompt += u"""
5. ⚠️ **专家审查提示**:
   - 当前已有 {} 次迭代历史
   - 如果本次仍然失败,专家审查系统将自动触发
   - 专家系统会提供根因分析和备选方案

""".format(len(iterations))

    resume_prompt += u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**立即开始**: 基于历史上下文,继续任务实施
"""

    return resume_prompt

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

        # === v3.2: 检测是否是 /mc 命令 ===
        if not cmd_info['is_mc_command']:
            # 非 /mc 命令，先检查是否是状态转移关键词（v3.0 Final新增）
            # 注意：状态转移检测仍然使用原始prompt（因为用户可能直接输入"同意"、"修复了"等）
            state_transition_result = handle_state_transition(prompt, cwd, session_id)

            if state_transition_result:
                # 是状态转移命令，输出结果并退出
                print(json.dumps(state_transition_result, ensure_ascii=False))
                sys.exit(0)
            else:
                # 非状态转移命令，放行
                output = {"continue": True}
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

        # === v3.1: 时间戳模糊匹配检测 ===
        # 检测格式：161424 继续修改 或 1116-161424（注意：v3.2已剥离/mc前缀）
        # v3.2修复：直接在command_args中匹配，不再需要/mc前缀
        timestamp_pattern = r'^([\d-]{4,11})(?:\s+(.*))?$'
        timestamp_match = re.match(timestamp_pattern, cmd_info['command_args'].strip())

        if timestamp_match:
            timestamp = timestamp_match.group(1)  # 提取时间戳
            new_user_input = timestamp_match.group(2) or ""  # 提取补充描述

            sys.stderr.write(u"[INFO v3.1] 检测到时间戳模糊匹配: {}\n".format(timestamp))

            if TaskMetaManager:
                mgr = TaskMetaManager(cwd)
                task_id = mgr.fuzzy_match_task_by_timestamp(timestamp)

                if task_id:
                    sys.stderr.write(u"[INFO v3.1] 匹配到任务: {}\n".format(task_id))

                    # 执行任务恢复流程
                    try:
                        task_dir = mgr.get_task_dir(task_id)
                        resume_prompt = resume_existing_task(
                            task_dir,
                            task_id,
                            new_user_input,
                            cwd,
                            session_id  # v3.1新增：传入session_id
                        )

                        # 输出恢复提示
                        output = {
                            "hookSpecificOutput": {
                                "hookEventName": "UserPromptSubmit",
                                "additionalContext": resume_prompt
                            },
                            "continue": True
                        }
                        print(json.dumps(output, ensure_ascii=False))

                        # VSCode通知
                        try:
                            notify_info(
                                u"✅ 任务已恢复（时间戳匹配）| {}".format(task_id[:30]),
                                u"继续执行: {}".format(new_user_input[:40] if new_user_input else "继续上一次工作")
                            )
                        except:
                            pass

                        sys.exit(0)

                    except Exception as e:
                        sys.stderr.write(u"[ERROR] 时间戳匹配恢复失败: {}\n".format(e))
                        import traceback
                        traceback.print_exc(file=sys.stderr)

                        # 降级：提示错误，让用户重新输入
                        output = {
                            "hookSpecificOutput": {
                                "hookEventName": "UserPromptSubmit",
                                "additionalContext": u"❌ 任务恢复失败: {}\n请使用完整任务路径重试".format(str(e))
                            },
                            "continue": False,
                            "stopReason": "task_resume_failed"
                        }
                        print(json.dumps(output, ensure_ascii=False))
                        sys.exit(0)
                else:
                    # 没有匹配到任务
                    output = {
                        "hookSpecificOutput": {
                            "hookEventName": "UserPromptSubmit",
                            "additionalContext": u"""
❌ 未找到匹配的任务

时间戳 `{}` 没有匹配到任何已存在的任务。

**建议**:
1. 检查时间戳是否正确（格式：MMDD-HHMMSS，如 1116-161424）
2. 查看 `tasks/` 目录确认任务是否存在
3. 使用完整任务路径：`/mc tasks/<任务目录> 继续修改`
""".format(timestamp)
                        },
                        "continue": False,
                        "stopReason": "task_not_found"
                    }
                    print(json.dumps(output, ensure_ascii=False))
                    sys.exit(0)

        # === v20.2.16: 任务恢复检测 ===
        # v3.2修复：使用提取的command_args
        resume_info = detect_existing_task_dir(cmd_info['command_args'], cwd)

        if resume_info['is_resume']:
            sys.stderr.write(u"[INFO v20.2.16] 进入任务恢复模式\n")

            # 执行任务恢复流程
            try:
                resume_prompt = resume_existing_task(
                    resume_info['task_dir'],
                    resume_info['task_id'],
                    resume_info['new_user_input'],
                    cwd,
                    session_id  # v3.1新增：传入session_id
                )

                # 输出控制JSON（官方格式 v20.2.17）
                output = {
                    "hookSpecificOutput": {
                        "hookEventName": "UserPromptSubmit",
                        "additionalContext": resume_prompt
                    },
                    "continue": True
                }
                print(json.dumps(output, ensure_ascii=False))

                # VSCode 通知
                try:
                    notify_info(
                        u"✅ 任务已恢复 | {}".format(resume_info['task_id']),
                        u"继续执行: {}".format(resume_info['new_user_input'][:40])
                    )
                except:
                    pass

                sys.exit(0)

            except Exception as e:
                sys.stderr.write(u"[ERROR] 任务恢复失败: {}\n".format(e))
                import traceback
                traceback.print_exc(file=sys.stderr)

                # 降级到新任务创建模式
                sys.stderr.write(u"[WARN] 降级到新任务创建模式\n")
                # 继续执行下面的新任务创建流程

        # === 新任务创建流程 ===

        # v3.2修复：使用提取的command_args作为任务描述
        task_desc = cmd_info['command_args'].strip().strip('"\'')

        # v3.2新增：参数验证
        if not task_desc:
            # 没有任务描述，提示用户
            sys.stderr.write(u"[ERROR v3.2] 缺少任务描述\n")

            output = {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ 缺少任务描述
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**用法**: `/mc <任务描述>`

**示例**:
- `/mc 修复玩家死亡复活丢失装备的BUG`
- `/mc 实现金币系统`
- `/mc 1116-201326 继续修改`（恢复已有任务）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
                },
                "continue": False,
                "stopReason": "missing_task_description"
            }
            print(json.dumps(output, ensure_ascii=False))
            sys.exit(0)

        # 生成任务ID - v20.2.5: 尝试保留中文，依赖stdin编码修复
        timestamp = datetime.now().strftime('%m%d-%H%M%S')
        max_desc_length = get_max_task_desc_length(cwd)
        safe_desc = task_desc[:max_desc_length]
        for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
            safe_desc = safe_desc.replace(char, '-')
        task_id = u"任务-{}-{}".format(timestamp, safe_desc)

        # 创建任务目录 (v20.2.6: 增强验证)
        task_dir = os.path.join(cwd, 'tasks', task_id)
        if not ensure_dir(task_dir):
            # 目录创建失败，阻塞流程
            sys.stderr.write(u"[CRITICAL] 任务初始化失败：无法创建任务目录\n")
            sys.stderr.write(u"  任务ID: {}\n".format(task_id))
            sys.stderr.write(u"  目标路径: {}\n".format(task_dir))
            sys.stderr.write(u"  可能原因：路径编码问题、权限不足、磁盘空间不足\n")

            output = {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": u"""
❌ 任务初始化失败

**问题**: 无法创建任务目录

**任务ID**: {}
**目标路径**: {}

**可能原因**:
1. 路径包含无效字符（中文路径编码问题）
2. 磁盘权限不足
3. 磁盘空间不足
4. 父目录不存在

**建议**:
1. 检查 tasks/ 目录是否存在且可写
2. 检查磁盘空间
3. 如果是 Windows 系统，确认路径不包含特殊字符
4. 查看上方 stderr 输出获取详细错误信息

**注意**: Hook 已阻止任务继续，请修复后重试
""".format(task_id, task_dir)
                },
                "continue": False,
                "stopReason": "task_init_failed"
            }
            print(json.dumps(output, ensure_ascii=False))
            sys.exit(2)  # exit 2 = 阻塞错误

        # === 玩法包匹配 (v19.0 新增) ===
        kb_path = os.path.join(cwd, '.claude', 'knowledge-base.json')
        knowledge_base = load_knowledge_base(kb_path)
        matched_pattern = find_best_gameplay_pattern(task_desc, knowledge_base)

        if matched_pattern:
            gameplay_pack_content = format_gameplay_pack(matched_pattern)
            pack_info = u"匹配成功: {}".format(matched_pattern['name'])
            sys.stderr.write(u"[INFO] 玩法包匹配: {} (score: {:.2f})\n".format(
                matched_pattern['name'],
                calculate_match_score(task_desc, matched_pattern.get('keywords', []))
            ))
        else:
            # v22.0: 任务类型路由（BUG修复使用专家审查流程）
            is_bugfix = is_bugfix_task(task_desc)
            sys.stderr.write(u"[DEBUG v22.0] is_bugfix_task result: {}\n".format(is_bugfix))

            if is_bugfix:
                try:
                    gameplay_pack_content = format_bugfix_guide(task_desc)
                    pack_info = u"BUG修复任务,启用专家审查机制 (v22.0)"
                    sys.stderr.write(u"[INFO] BUG修复模式激活,代码分析+专家审查流程已注入\n")
                except Exception as e:
                    sys.stderr.write(u"[ERROR] BUG修复指引生成失败: {}\n".format(e))
                    import traceback
                    traceback.print_exc(file=sys.stderr)
                    # 降级到通用指南
                    gameplay_pack_content = format_fallback_guide()
                    pack_info = u"BUG修复指引生成失败,使用通用指南"
            else:
                gameplay_pack_content = format_fallback_guide()
                pack_info = u"未匹配,使用通用指南"
                sys.stderr.write(u"[INFO] 未匹配到玩法包,使用降级方案\n")

        # v2.0/v3.0 Final: 创建任务元数据（唯一数据源，包含完整运行时状态）
        task_type = "bug_fix" if is_bugfix_task(task_desc) else "general"

        # v3.0 Final: 动态required_doc_count（根据task_type差异化设置）
        # 符合设计文档《Hooks状态机功能实现.md》:1440行
        if task_type == "bug_fix":
            required_doc_count = 0  # BUG修复: 无强制文档要求，触发专家审查
        elif matched_pattern:
            required_doc_count = 2  # 玩法包模式
        else:
            required_doc_count = 3  # 标准功能设计模式

        task_meta = {
            # 基础元数据
            "task_id": task_id,
            "task_description": task_desc,
            "task_type": task_type,
            "task_complexity": "standard",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "architecture_version": "v3.0 Final",

            # 运行时状态（v3.0 Final: 语义化4步状态机 - 从planning开始）
            "current_step": "planning",
            "last_injection_step": None,
            "steps": {
                # v3.0 Final: 语义化4步状态机
                "activation": {
                    "description": u"任务激活（自动）",
                    "status": "completed",
                    "completed_at": datetime.now().isoformat(),
                    "prompt": u"（v3.0 Final: 任务类型识别已自动完成）"
                },
                "planning": {
                    "description": u"方案制定阶段",
                    "status": "in_progress",
                    "started_at": datetime.now().isoformat(),
                    "required_doc_count": required_doc_count,

                    # v22.1新增：专家审查追踪（仅BUG修复任务）
                    "expert_review_required": (task_type == "bug_fix"),  # BUG修复强制专家审查
                    "expert_review_completed": False,                    # 专家审查是否完成
                    "expert_review_count": 0,                            # 专家审查次数
                    "expert_review_result": None,                        # 审查结果（pass/需要调整）

                    "prompt": (
                        u"直接分析代码，制定修复方案，**启动专家审查子代理**，等待用户确认后进入implementation。"
                        if task_type == "bug_fix"
                        else u"查阅至少{}个相关文档，制定修复/实现方案，等待用户确认后进入implementation。".format(required_doc_count)
                    )
                },
                "implementation": {
                    "description": u"代码实施",
                    "status": "pending",
                    "user_confirmed": False,
                    "prompt": u"基于确认的方案，实施代码修改，测试验证，直到用户确认完成。"
                },
                "finalization": {
                    "description": u"收尾归档",
                    "status": "pending",
                    "prompt": u"清理DEBUG代码，更新文档，归档任务。"
                }
            },

            # 玩法包追踪
            "gameplay_pack_matched": matched_pattern['id'] if matched_pattern else None,
            "gameplay_pack_name": matched_pattern['name'] if matched_pattern else None,

            # v2.0: 性能指标（BUG修复：必须初始化，PostToolUse Hook依赖）
            # v3.0 Final: 修复字段名 tool_calls → tools_used（匹配文档标准）
            "metrics": {
                "docs_read": [],
                "code_changes": [],
                "tools_used": [],  # Fix: 使用v3.0 Final标准字段名
                "failure_count": 0,
                "expert_review_triggered": False
            },

            # 会话追踪
            "session_started_at": datetime.now().isoformat(),
            "session_ended_at": None,

            # 归档状态
            "archived": False,
            "failed": False
        }

        # v2.0: BUG修复模式 - 立即初始化追踪状态
        if is_bugfix_task(task_desc):
            task_meta["bug_fix_tracking"] = {
                "enabled": True,
                "matched_gameplay_pack": matched_pattern['id'] if matched_pattern else None,
                "bug_description": task_desc,
                "iterations": [],
                "loop_indicators": {
                    "same_file_edit_count": 0,
                    "failed_test_count": 0,
                    "negative_feedback_count": 0,
                    "time_spent_minutes": 0
                },
                "expert_triggered": False
            }
            sys.stderr.write(u"[INFO v2.0] BUG修复追踪已初始化（玩法包: %s）\n" % (matched_pattern['id'] if matched_pattern else "None"))

        # 【v23.0新增】记录任务初始化的状态转移(null → planning)
        _log_state_transition(
            task_meta,
            from_step=None,
            to_step='planning',
            trigger='task_initialized',
            details={
                'user_input': task_desc,
                'task_type': task_type,
                'gameplay_pack_matched': matched_pattern['id'] if matched_pattern else None
            }
        )

        # 使用 TaskMetaManager 保存任务元数据
        if TaskMetaManager:
            mgr = TaskMetaManager(cwd)
            if not mgr.save_task_meta(task_id, task_meta):
                sys.stderr.write(u"[ERROR] 保存任务元数据失败\n")
                raise Exception("任务元数据保存失败")
        else:
            # 降级方案：直接写入文件
            meta_file = os.path.join(task_dir, '.task-meta.json')
            with open(meta_file, 'w', encoding='utf-8') as f:
                json.dump(task_meta, f, indent=2, ensure_ascii=False)

        sys.stderr.write(u"[INFO v2.0] 任务元数据已创建（单一数据源模式）\n")

        # 创建 .task-active.json（v3.1: 使用会话绑定）
        if TaskMetaManager:
            mgr = TaskMetaManager(cwd)
            # v3.1核心改动：绑定任务到当前会话
            if not mgr.bind_task_to_session(task_id, session_id):
                sys.stderr.write(u"[WARN] 绑定任务失败\n")
        else:
            # 降级方案：不创建绑定（TaskMetaManager不可用时）
            sys.stderr.write(u"[ERROR] TaskMetaManager不可用，无法创建任务绑定\n")

        # === v20.2.7: 创建会话历史文件（方案B - 持久化会话历史）===
        conversation_file = os.path.join(task_dir, '.conversation.jsonl')
        try:
            with open(conversation_file, 'w', encoding='utf-8') as f:
                # 记录初始用户输入
                entry = {
                    "timestamp": datetime.now().isoformat(),
                    "role": "user",
                    "content": prompt,
                    "event_type": "task_init"
                }
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
            sys.stderr.write(u"[INFO] 会话历史文件已创建: {}\n".format(conversation_file))
        except Exception as e:
            sys.stderr.write(u"[WARN] 会话历史文件创建失败: {}\n".format(e))
            # 不阻塞主流程

        # v20.3.1新增: 创建context.md和solution.md（解决BUG #4）
        # 原因: stop.py Hook依赖context.md检查用户确认
        # 原因: 任务恢复功能依赖这些文件获取历史上下文
        try:
            context_file = os.path.join(task_dir, 'context.md')
            with open(context_file, 'w', encoding='utf-8') as f:
                f.write(u"""# {}

## 任务分析

（请在此记录问题分析、根本原因定位）

## 关键发现

（请记录查阅文档的关键发现、设计思路）

## 实施方案

（请记录具体修改方案）

## 测试验证

（请记录测试步骤和验证结果）

## 用户确认

用户确认: 否

（当问题修复后，请将上方改为"用户确认: 是"）
""".format(task_desc))
            sys.stderr.write(u"[INFO] context.md已创建\n")

            solution_file = os.path.join(task_dir, 'solution.md')
            with open(solution_file, 'w', encoding='utf-8') as f:
                f.write(u"""# 解决方案记录

## 修改文件清单

（自动生成，无需手动填写）

## 迭代历史

### 迭代1

（请记录每次迭代的修改内容）

""")
            sys.stderr.write(u"[INFO] solution.md已创建\n")

        except Exception as e:
            sys.stderr.write(u"[WARN] 任务文件创建失败: {}\n".format(e))
            # 不阻塞主流程

        # 📢 通知1：任务启动 - 步骤3开始（玩法包模式）
        try:
            notify_info(
                u"步骤3：执行实施 | 玩法包: {}".format(pack_info),
                u"{}".format(task_desc[:40])
            )
        except:
            pass  # 通知失败不影响主流程

        # v2.0: 生成任务头部信息 + 任务边界声明
        project_name = os.path.basename(cwd)
        task_header = generate_task_header(task_id, task_type, task_desc, project_name)
        task_boundary = generate_task_boundary_notice(task_id, task_desc, task_type)

        # 构建注入内容（任务头部 + 边界声明 + 玩法包 + 任务追踪提醒）
        injected_content = task_header + task_boundary + gameplay_pack_content + u"""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 任务追踪系统已激活
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**任务目录**: tasks/{}/

**重要提醒**:
1. 上方玩法包已提供完整实现代码
2. 你可以直接使用或根据需求修改
3. Hook会自动检查CRITICAL规范，无需担心违规
4. 如遇错误，Hook会自动推送精确的修复方案
5. 必须等待用户明确确认"已修复"才能结束任务

**立即行动**: 基于玩法包开始实现
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(task_id)

        output = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": injected_content
            },
            "continue": True
        }

        # 输出到stdout（Claude会读取）
        print(json.dumps(output, ensure_ascii=False))

        # VSCode 右下角弹窗通知
        notify_info(
            u"✅ 任务追踪已初始化 | {}".format(pack_info),
            u"任务ID: {} | 目录: tasks/{}/".format(task_id, task_id)
        )

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
