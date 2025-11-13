#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成增强版 user-prompt-submit-hook.py (v19.0)
包含玩法包注入功能
"""

import os
import sys
import io

# 修复Windows GBK编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

HOOK_CODE = r'''#!/usr/bin/env python
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

# 修复Windows GBK编码问题：强制使用UTF-8输出
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 导入VSCode通知模块
try:
    from vscode_notify import notify_info, notify_warning, notify_error
except ImportError:
    # 降级方案：纯文本输出
    def notify_info(msg, detail=""): sys.stderr.write(u"ℹ️ {} {}\n".format(msg, detail))
    def notify_warning(msg, detail=""): sys.stderr.write(u"⚠️ {} {}\n".format(msg, detail))
    def notify_error(msg, detail=""): sys.stderr.write(u"❌ {} {}\n".format(msg, detail))

def ensure_dir(path):
    """确保目录存在"""
    try:
        if not os.path.exists(path):
            os.makedirs(path)
    except Exception as e:
        sys.stderr.write("[ERROR] 创建目录失败: {}\n".format(e))

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
        if score > 0.15:  # 相似度阈值降低到15%,提高召回率
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

def format_fallback_guide():
    """降级方案：未匹配到玩法包时的通用指南"""
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

def main():
    try:
        # 读取stdin输入
        data = json.load(sys.stdin)

        user_prompt = data.get('prompt', '')
        cwd = os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd())

        # 检测是否是 /mc 命令
        if not user_prompt.strip().startswith('/mc '):
            # 非 /mc 命令，放行（输出控制JSON）
            output = {"continue": True}
            print(json.dumps(output, ensure_ascii=False))
            sys.exit(0)

        # 提取任务描述
        task_desc = user_prompt.replace('/mc ', '').strip().strip('"\'')

        # 生成任务ID（时间戳格式 + 中文描述）
        timestamp = datetime.now().strftime('%m%d-%H%M%S')
        # 清理任务描述：移除不安全的文件名字符
        safe_desc = task_desc[:30]  # 限制长度
        for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
            safe_desc = safe_desc.replace(char, '-')
        task_id = u"任务-{}-{}".format(timestamp, safe_desc)

        # 创建任务目录
        task_dir = os.path.join(cwd, 'tasks', task_id)
        ensure_dir(task_dir)

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
            gameplay_pack_content = format_fallback_guide()
            pack_info = u"未匹配,使用通用指南"
            sys.stderr.write(u"[INFO] 未匹配到玩法包,使用降级方案\n")

        # 创建工作流状态文件（用于后续hook协调）
        workflow_state = {
            "task_id": task_id,
            "task_description": task_desc,
            "created_at": datetime.now().isoformat(),
            "current_step": 1,
            "steps_completed": {
                "step1_understanding": False,
                "step2_doc_reading": False,
                "step2_doc_count": 0,
                "step2_5_self_check": False,
                "step3_execution": False
            },
            "docs_read": [],
            "failure_count": 0,
            "expert_review_triggered": False,
            "gameplay_pack_matched": matched_pattern['id'] if matched_pattern else None,
            "gameplay_pack_name": matched_pattern['name'] if matched_pattern else None
        }

        state_file = os.path.join(cwd, '.claude', 'workflow-state.json')
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(workflow_state, f, indent=2, ensure_ascii=False)

        # 📢 通知1：任务启动 - 步骤1开始
        try:
            notify_info(
                u"步骤1：理解任务 | 玩法包: {}".format(pack_info),
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
        sys.stderr.write("[ERROR] Hook执行失败: {}\n".format(e))
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)  # 非阻塞错误

if __name__ == '__main__':
    main()
'''

def main():
    # 写入到目标位置
    output_path = os.path.join(
        os.path.dirname(__file__),
        '..',
        'templates',
        '.claude',
        'hooks',
        'user-prompt-submit-hook.py'
    )

    output_path = os.path.abspath(output_path)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(HOOK_CODE)

    print(u"✅ 增强版 hook 已生成: {}".format(output_path))

if __name__ == '__main__':
    main()
