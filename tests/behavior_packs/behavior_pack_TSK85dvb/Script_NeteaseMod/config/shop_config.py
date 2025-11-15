# -*- coding: utf-8 -*-
"""
商店配置文件 - 纯字典格式
替代原有的Builder模式和数据模型类

作者: AI助手
日期: 2025-02-01
版本: 1.0
"""

from mod.common.minecraftEnum import ItemColor, EnchantType
import mod.server.extraServerApi as serverApi
from Script_NeteaseMod.modConfig import MOD_NAME


# ========== 辅助函数 ==========

def get_player_team(preset, player_id):
    """
    获取玩家所在队伍

    架构设计:
    - BedWarsGameSystem.team_module 是游戏中队伍数据的唯一统一数据源
    - 数据流: RoomManagementSystem.team_players (临时分配)
             → BedWarsStartingState._initialize_teams() (同步)
             → BedWarsGameSystem.team_module (游戏中统一数据源)
    - RoomManagementSystem.team_module 虽然被初始化但实际未使用

    老项目对应关系:
    - 老项目: preset.GetPartByType("ECBedWarsPart").team_module
    - 新项目: GetSystem("BedWarsGameSystem").team_module

    Args:
        preset: ShopPresetDefServer实例
        player_id (str): 玩家ID

    Returns:
        str|None: 队伍ID或None
    """
    # 从BedWarsGameSystem.team_module获取（游戏中唯一的统一数据源）
    bedwars_game_sys = serverApi.GetSystem(MOD_NAME, "BedWarsGameSystem")

    if bedwars_game_sys and hasattr(bedwars_game_sys, 'team_module') and bedwars_game_sys.team_module:
        team = bedwars_game_sys.team_module.get_player_team(player_id)
        # 调试日志
        print("[ShopConfig] 获取玩家队伍: player={}, team={}".format(player_id, team))
        return team

    # 异常情况：BedWarsGameSystem或team_module不可用
    print("[ShopConfig] [错误] 无法从BedWarsGameSystem获取队伍: bedwars_game_sys={}, player={}".format(
        bedwars_game_sys, player_id))
    return None


def get_player_team_item_color(preset, player_id):
    """
    获取玩家所在队伍的物品颜色(羊毛/玻璃染色)

    Args:
        preset: ShopPresetDefServer实例
        player_id (str): 玩家ID

    Returns:
        ItemColor: 颜色枚举值
    """
    from Script_NeteaseMod.systems.team.TeamType import team_types
    team = get_player_team(preset, player_id)

    # 调试日志：确保颜色正确设置
    print("[ShopConfig] get_player_team_item_color: player={}, team={}".format(player_id, team))

    if team is None or team not in team_types:
        print("[ShopConfig] [警告] 队伍数据无效，使用黑色: player={}, team={}".format(player_id, team))
        return ItemColor.Black

    color = team_types[team].item_color
    print("[ShopConfig] 队伍颜色: player={}, team={}, color={}".format(player_id, team, color))
    return color


# ========== 限购检查辅助函数 ==========

# 护甲品质顺序
ORDERED_ARMOR_CHESTPLATE = [
    "minecraft:leather_chestplate",
    "minecraft:chainmail_chestplate",
    "minecraft:iron_chestplate",
    "minecraft:gold_chestplate",
    "minecraft:diamond_chestplate",
    "minecraft:netherite_chestplate",
]

ORDERED_LEGGINGS = [
    "minecraft:leather_leggings",
    "minecraft:chainmail_leggings",
    "minecraft:iron_leggings",
    "minecraft:gold_leggings",
    "minecraft:diamond_leggings",
    "minecraft:netherite_leggings",
]

# 剑品质顺序
ORDERED_SWORDS = [
    "minecraft:wooden_sword",
    "minecraft:stone_sword",
    "minecraft:iron_sword",
    "minecraft:diamond_sword",
    "minecraft:netherite_sword",
]


def is_player_chestplate_better_than(player_id, armor_item_name):
    """检查玩家穿戴的胸甲是否比指定护甲更好"""
    comp = serverApi.GetEngineCompFactory().CreateItem(player_id)
    chestplate = comp.GetPlayerItem(serverApi.GetMinecraftEnum().ItemPosType.ARMOR, 1)
    if chestplate is None:
        return False
    if armor_item_name not in ORDERED_ARMOR_CHESTPLATE:
        return False
    current_index = ORDERED_ARMOR_CHESTPLATE.index(chestplate['newItemName'])
    new_index = ORDERED_ARMOR_CHESTPLATE.index(armor_item_name)
    return new_index <= current_index


def is_player_leggings_better_than(player_id, armor_item_name):
    """检查玩家穿戴的护腿是否比指定护腿更好"""
    comp = serverApi.GetEngineCompFactory().CreateItem(player_id)
    leggings = comp.GetPlayerItem(serverApi.GetMinecraftEnum().ItemPosType.ARMOR, 2)
    if leggings is None:
        return False
    if armor_item_name not in ORDERED_LEGGINGS:
        return False
    current_index = ORDERED_LEGGINGS.index(leggings['newItemName'])
    new_index = ORDERED_LEGGINGS.index(armor_item_name)
    return new_index <= current_index


