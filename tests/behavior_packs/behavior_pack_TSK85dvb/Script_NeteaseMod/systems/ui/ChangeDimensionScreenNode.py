# -*- coding: utf-8 -*-
"""
ChangeDimensionScreenNode - 维度切换动画UI控制器

功能说明：
    控制维度切换时的UI遮罩动画，实现平滑的场景过渡效果。

重构说明：
    老项目: Parts/ChangeDimensionAnim/ChangeDimensionScreenNode.py
    新项目: systems/ui/ChangeDimensionScreenNode.py

核心职责：
    1. UI创建和销毁时的状态管理
    2. 淡入动画（离开维度前，0.5秒）
    3. 淡出动画（到达新维度后，1.0秒）
    4. Vignette后期处理接管（维度切换期间）
    5. 遮罩颜色设置（深蓝色 RGB[14, 24, 52]）

完整动画流程：
    1. 服务端触发 "StartChangeDimension" 事件
    2. 客户端播放淡入动画（0.5秒，Alpha 0→1）
    3. 服务端延迟0.8秒后执行维度切换
    4. UI销毁时启用Vignette后期处理维持遮罩
    5. 新维度UI创建时禁用Vignette并播放淡出动画（1.0秒，Alpha 1→0）
    6. 动画结束，玩家看到新场景

重要修复（2025-11-04）：
    - 修正Create()中masked状态判断逻辑（SetAlpha(1) → on_finish()）
    - 修正动画循环参数为True（与老项目一致，保持最终状态）
    - 在RoomManagementSystem中添加动画触发调用和延迟逻辑
"""

import time
import mod.client.extraClientApi as clientApi

ViewBinder = clientApi.GetViewBinderCls()
ViewRequest = clientApi.GetViewViewRequestCls()
ScreenNode = clientApi.GetScreenNodeCls()


def get_change_dimension_system():
    """
    获取维度切换动画系统

    Returns:
        ChangeDimensionAnimClient: 系统实例
    """
    try:
        system = clientApi.GetSystem("ECBedWars", "ChangeDimensionAnimClient")
        return system
    except:
        return None


