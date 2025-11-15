# -*- coding: utf-8 -*-
"""
ECHUDScreenNode - HUD界面节点

功能:
- 管理HUD UI组件
- 堆叠消息控制器(顶部/底部)
- 计分板控制器

原文件: Parts/ECHUD/ECHUDScreenNode.py
重构为: systems/ui/ECHUDScreenNode.py
"""

from __future__ import print_function
from collections import OrderedDict
import mod.client.extraClientApi as clientApi

# 获取ScreenNode基类
ScreenNode = clientApi.GetScreenNodeCls()


class ECHUDScreenNode(ScreenNode):
    """
    ECHUD界面节点

    管理三个核心UI组件:
    - stack_msg_top: 顶部堆叠消息面板
    - stack_msg_bottom: 底部堆叠消息面板
    - scoreboard: 侧边计分板
    """

    def __init__(self, namespace, name, param):
        """
        初始化ScreenNode

        Args:
            namespace: 命名空间
            name: 节点名称
            param: 参数
        """
        super(ECHUDScreenNode, self).__init__(namespace, name, param)

        # 控制器
        self.stack_msg_top = None
        self.stack_msg_bottom = None
        self.scoreboard = None

        print("[INFO] [ECHUDScreenNode] 初始化")

    def Create(self):
        """创建UI - 引擎会自动调用"""
        print("[INFO] [ECHUDScreenNode] Create")

        # 初始化控制器
        self.stack_msg_top = StackMsgController(self, "/stack_msg_top")
        self.stack_msg_bottom = StackMsgController(self, "/stack_msg_bottom")
        self.scoreboard = ScoreboardController(self, "/scoreboard")

        print("[INFO] [ECHUDScreenNode] 控制器初始化完成")

    def handle_hud_control(self, args):
        """
        处理HUD控制事件

        Args:
            args: {
                'type': 'stack_msg_top' | 'stack_msg_bottom' | 'scoreboard',
                'events': [...] 或其他字段
            }
        """
        hud_type = args.get('type')
        # print("[DEBUG] [ECHUDScreenNode] 收到HUD控制事件 type={}".format(hud_type))

        # 根据type分发到对应控制器
        if hud_type == 'stack_msg_top':
            if self.stack_msg_top:
                self.stack_msg_top.handle_control(args)

        elif hud_type == 'stack_msg_bottom':
            if self.stack_msg_bottom:
                self.stack_msg_bottom.handle_control(args)

        elif hud_type == 'scoreboard':
            if self.scoreboard:
                self.scoreboard.handle_control(args)

    def OnDestroy(self):
        """销毁UI"""
        print("[INFO] [ECHUDScreenNode] OnDestroy")

        # 清理控制器
        if self.stack_msg_top:
            self.stack_msg_top.clear_all()
            self.stack_msg_top = None

        if self.stack_msg_bottom:
            self.stack_msg_bottom.clear_all()
            self.stack_msg_bottom = None

        if self.scoreboard:
            self.scoreboard = None


