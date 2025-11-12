# -*- coding: utf-8 -*-
"""
添加经验掉落系统玩法包到知识库
"""
import json
import os

# 知识库路径
KB_PATH = "D:/EcWork/基于Claude的MODSDK开发工作流/.claude/knowledge-base.json"

# 经验掉落系统完整代码
EXPERIENCE_DROP_CODE = '''# -*- coding: utf-8 -*-
from __future__ import print_function
from mod.server.system.serverSystem import ServerSystem
import mod.server.extraServerApi as serverApi

class ExperienceDropServerSystem(ServerSystem):
    """经验掉落系统"""

    def __init__(self, namespace, systemName):
        super(ExperienceDropServerSystem, self).__init__(namespace, systemName)

        # 经验掉落配置表
        self.exp_config = {
            "minecraft:zombie": {
                "base_exp": 5,
                "bonus_exp": 10,
                "bonus_chance": 0.2
            },
            "minecraft:skeleton": {
                "base_exp": 5,
                "bonus_exp": 15,
                "bonus_chance": 0.15
            },
            "minecraft:ender_dragon": {
                "base_exp": 12000,
                "bonus_exp": 5000,
                "bonus_chance": 0.5
            },
            "minecraft:wither": {
                "base_exp": 5000,
                "bonus_exp": 2000,
                "bonus_chance": 0.3
            }
        }

        # 玩家击杀统计
        self.kill_stats = {}

        self.exp_comp = None
        self.msg_comp = None
        self.extra_data_comp = None
        self.Create()

    def Create(self):
        """初始化组件和事件监听"""
        level_id = serverApi.GetLevelId()
        comp_factory = serverApi.GetEngineCompFactory()

        self.exp_comp = comp_factory.CreateExp(level_id)
        self.msg_comp = comp_factory.CreateMsg(level_id)
        self.extra_data_comp = comp_factory.CreateExtraData(level_id)

        # 监听实体死亡事件
        self.ListenForEvent(
            serverApi.GetEngineNamespace(),
            serverApi.GetEngineSystemName(),
            "EntityDieEvent",
            self,
            self.OnEntityDie
        )

        # 监听玩家加入事件
        self.ListenForEvent(
            serverApi.GetEngineNamespace(),
            serverApi.GetEngineSystemName(),
            "AddServerPlayerEvent",
            self,
            self.OnPlayerJoin
        )

    def OnPlayerJoin(self, args):
        """玩家加入时加载击杀统计"""
        player_id = args["id"]
        stats_str = self.extra_data_comp.GetExtraData(player_id, "kill_stats")

        if stats_str:
            import json
            self.kill_stats[player_id] = json.loads(stats_str)
        else:
            self.kill_stats[player_id] = {}

    def OnEntityDie(self, args):
        """处理实体死亡事件 - 掉落经验"""
        entity_id = args.get("id")
        attacker_id = args.get("attacker")

        if not entity_id or not attacker_id:
            return

        # 获取实体类型
        entity_comp = serverApi.GetEngineCompFactory().CreateEngineType(serverApi.GetLevelId())
        entity_type = entity_comp.GetEngineTypeStr(entity_id)

        if not entity_type or entity_type not in self.exp_config:
            return

        config = self.exp_config[entity_type]

        # 计算经验值
        base_exp = config["base_exp"]
        bonus_exp = config.get("bonus_exp", 0)
        bonus_chance = config.get("bonus_chance", 0)

        import random
        total_exp = base_exp
        bonus_triggered = False

        if bonus_chance > 0 and random.random() < bonus_chance:
            total_exp += bonus_exp
            bonus_triggered = True

        # 给予经验
        self.exp_comp.AddPlayerExp(attacker_id, total_exp)

        # 更新击杀统计
        if attacker_id not in self.kill_stats:
            self.kill_stats[attacker_id] = {}

        if entity_type not in self.kill_stats[attacker_id]:
            self.kill_stats[attacker_id][entity_type] = 0

        self.kill_stats[attacker_id][entity_type] += 1

        # 保存统计
        import json
        self.extra_data_comp.SetExtraData(
            attacker_id,
            "kill_stats",
            json.dumps(self.kill_stats[attacker_id])
        )

        # 发送消息提示
        msg = "§e+{} 经验".format(total_exp)
        if bonus_triggered:
            msg += " §6(暴击!)§r"

        self.msg_comp.NotifyOneMessage(attacker_id, msg, "§a经验")

        print("[ExpDrop] {} 击杀 {} 获得 {} 经验 (bonus: {})".format(
            attacker_id, entity_type, total_exp, bonus_triggered
        ))

    def GetPlayerKillStats(self, player_id):
        """获取玩家击杀统计"""
        return self.kill_stats.get(player_id, {})

    def Destroy(self):
        """系统销毁时清理"""
        self.UnListenAllEvents()
'''

