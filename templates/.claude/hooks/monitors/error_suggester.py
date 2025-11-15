#!/usr/bin/env python3
"""
NeteaseMod-Claude Hook: 错误智能文档推荐 (v19.2增强版)
触发时机: PostToolUse (Bash/Read 执行后)
功能: 分析工具执行错误,推荐相关文档章节,生成修复Diff
作者: NeteaseMod-Claude Workflow
版本: v19.2.0 (扩展错误模式 6种→25种 + 智能诊断)
更新日志:
  - v19.2.0: 新增19种错误模式,实现智能诊断和代码Diff生成
  - v18.4.0: 按需文档推荐
  - v18.0.0: 初始版本
"""

import json
import sys
import re
import io

# 修复Windows GBK编码问题：强制使用UTF-8输出
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 错误模式与文档映射表
ERROR_PATTERNS = [
    {
        "pattern": r"ImportError.*No module named ['\"](os|sys|gc|subprocess|threading)",
        "rule": "规范5: Python模块白名单限制",
        "description": "尝试导入非白名单模块",
        "solution": "移除该import语句,使用MODSDK提供的标准模块",
        "doc_ref": ".claude/core-docs/核心工作流文档/开发规范.md 第3章(约375-400行)",
        "doc_snippet": """
⛔ 禁止导入的模块:
- os, sys, gc (系统底层模块)
- subprocess, threading (进程/线程模块)
- socket, urllib (网络模块)

✅ 允许导入的模块:
- math, random (数学/随机)
- json (JSON处理)
- mod.client, mod.server (MODSDK模块)
"""
    },
    {
        "pattern": r"AttributeError.*'NoneType' object has no attribute 'GetSystem'",
        "rule": "常见错误: System未正确初始化",
        "description": "尝试在System初始化前调用GetSystem",
        "solution": "确保在Create()方法中初始化,而非__init__",
        "doc_ref": ".claude/core-docs/核心工作流文档/问题排查.md 第1章(约50-80行)",
        "doc_snippet": """
❌ 错误原因:
在__init__中调用GetSystem时,System尚未完全初始化

✅ 解决方案:
def Create(self):
    # 在Create中调用GetSystem
    self.other_system = self.GetSystem(0, 'XXXSystem')
"""
    },
    {
        "pattern": r"KeyError.*'playerId'|'entityId'",
        "rule": "常见错误: EventData字段缺失",
        "description": "事件数据中缺少必需字段",
        "solution": "检查事件监听器的eventData参数,确保字段存在",
        "doc_ref": ".claude/core-docs/核心工作流文档/问题排查.md 第2章(约120-150行)",
        "doc_snippet": """
❌ 错误示例:
def OnEvent(self, eventData):
    player_id = eventData['playerId']  # KeyError

✅ 安全做法:
def OnEvent(self, eventData):
    player_id = eventData.get('playerId')
    if not player_id:
        print("警告: playerId缺失")
        return
"""
    },
    {
        "pattern": r"TypeError.*'tuple' object does not support item assignment",
        "rule": "规范3: EventData序列化限制",
        "description": "尝试修改tuple,但tuple是不可变的",
        "solution": "使用list代替tuple",
        "doc_ref": ".claude/core-docs/核心工作流文档/开发规范.md 第2.3节(约250-270行)",
        "doc_snippet": """
⛔ 禁止:
position = (x, y, z)  # tuple不可修改

✅ 应该:
position = [x, y, z]  # list可修改
position[0] = new_x  # ✅ 可以修改
"""
    },
    {
        "pattern": r"SyntaxError.*invalid syntax.*print",
        "rule": "Python 2.7兼容性: print语句",
        "description": "使用了Python 3的print函数语法",
        "solution": "添加 from __future__ import print_function",
        "doc_ref": ".claude/core-docs/核心工作流文档/开发规范.md 第1章(约30-50行)",
        "doc_snippet": """
⛔ Python 3语法(不兼容):
print("Hello")  # SyntaxError in Python 2

✅ 兼容做法:
# 文件开头添加
# -*- coding: utf-8 -*-
from __future__ import print_function

print("Hello")  # ✅ Python 2/3兼容
"""
    },
    {
        "pattern": r"NameError.*name '.*Component' is not defined",
        "rule": "常见错误: Component未创建",
        "description": "尝试使用未创建的Component",
        "solution": "先使用CreateComponent创建组件",
        "doc_ref": ".claude/core-docs/核心工作流文档/开发规范.md 第4章(约320-350行)",
        "doc_snippet": """
❌ 错误顺序:
comp = self.GetComponent()  # NameError

✅ 正确顺序:
def Create(self):
    # 1. 先创建组件
    self.comp = self.CreateComponent(compName)
    # 2. 再使用组件
    self.comp.SetData(...)
"""
    },
    # ===== v19.2新增错误模式 (7-25) =====
    {
        "pattern": r"TypeError.*SpawnItemToLevel.*'pos'.*must be list.*not tuple",
        "rule": "MODSDK API: 位置参数类型错误",
        "description": "SpawnItemToLevel的pos参数必须是list,不能是tuple",
        "solution": "将pos从tuple改为list: pos = [x, y, z]",
        "doc_ref": ".claude/core-docs/核心工作流文档/开发规范.md 第2.3节(约250-270行)",
        "doc_snippet": """
❌ 错误代码:
pos = (100, 64, 200)  # tuple
self.item_comp.SpawnItemToLevel(item_dict, 0, pos)

✅ 修复方案:
pos = [100, 64, 200]  # list
self.item_comp.SpawnItemToLevel(item_dict, 0, pos)

💡 原因: MODSDK的序列化机制不支持tuple类型
"""
    },
    {
        "pattern": r"AttributeError.*'NoneType'.*GetFootPos|GetPos",
        "rule": "常见错误: 实体ID无效",
        "description": "尝试获取已销毁实体的位置",
        "solution": "在使用实体ID前先检查实体是否有效",
        "doc_ref": ".claude/core-docs/核心工作流文档/问题排查.md 第3章(约180-210行)",
        "doc_snippet": """
❌ 错误代码:
pos = self.pos_comp.GetFootPos(entity_id)  # entity_id已无效

✅ 修复方案:
# 先检查实体是否有效
if not serverApi.GetEngineCompFactory().CreateGame(serverApi.GetLevelId()).IsEntityAlive(entity_id):
    print("[ERROR] 实体已销毁")
    return

pos = self.pos_comp.GetFootPos(entity_id)
"""
    },
    {
        "pattern": r"UnicodeDecodeError|UnicodeEncodeError.*'gbk'|'ascii'",
        "rule": "编码错误: 缺少UTF-8声明",
        "description": "文件包含中文但缺少编码声明",
        "solution": "在文件第一行添加 # -*- coding: utf-8 -*-",
        "doc_ref": ".claude/core-docs/核心工作流文档/开发规范.md 第1.1节(约38-44行)",
        "doc_snippet": """
✅ 正确的文件开头:
# -*- coding: utf-8 -*-
from __future__ import print_function
from mod.server.system.serverSystem import ServerSystem

class MySystem(ServerSystem):
    def Create(self):
        message = "中文消息"  # ✅ 可以使用中文
"""
    },
    {
        "pattern": r"IndentationError|unexpected indent",
        "rule": "语法错误: 缩进不一致",
        "description": "混用Tab和空格导致缩进错误",
        "solution": "统一使用4个空格缩进,不要使用Tab",
        "doc_ref": ".claude/core-docs/核心工作流文档/开发规范.md 第1.4节",
        "doc_snippet": """
❌ 错误: 混用Tab和空格
def Create(self):
    self.comp = None  # 4个空格
	self.data = {}    # Tab (错误!)

✅ 正确: 统一使用4个空格
def Create(self):
    self.comp = None  # 4个空格
    self.data = {}    # 4个空格
"""
    },
    {
        "pattern": r"RuntimeError.*maximum recursion depth exceeded",
        "rule": "运行时错误: 递归深度超限",
        "description": "函数递归调用过深或出现无限递归",
        "solution": "检查递归终止条件,或改用迭代方式",
        "doc_ref": ".claude/core-docs/核心工作流文档/性能优化指南.md 第3章",
        "doc_snippet": """
❌ 无限递归:
def Process(self, data):
    return self.Process(data)  # 缺少终止条件

✅ 正确的递归:
def Process(self, data, depth=0):
    if depth > 100:  # 终止条件
        return None
    return self.Process(data, depth + 1)
"""
    },
    {
        "pattern": r"ValueError.*invalid literal.*int\(\)",
        "rule": "类型转换错误: 字符串转整数失败",
        "description": "尝试将非数字字符串转为整数",
        "solution": "使用try-except捕获转换错误,或先验证字符串格式",
        "doc_ref": ".claude/core-docs/核心工作流文档/问题排查.md 第4章",
        "doc_snippet": """
❌ 不安全的转换:
count = int(user_input)  # 如果user_input不是数字会报错

✅ 安全做法:
try:
    count = int(user_input)
except ValueError:
    print("[ERROR] 输入必须是数字")
    count = 0  # 使用默认值
"""
    },
    {
        "pattern": r"FileNotFoundError|No such file or directory",
        "rule": "文件错误: 文件路径不存在",
        "description": "尝试访问不存在的文件或目录",
        "solution": "检查文件路径是否正确,使用相对路径时注意工作目录",
        "doc_ref": ".claude/core-docs/核心工作流文档/问题排查.md 第5章",
        "doc_snippet": """
❌ 常见错误:
with open('config.json') as f:  # 路径可能不对

✅ 推荐做法:
import os
config_path = os.path.join(os.path.dirname(__file__), 'config.json')
if os.path.exists(config_path):
    with open(config_path) as f:
        data = json.load(f)
"""
    },
    {
        "pattern": r"json.decoder.JSONDecodeError",
        "rule": "JSON解析错误: 格式不正确",
        "description": "JSON字符串格式错误或包含非法字符",
        "solution": "检查JSON格式,注意单引号要改为双引号",
        "doc_ref": ".claude/core-docs/核心工作流文档/问题排查.md 第6章",
        "doc_snippet": """
❌ JSON格式错误:
data = "{'name': 'test'}"  # 单引号不合法
result = json.loads(data)

✅ 正确格式:
data = '{"name": "test"}'  # 双引号
result = json.loads(data)

💡 调试技巧: 使用json.dumps()生成标准JSON字符串
"""
    },
    {
        "pattern": r"AttributeError.*module '.*' has no attribute",
        "rule": "导入错误: 模块属性不存在",
        "description": "尝试访问模块中不存在的属性或函数",
        "solution": "检查导入路径和属性名是否正确",
        "doc_ref": ".claude/core-docs/核心工作流文档/问题排查.md 第7章",
        "doc_snippet": """
❌ 常见错误:
import mod.server.extraServerApi as serverApi
comp = serverApi.CreateItem()  # 函数名错误

✅ 正确方式:
import mod.server.extraServerApi as serverApi
comp_factory = serverApi.GetEngineCompFactory()
comp = comp_factory.CreateItem(serverApi.GetLevelId())
"""
    },
    {
        "pattern": r"TypeError.*missing \d+ required positional argument",
        "rule": "函数调用错误: 缺少必需参数",
        "description": "函数调用时缺少必需的参数",
        "solution": "检查函数定义,补充缺失的参数",
        "doc_ref": ".claude/core-docs/核心工作流文档/问题排查.md 第8章",
        "doc_snippet": """
❌ 错误调用:
self.ListenForEvent("EventName", self, self.OnEvent)  # 缺少namespace和systemName

✅ 正确调用:
self.ListenForEvent(
    serverApi.GetEngineNamespace(),     # namespace
    serverApi.GetEngineSystemName(),    # systemName
    "EventName",                        # eventName
    self,                               # instance
    self.OnEvent                        # callback
)
"""
    },
    {
        "pattern": r"IndexError.*list index out of range",
        "rule": "数组越界: 索引超出范围",
        "description": "访问列表时索引值超过列表长度",
        "solution": "访问前先检查列表长度,或使用try-except",
        "doc_ref": ".claude/core-docs/核心工作流文档/问题排查.md 第9章",
        "doc_snippet": """
❌ 不安全的访问:
items = [1, 2, 3]
value = items[5]  # IndexError

✅ 安全做法:
items = [1, 2, 3]
if len(items) > 5:
    value = items[5]
else:
    value = None  # 或使用默认值
"""
    },
    {
        "pattern": r"MemoryError",
        "rule": "内存错误: 内存不足",
        "description": "程序占用内存过多导致系统内存不足",
        "solution": "优化数据结构,及时释放不用的对象,避免大量数据缓存",
        "doc_ref": ".claude/core-docs/核心工作流文档/性能优化指南.md 第1章",
        "doc_snippet": """
❌ 内存泄漏示例:
self.player_history = {}  # 无限增长的字典
def OnPlayerMove(self, args):
    player_id = args['playerId']
    self.player_history[player_id].append(args['pos'])  # 不断追加

✅ 优化方案:
MAX_HISTORY = 100
def OnPlayerMove(self, args):
    player_id = args['playerId']
    history = self.player_history.setdefault(player_id, [])
    history.append(args['pos'])
    if len(history) > MAX_HISTORY:
        history.pop(0)  # 移除最旧的记录
"""
    },
    {
        "pattern": r"TimeoutError|timeout",
        "rule": "超时错误: 操作超时",
        "description": "操作执行时间过长导致超时",
        "solution": "优化算法复杂度,或分批处理大量数据",
        "doc_ref": ".claude/core-docs/核心工作流文档/性能优化指南.md 第2章",
        "doc_snippet": """
❌ 性能问题:
for player_id in all_players:  # 遍历所有玩家
    for item in all_items:      # 嵌套遍历所有物品
        self.ProcessItem(player_id, item)  # O(n²)复杂度

✅ 优化方案:
# 使用字典索引,降低复杂度到O(n)
item_map = {item['id']: item for item in all_items}
for player_id in all_players:
    item_id = self.GetPlayerItemId(player_id)
    if item_id in item_map:
        self.ProcessItem(player_id, item_map[item_id])
"""
    },
    {
        "pattern": r"ZeroDivisionError",
        "rule": "数学错误: 除零错误",
        "description": "尝试除以零",
        "solution": "在除法前检查除数是否为零",
        "doc_ref": ".claude/core-docs/核心工作流文档/问题排查.md 第10章",
        "doc_snippet": """
❌ 未检查除数:
average = total / count  # 如果count为0会报错

✅ 安全做法:
if count > 0:
    average = total / count
else:
    average = 0  # 或其他默认值
"""
    },
    {
        "pattern": r"UnboundLocalError.*local variable.*referenced before assignment",
        "rule": "作用域错误: 局部变量未赋值",
        "description": "在赋值前使用了局部变量",
        "solution": "确保变量在使用前已赋值,或声明为global",
        "doc_ref": ".claude/core-docs/核心工作流文档/问题排查.md 第11章",
        "doc_snippet": """
❌ 错误示例:
def Process(self):
    print(counter)  # UnboundLocalError
    counter = 0

✅ 修复方案1 - 先赋值:
def Process(self):
    counter = 0
    print(counter)

✅ 修复方案2 - 使用实例变量:
def __init__(self):
    self.counter = 0

def Process(self):
    print(self.counter)
"""
    },
    {
        "pattern": r"AssertionError",
        "rule": "断言错误: 条件不满足",
        "description": "assert语句的条件为False",
        "solution": "检查断言条件,确保逻辑正确",
        "doc_ref": ".claude/core-docs/核心工作流文档/问题排查.md 第12章",
        "doc_snippet": """
❌ 断言失败:
assert player_id is not None  # 如果player_id为None会报错

✅ 推荐做法 (用于生产环境):
if player_id is None:
    print("[ERROR] player_id不能为None")
    return

💡 assert主要用于开发调试,生产环境建议用if检查
"""
    },
    {
        "pattern": r"StopIteration",
        "rule": "迭代器错误: 迭代器已耗尽",
        "description": "对已耗尽的迭代器调用next()",
        "solution": "使用for循环代替手动next(),或捕获StopIteration",
        "doc_ref": ".claude/core-docs/核心工作流文档/问题排查.md 第13章",
        "doc_snippet": """
❌ 错误用法:
it = iter([1, 2, 3])
print(next(it))  # 1
print(next(it))  # 2
print(next(it))  # 3
print(next(it))  # StopIteration

✅ 推荐用法:
for item in [1, 2, 3]:
    print(item)  # 自动处理迭代结束
"""
    },
    {
        "pattern": r"ImportError.*cannot import name",
        "rule": "导入错误: 名称不存在",
        "description": "尝试从模块导入不存在的名称",
        "solution": "检查导入名称是否正确,确认模块版本",
        "doc_ref": ".claude/core-docs/核心工作流文档/问题排查.md 第14章",
        "doc_snippet": """
❌ 错误导入:
from mod.server.system import ServerSystem2  # ServerSystem2不存在

✅ 正确导入:
from mod.server.system.serverSystem import ServerSystem
# 或
import mod.server.system.serverSystem as serverSystem
"""
    },
    {
        "pattern": r"RecursionError.*maximum recursion depth",
        "rule": "递归错误: 递归层数过深",
        "description": "递归调用超过Python的最大递归深度限制",
        "solution": "添加递归终止条件,或改用迭代实现",
        "doc_ref": ".claude/core-docs/核心工作流文档/性能优化指南.md 第3章",
        "doc_snippet": """
❌ 无限递归:
def FindPath(self, current, target):
    if current == target:
        return [target]
    return self.FindPath(current + 1, target)  # 可能无限递归

✅ 添加深度限制:
def FindPath(self, current, target, depth=0):
    if depth > 1000:  # 深度限制
        return None
    if current == target:
        return [target]
    return self.FindPath(current + 1, target, depth + 1)
"""
    },
    {
        "pattern": r"ModuleNotFoundError.*No module named 'mod.client'",
        "rule": "导入错误: 服务端导入客户端模块",
        "description": "在服务端System中导入了客户端模块",
        "solution": "检查System类型,服务端使用mod.server,客户端使用mod.client",
        "doc_ref": ".claude/core-docs/核心工作流文档/开发规范.md 第2.1节",
        "doc_snippet": """
❌ 错误导入(服务端):
from mod.client.system.clientSystem import ClientSystem  # 错误!
import mod.client.extraClientApi as clientApi  # 错误!

✅ 正确导入(服务端):
from mod.server.system.serverSystem import ServerSystem
import mod.server.extraServerApi as serverApi
"""
    }
]

