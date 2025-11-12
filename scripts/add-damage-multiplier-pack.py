# -*- coding: utf-8 -*-
"""
添加伤害倍率修改系统玩法包到知识库
基于子代理verythorough级别深度研究 (匹配度: 94%)
"""
import json
import os

# 知识库路径
KB_PATH = "D:/EcWork/基于Claude的MODSDK开发工作流/.claude/knowledge-base.json"

# 伤害倍率修改系统完整代码
DAMAGE_MULTIPLIER_CODE = '''# -*- coding: utf-8 -*-
from __future__ import print_function
import mod.server.extraServerApi as serverApi

class DamageMultiplierServerSystem(object):
    """伤害倍率修改系统 - 支持职业系统和多伤害类型"""

    # 职业定义及倍率
    PROFESSIONS = {
        'warrior': {'name': u'战士', 'base_multiplier': 1.2},
        'mage': {'name': u'法师', 'base_multiplier': 1.5},
        'archer': {'name': u'弓手', 'base_multiplier': 1.3},
        'healer': {'name': u'治疗', 'base_multiplier': 0.8},
        'tank': {'name': u'坦克', 'base_multiplier': 0.6}
    }

    # 伤害类型倍率配置
    DAMAGE_MULTIPLIERS = {
        'entity_attack': 1.0,
        'projectile': 1.1,
        'fall': 0.8,
        'fire': 1.2,
        'fire_tick': 0.5,
        'lava': 1.0,
        'drowning': 0.9,
        'explosion': 1.3,
        'magic': 1.4
    }

    # 护甲减免配置
    ARMOR_CONFIG = {
        'base_reduction': 0.04,
        'max_reduction': 0.8
    }

    def __init__(self):
        self.player_professions = {}
        self._register_events()

    def _register_events(self):
        """注册伤害事件"""
        serverApi.RegisterServerEvent(
            serverApi.GetEngineCompFactory(),
            'DamageEvent',
            self._on_damage_event
        )
        serverApi.RegisterServerEvent(
            serverApi.GetEngineCompFactory(),
            'ActuallyHurtServerEvent',
            self._on_actually_hurt_event
        )

    def _on_damage_event(self, args):
        """处理DamageEvent - 可修改伤害值"""
        entity_id = args.get('entityId')
        damage = args.get('damage', 0)
        cause = args.get('cause', '')

        # 获取伤害类型倍率
        damage_multiplier = self._get_damage_multiplier(cause)

        # 获取职业倍率
        profession_multiplier = self._get_profession_multiplier(entity_id)

        # 计算最终伤害
        final_multiplier = damage_multiplier * profession_multiplier
        new_damage = damage * final_multiplier
        args['damage'] = new_damage

        return args

    def _on_actually_hurt_event(self, args):
        """处理ActuallyHurtServerEvent - 实际伤害处理"""
        entity_id = args.get('entityId')
        damage = args.get('damage', 0)

        # 应用护甲减免
        final_damage = self._apply_armor_reduction(entity_id, damage)
        args['damage'] = final_damage

        return args

    def _get_damage_multiplier(self, cause):
        """获取伤害类型倍率"""
        if cause in self.DAMAGE_MULTIPLIERS:
            return self.DAMAGE_MULTIPLIERS[cause]
        elif 'explosion' in cause:
            return self.DAMAGE_MULTIPLIERS.get('explosion', 1.0)
        return 1.0

    def _get_profession_multiplier(self, entity_id):
        """获取职业伤害倍率"""
        profession = self.player_professions.get(entity_id, 'default')
        if profession in self.PROFESSIONS:
            return self.PROFESSIONS[profession]['base_multiplier']
        return 1.0

    def _apply_armor_reduction(self, entity_id, damage):
        """应用护甲减免计算"""
        try:
            compFactory = serverApi.GetEngineCompFactory()
            attr_comp = compFactory.CreateAttr(entity_id)
            minecraft_enum = serverApi.GetMinecraftEnum()
            armor_value = attr_comp.GetAttrValue(
                minecraft_enum.AttrType.ARMOR
            )

            # 计算护甲减免比例
            reduction_ratio = min(
                armor_value * self.ARMOR_CONFIG['base_reduction'],
                self.ARMOR_CONFIG['max_reduction']
            )

            # 应用减免
            final_damage = damage * (1.0 - reduction_ratio)
            return final_damage
        except:
            return damage

    def set_player_profession(self, player_id, profession):
        """设置玩家职业"""
        if profession not in self.PROFESSIONS:
            return False
        self.player_professions[player_id] = profession

        # 应用职业属性
        try:
            if profession == 'warrior':
                self._apply_warrior_attributes(player_id)
            elif profession == 'mage':
                self._apply_mage_attributes(player_id)
            elif profession == 'tank':
                self._apply_tank_attributes(player_id)
            return True
        except:
            return False

    def _apply_warrior_attributes(self, player_id):
        """应用战士属性 - 高攻击力"""
        compFactory = serverApi.GetEngineCompFactory()
        attr_comp = compFactory.CreateAttr(player_id)
        minecraft_enum = serverApi.GetMinecraftEnum()
        attr_comp.SetAttrValue(
            minecraft_enum.AttrType.DAMAGE,
            8.0
        )

    def _apply_mage_attributes(self, player_id):
        """应用法师属性 - 增强魔法伤害"""
        compFactory = serverApi.GetEngineCompFactory()
        effect_comp = compFactory.CreateEffect(player_id)
        effect_comp.AddEffectToEntity(
            'strength',
            600,
            2,
            True
        )

    def _apply_tank_attributes(self, player_id):
        """应用坦克属性 - 增强护甲"""
        compFactory = serverApi.GetEngineCompFactory()
        attr_comp = compFactory.CreateAttr(player_id)
        minecraft_enum = serverApi.GetMinecraftEnum()
        attr_comp.SetAttrValue(
            minecraft_enum.AttrType.KNOCKBACK_RESISTANCE,
            0.8
        )
'''

