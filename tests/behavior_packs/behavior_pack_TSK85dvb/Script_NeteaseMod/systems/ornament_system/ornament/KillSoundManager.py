# -*- coding: utf-8 -*-
"""
KillSoundManager - 击杀音效管理器

功能:
- 管理击杀音效配置
- 播放击杀音效
- 支持多种音效包

原文件: Parts/ECBedWarsOrnament/ornament/BedWarsOrnamentKillSound.py
重构为: systems/ornament_system/ornament/KillSoundManager.py
"""

import mod.server.extraServerApi as serverApi
import random


class KillSoundConfig(object):
    """击杀音效配置"""

    def __init__(self, sound_id, name, sounds):
        """
        初始化击杀音效配置

        Args:
            sound_id (str): 音效ID
            name (str): 音效名称
            sounds (list): 音效列表
        """
        self.sound_id = sound_id
        self.name = name
        self.sounds = sounds if sounds else []

    def get_random_sound(self):
        """
        获取随机音效

        Returns:
            str: 音效名称,如果没有音效则返回None
        """
        if len(self.sounds) == 0:
            return None
        return random.choice(self.sounds)


class KillSoundManager(object):
    """
    击杀音效管理器

    负责击杀音效的播放和管理
    """

    # 击杀音效配置
    KILL_SOUND_CONFIGS = {
        "default": KillSoundConfig(
            "default",
            u"默认",
            ["random.orb"]
        ),
        "animal-package": KillSoundConfig(
            "animal-package",
            u"动物礼包",
            ["mob.cow.say", "mob.sheep.say", "mob.pig.say", "mob.chicken.say"]
        ),
        "ghost-package": KillSoundConfig(
            "ghost-package",
            u"幽灵礼包",
            ["mob.zombie.death", "mob.skeleton.death", "mob.witch.death"]
        ),
        "forest-package": KillSoundConfig(
            "forest-package",
            u"森林礼包",
            ["mob.spider.death", "use.grass", "random.fizz"]
        ),
        "friend-package": KillSoundConfig(
            "friend-package",
            u"好友礼包",
            ["mob.wolf.bark", "mob.cat.meow", "mob.horse.idle"]
        ),
        "nether-package": KillSoundConfig(
            "nether-package",
            u"下界礼包",
            ["mob.ghast.scream", "mob.slime.squish", "mob.wither.ambient"]
        ),
        "end-package": KillSoundConfig(
            "end-package",
            u"末地礼包",
            ["mob.enderman.death", "mob.enderman.portal", "mob.enderdragon.growl"]
        ),
        "joker-package": KillSoundConfig(
            "joker-package",
            u"小丑礼包",
            ["ambient.weather.thunder", "block.end_portal.spawn", "mob.enderman.scream"]
        ),
        "cry-package": KillSoundConfig(
            "cry-package",
            u"哭泣礼包",
            ["mob.villager.hurt", "mob.villager.death"]
        ),
        "villager": KillSoundConfig(
            "villager",
            u"村民",
            ["mob.villager.hit"]
        ),
    }

    def __init__(self, ornament_system):
        """
        初始化击杀音效管理器

        Args:
            ornament_system: OrnamentSystem实例
        """
        self.ornament_system = ornament_system
        self.game_system = ornament_system.game_system

        print("[INFO] [KillSoundManager] 初始化完成")

    def initialize(self):
        """初始化击杀音效管理器"""
        try:
            print("[INFO] [KillSoundManager] 击杀音效管理器初始化成功")
        except Exception as e:
            print("[ERROR] [KillSoundManager] 初始化失败: {}".format(str(e)))

    def cleanup(self):
        """清理击杀音效管理器"""
        try:
            print("[INFO] [KillSoundManager] 清理完成")
        except Exception as e:
            print("[ERROR] [KillSoundManager] 清理失败: {}".format(str(e)))

    def play_kill_sound(self, killer_id, victim_id, death_pos):
        """
        播放击杀音效

        Args:
            killer_id (str): 击杀者ID
            victim_id (str): 受害者ID
            death_pos (tuple): 死亡位置 (x, y, z)
        """
        try:
            # 获取击杀者装备的击杀音效
            sound_id = self.ornament_system.get_player_ornament(killer_id, 'kill_sound')
            if not sound_id:
                sound_id = 'default'

            # 获取音效配置
            sound_config = self.KILL_SOUND_CONFIGS.get(sound_id)
            if not sound_config:
                print("[WARN] [KillSoundManager] 未找到击杀音效配置: {}".format(sound_id))
                return

            # 获取随机音效
            sound_name = sound_config.get_random_sound()
            if not sound_name:
                return

            # 播放音效
            self._play_sound_at_pos(sound_name, death_pos)

            print("[INFO] [KillSoundManager] 玩家 {} 击杀 {}, 播放音效: {}".format(
                killer_id, victim_id, sound_name
            ))
        except Exception as e:
            print("[ERROR] [KillSoundManager] 播放击杀音效失败: {}".format(str(e)))

    def _play_sound_at_pos(self, sound_name, pos, volume=1.0, pitch=1.0):
        """
        在指定位置播放音效

        Args:
            sound_name (str): 音效名称
            pos (tuple): 位置 (x, y, z)
            volume (float): 音量
            pitch (float): 音调
        """
        try:
            # 使用命令播放音效
            command = "/playsound {} @a {} {} {} {} {}".format(
                sound_name, pos[0], pos[1], pos[2], volume, pitch
            )

            # 执行命令
            comp = serverApi.GetEngineCompFactory()
            command_comp = comp.CreateCommand(serverApi.GetLevelId())
            command_comp.SetCommand(command)
        except Exception as e:
            print("[ERROR] [KillSoundManager] 播放音效失败: {}".format(str(e)))

    def get_all_kill_sounds(self):
        """
        获取所有击杀音效配置

        Returns:
            dict: 击杀音效配置字典 {sound_id: KillSoundConfig}
        """
        return self.KILL_SOUND_CONFIGS

    def get_kill_sound_config(self, sound_id):
        """
        获取指定击杀音效配置

        Args:
            sound_id (str): 音效ID

        Returns:
            KillSoundConfig: 音效配置,如果不存在则返回None
        """
        return self.KILL_SOUND_CONFIGS.get(sound_id)