# -*- coding: utf-8 -*-
r"""
TeamUpgradeEntry.py - 队伍升级条目模块

该模块定义了队伍升级系统的基类和各种具体升级类型：
- TeamUpgradeEntry: 升级条目基类
- TeamUpgradeEntryHealth: 生命值提升
- TeamUpgradeEntryArmor: 盔甲保护
- TeamUpgradeEntrySword: 锐利利剑
- TeamUpgradeEntryHomeGenerator: 生成器升级
- TeamUpgradeEntrySuperMiner: 疯狂矿工
- TeamUpgradeEntryHealingPool: 治愈池
- TeamUpgradeEntryCompassTracking: 指南针追踪

参考文件：D:\EcWork\NetEaseMapECBedWars备份\...\Parts\ECBedWars\team\TeamUpgradeEntry.py
"""

import mod.server.extraServerApi as serverApi

# 导入必要的枚举类型
EnchantType = serverApi.GetMinecraftEnum().EnchantType
ItemPosType = serverApi.GetMinecraftEnum().ItemPosType
EffectType = serverApi.GetMinecraftEnum().EffectType


class TeamUpgradeEntry(object):
    """
    队伍升级条目基类

    所有具体的升级类型都应继承此类
    """

    def __init__(self, manager, max_level):
        """
        初始化升级条目

        :param manager: TeamUpgradeManager实例
        :param max_level: 最大等级
        """
        self.manager = manager  # TeamUpgradeManager
        self.max_level = max_level  # int
        self.level = 0  # int - 当前等级

    def level_up(self):
        """
        升级（增加一级）
        """
        if self.level < self.max_level:
            old_level = self.level
            self.level += 1
            self.apply()
            self.send_upgrade_notification(old_level, self.level)

    def set_level(self, level):
        """
        设置等级

        :param level: 目标等级
        """
        if level < 0:
            level = 0
        elif level > self.max_level:
            level = self.max_level
        self.level = level
        self.apply()

    def apply(self):
        """
        应用效果到队伍所有玩家
        """
        # 需要从TeamModule获取队伍玩家列表
        # 新起床架构：通过manager访问game_system，再访问team_module
        try:
            team_players = self.manager.game_system.team_module.get_team_players(self.manager.team)
            for player_id in team_players:
                # 检查玩家是否在重生中
                if player_id in self.manager.game_system.respawning:
                    continue
                self.apply_to_player(player_id)
        except Exception as e:
            print("[TeamUpgradeEntry] apply() 出错: {}".format(str(e)))

    def apply_to_player(self, player_id):
        """
        对单个玩家应用效果（子类需要重写此方法）

        :param player_id: 玩家ID
        """
        pass

    def get_upgrade_name(self):
        """
        获取升级名称（子类需要重写）

        :return: 升级名称字符串
        """
        return "未知升级"

    def get_team_color_name(self):
        """
        获取队伍带颜色的名称

        :return: 格式化的队伍名称
        """
        from .TeamType import get_team_color_name
        return get_team_color_name(self.manager.team)

    def send_upgrade_notification(self, old_level, new_level):
        """
        发送升级通知给所有玩家

        :param old_level: 旧等级
        :param new_level: 新等级
        """
        try:
            upgrade_name = self.get_upgrade_name()
            team_name = self.get_team_color_name()

            # 构造彩色通知消息
            if old_level == 0:
                # 首次购买升级
                message = "§f{} §7购买了 §b{} §6I级§7!".format(team_name, upgrade_name)
            else:
                # 升级到更高等级
                level_roman = self.get_roman_numeral(new_level)
                message = "§f{} §7将 §b{} §7升级到了 §6{}级§7!".format(team_name, upgrade_name, level_roman)

            # 发送给所有在线玩家
            try:
                # 从game_system获取所有玩家
                all_players = self.manager.game_system.team_module.get_all_players()
                for player_id in all_players:
                    try:
                        comp_msg = serverApi.GetEngineCompFactory().CreateMsg(player_id)
                        comp_msg.NotifyOneMessage(player_id, message, "§f")
                    except:
                        pass
            except Exception as e:
                print("[TeamUpgradeEntry] 发送消息失败: {}".format(str(e)))

            # 播放升级音效
            try:
                comp = serverApi.GetEngineCompFactory().CreateCommand(serverApi.GetLevelId())
                comp.SetCommand("playsound random.levelup @a ~ ~ ~ 0.5 1.2")
            except:
                pass

            print("[升级通知] {}".format(message))

        except Exception as e:
            print("[TeamUpgradeEntry] 发送升级通知失败: {}".format(str(e)))

    def get_roman_numeral(self, level):
        """
        将数字等级转换为罗马数字

        :param level: 数字等级
        :return: 罗马数字字符串
        """
        roman_numerals = {
            1: "I",
            2: "II",
            3: "III",
            4: "IV",
            5: "V",
            6: "VI",
            7: "VII",
            8: "VIII",
            9: "IX",
            10: "X"
        }
        return roman_numerals.get(level, str(level))


