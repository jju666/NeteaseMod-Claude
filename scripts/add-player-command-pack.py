# -*- coding: utf-8 -*-
"""
添加玩家指令系统玩法包到知识库
"""
import json
import os

# 知识库路径
KB_PATH = "D:/EcWork/基于Claude的MODSDK开发工作流/.claude/knowledge-base.json"

# 玩家指令系统完整代码(精简版,仅保留核心部分)
PLAYER_COMMAND_CODE = '''# -*- coding: utf-8 -*-
from __future__ import print_function
from mod.server.system.serverSystem import ServerSystem
import mod.server.extraServerApi as serverApi

class PlayerCommandServerSystem(ServerSystem):
    """玩家指令系统"""

    def __init__(self, namespace, systemName):
        super(PlayerCommandServerSystem, self).__init__(namespace, systemName)

        # 指令处理器映射
        self.command_handlers = {
            "home": self._HandleHomeCommand,
            "tpa": self._HandleTpaCommand,
            "back": self._HandleBackCommand
        }

        # 玩家数据缓存
        self.player_data = {}

        self.command_comp = None
        self.pos_comp = None
        self.msg_comp = None
        self.extra_data_comp = None
        self.Create()

    def Create(self):
        """初始化组件和事件监听"""
        level_id = serverApi.GetLevelId()
        comp_factory = serverApi.GetEngineCompFactory()

        self.command_comp = comp_factory.CreateCommand(level_id)
        self.pos_comp = comp_factory.CreatePos(level_id)
        self.msg_comp = comp_factory.CreateMsg(level_id)
        self.extra_data_comp = comp_factory.CreateExtraData(level_id)

        # 注册指令
        for cmd_name in self.command_handlers.keys():
            self.command_comp.RegisterPlayerCommand(
                cmd_name,
                "Custom command: {}".format(cmd_name),
                0,  # 权限等级
                []  # 参数定义
            )

        # 监听指令执行事件
        self.ListenForEvent(
            serverApi.GetEngineNamespace(),
            serverApi.GetEngineSystemName(),
            "PlayerCommandEvent",
            self,
            self.OnPlayerCommand
        )

    def OnPlayerCommand(self, args):
        """处理玩家指令"""
        player_id = args.get("playerId")
        command = args.get("command")

        if not player_id or not command:
            return

        # 解析指令名称和参数
        parts = command.split()
        cmd_name = parts[0].lstrip("/")
        cmd_args = parts[1:] if len(parts) > 1 else []

        # 调用对应的指令处理器
        handler = self.command_handlers.get(cmd_name)
        if handler:
            handler(player_id, cmd_args)
            args["cancel"] = True  # 取消默认处理

    def _HandleHomeCommand(self, player_id, args):
        """处理/home指令 - 传送到家"""
        home_pos_str = self.extra_data_comp.GetExtraData(player_id, "home_pos")

        if not home_pos_str:
            self.msg_comp.NotifyOneMessage(player_id, "§c未设置家!", "§eHome")
            return

        import json
        home_pos = json.loads(home_pos_str)

        success = self.pos_comp.SetFootPos(player_id, tuple(home_pos))
        if success:
            self.msg_comp.NotifyOneMessage(player_id, "§a已传送到家!", "§eHome")
        else:
            self.msg_comp.NotifyOneMessage(player_id, "§c传送失败!", "§eHome")

    def _HandleTpaCommand(self, player_id, args):
        """处理/tpa指令 - 传送请求"""
        if len(args) < 1:
            self.msg_comp.NotifyOneMessage(player_id, "§c用法: /tpa <玩家名>", "§eTPA")
            return

        target_name = args[0]
        # 实现传送请求逻辑
        self.msg_comp.NotifyOneMessage(player_id, "§a已发送传送请求给 {}".format(target_name), "§eTPA")

    def _HandleBackCommand(self, player_id, args):
        """处理/back指令 - 返回上次位置"""
        last_pos_str = self.extra_data_comp.GetExtraData(player_id, "last_pos")

        if not last_pos_str:
            self.msg_comp.NotifyOneMessage(player_id, "§c无上次位置!", "§eBack")
            return

        import json
        last_pos = json.loads(last_pos_str)

        success = self.pos_comp.SetFootPos(player_id, tuple(last_pos))
        if success:
            self.msg_comp.NotifyOneMessage(player_id, "§a已返回上次位置!", "§eBack")

    def Destroy(self):
        """系统销毁时清理"""
        self.UnListenAllEvents()
'''

