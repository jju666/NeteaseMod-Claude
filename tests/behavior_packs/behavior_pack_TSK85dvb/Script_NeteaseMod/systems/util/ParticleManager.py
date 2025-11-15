# -*- coding: utf-8 -*-
"""
ParticleManager - 客户端粒子管理工具

功能说明：
    提供统一的客户端粒子生成接口，允许服务端请求在客户端播放粒子效果。
    支持多种粒子发送模式（指定玩家、指定维度、全局广播）。

重构说明：
    老项目: 使用PlayerClientParticlePart零件实现
    新项目: 使用工具类实现，集成到GamingStateSystem

核心职责：
    1. 服务端到客户端的粒子生成通信
    2. 支持粒子变量参数配置
    3. 支持粒子绑定到实体
    4. 提供简洁的API接口
"""

import mod.server.extraServerApi as serverApi


class ParticleManager(object):
    """
    粒子管理器（服务端）

    提供统一的粒子播放接口，简化粒子效果的使用
    """

    def __init__(self, system):
        """
        初始化粒子管理器

        Args:
            system: 游戏系统实例（用于获取玩家信息和发送事件）
        """
        self.system = system

    def spawn_particle(self, particle_id, pos, players=None, dimension=None, entity=None, variables=None):
        """
        生成粒子效果

        Args:
            particle_id (str): 粒子类型ID（如 "minecraft:critical_hit_emitter"）
            pos (list): 粒子生成位置 [x, y, z]
            players (list, optional): 指定玩家ID列表（优先级最高）
            dimension (int, optional): 指定维度ID（优先级次之）
            entity (str, optional): 绑定到的实体ID（粒子跟随实体移动）
            variables (dict, optional): 粒子变量参数（如 {"scale": 2.0}）

        发送模式（按优先级）：
            1. players: 向指定玩家列表发送
            2. dimension: 向指定维度的所有玩家发送
            3. 默认: 全局广播给所有玩家

        示例:
            # 向所有玩家广播粒子
            particle_mgr.spawn_particle(
                "minecraft:critical_hit_emitter",
                [100, 65, 100]
            )

            # 向特定玩家显示粒子
            particle_mgr.spawn_particle(
                "minecraft:heart_particle",
                [100, 65, 100],
                players=['player1', 'player2'],
                variables={'scale': 2.0}
            )

            # 向特定维度的所有玩家显示粒子
            particle_mgr.spawn_particle(
                "minecraft:dragon_breath_fire",
                [0, 100, 0],
                dimension=10000
            )
        """
        # 构建粒子参数
        particle_args = {
            'pos': [float(pos[0]), float(pos[1]), float(pos[2])],
            'particle': particle_id
        }

        # 可选参数
        if entity is not None:
            particle_args['entity'] = entity
        if variables is not None:
            particle_args['variables'] = variables

        # 模式1：指定玩家列表
        if players is not None:
            for player_id in players:
                self._notify_client(player_id, particle_args)

        # 模式2：指定维度
        elif dimension is not None:
            comp_player = serverApi.GetEngineCompFactory().CreatePlayer(serverApi.GetLevelId())
            for player_id in serverApi.GetPlayerList():
                player_dim = comp_player.GetPlayerDimensionId(player_id)
                if player_dim == dimension:
                    self._notify_client(player_id, particle_args)

        # 模式3：全局广播（默认）
        else:
            self._broadcast_to_all_clients(particle_args)

    def spawn_particle_at_player(self, player_id, particle_id, offset=(0, 1, 0), variables=None):
        """
        在玩家位置播放粒子（便捷方法）

        Args:
            player_id (str): 玩家ID
            particle_id (str): 粒子类型ID
            offset (tuple): 位置偏移量 (x, y, z)，默认向上偏移1格
            variables (dict, optional): 粒子变量参数
        """
        comp_pos = serverApi.GetEngineCompFactory().CreatePos(player_id)
        pos = comp_pos.GetFootPos()
        if pos:
            final_pos = [
                pos[0] + offset[0],
                pos[1] + offset[1],
                pos[2] + offset[2]
            ]
            self.spawn_particle(
                particle_id,
                final_pos,
                players=[player_id],
                entity=player_id,
                variables=variables
            )

    def spawn_particle_at_entity(self, entity_id, particle_id, offset=(0, 0, 0), players=None, variables=None):
        """
        在实体位置播放粒子（便捷方法）

        Args:
            entity_id (str): 实体ID
            particle_id (str): 粒子类型ID
            offset (tuple): 位置偏移量 (x, y, z)
            players (list, optional): 指定玩家列表（None则全局广播）
            variables (dict, optional): 粒子变量参数
        """
        comp_pos = serverApi.GetEngineCompFactory().CreatePos(entity_id)
        pos = comp_pos.GetFootPos()
        if pos:
            final_pos = [
                pos[0] + offset[0],
                pos[1] + offset[1],
                pos[2] + offset[2]
            ]
            self.spawn_particle(
                particle_id,
                final_pos,
                players=players,
                entity=entity_id,
                variables=variables
            )

    def _notify_client(self, player_id, particle_args):
        """
        向单个客户端发送粒子生成事件

        Args:
            player_id (str): 玩家ID
            particle_args (dict): 粒子参数
        """
        self.system.NotifyToClient(player_id, "ClientSpawnParticle", particle_args)

    def _broadcast_to_all_clients(self, particle_args):
        """
        向所有客户端广播粒子生成事件

        Args:
            particle_args (dict): 粒子参数
        """
        self.system.BroadcastToAllClient("ClientSpawnParticle", particle_args)


# ===== 常用粒子效果常量 =====

class ParticleEffects(object):
    """常用粒子效果ID常量"""

    # 击杀效果
    CRITICAL_HIT = "minecraft:critical_hit_emitter"

    # 爱心效果
    HEART = "minecraft:heart_particle"

    # 爆炸效果
    HUGE_EXPLODE = "minecraft:huge_explode_emitter"
    EXPLODE = "minecraft:explosion_particle"

    # 图腾效果（闪光）
    TOTEM = "minecraft:totem_particle"

    # 潜影贝子弹轨迹
    SHULKER_BULLET = "minecraft:shulker_bullet"

    # 龙息火焰
    DRAGON_BREATH = "minecraft:dragon_breath_fire"

    # 村民表情
    VILLAGER_ANGRY = "minecraft:villager_angry"
    VILLAGER_HAPPY = "minecraft:villager_happy"

    # 火焰
    FLAME = "minecraft:basic_flame_particle"

    # 烟雾
    SMOKE = "minecraft:basic_smoke_particle"

    # 传送门
    PORTAL = "minecraft:portal_directional"

    # 经验球
    ENCHANTING_TABLE = "minecraft:enchanting_table_particle"