class StackMsgController(object):
    """
    堆叠消息控制器

    管理动态堆叠消息的添加、更新和删除
    """

    def __init__(self, screen, stack_path):
        """
        初始化控制器

        Args:
            screen: ECHUDScreenNode实例
            stack_path: 面板路径 ("/stack_msg_top" 或 "/stack_msg_bottom")
        """
        self.screen = screen
        self.stack_path = stack_path
        self.entries = OrderedDict()  # {key: value}

        print("[INFO] [StackMsgController] 初始化 path={}".format(stack_path))

    def handle_control(self, args):
        """
        处理控制指令

        Args:
            args: 控制参数字典
                支持单个操作: {'event': str, 'key': str, 'value': str, 'border': bool}
                支持批量操作: {'events': [{'event': str, ...}, ...]}
        """
        # 批量操作
        if 'events' in args:
            for event_args in args['events']:
                self._handle_single_event(event_args)
        # 单个操作
        else:
            self._handle_single_event(args)

    def _handle_single_event(self, args):
        """
        处理单个事件

        Args:
            args: {
                'event': 'add_or_set' | 'remove' | 'clear_all',
                'key': str,           # 唯一标识
                'value': str,         # 显示文本
                'border': bool        # 是否显示边框(可选)
            }
        """
        event = args.get('event')

        if event == 'add_or_set':
            key = args.get('key')
            value = args.get('value', '')
            border = args.get('border', False)
            self.add_or_set_entry(key, value, border)

        elif event == 'remove':
            key = args.get('key')
            self.remove_entry(key)

        elif event == 'clear_all':
            self.clear_all()

    def add_or_set_entry(self, key, value, border=False):
        """
        添加或更新消息条目

        Args:
            key (str): 唯一标识
            value (str): 显示文本(支持颜色代码)
            border (bool): 是否显示边框
        """
        parent_node = self.screen.GetBaseUIControl(self.stack_path)
        if not parent_node:
            print("[ERROR] [StackMsgController] 父节点不存在: {}".format(self.stack_path))
            return

        node_name = "stack_msg_" + key

        # 获取或创建节点
        node = self.screen.GetBaseUIControl(self.stack_path + "/" + node_name)
        if node is None:
            # 如果已有其他条目,先添加间距
            if len(self.entries) >= 1:
                space_name = node_name + "_space"
                self.screen.CreateChildControl("ec_hud.space_w4", space_name, parent_node)

            # 创建消息条目
            node = self.screen.CreateChildControl("ec_hud.stack_msg", node_name, parent_node)

        # 设置文本
        text_node = node.GetChildByPath("/stack_msg_text")
        if text_node:
            text_node.asLabel().SetText(value)

        # 存储条目
        self.entries[key] = value

        # print("[DEBUG] [StackMsgController] 添加/更新条目 key={} value={}".format(key, value))

    def remove_entry(self, key):
        """
        移除消息条目

        Args:
            key (str): 唯一标识
        """
        node_name = "stack_msg_" + key

        # 移除消息节点
        node = self.screen.GetBaseUIControl(self.stack_path + "/" + node_name)
        if node:
            self.screen.RemoveChildControl(node)

        # 移除间距节点
        space_node = self.screen.GetBaseUIControl(self.stack_path + "/" + node_name + "_space")
        if space_node:
            self.screen.RemoveChildControl(space_node)

        # 从字典移除
        if key in self.entries:
            self.entries.pop(key)

        # print("[DEBUG] [StackMsgController] 移除条目 key={}".format(key))  # 调试日志已禁用

    def clear_all(self):
        """清空所有消息条目"""
        # 移除所有节点
        keys_to_remove = list(self.entries.keys())
        for key in keys_to_remove:
            self.remove_entry(key)

        # print("[DEBUG] [StackMsgController] 清空所有条目 path={}".format(self.stack_path))  # 调试日志已禁用


class ScoreboardController(object):
    """
    计分板控制器

    管理侧边计分板的标题、内容和可见性
    """

    def __init__(self, screen, path):
        """
        初始化控制器

        Args:
            screen: ECHUDScreenNode实例
            path: 计分板路径 ("/scoreboard")
        """
        self.screen = screen
        self.path = path
        self.title = ""
        self.text = ""

        print("[INFO] [ScoreboardController] 初始化 path={}".format(path))

        # 默认隐藏计分板（与老项目保持一致）
        # 只有在调用set_title()或set_content()时才会自动显示
        self.set_visible(False)

    def handle_control(self, args):
        """
        处理控制指令

        Args:
            args: {
                'event': 'set_title' | 'set_content' | 'set_visible',
                'value': str | bool
            }
        """
        event = args.get('event')
        value = args.get('value')

        if event == 'set_title':
            self.set_title(value)
        elif event == 'set_content':
            self.set_content(value)
        elif event == 'set_visible':
            self.set_visible(value)

    def set_title(self, title):
        """
        设置计分板标题

        Args:
            title (str): 标题文本
        """
        # ❌ 禁用自动显示计分板（与老项目保持一致，不显示计分板）
        # 原因: 用户反馈老项目中没有计分板显示功能
        # 修改人: Claude
        # 修改时间: 2025-11-12
        # self.set_visible(True)

        # 避免重复设置
        if self.title == title:
            return

        self.title = title

        # 更新UI
        node = self.screen.GetBaseUIControl(self.path)
        if node:
            title_node = node.GetChildByPath("/scoreboard_title")
            if title_node:
                title_node.asLabel().SetText(title)

    def set_content(self, text):
        """
        设置计分板内容

        Args:
            text (str): 内容文本(支持多行\n分隔)
        """
        # ❌ 禁用自动显示计分板（与老项目保持一致，不显示计分板）
        # 原因: 用户反馈老项目中没有计分板显示功能
        # 修改人: Claude
        # 修改时间: 2025-11-12
        # self.set_visible(True)

        # 避免重复设置
        if self.text == text:
            return

        self.text = text

        # 更新UI
        node = self.screen.GetBaseUIControl(self.path)
        if node:
            content_node = node.GetChildByPath("/scoreboard_content")
            if content_node:
                content_node.asLabel().SetText(text)

    def set_visible(self, visible=True):
        """
        设置计分板可见性

        Args:
            visible (bool): 是否可见
        """
        node = self.screen.GetBaseUIControl(self.path)
        if node:
            node.SetVisible(visible)

    def is_visible(self):
        """
        获取计分板可见性

        Returns:
            bool: 是否可见
        """
        node = self.screen.GetBaseUIControl(self.path)
        if node:
            return node.IsVisible()
        return False
