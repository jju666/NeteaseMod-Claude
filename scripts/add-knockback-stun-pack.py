# -*- coding: utf-8 -*-
"""
添加击退眩晕机制系统玩法包到知识库
"""
import json
import os

# 知识库路径
KB_PATH = "D:/EcWork/基于Claude的MODSDK开发工作流/.claude/knowledge-base.json"

# 击退眩晕机制系统完整代码
KNOCKBACK_STUN_CODE = '''# -*- coding: utf-8 -*-
from __future__ import print_function
from mod.server.system.serverSystem import ServerSystem
import mod.server.extraServerApi as serverApi
import math

class KnockbackStunServerSystem(ServerSystem):
    """击退眩晕机制系统"""

    def __init__(self, namespace, systemName):
        super(KnockbackStunServerSystem, self).__init__(namespace, systemName)

        # 击退配置
        self.knockback_config = {
            "base_multiplier": 1.5,
            "vertical_boost": 0.3,
            "max_distance": 5.0
        }

        # 眩晕配置
        self.stun_config = {
            "duration": 40,  # 2秒
            "chance": 0.15,  # 15%概率
            "particle": "minecraft:villager_angry"
        }

        # 眩晕状态记录
        self.stunned_entities = {}

        self.motion_comp = None
        self.pos_comp = None
        self.effect_comp = None
        self.particle_comp = None
        self.Create()

    def Create(self):
        """初始化组件和事件监听"""
        level_id = serverApi.GetLevelId()
        comp_factory = serverApi.GetEngineCompFactory()

        self.motion_comp = comp_factory.CreateActorMotion(level_id)
        self.pos_comp = comp_factory.CreatePos(level_id)
        self.effect_comp = comp_factory.CreateEffect(level_id)
        self.particle_comp = comp_factory.CreateParticle(level_id)

        # 监听实体伤害事件
        self.ListenForEvent(
            serverApi.GetEngineNamespace(),
            serverApi.GetEngineSystemName(),
            "ServerEntityDamageEvent",
            self,
            self.OnEntityDamage
        )

        # 监听Tick事件处理眩晕状态
        self.ListenForEvent(
            serverApi.GetEngineNamespace(),
            serverApi.GetEngineSystemName(),
            "ServerPlayerTickEvent",
            self,
            self.OnPlayerTick
        )

    def OnEntityDamage(self, args):
        """处理实体伤害事件 - 应用击退和眩晕"""
        attacker_id = args.get("attackerId")
        victim_id = args.get("entityId")
        damage = args.get("damage", 0)

        if not attacker_id or not victim_id or damage <= 0:
            return

        # 应用击退效果
        self._ApplyKnockback(attacker_id, victim_id, damage)

        # 随机触发眩晕
        import random
        if random.random() < self.stun_config["chance"]:
            self._ApplyStun(victim_id)

    def _ApplyKnockback(self, attacker_id, victim_id, damage):
        """应用击退效果"""
        # 获取攻击者和受害者位置
        attacker_pos = self.pos_comp.GetFootPos(attacker_id)
        victim_pos = self.pos_comp.GetFootPos(victim_id)

        if not attacker_pos or not victim_pos:
            return

        # 计算击退方向向量
        dx = victim_pos[0] - attacker_pos[0]
        dz = victim_pos[2] - attacker_pos[2]
        distance = math.sqrt(dx * dx + dz * dz)

        if distance < 0.1:
            return

        # 归一化方向向量
        norm_x = dx / distance
        norm_z = dz / distance

        # 计算击退强度(基于伤害值)
        knockback_strength = min(
            damage * self.knockback_config["base_multiplier"],
            self.knockback_config["max_distance"]
        )

        # 设置实体运动向量
        motion = (
            norm_x * knockback_strength,
            self.knockback_config["vertical_boost"],
            norm_z * knockback_strength
        )

        self.motion_comp.SetMotion(victim_id, motion)
        print("[KnockbackStun] 击退: {} 强度: {}".format(victim_id, knockback_strength))

    def _ApplyStun(self, entity_id):
        """应用眩晕效果"""
        duration = self.stun_config["duration"]

        # 添加缓慢和挖掘疲劳效果模拟眩晕
        self.effect_comp.AddEffectToEntity(
            entity_id,
            "minecraft:slowness",
            duration,
            3,  # 等级4
            True
        )

        self.effect_comp.AddEffectToEntity(
            entity_id,
            "minecraft:mining_fatigue",
            duration,
            2,  # 等级3
            True
        )

        # 记录眩晕状态
        self.stunned_entities[entity_id] = duration

        # 播放眩晕粒子
        pos = self.pos_comp.GetFootPos(entity_id)
        if pos:
            head_pos = (pos[0], pos[1] + 2, pos[2])
            self.particle_comp.CreateParticle(
                self.stun_config["particle"],
                head_pos
            )

        print("[KnockbackStun] 眩晕触发: {} 持续: {}tick".format(entity_id, duration))

    def OnPlayerTick(self, args):
        """Tick事件 - 更新眩晕状态"""
        # 减少眩晕计时器
        expired = []
        for entity_id, remaining in self.stunned_entities.items():
            remaining -= 1
            if remaining <= 0:
                expired.append(entity_id)
            else:
                self.stunned_entities[entity_id] = remaining

                # 每10tick播放一次粒子
                if remaining % 10 == 0:
                    pos = self.pos_comp.GetFootPos(entity_id)
                    if pos:
                        head_pos = (pos[0], pos[1] + 2, pos[2])
                        self.particle_comp.CreateParticle(
                            self.stun_config["particle"],
                            head_pos
                        )

        # 移除过期眩晕
        for entity_id in expired:
            del self.stunned_entities[entity_id]
            print("[KnockbackStun] 眩晕结束: {}".format(entity_id))

    def Destroy(self):
        """系统销毁时清理"""
        self.UnListenAllEvents()
'''

