# -*- coding: utf-8 -*-
"""
GamingStateSystem - 游戏状态机系统(服务端)

功能:
- 管理游戏状态机生命周期
- 提供状态机与ServerSystem的桥接
- 替代原GamingStatePart,移除对Preset系统的依赖

原文件: Parts/GamingState/GamingStatePart.py
重构为: systems/GamingStateSystem.py
"""

import mod.server.extraServerApi as serverApi
if False:
    from state.RootGamingState import RootGamingState


class GamingStateSystem(serverApi.GetServerSystemCls()):
    """
    游戏状态机系统(ServerSystem)

    核心职责:
    - 管理RootGamingState状态机实例
    - 提供状态机所需的引擎API访问
    - 驱动状态机tick更新

    重构说明:
    - 原GamingStatePart继承自PartBase(Preset系统)
    - 现改为继承ServerSystem,移除Preset依赖
    - 状态机核心逻辑(GamingState)保持不变
    """

    def __init__(self, namespace, systemName):
        """
        初始化游戏状态机系统

        Args:
            namespace: 命名空间
            systemName: 系统名称
        """
        super(GamingStateSystem, self).__init__(namespace, systemName)

        # 保存namespace和systemName供后续使用
        self.namespace = namespace
        self.systemName = systemName

        # 状态机实例
        self.root_state = None  # type: RootGamingState | None

        # 缓存的玩家对象
        self.cached_better_players = {}  # type: dict[str, BetterPlayerObject]

        # 待设置的朝向信息(维度切换后设置)
        self._pending_rotations = {}  # player_id -> rotation

        # 组件工厂
        self.comp_factory = serverApi.GetEngineCompFactory()

        # 定时器管理
        self.timers = {}  # {timer_id: timer_callback}

        # 注意: 不在这里调用Create(),引擎会自动调用System的Create方法
        # 如果在__init__中调用Create(),会导致:
        # 1. 子类无法在super().__init__()之后注册事件(因为Create已经执行完了)
        # 2. 子类如果在super().__init__()之前注册事件,会因为父类还未初始化而报错

    # ========== ServerSystem生命周期 ==========

    def Create(self):
        """系统创建时调用"""
        self.LogInfo("GamingStateSystem.Create")

        # 导入RootGamingState
        from state.RootGamingState import RootGamingState

        # 创建根状态机
        self.root_state = RootGamingState(self)

        # 注册引擎事件 - 使用super()避免访问mNamespace
        super(GamingStateSystem, self).ListenForEvent(
            serverApi.GetEngineNamespace(),
            serverApi.GetEngineSystemName(),
            'DelServerPlayerEvent',
            self,
            self._on_del_server_player
        )

        # 注册维度切换完成事件
        super(GamingStateSystem, self).ListenForEvent(
            serverApi.GetEngineNamespace(),
            serverApi.GetEngineSystemName(),
            'DimensionChangeFinishServerEvent',
            self,
            self._on_dimension_change_finish
        )

        # 注册自定义事件 - 使用super()避免访问mNamespace
        super(GamingStateSystem, self).ListenForEvent(
            self.namespace,  # 使用保存的namespace
            self.systemName,  # 使用保存的systemName
            'S2CPlaySoundEvent',
            self,
            self._on_play_sound_event
        )

        # 注册玩家命令事件 - 用于测试命令
        super(GamingStateSystem, self).ListenForEvent(
            serverApi.GetEngineNamespace(),
            serverApi.GetEngineSystemName(),
            'CommandEvent',
            self,
            self._on_player_command
        )

    def Destroy(self):
        """系统销毁时调用"""
        self.LogInfo("GamingStateSystem.Destroy")

        # 停止状态机
        if self.root_state:
            try:
                self.root_state.stop()
            except Exception as e:
                self.LogError("停止状态机失败: {}".format(str(e)))
            self.root_state = None

        # 清理缓存
        self.cached_better_players = {}

    def Update(self):
        """系统每帧更新 - 驱动状态机tick"""
        if self.root_state:
            try:
                self.root_state.tick()
            except Exception as e:
                self.LogError("状态机tick失败: {}".format(str(e)))
                import traceback
                traceback.print_exc()

    # ========== 事件处理 ==========

    def _on_del_server_player(self, args):
        """
        处理玩家离开事件

        Args:
            args: 事件参数 {'id': player_id}
        """
        player_id = args.get('id')
        if player_id in self.cached_better_players:
            self.cached_better_players.pop(player_id)

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

        self.LogInfo("[DEBUG] 玩家 {} 维度切换完成 ({}->{}), 位置: {}".format(
            player_id, from_dim, to_dim, to_pos
        ))

        # 检查是否有待处理的朝向信息
        if player_id in self._pending_rotations:
            rot = self._pending_rotations[player_id]

            try:
                # 设置玩家朝向
                pos_comp = self.comp_factory.CreatePos(player_id)
                pos_comp.SetRot(rot)

                self.LogInfo("[DEBUG] 玩家 {} 已设置朝向: {}".format(player_id, rot))

                # 清理已处理的朝向信息
                del self._pending_rotations[player_id]

            except Exception as e:
                self.LogError("设置玩家朝向失败: {}".format(e))
                import traceback
                traceback.print_exc()

        # [FIX 2025-11-08] 通知当前状态:玩家维度切换完成
        # 这样状态可以在所有玩家到达目标维度后再执行后续操作(如生成NPC)
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

    def _on_play_sound_event(self, args):
        """
        处理播放音效事件(仅服务端记录)

        Args:
            args: 事件参数
                - player_id: 玩家ID
                - sound: 音效名称
                - pos: 位置
                - volume: 音量
                - pitch: 音调
                - loop: 是否循环
        """
        # 服务端不处理音效播放,仅作为转发到客户端的桥接
        pass

    # ========== 玩家对象管理 ==========

    def get_all_better_players(self):
        """
        获取所有在线的玩家对象

        Returns:
            list[BetterPlayerObject]: 所有在线的玩家对象
        """
        from util.BetterPlayerObject import BetterPlayerObject

        players = []
        # 使用serverApi.GetPlayerList()获取所有玩家ID
        player_ids = serverApi.GetPlayerList()

        for player_id in player_ids:
            players.append(self.get_better_player_obj(player_id))

        return players

    def get_better_player_obj(self, player_id):
        """
        获取玩家对象(封装了常用API)

        Args:
            player_id (str): 玩家ID

        Returns:
            BetterPlayerObject: 玩家对象
        """
        from util.BetterPlayerObject import BetterPlayerObject

        # 不使用缓存,每次创建新对象(避免状态不同步)
        player_obj = BetterPlayerObject(self, player_id)
        return player_obj

    # ========== 引擎API封装 ==========

    def GetLevelId(self):
        """
        获取世界ID

        Returns:
            str: 世界ID
        """
        return serverApi.GetLevelId()

    def GetLocalPlayerId(self):
        """
        获取本地玩家ID(服务端不适用,返回None)

        Returns:
            None
        """
        return None

    def GetNamespace(self):
        """
        获取系统命名空间

        Returns:
            str: 命名空间
        """
        return self.namespace

    def GetSystemName(self):
        """
        获取系统名称

        Returns:
            str: 系统名称
        """
        return self.systemName

    def LogInfo(self, message):
        """
        记录Info日志

        Args:
            message (str): 日志消息
        """
        print("[INFO] [GamingStateSystem] {}".format(message))

    def LogDebug(self, message):
        """
        记录Debug日志

        Args:
            message (str): 日志消息
        """
        pass

    def LogError(self, message):
        """
        记录Error日志

        Args:
            message (str): 日志消息
        """
        print("[ERROR] [GamingStateSystem] {}".format(message))

    def LogWarn(self, message):
        """
        记录Warn日志

        Args:
            message (str): 日志消息
        """
        print("[WARN] [GamingStateSystem] {}".format(message))

    # 为了兼容性，添加LogWarning别名
    def LogWarning(self, message):
        """LogWarn的别名"""
        self.LogWarn(message)

    def GetSystem(self, namespace, systemName):
        """
        获取其他系统的引用

        Args:
            namespace (str): 命名空间
            systemName (str): 系统名称

        Returns:
            System: 系统实例，如果不存在返回None
        """
        try:
            import mod.server.extraServerApi as serverApi
            # 使用引擎API获取系统
            level_id = serverApi.GetLevelId()
            system = serverApi.GetSystem(namespace, systemName)
            return system
        except Exception as e:
            self.LogError("GetSystem失败 namespace={} systemName={}: {}".format(
                namespace, systemName, str(e)))
            return None

    # ========== 事件监听/触发 (兼容原Part API) ==========

    def ListenForEvent(self, namespace, systemName, eventName, instance, callback):
        """
        监听事件(转发到ServerSystem的ListenForEvent)

        Args:
            namespace (str): 命名空间
            systemName (str): 系统名称
            eventName (str): 事件名称
            instance: 实例对象
            callback: 回调函数
        """
        # 正确的实现:调用父类ServerSystem的ListenForEvent
        super(GamingStateSystem, self).ListenForEvent(namespace, systemName, eventName, instance, callback)

    def UnListenForEvent(self, namespace, systemName, eventName, instance, callback):
        """
        取消监听事件

        Args:
            namespace (str): 命名空间
            systemName (str): 系统名称
            eventName (str): 事件名称
            instance: 实例对象
            callback: 回调函数
        """
        self.UnNotifyToModServer(eventName, callback)

    def ListenSelfEvent(self, eventName, instance, callback):
        """
        监听自定义事件

        Args:
            eventName (str): 事件名称
            instance: 实例对象
            callback: 回调函数
        """
        self.NotifyToModServer(eventName, callback)

    def UnListenSelfEvent(self, eventName, instance, callback):
        """
        取消监听自定义事件

        Args:
            eventName (str): 事件名称
            instance: 实例对象
            callback: 回调函数
        """
        self.UnNotifyToModServer(eventName, callback)

    def NotifyToModServer(self, eventName, callback):
        """
        注册服务端事件监听

        Args:
            eventName (str): 事件名称
            callback: 回调函数
        """
        super(GamingStateSystem, self).ListenForEvent(
            self.GetNamespace(),
            self.GetSystemName(),
            eventName,
            self,
            callback
        )

    def UnNotifyToModServer(self, eventName, callback):
        """
        取消服务端事件监听

        Args:
            eventName (str): 事件名称
            callback: 回调函数
        """
        super(GamingStateSystem, self).UnListenForEvent(
            self.GetNamespace(),
            self.GetSystemName(),
            eventName,
            self,
            callback
        )

    # ========== 消息广播工具方法 ==========

    @staticmethod
    def format_text(raw_msg, **args):
        """
        格式化文本,支持颜色代码和变量替换

        Args:
            raw_msg (str): 原始消息
            **args: 变量参数

        Returns:
            str: 格式化后的消息
        """
        replacements = {
            # 基础格式
            "enter": "\n",
            # 颜色代码
            "black": u"\u00A70",
            "dark-blue": u"\u00A71",
            "dark-green": u"\u00A72",
            "dark-aqua": u"\u00A73",
            "dark-red": u"\u00A74",
            "dark-purple": u"\u00A75",
            "gold": u"\u00A76",
            "gray": u"\u00A77",
            "dark-gray": u"\u00A78",
            "blue": u"\u00A79",
            "green": u"\u00A7a",
            "aqua": u"\u00A7b",
            "red": u"\u00A7c",
            "light-purple": u"\u00A7d",
            "yellow": u"\u00A7e",
            "white": u"\u00A7f",
            "obfuscated": u"\u00A7k",
            "bold": u"\u00A7l",
            "italic": u"\u00A7o",
            "reset": u"\u00A7r",

            # ========== 图标占位符映射 (从老项目迁移) ==========
            # 通用图标
            "icon-heart": u"\uE110",
            # 游戏手柄图标
            "icon-gamepad-a": u"\uE000",
            "icon-gamepad-b": u"\uE001",
            "icon-gamepad-x": u"\uE002",
            "icon-gamepad-y": u"\uE003",
            "icon-gamepad-lb": u"\uE004",
            "icon-gamepad-rb": u"\uE005",
            "icon-gamepad-lt": u"\uE006",
            "icon-gamepad-rt": u"\uE007",
            # EC系统图标
            "icon-ec-lobby": u"\uE0B0",
            "icon-ec-room": u"\uE0B1",
            "icon-ec-buglet": u"\uE0B2",
            "icon-ec-admin": u"\uE0B3",
            "icon-ec-mission": u"\uE0B4",
            "icon-ec-prefix-vip3": u"\uE0B6",
            "icon-ec-prefix-vip4": u"\uE0B7",
            "icon-ec-buglet-red": u"\uE0B8",
            # EC UI图标
            "icon-ec-players": u"\uE180",
            "icon-ec-rooms": u"\uE181",
            "icon-ec-time": u"\uE182",
            "icon-ec-crystal-destroy": u"\uE183",
            "icon-ec-sword0": u"\uE184",
            "icon-ec-death": u"\uE185",
            "icon-ec-sword1": u"\uE186",
            "icon-ec-sword2": u"\uE187",
            "icon-ec-heart": u"\uE188",
            "icon-ec-mm-villager": u"\uE189",
            "icon-ec-mm-killer": u"\uE18A",
            "icon-ec-mm-spy": u"\uE18B",
            "icon-ec-mm-bow": u"\uE18C",
            # EC水晶图标（队伍标识-红黄绿蓝）
            "icon-ec-crystal-red": u"\uE190",
            "icon-ec-crystal-red-died": u"\uE1A0",
            "icon-ec-crystal-yellow": u"\uE191",
            "icon-ec-crystal-yellow-died": u"\uE1A1",
            "icon-ec-crystal-green": u"\uE192",
            "icon-ec-crystal-green-died": u"\uE1A2",
            "icon-ec-crystal-blue": u"\uE193",
            "icon-ec-crystal-blue-died": u"\uE1A3",
            # EC羊毛图标（队伍标识-8色）
            "icon-ec-wool-red": u"\uE194",
            "icon-ec-wool-red-died": u"\uE1A4",
            "icon-ec-wool-yellow": u"\uE195",
            "icon-ec-wool-yellow-died": u"\uE1A5",
            "icon-ec-wool-green": u"\uE196",
            "icon-ec-wool-green-died": u"\uE1A6",
            "icon-ec-wool-blue": u"\uE197",
            "icon-ec-wool-blue-died": u"\uE1A7",
            "icon-ec-wool-aqua": u"\uE1B4",
            "icon-ec-wool-aqua-died": u"\uE1C4",
            "icon-ec-wool-white": u"\uE1B5",
            "icon-ec-wool-white-died": u"\uE1C5",
            "icon-ec-wool-light-purple": u"\uE1B6",
            "icon-ec-wool-light-purple-died": u"\uE1C6",
            "icon-ec-wool-gray": u"\uE1B7",
            "icon-ec-wool-gray-died": u"\uE1C7",
            "icon-ec-wool-dark-purple": u"\uE1B8",
            "icon-ec-wool-dark-purple-died": u"\uE1C8",
            "icon-ec-wool-gold": u"\uE1B9",
            "icon-ec-wool-gold-died": u"\uE1C9",
            "icon-ec-wool-dark-green": u"\uE1BA",
            "icon-ec-wool-dark-green-died": u"\uE1CA",
            "icon-ec-wool-dark-blue": u"\uE1BB",
            "icon-ec-wool-dark-blue-died": u"\uE1CB",
            # EC游戏道具图标
            "icon-ec-sword3": u"\uE198",
            "icon-ec-chest": u"\uE199",
            "icon-ec-potion": u"\uE19A",
            "icon-ec-magnify": u"\uE19B",
            "icon-ec-block": u"\uE19C",
            "icon-ec-key": u"\uE19D",
            "icon-ec-diamond": u"\uE19E",
            # EC货币图标
            "icon-ec-coin": u"\uE19F",
            "icon-ec-coin-mw": u"\uE18D",
            "icon-ec-coin-mm": u"\uE18E",
            "icon-ec-coin-ruby": u"\uE18F",
            # EC其他UI图标
            "icon-ec-ball": u"\uE1A8",
            "icon-ec-star": u"\uE1A9",
            "icon-ec-star-empty": u"\uE1AA",
            # EC资源图标
            "icon-ec-res-copper": u"\uE1AB",
            "icon-ec-res-iron": u"\uE1AC",
            "icon-ec-res-gold": u"\uE1AD",
            "icon-ec-res-diamond": u"\uE1AE",
            "icon-ec-res-emerald": u"\uE1AF",
            "icon-ec-res-snowflake": u"\uE1C0",
            # EC资源图标别名（简化版）
            "icon-ec-iron": u"\uE1AC",
            "icon-ec-gold": u"\uE1AD",
            "icon-ec-diamond": u"\uE1AE",
            "icon-ec-emerald": u"\uE1AF",
            # EC状态图标
            "icon-ec-ok": u"\uE1B0",
            "icon-ec-fail": u"\uE1B1",
            "icon-ec-up": u"\uE1B2",
            "icon-ec-credits": u"\uE1B3",
            # EC数字图标
            "icon-ec-0": u"\uE1F0",
            "icon-ec-1": u"\uE1F1",
            "icon-ec-2": u"\uE1F2",
            "icon-ec-3": u"\uE1F3",
            "icon-ec-4": u"\uE1F4",
            "icon-ec-5": u"\uE1F5",
            "icon-ec-6": u"\uE1F6",
            "icon-ec-7": u"\uE1F7",
            "icon-ec-8": u"\uE1F8",
            "icon-ec-9": u"\uE1F9",
            "icon-ec-percent": u"\uE1FA",
            "icon-ec-percent-black": u"\uE1FB",
            # 特殊字符
            "|": u"\u00A6",
            "»": u"\u226B",
            "«": u"\u226A"
        }

        for arg in replacements:
            replacement_str = replacements[arg]
            raw_msg = raw_msg.replace("{" + arg + "}", replacement_str)

        for arg in args:
            arg_str = args[arg]
            if not isinstance(arg_str, str):
                arg_str = str(arg_str)
            raw_msg = raw_msg.replace("{" + arg + "}", arg_str)

        return raw_msg

    def broadcast_message(self, message, color='\xc2\xa7f'):
        """
        广播消息到所有玩家 - 使用SetNotifyMsg API

        Args:
            message (str): 消息内容
            color (str): 颜色代码 (\xc2\xa7f=白色, \xc2\xa7e=黄色, \xc2\xa7c=红色等)
                        使用UTF-8编码格式 '\xc2\xa7f'

        注意: SetNotifyMsg不支持私有Unicode字符(如\uE185图标)，这些字符会被自动过滤
        """
        try:
            # 关键：将Unicode字符串编码为UTF-8字节串（与老项目format_text一致）
            # Python 2.7中，SetNotifyMsg需要UTF-8编码的str类型，而非unicode类型
            # 保留所有字符：图标、颜色代码、中文等（资源包中有glyph_E0.png等字形文件支持图标）
            if isinstance(message, unicode):
                message_bytes = message.encode('utf-8')
            else:
                message_bytes = message

            # 使用SetNotifyMsg广播消息给所有玩家
            game_comp = self.comp_factory.CreateGame(self.GetLevelId())
            result = game_comp.SetNotifyMsg(message_bytes, color)

            if not result:
                self.LogWarn("broadcast_message失败: message='{}'".format(repr(message)))

        except Exception as e:
            self.LogError("broadcast_message失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _get_all_player_ids(self):
        """获取所有在线玩家ID列表"""
        try:
            # 使用serverApi.GetPlayerList()获取所有维度中的全部玩家
            player_ids = serverApi.GetPlayerList()
            self.LogInfo("[DEBUG] _get_all_player_ids(serverApi.GetPlayerList): {} 个玩家".format(len(player_ids)))

            if len(player_ids) > 0:
                return player_ids

            # 如果API返回空列表，尝试从缓存的玩家对象中获取
            self.LogInfo("[DEBUG] GetPlayerList返回0个玩家，尝试从缓存获取")
            cached_ids = list(self.cached_better_players.keys())
            self.LogInfo("[DEBUG] _get_all_player_ids(cached_better_players): {} 个玩家".format(len(cached_ids)))
            return cached_ids

        except Exception as e:
            self.LogError("[DEBUG] _get_all_player_ids失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()
            return []

    def broadcast_tip(self, tip):
        """
        广播提示消息到所有玩家

        Args:
            tip (str): 提示内容
        """
        try:
            game_comp = self.comp_factory.CreateGame(self.GetLevelId())
            game_comp.SetTipMessage(tip)
        except Exception as e:
            self.LogError("broadcast_tip失败: {}".format(str(e)))

    def broadcast_popup(self, popup, sub):
        """
        广播弹窗提示到所有玩家

        Args:
            popup (str): 主提示
            sub (str): 副提示
        """
        try:
            game_comp = self.comp_factory.CreateGame(self.GetLevelId())
            game_comp.SetPopupNotice(popup, sub)
        except Exception as e:
            self.LogError("broadcast_popup失败: {}".format(str(e)))

    def broadcast_actionbar(self, text):
        """
        广播ActionBar到所有玩家

        Args:
            text (str): 文本内容
        """
        try:
            command_comp = self.comp_factory.CreateCommand(self.GetLevelId())
            command_comp.SetCommand("title @a actionbar {}".format(text))
        except Exception as e:
            self.LogError("broadcast_actionbar失败: {}".format(str(e)))

    def broadcast_title_reset(self):
        """重置所有玩家的Title"""
        try:
            command_comp = self.comp_factory.CreateCommand(self.GetLevelId())
            command_comp.SetCommand("title @a reset")
        except Exception as e:
            self.LogError("broadcast_title_reset失败: {}".format(str(e)))

    def broadcast_title_times(self, fadein=20, duration=20, fadeout=5):
        """
        设置Title的显示时间

        Args:
            fadein (int): 淡入时间(ticks)
            duration (int): 保持时间(ticks)
            fadeout (int): 淡出时间(ticks)
        """
        try:
            if fadein is None:
                fadein = 20
            if duration is None:
                duration = 20
            if fadeout is None:
                fadeout = 5
            command_comp = self.comp_factory.CreateCommand(self.GetLevelId())
            command_comp.SetCommand("title @a times {} {} {}".format(fadein, duration, fadeout))
        except Exception as e:
            self.LogError("broadcast_title_times失败: {}".format(str(e)))

    def broadcast_title(self, title, sub_title=None, fadein=None, duration=None, fadeout=None):
        """
        广播Title到所有玩家

        Args:
            title (str): 主标题
            sub_title (str): 副标题(可选)
            fadein (int): 淡入时间(ticks,可选)
            duration (int): 保持时间(ticks,可选)
            fadeout (int): 淡出时间(ticks,可选)
        """
        try:
            command_comp = self.comp_factory.CreateCommand(self.GetLevelId())

            if fadein is not None or duration is not None or fadeout is not None:
                self.broadcast_title_times(fadein, duration, fadeout)
            else:
                command_comp.SetCommand("title @a reset")

            if sub_title is not None:
                command_comp.SetCommand("title @a subtitle {}".format(sub_title))

            command_comp.SetCommand("title @a title {}".format(title))
        except Exception as e:
            self.LogError("broadcast_title失败: {}".format(str(e)))

    # ========== HUD事件广播 ==========

    def broadcast_hud_event(self, hud_type, events, player_id=None):
        """
        广播HUD事件到客户端

        Args:
            hud_type (str): HUD类型 ('stack_msg_top' | 'stack_msg_bottom' | 'scoreboard')
            events (list): 事件列表，每个事件是字典 {'event': str, 'key': str, 'value': str}
            player_id (str, optional): 指定玩家ID，如果为None则广播给所有玩家

        事件通信说明:
            - 事件发送者: 调用此方法的System（通常是RoomManagementSystem）
            - 事件接收者: ECHUDScreenNode（客户端UI）
            - 通信路径: RoomManagementSystem → BroadcastToAllClient → ECHUDScreenNode.ListenForEvent
            - 客户端需要监听: ListenForEvent(MOD_NAME, "RoomManagementSystem", "HUDControlEvent")
        """
        try:
            event_data = {
                'type': hud_type,
                'events': events
            }

            if player_id:
                # 发送给指定玩家
                # NotifyToClient会自动使用当前System的namespace和systemName作为发送者
                event_data['playerId'] = player_id
                self.NotifyToClient(player_id, 'HUDControlEvent', event_data)
            else:
                # 广播给所有玩家
                # BroadcastToAllClient会自动使用当前System的namespace和systemName作为发送者
                self.BroadcastToAllClient('HUDControlEvent', event_data)

        except Exception as e:
            self.LogError("broadcast_hud_event失败: {}".format(str(e)))

    def broadcast_preset_event(self, event_name, event_data):
        """
        广播预设事件(兼容老项目API)

        通过ECPreset的EventBus发布事件，所有订阅了该事件的预设都会收到通知。
        这是为了兼容老项目中使用的BroadcastPresetSystemEvent接口。

        **重要**：使用发布-订阅模式，只向EventBus发布一次事件，EventBus会自动
        通知所有订阅者。避免遍历预设列表多次发布（会导致事件被发布N次的bug）。

        Args:
            event_name (str): 事件名称
                常用事件: 'BedWarsRunning' (游戏开始), 'BedWarsEnding' (游戏结束)
            event_data (dict): 事件数据，传递给订阅者的参数

        用法示例:
            # 通知所有预设游戏已开始
            system.broadcast_preset_event("BedWarsRunning", {})

            # 通知所有预设游戏已结束，并传递胜利队伍信息
            system.broadcast_preset_event("BedWarsEnding", {"winner": "RED"})

        技术细节:
            - 使用 preset_mgr.event_bus.publish() 直接发布到EventBus
            - EventBus内部维护订阅者列表，自动通知所有订阅者
            - 每个预设通过 instance.subscribe_event() 订阅感兴趣的事件
            - 发布-订阅模式确保解耦，预设之间不直接依赖

        历史Bug修复 (2025-11-04):
            修复前：遍历所有预设，每个预设调用 publish_event()
            问题：导致事件被发布N次（N=预设数量），触发重复响应
            症状：床预设收到26次BedWarsRunning事件，创建26个重复的浮动文字面板
            修复后：直接调用 event_bus.publish() 一次，所有订阅者自动收到
        """
        try:
            # [P0-1 FIX] 向ECPreset EventBus发布事件
            from ECPresetServerScripts import get_server_mgr

            preset_mgr = get_server_mgr("bedwars_room")
            if preset_mgr:
                # [CRITICAL FIX 2025-11-04] 只向EventBus发布一次事件
                # 直接调用 event_bus.publish()，而不是遍历预设调用 preset_instance.publish_event()
                # 这是发布-订阅模式的正确用法：发布者只发布一次，EventBus负责分发给所有订阅者
                try:
                    preset_mgr.event_bus.publish(event_name, event_data)
                    all_presets = preset_mgr.get_all_presets()
                    self.LogDebug("broadcast_preset_event: {} 已发布到EventBus ({} 个预设可接收)".format(
                        event_name, len(all_presets)
                    ))
                except Exception as e:
                    self.LogError("向EventBus发布事件{}失败: {}".format(event_name, str(e)))
            else:
                self.LogWarn("ECPreset管理器未初始化,无法广播事件: {}".format(event_name))

        except Exception as e:
            self.LogError("broadcast_preset_event失败: {}".format(str(e)))
            import traceback
            print(traceback.format_exc())

    # 为了兼容老项目API，添加大写字母开头的别名
    def BroadcastPresetSystemEvent(self, event_name, event_data):
        """broadcast_preset_event的别名(兼容老项目命名风格)"""
        return self.broadcast_preset_event(event_name, event_data)

    def update_stack_msg_top(self, key, value, player_id=None):
        """
        更新顶部堆叠消息

        Args:
            key (str): 消息键
            value (str): 消息值
            player_id (str, optional): 指定玩家ID，如果为None则广播给所有玩家
        """
        events = [
            {
                'event': 'add_or_set',
                'key': key,
                'value': value
            }
        ]
        self.broadcast_hud_event('stack_msg_top', events, player_id)

    def update_stack_msg_bottom(self, key, value, player_id=None):
        """
        更新底部堆叠消息

        Args:
            key (str): 消息键
            value (str): 消息值
            player_id (str, optional): 指定玩家ID，如果为None则广播给所有玩家
        """
        events = [
            {
                'event': 'add_or_set',
                'key': key,
                'value': value
            }
        ]
        self.broadcast_hud_event('stack_msg_bottom', events, player_id)

    def clear_stack_msg_top(self, key=None, player_id=None):
        """
        清除顶部堆叠消息

        Args:
            key (str, optional): 消息键，如果为None则清除所有
            player_id (str, optional): 指定玩家ID
        """
        events = [
            {
                'event': 'remove' if key else 'clear',
                'key': key if key else ''
            }
        ]
        self.broadcast_hud_event('stack_msg_top', events, player_id)

    def clear_stack_msg_bottom(self, key=None, player_id=None):
        """
        清除底部堆叠消息

        Args:
            key (str, optional): 消息键，如果为None则清除所有
            player_id (str, optional): 指定玩家ID
        """
        events = [
            {
                'event': 'remove' if key else 'clear',
                'key': key if key else ''
            }
        ]
        self.broadcast_hud_event('stack_msg_bottom', events, player_id)

    # ========== 定时器管理 ==========

    def add_timer(self, delay, callback, repeat=False):
        """
        添加定时器

        Args:
            delay (float): 延迟时间(秒)
            callback (function): 回调函数
            repeat (bool): 是否重复执行

        Returns:
            int: 定时器ID
        """
        try:
            game_comp = self.comp_factory.CreateGame(self.GetLevelId())

            def timer_wrapper(*args):
                """定时器包装器(接受可变参数)"""
                try:
                    callback()
                except Exception as e:
                    self.LogError("定时器回调执行失败: {}".format(str(e)))
                    import traceback
                    traceback.print_exc()

            # 使用引擎的AddTimer
            game_comp.AddTimer(delay, timer_wrapper, repeat)
            return True
        except Exception as e:
            self.LogError("添加定时器失败: {}".format(str(e)))
            return False

    def remove_timer(self, timer_id):
        """
        移除定时器

        Args:
            timer_id: 定时器ID

        Returns:
            bool: 是否成功
        """
        try:
            game_comp = self.comp_factory.CreateGame(self.GetLevelId())
            game_comp.CancelTimer(timer_id)
            if timer_id in self.timers:
                del self.timers[timer_id]
            return True
        except Exception as e:
            self.LogError("移除定时器失败: {}".format(str(e)))
            return False

    # ========== 测试命令 ==========

    def _on_player_command(self, args):
        """
        处理玩家命令事件（用于测试）

        Args:
            args: {
                'entityId': str,    # 玩家ID
                'command': str,     # 命令字符串
                'cancel': bool      # 是否取消命令
            }
        """
        try:
            player_id = args.get('entityId')
            command = args.get('command', '')

            if not player_id or not command:
                return

            # 解析命令
            parts = command.split(' ')
            if len(parts) == 0:
                return

        except Exception as e:
            self.LogError("处理命令事件失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _get_player_name(self, player_id):
        """获取玩家昵称"""
        try:
            comp = self.comp_factory.CreateName(player_id)
            name = comp.GetName()
            return name if name else str(player_id)
        except Exception as e:
            self.LogError("获取玩家昵称失败: player_id={}, error={}".format(player_id, str(e)))
            return str(player_id)