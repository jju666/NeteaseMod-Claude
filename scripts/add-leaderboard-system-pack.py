# -*- coding: utf-8 -*-
"""
添加排行榜系统玩法包到知识库
"""
import json
import os

# 知识库路径
KB_PATH = "D:/EcWork/基于Claude的MODSDK开发工作流/.claude/knowledge-base.json"

# 排行榜系统完整代码(精简版)
LEADERBOARD_SYSTEM_CODE = '''# -*- coding: utf-8 -*-
from __future__ import print_function
from mod.server.system.serverSystem import ServerSystem
import mod.server.extraServerApi as serverApi

class LeaderboardServerSystem(ServerSystem):
    """排行榜系统"""

    def __init__(self, namespace, systemName):
        super(LeaderboardServerSystem, self).__init__(namespace, systemName)

        # 排行榜配置
        self.leaderboards = {
            "kills": {"objective": "kills", "display": "击杀排行"},
            "wealth": {"objective": "wealth", "display": "财富排行"},
            "playtime": {"objective": "playtime", "display": "在线时长排行"}
        }

        self.scoreboard_comp = None
        self.msg_comp = None
        self.extra_data_comp = None
        self.Create()

    def Create(self):
        """初始化组件"""
        level_id = serverApi.GetLevelId()
        comp_factory = serverApi.GetEngineCompFactory()

        self.scoreboard_comp = comp_factory.CreateScoreBoard(level_id)
        self.msg_comp = comp_factory.CreateMsg(level_id)
        self.extra_data_comp = comp_factory.CreateExtraData(level_id)

        # 创建计分板目标
        for lb_id, config in self.leaderboards.items():
            self.scoreboard_comp.CreateScoreObjective(
                config["objective"],
                config["display"]
            )

    def UpdateScore(self, player_id, leaderboard_id, score):
        """更新玩家分数"""
        if leaderboard_id not in self.leaderboards:
            return False

        objective = self.leaderboards[leaderboard_id]["objective"]
        self.scoreboard_comp.SetScoreByName(objective, player_id, score)

        print("[Leaderboard] 更新 {} 排行榜 {}: {}".format(
            leaderboard_id, player_id, score
        ))
        return True

    def AddScore(self, player_id, leaderboard_id, amount):
        """增加玩家分数"""
        if leaderboard_id not in self.leaderboards:
            return False

        objective = self.leaderboards[leaderboard_id]["objective"]
        current = self.GetScore(player_id, leaderboard_id)
        new_score = current + amount

        self.scoreboard_comp.SetScoreByName(objective, player_id, new_score)
        return True

    def GetScore(self, player_id, leaderboard_id):
        """获取玩家分数"""
        if leaderboard_id not in self.leaderboards:
            return 0

        objective = self.leaderboards[leaderboard_id]["objective"]
        score = self.scoreboard_comp.GetPlayerScore(objective, player_id)
        return score if score is not None else 0

    def GetTopPlayers(self, leaderboard_id, limit=10):
        """获取排行榜前N名"""
        if leaderboard_id not in self.leaderboards:
            return []

        objective = self.leaderboards[leaderboard_id]["objective"]

        # 获取所有分数
        all_scores = self.scoreboard_comp.GetScoreList(objective)

        # 按分数降序排序
        sorted_scores = sorted(all_scores, key=lambda x: x["score"], reverse=True)

        # 返回前N名
        return sorted_scores[:limit]

    def ShowLeaderboard(self, player_id, leaderboard_id):
        """向玩家显示排行榜"""
        if leaderboard_id not in self.leaderboards:
            return

        config = self.leaderboards[leaderboard_id]
        top_players = self.GetTopPlayers(leaderboard_id, 10)

        message = "§e===== {} =====\\n".format(config["display"])
        for i, entry in enumerate(top_players, 1):
            message += "§a{}. {} - {}分\\n".format(
                i, entry["playerName"], entry["score"]
            )

        self.msg_comp.NotifyOneMessage(player_id, message, "§e排行榜")

    def Destroy(self):
        """系统销毁时清理"""
        self.UnListenAllEvents()
'''

