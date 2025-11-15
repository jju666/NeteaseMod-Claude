# -*- coding: utf-8 -*-
"""
商店上下文适配器

目的: 模拟老项目BedWarsShopPart接口，使数据模型代码无需修改

重构说明:
- 桥接新架构(ShopPresetDefServer) 和 老架构(ShopInstance等数据模型)
- 提供Part需要的核心接口方法
- 避免直接修改639行的ShopGoodsPool.py
"""

from __future__ import print_function
import mod.server.extraServerApi as serverApi
from modConfig import MOD_NAME


class ShopContextAdapter(object):
    """
    适配器类 - 模拟BedWarsShopPart接口

    用于桥接新架构(ShopPresetDefServer)和老架构(数据模型)
    """

    def __init__(self, preset_instance, shop_preset_def):
        """
        Args:
            preset_instance: ECPreset的PresetInstance对象
            shop_preset_def: ShopPresetDefServer实例
        """
        self.preset_instance = preset_instance
        self.shop_preset_def = shop_preset_def
        self.dimension = None  # 将在ShopPresetDefServer中设置
        self.team_id = None    # 将在ShopPresetDefServer中设置

        # 获取必要的系统引用
        self.bedwars_game_system = serverApi.GetSystem(MOD_NAME, "BedWarsGameSystem")
        self.room_management_system = serverApi.GetSystem(MOD_NAME, "RoomManagementSystem")

    def BroadcastPresetSystemEvent(self, event_name, data):
        """
        广播预设系统事件

        在新架构中，使用PresetInstance的事件发布机制
        """
        print("[ShopContextAdapter] BroadcastPresetSystemEvent: {}".format(event_name))

        # 发布到ECPreset事件总线
        self.preset_instance.publish_event(event_name, data)

        # 同时通过BedWarsGameSystem广播到全局（如果需要）
        if self.bedwars_game_system:
            # 通过状态机广播
            pass

    def LogError(self, msg):
        """记录错误日志"""
        print("[ShopContextAdapter] [ERROR] {}".format(msg))

    def GetParent(self):
        """
        获取父对象（模拟老项目的GetParent()）

        返回一个包含dimension属性的对象
        """
        class ParentMock:
            def __init__(self, dimension):
                self.dimension = dimension

        return ParentMock(self.dimension)

    def get_team_upgrades(self):
        """
        获取队伍升级管理器

        用于商品池中check_can_buy检查升级等级
        """
        if self.bedwars_game_system and self.team_id:
            return self.bedwars_game_system.team_upgrades.get(self.team_id)
        return None

    def get_player_team_id(self, player_id):
        """获取玩家队伍ID"""
        if self.room_management_system:
            team_module = self.room_management_system.team_module
            if team_module:
                return team_module.get_player_team(player_id)
        return None

    def get_dimension_id(self):
        """获取维度ID"""
        return self.dimension

    def get_shop_npc_id(self):
        """获取商店NPC实体ID"""
        return self.shop_preset_def.shop_npc_id

    def notify_client_refresh_ui(self, player_id):
        """通知客户端刷新UI"""
        if not self.shop_preset_def.shop_instance:
            print("[ShopContextAdapter] [错误] ShopInstance未创建")
            return

        # 生成UI数据
        ui_dict = self.shop_preset_def.shop_instance.to_ui_dict(player_id)

        # 发送刷新事件到客户端
        from modConfig import MOD_NAME
        shop_client_system = serverApi.GetSystem(MOD_NAME, "ShopClientSystem")
        if shop_client_system:
            shop_client_system.NotifyToClient(
                player_id,
                "BedWarsShopRefresh",
                {'ui_dict': ui_dict}
            )

    def play_sound(self, sound_name, player_id):
        """播放音效"""
        comp_game = serverApi.GetEngineCompFactory().CreateGame(serverApi.GetLevelId())
        comp_game.PlaySound(player_id, sound_name)
