# -*- coding: utf-8 -*-
"""
BedDestroyEffectSystem - 破坏床特效和消息系统

功能:
- 从JSON配置文件加载破坏床特效
- 播放多种类型的粒子特效
- 支持多阶段特效
- 支持定时器管理
- 广播破坏床消息

配置文件路径: config/ornaments/bed_destroy.json
"""

import mod.server.extraServerApi as serverApi
import json
import codecs
import os
import math
import random


class EffectTimer(object):
    """特效定时器管理器"""

    def __init__(self):
        self.timers = {}  # {timer_id: {'delay': float, 'callback': func, 'start_time': float}}
        self.timer_counter = 0

    def add_timer(self, timer_id, delay, callback):
        """
        添加定时器

        Args:
            timer_id (str): 定时器ID
            delay (float): 延迟时间(秒)
            callback (callable): 回调函数
        """
        import time
        self.timers[timer_id] = {
            'delay': delay,
            'callback': callback,
            'start_time': time.time()
        }

    def update(self):
        """更新定时器（每Tick调用）"""
        import time
        current_time = time.time()
        expired_timers = []

        for timer_id, timer_data in self.timers.items():
            elapsed = current_time - timer_data['start_time']
            if elapsed >= timer_data['delay']:
                # 执行回调
                try:
                    timer_data['callback'](timer_id)
                except Exception as e:
                    print("[ERROR] [EffectTimer] 定时器回调执行失败: {}".format(str(e)))
                expired_timers.append(timer_id)

        # 移除过期定时器
        for timer_id in expired_timers:
            del self.timers[timer_id]

    def clear_all(self):
        """清除所有定时器"""
        self.timers.clear()

    def get_next_timer_id(self):
        """生成下一个定时器ID"""
        self.timer_counter += 1
        return "timer_{}".format(self.timer_counter)


