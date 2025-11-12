# -*- coding: utf-8 -*-
"""
添加区域保护系统玩法包到知识库
"""
import json
import os

# 知识库路径
KB_PATH = "D:/EcWork/基于Claude的MODSDK开发工作流/.claude/knowledge-base.json"

# 区域保护系统完整代码(精简版)
REGION_PROTECTION_CODE = '''# -*- coding: utf-8 -*-
from __future__ import print_function
from mod.server.system.serverSystem import ServerSystem
import mod.server.extraServerApi as serverApi
import json

class RegionProtectionServerSystem(ServerSystem):
    """区域保护系统"""

    def __init__(self, namespace, systemName):
        super(RegionProtectionServerSystem, self).__init__(namespace, systemName)

        # 保护区域数据
        self.regions = {}

        self.extra_data_comp = None
        self.msg_comp = None
        self.Create()

    def Create(self):
        """初始化组件和事件监听"""
        level_id = serverApi.GetLevelId()
        comp_factory = serverApi.GetEngineCompFactory()

        self.extra_data_comp = comp_factory.CreateExtraData(level_id)
        self.msg_comp = comp_factory.CreateMsg(level_id)

        # 监听方块放置事件
        self.ListenForEvent(
            serverApi.GetEngineNamespace(),
            serverApi.GetEngineSystemName(),
            "ServerBlockPlaceEvent",
            self,
            self.OnBlockPlace
        )

        # 监听方块破坏事件
        self.ListenForEvent(
            serverApi.GetEngineNamespace(),
            serverApi.GetEngineSystemName(),
            "ServerBlockDestroyEvent",
            self,
            self.OnBlockDestroy
        )

    def OnBlockPlace(self, args):
        """处理方块放置 - 检查保护区域"""
        player_id = args.get("playerId")
        x = args.get("x")
        y = args.get("y")
        z = args.get("z")

        if not player_id:
            return

        # 检查是否在保护区域内
        region = self._FindRegionByPos((x, y, z))
        if region:
            # 检查权限
            if not self._HasPermission(player_id, region):
                args["cancel"] = True
                self.msg_comp.NotifyOneMessage(
                    player_id,
                    "§c该区域受保护,无法放置方块!",
                    "§e保护"
                )

    def OnBlockDestroy(self, args):
        """处理方块破坏 - 检查保护区域"""
        player_id = args.get("playerId")
        x = args.get("x")
        y = args.get("y")
        z = args.get("z")

        if not player_id:
            return

        # 检查是否在保护区域内
        region = self._FindRegionByPos((x, y, z))
        if region:
            # 检查权限
            if not self._HasPermission(player_id, region):
                args["cancel"] = True
                self.msg_comp.NotifyOneMessage(
                    player_id,
                    "§c该区域受保护,无法破坏方块!",
                    "§e保护"
                )

    def CreateRegion(self, region_id, owner_id, min_pos, max_pos):
        """创建保护区域"""
        self.regions[region_id] = {
            "owner": owner_id,
            "min_pos": min_pos,
            "max_pos": max_pos,
            "members": []
        }

        # 保存到ExtraData
        self._SaveRegions()

        print("[RegionProtection] 创建区域: {} 所有者: {}".format(region_id, owner_id))

    def _FindRegionByPos(self, pos):
        """根据坐标查找保护区域"""
        x, y, z = pos
        for region_id, region in self.regions.items():
            min_pos = region["min_pos"]
            max_pos = region["max_pos"]

            # AABB碰撞检测
            if (min_pos[0] <= x <= max_pos[0] and
                min_pos[1] <= y <= max_pos[1] and
                min_pos[2] <= z <= max_pos[2]):
                return region

        return None

    def _HasPermission(self, player_id, region):
        """检查玩家是否有权限"""
        return player_id == region["owner"] or player_id in region.get("members", [])

    def _SaveRegions(self):
        """保存区域数据"""
        level_id = serverApi.GetLevelId()
        data_str = json.dumps(self.regions)
        self.extra_data_comp.SetExtraData(level_id, "regions_data", data_str)

    def Destroy(self):
        """系统销毁时清理"""
        self.UnListenAllEvents()
'''