def is_player_sword_better_than(preset, player_id, sword_item_name):
    """
    检查玩家是否已拥有比指定剑更好品质的剑

    双重检查机制:
    1. 检查购买记录(防止玩家丢剑绕过限制)
    2. 检查背包中实际拥有的剑
    """
    # 新架构: 从BedWarsGameSystem获取购买记录
    game_system = serverApi.GetSystem(MOD_NAME, "BedWarsGameSystem")
    if not game_system or not hasattr(game_system, 'player_sword_record'):
        return False

    if sword_item_name not in ORDERED_SWORDS:
        return False

    new_sword_quality = ORDERED_SWORDS.index(sword_item_name)

    # 方法1: 检查购买记录
    current_sword_record = game_system.player_sword_record.get(player_id, "minecraft:wooden_sword")
    record_quality = 0
    if current_sword_record in ORDERED_SWORDS:
        record_quality = ORDERED_SWORDS.index(current_sword_record)

    # 方法2: 检查背包中实际拥有的最高品质剑
    comp = serverApi.GetEngineCompFactory().CreateItem(player_id)
    inv_items = comp.GetPlayerAllItems(serverApi.GetMinecraftEnum().ItemPosType.INVENTORY)

    highest_inv_sword_quality = 0
    for item in inv_items:
        if item and item.get('newItemName') in ORDERED_SWORDS:
            item_quality = ORDERED_SWORDS.index(item.get('newItemName'))
            if item_quality > highest_inv_sword_quality:
                highest_inv_sword_quality = item_quality

    # 防刷机制: 背包无剑但记录更好 → 禁止购买
    if highest_inv_sword_quality == 0 and record_quality > new_sword_quality:
        return True

    # 以背包中的剑为准
    if highest_inv_sword_quality > 0:
        return new_sword_quality <= highest_inv_sword_quality

    return False


# ========== 商品池配置 ==========

