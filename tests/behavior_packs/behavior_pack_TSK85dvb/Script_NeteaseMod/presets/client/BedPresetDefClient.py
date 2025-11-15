# -*- coding: utf-8 -*-
"""
床预设 - 客户端

功能:
- 显示床破坏特效
- 播放床破坏音效
- 显示床的装饰物特效
- 处理陷阱触发特效
"""

from ECPresetServerScripts import PresetDefinitionClient

class BedPresetDefClient(PresetDefinitionClient):
    """
    床预设客户端实现

    核心功能:
    1. 床破坏特效和音效
    2. 床装饰物显示 (床上方的团队图标)
    3. 陷阱触发特效
    4. 床颜色初始化特效
    """

    def __init__(self):
        super(BedPresetDefClient, self).__init__()

        # 特效ID列表
        self._effect_ids = []

        # 装饰物特效ID
        self._ornament_effect_id = None

        # 床破坏特效ID
        self._destroy_effect_id = None

        # P1功能数据
        self.bed_blocks = []  # type: list  # 床方块坐标列表
        self.player_to_team = {}  # type: dict  # 玩家ID -> 队伍ID映射
        self.bed_destroyed = False  # type: bool  # 床是否已破坏

        # P1.2功能数据 - 浮动文字
        self.floating_text_board_id = None  # type: int or None  # 浮动文字面板ID
        self.floating_text_timer = None  # type: object or None  # 浮动文字销毁定时器

    def on_init(self, instance):
        """
        预设初始化

        解析配置数据:
        - team: 队伍ID

        Args:
            instance: PresetInstanceClient对象
        """
        # 修复：应该从instance.config而不是instance.data读取team
        # instance.config是服务端通过PresetInstance同步过来的配置
        self.team = instance.get_config("team", "NONE")
        if not self.team or self.team == "NONE":
            print("[WARN] BedPresetDefClient.on_init 缺少team配置, 使用默认值: NONE")

        print("[INFO] [床预设-客户端] 初始化: team={}".format(self.team))

    def on_start(self, instance):
        """
        预设启动

        执行步骤:
        1. 创建床装饰物特效
        2. 注册事件监听（客户端破坏保护）

        Args:
            instance: PresetInstanceClient对象
        """
        print("[INFO] [床预设-客户端] 启动: team={}".format(self.team))

        # 保存instance引用
        self.instance = instance

        # 1. 创建床装饰物特效
        self._create_bed_ornament(instance)

        # 2. 注册客户端事件监听 - P1功能：客户端破坏保护
        self._register_client_events(instance)

    def on_tick(self, instance):
        """
        每Tick更新

        床预设客户端通常不需要Tick更新

        Args:
            instance: PresetInstanceClient对象
        """
        pass

    def on_stop(self, instance):
        """
        预设停止

        清理工作:
        1. 移除装饰物特效
        2. 取消事件监听
        3. 清理浮动文字（P1.2）

        Args:
            instance: PresetInstanceClient对象
        """
        print("[INFO] [床预设-客户端] 停止: team={}".format(self.team))

        # 移除装饰物特效
        if self._ornament_effect_id:
            self._stop_effect(self._ornament_effect_id)
            self._ornament_effect_id = None

        # 停止所有特效
        self._stop_all_effects()

        # P1.2: 清理浮动文字
        self._cleanup_floating_text()

    def on_destroy(self, instance):
        """
        预设销毁

        最终清理工作

        Args:
            instance: PresetInstanceClient对象
        """
        print("[INFO] [床预设-客户端] 销毁: team={}".format(self.team))

        # 清理特效ID列表
        self._effect_ids = []
        self._ornament_effect_id = None
        self._destroy_effect_id = None

    # ========== 接收服务端消息 ==========

    def on_server_message(self, instance, message_type, data):
        """
        接收服务端消息回调 - ECPreset框架标准接口

        Args:
            instance: PresetInstanceClient对象
            message_type: str 消息类型
            data: dict 消息数据
        """
        if message_type == "BedWarsBedDestroy":
            self._on_bed_destroy(data)
        elif message_type == "BedWarsTrapTriggered":
            self._on_trap_triggered(data)
        elif message_type == "SyncBedData":
            # P1功能：同步床数据（床方块位置、玩家队伍映射）
            self._on_sync_bed_data(data)
        elif message_type == "bed_blocks_placed":
            # P1.2功能：床方块放置完成后显示浮动文字提示
            # 保存instance引用（如果还未保存）
            if not hasattr(self, 'instance') or self.instance is None:
                self.instance = instance
            # 传递instance参数用于instance_id检查
            self._on_bed_blocks_placed(data, instance)

    # ========== 事件处理方法 ==========

    def _on_bed_destroy(self, event_data):
        """
        处理床破坏事件

        播放床破坏特效和音效

        Args:
            event_data: 事件数据
                - team: 队伍ID
                - who: 破坏者玩家ID
                - bed_pos: 床位置 (x, y, z)
        """
        team = event_data.get('team')

        # 只处理本预设对应的床
        if team != self.team:
            return

        bed_pos = event_data.get('bed_pos')
        print("[INFO] [床预设-客户端] 床被破坏: team={}, pos={}".format(team, bed_pos))

        # 播放床破坏特效
        self._play_bed_destroy_effect(bed_pos)

        # 播放床破坏音效
        self._play_bed_destroy_sound(bed_pos)

        # 移除装饰物特效
        if self._ornament_effect_id:
            self._stop_effect(self._ornament_effect_id)
            self._ornament_effect_id = None

    def _on_trap_triggered(self, event_data):
        """
        处理陷阱触发事件

        播放陷阱触发特效和音效

        Args:
            event_data: 事件数据
                - team: 队伍ID
                - trap_type: 陷阱类型
                - trigger_player: 触发玩家ID
        """
        team = event_data.get('team')

        # 只处理本预设对应的陷阱
        if team != self.team:
            return

        trap_type = event_data.get('trap_type')
        print("[INFO] [床预设-客户端] 陷阱触发: team={}, type={}".format(team, trap_type))

        # 播放陷阱触发特效 (根据陷阱类型)
        self._play_trap_effect(trap_type)

    # ========== 内部辅助方法 ==========

    def _create_bed_ornament(self, instance):
        """
        创建床装饰物特效

        在床上方显示团队图标或颜色标识

        Args:
            instance: PresetInstanceClient对象
        """
        # [FIX 2025-11-04] 修复PresetInstanceClient没有get_position()方法的问题
        position = instance.get_config("position") or instance.get_config("pos")
        if not position:
            print("[ERROR] [床预设-客户端] 无法获取position配置")
            return

        print("[INFO] [床预设-客户端] 创建装饰物: team={}, pos={}".format(
            self.team, position
        ))

        # TODO: 需要引擎API支持
        # 在床上方偏移位置创建装饰物特效
        # ornament_pos = {
        #     'x': position['x'],
        #     'y': position['y'] + 1.5,  # 床上方1.5格
        #     'z': position['z']
        # }
        #
        # # 根据队伍选择装饰物特效
        # effect_path = self._get_team_ornament_path(self.team)
        # self._ornament_effect_id = self._play_effect(effect_path, ornament_pos)

    def _play_bed_destroy_effect(self, position):
        # type: (tuple) -> None
        """
        播放床破坏特效

        P2.2功能实现 - 播放粒子飞溅效果

        Args:
            position: 床位置 (x, y, z)
        """
        try:
            from Script_NeteaseMod.systems.util.ClientAPIHelper import ClientAPIHelper

            print("[INFO] [床预设-客户端] 播放床破坏特效: pos={}".format(position))

            # 计算中心位置
            if isinstance(position, dict):
                center_pos = (
                    position['x'] + 0.5,
                    position['y'] + 0.5,
                    position['z'] + 0.5
                )
            else:
                center_pos = (
                    position[0] + 0.5,
                    position[1] + 0.5,
                    position[2] + 0.5
                )

            # 播放粒子飞溅效果（20个粒子）
            # 使用熔岩粒子（红色）模拟床破坏效果
            for i in range(20):
                particle_id = ClientAPIHelper.play_particle(
                    "minecraft:lava",  # 熔岩粒子（红色）
                    center_pos
                )
                if particle_id:
                    print("[INFO] [床预设-客户端] 播放床破坏粒子: id={}, pos={}".format(
                        particle_id, center_pos
                    ))

            print("[INFO] [床预设-客户端] 床破坏特效播放完成")

        except Exception as e:
            print("[ERROR] [床预设-客户端] 播放床破坏特效异常: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _play_bed_destroy_sound(self, position):
        # type: (tuple) -> None
        """
        播放床破坏音效

        P2.1功能实现

        Args:
            position: 床位置 (x, y, z)
        """
        try:
            import mod.client.extraClientApi as clientApi

            # 获取游戏组件
            game_comp = clientApi.GetEngineCompFactory().CreateGame(clientApi.GetLevelId())

            # 播放爆炸音效："random.explode" - 爆炸声音
            # 参数: (音效名称, 位置, 音量, 音调)
            game_comp.PlaySound(
                "random.explode",       # 音效名称
                position,               # 播放位置
                1.0,                    # 音量 (0.0-1.0)
                1.0                     # 音调 (0.5-2.0)
            )

            print("[INFO] [床预设-客户端] 播放床破坏音效: pos={}".format(position))

        except Exception as e:
            print("[ERROR] [床预设-客户端] 播放床破坏音效异常: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _play_trap_effect(self, trap_type):
        """
        播放陷阱触发特效

        Args:
            trap_type: 陷阱类型 (如: "alarm", "counter_offensive", "mining_fatigue")
        """
        print("[INFO] [床预设-客户端] 播放陷阱特效: type={}".format(trap_type))

        # TODO: 需要引擎API支持
        # 根据陷阱类型播放不同特效
        # trap_effects = {
        #     'alarm': 'particles/trap_alarm.json',
        #     'counter_offensive': 'particles/trap_counter.json',
        #     'mining_fatigue': 'particles/trap_fatigue.json'
        # }
        #
        # effect_path = trap_effects.get(trap_type)
        # if effect_path:
        #     # 在床位置播放特效
        #     position = self.instance.get_position()
        #     effect_id = self._play_effect(effect_path, position)
        #     self._effect_ids.append(effect_id)

    def _get_team_ornament_path(self, team):
        """
        获取队伍装饰物特效路径

        Args:
            team: 队伍ID

        Returns:
            str: 特效路径
        """
        # 根据队伍返回不同颜色的装饰物
        ornament_map = {
            'RED': 'particles/ornament_red.json',
            'BLUE': 'particles/ornament_blue.json',
            'GREEN': 'particles/ornament_green.json',
            'YELLOW': 'particles/ornament_yellow.json',
            'AQUA': 'particles/ornament_aqua.json',
            'WHITE': 'particles/ornament_white.json',
            'LIGHT_PURPLE': 'particles/ornament_purple.json',
            'GRAY': 'particles/ornament_gray.json',
        }

        return ornament_map.get(team, 'particles/ornament_default.json')

    # ========== 特效和音效工具方法 ==========

    def _play_effect(self, effect_path, position):
        """
        播放特效

        Args:
            effect_path: 特效文件路径
            position: 特效位置 (dict: {x, y, z})

        Returns:
            int: 特效ID
        """
        # TODO: 需要引擎API支持
        print("[INFO] 播放特效: {} at {}".format(effect_path, position))
        return 0  # 占位返回

    def _stop_effect(self, effect_id):
        """
        停止特效

        Args:
            effect_id: 特效ID
        """
        # TODO: 需要引擎API支持
        print("[INFO] 停止特效: {}".format(effect_id))

    def _stop_all_effects(self):
        """停止所有特效"""
        for effect_id in self._effect_ids:
            self._stop_effect(effect_id)
        self._effect_ids = []

    def _play_sound(self, sound_path, position, volume=1.0):
        """
        播放音效

        Args:
            sound_path: 音效文件路径
            position: 播放位置
            volume: 音量 (0.0-1.0)
        """
        # TODO: 需要引擎API支持
        print("[INFO] 播放音效: {} at {} (volume={})".format(
            sound_path, position, volume
        ))

    def _create_particle(self, particle_type, position):
        """
        创建粒子效果

        Args:
            particle_type: 粒子类型
            position: 粒子位置

        Returns:
            int: 粒子效果ID
        """
        # TODO: 需要引擎API支持
        print("[INFO] 创建粒子效果: {} at {}".format(particle_type, position))
        return 0  # 占位返回

    # ========== P1功能实现 ==========

    def _register_client_events(self, instance):
        """
        注册客户端事件监听

        P1功能: 客户端破坏保护
        监听客户端方块破坏事件,阻止玩家破坏己方的床
        """
        try:
            import mod.client.extraClientApi as clientApi

            # 获取客户端系统
            client_system = instance.manager.client_api
            if not client_system:
                print("[WARN] [床预设-客户端] 无法获取客户端系统，事件监听注册失败")
                return

            # 监听客户端方块破坏事件
            client_system.ListenForEvent(
                clientApi.GetEngineNamespace(),
                clientApi.GetEngineSystemName(),
                "StartDestroyBlockClientEvent",
                self,
                self._on_client_try_destroy_block
            )

            print("[INFO] [床预设-客户端] 客户端事件监听注册成功")

        except Exception as e:
            print("[ERROR] [床预设-客户端] 注册客户端事件失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _on_sync_bed_data(self, data):
        """
        接收服务端同步的床数据

        同步数据包括:
        - bed_blocks: 床方块坐标列表
        - player_to_team: 玩家-队伍映射
        - bed_destroyed: 床是否已破坏

        Args:
            data: 同步数据
        """
        self.bed_blocks = data.get('bed_blocks', [])
        self.player_to_team = data.get('player_to_team', {})
        self.bed_destroyed = data.get('bed_destroyed', False)

        print("[INFO] [床预设-客户端] 同步床数据: blocks={}, players={}, destroyed={}".format(
            len(self.bed_blocks),
            len(self.player_to_team),
            self.bed_destroyed
        ))

    def _on_client_try_destroy_block(self, event_data):
        """
        处理客户端玩家尝试破坏方块事件

        P1功能: 客户端破坏保护
        - 检查玩家是否在破坏床方块
        - 检查是否是自己队伍的床
        - 如果是，取消破坏并显示提示消息

        Args:
            event_data: 事件数据
                - playerId: 玩家ID
                - x, y, z: 方块坐标
                - cancel: 是否取消破坏（输出）
        """
        # 如果床已经被破坏，不需要保护
        if self.bed_destroyed:
            return

        # 获取方块坐标
        pos = (event_data.get('x'), event_data.get('y'), event_data.get('z'))

        # 检查是否是床方块
        if pos not in self.bed_blocks:
            return

        try:
            import mod.client.extraClientApi as clientApi

            # 获取本地玩家ID
            local_player_id = clientApi.GetLocalPlayerId()

            # 检查本地玩家是否在队伍映射中
            if local_player_id not in self.player_to_team:
                # 不在队伍中，阻止破坏
                event_data['cancel'] = True
                print("[INFO] [床预设-客户端] 玩家不在队伍中，阻止破坏床")
                return

            # 获取本地玩家的队伍
            player_team = self.player_to_team[local_player_id]

            # 如果是自己队伍的床，阻止破坏
            if player_team == self.team:
                event_data['cancel'] = True

                # 显示提示消息
                self._show_protect_tip_message(local_player_id)

                print("[INFO] [床预设-客户端] 阻止玩家破坏己方的床: team={}".format(self.team))

        except Exception as e:
            print("[ERROR] [床预设-客户端] 处理破坏事件失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _show_protect_tip_message(self, player_id):
        """
        显示床保护提示消息

        Args:
            player_id: 玩家ID
        """
        try:
            import mod.client.extraClientApi as clientApi

            # 获取游戏组件
            comp_factory = clientApi.GetEngineCompFactory()
            game_comp = comp_factory.CreateGame(clientApi.GetLevelId())

            # 显示提示消息 (使用ActionBar - 屏幕中央上方的文字)
            tip_message = "§c请务必保护好己方的床!"

            # 使用SetNotifyMsg显示提示（如果API可用）
            try:
                game_comp.SetNotifyMsg(tip_message, "§e提示")
            except:
                # 如果SetNotifyMsg不可用，尝试使用SetTipMessage
                try:
                    game_comp.SetTipMessage(tip_message)
                except:
                    # 如果都不可用，只打印日志
                    print("[INFO] [床预设-客户端] 提示消息: {}".format(tip_message))

        except Exception as e:
            print("[ERROR] [床预设-客户端] 显示提示消息失败: {}".format(str(e)))

    # ========== P1.2功能实现 ==========

    def _on_bed_blocks_placed(self, event_data, instance):
        """
        处理床方块放置完成事件

        P1.2功能：显示床上方的浮动文字提示
        - 显示"慎防开局偷家，保护队伍的床!"
        - 如果有装饰物提供者，显示感谢信息
        - 60秒后自动消失
        - 仅对本队玩家可见（老项目行为）

        Args:
            event_data: 事件数据
                - pos: 床的中心位置（由服务端发送）
                - team: 队伍ID
                - ornament_owner: 装饰物提供者名称（可选）
                - instance_id: 预设实例ID（用于过滤）
            instance: PresetInstanceClient对象
        """
        print("[INFO] [床预设-客户端] 收到bed_blocks_placed消息")

        # 获取床的位置和instance_id（由服务端在消息中发送）
        bed_pos = event_data.get('pos')
        bed_team = event_data.get('team')
        ornament_owner = event_data.get('ornament_owner')
        message_instance_id = event_data.get('instance_id')

        if not bed_pos:
            print("[ERROR] [床预设-客户端] 消息中缺少床位置信息，无法显示浮动文字")
            return

        # 修复：只响应本预设实例的消息（避免所有床都显示浮空文字）
        # 检查消息的instance_id是否与本预设实例匹配
        if message_instance_id and message_instance_id != instance.instance_id:
            return

        # 检查床的队伍是否与本预设的队伍匹配
        if bed_team != self.team:
            return

        # 修复：仅对本队玩家显示浮动文字（老项目行为）
        # 获取本地玩家所属队伍
        import mod.client.extraClientApi as clientApi
        local_player_id = clientApi.GetLocalPlayerId()
        player_team = self._get_player_team(local_player_id)

        if player_team and player_team != bed_team:
            return

        print("[INFO] [床预设-客户端] 所有检查通过，显示浮动文字提示")

        # 构建提示文字
        text = "§e§l慎防开局偷家，保护队伍的床!"
        if ornament_owner:
            text += "\n§b感谢 §e{} §b提供床的装饰".format(ornament_owner)

        # 创建浮动文字（传递床位置）
        self._show_floating_text_tip(text, bed_pos=bed_pos, duration_seconds=60)

    def _show_floating_text_tip(self, text, bed_pos, duration_seconds=60):
        # type: (str, tuple, int) -> None
        """
        在床上方显示浮动文字提示

        Args:
            text: 显示的文字内容（支持§格式化）
            bed_pos: 床的位置（tuple或list，由服务端发送）
            duration_seconds: 持续时间（秒），默认60秒
        """
        try:
            # 导入ClientAPIHelper
            from Script_NeteaseMod.systems.util.ClientAPIHelper import ClientAPIHelper

            if not bed_pos:
                print("[ERROR] [床预设-客户端] 无法获取床位置，浮动文字显示失败")
                return

            print("[INFO] [床预设-客户端] 使用床位置: {}".format(bed_pos))

            # 计算床上方位置
            # bed_pos可能是tuple(x,y,z)或list[x,y,z]
            floating_pos = (
                bed_pos[0] + 0.5,  # 床中心
                bed_pos[1] + 0.5,  # 床上方0.5格(原来1.5太高了)
                bed_pos[2] + 0.5   # 床中心
            )

            # 创建浮动文字
            self.floating_text_board_id = ClientAPIHelper.create_floating_text(
                text=text,
                pos=floating_pos,
                text_color=(1.0, 1.0, 1.0, 1.0),      # 白色文字
                board_color=(0.0, 0.0, 0.0, 0.3),     # 半透明黑色背景
                scale=(1.2, 1.2),                      # 放大1.2倍
                face_camera=True,                      # 始终朝向相机
                depth_test=False                       # 穿过方块显示
            )

            if self.floating_text_board_id:
                print("[INFO] [床预设-客户端] 创建浮动文字成功: board_id={}".format(
                    self.floating_text_board_id
                ))

                # 设置定时器，60秒后销毁浮动文字
                # 使用clientApi的游戏组件来添加定时器
                import mod.client.extraClientApi as clientApi
                comp_factory = clientApi.GetEngineCompFactory()
                game_comp = comp_factory.CreateGame(clientApi.GetLevelId())

                def destroy_callback():
                    self._cleanup_floating_text()
                    print("[INFO] [床预设-客户端] 浮动文字自动销毁（{}秒后）".format(duration_seconds))

                # 添加定时器(单位:秒)
                game_comp.AddTimer(duration_seconds, destroy_callback)
                print("[INFO] [床预设-客户端] 已设置浮动文字自动销毁定时器: {}秒".format(duration_seconds))
            else:
                print("[WARN] [床预设-客户端] 创建浮动文字失败")

        except Exception as e:
            print("[ERROR] [床预设-客户端] 显示浮动文字异常: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _get_player_team(self, player_id):
        """
        获取玩家所属队伍

        通过RoomManagementClientSystem获取

        Args:
            player_id: 玩家ID

        Returns:
            str: 队伍ID (RED, BLUE, etc.) 或 None
        """
        try:
            import mod.client.extraClientApi as clientApi
            from Script_NeteaseMod.modConfig import MOD_NAME

            # 获取RoomManagementClientSystem
            room_system = clientApi.GetSystem(MOD_NAME, "RoomManagementClientSystem")
            if room_system and hasattr(room_system, 'get_player_team'):
                team = room_system.get_player_team(player_id)
                return team
            else:
                print("[WARN] [床预设-客户端] RoomManagementClientSystem未找到或无get_player_team方法")
                return None
        except Exception as e:
            print("[ERROR] [床预设-客户端] 获取玩家队伍异常: {}".format(str(e)))
            return None

    def _cleanup_floating_text(self):
        """
        清理浮动文字和定时器

        P1.2功能辅助方法
        """
        try:
            # 销毁浮动文字
            if self.floating_text_board_id is not None:
                from Script_NeteaseMod.systems.util.ClientAPIHelper import ClientAPIHelper
                success = ClientAPIHelper.destroy_floating_text(self.floating_text_board_id)

                if success:
                    print("[INFO] [床预设-客户端] 浮动文字已清理: board_id={}".format(
                        self.floating_text_board_id
                    ))
                self.floating_text_board_id = None

            # 取消定时器
            if self.floating_text_timer is not None:
                import mod.client.extraClientApi as clientApi
                client_system = self.instance.manager.client_api
                if client_system:
                    try:
                        client_system.CancelTimer(self.floating_text_timer)
                    except:
                        pass
                self.floating_text_timer = None

        except Exception as e:
            print("[ERROR] [床预设-客户端] 清理浮动文字异常: {}".format(str(e)))
            import traceback
            traceback.print_exc()