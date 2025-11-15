#!/usr/bin/env python3
"""
NeteaseMod-Claude Hook: API用法验证
触发时机: PreToolUse (Edit/Write 之前)
功能: 检查常见API误用模式,推荐正确用法
作者: NeteaseMod-Claude Workflow
版本: v18.4.0 (阶段1优化 - API用法检查)
"""

import json
import sys
import re
import io

# 修复Windows GBK编码问题：强制使用UTF-8输出
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# API误用模式检查表
API_VALIDATION_RULES = [
    {
        "pattern": r"CreateComponent\s*\(\s*['\"](?!Minecraft\.|mod\.)[^'\"]+['\"]",
        "severity": "warning",
        "rule": "API最佳实践: Component命名规范",
        "description": "Component名称应使用完整命名空间(Minecraft.xxx 或 mod.xxx)",
        "solution": "使用完整命名空间,例如: 'Minecraft.PlayerComponent'",
        "doc_ref": ".claude/core-docs/核心工作流文档/开发规范.md 第4章(约330行)",
        "doc_snippet": """
⚠️ 不推荐:
self.CreateComponent('PlayerComp')  # 缺少命名空间

✅ 推荐:
self.CreateComponent('Minecraft.PlayerComp')  # 完整命名空间
"""
    },
    {
        "pattern": r"ListenForEvent\s*\(\s*['\"][^'\"]+['\"].*\)\s*$",
        "severity": "warning",
        "rule": "API最佳实践: 事件监听器未保存",
        "description": "ListenForEvent返回的监听器ID未保存,可能导致无法取消监听",
        "solution": "保存监听器ID到实例变量,便于后续UnListenForEvent",
        "doc_ref": ".claude/core-docs/核心工作流文档/开发规范.md 第5章(约380行)",
        "doc_snippet": """
⚠️ 不推荐:
self.ListenForEvent(...)  # 未保存ID

✅ 推荐:
self.listener_id = self.ListenForEvent(...)

def Destroy(self):
    self.UnListenForEvent(self.listener_id)
"""
    },
    {
        "pattern": r"GetEngineCompFactory\(\)\.Create(?:Component)?[^(]*\([^)]*\)\s*(?!#.*保存)",
        "severity": "info",
        "rule": "API最佳实践: 引擎组件未保存引用",
        "description": "引擎组件创建后未保存引用,后续无法使用",
        "solution": "将组件引用保存到实例变量",
        "doc_ref": ".claude/core-docs/核心工作流文档/开发规范.md 第4章(约340行)",
        "doc_snippet": """
❌ 错误:
factory.CreateAttrComp(entityId)  # 创建后丢失引用

✅ 正确:
self.attr_comp = factory.CreateAttrComp(entityId)
self.attr_comp.SetAttr(...)  # 后续可使用
"""
    },
    {
        "pattern": r"NotifyToClient\([^,]+,[^,]+,\s*['\"]",
        "severity": "warning",
        "rule": "API误用: NotifyToClient第三参数应为dict",
        "description": "NotifyToClient第三参数传递了字符串,应传递dict",
        "solution": "将事件数据封装为dict: {'key': 'value'}",
        "doc_ref": ".claude/core-docs/核心工作流文档/开发规范.md 第5章(约400行)",
        "doc_snippet": """
❌ 错误:
self.NotifyToClient(playerId, 'Event', 'data')  # ❌ 字符串

✅ 正确:
self.NotifyToClient(playerId, 'Event', {'data': 'value'})  # ✅ dict
"""
    },
    {
        "pattern": r"GetSystem\s*\(\s*0\s*,\s*['\"]Mods\.",
        "severity": "info",
        "rule": "API最佳实践: GetSystem命名空间",
        "description": "GetSystem使用了'Mods.'前缀,现代写法推荐省略或使用项目特定前缀",
        "solution": "检查项目配置,确认System命名空间约定",
        "doc_ref": ".claude/core-docs/核心工作流文档/开发规范.md 第3章(约280行)",
        "doc_snippet": """
⚠️ 旧写法:
self.GetSystem(0, 'Mods.XXX.XXXSystem')

✅ 现代写法(根据项目配置):
self.GetSystem(0, 'XXXSystem')  # 或
self.GetSystem(0, 'ProjectName.XXXSystem')
"""
    },
    {
        "pattern": r"DestroyEntity\s*\([^)]+\)(?!\s*#.*检查返回值)",
        "severity": "warning",
        "rule": "API最佳实践: 未检查DestroyEntity返回值",
        "description": "DestroyEntity可能失败,应检查返回值",
        "solution": "检查返回值,处理删除失败情况",
        "doc_ref": ".claude/core-docs/核心工作流文档/开发规范.md 第6章(约450行)",
        "doc_snippet": """
⚠️ 不推荐:
self.DestroyEntity(entityId)  # 未检查返回值

✅ 推荐:
success = self.DestroyEntity(entityId)
if not success:
    print("实体删除失败: %s" % entityId)
"""
    }
]

