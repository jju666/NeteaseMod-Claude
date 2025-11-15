# -*- coding: utf-8 -*-
"""
货币管理器

功能:
- 检查玩家拥有的货币数量
- 扣除玩家货币
- 支持多种货币类型（铁锭、金锭、钻石、绿宝石、铜锭、经验）

参考老项目:
- Parts/BedWarsShop/data/ShopCurrency.py
- 老项目使用ShopCurrency类管理货币
- 新项目使用静态方法简化实现
"""

from __future__ import print_function


class CurrencyManager(object):
    """
    货币管理器

    提供静态方法用于检查和扣除玩家货币
    """

    # 货币类型映射到物品ID
    CURRENCY_ITEMS = {
        'iron': 'minecraft:iron_ingot',
        'gold': 'minecraft:gold_ingot',
        'diamond': 'minecraft:diamond',
        'emerald': 'minecraft:emerald',
        'copper': 'minecraft:copper_ingot',
        'exp': 'experience'  # 特殊标记，使用经验等级作为货币
    }

    @staticmethod
    def get_player_currency_count(player_id, currency_type):
        """
        获取玩家拥有的指定货币数量

        Args:
            player_id (str): 玩家ID
            currency_type (str): 货币类型 ('iron', 'gold', 'diamond', 'emerald', 'copper', 'exp')

        Returns:
            int: 货币数量
        """
        try:
            import mod.server.extraServerApi as serverApi

            # 特殊处理：经验货币
            if currency_type == 'exp':
                exp_comp = serverApi.GetEngineCompFactory().CreateExp(player_id)
                player_level = exp_comp.GetPlayerLevel()
                return player_level

            # 获取对应的物品ID
            item_id = CurrencyManager.CURRENCY_ITEMS.get(currency_type)
            if not item_id:
                print("[ERROR] [CurrencyManager] 无效的货币类型: {}".format(currency_type))
                return 0

            # 获取物品组件
            item_comp = serverApi.GetEngineCompFactory().CreateItem(player_id)

            # 遍历背包统计物品数量
            total_count = 0
            for slot in range(36):  # 背包有36个格子
                item_dict = item_comp.GetPlayerItem(
                    serverApi.GetMinecraftEnum().ItemPosType.INVENTORY,
                    slot
                )

                if item_dict and item_dict.get('itemName') == item_id:
                    total_count += item_dict.get('count', 0)

            return total_count

        except Exception as e:
            print("[ERROR] [CurrencyManager] 获取玩家货币失败: player={}, currency={}, error={}".format(
                player_id, currency_type, str(e)))
            import traceback
            traceback.print_exc()
            return 0

    @staticmethod
    def can_afford(player_id, price):
        """
        检查玩家是否有足够的货币支付价格

        Args:
            player_id (str): 玩家ID
            price (dict): 价格字典 {'currency': 'iron', 'amount': 10}

        Returns:
            bool: 是否有足够货币
        """
        currency_type = price.get('currency')
        amount = price.get('amount', 0)

        if not currency_type or amount <= 0:
            return True

        player_have = CurrencyManager.get_player_currency_count(player_id, currency_type)
        return player_have >= amount

    @staticmethod
    def pay_price(player_id, price, skip_check=False):
        """
        扣除玩家货币

        Args:
            player_id (str): 玩家ID
            price (dict): 价格字典 {'currency': 'iron', 'amount': 10}
            skip_check (bool): 是否跳过余额检查

        Returns:
            bool: 是否成功扣除
        """
        try:
            currency_type = price.get('currency')
            amount = price.get('amount', 0)

            if not currency_type or amount <= 0:
                return True

            # 检查余额
            if not skip_check and not CurrencyManager.can_afford(player_id, price):
                print("[WARN] [CurrencyManager] 货币不足: player={}, currency={}, need={}, have={}".format(
                    player_id, currency_type, amount,
                    CurrencyManager.get_player_currency_count(player_id, currency_type)))
                return False

            import mod.server.extraServerApi as serverApi

            # 特殊处理：经验货币
            if currency_type == 'exp':
                exp_comp = serverApi.GetEngineCompFactory().CreateExp(player_id)
                current_level = exp_comp.GetPlayerLevel()
                if current_level < amount:
                    print("[WARN] [CurrencyManager] 经验等级不足: player={}, need={}, have={}".format(
                        player_id, amount, current_level))
                    return False
                # 扣除经验等级
                exp_comp.SetPlayerLevel(current_level - amount)
                print("[INFO] [CurrencyManager] 经验扣除成功: player={}, amount={}, new_level={}".format(
                    player_id, amount, current_level - amount))
                return True

            # 获取对应的物品ID
            item_id = CurrencyManager.CURRENCY_ITEMS.get(currency_type)
            if not item_id:
                print("[ERROR] [CurrencyManager] 无效的货币类型: {}".format(currency_type))
                return False

            item_comp = serverApi.GetEngineCompFactory().CreateItem(player_id)

            # 扣除货币
            remain_amount = amount
            for slot in range(36):
                if remain_amount <= 0:
                    break

                item_dict = item_comp.GetPlayerItem(
                    serverApi.GetMinecraftEnum().ItemPosType.INVENTORY,
                    slot
                )

                if item_dict and item_dict.get('itemName') == item_id:
                    item_count = item_dict.get('count', 0)

                    if item_count >= remain_amount:
                        # 这个槽位足够扣除
                        item_comp.SetInvItemNum(slot, item_count - remain_amount)
                        remain_amount = 0
                    else:
                        # 这个槽位不够，全部扣除
                        item_comp.SetInvItemNum(slot, 0)
                        remain_amount -= item_count

            if remain_amount > 0:
                print("[ERROR] [CurrencyManager] 货币扣除未完成: player={}, currency={}, remain={}".format(
                    player_id, currency_type, remain_amount))
                return False

            print("[INFO] [CurrencyManager] 货币扣除成功: player={}, currency={}, amount={}".format(
                player_id, currency_type, amount))
            return True

        except Exception as e:
            print("[ERROR] [CurrencyManager] 扣除货币失败: player={}, price={}, error={}".format(
                player_id, price, str(e)))
            import traceback
            traceback.print_exc()
            return False

    @staticmethod
    def give_currency(player_id, currency_type, amount):
        """
        给予玩家货币

        Args:
            player_id (str): 玩家ID
            currency_type (str): 货币类型 ('iron', 'gold', 'diamond', 'emerald', 'copper', 'exp')
            amount (int): 数量

        Returns:
            bool: 是否成功
        """
        try:
            if amount <= 0:
                return True

            import mod.server.extraServerApi as serverApi

            # 特殊处理：经验货币
            if currency_type == 'exp':
                exp_comp = serverApi.GetEngineCompFactory().CreateExp(player_id)
                current_level = exp_comp.GetPlayerLevel()
                exp_comp.SetPlayerLevel(current_level + amount)
                print("[INFO] [CurrencyManager] 经验给予成功: player={}, amount={}, new_level={}".format(
                    player_id, amount, current_level + amount))
                return True

            # 获取对应的物品ID
            item_id = CurrencyManager.CURRENCY_ITEMS.get(currency_type)
            if not item_id:
                print("[ERROR] [CurrencyManager] 无效的货币类型: {}".format(currency_type))
                return False

            item_comp = serverApi.GetEngineCompFactory().CreateItem(player_id)

            # 给予物品
            item_dict = {
                'itemName': item_id,
                'count': amount,
                'auxValue': 0
            }

            success = item_comp.SpawnItemToPlayerInv(item_dict, player_id)

            if success:
                print("[INFO] [CurrencyManager] 货币给予成功: player={}, currency={}, amount={}".format(
                    player_id, currency_type, amount))
            else:
                print("[ERROR] [CurrencyManager] 货币给予失败: player={}, currency={}, amount={}".format(
                    player_id, currency_type, amount))

            return success

        except Exception as e:
            print("[ERROR] [CurrencyManager] 给予货币异常: player={}, currency={}, amount={}, error={}".format(
                player_id, currency_type, amount, str(e)))
            import traceback
            traceback.print_exc()
            return False

    @staticmethod
    def refund_price(player_id, price):
        """
        退款给玩家（给予玩家货币）

        Args:
            player_id (str): 玩家ID
            price (dict): 价格字典 {'currency': 'iron', 'amount': 10}

        Returns:
            bool: 是否成功退款
        """
        try:
            currency_type = price.get('currency')
            amount = price.get('amount', 0)

            if not currency_type or amount <= 0:
                return True

            # 调用give_currency实现退款
            result = CurrencyManager.give_currency(player_id, currency_type, amount)

            if result:
                print("[INFO] [CurrencyManager] 退款成功: player={}, currency={}, amount={}".format(
                    player_id, currency_type, amount))
            else:
                print("[WARN] [CurrencyManager] 退款失败: player={}, currency={}, amount={}".format(
                    player_id, currency_type, amount))

            return result

        except Exception as e:
            print("[ERROR] [CurrencyManager] 退款异常: player={}, price={}, error={}".format(
                player_id, price, str(e)))
            import traceback
            traceback.print_exc()
            return False

    @staticmethod
    def format_player_currencies(player_id):
        """
        格式化玩家所有货币数量为显示字符串

        Args:
            player_id (str): 玩家ID

        Returns:
            str: 格式化的货币字符串，例如: "铁: 10 | 金: 5 | 钻: 2 | 绿宝石: 1 | 铜: 8 | 经验: 3"
        """
        try:
            # 货币类型列表（按优先级排序）
            currency_types = ['iron', 'gold', 'diamond', 'emerald', 'copper', 'exp']

            # 货币显示名称映射
            currency_names = {
                'iron': u'铁',
                'gold': u'金',
                'diamond': u'钻',
                'emerald': u'绿宝石',
                'copper': u'铜',
                'exp': u'经验'
            }

            # 货币颜色映射（用于UI显示）
            currency_colors = {
                'iron': '§7',      # 灰色
                'gold': '§6',      # 金色
                'diamond': '§b',   # 青色
                'emerald': '§a',   # 绿色
                'copper': '§c',    # 红色
                'exp': '§e'        # 黄色
            }

            # 收集所有货币信息
            currency_parts = []
            for currency_type in currency_types:
                count = CurrencyManager.get_player_currency_count(player_id, currency_type)
                name = currency_names.get(currency_type, currency_type)
                color = currency_colors.get(currency_type, '§f')

                # 格式化单个货币：颜色 + 名称 + 数量
                currency_parts.append(u"{}{}: {}§r".format(color, name, count))

            # 用分隔符连接
            return u" | ".join(currency_parts)

        except Exception as e:
            print("[ERROR] [CurrencyManager] 格式化货币显示失败: player={}, error={}".format(
                player_id, str(e)))
            import traceback
            traceback.print_exc()
            return u"货币信息获取失败"
