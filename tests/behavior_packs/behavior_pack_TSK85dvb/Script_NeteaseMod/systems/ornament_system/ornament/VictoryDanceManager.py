# -*- coding: utf-8 -*-
"""
VictoryDanceManager - 胜利之舞管理器

功能:
- 管理胜利之舞特效
- 播放胜利之舞特效
- 支持多种特效类型
- 使用JSON配置驱动

原文件: Parts/ECBedWarsOrnament/ornament/BedWarsOrnamentVictoryDance.py
重构为: systems/ornament_system/ornament/VictoryDanceManager.py (配置化版本)
"""

import mod.server.extraServerApi as serverApi
import time
import math
import random
import os
import json


class EffectTimer(object):
    """特效定时器管理器"""

    def __init__(self):
        self.active_timers = {}  # {timer_id: {'start_time': float, 'duration': float, 'callback': func}}

    def add_timer(self, timer_id, duration, callback):
        """添加定时器"""
        self.active_timers[timer_id] = {
            'start_time': time.time(),
            'duration': duration,
            'callback': callback
        }

    def update(self):
        """更新定时器状态,调用到期的回调"""
        current_time = time.time()
        expired_timers = []

        for timer_id, timer_info in self.active_timers.items():
            if current_time - timer_info['start_time'] >= timer_info['duration']:
                try:
                    timer_info['callback'](timer_id)
                except Exception as e:
                    print("[ERROR] [EffectTimer] 回调执行失败: {}".format(str(e)))
                expired_timers.append(timer_id)

        # 清理过期定时器
        for timer_id in expired_timers:
            del self.active_timers[timer_id]

    def clear_timer(self, timer_id):
        """清除指定定时器"""
        if timer_id in self.active_timers:
            del self.active_timers[timer_id]