# ============================================================================
# 具体升级类型
# ============================================================================

class TeamUpgradeEntryHealth(TeamUpgradeEntry):
    """生命值提升升级"""

    def __init__(self, manager):
        super(TeamUpgradeEntryHealth, self).__init__(manager, 3)

    def get_upgrade_name(self):
        return "生命值提升"

    def get_player_add_health(self):
        """获取增加的生命值"""
        if self.level == 1:
            return 3
        elif self.level == 2:
            return 6
        elif self.level == 3:
            return 10
        else:
            return 0

    def apply_to_player(self, player_id):
        """对玩家应用生命值提升效果"""
        if self.level > 0:
            try:
                comp_attr = serverApi.GetEngineCompFactory().CreateAttr(player_id)
                old_max_health = comp_attr.GetMaxHealth()
                new_max_health = 20 + self.get_player_add_health()
                heal_amount = new_max_health - old_max_health

                comp_attr.SetMaxHealth(new_max_health)
                if heal_amount > 0:
                    current_health = comp_attr.GetAttrValue(serverApi.GetMinecraftEnum().AttrType.HEALTH)
                    comp_attr.SetAttrValue(serverApi.GetMinecraftEnum().AttrType.HEALTH, current_health + heal_amount)
            except Exception as e:
                print("[TeamUpgradeEntryHealth] apply_to_player() 出错: {}".format(str(e)))


class TeamUpgradeEntryArmor(TeamUpgradeEntry):
    """盔甲保护升级"""

    def __init__(self, manager):
        super(TeamUpgradeEntryArmor, self).__init__(manager, 4)

    def get_upgrade_name(self):
        return "盔甲保护"

    def apply_to_player(self, player_id):
        """对玩家应用盔甲保护效果"""
        try:
            # 检查玩家队伍
            player_team = self.manager.game_system.team_module.get_player_team(player_id)
            if player_team != self.manager.team:
                return

            # 获取队伍颜色
            from .TeamType import team_types
            if player_team not in team_types:
                return

            team_type = team_types[player_team]
            color_int = team_type.get_rgb_color_int()
            custom_color = {
                "__type__": 3,
                "__value__": color_int
            }

            comp_item = serverApi.GetEngineCompFactory().CreateItem(player_id)
            armors = comp_item.GetPlayerAllItems(ItemPosType.ARMOR)
            slots = {}

            # 护具类型定义
            leather_armor_types = [
                "minecraft:leather_helmet",
                "minecraft:leather_chestplate",
                "minecraft:leather_leggings",
                "minecraft:leather_boots"
            ]

            upgradeable_armor_types = leather_armor_types + [
                "minecraft:chainmail_helmet", "minecraft:chainmail_chestplate",
                "minecraft:chainmail_leggings", "minecraft:chainmail_boots",
                "minecraft:iron_helmet", "minecraft:iron_chestplate",
                "minecraft:iron_leggings", "minecraft:iron_boots",
                "minecraft:diamond_helmet", "minecraft:diamond_chestplate",
                "minecraft:diamond_leggings", "minecraft:diamond_boots",
            ]

            for i in range(len(armors)):
                if armors[i]:
                    armor = armors[i]
                    armor_name = armor['newItemName']

                    if armor_name in upgradeable_armor_types:
                        # 设置附魔
                        armor['enchantData'] = []
                        armor['enchantData'].append((EnchantType.ArmorAll, self.level))
                        if i == 3 and self.level > 1:  # 靴子添加摔落保护
                            armor['enchantData'].append((EnchantType.ArmorFall, 1 if self.level < 3 else 3))

                        # 设置不掉耐久
                        if 'userData' not in armor:
                            armor['userData'] = {}
                        armor['userData']['minecraft:item_lock'] = {
                            "__type__": 1,
                            "__value__": True
                        }

                        # 皮革护具染色
                        if armor_name in leather_armor_types:
                            armor['userData']['customColor'] = custom_color

                        slots[(ItemPosType.ARMOR, i)] = armor

            comp_item.SetPlayerAllItems(slots)

        except Exception as e:
            print("[TeamUpgradeEntryArmor] apply_to_player() 出错: {}".format(str(e)))


