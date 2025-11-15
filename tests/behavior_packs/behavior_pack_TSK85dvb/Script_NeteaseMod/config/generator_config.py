# -*- coding: utf-8 -*-
"""
资源生成器配置

定义资源生成器的资源类型、升级等级和游戏阶段事件

重构说明：
从 generator_config.json 迁移到 Python 配置模块
"""

# 资源类型配置
RESOURCE_TYPES = {
    "IRON": {
        "name": "铁锭",
        "item": "minecraft:iron_ingot",
        "top_count": 15,  # 修正: 恢复老项目值（原64过大）
        "particle_color": [224, 224, 224],
        "floating_item": {
            "itemName": "minecraft:iron_ingot",
            "count": 1,
            "auxValue": 0
        }
    },
    "GOLD": {
        "name": "金锭",
        "item": "minecraft:gold_ingot",
        "top_count": 10,  # 修正: 恢复老项目值（原32过大）
        "particle_color": [255, 192, 0],
        "floating_item": {
            "itemName": "minecraft:gold_ingot",
            "count": 1,
            "auxValue": 0
        }
    },
    "DIAMOND": {
        "name": "钻石",
        "item": "minecraft:diamond",
        "top_count": 8,  # 修正: 恢复老项目值（原16过大）
        "particle_color": [60, 253, 255],
        "floating_item": {
            "itemName": "minecraft:diamond",
            "count": 1,
            "auxValue": 0
        }
    },
    "EMERALD": {
        "name": "绿宝石",
        "item": "minecraft:emerald",
        "top_count": 8,
        "particle_color": [40, 255, 52],
        "floating_item": {
            "itemName": "minecraft:emerald",
            "count": 1,
            "auxValue": 0
        }
    },
    "COPPER": {
        "name": "铜锭",
        "item": "minecraft:copper_ingot",
        "top_count": 20,
        "particle_color": [144, 59, 12],
        "floating_item": {
            "itemName": "minecraft:copper_ingot",
            "count": 1,
            "auxValue": 0
        }
    }
}

