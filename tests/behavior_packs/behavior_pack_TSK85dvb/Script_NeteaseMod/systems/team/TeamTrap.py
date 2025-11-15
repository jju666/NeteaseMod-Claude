# -*- coding: utf-8 -*-
r"""
TeamTrap.py - 队伍陷阱模块

该模块定义了陷阱系统的基类和各种具体陷阱类型：
- TeamTrap: 陷阱基类
- TeamTrapSlowness: 减速陷阱（这是个陷阱！）
- TeamTrapBeatBack: 反击陷阱
- TeamTrapAlert: 警报陷阱
- TeamTrapFatigue: 挖掘疲劳陷阱

参考文件：D:\EcWork\NetEaseMapECBedWars备份\...\Parts\BedWarsBed\trap\TeamTrap.py
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


class TeamTrap(object):
    """
    队伍陷阱基类

    所有具体的陷阱类型都应继承此类
    """

    def __init__(self, manager, name, bed_pos):
        """
        初始化陷阱

        :param manager: TeamTrapManager实例
        :param name: 陷阱名称
        :param bed_pos: 床的位置 (x, y, z)
        """
        self.manager = manager  # TeamTrapManager
        self.name = name  # str - 陷阱名称
        self.pos = bed_pos  # tuple - 陷阱位置（床的位置）
        self.effective_range = 8  # int - 生效范围（格）

    def get_effective_players(self):
        """
        获取生效的玩家（在范围内的敌对玩家）

        :return: 玩家ID列表
        """
        effective_players = []

        try:
            if self.pos is None:
                return effective_players

            game_system = self.manager.game_system
            if not game_system or not game_system.team_module:
                return effective_players

            # 获取所有非本队伍的玩家
            all_teams = game_system.team_module.get_all_teams()
            for team_id in all_teams:
                if team_id == self.manager.team:
                    continue

                team_players = game_system.team_module.get_team_players(team_id)
                for player_id in team_players:
                    # 跳过已淘汰的玩家
                    if player_id in game_system.eliminated_players:
                        continue

                    # 跳过重生中的玩家
                    if player_id in game_system.respawning:
                        continue

                    # 检查距离
                    try:
                        comp_pos = serverApi.GetEngineCompFactory().CreatePos(player_id)
                        player_pos = comp_pos.GetFootPos()

                        if distance_squared(player_pos, self.pos) < self.effective_range ** 2:
                            # 检查玩家是否具有陷阱免疫状态
                            if game_system.is_player_trap_immune(player_id):
                                # 发送免疫提示
                                comp_msg = serverApi.GetEngineCompFactory().CreateMsg(player_id)
                                comp_msg.NotifyOneMessage(
                                    player_id,
                                    u"§b陷阱免疫状态保护了你！",
                                    u"§b"
                                )
                            else:
                                effective_players.append(player_id)
                    except:
                        pass

        except Exception as e:
            print("[ERROR] [TeamTrap] get_effective_players() 出错: {}".format(str(e)))

        return effective_players

    def _trigger(self):
        """
        触发陷阱效果（子类需要重写此方法）
        """
        pass

    def trigger(self):
        """
        触发陷阱（公共接口）

        执行陷阱效果并通知队伍成员
        """
        try:
            # 执行陷阱效果
            self._trigger()

            # 通知队伍成员
            game_system = self.manager.game_system
            if not game_system or not game_system.team_module:
                return

            title = u"§c陷阱触发！"
            message = u"§c{} 触发了".format(self.name)

            team_players = game_system.team_module.get_team_players(self.manager.team)
            for player_id in team_players:
                try:
                    # 发送消息
                    comp_msg = serverApi.GetEngineCompFactory().CreateMsg(player_id)
                    comp_msg.NotifyOneMessage(player_id, message, u"§c")

                    # 播放音效
                    comp_cmd = serverApi.GetEngineCompFactory().CreateCommand(serverApi.GetLevelId())
                    comp_cmd.SetCommand("/playsound note.harp @a[name=\"{}\"] ~ ~ ~ 1 0.5".format(player_id))

                    # 发送标题（如果支持）
                    # TODO: 检查是否有发送标题的API
                    # comp_msg.NotifyOneTitle(player_id, title, message, 10, 20, 40)
                except:
                    pass

            print("[INFO] [TeamTrap] 陷阱触发: team={}, trap={}".format(self.manager.team, self.name))

        except Exception as e:
            print("[ERROR] [TeamTrap] trigger() 出错: {}".format(str(e)))


# ============================================================================
# 具体陷阱类型
# ============================================================================

class TeamTrapSlowness(TeamTrap):
    """减速陷阱（这是个陷阱！）"""

    def __init__(self, manager, bed_pos):
        super(TeamTrapSlowness, self).__init__(manager, u"这是个陷阱！", bed_pos)

    def _trigger(self):
        """触发减速和失明效果"""
        players = self.get_effective_players()
        for player_id in players:
            try:
                comp_effect = serverApi.GetEngineCompFactory().CreateEffect(player_id)
                comp_effect.AddEffectToEntity(EffectType.MOVEMENT_SLOWDOWN, 8, 0, True)
                comp_effect.AddEffectToEntity(EffectType.BLINDNESS, 8, 0, True)
            except Exception as e:
                print("[ERROR] [TeamTrapSlowness] 应用效果失败: {}".format(str(e)))


class TeamTrapBeatBack(TeamTrap):
    """反击陷阱"""

    def __init__(self, manager, bed_pos):
        super(TeamTrapBeatBack, self).__init__(manager, u"反击陷阱", bed_pos)

    def _trigger(self):
        """触发队友速度和跳跃提升效果"""
        try:
            game_system = self.manager.game_system
            if not game_system or not game_system.team_module:
                return

            team_players = game_system.team_module.get_team_players(self.manager.team)
            for player_id in team_players:
                # 跳过已淘汰的玩家
                if player_id in game_system.eliminated_players:
                    continue

                # 跳过重生中的玩家
                if player_id in game_system.respawning:
                    continue

                try:
                    # 检查玩家是否在合理范围内（255格内）
                    comp_pos = serverApi.GetEngineCompFactory().CreatePos(player_id)
                    player_pos = comp_pos.GetFootPos()

                    if distance_squared(player_pos, self.pos) < 255 * 255:
                        comp_effect = serverApi.GetEngineCompFactory().CreateEffect(player_id)
                        comp_effect.AddEffectToEntity(EffectType.MOVEMENT_SPEED, 15, 1, True)
                        comp_effect.AddEffectToEntity(EffectType.JUMP, 15, 1, True)
                except:
                    pass

        except Exception as e:
            print("[ERROR] [TeamTrapBeatBack] _trigger() 出错: {}".format(str(e)))


class TeamTrapAlert(TeamTrap):
    """警报陷阱"""

    def __init__(self, manager, bed_pos):
        super(TeamTrapAlert, self).__init__(manager, u"警报陷阱", bed_pos)

    def _trigger(self):
        """触发移除隐身效果"""
        players = self.get_effective_players()
        for player_id in players:
            try:
                comp_effect = serverApi.GetEngineCompFactory().CreateEffect(player_id)

                # 尝试移除隐身效果
                if comp_effect.RemoveEffectFromEntity(EffectType.INVISIBILITY):
                    # 发送提示消息
                    comp_msg = serverApi.GetEngineCompFactory().CreateMsg(player_id)
                    message = u"§e你触发了 §l§c警报陷阱§r§e， 你的隐身效果失效了！"
                    comp_msg.NotifyOneMessage(player_id, message, u"§e")

                    # TODO: 发送标题
                    # comp_msg.NotifyOneTitle(player_id, "·", message)
            except Exception as e:
                print("[ERROR] [TeamTrapAlert] 应用效果失败: {}".format(str(e)))


class TeamTrapFatigue(TeamTrap):
    """挖掘疲劳陷阱"""

    def __init__(self, manager, bed_pos):
        super(TeamTrapFatigue, self).__init__(manager, u"挖掘疲劳陷阱", bed_pos)

    def _trigger(self):
        """触发挖掘疲劳效果"""
        players = self.get_effective_players()
        for player_id in players:
            try:
                comp_effect = serverApi.GetEngineCompFactory().CreateEffect(player_id)
                comp_effect.AddEffectToEntity(EffectType.DIG_SLOWDOWN, 10, 0, True)
            except Exception as e:
                print("[ERROR] [TeamTrapFatigue] 应用效果失败: {}".format(str(e)))