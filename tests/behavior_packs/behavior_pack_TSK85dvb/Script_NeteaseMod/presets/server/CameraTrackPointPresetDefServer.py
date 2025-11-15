# -*- coding: utf-8 -*-
"""
相机追踪点预设 - 服务端

功能:
- 在地图中标记相机运镜的中心点
- 接收系统事件启动/停止运镜
- 控制相机围绕此点进行圆周运动

老项目对应:
- WorldPreviewCameraTrackPart (Parts/WorldPreviewCameraTrack/)

新项目改进:
- 使用ECPreset架构
- 配合CameraPreviewHelper工具使用
- 支持多个追踪点(按dimension区分)
"""

from ECPresetServerScripts import PresetDefinitionServer


class CameraTrackPointPresetDefServer(PresetDefinitionServer):
    """
    相机追踪点预设服务端实现

    核心功能:
    1. 标记地图运镜中心点
    2. 接收系统事件控制运镜启动/停止
    3. 同步运镜状态到客户端
    4. 向客户端广播运镜参数
    """

    def __init__(self):
        super(CameraTrackPointPresetDefServer, self).__init__()

        # 配置数据
        self.center_pos = None  # type: tuple | None  # 中心点位置
        self.dimension_id = 0  # type: int  # 维度ID

        # 运镜参数配置
        self.radius = 10.0  # type: float  # 初始半径(格)
        self.angular_velocity = 0.005  # type: float  # 角速度(弧度/tick)
        self.height_offset = 5.0  # type: float  # 相机高度偏移(格)

        # 运行时状态
        self.is_running = False  # type: bool  # 运镜是否正在运行
        self.tick_count = 0  # type: int  # Tick计数器(用于同步)

    def on_init(self, instance):
        """
        预设初始化

        解析配置数据:
        - pos: 中心点位置 (x, y, z)
        - dimension: 维度ID
        - radius: 初始半径(可选,默认10.0)
        - angular_velocity: 角速度(可选,默认0.005)
        - height_offset: 高度偏移(可选,默认5.0)

        Args:
            instance: PresetInstanceServer对象
        """
        # 读取位置配置 - 使用ECPreset框架的get_config API
        pos_config = instance.get_config("pos")
        if not pos_config:
            print("[ERROR] [相机追踪点-服务端] on_init 缺少pos配置")
            return

        # 转换位置格式
        if isinstance(pos_config, list):
            self.center_pos = tuple(pos_config)
        elif isinstance(pos_config, dict):
            self.center_pos = (pos_config['x'], pos_config['y'], pos_config['z'])
        else:
            self.center_pos = pos_config

        # 读取维度ID
        self.dimension_id = instance.get_config("dimension") or 0

        # 读取运镜参数(可选)
        self.radius = instance.get_config("radius") or 10.0
        self.angular_velocity = instance.get_config("angular_velocity") or 0.005
        self.height_offset = instance.get_config("height_offset") or 5.0

        print("[INFO] [相机追踪点-服务端] 初始化: pos={}, dim={}, radius={}".format(
            self.center_pos, self.dimension_id, self.radius
        ))

    def on_start(self, instance):
        """
        预设启动

        执行步骤:
        1. 保存instance引用
        2. 准备运镜参数

        Args:
            instance: PresetInstanceServer对象
        """
        # 保存instance引用
        self.instance = instance

        print("[INFO] [相机追踪点-服务端] 启动: pos={}, dim={}".format(
            self.center_pos, self.dimension_id
        ))

    def on_tick(self, instance):
        """
        每Tick更新

        运镜运行时同步状态

        Args:
            instance: PresetInstanceServer对象
        """
        if self.is_running:
            self.tick_count += 1

            # 每秒同步一次状态(20 ticks = 1秒)
            if self.tick_count % 20 == 0:
                self._sync_running_state()

    def on_stop(self, instance):
        """
        预设停止

        清理工作:
        1. 停止运镜
        2. 取消事件监听

        Args:
            instance: PresetInstanceServer对象
        """
        print("[INFO] [相机追踪点-服务端] 停止: pos={}".format(self.center_pos))

        # 停止运镜
        if self.is_running:
            self.stop_camera_preview()

    def on_destroy(self, instance):
        """
        预设销毁

        最终清理工作

        Args:
            instance: PresetInstanceServer对象
        """
        print("[INFO] [相机追踪点-服务端] 销毁: pos={}".format(self.center_pos))

        # 清理数据
        self.is_running = False
        self.tick_count = 0

    # ========== 接收系统事件 ==========

    def on_preset_event(self, instance, event_name, event_data):
        """
        接收系统广播的预设事件 - ECPreset框架标准接口

        Args:
            instance: PresetInstanceServer对象
            event_name: str 事件名称
            event_data: dict 事件数据
        """
        if event_name == "StartCameraPreview":
            self._on_start_camera_preview(event_data)
        elif event_name == "StopCameraPreview":
            self._on_stop_camera_preview(event_data)

    # ========== 事件处理方法 ==========

    def _on_start_camera_preview(self, event_data):
        """
        处理启动运镜事件

        Args:
            event_data: dict 事件数据
                - dimension: 维度ID
                - players: 玩家ID列表(可选,None表示所有玩家)
        """
        # 检查是否是本维度
        dimension = event_data.get('dimension', 0)
        if dimension != self.dimension_id:
            return

        print("[INFO] [相机追踪点-服务端] 收到启动运镜事件: dim={}".format(dimension))

        # 启动运镜
        players = event_data.get('players')
        self.start_camera_preview(players=players)

    def _on_stop_camera_preview(self, event_data):
        """
        处理停止运镜事件

        Args:
            event_data: dict 事件数据
                - dimension: 维度ID
                - players: 玩家ID列表(可选)
        """
        # 检查是否是本维度
        dimension = event_data.get('dimension', 0)
        if dimension != self.dimension_id:
            return

        print("[INFO] [相机追踪点-服务端] 收到停止运镜事件: dim={}".format(dimension))

        # 停止运镜
        players = event_data.get('players')
        self.stop_camera_preview(players=players)

    # ========== 运镜控制方法 ==========

    def start_camera_preview(self, players=None):
        """
        启动运镜

        Args:
            players: list | None 玩家ID列表,None表示所有玩家
        """
        if not self.instance:
            print("[ERROR] [相机追踪点-服务端] instance未初始化,无法启动运镜")
            return

        self.is_running = True
        self.tick_count = 0

        # 构建运镜参数
        preview_data = {
            'center_pos': list(self.center_pos),
            'radius': self.radius,
            'angular_velocity': self.angular_velocity,
            'height_offset': self.height_offset,
        }

        # 通过instance.manager.system发送消息到客户端
        # ECPreset框架会自动通过System发送到对应的客户端系统
        system = self._get_game_system()
        if not system:
            print("[ERROR] [相机追踪点-服务端] 无法获取BedWarsGameSystem,无法启动运镜")
            return

        if players is not None:
            # 向指定玩家发送
            for player_id in players:
                system.NotifyToClient(player_id, "StartCameraPreview", preview_data)
            print("[INFO] [相机追踪点-服务端] 启动运镜(指定玩家: {})".format(len(players)))
        else:
            # 广播给所有玩家
            system.BroadcastToAllClient("StartCameraPreview", preview_data)
            print("[INFO] [相机追踪点-服务端] 启动运镜(所有玩家)")

    def stop_camera_preview(self, players=None):
        """
        停止运镜

        Args:
            players: list | None 玩家ID列表,None表示所有玩家
        """
        if not self.instance:
            print("[ERROR] [相机追踪点-服务端] instance未初始化,无法停止运镜")
            return

        self.is_running = False
        self.tick_count = 0

        # 通过System发送停止事件到客户端
        system = self._get_game_system()
        if not system:
            print("[ERROR] [相机追踪点-服务端] 无法获取BedWarsGameSystem,无法停止运镜")
            return

        if players is not None:
            # 向指定玩家发送
            for player_id in players:
                system.NotifyToClient(player_id, "StopCameraPreview", {})
            print("[INFO] [相机追踪点-服务端] 停止运镜(指定玩家: {})".format(len(players)))
        else:
            # 广播给所有玩家
            system.BroadcastToAllClient("StopCameraPreview", {})
            print("[INFO] [相机追踪点-服务端] 停止运镜(所有玩家)")

    def _sync_running_state(self):
        """同步运镜运行状态(每秒一次)"""
        if self.is_running:
            sync_data = {
                'is_running': True,
                'tick_count': self.tick_count
            }
            # 通过System广播
            system = self._get_game_system()
            if system:
                system.BroadcastToAllClient("SyncCameraPreviewState", sync_data)

    # ========== 工具方法 ==========

    def _get_game_system(self):
        """
        获取BedWarsGameSystem实例

        Returns:
            BedWarsGameSystem | None: 游戏系统实例,失败返回None
        """
        try:
            import mod.server.extraServerApi as serverApi
            from Script_NeteaseMod.modConfig import MOD_NAME

            # 获取BedWarsGameSystem
            game_system = serverApi.GetSystem(MOD_NAME, "BedWarsGameSystem")
            return game_system

        except Exception as e:
            print("[ERROR] [相机追踪点-服务端] 获取BedWarsGameSystem失败: {}".format(str(e)))
            return None
