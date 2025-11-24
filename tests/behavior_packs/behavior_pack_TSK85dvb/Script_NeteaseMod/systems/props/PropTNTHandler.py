# -*- coding: utf-8 -*-
"""
PropTNTHandler - TNT道具处理器

功能:
- 监听TNT物品使用事件
- 生成TNT实体并设置爆炸延时
- 使用BedWarsExplosion自定义爆炸系统
- 友军保护、防爆玻璃免疫、只破坏玩家放置方块

原文件: Parts/PropTNT/PropTNTPart.py
重构为: systems/props/PropTNTHandler.py
"""

from __future__ import print_function
import time
from .IPropHandler import IPropHandler
import mod.server.extraServerApi as serverApi


class PropTNTHandler(IPropHandler):
    """
    TNT道具处理器

    核心功能:
    - 监听ServerItemUseOnEvent事件
    - 生成TNT实体(2秒爆炸延时)
    - Tick检测TNT实体爆炸时机
    - 调用BedWarsExplosion执行爆炸
    """

    def __init__(self):
        super(PropTNTHandler, self).__init__()
        self.enable_tick = True  # 启用Tick更新
        self.event_registered = False

        # TNT实体跟踪字典
        # {entity_id: {'spawn_time': float, 'owner_id': str, 'team': str, 'pos': tuple}}
        self.tnt_entities = {}

        # 配置参数
        self.explode_time = 2.0  # 爆炸延时(秒)
        self.tick_interval = 0.05  # Tick检查间隔(秒)
        self.next_tick = 0  # 下次Tick执行时间

    def on_create(self, system):
        """
        道具处理器创建时调用

        Args:
            system: PropsManagementSystem实例
        """
        super(PropTNTHandler, self).on_create(system)

        # 注册物品使用事件监听
        self._register_item_use_event()

        print("[INFO] [PropTNTHandler] 创建完成")

    def on_destroy(self):
        """道具处理器销毁时调用"""
        # 取消事件监听
        self._unregister_item_use_event()

        # 清理所有TNT实体记录
        self.tnt_entities = {}

        super(PropTNTHandler, self).on_destroy()
        print("[INFO] [PropTNTHandler] 销毁完成")

    def on_update(self):
        """
        每帧更新(由PropsManagementSystem.Update调用)

        检测所有TNT实体的爆炸时机
        """
        now = time.time()

        # 频率控制: 每0.05秒执行一次
        if self.next_tick > now:
            return
        self.next_tick = now + self.tick_interval

        # 检测所有TNT实体
        self._check_tnt_explosions(now)

    def on_trigger(self, player_id, **kwargs):
        """
        道具触发(TNT不使用此接口,使用物品使用事件)

        Args:
            player_id (str): 玩家ID
            **kwargs: 道具参数
        """
        # TNT通过物品使用事件触发,不需要主动调用
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
                print("[INFO] [PropTNTHandler] 物品使用事件已注册")
            except Exception as e:
                print("[ERROR] [PropTNTHandler] 注册物品使用事件失败: {}".format(str(e)))

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
                print("[INFO] [PropTNTHandler] 物品使用事件已取消")
            except Exception as e:
                print("[ERROR] [PropTNTHandler] 取消物品使用事件失败: {}".format(str(e)))

    def _on_item_use_on(self, args):
        """
        物品使用事件处理

        当玩家右键使用TNT物品时触发

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
        # 只处理TNT物品
        if args.get('itemName') != 'minecraft:tnt':
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
                print("[ERROR] [PropTNTHandler] 游戏系统未找到")
                return

            # 查询玩家队伍
            team_module = getattr(game_system, 'team_module', None)
            if not team_module:
                print("[ERROR] [PropTNTHandler] 队伍模块未找到")
                return

            team = team_module.get_player_team(entity_id)

            # 生成TNT实体(在目标方块上方1格)
            tnt_pos = (x + 0.5, y + 1, z + 0.5)
            tnt_entity_id = self._spawn_tnt_entity(tnt_pos, dimension_id)

            if tnt_entity_id:
                # 记录TNT实体信息
                self.tnt_entities[tnt_entity_id] = {
                    'spawn_time': time.time(),
                    'owner_id': entity_id,
                    'team': team,
                    'pos': tnt_pos,
                    'dimension': dimension_id
                }

                # 减少物品数量
                self._consume_tnt_item(entity_id)

                # 阻止默认放置行为
                args['ret'] = True

                print("[INFO] [PropTNTHandler] TNT已放置: pos={} owner={} team={}".format(
                    tnt_pos, entity_id, team
                ))
            else:
                print("[ERROR] [PropTNTHandler] TNT实体生成失败")

        except Exception as e:
            print("[ERROR] [PropTNTHandler] 处理TNT使用失败: {}".format(str(e)))
            import traceback
            print(traceback.format_exc())

    # ========== TNT实体管理 ==========

    def _spawn_tnt_entity(self, pos, dimension_id):
        """
        生成TNT实体

        Args:
            pos (tuple): 生成位置 (x, y, z)
            dimension_id (int): 维度ID

        Returns:
            str: TNT实体ID,失败返回None
        """
        try:
            comp_game = serverApi.GetEngineCompFactory().CreateGame(serverApi.GetLevelId())

            # 生成TNT实体
            tnt_entity_id = comp_game.SpawnEntity(
                'ecbedwars:tnt',  # 自定义TNT实体类型
                pos,
                dimension_id
            )

            return tnt_entity_id

        except Exception as e:
            print("[ERROR] [PropTNTHandler] 生成TNT实体失败: {}".format(str(e)))
            import traceback
            print(traceback.format_exc())
            return None

    def _consume_tnt_item(self, player_id):
        """
        减少玩家手持的TNT物品数量

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

            if item_dict and item_dict.get('newItemName') == 'minecraft:tnt':
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
            print("[ERROR] [PropTNTHandler] 减少TNT物品失败: {}".format(str(e)))

    # ========== 爆炸检测 ==========

    def _check_tnt_explosions(self, now):
        """
        检测所有TNT实体的爆炸时机

        Args:
            now (float): 当前时间戳
        """
        # 收集需要爆炸的TNT
        entities_to_explode = []

        for entity_id, data in self.tnt_entities.items():
            spawn_time = data['spawn_time']

            # 检查是否超时
            if now - spawn_time >= self.explode_time:
                entities_to_explode.append(entity_id)

        # 执行爆炸
        for entity_id in entities_to_explode:
            self._trigger_explosion(entity_id)

    def _trigger_explosion(self, entity_id):
        """
        触发TNT爆炸

        Args:
            entity_id (str): TNT实体ID
        """
        try:
            # 获取TNT数据
            data = self.tnt_entities.pop(entity_id, None)
            if not data:
                return

            # 获取游戏系统
            game_system = self.get_game_system()
            if not game_system:
                return

            # 导入爆炸系统
            from systems.util.BedWarsExplosion import BedWarsExplosion

            # 创建爆炸实例
            explosion = BedWarsExplosion(
                data['dimension'],    # 维度ID
                data['pos'],          # 爆炸中心位置
                4,                    # 爆炸半径(4格)
                entity_id,            # 爆炸源实体ID
                data['owner_id']      # 使用者ID
            )

            # 配置爆炸参数
            self._configure_explosion(explosion, game_system, data)

            # 执行爆炸
            explosion.explode()

            # 销毁TNT实体（先检查实体是否存在）
            comp_game = serverApi.GetEngineCompFactory().CreateGame(serverApi.GetLevelId())
            try:
                comp_entity_type = serverApi.GetEngineCompFactory().CreateEngineType(entity_id)
                if comp_entity_type.GetEngineTypeStr():
                    comp_game.DestroyEntity(entity_id)
                else:
                    print("[WARN] [PropTNTHandler] TNT实体已不存在: {}".format(entity_id))
            except:
                # 实体不存在或获取失败，忽略
                print("[WARN] [PropTNTHandler] 无法销毁TNT实体（可能已被销毁）: {}".format(entity_id))

            print("[INFO] [PropTNTHandler] TNT爆炸: pos={} owner={}".format(
                data['pos'], data['owner_id']
            ))

        except Exception as e:
            print("[ERROR] [PropTNTHandler] TNT爆炸失败: {}".format(str(e)))
            import traceback
            print(traceback.format_exc())

    def _configure_explosion(self, explosion, game_system, tnt_data):
        """
        配置爆炸参数

        Args:
            explosion: BedWarsExplosion实例
            game_system: BedWarsGameSystem实例
            tnt_data: TNT实体数据
        """
        # 配置1: 染色玻璃完全免疫爆炸
        explosion.explosion_resistance_map = {
            "minecraft:stained_glass": 6000
        }

        # 配置2: 只破坏玩家放置的方块
        def check_valid_pos(pos):
            """检查方块是否可以被破坏"""
            placed_blocks = getattr(game_system, 'placed_blocks', set())
            return pos in placed_blocks

        explosion.check_valid_pos = check_valid_pos

        # 配置3: 只对存活且未重生的玩家造成伤害
        def check_valid_hurt_target(target_id):
            """检查实体是否可以受到伤害"""
            team_module = getattr(game_system, 'team_module', None)
            respawning = getattr(game_system, 'respawning', set())

            if not team_module:
                return True

            # 玩家必须存活且未在重生中
            is_alive = team_module.is_player_alive(target_id)
            not_respawning = target_id not in respawning

            return is_alive and not_respawning

        explosion.check_valid_hurt_target = check_valid_hurt_target

        # 配置4: 友军只造成微量伤害
        def check_tiny_hurt(target_id):
            """检查是否只造成微量伤害(友军保护)"""
            team_module = getattr(game_system, 'team_module', None)
            if not team_module:
                return False

            # 获取爆炸源实体拥有者(使用者)
            owner_id = tnt_data['owner_id']
            source_team = tnt_data['team']

            # 如果目标和使用者是同一队伍,则只造成微量伤害
            target_team = team_module.get_player_team(target_id)

            return target_team == source_team

        explosion.check_tiny_hurt = check_tiny_hurt
