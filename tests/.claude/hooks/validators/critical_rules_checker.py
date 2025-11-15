#!/usr/bin/env python3
"""
NeteaseMod-Claude Hook: CRITICAL规范检查(v19.1增强版)
触发时机: PreToolUse (Edit/Write 之前)
功能: 检查是否违反12项CRITICAL规范,并提供精确文档章节引用
作者: NeteaseMod-Claude Workflow
版本: v19.1.0 (扩展规则5-12)
更新日志:
  - v19.1.0: 新增8项规则检查(print语法、模块导入、编码声明等)
  - v18.5.0: 更新为官方Hook格式
  - v18.0.0: 初始版本(4项基础规则)
"""

import json
import sys
import re
import io

# 修复Windows GBK编码问题:强制使用UTF-8输出
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Import notification module (v20.1)
try:
    from vscode_notify import notify_error
except ImportError:
    def notify_error(msg, detail=""): pass


def main():
    """主函数:从stdin读取JSON,检查CRITICAL规范"""
    try:
        # 从stdin读取JSON输入
        input_data = json.load(sys.stdin)

        # 提取关键字段
        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        # 只检查Edit和Write工具
        if tool_name not in ["Edit", "Write"]:
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    "permissionDecisionReason": "跳过检查(非Edit/Write操作)"
                },
                "suppressOutput": True
            }))
            sys.exit(0)

        # 获取文件路径和内容
        file_path = tool_input.get("file_path", "")
        new_string = tool_input.get("new_string", "")
        content = tool_input.get("content", "")

        # 只检查Python文件
        if file_path and not file_path.endswith(".py"):
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    "permissionDecisionReason": "跳过非Python文件"
                },
                "suppressOutput": True
            }))
            sys.exit(0)

        # Skip checking Hook scripts themselves to avoid false positives
        if file_path:
            path_normalized = file_path.replace("\\", "/")
            if ".claude/hooks" in path_normalized:
                print(json.dumps({
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "allow",
                        "permissionDecisionReason": "Skip Hook script check"
                    },
                    "suppressOutput": True
                }))
                sys.exit(0)

        # For Edit operations: check if original file has UTF-8 declaration
        # v20.2 fix: Skip encoding check for code snippets if file has declaration
        skip_encoding_check = False
        sys.stderr.write("[v20.2 DEBUG] tool_name={}, file_path={}, has_new_string={}\\n".format(tool_name, file_path, bool(new_string)))
        if tool_name == "Edit" and file_path and new_string:
            try:
                # Use os module (already imported at line 116 for violation tracking)
                import os as os_module
                check_path = file_path
                if not os_module.path.isabs(file_path):
                    cwd = os_module.environ.get('CLAUDE_PROJECT_DIR', os_module.getcwd())
                    check_path = os_module.path.join(cwd, file_path)

                if check_path.endswith(".py") and os_module.path.exists(check_path):
                    with open(check_path, 'r', encoding='utf-8') as file_check:
                        first_lines = [file_check.readline() for _ in range(3)]
                        file_content = ''.join(first_lines)
                        if re.search(r'#.*?coding[:=]\s*utf-?8', file_content, re.IGNORECASE):
                            skip_encoding_check = True
                            sys.stderr.write("[v20.2.6 INFO] File has UTF-8 declaration, skipping encoding check: {}\\n".format(file_path))
                        else:
                            sys.stderr.write("[v20.2.6 DEBUG] No UTF-8 declaration found in first 3 lines: {}\\n".format(file_path))
            except Exception as skip_check_error:
                sys.stderr.write("[v20.2 ERROR] Skip check failed: {}\\n".format(skip_check_error))

        # Get content to check
        check_content = new_string if new_string else content

        if not check_content:
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    "permissionDecisionReason": "无内容需检查"
                },
                "suppressOutput": True
            }))
            sys.exit(0)

        # Execute CRITICAL rule check
        violations = check_critical_rules(check_content, skip_encoding_check)

        if not violations:
            # 通过检查
            # v20.3: 支持详细模式（通过环境变量控制）
            import os
            VERBOSE_MODE = os.getenv("CLAUDE_HOOK_VERBOSE", "false").lower() == "true"

            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    "permissionDecisionReason": "✅ CRITICAL规范检查通过"
                },
                "suppressOutput": not VERBOSE_MODE  # 详细模式下显示
            }

            # 详细模式：输出到stderr让用户知道Hook在工作
            if VERBOSE_MODE:
                sys.stderr.write("✅ CRITICAL规范检查通过 ({})\n".format(file_path))

            print(json.dumps(output))
            sys.exit(0)
        else:
            # 发现违规,阻断操作并提供精准文档引导
            # v20.1: Update CRITICAL violation counter
            try:
                import os
                cwd = os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd())
                active_flag_path = os.path.join(cwd, '.claude', '.task-active.json')

                if os.path.exists(active_flag_path):
                    with open(active_flag_path, 'r', encoding='utf-8') as f:
                        import json as json2
                        active_flag = json2.load(f)

                    task_dir = active_flag.get("task_dir", "")
                    meta_path = os.path.join(task_dir, '.task-meta.json')

                    if os.path.exists(meta_path):
                        with open(meta_path, 'r', encoding='utf-8') as f:
                            meta = json2.load(f)

                        # Increase CRITICAL violation count
                        if "critical_violation_count" not in meta["metrics"]:
                            meta["metrics"]["critical_violation_count"] = 0
                        meta["metrics"]["critical_violation_count"] += 1

                        with open(meta_path, 'w', encoding='utf-8') as f:
                            json2.dump(meta, f, indent=2, ensure_ascii=False)
            except:
                pass  # Update failure doesn't affect main flow

            # Desktop notification
            try:
                notify_error(
                    "CRITICAL rule violation",
                    "Detected {} violations, operation blocked".format(len(violations))
                )
            except:
                pass

            reason_lines = ["❌ 检测到CRITICAL规范违规,操作已阻断\n"]
            reason_lines.append("=" * 60)

            for i, violation in enumerate(violations, 1):
                reason_lines.append(f"\n【违规{i}】{violation['rule']}")
                reason_lines.append(f"❌ 问题: {violation['description']}")
                reason_lines.append(f"✅ 解决: {violation['solution']}")
                reason_lines.append(f"📚 文档: {violation['doc_ref']}")
                reason_lines.append(f"\n💡 示例代码:{violation['doc_snippet']}")
                reason_lines.append("-" * 60)

            reason_lines.append("\n🔍 无需Read完整文档,Hook已提供精确章节和示例代码")
            reason_lines.append("💡 直接根据上述'解决方案'和'示例代码'修改即可")

            # 使用官方推荐的PreToolUse输出格式
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "\n".join(reason_lines)
                }
            }, ensure_ascii=False))
            sys.exit(0)

    except Exception as e:
        # 异常时不阻断,只输出警告
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": f"⚠️ Hook执行异常(已跳过检查): {str(e)}"
            },
            "suppressOutput": True
        }))
        sys.exit(0)


