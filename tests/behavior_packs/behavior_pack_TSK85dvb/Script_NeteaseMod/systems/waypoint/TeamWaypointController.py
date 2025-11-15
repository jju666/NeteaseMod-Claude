# -*- coding: utf-8 -*-
"""
TeamWaypointController - 队伍标点控制器

功能说明：
    管理队伍内标点的可见性和同步。
    确保队友可以看到彼此的标点，敌方队伍看不到。

重构说明：
    老项目: Parts/ECBedWars/waypoint/TeamWaypointController.py
    新项目: systems/waypoint/TeamWaypointController.py

核心职责：
    1. 管理队伍标点映射（team -> waypoints）
    2. 管理玩家标点映射（player -> waypoints）
    3. 标点同步给队友
    4. 队伍变更时的标点同步
    5. 玩家离开时清理标点
"""

import time


class TeamWaypointController(object):
    """队伍标点控制器 - 管理队伍内标点的可见性和同步"""

    def __init__(self, waypoint_manager):
        """
        初始化控制器

        Args:
            waypoint_manager: WaypointManager实例
        """
        self.manager = waypoint_manager
        self.bedwars_system = waypoint_manager.bedwars_system

        # 队伍标点映射: team_id -> {waypoint_id: waypoint_data}
        self.team_waypoints = {}

        # 玩家标点映射: player_id -> [waypoint_ids]
        self.player_waypoints = {}

        # 标点创建时间记录: waypoint_id -> timestamp
        self.waypoint_timestamps = {}

    def initialize(self):
        """初始化控制器"""
        self.team_waypoints.clear()
        self.player_waypoints.clear()
        self.waypoint_timestamps.clear()

        print("[TeamWaypointController] 队伍控制器初始化完成")

    def on_waypoint_created(self, player_id, waypoint_id, position, waypoint_type):
        """
        处理玩家创建标点事件

        Args:
            player_id (str): 玩家ID
            waypoint_id: 标点ID
            position (tuple): 标点位置 (x, y, z)
            waypoint_type (str): 标点类型

        Returns:
            bool: 是否成功
        """
        try:
            # 获取玩家所属队伍
            team_id = self._get_player_team_id(player_id)
            if not team_id:
                print("[TeamWaypointController] 玩家 {} 没有队伍，无法创建标点".format(player_id))
                return False

            # 检查队伍标点数量限制（由ec-team-pulse管理）
            if not self._check_team_waypoint_limit(team_id):
                return False

            # 检查玩家标点数量限制（由ec-team-pulse管理）
            if not self._check_player_waypoint_limit(player_id):
                return False

            # 创建标点数据
            waypoint_data = {
                'id': waypoint_id,
                'creator_id': player_id,
                'team_id': team_id,
                'position': position,
                'type': waypoint_type,
                'created_time': time.time()
            }

            # 添加到队伍标点映射
            if team_id not in self.team_waypoints:
                self.team_waypoints[team_id] = {}
            self.team_waypoints[team_id][waypoint_id] = waypoint_data

            # 添加到玩家标点映射
            if player_id not in self.player_waypoints:
                self.player_waypoints[player_id] = []
            self.player_waypoints[player_id].append(waypoint_id)

            # 记录创建时间
            self.waypoint_timestamps[waypoint_id] = time.time()

            # 同步给队友（ec-team-pulse会自动处理，这里只需记录）
            print("[TeamWaypointController] 标点创建成功，队伍 {} 当前标点数: {}".format(
                team_id, len(self.team_waypoints.get(team_id, {}))))
            return True

        except Exception as e:
            print("[TeamWaypointController] 创建标点失败: {}".format(str(e)))
            return False

    def on_waypoint_removed(self, waypoint_id):
        """
        处理标点移除事件

        Args:
            waypoint_id: 标点ID
        """
        try:
            # 查找标点所属队伍
            team_id = None
            waypoint_data = None

            for tid, waypoints in self.team_waypoints.items():
                if waypoint_id in waypoints:
                    team_id = tid
                    waypoint_data = waypoints[waypoint_id]
                    break

            if not team_id or not waypoint_data:
                return

            # 从队伍标点映射中移除
            del self.team_waypoints[team_id][waypoint_id]

            # 从玩家标点映射中移除
            creator_id = waypoint_data['creator_id']
            if creator_id in self.player_waypoints:
                if waypoint_id in self.player_waypoints[creator_id]:
                    self.player_waypoints[creator_id].remove(waypoint_id)

            # 移除时间记录
            if waypoint_id in self.waypoint_timestamps:
                del self.waypoint_timestamps[waypoint_id]

            print("[TeamWaypointController] 标点 {} 已移除".format(waypoint_id))

        except Exception as e:
            print("[TeamWaypointController] 移除标点失败: {}".format(str(e)))

    def on_player_team_changed(self, player_id, old_team_id, new_team_id):
        """
        处理玩家队伍变更事件

        Args:
            player_id (str): 玩家ID
            old_team_id (str): 旧队伍ID
            new_team_id (str): 新队伍ID
        """
        try:
            print("[TeamWaypointController] 玩家 {} 队伍变更: {} -> {}".format(
                player_id, old_team_id, new_team_id))

            # 隐藏原队伍的标点（由ec-team-pulse管理可见性）
            if old_team_id and old_team_id in self.team_waypoints:
                self._hide_team_waypoints_from_player(player_id, old_team_id)

            # 显示新队伍的标点
            if new_team_id and new_team_id in self.team_waypoints:
                self._show_team_waypoints_to_player(player_id, new_team_id)

        except Exception as e:
            print("[TeamWaypointController] 队伍变更处理失败: {}".format(str(e)))

    def on_player_leave(self, player_id):
        """
        处理玩家离开游戏事件

        Args:
            player_id (str): 玩家ID
        """
        try:
            print("[TeamWaypointController] 处理玩家离开: {}".format(player_id))

            # 清理该玩家创建的所有标点
            if player_id in self.player_waypoints:
                waypoint_ids = list(self.player_waypoints[player_id])
                for waypoint_id in waypoint_ids:
                    self.on_waypoint_removed(waypoint_id)
                    self._remove_waypoint(waypoint_id)

                # 清理映射关系
                del self.player_waypoints[player_id]
                print("[TeamWaypointController] 已清理玩家 {} 的所有标点".format(player_id))

        except Exception as e:
            print("[TeamWaypointController] 处理玩家离开失败: {}".format(str(e)))

    def cleanup_expired_waypoints(self):
        """清理过期标点（由ec-team-pulse自动管理）"""
        # 标点生命周期由ec-team-pulse组件自己管理
        pass

    def clear_team_waypoints(self, team_id):
        """
        清理指定队伍的所有标点

        Args:
            team_id (str): 队伍ID
        """
        try:
            if team_id not in self.team_waypoints:
                return

            waypoint_ids = list(self.team_waypoints[team_id].keys())
            for waypoint_id in waypoint_ids:
                self._remove_waypoint(waypoint_id)

        except Exception as e:
            print("[TeamWaypointController] 清理队伍标点失败: {}".format(str(e)))

    def clear_all_waypoints(self):
        """清理所有标点"""
        try:
            all_waypoint_ids = list(self.waypoint_timestamps.keys())
            for waypoint_id in all_waypoint_ids:
                self._remove_waypoint(waypoint_id)

            self.team_waypoints.clear()
            self.player_waypoints.clear()
            self.waypoint_timestamps.clear()

            print("[TeamWaypointController] 已清理所有标点")

        except Exception as e:
            print("[TeamWaypointController] 清理所有标点失败: {}".format(str(e)))

    def get_team_waypoint_count(self, team_id):
        """
        获取队伍标点数量

        Args:
            team_id (str): 队伍ID

        Returns:
            int: 标点数量
        """
        return len(self.team_waypoints.get(team_id, {}))

    def get_player_waypoint_count(self, player_id):
        """
        获取玩家标点数量

        Args:
            player_id (str): 玩家ID

        Returns:
            int: 标点数量
        """
        return len(self.player_waypoints.get(player_id, []))

    def cleanup(self):
        """
        清理控制器资源

        清理内容:
        - 清理所有标点
        - 清理所有映射关系
        """
        try:
            print("[TeamWaypointController] 开始清理控制器...")

            # 清理所有标点
            self.clear_all_waypoints()

            # 确保所有数据结构已清空
            self.team_waypoints.clear()
            self.player_waypoints.clear()
            self.waypoint_timestamps.clear()

            print("[TeamWaypointController] 控制器清理完成")
        except Exception as e:
            print("[TeamWaypointController] 清理控制器失败: {}".format(str(e)))

    # ===== 私有方法 =====

    def _get_player_team_id(self, player_id):
        """
        获取玩家所属队伍ID

        Args:
            player_id (str): 玩家ID

        Returns:
            str: 队伍ID，如果没有则返回None
        """
        try:
            if hasattr(self.bedwars_system, 'team_module'):
                return self.bedwars_system.team_module.get_player_team(player_id)
            return None
        except:
            return None

    def _get_team_players(self, team_id):
        """
        获取队伍所有玩家ID列表

        Args:
            team_id (str): 队伍ID

        Returns:
            list: 玩家ID列表
        """
        try:
            if hasattr(self.bedwars_system, 'team_module'):
                players = self.bedwars_system.team_module.get_team_players_ids(team_id)
                return players if players else []
            return []
        except Exception as e:
            print("[TeamWaypointController] 获取队伍玩家失败: {}".format(str(e)))
            return []

    def _check_team_waypoint_limit(self, team_id):
        """
        检查队伍标点数量限制（由ec-team-pulse管理）

        Args:
            team_id (str): 队伍ID

        Returns:
            bool: 是否允许创建
        """
        # 标点数量限制由ec-team-pulse组件自己管理
        return True

    def _check_player_waypoint_limit(self, player_id):
        """
        检查玩家标点数量限制（由ec-team-pulse管理）

        Args:
            player_id (str): 玩家ID

        Returns:
            bool: 是否允许创建
        """
        # 标点数量限制由ec-team-pulse组件自己管理
        return True

    def _show_team_waypoints_to_player(self, player_id, team_id):
        """
        向玩家显示队伍所有标点（由ec-team-pulse处理）

        Args:
            player_id (str): 玩家ID
            team_id (str): 队伍ID
        """
        # ec-team-pulse会自动处理可见性
        print("[TeamWaypointController] 玩家 {} 加入队伍 {}，标点自动同步".format(player_id, team_id))

    def _hide_team_waypoints_from_player(self, player_id, team_id):
        """
        从玩家处隐藏队伍所有标点（由ec-team-pulse处理）

        Args:
            player_id (str): 玩家ID
            team_id (str): 队伍ID
        """
        # ec-team-pulse会自动处理可见性
        print("[TeamWaypointController] 玩家 {} 离开队伍 {}，标点自动隐藏".format(player_id, team_id))

    def _remove_waypoint(self, waypoint_id):
        """
        移除标点（内部调用）

        Args:
            waypoint_id: 标点ID
        """
        try:
            waypoint_system = self.manager.get_waypoint_system()
            if waypoint_system and hasattr(waypoint_system, 'remove_waypoint'):
                waypoint_system.remove_waypoint(waypoint_id)
        except Exception as e:
            print("[TeamWaypointController] 移除标点失败: {}".format(str(e)))
