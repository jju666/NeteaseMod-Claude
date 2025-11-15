# -*- coding: utf-8 -*-
"""
PropIronGolemHandler - 铁傀儡召唤道具处理器

功能:
- 监听物品使用事件(ServerItemUseOnEvent)
- 召唤归属于玩家队伍的铁傀儡实体
- 处理道具消耗逻辑
- 验证玩家队伍权限

原文件: Parts/PropIronGolem/PropIronGolemPart.py
重构为: systems/props/PropIronGolemHandler.py
"""

from __future__ import print_function
from .IPropHandler import IPropHandler
import mod.server.extraServerApi as serverApi


class PropIronGolemHandler(IPropHandler):
    """
    铁傀儡召唤道具处理器

    核心功能:
    - 监听ServerItemUseOnEvent事件
    - 验证玩家队伍归属
    - 生成铁傀儡实体并设置队伍
    - 消耗道具物品
    """

    def __init__(self):
        super(PropIronGolemHandler, self).__init__()
        self.event_registered = False

        # 铁傀儡实体标识符(与老项目保持一致)
        self.item_identifier = 'ecbedwars:iron_golem'
        self.entity_identifier = 'ecbedwars:iron_golem'

    def on_create(self, system):
        """
        道具处理器创建时调用

        Args:
            system: PropsManagementSystem实例
        """
        super(PropIronGolemHandler, self).on_create(system)

        # 注册物品使用事件监听
        self._register_item_use_event()

        print("[INFO] [PropIronGolemHandler] 创建完成")

    def on_destroy(self):
        """道具处理器销毁时调用"""
        # 取消事件监听
        self._unregister_item_use_event()

        super(PropIronGolemHandler, self).on_destroy()
        print("[INFO] [PropIronGolemHandler] 销毁完成")

    def on_trigger(self, player_id, **kwargs):
        """
        道具触发(铁傀儡不使用此接口,使用物品使用事件)

        Args:
            player_id (str): 玩家ID
            **kwargs: 道具参数
        """
        # 铁傀儡通过物品使用事件触发,不需要主动调用
        pass

    # ========== 事件监听 ==========

    def _register_item_use_event(self):
        """注册物品使用事件"""
        if not self.event_registered:
            try:
                self.system.ListenForEvent(
                    serverApi.GetEngineNamespace(),
                    serverApi.GetEngineSystemName(),
                    'ServerItemUseOnEvent',
                    self,
                    self._on_item_use_on
                )
                self.event_registered = True
                print("[INFO] [PropIronGolemHandler] 物品使用事件已注册")
            except Exception as e:
                print("[ERROR] [PropIronGolemHandler] 注册物品使用事件失败: {}".format(str(e)))

    def _unregister_item_use_event(self):
        """取消物品使用事件监听"""
        if self.event_registered:
            try:
                self.system.UnListenForEvent(
                    serverApi.GetEngineNamespace(),
                    serverApi.GetEngineSystemName(),
                    'ServerItemUseOnEvent',
                    self,
                    self._on_item_use_on
                )
                self.event_registered = False
                print("[INFO] [PropIronGolemHandler] 物品使用事件已取消")
            except Exception as e:
                print("[ERROR] [PropIronGolemHandler] 取消物品使用事件失败: {}".format(str(e)))

    def _on_item_use_on(self, args):
        """
        物品使用事件处理

        当玩家右键使用铁傀儡蛋时触发

        Args:
            args: {
                'itemName': str,      # 物品ID
                'entityId': str,      # 使用者实体ID
                'x': int,             # 目标X坐标
                'y': int,             # 目标Y坐标
                'z': int,             # 目标Z坐标
                'dimensionId': int,   # 维度ID
                'blockName': str,     # 目标方块名称
                'face': int,          # 点击的方块面
            }
        """
        # 只处理铁傀儡道具
        if args.get('itemName') != self.item_identifier:
            return

        try:
            entity_id = args.get('entityId')
            x = args.get('x')
            y = args.get('y')
            z = args.get('z')
            dimension_id = args.get('dimensionId')

            # 获取游戏系统
            game_system = self.get_game_system()
            if not game_system:
                print("[ERROR] [PropIronGolemHandler] 游戏系统未找到")
                return

            # 查询玩家队伍
            team_module = getattr(game_system, 'team_module', None)
            if not team_module:
                print("[ERROR] [PropIronGolemHandler] 队伍模块未找到")
                return

            team = team_module.get_player_team(entity_id)
            if not team:
                # 玩家无队伍,无法使用道具
                return

            # 生成铁傀儡实体(在目标方块上方1格)
            golem_pos = (x + 0.5, y + 1, z + 0.5)
            golem_entity_id = self._spawn_iron_golem(golem_pos, dimension_id, team, entity_id)

            if golem_entity_id:
                # 减少物品数量
                self._consume_item(entity_id)

                print("[INFO] [PropIronGolemHandler] 铁傀儡已召唤: pos={} owner={} team={}".format(
                    golem_pos, entity_id, team
                ))
            else:
                print("[ERROR] [PropIronGolemHandler] 铁傀儡实体生成失败")

        except Exception as e:
            print("[ERROR] [PropIronGolemHandler] 处理铁傀儡使用失败: {}".format(str(e)))
            import traceback
            print(traceback.format_exc())

    # ========== 实体生成 ==========

    def _spawn_iron_golem(self, pos, dimension_id, team, owner_id):
        """
        生成铁傀儡实体

        Args:
            pos (tuple): 生成位置 (x, y, z)
            dimension_id (int): 维度ID
            team (str): 队伍名称
            owner_id (str): 召唤者ID

        Returns:
            str: 铁傀儡实体ID,失败返回None
        """
        try:
            comp_game = serverApi.GetEngineCompFactory().CreateGame(serverApi.GetLevelId())

            # 生成铁傀儡实体
            golem_entity_id = comp_game.SpawnEntity(
                self.entity_identifier,
                pos,
                dimension_id
            )

            if not golem_entity_id:
                print("[ERROR] [PropIronGolemHandler] SpawnEntity返回None")
                return None

            # 设置铁傀儡的队伍归属(通过EntityExtraData组件)
            self._set_golem_team(golem_entity_id, team, owner_id)

            return golem_entity_id

        except Exception as e:
            print("[ERROR] [PropIronGolemHandler] 生成铁傀儡实体失败: {}".format(str(e)))
            import traceback
            print(traceback.format_exc())
            return None

    def _set_golem_team(self, golem_entity_id, team, owner_id):
        """
        设置铁傀儡的队伍归属

        通过EntityExtraData组件存储队伍信息和召唤者ID

        Args:
            golem_entity_id (str): 铁傀儡实体ID
            team (str): 队伍名称
            owner_id (str): 召唤者ID
        """
        try:
            # 获取EntityExtraData组件
            comp_extra_data = serverApi.GetEngineCompFactory().CreateExtraData(golem_entity_id)

            # 存储队伍信息
            comp_extra_data.SetExtraData("bedwars_team", team)

            # 存储召唤者ID
            comp_extra_data.SetExtraData("bedwars_owner", owner_id)

        except Exception as e:
            print("[ERROR] [PropIronGolemHandler] 设置铁傀儡队伍失败: {}".format(str(e)))

    # ========== 道具消耗 ==========

    def _consume_item(self, player_id):
        """
        减少玩家手持的铁傀儡道具数量

        Args:
            player_id (str): 玩家ID
        """
        try:
            comp_item = serverApi.GetEngineCompFactory().CreateItem(player_id)

            # 获取当前选中的物品槽位
            comp_inv = serverApi.GetEngineCompFactory().CreateInventoryComponent(player_id)
            slot_id = comp_inv.GetSelectSlotId()

            # 获取该槽位的物品
            item_dict = comp_item.GetPlayerItem(
                serverApi.GetMinecraftEnum().ItemPosType.INVENTORY,
                slot_id
            )

            if item_dict and item_dict.get('newItemName') == self.item_identifier:
                # 减少数量
                item_dict['count'] -= 1

                # 更新物品
                if item_dict['count'] > 0:
                    comp_item.SpawnItemToPlayerInv(item_dict, player_id, slot_id)
                else:
                    # 数量为0,清空槽位
                    comp_item.SpawnItemToPlayerInv(
                        {'newItemName': 'minecraft:air', 'count': 0},
                        player_id,
                        slot_id
                    )

        except Exception as e:
            print("[ERROR] [PropIronGolemHandler] 减少铁傀儡道具失败: {}".format(str(e)))
