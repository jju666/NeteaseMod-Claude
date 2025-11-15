# -*- coding: utf-8 -*-
"""
StageBroadcastScoreState - 房间结算广播状态

功能:
- 传送玩家到结算区
- 异步加载结算区区块
- 生成NPC展示获胜者（前3名）
- 生成浮空字显示玩家名称和排名
- 打开结算UI显示详细数据
- 播放结算音效和动画
- 等待一段时间后返回大厅

原文件: Parts/ECStage/state/StageBroadcastScoreState.py
重构为: systems/room_states/StageBroadcastScoreState.py
"""

import mod.server.extraServerApi as serverApi
from Script_NeteaseMod.systems.state.TimedGamingState import TimedGamingState

# 获取引擎组件工厂
ServerCompFactory = serverApi.GetEngineCompFactory()


class StageBroadcastScoreState(TimedGamingState):
    """
    房间结算广播状态（带NPC展示）

    核心职责:
    - 传送玩家到结算区（维度0）
    - 异步加载结算区区块
    - 生成NPC展示获胜者（使用ecbedwars:broadcast_score_npc实体）
    - 生成浮空字显示玩家名称和排名
    - 打开结算UI显示详细统计数据
    - 定时后自动返回等待状态
    """

    def __init__(self, parent):
        """
        初始化结算广播状态

        Args:
            parent: 父状态
        """
        # 结算展示时长: 15秒
        TimedGamingState.__init__(self, parent, 15.0)

        # 结算数据
        self.broadcast_score_data = None  # 从RoomManagementSystem获取

        # 生成的实体ID列表（用于清理）
        self.spawned_entities = []

        # NPC加载标志
        self.npcs_spawned = False

        # [FIX 2025-11-08] 维度切换跟踪
        # 用于等待所有玩家完成维度切换后再加载区块生成NPC
        self.waiting_for_dimension_change = set()  # 等待维度切换完成的玩家ID集合
        self.dimension_change_completed = False     # 是否已完成维度切换并加载区块

        # 注册钩子
        self.with_enter(self.on_enter)
        self.with_tick(self.on_tick)
        self.with_time_out(self.on_timeout)
        self.with_exit(self.on_exit)

    def on_enter(self):
        """
        进入结算广播状态

        流程:
        1. 获取结算数据
        2. 传送所有玩家到结算区
        3. 禁止液体流动
        4. 【延迟1秒】等待玩家传送完成
        5. 异步加载结算区区块
        6. 加载完成后生成NPC和打开UI
        """
        system = self.get_system()
        system.LogInfo("StageBroadcastScoreState.on_enter")

        # 1. 获取结算数据（从RoomManagementSystem临时变量）
        if hasattr(system, 'tmp_broadcast_score_data'):
            self.broadcast_score_data = system.tmp_broadcast_score_data
        else:
            system.LogWarn("缺少结算数据 tmp_broadcast_score_data")
            self.broadcast_score_data = {'scores': []}

        # 2. [FIX 2025-11-08] 初始化等待维度切换的玩家列表
        # 传送是异步的,需要等待DimensionChangeFinishServerEvent才能确认玩家到达
        self.waiting_for_dimension_change = set(system.get_all_players())
        self.dimension_change_completed = False

        system.LogInfo("[DEBUG] 等待 {} 个玩家完成维度切换: {}".format(
            len(self.waiting_for_dimension_change),
            list(self.waiting_for_dimension_change)
        ))

        # 3. 传送所有玩家到结算区
        self._teleport_all_players()

        # 4. 禁止液体流动（避免水影响展示）
        self._forbid_liquid_flow(True)

        # 5. [FIX 2025-11-08] 不再立即加载区块
        # 改为等待on_player_dimension_change_finish事件通知
        # 当所有玩家都完成维度切换后,才会调用_load_broadcast_area_chunks()
        system.LogInfo("已传送所有玩家,等待维度切换完成事件...")
        system.LogInfo("结算广播状态已初始化")

    def on_tick(self):
        """每帧更新"""
        system = self.get_system()

        # 获取剩余秒数
        seconds_left = int(self.get_seconds_left())

        # 定期提示返回时间
        if seconds_left in [10, 5, 3]:
            system.broadcast_message(
                u"将在 {} 秒后返回大厅".format(seconds_left)
            )

    def on_timeout(self, timed_state):
        """结算展示超时,返回等待状态

        Args:
            timed_state: TimedGamingState实例
        """
        system = self.get_system()
        system.LogInfo("结算展示结束,返回等待状态")

        # 切换到下一个状态(waiting,因为状态机设置了loop)
        root_state = system.root_state
        if root_state:
            root_state.next_sub_state()
        else:
            system.LogError("root_state不存在,无法切换状态")

    def on_exit(self):
        """
        退出结算广播状态

        清理工作:
        1. 清理生成的NPC实体
        2. 恢复液体流动
        3. 清理结算数据
        """
        system = self.get_system()
        system.LogInfo("StageBroadcastScoreState.on_exit")

        # 1. 清理所有生成的实体
        self._cleanup_entities()

        # 2. 恢复液体流动
        self._forbid_liquid_flow(False)

        # 3. 清理结算数据
        self.broadcast_score_data = None
        self.npcs_spawned = False
        self.waiting_for_dimension_change.clear()

    def on_player_dimension_change_finish(self, player_id, from_dim, to_dim, to_pos):
        """
        处理玩家维度切换完成事件

        [FIX 2025-11-08] 等待所有玩家完成维度切换后再加载区块生成NPC
        这样确保NPC在正确的维度生成,玩家能看到

        Args:
            player_id: 玩家ID
            from_dim: 切换前维度
            to_dim: 切换后维度
            to_pos: 切换后位置
        """
        system = self.get_system()

        # 检查是否是我们等待的玩家
        if player_id not in self.waiting_for_dimension_change:
            return

        # 检查是否到达了目标维度(维度0-结算区)
        if to_dim != 0:
            system.LogWarn("[DEBUG] 玩家 {} 到达了错误的维度: {} (期望: 0)".format(player_id, to_dim))
            return

        # 标记该玩家已完成维度切换
        self.waiting_for_dimension_change.discard(player_id)

        system.LogInfo("[DEBUG] 玩家 {} 维度切换完成, 剩余等待: {}".format(
            player_id,
            len(self.waiting_for_dimension_change)
        ))

        # 如果所有玩家都完成了维度切换,加载区块生成NPC
        if len(self.waiting_for_dimension_change) == 0 and not self.dimension_change_completed:
            self.dimension_change_completed = True
            system.LogInfo("[DEBUG] 所有玩家维度切换完成,开始加载结算区区块")

            try:
                self._load_broadcast_area_chunks()
            except Exception as e:
                system.LogError("加载结算区区块失败: {}".format(str(e)))
                import traceback
                system.LogError(traceback.format_exc())

    def _teleport_all_players(self):
        """传送所有玩家到结算区"""
        system = self.get_system()

        try:
            # 获取结算区出生点配置（从RoomManagementSystem）
            if not hasattr(system, 'broadcast_score_spawn'):
                system.LogWarn("缺少broadcast_score_spawn配置，使用默认位置")
                spawn_pos = (0, 100, 0)
            else:
                # [FIX 2025-11-08] RoomManagementSystem已将配置转为tuple
                # 参考: RoomManagementSystem.py:1177-1181
                spawn_pos = system.broadcast_score_spawn
                system.LogInfo("[DEBUG] 结算区传送坐标: {}".format(spawn_pos))

            # 传送所有玩家到维度0（大厅）
            for player_id in system.get_all_players():
                player_obj = system.get_better_player_obj(player_id)

                # [FIX 2025-11-07] 使用teleport方法而不是ChangeDimension
                # BetterPlayerObject的teleport方法签名: teleport(pos, dim_id=None, rot=None)
                system.LogInfo("[DEBUG] 传送玩家 {} 到结算区: pos={}, dim=0".format(player_id, spawn_pos))
                player_obj.teleport(spawn_pos, dim_id=0)
                system.LogInfo("[DEBUG] 玩家 {} 传送完成".format(player_id))

                # [FIX 2025-11-07] 设置为冒险模式，与老项目保持一致
                # 参考: 老项目 StageBroadcastScoreState.py:52
                # 原因: 分数展示阶段应该使用冒险模式，而非观察者模式
                #       观察者模式会导致玩家无法正常交互
                comp_player = ServerCompFactory.CreatePlayer(player_id)
                MinecraftEnum = serverApi.GetMinecraftEnum()
                comp_player.SetPlayerGameType(MinecraftEnum.GameType.Adventure)

                # 开启伤害免疫
                comp_hurt = ServerCompFactory.CreateHurt(player_id)
                comp_hurt.ImmuneDamage(True)

                # 禁用飞行（与老项目保持一致）
                comp_fly = ServerCompFactory.CreateFly(player_id)
                comp_fly.ChangePlayerFlyState(False)

            system.LogInfo("所有玩家已传送到结算区")

        except Exception as e:
            system.LogError("传送玩家到结算区失败: {}".format(str(e)))

    def _forbid_liquid_flow(self, forbid):
        """
        禁止/允许液体流动

        Args:
            forbid (bool): True=禁止流动, False=允许流动
        """
        system = self.get_system()

        try:
            level_id = serverApi.GetLevelId()
            comp_game = ServerCompFactory.CreateGame(level_id)
            comp_game.ForbidLiquidFlow(forbid)

            action = u"禁止" if forbid else u"允许"
            system.LogInfo("液体流动已{}".format(action))

        except Exception as e:
            system.LogError("设置液体流动失败: {}".format(str(e)))

    def _load_broadcast_area_chunks(self):
        """异步加载结算区区块"""
        system = self.get_system()

        try:
            # 获取结算区出生点
            if not hasattr(system, 'broadcast_score_spawn'):
                system.LogWarn("缺少broadcast_score_spawn配置，跳过区块加载")
                # 直接生成NPC
                self._on_broadcast_area_loaded(None)
                return

            spawn_pos = system.broadcast_score_spawn

            # 计算加载范围（出生点±32格）
            min_pos = (spawn_pos[0] - 32, spawn_pos[1] - 16, spawn_pos[2] - 32)
            max_pos = (spawn_pos[0] + 32, spawn_pos[1] + 16, spawn_pos[2] + 32)

            system.LogInfo("开始异步加载结算区区块 range=({}, {})".format(min_pos, max_pos))

            # 异步加载区块
            level_id = serverApi.GetLevelId()
            comp_chunk = ServerCompFactory.CreateChunkSource(level_id)

            comp_chunk.DoTaskOnChunkAsync(
                0,  # 维度0（大厅）
                min_pos,
                max_pos,
                self._on_broadcast_area_loaded
            )

        except Exception as e:
            system.LogError("异步加载结算区区块失败: {}".format(str(e)))
            # 降级处理：直接生成NPC
            self._on_broadcast_area_loaded(None)

    def _on_broadcast_area_loaded(self, data):
        """
        结算区区块加载完成回调

        Args:
            data: 回调数据
        """
        system = self.get_system()
        system.LogInfo("结算区区块加载完成,延迟2.5秒后生成NPC(等待客户端UI初始化)")

        # [FIX 2025-11-08 #12] 延迟2.5秒后再生成NPC和发送UI
        # 根本原因:
        # - 服务端检测到玩家维度切换完成后立即生成NPC/浮空字/发送UI
        # - 但客户端此时还在进行维度切换,UI系统正在重新初始化
        # - 日志显示: 实体创建成功后,客户端才检测到维度切换(ChangeDimensionClientSystem)
        # - 客户端会重新初始化所有UI系统(HUDSystem, ChangeDimensionScreenNode等)
        # - 在客户端初始化完成前创建的实体和发送的UI事件会被忽略或丢失
        #
        # 解决方案:
        # - 添加2.5秒延迟,等待客户端完全完成维度切换和UI初始化
        # - 延迟后再生成NPC、浮空字,并发送结算UI
        #
        # 参考日志时序(D:\EcWork\NetEaseMapECBedWars\日志.log lines -107 to -34):
        # -107: [7:09:16] NPC创建成功
        # -106: [7:09:16] 浮空字实体创建成功
        # -105: [7:09:16] [ChangeDimensionClientSystem] 检测到维度切换 ❌ 客户端此时才开始切换!
        # ...中间是UI初始化日志...
        # -34: [7:09:17] [HUDSystem] UI初始化完成 ✅ 1秒后客户端才准备好
        try:
            comp_factory = serverApi.GetEngineCompFactory()
            game_comp = comp_factory.CreateGame(serverApi.GetLevelId())

            def delayed_spawn():
                """延迟生成NPC和发送UI的回调"""
                try:
                    system.LogInfo("[DEBUG] 客户端应已完成UI初始化,开始生成NPC和发送UI")

                    # 1. 生成NPC展示获胜者
                    self._spawn_score_npcs()

                    # 2. 打开结算UI
                    self._open_game_end_ui()

                    system.LogInfo("[DEBUG] 延迟生成NPC和UI完成")
                except Exception as e:
                    system.LogError("延迟生成NPC和UI失败: {}".format(str(e)))
                    import traceback
                    system.LogError(traceback.format_exc())

            # 延迟2.5秒(50 ticks, 每tick=0.05秒)
            game_comp.AddTimer(2.5, delayed_spawn)
            system.LogInfo("已添加延迟Timer,2.5秒后生成NPC和发送UI")
        except Exception as e:
            system.LogError("添加延迟Timer失败: {}".format(str(e)))
            import traceback
            system.LogError(traceback.format_exc())
            # 降级处理:立即生成(可能不显示)
            self._spawn_score_npcs()
            self._open_game_end_ui()

    def _spawn_score_npcs(self):
        """
        生成结算NPC

        流程:
        1. 根据scores数据确定前3名玩家
        2. 在对应位置生成NPC实体
        3. 设置NPC皮肤为对应玩家
        4. 设置NPC动画（第1名/第2名/第3名不同）
        5. 生成浮空字显示玩家名称和排名
        """
        system = self.get_system()

        try:
            if not self.broadcast_score_data or not self.broadcast_score_data.get('scores'):
                system.LogWarn("缺少结算数据，无法生成NPC")
                return

            scores = self.broadcast_score_data['scores']

            # 获取NPC位置配置
            if not hasattr(system, 'broadcast_score_npc_positions'):
                system.LogWarn("缺少broadcast_score_npc_positions配置，无法生成NPC")
                return

            npc_positions = system.broadcast_score_npc_positions

            # 生成前3名的NPC（或更少，如果玩家不足3人）
            max_npcs = min(len(scores), len(npc_positions))

            for i in range(max_npcs):
                score_entry = scores[i]
                npc_pos_config = npc_positions[i]

                # 转换pos字典为tuple
                pos_data = npc_pos_config['pos']
                if isinstance(pos_data, dict):
                    pos = (pos_data.get('x', 0), pos_data.get('y', 100), pos_data.get('z', 0))
                else:
                    pos = tuple(pos_data)
                yaw = npc_pos_config.get('yaw', 0)

                # [FIX 2025-11-08] 使用BedWarsGameSystem.CreateEngineEntityByTypeStr创建实体
                # 参考: BedWarsGameSystem.py:2386, EntityPresetServerBase.py:115
                # 原因: CreateEngineEntityByTypeStr是BedWarsGameSystem的方法，不是EngineCompFactory的方法
                # 正确调用链: system.bedwars_game_system.CreateEngineEntityByTypeStr()
                if not hasattr(system, 'bedwars_game_system') or system.bedwars_game_system is None:
                    system.LogError("BedWarsGameSystem未初始化，无法创建NPC")
                    continue

                npc_id = system.bedwars_game_system.CreateEngineEntityByTypeStr(
                    "ecbedwars:broadcast_score_npc",  # 实体类型
                    tuple(pos),                         # 位置
                    (0, yaw),                           # 旋转(pitch, yaw)
                    0                                   # 维度0（大厅）
                )

                if npc_id:
                    self.spawned_entities.append(npc_id)

                    # [FIX 2025-11-08] 获取EngineCompFactory来创建组件
                    comp_factory = serverApi.GetEngineCompFactory()

                    # [FIX 2025-11-07 #7] 使用CreateEntityDefinitions设置variant
                    # 参考: MemeOrnamentSystem.py:183, 老项目StageBroadcastScoreState.py:81
                    comp_def = comp_factory.CreateEntityDefinitions(npc_id)
                    if comp_def:
                        comp_def.SetVariant(i + 1)

                    # [FIX 2025-11-08] 广播NPC皮肤设置事件到所有客户端
                    # 参考: 老项目StageBroadcastScoreState.py:83
                    # 原因: 使用BroadcastToAllClient而非NotifyToClient,确保所有玩家都能看到NPC皮肤
                    #       如果只发送给score_entry['player_id'],其他玩家看不到皮肤
                    system.BroadcastToAllClient(
                        "ScoreBoardNPCSkin",
                        {
                            "entity_id": npc_id,
                            "skin_player": score_entry['player_id'],
                            "texture_key": "rank{}".format(i + 1)
                        }
                    )

                    # [FIX 2025-11-07 #7] 设置NPC动画（通过mark_variant）
                    # 参考: 老项目StageBroadcastScoreState.py:88-96
                    # 第1名=3, 第2名=2, 第3名=4
                    if i == 0:
                        mark_variant = 3  # 第一名动画
                    elif i == 1:
                        mark_variant = 2  # 第二名动画
                    elif i == 2:
                        mark_variant = 4  # 第三名动画
                    else:
                        mark_variant = 1  # 默认动画

                    if comp_def:
                        comp_def.SetMarkVariant(mark_variant)

                    # 生成浮空字实体显示玩家名称和排名
                    self._spawn_floating_text(pos, score_entry, i)

                    system.LogInfo("已生成结算NPC #{} player={}".format(i + 1, score_entry['player_name']))

            self.npcs_spawned = True
            system.LogInfo("结算NPC生成完成，共{}个".format(max_npcs))

        except Exception as e:
            system.LogError("生成结算NPC失败: {}".format(str(e)))

    def _spawn_floating_text(self, base_pos, score_entry, rank_index):
        """
        生成浮空字实体

        Args:
            base_pos (tuple): NPC基础位置
            score_entry (dict): 玩家分数数据
            rank_index (int): 排名索引（0=第1名）
        """
        system = self.get_system()

        try:
            # 浮空字位置（在NPC下方1格）
            floating_pos = (base_pos[0], base_pos[1] - 1, base_pos[2])

            # [FIX 2025-11-08] 使用BedWarsGameSystem.CreateEngineEntityByTypeStr创建浮空字实体
            # 参考: BedWarsGameSystem.py:2386, EntityPresetServerBase.py:115
            # 原因: CreateEngineEntityByTypeStr是BedWarsGameSystem的方法，不是EngineCompFactory的方法
            # 正确调用链: system.bedwars_game_system.CreateEngineEntityByTypeStr()
            if not hasattr(system, 'bedwars_game_system') or system.bedwars_game_system is None:
                system.LogError("BedWarsGameSystem未初始化，无法创建浮空字")
                return

            floating_id = system.bedwars_game_system.CreateEngineEntityByTypeStr(
                "ecbedwars:entity",  # 浮空字实体(老项目使用ecbedwars:entity而不是entity_1)
                tuple(floating_pos),
                (0, 0),
                0      # 维度0
            )

            if floating_id:
                self.spawned_entities.append(floating_id)

                # [FIX 2025-11-08] 格式化排名文本 - 100%还原老项目颜色
                # 参考: 老项目StageBroadcastScoreState.py:105-112
                # 第1名=黄色(yellow), 第2名=灰色(gray), 第3名=金色(gold)
                if rank_index == 0:
                    rank_text = system.format_text(u"{yellow}第1名")
                elif rank_index == 1:
                    rank_text = system.format_text(u"{gray}第2名")
                elif rank_index == 2:
                    rank_text = system.format_text(u"{gold}第3名")
                else:
                    rank_text = system.format_text(u"{gray}第{n}名", n=str(rank_index + 1))

                # 设置实体名称（显示为浮空字）
                # 参考: 老项目StageBroadcastScoreState.py:113-117
                comp_name = ServerCompFactory.CreateName(floating_id)

                if not comp_name:
                    system.LogError("创建NameComponent失败: floating_id={}".format(floating_id))
                    return

                display_text = system.format_text(
                    u" » {bold}{white}{name}{reset} «\n{rank}",
                    name=score_entry['player_name'],
                    rank=rank_text
                )

                # [FIX 2025-11-10] 使用str()转换字符串，解决SetName失败问题
                # 参考: 网易MODSDK Wiki > SDK实用技巧 > 踩坑总结 第3点
                # 原因: format_text返回的字符串类型可能不是纯str，导致SetName返回False
                # 解决方案: 使用str()强制转换为纯字符串类型
                success = comp_name.SetName(str(display_text))

                if success:
                    system.LogInfo("浮空字名字设置成功: entity_id={}, player={}".format(
                        floating_id, score_entry['player_name']
                    ))
                else:
                    system.LogWarn("浮空字名字设置失败(SetName返回False): entity_id={}".format(floating_id))

                system.LogInfo("已生成浮空字 player={}".format(score_entry['player_name']))

        except Exception as e:
            system.LogError("生成浮空字失败: {}".format(str(e)))

    def _open_game_end_ui(self):
        """
        打开游戏结算UI

        向每个玩家发送OpenGameEnd事件，显示详细统计数据
        """
        system = self.get_system()

        try:
            if not self.broadcast_score_data or not self.broadcast_score_data.get('scores'):
                system.LogWarn("缺少结算数据，无法打开UI")
                return

            scores = self.broadcast_score_data['scores']

            for score_entry in scores:
                player_id = score_entry['player_id']
                rank = scores.index(score_entry) + 1

                # [DEBUG] 打印score_entry内容
                system.LogInfo("[DEBUG] score_entry = {}".format(score_entry))

                # 格式化统计数据显示文本
                score_text = system.format_text(
                    u"{icon-ec-sword0} {kill}  {icon-ec-sword2} {final_kill}  {icon-ec-crystal-destroy} {bed_destroy}",
                    kill=score_entry.get('kills', 0),
                    final_kill=score_entry.get('final_kills', 0),
                    bed_destroy=score_entry.get('destroys', 0)
                )

                # 格式化奖励文本
                coin_delta = score_entry.get('coin', 0)
                coin_text = ("+{}".format(coin_delta)) if coin_delta >= 0 else str(coin_delta)

                # 格式化左侧文本（奖励类型），需要format_text转换图标
                left_text = system.format_text(u"{icon-ec-coin} 起床战争硬币")

                # 发送客户端事件打开UI
                system.NotifyToClient(player_id, "OpenGameEnd", {
                    "rank": rank,
                    "score": score_text,
                    "left_text": left_text,
                    "left_delta": coin_text
                })

            system.LogInfo("游戏结算UI已发送给所有玩家")

        except Exception as e:
            system.LogError("打开游戏结算UI失败: {}".format(str(e)))

    def _cleanup_entities(self):
        """清理所有生成的实体（NPC和浮空字）"""
        system = self.get_system()

        try:
            # [FIX 2025-11-07 #8] 直接调用system.DestroyEntity方法
            # 参考: BedWarsGameSystem.DestroyEntity, MemeOrnamentSystem._destroy_meme_entity
            for entity_id in self.spawned_entities:
                try:
                    system.DestroyEntity(entity_id)
                except Exception as e:
                    system.LogWarn("清理实体{}失败: {}".format(entity_id, str(e)))

            system.LogInfo("已清理{}个结算实体".format(len(self.spawned_entities)))
            self.spawned_entities = []

        except Exception as e:
            system.LogError("清理结算实体失败: {}".format(str(e)))

    def get_system(self):
        """
        获取RoomManagementSystem实例

        Returns:
            RoomManagementSystem: 系统实例
        """
        return self.parent.get_system()