GOODS_POOL = [
    # ==================== 方块类 (13个) ====================
    {
        "id": "block.wool",
        "name": u"羊毛",
        "intro": u"可用于搭桥穿越岛屿",
        "category": "blocks",
        "price": {"currency": "iron", "amount": 4},
        "item": lambda preset, player_id: {
            "newItemName": "minecraft:wool",
            "newAuxValue": get_player_team_item_color(preset, player_id),
            "count": 16
        },
        "check_can_buy": None
    },
    {
        "id": "block.hay",
        "name": u"干草块",
        "intro": u"干草块？？",
        "category": "blocks",
        "price": {"currency": "iron", "amount": 4},
        "item": {"newItemName": "minecraft:hay_block", "count": 16},
        "check_can_buy": None
    },
    {
        "id": "block.clay",
        "name": u"硬化粘土",
        "intro": u"用于保卫床的基础方块",
        "category": "blocks",
        "price": {"currency": "iron", "amount": 12},
        "item": lambda preset, player_id: {
            "newItemName": "minecraft:stained_hardened_clay",
            "newAuxValue": get_player_team_item_color(preset, player_id),
            "count": 16
        },
        "check_can_buy": None
    },
    {
        "id": "block.sandstone",
        "name": u"沙石",
        "intro": u"用于保卫家的基础方块",
        "category": "blocks",
        "price": {"currency": "iron", "amount": 12},
        "item": {"newItemName": "minecraft:sandstone", "count": 16},
        "check_can_buy": None
    },
    {
        "id": "block.plank",
        "name": u"木板",
        "intro": u"用于保卫床的优质方块。 能有效抵御镐子的破坏",
        "category": "blocks",
        "price": {"currency": "gold", "amount": 4},
        "item": {"newItemName": "minecraft:planks", "count": 16},
        "check_can_buy": None
    },
    {
        "id": "block.wood",
        "name": u"原木",
        "intro": u"用于保卫床的优质方块。 能有效抵御镐子的破坏",
        "category": "blocks",
        "price": {"currency": "gold", "amount": 4},
        "item": {"newItemName": "minecraft:log", "count": 16},
        "check_can_buy": None
    },
    {
        "id": "block.end-stone",
        "name": u"末地石",
        "intro": u"用于保卫床的坚固方块。",
        "category": "blocks",
        "price": {"currency": "iron", "amount": 24},
        "item": {"newItemName": "minecraft:end_stone", "count": 16},
        "check_can_buy": None
    },
    {
        "id": "block.purpur",
        "name": u"紫珀方块(防御使用)",
        "intro": u"防御使用的方块，和末地石差不多",
        "category": "blocks",
        "price": {"currency": "iron", "amount": 24},
        "item": {"newItemName": "minecraft:purpur_block", "count": 16},
        "check_can_buy": None
    },
    {
        "id": "block.end-stone.12",
        "name": u"末地石",
        "intro": u"用于保卫床的坚固方块。",
        "category": "blocks",
        "price": {"currency": "iron", "amount": 24},
        "item": {"newItemName": "minecraft:end_stone", "count": 12},
        "check_can_buy": None
    },
    {
        "id": "block.ladder",
        "name": u"梯子",
        "intro": u"可用于救助树上卡住的猫",
        "category": "blocks",
        "price": {"currency": "iron", "amount": 4},
        "item": {"newItemName": "minecraft:ladder", "count": 16},
        "check_can_buy": None
    },
    {
        "id": "block.obsidian",
        "name": u"黑曜石",
        "intro": u"百分百保护你的床",
        "category": "blocks",
        "price": {"currency": "emerald", "amount": 4},
        "item": {"newItemName": "minecraft:obsidian", "count": 1},
        "check_can_buy": None
    },
    {
        "id": "block.obsidian.4",
        "name": u"黑曜石",
        "intro": u"百分百保护你的床",
        "category": "blocks",
        "price": {"currency": "emerald", "amount": 4},
        "item": {"newItemName": "minecraft:obsidian", "count": 4},
        "check_can_buy": None
    },
    {
        "id": "block.glass",
        "name": u"防爆玻璃",
        "intro": u"免疫爆炸",
        "category": "blocks",
        "price": {"currency": "iron", "amount": 12},
        "item": lambda preset, player_id: {
            "newItemName": "minecraft:stained_glass",
            "newAuxValue": get_player_team_item_color(preset, player_id),
            "count": 8
        },
        "check_can_buy": None
    },
    {
        "id": "block.chest",
        "name": u"箱子",
        "intro": u"用于奇怪用途的箱子？",
        "category": "blocks",
        "price": {"currency": "iron", "amount": 2},
        "item": {"newItemName": "minecraft:chest", "count": 1},
        "check_can_buy": None
    },
    {
        "id": "block.cobweb",
        "name": u"蜘蛛网",
        "intro": u"阻碍敌人移动的极佳方法",
        "category": "blocks",
        "price": {"currency": "gold", "amount": 4},
        "item": {"newItemName": "minecraft:web", "count": 1},
        "check_can_buy": None
    },

    # ==================== 护甲类 (8个) ====================
    {
        "id": "armor.gold",
        "name": u"黄金套装",
        "intro": u"包含黄金胸甲和靴子",
        "category": "armor",
        "price": {"currency": "gold", "amount": 6},
        "item": [
            {"newItemName": "minecraft:golden_chestplate", "count": 1},
            {"newItemName": "minecraft:golden_boots", "count": 1}
        ],
        "check_can_buy": lambda preset, player_id: u"已拥有更好的护甲" if is_player_chestplate_better_than(player_id, "minecraft:golden_chestplate") else None
    },
    {
        "id": "armor.chain",
        "name": u"锁链套装",
        "intro": u"包含锁链胸甲和靴子",
        "category": "armor",
        "price": {"currency": "iron", "amount": 40},
        "item": [
            {"newItemName": "minecraft:chainmail_chestplate", "count": 1},
            {"newItemName": "minecraft:chainmail_boots", "count": 1}
        ],
        "check_can_buy": lambda preset, player_id: u"已拥有更好的护甲" if is_player_chestplate_better_than(player_id, "minecraft:chainmail_chestplate") else None
    },
    {
        "id": "armor.iron",
        "name": u"铁套装",
        "intro": u"包含铁胸甲和靴子",
        "category": "armor",
        "price": {"currency": "gold", "amount": 12},
        "item": [
            {"newItemName": "minecraft:iron_chestplate", "count": 1},
            {"newItemName": "minecraft:iron_boots", "count": 1}
        ],
        "check_can_buy": lambda preset, player_id: u"已拥有更好的护甲" if is_player_chestplate_better_than(player_id, "minecraft:iron_chestplate") else None
    },
    {
        "id": "armor.diamond",
        "name": u"钻石套装",
        "intro": u"包含钻石胸甲和靴子",
        "category": "armor",
        "price": {"currency": "emerald", "amount": 6},
        "item": [
            {"newItemName": "minecraft:diamond_chestplate", "count": 1},
            {"newItemName": "minecraft:diamond_boots", "count": 1}
        ],
        "check_can_buy": lambda preset, player_id: u"已拥有更好的护甲" if is_player_chestplate_better_than(player_id, "minecraft:diamond_chestplate") else None
    },
    {
        "id": "armor.gold.r",
        "name": u"黄金套装",
        "intro": u"包含黄金护腿和靴子",
        "category": "armor",
        "price": {"currency": "gold", "amount": 6},
        "item": [
            {"newItemName": "minecraft:golden_leggings", "count": 1},
            {"newItemName": "minecraft:golden_boots", "count": 1}
        ],
        "check_can_buy": lambda preset, player_id: u"已拥有更好的护甲" if is_player_leggings_better_than(player_id, "minecraft:golden_leggings") else None
    },
    {
        "id": "armor.chain.r",
        "name": u"锁链套装",
        "intro": u"包含锁链护腿和靴子",
        "category": "armor",
        "price": {"currency": "iron", "amount": 40},
        "item": [
            {"newItemName": "minecraft:chainmail_leggings", "count": 1},
            {"newItemName": "minecraft:chainmail_boots", "count": 1}
        ],
        "check_can_buy": lambda preset, player_id: u"已拥有更好的护甲" if is_player_leggings_better_than(player_id, "minecraft:chainmail_leggings") else None
    },
    {
        "id": "armor.iron.r",
        "name": u"铁套装",
        "intro": u"包含铁护腿和靴子",
        "category": "armor",
        "price": {"currency": "gold", "amount": 12},
        "item": [
            {"newItemName": "minecraft:iron_leggings", "count": 1},
            {"newItemName": "minecraft:iron_boots", "count": 1}
        ],
        "check_can_buy": lambda preset, player_id: u"已拥有更好的护甲" if is_player_leggings_better_than(player_id, "minecraft:iron_leggings") else None
    },
    {
        "id": "armor.diamond.r",
        "name": u"钻石套装",
        "intro": u"包含钻石护腿和靴子",
        "category": "armor",
        "price": {"currency": "emerald", "amount": 6},
        "item": [
            {"newItemName": "minecraft:diamond_leggings", "count": 1},
            {"newItemName": "minecraft:diamond_boots", "count": 1}
        ],
        "check_can_buy": lambda preset, player_id: u"已拥有更好的护甲" if is_player_leggings_better_than(player_id, "minecraft:diamond_leggings") else None
    },

    # ==================== 武器类 (5个) ====================
    {
        "id": "sword.stone",
        "name": u"石剑",
        "intro": u"每次攻击，造成6HP伤害",
        "category": "weapons",
        "price": {"currency": "iron", "amount": 10},
        "item": {"newItemName": "minecraft:stone_sword", "count": 1},
        "check_can_buy": lambda preset, player_id: u"已拥有高等级剑" if is_player_sword_better_than(preset, player_id, "minecraft:stone_sword") else None
    },
    {
        "id": "sword.iron",
        "name": u"铁剑",
        "intro": u"每次攻击，造成7HP伤害",
        "category": "weapons",
        "price": {"currency": "gold", "amount": 7},
        "item": {"newItemName": "minecraft:iron_sword", "count": 1},
        "check_can_buy": lambda preset, player_id: u"已拥有高等级剑" if is_player_sword_better_than(preset, player_id, "minecraft:iron_sword") else None
    },
    {
        "id": "sword.diamond",
        "name": u"钻石剑",
        "intro": u"每次攻击，造成8HP伤害",
        "category": "weapons",
        "price": {"currency": "emerald", "amount": 4},
        "item": {"newItemName": "minecraft:diamond_sword", "count": 1},
        "check_can_buy": lambda preset, player_id: u"已拥有高等级剑" if is_player_sword_better_than(preset, player_id, "minecraft:diamond_sword") else None
    },
    {
        "id": "sword.knock",
        "name": u"击退棒",
        "intro": u"把敌人打下虚空！",
        "category": "weapons",
        "price": {"currency": "gold", "amount": 5},
        "item": {
            "newItemName": "easecation:blaze_rod",
            "count": 1,
            "enchantData": [(EnchantType.WeaponKnockback, 2)],
            "customTips": u"击退棒%category%%enchanting%"
        },
        "check_can_buy": None
    },
    {
        "id": "sword.fishing-rod",
        "name": u"鱼竿",
        "intro": u"把敌人钓上钩！",
        "category": "weapons",
        "price": {"currency": "emerald", "amount": 1},
        "item": {"newItemName": "minecraft:fishing_rod", "count": 1},
        "check_can_buy": None
    },

    # ==================== 工具类 (6个) ====================
    {
        "id": "tool.shear",
        "name": u"剪刀",
        "intro": u"适用于破坏羊毛， 每次重生时都会获得剪刀。",
        "category": "tools",
        "price": {"currency": "iron", "amount": 20},
        "item": {"newItemName": "minecraft:shears", "count": 1},
        "check_can_buy": None
    },
    {
        "id": "tool.stone-pickaxe",
        "name": u"石镐",
        "intro": u"可以快速破坏石头类方块的道具",
        "category": "tools",
        "price": {"currency": "iron", "amount": 10},
        "item": {"newItemName": "minecraft:stone_pickaxe", "count": 1},
        "check_can_buy": None
    },
    {
        "id": "tool.iron-pickaxe",
        "name": u"铁镐",
        "intro": u"可以快速破坏石头类方块的道具",
        "category": "tools",
        "price": {"currency": "gold", "amount": 3},
        "item": {"newItemName": "minecraft:iron_pickaxe", "count": 1},
        "check_can_buy": None
    },
    {
        "id": "tool.gold-pickaxe",
        "name": u"金镐",
        "intro": u"可以快速破坏石头类方块的道具",
        "category": "tools",
        "price": {"currency": "gold", "amount": 6},
        "item": {"newItemName": "minecraft:golden_pickaxe", "count": 1},
        "check_can_buy": None
    },
    {
        "id": "tool.diamond-pickaxe",
        "name": u"钻石镐",
        "intro": u"可以快速破坏石头类方块的道具",
        "category": "tools",
        "price": {"currency": "gold", "amount": 6},
        "item": {"newItemName": "minecraft:diamond_pickaxe", "count": 1},
        "check_can_buy": None
    },
    {
        "id": "tool.iron-axe",
        "name": u"铁斧",
        "intro": u"可以快速破坏木头方块的道具",
        "category": "tools",
        "price": {"currency": "gold", "amount": 3},
        "item": {"newItemName": "minecraft:iron_axe", "count": 1},
        "check_can_buy": None
    },

    # ==================== 弓箭类 (6个) ====================
    {
        "id": "arrow.0",
        "name": u"普通 弓",
        "intro": u"平平无奇的弓",
        "category": "arrows",
        "price": {"currency": "gold", "amount": 12},
        "item": {"newItemName": "minecraft:bow", "count": 1},
        "check_can_buy": None
    },
    {
        "id": "arrow.1",
        "name": u"力量 附魔弓",
        "intro": u"拥有力量附魔的弓！",
        "category": "arrows",
        "price": {"currency": "gold", "amount": 20},
        "item": {
            "newItemName": "minecraft:bow",
            "count": 1,
            "enchantData": [(EnchantType.BowDamage, 1)]
        },
        "check_can_buy": None
    },
    {
        "id": "arrow.1.5",
        "name": u"力量I 冲击I 附魔弓",
        "intro": u"拥有力量附魔和击退的弓！",
        "category": "arrows",
        "price": {"currency": "emerald", "amount": 2},
        "item": {
            "newItemName": "minecraft:bow",
            "count": 1,
            "enchantData": [
                (EnchantType.BowDamage, 1),
                (EnchantType.BowKnockback, 1)
            ]
        },
        "check_can_buy": None
    },
    {
        "id": "arrow.2",
        "name": u"力量 击退 火焰 附魔弓",
        "intro": u"让敌人着火！",
        "category": "arrows",
        "price": {"currency": "emerald", "amount": 6},
        "item": {
            "newItemName": "minecraft:bow",
            "count": 1,
            "enchantData": [
                (EnchantType.BowDamage, 1),
                (EnchantType.BowKnockback, 1),
                (EnchantType.BowFire, 1)
            ]
        },
        "check_can_buy": None
    },
    {
        "id": "arrow.arrow",
        "name": u"箭",
        "intro": u"搭配弓使用",
        "category": "arrows",
        "price": {"currency": "gold", "amount": 2},
        "item": {"newItemName": "minecraft:arrow", "count": 1},
        "check_can_buy": None
    },
    {
        "id": "arrow.arrow5",
        "name": u"箭",
        "intro": u"一次性买5支，搭配弓使用",
        "category": "arrows",
        "price": {"currency": "gold", "amount": 6},
        "item": {"newItemName": "minecraft:arrow", "count": 5},
        "check_can_buy": None
    },
    {
        "id": "arrow.arrow6",
        "name": u"箭",
        "intro": u"一次性买6支，搭配弓使用",
        "category": "arrows",
        "price": {"currency": "emerald", "amount": 2},
        "item": {"newItemName": "minecraft:arrow", "count": 6},
        "check_can_buy": None
    },

    # ==================== 药水类 (4个) ====================
    {
        "id": "prop.golden-apple",
        "name": u"金苹果",
        "intro": u"全面治愈",
        "category": "potions",
        "price": {"currency": "gold", "amount": 3},
        "item": {"newItemName": "minecraft:golden_apple", "count": 1},
        "check_can_buy": None
    },
    {
        "id": "prop.speed",
        "name": u"速度药水[60秒]",
        "intro": u"喝下它，你将获得速度效果",
        "category": "potions",
        "price": {"currency": "emerald", "amount": 1},
        "item": {"newItemName": "ecbedwars:potion_speed", "count": 1},
        "check_can_buy": None
    },
    {
        "id": "prop.leaping",
        "name": u"跳跃药水[60秒]",
        "intro": u"喝下它，你将获得跳跃效果",
        "category": "potions",
        "price": {"currency": "emerald", "amount": 1},
        "item": {"newItemName": "ecbedwars:potion_leaping", "count": 1},
        "check_can_buy": None
    },
    {
        "id": "prop.invisible",
        "name": u"隐身药水[60秒]",
        "intro": u"喝下它，你将获得隐身效果",
        "category": "potions",
        "price": {"currency": "emerald", "amount": 2},
        "item": {"newItemName": "ecbedwars:potion_invisibility", "count": 1},
        "check_can_buy": None
    },

    # ==================== 特殊道具类 (14个) ====================
    {
        "id": "prop.ender-pearl",
        "name": u"末影珍珠",
        "intro": u"入侵敌人基地的最快方法",
        "category": "special",
        "price": {"currency": "emerald", "amount": 4},
        "item": {"newItemName": "minecraft:ender_pearl", "count": 1},
        "check_can_buy": None
    },
    {
        "id": "prop.snow-ball",
        "name": u"雪球",
        "intro": u"远距离把敌人打入虚空！",
        "category": "special",
        "price": {"currency": "iron", "amount": 10},
        "item": {"newItemName": "minecraft:snowball", "count": 5},
        "check_can_buy": None
    },
    {
        "id": "prop.egg",
        "name": u"爆炸鸡蛋",
        "intro": u"远程投掷的鸡蛋，落地后产生奇妙的爆炸",
        "category": "special",
        "price": {"currency": "emerald", "amount": 1},
        "item": {"newItemName": "minecraft:egg", "count": 1},
        "check_can_buy": None
    },
    {
        "id": "prop.tnt",
        "name": u"爆炸的TNT",
        "intro": u"瞬间点燃， 适用于摧毁沿途的防御工事",
        "category": "special",
        "price": {"currency": "gold", "amount": 4},
        "item": {
            "newItemName": "minecraft:tnt",
            "count": 1,
            "customTips": u"爆炸的TNT%category%\n瞬间点燃， 适用于摧毁沿途的防御工事"
        },
        "check_can_buy": None
    },
    {
        "id": "prop.bedbug",
        "name": u"床虱",
        "intro": u"在虫蛋落地之处生成蠹虫， 干扰你的对手。",
        "category": "special",
        "price": {"currency": "iron", "amount": 40},
        "item": {"newItemName": "ecbedwars:bedbug", "count": 1},
        "check_can_buy": None
    },
    {
        "id": "prop.dream-guardian",
        "name": u"梦境守护者",
        "intro": u"铁傀儡能守护你的基地",
        "category": "special",
        "price": {"currency": "emerald", "amount": 4},
        "item": {"newItemName": "ecbedwars:iron_golem", "count": 1},
        "check_can_buy": None
    },
    {
        "id": "prop.fireball",
        "name": u"烈焰弹",
        "intro": u"右键发射！ 击飞在桥上行走的敌人",
        "category": "special",
        "price": {"currency": "iron", "amount": 40},
        "item": {"newItemName": "ecbedwars:fireball", "count": 1},
        "check_can_buy": None
    },
    {
        "id": "prop.bucket",
        "name": u"水桶",
        "intro": u"能很好地降低来犯敌人的速度\n也可以抵消TNT的伤害",
        "category": "special",
        "price": {"currency": "gold", "amount": 3},
        "item": {"newItemName": "minecraft:water_bucket", "count": 1},
        "check_can_buy": None
    },
    {
        "id": "prop.magic-milk",
        "name": u"神奇牛奶",
        "intro": u"使用后，30秒内避免触发任何陷阱",
        "category": "special",
        "price": {"currency": "gold", "amount": 4},
        "item": {
            "newItemName": "minecraft:milk_bucket",
            "count": 1,
            "customTips": u"神奇牛奶%category%\n使用后，30秒内避免触发任何陷阱"
        },
        "check_can_buy": None
    },
    {
        "id": "prop.sponge",
        "name": u"干海绵",
        "intro": u"用于吸收水分",
        "category": "special",
        "price": {"currency": "gold", "amount": 6},
        "item": {"newItemName": "minecraft:sponge", "count": 4},
        "check_can_buy": None
    },
    {
        "id": "prop.bridge-egg",
        "name": u"搭桥蛋",
        "intro": u"扔出蛋后，会在其飞行轨迹上生成一座桥",
        "category": "special",
        "price": {"currency": "emerald", "amount": 1},
        "item": {"newItemName": "ecbedwars:bridge_egg", "count": 1},
        "check_can_buy": None
    },
    {
        "id": "prop.defense-tower",
        "name": u"紧凑型防御塔",
        "intro": u"建造一个速建防御塔！",
        "category": "special",
        "price": {"currency": "iron", "amount": 24},
        "item": {"newItemName": "ecbedwars:defense_tower", "count": 1},
        "check_can_buy": None
    },

    # ==================== 队伍升级类 (7个) ====================
    # 注: 这些商品的购买逻辑将在任务2.2中实现
    {
        "id": "upgrade.health",
        "name": u"升级 全队最高血量",
        "intro": u"提升己方所有成员的血量上限！",
        "category": "upgrades",
        "type": "team_upgrade",
        "upgrade_key": "health",
        "max_level": 3,
        "upgrade_type": True,
        "levels_intro": [u"+ 3HP", u"+ 6HP", u"+ 10HP"],
        "price": {
            0: {"currency": "diamond", "amount": 2},
            1: {"currency": "diamond", "amount": 4},
            2: {"currency": "diamond", "amount": 8}
        },
        "show_item": {"newItemName": "minecraft:redstone", "count": 1},
        "check_can_buy": "check_team_upgrade_limit"
    },
    {
        "id": "upgrade.armor",
        "name": u"升级 全队护甲保护等级",
        "intro": u"己方所有成员的盔甲将获得永久保护附魔！",
        "category": "upgrades",
        "type": "team_upgrade",
        "upgrade_key": "armor",
        "max_level": 4,
        "upgrade_type": True,
        "levels_intro": [u"保护I", u"保护II", u"保护III", u"保护IV"],
        "price": {
            0: {"currency": "diamond", "amount": 2},
            1: {"currency": "diamond", "amount": 4},
            2: {"currency": "diamond", "amount": 8},
            3: {"currency": "diamond", "amount": 16}
        },
        "show_item": {"newItemName": "minecraft:iron_chestplate", "count": 1},
        "check_can_buy": "check_team_upgrade_limit"
    },
    {
        "id": "upgrade.sword",
        "name": u"升级 全队武器锋利等级",
        "intro": u"己方全部成员将获得锋利附魔！",
        "category": "upgrades",
        "type": "team_upgrade",
        "upgrade_key": "sword",
        "max_level": 1,
        "upgrade_type": True,
        "levels_intro": [u"锋利附魔I"],
        "price": {
            0: {"currency": "diamond", "amount": 4}
        },
        "show_item": {"newItemName": "minecraft:diamond_sword", "count": 1},
        "check_can_buy": "check_team_upgrade_limit"
    },
    {
        "id": "upgrade.super-miner",
        "name": u"升级 超级矿工",
        "intro": u"己方所有队员将获得急迫效果！",
        "category": "upgrades",
        "type": "team_upgrade",
        "upgrade_key": "miner",
        "max_level": 2,
        "upgrade_type": True,
        "levels_intro": [u"急迫I", u"急迫II"],
        "price": {
            0: {"currency": "diamond", "amount": 2},
            1: {"currency": "diamond", "amount": 4}
        },
        "show_item": {"newItemName": "minecraft:golden_pickaxe", "count": 1},
        "check_can_buy": "check_team_upgrade_limit"
    },
    {
        "id": "upgrade.bedwars-gen",
        "name": u"升级 队伍产矿机",
        "intro": u"提升自己岛屿上的资源生成效率",
        "category": "upgrades",
        "type": "team_upgrade",
        "upgrade_key": "generator",
        "max_level": 4,
        "upgrade_type": True,
        "levels_intro": [u"+50%资源", u"+100%资源", u"生成绿宝石", u"+200%资源"],
        "price": {
            0: {"currency": "diamond", "amount": 2},
            1: {"currency": "diamond", "amount": 4},
            2: {"currency": "diamond", "amount": 6},
            3: {"currency": "diamond", "amount": 8}
        },
        "show_item": {"newItemName": "minecraft:furnace", "count": 1},
        "check_can_buy": "check_team_upgrade_limit"
    },
    {
        "id": "upgrade.healing-pool",
        "name": u"治愈池",
        "intro": u"基地附近的本队成员将获得生命恢复效果",
        "category": "upgrades",
        "type": "team_upgrade",
        "upgrade_key": "healing_pool",
        "max_level": 1,
        "upgrade_type": True,
        "levels_intro": [],
        "price": {
            0: {"currency": "diamond", "amount": 3}
        },
        "show_item": {"newItemName": "minecraft:beacon", "count": 1},
        "check_can_buy": "check_team_upgrade_limit"
    },
    {
        "id": "upgrade.compass-tracking",
        "name": u"指南针追踪",
        "intro": u"队伍全员的指南针将指向距离最近的敌人",
        "category": "upgrades",
        "type": "team_upgrade",
        "upgrade_key": "compass_tracking",
        "max_level": 1,
        "upgrade_type": True,
        "levels_intro": [],
        "price": {
            0: {"currency": "diamond", "amount": 2}
        },
        "show_item": {"newItemName": "minecraft:compass", "count": 1},
        "check_can_buy": "check_team_upgrade_limit"
    },

    # ==================== 可升级物品类 (2个) ====================
    # 注: 这些商品的购买逻辑将在任务2.3中实现
    {
        "id": "tool.pickaxe-upgrade",
        "name": u"稿子",
        "intro": u"该道具可升级\n\n重生后自动降低一级\n\n每次重生时,至少是最低等级",
        "category": "tools",
        "type": "item_upgrade",
        "upgrade_type": True,
        "levels_intro": [u"木稿 (效率I)", u"石稿 (效率II)", u"铁稿 (效率III)", u"钻石稿 (效率IV)"],
        "item_levels": [
            {"newItemName": "minecraft:wooden_pickaxe", "enchantData": [(EnchantType.MiningEfficiency, 1)], "count": 1},
            {"newItemName": "minecraft:stone_pickaxe", "enchantData": [(EnchantType.MiningEfficiency, 2)], "count": 1},
            {"newItemName": "minecraft:iron_pickaxe", "enchantData": [(EnchantType.MiningEfficiency, 3)], "count": 1},
            {"newItemName": "minecraft:diamond_pickaxe", "enchantData": [(EnchantType.MiningEfficiency, 4)], "count": 1}
        ],
        # 升级路径: 用于在背包中查找当前等级和显示物品图标
        "upgrade_path": [
            "minecraft:wooden_pickaxe",
            "minecraft:stone_pickaxe",
            "minecraft:iron_pickaxe",
            "minecraft:diamond_pickaxe"
        ],
        "price": {
            0: {"currency": "iron", "amount": 10},
            1: {"currency": "iron", "amount": 10},
            2: {"currency": "gold", "amount": 3},
            3: {"currency": "gold", "amount": 6}
        },
        "check_can_buy": "check_item_upgrade_limit"
    },
    {
        "id": "tool.axe-upgrade",
        "name": u"斧子",
        "intro": u"该道具可升级\n\n重生后自动降低一级\n\n每次重生时,至少是最低等级",
        "category": "tools",
        "type": "item_upgrade",
        "upgrade_type": True,
        "levels_intro": [u"木斧 (效率I)", u"石斧 (效率I)", u"铁斧 (效率II)", u"钻石斧 (效率III)"],
        "item_levels": [
            {"newItemName": "minecraft:wooden_axe", "enchantData": [(EnchantType.MiningEfficiency, 1)], "count": 1},
            {"newItemName": "minecraft:stone_axe", "enchantData": [(EnchantType.MiningEfficiency, 1)], "count": 1},
            {"newItemName": "minecraft:iron_axe", "enchantData": [(EnchantType.MiningEfficiency, 2)], "count": 1},
            {"newItemName": "minecraft:diamond_axe", "enchantData": [(EnchantType.MiningEfficiency, 3)], "count": 1}
        ],
        # 升级路径: 用于在背包中查找当前等级和显示物品图标
        "upgrade_path": [
            "minecraft:wooden_axe",
            "minecraft:stone_axe",
            "minecraft:iron_axe",
            "minecraft:diamond_axe"
        ],
        "price": {
            0: {"currency": "iron", "amount": 10},
            1: {"currency": "iron", "amount": 10},
            2: {"currency": "gold", "amount": 3},
            3: {"currency": "gold", "amount": 6}
        },
        "check_can_buy": "check_item_upgrade_limit"
    },

    # ==================== 陷阱类 (4个) ====================
    # 注: 这些商品的购买逻辑将在任务2.2中实现
    {
        "id": "trap.slowness",
        "name": u"这是个陷阱！",
        "intro": u"给予入侵的敌人短暂的失明+缓慢效果",
        "category": "traps",
        "type": "trap",
        "trap_type": "slowness",
        "price": {"currency": "diamond", "amount": 1},
        "show_item": {"newItemName": "minecraft:tripwire_hook", "count": 1},
        "check_can_buy": "check_trap_limit"
    },
    {
        "id": "trap.beat-back",
        "name": u"反击陷阱",
        "intro": u"当敌人入侵时，我方队员将获得短暂的速度II+跳跃II",
        "category": "traps",
        "type": "trap",
        "trap_type": "beat-back",
        "price": {"currency": "diamond", "amount": 1},
        "show_item": {"newItemName": "minecraft:feather", "count": 1},
        "check_can_buy": "check_trap_limit"
    },
    {
        "id": "trap.alert",
        "name": u"报警陷阱",
        "intro": u"这个陷阱可以发现处于隐身状态的入侵者",
        "category": "traps",
        "type": "trap",
        "trap_type": "alert",
        "price": {"currency": "diamond", "amount": 1},
        "show_item": {"newItemName": "minecraft:redstone_torch", "count": 1},
        "check_can_buy": "check_trap_limit"
    },
    {
        "id": "trap.fatigue",
        "name": u"挖掘疲劳陷阱",
        "intro": u"给予入侵者挖掘疲劳效果",
        "category": "traps",
        "type": "trap",
        "trap_type": "fatigue",
        "price": {"currency": "diamond", "amount": 1},
        "show_item": {"newItemName": "minecraft:iron_pickaxe", "count": 1},
        "check_can_buy": "check_trap_limit"
    },
]


