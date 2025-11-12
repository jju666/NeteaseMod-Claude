# -*- coding: utf-8 -*-
"""
添加NPC对话系统玩法包到知识库
"""
import json
import os

# 知识库路径
KB_PATH = "D:/EcWork/基于Claude的MODSDK开发工作流/.claude/knowledge-base.json"

# NPC对话系统完整代码(精简版 - 保留核心逻辑)
NPC_DIALOGUE_CODE = '''# -*- coding: utf-8 -*-
from __future__ import print_function
from mod.server.system.serverSystem import ServerSystem
import mod.server.extraServerApi as serverApi

class NPCDialogueServerSystem(ServerSystem):
    """NPC对话系统 - 服务端"""

    def __init__(self, namespace, systemName):
        super(NPCDialogueServerSystem, self).__init__(namespace, systemName)

        # 对话配置表
        self.dialogue_config = {
            "merchant": {
                "greet": "欢迎光临!需要什么?",
                "options": [
                    {"text": "购买物品", "action": "shop"},
                    {"text": "出售物品", "action": "sell"},
                    {"text": "离开", "action": "close"}
                ]
            },
            "quest_giver": {
                "greet": "我有任务给你!",
                "quest": "击败10只僵尸,带回僵尸头颅。奖励:1000经验+稀有战利品",
                "options": [
                    {"text": "接受任务", "action": "accept_quest"},
                    {"text": "拒绝", "action": "close"}
                ]
            }
        }

        # NPC位置映射(entityId -> NPC类型)
        self.npc_registry = {}

        # 玩家对话状态
        self.player_dialogue_state = {}

        self.Create()

    def Create(self):
        """初始化组件和事件监听"""
        # 监听玩家交互实体事件
        self.ListenForEvent(
            serverApi.GetEngineNamespace(),
            serverApi.GetEngineSystemName(),
            "PlayerInteractEntityEvent",
            self,
            self.OnPlayerInteractEntity
        )

        # 监听自定义对话选择事件(客户端发送)
        self.ListenForEvent(
            "MyMod",
            "MyClientSystem",
            "OnDialogueChoice",
            self,
            self.OnDialogueChoice
        )

    def RegisterNPC(self, entity_id, npc_type):
        """注册NPC实体"""
        self.npc_registry[entity_id] = npc_type
        print("[DialogueSystem] 注册NPC: {} -> {}".format(entity_id, npc_type))

    def OnPlayerInteractEntity(self, args):
        """玩家交互实体事件处理"""
        player_id = args.get("playerId")
        entity_id = args.get("entityId")

        if not player_id or not entity_id:
            return

        # 检查是否是注册的NPC
        if entity_id not in self.npc_registry:
            return

        npc_type = self.npc_registry[entity_id]

        # 显示对话
        self.ShowDialogue(player_id, npc_type, entity_id)

    def ShowDialogue(self, player_id, npc_type, entity_id):
        """显示对话UI"""
        if npc_type not in self.dialogue_config:
            print("[DialogueSystem] 未找到NPC配置: {}".format(npc_type))
            return

        config = self.dialogue_config[npc_type]

        # 保存玩家当前对话状态
        self.player_dialogue_state[player_id] = {
            "npc_type": npc_type,
            "entity_id": entity_id,
            "stage": "greeting"
        }

        # 发送对话数据到客户端
        event_data = self.CreateEventData()
        event_data["npcType"] = npc_type
        event_data["greetText"] = config["greet"]
        event_data["options"] = config["options"]

        self.NotifyToClient(player_id, "ShowDialogueUI", event_data)

        print("[DialogueSystem] 向玩家 {} 显示对话: {}".format(player_id, npc_type))

    def OnDialogueChoice(self, args):
        """处理玩家的对话选择"""
        player_id = args.get("playerId")
        choice = args.get("choice")  # 选项索引或动作名

        if not player_id or choice is None:
            return

        # 获取玩家对话状态
        state = self.player_dialogue_state.get(player_id)
        if not state:
            return

        npc_type = state["npc_type"]

        # 处理不同的选择
        if choice == "shop":
            self.ShowShop(player_id)
        elif choice == "sell":
            self.ShowSellUI(player_id)
        elif choice == "accept_quest":
            self.GiveQuest(player_id, "defeat_zombies")
        elif choice == "close":
            self.CloseDialogue(player_id)

        print("[DialogueSystem] 玩家 {} 选择: {}".format(player_id, choice))

    def ShowShop(self, player_id):
        """显示商店UI"""
        shop_items = [
            {"item": "minecraft:iron_sword", "price": 100},
            {"item": "minecraft:diamond", "price": 500},
            {"item": "minecraft:enchanted_book", "price": 200}
        ]

        event_data = self.CreateEventData()
        event_data["items"] = shop_items

        self.NotifyToClient(player_id, "ShowShopUI", event_data)

    def ShowSellUI(self, player_id):
        """显示出售UI"""
        # 获取玩家背包物品
        inv_comp = serverApi.GetEngineCompFactory().CreateItem(player_id)

        event_data = self.CreateEventData()
        event_data["message"] = "选择要出售的物品"

        self.NotifyToClient(player_id, "ShowSellUI", event_data)

    def GiveQuest(self, player_id, quest_id):
        """给玩家任务"""
        # 添加任务标签
        tag_comp = serverApi.GetEngineCompFactory().CreateTag(serverApi.GetLevelId())
        tag_comp.AddEntityTag(player_id, "quest_{}".format(quest_id))

        # 发送任务接受消息
        msg_comp = serverApi.GetEngineCompFactory().CreateMsg(player_id)
        msg_comp.NotifyOneMessage(
            player_id,
            "§e[任务] §f已接受任务: 击败10只僵尸",
            "§c警告"
        )

        print("[DialogueSystem] 玩家 {} 接受任务: {}".format(player_id, quest_id))

    def CloseDialogue(self, player_id):
        """关闭对话"""
        if player_id in self.player_dialogue_state:
            del self.player_dialogue_state[player_id]

        event_data = self.CreateEventData()
        self.NotifyToClient(player_id, "CloseDialogueUI", event_data)

    def Destroy(self):
        """系统销毁时清理"""
        self.UnListenAllEvents()
'''

