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

# v20.3.1: 导入任务取消处理器
try:
    from task_cancellation_handler import handle_cancellation_from_user_prompt
except ImportError:
    # 降级方案：禁用取消功能
    def handle_cancellation_from_user_prompt(user_input, cwd):
        return None
    sys.stderr.write(u"[WARN] 任务取消功能不可用（task_cancellation_handler模块缺失）\n")

# v21.0: 导入任务元数据管理器（单一数据源架构）
HOOK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HOOK_DIR)

try:
    from core.task_meta_manager import TaskMetaManager
except ImportError:
    sys.stderr.write(u"[WARN] TaskMetaManager模块缺失，任务恢复功能可能受限\n")
    TaskMetaManager = None

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
        # v20.3.1增强: 明确区分Glob和Grep的使用场景（解决BUG #5）
        guidance += u"```python\n"
        guidance += u"# 查找文件名包含关键词的文档（使用Glob工具）\n"
        guidance += u"Glob(\"markdown/**/*{}*.md\")\n".format(keywords[0])
        guidance += u"\n# 如果没有找到，再搜索文件内容（使用Grep工具）\n"
        guidance += u"Grep(pattern=\"{}\", path=\"markdown\", output_mode=\"files_with_matches\")\n".format(keywords[0])
        guidance += u"```\n"
        guidance += u"**工具选择原则**:\n"
        guidance += u"- Glob: 查找文件名（快速定位）\n"
        guidance += u"- Grep: 搜索文件内容（深度查找）\n"
        guidance += u"- Read: 阅读具体文件\n\n"
        guidance += u"理解设计意图 → 定位代码 → 验证一致性\n\n"
        guidance += route.get("guidance_note", u"") + u"\n\n"
    elif symptom_type == "api_error":
        guidance += u"### 第1步: 快速匹配常见错误\n\n"
        guidance += u"```python\n"
        guidance += u"Read(\"markdown/core/问题排查.md\", offset=1, limit=150)\n"
        guidance += u"```\n"
        guidance += u"11个常见问题速查 → 验证API用法\n\n"
        guidance += route.get("guidance_note", u"") + u"\n\n"
    elif symptom_type in ["lifecycle_error", "critical_violation"]:
        guidance += u"### 第1步: 查阅CRITICAL规范\n\n"
        guidance += u"```python\n"
        guidance += u"Read(\"markdown/core/开发规范.md\", offset=20, limit=100)\n"
        guidance += u"```\n"
        guidance += u"验证规范违规 → 定位问题代码\n\n"
        guidance += route.get("guidance_note", u"") + u"\n\n"
    elif symptom_type == "performance":
        guidance += u"### 第1步: 性能优化指南\n\n"
        guidance += u"```python\n"
        guidance += u"Read(\"markdown/深度指南/性能优化完整指南.md\")\n"
        guidance += u"```\n"
        guidance += u"问题12-15: 卡顿/延迟/内存问题\n\n"
    else:
        guidance += u"### 混合探索\n\n"
        guidance += u"先查项目文档 → 再查常见问题 → 动态调整\n\n"

    # 通用结尾
    guidance += u"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    guidance += u"⚠️ 提示: 文档不存在→降级探索 | 文档过期→以代码为准\n"
    guidance += u"**重要**: 本次BUG修复无需启动子代理，Hook会自动检查规范\n"
    guidance += u"**立即开始**: 严格按照上述工具调用示例执行第1步\n"  # v20.3.1强化引导
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

