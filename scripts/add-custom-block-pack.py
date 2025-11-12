# -*- coding: utf-8 -*-
"""
添加自定义方块功能系统玩法包到知识库
"""
import json
import os

# 知识库路径
KB_PATH = "D:/EcWork\基于Claude的MODSDK开发工作流/.claude/knowledge-base.json"

# 自定义方块功能系统完整代码(精简版)
CUSTOM_BLOCK_CODE = '''# -*- coding: utf-8 -*-
from __future__ import print_function
from mod.server.system.serverSystem import ServerSystem
import mod.server.extraServerApi as serverApi

class CustomBlockServerSystem(ServerSystem):
    """自定义方块功能系统"""

    def __init__(self, namespace, systemName):
        super(CustomBlockServerSystem, self).__init__(namespace, systemName)

        # 自定义方块配置
        self.custom_blocks = {
            "mymod:energy_block": {
                "on_place": self._OnEnergyBlockPlace,
                "on_break": self._OnEnergyBlockBreak,
                "on_use": self._OnEnergyBlockUse
            }
        }

        self.block_comp = None
        self.Create()

    def Create(self):
        """初始化组件和事件监听"""
        level_id = serverApi.GetLevelId()
        comp_factory = serverApi.GetEngineCompFactory()

        self.block_comp = comp_factory.CreateBlockInfo(level_id)

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

        # 监听方块使用事件
        self.ListenForEvent(
            serverApi.GetEngineNamespace(),
            serverApi.GetEngineSystemName(),
            "ServerBlockUseEvent",
            self,
            self.OnBlockUse
        )

    def OnBlockPlace(self, args):
        """处理方块放置"""
        block_name = args.get("fullName")
        player_id = args.get("playerId")

        if block_name in self.custom_blocks:
            handler = self.custom_blocks[block_name].get("on_place")
            if handler:
                handler(args, player_id)

    def OnBlockDestroy(self, args):
        """处理方块破坏"""
        block_name = args.get("fullName")
        player_id = args.get("playerId")

        if block_name in self.custom_blocks:
            handler = self.custom_blocks[block_name].get("on_break")
            if handler:
                handler(args, player_id)

    def OnBlockUse(self, args):
        """处理方块使用"""
        block_name = args.get("blockName")
        player_id = args.get("playerId")

        if block_name in self.custom_blocks:
            handler = self.custom_blocks[block_name].get("on_use")
            if handler:
                handler(args, player_id)

    def _OnEnergyBlockPlace(self, args, player_id):
        """能量方块放置处理"""
        print("[CustomBlock] 能量方块已放置: {}".format(player_id))

    def _OnEnergyBlockBreak(self, args, player_id):
        """能量方块破坏处理"""
        print("[CustomBlock] 能量方块已破坏: {}".format(player_id))

    def _OnEnergyBlockUse(self, args, player_id):
        """能量方块使用处理"""
        print("[CustomBlock] 能量方块已使用: {}".format(player_id))

    def Destroy(self):
        """系统销毁时清理"""
        self.UnListenAllEvents()
'''

# 自定义方块功能系统玩法包配置
CUSTOM_BLOCK_PACK = {
    "id": "custom-block-system",
    "name": "自定义方块功能系统",
    "keywords": [
        "方块", "自定义方块", "放置", "破坏", "交互", "方块事件",
        "block", "custom block", "place", "break", "interact", "tile entity"
    ],
    "category": "世界玩法",
    "difficulty": "中等",
    "estimated_time": "15分钟",

    "description": "实现自定义方块功能系统,支持方块放置、破坏、使用事件的自定义处理",

    "implementation_guide": {
        "principle": "服务端监听ServerBlockPlaceEvent/ServerBlockDestroyEvent/ServerBlockUseEvent → 判断方块类型 → 调用对应的事件处理器",

        "modsdk_apis": [
            {
                "name": "ServerBlockPlaceEvent",
                "type": "事件",
                "trigger": "方块被放置时触发",
                "fields": {
                    "playerId": "放置玩家ID (str)",
                    "fullName": "方块完整名称 (str)",
                    "x": "x坐标 (int)",
                    "y": "y坐标 (int)",
                    "z": "z坐标 (int)"
                },
                "doc_path": "MODSDK/事件/方块.md",
                "common_pitfall": "事件可能在客户端和服务端都触发"
            },
            {
                "name": "ServerBlockDestroyEvent",
                "type": "事件",
                "trigger": "方块被破坏时触发",
                "fields": {
                    "playerId": "破坏玩家ID (str)",
                    "fullName": "方块完整名称 (str)",
                    "x": "x坐标 (int)",
                    "y": "y坐标 (int)",
                    "z": "z坐标 (int)"
                },
                "doc_path": "MODSDK/事件/方块.md",
                "common_pitfall": "取消事件不会阻止方块被破坏"
            },
            {
                "name": "ServerBlockUseEvent",
                "type": "事件",
                "trigger": "玩家右键点击方块时触发",
                "fields": {
                    "playerId": "交互玩家ID (str)",
                    "blockName": "方块identifier (str)",
                    "x": "方块x坐标 (int)",
                    "y": "方块y坐标 (int)",
                    "z": "方块z坐标 (int)"
                },
                "doc_path": "MODSDK/事件/方块.md",
                "common_pitfall": "该事件tick执行,需注意效率"
            }
        ],

        "complete_code": {
            "file": "mod/server/system/CustomBlockServerSystem.py",
            "content": CUSTOM_BLOCK_CODE
        },

        "config_guide": {
            "description": "在custom_blocks中配置自定义方块",
            "example": {
                "mymod:teleporter_block": {
                    "on_place": "_OnTeleporterPlace",
                    "on_break": "_OnTeleporterBreak",
                    "on_use": "_OnTeleporterUse"
                }
            },
            "fields": {
                "on_place": "放置处理函数 (str,可选)",
                "on_break": "破坏处理函数 (str,可选)",
                "on_use": "使用处理函数 (str,可选)"
            }
        },

        "common_issues": [
            {
                "problem": "事件不触发",
                "cause": "方块名称不匹配或未正确监听",
                "solution": "确保方块名称使用完整identifier(namespace:name)"
            },
            {
                "problem": "事件重复触发",
                "cause": "客户端和服务端都触发了事件",
                "solution": "只在服务端处理或添加去重逻辑"
            }
        ],

        "related_gameplay": [
            {
                "name": "右键方块触发事件系统",
                "similarity": "方块交互事件",
                "reusable_code": "方块事件处理框架"
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
    if "custom-block-system" in existing_ids:
        print("[SKIP] Custom Block System pack already exists")
        return

    # 添加新玩法包
    kb["gameplay_patterns"].append(CUSTOM_BLOCK_PACK)

    # 更新元数据
    kb["metadata"]["total_patterns"] = len(kb["gameplay_patterns"])

    # 保存
    with open(KB_PATH, 'w', encoding='utf-8') as f:
        json.dump(kb, f, ensure_ascii=False, indent=2)

    print("[SUCCESS] Custom Block System gameplay pack added!")
    print(f"[INFO] Total patterns: {kb['metadata']['total_patterns']}")
    print(f"[INFO] Keywords: {', '.join(CUSTOM_BLOCK_PACK['keywords'][:8])}")

if __name__ == "__main__":
    main()