# 经验掉落系统玩法包配置
EXPERIENCE_DROP_PACK = {
    "id": "experience-drop-system",
    "name": "经验掉落系统",
    "keywords": [
        "经验", "掉落", "击杀", "经验值", "升级", "奖励",
        "exp", "experience", "drop", "kill", "reward", "level"
    ],
    "category": "战斗玩法",
    "difficulty": "简单",
    "estimated_time": "10分钟",

    "description": "实现实体击杀掉落经验的系统,支持基础经验、暴击加成、击杀统计等功能",

    "implementation_guide": {
        "principle": "服务端监听EntityDieEvent → 获取击杀者和被击杀实体类型 → 根据配置表计算经验值 → 随机判断暴击加成 → 调用AddPlayerExp给予经验 → 记录击杀统计到ExtraData",

        "modsdk_apis": [
            {
                "name": "EntityDieEvent",
                "type": "事件",
                "trigger": "实体死亡时触发",
                "fields": {
                    "id": "死亡实体ID (str)",
                    "attacker": "击杀者ID (str)"
                },
                "doc_path": "MODSDK/事件/实体.md",
                "common_pitfall": "attacker可能为None(自然死亡),需判空"
            },
            {
                "name": "expComp.AddPlayerExp",
                "type": "组件方法",
                "purpose": "给玩家添加经验值",
                "params": {
                    "playerId": "玩家ID (str)",
                    "exp": "经验值 (int)"
                },
                "doc_path": "MODSDK/Component/expComp.md",
                "common_pitfall": "经验值为负数会扣除经验"
            },
            {
                "name": "engineTypeComp.GetEngineTypeStr",
                "type": "组件方法",
                "purpose": "获取实体类型标识符",
                "params": {
                    "entityId": "实体ID (str)"
                },
                "returns": "实体类型字符串 (str)",
                "doc_path": "MODSDK/Component/engineTypeComp.md",
                "common_pitfall": "返回值可能为None,需判空"
            },
            {
                "name": "extraDataComp.SetExtraData / GetExtraData",
                "type": "组件方法",
                "purpose": "数据持久化存储",
                "params": {
                    "entityId": "实体ID (str)",
                    "key": "数据键名 (str)",
                    "value": "数据值 (str,需转换)"
                },
                "doc_path": "MODSDK/Component/extraDataComp.md",
                "common_pitfall": "仅支持字符串,需json.dumps/loads转换"
            }
        ],

        "complete_code": {
            "file": "mod/server/system/ExperienceDropServerSystem.py",
            "content": EXPERIENCE_DROP_CODE
        },

        "config_guide": {
            "description": "在exp_config中配置不同实体的经验掉落",
            "example": {
                "minecraft:creeper": {
                    "base_exp": 8,
                    "bonus_exp": 20,
                    "bonus_chance": 0.25
                }
            },
            "fields": {
                "base_exp": "基础经验值 (int)",
                "bonus_exp": "暴击额外经验 (int,可选)",
                "bonus_chance": "暴击触发概率 (float,0-1,可选)"
            }
        },

        "common_issues": [
            {
                "problem": "经验不掉落",
                "cause": "实体类型未在exp_config中配置",
                "solution": "添加对应实体类型到配置表"
            },
            {
                "problem": "击杀统计丢失",
                "cause": "SetExtraData调用失败或时机错误",
                "solution": "确保在每次击杀后立即保存统计数据"
            },
            {
                "problem": "暴击不触发",
                "cause": "random.random()使用错误",
                "solution": "确保导入random模块并正确使用"
            }
        ],

        "related_gameplay": [
            {
                "name": "击杀掉落系统",
                "similarity": "同样监听EntityDieEvent",
                "reusable_code": "实体死亡事件处理框架"
            },
            {
                "name": "排行榜系统",
                "similarity": "击杀统计数据",
                "extension": "可扩展为击杀排行榜"
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
    if "experience-drop-system" in existing_ids:
        print("[SKIP] Experience Drop System pack already exists")
        return

    # 添加新玩法包
    kb["gameplay_patterns"].append(EXPERIENCE_DROP_PACK)

    # 更新元数据
    kb["metadata"]["total_patterns"] = len(kb["gameplay_patterns"])

    # 保存
    with open(KB_PATH, 'w', encoding='utf-8') as f:
        json.dump(kb, f, ensure_ascii=False, indent=2)

    print("[SUCCESS] Experience Drop System gameplay pack added!")
    print(f"[INFO] Total patterns: {kb['metadata']['total_patterns']}")
    print(f"[INFO] Keywords: {', '.join(EXPERIENCE_DROP_PACK['keywords'][:8])}")

if __name__ == "__main__":
    main()
