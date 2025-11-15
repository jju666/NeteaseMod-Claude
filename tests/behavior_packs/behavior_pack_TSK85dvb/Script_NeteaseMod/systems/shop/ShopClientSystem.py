# -*- coding: utf-8 -*-
"""
商店客户端系统

功能:
- 监听商店打开事件
- 注册商店UI
- 显示商店界面
"""

from __future__ import print_function
import mod.client.extraClientApi as clientApi


class ShopClientSystem(clientApi.GetClientSystemCls()):
    """
    商店客户端系统

    职责:
    1. 注册BedWarsShopScreenNode UI
    2. 监听服务端商店打开事件
    3. 显示商店UI界面
    """

    def __init__(self, namespace, systemName):
        super(ShopClientSystem, self).__init__(namespace, systemName)

        print("[ShopClientSystem] 手动调用Create()完成系统初始化")
        self.Create()

    def Create(self):
        """系统创建时的初始化逻辑"""
        print("[ShopClientSystem] Create() 被调用")

        # 监听UI初始化完成事件
        self.ListenForEvent(
            clientApi.GetEngineNamespace(),
            clientApi.GetEngineSystemName(),
            "UiInitFinished",
            self,
            self.OnUiInitFinished
        )

        # 监听服务端商店打开事件
        # 注意：监听的系统名是ShopServerSystem（服务端发送者），而不是ShopClientSystem（自己）
        # 原因：NotifyToClient发送的事件来源是发送者系统名
        # 参考：GamingStateSystem.py:717 - 客户端监听服务端系统的事件
        from Script_NeteaseMod.modConfig import MOD_NAME
        self.ListenForEvent(
            MOD_NAME,
            "ShopServerSystem",  # 修复：监听服务端系统而非自己
            "BedWarsShopTryOpen",
            self,
            self.OnShopTryOpen
        )

        # 监听商店刷新事件
        self.ListenForEvent(
            MOD_NAME,
            "ShopServerSystem",  # 修复：监听服务端系统
            "BedWarsShopRefresh",
            self,
            self.OnShopRefresh
        )

        # 监听购买结果事件
        self.ListenForEvent(
            MOD_NAME,
            "ShopServerSystem",  # 修复：监听服务端系统
            "BedWarsShopBuyResult",
            self,
            self.OnShopBuyResult
        )

    def Destroy(self):
        """系统销毁时自动被引擎调用"""
        print("[ShopClientSystem] Destroy() 被调用")

    def OnUiInitFinished(self, args):
        """UI初始化完成 - 注册商店UI"""
        print("[ShopClientSystem] UI初始化完成，注册商店UI")

        from Script_NeteaseMod.modConfig import MOD_NAME

        # 注册商店UI屏幕节点
        # 修复：UI文件位于systems/ui/目录，而非systems/shop/ui/
        # 参考：BedWarsShopScreenNode.py注释 - 新路径: systems/ui/BedWarsShopScreenNode.py
        clientApi.RegisterUI(
            MOD_NAME,
            "bedwars_shop_screen",
            "Script_NeteaseMod.systems.ui.BedWarsShopScreenNode.BedWarsShopScreenNode",
            "bedwars_shop.main"
        )

        print("[ShopClientSystem] 商店UI注册成功: bedwars_shop_screen")

    def OnShopTryOpen(self, args):
        """
        收到服务端商店打开请求

        Args:
            args: {
                'ui_dict': {...},  # 商店UI数据
                'player_id': str   # 玩家ID
            }
        """
        print("[ShopClientSystem] 收到商店打开事件")

        ui_dict = args.get('ui_dict')
        if not ui_dict:
            print("[ShopClientSystem] [错误] ui_dict为空")
            return

        from Script_NeteaseMod.modConfig import MOD_NAME

        # 显示商店UI
        # 注意：BedWarsShopScreenNode的__init__中 self.ui_data = param
        # 所以param应该直接是ui_dict，而不是包装在字典中
        # 参考：BedWarsShopScreenNode.py:43 self.ui_data = param
        clientApi.PushScreen(
            MOD_NAME,
            "bedwars_shop_screen",
            ui_dict  # 修复：直接传递ui_dict，而不是包装在字典中
        )

        print("[ShopClientSystem] 商店UI已显示")

    def OnShopRefresh(self, args):
        """
        刷新商店UI

        Args:
            args: {
                'ui_dict': {...}  # 更新后的商店UI数据
            }
        """
        print("[ShopClientSystem] 收到商店刷新事件")

        ui_dict = args.get('ui_dict')
        if not ui_dict:
            print("[ShopClientSystem] [错误] ui_dict为空，无法刷新")
            return

        # 获取当前栈顶的ScreenNode
        from Script_NeteaseMod.systems.ui.BedWarsShopScreenNode import BedWarsShopScreenNode

        current_screen = clientApi.GetTopScreen()

        # 检查当前屏幕是否是商店UI
        if current_screen is not None and isinstance(current_screen, BedWarsShopScreenNode):
            print("[ShopClientSystem] 找到商店UI，开始刷新")

            # 更新UI数据
            current_screen.ui_data = ui_dict

            # 调用UpdateScreen刷新UI
            current_screen.UpdateScreen()

            print("[ShopClientSystem] 商店UI刷新完成")
        else:
            print("[ShopClientSystem] [警告] 当前没有打开商店UI，无法刷新")

    def OnShopBuyResult(self, args):
        """
        购买结果通知

        Args:
            args: {
                'success': bool,    # 是否成功
                'msg': str          # 提示消息
            }
        """
        success = args.get('success', False)
        msg = args.get('msg', '')

        print("[ShopClientSystem] 购买结果: success={}, msg={}".format(success, msg))

        # 1. 播放音效（与老项目一致：note.pling(成功)/note.bass(失败)，使用音调变化）
        import math
        player_id = clientApi.GetLocalPlayerId()
        if player_id:
            # 获取玩家位置用于播放音效（PlayCustomMusic需要位置参数）
            comp_pos = clientApi.GetEngineCompFactory().CreatePos(player_id)
            pos = comp_pos.GetPos()
            if pos:
                comp_sound = clientApi.GetEngineCompFactory().CreateCustomAudio(player_id)
                if success:
                    # 成功音效：note.pling 高音调(key=20, pitch≈1.587)
                    pitch = math.pow(2, (20.0 - 12) / 12)
                    comp_sound.PlayCustomMusic("note.pling", pos, 1.0, pitch, False)
                else:
                    # 失败音效：note.bass 低音调(key=0, pitch=0.5)
                    pitch = math.pow(2, (0.0 - 12) / 12)
                    comp_sound.PlayCustomMusic("note.bass", pos, 1.0, pitch, False)

        # 2. 显示提示消息到商店UI的tooltip
        from Script_NeteaseMod.systems.ui.BedWarsShopScreenNode import BedWarsShopScreenNode

        current_screen = clientApi.GetTopScreen()

        # 检查当前屏幕是否是商店UI
        if current_screen is not None and isinstance(current_screen, BedWarsShopScreenNode):
            print("[ShopClientSystem] 找到商店UI，显示购买结果提示")

            # 调用show_tooltip显示消息
            current_screen.show_tooltip(msg)

            print("[ShopClientSystem] 购买结果提示已显示")
        else:
            print("[ShopClientSystem] [警告] 当前没有打开商店UI，无法显示提示")

    def SendBuyRequest(self, category_index, goods_index, goods_key):
        """
        发送购买请求到服务端

        Args:
            category_index: 分类索引
            goods_index: 商品索引
            goods_key: 商品键
        """
        from Script_NeteaseMod.modConfig import MOD_NAME

        # 获取本地玩家ID
        player_id = clientApi.GetLocalPlayerId()

        self.NotifyToServer(
            "BedWarsShopTryBuy",
            {
                'player_id': player_id,  # ⭐ [修复] 添加player_id字段
                'category_index': category_index,
                'goods_index': goods_index,
                'goods_key': goods_key
            }
        )

        print("[ShopClientSystem] 已发送购买请求: player={}, key={}".format(player_id, goods_key))
