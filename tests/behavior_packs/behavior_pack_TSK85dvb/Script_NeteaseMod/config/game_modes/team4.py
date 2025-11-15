# -*- coding: utf-8 -*-
"""
自动从JSON转换的配置文件
原文件: team4.json
"""

MODE_CONFIG = {
    "mode_id": "team4",
    "mode_name": u"4队2人",
    "teams": ["RED", "YELLOW", "GREEN", "BLUE"],
    "teams_max_players": 2,
    "scoreboard_title": "game.name.bed-wars",
    "dragon_since": 360,
    "dragon_each": 360,
    "gaming_states": [
        {
            "duration": 180000,
            "name": u"游戏开始",
        },
        {
            "duration": 180000,
            "name": u"钻石点II级",
            "starting_do": {
                "type": "GENERATOR",
                "resource_type": "DIAMOND",
                "team": "NONE",
                "level": 2,
            },
        },
        {
            "duration": 180000,
            "name": u"绿宝石点II级",
            "starting_do": {
                "type": "GENERATOR",
                "resource_type": "EMERALD",
                "team": "NONE",
                "level": 2,
            },
        },
        {
            "duration": 180000,
            "name": u"钻石点III级",
            "starting_do": {
                "type": "GENERATOR",
                "resource_type": "DIAMOND",
                "team": "NONE",
                "level": 3,
            },
        },
        {
            "duration": 180000,
            "name": u"绿宝石点III级",
            "starting_do": {
                "type": "GENERATOR",
                "resource_type": "EMERALD",
                "team": "NONE",
                "level": 3,
            },
        },
        {
            "duration": 180000,
            "name": u"床自毁",
            "starting_do": {
                "type": "DESTROY",
            },
        },
        {
            "duration": 180000,
            "name": u"最终阶段",
            "starting_do": {
                "type": "DRAGON",
                "message": u"{bold}{light-purple}末影龙出没",
            },
        },
        {
            "duration": 0,
            "name": u"游戏结束",
        },
    ],
    "keep_armors": True,
    "base_health": 20,
    "crystal_health": 20,
    "arrow_break": True,
    "auto_rescue": True,
    "tnt_size": 5,
    "auto_road": False,
    "attack_cool_down": -1,
    "knockback": -1,
    "death_transfer": [],
    "death_drop": [
        "minecraft:iron_ingot",
        "minecraft:gold_ingot",
        "minecraft:diamond",
        "minecraft:emerald",
    ],
    "death_exp_transfer": 0,
    "death_keep": [
        "minecraft:wooden_sword",
        "minecraft:compass",
        "minecraft:golden_helmet",
        "minecraft:golden_chestplate",
        "minecraft:golden_leggings",
        "minecraft:golden_boots",
        "minecraft:chainmail_helmet",
        "minecraft:chainmail_chestplate",
        "minecraft:chainmail_leggings",
        "minecraft:chainmail_boots",
        "minecraft:iron_helmet",
        "minecraft:iron_chestplate",
        "minecraft:iron_leggings",
        "minecraft:iron_boots",
        "minecraft:diamond_helmet",
        "minecraft:diamond_chestplate",
        "minecraft:diamond_leggings",
        "minecraft:diamond_boots",
        "minecraft:shears",
    ],
    "death_item_demotion": [
        "tool.pickaxe-upgrade",
        "tool.axe-upgrade",
    ],
    "available_currency": ["IRON", "GOLD", "DIAMOND", "EMERALD"],
}