class VictoryDanceManager(object):
    """
    胜利之舞管理器

    负责胜利之舞特效的播放和管理
    从JSON配置文件加载特效配置
    """

    def __init__(self, ornament_system):
        """
        初始化胜利之舞管理器

        Args:
            ornament_system: OrnamentSystem实例
        """
        self.ornament_system = ornament_system
        self.game_system = ornament_system.game_system

        # 定时器管理器
        self.timer_manager = EffectTimer()
        self.effect_counter = 0  # 用于生成唯一的特效ID

        # 加载配置
        self.victory_dance_configs = {}

        print("[INFO] [VictoryDanceManager] 初始化完成")

    def initialize(self):
        """初始化胜利之舞管理器"""
        try:
            self._load_config()
            print("[INFO] [VictoryDanceManager] 胜利之舞管理器初始化成功，已加载 {} 种舞蹈".format(
                len(self.victory_dance_configs)
            ))
        except Exception as e:
            print("[ERROR] [VictoryDanceManager] 初始化失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _load_config(self):
        """从JSON文件加载胜利之舞配置"""
        try:
            # 获取配置文件路径
            from Script_NeteaseMod.config import ornament_config

            # 从ornament_config获取配置（已经加载了JSON）
            for dance_id, dance_info in ornament_config.VICTORY_DANCE_CONFIG.items():
                full_config = dance_info.get('_full_config')
                if full_config:
                    self.victory_dance_configs[dance_id] = full_config
                else:
                    # 兼容旧配置格式
                    self.victory_dance_configs[dance_id] = dance_info

            print("[INFO] [VictoryDanceManager] 配置加载成功，共 {} 个胜利舞蹈".format(
                len(self.victory_dance_configs)
            ))

        except Exception as e:
            print("[ERROR] [VictoryDanceManager] 加载配置失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

            # 使用默认配置
            self.victory_dance_configs = {
                "default": {
                    "id": "default",
                    "name": u"默认",
                    "effect_type": "default"
                }
            }

    def cleanup(self):
        """清理胜利之舞管理器"""
        try:
            self.timer_manager.active_timers = {}
            print("[INFO] [VictoryDanceManager] 清理完成")
        except Exception as e:
            print("[ERROR] [VictoryDanceManager] 清理失败: {}".format(str(e)))

    def update(self):
        """更新定时器 - 需要在游戏主循环中调用"""
        self.timer_manager.update()

    def get_next_effect_id(self):
        """获取下一个特效ID"""
        self.effect_counter += 1
        return "victory_effect_{}".format(self.effect_counter)

    def play_victory_dance(self, player_scores):
        """
        播放胜利之舞

        Args:
            player_scores (list): 玩家积分列表,按排名排序
                格式: [{'player_id': str, 'score': int, 'pos': (x, y, z)}, ...]
        """
        if not player_scores or len(player_scores) == 0:
            return

        # 获取前三名玩家
        top_players = player_scores[:3]

        for rank, score_entry in enumerate(top_players):
            player_id = score_entry.get('player_id')
            pos = score_entry.get('pos')

            if not player_id or not pos:
                continue

            # 获取玩家装备的胜利之舞
            dance_id = self.ornament_system.get_player_ornament(player_id, 'victory_dance')
            if not dance_id:
                dance_id = 'default'

            # 播放胜利之舞特效
            self._play_dance_effect(player_id, dance_id, pos, rank + 1)

            print("[INFO] [VictoryDanceManager] 玩家 {} 排名 {} 播放胜利之舞: {}".format(
                player_id, rank + 1, dance_id
            ))

    def _play_dance_effect(self, player_id, dance_id, pos, rank):
        """
        播放胜利之舞特效

        Args:
            player_id (str): 玩家ID
            dance_id (str): 舞蹈ID
            pos (tuple): 特效位置 (x, y, z)
            rank (int): 排名 (1=第一名, 2=第二名, 3=第三名)
        """
        try:
            # 获取舞蹈配置
            dance_config = self.victory_dance_configs.get(dance_id)
            if not dance_config:
                print("[WARN] [VictoryDanceManager] 未找到胜利之舞配置: {}".format(dance_id))
                return

            effect_type = dance_config.get('effect_type', 'default')

            # 调用对应的特效方法
            method_name = "play_{}_dance".format(effect_type.replace("-", "_"))
            if hasattr(self, method_name):
                effect_method = getattr(self, method_name)
                effect_method(dance_config, pos, rank)
            else:
                print("[ERROR] [VictoryDanceManager] 未找到胜利之舞特效方法: {}".format(method_name))

        except Exception as e:
            print("[ERROR] [VictoryDanceManager] 播放胜利之舞特效失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    # ========== 粒子和音效工具方法 ==========

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

        if delay > 0:
            timer_id = self.get_next_effect_id()
            self.timer_manager.add_timer(timer_id, delay, spawn_callback)
        else:
            spawn_callback(None)

    def _spawn_particle(self, pos, particle_type):
        """
        在指定位置生成粒子

        Args:
            pos (tuple): 位置 (x, y, z)
            particle_type (str): 粒子类型
        """
        try:
            command = "/particle {} {} {} {}".format(
                particle_type, pos[0], pos[1], pos[2]
            )
            self._execute_command(command)
        except Exception as e:
            print("[ERROR] [VictoryDanceManager] 生成粒子失败: {}".format(str(e)))

    def _play_sound(self, pos, sound_name, volume=1.0, pitch=1.0):
        """
        在指定位置播放音效

        Args:
            pos (tuple): 位置 (x, y, z)
            sound_name (str): 音效名称
            volume (float): 音量
            pitch (float): 音调
        """
        try:
            command = "/playsound {} @a {} {} {} {} {}".format(
                sound_name, pos[0], pos[1], pos[2], volume, pitch
            )
            self._execute_command(command)
        except Exception as e:
            print("[ERROR] [VictoryDanceManager] 播放音效失败: {}".format(str(e)))

    def _execute_command(self, command):
        """
        执行命令

        Args:
            command (str): 命令字符串
        """
        try:
            comp = serverApi.GetEngineCompFactory()
            command_comp = comp.CreateCommand(serverApi.GetLevelId())
            command_comp.SetCommand(command)
        except Exception as e:
            print("[ERROR] [VictoryDanceManager] 执行命令失败: {}".format(str(e)))

    # ========== 特效实现方法 ==========

    def play_default_dance(self, config, pos, rank=1):
        """
        默认胜利之舞 - 简单的庆祝粒子

        Args:
            config (dict): 舞蹈配置
            pos (tuple): 位置
            rank (int): 排名
        """
        # 获取rank配置
        rank_configs = config.get('rank_configs', {})
        rank_config = rank_configs.get(str(rank), rank_configs.get('1', {}))

        particle_count = rank_config.get('particle_count', 15)
        height_range = rank_config.get('height_range', 3.0)
        volume = rank_config.get('volume', 1.5)
        particle_interval = rank_config.get('particle_interval', 0.15)

        # 播放音效
        sounds = config.get('sounds', [])
        for sound in sounds:
            sound_name = sound.get('name', 'random.levelup')
            delay = sound.get('delay', 0.0)
            pitch = sound.get('pitch', 1.0)

            if delay > 0:
                def play_delayed_sound(timer_id):
                    self._play_sound(pos, sound_name, volume, pitch)
                timer_id = self.get_next_effect_id()
                self.timer_manager.add_timer(timer_id, delay, play_delayed_sound)
            else:
                self._play_sound(pos, sound_name, volume, pitch)

        # 生成心形粒子
        particles = config.get('particles', [])
        for particle_config in particles:
            particle_type = particle_config.get('type', 'minecraft:heart_particle')
            base_height = particle_config.get('base_height', 1.0)

            for i in range(particle_count):
                delay = i * particle_interval
                particle_pos = (
                    pos[0],
                    pos[1] + base_height + i * (height_range / particle_count),
                    pos[2]
                )
                self.spawn_timed_particle(particle_pos, particle_type, delay)

    def play_futou_dance(self, config, pos, rank=1):
        """
        斧头胜利之舞 - 头顶喷斧头特效

        Args:
            config (dict): 舞蹈配置
            pos (tuple): 位置
            rank (int): 排名
        """
        # 获取rank配置
        rank_configs = config.get('rank_configs', {})
        rank_config = rank_configs.get(str(rank), rank_configs.get('1', {}))

        axe_count = rank_config.get('axe_count', 25)
        radius = rank_config.get('radius', 1.5)
        height_range = rank_config.get('height_range', 2.0)
        volume = rank_config.get('volume', 1.5)
        particle_interval = rank_config.get('particle_interval', 0.12)

        # 播放音效
        sounds = config.get('sounds', [])
        for sound in sounds:
            self._play_sound(pos, sound.get('name', 'item.axe.hit'), volume, sound.get('pitch', 1.0))

        # 获取粒子配置
        particles = config.get('particles', [])
        fall_particle = None
        impact_particle = None

        for particle_config in particles:
            spawn_pattern = particle_config.get('spawn_pattern', '')
            if spawn_pattern == 'rain':
                fall_particle = particle_config
            elif spawn_pattern == 'ground_impact':
                impact_particle = particle_config

        # 生成斧头粒子雨
        for i in range(axe_count):
            delay = i * particle_interval

            # 随机位置
            x_offset = random.uniform(-radius, radius)
            z_offset = random.uniform(-radius, radius)
            base_height = fall_particle.get('base_height', 3.0) if fall_particle else 3.0
            height = pos[1] + base_height + random.uniform(0, height_range)

            effect_pos = (pos[0] + x_offset, height, pos[2] + z_offset)

            # 斧头掉落粒子
            if fall_particle:
                particle_type = fall_particle.get('type', 'minecraft:iron_ingot_particle')
                self.spawn_timed_particle(effect_pos, particle_type, delay)

            # 撞击地面效果
            if impact_particle:
                ground_pos = (effect_pos[0], pos[1], effect_pos[2])
                impact_delay = delay + impact_particle.get('delay', 0.5)
                impact_type = impact_particle.get('type', 'minecraft:critical_hit_emitter')
                self.spawn_timed_particle(ground_pos, impact_type, impact_delay)

    def play_lightning_dance(self, config, pos, rank=1):
        """
        闪电胜利之舞 - 召唤闪电庆祝

        Args:
            config (dict): 舞蹈配置
            pos (tuple): 位置
            rank (int): 排名
        """
        # 获取rank配置
        rank_configs = config.get('rank_configs', {})
        rank_config = rank_configs.get(str(rank), rank_configs.get('1', {}))

        wave_count = rank_config.get('wave_count', 10)
        lightning_per_wave = rank_config.get('lightning_per_wave', 4)
        thunder_volume = rank_config.get('thunder_volume', 2.5)
        wave_interval = rank_config.get('wave_interval', 0.6)
        strike_interval = rank_config.get('strike_interval', 0.1)
        lightning_height = rank_config.get('lightning_height', 10)

        # 播放雷声
        sounds = config.get('sounds', [])
        for sound in sounds:
            self._play_sound(pos, sound.get('name', 'ambient.weather.thunder'), thunder_volume, sound.get('pitch', 1.0))

        # 获取粒子配置
        particles = config.get('particles', [])

        # 连续闪电效果
        for wave in range(wave_count):
            wave_delay = wave * wave_interval

            # 每波生成闪电
            for lightning_strike in range(lightning_per_wave):
                strike_delay = wave_delay + lightning_strike * strike_interval

                # 随机闪电位置
                lightning_x = pos[0] + random.uniform(-3, 3)
                lightning_z = pos[2] + random.uniform(-3, 3)

                # 垂直闪电柱
                for particle_config in particles:
                    height_segments = particle_config.get('height_segments', 10)
                    segment_interval = particle_config.get('segment_interval', 0.02)
                    random_offset = particle_config.get('random_offset', 0.3)
                    particle_type = particle_config.get('type', 'minecraft:end_rod')
                    layer_parity = particle_config.get('layer_parity', 'all')

                    for height in range(height_segments):
                        # 根据layer_parity过滤
                        if layer_parity == 'even' and height % 2 != 0:
                            continue
                        if layer_parity == 'odd' and height % 2 == 0:
                            continue

                        height_delay = strike_delay + height * segment_interval
                        lightning_y = pos[1] + height * (lightning_height / height_segments)

                        # 随机偏移
                        x_offset = random.uniform(-random_offset, random_offset)
                        z_offset = random.uniform(-random_offset, random_offset)

                        effect_pos = (lightning_x + x_offset, lightning_y, lightning_z + z_offset)
                        self.spawn_timed_particle(effect_pos, particle_type, height_delay)

    def play_space_dance(self, config, pos, rank=1):
        """
        外太空胜利之舞 - 太空效果

        Args:
            config (dict): 舞蹈配置
            pos (tuple): 位置
            rank (int): 排名
        """
        # 获取rank配置
        rank_configs = config.get('rank_configs', {})
        rank_config = rank_configs.get(str(rank), rank_configs.get('1', {}))

        orbit_count = rank_config.get('orbit_count', 4)
        stars_per_orbit = rank_config.get('stars_per_orbit', 20)
        portal_particles = rank_config.get('portal_particles', 30)
        volume = rank_config.get('volume', 0.8)
        orbit_interval = rank_config.get('orbit_interval', 0.4)
        star_interval = rank_config.get('star_interval', 0.08)
        portal_interval = rank_config.get('portal_interval', 0.08)

        # 太空音效
        sounds = config.get('sounds', [])
        for sound in sounds:
            self._play_sound(pos, sound.get('name', 'ambient.weather.thunder'), volume, sound.get('pitch', 2.0))

        # 获取粒子配置
        particles = config.get('particles', [])
        orbit_particle = None
        center_particle = None

        for particle_config in particles:
            spawn_pattern = particle_config.get('spawn_pattern', '')
            if spawn_pattern == 'orbit':
                orbit_particle = particle_config
            elif spawn_pattern == 'center_vertical':
                center_particle = particle_config

        # 环绕的星星轨道效果
        if orbit_particle:
            base_radius = orbit_particle.get('base_radius', 1.5)
            radius_increment = orbit_particle.get('radius_increment', 0.7)
            base_height = orbit_particle.get('base_height', 1.0)
            height_increment = orbit_particle.get('height_increment', 0.4)
            rotation_offset = orbit_particle.get('rotation_offset', 45)
            particle_type = orbit_particle.get('type', 'minecraft:end_rod')

            for orbit in range(orbit_count):
                orbit_delay = orbit * orbit_interval
                radius = base_radius + orbit * radius_increment

                for i in range(stars_per_orbit):
                    particle_delay = orbit_delay + i * star_interval
                    angle = i * (360.0 / stars_per_orbit) + orbit * rotation_offset

                    x_offset = math.cos(math.radians(angle)) * radius
                    z_offset = math.sin(math.radians(angle)) * radius
                    height = pos[1] + base_height + orbit * height_increment + math.sin(math.radians(angle * 2)) * 0.25

                    star_pos = (pos[0] + x_offset, height, pos[2] + z_offset)
                    self.spawn_timed_particle(star_pos, particle_type, particle_delay)

        # 中心的"太空门"效果
        if center_particle:
            particle_type = center_particle.get('type', 'minecraft:portal_particle')
            base_height = center_particle.get('base_height', 0.5)
            height_range = center_particle.get('height_range', 3.0)

            for i in range(portal_particles):
                portal_delay = i * portal_interval
                portal_height = pos[1] + base_height + i * (height_range / portal_particles)
                portal_pos = (pos[0], portal_height, pos[2])
                self.spawn_timed_particle(portal_pos, particle_type, portal_delay)

    def play_yanhua_dance(self, config, pos, rank=1):
        """
        圣灵烟花胜利之舞 - 大型烟花秀

        Args:
            config (dict): 舞蹈配置
            pos (tuple): 位置
            rank (int): 排名
        """
        # 获取rank配置
        rank_configs = config.get('rank_configs', {})
        rank_config = rank_configs.get(str(rank), rank_configs.get('1', {}))

        batch_count = rank_config.get('batch_count', 5)
        firework_array_size = rank_config.get('firework_array_size', 17)
        volume = rank_config.get('volume', 2.5)
        batch_interval = rank_config.get('batch_interval', 1.5)
        firework_interval = rank_config.get('firework_interval', 0.2)
        spark_count = rank_config.get('spark_count', 8)
        spark_radius = rank_config.get('spark_radius', 1.2)

        # 烟花音效
        sounds = config.get('sounds', [])
        for sound in sounds:
            self._play_sound(pos, sound.get('name', 'firework.blast'), volume, sound.get('pitch', 1.0))

        # 获取烟花点位
        firework_points_config = config.get('firework_points', {})
        firework_points = firework_points_config.get(str(rank), [[0, 0]])

        # 获取粒子类型变体
        particle_variants = config.get('particle_variants', [
            'minecraft:firework_emitter',
            'minecraft:critical_hit_emitter',
            'minecraft:end_rod',
            'minecraft:totem_particle'
        ])

        # 获取粒子配置
        particles = config.get('particles', [])
        firework_particle = None
        spark_particle = None

        for particle_config in particles:
            spawn_pattern = particle_config.get('spawn_pattern', '')
            if spawn_pattern == 'array_burst':
                firework_particle = particle_config
            elif spawn_pattern == 'radial_sparks':
                spark_particle = particle_config

        height_min = firework_particle.get('height_min', 4.0) if firework_particle else 4.0
        height_max = firework_particle.get('height_max', 8.0) if firework_particle else 8.0

        # 分批发射烟花
        for batch in range(batch_count):
            batch_delay = batch * batch_interval

            for idx, point in enumerate(firework_points[:firework_array_size]):
                firework_delay = batch_delay + idx * firework_interval

                firework_x = pos[0] + point[0]
                firework_z = pos[2] + point[1]
                firework_height = pos[1] + random.uniform(height_min, height_max)

                firework_pos = (firework_x, firework_height, firework_z)

                # 使用不同的烟花粒子
                particle_type = particle_variants[idx % len(particle_variants)]
                self.spawn_timed_particle(firework_pos, particle_type, firework_delay)

                # 烟花爆炸的散射效果
                if spark_particle:
                    spark_delay_offset = spark_particle.get('delay', 0.1)
                    height_offset = spark_particle.get('height_offset', -0.5)
                    spark_type = spark_particle.get('type', 'minecraft:critical_hit_emitter')

                    for spark in range(spark_count):
                        spark_delay = firework_delay + spark_delay_offset
                        spark_angle = spark * (360 / spark_count)

                        spark_x = firework_x + math.cos(math.radians(spark_angle)) * spark_radius
                        spark_z = firework_z + math.sin(math.radians(spark_angle)) * spark_radius
                        spark_y = firework_height + height_offset

                        spark_pos = (spark_x, spark_y, spark_z)
                        self.spawn_timed_particle(spark_pos, spark_type, spark_delay)

    # 保留原有的dragon舞蹈以便向后兼容（虽然JSON中不包含）
    def play_dragon_dance(self, config, pos, rank=1):
        """
        末影龙胜利之舞 - 龙环绕效果
        （保留以便向后兼容，但不在JSON配置中）

        Args:
            config (dict): 舞蹈配置
            pos (tuple): 位置
            rank (int): 排名
        """
        # 根据排名调整龙的规模
        if rank == 1:
            spiral_points = 80
            max_radius = 3.5
            max_height = 12
            roar_radius = 3.0
            roar_points = 16
            volume = 2.0
        elif rank == 2:
            spiral_points = 60
            max_radius = 2.8
            max_height = 9
            roar_radius = 2.5
            roar_points = 12
            volume = 1.5
        else:
            spiral_points = 40
            max_radius = 2.0
            max_height = 6
            roar_radius = 2.0
            roar_points = 8
            volume = 1.0

        # 龙吟音效
        self._play_sound(pos, "mob.enderdragon.growl", volume, 1.0)

        # 龙飞行轨迹效果
        for i in range(spiral_points):
            delay = i * 0.08

            # 螺旋参数
            progress = float(i) / spiral_points
            angle = i * 15

            # 半径变化
            if progress < 0.5:
                radius = max_radius * (progress * 2)
            else:
                radius = max_radius * (2 - progress * 2)

            # 高度变化:抛物线轨迹
            height_progress = progress * 2 - 1  # -1 to 1
            height = pos[1] + 2 + max_height * (1 - height_progress * height_progress)

            dragon_x = pos[0] + math.cos(math.radians(angle)) * radius
            dragon_z = pos[2] + math.sin(math.radians(angle)) * radius
            dragon_pos = (dragon_x, height, dragon_z)

            # 龙息粒子
            self.spawn_timed_particle(dragon_pos, 'minecraft:dragon_breath_particle', delay)

            # 龙鳞闪光
            flash_interval = 4 if rank == 1 else (3 if rank == 2 else 5)
            if i % flash_interval == 0:
                scale_pos = (dragon_pos[0], dragon_pos[1] - 0.3, dragon_pos[2])
                self.spawn_timed_particle(scale_pos, 'minecraft:portal_particle', delay + 0.05)

        # 最终的龙吼爆发
        def final_roar(timer_id):
            self._play_sound(pos, "mob.enderdragon.death", volume * 1.2, 0.8)
            # 环形龙息爆发
            for i in range(roar_points):
                angle = i * (360.0 / roar_points)
                roar_x = pos[0] + math.cos(math.radians(angle)) * roar_radius
                roar_z = pos[2] + math.sin(math.radians(angle)) * roar_radius
                roar_pos = (roar_x, pos[1] + 1, roar_z)
                self._spawn_particle(roar_pos, 'minecraft:dragon_breath_particle')

        self.timer_manager.add_timer(
            self.get_next_effect_id(),
            spiral_points * 0.08 + 0.5,
            final_roar
        )

    def get_all_victory_dances(self):
        """
        获取所有胜利之舞配置

        Returns:
            dict: 胜利之舞配置字典 {dance_id: config}
        """
        return self.victory_dance_configs

    def get_victory_dance_config(self, dance_id):
        """
        获取指定胜利之舞配置

        Args:
            dance_id (str): 舞蹈ID

        Returns:
            dict: 舞蹈配置,如果不存在则返回None
        """
        return self.victory_dance_configs.get(dance_id)
