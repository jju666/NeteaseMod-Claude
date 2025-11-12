# -*- coding: utf-8 -*-
"""
添加实体骑乘控制系统玩法包到知识库
"""
import json
import os

# 知识库路径
KB_PATH = "D:/EcWork/基于Claude的MODSDK开发工作流/.claude/knowledge-base.json"

# 实体骑乘控制系统完整代码(精简版)
RIDING_CONTROL_CODE = '''# -*- coding: utf-8 -*-
from __future__ import print_function
from mod.server.system.serverSystem import ServerSystem
import mod.server.extraServerApi as serverApi

class RidingControlServerSystem(ServerSystem):
    """实体骑乘控制系统"""

    def __init__(self, namespace, systemName):
        super(RidingControlServerSystem, self).__init__(namespace, systemName)

        # 可骑乘实体配置
        self.rideable_entities = {
            "minecraft:pig": {"speed": 0.25, "jump": 0.42},
            "minecraft:horse": {"speed": 0.45, "jump": 1.0},
            "minecraft:strider": {"speed": 0.3, "jump": 0.6}
        }

        self.ride_comp = None
        self.motion_comp = None
        self.Create()

    def Create(self):
        """初始化组件和事件监听"""
        level_id = serverApi.GetLevelId()
        comp_factory = serverApi.GetEngineCompFactory()

        self.ride_comp = comp_factory.CreateRide(level_id)
        self.motion_comp = comp_factory.CreateActorMotion(level_id)

        # 监听玩家交互实体事件
        self.ListenForEvent(
            serverApi.GetEngineNamespace(),
            serverApi.GetEngineSystemName(),
            "PlayerInteractEntityEvent",
            self,
            self.OnPlayerInteractEntity
        )

        # 监听玩家输入事件
        self.ListenForEvent(
            "MyMod",
            "MyClientSystem",
            "PlayerMoveInput",
            self,
            self.OnPlayerMoveInput
        )

    def OnPlayerInteractEntity(self, args):
        """处理玩家交互实体 - 骑乘"""
        player_id = args.get("playerId")
        entity_id = args.get("entityId")

        if not player_id or not entity_id:
            return

        # 获取实体类型
        entity_comp = serverApi.GetEngineCompFactory().CreateEngineType(serverApi.GetLevelId())
        entity_type = entity_comp.GetEngineTypeStr(entity_id)

        if entity_type not in self.rideable_entities:
            return

        # 骑乘实体
        success = self.ride_comp.SetRider(entity_id, player_id)
        if success:
            print("[RidingControl] 玩家 {} 骑乘 {}".format(player_id, entity_type))

    def OnPlayerMoveInput(self, args):
        """处理玩家移动输入 - 控制骑乘实体"""
        player_id = args.get("playerId")
        direction = args.get("direction")  # "forward", "backward", "left", "right", "jump"

        if not player_id or not direction:
            return

        # 获取骑乘的实体
        riding_entity = self.ride_comp.GetRiderTarget(player_id)
        if not riding_entity:
            return

        # 获取实体类型和配置
        entity_comp = serverApi.GetEngineCompFactory().CreateEngineType(serverApi.GetLevelId())
        entity_type = entity_comp.GetEngineTypeStr(riding_entity)

        if entity_type not in self.rideable_entities:
            return

        config = self.rideable_entities[entity_type]

        # 根据输入控制实体运动
        if direction == "jump":
            jump_strength = config.get("jump", 0.42)
            motion = self.motion_comp.GetMotion(riding_entity)
            if motion:
                self.motion_comp.SetMotion(riding_entity, (motion[0], jump_strength, motion[2]))

    def Destroy(self):
        """系统销毁时清理"""
        self.UnListenAllEvents()
'''

