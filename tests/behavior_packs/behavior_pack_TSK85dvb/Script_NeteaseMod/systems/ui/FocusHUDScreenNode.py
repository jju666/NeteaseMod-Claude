# -*- coding: utf-8 -*-
"""
FocusHUDScreenNode - 焦点准星UI屏幕节点

功能说明：
    为火球武器提供瞄准辅助的UI屏幕节点。
    通过数据绑定控制准星的显示/隐藏。

重构说明：
    老项目: ECFocusNodeScreenNode (ScreenNode + ViewBinder)
    新项目: FocusHUDScreenNode (ScreenNode + ViewBinder)

核心职责：
    1. 管理focus_status全局变量
    2. 通过ViewBinder绑定UI可见性
    3. 提供准星显示/隐藏接口
"""

import mod.client.extraClientApi as clientApi

# 获取ViewBinder和ScreenNode基类
ViewBinder = clientApi.GetViewBinderCls()
ScreenNode = clientApi.GetScreenNodeCls()


class FocusHUDScreenNode(ScreenNode):
    """焦点准星UI屏幕节点"""

    def __init__(self, namespace, name, param):
        """
        初始化屏幕节点

        Args:
            namespace (str): 命名空间
            name (str): 节点名称
            param (dict): 初始化参数
        """
        ScreenNode.__init__(self, namespace, name, param)

        # 准星显示状态
        self.focus_show_status = False

        print("[INFO] [FocusHUDScreenNode] 屏幕节点初始化")

    def Create(self):
        """创建UI"""
        print("[INFO] [FocusHUDScreenNode] UI创建")

    # ===== 准星控制接口 =====

    def show_focus(self):
        """显示准星"""
        if not self.focus_show_status:
            self.focus_show_status = True

    def hide_focus(self):
        """隐藏准星"""
        if self.focus_show_status:
            self.focus_show_status = False

    def set_focus_visible(self, visible):
        """
        设置准星可见性

        Args:
            visible (bool): 是否可见
        """
        self.focus_show_status = visible

    # ===== 数据绑定 =====

    @ViewBinder.binding(ViewBinder.BF_BindBool, "#focus_status")
    def focus_visible(self):
        """
        绑定准星可见性到UI

        绑定流程:
            Python属性 focus_show_status (Boolean)
            → ViewBinder 绑定到 #focus_status 变量
            → UI JSON 中 binding_name: "#focus_status"
            → 控制 #visible 属性
            → 准星图像显示/隐藏

        Returns:
            bool: 准星是否可见
        """
        return self.focus_show_status
