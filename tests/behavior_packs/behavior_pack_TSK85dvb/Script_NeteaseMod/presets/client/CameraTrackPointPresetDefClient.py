# -*- coding: utf-8 -*-
"""
相机追踪点预设 - 客户端

功能:
- 接收服务端运镜控制指令
- 执行相机锁定和圆周运动
- 实时更新相机位置和朝向

老项目对应:
- WorldPreviewCameraTrackPart (客户端Tick逻辑)

新项目改进:
- 使用ECPreset架构
- 优化运镜轨迹算法
- 支持参数化配置
"""

from ECPresetServerScripts import PresetDefinitionClient


class CameraTrackPointPresetDefClient(PresetDefinitionClient):
    """
    相机追踪点预设客户端实现

    核心功能:
    1. 接收服务端运镜参数
    2. 每Tick更新相机位置(圆周运动)
    3. 相机始终朝向中心点
    4. 螺旋上升轨迹
    """

    def __init__(self):
        super(CameraTrackPointPresetDefClient, self).__init__()

        # 运镜参数
        self.center_pos = None  # type: tuple | None  # 中心点位置
        self.radius = 10.0  # type: float  # 初始半径
        self.angular_velocity = 0.005  # type: float  # 角速度(弧度/tick)
        self.height_offset = 5.0  # type: float  # 高度偏移

        # 运行时状态
        self.is_running = False  # type: bool  # 是否正在运行
        self.tick_count = 0  # type: int  # Tick计数器

        # 相机组件引用
        self.camera_comp = None  # type: object | None

    def on_init(self, instance):
        """
        预设初始化

        Args:
            instance: PresetInstanceClient对象
        """
        print("[INFO] [相机追踪点-客户端] 初始化")

    def on_start(self, instance):
        """
        预设启动

        执行步骤:
        1. 创建相机组件
        2. 注册事件监听

        Args:
            instance: PresetInstanceClient对象
        """
        print("[INFO] [相机追踪点-客户端] 启动")

        # 创建相机组件
        self._create_camera_component()

        # 注意: 事件通过on_server_message接收,不需要手动注册

    def on_tick(self, instance):
        """
        每Tick更新

        执行相机运镜逻辑

        Args:
            instance: PresetInstanceClient对象
        """
        if self.is_running and self.center_pos:
            self._update_camera()

    def on_stop(self, instance):
        """
        预设停止

        清理工作:
        1. 停止运镜
        2. 解锁相机

        Args:
            instance: PresetInstanceClient对象
        """
        print("[INFO] [相机追踪点-客户端] 停止")

        # 停止运镜
        if self.is_running:
            self.stop_camera_preview()

    def on_destroy(self, instance):
        """
        预设销毁

        最终清理工作

        Args:
            instance: PresetInstanceClient对象
        """
        print("[INFO] [相机追踪点-客户端] 销毁")

        # 解锁相机
        if self.camera_comp:
            try:
                self.camera_comp.UnLockCamera()
            except Exception as e:
                print("[ERROR] [相机追踪点-客户端] 解锁相机失败: {}".format(str(e)))

        # 清理数据
        self.camera_comp = None
        self.is_running = False
        self.tick_count = 0

    # ========== 接收服务端消息 ==========

    def on_server_message(self, instance, message_type, data):
        """
        接收服务端消息回调 - ECPreset框架标准接口

        Args:
            instance: PresetInstanceClient对象
            message_type: str 消息类型
            data: dict 消息数据
        """
        if message_type == "StartCameraPreview":
            self._on_start_camera_preview(data)
        elif message_type == "StopCameraPreview":
            self._on_stop_camera_preview(data)
        elif message_type == "SyncCameraPreviewState":
            self._on_sync_state(data)

    # ========== 事件处理方法 ==========

    def _on_start_camera_preview(self, event_data):
        """
        处理启动运镜事件

        Args:
            event_data: dict 事件数据
                - center_pos: 中心点位置 [x, y, z]
                - radius: 初始半径
                - angular_velocity: 角速度
                - height_offset: 高度偏移
        """
        # 读取运镜参数
        center = event_data.get('center_pos')
        if not center:
            print("[ERROR] [相机追踪点-客户端] 缺少center_pos参数")
            return

        self.center_pos = tuple(center)
        self.radius = event_data.get('radius', 10.0)
        self.angular_velocity = event_data.get('angular_velocity', 0.005)
        self.height_offset = event_data.get('height_offset', 5.0)

        print("[INFO] [相机追踪点-客户端] 启动运镜: center={}, radius={}".format(
            self.center_pos, self.radius
        ))

        # 启动运镜
        self.is_running = True
        self.tick_count = 0

    def _on_stop_camera_preview(self, event_data):
        """
        处理停止运镜事件

        Args:
            event_data: dict 事件数据
        """
        print("[INFO] [相机追踪点-客户端] 停止运镜")

        # 停止运镜
        self.stop_camera_preview()

    def _on_sync_state(self, event_data):
        """
        处理状态同步事件

        Args:
            event_data: dict 事件数据
                - is_running: 是否运行
                - tick_count: Tick计数
        """
        # 同步运行状态(防止客户端服务端不一致)
        is_running = event_data.get('is_running', False)
        if not is_running and self.is_running:
            print("[INFO] [相机追踪点-客户端] 服务端已停止,同步停止运镜")
            self.stop_camera_preview()

    # ========== 相机控制方法 ==========

    def _create_camera_component(self):
        """创建相机组件"""
        try:
            import mod.client.extraClientApi as clientApi

            comp_factory = clientApi.GetEngineCompFactory()
            level_id = clientApi.GetLevelId()
            self.camera_comp = comp_factory.CreateCamera(level_id)

            print("[INFO] [相机追踪点-客户端] 相机组件创建成功")

        except Exception as e:
            print("[ERROR] [相机追踪点-客户端] 创建相机组件失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _update_camera(self):
        """
        更新相机位置和朝向

        运镜轨迹:
        - 圆周运动: 围绕中心点旋转
        - 螺旋上升: 半径随时间线性增长
        - 朝向中心: 相机始终看向中心点
        """
        if not self.camera_comp or not self.center_pos:
            return

        try:
            import math

            # 增加Tick计数
            self.tick_count += 1

            # 计算当前半径(螺旋上升)
            radius = self.radius + 0.1 * self.tick_count

            # 计算当前角度
            angle = self.tick_count * self.angular_velocity

            # 计算相机位置(圆周运动)
            x = self.center_pos[0] + radius * math.cos(angle)
            y = self.center_pos[1] + self.height_offset  # 固定高度
            z = self.center_pos[2] + radius * math.sin(angle)
            camera_pos = (x, y, z)

            # 计算相机朝向(看向中心点)
            dx = self.center_pos[0] - x
            dy = self.center_pos[1] - y
            dz = self.center_pos[2] - z

            # 计算yaw和pitch
            distance = math.sqrt(dx * dx + dz * dz)
            yaw = math.degrees(math.atan2(dz, dx)) - 90  # 偏移90度以修正方向
            pitch = -math.degrees(math.atan2(dy, distance))  # 俯仰角
            camera_rot = (pitch, yaw)

            # 锁定相机
            self.camera_comp.LockCamera(camera_pos, camera_rot)

        except Exception as e:
            print("[ERROR] [相机追踪点-客户端] 更新相机失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def stop_camera_preview(self):
        """停止运镜并解锁相机"""
        self.is_running = False
        self.tick_count = 0

        # 解锁相机
        if self.camera_comp:
            try:
                self.camera_comp.UnLockCamera()
                print("[INFO] [相机追踪点-客户端] 相机已解锁")
            except Exception as e:
                print("[ERROR] [相机追踪点-客户端] 解锁相机失败: {}".format(str(e)))
