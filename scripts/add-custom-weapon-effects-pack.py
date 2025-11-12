# -*- coding: utf-8 -*-
"""
添加自定义武器效果系统玩法包到知识库
"""
import json
import os

# 知识库路径
KB_PATH = "D:/EcWork/基于Claude的MODSDK开发工作流/.claude/knowledge-base.json"

# 自定义武器效果系统完整代码
CUSTOM_WEAPON_EFFECTS_CODE = '''# -*- coding: utf-8 -*-
from __future__ import print_function
from mod.server.system.serverSystem import ServerSystem
import mod.server.extraServerApi as serverApi

class CustomWeaponEffectsServerSystem(ServerSystem):
    """自定义武器效果系统"""

    def __init__(self, namespace, systemName):
        super(CustomWeaponEffectsServerSystem, self).__init__(namespace, systemName)

        # 武器效果配置表
        self.weapon_effects = {
            "minecraft:diamond_sword": {
                "particle": "minecraft:critical_hit_emitter",
                "damage_multiplier": 1.5,
                "effect": "minecraft:slowness",
                "effect_duration": 60,
                "effect_amplifier": 1
            },
            "minecraft:iron_axe": {
                "particle": "minecraft:heart_particle",
                "damage_multiplier": 1.2,
                "effect": "minecraft:weakness",
                "effect_duration": 40,
                "effect_amplifier": 0
            }
        }

        self.effect_comp = None
        self.particle_comp = None
        self.item_comp = None
        self.Create()

    def Create(self):
        """初始化组件和事件监听"""
        level_id = serverApi.GetLevelId()
        comp_factory = serverApi.GetEngineCompFactory()

        self.effect_comp = comp_factory.CreateEffect(level_id)
        self.particle_comp = comp_factory.CreateParticle(level_id)
        self.item_comp = comp_factory.CreateItem(level_id)

        # 监听实体伤害事件
        self.ListenForEvent(
            serverApi.GetEngineNamespace(),
            serverApi.GetEngineSystemName(),
            "ServerEntityDamageEvent",
            self,
            self.OnEntityDamage
        )

    def OnEntityDamage(self, args):
        """处理实体伤害事件 - 应用武器效果"""
        attacker_id = args.get("attackerId")
        victim_id = args.get("entityId")
        damage = args.get("damage", 0)

        if not attacker_id or not victim_id:
            return

        # 获取攻击者手持物品
        hand_item = self.item_comp.GetPlayerItem(
            serverApi.GetEngineNamespace(),
            attacker_id,
            serverApi.GetMinecraftEnum().ItemPosType.CARRIED,
            True
        )

        if not hand_item:
            return

        item_name = hand_item.get("itemName")

        # 检查武器是否有自定义效果
        if item_name not in self.weapon_effects:
            return

        effect_config = self.weapon_effects[item_name]

        # 应用伤害倍率
        if "damage_multiplier" in effect_config:
            multiplier = effect_config["damage_multiplier"]
            new_damage = damage * multiplier
            args["damage"] = new_damage
            print("[WeaponEffects] 应用伤害倍率: {} -> {}".format(damage, new_damage))

        # 施加状态效果
        if "effect" in effect_config:
            effect_name = effect_config["effect"]
            duration = effect_config.get("effect_duration", 60)
            amplifier = effect_config.get("effect_amplifier", 0)

            self.effect_comp.AddEffectToEntity(
                victim_id,
                effect_name,
                duration,
                amplifier,
                True
            )
            print("[WeaponEffects] 施加效果: {} -> {}".format(victim_id, effect_name))

        # 播放粒子特效
        if "particle" in effect_config:
            particle_name = effect_config["particle"]
            pos = serverApi.GetEngineCompFactory().CreatePos(level_id).GetFootPos(victim_id)

            if pos:
                self.particle_comp.CreateParticle(
                    particle_name,
                    pos
                )
                print("[WeaponEffects] 播放粒子: {}".format(particle_name))

    def Destroy(self):
        """系统销毁时清理"""
        self.UnListenAllEvents()
'''

