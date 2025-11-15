# -*- coding: utf-8 -*-
"""
WaypointManager - 标点管理器

功能说明：
    负责标点功能的启用/禁用控制和权限管理。
    作为BedWarsGameSystem和ec-team-pulse外部组件之间的桥梁。

重构说明：
    老项目: Parts/ECBedWars/waypoint/WaypointManager.py
    新项目: systems/waypoint/WaypointManager.py

核心职责：
    1. 获取和管理ec-team-pulse外部组件接口
    2. 标点功能启用/禁用控制
    3. 玩家权限检查（缓存机制）
    4. 标点创建/移除请求处理
    5. 玩家事件处理（加入/离开/队伍变更）
    6. 与TeamWaypointController协同工作

外部依赖：
    - ec-team-pulse组件（通过GetSystem获取）
    - 如果组件不可用，系统会优雅降级
"""

import time
import mod.server.extraServerApi as serverApi
from .TeamWaypointController import TeamWaypointController


class WaypointManager(object):
    """标点管理器 - 负责标点功能的启用/禁用控制和权限管理"""

    def __init__(self, bedwars_system):
        """
        初始化标点管理器

        Args:
            bedwars_system: BedWarsGameSystem实例
        """
        self.bedwars_system = bedwars_system
        self.waypoint_system = None  # ec-team-pulse接口
        self.is_enabled = False
        self.team_controller = None

        # 权限检查缓存（避免频繁计算）
        self._permission_cache = {}
        self._cache_expire_time = {}
        self._cache_duration = 1.0  # 缓存1秒

    def initialize(self):
        """
        初始化标点系统

        Returns:
            bool: 是否成功
        """
        try:
            print("[WaypointManager] 开始初始化标点管理器...")

            # 通过GetSystem获取标点组件接口
            self.waypoint_system = self._get_waypoint_system()
            if self.waypoint_system:
                print("[WaypointManager] 标点系统获取成功")
            else:
                print("[WaypointManager] 标点系统未找到（ec-team-pulse组件可能未安装）")
                print("[WaypointManager] 标点功能将不可用，但不影响其他游戏功能")

            # 初始化队伍控制器
            self.team_controller = TeamWaypointController(self)
            self.team_controller.initialize()
            print("[WaypointManager] 队伍控制器初始化完成")

            # 注册标点相关事件监听
            self._register_waypoint_events()

            print("[WaypointManager] 标点管理器初始化完成")
            return True

        except Exception as e:
            print("[WaypointManager] 初始化失败: {}".format(str(e)))
            return False

    def enable_waypoint(self):
        """
        启用标点功能（仅在对局中调用）

        Returns:
            bool: 是否成功
        """
        try:
            print("[WaypointManager] === 尝试启用标点功能 ===")

            if not self.waypoint_system:
                print("[WaypointManager] 标点系统未初始化，尝试重新获取...")
                self.waypoint_system = self._get_waypoint_system()
                if not self.waypoint_system:
                    print("[WaypointManager] 重新获取标点系统失败")
                    print("[WaypointManager] 提示：请确保ec-team-pulse组件已安装")
                    return False

            # 调用标点组件的开启接口
            if hasattr(self.waypoint_system, 'enable_waypoint'):
                result = self.waypoint_system.enable_waypoint()
                if result:
                    self.is_enabled = True
                    print("[WaypointManager] 标点功能已启用")
                    return True
                else:
                    print("[WaypointManager] 标点组件拒绝启用标点功能")
                    return False
            else:
                print("[WaypointManager] 标点组件不支持enable_waypoint接口")
                return False

        except Exception as e:
            print("[WaypointManager] 启用标点功能失败: {}".format(str(e)))
            return False

    def disable_waypoint(self):
        """
        禁用标点功能（对局结束时调用）

        Returns:
            bool: 是否成功
        """
        try:
            if not self.waypoint_system:
                print("[WaypointManager] 标点系统未初始化")
                return False

            # 先注销事件监听
            self._unregister_waypoint_events()

            # 调用标点组件的关闭接口
            if hasattr(self.waypoint_system, 'disable_waypoint'):
                self.waypoint_system.disable_waypoint()
                self.is_enabled = False
                print("[WaypointManager] 标点功能已禁用")
                return True
            else:
                # 如果没有disable接口，至少在本地标记为禁用
                self.is_enabled = False
                print("[WaypointManager] 标点组件不支持disable_waypoint接口，仅本地禁用")
                return True

        except Exception as e:
            print("[WaypointManager] 禁用标点功能失败: {}".format(str(e)))
            return False

    def is_waypoint_allowed(self, player_id):
        """
        检查玩家是否允许使用标点功能

        Args:
            player_id (str): 玩家ID

        Returns:
            bool: 是否允许
        """
        try:
            # 检查缓存
            current_time = time.time()
            if player_id in self._permission_cache:
                if current_time < self._cache_expire_time.get(player_id, 0):
                    return self._permission_cache[player_id]

            # 执行权限检查
            allowed = self._check_waypoint_permission(player_id)

            # 更新缓存
            self._permission_cache[player_id] = allowed
            self._cache_expire_time[player_id] = current_time + self._cache_duration

            return allowed

        except Exception as e:
            print("[WaypointManager] 权限检查失败: {}".format(str(e)))
            return False

    def on_waypoint_create_request(self, player_id, position, waypoint_type):
        """
        处理玩家标点创建请求

        Args:
            player_id (str): 玩家ID
            position (tuple): 标点位置
            waypoint_type (str): 标点类型

        Returns:
            waypoint_id or False: 标点ID或失败
        """
        try:
            # 权限检查
            if not self.is_waypoint_allowed(player_id):
                return False

            # 调用标点组件创建标点
            waypoint_id = self._create_waypoint_via_system(player_id, position, waypoint_type)
            if not waypoint_id:
                return False

            # 通知队伍控制器处理
            if self.team_controller:
                success = self.team_controller.on_waypoint_created(
                    player_id, waypoint_id, position, waypoint_type
                )
                if not success:
                    # 如果队伍处理失败，移除已创建的标点
                    self._remove_waypoint_via_system(waypoint_id)
                    return False

            return waypoint_id

        except Exception as e:
            print("[WaypointManager] 处理标点创建请求失败: {}".format(str(e)))
            return False

    def on_waypoint_remove_request(self, player_id, waypoint_id):
        """
        处理玩家标点移除请求

        Args:
            player_id (str): 玩家ID
            waypoint_id: 标点ID

        Returns:
            bool: 是否成功
        """
        try:
            # 权限检查
            if not self.is_waypoint_allowed(player_id):
                return False

            # 检查玩家是否有权限移除此标点
            if not self._can_player_remove_waypoint(player_id, waypoint_id):
                return False

            # 通知队伍控制器处理
            if self.team_controller:
                self.team_controller.on_waypoint_removed(waypoint_id)

            # 调用标点组件移除标点
            return self._remove_waypoint_via_system(waypoint_id)

        except Exception as e:
            print("[WaypointManager] 处理标点移除请求失败: {}".format(str(e)))
            return False

    def on_player_join(self, args):
        """
        处理玩家加入游戏事件

        Args:
            args (dict): 事件参数
        """
        try:
            player_id = args.get('id', args.get('__id__'))
            if not player_id:
                return

            print("[WaypointManager] 玩家加入游戏: {}".format(player_id))

            # 清理该玩家的权限缓存
            if player_id in self._permission_cache:
                del self._permission_cache[player_id]
            if player_id in self._cache_expire_time:
                del self._cache_expire_time[player_id]

            # 确保玩家被添加到标点系统中（如果组件支持）
            if self.is_enabled and self.waypoint_system:
                if hasattr(self.waypoint_system, 'add_player_to_session'):
                    self.waypoint_system.add_player_to_session(player_id)

        except Exception as e:
            print("[WaypointManager] 处理玩家加入失败: {}".format(str(e)))

    def on_player_leave(self, args):
        """
        处理玩家退出游戏事件

        Args:
            args (dict): 事件参数
        """
        try:
            player_id = args.get('id', args.get('__id__'))
            if not player_id:
                return

            print("[WaypointManager] 玩家退出游戏: {}".format(player_id))

            # 清理权限缓存
            if player_id in self._permission_cache:
                del self._permission_cache[player_id]
            if player_id in self._cache_expire_time:
                del self._cache_expire_time[player_id]

            # 通知队伍控制器清理该玩家的标点
            if self.team_controller:
                self.team_controller.on_player_leave(player_id)

        except Exception as e:
            print("[WaypointManager] 处理玩家退出失败: {}".format(str(e)))

    def on_player_team_changed(self, player_id, old_team_id, new_team_id):
        """
        处理玩家队伍变更事件

        Args:
            player_id (str): 玩家ID
            old_team_id (str): 旧队伍ID
            new_team_id (str): 新队伍ID
        """
        try:
            print("[WaypointManager] 玩家 {} 队伍变更: {} -> {}".format(
                player_id, old_team_id, new_team_id))

            # 清理该玩家的权限缓存
            if player_id in self._permission_cache:
                del self._permission_cache[player_id]
            if player_id in self._cache_expire_time:
                del self._cache_expire_time[player_id]

            # 通知队伍控制器处理队伍变更
            if self.team_controller:
                self.team_controller.on_player_team_changed(player_id, old_team_id, new_team_id)

        except Exception as e:
            print("[WaypointManager] 处理队伍变更失败: {}".format(str(e)))

    def update(self):
        """定期更新（清理过期标点等）"""
        try:
            if not self.is_enabled:
                return

            # 清理过期标点
            if self.team_controller:
                self.team_controller.cleanup_expired_waypoints()

            # 清理过期的权限缓存
            self._cleanup_expired_cache()

        except Exception as e:
            print("[WaypointManager] 更新失败: {}".format(str(e)))

    def get_waypoint_system(self):
        """
        获取标点系统接口

        Returns:
            标点系统实例或None
        """
        return self.waypoint_system

    # ===== 私有方法 =====

    def _get_waypoint_system(self):
        """
        通过GetSystem获取标点组件接口

        Returns:
            标点系统实例或None
        """
        try:
            system = serverApi.GetSystem("ECTeamPulse", "ECTeamPulseServer")
            if system:
                print("[WaypointManager] 成功获取标点系统接口")
                return system
            else:
                print("[WaypointManager] 未找到标点系统组件（ECTeamPulse）")
                return None
        except Exception as e:
            print("[WaypointManager] 获取标点系统接口失败: {}".format(str(e)))
            return None

    def _register_waypoint_events(self):
        """注册标点相关事件监听"""
        try:
            # 注册玩家加入/退出游戏的事件监听
            if hasattr(self.bedwars_system, 'ListenForEvent'):
                # 监听玩家加入游戏事件
                self.bedwars_system.ListenForEvent(
                    serverApi.GetEngineNamespace(),
                    serverApi.GetEngineSystemName(),
                    "AddServerPlayerEvent",
                    self,
                    self.on_player_join
                )

                # 监听玩家退出游戏事件
                self.bedwars_system.ListenForEvent(
                    serverApi.GetEngineNamespace(),
                    serverApi.GetEngineSystemName(),
                    "DelServerPlayerEvent",
                    self,
                    self.on_player_leave
                )

                print("[WaypointManager] 玩家加入/退出事件监听已注册")
            else:
                print("[WaypointManager] 无法注册事件监听")

        except Exception as e:
            print("[WaypointManager] 标点事件注册失败: {}".format(str(e)))

    def _unregister_waypoint_events(self):
        """注销标点相关事件监听"""
        try:
            # 注销玩家加入/退出游戏的事件监听
            if hasattr(self.bedwars_system, 'UnListenForEvent'):
                # 注销玩家加入游戏事件
                self.bedwars_system.UnListenForEvent(
                    serverApi.GetEngineNamespace(),
                    serverApi.GetEngineSystemName(),
                    "AddServerPlayerEvent",
                    self,
                    self.on_player_join
                )

                # 注销玩家退出游戏事件
                self.bedwars_system.UnListenForEvent(
                    serverApi.GetEngineNamespace(),
                    serverApi.GetEngineSystemName(),
                    "DelServerPlayerEvent",
                    self,
                    self.on_player_leave
                )

                print("[WaypointManager] 玩家加入/退出事件监听已注销")

        except Exception as e:
            print("[WaypointManager] 标点事件注销失败: {}".format(str(e)))

    def _check_waypoint_permission(self, player_id):
        """
        检查玩家标点权限（核心逻辑）

        Args:
            player_id (str): 玩家ID

        Returns:
            bool: 是否有权限
        """
        try:
            # 1. 检查标点功能是否已启用
            if not self.is_enabled:
                return False

            # 2. 检查是否在对局中
            if not self._is_game_running():
                return False

            # 3. 检查玩家是否在游戏中（非观战）
            if self._is_player_spectator(player_id):
                return False

            # 4. 检查玩家队伍状态
            if not self._is_player_team_active(player_id):
                return False

            # 5. 检查玩家连接状态
            if not self._is_player_connected(player_id):
                return False

            return True

        except Exception as e:
            print("[WaypointManager] 权限检查异常: {}".format(str(e)))
            return False

    def _is_game_running(self):
        """检查游戏是否正在运行"""
        try:
            if not hasattr(self.bedwars_system, 'root_state') or self.bedwars_system.root_state is None:
                return False

            current_state_name = getattr(self.bedwars_system.root_state, 'current_sub_state_name', None)
            if not current_state_name:
                return False

            # 只有在 'starting' 和 'running' 状态下才允许标点
            allowed_states = ['starting', 'running']
            return current_state_name in allowed_states

        except Exception as e:
            print("[WaypointManager] 检查游戏状态异常: {}".format(str(e)))
            return False

    def _is_player_spectator(self, player_id):
        """检查玩家是否为观战者"""
        try:
            if hasattr(self.bedwars_system, 'is_spectator'):
                return self.bedwars_system.is_spectator(player_id)
            return False
        except:
            return False

    def _is_player_team_active(self, player_id):
        """检查玩家队伍是否活跃（未被淘汰）"""
        try:
            if not hasattr(self.bedwars_system, 'team_module'):
                return False

            team = self.bedwars_system.team_module.get_player_team(player_id)
            if not team:
                return False

            # 检查队伍是否被淘汰
            # 队伍淘汰的判定：床被破坏 + 队伍所有玩家都死亡/离线
            # 这里简化为检查床是否被破坏 + 队伍是否还有存活玩家
            if hasattr(self.bedwars_system, 'destroyed_beds'):
                if team in self.bedwars_system.destroyed_beds:
                    # 床已破坏，检查是否还有存活玩家
                    team_players = self.bedwars_system.team_module.get_team_players(team)
                    if not team_players or len(team_players) == 0:
                        return False

            return True

        except:
            return False

    def _is_player_connected(self, player_id):
        """检查玩家是否在线"""
        # 简化实现：默认返回True
        return True

    def _can_player_remove_waypoint(self, player_id, waypoint_id):
        """检查玩家是否有权限移除指定标点"""
        try:
            if not self.team_controller:
                return False

            # 检查是否为标点创建者
            player_waypoints = self.team_controller.player_waypoints.get(player_id, [])
            return waypoint_id in player_waypoints

        except:
            return False

    def _create_waypoint_via_system(self, player_id, position, waypoint_type):
        """通过标点组件创建标点"""
        try:
            if not self.waypoint_system:
                print("[WaypointManager] waypoint_system未初始化")
                return None

            # 调用ec-team-pulse的创建接口
            if hasattr(self.waypoint_system, 'create_waypoint'):
                waypoint_id = self.waypoint_system.create_waypoint(
                    player_id, position, waypoint_type
                )
                return waypoint_id
            else:
                print("[WaypointManager] 标点系统不支持create_waypoint接口")
                return None

        except Exception as e:
            print("[WaypointManager] 创建标点失败: {}".format(str(e)))
            return None

    def _remove_waypoint_via_system(self, waypoint_id):
        """通过标点组件移除标点"""
        try:
            if not self.waypoint_system:
                return False

            # 调用ec-team-pulse的移除接口
            if hasattr(self.waypoint_system, 'remove_waypoint'):
                return self.waypoint_system.remove_waypoint(waypoint_id)
            else:
                return False

        except Exception as e:
            print("[WaypointManager] 移除标点失败: {}".format(str(e)))
            return False

    def _cleanup_expired_cache(self):
        """清理过期的权限缓存"""
        try:
            current_time = time.time()
            expired_players = []

            for player_id, expire_time in self._cache_expire_time.items():
                if current_time >= expire_time:
                    expired_players.append(player_id)

            for player_id in expired_players:
                if player_id in self._permission_cache:
                    del self._permission_cache[player_id]
                if player_id in self._cache_expire_time:
                    del self._cache_expire_time[player_id]

        except Exception as e:
            print("[WaypointManager] 清理缓存失败: {}".format(str(e)))

    def get_debug_info(self):
        """获取调试信息"""
        info = {
            'enabled': self.is_enabled,
            'waypoint_system_available': self.waypoint_system is not None,
            'permission_cache_size': len(self._permission_cache),
            'game_running': self._is_game_running()
        }

        if self.team_controller:
            info.update({
                'team_waypoints': len(self.team_controller.team_waypoints),
                'total_waypoints': len(self.team_controller.waypoint_timestamps)
            })

        return info

    def cleanup(self):
        """
        清理标点管理器资源

        清理内容:
        - 禁用标点系统
        - 清理缓存数据
        - 解除引用
        """
        print("[WaypointManager] 开始清理...")

        # 禁用系统
        self.is_enabled = False

        # 先禁用标点功能
        try:
            self.disable_waypoint()
        except Exception as e:
            print("[WaypointManager] 禁用标点功能失败: {}".format(str(e)))

        # 清理团队控制器
        if self.team_controller:
            # 如果team_controller也有cleanup方法,调用它
            if hasattr(self.team_controller, 'cleanup'):
                self.team_controller.cleanup()
            self.team_controller = None

        # 清理缓存
        if hasattr(self, '_permission_cache'):
            self._permission_cache.clear()
        if hasattr(self, '_cache_expire_time'):
            self._cache_expire_time.clear()

        # 清理系统引用
        self.waypoint_system = None

        print("[WaypointManager] 清理完成")
