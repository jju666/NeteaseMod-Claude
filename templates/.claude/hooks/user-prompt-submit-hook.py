#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Hook 1: UserPromptSubmit - 任务初始化拦截器 + 玩法包注入器 (v19.0)
当检测到 /mc 命令时，自动创建任务追踪基础设施并注入匹配的玩法包

触发时机: 用户提交提示词后
工作机制:
1. 检测 /mc 命令
2. 自动创建 tasks/{task_id}/ 目录结构
3. 初始化 context.md, solution.md, .task-meta.json
4. 匹配玩法知识库，注入完整代码实现
5. 注入任务追踪提醒到对话

退出码:
- 0: 成功，继续执行
- 2: 阻止操作
- 1: 非阻塞错误
"""

import sys
import json
import os
from datetime import datetime
import io

# 修复Windows编码问题：强制使用UTF-8 (v20.2.5增强)
if sys.platform == 'win32':
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='replace')
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 导入VSCode通知模块
try:
    from vscode_notify import notify_info, notify_warning, notify_error
except ImportError:
    # 降级方案：纯文本输出
    def notify_info(msg, detail=""): sys.stderr.write(u"ℹ️ {} {}\n".format(msg, detail))
    def notify_warning(msg, detail=""): sys.stderr.write(u"⚠️ {} {}\n".format(msg, detail))
    def notify_error(msg, detail=""): sys.stderr.write(u"❌ {} {}\n".format(msg, detail))

# 导入工作流配置加载器 (v20.2.4)
try:
    from workflow_config_loader import get_max_task_desc_length
except ImportError:
    def get_max_task_desc_length(project_path=None):
        return 8  # 默认值

def ensure_dir(path):
    """确保目录存在 - 增强验证版 (v20.2.6)

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

def analyze_bug_symptom(task_desc):
    """v20.2: 分析BUG症状类型"""
    import re
    task_lower = task_desc.lower()

    # API错误
    if re.search(r'(attributeerror|notimplementederror|keyerror|api.*not.*work)', task_lower):
        return ("api_error", u"API调用错误")

    # 生命周期错误
    if re.search(r'(初始化|加载|卸载|生命周期|lifecycle)', task_lower):
        return ("lifecycle_error", u"生命周期管理问题")

    # CRITICAL违规
    if re.search(r'(client.*server|同步|tick)', task_lower):
        return ("critical_violation", u"CRITICAL规范违规")

    # 性能问题
    if re.search(r'(卡顿|延迟|性能|performance)', task_lower):
        return ("performance", u"性能问题")

    # 业务逻辑 (默认)
    return ("business_logic", u"业务逻辑BUG")

def route_knowledge_sources(symptom_type, task_desc):
    """v20.2: 根据症状类型路由知识源"""
    routes = {
        "business_logic": {
            "strategy": u"项目文档优先 → 代码实现",
            "guidance_note": u"💡 业务逻辑问题通常记录在项目markdown文档中"
        },
        "api_error": {
            "strategy": u"常见问题速查 → API文档",
            "guidance_note": u"💡 11个常见问题覆盖90%的API错误"
        },
        "lifecycle_error": {
            "strategy": u"CRITICAL规范 → 生命周期文档",
            "guidance_note": u"💡 生命周期问题多为违反规范导致"
        },
        "critical_violation": {
            "strategy": u"CRITICAL规范 → 双端隔离文档",
            "guidance_note": u"💡 检查是否违反12项CRITICAL规则"
        },
        "performance": {
            "strategy": u"性能优化指南 → Profiling",
            "guidance_note": u"💡 常见性能问题已有标准化解决方案"
        }
    }
    return routes.get(symptom_type, routes["business_logic"])

def extract_business_keywords(task_desc):
    """v20.2: 提取业务关键词（用于文档搜索）"""
    import re
    # 移除常见停用词
    stop_words = [u'修复', u'问题', u'BUG', u'bug', u'错误', u'不', u'无法', u'没有', u'tests', u'目录', u'中']
    words = re.findall(r'[\u4e00-\u9fa5]+', task_desc)
    keywords = [w for w in words if w not in stop_words and len(w) >= 2]
    return keywords[:3]  # 返回前3个关键词

