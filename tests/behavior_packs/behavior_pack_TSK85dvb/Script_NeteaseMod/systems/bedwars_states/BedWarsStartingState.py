# -*- coding: utf-8 -*-
"""
BedWarsStartingState - 起床战争开始状态

功能:
- 游戏准备阶段
- 初始化队伍数据
- 玩家装备发放
- 倒计时显示
- 地图预览运镜

原文件: Parts/ECBedWars/state/BedWarsStartingState.py
"""

from ..state.GamingState import GamingState


class BedWarsStartingState(GamingState):
    """起床战争开始状态"""

    def __init__(self, parent):
        """
        初始化开始状态

        Args:
            parent: 父状态
        """
        GamingState.__init__(self, parent)

        # 注册生命周期回调
        self.with_enter(self._on_enter)
        self.with_exit(self._on_exit)
        self.with_tick(self._on_tick)

        # 注册事件监听(拦截破坏/放置方块、拦截伤害)
        self.listen_engine_event('ServerPlayerTryDestroyBlockEvent', self._on_player_try_destroy_block)
        self.listen_engine_event('ServerEntityTryPlaceBlockEvent', self._on_entity_try_place_block)
        self.listen_engine_event("DamageEvent", self._on_damage_event)

        # 倒计时 - 与老项目保持一致
        self.countdown = 10  # 10秒倒计时(老项目TimedGamingState(10))
        self.countdown_timer_id = None
        self.ticks_passed = 0  # 已经过的tick数(用于计算秒数)

        # 运镜相关
        self.camera_preview_started = False  # 运镜是否已启动
        self.title_sent = False  # 是否已发送地图名称标题
        self.spectator_mode_set = False  # 是否已设置旁观者模式

    def _on_enter(self):
        """进入开始状态"""
        system = self.get_system()
        system.LogInfo("BedWarsStartingState entered")

        # 初始化队伍数据
        self._initialize_teams()

        # 发放初始装备
        self._give_starter_equipment()

        # 开始倒计时
        self._start_countdown()

    def _on_exit(self):
        """退出开始状态"""
        system = self.get_system()
        system.LogInfo("BedWarsStartingState exited")

        # 停止地图预览运镜
        self._stop_camera_preview()

        # 清理倒计时定时器
        if self.countdown_timer_id:
            try:
                import mod.server.extraServerApi as serverApi
                comp = serverApi.GetEngineCompFactory().CreateGame(serverApi.GetLevelId())
                comp.CancelTimer(self.countdown_timer_id)
                self.countdown_timer_id = None
            except:
                pass

    def _on_tick(self):
        """
        每帧更新

        功能:
        1. 启动运镜(首次tick时)
        2. 设置旁观者模式(首次tick时)
        3. 显示地图名称标题(经过1秒后,即20 ticks)
        """
        # 累计tick数
        self.ticks_passed += 1

        # 计算经过的秒数 (20 ticks = 1秒)
        seconds_passed = self.ticks_passed / 20.0

        # 首次tick时启动运镜(模拟老项目行为)
        if not self.camera_preview_started:
            self._start_camera_preview()

        # 首次tick时设置旁观者模式(老项目在发送title时同时设置)
        if not self.spectator_mode_set:
            self._set_players_spectator_mode()
            self.spectator_mode_set = True

        # 在经过1秒后显示地图名称标题(老项目: self.get_seconds_passed() > 1)
        if not self.title_sent and seconds_passed > 1.0:
            self._send_map_title()
            self.title_sent = True

    # ===== 事件处理方法 =====

    def _on_damage_event(self, args):
        """
        拦截运镜阶段的伤害事件

        Args:
            args (dict): 伤害事件参数
                - damage: 伤害值
                - srcId: 伤害来源ID
                - victimId: 受害者ID

        功能:
            在运镜阶段将所有伤害设置为0,保护玩家
        """
        # 将伤害设置为0
        args['damage'] = 0
        return

    def _on_player_try_destroy_block(self, args):
        """
        拦截玩家破坏方块事件

        Args:
            args (dict): 破坏方块事件参数
                - playerId: 玩家ID
                - dimensionId: 维度ID
                - x, y, z: 方块坐标
                - cancel: 是否取消

        功能:
            在运镜阶段禁止玩家破坏方块
        """
        system = self.get_system()
        if system.dimension == args['dimensionId']:
            args['cancel'] = True

    def _on_entity_try_place_block(self, args):
        """
        拦截实体放置方块事件

        Args:
            args (dict): 放置方块事件参数
                - entityId: 实体ID
                - dimensionId: 维度ID
                - x, y, z: 方块坐标
                - cancel: 是否取消

        功能:
            在运镜阶段禁止实体放置方块
        """
        system = self.get_system()
        if system.dimension == args['dimensionId']:
            args['cancel'] = True

    # ===== 核心逻辑方法 =====

    def _initialize_teams(self):
        """初始化队伍数据"""
        system = self.get_system()

        if not system.team_module:
            system.LogError("队伍模块未初始化")
            return

        # 确保room_system引用存在
        if not system.room_system:
            system._initialize_room_system_reference()

        if not system.room_system:
            system.LogError("[_initialize_teams] 无法获取room_system引用!")
            return

        # 获取房间系统的队伍分配
        team_players = getattr(system.room_system, 'team_players', {})

        for team_id, player_list in team_players.items():
            for player_id in player_list:
                system.team_module.assign_player_to_team(player_id, team_id)

        # 初始化陷阱管理器引用
        self._initialize_trap_managers()

        system.LogInfo("队伍数据初始化完成")

    def _give_starter_equipment(self):
        """发放初始装备"""
        system = self.get_system()

        if not system.team_module:
            return

        # 获取所有玩家
        all_teams = system.team_module.get_all_teams()
        for team_id in all_teams:
            players = system.team_module.get_team_players(team_id)
            for player_id in players:
                self._give_player_starter_equipment(player_id, team_id)

        system.LogInfo("初始装备发放完成")

    def _give_player_starter_equipment(self, player_id, team_id):
        """
        给玩家发放初始装备（已废弃）

        注意: 此方法已被移除，装备初始化在BedWarsRunningState中通过以下调用链完成:
        - BedWarsRunningState._initialize_players()
          → BedWarsGameSystem._respawn_player()
          → BedWarsGameSystem._apply_player_equipment_and_upgrades()
          → BedWarsGameSystem._init_player_equipment()

        Args:
            player_id (str): 玩家ID
            team_id (str): 队伍ID
        """
        # 不在Starting状态发放装备，等待进入Running状态后统一发放
        pass

    def _start_countdown(self):
        """开始倒计时"""
        system = self.get_system()

        def countdown_tick():
            if self.countdown > 0:
                # 运镜播放期间不显示聊天消息，只在Title中显示倒计时
                # message = u"游戏将在{}秒后开始".format(self.countdown)
                # system._broadcast_message(message, u'\xa7e')
                self.countdown -= 1
            else:
                # 倒计时结束,进入running状态
                self.parent.next_sub_state()

        # 创建定时器
        import mod.server.extraServerApi as serverApi
        comp = serverApi.GetEngineCompFactory().CreateGame(serverApi.GetLevelId())
        self.countdown_timer_id = comp.AddRepeatedTimer(1.0, countdown_tick)

        system.LogInfo("倒计时已开始")

    def _set_players_spectator_mode(self):
        """
        将所有玩家设置为旁观者模式

        功能:
            在运镜阶段,将维度内所有玩家的游戏模式设置为Spectator(旁观者)
            确保玩家在运镜阶段不受伤害、不能交互

        参考:
            老项目: BedWarsStartingState.py:128-131
        """
        system = self.get_system()

        try:
            import mod.server.extraServerApi as serverApi
            comp_factory = serverApi.GetEngineCompFactory()

            # 从team_module获取所有玩家
            if not system.team_module:
                system.LogWarn("team_module未初始化,无法设置旁观者模式")
                return

            # 遍历所有队伍的所有玩家
            all_teams = system.team_module.get_all_teams()
            player_count = 0
            for team_id in all_teams:
                players = system.team_module.get_team_players(team_id)
                for player_id in players:
                    # 设置为旁观者模式
                    comp_player = comp_factory.CreatePlayer(player_id)
                    comp_player.SetPlayerGameType(serverApi.GetMinecraftEnum().GameType.Spectator)
                    system.LogInfo("已将玩家 {} 设置为旁观者模式".format(player_id))
                    player_count += 1

            system.LogInfo("所有玩家({})已设置为旁观者模式".format(player_count))

        except Exception as e:
            system.LogError("设置旁观者模式失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _initialize_trap_managers(self):
        """
        初始化陷阱管理器引用

        从所有床位预设中收集trap_manager引用，存储到system.team_trap_managers
        """
        system = self.get_system()

        try:
            # 清空原有的引用
            system.team_trap_managers = {}

            # 从ECPreset管理器获取所有床位预设
            from ECPresetServerScripts import get_server_mgr

            # 获取预设管理器 (注意: 必须使用与RoomManagementSystem相同的context_id)
            context_id = "bedwars_room"
            preset_mgr = get_server_mgr(context_id)

            if not preset_mgr:
                system.LogWarn("预设管理器未找到: {}".format(context_id))
                return

            # 遍历所有预设实例
            # 注意：get_all_presets()返回字典{instance_id: PresetInstance}
            all_presets = preset_mgr.get_all_presets()
            for instance_id, instance in all_presets.items():
                # 只处理床位预设
                # [FIX 2025-11-04] PresetInstance没有get_preset_type()方法,应该访问preset_type属性
                preset_type = instance.preset_type
                if preset_type != "bedwars:bed":
                    continue

                # 获取床位预设的定义对象
                # [FIX 2025-11-04] PresetInstance没有get_definition()方法,应该访问preset_def属性
                preset_def = instance.preset_def
                if not preset_def:
                    continue

                # 获取队伍ID和trap_manager引用
                team_id = getattr(preset_def, 'team', None)
                trap_manager = getattr(preset_def, 'trap_manager', None)

                if team_id and trap_manager:
                    system.team_trap_managers[team_id] = trap_manager
                    system.LogInfo("收集陷阱管理器: team={}".format(team_id))

            system.LogInfo("陷阱管理器引用收集完成: {} 个队伍".format(
                len(system.team_trap_managers)))

        except Exception as e:
            system.LogError("初始化陷阱管理器引用失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _start_camera_preview(self):
        """
        启动地图预览运镜

        功能:
            从地图中的camera:track_point预设获取中心点并启动运镜

        实现方式:
            1. 查找当前维度的camera:track_point预设
            2. 获取预设的世界位置作为中心点
            3. 广播事件到预设,由预设发送运镜指令到客户端
        """
        if self.camera_preview_started:
            return

        system = self.get_system()

        try:
            # 从ECPreset管理器获取camera:track_point预设
            from ECPresetServerScripts import get_server_mgr

            # 获取当前维度的预设管理器
            # 注意：预设是在"bedwars_room"上下文中创建的，不是"bedwars_room_{dimension}"
            context_id = "bedwars_room"
            preset_mgr = get_server_mgr(context_id)

            if not preset_mgr:
                system.LogWarn("预设管理器未找到: {}, 无法启动运镜".format(context_id))
                return

            # 查找camera:track_point类型的预设（需要匹配当前维度）
            camera_track_preset = None
            all_presets = preset_mgr.get_all_presets()

            system.LogInfo("开始查找camera:track_point预设, 当前维度={}, 预设总数={}".format(
                system.dimension, len(all_presets)
            ))

            for instance_id, instance in all_presets.items():
                preset_type = instance.preset_type  # 使用属性而非方法
                system.LogDebug("检查预设: id={}, type={}".format(instance_id, preset_type))

                if preset_type == "camera:track_point":
                    # 检查维度是否匹配
                    preset_dimension = instance.get_config("dimension")
                    system.LogInfo("找到camera:track_point预设: dimension={}".format(preset_dimension))

                    if preset_dimension == system.dimension:
                        camera_track_preset = instance
                        system.LogInfo("找到匹配维度的camera:track_point预设")
                        break

            if not camera_track_preset:
                system.LogWarn("未找到维度{}的camera:track_point预设, 无法启动运镜".format(system.dimension))
                return

            # 获取所有玩家列表
            all_players = []
            if system.team_module:
                all_teams = system.team_module.get_all_teams()
                for team_id in all_teams:
                    players = system.team_module.get_team_players(team_id)
                    all_players.extend(players)

            # 直接调用预设的start_camera_preview()方法
            # 预设内部会通过System.NotifyToClient发送消息到客户端
            preset_def = camera_track_preset.preset_def
            if preset_def and hasattr(preset_def, 'start_camera_preview'):
                preset_def.start_camera_preview(players=all_players if all_players else None)
                self.camera_preview_started = True
                system.LogInfo("地图预览运镜已启动 (通过预设, {} 个玩家)".format(len(all_players)))
            else:
                system.LogError("camera:track_point预设没有start_camera_preview方法")

        except Exception as e:
            system.LogError("启动地图预览运镜失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _stop_camera_preview(self):
        """
        停止地图预览运镜

        功能:
            直接向客户端发送停止运镜事件，释放玩家相机控制权
        """
        if not self.camera_preview_started:
            return

        system = self.get_system()

        try:
            # 找到camera:track_point预设并调用其stop方法
            from ECPresetServerScripts import get_server_mgr

            context_id = "bedwars_room"
            preset_mgr = get_server_mgr(context_id)

            if preset_mgr:
                # 获取所有玩家列表
                all_players = []
                if system.team_module:
                    all_teams = system.team_module.get_all_teams()
                    for team_id in all_teams:
                        players = system.team_module.get_team_players(team_id)
                        all_players.extend(players)

                # 查找匹配维度的camera:track_point预设
                all_presets = preset_mgr.get_all_presets()
                for instance_id, instance in all_presets.items():
                    if instance.preset_type == "camera:track_point":
                        preset_dimension = instance.get_config("dimension")
                        if preset_dimension == system.dimension:
                            # 调用预设的停止方法
                            preset_def = instance.preset_def
                            if preset_def and hasattr(preset_def, 'stop_camera_preview'):
                                preset_def.stop_camera_preview(players=all_players if all_players else None)
                                break

            self.camera_preview_started = False
            system.LogInfo("地图预览运镜已停止")

        except Exception as e:
            system.LogError("停止地图预览运镜失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _send_map_title(self):
        """
        发送地图名称标题

        功能:
            在运镜过程中显示地图名称和提示文字
        """
        system = self.get_system()

        try:
            # 获取当前房间配置
            if not hasattr(system, 'room_system') or not system.room_system:
                return

            # 获取当前选中的地图配置
            current_stage = getattr(system.room_system, 'current_stage_config', None)
            if not current_stage:
                return

            # 获取地图名称
            map_name = current_stage.get('name', u'未知地图')

            # 获取所有在线玩家
            import mod.server.extraServerApi as serverApi
            comp_factory = serverApi.GetEngineCompFactory()
            comp_game = comp_factory.CreateGame(serverApi.GetLevelId())

            # 从team_module获取维度内所有玩家
            from ..util.BetterPlayerObject import BetterPlayerObject
            dimension_players = []
            if system.team_module:
                all_teams = system.team_module.get_all_teams()
                for team_id in all_teams:
                    players = system.team_module.get_team_players(team_id)
                    for player_id in players:
                        player = BetterPlayerObject(player_id, system)
                        dimension_players.append(player)

            # 为每个玩家发送标题(延迟1秒,与老项目保持一致)
            for player in dimension_players:
                def send_title_delayed(player_obj=player, name=map_name):
                    # 主标题: » 地图名 «
                    title = u"» {} «".format(name)

                    # 副标题: {icon-ec-sword2} §c准备战斗 {icon-ec-sword2}
                    # 使用format_text处理图标 (将{icon-ec-sword2}替换为\uE187)
                    subtitle = system.format_text(u"{icon-ec-sword2} \xa7c准备战斗 {icon-ec-sword2}")

                    # 发送title: fadein=10, duration=140(7秒), fadeout=20
                    player_obj.send_title(title, subtitle, fadein=10, duration=140, fadeout=20)

                comp_game.AddTimer(1.0, send_title_delayed)

            system.LogInfo("地图标题已发送: {}".format(map_name))

        except Exception as e:
            system.LogError("发送地图标题失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()