# 升级等级配置
# [P0-7修复] 修正生成器配置，恢复与老项目一致的生成速度
UPGRADE_LEVELS = {
    "IRON": [
        {
            "level": 1,
            "period": 2000,  # 修正: 2秒（老项目值）
            "count": 3,      # 修正: 每次生成3个（老项目值）
            "description": "每2秒生成3个铁锭"
        },
        {
            "level": 2,
            "period": 2000,  # 修正: 2秒（老项目值）
            "count": 5,      # 修正: 每次生成5个（老项目值）
            "description": "每2秒生成5个铁锭"
        },
        {
            "level": 3,
            "period": 2000,  # 修正: 2秒（老项目值）
            "count": 10,     # 修正: 每次生成10个（老项目值）
            "description": "每2秒生成10个铁锭"
        },
        {
            "level": 4,
            "period": 500,
            "count": 2,
            "description": "每0.5秒生成2个铁锭"
        }
    ],
    "GOLD": [
        {
            "level": 1,
            "period": 5000,  # 修正: 5秒（老项目值）
            "count": 1,      # 保持1个
            "description": "每5秒生成1个金锭"
        },
        {
            "level": 2,
            "period": 5000,  # 修正: 5秒（老项目值）
            "count": 2,      # 修正: 每次生成2个（老项目值）
            "description": "每5秒生成2个金锭"
        },
        {
            "level": 3,
            "period": 5000,  # 修正: 5秒（老项目值）
            "count": 4,      # 修正: 每次生成4个（老项目值）
            "description": "每5秒生成4个金锭"
        },
        {
            "level": 4,
            "period": 2000,
            "count": 1,
            "description": "每2秒生成1个金锭"
        }
    ],
    "DIAMOND": [
        {
            "level": 1,
            "period": 30000,
            "count": 1,
            "description": "每30秒生成1个钻石"
        },
        {
            "level": 2,
            "period": 23000,  # 修正: 23秒（老项目值）
            "count": 1,
            "description": "每23秒生成1个钻石"
        },
        {
            "level": 3,
            "period": 15000,
            "count": 1,
            "description": "每15秒生成1个钻石"
        },
        {
            "level": 4,
            "period": 10000,
            "count": 1,
            "description": "每10秒生成1个钻石"
        }
    ],
    "EMERALD": [
        {
            "level": 1,
            "period": 55000,  # 修正: 55秒（老项目值 - 2队/4队模式）
            "count": 1,
            "description": "每55秒生成1个绿宝石"
        },
        {
            "level": 2,
            "period": 40000,  # 修正: 40秒（老项目值 - 2队/4队模式）
            "count": 1,
            "description": "每40秒生成1个绿宝石"
        },
        {
            "level": 3,
            "period": 30000,
            "count": 1,
            "description": "每30秒生成1个绿宝石"
        },
        {
            "level": 4,
            "period": 20000,
            "count": 1,
            "description": "每20秒生成1个绿宝石"
        }
    ],
    # 8队模式专用绿宝石配置（单人模式资源更稀缺）
    "EMERALD_TEAM8": [
        {
            "level": 1,
            "period": 65000,  # 修正: 65秒（老项目8队模式值）
            "count": 1,
            "description": "每65秒生成1个绿宝石（8队模式）"
        },
        {
            "level": 2,
            "period": 50000,  # 修正: 50秒（老项目8队模式值）
            "count": 1,
            "description": "每50秒生成1个绿宝石（8队模式）"
        },
        {
            "level": 3,
            "period": 40000,  # 修正: 40秒（老项目8队模式值）
            "count": 1,
            "description": "每40秒生成1个绿宝石（8队模式）"
        },
        {
            "level": 4,
            "period": 30000,  # 修正: 30秒（老项目8队模式值）
            "count": 1,
            "description": "每30秒生成1个绿宝石（8队模式）"
        }
    ]
}

# 游戏阶段事件配置
PHASE_EVENTS = {
    "description": "游戏阶段事件 - 自动升级产矿机",
    "events": [
        {
            "time": 0,
            "event_type": "game_start",
            "generator_level": {
                "DIAMOND": 1,
                "EMERALD": 1
            }
        },
        {
            "time": 180,
            "event_type": "diamond_upgrade_2",
            "message": "§b§l钻石产矿机 §r§e已升级至 §c等级 II",
            "generator_level": {
                "DIAMOND": 2
            }
        },
        {
            "time": 360,
            "event_type": "emerald_upgrade_2",
            "message": "§a§l绿宝石产矿机 §r§e已升级至 §c等级 II",
            "generator_level": {
                "EMERALD": 2
            }
        },
        {
            "time": 540,
            "event_type": "diamond_upgrade_3",
            "message": "§b§l钻石产矿机 §r§e已升级至 §c等级 III",
            "generator_level": {
                "DIAMOND": 3
            }
        },
        {
            "time": 720,
            "event_type": "emerald_upgrade_3",
            "message": "§a§l绿宝石产矿机 §r§e已升级至 §c等级 III",
            "generator_level": {
                "EMERALD": 3
            }
        },
        {
            "time": 900,
            "event_type": "bed_destroy",
            "message": "§c§l所有床位即将自毁！",
            "bed_destroy_countdown": 60
        },
        {
            "time": 960,
            "event_type": "bed_destroyed",
            "message": "§c§l所有床位已被摧毁！",
            "destroy_all_beds": True
        },
        {
            "time": 1200,
            "event_type": "dragon_spawn",
            "message": "§5§l末影龙已生成！",
            "spawn_dragon": True
        }
    ]
}

# 完整配置（向后兼容）
GENERATOR_CONFIG = {
    "resource_types": RESOURCE_TYPES,
    "upgrade_levels": UPGRADE_LEVELS,
    "phase_events": PHASE_EVENTS
}
