# -*- coding: utf-8 -*-
"""
复活点预设 - 服务端

功能:
- 记录复活点位置和朝向
- 提供复活点查询接口
- 上报复活点数据到游戏系统
"""

from ECPresetServerScripts import PresetDefinitionServer


class SpawnPresetDefServer(PresetDefinitionServer):
    """
    复活点预设服务端实现

    核心功能:
    1. 记录复活点位置和朝向
    2. 提供复活点信息查询
    3. 上报数据到游戏系统
    4. 处理玩家复活事件
    """

    def __init__(self):
        super(SpawnPresetDefServer, self).__init__()

        # 配置数据
        self.team = None  # type: str | None  # 队伍ID

        # 运行时状态
        self.spawn_position = None  # type: tuple | None  # 复活点位置 (x, y, z)
        self.spawn_rotation = None  # type: tuple | None  # 复活点朝向 (pitch, yaw)

    def on_init(self, instance):
        """
        预设初始化

        解析配置数据:
        - team: 队伍ID
        - position: 复活点位置 (可选,默认使用预设位置)
        - rotation: 复活点朝向 (可选,默认使用预设朝向)

        Args:
            instance: PresetInstance对象
        """
        self.team = instance.get_config("team")
        if not self.team:
            print("[ERROR] SpawnPresetDefServer.on_init 缺少team配置")
            return

        # 获取复活点位置
        pos_data = instance.get_config("position")
        if pos_data:
            # position可能是字典或列表
            if isinstance(pos_data, dict):
                self.spawn_position = (pos_data.get('x', 0), pos_data.get('y', 0), pos_data.get('z', 0))
            else:
                self.spawn_position = tuple(pos_data)
        else:
            # 使用预设位置 - pos通常是列表 [x, y, z]
            pos = instance.get_config("pos")
            if isinstance(pos, dict):
                self.spawn_position = (pos['x'], pos['y'], pos['z'])
            else:
                self.spawn_position = tuple(pos)

        # 获取复活点朝向
        rot_data = instance.get_config("rotation")
        if rot_data:
            self.spawn_rotation = (rot_data.get('pitch', 0), rot_data.get('yaw', 0))
        else:
            # 默认朝向
            self.spawn_rotation = (0, 0)

        print("[INFO] [复活点] 初始化: team={}, pos={}".format(
            self.team, self.spawn_position
        ))

        # 保存配置到instance
        instance.set_data("team", self.team)
        instance.set_data("spawn_position", self.spawn_position)
        instance.set_data("spawn_rotation", self.spawn_rotation)

    def on_start(self, instance):
        """
        预设启动

        执行步骤:
        1. 上报复活点数据到游戏系统
        2. 注册事件监听

        Args:
            instance: PresetInstance对象
        """
        print("[INFO] [复活点] 启动: team={}".format(self.team))

        # 1. 上报复活点数据到游戏系统
        self._notify_spawn_data_to_game_system(instance)

        # 2. 注册事件监听
        # 注意：ECPreset框架的事件系统API可能与网易Preset不同
        # 暂时注释掉，这些事件监听不是核心功能
        # 监听玩家复活事件
        # instance.subscribe_event("PlayerRespawnEvent", self._on_player_respawn)

        # 监听复活点查询事件
        # instance.subscribe_event("QuerySpawnLocation", self._on_query_spawn_location)

    def on_tick(self, instance):
        """
        每Tick更新

        复活点预设通常不需要Tick更新

        Args:
            instance: PresetInstance对象
        """
        pass

    def on_stop(self, instance):
        """
        预设停止

        清理工作:
        1. 取消事件监听

        Args:
            instance: PresetInstance对象
        """
        print("[INFO] [复活点] 停止: team={}".format(self.team))

        # 取消事件监听
        # EventBus事件会自动取消订阅
        # EventBus事件会自动取消订阅

    def on_destroy(self, instance):
        """
        预设销毁

        最终清理工作

        Args:
            instance: PresetInstance对象
        """
        print("[INFO] [复活点] 销毁: team={}".format(self.team))

        # 清理数据
        self.spawn_position = None
        self.spawn_rotation = None

    # ========== 事件处理方法 ==========

    def _on_player_respawn(self, event_data):
        """
        处理玩家复活事件

        将对应队伍的玩家传送到复活点

        Args:
            event_data: 事件数据
                - playerId: 玩家ID
                - teamId: 队伍ID
        """
        player_id = event_data.get('playerId')
        team_id = event_data.get('teamId')

        # 检查是否是本队伍的玩家
        if team_id != self.team:
            return

        print("[INFO] [复活点] 玩家复活: player={}, team={}".format(player_id, team_id))

        # 传送玩家到复活点
        self._teleport_player_to_spawn(player_id)

    def _on_query_spawn_location(self, event_data):
        """
        处理复活点查询事件

        返回复活点的位置和朝向信息

        Args:
            event_data: 事件数据
                - teamId: 队伍ID
        """
        team_id = event_data.get('teamId')

        # 检查是否是本队伍
        if team_id != self.team:
            return

        # 返回复活点信息
        spawn_info = {
            'team': self.team,
            'position': self.spawn_position,
            'rotation': self.spawn_rotation
        }

        # 发送回复事件
        self.instance.manager.event_bus.emit_event('SpawnLocationResponse', spawn_info)

    # ========== 内部辅助方法 ==========

    def _teleport_player_to_spawn(self, player_id):
        """
        传送玩家到复活点

        Args:
            player_id: 玩家ID
        """
        if not self.spawn_position:
            print("[ERROR] [复活点] 位置未设置")
            return

        print("[INFO] [复活点] 传送玩家: player={}, pos={}".format(
            player_id, self.spawn_position
        ))

        try:
            import mod.server.extraServerApi as serverApi
            comp_factory = serverApi.GetEngineCompFactory()

            # 获取维度ID
            dimension_id = self.instance.get_config("dimension_id", 0)

            # 传送玩家到复活点
            pos_comp = comp_factory.CreatePos(player_id)
            pos_comp.SetFootPos(self.spawn_position)

            # 设置玩家朝向
            if self.spawn_rotation:
                rot_comp = comp_factory.CreateRot(player_id)
                # spawn_rotation 是 (pitch, yaw), 引擎需要 (pitch, yaw)
                rot_comp.SetRot((self.spawn_rotation[0], self.spawn_rotation[1]))

            # 清除玩家速度（防止摔落伤害）
            actor_motion_comp = comp_factory.CreateActorMotion(player_id)
            actor_motion_comp.SetMotion((0, 0, 0))

            # 播放传送特效（末影人传送粒子）
            try:
                particle_comp = comp_factory.CreateParticle(player_id)
                # 在玩家位置播放紫色传送粒子
                particle_comp.SpawnParticle(self.spawn_position, "minecraft:portal", dimension_id)
            except Exception as particle_error:
                # 特效播放失败不影响主流程
                print("[WARN] [复活点] 播放传送特效失败: {}".format(str(particle_error)))

            print("[INFO] [复活点] 玩家传送成功: player={}, pos={}".format(
                player_id, self.spawn_position
            ))

        except Exception as e:
            print("[ERROR] [复活点] 传送玩家失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _notify_spawn_data_to_game_system(self, instance):
        """
        上报复活点数据到游戏系统

        用于游戏系统的自检和管理

        Args:
            instance: PresetInstance对象
        """
        spawn_id = "spawn_{}_{}".format(instance.get_config("dimension_id", 0), self.team)

        spawn_data = {
            "spawn_id": spawn_id,
            "dimension": instance.get_config("dimension_id", 0),
            "team": self.team,
            "position": self.spawn_position,
            "rotation": self.spawn_rotation,
        }

        print("[INFO] [复活点] 上报数据: {}".format(spawn_id))

        # 发送复活点数据事件到游戏系统
        # 注意：ECPreset框架的EventBus API与网易Preset系统不同
        # 这里注释掉，改为直接通过PresetDefinition属性暴露数据
        # instance.manager.event_bus.emit_event("SpawnDataReport", spawn_data)

        # 游戏系统会通过get_definition()获取预设定义对象，
        # 然后直接访问team、spawn_position、spawn_rotation属性

    def get_location(self):
        """
        获取复活点位置信息

        供外部调用的公共方法

        Returns:
            tuple: (position, rotation)
                position: (x, y, z)
                rotation: (pitch, yaw)
        """
        return self.spawn_position, self.spawn_rotation

    def set_location(self, position, rotation=None):
        """
        设置复活点位置信息

        供外部调用的公共方法

        Args:
            position: 位置 (x, y, z)
            rotation: 朝向 (pitch, yaw),可选
        """
        self.spawn_position = position

        if rotation:
            self.spawn_rotation = rotation

        print("[INFO] [复活点] 更新位置: pos={}".format(position))

        # 更新instance数据
        self.instance.set_data("spawn_position", self.spawn_position)
        self.instance.set_data("spawn_rotation", self.spawn_rotation)