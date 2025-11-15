# -*- coding: utf-8 -*-
"""
CameraPreviewClientSystem - 地图预览摄像机运镜系统（客户端）

功能说明：
    在游戏开始前为玩家呈现地图的环绕视角。
    通过动态计算相机位置和朝向，实现螺旋上升的圆周运动轨迹。

重构说明：
    老项目: WorldPreviewCameraTrackPart零件实现
    新项目: 独立的ClientSystem实现

核心职责：
    1. 监听服务端的启动/停止运镜事件
    2. 每帧计算相机位置（螺旋轨迹）
    3. 计算相机朝向（始终朝向地图中心）
    4. 锁定/释放相机控制权
"""

import mod.client.extraClientApi as clientApi
import math

ClientSystem = clientApi.GetClientSystemCls()


class CameraPreviewClientSystem(ClientSystem):
    """地图预览摄像机运镜系统（客户端）"""

    def __init__(self, namespace, systemName):
        super(CameraPreviewClientSystem, self).__init__(namespace, systemName)

        # 运镜状态
        self.running = False  # 是否正在运镜
        self.camera_tick = 0  # 累计tick数

        # 运镜参数（可配置）
        self.angular_velocity = 0.005  # 角速度（弧度/tick）
        self.initial_radius = 10.0  # 初始半径（格）
        self.radius_growth_rate = 0.1  # 半径增长率（格/tick）
        self.camera_height_offset = 5.0  # 相机高度偏移（格）

        # 地图中心点
        self.center_pos = None  # (x, y, z)

        print("[INFO] [CameraPreviewClientSystem] 地图预览摄像机系统初始化")

        # ⚠️ 关键：手动调用Create()来注册事件监听器
        # 网易引擎不会自动调用Create()，必须手动调用
        self.Create()

    def Create(self):
        """系统创建时调用"""
        # 注册事件监听
        # 监听服务端BedWarsGameSystem发送的运镜事件
        from Script_NeteaseMod.modConfig import MOD_NAME

        # 监听启动运镜事件
        self.ListenForEvent(
            MOD_NAME,
            'BedWarsGameSystem',  # 监听服务端BedWarsGameSystem
            "StartCameraPreview",
            self,
            self._on_start_camera_preview
        )

        # 监听停止运镜事件
        self.ListenForEvent(
            MOD_NAME,
            'BedWarsGameSystem',  # 监听服务端BedWarsGameSystem
            "StopCameraPreview",
            self,
            self._on_stop_camera_preview
        )

        print("[INFO] [CameraPreviewClientSystem] 事件监听注册完成")

    def Destroy(self):
        """系统销毁"""
        # 确保释放相机
        self._stop_camera_preview()
        print("[INFO] [CameraPreviewClientSystem] 系统销毁")
        super(CameraPreviewClientSystem, self).Destroy()

    def OnDestroy(self):
        """系统销毁回调"""
        pass

    def Update(self):
        """系统Tick更新 - 每帧计算相机位置"""
        if self.running and self.center_pos is not None:
            self._update_camera()

    # ===== 事件处理 =====

    def _on_start_camera_preview(self, args):
        """
        开始运镜事件

        Args:
            args (dict): {
                "center_pos": [x, y, z],  # 地图中心点
                "radius": float,           # 可选：初始半径
                "angular_velocity": float, # 可选：角速度
                "height_offset": float     # 可选：高度偏移
            }
        """
        if 'center_pos' not in args:
            print("[ERROR] [CameraPreviewClientSystem] 缺少center_pos参数")
            return

        # 设置地图中心点
        self.center_pos = tuple(args['center_pos'])

        # 可选参数
        if 'radius' in args:
            self.initial_radius = float(args['radius'])
        if 'angular_velocity' in args:
            self.angular_velocity = float(args['angular_velocity'])
        if 'height_offset' in args:
            self.camera_height_offset = float(args['height_offset'])

        # 重置状态
        self.camera_tick = 0
        self.running = True

        print("[INFO] [CameraPreviewClientSystem] 开始运镜 - 中心点: {}".format(self.center_pos))

    def _on_stop_camera_preview(self, args):
        """停止运镜事件"""
        self._stop_camera_preview()

    def _stop_camera_preview(self):
        """停止运镜并释放相机"""
        if not self.running:
            return

        # 释放相机锁定
        try:
            comp_camera = clientApi.GetEngineCompFactory().CreateCamera(clientApi.GetLevelId())
            comp_camera.UnLockCamera()
            print("[INFO] [CameraPreviewClientSystem] 相机已释放")
        except Exception as e:
            print("[ERROR] [CameraPreviewClientSystem] 释放相机失败: {}".format(e))

        # 重置状态
        self.running = False
        self.camera_tick = 0
        self.center_pos = None

    # ===== 相机运动逻辑 =====

    def _update_camera(self):
        """
        更新相机位置和朝向（每帧调用）

        运动轨迹：螺旋上升的圆周运动
        - 半径随时间线性增长
        - 角度匀速旋转
        - 相机始终朝向地图中心
        """
        try:
            # 1. 累计tick计数
            self.camera_tick += 1

            # 2. 计算相机位置（螺旋轨迹）
            radius = self.initial_radius + self.radius_growth_rate * self.camera_tick
            angle = self.camera_tick * self.angular_velocity

            x = self.center_pos[0] + radius * math.cos(angle)
            y = self.center_pos[1] + self.camera_height_offset
            z = self.center_pos[2] + radius * math.sin(angle)
            camera_pos = (x, y, z)

            # 3. 计算相机朝向（始终朝向中心点）
            dx = self.center_pos[0] - x
            dy = self.center_pos[1] - y
            dz = self.center_pos[2] - z

            # 计算水平距离
            distance_xz = math.sqrt(dx * dx + dz * dz)

            # 偏航角（Yaw）：水平方向的旋转角度
            yaw = math.degrees(math.atan2(dz, dx)) - 90.0

            # 俯仰角（Pitch）：垂直方向的旋转角度
            pitch = -math.degrees(math.atan2(dy, distance_xz))

            camera_rot = (pitch, yaw)

            # 4. 锁定相机
            comp_camera = clientApi.GetEngineCompFactory().CreateCamera(clientApi.GetLevelId())
            comp_camera.LockCamera(camera_pos, camera_rot)

        except Exception as e:
            print("[ERROR] [CameraPreviewClientSystem] 更新相机失败: {}".format(e))
            # 遇到错误时停止运镜
            self._stop_camera_preview()

    # ===== 配置方法 =====

    def set_parameters(self, angular_velocity=None, initial_radius=None,
                      radius_growth_rate=None, camera_height_offset=None):
        """
        设置运镜参数（可选）

        Args:
            angular_velocity (float): 角速度（弧度/tick）
            initial_radius (float): 初始半径（格）
            radius_growth_rate (float): 半径增长率（格/tick）
            camera_height_offset (float): 相机高度偏移（格）
        """
        if angular_velocity is not None:
            self.angular_velocity = angular_velocity
        if initial_radius is not None:
            self.initial_radius = initial_radius
        if radius_growth_rate is not None:
            self.radius_growth_rate = radius_growth_rate
        if camera_height_offset is not None:
            self.camera_height_offset = camera_height_offset

        print("[INFO] [CameraPreviewClientSystem] 运镜参数已更新")
