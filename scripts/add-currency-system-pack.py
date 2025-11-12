# -*- coding: utf-8 -*-
"""
添加货币系统玩法包到知识库
"""
import json
import os

# 知识库路径
KB_PATH = "D:/EcWork/基于Claude的MODSDK开发工作流/.claude/knowledge-base.json"

# 货币系统完整代码(精简版)
CURRENCY_SYSTEM_CODE = '''# -*- coding: utf-8 -*-
from __future__ import print_function
from mod.server.system.serverSystem import ServerSystem
import mod.server.extraServerApi as serverApi

class CurrencyServerSystem(ServerSystem):
    """货币系统"""

    def __init__(self, namespace, systemName):
        super(CurrencyServerSystem, self).__init__(namespace, systemName)

        # 货币缓存
        self.player_money = {}

        # 初始金币
        self.initial_money = 1000

        self.extra_data_comp = None
        self.msg_comp = None
        self.Create()

    def Create(self):
        """初始化组件和事件监听"""
        level_id = serverApi.GetLevelId()
        comp_factory = serverApi.GetEngineCompFactory()

        self.extra_data_comp = comp_factory.CreateExtraData(level_id)
        self.msg_comp = comp_factory.CreateMsg(level_id)

        # 监听玩家加入事件
        self.ListenForEvent(
            serverApi.GetEngineNamespace(),
            serverApi.GetEngineSystemName(),
            "AddServerPlayerEvent",
            self,
            self.OnPlayerJoin
        )

    def OnPlayerJoin(self, args):
        """玩家加入时初始化货币"""
        player_id = args["id"]
        money = self._LoadMoney(player_id)

        if money == 0:
            money = self.initial_money
            self._SaveMoney(player_id, money)

        self.player_money[player_id] = money
        print("[Currency] 玩家 {} 金币: {}".format(player_id, money))

    def AddMoney(self, player_id, amount):
        """增加金币"""
        current = self.player_money.get(player_id, 0)
        new_money = current + amount
        self.player_money[player_id] = new_money
        self._SaveMoney(player_id, new_money)

        self.msg_comp.NotifyOneMessage(
            player_id,
            "§a+{} 金币 (余额: {})".format(amount, new_money),
            "§e货币"
        )
        return new_money

    def RemoveMoney(self, player_id, amount):
        """扣除金币"""
        current = self.player_money.get(player_id, 0)
        if current < amount:
            return False

        new_money = current - amount
        self.player_money[player_id] = new_money
        self._SaveMoney(player_id, new_money)

        self.msg_comp.NotifyOneMessage(
            player_id,
            "§c-{} 金币 (余额: {})".format(amount, new_money),
            "§e货币"
        )
        return True

    def GetMoney(self, player_id):
        """获取金币"""
        return self.player_money.get(player_id, 0)

    def _LoadMoney(self, player_id):
        """从ExtraData加载金币"""
        money_str = self.extra_data_comp.GetExtraData(player_id, "currency_money")
        return int(money_str) if money_str else 0

    def _SaveMoney(self, player_id, money):
        """保存金币到ExtraData"""
        self.extra_data_comp.SetExtraData(player_id, "currency_money", str(money))

    def Destroy(self):
        """系统销毁时清理"""
        self.UnListenAllEvents()
'''

# 货币系统玩法包配置
CURRENCY_SYSTEM_PACK = {
    "id": "currency-system",
    "name": "货币系统",
    "keywords": [
        "货币", "金币", "经济", "钱", "余额", "交易",
        "currency", "money", "economy", "coin", "balance", "transaction"
    ],
    "category": "经济玩法",
    "difficulty": "简单",
    "estimated_time": "10分钟",

    "description": "实现货币系统,支持金币增加、扣除、查询、持久化存储等功能",

    "implementation_guide": {
        "principle": "使用ExtraData组件持久化存储玩家金币 → 提供AddMoney/RemoveMoney/GetMoney接口 → 内存缓存提高性能",

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
                "common_pitfall": "仅支持字符串,需要str()和int()转换"
            },
            {
                "name": "AddServerPlayerEvent",
                "type": "事件",
                "trigger": "玩家加入服务器时触发",
                "fields": {
                    "id": "玩家ID (str)"
                },
                "doc_path": "MODSDK/事件/玩家.md",
                "common_pitfall": "玩家重连不会触发,需用PlayerRespawnEvent补充"
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
            "file": "mod/server/system/CurrencyServerSystem.py",
            "content": CURRENCY_SYSTEM_CODE
        },

        "config_guide": {
            "description": "配置初始金币数量",
            "example": {
                "initial_money": 5000
            }
        },

        "common_issues": [
            {
                "problem": "金币数据丢失",
                "cause": "SetExtraData未被调用或返回False",
                "solution": "确保每次金币变动后调用_SaveMoney()"
            },
            {
                "problem": "扣款失败",
                "cause": "余额不足",
                "solution": "调用RemoveMoney前先检查GetMoney()返回值"
            },
            {
                "problem": "新玩家金币为0",
                "cause": "初始化逻辑错误",
                "solution": "在OnPlayerJoin中判断money==0时赋予初始金币"
            }
        ],

        "related_gameplay": [
            {
                "name": "自定义商店系统",
                "similarity": "货币管理",
                "reusable_code": "金币增减和存储逻辑"
            },
            {
                "name": "经验掉落系统",
                "similarity": "数值管理",
                "extension": "可扩展为多货币系统"
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
    if "currency-system" in existing_ids:
        print("[SKIP] Currency System pack already exists")
        return

    # 添加新玩法包
    kb["gameplay_patterns"].append(CURRENCY_SYSTEM_PACK)

    # 更新元数据
    kb["metadata"]["total_patterns"] = len(kb["gameplay_patterns"])

    # 保存
    with open(KB_PATH, 'w', encoding='utf-8') as f:
        json.dump(kb, f, ensure_ascii=False, indent=2)

    print("[SUCCESS] Currency System gameplay pack added!")
    print(f"[INFO] Total patterns: {kb['metadata']['total_patterns']}")
    print(f"[INFO] Keywords: {', '.join(CURRENCY_SYSTEM_PACK['keywords'][:8])}")

if __name__ == "__main__":
    main()
