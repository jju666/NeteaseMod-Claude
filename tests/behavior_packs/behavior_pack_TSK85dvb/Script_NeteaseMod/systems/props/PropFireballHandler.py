# -*- coding: utf-8 -*-
"""
PropFireballHandler - 火球道具处理器

功能:
- 监听实体定义事件触发爆炸
- 自定义爆炸系统(BedWarsExplosion)
- 只破坏玩家放置的方块
- 友军伤害减免

原文件: Parts/PropFireball/PropFireballPart.py
重构为: systems/props/PropFireballHandler.py
"""

from __future__ import print_function
from .IPropHandler import IPropHandler
import mod.server.extraServerApi as serverApi


class PropFireballHandler(IPropHandler):
    """
    火球道具处理器

    核心功能:
    - 监听火球爆炸事件(EntityDefinitionsEventServerEvent)
    - 使用自定义爆炸系统(BedWarsExplosion)
    - 配置爆炸参数(友军保护、防爆玻璃等)
    """

    def __init__(self):
        super(PropFireballHandler, self).__init__()
        self.event_registered = False

    def on_create(self, system):
        """
        道具处理器创建时调用

        Args:
            system: PropsManagementSystem实例
        """
        super(PropFireballHandler, self).on_create(system)

        # 注册实体定义事件监听
        self._register_entity_event()

    def on_destroy(self):
        """道具处理器销毁时调用"""
        # 取消事件监听
        self._unregister_entity_event()

        super(PropFireballHandler, self).on_destroy()

    def on_trigger(self, player_id, **kwargs):
        """
        道具触发(火球道具不使用此接口,使用实体事件)

        Args:
            player_id (str): 玩家ID
            **kwargs: 道具参数
        """
        # 火球道具通过右键使用自动触发,不需要主动调用
        pass

    # ========== 事件监听 ==========

    def _register_entity_event(self):
        """注册实体定义事件"""
        if not self.event_registered:
            try:
                self.system.ListenForEvent(
                    serverApi.GetEngineNamespace(),
                    serverApi.GetEngineSystemName(),
                    'EntityDefinitionsEventServerEvent',
                    self,
                    self._on_entity_definitions_event
                )
                self.event_registered = True
                print("[INFO] [PropFireballHandler] 实体定义事件已注册")
            except Exception as e:
                print("[ERROR] [PropFireballHandler] 注册实体事件失败: {}".format(str(e)))

    def _unregister_entity_event(self):
        """取消实体定义事件监听"""
        if self.event_registered:
            try:
                self.system.UnListenForEvent(
                    serverApi.GetEngineNamespace(),
                    serverApi.GetEngineSystemName(),
                    'EntityDefinitionsEventServerEvent',
                    self,
                    self._on_entity_definitions_event
                )
                self.event_registered = False
                print("[INFO] [PropFireballHandler] 实体定义事件已取消")
            except Exception as e:
                print("[ERROR] [PropFireballHandler] 取消实体事件失败: {}".format(str(e)))

    def _on_entity_definitions_event(self, args):
        """
        实体定义事件处理

        当火球实体触发 ecbedwars:fireball_explode 事件时执行爆炸逻辑

        Args:
            args: {
                'entityId': str,     # 实体ID
                'eventName': str     # 事件名称
            }
        """
        entity_id = args.get('entityId')
        event_name = args.get('eventName')

        # 只处理火球爆炸事件
        if event_name != "ecbedwars:fireball_explode":
            return

        try:
            # 获取实体对象
            comp_entity = serverApi.GetEngineCompFactory().CreatePos(entity_id)
            if not comp_entity:
                print("[ERROR] [PropFireballHandler] 实体不存在: {}".format(entity_id))
                return

            # 获取实体位置和维度
            entity_pos = comp_entity.GetPos()
            dimension_id = comp_entity.GetDimensionId()

            # 获取实体拥有者(投掷者)
            comp_owner = serverApi.GetEngineCompFactory().CreateEntityOwner(entity_id)
            owner_id = comp_owner.GetEntityOwner() if comp_owner else None

            # 执行爆炸
            self._execute_explosion(entity_id, entity_pos, dimension_id, owner_id)

            # 销毁火球实体
            serverApi.GetEngineCompFactory().CreateGame(serverApi.GetLevelId()).DestroyEntity(entity_id)

        except Exception as e:
            print("[ERROR] [PropFireballHandler] 处理火球爆炸失败: {}".format(str(e)))
            import traceback
            print(traceback.format_exc())

    # ========== 爆炸逻辑 ==========

    def _execute_explosion(self, entity_id, entity_pos, dimension_id, owner_id):
        """
        执行爆炸逻辑

        Args:
            entity_id (str): 火球实体ID
            entity_pos (tuple): 爆炸位置
            dimension_id (int): 维度ID
            owner_id (str): 投掷者ID
        """
        # 导入爆炸系统
        from systems.util.BedWarsExplosion import BedWarsExplosion

        # 获取游戏系统
        game_system = self.get_game_system()
        if not game_system:
            print("[ERROR] [PropFireballHandler] 游戏系统未找到")
            return

        # 创建爆炸实例
        explosion = BedWarsExplosion(
            dimension_id,    # 维度ID
            entity_pos,      # 爆炸中心位置
            4,               # 爆炸半径(4格)
            entity_id,       # 爆炸源实体ID
            owner_id         # 投掷者ID
        )

        # 配置爆炸参数
        self._configure_explosion(explosion, game_system)

        # 执行爆炸
        explosion.explode()

        print("[INFO] [PropFireballHandler] 火球爆炸: pos={} owner={}".format(entity_pos, owner_id))

    def _configure_explosion(self, explosion, game_system):
        """
        配置爆炸参数

        Args:
            explosion: BedWarsExplosion实例
            game_system: BedWarsGameSystem实例
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

            # 获取爆炸源实体拥有者(投掷者)
            owner_id = explosion.source_entity_id
            if not owner_id:
                return False

            # 如果目标和投掷者是同一队伍,则只造成微量伤害
            target_team = team_module.get_player_team(target_id)
            owner_team = team_module.get_player_team(owner_id)

            return target_team == owner_team

        explosion.check_tiny_hurt = check_tiny_hurt