# 击退眩晕机制系统玩法包配置
KNOCKBACK_STUN_PACK = {
    "id": "knockback-stun-system",
    "name": "击退眩晕机制系统",
    "keywords": [
        "击退", "眩晕", "控制", "运动", "矢量", "战斗机制",
        "knockback", "stun", "motion", "vector", "combat", "control"
    ],
    "category": "战斗玩法",
    "difficulty": "中等",
    "estimated_time": "15分钟",

    "description": "实现战斗中的击退和眩晕机制,包括基于伤害的击退强度计算、随机眩晕触发、眩晕状态管理等功能",

    "implementation_guide": {
        "principle": "服务端监听ServerEntityDamageEvent → 计算攻击者和受害者位置的方向向量 → 应用击退运动 → 随机判断眩晕触发 → 施加状态效果+粒子 → Tick事件管理眩晕计时器",

        "modsdk_apis": [
            {
                "name": "actorMotionComp.SetMotion",
                "type": "组件方法",
                "purpose": "设置实体运动向量",
                "params": {
                    "entityId": "实体ID (str)",
                    "motion": "运动向量(x,y,z) (tuple)"
                },
                "doc_path": "MODSDK/Component/actorMotionComp.md",
                "common_pitfall": "运动向量单位为方块/tick,过大会导致实体穿墙"
            },
            {
                "name": "posComp.GetFootPos",
                "type": "组件方法",
                "purpose": "获取实体脚部位置坐标",
                "params": {
                    "entityId": "实体ID (str)"
                },
                "returns": "(x, y, z) tuple or None",
                "doc_path": "MODSDK/Component/posComp.md",
                "common_pitfall": "返回可能为None,需判空"
            },
            {
                "name": "effectComp.AddEffectToEntity",
                "type": "组件方法",
                "purpose": "给实体添加状态效果",
                "params": {
                    "entityId": "实体ID (str)",
                    "effectName": "效果名称 (str)",
                    "duration": "持续时间/tick (int)",
                    "amplifier": "效果等级 (int)",
                    "showParticles": "是否显示粒子 (bool)"
                },
                "doc_path": "MODSDK/Component/effectComp.md",
                "common_pitfall": "amplifier从0开始(0=等级1)"
            },
            {
                "name": "ServerPlayerTickEvent",
                "type": "事件",
                "trigger": "每tick触发一次(服务端)",
                "fields": {
                    "playerId": "玩家ID (str)"
                },
                "doc_path": "MODSDK/事件/玩家.md",
                "common_pitfall": "高频事件,避免复杂计算影响性能"
            }
        ],

        "complete_code": {
            "file": "mod/server/system/KnockbackStunServerSystem.py",
            "content": KNOCKBACK_STUN_CODE
        },

        "config_guide": {
            "description": "配置击退和眩晕参数",
            "example": {
                "knockback_config": {
                    "base_multiplier": 2.0,
                    "vertical_boost": 0.5,
                    "max_distance": 8.0
                },
                "stun_config": {
                    "duration": 60,
                    "chance": 0.25,
                    "particle": "minecraft:critical_hit_emitter"
                }
            },
            "fields": {
                "base_multiplier": "击退强度基础倍率 (float)",
                "vertical_boost": "垂直击退强度 (float)",
                "max_distance": "最大击退距离 (float)",
                "duration": "眩晕持续时间/tick (int)",
                "chance": "眩晕触发概率 (float,0-1)",
                "particle": "眩晕粒子特效名称 (str)"
            }
        },

        "common_issues": [
            {
                "problem": "击退方向错误",
                "cause": "方向向量计算错误或未归一化",
                "solution": "确保使用受害者坐标减去攻击者坐标,并归一化"
            },
            {
                "problem": "击退过强导致穿墙",
                "cause": "击退强度过大",
                "solution": "设置max_distance限制最大击退距离"
            },
            {
                "problem": "眩晕粒子不显示",
                "cause": "粒子坐标计算错误",
                "solution": "确保粒子生成在实体头部位置(y+2)"
            }
        ],

        "related_gameplay": [
            {
                "name": "自定义武器效果系统",
                "similarity": "同样处理伤害事件添加效果",
                "reusable_code": "DamageEvent处理框架"
            },
            {
                "name": "粒子特效生成系统",
                "similarity": "粒子效果播放",
                "extension": "可扩展为技能特效系统"
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
    if "knockback-stun-system" in existing_ids:
        print("[SKIP] Knockback Stun System pack already exists")
        return

    # 添加新玩法包
    kb["gameplay_patterns"].append(KNOCKBACK_STUN_PACK)

    # 更新元数据
    kb["metadata"]["total_patterns"] = len(kb["gameplay_patterns"])

    # 保存
    with open(KB_PATH, 'w', encoding='utf-8') as f:
        json.dump(kb, f, ensure_ascii=False, indent=2)

    print("[SUCCESS] Knockback Stun System gameplay pack added!")
    print(f"[INFO] Total patterns: {kb['metadata']['total_patterns']}")
    print(f"[INFO] Keywords: {', '.join(KNOCKBACK_STUN_PACK['keywords'][:8])}")

if __name__ == "__main__":
    main()
