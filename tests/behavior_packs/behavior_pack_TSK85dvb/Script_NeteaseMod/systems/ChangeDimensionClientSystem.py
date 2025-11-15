# -*- coding: utf-8 -*-
"""
ChangeDimensionClientSystem - 维度切换动画系统（客户端）

功能说明：
    在玩家进行维度切换（传送到游戏地图、返回大厅等）时提供平滑的视觉过渡效果。
    通过UI动画和后期处理（PostProcess）效果的组合，实现专业级的场景转换体验。

重构说明：
    老项目: ChangeDimensionAnimPart零件实现
    新项目: 独立的ClientSystem + ScreenNode实现

核心职责：
    1. 监听引擎维度切换事件 (DimensionChangeClientEvent、UiInitFinished)
    2. 监听服务端动画触发事件 (StartChangeDimension)
    3. 控制UI遮罩层的淡入淡出动画
    4. 管理Vignette后期处理效果
    5. 确保UI栈无冲突，动画流畅播放
"""

import mod.client.extraClientApi as clientApi
from Script_NeteaseMod.modConfig import MOD_NAME

ClientSystem = clientApi.GetClientSystemCls()


class ChangeDimensionClientSystem(ClientSystem):
    """维度切换动画客户端系统"""

    def __init__(self, namespace, systemName):
        super(ChangeDimensionClientSystem, self).__init__(namespace, systemName)

        # 状态标记
        self.changing_dimension = False  # 是否正在切换维度
        self.masked = False  # 是否已显示遮罩

        # 遮罩颜色配置（RGB 0-255）
        self.mask_color = [14, 24, 52]  # 深蓝色

        # UI屏幕节点引用
        self.screen_node = None

        # UI路径
        self.ui_namespace = "change_dimension"
        self.ui_screen_def = "loading"

        # UI注册标记（防止重复注册）
        self.ui_registered = False

        print("[INFO] [ChangeDimensionAnimClient] 维度切换动画系统初始化")

        # ⚠️ 关键：手动调用Create()来注册事件监听器
        # 网易引擎不会自动调用Create()，必须手动调用
        self.Create()

    def Create(self):
        """系统创建时调用"""
        print("[INFO] [ChangeDimensionClientSystem] 系统创建")
        self._register_events()

        # 注册UI初始化完成事件监听（用于创建UI）
        self.ListenForEvent(
            clientApi.GetEngineNamespace(),
            clientApi.GetEngineSystemName(),
            "UiInitFinished",
            self,
            self._on_ui_init_finished
        )

    def Destroy(self):
        """系统销毁"""
        print("[INFO] [ChangeDimensionClientSystem] 系统销毁")
        # 清理Vignette效果
        try:
            comp_post = clientApi.GetEngineCompFactory().CreatePostProcess(clientApi.GetLevelId())
            comp_post.SetEnableVignette(False)
        except Exception as e:
            print("[ERROR] [ChangeDimensionClientSystem] 清理Vignette失败: {}".format(e))
        super(ChangeDimensionClientSystem, self).Destroy()

    def Update(self):
        """系统Tick更新"""
        pass

    # ===== 初始化 =====

    def _register_events(self):
        """注册事件监听"""
        # 监听引擎维度切换事件（设置changing_dimension=True）
        self.ListenForEvent(
            clientApi.GetEngineNamespace(),
            clientApi.GetEngineSystemName(),
            "DimensionChangeClientEvent",
            self,
            self._on_dimension_change_start
        )

        # 监听服务端触发的动画开始事件
        # ⚠️ 关键修复：事件实际上是从RoomManagementSystem广播的，不是GamingStateSystem
        # StageWaitingState → get_system() → RoomManagementSystem → BroadcastToAllClient()
        self.ListenForEvent(
            MOD_NAME,
            "RoomManagementSystem",  # ✅ 修复：使用正确的System名字
            "StartChangeDimension",
            self,
            self._on_start_change_dimension
        )

        print("[INFO] [ChangeDimensionClientSystem] 事件监听注册完成")

    def _on_ui_init_finished(self, args):
        """
        UI初始化完成事件处理

        两种情况：
        1. 游戏启动时：注册和创建UI
        2. 维度切换后：触发淡出动画（UI不再被销毁，无需重建）
        """
        print("[INFO] [ChangeDimensionClientSystem] UI初始化完成")

        # 情况1：游戏启动时的UI创建
        if not self.screen_node:
            print("[INFO] [ChangeDimensionClientSystem] 首次UI创建，开始注册维度切换UI")
            self._create_ui()
            print("[INFO] [ChangeDimensionClientSystem] 维度切换UI已注册和创建")
            return

        # 情况2：维度切换后重新创建UI
        if self.changing_dimension:
            # 重置切换状态
            self.changing_dimension = False

            # 立即禁用Vignette
            try:
                comp_post = clientApi.GetEngineCompFactory().CreatePostProcess(clientApi.GetLevelId())
                comp_post.SetEnableVignette(False)
            except Exception as e:
                print("[ERROR] [ChangeDimensionClientSystem] 禁用Vignette失败: {}".format(e))

            # 重置UI注册标记，允许重新注册
            self.ui_registered = False
            self.screen_node = None

            # 直接重新创建UI（维度切换后定时器不可靠）
            self._create_ui()

    # ===== 事件处理 =====

    def _on_start_change_dimension(self, args):
        """
        维度切换前的准备工作（服务端事件触发）

        服务端触发该事件，客户端开始播放淡入动画
        """
        print("[INFO] [ChangeDimensionClientSystem] 收到服务端维度切换开始事件")

        # 关闭非HUD界面，防止UI冲突
        top_ui = clientApi.GetTopUI()
        if top_ui != "hud_screen":
            print("[INFO] [ChangeDimensionClientSystem] 关闭非HUD界面: {}".format(top_ui))
            clientApi.PopTopUI()

        # 防止重复播放动画
        if self.masked:
            print("[WARN] [ChangeDimensionClientSystem] 遮罩已显示，跳过动画")
            return

        self.masked = True
        print("[INFO] [ChangeDimensionClientSystem] 设置masked=True，准备播放淡入动画")

        # 触发UI淡入动画
        self._start_fade_in_animation()

    def _on_dimension_change_start(self, args):
        """
        维度切换开始事件（引擎事件触发 - DimensionChangeClientEvent）
        标记正在切换维度状态
        """
        # 修复：无论当前UI状态如何，都标记维度切换
        # 这样可以处理玩家刚加入游戏时的维度切换场景
        self.changing_dimension = True
        print("[INFO] [ChangeDimensionClientSystem] 检测到维度切换，设置changing_dimension=True")

    # ===== UI动画控制 =====

    def _start_fade_in_animation(self):
        """
        开始淡入动画（遮挡场景）

        0.5秒从透明到不透明
        通过ScreenNode的on_start()方法播放UI动画
        """
        print("[INFO] [ChangeDimensionAnimClient] 开始淡入动画")

        # 调用ScreenNode的on_start方法播放淡入动画
        if self.screen_node:
            try:
                self.screen_node.on_start()
            except Exception as e:
                print("[ERROR] [ChangeDimensionAnimClient] 播放淡入动画失败: {}".format(e))
        else:
            print("[ERROR] [ChangeDimensionAnimClient] screen_node未创建，无法播放动画")

    def _start_fade_out_animation(self):
        """
        开始淡出动画（显示新场景）

        1秒从不透明到透明
        通过ScreenNode的on_finish()方法播放UI动画
        """
        print("[INFO] [ChangeDimensionAnimClient] 开始淡出动画")

        # ScreenNode会在Create时自动调用on_finish
        # 这里只是确保状态正确
        # on_finish动画完成后会在ScreenNode中重置masked=False

    # ===== UI管理 =====

    def _create_ui(self):
        """创建UI屏幕节点"""
        try:
            # 只在第一次注册ScreenNode类（避免重复注册）
            if not self.ui_registered:
                clientApi.RegisterUI(
                    self.ui_namespace,
                    self.ui_screen_def,
                    "Script_NeteaseMod.systems.ui.ChangeDimensionScreenNode.ChangeDimensionScreenNode",
                    "change_dimension.loading"
                )
                self.ui_registered = True

            # 创建UI实例
            self.screen_node = clientApi.CreateUI(
                self.ui_namespace,
                self.ui_screen_def,
                {"isHud": 1}
            )
        except Exception as e:
            print("[ERROR] [ChangeDimensionAnimClient] UI创建失败: {}".format(e))
            import traceback
            traceback.print_exc()

    # ===== 工具方法 =====

    def create_game_timer(self, delay, callback, repeat):
        """
        创建游戏定时器

        Args:
            delay (float): 延迟时间（秒）
            callback (function): 回调函数
            repeat (bool): 是否重复
        """
        import mod.common.minecraftEnum as minecraftEnum

        comp_game = clientApi.GetEngineCompFactory().CreateGame(clientApi.GetLevelId())
        comp_game.AddTimer(delay, callback, repeat)

    def set_mask_color(self, r, g, b):
        """
        设置遮罩颜色

        Args:
            r (int): 红色分量 (0-255)
            g (int): 绿色分量 (0-255)
            b (int): 蓝色分量 (0-255)
        """
        self.mask_color = [r, g, b]
        print("[INFO] [ChangeDimensionClientSystem] 遮罩颜色设置为: {}".format(self.mask_color))
