# -*- coding: utf-8 -*-
r"""
TeamUpgradeManager.py - 队伍升级管理器模块

该模块管理队伍的所有升级项：
- 管理7种升级类型（生命值、盔甲、利剑、生成器、矿工、治疗池、指南针）
- 处理升级购买和效果应用
- 处理玩家重生时的升级效果重新应用

参考文件：D:\EcWork\NetEaseMapECBedWars备份\...\Parts\ECBedWars\team\TeamUpgradeManager.py
"""

from .TeamUpgradeEntry import (
    TeamUpgradeEntry,
    TeamUpgradeEntryHealth,
    TeamUpgradeEntryArmor,
    TeamUpgradeEntrySword,
    TeamUpgradeEntryHomeGenerator,
    TeamUpgradeEntrySuperMiner,
    TeamUpgradeEntryHealingPool,
    TeamUpgradeEntryCompassTracking
)


class TeamUpgradeManager(object):
    """
    队伍升级管理器类

    管理一个队伍的所有升级项
    """

    def __init__(self, game_system, team):
        """
        初始化队伍升级管理器

        :param game_system: BedWarsGameSystem实例
        :param team: 队伍ID
        """
        self.entries = {}  # dict[str, TeamUpgradeEntry] - 升级条目字典
        self.game_system = game_system  # BedWarsGameSystem
        self.team = team  # str - 队伍ID
        self.init_default()

    def init_default(self):
        """
        初始化默认的升级项
        创建所有7种升级类型的实例
        """
        self.entries["health"] = TeamUpgradeEntryHealth(self)
        self.entries["armor"] = TeamUpgradeEntryArmor(self)
        self.entries["sword"] = TeamUpgradeEntrySword(self)
        self.entries["generator"] = TeamUpgradeEntryHomeGenerator(self)
        self.entries["miner"] = TeamUpgradeEntrySuperMiner(self)
        self.entries["healing_pool"] = TeamUpgradeEntryHealingPool(self)
        self.entries["compass_tracking"] = TeamUpgradeEntryCompassTracking(self)

    def get_upgrade(self, upgrade_key):
        """
        获取指定的升级条目

        :param upgrade_key: 升级键名（如 "health", "armor", "sword"等）
        :return: TeamUpgradeEntry实例，如果不存在返回None
        """
        return self.entries.get(upgrade_key, None)

    def purchase_upgrade(self, upgrade_key):
        """
        购买升级（升级一级）

        :param upgrade_key: 升级键名
        :return: True如果升级成功，False如果已达最大等级或升级不存在
        """
        upgrade = self.get_upgrade(upgrade_key)
        if upgrade and upgrade.level < upgrade.max_level:
            upgrade.level_up()
            return True
        return False

    def set_upgrade_level(self, upgrade_key, level):
        """
        设置升级等级

        :param upgrade_key: 升级键名
        :param level: 目标等级
        :return: True如果设置成功，False如果升级不存在
        """
        upgrade = self.get_upgrade(upgrade_key)
        if upgrade:
            upgrade.set_level(level)
            return True
        return False

    def get_upgrade_level(self, upgrade_key):
        """
        获取升级当前等级

        :param upgrade_key: 升级键名
        :return: 当前等级，如果升级不存在返回0
        """
        upgrade = self.get_upgrade(upgrade_key)
        if upgrade:
            return upgrade.level
        return 0

    def on_player_respawn(self, player_id):
        """
        玩家重生时重新应用所有升级效果

        :param player_id: 玩家ID
        """
        try:
            # 检查玩家是否属于当前队伍
            player_team = self.game_system.team_module.get_player_team(player_id)
            if player_team == self.team:
                # 对玩家应用所有升级效果
                for entry in self.entries.values():
                    try:
                        entry.apply_to_player(player_id)
                    except Exception as e:
                        print("[TeamUpgradeManager] 应用升级 {} 到玩家 {} 失败: {}".format(
                            entry.get_upgrade_name(), player_id, str(e)))
        except Exception as e:
            print("[TeamUpgradeManager] on_player_respawn() 出错: {}".format(str(e)))

    def apply_all_to_player(self, player_id):
        """
        对玩家应用所有升级效果（用于玩家加入队伍时）

        :param player_id: 玩家ID
        """
        try:
            for entry in self.entries.values():
                try:
                    entry.apply_to_player(player_id)
                except Exception as e:
                    print("[TeamUpgradeManager] 应用升级 {} 到玩家 {} 失败: {}".format(
                        entry.get_upgrade_name(), player_id, str(e)))
        except Exception as e:
            print("[TeamUpgradeManager] apply_all_to_player() 出错: {}".format(str(e)))

    def get_all_upgrades_data(self):
        """
        获取所有升级的数据（用于持久化）

        :return: 字典，键为升级名称，值为等级
        """
        data = {}
        for key, entry in self.entries.items():
            data[key] = entry.level
        return data

    def load_upgrades_data(self, data):
        """
        加载升级数据（用于从持久化恢复）

        :param data: 字典，键为升级名称，值为等级
        """
        try:
            for key, level in data.items():
                if key in self.entries:
                    self.entries[key].set_level(level)
        except Exception as e:
            print("[TeamUpgradeManager] load_upgrades_data() 出错: {}".format(str(e)))

    def is_upgrade_max_level(self, upgrade_key):
        """
        检查升级是否已达最大等级

        :param upgrade_key: 升级键名
        :return: True如果已达最大等级或升级不存在，否则False
        """
        upgrade = self.get_upgrade(upgrade_key)
        if upgrade:
            return upgrade.level >= upgrade.max_level
        return True

    def get_upgrade_max_level(self, upgrade_key):
        """
        获取升级的最大等级

        :param upgrade_key: 升级键名
        :return: 最大等级，如果升级不存在返回0
        """
        upgrade = self.get_upgrade(upgrade_key)
        if upgrade:
            return upgrade.max_level
        return 0

    def reset_all_upgrades(self):
        """
        重置所有升级到0级（用于游戏重置）
        """
        try:
            for entry in self.entries.values():
                entry.set_level(0)
        except Exception as e:
            print("[TeamUpgradeManager] reset_all_upgrades() 出错: {}".format(str(e)))

    def get_upgrade_names(self):
        """
        获取所有升级的键名列表

        :return: 升级键名列表
        """
        return list(self.entries.keys())

    def has_upgrade(self, upgrade_key):
        """
        检查是否存在指定的升级

        :param upgrade_key: 升级键名
        :return: True如果存在，否则False
        """
        return upgrade_key in self.entries