# ========== 商店分类配置 ==========

SHOP_CONFIG = {
    "type": "default",
    "name": u"装备&道具 商店",
    "intro": u"请点击下列分类来购买道具与装备:",
    "currencies": ["iron", "gold", "diamond", "emerald"],
    "categories": [
        # 1. 快捷列表 (与老项目完全一致 - 最重要的橱窗)
        {
            "id": "quick_list",
            "name": u"快捷列表",
            "intro": u"常用道具快速购买",
            "goods_ids": [
                "block.wool",
                "sword.stone",
                "armor.chain.r",
                "tool.pickaxe-upgrade",
                "arrow.0",
                "prop.fireball",
                "prop.tnt",
                "block.plank",
                "sword.iron",
                "armor.iron.r",
                "tool.axe-upgrade",
                "arrow.1",
                "prop.speed",
                "prop.golden-apple",
                "block.clay",
                "sword.diamond",
                "armor.diamond.r",
                "tool.shear",
                "arrow.arrow6",
                "prop.invisible",
                "prop.bucket",
                "block.glass",
                "block.end-stone.12",
                "block.ladder",
                "block.obsidian.4",
                "sword.knock",
                "arrow.1.5",
                "prop.leaping",
                "prop.bedbug",
                "prop.dream-guardian",
                "prop.ender-pearl",
                "prop.bridge-egg",
                "prop.magic-milk",
                "prop.sponge",
                "prop.defense-tower",
                "trap.slowness",
                "trap.beat-back",
                "trap.alert",
                "trap.fatigue"
            ],
            "ui": {
                "layout": "GRID",
                "recommend": True,
                "title": "quick_list",
                "categoryTexture": "textures/ui/bw/bw_category_fast"
            }
        },
        # 2. 方块分类 (与老项目完全一致 - 7个商品)
        {
            "id": "blocks",
            "name": u"方块",
            "intro": u"购买建筑方块",
            "goods_ids": [
                "block.wool",
                "block.clay",
                "block.glass",
                "block.end-stone.12",
                "block.ladder",
                "block.plank",
                "block.obsidian.4"
            ],
            "ui": {
                "layout": "BLOCK",
                "recommend": False,
                "title": "blocks",
                "categoryTexture": "textures/ui/bw/bw_category_block"
            }
        },
        # 3. 利剑分类 (与老项目完全一致 - 4个商品)
        {
            "id": "weapons",
            "name": u"利剑",
            "intro": u"购买武器",
            "goods_ids": [
                "sword.stone",
                "sword.iron",
                "sword.diamond",
                "sword.knock"
            ],
            "ui": {
                "layout": "BLOCK",
                "recommend": False,
                "title": "weapons",
                "categoryTexture": "textures/ui/bw/bw_category_sword"
            }
        },
        # 4. 弓箭分类 (与老项目完全一致 - 4个商品)
        {
            "id": "arrows",
            "name": u"弓箭",
            "intro": u"购买弓和箭",
            "goods_ids": [
                "arrow.0",
                "arrow.1",
                "arrow.1.5",
                "arrow.arrow6"
            ],
            "ui": {
                "layout": "BLOCK",
                "recommend": False,
                "title": "arrows",
                "categoryTexture": "textures/ui/bw/bw_category_arrow"
            }
        },
        # 5. 护甲分类 (与老项目完全一致 - 3个商品, 只有护腿版本)
        {
            "id": "armor",
            "name": u"防具",
            "intro": u"购买护甲装备",
            "goods_ids": [
                "armor.chain.r",
                "armor.iron.r",
                "armor.diamond.r"
            ],
            "ui": {
                "layout": "BLOCK",
                "recommend": False,
                "title": "armor",
                "categoryTexture": "textures/ui/bw/bw_category_armor"
            }
        },
        # 6. 工具分类 (与老项目完全一致 - 3个商品)
        {
            "id": "tools",
            "name": u"工具",
            "intro": u"购买工具",
            "goods_ids": [
                "tool.pickaxe-upgrade",
                "tool.axe-upgrade",
                "tool.shear"
            ],
            "ui": {
                "layout": "BLOCK",
                "recommend": False,
                "title": "tools",
                "categoryTexture": "textures/ui/bw/bw_category_tool"
            }
        },
        # 7. 酿造分类 (与老项目完全一致 - 3个商品)
        {
            "id": "potions",
            "name": u"酿造",
            "intro": u"购买药水",
            "goods_ids": [
                "prop.golden-apple",
                "prop.speed",
                "prop.invisible"
            ],
            "ui": {
                "layout": "BLOCK",
                "recommend": False,
                "title": "potions",
                "categoryTexture": "textures/ui/bw/bw_category_brewing"
            }
        },
        # 8. 道具分类 (与老项目完全一致 - 9个商品)
        {
            "id": "special",
            "name": u"道具",
            "intro": u"购买特殊道具",
            "goods_ids": [
                "prop.ender-pearl",
                "prop.fireball",
                "prop.tnt",
                "prop.bucket",
                "prop.sponge",
                "prop.bedbug",
                "prop.dream-guardian",
                "prop.bridge-egg",
                "prop.defense-tower"
            ],
            "ui": {
                "layout": "BLOCK",
                "recommend": False,
                "title": "special",
                "categoryTexture": "textures/ui/bw/bw_category_props"
            }
        }
    ]
}


