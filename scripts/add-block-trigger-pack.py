# -*- coding: utf-8 -*-
"""
添加右键方块触发事件系统玩法包到知识库
"""
import json
import os

# 知识库路径
KB_PATH = "D:/EcWork/基于Claude的MODSDK开发工作流/.claude/knowledge-base.json"

# 右键方块触发事件系统完整代码
BLOCK_TRIGGER_CODE = '''# -*- coding: utf-8 -*-
from __future__ import print_function
from mod.server.system.serverSystem import ServerSystem
import mod.server.extraServerApi as serverApi

class BlockTriggerServerSystem(ServerSystem):
    """右键方块触发事件系统"""

    def __init__(self, namespace, systemName):
        super(BlockTriggerServerSystem, self).__init__(namespace, systemName)

        # 方块触发器配置
        self.block_triggers = {
            "minecraft:diamond_block": {
                "action": "teleport",
                "target_pos": (100, 64, 100),
                "cooldown": 100
            },
            "minecraft:gold_block": {
                "action": "give_items",
                "items": [
                    {"itemName": "minecraft:diamond", "count": 5},
                    {"itemName": "minecraft:gold_ingot", "count": 10}
                ],
                "cooldown": 200
            },
            "minecraft:emerald_block": {
                "action": "execute_command",
                "commands": [
                    "/effect @s speed 60 1",
                    "/effect @s jump_boost 60 2"
                ],
                "cooldown": 60
            }
        }

        # 冷却时间记录
        self.cooldowns = {}

        self.pos_comp = None
        self.item_comp = None
        self.command_comp = None
        self.msg_comp = None
        self.Create()

    def Create(self):
        """初始化组件和事件监听"""
        level_id = serverApi.GetLevelId()
        comp_factory = serverApi.GetEngineCompFactory()

        self.pos_comp = comp_factory.CreatePos(level_id)
        self.item_comp = comp_factory.CreateItem(level_id)
        self.command_comp = comp_factory.CreateCommand(level_id)
        self.msg_comp = comp_factory.CreateMsg(level_id)

        # 监听方块交互事件
        self.ListenForEvent(
            serverApi.GetEngineNamespace(),
            serverApi.GetEngineSystemName(),
            "ServerBlockUseEvent",
            self,
            self.OnBlockUse
        )

    def OnBlockUse(self, args):
        """处理方块交互事件"""
        player_id = args.get("playerId")
        block_name = args.get("blockName")
        x = args.get("x")
        y = args.get("y")
        z = args.get("z")

        if not player_id or not block_name:
            return

        # 检查方块是否有触发器
        if block_name not in self.block_triggers:
            return

        trigger = self.block_triggers[block_name]

        # 检查冷却时间
        cooldown_key = "{}_{}_{}_{}".format(player_id, x, y, z)
        if cooldown_key in self.cooldowns:
            remaining = self.cooldowns[cooldown_key]
            self.msg_comp.NotifyOneMessage(
                player_id,
                "§c冷却中,剩余 {} 秒".format(remaining // 20),
                "§e触发器"
            )
            return

        # 执行触发动作
        action = trigger.get("action")
        success = False

        if action == "teleport":
            success = self._ExecuteTeleport(player_id, trigger)
        elif action == "give_items":
            success = self._ExecuteGiveItems(player_id, trigger)
        elif action == "execute_command":
            success = self._ExecuteCommands(player_id, trigger)

        if success:
            # 设置冷却时间
            cooldown = trigger.get("cooldown", 0)
            if cooldown > 0:
                self.cooldowns[cooldown_key] = cooldown
                # 启动冷却倒计时
                self._StartCooldown(cooldown_key, cooldown)

            print("[BlockTrigger] 玩家 {} 触发 {} 动作: {}".format(
                player_id, block_name, action
            ))

    def _ExecuteTeleport(self, player_id, trigger):
        """执行传送动作"""
        target_pos = trigger.get("target_pos")
        if not target_pos:
            return False

        dimension = trigger.get("dimension", 0)
        success = self.pos_comp.SetFootPos(player_id, target_pos)

        if success:
            self.msg_comp.NotifyOneMessage(
                player_id,
                "§a传送成功!",
                "§e触发器"
            )
        return success

    def _ExecuteGiveItems(self, player_id, trigger):
        """执行给予物品动作"""
        items = trigger.get("items", [])
        if not items:
            return False

        for item_dict in items:
            self.item_comp.SpawnItemToPlayerInv(item_dict, player_id, 0)

        self.msg_comp.NotifyOneMessage(
            player_id,
            "§a已获得物品!",
            "§e触发器"
        )
        return True

    def _ExecuteCommands(self, player_id, trigger):
        """执行命令动作"""
        commands = trigger.get("commands", [])
        if not commands:
            return False

        for cmd in commands:
            # 替换@s为玩家ID
            cmd = cmd.replace("@s", player_id)
            self.command_comp.SetCommand(cmd, player_id)

        self.msg_comp.NotifyOneMessage(
            player_id,
            "§a效果已激活!",
            "§e触发器"
        )
        return True

    def _StartCooldown(self, cooldown_key, duration):
        """启动冷却倒计时"""
        import threading
        import time

        def countdown():
            remaining = duration
            while remaining > 0:
                time.sleep(0.05)  # 1 tick
                remaining -= 1
                self.cooldowns[cooldown_key] = remaining

            # 冷却结束
            if cooldown_key in self.cooldowns:
                del self.cooldowns[cooldown_key]

        thread = threading.Thread(target=countdown)
        thread.daemon = True
        thread.start()

    def Destroy(self):
        """系统销毁时清理"""
        self.UnListenAllEvents()
'''

