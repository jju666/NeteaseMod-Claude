# -*- coding: utf-8 -*-
r"""
BedWarsScoreboard.py - 起床战争计分板系统

该模块管理游戏的计分板和玩家统计：
- 管理所有玩家的统计数据
- 处理击杀、死亡、床破坏等事件
- 计算MVP和奖励
- 提供数据收集接口

参考文件：D:\EcWork\NetEaseMapECBedWars备份\...\Parts\ECBedWars\scoreboard\BedWarsScoreboard.py
"""

import time
import mod.server.extraServerApi as serverApi
from .BedWarsPlayerScore import BedWarsPlayerScore


class BedWarsScoreboard(object):
    """
    起床战争计分板类

    管理所有玩家的统计数据和评分
    """

    def __init__(self, game_system):
        """
        初始化计分板系统

        :param game_system: BedWarsGameSystem实例
        """
        self.game_system = game_system  # BedWarsGameSystem
        self.scores = {}  # dict - {player_id: BedWarsPlayerScore}
        self.win_team = None  # str - 胜利队伍ID

    def set_win_team(self, team):
        """
        设置胜利队伍

        :param team: 胜利队伍ID
        """
        self.win_team = team
        if team is None:
            return

        # 标记胜利队伍的所有玩家
        for score in self.scores.values():
            if score.team == team:
                score.win_team = True

    def get_player_score(self, player_id):
        """
        获取玩家的统计对象（如果不存在则创建）

        :param player_id: 玩家ID
        :return: BedWarsPlayerScore实例
        """
        if player_id not in self.scores:
            # 获取玩家信息
            try:
                comp_name = serverApi.GetEngineCompFactory().CreateName(player_id)
                player_name = comp_name.GetName()
            except:
                player_name = player_id

            # 获取玩家队伍
            team = None
            if self.game_system and self.game_system.team_module:
                team = self.game_system.team_module.get_player_team(player_id)

            # 创建统计对象
            player_score = BedWarsPlayerScore(player_id, player_name, team)
            self.scores[player_id] = player_score
        else:
            player_score = self.scores[player_id]

        return player_score

    def on_player_damage(self, player_id, src_id, damage, cause):
        """
        记录玩家受到伤害（用于击杀归属判定）

        :param player_id: 受伤玩家ID
        :param src_id: 伤害来源ID
        :param damage: 伤害值
        :param cause: 伤害类型
        """
        player_score = self.get_player_score(player_id)
        player_score.last_damage = (time.time(), src_id, damage, cause)

    def find_real_attacker_id(self, player_id):
        """
        查找真实攻击者ID（10秒内的最后伤害来源）

        :param player_id: 死亡玩家ID
        :return: 攻击者ID，如果没有则返回None
        """
        player_score = self.get_player_score(player_id)

        if player_score.last_damage:
            # 检查伤害是否在10秒内
            damage_time = player_score.last_damage[0]
            if time.time() - damage_time < 10:
                return player_score.last_damage[1]

        return None

    def on_player_death(self, player_id, killer, final_kill=False):
        """
        处理玩家死亡事件

        :param player_id: 死亡玩家ID
        :param killer: 击杀者ID（可能是"-1"表示无击杀者）
        :param final_kill: 是否为终结击杀
        """
        try:
            player_id = str(player_id)
            killer = str(killer)

            # 记录死亡
            player_score = self.get_player_score(player_id)
            player_score.deaths += 1

            # 记录击杀
            if killer != "-1":
                killer_score = self.get_player_score(killer)
                killer_score.kills += 1

                if final_kill:
                    killer_score.final_kills += 1

                print("[INFO] [BedWarsScoreboard] 玩家击杀: killer={}, victim={}, final={}".format(
                    killer, player_id, final_kill))

        except Exception as e:
            print("[ERROR] [BedWarsScoreboard] on_player_death() 出错: {}".format(str(e)))

    def on_player_destroy_bed(self, player_id):
        """
        处理玩家破坏床事件

        :param player_id: 破坏者ID
        """
        try:
            player_score = self.get_player_score(player_id)
            player_score.destroys += 1

            print("[INFO] [BedWarsScoreboard] 床破坏: player={}, total={}".format(
                player_id, player_score.destroys))

        except Exception as e:
            print("[ERROR] [BedWarsScoreboard] on_player_destroy_bed() 出错: {}".format(str(e)))

    def collect_all_scoreboard_data(self):
        """
        收集所有计分板数据（用于游戏结束统计）

        :return: 计分板数据字典
        """
        try:
            # 转换所有玩家统计为字典
            scores = [score.to_dict() for score in self.scores.values()]

            # 按照评分倒序排序
            scores.sort(key=lambda x: x['score'], reverse=True)

            # 构造数据
            data = {
                "win_team": self.win_team,
                "scores": scores
            }

            return data

        except Exception as e:
            print("[ERROR] [BedWarsScoreboard] collect_all_scoreboard_data() 出错: {}".format(str(e)))
            return {
                "win_team": None,
                "scores": []
            }

    def get_mvp_player(self):
        """
        获取MVP玩家

        :return: MVP玩家的BedWarsPlayerScore对象，如果没有玩家则返回None
        """
        if not self.scores:
            return None

        # 找到评分最高的玩家
        mvp = max(self.scores.values(), key=lambda s: s.calculate_score())
        return mvp

    def clear_all_scores(self):
        """
        清空所有统计数据（用于游戏重置）
        """
        self.scores = {}
        self.win_team = None