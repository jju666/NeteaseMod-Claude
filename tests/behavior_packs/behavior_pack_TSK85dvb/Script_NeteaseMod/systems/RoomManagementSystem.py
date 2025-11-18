# -*- coding: utf-8 -*-
"""
RoomManagementSystem - 房间管理系统(服务端)

功能:
- 管理游戏房间全生命周期
- 地图投票、玩家管理
- 大厅管理、状态机循环
- 队伍分配和管理

原文件: Parts/ECStage/ECStagePart.py
重构为: systems/RoomManagementSystem.py
"""

import mod.server.extraServerApi as serverApi
from .GamingStateSystem import GamingStateSystem
from ..modConfig import MOD_NAME, SERVER_SYSTEMS, CLIENT_SYSTEMS


class RoomManagementSystem(GamingStateSystem):
    """
    房间管理系统(ServerSystem + 状态机)

    核心职责:
    - 继承GamingStateSystem,获得状态机能力
    - 管理房间状态(等待 → 游戏进行 → 结算 → 循环)
    - 管理玩家分配、队伍管理
    - 协调BedWarsGameSystem游戏逻辑

    重构说明:
    - 原ECStagePart继承自GamingStatePart + PartBase
    - 现改为继承GamingStateSystem
    - 简化地图备份/还原逻辑(初期版本)
    """

    def __init__(self, namespace, systemName):
        """
        初始化房间管理系统

        Args:
            namespace: 命名空间
            systemName: 系统名称
        """
        # ========== 重要: 先初始化所有实例属性,再调用父类__init__ ==========
        # 因为父类GamingStateSystem.__init__会调用self.Create(),
        # 而Create()中会访问这些属性,所以必须先初始化

        # ========== 配置加载器 ==========
        self.config_loader = None  # RoomConfigLoader实例

        # ========== 房间配置 ==========
        self.playing_method_name = "EC起床战争"
        self.max_players = 16  # 最大玩家数
        self.start_players = 2  # 最少开始人数
        self.countdown_time = 10  # 倒计时秒数
        self.waiting_spawn = (0, 100, 0)  # 大厅出生点
        self.waiting_spawn_yaw = 0  # 大厅出生点朝向
        self.broadcast_score_spawn = (0, 100, 20)  # 结算出生点
        self.broadcast_score_spawn_yaw = 0  # 结算出生点朝向
        self.broadcast_score_npc_positions = []  # 结算NPC位置列表

        # ========== 地图配置 ==========
        self.stages = []  # 地图配置列表
        self.current_stage_config = None  # 当前选中的地图
        self._maps_in_use = set()  # 正在使用中的地图ID集合
        self.restoring_maps = set()  # 正在还原中的地图ID集合
        self.map_backup_handlers = {}  # dimension_id -> DimensionBackupHandler

        # ========== 玩家管理 ==========
        self.cached_uid = {}  # player_id -> uid
        self.waiting_players = []  # 等待中的玩家列表
        self.playing_players = []  # 游戏中的玩家列表
        self._pending_rotations = {}  # player_id -> rotation (待设置的朝向信息)

        # ===== [P0-1 FIX] 玩家数据缓存系统 =====
        self.cached_player_data = {}  # uid -> {coin: int, kills: int, ...}
        self.cached_player_data_delta = {}  # uid -> {coin: delta, ...} (增量数据)
        self.pending_cache_players = set()  # 缓存中的玩家UID

        # ========== 队伍管理 ==========
        self.team_module = None  # TeamModule实例
        self.available_teams = ['RED', 'BLUE', 'GREEN', 'YELLOW']  # 可用队伍列表
        self.team_players = {}  # team_id -> [player_id, ...]

        # ========== 大厅配置 ==========
        self.lobby_dimension = 0  # 大厅维度ID

        # ========== 跨系统引用 ==========
        self.bedwars_game_system = None  # BedWarsGameSystem实例引用
        self.preset_manager = None  # PresetManager实例引用

        # ========== 游戏状态 ==========
        self.is_game_running = False  # 游戏是否正在进行
        self.current_dimension = None  # 当前游戏维度
        self.current_preset_instances = []  # 当前游戏的预设实例ID列表
        self.lobby_preset_instances = []  # 大厅预设实例ID列表

        # ========== 地图投票 ==========
        self.map_vote = None  # MapVoteInstance实例

        # ========== 调用父类__init__ ==========
        super(RoomManagementSystem, self).__init__(namespace, systemName)

        # ========== 注册C2S事件监听 ==========
        # 重要: 在__init__中注册,参考ServerFormServerSystem.py line 78
        # 注意: GamingStateSystem.__init__不再调用Create(),所以可以安全地在这里注册事件
        self._register_c2s_events()

        # ========== 重要：手动调用Create() ==========
        # 说明：网易引擎设计上只自动触发Destroy()，不自动触发Create()
        # 因此需要在__init__中手动调用Create()完成系统初始化
        self.LogInfo("[RoomManagementSystem] 手动调用Create()完成系统初始化")
        self.Create()

    # ========== ServerSystem生命周期 ==========

    def Create(self):
        """系统创建时调用"""
        self.LogInfo("RoomManagementSystem.Create")

        # 调用父类Create(GamingStateSystem)
        super(RoomManagementSystem, self).Create()

        # 注册引擎事件监听
        self._register_engine_events()

        # 获取BedWarsGameSystem引用
        self._initialize_bedwars_game_system_reference()

        # 初始化配置加载器
        self._initialize_config_loader()

        # 从JSON加载房间配置
        self._load_room_config_from_json()

        # 初始化PresetManager
        self._initialize_preset_manager()

        # 初始化大厅预设
        self._initialize_lobby_presets()

        # 初始化房间状态机
        self._initialize_room_state_machine()

        # 初始化队伍模块
        self._initialize_team_module()

        # 检测已在线的玩家并添加到等待列表
        self._add_existing_players_to_waiting_list()

        # 应用游戏规则（设置白天、禁止怪物生成等）
        # 注意：在大厅维度(lobby_dimension)应用游戏规则，确保玩家一进入就看到正确的环境
        self.LogInfo("开始应用游戏规则到大厅维度 {}".format(self.lobby_dimension))
        self.apply_game_rules(self.lobby_dimension)

        # 启动状态机
        if self.root_state:
            self.root_state.start()
            self.LogInfo("房间状态机已启动")

    def Destroy(self):
        """系统销毁时调用"""
        self.LogInfo("RoomManagementSystem.Destroy")

        # 清理队伍模块
        if self.team_module:
            self.team_module.cleanup()
            self.team_module = None

        # 调用父类Destroy
        super(RoomManagementSystem, self).Destroy()

    def Update(self):
        """系统每帧更新"""
        # 调用父类Update(驱动状态机)
        super(RoomManagementSystem, self).Update()

        # 更新房间逻辑
        self._update_room_logic()

    # ========== 游戏控制接口 ==========

    def start_game(self):
        """
        启动游戏(由状态机调用)

        执行步骤:
        1. 选择地图(使用投票系统)
        2. 加载并创建地图预设
        3. 分配队伍
        4. 传送玩家到游戏地图
        5. 启动BedWarsGameSystem
        6. 初始化地图备份管理器
        """
        self.LogInfo("start_game")

        # 1. 选择地图(使用投票系统)
        if not self.stages:
            self.LogError("start_game: 没有可用地图")
            return

        # 创建地图投票实例(如果不存在)
        if not self.map_vote:
            self.create_map_vote()

        # 通过投票选择地图
        selected_map_id = self.map_vote.find_most_voted()
        if not selected_map_id:
            self.LogError("start_game: 投票系统未选出地图")
            return

        # 查找对应的地图配置
        self.current_stage_config = None
        for stage in self.stages:
            if stage.get("id") == selected_map_id:
                self.current_stage_config = stage
                break

        if not self.current_stage_config:
            self.LogError("start_game: 找不到地图配置 map_id={}".format(selected_map_id))
            return

        dimension = self.current_stage_config.get("map_dimension")
        mode = self.current_stage_config.get("mode", "team2")

        self.LogInfo("选择地图: map_id={}, dimension={}, mode={}".format(
            selected_map_id, dimension, mode
        ))

        # 将地图标记为使用中
        self._maps_in_use.add(selected_map_id)

        # 重要: 在创建预设之前设置current_dimension
        # 因为预设在on_start时会从RoomManagementSystem.current_dimension获取维度ID
        self.current_dimension = dimension
        self.is_game_running = True
        self.LogInfo("已设置current_dimension={} (在创建预设之前)".format(dimension))

        # 2. 加载并创建地图预设
        self._load_and_create_presets(dimension)

        # 3. 分配队伍
        self._assign_teams(mode)

        # 4. 触发维度切换动画（先播放淡入动画，延迟后再传送）
        # 关键修复（2025-11-04）：添加动画触发调用
        # 老项目通过PresetSystemEvent触发，新项目通过System事件触发
        self.LogInfo("触发维度切换动画")
        self.BroadcastToAllClient("StartChangeDimension", {})

        # 4.5. 延迟0.8秒后传送玩家（给淡入动画时间播放）
        # 时间计算：
        # - 淡入动画：0.5秒（Alpha 0→1）
        # - 缓冲时间：0.3秒（确保动画完成且遮罩稳定）
        # - 总延迟：0.8秒
        def delayed_teleport():
            self._teleport_players_to_game(dimension)
            # 应用游戏规则
            self.apply_game_rules(dimension)

        # 使用定时器延迟执行
        self.add_timer(0.8, delayed_teleport, False)

        # 5. 启动BedWarsGameSystem
        # 确保bedwars_game_system引用存在（延迟初始化）
        if not self.bedwars_game_system:
            self._initialize_bedwars_game_system_reference()

        if self.bedwars_game_system:
            self.bedwars_game_system.start_game_directly(
                dimension, mode, self.current_stage_config
            )
            # 注意: is_game_running 和 current_dimension 已经在创建预设之前设置
        else:
            self.LogError("bedwars_game_system引用未初始化（即使延迟初始化也失败）")

        # 6. 初始化地图备份管理器并开始记录方块变更
        backup_handler = self.get_backup_handler(dimension)
        load_range = self.get_map_backup_range(selected_map_id)
        if load_range:
            backup_handler.restore_and_start_record(load_range, is_record=True)
            self.LogInfo("地图备份管理器已初始化 dimension={} range={}".format(
                dimension, load_range
            ))

    def end_game(self, winning_team):
        """
        结束游戏(由BedWarsGameSystem调用)

        执行步骤:
        1. 清理地图预设
        2. 传送所有玩家回大厅
        3. 清空队伍分配
        4. 触发地图还原
        5. 还原完成后更新地图状态
        6. [FIX 2025-11-07] 推进状态机到下一个状态（StageBroadcastScore或回到Waiting）

        Args:
            winning_team (str): 获胜队伍ID
        """
        self.LogInfo("end_game winning_team={}".format(winning_team))

        self.is_game_running = False

        # 记录当前地图信息
        current_map_id = None
        current_dimension = None
        if self.current_stage_config:
            current_map_id = self.current_stage_config.get("id")
            current_dimension = self.current_stage_config.get("map_dimension")

        # 清理地图预设
        self._destroy_all_presets()

        # [FIX 2025-11-08] 注释掉传送到大厅的逻辑
        # 由StageBroadcastScoreState负责传送玩家到结算区
        # 等结算展示结束后,StageWaitingState会传送玩家回大厅
        # self._teleport_all_players_to_lobby()
        self.LogInfo("[FIX] 跳过传送到大厅,等待结算状态处理")

        # 清空队伍分配
        self.team_players = {}

        # 重置玩家列表
        self.playing_players = []

        # 触发地图还原
        if current_map_id and current_dimension is not None:
            self.LogInfo("开始还原地图 map_id={} dimension={}".format(
                current_map_id, current_dimension
            ))

            # 将地图从使用中移除,添加到还原中
            if current_map_id in self._maps_in_use:
                self._maps_in_use.remove(current_map_id)
            self.restoring_maps.add(current_map_id)

            # 获取备份管理器并开始还原
            backup_handler = self.get_backup_handler(current_dimension)

            def on_restore_complete():
                """地图还原完成回调"""
                self.LogInfo("地图还原完成 map_id={} dimension={}".format(
                    current_map_id, current_dimension
                ))

                # 从还原列表移除
                if current_map_id in self.restoring_maps:
                    self.restoring_maps.remove(current_map_id)

                # 刷新地图投票列表
                if self.map_vote:
                    self.map_vote.refresh_available_maps()
                    self.LogInfo("地图投票列表已刷新")

            # 执行还原
            backup_handler.restore(on_restore_complete)
        else:
            self.LogWarn("end_game: 无法还原地图,缺少地图信息")

        # [FIX 2025-11-07] 在清理完成后切换到broadcast_score状态
        # 新的游戏结束流程:
        # 1. BedWarsGameSystem触发BedWarsGameEnd事件
        # 2. BedWarsGameSystem进入BedWarsEndingState(10秒胜利展示)
        # 3. BedWarsEndingState结束后调用_notify_game_end_to_room()
        # 4. _notify_game_end_to_room()调用本方法end_game()
        # 5. end_game()完成清理后,调用root_state.next_sub_state()切换到broadcast_score
        # 6. broadcast_score状态15秒后切换到waiting(循环)
        #
        # 解决方案：
        # - 移除end_game()内部的next_sub_state()调用
        # - 由调用者（StageRunningState.on_game_end()等）负责推进状态机
        # - 保持职责单一：end_game()只负责清理，不负责状态切换
        #
        # 注意：
        # - 调用者会确保正确推进状态机
        # - StageRunningState.on_game_end() 第163行: root_state.next_sub_state()
        # - StageRunningState.on_timeout() 第138行: root_state.next_sub_state()

        # [已移除] 不再在end_game()中推进状态机
        # if self.root_state and self.root_state.current_sub_state:
        #     self.LogInfo("[end_game] 推进状态机到下一个状态")
        #     self.root_state.next_sub_state()

        self.LogInfo("[end_game] 清理完成，等待调用者推进状态机")

    # ========== HUD事件转发 ==========

    def forward_hud_event(self, player_id, event_data):
        """
        转发HUD事件到客户端

        说明:
        - 由BedWarsGameSystem调用,用于发送HUD更新事件
        - 统一由RoomManagementSystem发送HUD事件,客户端HUDSystem只监听此System
        - 这样可以避免客户端监听多个System

        Args:
            player_id (str|None): 指定玩家ID,如果为None则广播给所有玩家
            event_data (dict): HUD事件数据,包含type和events等字段
        """
        try:
            if player_id:
                self.NotifyToClient(player_id, 'HUDControlEvent', event_data)
            else:
                self.BroadcastToAllClient('HUDControlEvent', event_data)
        except Exception as e:
            self.LogError("转发HUD事件失败: {}".format(str(e)))

    # ========== 玩家管理 ==========

    def get_player_uid(self, player_id):
        """
        获取玩家UID

        Args:
            player_id: 玩家ID

        Returns:
            str: 玩家UID,如果获取失败返回None
        """
        if player_id in self.cached_uid:
            return self.cached_uid[player_id]

        try:
            comp_factory = serverApi.GetEngineCompFactory()
            http_comp = comp_factory.CreateHttp(serverApi.GetLevelId())
            uid = http_comp.GetPlayerUid(player_id)

            if uid:
                self.cached_uid[player_id] = uid
                return uid
        except Exception as e:
            self.LogError(u"[get_player_uid] 获取玩家{}的UID失败: {}".format(player_id, str(e)))

        return None

    def on_player_join(self, player_id):
        """
        玩家加入房间 - 完整初始化流程

        Args:
            player_id (str): 玩家ID
        """
        self.LogInfo("on_player_join player_id={}".format(player_id))

        # ===== [P0-1 FIX] 开始缓存玩家数据 =====
        self.start_player_cache(player_id)

        # 添加到等待列表
        if player_id not in self.waiting_players:
            self.waiting_players.append(player_id)

        # 完整的玩家初始化(参考老起床)
        try:
            player_obj = self.get_better_player_obj(player_id)

            # 1. 清空背包
            player_obj.clear_inventory()

            # 2. 传送到大厅（包含朝向）
            rot = (0, self.waiting_spawn_yaw)  # (pitch, yaw)
            player_obj.teleport(self.waiting_spawn, self.lobby_dimension, rot)

            # 3. 设置游戏模式为冒险模式
            comp_player = self.comp_factory.CreatePlayer(player_id)
            comp_player.SetPlayerGameType(serverApi.GetMinecraftEnum().GameType.Adventure)

            # 4. 设置无敌
            comp_hurt = self.comp_factory.CreateHurt(player_id)
            comp_hurt.ImmuneDamage(True)

            # 5. 设置饥饿值不掉落
            # 方法：设置饥饿值为满，并设置最大消耗度为很大的值，使饥饿度几乎不下降
            comp_player.SetPlayerHunger(20.0)  # 设置饥饿度为满值（20 = 10个鸡腿）
            comp_player.SetPlayerMaxExhaustionValue(9999.0)  # 设置很大的最大消耗度，使饥饿度几乎不下降
            self.LogInfo("玩家 {} 饥饿值已设置为满，并禁止下降".format(player_id))

            # 6. 发放大厅道具
            comp_item = self.comp_factory.CreateItem(player_id)

            # 地图投票道具（槽位1）
            comp_item.SpawnItemToPlayerInv({
                "itemName": "ecbedwars:map_vote",
                "count": 1
            }, player_id, 1)

            # 装扮更换道具（槽位2）
            comp_item.SpawnItemToPlayerInv({
                "itemName": "ecbedwars:personal_workshop",
                "count": 1
            }, player_id, 2)

            self.LogInfo("玩家 {} 已初始化完成(传送、清空背包、冒险模式、无敌、道具发放)".format(player_id))

        except Exception as e:
            self.LogError("玩家 {} 初始化失败: {}".format(player_id, str(e)))
            import traceback
            traceback.print_exc()

        # 发送欢迎消息和title
        player_obj = self.get_better_player_obj(player_id)
        player_obj.send_message("欢迎来到{}!".format(self.playing_method_name))

        # 延迟1秒后发送欢迎title，格式与老项目完全一致
        # 老项目格式: {bold}»{reset}{white} {game} {white}{bold}«
        # 实际效果: §l»§r§f 游戏名 §f§l«
        def send_welcome_title():
            self.LogInfo("[DEBUG] 准备发送欢迎title给玩家: {}".format(player_id))
            # 正确的格式: §l»§r§f (粗体», 重置, 白色) + 游戏名 + §f§l« (白色, 粗体«)
            title_text = u"\u00a7l\u00bb\u00a7r\u00a7f {} \u00a7f\u00a7l\u00ab".format(self.playing_method_name)
            self.LogInfo("[DEBUG] title文本: {}".format(title_text))
            try:
                player_obj.send_title(title_text, u"EaseCation", fadein=10, duration=40, fadeout=10)
                self.LogInfo("[DEBUG] 欢迎title发送成功")
            except Exception as e:
                self.LogError("[DEBUG] 发送title失败: {}".format(e))
                import traceback
                traceback.print_exc()

        self.LogInfo("[DEBUG] 设置1秒延时timer发送欢迎title")
        self.add_timer(1.0, send_welcome_title)

        # 发送玩家加入事件到当前状态
        if self.root_state and self.root_state.current_sub_state:
            self.root_state.current_sub_state.notify_event("ServerPlayerJoinEvent", {
                'player_id': player_id
            })
            self.LogInfo("已发送ServerPlayerJoinEvent到状态机")

    def on_player_leave(self, player_id):
        """
        玩家离开房间

        Args:
            player_id (str): 玩家ID
        """
        self.LogInfo("on_player_leave player_id={}".format(player_id))

        # ===== [P0-1 FIX] 保存并清理玩家缓存 =====
        self.save_player_data(player_id)
        self.cleanup_player_cache(player_id)

        # 从等待列表移除
        if player_id in self.waiting_players:
            self.waiting_players.remove(player_id)

        # 从游戏列表移除
        if player_id in self.playing_players:
            self.playing_players.remove(player_id)

        # 从队伍中移除
        for team_id, players in self.team_players.items():
            if player_id in players:
                players.remove(player_id)
                break

        # 发送玩家离开事件到当前状态
        if self.root_state and self.root_state.current_sub_state:
            self.root_state.current_sub_state.notify_event("ServerPlayerLeaveEvent", {
                'player_id': player_id
            })
            self.LogInfo("已发送ServerPlayerLeaveEvent到状态机")

    # ===== [P0-1 FIX] 玩家数据缓存方法 =====

    def start_player_cache(self, player_id):
        """
        开始缓存玩家数据

        通过联机大厅API获取玩家的持久化数据（金币、击杀数、统计等）

        Args:
            player_id: 玩家ID
        """
        uid = self.get_player_uid(player_id)
        if uid is None:
            self.LogWarn(u"[start_player_cache] 无法获取玩家{}的UID".format(player_id))
            return

        # 标记玩家正在缓存中
        self.pending_cache_players.add(uid)

        # 初始化缓存字典
        if uid not in self.cached_player_data:
            self.cached_player_data[uid] = {}

        # 创建HTTP组件
        comp_factory = serverApi.GetEngineCompFactory()
        http_comp = comp_factory.CreateHttp(serverApi.GetLevelId())

        # 定义数据加载回调
        def on_load_callback(data):
            """
            大厅API数据加载回调

            Args:
                data: API返回数据 {
                    'entity': {
                        'data': [
                            {'key': 'coin', 'value': 100},
                            {'key': 'kills', 'value': 50},
                            ...
                        ]
                    }
                }
            """
            try:
                if data and 'entity' in data and 'data' in data['entity']:
                    # 解析返回的数据
                    for entry in data['entity']['data']:
                        key = entry.get('key')
                        value = entry.get('value')
                        if key:
                            self.cached_player_data[uid][key] = value

                    self.LogInfo(u"[start_player_cache] 玩家{}数据加载成功: {}".format(
                        player_id, self.cached_player_data[uid]
                    ))
                else:
                    self.LogWarn(u"[start_player_cache] 玩家{}数据加载失败，返回空数据".format(player_id))

                # 标记缓存完成（成功或失败都要移除pending标记）
                self.pending_cache_players.discard(uid)

            except Exception as e:
                self.LogError(u"[start_player_cache] 处理玩家{}数据回调失败: {}".format(
                    player_id, str(e)
                ))
                # 即使异常也要标记缓存完成，避免无限等待
                self.pending_cache_players.discard(uid)

        # 定义需要加载的数据键
        # 参考老项目ECBedWarsOrnamentPart.py line 69
        data_keys = ['coin']  # 基础数据：金币

        # 调用大厅API获取玩家数据
        try:
            http_comp.LobbyGetStorage(on_load_callback, uid, data_keys)
            self.LogInfo(u"[start_player_cache] 已发送HTTP请求加载玩家{}数据 (UID: {}, keys: {})".format(
                player_id, uid, data_keys
            ))
        except Exception as e:
            self.LogError(u"[start_player_cache] 发送HTTP请求失败: {}".format(str(e)))
            # 如果HTTP请求失败，也要标记缓存完成，避免无限等待
            self.pending_cache_players.discard(uid)

    def get_player_data(self, player_id, key, default=None):
        """
        获取玩家数据

        Args:
            player_id: 玩家ID
            key: 数据键名 (如 'coin', 'kills')
            default: 默认值

        Returns:
            玩家数据值,如果不存在返回default
        """
        uid = self.get_player_uid(player_id)
        if uid and uid in self.cached_player_data:
            return self.cached_player_data[uid].get(key, default)
        return default

    def set_player_data(self, player_id, key, value, force=False):
        """
        设置玩家数据（支持增量更新和强制更新两种模式）

        Args:
            player_id: 玩家ID
            key: 数据键名
            value: 数据值
            force: 是否强制更新（True=直接设置值，False=计算增量）
        """
        uid = self.get_player_uid(player_id)
        if not uid:
            return

        # 确保缓存字典存在
        if uid not in self.cached_player_data:
            self.cached_player_data[uid] = {}

        # 获取原始值
        origin = self.cached_player_data[uid].get(key, 0)

        # 如果值没有变化，直接返回
        if origin == value:
            return

        if force:
            # 强制模式：直接设置缓存的数值，最终上报也会直接上报缓存的数值
            self.cached_player_data[uid][key] = value
        else:
            # 增量模式：计算delta，最终上报的是原始数据+delta
            delta = value - origin
            # 这边不会再将数据写入cached_player_data，因为最终都按照原始数据+delta的形式上报
            if uid not in self.cached_player_data_delta:
                self.cached_player_data_delta[uid] = {}
            if key not in self.cached_player_data_delta[uid]:
                self.cached_player_data_delta[uid][key] = 0
            self.cached_player_data_delta[uid][key] += delta

        self.LogDebug(u"[set_player_data] 玩家{}设置数据: {}={} (force={})".format(
            player_id, key, value, force
        ))

    def add_player_data(self, player_id, key, add):
        """
        增加玩家的数据（便捷方法）

        Args:
            player_id: 玩家ID
            key: 数据的键
            add: 增加的数值
        """
        uid = self.get_player_uid(player_id)
        if not uid:
            return

        origin = self.cached_player_data.get(uid, {}).get(key, 0)
        new_value = origin + add
        self.set_player_data(player_id, key, new_value)

    def cleanup_player_cache(self, player_id):
        """
        清理玩家缓存

        Args:
            player_id: 玩家ID
        """
        uid = self.get_player_uid(player_id)
        if uid is None:
            return

        self.pending_cache_players.discard(uid)
        self.cached_player_data.pop(uid, None)
        self.cached_uid.pop(player_id, None)

        self.LogInfo(u"[cleanup_player_cache] 已清理玩家{}的缓存 (UID: {})".format(
            player_id, uid
        ))

    def save_player_data(self, player_id):
        """
        保存玩家数据到联机大厅

        使用增量更新机制，只上传变更的数据，避免数据冲突

        Args:
            player_id: 玩家ID
        """
        uid = self.get_player_uid(player_id)
        if not uid or uid not in self.cached_player_data:
            self.LogWarn(u"[save_player_data] 玩家{}没有缓存数据，跳过保存".format(player_id))
            return

        player_data = self.cached_player_data[uid]
        player_delta = self.cached_player_data_delta.get(uid, {})

        # 如果没有增量数据，不需要保存
        if not player_delta:
            self.LogInfo(u"[save_player_data] 玩家{}没有数据变更，跳过保存".format(player_id))
            return

        # 创建HTTP组件
        comp_factory = serverApi.GetEngineCompFactory()
        http_comp = comp_factory.CreateHttp(serverApi.GetLevelId())

        # 定义数据保存回调
        def on_save_callback(result):
            """
            大厅API数据保存回调

            Args:
                result: API返回结果 {
                    'code': int,  # 0=成功, 2=数据冲突, 其他=失败
                    'message': str,
                    'entity': {
                        'data': [...]  # 最新的服务器数据
                    }
                }
            """
            try:
                if result is None:
                    self.LogError(u"[save_player_data] 玩家{}数据保存失败：返回None".format(player_id))
                    return

                code = result.get('code', -1)
                message = result.get('message', 'Unknown')

                if code == 0:
                    # 保存成功
                    self.LogInfo(u"[save_player_data] 玩家{}数据保存成功 code={} message={}".format(
                        player_id, code, message
                    ))

                    # 清空delta（保存成功后重置增量）
                    if uid in self.cached_player_data_delta:
                        for key in player_delta.keys():
                            self.cached_player_data_delta[uid][key] = 0

                elif code == 2:
                    # 数据冲突，需要重新同步
                    self.LogWarn(u"[save_player_data] 数据冲突，重新同步玩家{}数据 code={} message={}".format(
                        player_id, code, message
                    ))
                else:
                    # 其他错误
                    self.LogError(u"[save_player_data] 玩家{}数据保存失败 code={} message={}".format(
                        player_id, code, message
                    ))

                # 无论成功还是失败，始终刷新本地缓存（使用服务器返回的最新数据）
                if 'entity' in result and 'data' in result['entity']:
                    for entry in result['entity']['data']:
                        key = entry.get('key')
                        value = entry.get('value')
                        if key:
                            self.cached_player_data[uid][key] = value

            except Exception as e:
                self.LogError(u"[save_player_data] 处理玩家{}保存回调失败: {}".format(
                    player_id, str(e)
                ))

        # 定义数据获取器（返回增量更新后的最终值）
        def entities_getter():
            """
            获取要保存的数据列表（原始数据 + 增量）

            Returns:
                list: [{'key': str, 'value': int}, ...]
            """
            result = []
            # 遍历所有有增量的键
            for key, delta in player_delta.items():
                if delta != 0:  # 只保存有变更的数据
                    origin_value = player_data.get(key, 0)
                    final_value = origin_value + delta
                    result.append({
                        'key': key,
                        'value': final_value
                    })
            return result

        # 调用大厅API保存玩家数据
        try:
            http_comp.LobbySetStorageAndUserItem(
                callback=on_save_callback,
                uid=uid,
                entitiesGetter=entities_getter
            )
            self.LogInfo(u"[save_player_data] 已发送HTTP请求保存玩家{}数据 (UID: {})".format(
                player_id, uid
            ))
        except Exception as e:
            self.LogError(u"[save_player_data] 发送HTTP保存请求失败: {}".format(str(e)))

    # ========== 状态机初始化 ==========

    def _initialize_room_state_machine(self):
        """初始化房间状态机"""
        if not self.root_state:
            self.LogError("root_state未初始化,无法配置房间状态机")
            return

        # 导入状态类
        from room_states.StageWaitingState import StageWaitingState
        from room_states.StageRunningState import StageRunningState
        from room_states.StageBroadcastScoreState import StageBroadcastScoreState

        # 设置状态机循环
        self.root_state.set_loop()

        # 添加子状态（顺序很重要：waiting -> running -> broadcast_score -> loop）
        # [FIX 2025-11-07] 移除ending状态,BedWarsEndingState由BedWarsGameSystem管理
        # 游戏结束流程: running收到BedWarsGameEnd事件 -> 触发BedWarsGameSystem.ending -> 直接切换到broadcast_score
        self.root_state.add_sub_state("waiting", StageWaitingState)
        self.root_state.add_sub_state("running", StageRunningState)
        self.root_state.add_sub_state("broadcast_score", StageBroadcastScoreState)

        # 注意: 不在这里调用next_sub_state(),
        # 状态机将在root_state.start()时自动进入第一个状态

        self.LogInfo("房间状态机初始化完成: waiting -> running -> broadcast_score -> (loop)")

    # ========== 队伍管理 ==========

    def _initialize_team_module(self):
        """初始化队伍模块"""
        from team.TeamModule import TeamModule
        self.team_module = TeamModule(self)
        self.LogInfo("队伍模块初始化完成")

    def _assign_teams(self, mode):
        """
        分配队伍

        Args:
            mode (str): 游戏模式 (team2/team4)
        """
        self.LogInfo("_assign_teams mode={}".format(mode))

        # 确定队伍数量
        team_count = 2 if mode == "team2" else 4
        teams = self.available_teams[:team_count]

        # 清空队伍分配
        self.team_players = {team: [] for team in teams}

        # 将等待玩家分配到队伍
        players = list(self.waiting_players)
        for i, player_id in enumerate(players):
            team_id = teams[i % team_count]
            self.team_players[team_id].append(player_id)
            self.playing_players.append(player_id)

        # 从等待列表移除
        self.waiting_players = []

        # 记录分配结果
        for team_id, player_list in self.team_players.items():
            self.LogInfo("队伍{}: {} 名玩家".format(team_id, len(player_list)))

    def get_player_team(self, player_id):
        """
        获取玩家所在队伍

        Args:
            player_id (str): 玩家ID

        Returns:
            str: 队伍ID,如果没有则返回None
        """
        for team_id, players in self.team_players.items():
            if player_id in players:
                return team_id
        return None

    def get_team_players(self, team_id):
        """
        获取队伍中的玩家列表

        Args:
            team_id (str): 队伍ID

        Returns:
            list: 玩家ID列表
        """
        return self.team_players.get(team_id, [])

    # ========== 传送管理 ==========

    def _teleport_player_to_lobby(self, player_id):
        """
        传送玩家到大厅并重置状态

        [FIX 2025-11-07] 添加完整的玩家状态重置：
        - 设置游戏模式为冒险模式
        - 禁用飞行（清除旁观模式遗留状态）
        - 开启伤害免疫
        - 清空背包
        - 传送回大厅

        Args:
            player_id (str): 玩家ID
        """
        try:
            player_obj = self.get_better_player_obj(player_id)

            # 1. 重置游戏模式为冒险模式
            comp_player = self.comp_factory.CreatePlayer(player_id)
            MinecraftEnum = serverApi.GetMinecraftEnum()
            comp_player.SetPlayerGameType(MinecraftEnum.GameType.Adventure)

            # 2. 禁用飞行（防止旁观模式遗留的飞行状态）
            comp_fly = self.comp_factory.CreateFly(player_id)
            comp_fly.ChangePlayerFlyState(False)

            # 3. 开启伤害免疫
            comp_hurt = self.comp_factory.CreateHurt(player_id)
            comp_hurt.ImmuneDamage(True)

            # 4. 清空背包
            player_obj.clear_inventory()

            # 5. 传送回大厅
            rot = (0, self.waiting_spawn_yaw)  # (pitch, yaw)
            player_obj.teleport(
                self.waiting_spawn,
                self.lobby_dimension,
                rot
            )

            self.LogInfo("玩家 {} 已传送回大厅并重置状态（冒险模式、飞行已禁用）".format(player_id))

        except Exception as e:
            self.LogError("传送玩家{}回大厅失败: {}".format(player_id, str(e)))
            import traceback
            self.LogError(traceback.format_exc())

    def _teleport_all_players_to_lobby(self):
        """传送所有玩家回大厅"""
        for player_id in self.playing_players:
            self._teleport_player_to_lobby(player_id)

    def _teleport_players_to_game(self, dimension):
        """
        传送玩家到游戏地图

        从ECPreset的spawn预设中收集队伍出生点信息并传送玩家

        Args:
            dimension (int): 游戏维度ID
        """
        # 从ECPreset的spawn预设中收集队伍出生点
        teams_spawns = self._find_team_spawns()

        if not teams_spawns:
            self.LogError("未找到任何队伍出生点预设")
            return

        for team_id, players in self.team_players.items():
            # 获取队伍出生点列表
            if team_id not in teams_spawns:
                self.LogError("队伍{}没有出生点配置".format(team_id))
                continue

            spawns = teams_spawns[team_id]
            if not spawns:
                self.LogError("队伍{}的出生点列表为空".format(team_id))
                continue

            # 传送队伍所有玩家（循环使用出生点）
            for index, player_id in enumerate(players):
                try:
                    # 使用模运算循环使用出生点
                    spawn = spawns[index % len(spawns)]
                    spawn_pos = spawn[0]  # (x, y, z)
                    spawn_rot = spawn[1]  # (pitch, yaw)

                    player_obj = self.get_better_player_obj(player_id)
                    player_obj.teleport(spawn_pos, dimension, spawn_rot)
                    player_obj.send_message(u"你被分配到{}队!".format(team_id))

                    self.LogInfo("玩家 {} 传送到队伍 {} 出生点: pos={}, rot={}".format(
                        player_id, team_id, spawn_pos, spawn_rot
                    ))
                except Exception as e:
                    self.LogError("传送玩家 {} 失败: {}".format(player_id, str(e)))
                    import traceback
                    traceback.print_exc()

    def _find_team_spawns(self):
        """
        从ECPreset的spawn预设中收集队伍出生点信息

        Returns:
            dict: {team_id: [(pos, rot), ...]}
        """
        try:
            from ECPresetServerScripts import get_server_mgr

            context_id = "bedwars_room"
            preset_mgr = get_server_mgr(context_id)

            if not preset_mgr:
                self.LogError("预设管理器未找到: {}".format(context_id))
                return {}

            teams_spawns = {}

            # 遍历所有预设实例
            # ECPreset框架的PresetInstance结构：instance.preset_def 是 PresetDefinition对象
            all_presets = preset_mgr.get_all_presets()
            for instance_id, instance in all_presets.items():
                # 检查预设类型（通过instance.preset_type字符串）
                if instance.preset_type != "bedwars:spawn":
                    continue

                # 通过 instance.preset_def 获取预设定义对象
                preset_def = instance.preset_def
                if not preset_def:
                    continue

                # 从预设定义对象获取队伍ID和位置信息
                team = getattr(preset_def, 'team', None)
                spawn_position = getattr(preset_def, 'spawn_position', None)
                spawn_rotation = getattr(preset_def, 'spawn_rotation', None)

                if not team:
                    self.LogWarn("spawn预设缺少team: instance_id={}".format(instance_id))
                    continue

                if not spawn_position:
                    self.LogWarn("spawn预设缺少spawn_position: instance_id={}".format(instance_id))
                    continue

                # 默认朝向
                if not spawn_rotation:
                    spawn_rotation = (0, 0)

                # 添加到队伍出生点列表
                if team not in teams_spawns:
                    teams_spawns[team] = []

                teams_spawns[team].append((spawn_position, spawn_rotation))

                self.LogInfo("收集spawn预设: team={}, pos={}, rot={}".format(
                    team, spawn_position, spawn_rotation
                ))

            self.LogInfo("收集到 {} 个队伍的出生点: {}".format(
                len(teams_spawns),
                {k: len(v) for k, v in teams_spawns.items()}
            ))

            return teams_spawns

        except Exception as e:
            self.LogError("收集队伍出生点失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()
            return {}

    # ========== 系统引用初始化 ==========

    def _initialize_bedwars_game_system_reference(self):
        """获取BedWarsGameSystem引用"""
        try:
            self.bedwars_game_system = serverApi.GetSystem(self.namespace, "BedWarsGameSystem")
            if self.bedwars_game_system:
                self.LogInfo("BedWarsGameSystem引用获取成功")
            else:
                self.LogWarn("BedWarsGameSystem未找到")
        except Exception as e:
            self.LogError("获取BedWarsGameSystem引用失败: {}".format(str(e)))

    # ========== 配置加载 ==========

    def _initialize_config_loader(self):
        """初始化配置加载器 - 使用Python模块导入,避免文件系统路径问题"""
        from util.RoomConfigLoader import RoomConfigLoader

        # 直接创建配置加载器,不需要传入路径
        # 配置加载器会使用Python的import机制加载config模块
        self.config_loader = RoomConfigLoader()
        self.LogInfo("配置加载器初始化完成 (使用Python配置模块)")

    def _load_room_config_from_json(self):
        """从JSON加载房间配置"""
        if not self.config_loader:
            self.LogError("配置加载器未初始化")
            return

        # 加载房间设置
        room_config = self.config_loader.load_room_settings()

        # 应用配置
        self.playing_method_name = room_config.get('room_name', u"EC起床战争")
        self.max_players = room_config.get('max_players', 16)
        self.start_players = room_config.get('start_players', 2)
        self.countdown_time = room_config.get('countdown_time', 10)
        self.lobby_dimension = room_config.get('lobby_dimension', 0)

        # 加载出生点配置
        waiting_spawn_data = room_config.get('waiting_spawn', {})
        self.LogInfo("[DEBUG] 配置中的waiting_spawn数据: {}".format(waiting_spawn_data))
        self.waiting_spawn = (
            waiting_spawn_data.get('x', 0),
            waiting_spawn_data.get('y', 100),
            waiting_spawn_data.get('z', 0)
        )
        self.waiting_spawn_yaw = room_config.get('waiting_spawn_yaw', 0)
        self.LogInfo("[DEBUG] 加载后的waiting_spawn: {}, yaw: {}".format(
            self.waiting_spawn, self.waiting_spawn_yaw))

        # 加载结算出生点配置
        broadcast_spawn_data = room_config.get('broadcast_score_spawn', {})
        self.broadcast_score_spawn = (
            broadcast_spawn_data.get('x', 0),
            broadcast_spawn_data.get('y', 100),
            broadcast_spawn_data.get('z', 20)
        )
        self.broadcast_score_spawn_yaw = room_config.get('broadcast_score_spawn_yaw', 0)

        # 加载结算NPC位置
        npc_positions = room_config.get('broadcast_score_npc_positions', [])
        self.broadcast_score_npc_positions = npc_positions

        # 加载地图列表
        self.stages = room_config.get('stages', [])

        self.LogInfo("房间配置加载完成:")
        self.LogInfo("  - 房间名称: {}".format(self.playing_method_name))
        self.LogInfo("  - 最大人数: {}".format(self.max_players))
        self.LogInfo("  - 开始人数: {}".format(self.start_players))
        self.LogInfo("  - 倒计时: {}秒".format(self.countdown_time))
        self.LogInfo("  - 地图数量: {}".format(len(self.stages)))

    def apply_game_rules(self, dimension_id=None):
        """
        应用游戏规则到指定维度

        Args:
            dimension_id (int): 维度ID，None表示应用到所有维度
        """
        if not self.config_loader:
            self.LogError("配置加载器未初始化，无法应用游戏规则")
            return

        # 加载游戏规则配置
        game_rules_config = self.config_loader.get_game_rules()
        if not game_rules_config:
            self.LogError("游戏规则配置加载失败")
            return

        # 获取游戏规则设置
        game_rules = game_rules_config.get('game_rules', {})
        time_config = game_rules_config.get('time', {})
        weather_config = game_rules_config.get('weather', {})

        # 获取GameRulesComp
        game_comp = serverApi.GetEngineCompFactory().CreateGame(serverApi.GetLevelId())

        # 应用游戏规则 - 使用正确的API结构（一次性传入完整字典）
        try:
            game_comp.SetGameRulesInfoServer(game_rules)
            self.LogInfo("游戏规则应用成功:")

            # 记录应用的规则
            if 'option_info' in game_rules:
                for key, value in game_rules['option_info'].items():
                    self.LogInfo("  [option_info] {} = {}".format(key, value))
            if 'cheat_info' in game_rules:
                for key, value in game_rules['cheat_info'].items():
                    self.LogInfo("  [cheat_info] {} = {}".format(key, value))

        except Exception as e:
            self.LogError("应用游戏规则失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

        # 应用时间设置
        if time_config.get('set_time') is not None:
            try:
                time_comp = serverApi.GetEngineCompFactory().CreateTime(serverApi.GetLevelId())
                time_comp.SetTime(time_config['set_time'])
                self.LogInfo("设置游戏时间: {} (正午)".format(time_config['set_time']))

                # 注意：时间锁定已经通过game_rules中的daylight_cycle: False实现，无需重复设置
                if time_config.get('lock_time'):
                    self.LogInfo("游戏时间已锁定 (通过 daylight_cycle: False)")

            except Exception as e:
                self.LogError("设置时间失败: {}".format(str(e)))
                import traceback
                traceback.print_exc()

        # 应用天气设置
        if weather_config.get('set_weather') is not None:
            try:
                weather_comp = serverApi.GetEngineCompFactory().CreateWeather(serverApi.GetLevelId())
                weather_type = weather_config['set_weather']

                # 设置天气（使用正确的API）
                if weather_type == 'clear':
                    # 设置晴天：停止下雨和打雷
                    weather_comp.SetRaining(0.0, 0)  # rainLevel=0, time=0
                    weather_comp.SetThunder(0.0, 0)   # thunderLevel=0, time=0
                    self.LogInfo("设置天气: 晴天（停止下雨和打雷）")
                elif weather_type == 'rain':
                    # 设置雨天
                    weather_comp.SetRaining(1.0, 999999)  # rainLevel=1.0（最大降雨），time=很长
                    weather_comp.SetThunder(0.0, 0)       # 不打雷
                    self.LogInfo("设置天气: 雨天")
                elif weather_type == 'thunder':
                    # 设置雷暴
                    weather_comp.SetRaining(1.0, 999999)  # 下雨
                    weather_comp.SetThunder(1.0, 999999)  # 打雷
                    self.LogInfo("设置天气: 雷暴")

                # 注意：天气锁定已经通过game_rules中的weather_cycle: False实现，无需重复设置
                if weather_config.get('lock_weather'):
                    self.LogInfo("天气已锁定 (通过 weather_cycle: False)")

            except Exception as e:
                self.LogError("设置天气失败: {}".format(str(e)))
                import traceback
                traceback.print_exc()

        self.LogInfo("=" * 50)
        self.LogInfo("游戏规则应用完成")
        self.LogInfo("=" * 50)

    def _initialize_preset_manager(self):
        """初始化PresetManager - 从ECPreset框架获取"""
        try:
            # 从ECPreset框架获取PresetManagerSystem
            from ECPresetServerScripts import get_server_system
            preset_system = get_server_system()

            # 获取bedwars_room上下文的PresetManager
            # 这会自动继承全局注册的预设类型（在BedWarsGameSystem中已注册）
            self.preset_manager = preset_system.GetPresetManager("bedwars_room")
            self.LogInfo("从ECPreset框架获取PresetManager成功 (context_id=bedwars_room)")

        except Exception as e:
            self.LogError("PresetManager初始化失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()
            self.preset_manager = None

    def _load_and_create_presets(self, dimension_id):
        """
        加载并创建指定维度的所有预设

        Args:
            dimension_id (int): 维度ID
        """
        if not self.preset_manager:
            self.LogError("PresetManager未初始化,无法创建预设")
            return

        if not self.config_loader:
            self.LogError("ConfigLoader未初始化,无法加载预设配置")
            return

        try:
            # 加载预设配置
            preset_config = self.config_loader.load_preset_config(dimension_id)
            if not preset_config:
                self.LogError("加载维度{}的预设配置失败".format(dimension_id))
                return

            presets_list = preset_config.get("presets", [])
            if not presets_list:
                self.LogWarning("维度{}没有预设配置".format(dimension_id))
                return

            self.LogInfo("开始创建维度{}的预设,共{}个".format(
                dimension_id, len(presets_list)))

            # 使用PresetManager批量创建预设
            result = self.preset_manager.create_presets_from_config(
                presets_list,
                auto_start=True
            )

            # 记录创建的预设ID
            self.current_preset_instances = list(result["success"].keys())

            # 打印结果
            success_count = len(result["success"])
            failed_count = len(result["failed"])

            self.LogInfo("预设创建完成: 成功={}, 失败={}".format(
                success_count, failed_count))

            # 打印失败详情
            for failed in result["failed"]:
                self.LogError("预设创建失败: id={}, type={}, error={}".format(
                    failed.get("id"),
                    failed.get("type"),
                    failed.get("error")
                ))

        except Exception as e:
            self.LogError("加载并创建预设失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _destroy_all_presets(self):
        """销毁当前游戏的所有预设"""
        if not self.preset_manager:
            return

        if not self.current_preset_instances:
            self.LogInfo("没有需要销毁的预设")
            return

        try:
            self.LogInfo("开始销毁预设,共{}个".format(
                len(self.current_preset_instances)))

            # 逐个销毁预设
            destroyed_count = 0
            for instance_id in self.current_preset_instances:
                try:
                    self.preset_manager.destroy_preset(instance_id)
                    destroyed_count += 1
                except Exception as e:
                    self.LogError("销毁预设{}失败: {}".format(instance_id, str(e)))

            self.LogInfo("预设销毁完成: {}个".format(destroyed_count))

            # 清空列表
            self.current_preset_instances = []

        except Exception as e:
            self.LogError("销毁预设失败: {}".format(str(e)))

    def _initialize_lobby_presets(self):
        """初始化大厅预设(练习区域等)"""
        if not self.preset_manager:
            self.LogError("PresetManager未初始化,无法创建大厅预设")
            return

        if not self.config_loader:
            self.LogError("ConfigLoader未初始化,无法加载大厅预设配置")
            return

        try:
            # 加载大厅维度的预设配置
            lobby_dimension = self.lobby_dimension
            preset_config = self.config_loader.load_preset_config(lobby_dimension)

            if not preset_config:
                self.LogWarning("大厅维度{}没有预设配置".format(lobby_dimension))
                return

            presets_list = preset_config.get("presets", [])
            if not presets_list:
                self.LogWarning("大厅维度{}没有预设列表".format(lobby_dimension))
                return

            self.LogInfo("开始创建大厅预设,共{}个".format(len(presets_list)))

            # 使用PresetManager批量创建预设
            result = self.preset_manager.create_presets_from_config(
                presets_list,
                auto_start=True
            )

            # 记录创建的预设ID
            self.lobby_preset_instances = list(result["success"].keys())

            # 打印结果
            success_count = len(result["success"])
            failed_count = len(result["failed"])

            self.LogInfo("大厅预设创建完成: 成功={}, 失败={}".format(
                success_count, failed_count))

            # 打印失败详情
            for failed in result["failed"]:
                self.LogError("大厅预设创建失败: id={}, type={}, error={}".format(
                    failed.get("id"),
                    failed.get("type"),
                    failed.get("error")
                ))

        except Exception as e:
            self.LogError("初始化大厅预设失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    # ========== 事件注册配置 ==========

    def _get_c2s_event_configs(self):
        """
        获取客户端到服务端(C2S)事件监听配置

        配置格式: (事件名, 回调方法, 描述)

        Returns:
            list: C2S事件配置列表
        """
        return [
            # (事件名, 回调方法, 描述)
            ('C2SOnLocalPlayerStopLoading', self._on_local_player_stop_loading, '玩家加载完成'),
            ('C2STryVoteMap', self._on_player_try_vote_map, '玩家投票地图'),
            # 未来可以在这里添加更多C2S事件:
            # ('C2SOnPlayerRespawn', self._on_player_respawn, '玩家重生请求'),
            # ('C2SOnShopInteract', self._on_shop_interact, '商店交互'),
            # ('C2SOnTeamSelect', self._on_team_select, '队伍选择'),
        ]

    def _get_engine_event_configs(self):
        """
        获取引擎事件监听配置

        配置格式: (namespace, systemName, 事件名, 回调方法, 描述)

        Returns:
            list: 引擎事件配置列表
        """
        engine_ns = serverApi.GetEngineNamespace()
        engine_sys = serverApi.GetEngineSystemName()

        return [
            # (namespace, systemName, 事件名, 回调方法, 描述)
            (engine_ns, engine_sys, 'DelServerPlayerEvent', self._on_del_server_player, '玩家离开服务器'),
            (engine_ns, engine_sys, 'DimensionChangeFinishServerEvent', self._on_dimension_change_finish, '玩家维度切换完成'),
            (engine_ns, engine_sys, 'ItemUseAfterServerEvent', self._on_item_use_after_server, '玩家使用物品后'),
            (engine_ns, engine_sys, 'CommandEvent', self._on_command, '玩家输入命令'),
            (engine_ns, engine_sys, 'PlayerHungerChangeServerEvent', self._on_player_hunger_change, '玩家饥饿度变化'),
            # 未来可以在这里添加更多引擎事件:
            # (engine_ns, engine_sys, 'ServerPlayerGetExperienceEvent', self._on_player_exp, '玩家获得经验'),
            # (engine_ns, engine_sys, 'PlayerDieEvent', self._on_player_die, '玩家死亡'),
            # (engine_ns, engine_sys, 'PlayerAttackEvent', self._on_player_attack, '玩家攻击'),
        ]

    # ========== 事件注册核心方法 ==========

    def _register_c2s_events(self):
        """
        在__init__中注册客户端到服务端的事件监听

        重要: 必须在__init__中注册,参考ServerFormServerSystem.py line 78

        工作流程:
        1. 获取C2S事件配置列表
        2. 遍历配置,批量注册监听器
        3. 记录注册结果
        """
        self.LogInfo("[DEBUG] 开始注册C2S事件...")

        configs = self._get_c2s_event_configs()
        success_count = 0

        for event_name, callback, description in configs:
            try:
                super(RoomManagementSystem, self).ListenForEvent(
                    MOD_NAME,                # 客户端的namespace: "ECBedWars"
                    CLIENT_SYSTEMS[0][0],    # 客户端的systemName: "RoomManagementClientSystem"
                    event_name,
                    self,
                    callback
                )
                self.LogInfo("[DEBUG] ✓ C2S事件已注册: {} ({})".format(event_name, description))
                success_count += 1
            except Exception as e:
                self.LogError("[ERROR] ✗ C2S事件注册失败: {} - {}".format(event_name, str(e)))

        self.LogInfo("[DEBUG] C2S事件注册完成: 成功 {}/{}, 监听客户端: {}.{}".format(
            success_count, len(configs), MOD_NAME, CLIENT_SYSTEMS[0][0]))

    def _register_engine_events(self):
        """
        在Create中注册引擎事件监听

        工作流程:
        1. 获取引擎事件配置列表
        2. 遍历配置,批量注册监听器
        3. 记录注册结果
        """
        self.LogInfo("[DEBUG] 开始注册引擎事件...")

        configs = self._get_engine_event_configs()
        success_count = 0

        for namespace, system_name, event_name, callback, description in configs:
            try:
                super(RoomManagementSystem, self).ListenForEvent(
                    namespace,
                    system_name,
                    event_name,
                    self,
                    callback
                )
                self.LogInfo("[DEBUG] ✓ 引擎事件已注册: {} ({})".format(event_name, description))
                success_count += 1
            except Exception as e:
                self.LogError("[ERROR] ✗ 引擎事件注册失败: {} - {}".format(event_name, str(e)))

        self.LogInfo("[DEBUG] 引擎事件注册完成: 成功 {}/{}".format(success_count, len(configs)))

    def _on_local_player_stop_loading(self, args):
        """
        处理客户端玩家加载完成事件(推荐方式)

        Args:
            args: 事件参数 {'playerId': player_id}
        """
        self.LogInfo("[DEBUG] _on_local_player_stop_loading 被触发! args={}".format(args))
        player_id = args.get('playerId')
        self.LogInfo("[DEBUG] 提取player_id={}, 开始初始化".format(player_id))

        # 执行完整的玩家初始化
        self.on_player_join(player_id)

    def _on_player_try_vote_map(self, args):
        """
        处理玩家投票地图事件

        Args:
            args: 事件参数 {'player_id': player_id, 'map_id': map_id}
        """
        try:
            player_id = args.get('player_id')
            map_id = args.get('map_id')

            if not player_id or not map_id:
                self.LogError("投票参数不完整: player_id={}, map_id={}".format(player_id, map_id))
                return

            self.LogInfo("玩家 {} 尝试投票地图: {}".format(player_id, map_id))

            # 获取玩家对象
            player = self.get_better_player_obj(player_id)
            if not player:
                self.LogError("无法获取玩家对象: {}".format(player_id))
                return

            # 检查玩家是否在大厅维度
            if player.GetDimensionId() != self.lobby_dimension:
                self.LogInfo("玩家不在大厅维度，无法投票")
                return

            # 检查地图是否正在还原中
            if self.is_map_restoring(map_id):
                player.send_title(
                    u"\xa7c地图暂时不可用",
                    u"\xa77该地图正在恢复中，请稍后再试"
                )
                # 播放错误音效
                player.play_sound("random.burp", player.GetFootPos(), 1, 1)
                self.LogInfo("地图 {} 正在还原中，拒绝投票".format(map_id))
                return

            # 检查是否处于等待状态并且允许投票
            from room_states.StageWaitingState import StageWaitingState
            if not isinstance(self.root_state.current_sub_state, StageWaitingState):
                self.LogInfo("当前不在等待状态，无法投票")
                return

            if not self.root_state.current_sub_state.is_allow_map_vote():
                self.LogInfo("当前等待状态不允许投票")
                return

            # 执行投票
            if self.map_vote:
                self.map_vote.vote(player_id, map_id)
                self.LogInfo("玩家 {} 成功投票地图: {}".format(player_id, map_id))

                # 播放成功音效
                player.play_sound("random.levelup", player.GetFootPos(), 1, 1)

                # 广播刷新投票UI到所有玩家
                ui_data = self.map_vote.to_ui_dict()
                for waiting_player_id in self.waiting_players:
                    self.NotifyToClient(waiting_player_id, "RefreshMapVote", ui_data)
                self.LogInfo("已广播投票刷新到 {} 个玩家".format(len(self.waiting_players)))
            else:
                self.LogError("地图投票实例不存在")

        except Exception as e:
            self.LogError("处理玩家投票失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _on_del_server_player(self, args):
        """
        处理玩家离开服务器事件

        Args:
            args: 事件参数 {'id': player_id}
        """
        player_id = args.get('id')
        self.LogInfo("[DEBUG] 玩家离开: {}".format(player_id))
        self.on_player_leave(player_id)

    def _on_dimension_change_finish(self, args):
        """
        处理玩家维度切换完成事件

        在维度切换完成后设置玩家朝向(如果有待处理的朝向信息)

        Args:
            args: 事件参数 {
                'playerId': str,           # 玩家实体ID
                'fromDimensionId': int,    # 切换前的维度
                'toDimensionId': int,      # 切换后的维度
                'toPos': tuple             # 切换后的位置
            }
        """
        player_id = args.get('playerId')
        from_dim = args.get('fromDimensionId')
        to_dim = args.get('toDimensionId')
        to_pos = args.get('toPos')

        # 检查是否有待处理的朝向信息
        if hasattr(self, '_pending_rotations') and player_id in self._pending_rotations:
            rot = self._pending_rotations[player_id]

            try:
                # 设置玩家朝向
                comp_factory = serverApi.GetEngineCompFactory()
                # 修复：使用CreateRot组件设置朝向
                rot_comp = comp_factory.CreateRot(player_id)
                rot_comp.SetRot(rot)

                self.LogInfo("[DEBUG] 玩家 {} 维度切换完成 ({}->{}),已设置朝向: {}".format(
                    player_id, from_dim, to_dim, rot
                ))

                # 清理已处理的朝向信息
                del self._pending_rotations[player_id]

            except Exception as e:
                self.LogError("设置玩家朝向失败: {}".format(e))
                import traceback
                traceback.print_exc()

        # [FIX 2025-11-08] 转发事件给当前状态
        # RoomManagementSystem有自己的root_state状态机
        if self.root_state and self.root_state.current_sub_state:
            current_state = self.root_state.current_sub_state
            current_state_name = getattr(current_state, '__class__', type(current_state)).__name__

            self.LogInfo("[DEBUG] 当前状态: {}, 是否有on_player_dimension_change_finish: {}".format(
                current_state_name,
                hasattr(current_state, 'on_player_dimension_change_finish')
            ))

            # 如果当前状态有处理维度切换完成的方法,调用它
            if hasattr(current_state, 'on_player_dimension_change_finish'):
                try:
                    self.LogInfo("[DEBUG] 调用状态的on_player_dimension_change_finish方法")
                    current_state.on_player_dimension_change_finish(player_id, from_dim, to_dim, to_pos)
                except Exception as e:
                    self.LogError("状态处理维度切换完成失败: {}".format(e))
                    import traceback
                    traceback.print_exc()
        else:
            self.LogWarn("[DEBUG] root_state或current_sub_state为None,无法转发维度切换事件")

    def _on_item_use_after_server(self, args):
        """
        处理玩家使用物品后事件（对应老项目的ItemUseAfterServerEvent）

        当玩家使用地图投票道具时，打开地图投票UI
        当玩家使用装扮更换道具时，打开装扮商店UI

        Args:
            args: 事件参数 {
                'entityId': str,        # 玩家实体ID
                'itemDict': dict,       # 物品信息 {'itemName': str, 'auxValue': int, ...}
                'blockName': str,       # 点击的方块名称（如果有）
                'x': int,               # 方块坐标X（如果有）
                'y': int,               # 方块坐标Y（如果有）
                'z': int,               # 方块坐标Z（如果有）
            }
        """
        try:
            # 提取玩家ID（ItemUseAfterServerEvent使用entityId而非playerId）
            player_id = args.get('entityId')
            if not player_id:
                return

            # 获取玩家对象
            player = self.get_better_player_obj(player_id)
            if not player:
                return

            # 检查玩家是否在大厅维度（只在大厅允许使用道具）
            if player.GetDimensionId() != self.lobby_dimension:
                return

            # 注意：物品使用的处理逻辑已经移到状态机中
            # StageWaitingState.on_player_use_item_on_block 会处理：
            # - ecbedwars:map_vote (地图投票道具)
            # - ecbedwars:personal_workshop (装扮更换道具)
            #
            # 这里不再处理，避免重复触发UI打开
            # 参考老项目：ECStagePart 不直接处理物品使用，而是由 StageWaitingState 处理

            pass  # 保留此方法作为占位，未来如果需要在所有状态下处理某些道具可在此添加

        except Exception as e:
            self.LogError("_on_item_use_after_server处理失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    # 注意：_handle_map_vote_item_use 和 _handle_personal_workshop_item_use 方法已删除
    # 原因：这些逻辑已移到状态机中处理（StageWaitingState.on_player_use_item_on_block）
    # 避免重复处理导致UI被打开两次

    def _on_command(self, args):
        """
        处理玩家输入命令事件

        实现/stage start命令，允许管理员强制开始游戏倒计时

        Args:
            args: 事件参数 {
                'entityId': str,      # 玩家实体ID
                'command': str,       # 完整命令字符串
                'cancel': bool        # 是否取消命令（可修改）
            }
        """
        try:
            player_id = args.get('entityId')
            command = args.get('command')

            if not player_id or not command:
                return

            # 获取玩家对象
            player = self.get_better_player_obj(player_id)
            if not player:
                return

            # 解析命令
            split = command.split(" ")
            if len(split) == 0:
                return

            # 处理 /stage 命令
            if split[0] == "/stage":
                # 取消命令的默认处理（避免显示"未知命令"）
                args['cancel'] = True

                # 检查子命令
                if len(split) < 2:
                    player.send_message(u"\u00a7c用法：/stage <start|start_now>")
                    return

                # 处理 /stage start 子命令
                if split[1] == "start":
                    self._handle_stage_start_command(player_id, player)
                # 处理 /stage start_now 子命令
                elif split[1] == "start_now":
                    self._handle_stage_start_now_command(player_id, player)
                else:
                    player.send_message(u"\u00a7c用法：/stage <start|start_now>")

        except Exception as e:
            self.LogError("处理命令失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _handle_stage_start_command(self, player_id, player):
        """
        处理 /stage start 命令

        功能：
        - 检查当前是否在等待状态的pending子状态
        - 如果是，则设置force_start标志，触发倒计时
        - 如果不是，提示玩家当前不是等待状态

        Args:
            player_id (str): 玩家ID
            player: BetterPlayerObject 玩家对象
        """
        try:
            # 检查root_state是否存在
            if not self.root_state:
                player.send_message(u"\u00a7c状态机未初始化")
                self.LogError("root_state不存在，无法处理/stage start命令")
                return

            # 获取当前主状态名称
            current_state_name = self.root_state.current_sub_state_name
            if not current_state_name:
                player.send_message(u"\u00a7c当前没有活动状态")
                return

            # 检查是否在waiting状态
            if current_state_name != 'waiting':
                player.send_message(u"\u00a7c当前不是等待状态（当前状态：{}）".format(current_state_name))
                self.LogInfo("玩家 {} 尝试使用/stage start，但当前状态是: {}".format(
                    player_id, current_state_name))
                return

            # 获取waiting状态实例
            waiting_state = self.root_state.current_sub_state
            if not waiting_state:
                player.send_message(u"\u00a7c无法获取等待状态实例")
                return

            # 获取waiting状态的子状态名称
            waiting_sub_state_name = waiting_state.current_sub_state_name
            if not waiting_sub_state_name:
                player.send_message(u"\u00a7c等待状态未初始化")
                return

            # 检查是否在pending子状态
            if waiting_sub_state_name != 'pending':
                player.send_message(u"\u00a7c当前不是等待玩家阶段（当前阶段：{}）".format(
                    waiting_sub_state_name))
                self.LogInfo("玩家 {} 尝试使用/stage start，但等待状态子状态是: {}".format(
                    player_id, waiting_sub_state_name))
                return

            # 设置强制开始标志
            waiting_state.force_start = True
            player.send_message(u"\u00a7a开始倒计时...")
            self.LogInfo("玩家 {} 使用/stage start命令，已设置force_start=True".format(player_id))

            # 广播消息给所有玩家
            self.broadcast_message(u"\u00a7e管理员强制开始游戏倒计时！")

        except Exception as e:
            player.send_message(u"\u00a7c执行命令时发生错误")
            self.LogError("_handle_stage_start_command失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _handle_stage_start_now_command(self, player_id, player):
        """
        处理 /stage start_now 命令 - 直接开启对局（跳过倒计时）

        功能：
        - 检查当前是否在等待状态(waiting)
        - 直接切换到running状态，跳过倒计时阶段
        - 触发玩家传送和运镜动画

        设计依据：
        - 使用 root_state.next_sub_state() 切换主状态（状态机系统.md:449-466）
        - 参考 StageWaitingState.on_timeout() 的状态切换逻辑（StageWaitingState.py:749-771）

        Args:
            player_id (str): 玩家ID
            player: BetterPlayerObject 玩家对象
        """
        try:
            # 检查root_state是否存在
            if not self.root_state:
                player.send_message(u"\u00a7c状态机未初始化")
                self.LogError("root_state不存在，无法处理/stage start_now命令")
                return

            # 获取当前主状态名称
            current_state_name = self.root_state.current_sub_state_name
            if not current_state_name:
                player.send_message(u"\u00a7c当前没有活动状态")
                return

            # 检查是否在waiting状态
            if current_state_name != 'waiting':
                player.send_message(u"\u00a7c当前不是等待状态（当前状态：{}）".format(current_state_name))
                self.LogInfo("玩家 {} 尝试使用/stage start_now，但当前状态是: {}".format(
                    player_id, current_state_name))
                return

            # 获取waiting状态实例
            waiting_state = self.root_state.current_sub_state
            if not waiting_state:
                player.send_message(u"\u00a7c无法获取等待状态实例")
                return

            # 清除HUD（参考StageWaitingState.on_timeout()的逻辑）
            try:
                self.clear_stack_msg_bottom()
            except Exception as e:
                self.LogError("清除HUD失败: {}".format(str(e)))

            # 广播消息给所有玩家
            self.broadcast_message(u"\u00a7e管理员跳过倒计时，游戏即将开始！")
            player.send_message(u"\u00a7a跳过倒计时，立即进入对局...")
            self.LogInfo("玩家 {} 使用/stage start_now命令，直接切换到running状态".format(player_id))

            # 直接切换到下一个主状态(running)
            # 使用root_state.next_sub_state()方法来切换主状态
            # 这是状态机的标准切换方式（状态机系统.md:449-466）
            self.root_state.next_sub_state()

        except Exception as e:
            player.send_message(u"\u00a7c执行命令时发生错误")
            self.LogError("_handle_stage_start_now_command失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _on_player_hunger_change(self, args):
        """
        处理玩家饥饿度变化事件

        在大厅维度(lobby_dimension)禁止饥饿度变化，保持玩家饥饿度始终为满值

        Args:
            args: 事件参数 {
                'playerId': str,     # 玩家ID
                'hunger': int,       # 当前饥饿度
                'cancel': bool       # 是否取消变化（可修改）
            }
        """
        try:
            player_id = args.get('playerId')
            if not player_id:
                return

            # 获取玩家对象
            player = self.get_better_player_obj(player_id)
            if not player:
                return

            # 检查玩家是否在大厅维度
            # 老项目逻辑：在维度0（大厅）禁止饥饿度变化
            if player.GetDimensionId() == self.lobby_dimension:
                # 取消饥饿度变化
                args['cancel'] = True

        except Exception as e:
            self.LogError("处理饥饿度变化事件失败: {}".format(str(e)))

    def _add_existing_players_to_waiting_list(self):
        """
        在系统初始化时,将已经在线的玩家添加到等待列表

        重要: 对已在线玩家执行完整的初始化流程(清空背包、设置模式、发放道具等)
        """
        try:
            # 获取所有在线玩家
            all_players = self.get_all_better_players()

            for player in all_players:
                player_id = player.GetPlayerId()
                if player_id not in self.waiting_players:
                    self.LogInfo("检测到已在线玩家: {},执行完整初始化".format(player_id))

                    # 调用on_player_join执行完整的玩家初始化流程
                    # (清空背包、传送、设置模式、设置无敌、发放道具)
                    self.on_player_join(player_id)

            self.LogInfo("已在线玩家检测完成,等待列表: {} 人".format(len(self.waiting_players)))
        except Exception as e:
            self.LogError("添加已在线玩家失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    # ========== 房间逻辑更新 ==========

    def _update_room_logic(self):
        """
        更新房间逻辑(每帧调用)

        注意: 房间逻辑由各个状态负责：
        - StageWaitingState: 处理等待阶段的玩家数量检查、倒计时等
        - BedWarsRunningState: 处理游戏进行中的逻辑
        - BedWarsEndingState: 处理游戏结束阶段的逻辑

        此方法保留用于全局房间逻辑（如果需要）
        """
        pass

    # ========== 辅助方法 ==========

    def get_all_players(self):
        """
        获取所有在线玩家列表

        Returns:
            list: 所有玩家ID列表
        """
        return serverApi.GetPlayerList()

    def get_online_player_count(self):
        """
        获取在线玩家数量

        Returns:
            int: 在线玩家数
        """
        # 使用serverApi.GetPlayerList()获取所有玩家ID
        return len(serverApi.GetPlayerList())

    def broadcast_message(self, message, color=u'\xa7f'):
        """
        向所有玩家广播消息

        Args:
            message (str): 消息内容
            color (str): 颜色代码
        """
        # 使用serverApi.GetPlayerList()获取所有玩家ID
        player_ids = serverApi.GetPlayerList()

        for player_id in player_ids:
            player_obj = self.get_better_player_obj(player_id)
            player_obj.send_message(message, color)

    # ========== 地图投票与备份管理 ==========

    def is_map_restoring(self, map_id):
        """
        检查地图是否正在还原中

        Args:
            map_id (str): 地图ID

        Returns:
            bool: 是否正在还原中
        """
        return map_id in self.restoring_maps

    def get_available_maps_for_vote(self):
        """
        获取可以用于投票的地图列表

        排除规则:
        1. 正在还原中的地图
        2. 正在使用的地图(游戏进行中)

        Returns:
            list: 可用地图列表
        """
        available_stages = []

        for stage in self.stages:
            map_id = stage['id']
            map_name = stage.get('name', u'未知地图')

            # 规则1: 排除还原中的地图
            if map_id in self.restoring_maps:
                continue

            # 规则2: 排除正在被使用的地图
            if map_id in self._maps_in_use:
                continue

            # 通过所有检查,地图可用
            available_stages.append(stage)

        self.LogInfo("可用地图数量: {}, 还原中: {}, 使用中: {}".format(
            len(available_stages),
            len(self.restoring_maps),
            len(self._maps_in_use)
        ))

        return available_stages

    def create_map_vote(self):
        """创建地图投票实例"""
        from Script_NeteaseMod.systems.util.MapVoteInstance import MapVoteInstance
        self.map_vote = MapVoteInstance(self)
        self.LogInfo("地图投票实例已创建,可用地图数: {}".format(len(self.map_vote.maps)))

    def get_backup_handler(self, dimension_id):
        """
        获取或创建地图备份管理器

        Args:
            dimension_id (int): 维度ID

        Returns:
            DimensionBackupHandler: 备份管理器实例
        """
        if dimension_id not in self.map_backup_handlers:
            from util.DimensionBackupHandler import DimensionBackupHandler
            self.map_backup_handlers[dimension_id] = DimensionBackupHandler(self, dimension_id)
            self.LogInfo("创建维度{}的备份管理器".format(dimension_id))

        return self.map_backup_handlers[dimension_id]

    def get_map_backup_range(self, map_id):
        """
        获取指定地图的备份范围

        Args:
            map_id (str): 地图ID

        Returns:
            tuple: 备份范围 ((min_x, min_y, min_z), (max_x, max_y, max_z))
        """
        try:
            stage = next((s for s in self.stages if s.get('id') == map_id), None)
            if not stage:
                self.LogError("找不到地图 {} 的配置信息".format(map_id))
                # 返回默认范围
                return ((-200, 0, -200), (200, 140, 200))

            # 优先使用load_range字段
            if 'load_range' in stage:
                load_range_config = stage['load_range']
                min_pos = load_range_config[0]
                max_pos = load_range_config[1]
                return (
                    (int(min_pos['x']), int(min_pos['y']), int(min_pos['z'])),
                    (int(max_pos['x']), int(max_pos['y']), int(max_pos['z']))
                )

            # 如果没有load_range,使用center_pos计算
            if 'center_pos' in stage:
                center_pos = stage['center_pos']
                radius = stage.get('backup_radius', 200)
                x, y, z = int(center_pos['x']), int(center_pos['y']), int(center_pos['z'])
                return (
                    (x - radius, 0, z - radius),
                    (x + radius, 140, z + radius)
                )

            # 如果也没有,使用spawn_pos计算
            if 'spawn_pos' in stage:
                spawn_pos = stage['spawn_pos']
                radius = 200
                x, y, z = int(spawn_pos['x']), int(spawn_pos['y']), int(spawn_pos['z'])
                return (
                    (x - radius, 0, z - radius),
                    (x + radius, 140, z + radius)
                )

            # 兜底:返回默认范围
            self.LogWarn("地图 {} 没有配置备份范围相关字段,使用默认范围".format(map_id))
            return ((-200, 0, -200), (200, 140, 200))

        except Exception as e:
            self.LogError("获取地图备份范围失败: {}".format(str(e)))
            return ((-200, 0, -200), (200, 140, 200))

    def record_block_to_backup(self, pos, dimension):
        """
        记录方块变更到备份系统

        由BedWarsGameSystem调用,在玩家放置或破坏方块时记录

        Args:
            pos (tuple): 方块位置 (x, y, z)
            dimension (int): 维度ID
        """
        try:
            # 获取该维度的备份管理器
            backup_handler = self.get_backup_handler(dimension)

            # 记录方块变更
            backup_handler.backup.record(pos)

        except Exception as e:
            self.LogError("记录方块变更失败 pos={} dimension={}: {}".format(
                pos, dimension, str(e)
            ))
