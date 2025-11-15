# -*- coding: utf-8 -*-
"""
BedDestroyEffectManager - 床破坏特效管理器

功能:
- 管理床破坏特效
- 播放床破坏特效
- 支持多种特效类型

原文件: Parts/ECBedWarsOrnament/ornament/BedWarsOrnamentBedDestroyEffect.py
重构为: systems/ornament_system/ornament/BedDestroyEffectManager.py
"""

import mod.server.extraServerApi as serverApi
import time
import math
import random


class BedDestroyEffectConfig(object):
    """床破坏特效配置"""

    def __init__(self, effect_id, name, effect_type):
        """
        初始化床破坏特效配置

        Args:
            effect_id (str): 特效ID
            name (str): 特效名称
            effect_type (str): 特效类型
        """
        self.effect_id = effect_id
        self.name = name
        self.effect_type = effect_type


class BedDestroyEffectManager(object):
    """
    床破坏特效管理器

    负责床破坏特效的播放和管理
    """

    # 床破坏特效配置
    BED_DESTROY_EFFECT_CONFIGS = {
        "default": BedDestroyEffectConfig("default", u"默认", "default"),
        "yanhua": BedDestroyEffectConfig("yanhua", u"烟花", "yanhua"),
        "gold": BedDestroyEffectConfig("gold", u"金黄", "gold"),
        "cow": BedDestroyEffectConfig("cow", u"勇敢牛牛", "cow"),
        "heart": BedDestroyEffectConfig("heart", u"爱心", "heart"),
        "boom": BedDestroyEffectConfig("boom", u"爆炸", "boom"),
        "lightning": BedDestroyEffectConfig("lightning", u"雷击", "lightning"),
        "qingchun": BedDestroyEffectConfig("qingchun", u"青春飞扬", "qingchun"),
    }

    def __init__(self, ornament_system):
        """
        初始化床破坏特效管理器

        Args:
            ornament_system: OrnamentSystem实例
        """
        self.ornament_system = ornament_system
        self.game_system = ornament_system.game_system

        # 定时器管理器(复用victory_dance的定时器)
        self.timer_manager = None
        self.effect_counter = 0

        print("[INFO] [BedDestroyEffectManager] 初始化完成")

    def initialize(self):
        """初始化床破坏特效管理器"""
        try:
            # 使用VictoryDanceManager的定时器
            if hasattr(self.ornament_system, 'victory_dance_manager'):
                self.timer_manager = self.ornament_system.victory_dance_manager.timer_manager

            print("[INFO] [BedDestroyEffectManager] 床破坏特效管理器初始化成功")
        except Exception as e:
            print("[ERROR] [BedDestroyEffectManager] 初始化失败: {}".format(str(e)))

    def cleanup(self):
        """清理床破坏特效管理器"""
        try:
            print("[INFO] [BedDestroyEffectManager] 清理完成")
        except Exception as e:
            print("[ERROR] [BedDestroyEffectManager] 清理失败: {}".format(str(e)))

    def get_next_effect_id(self):
        """获取下一个特效ID"""
        self.effect_counter += 1
        return "bed_effect_{}".format(self.effect_counter)

    def play_bed_destroy_effect(self, destroyer_id, bed_pos, team_id):
        """
        播放床破坏特效

        Args:
            destroyer_id (str): 破坏者ID
            bed_pos (tuple): 床位置 (x, y, z)
            team_id (str): 队伍ID
        """
        try:
            # 获取破坏者装备的床破坏特效
            effect_id = self.ornament_system.get_player_ornament(destroyer_id, 'bed_destroy_effect')
            if not effect_id:
                effect_id = 'default'

            # 获取特效配置
            effect_config = self.BED_DESTROY_EFFECT_CONFIGS.get(effect_id)
            if not effect_config:
                print("[WARN] [BedDestroyEffectManager] 未找到床破坏特效配置: {}".format(effect_id))
                return

            # 播放特效
            self._play_effect(destroyer_id, effect_config.effect_type, bed_pos)

            print("[INFO] [BedDestroyEffectManager] 玩家 {} 破坏 {} 的床, 播放特效: {}".format(
                destroyer_id, team_id, effect_id
            ))
        except Exception as e:
            print("[ERROR] [BedDestroyEffectManager] 播放床破坏特效失败: {}".format(str(e)))

    def _play_effect(self, player_id, effect_type, bed_pos):
        """
        播放特效

        Args:
            player_id (str): 玩家ID
            effect_type (str): 特效类型
            bed_pos (tuple): 床位置 (x, y, z)
        """
        # 调用对应的特效方法
        method_name = "play_{}_effect".format(effect_type.replace("-", "_"))
        if hasattr(self, method_name):
            effect_method = getattr(self, method_name)
            effect_method(bed_pos)
        else:
            print("[ERROR] [BedDestroyEffectManager] 未找到特效方法: {}".format(method_name))

    # ========== 辅助方法 ==========

    def spawn_timed_particle(self, pos, particle_type, delay=0.0):
        """
        生成带定时延迟的粒子

        Args:
            pos (tuple): 位置 (x, y, z)
            particle_type (str): 粒子类型
            delay (float): 延迟时间(秒)
        """
        def spawn_callback(timer_id):
            self._spawn_particle(pos, particle_type)

        if delay > 0 and self.timer_manager:
            timer_id = self.get_next_effect_id()
            self.timer_manager.add_timer(timer_id, delay, spawn_callback)
        else:
            spawn_callback(None)

    def _spawn_particle(self, pos, particle_type):
        """在指定位置生成粒子"""
        try:
            command = "/particle {} {} {} {}".format(
                particle_type, pos[0], pos[1], pos[2]
            )
            self._execute_command(command)
        except Exception as e:
            print("[ERROR] [BedDestroyEffectManager] 生成粒子失败: {}".format(str(e)))

    def _play_sound(self, pos, sound_name, volume=1.0, pitch=1.0):
        """在指定位置播放音效"""
        try:
            command = "/playsound {} @a {} {} {} {} {}".format(
                sound_name, pos[0], pos[1], pos[2], volume, pitch
            )
            self._execute_command(command)
        except Exception as e:
            print("[ERROR] [BedDestroyEffectManager] 播放音效失败: {}".format(str(e)))

    def _execute_command(self, command):
        """执行命令"""
        try:
            comp = serverApi.GetEngineCompFactory()
            command_comp = comp.CreateCommand(serverApi.GetLevelId())
            command_comp.SetCommand(command)
        except Exception as e:
            print("[ERROR] [BedDestroyEffectManager] 执行命令失败: {}".format(str(e)))

    # ========== 特效实现 ==========

    def play_default_effect(self, bed_pos):
        """默认特效 - 简单的粒子效果"""
        self._spawn_particle(bed_pos, 'minecraft:critical_hit_emitter')

    def play_yanhua_effect(self, bed_pos):
        """烟花特效 - 连续绽放的多彩烟花"""
        # 初始音效
        self._play_sound(bed_pos, "firework.blast", 1.0, 1.0)

        firework_colors = [
            'minecraft:firework_emitter',
            'minecraft:critical_hit_emitter',
            'minecraft:end_rod',
            'minecraft:totem_particle'
        ]

        # 5波连续烟花
        for wave in range(5):
            wave_delay = wave * 0.4
            particle_type = firework_colors[wave % len(firework_colors)]

            # 每波延迟音效
            if wave > 0:
                def delayed_blast(timer_id, w=wave):
                    self._play_sound(bed_pos, "firework.blast", max(0.3, 1.0 - w * 0.15), 1.0 + w * 0.1)

                self.timer_manager.add_timer(self.get_next_effect_id(), wave_delay, delayed_blast)

            # 每波多层烟花
            for layer in range(3):
                layer_delay = wave_delay + layer * 0.08
                height = bed_pos[1] + 2 + layer * 0.4
                radius = 1.5 - wave * 0.2 + layer * 0.2

                # 每层8个方向
                for i in range(8):
                    particle_delay = layer_delay + i * 0.02
                    angle = i * 45

                    x_offset = math.cos(math.radians(angle)) * radius
                    z_offset = math.sin(math.radians(angle)) * radius
                    pos = (bed_pos[0] + x_offset, height, bed_pos[2] + z_offset)

                    self.spawn_timed_particle(pos, particle_type, particle_delay)

    def play_gold_effect(self, bed_pos):
        """金黄特效 - 渐变螺旋上升"""
        # 音效
        self._play_sound(bed_pos, "random.orb", 2.0, 0.5)
        self._play_sound(bed_pos, "note.pling", 1.5, 0.8)

        # 分阶段螺旋上升
        particle_types = ['minecraft:end_rod', 'minecraft:flame_particle', 'minecraft:redstone_ore_dust_particle']

        for phase in range(3):
            for i in range(10):
                delay = phase * 0.5 + i * 0.05

                # 螺旋计算
                angle = (phase * 10 + i) * 18
                height_offset = (phase * 10 + i) * 0.1
                radius = 1.5 - (phase * 10 + i) * 0.03

                x_offset = math.cos(math.radians(angle)) * radius
                z_offset = math.sin(math.radians(angle)) * radius
                pos = (bed_pos[0] + x_offset, bed_pos[1] + 1 + height_offset, bed_pos[2] + z_offset)

                # 根据阶段使用不同粒子
                particle_type = particle_types[phase]
                self.spawn_timed_particle(pos, particle_type, delay)

    def play_boom_effect(self, bed_pos):
        """爆炸特效 - 环形冲击波"""
        self._play_sound(bed_pos, "random.explode", 1.0, 1.0)

        # 中心爆炸
        self._spawn_particle((bed_pos[0], bed_pos[1] + 1, bed_pos[2]), 'minecraft:large_explosion_emitter')

        # 环形冲击波
        for ring in range(3):
            ring_delay = ring * 0.1
            radius = 0.8 + ring * 0.6

            for i in range(12):
                particle_delay = ring_delay + i * 0.02
                angle = i * 30

                x_offset = math.cos(math.radians(angle)) * radius
                z_offset = math.sin(math.radians(angle)) * radius
                pos = (bed_pos[0] + x_offset, bed_pos[1] + 0.5, bed_pos[2] + z_offset)

                # 根据环形使用不同粒子
                if ring == 0:
                    self.spawn_timed_particle(pos, 'minecraft:flame_particle', particle_delay)
                elif ring == 1:
                    self.spawn_timed_particle(pos, 'minecraft:lava_particle', particle_delay)
                else:
                    self.spawn_timed_particle(pos, 'minecraft:smoke_particle', particle_delay)

    def play_lightning_effect(self, bed_pos):
        """雷击特效 - 垂直闪电柱"""
        self._play_sound(bed_pos, "ambient.weather.thunder", 1.0, 1.0)

        # 垂直闪电柱
        for height in range(8):
            height_delay = height * 0.05
            y_pos = bed_pos[1] + height * 0.5

            # 随机偏移
            x_offset = random.uniform(-0.2, 0.2)
            z_offset = random.uniform(-0.2, 0.2)
            pos = (bed_pos[0] + x_offset, y_pos, bed_pos[2] + z_offset)

            # 交替使用不同粒子
            if height % 2 == 0:
                self.spawn_timed_particle(pos, 'minecraft:end_rod', height_delay)
            else:
                self.spawn_timed_particle(pos, 'minecraft:critical_hit_emitter', height_delay)

    def play_heart_effect(self, bed_pos):
        """爱心特效 - 脉动的3D心形粒子云"""
        # 音效
        self._play_sound(bed_pos, "note.pling", 0.8, 1.5)

        # 多阶段心形
        for stage_idx in range(3):
            stage_delay = stage_idx * 0.4
            scale_factor = 0.6 + stage_idx * 0.2

            # 每个阶段生成心形
            for layer in range(3):
                layer_delay = stage_delay + layer * 0.02

                for t in range(12):
                    particle_delay = layer_delay + t * 0.01

                    angle = t * math.pi / 6
                    # 心形参数方程
                    x = 16 * math.sin(angle) ** 3
                    y = 13 * math.cos(angle) - 5 * math.cos(2*angle) - 2 * math.cos(3*angle) - math.cos(4*angle)

                    # 应用缩放
                    base_scale = 0.05 * scale_factor
                    x_offset = x * base_scale
                    y_offset = y * base_scale * 0.4
                    z_offset = (layer - 1) * 0.2

                    pos = (bed_pos[0] + x_offset, bed_pos[1] + 1.5 + y_offset, bed_pos[2] + z_offset)

                    self.spawn_timed_particle(pos, 'minecraft:heart_particle', particle_delay)

    def play_qingchun_effect(self, bed_pos):
        """青春飞扬特效 - 彩虹漩涡"""
        # 音效
        self._play_sound(bed_pos, "note.pling", 1.0, 1.2)

        particles = [
            'minecraft:end_rod',
            'minecraft:flame_particle',
            'minecraft:villager_happy',
            'minecraft:enchanting_table_particle',
            'minecraft:portal_particle',
            'minecraft:critical_hit_emitter'
        ]

        # 多阶段彩虹漩涡
        for stage in range(4):
            stage_delay = stage * 0.5

            # 每个阶段生成螺旋
            for i in range(12):
                particle_delay = stage_delay + i * 0.03

                # 螺旋参数
                angle = i * 30 + stage * 45
                height_offset = i * 0.15 + stage * 0.3
                radius = 1.2 - i * 0.02

                # 三螺旋结构
                for spiral in range(3):
                    spiral_angle = angle + spiral * 120
                    x_offset = math.cos(math.radians(spiral_angle)) * radius
                    z_offset = math.sin(math.radians(spiral_angle)) * radius
                    pos = (bed_pos[0] + x_offset, bed_pos[1] + 0.5 + height_offset, bed_pos[2] + z_offset)

                    # 颜色循环
                    particle_type = particles[(i + spiral + stage) % len(particles)]
                    self.spawn_timed_particle(pos, particle_type, particle_delay)

    def play_cow_effect(self, bed_pos):
        """勇敢牛牛特效 - 冲撞踩踏地面震动效果"""
        # 牛牛音效
        self._play_sound(bed_pos, "mob.cow.say", 1.0, 0.8)

        # 延迟音效
        def cow_sound_1(timer_id):
            self._play_sound(bed_pos, "mob.cow.step", 1.5, 0.6)

        def final_moo(timer_id):
            self._play_sound(bed_pos, "mob.cow.say", 2.0, 1.5)

        if self.timer_manager:
            self.timer_manager.add_timer(self.get_next_effect_id(), 0.3, cow_sound_1)
            self.timer_manager.add_timer(self.get_next_effect_id(), 1.2, final_moo)

        # 奔跑尘土
        for i in range(12):
            delay = i * 0.06
            distance = 3.0 - (i * 0.25)
            angle = random.uniform(-30, 30)

            x_offset = math.cos(math.radians(angle)) * distance
            z_offset = math.sin(math.radians(angle)) * distance
            pos = (bed_pos[0] + x_offset, bed_pos[1] + 0.1, bed_pos[2] + z_offset)

            self.spawn_timed_particle(pos, 'minecraft:smoke_particle', delay)

        # 冲撞震动
        impact_delay = 0.8
        self.spawn_timed_particle((bed_pos[0], bed_pos[1] + 0.5, bed_pos[2]), 'minecraft:critical_hit_emitter', impact_delay)

        # 环形扩散
        for ring in range(4):
            ring_delay = impact_delay + ring * 0.05
            radius = 0.5 + ring * 0.4

            for i in range(8):
                angle = i * 45
                x_offset = math.cos(math.radians(angle)) * radius
                z_offset = math.sin(math.radians(angle)) * radius
                pos = (bed_pos[0] + x_offset, bed_pos[1], bed_pos[2] + z_offset)

                self.spawn_timed_particle(pos, 'minecraft:smoke_particle', ring_delay)

    def get_all_bed_destroy_effects(self):
        """
        获取所有床破坏特效配置

        Returns:
            dict: 床破坏特效配置字典 {effect_id: BedDestroyEffectConfig}
        """
        return self.BED_DESTROY_EFFECT_CONFIGS

    def get_bed_destroy_effect_config(self, effect_id):
        """
        获取指定床破坏特效配置

        Args:
            effect_id (str): 特效ID

        Returns:
            BedDestroyEffectConfig: 特效配置,如果不存在则返回None
        """
        return self.BED_DESTROY_EFFECT_CONFIGS.get(effect_id)