def resume_existing_task(task_dir, task_id, new_user_input, cwd):
    """v21.0: 恢复已有任务的工作流（简化版）

    职责:
    1. 加载 .task-meta.json（唯一数据源）
    2. 更新恢复信息
    3. 更新 .task-active.json
    4. 生成智能恢复提示(包含历史上下文)
    5. 记录恢复事件到 .conversation.jsonl

    返回:
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

    sys.stderr.write(u"[INFO v21.0] 任务元数据已加载（单一数据源模式）\n")

    # 3. 更新.task-active.json
    current_step = task_meta.get('current_step', 'step3_execute')
    if not mgr.set_active_task(task_id, current_step):
        sys.stderr.write(u"[WARN] 设置活跃任务失败\n")

    sys.stderr.write(u"[INFO] .task-active.json已更新\n")

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
    # v21.0: bug_fix_tracking 现在直接在 task_meta 中
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
🔄 **任务恢复模式已激活** (v21.0)
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

        # === v20.3.1: 任务取消/失败检测 ===
        cancellation_message = handle_cancellation_from_user_prompt(prompt, cwd)

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

        # === v20.2.16: 任务恢复检测 ===
        resume_info = detect_existing_task_dir(prompt, cwd)

        if resume_info['is_resume']:
            sys.stderr.write(u"[INFO v20.2.16] 进入任务恢复模式\n")

            # 执行任务恢复流程
            try:
                resume_prompt = resume_existing_task(
                    resume_info['task_dir'],
                    resume_info['task_id'],
                    resume_info['new_user_input'],
                    cwd
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

        # v21.0/v22.0: 创建任务元数据（唯一数据源，包含完整运行时状态）
        task_type = "bug_fix" if is_bugfix_task(task_desc) else "general"

        # v22.1: 动态required_doc_count（差异化配置）
        # BUG修复: 0文档（依赖专家审查）
        # 玩法包匹配: 2文档（降低难度）
        # 通用任务: 1文档（简化流程，避免过度严格）
        if task_type == "bug_fix":
            required_doc_count = 0
        elif matched_pattern:
            required_doc_count = 2
        else:
            # 通用任务：简化文档要求（从3降低到1）
            required_doc_count = 1

        task_meta = {
            # 基础元数据
            "task_id": task_id,
            "task_description": task_desc,
            "task_type": task_type,
            "task_complexity": "standard",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "architecture_version": "v21.0",

            # 运行时状态（v22.0: 所有任务强制从step2_research开始）
            "current_step": "step2_research",
            "last_injection_step": None,
            "steps": {
                # v21.0: step0_context 和 step1_understand 已废弃（保留以兼容旧数据）
                "step0_context": {
                    "description": u"阅读项目CLAUDE.md（已废弃）",
                    "status": "skipped",
                    "prompt": u"（v21.0: 已废弃，所有任务从 step2_research 开始）"
                },
                "step1_understand": {
                    "description": u"理解任务需求（已废弃）",
                    "status": "skipped",
                    "prompt": u"（v21.0: 已废弃，所有任务从 step2_research 开始）"
                },
                "step2_research": {
                    "description": u"任务研究阶段（强制）",
                    "status": "in_progress",
                    "started_at": datetime.now().isoformat(),
                    "required_doc_count": required_doc_count,
                    "prompt": u"查阅至少{}个相关文档，理解问题根因和技术约束，明确说明研究结论后Hook自动推进到step3。".format(required_doc_count)
                },
                "step3_execute": {
                    "description": u"执行实施",
                    "status": "pending",
                    "user_confirmed": False,
                    "prompt": u"基于充分的文档研究，实施代码修改，测试验证，直到用户确认修复完成。"
                },
                "step4_cleanup": {
                    "description": u"收尾归档",
                    "status": "pending",
                    "prompt": u"清理DEBUG代码，更新文档，归档任务。"
                }
            },

            # 玩法包追踪
            "gameplay_pack_matched": matched_pattern['id'] if matched_pattern else None,
            "gameplay_pack_name": matched_pattern['name'] if matched_pattern else None,

            # v21.0: 性能指标（BUG修复：必须初始化，PostToolUse Hook依赖）
            "metrics": {
                "docs_read": [],
                "code_changes": [],
                "tool_calls": [],
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

        # v21.0: BUG修复模式 - 立即初始化追踪状态
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
            sys.stderr.write(u"[INFO v21.0] BUG修复追踪已初始化（玩法包: %s）\n" % (matched_pattern['id'] if matched_pattern else "None"))

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

        sys.stderr.write(u"[INFO v21.0] 任务元数据已创建（单一数据源模式）\n")

        # 创建 .task-active.json（使用 TaskMetaManager）
        if TaskMetaManager:
            mgr = TaskMetaManager(cwd)
            if not mgr.set_active_task(task_id, "step2_research"):
                sys.stderr.write(u"[WARN] 设置活跃任务失败\n")
        else:
            # 降级方案：直接写入文件
            active_flag = {
                "task_id": task_id,
                "task_dir": task_dir,
                "current_step": "step2_research",
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

        # v21.0: 生成任务头部信息 + 任务边界声明
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
        sys.stderr.write(u"[ERROR] Hook执行失败: {}\n".format(e))
        import traceback
        traceback.print_exc(file=sys.stderr)

        # v21.0: 错误回滚 - 清理不完整的状态文件
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

        sys.exit(1)  # 非阻塞错误

if __name__ == '__main__':
    main()
