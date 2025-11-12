# -*- coding: utf-8 -*-
"""
添加自定义商店系统玩法包到知识库
"""
import json
import os

# 知识库路径
KB_PATH = "D:/EcWork/基于Claude的MODSDK开发工作流/.claude/knowledge-base.json"

# 自定义商店系统完整代码(精简版 - 保留核心逻辑)
CUSTOM_SHOP_CODE = '''# -*- coding: utf-8 -*-
from __future__ import print_function
from mod.server.system.serverSystem import ServerSystem
import mod.server.extraServerApi as serverApi
import json

class CustomShopServerSystem(ServerSystem):
    """自定义商店系统"""

    def __init__(self, namespace, systemName):
        super(CustomShopServerSystem, self).__init__(namespace, systemName)

        # 商品配置表
        self.shop_items = {
            "diamond_sword": {
                "price": 100,
                "itemName": "minecraft:diamond_sword",
                "count": 1,
                "enchantData": [(0, 5)]  # 锋利5
            },
            "gold_block": {
                "price": 50,
                "itemName": "minecraft:gold_block",
                "count": 10,
                "enchantData": []
            },
            "diamond": {
                "price": 30,
                "itemName": "minecraft:diamond",
                "count": 64,
                "enchantData": []
            }
        }

        # 初始金币
        self.initial_money = 1000

        # 玩家金币缓存
        self.player_money = {}

        self.extra_data_comp = None
        self.item_comp = None
        self.msg_comp = None
        self.Create()

    def Create(self):
        """初始化组件和事件监听"""
        level_id = serverApi.GetLevelId()

        # 创建组件
        comp_factory = serverApi.GetEngineCompFactory()
        self.extra_data_comp = comp_factory.CreateExtraData(level_id)
        self.item_comp = comp_factory.CreateItem(level_id)
        self.msg_comp = comp_factory.CreateMsg(level_id)

        # 监听玩家加入事件
        self.ListenForEvent(
            serverApi.GetEngineNamespace(),
            serverApi.GetEngineSystemName(),
            "AddServerPlayerEvent",
            self,
            self.OnPlayerJoin
        )

        # 监听玩家方块交互事件
        self.ListenForEvent(
            serverApi.GetEngineNamespace(),
            serverApi.GetEngineSystemName(),
            "ServerBlockUseEvent",
            self,
            self.OnBlockUse
        )

        # 监听客户端购买请求
        self.ListenForEvent(
            "MyMod",
            "MyClientSystem",
            "OnShopPurchaseRequest",
            self,
            self.OnPurchaseRequest
        )

    def OnPlayerJoin(self, args):
        """玩家加入时初始化金币"""
        player_id = args["id"]
        money = self._LoadPlayerMoney(player_id)

        # 新玩家赋予初始金币
        if money == 0:
            money = self.initial_money
            self._SavePlayerMoney(player_id, money)

        self.player_money[player_id] = money
        print("[ShopSystem] 玩家 {} 加入,金币: {}".format(player_id, money))

    def OnBlockUse(self, args):
        """玩家右键方块时打开商店"""
        player_id = args["playerId"]
        block_name = args["blockName"]

        # 仅在特定方块(如绿宝石块)上打开商店
        if block_name == "minecraft:emerald_block":
            # 通知客户端打开商店UI
            money = self.player_money.get(player_id, 0)
            event_data = self.CreateEventData()
            event_data["money"] = money
            event_data["items"] = self.shop_items

            self.NotifyToClient(player_id, "OpenShopUI", event_data)
            print("[ShopSystem] 玩家 {} 打开商店".format(player_id))

    def OnPurchaseRequest(self, args):
        """处理购买请求 - 核心交易逻辑"""
        player_id = args.get("playerId")
        item_id = args.get("itemId")
        count = args.get("count", 1)

        if not player_id or not item_id:
            return

        print("[ShopSystem] 玩家 {} 购买请求: {} x{}".format(player_id, item_id, count))

        # 步骤1: 验证物品是否存在
        if item_id not in self.shop_items:
            self._SendPurchaseResult(player_id, False, "Invalid item")
            return

        item_config = self.shop_items[item_id]

        # 步骤2: 从服务端配置计算总价格(防止客户端篡改)
        total_price = item_config["price"] * count
        current_money = self.player_money.get(player_id, 0)

        # 步骤3: 验证玩家余额
        if current_money < total_price:
            self._SendPurchaseResult(
                player_id,
                False,
                "Insufficient money. Need: {}, Have: {}".format(total_price, current_money)
            )
            return

        # 步骤4: 扣除货币
        new_money = current_money - total_price
        self.player_money[player_id] = new_money
        self._SavePlayerMoney(player_id, new_money)

        # 步骤5: 发放物品
        item_dict = {
            "itemName": item_config["itemName"],
            "count": item_config["count"] * count
        }

        if item_config.get("enchantData"):
            item_dict["enchantData"] = item_config["enchantData"]

        try:
            self.item_comp.SpawnItemToPlayerInv(item_dict, player_id, 0)
            print("[ShopSystem] 物品发放成功: {}".format(item_dict))
        except Exception as e:
            # 失败时回滚货币
            self.player_money[player_id] = current_money
            self._SavePlayerMoney(player_id, current_money)
            print("[ShopSystem] 物品发放失败: {}".format(e))
            self._SendPurchaseResult(player_id, False, "Failed to give item")
            return

        # 步骤6: 记录交易历史
        self._RecordTransaction(player_id, item_id, total_price, count)

        # 步骤7: 发送成功响应
        self._SendPurchaseResult(player_id, True, "Purchase successful", new_money)

        # 步骤8: 播放成功提示
        self.msg_comp.NotifyOneMessage(
            player_id,
            "Purchase successful! Remaining money: {}".format(new_money),
            "Shop"
        )

    def _LoadPlayerMoney(self, player_id):
        """从ExtraData加载玩家金币"""
        money_str = self.extra_data_comp.GetExtraData(player_id, "shop_money")
        return int(money_str) if money_str else 0

    def _SavePlayerMoney(self, player_id, money):
        """保存玩家金币到ExtraData"""
        success = self.extra_data_comp.SetExtraData(
            player_id,
            "shop_money",
            str(money)
        )
        if not success:
            print("[ShopSystem] 保存金币失败: {}".format(player_id))
        return success

    def _RecordTransaction(self, player_id, item_id, price, count):
        """记录交易历史"""
        history_str = self.extra_data_comp.GetExtraData(
            player_id,
            "shop_transaction_history"
        )
        history = json.loads(history_str) if history_str else []

        # 限制历史记录数量
        if len(history) >= 100:
            history = history[-99:]

        transaction = {
            "itemId": item_id,
            "price": price,
            "count": count
        }
        history.append(transaction)

        self.extra_data_comp.SetExtraData(
            player_id,
            "shop_transaction_history",
            json.dumps(history)
        )

    def _SendPurchaseResult(self, player_id, success, message, new_money=None):
        """发送购买结果给客户端"""
        event_data = self.CreateEventData()
        event_data["success"] = success
        event_data["message"] = message
        event_data["money"] = new_money if new_money is not None else self.player_money.get(player_id, 0)

        self.NotifyToClient(player_id, "OnShopPurchaseResult", event_data)

    def Destroy(self):
        """系统销毁时清理"""
        self.UnListenAllEvents()
'''

