# -*- coding: utf-8 -*-
"""
TeamModule - 队伍管理模块

功能:
- 管理队伍和玩家的映射关系
- 提供队伍查询接口
- 队伍数据统计
- 管理队伍升级系统

原文件: Parts/ECBedWars/team/TeamModule.py
重构为: systems/team/TeamModule.py
"""

from .TeamUpgradeManager import TeamUpgradeManager


class TeamModule(object):
    """
    队伍管理模块

    核心职责:
    - 维护队伍->玩家映射
    - 维护玩家->队伍映射
    - 提供队伍成员查询
    - 队伍状态统计
    """

    def __init__(self, game_system):
        """
        初始化队伍模块

        Args:
            game_system: BedWarsGameSystem实例
        """
        self.game_system = game_system

        # 队伍配置
        self.team_colors = {
            'RED': u'\xa7c',  # 红色
            'BLUE': u'\xa79',  # 蓝色
            'GREEN': u'\xa7a',  # 绿色
            'YELLOW': u'\xa7e',  # 黄色
            'AQUA': u'\xa7b',  # 青色
            'WHITE': u'\xa7f',  # 白色
            'LIGHT_PURPLE': u'\xa7d',  # 紫色
            'GRAY': u'\xa77',  # 灰色
        }

        self.team_names = {
            'RED': u'红队',
            'BLUE': u'蓝队',
            'GREEN': u'绿队',
            'YELLOW': u'黄队',
            'AQUA': u'青队',
            'WHITE': u'白队',
            'LIGHT_PURPLE': u'紫队',
            'GRAY': u'灰队',
        }

        # 队伍数据
        self.team_player_map = {}  # team_id -> [player_id, ...]
        self.player_team_map = {}  # player_id -> team_id

        # 队伍升级管理器
        self.team_upgrade_managers = {}  # team_id -> TeamUpgradeManager

        print("[INFO] [TeamModule] 初始化完成")

    def assign_player_to_team(self, player_id, team_id):
        """
        将玩家分配到队伍

        Args:
            player_id (str): 玩家ID
            team_id (str): 队伍ID
        """
        # 从旧队伍移除
        old_team = self.player_team_map.get(player_id)
        if old_team and old_team in self.team_player_map:
            if player_id in self.team_player_map[old_team]:
                self.team_player_map[old_team].remove(player_id)

        # 添加到新队伍
        if team_id not in self.team_player_map:
            self.team_player_map[team_id] = []
            # 为新队伍创建升级管理器
            self._create_team_upgrade_manager(team_id)

        if player_id not in self.team_player_map[team_id]:
            self.team_player_map[team_id].append(player_id)

        # 更新玩家->队伍映射
        self.player_team_map[player_id] = team_id

        # 对新加入的玩家应用队伍升级效果
        if team_id in self.team_upgrade_managers:
            try:
                self.team_upgrade_managers[team_id].apply_all_to_player(player_id)
            except Exception as e:
                print("[ERROR] [TeamModule] 应用升级到玩家{}失败: {}".format(player_id, str(e)))

        # 通知标点管理器队伍变更
        if hasattr(self.game_system, 'waypoint_manager') and self.game_system.waypoint_manager:
            self.game_system.waypoint_manager.on_player_team_changed(player_id, old_team, team_id)

        print("[INFO] [TeamModule] 玩家{} 分配到队伍{}".format(player_id, team_id))

    def remove_player_from_team(self, player_id):
        """
        从队伍移除玩家

        Args:
            player_id (str): 玩家ID
        """
        team_id = self.player_team_map.get(player_id)
        if not team_id:
            return

        # 从队伍列表移除
        if team_id in self.team_player_map:
            if player_id in self.team_player_map[team_id]:
                self.team_player_map[team_id].remove(player_id)

        # 从映射移除
        if player_id in self.player_team_map:
            del self.player_team_map[player_id]

        # 通知标点管理器玩家离开
        if hasattr(self.game_system, 'waypoint_manager') and self.game_system.waypoint_manager:
            self.game_system.waypoint_manager.on_player_leave(player_id)

    def get_player_team(self, player_id):
        """
        获取玩家所在队伍

        Args:
            player_id (str): 玩家ID

        Returns:
            str: 队伍ID,如果没有则返回None
        """
        return self.player_team_map.get(player_id)

    def get_team_players(self, team_id):
        """
        获取队伍中的玩家列表

        Args:
            team_id (str): 队伍ID

        Returns:
            list: 玩家ID列表
        """
        return self.team_player_map.get(team_id, [])

    def get_team_player_count(self, team_id):
        """
        获取队伍玩家数量

        Args:
            team_id (str): 队伍ID

        Returns:
            int: 玩家数量
        """
        return len(self.team_player_map.get(team_id, []))

    def get_all_teams(self):
        """
        获取所有队伍ID

        Returns:
            list: 队伍ID列表
        """
        return list(self.team_player_map.keys())

    def is_team_empty(self, team_id):
        """
        判断队伍是否为空

        Args:
            team_id (str): 队伍ID

        Returns:
            bool: 是否为空
        """
        return self.get_team_player_count(team_id) == 0

    def is_player_alive(self, player_id):
        """
        判断玩家是否存活（在队伍中）

        Args:
            player_id (str): 玩家ID

        Returns:
            bool: 玩家是否存活（是否在队伍映射中）
        """
        return player_id in self.player_team_map

    def is_teammates(self, player_id1, player_id2):
        """
        判断两个玩家是否是队友

        Args:
            player_id1 (str): 玩家1ID
            player_id2 (str): 玩家2ID

        Returns:
            bool: 是否是队友
        """
        team1 = self.get_player_team(player_id1)
        team2 = self.get_player_team(player_id2)

        if not team1 or not team2:
            return False

        return team1 == team2

    def get_team_color(self, team_id):
        """
        获取队伍颜色代码

        Args:
            team_id (str): 队伍ID

        Returns:
            str: 颜色代码
        """
        return self.team_colors.get(team_id, u'\xa7f')

    def get_team_name(self, team_id):
        """
        获取队伍名称

        Args:
            team_id (str): 队伍ID

        Returns:
            str: 队伍名称
        """
        return self.team_names.get(team_id, team_id)

    def get_colored_team_name(self, team_id):
        """
        获取带颜色的队伍名称

        Args:
            team_id (str): 队伍ID

        Returns:
            str: 带颜色的队伍名称
        """
        color = self.get_team_color(team_id)
        name = self.get_team_name(team_id)
        return u"{}{}".format(color, name)

    def broadcast_to_team(self, team_id, message, color=None):
        """
        向队伍广播消息

        Args:
            team_id (str): 队伍ID
            message (str): 消息内容
            color (str): 颜色代码(可选,默认使用队伍颜色)
        """
        import mod.server.extraServerApi as serverApi

        if color is None:
            color = self.get_team_color(team_id)

        players = self.get_team_players(team_id)
        for player_id in players:
            try:
                comp_msg = serverApi.GetEngineCompFactory().CreateMsg(player_id)
                comp_msg.NotifyOneMessage(player_id, message, color)
            except Exception as e:
                print("[ERROR] [TeamModule] 发送消息到玩家{}失败: {}".format(player_id, str(e)))

    def clear_all_teams(self):
        """清空所有队伍数据"""
        self.team_player_map = {}
        self.player_team_map = {}
        self.team_upgrade_managers = {}

    def cleanup(self):
        """清理队伍模块"""
        self.clear_all_teams()
        print("[INFO] [TeamModule] 清理完成")

    # ========== 队伍升级管理 ==========

    def _create_team_upgrade_manager(self, team_id):
        """
        为队伍创建升级管理器

        Args:
            team_id (str): 队伍ID
        """
        if team_id not in self.team_upgrade_managers:
            self.team_upgrade_managers[team_id] = TeamUpgradeManager(self.game_system, team_id)
            print("[INFO] [TeamModule] 为队伍 {} 创建升级管理器".format(team_id))

    def get_team_upgrade_manager(self, team_id):
        """
        获取队伍的升级管理器

        Args:
            team_id (str): 队伍ID

        Returns:
            TeamUpgradeManager: 升级管理器实例,如果不存在返回None
        """
        return self.team_upgrade_managers.get(team_id, None)

    def get_team_trap_manager(self, team_id):
        """
        获取队伍的陷阱管理器

        Args:
            team_id (str): 队伍ID

        Returns:
            TeamTrapManager: 陷阱管理器实例,如果不存在返回None
        """
        return self.game_system.team_trap_managers.get(team_id, None)

    def on_player_respawn(self, player_id):
        """
        玩家重生时重新应用队伍升级效果

        Args:
            player_id (str): 玩家ID
        """
        player_team = self.get_player_team(player_id)
        if player_team and player_team in self.team_upgrade_managers:
            try:
                self.team_upgrade_managers[player_team].on_player_respawn(player_id)
                print("[INFO] [TeamModule] 为玩家{}重新应用队伍升级效果".format(player_id))
            except Exception as e:
                print("[ERROR] [TeamModule] 重新应用升级到玩家{}失败: {}".format(player_id, str(e)))

    def get_all_players(self):
        """
        获取所有玩家列表

        Returns:
            list: 所有玩家ID列表
        """
        return list(self.player_team_map.keys())

    # ========== 兼容老API ==========

    @property
    def team_to_player(self):
        """兼容老API: 获取队伍到玩家映射"""
        return self.team_player_map

    @property
    def player_to_team(self):
        """兼容老API: 获取玩家到队伍映射"""
        return self.player_team_map

    def get_all_team_players(self):
        """
        获取所有队伍的玩家映射(兼容老API)

        Returns:
            dict: {team_id: [player_id, ...]}
        """
        return self.team_player_map