def format_bugfix_guide(task_desc):
    """v20.2: BUG修复智能指引"""
    # 分析症状
    symptom_type, symptom_desc = analyze_bug_symptom(task_desc)
    route = route_knowledge_sources(symptom_type, task_desc)
    keywords = []
    if symptom_type == "business_logic":
        keywords = extract_business_keywords(task_desc)

    # 构建指引
    guidance = u"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    guidance += u"🐛 智能BUG修复系统 v20.2\n"
    guidance += u"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    guidance += u"**症状**: {}\n".format(symptom_desc)
    guidance += u"**策略**: {}\n\n".format(route["strategy"])

    # 差异化指引
    if symptom_type == "business_logic" and keywords:
        guidance += u"### 第1步: 查阅项目文档（⭐优先）\n\n"
        guidance += u"关键词: {}\n".format(u', '.join(keywords[:2]))
        guidance += u"```\nGlob(\"markdown/**/*{}*.md\")\n```\n".format(keywords[0])
        guidance += u"理解设计意图 → 定位代码 → 验证一致性\n\n"
        guidance += route.get("guidance_note", u"") + u"\n\n"
    elif symptom_type == "api_error":
        guidance += u"### 第1步: 快速匹配常见错误\n\n"
        guidance += u"```\nRead(\".claude/core-docs/核心工作流文档/问题排查.md\", offset=1, limit=150)\n```\n"
        guidance += u"11个常见问题速查 → 验证API用法\n\n"
        guidance += route.get("guidance_note", u"") + u"\n\n"
    elif symptom_type in ["lifecycle_error", "critical_violation"]:
        guidance += u"### 第1步: 查阅CRITICAL规范\n\n"
        guidance += u"```\nRead(\".claude/core-docs/核心工作流文档/开发规范.md\", offset=20, limit=100)\n```\n"
        guidance += u"验证规范违规 → 定位问题代码\n\n"
        guidance += route.get("guidance_note", u"") + u"\n\n"
    elif symptom_type == "performance":
        guidance += u"### 第1步: 性能优化指南\n\n"
        guidance += u"```\nRead(\".claude/core-docs/深度指南/性能优化完整指南.md\")\n```\n"
        guidance += u"问题12-15: 卡顿/延迟/内存问题\n\n"
    else:
        guidance += u"### 混合探索\n\n"
        guidance += u"先查项目文档 → 再查常见问题 → 动态调整\n\n"

    # 通用结尾
    guidance += u"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    guidance += u"⚠️ 提示: 文档不存在→降级探索 | 文档过期→以代码为准\n"
    guidance += u"**重要**: 本次BUG修复无需启动子代理，Hook会自动检查规范\n"
    guidance += u"**立即开始**: 执行上述第1步查阅\n"
    guidance += u"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

    return guidance

