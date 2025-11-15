# -*- coding: utf-8 -*-
r"""
BedWarsPlayerScore.py - 起床战争玩家统计模块

该模块管理单个玩家的游戏统计数据：
- 击杀、死亡、终结击杀统计
- 床破坏统计
- MVP评分计算
- 金币奖励计算

参考文件：D:\EcWork\NetEaseMapECBedWars备份\...\Parts\ECBedWars\scoreboard\BedWarsPlayerScore.py
"""


class BedWarsPlayerScore(object):
    """
    起床战争玩家统计类

    记录单个玩家的游戏数据和计算评分
    """

    def __init__(self, player_id, player_name, team):
        """
        初始化玩家统计

        :param player_id: 玩家ID
        :param player_name: 玩家名称
        :param team: 队伍ID
        """
        self.player_id = player_id  # str - 玩家ID
        self.player_name = player_name  # str - 玩家名称
        self.team = team  # str - 队伍ID

        # 伤害记录（用于击杀归属判定）
        self.last_damage = None  # tuple - (时间戳, 伤害来源玩家ID, 伤害值, 伤害类型)

        # 统计数据
        self.kills = 0  # int - 击杀数
        self.deaths = 0  # int - 死亡数
        self.final_kills = 0  # int - 终结击杀数
        self.destroys = 0  # int - 床破坏数

        # 特殊标记
        self.win_team = False  # bool - 是否胜利
        self.bought_diamond_armor = False  # bool - 是否购买过钻石装备
        self.num_team_upgrade = 0  # int - 团队升级次数

    def calculate_score(self):
        """
        计算MVP评分

        评分规则：
        - 击杀：20分/次
        - 终结击杀：10分/次
        - 床破坏：50分/次
        - 胜利：40分

        :return: 总评分
        """
        score = 0
        score += self.kills * 20  # 击杀得分
        score += self.final_kills * 10  # 终结击杀得分
        score += self.destroys * 50  # 床破坏得分

        if self.win_team:
            score += 40  # 胜利奖励

        return score

    def calculate_coin(self):
        """
        计算金币奖励

        金币规则：
        - 参与游戏：3金币
        - 胜利：5金币
        - 购买钻石装备：2金币
        - 团队升级：每次1金币（最多3金币）
        - 床破坏：每个3金币
        - 击杀：每10次击杀1金币（最多3金币）
        - 终结击杀：每5次终结2金币

        :return: 总金币数
        """
        coin = 0

        # 基础奖励
        coin += 3  # 参与游戏

        # 胜利奖励
        if self.win_team:
            coin += 5

        # 装备购买奖励
        if self.bought_diamond_armor:
            coin += 2

        # 团队升级奖励（最多3金币）
        coin += min(self.num_team_upgrade, 3)

        # 床破坏奖励
        coin += self.destroys * 3

        # 击杀奖励（最多3金币）
        coin += int(min(self.kills / 10.0, 3))

        # 终结击杀奖励
        coin += int(self.final_kills / 5.0 * 2)

        return coin

    def to_dict(self):
        """
        将统计数据转换为字典格式（用于序列化）

        :return: 统计数据字典
        """
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "team": self.team,
            "kills": self.kills,
            "deaths": self.deaths,
            "final_kills": self.final_kills,
            "destroys": self.destroys,
            "win_team": self.win_team,
            "score": self.calculate_score(),
            "coin": self.calculate_coin(),
        }