# NPC对话系统玩法包配置
NPC_DIALOGUE_PACK = {
    "id": "npc-dialogue-system",
    "name": "NPC对话系统",
    "keywords": [
        "NPC", "对话", "交互", "对话框", "对话系统", "选项", "分支",
        "商人", "任务", "questgiver", "merchant", "dialogue", "talk",
        "interact", "conversation"
    ],
    "category": "交互玩法",
    "difficulty": "中等",
    "estimated_time": "10分钟",

    "description": "实现NPC对话系统,支持多选项对话、对话分支、任务接取、商店交互等功能",

    "implementation_guide": {
        "principle": "服务端监听PlayerInteractEntityEvent → 判断NPC类型 → NotifyToClient发送对话数据 → 客户端显示UI → 玩家选择后发送事件 → 服务端处理选择结果",

        "modsdk_apis": [
            {
                "name": "PlayerInteractEntityEvent",
                "type": "事件",
                "trigger": "玩家右键点击实体时触发",
                "fields": {
                    "playerId": "交互玩家ID (str)",
                    "entityId": "被交互实体ID (str)"
                },
                "doc_path": "MODSDK/事件/玩家.md",
                "common_pitfall": "事件在服务端和客户端都会触发,需区分处理"
            },
            {
                "name": "NotifyToClient",
                "type": "系统方法",
                "purpose": "服务端向客户端发送自定义事件",
                "params": {
                    "playerId": "目标玩家ID (str)",
                    "eventName": "事件名称 (str)",
                    "eventData": "事件数据字典 (dict)"
                },
                "doc_path": "MODSDK/系统/事件通信.md",
                "common_pitfall": "eventData中不能包含tuple,必须使用list或dict"
            },
            {
                "name": "CreateEventData",
                "type": "系统方法",
                "purpose": "创建事件数据字典",
                "doc_path": "MODSDK/系统/事件通信.md",
                "common_pitfall": "必须使用CreateEventData创建,不能直接用{}"
            },
            {
                "name": "tagComp.AddEntityTag",
                "type": "组件方法",
                "purpose": "给实体添加标签",
                "params": {
                    "entityId": "实体ID (str)",
                    "tag": "标签名称 (str)"
                },
                "doc_path": "MODSDK/Component/tagComp.md",
                "common_pitfall": "标签名不能包含空格和特殊字符"
            },
            {
                "name": "msgComp.NotifyOneMessage",
                "type": "组件方法",
                "purpose": "向玩家发送聊天消息",
                "params": {
                    "playerId": "玩家ID (str)",
                    "message": "消息内容 (str,支持§颜色代码)",
                    "messageType": "消息类型 (str)"
                },
                "doc_path": "MODSDK/Component/msgComp.md",
                "common_pitfall": "颜色代码需使用§而非&"
            }
        ],

        "complete_code": {
            "file": "mod/server/system/NPCDialogueServerSystem.py",
            "content": NPC_DIALOGUE_CODE
        },

        "config_guide": {
            "description": "在dialogue_config中配置NPC对话内容和选项",
            "example": {
                "blacksmith": {
                    "greet": "需要修理装备吗?",
                    "options": [
                        {"text": "修理装备", "action": "repair"},
                        {"text": "强化装备", "action": "upgrade"},
                        {"text": "离开", "action": "close"}
                    ]
                }
            },
            "fields": {
                "greet": "NPC问候语 (str)",
                "quest": "任务描述 (str,可选)",
                "options": "对话选项列表 (list)",
                "options[].text": "选项显示文本 (str)",
                "options[].action": "选项动作名称 (str,用于OnDialogueChoice处理)"
            }
        },

        "common_issues": [
            {
                "problem": "客户端未收到对话UI事件",
                "cause": "NotifyToClient的eventName与客户端监听的不一致,或eventData包含不可序列化对象",
                "solution": "检查事件名拼写;确保eventData只包含基本类型(str/int/float/list/dict)"
            },
            {
                "problem": "多人游戏时所有玩家都看到对话",
                "cause": "使用了BroadcastToAllClient而非NotifyToClient",
                "solution": "使用NotifyToClient(player_id, ...)只向特定玩家发送"
            },
            {
                "problem": "对话状态丢失",
                "cause": "玩家重新登录或服务器重启导致内存状态清空",
                "solution": "重要状态使用tag或scoreboard持久化存储"
            },
            {
                "problem": "NPC交互无响应",
                "cause": "NPC未注册或entityId不匹配",
                "solution": "在NPC生成时调用RegisterNPC;检查entity_id是否正确"
            }
        ],

        "related_gameplay": [
            {
                "name": "自定义商店",
                "similarity": "同样使用对话UI展示商品列表",
                "reusable_code": "对话框架、选项处理逻辑"
            },
            {
                "name": "任务系统",
                "similarity": "NPC发布任务、跟踪任务进度",
                "extension": "添加任务进度追踪、完成条件判断"
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
    if "npc-dialogue-system" in existing_ids:
        print("[SKIP] NPC Dialogue System pack already exists")
        return

    # 添加新玩法包
    kb["gameplay_patterns"].append(NPC_DIALOGUE_PACK)

    # 更新元数据
    kb["metadata"]["total_patterns"] = len(kb["gameplay_patterns"])

    # 保存
    with open(KB_PATH, 'w', encoding='utf-8') as f:
        json.dump(kb, f, ensure_ascii=False, indent=2)

    print("[SUCCESS] NPC Dialogue System gameplay pack added!")
    print(f"[INFO] Total patterns: {kb['metadata']['total_patterns']}")
    print(f"[INFO] Keywords: {', '.join(NPC_DIALOGUE_PACK['keywords'][:8])}")
    print(f"[INFO] Code lines: {len(NPC_DIALOGUE_CODE.splitlines())}")

if __name__ == "__main__":
    main()
