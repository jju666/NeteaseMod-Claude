# -*- coding: utf-8 -*-
"""
HUDSystem - HUD显示系统(客户端)

功能:
- 简单的HUD管理系统
- ECHUDScreenNode自己处理所有UI逻辑
- HUDSystem只用于获取本地玩家信息

原文件: Parts/ECHUD/ECHUDPart.py + ECHUDScreenNode.py
重构为: systems/HUDSystem.py + ui/ECHUDScreenNode.py
"""

import mod.client.extraClientApi as clientApi


class HUDSystem(clientApi.GetClientSystemCls()):
    """
    HUD显示系统(ClientSystem)

    重构说明:
    - 原ECHUDPart继承PartBase(Preset系统)
    - 现改为继承ClientSystem
    - ECHUDScreenNode是screen类型UI，自动创建并显示
    - ECHUDScreenNode自己监听HUDControlEvent并更新UI
    """

    def __init__(self, namespace, systemName):
        """
        初始化HUD系统

        Args:
            namespace: 命名空间
            systemName: 系统名称
        """
        super(HUDSystem, self).__init__(namespace, systemName)

        # 本地玩家ID
        self.local_player_id = None

        # ScreenNode实例
        self.screen_node = None

        print("[INFO] [HUDSystem] __init__ 完成")

        # 手动调用Create()以初始化
        self.Create()

    # ========== ClientSystem生命周期 ==========

    def Create(self):
        """
        系统创建

        注意：
        1. ECHUDScreenNode是screen类型，会自动创建并显示
        2. HUDSystem监听HUDControlEvent并转发给ECHUDScreenNode
        3. HUDSystem监听UiInitFinished获取本地玩家ID并创建UI
        """
        self.LogInfo("HUDSystem.Create")

        # 监听UiInitFinished事件
        self.ListenForEvent(
            clientApi.GetEngineNamespace(),
            clientApi.GetEngineSystemName(),
            'UiInitFinished',
            self,
            self._on_ui_init_finished
        )
        self.LogInfo("HUDSystem 已监听UiInitFinished事件")

        # 监听服务端HUD控制事件
        # 说明: 统一由RoomManagementSystem发送HUD事件
        #       BedWarsGameSystem通过room_system.forward_hud_event()转发
        from Script_NeteaseMod.modConfig import MOD_NAME
        self.ListenForEvent(
            MOD_NAME,                # 服务端namespace
            "RoomManagementSystem",  # 服务端systemName
            'HUDControlEvent',
            self,
            self._on_hud_control_event
        )
        self.LogInfo("HUDSystem 已监听HUDControlEvent (来自 {}:RoomManagementSystem)".format(MOD_NAME))

        print("[INFO] [HUDSystem] Create完成")

    def _on_ui_init_finished(self, args):
        """
        UI初始化完成事件

        说明：
        - 必须先RegisterUI，再CreateUI，然后用GetUI获取实例
        """
        self.LogInfo("HUDSystem._on_ui_init_finished - UI系统就绪，开始注册和创建HUD")

        # 获取本地玩家ID
        self.local_player_id = clientApi.GetLocalPlayerId()
        self.LogInfo("HUDSystem 本地玩家ID: {}".format(self.local_player_id))

        # 创建UI
        try:
            from Script_NeteaseMod.modConfig import MOD_NAME

            # 1. RegisterUI注册UI类（在UI初始化完成后）
            # 注意：第1个参数应该与UI JSON文件中的namespace字段匹配
            self.LogInfo("开始注册ECHUDScreenNode UI")
            clientApi.RegisterUI(
                "ec_hud",  # UI JSON文件的namespace（必须与ec_hud.json中的namespace字段一致）
                "ec_hud",  # UI唯一标识符
                "Script_NeteaseMod.systems.ui.ECHUDScreenNode.ECHUDScreenNode",
                "ec_hud.main"
            )
            self.LogInfo("ECHUDScreenNode UI已注册")

            # 2. CreateUI创建UI实例
            # 注意：前两个参数必须与RegisterUI保持一致
            result = clientApi.CreateUI("ec_hud", "ec_hud", {"isHud": 1})
            self.LogInfo("CreateUI返回: {}".format(result))

            # 2. 延迟获取UI实例(避免时序问题)
            # 使用AddTimer延迟0.1秒后获取
            comp_game = clientApi.GetEngineCompFactory().CreateGame(clientApi.GetLevelId())
            comp_game.AddTimer(0.1, self._try_get_ui)

        except Exception as e:
            self.LogError("创建ECHUDScreenNode失败: {}".format(str(e)))
            import traceback
            print(traceback.format_exc())

        print("[INFO] [HUDSystem] UI初始化请求已发送，等待获取UI实例")

    def _try_get_ui(self):
        """
        尝试获取UI实例(定时器回调)

        说明: CreateUI后可能需要一小段时间才能GetUI成功
        """
        try:
            # GetUI获取UI实例
            # 参数必须与RegisterUI和CreateUI保持一致
            self.screen_node = clientApi.GetUI("ec_hud", "ec_hud")

            if self.screen_node:
                self.LogInfo("ECHUDScreenNode 获取成功")
                # 调用Init方法初始化UI
                if hasattr(self.screen_node, 'Init'):
                    self.screen_node.Init()
                    self.LogInfo("ECHUDScreenNode Init完成")
            else:
                self.LogWarn("GetUI返回None，UI可能创建失败或尚未就绪")
                # 再次尝试(最多3次)
                if not hasattr(self, '_ui_retry_count'):
                    self._ui_retry_count = 0
                self._ui_retry_count += 1

                if self._ui_retry_count < 3:
                    self.LogInfo("将在0.2秒后重试获取UI (第{}次)".format(self._ui_retry_count + 1))
                    comp_game = clientApi.GetEngineCompFactory().CreateGame(clientApi.GetLevelId())
                    comp_game.AddTimer(0.2, self._try_get_ui)
                else:
                    self.LogError("UI获取失败，已达到最大重试次数")

        except Exception as e:
            self.LogError("获取ECHUDScreenNode异常: {}".format(str(e)))
            import traceback
            print(traceback.format_exc())

    def _on_hud_control_event(self, args):
        """
        接收服务端HUD控制事件并转发给ScreenNode

        Args:
            args (dict): 事件参数 {'type': str, 'events': list}
        """
        if not self.screen_node:
            self.LogWarn("收到HUD事件但ScreenNode尚未就绪，忽略")
            return

        try:
            # 转发给ScreenNode处理
            self.screen_node.handle_hud_control(args)
        except Exception as e:
            self.LogError("转发HUD事件失败: {}".format(str(e)))
            import traceback
            print(traceback.format_exc())

    def Destroy(self):
        """系统销毁时调用"""
        self.LogInfo("HUDSystem.Destroy")

        # 销毁ScreenNode
        if self.screen_node:
            try:
                # 使用ScreenNode的SetRemove()方法删除UI节点
                self.screen_node.SetRemove()
                self.screen_node = None
                self.LogInfo("ECHUDScreenNode 已销毁")
            except Exception as e:
                self.LogError("销毁ECHUDScreenNode失败: {}".format(str(e)))

        print("[INFO] [HUDSystem] Destroy完成")

    # ========== 日志方法 ==========

    def LogInfo(self, message):
        """输出Info日志"""
        print("[INFO] [HUDSystem] {}".format(message))

    def LogDebug(self, message):
        """输出Debug日志"""
        # print("[DEBUG] [HUDSystem] {}".format(message))
        pass

    def LogError(self, message):
        """输出Error日志"""
        print("[ERROR] [HUDSystem] {}".format(message))

    def LogWarn(self, message):
        """输出Warn日志"""
        print("[WARN] [HUDSystem] {}".format(message))