# -*- coding: utf-8 -*-
r"""
TeamTrapManager.py - 队伍陷阱管理器模块

该模块管理队伍的陷阱系统：
- 管理4种陷阱类型（减速、反击、警报、挖掘疲劳）
- 处理陷阱添加和触发
- 陷阱触发冷却时间控制
- 最多同时持有3个陷阱

参考文件：D:\EcWork\NetEaseMapECBedWars备份\...\Parts\BedWarsBed\trap\TeamTrapManager.py
"""

import time
from .TeamTrap import (
    TeamTrap,
    TeamTrapSlowness,
    TeamTrapBeatBack,
    TeamTrapAlert,
    TeamTrapFatigue
)


class TeamTrapManager(object):
    """
    队伍陷阱管理器类

    管理一个队伍的所有陷阱
    """

    # 陷阱触发冷却时间（秒）
    COOLDOWN = 20.0

    # 陷阱类映射
    TRAP_CLASSES = {
        "slowness": TeamTrapSlowness,
        "beat_back": TeamTrapBeatBack,
        "alert": TeamTrapAlert,
        "fatigue": TeamTrapFatigue
    }

    def __init__(self, game_system, team, bed_pos):
        """
        初始化陷阱管理器

        :param game_system: BedWarsGameSystem实例
        :param team: 队伍ID
        :param bed_pos: 床的位置 (x, y, z)
        """
        self.game_system = game_system  # BedWarsGameSystem
        self.team = team  # str - 队伍ID
        self.bed_pos = bed_pos  # tuple - 床的位置
        self.traps = []  # list[TeamTrap] - 陷阱队列（最多3个）
        self.cooldown = 0.0  # float - 冷却结束时间戳

    def add_trap(self, trap_type):
        """
        添加陷阱

        :param trap_type: 陷阱类型（"slowness", "beat_back", "alert", "fatigue"）或TeamTrap实例
        :return: True如果添加成功，False如果陷阱已满
        """
        try:
            # 检查陷阱是否已满
            if self.is_trap_full():
                return False

            # 创建陷阱实例
            if isinstance(trap_type, str):
                if trap_type not in self.TRAP_CLASSES:
                    print("[ERROR] [TeamTrapManager] 未知的陷阱类型: {}".format(trap_type))
                    return False

                trap_class = self.TRAP_CLASSES[trap_type]
                trap = trap_class(self, self.bed_pos)
            else:
                trap = trap_type

            # 添加到陷阱队列
            self.traps.append(trap)
            print("[INFO] [TeamTrapManager] 添加陷阱: team={}, type={}, count={}".format(
                self.team, trap.name, len(self.traps)))

            # 通知队伍成员
            self._notify_trap_added(trap)

            return True

        except Exception as e:
            print("[ERROR] [TeamTrapManager] add_trap() 出错: {}".format(str(e)))
            return False

    def is_trap_full(self):
        """
        检查陷阱是否已满（最多3个）

        :return: True如果已满，否则False
        """
        return len(self.traps) >= 3

    def on_update(self):
        """
        更新陷阱系统（每tick调用）

        检测敌人进入范围并触发陷阱
        """
        try:
            # 检查冷却时间
            now = time.time()
            if now < self.cooldown:
                return

            # 检查是否有陷阱
            if len(self.traps) == 0:
                return

            # 获取第一个陷阱
            trap = self.traps[0]

            # 检查是否有敌人在范围内
            effective_players = trap.get_effective_players()
            if len(effective_players) > 0:
                # 触发陷阱
                trap.trigger()

                # 移除陷阱
                self.traps.pop(0)

                # 设置冷却时间
                self.cooldown = now + self.COOLDOWN

                print("[INFO] [TeamTrapManager] 陷阱触发: team={}, trap={}, cooldown={}s".format(
                    self.team, trap.name, self.COOLDOWN))

        except Exception as e:
            print("[ERROR] [TeamTrapManager] on_update() 出错: {}".format(str(e)))

    def get_trap_count(self):
        """
        获取当前陷阱数量

        :return: 陷阱数量
        """
        return len(self.traps)

    def get_trap_names(self):
        """
        获取所有陷阱的名称列表

        :return: 陷阱名称列表
        """
        return [trap.name for trap in self.traps]

    def clear_all_traps(self):
        """
        清空所有陷阱（用于游戏重置）
        """
        self.traps = []
        self.cooldown = 0.0

    def set_bed_position(self, bed_pos):
        """
        设置床的位置（如果床被移动或重置）

        :param bed_pos: 床的位置 (x, y, z)
        """
        self.bed_pos = bed_pos

        # 更新所有陷阱的位置
        for trap in self.traps:
            trap.pos = bed_pos

    def _notify_trap_added(self, trap):
        """
        通知队伍成员陷阱已添加

        :param trap: 陷阱实例
        """
        try:
            import mod.server.extraServerApi as serverApi

            if not self.game_system or not self.game_system.team_module:
                return

            message = u"§7你的队伍购买了 §6{}§7!".format(trap.name)

            team_players = self.game_system.team_module.get_team_players(self.team)
            for player_id in team_players:
                try:
                    comp_msg = serverApi.GetEngineCompFactory().CreateMsg(player_id)
                    comp_msg.NotifyOneMessage(player_id, message, u"§7")
                except:
                    pass

        except Exception as e:
            print("[ERROR] [TeamTrapManager] _notify_trap_added() 出错: {}".format(str(e)))

    def get_all_traps_data(self):
        """
        获取所有陷阱的数据（用于持久化）

        :return: 陷阱类型列表
        """
        data = []
        for trap in self.traps:
            # 根据陷阱类型获取键名
            for key, trap_class in self.TRAP_CLASSES.items():
                if isinstance(trap, trap_class):
                    data.append(key)
                    break
        return data

    def load_traps_data(self, data):
        """
        加载陷阱数据（用于从持久化恢复）

        :param data: 陷阱类型列表
        """
        try:
            self.traps = []
            for trap_type in data:
                self.add_trap(trap_type)
        except Exception as e:
            print("[ERROR] [TeamTrapManager] load_traps_data() 出错: {}".format(str(e)))
