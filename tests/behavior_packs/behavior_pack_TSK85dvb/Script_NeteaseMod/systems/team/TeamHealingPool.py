# -*- coding: utf-8 -*-
r"""
TeamHealingPool.py - 队伍治疗池模块

该模块实现队伍治疗池功能：
- 在队伍基地附近提供持续治疗效果
- 给进入范围的队友施加生命恢复效果
- 显示治疗池粒子特效

参考文件：D:\EcWork\NetEaseMapECBedWars备份\...\Parts\ECBedWars\team\TeamHealingPool.py
"""

import mod.server.extraServerApi as serverApi

EffectType = serverApi.GetMinecraftEnum().EffectType


def distance_squared(pos1, pos2):
    """
    计算两点之间的距离平方（避免开方运算提高性能）

    :param pos1: 位置1 (x, y, z)
    :param pos2: 位置2 (x, y, z)
    :return: 距离平方值
    """
    return (pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2 + (pos1[2] - pos2[2]) ** 2


class TeamHealingPool(object):
    """
    队伍治疗池类

    在指定位置创建一个治疗区域，队友进入后获得生命恢复效果
    """

    def __init__(self, game_system, team, origin_position, radius):
        """
        初始化治疗池

        :param game_system: BedWarsGameSystem实例
        :param team: 队伍ID
        :param origin_position: 治疗池中心位置 (x, y, z)
        :param radius: 治疗池半径
        """
        self.game_system = game_system  # BedWarsGameSystem
        self.team = team  # str - 队伍ID
        self.origin_position = origin_position  # tuple - 治疗池中心位置
        self.radius = radius  # float - 治疗池半径
        self.radius_squared = radius ** 2  # 预计算半径平方

    def on_update(self):
        """
        更新治疗池（每tick调用）
        检测范围内的队友并施加治疗效果
        """
        try:
            # 获取队伍所有玩家
            team_players = self.game_system.team_module.get_team_players(self.team)
            if not team_players:
                return

            # 收集在治疗范围内的玩家
            players_in_range = []

            for player_id in team_players:
                # 跳过正在重生的玩家
                if player_id in self.game_system.respawning:
                    continue

                # 获取玩家位置
                comp_pos = serverApi.GetEngineCompFactory().CreatePos(player_id)
                player_pos = comp_pos.GetFootPos()

                # 检查是否在治疗范围内（使用平方距离避免开方）
                if distance_squared(player_pos, self.origin_position) <= self.radius_squared:
                    # 施加生命恢复效果（1秒，等级0，不显示粒子）
                    comp_effect = serverApi.GetEngineCompFactory().CreateEffect(player_id)
                    comp_effect.AddEffectToEntity(EffectType.REGENERATION, 1, 0, False)
                    players_in_range.append(player_id)

            # 如果有玩家在范围内，显示治疗池粒子特效
            if len(players_in_range) > 0:
                self._show_healing_particles(players_in_range)

        except Exception as e:
            print("[TeamHealingPool] on_update() 出错: {}".format(str(e)))

    def _show_healing_particles(self, player_ids):
        """
        显示治疗池粒子特效

        :param player_ids: 在范围内的玩家ID列表
        """
        try:
            # 向客户端广播粒子特效事件
            # 注意：这需要客户端预设支持
            # TODO: 确认新起床的粒子特效事件名称和数据格式
            event_data = {
                "players": player_ids,
                "particle": {
                    "particle": "ecbedwars:healingpool",
                    "pos": self.origin_position,
                    "variables": {
                        "variables.healing_radius": self.radius
                    }
                }
            }

            # 广播给所有相关玩家
            # 新起床架构：通过game_system广播事件
            for player_id in player_ids:
                try:
                    # TODO: 适配新起床的客户端事件系统
                    # 这里可能需要根据实际情况调整事件名称和发送方式
                    pass
                except:
                    pass

        except Exception as e:
            print("[TeamHealingPool] _show_healing_particles() 出错: {}".format(str(e)))

    def get_center_position(self):
        """
        获取治疗池中心位置

        :return: 中心位置 (x, y, z)
        """
        return self.origin_position

    def get_radius(self):
        """
        获取治疗池半径

        :return: 半径值
        """
        return self.radius

    def is_player_in_range(self, player_id):
        """
        检查玩家是否在治疗池范围内

        :param player_id: 玩家ID
        :return: True如果在范围内，否则False
        """
        try:
            comp_pos = serverApi.GetEngineCompFactory().CreatePos(player_id)
            player_pos = comp_pos.GetFootPos()
            return distance_squared(player_pos, self.origin_position) <= self.radius_squared
        except:
            return False
