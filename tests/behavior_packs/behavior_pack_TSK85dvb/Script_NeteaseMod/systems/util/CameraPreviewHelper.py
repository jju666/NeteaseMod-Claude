# -*- coding: utf-8 -*-
"""
CameraPreviewHelper - 地图预览摄像机触发工具

功能说明：
    提供简洁的API，用于在游戏开始前触发地图预览运镜效果。
    服务端系统可以通过该工具通知客户端启动/停止运镜。

重构说明：
    老项目: 通过预设系统事件BroadcastPresetSystemEvent触发
    新项目: 通过System的BroadcastToAllClient触发

使用示例：
    # 在System中初始化
    self.camera_preview = CameraPreviewHelper(self)

    # 启动运镜（所有玩家）
    self.camera_preview.start_preview(center_pos=(0, 100, 0))

    # 停止运镜
    self.camera_preview.stop_preview()

    # 自定义参数
    self.camera_preview.start_preview(
        center_pos=(0, 100, 0),
        radius=15.0,
        angular_velocity=0.01,
        height_offset=10.0
    )
"""

import mod.server.extraServerApi as serverApi


class CameraPreviewHelper(object):
    """地图预览摄像机触发工具"""

    def __init__(self, system):
        """
        初始化工具

        Args:
            system: 游戏系统实例（用于发送事件）
        """
        self.system = system

    def start_preview(self, center_pos, players=None, radius=10.0,
                     angular_velocity=0.005, height_offset=5.0):
        """
        启动地图预览运镜

        Args:
            center_pos (tuple): 地图中心点坐标 (x, y, z)
            players (list, optional): 指定玩家ID列表。如果为None，则广播给所有玩家。
            radius (float): 初始半径（格），默认10.0
            angular_velocity (float): 角速度（弧度/tick），默认0.005
            height_offset (float): 相机高度偏移（格），默认5.0

        说明:
            运镜轨迹：螺旋上升的圆周运动
            - 半径随时间线性增长
            - 相机始终朝向地图中心
            - 完整旋转一圈约需63秒（角速度0.005）

        示例:
            # 基本使用
            self.camera_preview.start_preview(center_pos=(0, 100, 0))

            # 自定义参数
            self.camera_preview.start_preview(
                center_pos=(100, 65, 100),
                radius=15.0,              # 更大的初始半径
                angular_velocity=0.01,    # 更快的旋转速度
                height_offset=10.0        # 更高的视角
            )

            # 指定玩家
            self.camera_preview.start_preview(
                center_pos=(0, 100, 0),
                players=['player1', 'player2']
            )
        """
        event_data = {
            'center_pos': list(center_pos),
            'radius': radius,
            'angular_velocity': angular_velocity,
            'height_offset': height_offset,
        }

        if players is not None:
            # 向指定玩家发送
            for player_id in players:
                self.system.NotifyToClient(player_id, "StartCameraPreview", event_data)
            print("[INFO] [CameraPreviewHelper] 已启动地图预览（指定玩家: {}）".format(len(players)))
        else:
            # 向所有玩家广播
            self.system.BroadcastToAllClient("StartCameraPreview", event_data)
            print("[INFO] [CameraPreviewHelper] 已启动地图预览（所有玩家）")

    def stop_preview(self, players=None):
        """
        停止地图预览运镜

        Args:
            players (list, optional): 指定玩家ID列表。如果为None，则广播给所有玩家。

        说明:
            停止运镜并释放玩家的相机控制权

        示例:
            # 停止所有玩家的运镜
            self.camera_preview.stop_preview()

            # 停止特定玩家的运镜
            self.camera_preview.stop_preview(players=['player1', 'player2'])
        """
        event_data = {}

        if players is not None:
            # 向指定玩家发送
            for player_id in players:
                self.system.NotifyToClient(player_id, "StopCameraPreview", event_data)
            print("[INFO] [CameraPreviewHelper] 已停止地图预览（指定玩家: {}）".format(len(players)))
        else:
            # 向所有玩家广播
            self.system.BroadcastToAllClient("StopCameraPreview", event_data)
            print("[INFO] [CameraPreviewHelper] 已停止地图预览（所有玩家）")

    def get_map_center_from_config(self, dimension):
        """
        从配置中获取地图中心点（便捷方法）

        Args:
            dimension (int): 维度ID

        Returns:
            tuple: 地图中心点坐标 (x, y, z)，如果未找到则返回None

        说明:
            需要在配置文件中预先配置各地图的中心点
            配置格式示例：
            {
                "map_centers": {
                    "10000": [0, 100, 0],
                    "10001": [100, 65, 100],
                    ...
                }
            }
        """
        # TODO: 从配置文件加载地图中心点
        # 这里提供一个占位实现
        default_centers = {
            10000: (0, 100, 0),
            10001: (100, 65, 100),
        }

        center = default_centers.get(dimension)
        if center:
            print("[INFO] [CameraPreviewHelper] 找到地图中心点: {} -> {}".format(dimension, center))
        else:
            print("[WARN] [CameraPreviewHelper] 未找到维度 {} 的地图中心点配置".format(dimension))

        return center


# ===== 全局工具函数 =====

def start_camera_preview(system, center_pos, players=None, **kwargs):
    """
    全局工具函数：启动地图预览运镜

    Args:
        system: 游戏系统实例
        center_pos (tuple): 地图中心点坐标
        players (list, optional): 指定玩家列表
        **kwargs: 其他可选参数（radius, angular_velocity, height_offset）

    示例:
        from systems.util.CameraPreviewHelper import start_camera_preview

        start_camera_preview(self, (0, 100, 0))
        start_camera_preview(self, (0, 100, 0), players=['p1'], radius=15.0)
    """
    helper = CameraPreviewHelper(system)
    helper.start_preview(center_pos, players=players, **kwargs)


def stop_camera_preview(system, players=None):
    """
    全局工具函数：停止地图预览运镜

    Args:
        system: 游戏系统实例
        players (list, optional): 指定玩家列表

    示例:
        from systems.util.CameraPreviewHelper import stop_camera_preview

        stop_camera_preview(self)
        stop_camera_preview(self, players=['p1', 'p2'])
    """
    helper = CameraPreviewHelper(system)
    helper.stop_preview(players=players)