class BedDestroyEffectSystem(object):
    """
    破坏床特效和消息系统

    从JSON配置驱动特效和消息的生成
    """

    def __init__(self, bedwars_game_system):
        """
        初始化破坏床特效系统

        Args:
            bedwars_game_system: BedWarsGameSystem实例
        """
        # 导入MOD_NAME常量
        from Script_NeteaseMod.modConfig import MOD_NAME

        self.game_system = bedwars_game_system
        self.mod_name = MOD_NAME  # [FIX 2025-11-05] 添加mod_name属性
        self.config = None
        self.bed_destroy_effects = {}
        self.bed_destroy_messages = {}
        self.timer_manager = EffectTimer()
        self.effect_counter = 0
        self.player_bed_destroy_counts = {}  # {player_id: count}

        print("[INFO] [BedDestroyEffectSystem] 初始化完成")

    def initialize(self):
        """初始化系统"""
        try:
            # 加载配置
            self.config = self._load_config()
            if not self.config:
                print("[ERROR] [BedDestroyEffectSystem] 配置加载失败")
                return

            # 解析特效配置
            self.bed_destroy_effects = {
                effect['id']: effect
                for effect in self.config.get('bed_destroy_effects', [])
            }

            # 解析消息配置
            self.bed_destroy_messages = {
                msg['id']: msg
                for msg in self.config.get('bed_destroy_messages', [])
            }

            print("[INFO] [BedDestroyEffectSystem] 系统初始化成功 - 特效数: {}, 消息数: {}".format(
                len(self.bed_destroy_effects),
                len(self.bed_destroy_messages)
            ))
        except Exception as e:
            print("[ERROR] [BedDestroyEffectSystem] 初始化失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def cleanup(self):
        """清理系统"""
        try:
            self.timer_manager.clear_all()
            print("[INFO] [BedDestroyEffectSystem] 清理完成")
        except Exception as e:
            print("[ERROR] [BedDestroyEffectSystem] 清理失败: {}".format(str(e)))

    def on_tick(self):
        """每Tick更新"""
        try:
            self.timer_manager.update()
        except Exception as e:
            print("[ERROR] [BedDestroyEffectSystem] Tick更新失败: {}".format(str(e)))

    def _load_config(self):
        """
        加载JSON配置文件

        Returns:
            dict: 配置数据
        """
        # 默认配置
        default_config = {
            "bed_destroy_effects": [
                {
                    "id": "default",
                    "name": u"默认",
                    "particle": "minecraft:huge_explosion_emitter",
                    "sound": "random.explode",
                    "duration": 2.0,
                    "price": 0,
                    "unlocked_by_default": True
                }
            ],
            "bed_destroy_messages": [
                {
                    "id": "default",
                    "message": u"§c{attacker} §f摧毁了 §{team_color}{team_name} §f的床！"
                }
            ]
        }

        try:
            # 获取配置文件路径
            script_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            config_path = os.path.join(script_path, 'config', 'ornaments', 'bed_destroy.json')

            # 检查文件是否存在
            if not os.path.exists(config_path):
                print("[INFO] [BedDestroyEffectSystem] bed_destroy.json不存在，使用默认配置")
                return default_config

            print("[INFO] [BedDestroyEffectSystem] 加载配置文件: {}".format(config_path))

            # 读取配置文件 (Python 2.7兼容方式)
            with codecs.open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            return config
        except Exception as e:
            print("[ERROR] [BedDestroyEffectSystem] 加载配置文件失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()
            # 返回默认配置而不是None
            return default_config

    def play_bed_destroy_effect(self, attacker_id, bed_pos, dimension=0):
        """
        播放破坏床特效

        Args:
            attacker_id (str): 攻击者玩家ID
            bed_pos (tuple): 床位置 (x, y, z)
            dimension (int): 维度ID
        """
        try:
            # 获取玩家装备的特效ID（这里暂时使用默认特效，后续需要从装扮系统获取）
            effect_config = self.get_player_bed_destroy_effect_config(attacker_id)

            if not effect_config:
                print("[WARN] [BedDestroyEffectSystem] 未找到特效配置，使用默认特效")
                effect_config = self.bed_destroy_effects.get('default')

            if not effect_config:
                print("[ERROR] [BedDestroyEffectSystem] 默认特效配置不存在")
                return

            effect_type = effect_config.get('effect_type')
            print("[INFO] [BedDestroyEffectSystem] 播放床破坏特效: type={}, pos={}".format(
                effect_type, bed_pos
            ))

            # 根据effect_type调用对应的特效方法
            if effect_type == 'firework_sequence':
                self.play_firework_sequence_effect(effect_config, bed_pos, dimension)
            elif effect_type == 'spiral':
                self.play_spiral_effect(effect_config, bed_pos, dimension)
            elif effect_type == 'cow_charge':
                self.play_cow_charge_effect(effect_config, bed_pos, dimension)
            elif effect_type == 'heart_cloud':
                self.play_heart_cloud_effect(effect_config, bed_pos, dimension)
            elif effect_type == 'explosion':
                self.play_explosion_effect(effect_config, bed_pos, dimension)
            elif effect_type == 'lightning':
                self.play_lightning_effect(effect_config, bed_pos, dimension)
            elif effect_type == 'default':
                self.play_default_effect(effect_config, bed_pos, dimension)
            else:
                print("[ERROR] [BedDestroyEffectSystem] 未知的特效类型: {}".format(effect_type))

        except Exception as e:
            print("[ERROR] [BedDestroyEffectSystem] 播放床破坏特效失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def broadcast_bed_destroy_message(self, attacker_id, team_id, count=None):
        """
        广播破坏床消息

        Args:
            attacker_id (str): 攻击者玩家ID
            team_id (str): 被破坏的队伍ID
            count (int): 破坏次数（可选）
        """
        try:
            # 自动计数
            if count is None:
                if attacker_id not in self.player_bed_destroy_counts:
                    self.player_bed_destroy_counts[attacker_id] = 0
                self.player_bed_destroy_counts[attacker_id] += 1
                count = self.player_bed_destroy_counts[attacker_id]

            # 获取玩家装备的消息ID（暂时使用默认消息）
            message_config = self.get_player_bed_destroy_message_config(attacker_id)

            if not message_config:
                message_config = self.bed_destroy_messages.get('default')

            if not message_config:
                print("[ERROR] [BedDestroyEffectSystem] 默认消息配置不存在")
                return

            # 随机选择消息模板
            messages = message_config.get('messages', [])
            if not messages:
                return

            message_template = random.choice(messages)

            # 替换占位符
            attacker_name = self.get_player_name(attacker_id)
            team_name = self.get_team_display_name(team_id)

            message = message_template.format(
                team=team_name,
                player=attacker_name,
                count=count
            )

            # 广播给所有玩家
            self.broadcast_message(message)

            print("[INFO] [BedDestroyEffectSystem] 广播破坏床消息: {}".format(message))

        except Exception as e:
            print("[ERROR] [BedDestroyEffectSystem] 广播破坏床消息失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def get_player_bed_destroy_effect_config(self, player_id):
        """
        获取玩家装备的床破坏特效配置

        Args:
            player_id (str): 玩家ID

        Returns:
            dict: 特效配置
        """
        # 从装扮系统获取玩家装备的特效ID
        try:
            # 获取BedWarsGameSystem
            game_system = serverApi.GetSystem(self.mod_name, "BedWarsGameSystem")
            if game_system and hasattr(game_system, 'ornament_system'):
                ornament_system = game_system.ornament_system
                if ornament_system:
                    # 获取玩家装备的床破坏特效ID
                    effect_id = ornament_system.get_player_ornament(player_id, 'bed_destroy_effect')
                    if effect_id and effect_id in self.bed_destroy_effects:
                        return self.bed_destroy_effects.get(effect_id)
        except Exception as e:
            print("[WARN] [BedDestroyEffectSystem] 获取玩家装扮失败，使用默认特效: {}".format(str(e)))

        # 默认返回默认特效
        return self.bed_destroy_effects.get('default')

    def get_player_bed_destroy_message_config(self, player_id):
        """
        获取玩家装备的床破坏消息配置

        Args:
            player_id (str): 玩家ID

        Returns:
            dict: 消息配置
        """
        # 从装扮系统获取玩家装备的消息ID
        try:
            # 获取BedWarsGameSystem
            game_system = serverApi.GetSystem(self.mod_name, "BedWarsGameSystem")
            if game_system and hasattr(game_system, 'ornament_system'):
                ornament_system = game_system.ornament_system
                if ornament_system:
                    # 获取玩家装备的床破坏消息ID
                    message_id = ornament_system.get_player_ornament(player_id, 'bed_destroy_message')
                    if message_id and message_id in self.bed_destroy_messages:
                        return self.bed_destroy_messages.get(message_id)
        except Exception as e:
            print("[WARN] [BedDestroyEffectSystem] 获取玩家装扮失败，使用默认消息: {}".format(str(e)))

        # 默认返回默认消息
        return self.bed_destroy_messages.get('default')

    def get_player_name(self, player_id):
        """
        获取玩家名称

        Args:
            player_id (str): 玩家ID

        Returns:
            str: 玩家名称
        """
        try:
            name_comp = serverApi.GetEngineCompFactory().CreateName(player_id)
            return name_comp.GetName()
        except Exception as e:
            print("[ERROR] [BedDestroyEffectSystem] 获取玩家名称失败: {}".format(str(e)))
            return "Unknown"

    def get_team_display_name(self, team_id):
        """
        获取队伍显示名称

        Args:
            team_id (str): 队伍ID

        Returns:
            str: 队伍显示名称
        """
        # 队伍ID到显示名称的映射
        team_names = {
            'RED': u'红',
            'BLUE': u'蓝',
            'GREEN': u'绿',
            'YELLOW': u'黄',
            'AQUA': u'青',
            'WHITE': u'白',
            'LIGHT_PURPLE': u'粉',
            'GRAY': u'灰',
        }
        return team_names.get(team_id, team_id)

    def broadcast_message(self, message):
        """
        广播消息给所有玩家

        Args:
            message (str): 消息内容
        """
        try:
            # 使用BedWarsGameSystem的广播方法
            if hasattr(self.game_system, 'broadcast_message'):
                self.game_system.broadcast_message(message)
            else:
                # 直接使用游戏组件广播
                game_comp = serverApi.GetEngineCompFactory().CreateGame(serverApi.GetLevelId())
                game_comp.SetNotifyMsg(message)
        except Exception as e:
            print("[ERROR] [BedDestroyEffectSystem] 广播消息失败: {}".format(str(e)))

    # ==================== 特效实现 ====================

    def play_default_effect(self, config, bed_pos, dimension):
        """默认特效"""
        try:
            particles = config.get('particles', [])
            sounds = config.get('sounds', [])

            # 播放粒子
            for particle_config in particles:
                self._spawn_particle(bed_pos, particle_config['type'], dimension)

            # 播放音效
            for sound_config in sounds:
                self._play_sound(bed_pos, sound_config['name'],
                               sound_config.get('volume', 1.0),
                               sound_config.get('pitch', 1.0), dimension)

        except Exception as e:
            print("[ERROR] [BedDestroyEffectSystem] 播放默认特效失败: {}".format(str(e)))

    def play_firework_sequence_effect(self, config, bed_pos, dimension):
        """烟花序列特效"""
        try:
            particle_config = config['particles'][0]
            sound_config = config['sounds'][0]

            wave_count = particle_config.get('wave_count', 5)
            wave_interval = particle_config.get('wave_interval', 0.4)
            layers_per_wave = particle_config.get('layers_per_wave', 3)
            directions_per_layer = particle_config.get('directions_per_layer', 8)
            color_variants = particle_config.get('color_variants', ['minecraft:firework_emitter'])
            radius = particle_config.get('radius', 1.5)

            # 初始音效
            self._play_sound(bed_pos, sound_config['name'],
                           sound_config.get('volume', 1.0),
                           sound_config.get('pitch', 1.0), dimension)

            # 5波连续烟花
            for wave in range(wave_count):
                wave_delay = wave * wave_interval
                particle_type = color_variants[wave % len(color_variants)]

                # 延迟音效
                if wave > 0:
                    volume_decay = sound_config.get('volume_decay', 0.15)
                    pitch_increase = sound_config.get('pitch_increase', 0.1)
                    volume = max(0.3, sound_config.get('volume', 1.0) - wave * volume_decay)
                    pitch = sound_config.get('pitch', 1.0) + wave * pitch_increase

                    def delayed_sound(timer_id, pos=bed_pos, dim=dimension, vol=volume, p=pitch):
                        self._play_sound(pos, sound_config['name'], vol, p, dim)

                    self.timer_manager.add_timer(self.timer_manager.get_next_timer_id(),
                                                wave_delay, delayed_sound)

                # 每波多层烟花
                for layer in range(layers_per_wave):
                    layer_delay = wave_delay + layer * 0.08
                    height = bed_pos[1] + 2 + layer * 0.4
                    current_radius = radius - wave * 0.2 + layer * 0.2

                    # 每层多个方向
                    for i in range(directions_per_layer):
                        particle_delay = layer_delay + i * 0.02
                        angle = i * (360.0 / directions_per_layer)

                        x_offset = math.cos(math.radians(angle)) * current_radius
                        z_offset = math.sin(math.radians(angle)) * current_radius
                        pos = (bed_pos[0] + x_offset, height, bed_pos[2] + z_offset)

                        def spawn_particle(timer_id, p=pos, ptype=particle_type, dim=dimension):
                            self._spawn_particle(p, ptype, dim)

                        self.timer_manager.add_timer(self.timer_manager.get_next_timer_id(),
                                                    particle_delay, spawn_particle)

        except Exception as e:
            print("[ERROR] [BedDestroyEffectSystem] 播放烟花特效失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def play_spiral_effect(self, config, bed_pos, dimension):
        """金黄螺旋特效"""
        try:
            particle_config = config['particles'][0]
            sounds = config.get('sounds', [])

            # 播放音效
            for sound_config in sounds:
                self._play_sound(bed_pos, sound_config['name'],
                               sound_config.get('volume', 1.0),
                               sound_config.get('pitch', 1.0), dimension)

            phases = particle_config.get('phases', 3)
            particles_per_phase = particle_config.get('particles_per_phase', 10)
            phase_interval = particle_config.get('phase_interval', 0.5)
            color_gradient = particle_config.get('color_gradient', [])

            # 分阶段螺旋上升
            for phase in range(phases):
                for i in range(particles_per_phase):
                    delay = phase * phase_interval + i * 0.05

                    # 螺旋计算
                    angle = (phase * particles_per_phase + i) * 18
                    height_offset = (phase * particles_per_phase + i) * 0.1
                    radius = 1.5 - (phase * particles_per_phase + i) * 0.03

                    x_offset = math.cos(math.radians(angle)) * radius
                    z_offset = math.sin(math.radians(angle)) * radius
                    pos = (bed_pos[0] + x_offset, bed_pos[1] + 1 + height_offset,
                          bed_pos[2] + z_offset)

                    # 根据阶段使用不同粒子
                    particle_type = color_gradient[phase]['particle'] if phase < len(color_gradient) else 'minecraft:end_rod'

                    def spawn_particle(timer_id, p=pos, ptype=particle_type, dim=dimension):
                        self._spawn_particle(p, ptype, dim)

                    self.timer_manager.add_timer(self.timer_manager.get_next_timer_id(),
                                                delay, spawn_particle)

        except Exception as e:
            print("[ERROR] [BedDestroyEffectSystem] 播放螺旋特效失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def play_cow_charge_effect(self, config, bed_pos, dimension):
        """勇敢牛牛多阶段特效"""
        try:
            phases = config.get('phases', [])
            current_time = 0.0

            for phase in phases:
                phase_duration = phase.get('duration', 0.0)

                # 播放阶段音效
                for sound_config in phase.get('sounds', []):
                    sound_delay = current_time + sound_config.get('delay', 0.0)

                    def play_sound(timer_id, pos=bed_pos, name=sound_config['name'],
                                  vol=sound_config.get('volume', 1.0),
                                  pitch=sound_config.get('pitch', 1.0), dim=dimension):
                        self._play_sound(pos, name, vol, pitch, dim)

                    self.timer_manager.add_timer(self.timer_manager.get_next_timer_id(),
                                                sound_delay, play_sound)

                # 播放阶段粒子
                for particle_config in phase.get('particles', []):
                    spawn_pattern = particle_config.get('spawn_pattern')

                    if spawn_pattern == 'ground_dust':
                        # 奔跑扬尘
                        count = particle_config.get('count', 12)
                        interval = particle_config.get('interval', 0.06)
                        distance_range = particle_config.get('distance_range', [3.0, 0.5])
                        angle_range = particle_config.get('angle_range', [-30, 30])
                        height_offset = particle_config.get('height_offset', 0.1)

                        for i in range(count):
                            delay = current_time + i * interval
                            distance = distance_range[0] - (i * (distance_range[0] - distance_range[1]) / count)
                            angle = random.uniform(angle_range[0], angle_range[1])

                            x_offset = math.cos(math.radians(angle)) * distance
                            z_offset = math.sin(math.radians(angle)) * distance
                            pos = (bed_pos[0] + x_offset, bed_pos[1] + height_offset,
                                  bed_pos[2] + z_offset)

                            def spawn_dust(timer_id, p=pos, ptype=particle_config['type'], dim=dimension):
                                self._spawn_particle(p, ptype, dim)

                            self.timer_manager.add_timer(self.timer_manager.get_next_timer_id(),
                                                        delay, spawn_dust)

                    elif spawn_pattern == 'shockwave':
                        # 冲击波
                        rings = particle_config.get('rings', 4)
                        particles_per_ring = particle_config.get('particles_per_ring', 8)
                        ring_interval = particle_config.get('ring_interval', 0.05)
                        radius_range = particle_config.get('radius_range', [0.5, 2.1])
                        height_offset = particle_config.get('height_offset', 0.5)

                        # 先播放中心爆炸
                        center_pos = (bed_pos[0], bed_pos[1] + height_offset, bed_pos[2])

                        def spawn_center(timer_id, p=center_pos, ptype=particle_config['type'], dim=dimension):
                            self._spawn_particle(p, ptype, dim)

                        self.timer_manager.add_timer(self.timer_manager.get_next_timer_id(),
                                                    current_time, spawn_center)

                        # 环形扩散
                        for ring in range(rings):
                            ring_delay = current_time + ring * ring_interval
                            radius = radius_range[0] + (ring * (radius_range[1] - radius_range[0]) / rings)

                            for i in range(particles_per_ring):
                                angle = i * (360.0 / particles_per_ring)
                                x_offset = math.cos(math.radians(angle)) * radius
                                z_offset = math.sin(math.radians(angle)) * radius
                                pos = (bed_pos[0] + x_offset, bed_pos[1], bed_pos[2] + z_offset)

                                ptype = 'minecraft:smoke_particle'  # 冲击波使用烟雾粒子

                                def spawn_ring(timer_id, p=pos, pt=ptype, dim=dimension):
                                    self._spawn_particle(p, pt, dim)

                                self.timer_manager.add_timer(self.timer_manager.get_next_timer_id(),
                                                            ring_delay, spawn_ring)

                current_time += phase_duration

        except Exception as e:
            print("[ERROR] [BedDestroyEffectSystem] 播放勇敢牛牛特效失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def play_heart_cloud_effect(self, config, bed_pos, dimension):
        """爱心粒子云特效"""
        try:
            particle_config = config['particles'][0]
            sounds = config.get('sounds', [])

            # 播放音效
            for sound_config in sounds:
                self._play_sound(bed_pos, sound_config['name'],
                               sound_config.get('volume', 1.0),
                               sound_config.get('pitch', 1.0), dimension)

            pulse_phases = particle_config.get('pulse_phases', 3)
            points_per_heart = particle_config.get('points_per_heart', 12)
            layers = particle_config.get('layers', 3)
            base_scale = particle_config.get('base_scale', 0.05)
            y_scale = particle_config.get('y_scale', 0.4)
            phase_interval = particle_config.get('phase_interval', 0.4)
            layer_offset = particle_config.get('layer_offset', 0.2)
            size_range = particle_config.get('size_range', [0.6, 1.2])

            # 多阶段心形
            for stage_idx in range(pulse_phases):
                stage_delay = stage_idx * phase_interval
                scale_factor = size_range[0] + (stage_idx * (size_range[1] - size_range[0]) / pulse_phases)

                # 每个阶段生成心形
                for layer in range(layers):
                    layer_delay = stage_delay + layer * 0.02

                    for t in range(points_per_heart):
                        particle_delay = layer_delay + t * 0.01

                        angle = t * math.pi / 6
                        # 心形参数方程
                        x = 16 * math.sin(angle) ** 3
                        y = 13 * math.cos(angle) - 5 * math.cos(2*angle) - 2 * math.cos(3*angle) - math.cos(4*angle)

                        # 应用缩放
                        current_scale = base_scale * scale_factor
                        x_offset = x * current_scale
                        y_offset = y * current_scale * y_scale
                        z_offset = (layer - 1) * layer_offset

                        pos = (bed_pos[0] + x_offset, bed_pos[1] + 1.5 + y_offset,
                              bed_pos[2] + z_offset)

                        def spawn_heart(timer_id, p=pos, ptype=particle_config['type'], dim=dimension):
                            self._spawn_particle(p, ptype, dim)

                        self.timer_manager.add_timer(self.timer_manager.get_next_timer_id(),
                                                    particle_delay, spawn_heart)

        except Exception as e:
            print("[ERROR] [BedDestroyEffectSystem] 播放爱心特效失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def play_explosion_effect(self, config, bed_pos, dimension):
        """爆炸特效"""
        try:
            particles = config.get('particles', [])
            sounds = config.get('sounds', [])

            # 播放音效
            for sound_config in sounds:
                self._play_sound(bed_pos, sound_config['name'],
                               sound_config.get('volume', 1.0),
                               sound_config.get('pitch', 1.0), dimension)

            # 中心爆炸
            center_particle = particles[0]
            height_offset = center_particle.get('height_offset', 1.0)
            center_pos = (bed_pos[0], bed_pos[1] + height_offset, bed_pos[2])
            self._spawn_particle(center_pos, center_particle['type'], dimension)

            # 环形冲击波
            if len(particles) > 1:
                ring_particle = particles[1]
                ring_count = ring_particle.get('ring_count', 3)
                particles_per_ring = ring_particle.get('particles_per_ring', 12)
                ring_interval = ring_particle.get('ring_interval', 0.1)
                radius_range = ring_particle.get('radius_range', [0.8, 2.6])
                height_offset = ring_particle.get('height_offset', 0.5)
                particle_variants = ring_particle.get('particle_variants', [])

                for ring in range(ring_count):
                    ring_delay = ring * ring_interval
                    radius = radius_range[0] + (ring * (radius_range[1] - radius_range[0]) / ring_count)

                    # 获取当前环的粒子类型
                    particle_type = ring_particle['type']
                    for variant in particle_variants:
                        if variant.get('ring') == ring:
                            particle_type = variant.get('particle', particle_type)
                            break

                    for i in range(particles_per_ring):
                        particle_delay = ring_delay + i * 0.02
                        angle = i * (360.0 / particles_per_ring)

                        x_offset = math.cos(math.radians(angle)) * radius
                        z_offset = math.sin(math.radians(angle)) * radius
                        pos = (bed_pos[0] + x_offset, bed_pos[1] + height_offset,
                              bed_pos[2] + z_offset)

                        def spawn_ring_particle(timer_id, p=pos, ptype=particle_type, dim=dimension):
                            self._spawn_particle(p, ptype, dim)

                        self.timer_manager.add_timer(self.timer_manager.get_next_timer_id(),
                                                    particle_delay, spawn_ring_particle)

        except Exception as e:
            print("[ERROR] [BedDestroyEffectSystem] 播放爆炸特效失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def play_lightning_effect(self, config, bed_pos, dimension):
        """雷击特效"""
        try:
            particle_config = config['particles'][0]
            sounds = config.get('sounds', [])

            # 播放音效
            for sound_config in sounds:
                self._play_sound(bed_pos, sound_config['name'],
                               sound_config.get('volume', 1.0),
                               sound_config.get('pitch', 1.0), dimension)

            count = particle_config.get('count', 8)
            random_offset = particle_config.get('random_offset', 0.2)
            height_interval = particle_config.get('height_interval', 0.5)
            delay_per_layer = particle_config.get('delay_per_layer', 0.05)
            particle_variants = particle_config.get('particle_variants', [])

            # 垂直闪电柱
            for height in range(count):
                height_delay = height * delay_per_layer
                y_pos = bed_pos[1] + height * height_interval

                # 随机偏移
                x_offset = random.uniform(-random_offset, random_offset)
                z_offset = random.uniform(-random_offset, random_offset)
                pos = (bed_pos[0] + x_offset, y_pos, bed_pos[2] + z_offset)

                # 获取粒子类型（交替使用）
                particle_type = particle_config['type']
                for variant in particle_variants:
                    parity = variant.get('layer_parity')
                    if (parity == 'even' and height % 2 == 0) or (parity == 'odd' and height % 2 == 1):
                        particle_type = variant.get('particle', particle_type)
                        break

                def spawn_lightning(timer_id, p=pos, ptype=particle_type, dim=dimension):
                    self._spawn_particle(p, ptype, dim)

                self.timer_manager.add_timer(self.timer_manager.get_next_timer_id(),
                                            height_delay, spawn_lightning)

        except Exception as e:
            print("[ERROR] [BedDestroyEffectSystem] 播放雷击特效失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    # ==================== 辅助方法 ====================

    def _spawn_particle(self, pos, particle_type, dimension=0):
        """在指定位置生成粒子"""
        try:
            command = "/particle {} {} {} {}".format(
                particle_type, pos[0], pos[1], pos[2]
            )
            self._execute_command(command)
        except Exception as e:
            print("[ERROR] [BedDestroyEffectSystem] 生成粒子失败: {}".format(str(e)))

    def _play_sound(self, pos, sound_name, volume=1.0, pitch=1.0, dimension=0):
        """在指定位置播放音效"""
        try:
            command = "/playsound {} @a {} {} {} {} {}".format(
                sound_name, pos[0], pos[1], pos[2], volume, pitch
            )
            self._execute_command(command)
        except Exception as e:
            print("[ERROR] [BedDestroyEffectSystem] 播放音效失败: {}".format(str(e)))

    def _execute_command(self, command):
        """执行命令"""
        try:
            comp = serverApi.GetEngineCompFactory()
            command_comp = comp.CreateCommand(serverApi.GetLevelId())
            command_comp.SetCommand(command)
        except Exception as e:
            print("[ERROR] [BedDestroyEffectSystem] 执行命令失败: {}".format(str(e)))
