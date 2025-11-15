# -*- coding: utf-8 -*-
"""
复活点预设 - 客户端

功能:
- 显示复活点标识特效
- 播放玩家复活特效
- 播放复活音效
- 显示队伍颜色标识
"""

from ECPresetServerScripts import PresetDefinitionClient


class SpawnPresetDefClient(PresetDefinitionClient):
    """
    复活点预设客户端实现

    核心功能:
    1. 复活点标识特效 (团队颜色圈)
    2. 玩家复活传送特效
    3. 复活音效
    4. 复活点粒子效果
    """

    def __init__(self):
        super(SpawnPresetDefClient, self).__init__()

        # 配置数据
        self.team = None  # type: str | None  # 队伍ID

        # 特效ID列表
        self._effect_ids = []

        # 复活点标识特效ID
        self._spawn_indicator_effect_id = None

        # 粒子循环ID
        self._particle_loop_id = None

        # ========== P1.1功能数据成员 ==========
        self.particle_circle_id = None  # type: int | None  # 粒子圈ID

    def on_init(self, instance):
        """
        预设初始化

        解析配置数据:
        - team: 队伍ID

        Args:
            instance: PresetInstanceClient对象
        """
        self.team = instance.data.get("team", "NONE")
        if not self.team or self.team == "NONE":
            if not instance.data.get("team"):
                print("[WARN] SpawnPresetDefClient.on_init 缺少team配置, 使用默认值: NONE")

        print("[INFO] [复活点-客户端] 初始化: team={}".format(self.team))

    def on_start(self, instance):
        """
        预设启动

        执行步骤:
        1. 创建复活点标识特效
        2. 开始粒子循环
        3. 注册事件监听

        Args:
            instance: PresetInstanceClient对象
        """
        print("[INFO] [复活点-客户端] 启动: team={}".format(self.team))

        # 1. 创建复活点标识特效
        self._create_spawn_indicator(instance)

        # 2. 开始粒子循环
        self._start_particle_loop(instance)

        # 注意: 事件通过on_server_message接收,不需要手动注册

    def on_tick(self, instance):
        """
        每Tick更新

        复活点客户端通常不需要Tick更新

        Args:
            instance: PresetInstanceClient对象
        """
        pass

    def on_stop(self, instance):
        """
        预设停止

        清理工作:
        1. 移除复活点标识特效
        2. 停止粒子循环
        3. 取消事件监听
        4. 清理粒子圈 (P1.1)

        Args:
            instance: PresetInstanceClient对象
        """
        print("[INFO] [复活点-客户端] 停止: team={}".format(self.team))

        # 移除复活点标识特效
        if self._spawn_indicator_effect_id:
            self._stop_effect(self._spawn_indicator_effect_id)
            self._spawn_indicator_effect_id = None

        # 停止粒子循环
        if self._particle_loop_id:
            self._stop_particle(self._particle_loop_id)
            self._particle_loop_id = None

        # 停止所有特效
        self._stop_all_effects()

        # P1.1功能：清理粒子圈
        self._cleanup_particle_circle()

    def on_destroy(self, instance):
        """
        预设销毁

        最终清理工作

        Args:
            instance: PresetInstanceClient对象
        """
        print("[INFO] [复活点-客户端] 销毁: team={}".format(self.team))

        # 清理数据
        self._effect_ids = []
        self._spawn_indicator_effect_id = None
        self._particle_loop_id = None

    # ========== 接收服务端消息 ==========

    def on_server_message(self, instance, message_type, data):
        """
        接收服务端消息回调 - ECPreset框架标准接口

        Args:
            instance: PresetInstanceClient对象
            message_type: str 消息类型
            data: dict 消息数据
        """
        if message_type == "PlayerRespawnEvent":
            self._on_player_respawn(data)

    # ========== 事件处理方法 ==========

    def _on_player_respawn(self, event_data):
        """
        处理玩家复活事件

        播放复活传送特效和音效

        Args:
            event_data: 事件数据
                - playerId: 玩家ID
                - teamId: 队伍ID
        """
        team_id = event_data.get('teamId')

        # 只处理本复活点对应的队伍
        if team_id != self.team:
            return

        player_id = event_data.get('playerId')
        print("[INFO] [复活点-客户端] 玩家复活: player={}, team={}".format(
            player_id, team_id
        ))

        # 播放复活传送特效
        self._play_respawn_effect()

        # 播放复活音效
        self._play_respawn_sound()

    # ========== 内部辅助方法 ==========

    def _create_spawn_indicator(self, instance):
        """
        创建复活点标识特效

        P1.1功能：在复活点地面显示团队颜色的粒子圈

        Args:
            instance: PresetInstanceClient对象
        """
        try:
            from Script_NeteaseMod.systems.util.ClientAPIHelper import ClientAPIHelper

            # [FIX 2025-11-04] 修复PresetInstanceClient没有get_position()方法的问题
            # 正确方式：从config中读取position
            position = instance.get_config("position") or instance.get_config("pos")
            if not position:
                print("[ERROR] [复活点-客户端] 无法获取position配置")
                return

            print("[INFO] [复活点-客户端] 创建复活点标识: team={}, pos={}".format(
                self.team, position
            ))

            # 计算地面位置
            if isinstance(position, dict):
                particle_pos = (
                    position['x'] + 0.5,  # 中心位置
                    position['y'] + 0.1,  # 地面上方0.1格
                    position['z'] + 0.5   # 中心位置
                )
            else:
                particle_pos = (
                    position[0] + 0.5,
                    position[1] + 0.1,
                    position[2] + 0.5
                )

            # 获取队伍颜色（RGB归一化）
            team_color = self._get_team_color_rgb(self.team)

            # 使用ClientAPIHelper创建粒子圈（持续播放）
            # 注意：play_particle会播放单次粒子，所以我们使用minecraft:villager_happy作为简化方案
            # 实际项目中可以使用play_particle_circle创建圆圈粒子
            self.particle_circle_id = ClientAPIHelper.play_particle(
                "minecraft:villager_happy",  # 使用愉快粒子作为简化方案
                particle_pos
            )

            if self.particle_circle_id:
                print("[INFO] [复活点-客户端] 创建粒子圈成功: particle_id={}".format(
                    self.particle_circle_id
                ))
            else:
                print("[WARN] [复活点-客户端] 创建粒子圈失败")

        except Exception as e:
            print("[ERROR] [复活点-客户端] 创建复活点标识异常: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _start_particle_loop(self, instance):
        # type: (object) -> None
        """
        开始粒子循环

        P2.1功能实现 - 在复活点周围显示循环粒子

        Args:
            instance: PresetInstanceClient对象
        """
        try:
            from Script_NeteaseMod.systems.util.ClientAPIHelper import ClientAPIHelper
            import math

            # [FIX 2025-11-04] 修复PresetInstanceClient没有get_position()方法的问题
            position = instance.get_config("position") or instance.get_config("pos")
            if not position:
                print("[ERROR] [复活点-客户端] 无法获取position配置")
                return

            print("[INFO] [复活点-客户端] 启动粒子循环: team={}, pos={}".format(
                self.team, position
            ))

            # 计算中心位置
            if isinstance(position, dict):
                center_x = position['x'] + 0.5
                center_y = position['y'] + 0.1
                center_z = position['z'] + 0.5
            else:
                center_x = position[0] + 0.5
                center_y = position[1] + 0.1
                center_z = position[2] + 0.5

            # 在复活点周围创建圆圈粒子效果（简化方案）
            # 在圆周上均匀分布8个粒子点
            radius = 1.5  # 圆圈半径
            particle_count = 8  # 粒子数量

            for i in range(particle_count):
                angle = 2.0 * math.pi * i / particle_count
                particle_x = center_x + radius * math.cos(angle)
                particle_z = center_z + radius * math.sin(angle)
                particle_pos = (particle_x, center_y, particle_z)

                # 播放粒子
                particle_id = ClientAPIHelper.play_particle(
                    "minecraft:villager_happy",  # 绿色爱心粒子
                    particle_pos
                )

                if particle_id:
                    print("[INFO] [复活点-客户端] 创建循环粒子: id={}, pos={}".format(
                        particle_id, particle_pos
                    ))

            print("[INFO] [复活点-客户端] 粒子循环启动完成")

        except Exception as e:
            print("[ERROR] [复活点-客户端] 启动粒子循环异常: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _play_respawn_effect(self):
        # type: () -> None
        """
        播放复活传送特效

        P2.2功能实现（粒子特效部分）
        """
        try:
            from Script_NeteaseMod.systems.util.ClientAPIHelper import ClientAPIHelper

            # 获取位置
            if not hasattr(self, 'instance') or not self.instance:
                print("[WARN] [复活点-客户端] instance未初始化，无法播放复活特效")
                return

            # [FIX 2025-11-04] 修复PresetInstanceClient没有get_position()方法的问题
            position = self.instance.get_config("position") or self.instance.get_config("pos")
            if not position:
                print("[ERROR] [复活点-客户端] 无法获取position配置")
                return

            if isinstance(position, dict):
                pos = (position['x'] + 0.5, position['y'] + 0.5, position['z'] + 0.5)
            else:
                pos = (position[0] + 0.5, position[1] + 0.5, position[2] + 0.5)

            print("[INFO] [复活点-客户端] 播放复活特效: team={}, pos={}".format(self.team, pos))

            # 播放传送门粒子效果（15个粒子）
            for i in range(15):
                particle_id = ClientAPIHelper.play_particle(
                    "minecraft:portal",  # 传送门粒子（紫色）
                    pos
                )
                if particle_id:
                    print("[INFO] [复活点-客户端] 播放传送门粒子: id={}, pos={}".format(particle_id, pos))

            # 播放团队颜色粒子向上飞溅（10个粒子）
            for i in range(10):
                particle_id = ClientAPIHelper.play_particle(
                    "minecraft:villager_happy",  # 绿色爱心粒子（作为团队粒子的简化替代）
                    pos
                )
                if particle_id:
                    print("[INFO] [复活点-客户端] 播放团队颜色粒子: id={}, pos={}".format(particle_id, pos))

            print("[INFO] [复活点-客户端] 复活特效播放完成")

        except Exception as e:
            print("[ERROR] [复活点-客户端] 播放复活特效异常: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _play_respawn_sound(self):
        # type: () -> None
        """
        播放复活音效

        P2.2功能实现（音效部分）
        """
        try:
            import mod.client.extraClientApi as clientApi

            # 获取位置
            if not hasattr(self, 'instance') or not self.instance:
                print("[WARN] [复活点-客户端] instance未初始化，无法播放复活音效")
                return

            # [FIX 2025-11-04] 修复PresetInstanceClient没有get_position()方法的问题
            position = self.instance.get_config("position") or self.instance.get_config("pos")
            if not position:
                print("[ERROR] [复活点-客户端] 无法获取position配置")
                return

            if isinstance(position, dict):
                pos = (position['x'] + 0.5, position['y'] + 0.5, position['z'] + 0.5)
            else:
                pos = (position[0] + 0.5, position[1] + 0.5, position[2] + 0.5)

            # 获取游戏组件
            game_comp = clientApi.GetEngineCompFactory().CreateGame(clientApi.GetLevelId())

            # 播放传送门音效："mob.endermen.portal" - 末影人传送音效
            game_comp.PlaySound(
                "mob.endermen.portal",  # 音效名称
                pos,                    # 播放位置
                0.8,                    # 音量
                1.0                     # 音调
            )

            print("[INFO] [复活点-客户端] 播放复活音效: team={}, pos={}".format(self.team, pos))

        except Exception as e:
            print("[ERROR] [复活点-客户端] 播放复活音效异常: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _get_team_indicator_path(self, team):
        """
        获取团队标识特效路径

        Args:
            team: 队伍ID

        Returns:
            str: 特效路径
        """
        # 根据队伍返回不同颜色的地面圈特效
        indicator_map = {
            'RED': 'particles/spawn_circle_red.json',
            'BLUE': 'particles/spawn_circle_blue.json',
            'GREEN': 'particles/spawn_circle_green.json',
            'YELLOW': 'particles/spawn_circle_yellow.json',
            'AQUA': 'particles/spawn_circle_aqua.json',
            'WHITE': 'particles/spawn_circle_white.json',
            'LIGHT_PURPLE': 'particles/spawn_circle_purple.json',
            'GRAY': 'particles/spawn_circle_gray.json',
        }

        return indicator_map.get(team, 'particles/spawn_circle_default.json')

    def _get_team_particle_type(self, team):
        """
        获取团队粒子类型

        Args:
            team: 队伍ID

        Returns:
            str: 粒子类型
        """
        # 根据队伍返回不同颜色的粒子
        particle_map = {
            'RED': 'minecraft:red_glint',
            'BLUE': 'minecraft:blue_glint',
            'GREEN': 'minecraft:green_glint',
            'YELLOW': 'minecraft:yellow_glint',
            'AQUA': 'minecraft:cyan_glint',
            'WHITE': 'minecraft:white_glint',
            'LIGHT_PURPLE': 'minecraft:purple_glint',
            'GRAY': 'minecraft:gray_glint',
        }

        return particle_map.get(team, 'minecraft:white_glint')

    # ========== 特效和音效工具方法 ==========

    def _play_effect(self, effect_path, position):
        """
        播放特效

        Args:
            effect_path: 特效文件路径
            position: 特效位置 (dict: {x, y, z})

        Returns:
            int: 特效ID
        """
        # TODO: 需要引擎API支持
        print("[INFO] 播放特效: {} at {}".format(effect_path, position))
        return 0  # 占位返回

    def _stop_effect(self, effect_id):
        """
        停止特效

        Args:
            effect_id: 特效ID
        """
        # TODO: 需要引擎API支持
        print("[INFO] 停止特效: {}".format(effect_id))

    def _stop_all_effects(self):
        """停止所有特效"""
        for effect_id in self._effect_ids:
            self._stop_effect(effect_id)
        self._effect_ids = []

    def _play_sound(self, sound_path, position, volume=1.0):
        """
        播放音效

        Args:
            sound_path: 音效文件路径
            position: 播放位置
            volume: 音量 (0.0-1.0)
        """
        # TODO: 需要引擎API支持
        print("[INFO] 播放音效: {} at {} (volume={})".format(
            sound_path, position, volume
        ))

    def _create_particle(self, particle_type, position):
        """
        创建粒子效果

        Args:
            particle_type: 粒子类型
            position: 粒子位置

        Returns:
            int: 粒子效果ID
        """
        # TODO: 需要引擎API支持
        print("[INFO] 创建粒子效果: {} at {}".format(particle_type, position))
        return 0  # 占位返回

    def _create_looping_particle(self, particle_type, position):
        """
        创建循环粒子效果

        Args:
            particle_type: 粒子类型
            position: 粒子位置

        Returns:
            int: 粒子效果ID
        """
        # TODO: 需要引擎API支持
        print("[INFO] 创建循环粒子: {} at {}".format(particle_type, position))
        return 0  # 占位返回

    def _stop_particle(self, particle_id):
        """
        停止粒子效果

        Args:
            particle_id: 粒子效果ID
        """
        # TODO: 需要引擎API支持
        print("[INFO] 停止粒子效果: {}".format(particle_id))

    # ========== P1.1功能实现 ==========

    def _get_team_color_rgb(self, team_id):
        # type: (str) -> tuple
        """
        获取队伍颜色的RGB值（归一化，0.0-1.0）

        Args:
            team_id: 队伍ID (RED, BLUE, GREEN, YELLOW等)

        Returns:
            tuple: (R, G, B) 归一化RGB值
        """
        color_map = {
            'RED': (1.0, 0.0, 0.0),
            'BLUE': (0.0, 0.0, 1.0),
            'GREEN': (0.0, 1.0, 0.0),
            'YELLOW': (1.0, 1.0, 0.0),
            'PINK': (1.0, 0.4, 0.7),
            'CYAN': (0.0, 1.0, 1.0),
            'WHITE': (1.0, 1.0, 1.0),
            'GRAY': (0.5, 0.5, 0.5),
            'AQUA': (0.0, 1.0, 1.0),
            'LIGHT_PURPLE': (0.7, 0.4, 1.0)
        }

        return color_map.get(team_id.upper() if team_id else 'WHITE', (1.0, 1.0, 1.0))

    def _cleanup_particle_circle(self):
        # type: () -> None
        """
        清理粒子圈

        P1.1功能清理逻辑
        """
        try:
            if self.particle_circle_id is not None:
                from Script_NeteaseMod.systems.util.ClientAPIHelper import ClientAPIHelper
                success = ClientAPIHelper.remove_particle(self.particle_circle_id)

                if success:
                    print("[INFO] [复活点-客户端] 粒子圈已清理: particle_id={}".format(
                        self.particle_circle_id
                    ))
                self.particle_circle_id = None

        except Exception as e:
            print("[ERROR] [复活点-客户端] 清理粒子圈异常: {}".format(str(e)))
            import traceback
            traceback.print_exc()