# 右键方块触发事件系统玩法包配置
BLOCK_TRIGGER_PACK = {
    "id": "block-trigger-system",
    "name": "右键方块触发事件系统",
    "keywords": [
        "方块", "触发器", "交互", "右键", "传送", "命令执行",
        "block", "trigger", "interact", "use", "teleport", "command"
    ],
    "category": "交互玩法",
    "difficulty": "简单",
    "estimated_time": "10分钟",

    "description": "实现右键方块触发各种事件的系统,支持传送、物品给予、命令执行等多种动作,包含冷却时间管理",

    "implementation_guide": {
        "principle": "服务端监听ServerBlockUseEvent → 判断方块类型是否有触发器 → 检查冷却时间 → 执行对应动作(传送/给予物品/执行命令) → 启动冷却计时器",

        "modsdk_apis": [
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
                "common_pitfall": "事件tick执行,需注意效率"
            },
            {
                "name": "posComp.SetFootPos",
                "type": "组件方法",
                "purpose": "设置实体脚部位置(传送)",
                "params": {
                    "entityId": "实体ID (str)",
                    "pos": "目标坐标(x,y,z) (tuple)"
                },
                "returns": "是否成功 (bool)",
                "doc_path": "MODSDK/Component/posComp.md",
                "common_pitfall": "坐标需为有效位置,否则返回False"
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
                "name": "commandComp.SetCommand",
                "type": "组件方法",
                "purpose": "执行命令",
                "params": {
                    "command": "命令字符串 (str)",
                    "playerId": "执行者ID (str)"
                },
                "doc_path": "MODSDK/Component/commandComp.md",
                "common_pitfall": "命令需包含/前缀"
            }
        ],

        "complete_code": {
            "file": "mod/server/system/BlockTriggerServerSystem.py",
            "content": BLOCK_TRIGGER_CODE
        },

        "config_guide": {
            "description": "在block_triggers中配置触发器",
            "example": {
                "minecraft:redstone_block": {
                    "action": "teleport",
                    "target_pos": (0, 100, 0),
                    "dimension": 0,
                    "cooldown": 200
                }
            },
            "fields": {
                "action": "动作类型 (str: teleport/give_items/execute_command)",
                "target_pos": "传送目标坐标 (tuple,teleport需要)",
                "dimension": "目标维度 (int,可选)",
                "items": "物品列表 (list,give_items需要)",
                "commands": "命令列表 (list,execute_command需要)",
                "cooldown": "冷却时间/tick (int,可选)"
            }
        },

        "common_issues": [
            {
                "problem": "传送失败",
                "cause": "目标坐标无效或不安全",
                "solution": "确保目标坐标为有效位置,y坐标不能超出世界高度限制"
            },
            {
                "problem": "冷却时间不生效",
                "cause": "cooldown_key生成错误或线程未正确启动",
                "solution": "检查cooldown_key拼接逻辑,确保线程正确启动"
            },
            {
                "problem": "命令执行无效",
                "cause": "命令格式错误或权限不足",
                "solution": "确保命令以/开头,@s正确替换为玩家ID"
            }
        ],

        "related_gameplay": [
            {
                "name": "区域传送门系统",
                "similarity": "传送功能",
                "reusable_code": "传送逻辑和冷却管理"
            },
            {
                "name": "自定义商店系统",
                "similarity": "方块交互触发",
                "extension": "可扩展为机关系统"
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
    if "block-trigger-system" in existing_ids:
        print("[SKIP] Block Trigger System pack already exists")
        return

    # 添加新玩法包
    kb["gameplay_patterns"].append(BLOCK_TRIGGER_PACK)

    # 更新元数据
    kb["metadata"]["total_patterns"] = len(kb["gameplay_patterns"])

    # 保存
    with open(KB_PATH, 'w', encoding='utf-8') as f:
        json.dump(kb, f, ensure_ascii=False, indent=2)

    print("[SUCCESS] Block Trigger System gameplay pack added!")
    print(f"[INFO] Total patterns: {kb['metadata']['total_patterns']}")
    print(f"[INFO] Keywords: {', '.join(BLOCK_TRIGGER_PACK['keywords'][:8])}")

if __name__ == "__main__":
    main()