def main():
    try:
        # 读取stdin输入
        data = json.load(sys.stdin)

        prompt = data.get('prompt', '')
        cwd = os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd())

        # 检测是否是 /mc 命令
        if not prompt.strip().startswith('/mc '):
            # 非 /mc 命令，放行（输出控制JSON）
            output = {"continue": True}
            print(json.dumps(output, ensure_ascii=False))
            sys.exit(0)

        # 提取任务描述
        task_desc = prompt.replace('/mc ', '').strip().strip('"\'')

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
                "continue": False,
                "stopReason": "task_init_failed",
                "injectedContext": u"""
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
            # v20.2: Intelligent routing based on task type
            is_bugfix = is_bugfix_task(task_desc)
            sys.stderr.write(u"[DEBUG v20.2] is_bugfix_task result: {}\n".format(is_bugfix))

            if is_bugfix:
                try:
                    gameplay_pack_content = format_bugfix_guide(task_desc)
                    pack_info = u"BUG修复任务,启用智能诊断 (v20.2)"
                    sys.stderr.write(u"[INFO] BUG修复模式激活,智能诊断系统已注入\n")
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

        # 创建工作流状态文件（用于后续hook协调）
        workflow_state = {
            "task_id": task_id,
            "task_description": task_desc,
            "task_type": "bug_fix" if (not matched_pattern and is_bugfix_task(task_desc)) else "general",  # v20.2.5
            "created_at": datetime.now().isoformat(),
            "current_step": "step3_execute",  # v20.2: 玩法包已提供代码，跳过step0/1直接执行
            "last_injection_step": None,
            "steps": {
                "step0_context": {
                    "description": u"阅读项目CLAUDE.md",
                    "status": "skipped",  # 玩法包已提供完整上下文
                    "prompt": u"（玩法包模式：已跳过）"
                },
                "step1_understand": {
                    "description": u"理解任务需求",
                    "status": "skipped",  # 玩法包已提供完整代码
                    "prompt": u"（玩法包模式：已跳过）"
                },
                "step3_execute": {
                    "description": u"执行实施",
                    "status": "in_progress",
                    "started_at": datetime.now().isoformat(),
                    "user_confirmed": False,
                    "prompt": u"基于玩法包代码实现功能，测试验证，直到用户确认修复完成。"
                },
                "step4_cleanup": {
                    "description": u"收尾归档",
                    "status": "pending",
                    "prompt": u"清理DEBUG代码，更新文档，归档任务。"
                }
            },
            "gameplay_pack_matched": matched_pattern['id'] if matched_pattern else None,
            "gameplay_pack_name": matched_pattern['name'] if matched_pattern else None
        }

        # v20.2.5: BUG修复模式 - 立即初始化追踪状态
        if not matched_pattern and is_bugfix_task(task_desc):
            workflow_state["bug_fix_tracking"] = {
                "enabled": True,
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
            sys.stderr.write(u"[INFO] BUG修复追踪已初始化\n")

        # 保存workflow-state.json
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
            "created_at": datetime.now().isoformat()
        }

        active_file = os.path.join(cwd, '.claude', '.task-active.json')
        with open(active_file, 'w', encoding='utf-8') as f:
            json.dump(active_flag, f, indent=2, ensure_ascii=False)

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

        # 📢 通知1：任务启动 - 步骤3开始（玩法包模式）
        try:
            notify_info(
                u"步骤3：执行实施 | 玩法包: {}".format(pack_info),
                u"{}".format(task_desc[:40])
            )
        except:
            pass  # 通知失败不影响主流程

        # 构建注入内容（玩法包 + 任务追踪提醒）
        injected_content = gameplay_pack_content + u"""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 任务追踪系统已激活
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**任务ID**: {}
**任务目录**: tasks/{}/

**重要提醒**:
1. 上方玩法包已提供完整实现代码
2. 你可以直接使用或根据需求修改
3. Hook会自动检查CRITICAL规范，无需担心违规
4. 如遇错误，Hook会自动推送精确的修复方案
5. 必须等待用户明确确认"已修复"才能结束任务

**立即行动**: 基于玩法包开始实现
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(task_id, task_id)

        output = {
            "continue": True,
            "injectedContext": injected_content
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
        sys.stderr.write(u"[ERROR] Hook执行失败: {}\n".format(e))
        import traceback
        traceback.print_exc(file=sys.stderr)

        # v20.2.5: 错误回滚 - 清理不完整的状态文件
        try:
            cwd = os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd())
            state_file = os.path.join(cwd, '.claude', 'workflow-state.json')
            active_file = os.path.join(cwd, '.claude', '.task-active.json')

            # 删除损坏的状态文件
            for f in [state_file, active_file]:
                if os.path.exists(f):
                    # 检查文件是否完整
                    try:
                        with open(f, 'r', encoding='utf-8') as fp:
                            json.load(fp)
                    except (json.JSONDecodeError, ValueError):
                        sys.stderr.write(u"[ROLLBACK] 删除损坏的状态文件: {}\n".format(f))
                        os.remove(f)
        except Exception as rollback_err:
            sys.stderr.write(u"[WARN] 回滚清理失败: {}\n".format(rollback_err))

        sys.exit(1)  # 非阻塞错误

if __name__ == '__main__':
    main()