class TeamUpgradeEntrySword(TeamUpgradeEntry):
    """锐利利剑升级"""

    weapons_set = [
        "minecraft:wooden_sword",
        "minecraft:stone_sword",
        "minecraft:iron_sword",
        "minecraft:diamond_sword",
    ]

    def __init__(self, manager):
        super(TeamUpgradeEntrySword, self).__init__(manager, 1)

    def get_upgrade_name(self):
        return "锐利利剑"

    def apply_to_player(self, player_id):
        """对玩家应用锐利效果"""
        try:
            # 获取玩家记录的剑
            recorded_sword = self.manager.game_system.player_sword_record.get(player_id, "minecraft:wooden_sword")

            comp_item = serverApi.GetEngineCompFactory().CreateItem(player_id)
            weapons = comp_item.GetPlayerAllItems(ItemPosType.INVENTORY)
            slots = {}

            for i in range(len(weapons)):
                if weapons[i] and weapons[i]['newItemName'] == recorded_sword:
                    weapon = weapons[i]
                    weapon['enchantData'] = []
                    weapon['enchantData'].append((EnchantType.WeaponDamage, self.level))
                    slots[(ItemPosType.INVENTORY, i)] = weapon
                    break

            if slots:
                comp_item.SetPlayerAllItems(slots)

        except Exception as e:
            print("[TeamUpgradeEntrySword] apply_to_player() 出错: {}".format(str(e)))


class TeamUpgradeEntrySuperMiner(TeamUpgradeEntry):
    """疯狂矿工升级"""

    def __init__(self, manager):
        super(TeamUpgradeEntrySuperMiner, self).__init__(manager, 2)

    def get_upgrade_name(self):
        return "疯狂矿工"

    def apply_to_player(self, player_id):
        """对玩家应用急迫效果"""
        if self.level > 0:
            try:
                comp_effect = serverApi.GetEngineCompFactory().CreateEffect(player_id)
                comp_effect.AddEffectToEntity(EffectType.DIG_SPEED, 60 * 60, self.level - 1, False)
            except Exception as e:
                print("[TeamUpgradeEntrySuperMiner] apply_to_player() 出错: {}".format(str(e)))


class TeamUpgradeEntryHealingPool(TeamUpgradeEntry):
    """治愈池升级"""

    def __init__(self, manager):
        super(TeamUpgradeEntryHealingPool, self).__init__(manager, 1)

    def get_upgrade_name(self):
        return "治愈池"

    def apply(self):
        """应用治愈池效果（创建治愈池）"""
        try:
            from .TeamHealingPool import TeamHealingPool
            if self.level > 0:
                # 获取队伍出生点位置
                team_spawns = self.manager.game_system.find_team_spawns()
                if self.manager.team in team_spawns and len(team_spawns[self.manager.team]) > 0:
                    spawn_pos = team_spawns[self.manager.team][0][0]  # 第一个出生点的位置
                    # 创建治疗池
                    self.manager.game_system.team_healing_pools[self.manager.team] = TeamHealingPool(
                        self.manager.game_system,
                        self.manager.team,
                        spawn_pos,
                        15  # 治疗范围15格
                    )
                    print("[TeamUpgradeEntryHealingPool] 为队伍 {} 创建治疗池，位置: {}".format(
                        self.manager.team, spawn_pos))
        except Exception as e:
            print("[TeamUpgradeEntryHealingPool] apply() 出错: {}".format(str(e)))


class TeamUpgradeEntryHomeGenerator(TeamUpgradeEntry):
    """生成器升级"""

    def __init__(self, manager):
        super(TeamUpgradeEntryHomeGenerator, self).__init__(manager, 4)

    def get_upgrade_name(self):
        return "生成器升级"

    def apply(self):
        """
        应用生成器升级效果
        等级1: 铁锭+100%
        等级2: 铁锭保持, 金锭+100%
        等级3: 铁锭保持, 金锭保持
        等级4: 铁锭+100%, 金锭保持
        """
        try:
            generators = self.manager.game_system.find_generators(self.manager.team)
            for generator in generators:
                if self.level == 1:
                    if generator.resource_type_id == "iron":
                        generator.set_level(2)
                elif self.level == 2:
                    if generator.resource_type_id == "iron":
                        generator.set_level(2)
                    elif generator.resource_type_id == "gold":
                        generator.set_level(2)
                elif self.level == 3:
                    if generator.resource_type_id == "iron":
                        generator.set_level(2)
                    elif generator.resource_type_id == "gold":
                        generator.set_level(2)
                elif self.level == 4:
                    if generator.resource_type_id == "iron":
                        generator.set_level(3)
                    elif generator.resource_type_id == "gold":
                        generator.set_level(2)
        except Exception as e:
            print("[TeamUpgradeEntryHomeGenerator] apply() 出错: {}".format(str(e)))


class TeamUpgradeEntryCompassTracking(TeamUpgradeEntry):
    """指南针追踪升级"""

    def __init__(self, manager):
        super(TeamUpgradeEntryCompassTracking, self).__init__(manager, 1)

    def get_upgrade_name(self):
        return "指南针追踪"

    def apply_to_player(self, player_id):
        """指南针追踪不需要对单个玩家应用效果"""
        pass

    def is_enabled(self):
        """检查指南针追踪是否已启用"""
        return self.level > 0