# 区域保护系统玩法包配置
REGION_PROTECTION_PACK = {
    "id": "region-protection-system",
    "name": "区域保护系统",
    "keywords": [
        "区域", "保护", "领地", "权限", "AABB", "碰撞检测",
        "region", "protection", "claim", "permission", "area", "territory"
    ],
    "category": "世界玩法",
    "difficulty": "中等",
    "estimated_time": "15分钟",

    "description": "实现区域保护系统,支持创建保护区域、权限控制、AABB碰撞检测等功能",

    "implementation_guide": {
        "principle": "服务端监听ServerBlockPlaceEvent/ServerBlockDestroyEvent → 使用AABB算法检测坐标是否在保护区域内 → 验证玩家权限 → 允许或取消操作",

        "modsdk_apis": [
            {
                "name": "ServerBlockPlaceEvent",
                "type": "事件",
                "trigger": "方块被放置时触发",
                "fields": {
                    "playerId": "放置玩家ID (str)",
                    "x": "x坐标 (int)",
                    "y": "y坐标 (int)",
                    "z": "z坐标 (int)",
                    "cancel": "是否取消 (bool,可修改)"
                },
                "doc_path": "MODSDK/事件/方块.md",
                "common_pitfall": "设置cancel=True可取消方块放置"
            },
            {
                "name": "ServerBlockDestroyEvent",
                "type": "事件",
                "trigger": "方块被破坏时触发",
                "fields": {
                    "playerId": "破坏玩家ID (str)",
                    "x": "x坐标 (int)",
                    "y": "y坐标 (int)",
                    "z": "z坐标 (int)",
                    "cancel": "是否取消 (bool,可修改)"
                },
                "doc_path": "MODSDK/事件/方块.md",
                "common_pitfall": "设置cancel=True可取消方块破坏"
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
            "file": "mod/server/system/RegionProtectionServerSystem.py",
            "content": REGION_PROTECTION_CODE
        },

        "config_guide": {
            "description": "调用CreateRegion创建保护区域",
            "example": {
                "region_id": "spawn_area",
                "owner_id": "admin",
                "min_pos": [0, 60, 0],
                "max_pos": [100, 100, 100]
            }
        },

        "common_issues": [
            {
                "problem": "AABB检测不准确",
                "cause": "min_pos和max_pos设置错误",
                "solution": "确保min_pos每个坐标都小于max_pos对应坐标"
            },
            {
                "problem": "保护不生效",
                "cause": "事件未正确取消",
                "solution": "确保设置args['cancel']=True"
            },
            {
                "problem": "区域数据丢失",
                "cause": "未正确保存到ExtraData",
                "solution": "调用_SaveRegions()持久化数据"
            }
        ],

        "related_gameplay": [
            {
                "name": "自定义方块功能系统",
                "similarity": "方块事件处理",
                "reusable_code": "方块事件监听框架"
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
    if "region-protection-system" in existing_ids:
        print("[SKIP] Region Protection System pack already exists")
        return

    # 添加新玩法包
    kb["gameplay_patterns"].append(REGION_PROTECTION_PACK)

    # 更新元数据
    kb["metadata"]["total_patterns"] = len(kb["gameplay_patterns"])

    # 保存
    with open(KB_PATH, 'w', encoding='utf-8') as f:
        json.dump(kb, f, ensure_ascii=False, indent=2)

    print("[SUCCESS] Region Protection System gameplay pack added!")
    print(f"[INFO] Total patterns: {kb['metadata']['total_patterns']}")
    print(f"[INFO] Keywords: {', '.join(REGION_PROTECTION_PACK['keywords'][:8])}")

if __name__ == "__main__":
    main()
