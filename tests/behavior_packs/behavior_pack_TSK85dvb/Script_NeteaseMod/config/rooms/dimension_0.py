# -*- coding: utf-8 -*-
"""
自动从JSON转换的配置文件
原文件: dimension_0.json
"""

PRESET_CONFIG = {
    "dimension_id": 0,
    "preset_count": 7,
    "presets": [
        {
            "type": "bedwars:practice",
            "id": "practice_area_lobby",
            "config": {
                "pos": [12.0, 135.0, 72.0],
                "practice_range": [
                    [-2, 130, 43],
                    [23, 150, 74],
                ],
                "placeable_range": [
                    [-2, 130, 43],
                    [23, 150, 69],
                ],
                "spawn_pos": [12, 135, 72],
                "spawn_yaw": 0,
                "exit_spawn": [5.5, 134.0, 104],  # 离开时传送回等待出生点
                "exit_spawn_yaw": -90,
                "dimension_id": 0,
            },
        },
        # 教程指引预设
        # 生成器教学演示预设（不创建实体，仅在位置生成物品）
        {
            "type": "bedwars:guide_generator",
            "id": "guide_generator_lobby",
            "config": {
                "pos": [23.0, 136.0, 85.44000244140625],
                "dimension_id": 0,
            },
        },
        {
            "type": "bedwars:guide",
            "id": "684cca97abc74074999c2837d0a48d8b",
            "config": {
                "runtime_entity_id": "ecbedwars:guide",
                "pos": [23.0, 138.0, 85.12000274658203],
                "rotation": {
                    "pitch": 0,
                    "yaw": 0,
                    "roll": 0,
                },
                "guide_type": "COLLECT",
                "dimension_id": 0,
            },
        },
        {
            "type": "bedwars:guide",
            "id": "ef60700beb804883a457d7eb8561921e",
            "config": {
                "runtime_entity_id": "ecbedwars:guide",
                "pos": [20.080001831054688, 138.0400390625, 89.0],
                "rotation": {
                    "pitch": 0,
                    "yaw": 90.0,
                    "roll": 0,
                },
                "transform.rotation[1]": 90.0,
                "guide_type": "BUY",
                "dimension_id": 0,
            },
        },
        {
            "type": "bedwars:guide",
            "id": "4fa50ce8446b4b8dba510358f7d6b877",
            "config": {
                "runtime_entity_id": "ecbedwars:guide",
                "pos": [29.5, 137.0, 90.0],
                "rotation": {
                    "pitch": 0,
                    "yaw": 0,
                    "roll": 0,
                },
                "guide_type": "PROTECT",
                "dimension_id": 0,
            },
        },
        {
            "type": "bedwars:guide_shop",
            "id": "c5ab1c45f4274a51af47156461abe03d",
            "config": {
                "runtime_entity_id": "ecbedwars:entity_5",
                "pos": [19.0, 136.0625, 89.0],
                "rotation": {
                    "pitch": 0,
                    "yaw": 0,
                    "roll": 0,
                },
                "dimension_id": 0,
            },
        },
        {
            "type": "bedwars:guide_bed",
            "id": "b5ce77e6c2cd4b46bfd47337131da0fa",
            "config": {
                "runtime_block_id": "minecraft:bed",
                "pos": [30.0, 136.0, 92.0],
                "rotation": {
                    "pitch": 0,
                    "yaw": 180.0,
                    "roll": 0,
                },
                "dimension_id": 0,
            },
        },
    ],
}