# 自定义武器效果系统玩法包配置
CUSTOM_WEAPON_EFFECTS_PACK = {
    "id": "custom-weapon-effects",
    "name": "自定义武器效果系统",
    "keywords": [
        "武器", "效果", "伤害倍率", "状态效果", "粒子", "附魔",
        "weapon", "effect", "damage", "modifier", "particle", "enchant"
    ],
    "category": "战斗玩法",
    "difficulty": "中等",
    "estimated_time": "12分钟",

    "description": "为武器添加自定义效果,包括伤害倍率、状态效果施加、粒子特效播放等功能",

    "implementation_guide": {
        "principle": "服务端监听ServerEntityDamageEvent → 获取攻击者手持物品 → 根据物品ID查找效果配置 → 修改伤害值/施加状态效果/播放粒子",

        "modsdk_apis": [
            {
                "name": "ServerEntityDamageEvent",
                "type": "事件",
                "trigger": "实体受到伤害时触发",
                "fields": {
                    "attackerId": "攻击者ID (str)",
                    "entityId": "受害者ID (str)",
                    "damage": "伤害值 (float)",
                    "cause": "伤害来源 (str)"
                },
                "doc_path": "MODSDK/事件/实体.md",
                "common_pitfall": "修改damage字段需在事件处理中直接修改args字典"
            },
            {
                "name": "itemComp.GetPlayerItem",
                "type": "组件方法",
                "purpose": "获取玩家指定槽位的物品信息",
                "params": {
                    "namespace": "命名空间 (str)",
                    "playerId": "玩家ID (str)",
                    "slotType": "槽位类型枚举 (int)",
                    "getUserData": "是否获取用户数据 (bool)"
                },
                "doc_path": "MODSDK/Component/itemComp.md",
                "common_pitfall": "需要传入正确的ItemPosType枚举值"
            },
            {
                "name": "effectComp.AddEffectToEntity",
                "type": "组件方法",
                "purpose": "给实体添加状态效果",
                "params": {
                    "entityId": "实体ID (str)",
                    "effectName": "效果名称 (str)",
                    "duration": "持续时间(tick) (int)",
                    "amplifier": "效果等级 (int)",
                    "showParticles": "是否显示粒子 (bool)"
                },
                "doc_path": "MODSDK/Component/effectComp.md",
                "common_pitfall": "duration单位为tick(20tick=1秒)"
            },
            {
                "name": "particleComp.CreateParticle",
                "type": "组件方法",
                "purpose": "在指定位置创建粒子效果",
                "params": {
                    "particleName": "粒子名称 (str)",
                    "pos": "位置坐标 (tuple)"
                },
                "doc_path": "MODSDK/Component/particleComp.md",
                "common_pitfall": "粒子名称需使用完整identifier"
            }
        ],

        "complete_code": {
            "file": "mod/server/system/CustomWeaponEffectsServerSystem.py",
            "content": CUSTOM_WEAPON_EFFECTS_CODE
        },

        "config_guide": {
            "description": "在weapon_effects中配置武器效果",
            "example": {
                "minecraft:netherite_sword": {
                    "particle": "minecraft:flame_particle",
                    "damage_multiplier": 2.0,
                    "effect": "minecraft:wither",
                    "effect_duration": 100,
                    "effect_amplifier": 2
                }
            },
            "fields": {
                "particle": "粒子特效名称 (str,可选)",
                "damage_multiplier": "伤害倍率 (float,可选)",
                "effect": "状态效果名称 (str,可选)",
                "effect_duration": "效果持续时间/tick (int,可选)",
                "effect_amplifier": "效果等级 (int,可选)"
            }
        },

        "common_issues": [
            {
                "problem": "伤害倍率不生效",
                "cause": "未正确修改args['damage']字段",
                "solution": "确保直接修改事件参数字典中的damage值"
            },
            {
                "problem": "状态效果施加失败",
                "cause": "effectName拼写错误或不存在",
                "solution": "使用minecraft:前缀的完整效果名称"
            },
            {
                "problem": "粒子不显示",
                "cause": "粒子名称错误或坐标获取失败",
                "solution": "检查粒子identifier拼写;确保GetFootPos返回有效坐标"
            }
        ],

        "related_gameplay": [
            {
                "name": "击退眩晕机制系统",
                "similarity": "同样处理战斗伤害事件",
                "reusable_code": "DamageEvent处理框架"
            },
            {
                "name": "经验掉落系统",
                "similarity": "击杀后触发效果",
                "extension": "可扩展为击杀特效系统"
            }
        ]
    }
}

def main():
    # 读取现有知识库
    with open(KB_PATH, 'r', encoding='utf-8') as f:
        kb = json.load(f)

    # 检查是否已存在
    existing_ids = [p["id"] for p in kb["gameplay_patterns"]]
    if "custom-weapon-effects" in existing_ids:
        print("[SKIP] Custom Weapon Effects pack already exists")
        return

    # 添加新玩法包
    kb["gameplay_patterns"].append(CUSTOM_WEAPON_EFFECTS_PACK)

    # 更新元数据
    kb["metadata"]["total_patterns"] = len(kb["gameplay_patterns"])

    # 保存
    with open(KB_PATH, 'w', encoding='utf-8') as f:
        json.dump(kb, f, ensure_ascii=False, indent=2)

    print("[SUCCESS] Custom Weapon Effects gameplay pack added!")
    print(f"[INFO] Total patterns: {kb['metadata']['total_patterns']}")
    print(f"[INFO] Keywords: {', '.join(CUSTOM_WEAPON_EFFECTS_PACK['keywords'][:8])}")

if __name__ == "__main__":
    main()
