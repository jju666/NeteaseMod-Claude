# -*- coding: utf-8 -*-
"""
添加背包扩展系统玩法包到知识库
"""
import json
import os

# 知识库路径
KB_PATH = "D:/EcWork/基于Claude的MODSDK开发工作流/.claude/knowledge-base.json"

# 背包扩展系统完整代码(精简版)
BACKPACK_EXPANSION_CODE = '''# -*- coding: utf-8 -*-
from __future__ import print_function
from mod.server.system.serverSystem import ServerSystem
import mod.server.extraServerApi as serverApi
import json

class BackpackExpansionServerSystem(ServerSystem):
    """背包扩展系统"""

    def __init__(self, namespace, systemName):
        super(BackpackExpansionServerSystem, self).__init__(namespace, systemName)

        # 背包数据缓存
        self.backpacks = {}

        # 默认背包大小
        self.default_size = 27

        self.extra_data_comp = None
        self.item_comp = None
        self.Create()

    def Create(self):
        """初始化组件和事件监听"""
        level_id = serverApi.GetLevelId()
        comp_factory = serverApi.GetEngineCompFactory()

        self.extra_data_comp = comp_factory.CreateExtraData(level_id)
        self.item_comp = comp_factory.CreateItem(level_id)

        # 监听玩家加入事件
        self.ListenForEvent(
            serverApi.GetEngineNamespace(),
            serverApi.GetEngineSystemName(),
            "AddServerPlayerEvent",
            self,
            self.OnPlayerJoin
        )

    def OnPlayerJoin(self, args):
        """玩家加入时初始化背包"""
        player_id = args["id"]
        backpack_data = self._LoadBackpack(player_id)

        if not backpack_data:
            backpack_data = {
                "size": self.default_size,
                "items": []
            }
            self._SaveBackpack(player_id, backpack_data)

        self.backpacks[player_id] = backpack_data
        print("[BackpackExpansion] 玩家 {} 背包大小: {}".format(
            player_id, backpack_data["size"]
        ))

    def ExpandBackpack(self, player_id, additional_slots):
        """扩展背包大小"""
        backpack = self.backpacks.get(player_id)
        if not backpack:
            return False

        backpack["size"] += additional_slots
        self._SaveBackpack(player_id, backpack)

        print("[BackpackExpansion] 玩家 {} 背包扩展至 {} 格".format(
            player_id, backpack["size"]
        ))
        return True

    def StoreItem(self, player_id, item_dict):
        """存储物品到扩展背包"""
        backpack = self.backpacks.get(player_id)
        if not backpack:
            return False

        if len(backpack["items"]) >= backpack["size"]:
            print("[BackpackExpansion] 背包已满")
            return False

        backpack["items"].append(item_dict)
        self._SaveBackpack(player_id, backpack)
        return True

    def RetrieveItem(self, player_id, slot_index):
        """从扩展背包取出物品"""
        backpack = self.backpacks.get(player_id)
        if not backpack or slot_index >= len(backpack["items"]):
            return None

        item_dict = backpack["items"].pop(slot_index)
        self._SaveBackpack(player_id, backpack)

        # 给予玩家物品
        self.item_comp.SpawnItemToPlayerInv(item_dict, player_id, 0)
        return item_dict

    def _LoadBackpack(self, player_id):
        """从ExtraData加载背包数据"""
        data_str = self.extra_data_comp.GetExtraData(player_id, "backpack_data")
        return json.loads(data_str) if data_str else None

    def _SaveBackpack(self, player_id, backpack_data):
        """保存背包数据到ExtraData"""
        data_str = json.dumps(backpack_data)
        self.extra_data_comp.SetExtraData(player_id, "backpack_data", data_str)

    def Destroy(self):
        """系统销毁时清理"""
        self.UnListenAllEvents()
'''

# 背包扩展系统玩法包配置
BACKPACK_EXPANSION_PACK = {
    "id": "backpack-expansion-system",
    "name": "背包扩展系统",
    "keywords": [
        "背包", "扩展", "存储", "物品", "容量", "仓库",
        "backpack", "expansion", "storage", "inventory", "capacity", "chest"
    ],
    "category": "经济玩法",
    "difficulty": "中等",
    "estimated_time": "12分钟",

    "description": "实现背包扩展系统,支持扩展背包容量、物品存储、物品取出等功能",

    "implementation_guide": {
        "principle": "使用ExtraData存储背包数据(size和items列表) → 提供ExpandBackpack/StoreItem/RetrieveItem接口 → 通过UI显示扩展背包内容",

        "modsdk_apis": [
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
            },
            {
                "name": "itemComp.SpawnItemToPlayerInv",
                "type": "组件方法",
                "purpose": "给玩家发放物品到背包",
                "params": {
                    "itemDict": "物品信息字典 (dict)",
                    "playerId": "玩家ID (str)",
                    "slot": "背包槽位 (int,0表示自动)"
                },
                "doc_path": "MODSDK/Component/itemComp.md",
                "common_pitfall": "itemDict必须包含itemName和count"
            },
            {
                "name": "AddServerPlayerEvent",
                "type": "事件",
                "trigger": "玩家加入服务器时触发",
                "fields": {
                    "id": "玩家ID (str)"
                },
                "doc_path": "MODSDK/事件/玩家.md",
                "common_pitfall": "玩家重连不会触发"
            }
        ],

        "complete_code": {
            "file": "mod/server/system/BackpackExpansionServerSystem.py",
            "content": BACKPACK_EXPANSION_CODE
        },

        "config_guide": {
            "description": "配置默认背包大小",
            "example": {
                "default_size": 54
            }
        },

        "common_issues": [
            {
                "problem": "背包数据丢失",
                "cause": "SetExtraData调用失败",
                "solution": "确保每次背包变动后调用_SaveBackpack()"
            },
            {
                "problem": "物品存储失败",
                "cause": "背包已满或item_dict格式错误",
                "solution": "检查len(items) < size;确保itemDict包含itemName和count"
            },
            {
                "problem": "取出物品后背包槽位错乱",
                "cause": "pop()操作改变了索引",
                "solution": "使用固定slot_id而非索引;或重新排序items列表"
            }
        ],

        "related_gameplay": [
            {
                "name": "自定义商店系统",
                "similarity": "物品管理",
                "reusable_code": "物品存储逻辑"
            },
            {
                "name": "货币系统",
                "similarity": "数据持久化",
                "extension": "可扩展为仓库系统"
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
    if "backpack-expansion-system" in existing_ids:
        print("[SKIP] Backpack Expansion System pack already exists")
        return

    # 添加新玩法包
    kb["gameplay_patterns"].append(BACKPACK_EXPANSION_PACK)

    # 更新元数据
    kb["metadata"]["total_patterns"] = len(kb["gameplay_patterns"])

    # 保存
    with open(KB_PATH, 'w', encoding='utf-8') as f:
        json.dump(kb, f, ensure_ascii=False, indent=2)

    print("[SUCCESS] Backpack Expansion System gameplay pack added!")
    print(f"[INFO] Total patterns: {kb['metadata']['total_patterns']}")
    print(f"[INFO] Keywords: {', '.join(BACKPACK_EXPANSION_PACK['keywords'][:8])}")

if __name__ == "__main__":
    main()