# 排行榜系统玩法包配置
LEADERBOARD_SYSTEM_PACK = {
    "id": "leaderboard-system",
    "name": "排行榜系统",
    "keywords": [
        "排行榜", "排名", "榜单", "计分板", "竞赛", "比赛",
        "leaderboard", "ranking", "scoreboard", "top", "competition", "contest"
    ],
    "category": "多人玩法",
    "difficulty": "中等",
    "estimated_time": "12分钟",

    "description": "实现排行榜系统,支持多维度排名、实时更新、排行榜显示等功能",

    "implementation_guide": {
        "principle": "使用Scoreboard组件存储分数 → CreateScoreObjective创建计分项 → SetScoreByName更新分数 → GetScoreList获取排名",

        "modsdk_apis": [
            {
                "name": "scoreboardComp.CreateScoreObjective",
                "type": "组件方法",
                "purpose": "创建计分板目标",
                "params": {
                    "objectiveName": "目标名称 (str)",
                    "displayName": "显示名称 (str)"
                },
                "returns": "是否成功 (bool)",
                "doc_path": "MODSDK/Component/scoreboardComp.md",
                "common_pitfall": "objectiveName必须唯一"
            },
            {
                "name": "scoreboardComp.SetScoreByName",
                "type": "组件方法",
                "purpose": "设置玩家分数",
                "params": {
                    "objectiveName": "目标名称 (str)",
                    "playerName": "玩家名称 (str)",
                    "score": "分数 (int)"
                },
                "returns": "是否成功 (bool)",
                "doc_path": "MODSDK/Component/scoreboardComp.md",
                "common_pitfall": "score必须为整数"
            },
            {
                "name": "scoreboardComp.GetPlayerScore",
                "type": "组件方法",
                "purpose": "获取玩家分数",
                "params": {
                    "objectiveName": "目标名称 (str)",
                    "playerId": "玩家ID (str)"
                },
                "returns": "分数 (int) or None",
                "doc_path": "MODSDK/Component/scoreboardComp.md",
                "common_pitfall": "玩家无分数时返回None"
            },
            {
                "name": "scoreboardComp.GetScoreList",
                "type": "组件方法",
                "purpose": "获取所有分数列表",
                "params": {
                    "objectiveName": "目标名称 (str)"
                },
                "returns": "分数列表 (list of dict)",
                "doc_path": "MODSDK/Component/scoreboardComp.md",
                "common_pitfall": "返回格式: [{'playerName': str, 'score': int}, ...]"
            }
        ],

        "complete_code": {
            "file": "mod/server/system/LeaderboardServerSystem.py",
            "content": LEADERBOARD_SYSTEM_CODE
        },

        "config_guide": {
            "description": "在leaderboards中配置排行榜",
            "example": {
                "deaths": {
                    "objective": "deaths",
                    "display": "死亡次数排行"
                }
            },
            "fields": {
                "objective": "计分板目标名称 (str)",
                "display": "排行榜显示名称 (str)"
            }
        },

        "common_issues": [
            {
                "problem": "分数不更新",
                "cause": "SetScoreByName调用失败或objective不存在",
                "solution": "确保objective已通过CreateScoreObjective创建"
            },
            {
                "problem": "排行榜显示乱序",
                "cause": "未正确排序GetScoreList返回的数据",
                "solution": "使用sorted()按score字段降序排序"
            },
            {
                "problem": "玩家名称显示为ID",
                "cause": "使用了playerId而非playerName",
                "solution": "GetScoreList返回的是playerName,可直接使用"
            }
        ],

        "related_gameplay": [
            {
                "name": "经验掉落系统",
                "similarity": "数值统计",
                "extension": "可扩展为经验排行榜"
            },
            {
                "name": "队伍系统",
                "similarity": "多人数据管理",
                "reusable_code": "队伍排行榜"
            },
            {
                "name": "货币系统",
                "similarity": "数值记录",
                "extension": "可扩展为财富排行榜"
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
    if "leaderboard-system" in existing_ids:
        print("[SKIP] Leaderboard System pack already exists")
        return

    # 添加新玩法包
    kb["gameplay_patterns"].append(LEADERBOARD_SYSTEM_PACK)

    # 更新元数据
    kb["metadata"]["total_patterns"] = len(kb["gameplay_patterns"])

    # 保存
    with open(KB_PATH, 'w', encoding='utf-8') as f:
        json.dump(kb, f, ensure_ascii=False, indent=2)

    print("[SUCCESS] Leaderboard System gameplay pack added!")
    print(f"[INFO] Total patterns: {kb['metadata']['total_patterns']}")
    print(f"[INFO] Keywords: {', '.join(LEADERBOARD_SYSTEM_PACK['keywords'][:8])}")

if __name__ == "__main__":
    main()