def check_critical_rules(code_content, skip_encoding_check=False):
    """
    Check 12 CRITICAL rules (v19.1 Enhanced + v20.2 UTF-8 fix)

    Args:
        code_content: Python code content to check
        skip_encoding_check: Skip UTF-8 encoding check for Edit operations (v20.2)

    Returns:
        list: Violation details list with {rule, description, doc_ref}
    """
    violations = []

    # ===================================================================
    # 规范1: 双端隔离原则
    # 禁止: 跨端GetSystem(服务端获取客户端System或反之)
    # ===================================================================
    if re.search(r'class\s+\w+\s*\(\s*ServerSystem\s*\)', code_content):
        # 这是一个ServerSystem
        # 修复: 允许GetSystem有多个参数,如GetSystem(0, "ClientSystem")
        if re.search(r'GetSystem\s*\([^)]*["\'].*Client.*System["\']', code_content):
            violations.append({
                "rule": "规范1: 双端隔离原则",
                "description": "服务端尝试获取客户端System(禁止跨端GetSystem)",
                "solution": "使用 NotifyToClient() 发送事件通知客户端,而非直接GetSystem",
                "doc_ref": ".claude/core-docs/核心工作流文档/开发规范.md 第2.1节(约150-180行)",
                "doc_snippet": """
⛔ 禁止: self.GetSystem(0, 'Mods.XXX.XXXClientSystem')  # 服务端获取客户端System
✅ 应该: self.NotifyToClient(playerId, 'EventName', {'data': value})
"""
            })

    if re.search(r'class\s+\w+\s*\(\s*ClientSystem\s*\)', code_content):
        # 这是一个ClientSystem
        # 修复: 允许GetSystem有多个参数
        if re.search(r'GetSystem\s*\([^)]*["\'].*Server.*System["\']', code_content):
            violations.append({
                "rule": "规范1: 双端隔离原则",
                "description": "客户端尝试获取服务端System(禁止跨端GetSystem)",
                "solution": "使用 NotifyToServer() 发送事件通知服务端,而非直接GetSystem",
                "doc_ref": ".claude/core-docs/核心工作流文档/开发规范.md 第2.1节(约150-180行)",
                "doc_snippet": """
⛔ 禁止: self.GetSystem(0, 'Mods.XXX.XXXServerSystem')  # 客户端获取服务端System
✅ 应该: self.NotifyToServer('EventName', {'data': value})
"""
            })

    # ===================================================================
    # 规范2: System生命周期限制
    # 禁止: 在__init__中调用MODSDK API(除非手动调用self.Create())
    # ===================================================================
    init_method_match = re.search(r'def\s+__init__\s*\([^)]*\):(.{0,1000})', code_content, re.DOTALL)
    if init_method_match:
        init_body = init_method_match.group(1)

        # 检查是否在__init__中调用了MODSDK API
        api_calls = re.findall(r'(CreateComponent|ListenForEvent|GetEngineCompFactory|CreateGame)', init_body)

        if api_calls:
            # 检查是否有self.Create()调用
            if not re.search(r'self\.Create\s*\(\s*\)', init_body):
                violations.append({
                    "rule": "规范2: System生命周期限制",
                    "description": f"在__init__中调用了MODSDK API({', '.join(set(api_calls))})但未调用self.Create()",
                    "solution": "在__init__中手动调用self.Create(),或将API调用移到Create()方法中",
                    "doc_ref": ".claude/core-docs/核心工作流文档/开发规范.md 第2.2节(约200-230行)",
                    "doc_snippet": """
⛔ 禁止:
def __init__(self, namespace, systemName):
    ServerSystem.__init__(self, namespace, systemName)
    self.CreateComponent(...)  # ❌ __init__中调用API

✅ 方案1(推荐):
def __init__(self, namespace, systemName):
    ServerSystem.__init__(self, namespace, systemName)
    self.Create()  # 手动调用Create

def Create(self):
    self.CreateComponent(...)  # ✅ 在Create中调用

✅ 方案2:
# 不覆盖__init__,直接在Create中初始化
def Create(self):
    self.CreateComponent(...)
"""
                })

    # ===================================================================
    # 规范3: EventData序列化限制
    # 禁止: EventData中使用tuple类型
    # ===================================================================
    notify_matches = re.finditer(
        r'(NotifyToClient|NotifyToServer)\s*\([^)]+\)',
        code_content
    )

    for match in notify_matches:
        notify_call = match.group(0)
        # 检测是否包含tuple(简化检测:括号中的数字序列)
        if re.search(r'\(\s*\d+\s*,\s*\d+\s*(?:,\s*\d+\s*)?\)', notify_call):
            violations.append({
                "rule": "规范3: EventData序列化限制",
                "description": "NotifyTo方法参数可能包含tuple类型(应使用list)",
                "solution": "将tuple改为list,例如: (1, 2, 3) → [1, 2, 3]",
                "doc_ref": ".claude/core-docs/核心工作流文档/开发规范.md 第2.3节(约250-270行)",
                "doc_snippet": """
⛔ 禁止:
self.NotifyToClient(playerId, 'EventName', {
    'position': (100, 200, 300)  # ❌ tuple无法序列化
})

✅ 应该:
self.NotifyToClient(playerId, 'EventName', {
    'position': [100, 200, 300]  # ✅ 使用list
})
"""
            })
            break

    # ===================================================================
    # 规范4: AOI感应区范围限制
    # 禁止: AOI范围超过2000格
    # ===================================================================
    aoi_matches = re.finditer(r'(AddAoi|CreateAoi)\s*\(([^)]+)\)', code_content)

    for match in aoi_matches:
        aoi_args = match.group(2)
        # 提取数字参数
        numbers = re.findall(r'\b(\d{4,})\b', aoi_args)

        for num_str in numbers:
            num = int(num_str)
            if num > 2000:
                violations.append({
                    "rule": "规范4: AOI感应区范围限制",
                    "description": f"检测到可能超过2000格的AOI范围参数: {num}",
                    "solution": "将AOI范围限制在2000格以内,避免性能问题",
                    "doc_ref": ".claude/core-docs/核心工作流文档/开发规范.md 第2.4节(约290-310行)",
                    "doc_snippet": f"""
⛔ 禁止:
comp.AddAoi({num})  # ❌ 超过2000格限制

✅ 应该:
comp.AddAoi(2000)  # ✅ 限制在2000格以内
# 或分块处理大范围感应需求
"""
                })

    # ===================================================================
    # 规范5: Python 2.7 print语法
    # 禁止: 使用Python 2的print语句(无括号)
    # ===================================================================
    # 检测 print xxx 格式(不是 print(xxx))
    print_violations = re.finditer(r'^\s*print\s+(?!\()', code_content, re.MULTILINE)

    for match in print_violations:
        violations.append({
            "rule": "规范5: Python 2.7 print语法",
            "description": "使用了Python 2的print语句(无括号),MODSDK需要Python 2.7兼容语法",
            "solution": "在文件开头添加 from __future__ import print_function,并使用括号形式 print()",
            "doc_ref": ".claude/core-docs/核心工作流文档/开发规范.md 第1.2节(约46-59行)",
            "doc_snippet": """
⛔ 禁止:
print "Hello"  # ❌ Python 2语法,但缺少future导入

✅ 应该:
from __future__ import print_function
print("Hello")  # ✅ 兼容Python 2.7和3.x
"""
        })
        break  # 只报告一次

    # ===================================================================
    # 规范6: 模块导入白名单
    # 禁止: 导入不允许的系统模块
    # ===================================================================
    forbidden_modules = ['os', 'sys', 'subprocess', 'threading', 'socket', 'multiprocessing']
    forbidden_imports = []

    for module in forbidden_modules:
        # 检测 import os 或 from os import xxx
        if re.search(rf'\bimport\s+{module}\b|\bfrom\s+{module}\s+import', code_content):
            forbidden_imports.append(module)

    if forbidden_imports:
        violations.append({
            "rule": "规范6: 模块导入白名单",
            "description": f"导入了禁止使用的模块: {', '.join(forbidden_imports)}",
            "solution": "移除这些导入,使用MODSDK提供的API替代。例如:文件操作使用mod.common.utils,网络操作使用MODSDK网络组件",
            "doc_ref": ".claude/core-docs/核心工作流文档/开发规范.md 第1.3节(约375-400行)",
            "doc_snippet": f"""
⛔ 禁止:
import {forbidden_imports[0]}  # ❌ 不允许的系统模块
{forbidden_imports[0]}.system('cmd')

✅ 应该:
# 使用MODSDK提供的API
import mod.common.utils as utils
# 或使用允许的模块: json, re, math, random等
"""
        })

    # ===================================================================
    # Rule 7: UTF-8 Encoding Declaration
    # v20.2 fix: Skip check for Edit operations if original file has declaration
    # ===================================================================
    if not skip_encoding_check:
        # Check first 3 lines for encoding declaration
        first_lines = code_content.split('\n')[:3]
        has_encoding = any(re.search(r'#.*?coding[:=]\s*utf-?8', line, re.IGNORECASE) for line in first_lines)

        # Check for Chinese characters
        has_chinese = bool(re.search(r'[\u4e00-\u9fff]', code_content))

        # Only error if code contains Chinese but lacks encoding
        if has_chinese and not has_encoding and len(code_content.strip()) > 0:
            violations.append({
                "rule": "Rule 7: UTF-8 Encoding",
                "description": "File contains Chinese but lacks UTF-8 declaration",
                "solution": "Add at line 1: # -*- coding: utf-8 -*-",
                "doc_ref": ".claude/core-docs/dev-guide.md Section 1.1 (lines 38-44)",
                "doc_snippet": """
Correct file header:
# -*- coding: utf-8 -*-
from __future__ import print_function
...
"""
            })

    # 规范8: Component初始化顺序
    # 警告: 在Create()之外使用Component方法可能导致NoneType错误
    # ===================================================================
    # 检测在__init__中直接使用self.xxx_comp.Method()
    init_method_match = re.search(r'def\s+__init__\s*\([^)]*\):(.{0,1500}?)(?:def\s+\w+|$)', code_content, re.DOTALL)
    if init_method_match:
        init_body = init_method_match.group(1)

        # 查找 self.xxx_comp.XXX() 调用
        comp_calls = re.findall(r'self\.\w+_comp\.\w+\(', init_body)

        if comp_calls and not re.search(r'self\.Create\s*\(\s*\)', init_body):
            violations.append({
                "rule": "规范8: Component初始化顺序",
                "description": "在__init__中使用Component方法但未先调用self.Create()",
                "solution": "确保在__init__中调用self.Create(),或将Component操作移到Create()方法中",
                "doc_ref": ".claude/core-docs/核心工作流文档/开发规范.md 第2.2节(约320-350行)",
                "doc_snippet": """
⛔ 错误:
def __init__(self, namespace, systemName):
    super(MySystem, self).__init__(namespace, systemName)
    self.item_comp = None
    self.item_comp.SpawnItem(...)  # ❌ Component未创建

✅ 正确:
def __init__(self, namespace, systemName):
    super(MySystem, self).__init__(namespace, systemName)
    self.item_comp = None
    self.Create()  # 先调用Create

def Create(self):
    comp_factory = serverApi.GetEngineCompFactory()
    self.item_comp = comp_factory.CreateItem(...)
    self.item_comp.SpawnItem(...)  # ✅ Component已创建
"""
            })

    # ===================================================================
    # 规范9: 事件名拼写检查
    # 警告: 常见事件名拼写错误
    # ===================================================================
    common_typos = {
        'ServerPlayerKillEntityEvents': 'ServerPlayerKillEntityEvent',  # 多了s
        'PlayerAttackEntityEvents': 'PlayerAttackEntityEvent',
        'OnPlayerDie': 'OnPlayerDieEvent',
        'PlayerInteractBlock': 'PlayerInteractBlockEvent',
    }

    for typo, correct in common_typos.items():
        # 只检查带引号的完整事件名
        if re.search(rf'["\']' + re.escape(typo) + rf'["\']', code_content):
            violations.append({
                "rule": "规范9: 事件名拼写",
                "description": f"事件名可能拼写错误: {typo}",
                "solution": f"正确的事件名应为: {correct}",
                "doc_ref": ".claude/core-docs/核心工作流文档/MODSDK事件列表.md",
                "doc_snippet": f"""
⛔ 错误:
self.ListenForEvent(..., "{typo}", ...)  # ❌ 拼写错误

✅ 正确:
self.ListenForEvent(..., "{correct}", ...)  # ✅ 正确事件名
"""
            })
            break

    # ===================================================================
    # 规范10: 跨System直接调用
    # 警告: 不应通过GetSystem后直接调用其他System的方法
    # ===================================================================
    # 检测模式: self.GetSystem(...).XXX(...) 但排除变量赋值
    lines = code_content.split('\n')
    for line in lines:
        # 跳过赋值语句 (xxx = self.GetSystem(...))
        if '=' in line and line.index('=') < line.find('GetSystem') if 'GetSystem' in line else False:
            continue

        # 检测链式调用: self.GetSystem(...).Method(...)
        if re.search(r'self\.GetSystem\s*\([^)]+\)\s*\.\s*\w+\s*\(', line):
            violations.append({
                "rule": "规范10: 跨System直接调用",
                "description": "通过GetSystem获取其他System后直接调用方法,违反松耦合原则",
                "solution": "使用事件通知机制(NotifyToClient/NotifyToServer)代替直接调用",
                "doc_ref": ".claude/core-docs/核心工作流文档/开发规范.md 第2.1节(约150-180行)",
                "doc_snippet": """
⛔ 禁止:
other_system = self.GetSystem("Mods", "OtherSystem")
other_system.DoSomething()  # ❌ 直接调用方法

✅ 应该:
# 发送事件通知
self.NotifyToClient(playerId, "DoSomethingEvent", {"data": value})

# 在OtherSystem中监听
class OtherSystem(...):
    def Create(self):
        self.ListenForEvent("Mods", "MySystem", "DoSomethingEvent", self, self.OnDoSomething)
"""
            })
            break

    # ===================================================================
    # 规范11: 全局变量污染
    # 警告: 不应在模块级别定义可变全局变量
    # ===================================================================
    # 检测模块级别的全局变量(排除常量和导入)
    global_var_lines = []
    lines = code_content.split('\n')

    for i, line in enumerate(lines, 1):
        # 跳过注释、空行、导入、函数/类定义
        if re.match(r'^\s*#', line) or re.match(r'^\s*$', line):
            continue
        if re.match(r'^\s*(import|from|def|class)', line):
            continue

        # 检测全局变量赋值(排除全大写的常量)
        if re.match(r'^[a-z_]\w*\s*=\s*[\[{]', line):
            global_var_lines.append((i, line.strip()))

    if global_var_lines:
        violations.append({
            "rule": "规范11: 全局变量污染",
            "description": f"检测到{len(global_var_lines)}个模块级别的可变全局变量,可能导致多玩家状态污染",
            "solution": "将全局变量移到System类的__init__中作为实例变量",
            "doc_ref": ".claude/core-docs/核心工作流文档/开发规范.md 第3.2节(约430-450行)",
            "doc_snippet": """
⛔ 禁止:
# 模块级别
player_data = {}  # ❌ 全局可变变量,多玩家会冲突

class MySystem(ServerSystem):
    def OnPlayerJoin(self, args):
        player_data[playerId] = {...}  # ❌ 污染全局状态

✅ 应该:
class MySystem(ServerSystem):
    def __init__(self, namespace, systemName):
        super(MySystem, self).__init__(namespace, systemName)
        self.player_data = {}  # ✅ 实例变量
        self.Create()

    def OnPlayerJoin(self, args):
        self.player_data[playerId] = {...}  # ✅ 使用实例变量
"""
        })

    # ===================================================================
    # 规范12: 事件监听器未解绑
    # 警告: 使用ListenForEvent但未在Destroy中UnListen
    # ===================================================================
    has_listen = bool(re.search(r'ListenForEvent\s*\(', code_content))
    has_unlisten = bool(re.search(r'UnListenForEvent|UnListenAllEvents', code_content))
    has_destroy = bool(re.search(r'def\s+Destroy\s*\(', code_content))

    if has_listen and has_destroy and not has_unlisten:
        violations.append({
            "rule": "规范12: 事件监听器未解绑",
            "description": "注册了事件监听但在Destroy()中未解绑,可能导致内存泄漏",
            "solution": "在Destroy()方法中调用UnListenAllEvents()或对每个事件调用UnListenForEvent()",
            "doc_ref": ".claude/core-docs/核心工作流文档/性能优化指南.md 第2.3节(约80-100行)",
            "doc_snippet": """
✅ 推荐做法:
def Create(self):
    self.ListenForEvent(...)
    self.ListenForEvent(...)

def Destroy(self):
    self.UnListenAllEvents()  # ✅ 清理所有监听器
    # 或单独解绑
    # self.UnListenForEvent(...)
"""
        })

    return violations


if __name__ == "__main__":
    main()