# ========== 升级商店配置 (upgrade商店专用) ==========

UPGRADE_SHOP_CONFIG = {
    "type": "upgrade",
    "name": u"升级&陷阱 商店",
    "intro": u"升级团队的装备，布置团队陷阱，为大局考虑!",
    "currencies": ["iron", "gold", "diamond", "emerald"],
    "categories": [
        # 1. 队伍升级分类 (与老项目完全一致 - 6个商品)
        {
            "id": "upgrades",
            "name": u"升级",
            "intro": u"升级团队的装备",
            "goods_ids": [
                "upgrade.sword",
                "upgrade.armor",
                "upgrade.super-miner",
                "upgrade.bedwars-gen",
                "upgrade.healing-pool",
                "upgrade.compass-tracking"
            ],
            "ui": {
                "layout": "DETAIL",
                "recommend": False,
                "title": "upgrades",
                "categoryTexture": "textures/ui/bw/bw_category_upgrade"
            }
        },
        # 2. 陷阱分类
        {
            "id": "traps",
            "name": u"陷阱",
            "intro": u"布置陷阱，将在敌人接近你的床时触发！最多3个陷阱。",
            "goods_ids": [
                "trap.slowness",
                "trap.beat-back",
                "trap.alert",
                "trap.fatigue"
            ],
            "ui": {
                "layout": "DETAIL",
                "recommend": False,
                "title": "traps",
                "categoryTexture": "textures/ui/bw/bw_category_trap"
            }
        }
    ]
}


# ========== 辅助函数: 根据ID查找商品 ==========

def find_goods_by_id(goods_id):
    """
    根据商品ID查找商品配置

    Args:
        goods_id (str): 商品ID

    Returns:
        dict|None: 商品配置字典或None
    """
    for goods in GOODS_POOL:
        if goods["id"] == goods_id:
            return goods
    return None