# 玩家指令系统玩法包配置
PLAYER_COMMAND_PACK = {
    "id": "player-command-system",
    "name": "玩家指令系统",
    "keywords": [
        "指令", "命令", "传送", "home", "tpa", "back", "command",
        "teleport", "tp", "player", "custom command"
    ],
    "category": "交互玩法",
    "difficulty": "简单",
    "estimated_time": "12分钟",

    "description": "实现自定义玩家指令系统,支持指令注册、参数解析、权限控制、指令处理等功能",

    "implementation_guide": {
        "principle": "服务端初始化时调用RegisterPlayerCommand注册指令 → 监听PlayerCommandEvent → 解析指令名称和参数 → 调用对应的处理器函数 → 执行指令逻辑",

        "modsdk_apis": [
            {
                "name": "commandComp.RegisterPlayerCommand",
                "type": "组件方法",
                "purpose": "注册自定义玩家指令",
                "params": {
                    "commandName": "指令名称 (str,不含/)",
                    "description": "指令描述 (str)",
                    "permissionLevel": "权限等级 (int,0-4)",
                    "paramDefinitions": "参数定义 (list)"
                },
                "returns": "是否成功 (bool)",
                "doc_path": "MODSDK/Component/commandComp.md",
                "common_pitfall": "指令名称不能包含/前缀;权限等级0为所有玩家"
            },
            {
                "name": "PlayerCommandEvent",
                "type": "事件",
                "trigger": "玩家执行指令时触发",
                "fields": {
                    "playerId": "玩家ID (str)",
                    "command": "指令字符串 (str,包含/)",
                    "cancel": "是否取消 (bool,可修改)"
                },
                "doc_path": "MODSDK/事件/玩家.md",
                "common_pitfall": "设置cancel=True可取消默认处理"
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
                "common_pitfall": "坐标需为有效位置"
            }
        ],

        "complete_code": {
            "file": "mod/server/system/PlayerCommandServerSystem.py",
            "content": PLAYER_COMMAND_CODE
        },

        "config_guide": {
            "description": "在command_handlers中添加新指令处理器",
            "example": {
                "spawn": "_HandleSpawnCommand"
            },
            "fields": {
                "command_name": "指令名称 (str)",
                "handler": "处理函数名 (str)"
            }
        },

        "common_issues": [
            {
                "problem": "指令注册失败",
                "cause": "指令名称包含/或已被占用",
                "solution": "使用不含/的唯一指令名称"
            },
            {
                "problem": "指令不响应",
                "cause": "PlayerCommandEvent未正确监听或处理",
                "solution": "确保事件监听成功;检查args['cancel']设置"
            },
            {
                "problem": "传送失败",
                "cause": "坐标无效或格式错误",
                "solution": "确保从ExtraData读取的坐标使用json.loads解析为tuple"
            }
        ],

        "related_gameplay": [
            {
                "name": "区域传送门系统",
                "similarity": "传送功能",
                "reusable_code": "位置传送逻辑"
            },
            {
                "name": "右键方块触发事件系统",
                "similarity": "事件处理模式",
                "extension": "可扩展为多功能指令系统"
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
    if "player-command-system" in existing_ids:
        print("[SKIP] Player Command System pack already exists")
        return

    # 添加新玩法包
    kb["gameplay_patterns"].append(PLAYER_COMMAND_PACK)

    # 更新元数据
    kb["metadata"]["total_patterns"] = len(kb["gameplay_patterns"])

    # 保存
    with open(KB_PATH, 'w', encoding='utf-8') as f:
        json.dump(kb, f, ensure_ascii=False, indent=2)

    print("[SUCCESS] Player Command System gameplay pack added!")
    print(f"[INFO] Total patterns: {kb['metadata']['total_patterns']}")
    print(f"[INFO] Keywords: {', '.join(PLAYER_COMMAND_PACK['keywords'][:8])}")

if __name__ == "__main__":
    main()