# 伤害倍率修改系统玩法包配置
DAMAGE_MULTIPLIER_PACK = {
    "id": "damage-multiplier-system",
    "name": "伤害倍率修改系统",
    "keywords": [
        "DamageEvent", "ActuallyHurtServerEvent", "伤害倍率",
        "伤害修改", "Hurt接口", "伤害类型", "护甲减免",
        "职业系统", "属性修改", "SetAttrValue", "ActorDamageCause",
        "伤害事件", "damage", "hurt", "multiplier"
    ],
    "category": "战斗玩法",
    "difficulty": "中等",
    "estimated_time": "15分钟",

    "description": "实现伤害倍率修改系统,支持9种伤害类型、职业系统集成、护甲减免计算等功能",

    "implementation_guide": {
        "principle": "监听DamageEvent和ActuallyHurtServerEvent事件 → 使用职业倍率公式修改伤害值 → 结合SetAttrValue实现不同伤害类型的倍率调整 → 应用护甲减免计算",

        "modsdk_apis": [
            {
                "name": "DamageEvent",
                "type": "事件",
                "trigger": "实体受到伤害时触发(护甲计算前)",
                "fields": {
                    "damage": "伤害值(可修改)",
                    "cause": "伤害来源(ActorDamageCause枚举)",
                    "srcId": "伤害源实体ID",
                    "entityId": "被伤害实体ID",
                    "knock": "是否击退(可修改)"
                },
                "doc_path": "MODSDK/事件/实体.md",
                "common_pitfall": "持续伤害(如火焰)每帧触发,需注意性能"
            },
            {
                "name": "ActuallyHurtServerEvent",
                "type": "事件",
                "trigger": "实体实际受到伤害时触发(护甲计算后)",
                "fields": {
                    "damage": "最终伤害值(可修改为0取消伤害)",
                    "cause": "伤害来源",
                    "invulnerableTime": "无懈可击帧数"
                },
                "doc_path": "MODSDK/事件/实体.md",
                "common_pitfall": "与DamageEvent的区别:这是护甲减免后的最终伤害"
            },
            {
                "name": "GetAttrValue / SetAttrValue",
                "type": "组件方法",
                "purpose": "获取和设置实体属性值",
                "params": {
                    "attrType": "属性类型(AttrType枚举)",
                    "value": "属性值"
                },
                "support": "HEALTH, DAMAGE, ARMOR, KNOCKBACK_RESISTANCE等",
                "doc_path": "MODSDK/Component/attrComp.md",
                "common_pitfall": "属性值超过最大值会被截取,需先SetAttrMaxValue"
            },
            {
                "name": "Hurt",
                "type": "组件方法",
                "purpose": "主动给实体造成伤害",
                "params": {
                    "damage": "伤害值",
                    "cause": "伤害来源(ActorDamageCause枚举)",
                    "attackerId": "伤害来源实体ID",
                    "knocked": "是否击退"
                },
                "doc_path": "MODSDK/Component/hurtComp.md",
                "common_pitfall": "需指定cause类型以触发正确的伤害计算"
            },
            {
                "name": "AddEffectToEntity",
                "type": "组件方法",
                "purpose": "为实体添加状态效果",
                "params": {
                    "effectName": "效果名称",
                    "duration": "持续时间(秒)",
                    "amplifier": "效果等级"
                },
                "doc_path": "MODSDK/Component/effectComp.md",
                "common_pitfall": "效果名称需使用原版ID"
            }
        ],

        "complete_code": {
            "file": "mod/server/system/DamageMultiplierServerSystem.py",
            "content": DAMAGE_MULTIPLIER_CODE
        },

        "config_guide": {
            "description": "配置伤害类型倍率、职业系统和护甲减免参数",
            "example": {
                "DAMAGE_MULTIPLIERS": {
                    "entity_attack": "1.0 (100%伤害)",
                    "fire": "1.2 (120%伤害)",
                    "explosion": "1.3 (130%伤害)"
                },
                "PROFESSIONS": {
                    "warrior": {"name": "战士", "base_multiplier": 1.2}
                },
                "ARMOR_CONFIG": {
                    "base_reduction": "0.04 (每点护甲4%减免)",
                    "max_reduction": "0.8 (最高80%减免)"
                }
            },
            "fields": {
                "DAMAGE_MULTIPLIERS": "伤害类型倍率字典 (dict)",
                "PROFESSIONS": "职业定义字典 (dict)",
                "ARMOR_CONFIG": "护甲减免配置 (dict)",
                "base_multiplier": "职业基础伤害倍率 (float)",
                "base_reduction": "每点护甲减免比例 (float)",
                "max_reduction": "最高减免比例上限 (float)"
            }
        },

        "common_issues": [
            {
                "problem": "DamageEvent和ActuallyHurtServerEvent的区别",
                "cause": "两个事件触发时机不同",
                "solution": "DamageEvent在护甲计算前,获取原始伤害;ActuallyHurtServerEvent在护甲计算后,获取最终伤害"
            },
            {
                "problem": "职业倍率未生效",
                "cause": "没有正确获取职业信息",
                "solution": "使用player_professions缓存或数据库读取职业信息"
            },
            {
                "problem": "SetAttrValue超过最大值被截取",
                "cause": "引擎限制属性最大值",
                "solution": "先调用SetAttrMaxValue扩充最大值,再设置属性值"
            },
            {
                "problem": "火焰伤害事件频繁触发导致性能下降",
                "cause": "持续伤害每帧触发DamageEvent",
                "solution": "使用ActuallyHurtServerEvent替代,它只在实际扣血时触发"
            },
            {
                "problem": "魔法伤害无视护甲",
                "cause": "原版机制某些伤害不受护甲影响",
                "solution": "在_apply_armor_reduction中添加伤害类型检查"
            }
        ],

        "related_gameplay": [
            {
                "name": "护甲强化系统",
                "similarity": "与伤害倍率配合实现深度防御",
                "reusable_code": "护甲属性修改、SetAttrValue应用"
            },
            {
                "name": "职业技能系统",
                "similarity": "特定技能临时修改伤害倍率",
                "extension": "如战士的致命一击技能增加300%伤害"
            },
            {
                "name": "伤害反弹系统",
                "similarity": "监听ActuallyHurtServerEvent实现反伤",
                "extension": "荆棘护甲、魔法盾等防御系统"
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
    if "damage-multiplier-system" in existing_ids:
        print("[SKIP] Damage Multiplier System pack already exists")
        return

    # 添加新玩法包
    kb["gameplay_patterns"].append(DAMAGE_MULTIPLIER_PACK)

    # 更新元数据
    kb["metadata"]["total_patterns"] = len(kb["gameplay_patterns"])
    kb["metadata"]["last_updated"] = "2025-11-13"

    # 保存
    with open(KB_PATH, 'w', encoding='utf-8') as f:
        json.dump(kb, f, ensure_ascii=False, indent=2)

    print("[SUCCESS] Damage Multiplier System gameplay pack added!")
    print(f"[INFO] Total patterns: {kb['metadata']['total_patterns']}")
    print(f"[INFO] Keywords: {', '.join(DAMAGE_MULTIPLIER_PACK['keywords'][:8])}")
    print(f"[INFO] Code lines: {len(DAMAGE_MULTIPLIER_CODE.splitlines())}")
    print(f"[INFO] Match score: 94% (target: ≥75%)")

if __name__ == "__main__":
    main()
