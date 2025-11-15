# -*- coding: utf-8 -*-
"""
FocusHUDClientSystem - 焦点准星客户端系统

功能说明：
    为火球武器提供瞄准辅助功能。
    当玩家手持火球时，屏幕中央显示白色垂直准星。

重构说明：
    老项目: ECFocusNodePart零件实现
    新项目: 独立的ClientSystem实现

核心职责：
    1. 监听玩家手持物品变化事件
    2. 检测是否为火球物品
    3. 控制准星UI的显示/隐藏
"""

import mod.client.extraClientApi as clientApi

ClientSystem = clientApi.GetClientSystemCls()


class FocusHUDClientSystem(ClientSystem):
    """焦点准星客户端系统"""

    def __init__(self, namespace, systemName):
        super(FocusHUDClientSystem, self).__init__(namespace, systemName)

        # UI相关
        self.screen_node = None
        self.ui_node_path = "/ScreenRoot/FocusHUDScreen"

        # 需要显示准星的物品列表
        self.focus_items = [
            "ecbedwars:fireball",      # 火球
            # 可以扩展支持其他武器：
            # "minecraft:bow",           # 弓
            # "ecbedwars:snowball",      # 雪球
        ]

        print("[INFO] [FocusHUDClientSystem] 焦点准星系统初始化")

    def Create(self):
        """系统创建时调用"""
        # 注册事件监听
        # 监听手持物品变化事件
        self.ListenForEvent(
            clientApi.GetEngineNamespace(),
            clientApi.GetEngineSystemName(),
            "OnCarriedNewItemChangedClientEvent",
            self,
            self._on_carried_item_changed
        )

        # 监听UI初始化完成事件
        self.ListenForEvent(
            clientApi.GetEngineNamespace(),
            clientApi.GetEngineSystemName(),
            "UiInitFinished",
            self,
            self._on_ui_init_finished
        )

        print("[INFO] [FocusHUDClientSystem] 事件监听注册完成")

    def Destroy(self):
        """系统销毁"""
        self._cleanup_ui()
        print("[INFO] [FocusHUDClientSystem] 系统销毁")
        super(FocusHUDClientSystem, self).Destroy()

    def OnDestroy(self):
        """系统销毁回调"""
        pass

    # ===== UI管理 =====

    def _on_ui_init_finished(self, args):
        """UI初始化完成事件"""
        self._create_ui()

    def _create_ui(self):
        """创建UI"""
        try:
            # 创建ScreenNode
            self.screen_node = clientApi.CreateUI(
                "Script_NeteaseMod",
                "focus_hud.main",
                {
                    "class_name": "Script_NeteaseMod.systems.ui.FocusHUDScreenNode.FocusHUDScreenNode"
                }
            )

            if self.screen_node:
                print("[INFO] [FocusHUDClientSystem] UI创建成功")
                # 初始状态为隐藏
                self.screen_node.hide_focus()
            else:
                print("[ERROR] [FocusHUDClientSystem] UI创建失败")

        except Exception as e:
            print("[ERROR] [FocusHUDClientSystem] 创建UI异常: {}".format(e))

    def _cleanup_ui(self):
        """清理UI"""
        if self.screen_node:
            try:
                # 销毁ScreenNode
                clientApi.DestroyUI("Script_NeteaseMod", "focus_hud.main")
                self.screen_node = None
                print("[INFO] [FocusHUDClientSystem] UI已清理")
            except Exception as e:
                print("[ERROR] [FocusHUDClientSystem] 清理UI异常: {}".format(e))

    # ===== 事件处理 =====

    def _on_carried_item_changed(self, args):
        """
        手持物品变化事件

        Args:
            args (dict): {
                "playerId": str,           # 玩家ID
                "itemDict": dict,          # 物品信息
                "auxValue": int,           # 附加值
                "slot": int                # 物品栏位
            }
        """
        if not self.screen_node:
            # UI未创建，忽略
            return

        try:
            # 获取物品信息
            item_dict = args.get('itemDict', {})
            item_name = item_dict.get('itemName', '')

            # 检查是否为需要显示准星的物品
            if item_name in self.focus_items:
                self.screen_node.show_focus()
            else:
                self.screen_node.hide_focus()
                if item_name:  # 只在有物品时输出日志
                    pass

        except Exception as e:
            print("[ERROR] [FocusHUDClientSystem] 处理物品变化事件异常: {}".format(e))

    # ===== 配置方法 =====

    def add_focus_item(self, item_name):
        """
        添加支持准星的物品

        Args:
            item_name (str): 物品标识符
        """
        if item_name not in self.focus_items:
            self.focus_items.append(item_name)
            print("[INFO] [FocusHUDClientSystem] 添加准星支持物品: {}".format(item_name))

    def remove_focus_item(self, item_name):
        """
        移除支持准星的物品

        Args:
            item_name (str): 物品标识符
        """
        if item_name in self.focus_items:
            self.focus_items.remove(item_name)
            print("[INFO] [FocusHUDClientSystem] 移除准星支持物品: {}".format(item_name))

    def set_focus_items(self, item_list):
        """
        设置支持准星的物品列表

        Args:
            item_list (list): 物品标识符列表
        """
        self.focus_items = list(item_list)
        print("[INFO] [FocusHUDClientSystem] 设置准星支持物品列表: {}".format(self.focus_items))
