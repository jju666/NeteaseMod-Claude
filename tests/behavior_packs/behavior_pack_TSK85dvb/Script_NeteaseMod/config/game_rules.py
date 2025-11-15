# -*- coding: utf-8 -*-
"""
游戏规则配置

定义起床战争游戏的基本规则、时间和天气设置

重构说明：
从 game_rules.json 迁移到 Python 配置模块

API文档参考：
SetGameRulesInfoServer 需要的字典结构：
{
    'option_info': {
        'pvp': bool,                      # 玩家间伤害
        'show_coordinates': bool,         # 显示坐标
        'natural_regeneration': bool,     # 自然生命恢复
        'tile_drops': bool,               # 方块掉落
        'mob_loot': bool,                 # 生物战利品
        # ... 其他option_info参数
    },
    'cheat_info': {
        'enable': bool,                   # 激活作弊
        'always_day': bool,               # 终为白日
        'mob_griefing': bool,             # 生物破坏
        'keep_inventory': bool,           # 保留物品栏
        'weather_cycle': bool,            # 天气更替
        'mob_spawn': bool,                # 生物生成
        'daylight_cycle': bool,           # 开启昼夜更替
        'command_blocks_enabled': bool,   # 启用命令方块
        # ... 其他cheat_info参数
    }
}
"""

# 游戏规则配置 - 使用正确的API结构
GAME_RULES = {
    'option_info': {
        'pvp': True,                      # 启用PVP
        'show_coordinates': False,        # 不显示坐标
        'natural_regeneration': False,    # 禁用自然回血
        'tile_drops': True,               # 方块掉落
        'mob_loot': True,                 # 生物战利品
    },
    'cheat_info': {
        'enable': True,                   # 激活作弊（必须开启才能修改其他规则）
        'always_day': False,              # 不使用终为白日（我们用SetTime手动设置）
        'mob_griefing': False,            # 生物不破坏方块
        'keep_inventory': False,          # 死亡掉落物品
        'weather_cycle': False,           # 禁用天气更替
        'mob_spawn': False,               # 禁用生物生成 ✅
        'daylight_cycle': False,          # 禁用昼夜循环 ✅
        'command_blocks_enabled': True,   # 启用命令方块
    }
}

# 时间设置
TIME_CONFIG = {
    "set_time": 6000,       # 设置时间为正午（6000 ticks）
    "lock_time": True       # 锁定时间
}

# 天气设置
WEATHER_CONFIG = {
    "set_weather": "clear",  # 设置天气为晴天
    "lock_weather": True     # 锁定天气
}

# 完整配置（向后兼容）
GAME_RULES_CONFIG = {
    "game_rules": GAME_RULES,
    "time": TIME_CONFIG,
    "weather": WEATHER_CONFIG
}
