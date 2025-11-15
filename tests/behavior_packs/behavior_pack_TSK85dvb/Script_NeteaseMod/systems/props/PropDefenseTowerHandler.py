# -*- coding: utf-8 -*-
"""
PropDefenseTowerHandler - 防御塔道具处理器

功能:
- 监听防御塔物品使用事件
- 根据玩家朝向自动旋转塔的结构
- 使用异步定时器逐步构建防御塔（动画效果）
- 与 BedWarsGameSystem 协同工作,实现队伍颜色方块放置
- 自动消耗玩家背包中的防御塔道具

原文件: Parts/PropDefenseTower/PropDefenseTowerPart.py
重构为: systems/props/PropDefenseTowerHandler.py

参考文档: D:\EcWork\NetEaseMapECBedWars备份\docs\PropDefenseTower.md
"""

from __future__ import print_function
from .IPropHandler import IPropHandler
import mod.server.extraServerApi as serverApi


class PropDefenseTowerHandler(IPropHandler):
    """
    防御塔道具处理器

    核心功能:
    - 监听ServerItemUseOnEvent事件
    - 计算玩家朝向和塔的旋转角度
    - 创建DefenseTowerBuilder构建器
    - 异步建造防御塔（7x7x8结构）
    - 消耗道具物品
    """

    def __init__(self):
        super(PropDefenseTowerHandler, self).__init__()
        self.event_registered = False

        # 防御塔道具标识符
        self.item_identifier = 'ecbedwars:defense_tower'

    def on_create(self, system):
        """
        道具处理器创建时调用

        Args:
            system: PropsManagementSystem实例
        """
        super(PropDefenseTowerHandler, self).on_create(system)

        # 注册物品使用事件监听
        self._register_item_use_event()

        print("[INFO] [PropDefenseTowerHandler] 创建完成")

    def on_destroy(self):
        """道具处理器销毁时调用"""
        # 取消事件监听
        self._unregister_item_use_event()

        super(PropDefenseTowerHandler, self).on_destroy()
        print("[INFO] [PropDefenseTowerHandler] 销毁完成")

    def on_trigger(self, player_id, **kwargs):
        """
        道具触发(防御塔不使用此接口,使用物品使用事件)

        Args:
            player_id (str): 玩家ID
            **kwargs: 道具参数
        """
        # 防御塔通过物品使用事件触发,不需要主动调用
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
                print("[INFO] [PropDefenseTowerHandler] 物品使用事件已注册")
            except Exception as e:
                print("[ERROR] [PropDefenseTowerHandler] 注册物品使用事件失败: {}".format(str(e)))

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
                print("[INFO] [PropDefenseTowerHandler] 物品使用事件已取消")
            except Exception as e:
                print("[ERROR] [PropDefenseTowerHandler] 取消物品使用事件失败: {}".format(str(e)))

    def _on_item_use_on(self, args):
        """
        物品使用事件处理

        当玩家右键使用防御塔物品时触发

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
        # 只处理防御塔物品
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
                print("[ERROR] [PropDefenseTowerHandler] 游戏系统未找到")
                return

            # 查询玩家队伍
            team_module = getattr(game_system, 'team_module', None)
            if not team_module:
                print("[ERROR] [PropDefenseTowerHandler] 队伍模块未找到")
                return

            team = team_module.get_player_team(entity_id)
            if not team:
                return

            # 获取队伍类型对象
            # [FIX 2025-11-04] 修复Python 2.7导入路径问题
            from Script_NeteaseMod.systems.team.TeamType import team_types
            team_type = team_types.get(team)
            if not team_type:
                print("[ERROR] [PropDefenseTowerHandler] 未找到队伍类型: {}".format(team))
                return

            # 获取玩家旋转角度
            comp_rot = serverApi.GetEngineCompFactory().CreateRot(entity_id)
            rot = comp_rot.GetRot()

            # 计算塔的朝向(对齐到90度的倍数)
            yaw = int((rot[1] + 90 - 45) % 360 / 90) * 90

            # 计算梯子方向
            ladder_aux = self._calculate_ladder_direction(yaw)

            # 构建方块配置
            block_palette = {
                1: {
                    'name': 'minecraft:wool',
                    'aux': team_type.item_color  # 队伍颜色羊毛
                },
                2: {
                    'name': 'minecraft:ladder',
                    'aux': ladder_aux  # 梯子朝向
                }
            }

            # 创建构建器并开始建造
            from systems.util.DefenseTowerBuilder import DefenseTowerBuilder
            DefenseTowerBuilder(
                self.system,
                dimension_id,
                (x, y, z),
                yaw,
                block_palette,
                game_system
            )

            # 消耗物品
            self._consume_item(entity_id)

            # 阻止默认行为
            args['ret'] = True

            print("[INFO] [PropDefenseTowerHandler] 防御塔开始建造: pos=({},{},{}) yaw={} team={}".format(
                x, y, z, yaw, team
            ))

        except Exception as e:
            print("[ERROR] [PropDefenseTowerHandler] 处理防御塔使用失败: {}".format(str(e)))
            import traceback
            print(traceback.format_exc())

    # ========== 辅助方法 ==========

    def _calculate_ladder_direction(self, yaw):
        """
        计算梯子方向

        Args:
            yaw (int): 旋转角度(0/90/180/270)

        Returns:
            int: 梯子朝向值
        """
        # Minecraft 梯子朝向值映射
        # 2: 朝南(+Z), 3: 朝北(-Z), 4: 朝东(+X), 5: 朝西(-X)
        ladder_direction_map = {
            0: 2,    # 南向梯子
            90: 5,   # 西向梯子
            180: 3,  # 北向梯子
            270: 4   # 东向梯子
        }
        return ladder_direction_map.get(yaw, 2)

    def _consume_item(self, player_id):
        """
        减少玩家手持的防御塔物品数量

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
            print("[ERROR] [PropDefenseTowerHandler] 减少防御塔物品失败: {}".format(str(e)))
