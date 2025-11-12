# -*- coding: utf-8 -*-
"""
添加粒子特效生成系统玩法包到知识库
"""
import json
import os

# 知识库路径
KB_PATH = "D:/EcWork/基于Claude的MODSDK开发工作流/.claude/knowledge-base.json"

# 粒子特效生成系统完整代码(精简版)
PARTICLE_EFFECT_CODE = '''# -*- coding: utf-8 -*-
from __future__ import print_function
from mod.server.system.serverSystem import ServerSystem
import mod.server.extraServerApi as serverApi
import math

class ParticleEffectServerSystem(ServerSystem):
    """粒子特效生成系统"""

    def __init__(self, namespace, systemName):
        super(ParticleEffectServerSystem, self).__init__(namespace, systemName)

        self.particle_comp = None
        self.pos_comp = None
        self.Create()

    def Create(self):
        """初始化组件"""
        level_id = serverApi.GetLevelId()
        comp_factory = serverApi.GetEngineCompFactory()

        self.particle_comp = comp_factory.CreateParticle(level_id)
        self.pos_comp = comp_factory.CreatePos(level_id)

    def CreateCircleParticles(self, center_pos, particle_name, radius=2.0, count=20):
        """创建圆形粒子特效"""
        for i in range(count):
            angle = (2 * math.pi / count) * i
            x = center_pos[0] + radius * math.cos(angle)
            y = center_pos[1]
            z = center_pos[2] + radius * math.sin(angle)

            self.particle_comp.CreateParticle(particle_name, (x, y, z))

    def CreateSpiralParticles(self, center_pos, particle_name, height=5.0, turns=3, count=50):
        """创建螺旋粒子特效"""
        for i in range(count):
            progress = float(i) / count
            angle = (2 * math.pi * turns) * progress
            radius = 1.0

            x = center_pos[0] + radius * math.cos(angle)
            y = center_pos[1] + height * progress
            z = center_pos[2] + radius * math.sin(angle)

            self.particle_comp.CreateParticle(particle_name, (x, y, z))

    def CreateExplosionParticles(self, center_pos, particle_name, count=30):
        """创建爆炸粒子特效"""
        import random
        for i in range(count):
            x = center_pos[0] + random.uniform(-2, 2)
            y = center_pos[1] + random.uniform(-2, 2)
            z = center_pos[2] + random.uniform(-2, 2)

            self.particle_comp.CreateParticle(particle_name, (x, y, z))

    def Destroy(self):
        """系统销毁时清理"""
        self.UnListenAllEvents()
'''

# 粒子特效生成系统玩法包配置
PARTICLE_EFFECT_PACK = {
    "id": "particle-effect-system",
    "name": "粒子特效生成系统",
    "keywords": [
        "粒子", "特效", "粒子效果", "圆形", "螺旋", "爆炸",
        "particle", "effect", "visual", "circle", "spiral", "explosion"
    ],
    "category": "世界玩法",
    "difficulty": "简单",
    "estimated_time": "10分钟",

    "description": "实现粒子特效生成系统,支持圆形、螺旋、爆炸等多种粒子特效模式",

    "implementation_guide": {
        "principle": "使用particleComp.CreateParticle在指定坐标生成粒子 → 通过数学计算(圆形、螺旋等)生成特效图案",

        "modsdk_apis": [
            {
                "name": "particleComp.CreateParticle",
                "type": "组件方法",
                "purpose": "在指定位置创建粒子效果",
                "params": {
                    "particleName": "粒子名称 (str)",
                    "pos": "位置坐标(x,y,z) (tuple)"
                },
                "doc_path": "MODSDK/Component/particleComp.md",
                "common_pitfall": "粒子名称需使用完整identifier;过多粒子会影响性能"
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
            }
        ],

        "complete_code": {
            "file": "mod/server/system/ParticleEffectServerSystem.py",
            "content": PARTICLE_EFFECT_CODE
        },

        "config_guide": {
            "description": "调用不同的粒子生成方法创建特效",
            "example": {
                "circle": "CreateCircleParticles((100, 64, 100), 'minecraft:heart_particle', 3.0, 30)",
                "spiral": "CreateSpiralParticles((100, 64, 100), 'minecraft:flame_particle', 10.0, 5, 100)",
                "explosion": "CreateExplosionParticles((100, 64, 100), 'minecraft:critical_hit_emitter', 50)"
            }
        },

        "common_issues": [
            {
                "problem": "粒子不显示",
                "cause": "粒子名称错误或坐标超出渲染范围",
                "solution": "使用minecraft:前缀的有效粒子名称;确保坐标在玩家视野范围内"
            },
            {
                "problem": "粒子卡顿",
                "cause": "一次生成粒子数量过多",
                "solution": "分批生成或减少粒子数量;避免在tick事件中频繁生成"
            }
        ],

        "related_gameplay": [
            {
                "name": "击退眩晕机制系统",
                "similarity": "粒子特效播放",
                "reusable_code": "粒子生成逻辑"
            },
            {
                "name": "自定义武器效果系统",
                "similarity": "战斗粒子特效",
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
    if "particle-effect-system" in existing_ids:
        print("[SKIP] Particle Effect System pack already exists")
        return

    # 添加新玩法包
    kb["gameplay_patterns"].append(PARTICLE_EFFECT_PACK)

    # 更新元数据
    kb["metadata"]["total_patterns"] = len(kb["gameplay_patterns"])

    # 保存
    with open(KB_PATH, 'w', encoding='utf-8') as f:
        json.dump(kb, f, ensure_ascii=False, indent=2)

    print("[SUCCESS] Particle Effect System gameplay pack added!")
    print(f"[INFO] Total patterns: {kb['metadata']['total_patterns']}")
    print(f"[INFO] Keywords: {', '.join(PARTICLE_EFFECT_PACK['keywords'][:8])}")

if __name__ == "__main__":
    main()
