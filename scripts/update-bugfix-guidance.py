# -*- coding: utf-8 -*-
"""
临时脚本：更新 user-prompt-submit-hook.py 中的 inject_bugfix_guidance 函数
"""
import re
import sys

def main():
    file_path = r"d:\EcWork\基于Claude的MODSDK开发工作流\templates\.claude\hooks\user-prompt-submit-hook.py"

    # 读取文件
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 旧的函数体（要替换的部分）
    old_pattern = r'''    guidance = u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🐛 BUG修复模式已激活
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

\*\*任务类型\*\*: BUG修复
\*\*复杂度\*\*: \{\}

\*\*BUG修复流程建议\*\*:

1\. \*\*问题定位\*\* \(使用工具快速搜索\)
   - 使用 Grep 搜索错误相关关键词 \(如: "玩家死亡", "背包", "掉落"\)
   - 使用 Glob 查找可能相关的 System 文件
   - 使用 Read 阅读可疑文件，定位具体代码行

2\. \*\*原因分析\*\* \(可能的BUG类型\)
   - API使用错误
   - 事件监听遗漏
   - 生命周期问题
   - 双端隔离违规
   - 逻辑错误

   💡 如遇到不熟悉的API/事件，按需查阅 \.claude/core-docs/ 中的文档

3\. \*\*修复验证\*\*
   - 修改代码后，Hook会自动检查CRITICAL规范
   - 建议运行测试验证修复效果

\*\*重要提醒\*\*:
- 本次任务为BUG修复，无需启动子代理
- 你应该自己使用 Grep/Glob/Read 工具定位问题
- Hook会在你修改代码时自动检查规范

\*\*立即开始\*\*: 使用 Grep 搜索 BUG 相关关键词
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""\.format\(complexity_names\.get\(complexity, complexity\)\)
    return guidance'''

    # 新的函数体
    new_code = '''    # v20.2: 智能诊断
    symptom_type, symptom_desc = analyze_bug_symptom(task_desc)
    route = route_knowledge_sources(symptom_type, task_desc)
    keywords = []
    if route.get("extract_keywords"):
        keywords = extract_business_keywords(task_desc)

    # 构建指引
    guidance = u"\\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n"
    guidance += u"🐛 智能BUG修复系统 v20.2\\n"
    guidance += u"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n\\n"
    guidance += u"**症状**: {}\\n".format(symptom_desc)
    guidance += u"**策略**: {}\\n".format(route["strategy"])
    guidance += u"**复杂度**: {}\\n\\n".format(complexity_names.get(complexity, complexity))

    # 差异化指引
    if symptom_type == "business_logic" and keywords:
        guidance += u"### 第1步: 查阅项目文档（⭐优先）\\n\\n"
        guidance += u"关键词: {}\\n".format(u', '.join(keywords[:2]))
        guidance += u"```\\nGlob(\\"markdown/**/*{}*.md\\")\\n```\\n".format(keywords[0])
        guidance += u"理解设计意图 → 定位代码 → 验证一致性\\n\\n"
        guidance += route.get("guidance_note", "") + u"\\n\\n"
    elif symptom_type == "api_error":
        guidance += u"### 第1步: 快速匹配常见错误\\n\\n"
        guidance += u"```\\nRead(\\".claude/core-docs/核心工作流文档/问题排查.md\\", offset=1, limit=150)\\n```\\n"
        guidance += u"11个常见问题速查 → 验证API用法\\n\\n"
        guidance += route.get("guidance_note", "") + u"\\n\\n"
    elif symptom_type in ["lifecycle_error", "critical_violation"]:
        guidance += u"### 第1步: 查阅CRITICAL规范\\n\\n"
        guidance += u"```\\nRead(\\".claude/core-docs/核心工作流文档/开发规范.md\\", offset=20, limit=100)\\n```\\n"
        guidance += u"验证规范违规 → 定位问题代码\\n\\n"
        guidance += route.get("guidance_note", "") + u"\\n\\n"
    elif symptom_type == "performance":
        guidance += u"### 第1步: 性能优化指南\\n\\n"
        guidance += u"```\\nRead(\\".claude/core-docs/深度指南/性能优化完整指南.md\\")\\n```\\n"
        guidance += u"问题12-15: 卡顿/延迟/内存问题\\n\\n"
    else:
        guidance += u"### 混合探索\\n\\n"
        guidance += u"先查项目文档 → 再查常见问题 → 动态调整\\n\\n"

    # 通用结尾
    guidance += u"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n"
    guidance += u"⚠️ 提示: 文档不存在→降级探索 | 文档过期→以代码为准\\n"
    guidance += u"**重要**: 本次BUG修复无需启动子代理，Hook会自动检查规范\\n"
    guidance += u"**立即开始**: 执行上述第1步查阅\\n"
    guidance += u"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n"

    return guidance'''

    # 执行替换
    new_content = re.sub(old_pattern, new_code, content, flags=re.DOTALL)

    if new_content == content:
        print("未找到匹配的代码块，替换失败", file=sys.stderr)
        sys.exit(1)

    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print("✅ 成功更新 inject_bugfix_guidance 函数")

if __name__ == '__main__':
    main()
