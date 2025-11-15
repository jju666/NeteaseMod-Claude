# -*- coding: utf-8 -*-
"""
SpectatorSystem - 旁观者系统(客户端)

功能:
- 管理旁观者界面显示
- 切换观察目标
- 显示被观察玩家信息
- 快速切换按钮

原文件: Parts/ECSpectatorHUD/ECSpectatorHUDPart.py
重构为: systems/SpectatorSystem.py + ui/SpectatorHUD.py
"""

import mod.client.extraClientApi as clientApi


class SpectatorSystem(clientApi.GetClientSystemCls()):
    """
    旁观者系统(ClientSystem)

    核心职责:
    - 管理旁观者界面
    - 切换观察目标玩家
    - 显示被观察玩家信息(生命、装备、队伍)
    - 快速切换按钮

    重构说明:
    - 原ECSpectatorHUDPart继承PartBase
    - 现改为继承ClientSystem
    """

    def __init__(self, namespace, systemName):
        """
        初始化旁观者系统

        Args:
            namespace: 命名空间
            systemName: 系统名称
        """
        super(SpectatorSystem, self).__init__(namespace, systemName)

        # 中途加入按钮可见性
        self.join_button_visible = False

        # 旁观者HUD管理器
        self.spectator_hud = None

        # 本地玩家ID
        self.local_player_id = None

        # 当前观察的玩家
        self.current_target = None

        # 当前观察目标索引
        self.current_target_index = 0

        # 可观察的玩家列表(动态更新)
        self.available_targets = []

        # 是否处于旁观模式
        self.is_spectating = False

        print("[INFO] [SpectatorSystem] 初始化完成")

    # ========== ClientSystem生命周期 ==========

    def Create(self):
        """系统创建时调用"""
        self.LogInfo("SpectatorSystem.Create")

        # 获取本地玩家ID
        self.local_player_id = clientApi.GetLocalPlayerId()

        # 初始化旁观者HUD
        self._initialize_spectator_hud()

        # 注册事件监听
        self._register_events()

        print("[INFO] [SpectatorSystem] Create完成")

    def Destroy(self):
        """系统销毁时调用"""
        self.LogInfo("SpectatorSystem.Destroy")

        # 清理HUD
        if self.spectator_hud:
            self.spectator_hud.cleanup()
            self.spectator_hud = None

        print("[INFO] [SpectatorSystem] Destroy完成")

    def Update(self):
        """系统每帧更新"""
        # 更新HUD
        if self.spectator_hud and self.is_spectating:
            self.spectator_hud.update()

    # ========== 初始化 ==========

    def _initialize_spectator_hud(self):
        """初始化旁观者HUD"""
        try:
            from ui.SpectatorHUD import SpectatorHUD
            self.spectator_hud = SpectatorHUD(self)
            self.spectator_hud.initialize()
            self.LogInfo("旁观者HUD初始化完成")
        except Exception as e:
            self.LogError("旁观者HUD初始化失败: {}".format(str(e)))

    # ========== 事件注册 ==========

    def _register_events(self):
        """注册事件监听"""
        # 监听游戏模式变化
        self.ListenForEvent(
            clientApi.GetEngineNamespace(),
            clientApi.GetEngineSystemName(),
            'OnPlayerGameTypeChanged',
            self,
            self._on_game_type_changed
        )

        # 监听服务端响应中途加入结果
        self.ListenForEvent(
            self.namespace,
            self.systemName,
            'ServerResponseMidwayGameEvent',
            self,
            self._on_server_response_midway_game
        )

        # 监听服务端显示按钮事件
        self.ListenForEvent(
            self.namespace,
            self.systemName,
            'ServerShowJoinButtonVisible',
            self,
            self._on_server_show_join_button
        )

        # 监听服务端更新可观战玩家列表
        self.ListenForEvent(
            self.namespace,
            self.systemName,
            'ServerUpdateSpectatorTargets',
            self,
            self._on_update_spectator_targets
        )

        # 监听玩家输入事件(用于切换观战目标)
        # 注意: 需要使用LeftClickAttack和RightClickAttack事件
        # 但在旁观模式下,这些事件可能不会触发
        # 可以使用OnUseItemServerEvent或其他输入事件

        # 注: 观战目标切换通常使用物品栏物品点击实现
        # 这里暂时不监听输入事件,留待HUD实现时通过UI按钮触发

        self.LogInfo("旁观者事件监听已注册")

    # ========== 事件处理 ==========

    def _on_game_type_changed(self, args):
        """
        游戏模式变化事件

        Args:
            args: {'playerId': str, 'oldGameType': int, 'newGameType': int}
        """
        player_id = args.get('playerId')
        if player_id != self.local_player_id:
            return

        new_game_type = args.get('newGameType')

        # 检查是否切换到旁观模式
        import mod.client.extraClientApi as clientApi
        if new_game_type == clientApi.GetMinecraftEnum().GameType.SPECTATOR:
            self._enter_spectator_mode()
        else:
            self._exit_spectator_mode()

    # ========== 旁观模式控制 ==========

    def _enter_spectator_mode(self):
        """进入旁观模式"""
        self.is_spectating = True

        # 显示旁观者HUD
        if self.spectator_hud:
            self.spectator_hud.show()

        self.LogInfo("进入旁观模式")

    def _exit_spectator_mode(self):
        """退出旁观模式"""
        self.is_spectating = False

        # 隐藏旁观者HUD
        if self.spectator_hud:
            self.spectator_hud.hide()

        self.current_target = None

        self.LogInfo("退出旁观模式")

    # ========== 观察目标控制 ==========

    def switch_target(self, target_player_id):
        """
        切换观察目标

        Args:
            target_player_id (str): 目标玩家ID
        """
        self.current_target = target_player_id

        if self.spectator_hud:
            self.spectator_hud.update_target(target_player_id)

        self.LogInfo("切换观察目标 target={}".format(target_player_id))

    def next_target(self):
        """
        切换到下一个玩家

        使用方法:
        - 玩家右键点击时调用
        - 从当前目标切换到下一个存活的玩家
        """
        if not self.is_spectating or not self.available_targets:
            self.LogInfo("无法切换目标: 不在观战模式或无可用目标")
            return

        # 切换到下一个目标
        self.current_target_index = (self.current_target_index + 1) % len(self.available_targets)
        new_target = self.available_targets[self.current_target_index]

        # 切换观察目标
        self.switch_target(new_target)
        self.LogInfo("切换到下一个目标: {}".format(new_target))

    def previous_target(self):
        """
        切换到上一个玩家

        使用方法:
        - 玩家左键点击时调用
        - 从当前目标切换到上一个存活的玩家
        """
        if not self.is_spectating or not self.available_targets:
            self.LogInfo("无法切换目标: 不在观战模式或无可用目标")
            return

        # 切换到上一个目标
        self.current_target_index = (self.current_target_index - 1) % len(self.available_targets)
        new_target = self.available_targets[self.current_target_index]

        # 切换观察目标
        self.switch_target(new_target)
        self.LogInfo("切换到上一个目标: {}".format(new_target))

    def update_available_targets(self, target_ids):
        """
        更新可观察的玩家列表

        Args:
            target_ids (list): 玩家ID列表
        """
        self.available_targets = target_ids

        # 更新HUD显示
        if self.spectator_hud:
            self.spectator_hud.update_player_list(target_ids)

        self.LogInfo("更新可观察玩家列表: {} 个玩家".format(len(target_ids)))

        # 如果当前目标不在新列表中,切换到第一个目标
        if self.current_target not in target_ids and target_ids:
            self.current_target_index = 0
            self.switch_target(target_ids[0])

    # ========== 中途加入游戏功能 ==========

    def _on_server_response_midway_game(self, args):
        """
        处理服务端响应中途加入结果

        Args:
            args: {'res': bool}  # True=成功, False=失败
        """
        success = args.get('res', False)

        if not success:
            # 加入失败,重新显示按钮
            self.join_button_visible = True
            self.LogInfo("中途加入游戏失败,按钮重新显示")
        else:
            # 加入成功,按钮保持隐藏
            self.join_button_visible = False
            self.LogInfo("中途加入游戏成功")

    def _on_server_show_join_button(self, args):
        """
        处理服务端显示按钮事件

        当服务端通知可以中途加入时显示按钮
        """
        self.join_button_visible = True
        self.LogInfo("显示中途加入按钮")

    def _on_update_spectator_targets(self, args):
        """
        处理服务端更新可观战玩家列表事件

        Args:
            args: {'player_ids': list}
        """
        player_ids = args.get('player_ids', [])
        self.update_available_targets(player_ids)
        self.LogInfo("收到服务端更新观战目标列表: {} 个玩家".format(len(player_ids)))

    def client_send_request_midway_game(self):
        """
        客户端发送请求中途加入游戏事件

        当玩家点击"参战"按钮时调用
        """
        # 立即隐藏按钮,防止重复点击
        self.join_button_visible = False

        # 发送请求到服务端
        self.NotifyToServer('ClientRequestMidwayGameEvent', {
            'player_id': self.local_player_id
        })

        self.LogInfo("已发送中途加入请求")