# 自定义商店系统玩法包配置
CUSTOM_SHOP_PACK = {
    "id": "custom-shop-system",
    "name": "自定义商店",
    "keywords": [
        "商店", "购买", "交易", "货币", "商城", "店铺", "商品",
        "库存", "价格", "金币", "计分板", "scoreboard",
        "shop", "buy", "sell", "trade", "store", "merchant", "currency"
    ],
    "category": "经济玩法",
    "difficulty": "中等",
    "estimated_time": "15分钟",

    "description": "实现自定义商店系统,支持商品购买、货币管理、交易记录、库存系统等功能",

    "implementation_guide": {
        "principle": "服务端监听ServerBlockUseEvent → 判断触发方块 → NotifyToClient发送商品列表 → 客户端显示UI → 玩家购买后发送请求 → 服务端验证余额+扣除货币+发放物品 → 记录交易历史",

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
                "common_pitfall": "该事件tick执行,需注意效率;不能取消对方块使用物品的行为"
            },
            {
                "name": "NotifyToClient / NotifyToServer",
                "type": "双端通信方法",
                "purpose": "服务端与客户端之间的事件通知",
                "params": {
                    "playerId": "目标玩家ID (str,NotifyToClient需要)",
                    "eventName": "自定义事件名称 (str)",
                    "eventData": "事件数据字典 (dict)"
                },
                "doc_path": "MODSDK/系统/事件通信.md",
                "common_pitfall": "eventData不能包含tuple,必须使用list或dict;数据大小建议<10KB"
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
                "common_pitfall": "ExtraData仅支持字符串,需要json.dumps/loads转换;字符串总大小建议<64KB/玩家"
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
                "common_pitfall": "itemDict必须包含itemName和count;count超过最大堆叠数会失败;失败时应回滚货币"
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
            "file": "mod/server/system/CustomShopServerSystem.py",
            "content": CUSTOM_SHOP_CODE
        },

        "config_guide": {
            "description": "在shop_items中配置商品信息,包括价格、物品ID、数量、附魔等",
            "example": {
                "enchanted_book": {
                    "price": 200,
                    "itemName": "minecraft:enchanted_book",
                    "count": 1,
                    "enchantData": [(0, 10)]
                }
            },
            "fields": {
                "price": "购买价格 (int)",
                "itemName": "物品ID (str,格式: namespace:item)",
                "count": "发放数量 (int)",
                "enchantData": "附魔数据 (list,可选)"
            }
        },

        "common_issues": [
            {
                "problem": "购买后物品没有给予到玩家背包",
                "cause": "SpawnItemToPlayerInv()调用失败,可能是itemDict字段不完整或背包已满",
                "solution": "添加try-except捕获异常;确保itemDict包含itemName和count;失败时回滚金币扣除"
            },
            {
                "problem": "金币数据在重启后丢失",
                "cause": "SetExtraData()未被正确调用或返回False",
                "solution": "确保_SavePlayerMoney()在交易完成后被调用;检查SetExtraData()返回值;使用内存缓存+定期保存策略"
            },
            {
                "problem": "客户端篡改购买请求中的价格信息",
                "cause": "从客户端eventData中直接读取price字段",
                "solution": "严格遵守服务器权威原则:价格仅存储在服务端;客户端仅发送itemId和count;服务端根据itemId查表获取价格"
            },
            {
                "problem": "ServerBlockUseEvent没有触发",
                "cause": "方块不是自定义方块或未注册监听",
                "solution": "使用自定义方块(推荐);或调用AddBlockItemListenForUseEvent注册原生方块监听"
            }
        ],

        "related_gameplay": [
            {
                "name": "NPC对话系统",
                "similarity": "同样使用UI展示选项",
                "reusable_code": "UI框架、选项处理逻辑"
            },
            {
                "name": "经济系统",
                "similarity": "货币管理、交易记录",
                "extension": "扩展支持银行存款、贷款、利息"
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
    if "custom-shop-system" in existing_ids:
        print("[SKIP] Custom Shop System pack already exists")
        return

    # 添加新玩法包
    kb["gameplay_patterns"].append(CUSTOM_SHOP_PACK)

    # 更新元数据
    kb["metadata"]["total_patterns"] = len(kb["gameplay_patterns"])

    # 保存
    with open(KB_PATH, 'w', encoding='utf-8') as f:
        json.dump(kb, f, ensure_ascii=False, indent=2)

    print("[SUCCESS] Custom Shop System gameplay pack added!")
    print(f"[INFO] Total patterns: {kb['metadata']['total_patterns']}")
    print(f"[INFO] Keywords: {', '.join(CUSTOM_SHOP_PACK['keywords'][:8])}")
    print(f"[INFO] Code lines: {len(CUSTOM_SHOP_CODE.splitlines())}")

if __name__ == "__main__":
    main()