def main():
    """主函数:从stdin读取JSON,检查API用法"""
    try:
        # 从stdin读取JSON输入
        input_data = json.load(sys.stdin)

        # 提取关键字段
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        # 只检查Edit和Write工具
        if tool_name not in ["Edit", "Write"]:
            print(json.dumps({
                "continue": True,
                "decision": "approve",
                "reason": "跳过检查（非Edit/Write操作）"
            }))
            sys.exit(0)

        # 获取文件路径和内容
        file_path = tool_input.get("file_path", "")
        new_string = tool_input.get("new_string", "")
        content = tool_input.get("content", "")

        # 只检查Python文件
        if file_path and not file_path.endswith(".py"):
            print(json.dumps({
                "continue": True,
                "decision": "approve",
                "reason": "跳过非Python文件"
            }))
            sys.exit(0)

        # 获取要检查的代码内容
        check_content = new_string if new_string else content

        if not check_content:
            print(json.dumps({
                "continue": True,
                "decision": "approve",
                "reason": "无内容需检查"
            }))
            sys.exit(0)

        # 执行API用法检查
        warnings = validate_api_usage(check_content)

        if not warnings:
            # 通过检查
            print(json.dumps({
                "continue": True,
                "decision": "approve",
                "reason": "✅ API用法检查通过"
            }))
            sys.exit(0)
        else:
            # 发现警告,但不阻断操作(仅提示)
            reason_lines = ["💡 API用法提示(非阻断):\n"]
            reason_lines.append("=" * 60)

            for i, warning in enumerate(warnings, 1):
                severity_icon = {
                    "warning": "⚠️",
                    "info": "ℹ️",
                    "error": "❌"
                }.get(warning['severity'], "💡")

                reason_lines.append(f"\n【提示{i}】{severity_icon} {warning['rule']}")
                reason_lines.append(f"📝 说明: {warning['description']}")
                reason_lines.append(f"✅ 建议: {warning['solution']}")
                reason_lines.append(f"📚 文档: {warning['doc_ref']}")
                reason_lines.append(f"\n💡 示例:{warning['doc_snippet']}")
                reason_lines.append("-" * 60)

            reason_lines.append("\n🔍 以上为最佳实践建议,代码仍可正常运行")
            reason_lines.append("💡 建议参考示例优化代码质量")

            # 不阻断操作,只通过stdout输出提示
            print(json.dumps({
                "continue": True,
                "decision": "approve",
                "reason": "\n".join(reason_lines),
                "hookSpecificOutput": {
                    "warnings": warnings,
                    "enhancement_version": "v18.4.0"
                }
            }, ensure_ascii=False))
            sys.exit(0)

    except Exception as e:
        # 异常时不阻断，只输出警告
        print(json.dumps({
            "continue": True,
            "decision": "approve",
            "reason": f"⚠️ Hook执行异常（已跳过检查）: {str(e)}"
        }))
        sys.exit(0)


def validate_api_usage(code_content):
    """
    检查API用法,返回警告列表

    Args:
        code_content: 要检查的Python代码内容

    Returns:
        list: 警告详情列表
    """
    warnings = []

    for rule in API_VALIDATION_RULES:
        if re.search(rule["pattern"], code_content, re.MULTILINE):
            warnings.append({
                "severity": rule["severity"],
                "rule": rule["rule"],
                "description": rule["description"],
                "solution": rule["solution"],
                "doc_ref": rule["doc_ref"],
                "doc_snippet": rule["doc_snippet"]
            })

    return warnings


if __name__ == "__main__":
    main()