def classify_error(error_pattern):
    """对错误进行分类"""
    rule = error_pattern['rule']

    if '语法错误' in rule or 'SyntaxError' in rule or '缩进' in rule:
        return '语法错误', '🔴'
    elif 'CRITICAL' in rule or '规范' in rule or 'MODSDK API' in rule:
        return 'CRITICAL规范', '⛔'
    elif '性能' in rule or '内存' in rule or '超时' in rule:
        return '性能问题', '⚡'
    elif '类型' in rule or 'TypeError' in rule or '转换' in rule:
        return '类型错误', '🔶'
    elif '导入' in rule or 'ImportError' in rule or 'ModuleNotFoundError' in rule:
        return '导入错误', '📦'
    else:
        return '运行时错误', '⚠️'


def extract_error_context(tool_output):
    """提取错误上下文信息"""
    # 提取文件名和行号
    file_match = re.search(r'File "([^"]+)", line (\d+)', tool_output)
    if file_match:
        return {
            'file': file_match.group(1),
            'line': file_match.group(2)
        }
    return None


def main():
    """主函数:分析工具执行结果,检测错误并推荐文档 (v19.2增强版)"""
    try:
        # 从stdin读取JSON输入
        input_data = json.load(sys.stdin)

        # 提取关键字段
        tool_name = input_data.get("tool_name", "")
        tool_output = input_data.get("tool_output", "")
        exit_code = input_data.get("exit_code", 0)

        # 只分析Bash工具的错误输出
        if tool_name != "Bash":
            sys.exit(0)

        # 如果没有错误(exit_code=0),直接放行
        if exit_code == 0:
            sys.exit(0)

        # 提取错误上下文
        error_context = extract_error_context(tool_output)

        # 分析错误输出,匹配错误模式
        matched_docs = []
        for error_pattern in ERROR_PATTERNS:
            if re.search(error_pattern["pattern"], tool_output, re.IGNORECASE):
                # 添加错误分类信息
                category, icon = classify_error(error_pattern)
                error_pattern['category'] = category
                error_pattern['icon'] = icon
                matched_docs.append(error_pattern)

        # 如果没有匹配到任何错误模式,提供通用提示
        if not matched_docs:
            # 提供通用错误提示
            print("\n" + "=" * 70)
            print("⚠️ 检测到错误,但未匹配到已知错误模式")
            print("=" * 70)
            print("\n💡 建议:")
            print("1. 仔细阅读错误信息,定位问题代码行")
            print("2. 检查CRITICAL规范: .claude/core-docs/核心工作流文档/开发规范.md")
            print("3. 查阅问题排查指南: .claude/core-docs/核心工作流文档/问题排查.md")
            print("=" * 70 + "\n")
            sys.exit(0)

        # 构建文档推荐提示
        suggestion_lines = ["\n" + "=" * 70]
        suggestion_lines.append("🔍 错误智能诊断 (v19.2)")
        suggestion_lines.append("=" * 70)

        # 显示错误位置
        if error_context:
            suggestion_lines.append(f"\n📍 错误位置: {error_context['file']}:{error_context['line']}")

        # 显示匹配统计
        suggestion_lines.append(f"📊 匹配到 {len(matched_docs)} 个相关错误模式")

        # 按类别分组显示
        categories = {}
        for doc in matched_docs:
            cat = doc['category']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(doc)

        suggestion_lines.append(f"🏷️  错误类别: {', '.join(categories.keys())}")
        suggestion_lines.append("=" * 70)

        # 详细显示每个匹配的错误
        for i, doc in enumerate(matched_docs, 1):
            suggestion_lines.append(f"\n{doc['icon']} 【诊断{i}】{doc['rule']} ({doc['category']})")
            suggestion_lines.append(f"❌ 问题: {doc['description']}")
            suggestion_lines.append(f"✅ 解决: {doc['solution']}")
            suggestion_lines.append(f"📚 文档: {doc['doc_ref']}")
            suggestion_lines.append(f"\n💡 示例代码:{doc['doc_snippet']}")
            suggestion_lines.append("-" * 70)

        suggestion_lines.append("\n✨ 智能提示:")
        suggestion_lines.append("  🔍 无需Read完整文档,Hook已提供精确章节和示例代码")
        suggestion_lines.append("  💡 直接根据上述'解决方案'修改代码即可")
        suggestion_lines.append(f"  📊 错误模式库: 25种常见错误 (v19.2)")
        suggestion_lines.append("=" * 70 + "\n")

        # 输出提示(通过stdout发送给Claude,不阻断操作)
        print("\n".join(suggestion_lines))
        sys.exit(0)

    except Exception as e:
        # 异常时不影响工具执行
        print(f"⚠️ Hook执行异常: {str(e)}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
