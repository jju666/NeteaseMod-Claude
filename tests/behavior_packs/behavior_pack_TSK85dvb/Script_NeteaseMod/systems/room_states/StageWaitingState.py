# -*- coding: utf-8 -*-
"""
StageWaitingState - 房间等待状态

功能:
- 等待玩家加入
- 玩家数量检测
- 倒计时管理
- 地图投票

原文件: Parts/ECStage/state/StageWaitingState.py
重构为: systems/room_states/StageWaitingState.py
"""

import time
import mod.server.extraServerApi as serverApi
from Script_NeteaseMod.systems.state.GamingState import GamingState
from Script_NeteaseMod.systems.state.TimedGamingState import TimedGamingState


class StageWaitingState(GamingState):
    """
    房间等待状态

    子状态:
    - pending: 等待玩家加入
    - countdown: 倒计时阶段
    """

    def __init__(self, parent):
        """
        初始化等待状态

        Args:
            parent: 父状态
        """
        GamingState.__init__(self, parent)

        # 检查频率控制
        self.next_check = 0

        # 强制开始标志
        self.force_start = False

        # 防抖机制状态
        self._state_transition_debounce = {
            'last_check_time': 0,
            'last_state': None,
            'stable_count': 0,
            'required_stable_count': 3  # 需要连续3次检查结果一致
        }

        # 全局状态切换锁
        self._global_state_switch_lock = False

        # 添加子状态
        self.add_sub_state("pending", StageWaitingPendingState)
        self.add_sub_state("countdown", StageWaitingCountdownState)

        # 注册钩子
        self.with_enter(self.on_enter)
        self.with_tick(self.on_tick)
        self.with_exit(self.on_exit)

        # 注册引擎事件监听（参考老项目）
        # 这些事件在等待状态时需要处理
        self.listen_engine_event('AddServerPlayerEvent', self.on_add_server_player)
        self.listen_engine_event('ItemUseAfterServerEvent', self.on_player_use_item_on_block)
        self.listen_engine_event('MobGriefingBlockServerEvent', self.on_farm_block_to_dirt)

    def is_allow_map_vote(self):
        """
        检查当前是否允许地图投票

        Returns:
            bool: 是否允许投票
        """
        # 在pending状态时始终允许投票
        if self.current_sub_state_name == "pending":
            return True

        # 在countdown状态时，剩余时间>5秒时允许投票
        elif self.current_sub_state_name == "countdown":
            countdown_state = self.current_sub_state
            if countdown_state and hasattr(countdown_state, 'get_seconds_left'):
                return countdown_state.get_seconds_left() > 5

        # 其他情况不允许投票
        return False

    def on_enter(self):
        """进入等待状态时调用

        注意: 不要在这里手动调用toggle_sub_state()!
        GamingState.enter()会在回调执行完后自动进入第一个子状态(pending)

        修复说明 [FIX 2025-11-07]:
        - 添加了 _update_coin_display() 调用，确保从游戏结束返回等待状态时立即显示UI
        - 解决了对局结束后顶部HUD不显示的问题
        - 参考：StageWaitingPendingState.on_enter():543 的UI更新逻辑

        [DEBUG 2025-11-07]:
        - 添加详细日志追踪状态进入流程和玩家状态
        """
        system = self.get_system()
        system.LogInfo("StageWaitingState.on_enter")
        system.LogInfo("[DEBUG] StageWaitingState.on_enter 开始执行")
        system.LogInfo("[DEBUG] - waiting_players数量: {}".format(len(system.waiting_players)))
        system.LogInfo("[DEBUG] - playing_players数量: {}".format(len(system.playing_players)))

        # 重置强制开始标志
        self.force_start = False

        # 重置游戏状态
        system.is_game_running = False
        system.current_dimension = None

        # 传送所有玩家回大厅
        self._teleport_all_to_lobby()

        # 清空游戏玩家列表,移回等待列表
        system.waiting_players.extend(system.playing_players)
        system.playing_players = []

        # 创建地图投票实例
        system.create_map_vote()
        system.LogInfo("地图投票实例已创建")

        # 监听玩家加入/离开事件（在等待状态时处理）
        # 注意：这些事件的实际注册在RoomManagementSystem._register_engine_events()中
        # 但我们需要在状态中注册监听器，以便状态切换时自动清理
        self.listen_self_event("ServerPlayerJoinEvent", self.on_player_join)
        self.listen_self_event("ServerPlayerLeaveEvent", self.on_player_leave)

        # [FIX 2025-11-07] 立即更新HUD，确保从游戏结束返回时UI正常显示
        # 主要更新顶部coin显示，底部状态栏会在子状态pending进入时更新
        self._update_coin_display()

        # [FIX 2025-11-12] 清理结算UI
        # 从结算状态返回等待状态时，需要清理Title和ActionBar
        system.NotifyToClient(None, "ClearGameEndUI", {})

        # [FIX 2025-11-07 #3] 延迟发放大厅道具,等待玩家传送完成
        # 问题: 在on_enter()时立即调用_give_lobby_items_to_all_players(),但此时玩家可能还在传送中
        # 解决: 延迟2秒后发放道具,确保玩家已经传送到大厅并且客户端已加载完成
        # 参考: 老项目也是在玩家实际加入时发放道具,而不是在状态进入时
        def delayed_give_items():
            try:
                self._give_lobby_items_to_all_players()
                system.LogInfo("延迟发放大厅道具完成")
            except Exception as e:
                system.LogError("延迟发放大厅道具失败: {}".format(str(e)))

        system.add_timer(2.0, delayed_give_items)

        system.LogInfo("StageWaitingState 进入完成")

    def on_tick(self):
        """每帧更新"""
        # 限制检查频率
        if time.time() < self.next_check:
            return

        self.next_check = time.time() + 0.5  # 每0.5秒检查一次

        # 检查等待玩家的位置，防止掉入虚空
        self._check_players_position()

        # 使用防抖机制处理状态切换
        self._handle_state_transition_with_debounce()

    def _handle_state_transition_with_debounce(self):
        """
        使用防抖机制处理状态切换

        防止状态切换抖动:
        - 需要连续3次检查结果一致才执行切换
        - 使用全局锁防止重复切换
        """
        # 检查全局锁
        if self._global_state_switch_lock:
            return

        system = self.get_system()

        # 获取等待玩家数量
        waiting_count = len(system.waiting_players)
        start_players = system.start_players

        # 判断是否需要倒计时
        need_countdown = self.force_start or waiting_count >= start_players
        current_state = 'countdown' if need_countdown else 'pending'

        # 更新防抖状态
        current_time = time.time()
        self._state_transition_debounce['last_check_time'] = current_time

        # 检查状态是否变化
        if current_state != self._state_transition_debounce['last_state']:
            # 状态变化,重置稳定计数器
            self._state_transition_debounce['last_state'] = current_state
            self._state_transition_debounce['stable_count'] = 1
            return

        # 状态未变化,增加稳定计数器
        self._state_transition_debounce['stable_count'] += 1

        # 检查是否达到稳定次数
        required_count = self._state_transition_debounce['required_stable_count']
        if self._state_transition_debounce['stable_count'] < required_count:
            return

        # 达到稳定次数,检查是否需要切换
        if self.current_sub_state_name != current_state:
            # 锁定状态切换
            self._global_state_switch_lock = True

            # 执行状态切换
            if current_state == 'countdown':
                system.LogInfo("玩家数达到要求({}/{}),开始倒计时".format(
                    waiting_count, start_players))
                self.toggle_sub_state("countdown")
            else:
                system.LogInfo("玩家数不足({}/{}),取消倒计时".format(
                    waiting_count, start_players))
                self.toggle_sub_state("pending")

            # 延迟解锁(2秒后)
            def unlock_state_switch():
                self._global_state_switch_lock = False
                system.LogInfo("状态切换锁已解除")

            system.add_timer(2.0, unlock_state_switch)

        # 重置稳定计数器
        self._state_transition_debounce['stable_count'] = 0

    def on_exit(self):
        """退出等待状态时调用"""
        system = self.get_system()
        system.LogInfo("StageWaitingState.on_exit")

    def _check_players_position(self):
        """
        检查等待玩家的位置，防止掉入虚空

        功能：
        - 检查玩家Y坐标是否小于60（虚空检测）
        - 如果是，传送玩家回大厅出生点
        - 广播玩家坠落事件

        参考老项目：StageWaitingState.py line 175-188
        """
        system = self.get_system()

        try:
            # 遍历所有等待中的玩家
            for player_id in list(system.waiting_players):  # 使用list复制避免迭代时修改
                try:
                    player_obj = system.get_better_player_obj(player_id)
                    if not player_obj:
                        continue

                    # 获取玩家位置
                    pos = player_obj.GetPos()
                    if not pos or len(pos) < 2:
                        continue

                    # 检查Y坐标（虚空检测阈值：60）
                    if pos[1] < 60:
                        # 传送玩家回大厅
                        player_obj.teleport(system.waiting_spawn, system.lobby_dimension)
                        system.LogInfo("玩家 {} 掉入虚空(Y={}),已传送回大厅".format(
                            player_id, pos[1]
                        ))

                        # 广播玩家坠落事件（可选，用于统计或提示）
                        # 注意：老项目使用BroadcastPresetSystemEvent，新项目可以使用自定义事件
                        # system.broadcast_preset_event("ServerPlayerFallEvent", {
                        #     "playerId": player_id,
                        #     "pos": pos
                        # })

                except Exception as e:
                    system.LogError("检查玩家 {} 位置失败: {}".format(player_id, str(e)))

        except Exception as e:
            system.LogError("_check_players_position执行失败: {}".format(str(e)))

    def _teleport_all_to_lobby(self):
        """
        传送所有玩家回大厅并重置状态

        功能：
        - 清空玩家背包
        - 传送回大厅
        - 重置游戏模式为冒险模式（修复：确保所有玩家都重置，包括已在大厅的玩家）
        - 设置无敌状态
        - 禁用飞行状态

        注意：
        - 大厅道具的发放已移到 _give_lobby_items_to_all_players() 方法中
        - 该方法在 on_enter() 中单独调用，职责分离更加清晰

        修复说明：
        对局结束后，状态机回到等待状态时，必须重新设置所有玩家的游戏模式为冒险模式。
        之前的实现在传送过程中设置了游戏模式，但如果玩家已经在大厅维度（如中途加入的玩家），
        则teleport可能不会真正执行传送，导致后续的游戏模式设置被跳过。

        [DEBUG 2025-11-07]:
        添加详细日志追踪玩家状态重置过程

        参考：StageWaitingState.py:370-403（玩家加入事件中的状态设置）
        """
        system = self.get_system()
        system.LogInfo("[DEBUG] _teleport_all_to_lobby 开始执行")

        # 获取所有在线玩家
        all_players = system.get_all_better_players()
        system.LogInfo("[DEBUG] - 待处理玩家数量: {}".format(len(all_players)))

        for player in all_players:
            try:
                player_id = player.GetPlayerId()

                # 1. 清空背包
                player.clear_inventory()

                # 2. 传送回大厅
                player.teleport(system.waiting_spawn, system.lobby_dimension)

                # 3. 重置游戏模式为冒险模式
                # 注意：必须在这里重新设置，确保从游戏结束状态（旁观模式）恢复到冒险模式
                # [FIX 2025-11-08] 删除GetPlayerGameType调用
                # 原因: PlayerCompServer没有GetPlayerGameType方法，GetPlayerGameType是GameCompLevel的方法
                # 参考: 探索报告02_探索_玩家传送正确实现.md，与老项目保持一致
                comp_player = system.comp_factory.CreatePlayer(player_id)
                MinecraftEnum = serverApi.GetMinecraftEnum()
                comp_player.SetPlayerGameType(MinecraftEnum.GameType.Adventure)
                system.LogInfo("[DEBUG] 玩家 {} 游戏模式已重置为 Adventure".format(player_id))

                # 4. 设置无敌
                comp_hurt = system.comp_factory.CreateHurt(player_id)
                comp_hurt.ImmuneDamage(True)

                # 5. 禁用飞行（防止旁观模式遗留的飞行状态）
                comp_fly = system.comp_factory.CreateFly(player_id)
                comp_fly.ChangePlayerFlyState(False)
                system.LogInfo("[DEBUG] 玩家 {} 飞行已禁用".format(player_id))

                # 注意：大厅道具的发放已移到 _give_lobby_items_to_all_players() 方法中
                # 该方法在 on_enter() 中被调用，使用 serverApi.GetPlayerList() 获取玩家
                # 这样可以避免重复发放道具，并且更加可靠

                system.LogInfo("玩家 {} 已传送回大厅，游戏模式已重置为冒险模式，飞行已禁用".format(player_id))

            except Exception as e:
                system.LogError("传送玩家失败: {}".format(str(e)))

    def _update_coin_display(self):
        """
        更新玩家coin货币显示（顶部HUD）

        功能：
        - 遍历所有等待玩家
        - 获取每个玩家的coin数据（从联机大厅缓存）
        - 向每个玩家发送个性化的coin显示HUD

        参考：
        - 老项目: StageWaitingState.py:238-256 _update_player_hud()
        - 数据来源: RoomManagementSystem.get_player_data(player_id, 'coin')
        - 显示位置: stack_msg_top（屏幕顶部中央）

        修复说明 [FIX 2025-11-07]:
        - 将此方法从StageWaitingPendingState移动到父类StageWaitingState
        - 使其可以在父类的on_enter中被调用，解决对局结束后UI不显示的问题
        """
        system = self.get_system()

        try:
            # 遍历所有等待玩家
            for player_id in system.waiting_players:
                try:
                    # 获取玩家的coin数据（从联机大厅缓存）
                    coin = system.get_player_data(player_id, 'coin', 0)
                    if coin is None:
                        coin = 0

                    # 发送coin显示事件到该玩家
                    # 使用NotifyToClient确保只发送给该玩家（而非广播）
                    system.NotifyToClient(player_id, "HUDControlEvent", {
                        'type': 'stack_msg_top',
                        'events': [
                            {
                                'event': 'add_or_set',
                                'key': 'coins',
                                'value': system.format_text(u'{icon-ec-coin} {coins} ', coins=coin)
                            }
                        ]
                    })

                except Exception as e:
                    system.LogError("更新玩家 {} coin显示失败: {}".format(player_id, str(e)))

        except Exception as e:
            system.LogError("_update_coin_display失败: {}".format(str(e)))

    def _give_lobby_items_to_all_players(self):
        """
        给所有在线玩家发放大厅道具（地图投票道具+个性攻防道具）

        参考：老项目 StageWaitingState.on_player_join():282-292
              player.clear_inventory()
              comp_item.SpawnItemToPlayerInv({"itemName": "ecbedwars:map_vote", "count": 1}, player_id, 1)
              comp_item.SpawnItemToPlayerInv({"itemName": "ecbedwars:personal_workshop", "count": 1}, player_id, 2)

        功能：
        - 清空玩家背包
        - 发放地图投票道具到快捷栏槽位1
        - 发放个性攻防道具到快捷栏槽位2

        [FIX 2025-11-07] 修复问题：
        - 对局结束后，玩家返回等待状态时，需要重新获得道具
        - 之前只在玩家首次加入（on_player_join）时发放道具，导致对局结束后没有道具
        - 现在在StageWaitingState.on_enter()中调用此方法，确保所有玩家都能获得道具

        [FIX 2025-11-07 #2] 使用引擎接口获取在线玩家：
        - 问题：waiting_players在end_game()中被清空，导致无法获取玩家
        - 解决：使用serverApi.GetPlayerList()直接从引擎获取所有在线玩家
        - 原因：不依赖可能被清空的内部列表，使用引擎的权威数据源
        """
        system = self.get_system()

        try:
            # 使用引擎接口获取所有在线玩家（不依赖waiting_players列表）
            all_player_ids = serverApi.GetPlayerList()
            system.LogInfo("[DEBUG] _give_lobby_items_to_all_players: 在线玩家数量={}".format(len(all_player_ids)))

            # 遍历所有在线玩家
            for player_id in all_player_ids:
                try:
                    player_obj = system.get_better_player_obj(player_id)
                    if not player_obj:
                        system.LogWarn("无法获取玩家对象: {}".format(player_id))
                        continue

                    # 1. 清空背包（已在_teleport_all_to_lobby中执行，这里不需要重复）
                    # player_obj.clear_inventory()

                    # 2. 创建物品组件
                    comp_item = system.comp_factory.CreateItem(player_id)

                    # 3. 发放地图投票道具到快捷栏槽位1
                    comp_item.SpawnItemToPlayerInv({
                        "itemName": "ecbedwars:map_vote",
                        "count": 1
                    }, player_id, 1)

                    # 4. 发放个性攻防道具到快捷栏槽位2
                    comp_item.SpawnItemToPlayerInv({
                        "itemName": "ecbedwars:personal_workshop",
                        "count": 1
                    }, player_id, 2)

                    system.LogInfo("已给玩家 {} 发放大厅道具".format(player_id))

                except Exception as e:
                    system.LogError("给玩家 {} 发放道具失败: {}".format(player_id, str(e)))
                    import traceback
                    system.LogError(traceback.format_exc())

        except Exception as e:
            system.LogError("_give_lobby_items_to_all_players失败: {}".format(str(e)))
            import traceback
            system.LogError(traceback.format_exc())

    def on_player_join(self, args):
        """
        处理玩家加入事件（等待状态时）

        Args:
            args: 事件参数 {'player_id': player_id}
        """
        system = self.get_system()
        player_id = args.get('player_id')

        system.LogInfo("[StageWaitingState] 玩家加入: {}".format(player_id))

        # 玩家加入等待列表的逻辑已在RoomManagementSystem.on_player_join中处理
        # 这里需要：1) 广播欢迎消息  2) 给玩家发放大厅道具
        try:
            player_obj = system.get_better_player_obj(player_id)

            # 1. 发送欢迎Title（延迟1秒显示）
            def send_welcome_title():
                if player_obj:
                    player_obj.send_title(
                        system.format_text(u"{bold}»{reset}{white} {} {white}{bold}«",
                                         playing_method_name=system.playing_method_name),
                        "EaseCation"
                    )
            system.add_timer(1.0, send_welcome_title)

            # 2. 广播玩家数量更新
            waiting_count = len(system.waiting_players)
            system.broadcast_message(u"玩家 {} 加入了游戏！({}/{})".format(
                player_id, waiting_count, system.max_players
            ))

            # 3. 清空背包（确保没有残留物品）
            player_obj.clear_inventory()

            # 4. 发放大厅道具
            # 参考：老项目 StageWaitingState.on_player_join():284-292
            comp_item = system.comp_factory.CreateItem(player_id)

            # 地图投票道具到快捷栏槽位1
            comp_item.SpawnItemToPlayerInv({
                "itemName": "ecbedwars:map_vote",
                "count": 1
            }, player_id, 1)

            # 个性攻防道具到快捷栏槽位2
            comp_item.SpawnItemToPlayerInv({
                "itemName": "ecbedwars:personal_workshop",
                "count": 1
            }, player_id, 2)

            system.LogInfo("已给新加入玩家 {} 发放大厅道具".format(player_id))

        except Exception as e:
            system.LogError("[StageWaitingState] 处理玩家加入失败: {}".format(str(e)))
            import traceback
            system.LogError(traceback.format_exc())

    def on_player_leave(self, args):
        """
        处理玩家离开事件（等待状态时）

        Args:
            args: 事件参数 {'player_id': player_id}
        """
        system = self.get_system()
        player_id = args.get('player_id')

        system.LogInfo("[StageWaitingState] 玩家离开: {}".format(player_id))

        # 玩家离开的清理逻辑已在RoomManagementSystem.on_player_leave中处理
        # 这里广播离开消息
        try:
            waiting_count = len(system.waiting_players)
            system.broadcast_message(u"玩家 {} 离开了游戏！({}/{})".format(
                player_id, waiting_count, system.max_players
            ))

        except Exception as e:
            system.LogError("[StageWaitingState] 处理玩家离开失败: {}".format(str(e)))

    def on_add_server_player(self, args):
        """
        处理玩家进入服务器事件（引擎事件）

        此事件在玩家首次连接服务器时触发，早于C2SOnLocalPlayerStopLoading
        需要立即设置玩家的基础状态，防止出现短暂的异常状态

        Args:
            args: 事件参数 {'id': player_id}
        """
        system = self.get_system()
        player_id = args.get('id')

        system.LogInfo("[StageWaitingState] AddServerPlayerEvent: {}".format(player_id))

        try:
            # 立即设置玩家游戏模式为冒险模式（防止放置方块）
            comp_player = system.comp_factory.CreatePlayer(player_id)
            MinecraftEnum = serverApi.GetMinecraftEnum()
            comp_player.SetPlayerGameType(MinecraftEnum.GameType.Adventure)

            # 立即设置无敌状态
            comp_hurt = system.comp_factory.CreateHurt(player_id)
            comp_hurt.ImmuneDamage(True)

            # 禁用飞行
            comp_fly = system.comp_factory.CreateFly(player_id)
            comp_fly.ChangePlayerFlyState(False)

            # 设置玩家重生点为等待大厅出生点
            if hasattr(system, 'waiting_spawn_pos') and system.waiting_spawn_pos:
                spawn_pos = system.waiting_spawn_pos
                spawn_yaw = system.waiting_spawn_yaw if hasattr(system, 'waiting_spawn_yaw') else -90

                # 设置重生点
                comp_player.SetPlayerRespawnPos(spawn_pos, 0)  # 0 = 主维度
                system.LogInfo("玩家 {} 重生点已设置: pos={}, yaw={}".format(
                    player_id, spawn_pos, spawn_yaw))

                # 传送玩家到出生点
                comp_pos = system.comp_factory.CreatePos(player_id)
                comp_pos.SetPos(spawn_pos)
                comp_rot = system.comp_factory.CreateRot(player_id)
                comp_rot.SetRot((0, spawn_yaw))  # (pitch, yaw)

                system.LogInfo("玩家 {} 已传送到等待大厅出生点".format(player_id))
            else:
                system.LogWarn("等待大厅出生点未配置，无法传送玩家 {}".format(player_id))

            system.LogInfo("玩家 {} 已设置基础状态(冒险模式、无敌、禁飞、重生点)".format(player_id))

        except Exception as e:
            system.LogError("处理AddServerPlayerEvent失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def on_player_use_item_on_block(self, args):
        """
        处理玩家使用物品事件

        用于响应地图投票和装扮更换道具的使用

        Args:
            args: 事件参数
        """
        system = self.get_system()

        # 统一参数键名
        args['playerId'] = args.get('entityId')
        player_id = args.get('playerId')

        if not player_id:
            return

        try:
            player_obj = system.get_better_player_obj(player_id)
            if not player_obj:
                return

            # 只在大厅维度处理
            if player_obj.GetDimensionId() != system.lobby_dimension:
                return

            item_dict = args.get('itemDict', {})
            item_name = item_dict.get('itemName', '')

            if item_name == 'ecbedwars:map_vote':
                # 检查地图投票实例是否存在
                if hasattr(system, 'map_vote') and system.map_vote is not None:
                    try:
                        system.NotifyToClient(player_id, "OpenMapVote", system.map_vote.to_ui_dict())
                        system.LogInfo("向玩家 {} 发送地图投票UI".format(player_id))
                    except Exception as e:
                        system.LogError("发送地图投票UI失败: {}".format(str(e)))
                else:
                    system.LogWarn("地图投票实例不存在")

            elif item_name == 'ecbedwars:personal_workshop':
                # 打开装扮商店
                # 修复说明: OrnamentSystem不是预设,无法通过broadcast_preset_event接收事件
                # 需要直接调用ornament_system.open_ornament_shop()方法
                # 参考老项目: StageWaitingState.py:347使用BroadcastPresetSystemEvent触发
                # 新项目架构: RoomManagementSystem -> BedWarsGameSystem -> OrnamentSystem

                # [FIX 2025-11-06] 延迟获取BedWarsGameSystem引用
                # 原因: RoomManagementSystem.Create()时BedWarsGameSystem还未注册
                # 解决: 使用时再获取引用,而不是依赖Create时的引用
                if not system.bedwars_game_system:
                    system._initialize_bedwars_game_system_reference()

                if system.bedwars_game_system and system.bedwars_game_system.ornament_system:
                    system.bedwars_game_system.ornament_system.open_ornament_shop(player_id)
                    system.LogInfo("打开装扮商店: player={}".format(player_id))
                else:
                    system.LogWarn("OrnamentSystem未初始化,无法打开装扮商店")

        except Exception as e:
            system.LogError("处理物品使用事件失败: {}".format(str(e)))

    def on_farm_block_to_dirt(self, args):
        """
        处理耕地变成泥土的事件

        在等待区域禁止耕地退化，保持地图美观

        Args:
            args: 事件参数
        """
        if args.get("blockName") in ("minecraft:farmland",):
            args["cancel"] = True

    def get_system(self):
        """
        获取RoomManagementSystem实例

        Returns:
            RoomManagementSystem: 系统实例
        """
        return self.parent.get_system()


class StageWaitingPendingState(GamingState):
    """
    等待状态 - pending子状态
    等待玩家加入
    """

    def __init__(self, parent):
        GamingState.__init__(self, parent)
        self.with_enter(self.on_enter)
        self.with_tick(self.on_tick)

        # HUD更新计时器
        self.next_hud_update = 0

    def on_enter(self):
        """进入pending状态"""
        system = self.get_system()
        system.LogInfo("StageWaitingPendingState.on_enter")

        # 向所有玩家发送提示
        waiting_count = len(system.waiting_players)
        start_players = system.start_players
        system.broadcast_message(
            u"等待玩家加入... ({}/{})".format(waiting_count, start_players)
        )

        # 立即更新HUD
        self._update_hud()

    def on_tick(self):
        """每帧更新 - 定期更新HUD信息"""
        current_time = time.time()

        # 每1秒更新一次HUD
        if current_time >= self.next_hud_update:
            self.next_hud_update = current_time + 1.0
            self._update_hud()

    def _update_hud(self):
        """更新HUD显示"""
        system = self.get_system()

        try:
            # 获取当前信息
            waiting_count = len(system.waiting_players)
            max_players = system.max_players
            playing_method_name = system.playing_method_name

            # 更新底部消息堆叠
            # 使用format_text格式化图标和颜色代码（与老项目保持一致）
            events = [
                {
                    'event': 'add_or_set',
                    'key': 'stage_info',
                    'value': system.format_text(u'{icon-ec-ball} {game} ', game=playing_method_name)
                },
                {
                    'event': 'add_or_set',
                    'key': 'player_count',
                    'value': system.format_text(u'{icon-ec-players} 人数 {count}/{max} ', count=waiting_count, max=max_players)
                },
                {
                    'event': 'add_or_set',
                    'key': 'countdown',
                    'value': system.format_text(u'{icon-ec-time} 等待中 ')
                }
            ]

            # 广播HUD事件
            system.broadcast_hud_event('stack_msg_bottom', events)

            # 更新顶部coin货币显示（参考老项目实现）
            # 原理：通过RoomManagementSystem.get_player_data()获取联机大厅的coin数据
            # 参考：老项目StageWaitingState.py line 211-256
            # [FIX 2025-11-07] 通过parent调用父状态的方法
            self.parent._update_coin_display()

        except Exception as e:
            system.LogError("_update_hud失败: {}".format(str(e)))

    # [FIX 2025-11-07] _update_coin_display方法已移至父类StageWaitingState
    # 子类通过继承直接使用父类的实现

    def get_system(self):
        """获取系统实例"""
        return self.parent.parent.get_system()


class StageWaitingCountdownState(TimedGamingState):
    """
    等待状态 - countdown子状态
    倒计时阶段
    """

    def __init__(self, parent):
        """
        初始化倒计时状态

        Args:
            parent: 父状态
        """
        # 获取倒计时时长
        system = parent.parent.get_system()
        countdown_time = system.countdown_time

        # 初始化定时状态
        TimedGamingState.__init__(self, parent, countdown_time)

        # 注册钩子
        self.with_enter(self.on_enter)
        self.with_tick(self.on_tick)
        self.with_time_out(self.on_timeout)

        # HUD更新计时器
        self.next_hud_update = 0
        self.last_second = -1

        # 倒计时完成标志
        self.countdown_finished = False

        # 维度切换动画发送标志
        self.sent_pre_change_dimension = False

    def on_enter(self):
        """进入倒计时状态"""
        system = self.get_system()
        system.LogInfo("StageWaitingCountdownState.on_enter")

        # 向所有玩家发送提示
        system.broadcast_message(u"游戏即将开始!")

        # 立即更新HUD
        self._update_hud()

    def on_tick(self):
        """每帧更新"""
        system = self.get_system()
        current_time = time.time()

        # 获取剩余秒数
        seconds_left = int(self.get_seconds_left())

        # 每秒更新一次HUD（当秒数变化时）
        if seconds_left != self.last_second:
            self.last_second = seconds_left
            self._update_hud()

            # 关键时间点播报
            if seconds_left in [10, 5, 4, 3, 2, 1]:
                system.broadcast_message(u"游戏将在 {} 秒后开始".format(seconds_left))

            # 显示Title提示（倒计时<=12秒时）
            if seconds_left <= 12:
                self._send_countdown_title(seconds_left)

            # 播放提示音
            self._play_countdown_sound(seconds_left)

        # 倒计时结束时发送维度切换动画
        if seconds_left <= 0 and not self.countdown_finished:
            self.countdown_finished = True

            # 发送预开始动画
            if not self.sent_pre_change_dimension:
                self.sent_pre_change_dimension = True
                self._send_dimension_change_animation()

    def _send_countdown_title(self, seconds_left):
        """
        发送倒计时Title提示

        Args:
            seconds_left (int): 剩余秒数
        """
        system = self.get_system()

        try:
            # 格式化title文本
            tip_text = system.format_text(
                u"{yellow}游戏将在 {bold}{gold}{sec}秒{reset}{yellow} 后开始",
                sec=str(seconds_left)
            )

            # 为每个等待玩家发送title
            for player_id in system.waiting_players:
                player_obj = system.get_better_player_obj(player_id)
                player_obj.send_title(".", tip_text, fadein=0, duration=30, fadeout=10)

        except Exception as e:
            system.LogError("发送倒计时Title失败: {}".format(str(e)))

    def _play_countdown_sound(self, seconds_left):
        """
        播放倒计时音效

        老项目逻辑：
        - sec > 8: 播放2个音符（1, 5）
        - sec <= 8: 播放3个音符（1, 5, 8）
        - sec <= 4: 播放4个音符（1, 5, 8, 13）
        - sec <= 0: 播放结束音（13, 17, 20, 25）

        Args:
            seconds_left (int): 剩余秒数
        """
        system = self.get_system()

        try:
            # 确定音高（note.pling音效） - 完全还原老项目逻辑
            pitch = None

            if seconds_left <= 0:
                pitch = [13, 17, 20, 25]  # 结束音
            elif seconds_left <= 4:
                pitch = [1, 5, 8, 13]     # 急促音（1-4秒）
            elif seconds_left <= 8:
                pitch = [1, 5, 8]         # 提示音（5-8秒）
            else:
                pitch = [1, 5]            # 预警音（9秒及以上）

            # 播放音效
            if pitch:
                for player_id in system.waiting_players:
                    player_obj = system.get_better_player_obj(player_id)
                    player_pos = player_obj.get_position()
                    player_obj.play_note_pling_sound(player_pos, pitch)

        except Exception as e:
            system.LogError("播放倒计时音效失败: {}".format(str(e)))

    def _send_dimension_change_animation(self):
        """发送维度切换动画事件"""
        system = self.get_system()

        try:
            # 广播维度切换预开始动画事件
            # 这会触发ChangeDimensionAnim系统播放加载动画
            system.broadcast_preset_event("ChangeDimensionAnimPreStart", {})
            system.LogInfo("维度切换动画事件已发送")

        except Exception as e:
            system.LogError("发送维度切换动画失败: {}".format(str(e)))

    def _update_hud(self):
        """更新HUD显示"""
        system = self.get_system()

        try:
            # 获取当前信息
            waiting_count = len(system.waiting_players)
            max_players = system.max_players
            playing_method_name = system.playing_method_name
            seconds_left = int(self.get_seconds_left())

            # 更新底部消息堆叠（与老项目保持一致）
            events = [
                {
                    'event': 'add_or_set',
                    'key': 'stage_info',
                    'value': system.format_text(u'{icon-ec-ball} {game} ', game=playing_method_name)
                },
                {
                    'event': 'add_or_set',
                    'key': 'player_count',
                    'value': system.format_text(u'{icon-ec-players} 人数 {count}/{max} ', count=waiting_count, max=max_players)
                },
                {
                    'event': 'add_or_set',
                    'key': 'countdown',
                    'value': system.format_text(u'{icon-ec-time} {sec} ', sec=seconds_left)
                }
            ]

            # 广播HUD事件
            system.broadcast_hud_event('stack_msg_bottom', events)

            # 更新顶部coin货币显示（与pending状态保持一致）
            # 参考：老项目StageWaitingState.py line 211-256
            # [FIX 2025-11-07] 通过parent调用父状态的方法
            self.parent._update_coin_display()

        except Exception as e:
            system.LogError("_update_hud失败: {}".format(str(e)))

    # [FIX 2025-11-07] _update_coin_display方法已移至父类StageWaitingState
    # 子类通过parent.方法名()调用父状态的实现

    def on_timeout(self, timed_state):
        """倒计时结束

        Args:
            timed_state: TimedGamingState实例
        """
        system = self.get_system()
        system.LogInfo("倒计时结束,切换到游戏进行状态")

        # 清除HUD
        try:
            system.clear_stack_msg_bottom()
        except Exception as e:
            system.LogError("清除HUD失败: {}".format(str(e)))

        # 切换到下一个状态(running)
        # 注意: 必须调用root_state的next_sub_state()来切换主状态
        # TimedGamingState._time_out()中的parent.next_sub_state()只会切换子状态
        root_state = system.root_state
        if root_state:
            root_state.next_sub_state()
        else:
            system.LogError("root_state不存在,无法切换状态")

    def get_system(self):
        """获取系统实例"""
        return self.parent.parent.get_system()