class ChangeDimensionScreenNode(ScreenNode):
    """维度切换动画UI控制器"""

    def __init__(self, namespace, name, param):
        """
        初始化ScreenNode

        Args:
            namespace (str): UI命名空间
            name (str): UI名称
            param: 参数
        """
        ScreenNode.__init__(self, namespace, name, param)

    def Create(self):
        """
        UI创建成功时调用

        调用时机：
        1. 游戏启动时：首次创建UI，保持透明状态
        2. 维度切换后：新维度场景加载完成，UI重建

        状态判断逻辑（基于老项目）：
        - masked=True: 维度切换后UI重建，从Vignette遮罩状态过渡到UI遮罩并淡出
        - masked=False: 正常状态，保持透明

        关键修复（2025-11-04）：
        - 维度切换后必须SetAlpha(1)保持遮罩，然后调用on_finish()淡出
        - 之前错误地SetAlpha(0)并调用on_start()，导致动画逻辑反向
        """
        system = get_change_dimension_system()
        if not system:
            return

        print("[ChangeDimensionScreenNode] Create time={} masked={} changing={}".format(
            time.time(), system.masked, system.changing_dimension))

        # 禁用默认的Vignette效果
        comp_post = clientApi.GetEngineCompFactory().CreatePostProcess(clientApi.GetLevelId())
        comp_post.SetEnableVignette(False)

        # 获取背景节点
        node = self.GetBaseUIControl("/bg")
        if not node:
            print("[ChangeDimensionScreenNode] ERROR: 找不到 /bg 节点")
            return

        # 设置遮罩颜色
        color = system.mask_color
        print("[ChangeDimensionScreenNode] 设置遮罩颜色: RGB{}".format(color))
        node.asImage().SetSpriteColor((
            color[0] / 255.0,
            color[1] / 255.0,
            color[2] / 255.0
        ))

        # 根据状态决定初始Alpha和动画
        # 状态说明：
        # - masked=True: 维度切换后UI重建，Vignette已遮挡屏幕（Alpha理论上为1）
        # - masked=False: 正常启动或非切换场景，屏幕应该透明
        if system.masked:
            # 场景：维度切换后UI重建
            # 此时Vignette后期处理已经遮挡了屏幕（深蓝色）
            # 需要从遮挡状态无缝过渡到UI遮罩，然后淡出显示新场景

            # 步骤1：设置Alpha=1，维持遮罩状态（与Vignette视觉一致）
            node.SetAlpha(1)

            # 步骤2：播放淡出动画（1.0秒，Alpha 1→0）
            print("[ChangeDimensionScreenNode] 维度切换后UI重建，开始淡出动画")
            self.on_finish()

            # 注意：masked标志会在on_finish()开始时重置为False
        else:
            # 场景：游戏正常启动或其他情况
            # 保持透明状态，不显示遮罩
            node.SetAlpha(0)
            print("[ChangeDimensionScreenNode] 正常状态，保持透明")

    def Destroy(self):
        """
        UI销毁时调用

        旧维度UI即将销毁时：
        - 设置 masked = True
        - 启用Vignette后期处理接管遮罩
        - 确保玩家在UI销毁到新UI创建之间看到遮罩
        """
        system = get_change_dimension_system()
        if not system:
            return

        print("[ChangeDimensionScreenNode] Destroy time={}".format(time.time()))

        # 标记已遮罩
        system.masked = True

        # 使用后期处理Vignette接管遮罩
        comp_post = clientApi.GetEngineCompFactory().CreatePostProcess(clientApi.GetLevelId())
        comp_post.SetVignetteCenter((0, 2))  # 中心在屏幕外上方
        comp_post.SetVignetteRGB((
            system.mask_color[0],
            system.mask_color[1],
            system.mask_color[2]
        ))
        comp_post.SetVignetteRadius(1)       # 半径1，覆盖全屏
        comp_post.SetVignetteSmoothness(0)   # 无平滑，硬边界
        comp_post.SetEnableVignette(True)

        print("[ChangeDimensionScreenNode] Vignette已启用，接管遮罩")

    def OnActive(self):
        """
        UI重新回到栈顶时调用
        """
        print("[ChangeDimensionScreenNode] OnActive time={}".format(time.time()))

    def OnDeactive(self):
        """
        栈顶UI有其他UI入栈时调用
        """
        print("[ChangeDimensionScreenNode] OnDeactive time={}".format(time.time()))

    def on_start(self):
        """
        开始淡入动画（遮挡场景）

        触发时机：
        - 收到服务端 "StartChangeDimension" 事件后立即调用

        动画效果：
        - 时长：0.5秒
        - Alpha变化：0 → 1（从透明到不透明）
        - 循环播放：True（保持最终状态）

        后续流程：
        - 淡入完成后，服务端会延迟0.8秒执行维度切换
        - 维度切换时UI销毁，Vignette后期处理接管遮罩
        - 新维度场景加载完成后，UI重建并播放淡出动画

        关键修复（2025-11-04）：
        - 动画循环参数必须为True（与老项目一致）
        - True会保持动画最终状态（Alpha=1），维持遮罩效果
        """
        print("[ChangeDimensionScreenNode] on_start (淡入动画) time={}".format(time.time()))

        node = self.GetBaseUIControl("/bg")
        if node:
            # 移除旧动画（防止冲突）
            node.RemoveAnimation("alpha")

            # 播放淡入动画
            node.SetAnimation(
                "alpha",                # 动画类型
                "change_dimension",     # 命名空间
                "loading_bg_in",        # 动画名称
                True                    # 循环播放（与老项目一致）
            )
            print("[ChangeDimensionScreenNode] 淡入动画已启动（0.5秒）")

    def on_finish(self):
        """
        开始淡出动画（显示新场景）

        触发时机：
        - 维度切换完成后，新UI在Create()中调用

        动画效果：
        - 时长：1.0秒
        - Alpha变化：1 → 0（从不透明到透明）
        - 循环播放：True（保持最终状态）

        状态管理：
        - 动画开始时重置masked标志为False
        - 确保下次UI创建时不会误判为切换后状态

        关键修复（2025-11-04）：
        - 动画循环参数必须为True（与老项目一致）
        - True会保持动画最终状态（Alpha=0），维持透明状态
        - 如果用False，动画结束后可能回到初始状态，导致遮罩重新出现
        """
        print("[ChangeDimensionScreenNode] on_finish (淡出动画) time={}".format(time.time()))

        # 重置masked标志（在淡出开始时）
        system = get_change_dimension_system()
        if system and system.masked:
            system.masked = False
            print("[ChangeDimensionScreenNode] 重置masked标志")

        node = self.GetBaseUIControl("/bg")
        if node:
            # 移除旧动画
            node.RemoveAnimation("alpha")

            # 播放淡出动画
            node.SetAnimation(
                "alpha",                # 动画类型
                "change_dimension",     # 命名空间
                "loading_bg_out",       # 动画名称
                True                    # 循环播放（与老项目一致）
            )
            print("[ChangeDimensionScreenNode] 淡出动画已启动（1秒）")

    def on_finish_after_dimension_change(self):
        """
        维度切换后触发淡出动画（特殊处理）

        网易引擎在维度切换时会销毁HUD UI的视觉显示，但对象还在内存中。
        此时需要：
        1. 重新设置背景节点的Alpha为1（因为Vignette已经接管遮罩）
        2. 播放淡出动画显示新场景
        3. 重置masked状态
        """
        print("[ChangeDimensionScreenNode] on_finish_after_dimension_change() time={}".format(time.time()))

        system = get_change_dimension_system()
        if not system:
            print("[ChangeDimensionScreenNode] ERROR: 无法获取系统实例")
            return

        node = self.GetBaseUIControl("/bg")
        if not node:
            print("[ChangeDimensionScreenNode] ERROR: 找不到 /bg 节点")
            return

        # 设置初始Alpha为1（完全不透明）
        # 因为Vignette已经接管了遮罩，现在需要UI接管并淡出
        node.SetAlpha(1)
        print("[ChangeDimensionScreenNode] 设置背景Alpha=1")

        # 移除旧动画（如果有）
        node.RemoveAnimation("alpha")

        # 播放淡出动画
        node.SetAnimation(
            "alpha",                # 动画类型
            "change_dimension",     # 命名空间
            "loading_bg_out",       # 动画名称
            True                    # 循环播放
        )

        # 重置masked状态
        system.masked = False

        print("[ChangeDimensionScreenNode] 淡出动画已启动，masked已重置为False")