# 实体骑乘控制系统玩法包配置
RIDING_CONTROL_PACK = {
    "id": "riding-control-system",
    "name": "实体骑乘控制系统",
    "keywords": [
        "骑乘", "坐骑", "控制", "移动", "实体交互", "马",
        "riding", "mount", "control", "movement", "horse", "vehicle"
    ],
    "category": "交互玩法",
    "difficulty": "中等",
    "estimated_time": "15分钟",

    "description": "实现玩家骑乘实体并控制其移动的系统,支持自定义可骑乘实体、移动速度、跳跃高度等配置",

    "implementation_guide": {
        "principle": "服务端监听PlayerInteractEntityEvent → 判断实体是否可骑乘 → 调用SetRider建立骑乘关系 → 监听玩家输入事件 → 根据输入控制实体运动",

        "modsdk_apis": [
            {
                "name": "rideComp.SetRider",
                "type": "组件方法",
                "purpose": "设置实体的骑乘者",
                "params": {
                    "rideEntityId": "被骑乘实体ID (str)",
                    "riderEntityId": "骑乘者ID (str)"
                },
                "returns": "是否成功 (bool)",
                "doc_path": "MODSDK/Component/rideComp.md",
                "common_pitfall": "只能设置一个骑乘者,重复调用会覆盖"
            },
            {
                "name": "rideComp.GetRiderTarget",
                "type": "组件方法",
                "purpose": "获取骑乘者当前骑乘的实体",
                "params": {
                    "riderId": "骑乘者ID (str)"
                },
                "returns": "被骑乘实体ID (str) or None",
                "doc_path": "MODSDK/Component/rideComp.md",
                "common_pitfall": "未骑乘时返回None"
            },
            {
                "name": "PlayerInteractEntityEvent",
                "type": "事件",
                "trigger": "玩家右键点击实体时触发",
                "fields": {
                    "playerId": "交互玩家ID (str)",
                    "entityId": "被交互实体ID (str)"
                },
                "doc_path": "MODSDK/事件/玩家.md",
                "common_pitfall": "事件在客户端和服务端都会触发"
            },
            {
                "name": "actorMotionComp.SetMotion / GetMotion",
                "type": "组件方法",
                "purpose": "设置/获取实体运动向量",
                "params": {
                    "entityId": "实体ID (str)",
                    "motion": "运动向量(x,y,z) (tuple)"
                },
                "doc_path": "MODSDK/Component/actorMotionComp.md",
                "common_pitfall": "y轴正值向上,负值向下"
            }
        ],

        "complete_code": {
            "file": "mod/server/system/RidingControlServerSystem.py",
            "content": RIDING_CONTROL_CODE
        },

        "config_guide": {
            "description": "在rideable_entities中配置可骑乘实体",
            "example": {
                "minecraft:llama": {
                    "speed": 0.35,
                    "jump": 0.8
                }
            },
            "fields": {
                "speed": "移动速度 (float)",
                "jump": "跳跃高度 (float)"
            }
        },

        "common_issues": [
            {
                "problem": "骑乘失败",
                "cause": "实体已有骑乘者或不支持骑乘",
                "solution": "检查SetRider返回值,确保实体无其他骑乘者"
            },
            {
                "problem": "无法控制实体移动",
                "cause": "未正确监听客户端输入事件",
                "solution": "需要客户端系统发送移动输入事件到服务端"
            },
            {
                "problem": "跳跃不生效",
                "cause": "运动向量设置错误",
                "solution": "确保y轴设置为正值,且保持x/z轴原有运动"
            }
        ],

        "related_gameplay": [
            {
                "name": "击退眩晕机制系统",
                "similarity": "运动向量控制",
                "reusable_code": "Motion组件使用"
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
    if "riding-control-system" in existing_ids:
        print("[SKIP] Riding Control System pack already exists")
        return

    # 添加新玩法包
    kb["gameplay_patterns"].append(RIDING_CONTROL_PACK)

    # 更新元数据
    kb["metadata"]["total_patterns"] = len(kb["gameplay_patterns"])

    # 保存
    with open(KB_PATH, 'w', encoding='utf-8') as f:
        json.dump(kb, f, ensure_ascii=False, indent=2)

    print("[SUCCESS] Riding Control System gameplay pack added!")
    print(f"[INFO] Total patterns: {kb['metadata']['total_patterns']}")
    print(f"[INFO] Keywords: {', '.join(RIDING_CONTROL_PACK['keywords'][:8])}")

if __name__ == "__main__":
    main()
