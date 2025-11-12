# -*- coding: utf-8 -*-
"""
添加队伍系统玩法包到知识库
"""
import json
import os

# 知识库路径
KB_PATH = "D:/EcWork/基于Claude的MODSDK开发工作流/.claude/knowledge-base.json"

# 队伍系统完整代码(精简版)
TEAM_SYSTEM_CODE = '''# -*- coding: utf-8 -*-
from __future__ import print_function
from mod.server.system.serverSystem import ServerSystem
import mod.server.extraServerApi as serverApi
import json

class TeamServerSystem(ServerSystem):
    """队伍系统"""

    def __init__(self, namespace, systemName):
        super(TeamServerSystem, self).__init__(namespace, systemName)

        # 队伍数据
        self.teams = {}

        # 玩家所属队伍映射
        self.player_teams = {}

        self.tag_comp = None
        self.msg_comp = None
        self.extra_data_comp = None
        self.Create()

    def Create(self):
        """初始化组件"""
        level_id = serverApi.GetLevelId()
        comp_factory = serverApi.GetEngineCompFactory()

        self.tag_comp = comp_factory.CreateTag(level_id)
        self.msg_comp = comp_factory.CreateMsg(level_id)
        self.extra_data_comp = comp_factory.CreateExtraData(level_id)

    def CreateTeam(self, team_id, owner_id, team_name):
        """创建队伍"""
        if team_id in self.teams:
            return False

        self.teams[team_id] = {
            "name": team_name,
            "owner": owner_id,
            "members": [owner_id],
            "created_at": serverApi.GetEngineCompFactory().CreateTime(serverApi.GetLevelId()).GetServerTime()
        }

        # 添加队伍标签
        self.tag_comp.AddEntityTag(owner_id, "team_{}".format(team_id))

        self.player_teams[owner_id] = team_id

        # 保存数据
        self._SaveTeams()

        print("[TeamSystem] 创建队伍: {} 队长: {}".format(team_name, owner_id))
        return True

    def JoinTeam(self, team_id, player_id):
        """加入队伍"""
        if team_id not in self.teams:
            return False

        if player_id in self.player_teams:
            self.msg_comp.NotifyOneMessage(player_id, "§c你已在其他队伍中!", "§e队伍")
            return False

        team = self.teams[team_id]
        team["members"].append(player_id)

        # 添加队伍标签
        self.tag_comp.AddEntityTag(player_id, "team_{}".format(team_id))

        self.player_teams[player_id] = team_id

        # 保存数据
        self._SaveTeams()

        # 通知所有队员
        self._BroadcastToTeam(team_id, "§a{} 加入了队伍!".format(player_id))

        return True

    def LeaveTeam(self, player_id):
        """离开队伍"""
        team_id = self.player_teams.get(player_id)
        if not team_id:
            return False

        team = self.teams[team_id]

        # 移除队伍标签
        self.tag_comp.RemoveEntityTag(player_id, "team_{}".format(team_id))

        team["members"].remove(player_id)
        del self.player_teams[player_id]

        # 如果是队长离开且还有成员,转让队长
        if team["owner"] == player_id and len(team["members"]) > 0:
            team["owner"] = team["members"][0]

        # 如果队伍为空,解散
        if len(team["members"]) == 0:
            del self.teams[team_id]

        # 保存数据
        self._SaveTeams()

        self._BroadcastToTeam(team_id, "§c{} 离开了队伍!".format(player_id))

        return True

    def GetTeamMembers(self, team_id):
        """获取队伍成员"""
        team = self.teams.get(team_id)
        return team["members"] if team else []

    def _BroadcastToTeam(self, team_id, message):
        """向队伍所有成员广播消息"""
        members = self.GetTeamMembers(team_id)
        for member_id in members:
            self.msg_comp.NotifyOneMessage(member_id, message, "§e队伍")

    def _SaveTeams(self):
        """保存队伍数据"""
        level_id = serverApi.GetLevelId()
        data_str = json.dumps({
            "teams": self.teams,
            "player_teams": self.player_teams
        })
        self.extra_data_comp.SetExtraData(level_id, "team_data", data_str)

    def Destroy(self):
        """系统销毁时清理"""
        self.UnListenAllEvents()
'''

# 队伍系统玩法包配置
TEAM_SYSTEM_PACK = {
    "id": "team-system",
    "name": "队伍系统",
    "keywords": [
        "队伍", "团队", "组队", "公会", "帮派", "成员",
        "team", "party", "group", "guild", "clan", "member"
    ],
    "category": "多人玩法",
    "difficulty": "中等",
    "estimated_time": "15分钟",

    "description": "实现队伍系统,支持创建队伍、加入队伍、离开队伍、队伍聊天等功能",

    "implementation_guide": {
        "principle": "使用Tag组件标记队伍成员 → ExtraData持久化存储队伍数据 → 提供CreateTeam/JoinTeam/LeaveTeam接口",

        "modsdk_apis": [
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
                "name": "tagComp.RemoveEntityTag",
                "type": "组件方法",
                "purpose": "移除实体标签",
                "params": {
                    "entityId": "实体ID (str)",
                    "tag": "标签名称 (str)"
                },
                "doc_path": "MODSDK/Component/tagComp.md",
                "common_pitfall": "移除不存在的标签不会报错"
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
            "file": "mod/server/system/TeamServerSystem.py",
            "content": TEAM_SYSTEM_CODE
        },

        "config_guide": {
            "description": "调用CreateTeam创建队伍",
            "example": {
                "team_id": "team_001",
                "owner_id": "player_1",
                "team_name": "勇者小队"
            }
        },

        "common_issues": [
            {
                "problem": "队伍数据丢失",
                "cause": "SetExtraData未被调用",
                "solution": "确保每次队伍变动后调用_SaveTeams()"
            },
            {
                "problem": "队员无法看到队伍消息",
                "cause": "_BroadcastToTeam逻辑错误",
                "solution": "确保遍历所有members并发送消息"
            },
            {
                "problem": "队长离开后队伍解散",
                "cause": "未实现队长转让逻辑",
                "solution": "在LeaveTeam中添加队长转让代码"
            }
        ],

        "related_gameplay": [
            {
                "name": "排行榜系统",
                "similarity": "多人数据管理",
                "extension": "可扩展为队伍排行榜"
            },
            {
                "name": "区域保护系统",
                "similarity": "权限管理",
                "reusable_code": "成员权限验证"
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
    if "team-system" in existing_ids:
        print("[SKIP] Team System pack already exists")
        return

    # 添加新玩法包
    kb["gameplay_patterns"].append(TEAM_SYSTEM_PACK)

    # 更新元数据
    kb["metadata"]["total_patterns"] = len(kb["gameplay_patterns"])

    # 保存
    with open(KB_PATH, 'w', encoding='utf-8') as f:
        json.dump(kb, f, ensure_ascii=False, indent=2)

    print("[SUCCESS] Team System gameplay pack added!")
    print(f"[INFO] Total patterns: {kb['metadata']['total_patterns']}")
    print(f"[INFO] Keywords: {', '.join(TEAM_SYSTEM_PACK['keywords'][:8])}")

if __name__ == "__main__":
    main()
