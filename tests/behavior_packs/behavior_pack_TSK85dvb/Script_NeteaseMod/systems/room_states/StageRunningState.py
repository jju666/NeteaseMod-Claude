# -*- coding: utf-8 -*-
"""
StageRunningState - 房间游戏进行状态

功能:
- 异步加载地图区块
- 启动游戏
- 传送玩家到游戏地图
- 监听游戏结束事件
- 超时保护(最长1小时)

原文件: Parts/ECStage/state/StageRunningState.py
重构为: systems/room_states/StageRunningState.py
"""

import mod.server.extraServerApi as serverApi
from Script_NeteaseMod.systems.state.TimedGamingState import TimedGamingState

# 获取引擎组件工厂
ServerCompFactory = serverApi.GetEngineCompFactory()


class StageRunningState(TimedGamingState):
    """
    房间游戏进行状态（带超时保护）

    核心职责:
    - 异步加载地图区块（防止卡顿）
    - 游戏开始时的初始化
    - 将玩家传送到游戏维度
    - 启动BedWarsGameSystem
    - 等待游戏结束信号
    - 超时保护: 最长游戏时间3600秒(1小时)
    """

    def __init__(self, parent):
        """
        初始化游戏进行状态

        Args:
            parent: 父状态
        """
        # 初始化TimedGamingState，设置最长游戏时间为3600秒(1小时)
        TimedGamingState.__init__(self, parent, 3600.0)

        # 区块加载状态
        self.chunks_loaded = False

        # 注册钩子
        self.with_enter(self.on_enter)
        self.with_tick(self.on_tick)
        self.with_exit(self.on_exit)
        self.with_time_out(self.on_timeout)

        # 监听游戏结束事件
        self.listen_self_event("BedWarsGameEnd", self.on_game_end)

        # 监听玩家加入/离开事件（中途加入功能）
        self.listen_self_event("ServerPlayerJoinEvent", self.on_viewer_join)
        self.listen_self_event("ServerPlayerLeaveEvent", self.on_player_leave)

    def on_enter(self):
        """
        进入游戏进行状态

        流程:
        1. 标记地图为使用中
        2. 暂停地图任务系统（防止还原与游戏冲突）
        3. 显示地图载入HUD提示
        4. 异步加载地图区块
        5. 加载完成后启动游戏
        """
        system = self.get_system()
        system.LogInfo("StageRunningState.on_enter")

        # 1. 标记当前地图为使用中
        if hasattr(system, 'current_stage_id') and system.current_stage_id:
            system.mark_map_as_in_use(system.current_stage_id)
            system.LogInfo("地图已标记为使用中: {}".format(system.current_stage_id))

        # 2. 暂停地图任务系统（如果有还原任务在进行）
        if hasattr(system, 'pause_map_task_system'):
            system.pause_map_task_system()

        # 3. 显示地图载入提示HUD
        self._show_map_loading_hud()

        # 4. 异步加载地图区块
        self._load_chunks_async()

    def on_tick(self):
        """每帧更新"""
        # 游戏进行中,主要逻辑由BedWarsGameSystem处理
        pass

    def on_exit(self):
        """
        退出游戏进行状态

        清理工作:
        1. 取消地图使用中标记
        2. 恢复玩家游戏模式为冒险模式
        3. 开启伤害免疫
        """
        system = self.get_system()
        system.LogInfo("StageRunningState.on_exit")

        # 1. 取消地图使用中标记
        if hasattr(system, 'current_stage_id') and system.current_stage_id:
            system.unmark_map_as_in_use(system.current_stage_id)
            system.LogInfo("地图已取消使用中标记: {}".format(system.current_stage_id))

        # 2. 恢复所有玩家的游戏模式为冒险模式，开启伤害免疫
        self._reset_players_game_mode()

        # 3. 标记游戏结束
        system.is_game_running = False

    def on_timeout(self, timed_state):
        """
        游戏超时回调(1小时)

        Args:
            timed_state: TimedGamingState实例
        """
        system = self.get_system()
        system.LogInfo("游戏超时(3600秒),强制结束游戏")

        # 广播超时消息
        system.broadcast_message(u"游戏时间已达上限,游戏结束!")

        # 强制结束游戏,获胜队伍为None(平局)
        system.end_game(None)

        # 【修复 2025-11-18】清除父状态的子状态引用,阻止TimedGamingState的自动切换
        # 原理同StageWaitingCountdownState.on_timeout的修复
        # StageRunningState的parent是root_state,清除current_sub_state防止状态被切换两次
        root_state = system.root_state
        if root_state:
            root_state.current_sub_state = None
            system.LogInfo("已清除root_state的子状态引用,阻止TimedGamingState自动切换")

        # 切换到下一个状态(broadcast_score)
        if root_state:
            root_state.next_sub_state()
            system.LogInfo("已切换到broadcast_score状态")
        else:
            system.LogError("root_state不存在,无法切换状态")

    def on_game_end(self, args):
        """
        处理游戏结束事件

        [FIX 2025-11-07] 修复胜利结算流程:
        新流程:
        1. BedWarsGameSystem触发BedWarsGameEnd事件(本方法接收)
        2. BedWarsGameSystem进入BedWarsEndingState(10秒胜利展示)
        3. BedWarsEndingState结束后调用_notify_game_end_to_room()
        4. _notify_game_end_to_room()调用room_system.end_game()清理
        5. _notify_game_end_to_room()调用room_system.root_state.next_sub_state()切换到broadcast_score

        因此本方法不需要做任何处理,只记录日志

        Args:
            args: 事件参数
                - winning_team: 获胜队伍ID
                - game_time: 游戏时长
                - stats: 游戏统计数据
        """
        system = self.get_system()
        winning_team = args.get("winning_team")

        system.LogInfo("收到游戏结束事件 winning_team={},等待BedWarsGameSystem完成ending状态".format(winning_team))

        # [FIX 2025-11-07] 不做任何处理
        # BedWarsGameSystem会自己进入ending状态,结束后会自动:
        # 1. 调用room_system.end_game()清理
        # 2. 调用room_system.root_state.next_sub_state()切换到broadcast_score

    def _show_map_loading_hud(self):
        """显示地图载入中HUD提示"""
        system = self.get_system()

        try:
            # 为所有等待中的玩家显示HUD
            hud_data = {
                'type': 'stack_msg_bottom',
                'events': [{
                    'event': 'add_or_set',
                    'key': 'map_loading',
                    'value': system.format_text(u"{gray}请稍等，地图正在载入...")
                }]
            }

            system.broadcast_preset_event("ECHUDControl", hud_data)
            system.LogInfo("地图载入HUD已显示")

        except Exception as e:
            system.LogError("显示地图载入HUD失败: {}".format(str(e)))

    def _hide_map_loading_hud(self):
        """隐藏地图载入中HUD提示"""
        system = self.get_system()

        try:
            hud_data = {
                'type': 'stack_msg_bottom',
                'events': [{
                    'event': 'remove',
                    'key': 'map_loading'
                }]
            }

            system.broadcast_preset_event("ECHUDControl", hud_data)
            system.LogInfo("地图载入HUD已隐藏")

        except Exception as e:
            system.LogError("隐藏地图载入HUD失败: {}".format(str(e)))

    def _load_chunks_async(self):
        """
        异步加载地图区块

        流程:
        1. 获取地图中心点和备份范围
        2. 调用DoTaskOnChunkAsync异步加载
        3. 加载完成后回调_on_chunks_loaded
        """
        system = self.get_system()

        try:
            # 获取当前地图配置
            if not hasattr(system, 'current_stage_config') or system.current_stage_config is None:
                system.LogError("缺少current_stage_config，无法加载区块")
                # 降级处理：直接启动游戏
                self._on_chunks_loaded(None)
                return

            stage_config = system.current_stage_config

            # 获取地图中心点（默认使用spawn_pos）
            center_pos = stage_config.get('center_pos')
            if not center_pos:
                center_pos = stage_config.get('spawn_pos', [0, 100, 0])

            # 计算备份范围（从中心点扩展150格）
            backup_range = system.get_backup_range_from_center(center_pos, 150)

            # 获取游戏维度
            dimension = system.current_dimension

            system.LogInfo("开始异步加载区块 dimension={} range={}".format(
                dimension, backup_range
            ))

            # 异步加载区块
            level_id = serverApi.GetLevelId()
            comp_chunk = ServerCompFactory.CreateChunkSource(level_id)

            comp_chunk.DoTaskOnChunkAsync(
                dimension,
                backup_range[0],
                backup_range[1],
                self._on_chunks_loaded
            )

        except Exception as e:
            system.LogError("异步加载区块失败: {}".format(str(e)))
            # 降级处理：直接启动游戏
            self._on_chunks_loaded(None)

    def _on_chunks_loaded(self, data):
        """
        区块加载完成回调

        Args:
            data: 回调数据（通常为None）
        """
        system = self.get_system()
        system.LogInfo("区块加载完成，准备启动游戏")

        # 标记区块已加载
        self.chunks_loaded = True

        # 1. 隐藏载入提示HUD
        self._hide_map_loading_hud()

        # 2. 启动游戏（传送玩家到游戏维度）
        self._start_game()

        # 3. 设置玩家为生存模式
        self._set_players_survival_mode()

    def _start_game(self):
        """
        启动游戏

        流程:
        1. 调用RoomManagementSystem的start_game方法
           - 这会选择地图、分配队伍、传送玩家到队伍出生点
           - 启动BedWarsGameSystem并初始化游戏
        """
        system = self.get_system()

        try:
            # 调用RoomManagementSystem的start_game方法
            # 注意：system.start_game()已经包含了玩家传送逻辑
            # 它会根据队伍分配将玩家传送到各自的队伍出生点
            system.start_game()

            system.LogInfo("游戏已启动")

        except Exception as e:
            system.LogError("启动游戏失败: {}".format(str(e)))

    def _set_players_survival_mode(self):
        """设置所有玩家为生存模式"""
        system = self.get_system()

        try:
            for player_id in list(system.waiting_players):
                comp_player = ServerCompFactory.CreatePlayer(player_id)
                comp_player.SetPlayerGameType(1)  # 1 = 生存模式

            system.LogInfo("所有玩家已设置为生存模式")

        except Exception as e:
            system.LogError("设置玩家生存模式失败: {}".format(str(e)))

    def _reset_players_game_mode(self):
        """重置所有玩家为冒险模式并开启伤害免疫"""
        system = self.get_system()

        try:
            for player_id in system.get_all_players():
                comp_player = ServerCompFactory.CreatePlayer(player_id)
                comp_player.SetPlayerGameType(2)  # 2 = 冒险模式

                # 开启伤害免疫
                comp_hurt = ServerCompFactory.CreateHurt(player_id)
                comp_hurt.ImmuneDamage(True)

            system.LogInfo("所有玩家已重置为冒险模式并开启伤害免疫")

        except Exception as e:
            system.LogError("重置玩家游戏模式失败: {}".format(str(e)))

    def on_viewer_join(self, args):
        """
        处理中途加入的玩家（游戏已开始后加入）

        根据用户需求：倒计时结束后玩家仍可加入对局内

        处理策略：
        1. 玩家以观战者身份加入
        2. 传送到观战出生点（地图中心或等待区）
        3. 设置为观察者模式或冒险模式（无敌）
        4. 发送HUD提示
        5. 允许观看游戏进行

        Args:
            args: 事件参数 {'player_id': player_id}
        """
        system = self.get_system()
        player_id = args.get('player_id')

        system.LogInfo("[StageRunningState] 玩家中途加入: {}（以观战者身份）".format(player_id))

        try:
            player_obj = system.get_better_player_obj(player_id)

            # 1. 清空背包
            player_obj.clear_inventory()

            # 2. 确定观战出生点
            # 优先使用地图中心点，如果没有则使用spawn_pos
            if hasattr(system, 'current_stage_config') and system.current_stage_config:
                stage_config = system.current_stage_config
                spectator_pos = stage_config.get('center_pos')
                if not spectator_pos:
                    spectator_pos = stage_config.get('spawn_pos', [0, 100, 0])

                # 转换为元组
                spectator_pos = tuple(spectator_pos)
            else:
                # 默认观战点
                spectator_pos = (0, 100, 0)

            # 3. 传送到观战位置（游戏维度）
            dimension = system.current_dimension
            if dimension is not None:
                player_obj.teleport(spectator_pos, dimension)
                system.LogInfo("玩家 {} 传送到观战位置: pos={}, dim={}".format(
                    player_id, spectator_pos, dimension
                ))
            else:
                system.LogWarn("游戏维度未设置，传送到大厅")
                player_obj.teleport(system.waiting_spawn, system.lobby_dimension)

            # 4. 设置为冒险模式（无法破坏方块，可以移动）
            comp_player = ServerCompFactory.CreatePlayer(player_id)
            comp_player.SetPlayerGameType(2)  # 2 = 冒险模式

            # 5. 开启伤害免疫
            comp_hurt = ServerCompFactory.CreateHurt(player_id)
            comp_hurt.ImmuneDamage(True)

            # 6. 设置饥饿值不掉落
            comp_player.SetPlayerHunger(20.0)
            comp_player.SetPlayerMaxExhaustionValue(9999.0)

            # 7. 发送欢迎消息和说明
            player_obj.send_message(u"\u00a7e游戏已开始，您将以观战者身份观看比赛！")
            player_obj.send_message(u"\u00a77提示：您可以自由移动，但无法参与战斗")

            # 8. 发送Title提示
            player_obj.send_title(
                u"\u00a7e观战模式",
                u"\u00a77游戏正在进行中",
                fadein=10,
                duration=60,
                fadeout=10
            )

            # 9. 广播玩家加入观战
            system.broadcast_message(u"\u00a77玩家 \u00a7f{} \u00a77以观战者身份加入".format(player_id))

            # 10. 通知BedWarsGameSystem有观战者加入（如果需要显示在观战列表）
            if system.bedwars_game_system:
                system.bedwars_game_system.notify_viewer_join(player_id)

            system.LogInfo("中途加入玩家 {} 已设置为观战者".format(player_id))

        except Exception as e:
            system.LogError("处理中途加入玩家失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def on_player_leave(self, args):
        """
        处理游戏进行中玩家离开事件

        Args:
            args: 事件参数 {'player_id': player_id}
        """
        system = self.get_system()
        player_id = args.get('player_id')

        system.LogInfo("[StageRunningState] 玩家离开（游戏中）: {}".format(player_id))

        # 玩家离开的清理逻辑已在RoomManagementSystem.on_player_leave中处理
        # 如果玩家是游戏参与者，BedWarsGameSystem会处理淘汰逻辑
        # 这里只记录日志

        try:
            # 通知BedWarsGameSystem玩家离开
            if system.bedwars_game_system:
                system.bedwars_game_system.notify_player_leave(player_id)

        except Exception as e:
            system.LogError("处理游戏中玩家离开失败: {}".format(str(e)))

    def get_system(self):
        """
        获取RoomManagementSystem实例

        Returns:
            RoomManagementSystem: 系统实例
        """
        return self.parent.get_system()
