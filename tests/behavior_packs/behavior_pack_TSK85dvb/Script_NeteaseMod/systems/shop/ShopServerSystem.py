# 测试PostToolUse修复-最终版
# 测试atomic_update诊断
# Phase
# -*- coding: utf-8 -*- # 测试atomic_update诊断
"""
商店服务端系统

职责:
- 商品配置管理
- UI数据生成
- 购买流程处理
- 限购规则执行
- 双端通信

设计原则:
- Preset负责NPC管理和玩家交互检测
- System负责所有商店业务逻辑
- 通过事件进行Preset和System间的通信
"""

from __future__ import print_function
import mod.server.extraServerApi as serverApi

# 获取ServerSystem基类
ServerSystem = serverApi.GetServerSystemCls()


class ShopServerSystem(ServerSystem):
    """
    商店服务端系统

    核心功能:
    1. 管理商品配置池 (GOODS_POOL)
    2. 生成UI数据 (generate_ui_dict)
    3. 处理购买请求 (handle_player_buy_goods)
    4. 限购规则检查
    5. 双端通信 (NotifyToClient)

    与ShopPreset的职责边界:
    - ShopPreset: NPC管理、玩家交互检测、事件转发
    - ShopServerSystem: 商店业务逻辑、UI数据生成、购买处理
    """

    def __init__(self, namespace, systemName):
        """
        系统初始化

        Args:
            namespace (str): 命名空间
            systemName (str): 系统名称
        """
        super(ShopServerSystem, self).__init__(namespace, systemName)

        # 商品配置
        self.goods_pool = {}  # dict[goods_id, goods_config] 商品池
        self.shop_configs = {}  # dict[shop_type, shop_config] 商店配置

        # 购买记录 (用于限购检查)
        self.player_purchase_records = {}  # dict[player_id, dict[goods_id, count]]

        # 玩家当前打开的商店类型 (用于刷新UI)
        self.player_shop_types = {}  # dict[player_id, shop_type]

        # ========== ⚠️ 重要：手动调用Create() ==========
        # 说明：网易引擎设计上只自动触发Destroy()，不自动触发Create()
        # 因此需要在__init__中手动调用Create()完成系统初始化
        # 参考：开发规范.md - System生命周期 CRITICAL
        print("[ShopServerSystem] 手动调用Create()完成系统初始化")
        self.Create()

    def Create(self):
        """
        系统创建时的初始化逻辑

        执行步骤:
        1. 加载商品配置
        2. 监听购买事件
        3. 监听队伍更新事件(用于刷新UI)
        """
        print("[ShopServerSystem] Create() 被调用")

        # 1. 加载商品配置
        self._load_shop_configs()

        # 2. 监听购买事件
        from Script_NeteaseMod.modConfig import MOD_NAME
        self.ListenForEvent(
            MOD_NAME,
            "ShopClientSystem",
            "BedWarsShopTryBuy",
            self,
            self.handle_player_buy_goods
        )
        print("[ShopServerSystem] 已注册购买事件监听: BedWarsShopTryBuy")

        # 3. 监听队伍更新事件 (用于刷新UI)
        # TODO: 监听TeamModuleUpdateTeamPlayers事件

    def Destroy(self):
        """
        系统销毁时自动被引擎调用

        清理工作:
        - 清空配置数据
        - 清空购买记录
        """
        print("[ShopServerSystem] Destroy() 被调用")
        self.goods_pool = {}
        self.shop_configs = {}
        self.player_purchase_records = {}

    # ========== 配置加载 ==========

    def _load_shop_configs(self):
        """
        加载商品配置

        从shop_config.py加载GOODS_POOL和SHOP_CONFIG
        将GOODS_POOL转换为字典以便快速查找
        """
        from Script_NeteaseMod.config.shop_config import (
            GOODS_POOL,
            SHOP_CONFIG,
            UPGRADE_SHOP_CONFIG
        )

        # 将GOODS_POOL转换为字典
        self.goods_pool = {g['id']: g for g in GOODS_POOL}

        # 加载商店配置
        # 注意：键名必须与预设配置中的shop_type字段保持一致
        # 参考：商人预设.md - shop_type只有两种值: "items" 和 "upgrade"
        self.shop_configs = {
            'items': SHOP_CONFIG,
            'upgrade': UPGRADE_SHOP_CONFIG  # 修复：使用单数形式'upgrade'而非'upgrades'
        }

        print("[ShopServerSystem] 加载了{}个商品配置".format(len(self.goods_pool)))
        print("[ShopServerSystem] 加载了{}个商店类型配置".format(len(self.shop_configs)))

    # ========== 打开商店UI ==========

    def handle_player_open_shop(self, player_id, team, shop_type):
        """
        处理玩家打开商店

        由ShopPreset调用，当玩家与商店NPC交互时

        Args:
            player_id (str): 玩家ID
            team (str): 队伍ID
            shop_type (str): 商店类型 ("items" / "upgrade")
        """
        print("[ShopServerSystem] 玩家打开商店: player={}, team={}, type={}".format(
            player_id, team, shop_type))

        # 记录玩家当前打开的商店类型（用于购买后刷新UI）
        self.player_shop_types[player_id] = shop_type

        # 1. 生成UI数据
        ui_dict = self.generate_ui_dict(player_id, shop_type)

        # 2. 发送到客户端
        # 使用NotifyToClient通信而非GetSystem获取客户端系统
        # 原因：网易引擎的双端隔离原则（开发规范.md:1075 - 客户端组件不能在服务端使用）
        # 参考：商店系统.md:148 正确的双端通信方式
        self.NotifyToClient(
            player_id,
            "BedWarsShopTryOpen",
            {
                'ui_dict': ui_dict,
                'player_id': player_id
            }
        )
        print("[ShopServerSystem] 已发送UI数据到客户端: player={}".format(player_id))

    def generate_ui_dict(self, player_id, shop_type):
        """
        生成商店UI数据

        从ShopPresetDefServer._generate_ui_dict_new()迁移

        Args:
            player_id (str): 玩家ID
            shop_type (str): 商店类型

        Returns:
            dict: UI数据字典
        """
        try:
            # 获取商店配置
            shop_config = self.shop_configs.get(shop_type)
            if not shop_config:
                print("[ERROR] [ShopServerSystem] shop_type={}配置不存在".format(shop_type))
                return {
                    "type": "default",
                    "name": u"商店",
                    "intro": u"",
                    "currencies": "",
                    "categories": []
                }

            # 1. 基础信息
            ui_dict = {
                "type": shop_config.get("type", "default"),
                "name": shop_config.get("name", u"商店"),
                "intro": shop_config.get("intro", u""),
                "currencies": self._format_currencies(player_id),
                "categories": []
            }

            # 2. 生成分类列表
            categories = shop_config.get("categories", [])
            for category_config in categories:
                category_ui = self._generate_category_ui(player_id, category_config)
                if category_ui:
                    ui_dict["categories"].append(category_ui)

            print("[ShopServerSystem] UI数据生成成功: player={}, categories={}".format(
                player_id, len(ui_dict["categories"])))

            return ui_dict

        except Exception as e:
            print("[ERROR] [ShopServerSystem] UI数据生成异常: player={}, error={}".format(
                player_id, str(e)))
            import traceback
            traceback.print_exc()
            # 返回空UI
            return {
                "type": "default",
                "name": u"商店",
                "intro": u"",
                "currencies": "",
                "categories": []
            }

    def _generate_category_ui(self, player_id, category_config):
        """
        生成单个分类的UI数据

        从ShopPresetDefServer._generate_category_ui_new()迁移

        Args:
            player_id (str): 玩家ID
            category_config (dict): 分类配置

        Returns:
            dict: 分类UI数据,如果无商品返回None
        """
        try:
            # 1. 基础信息
            category_ui = {
                "name": category_config.get("name", ""),
                "intro": category_config.get("intro", ""),
                "ui": category_config.get("ui", {}),
                "goods": []
            }

            # 2. 获取该分类的商品ID列表
            goods_ids = category_config.get("goods_ids", [])

            # 3. 生成每个商品的UI
            for goods_id in goods_ids:
                # 从goods_pool中查找商品配置
                goods_config = self.goods_pool.get(goods_id)
                if not goods_config:
                    print("[WARN] [ShopServerSystem] 商品ID未找到: {}".format(goods_id))
                    continue

                goods_ui = self._generate_goods_ui(player_id, goods_config)
                if goods_ui:
                    category_ui["goods"].append(goods_ui)

            # 4. 如果分类没有商品,返回None
            if not category_ui["goods"]:
                return None

            return category_ui

        except Exception as e:
            print("[ERROR] [ShopServerSystem] 分类UI生成异常: category={}, error={}".format(
                category_config.get("id"), str(e)))
            import traceback
            traceback.print_exc()
            return None

    def _generate_goods_ui(self, player_id, goods_config):
        """
        生成单个商品的UI数据

        从ShopPresetDefServer._generate_goods_ui_new()迁移

        Args:
            player_id (str): 玩家ID
            goods_config (dict): 商品配置

        Returns:
            dict: 商品UI数据
        """
        try:
            # 1. 基础信息
            goods_ui = {
                "key": goods_config.get("id"),
                "name": goods_config.get("name", goods_config.get("id")),
                "intro": goods_config.get("intro", ""),
                "upgrade_type": goods_config.get("upgrade_type", False),
                "levels_intro": goods_config.get("levels_intro", []),
                "show_item_dict": self._get_show_item(player_id, goods_config),
                "cannot_buy_msg": self._check_cannot_buy(player_id, goods_config),
                "price": self._format_price(player_id, goods_config),
                "detail_intros": goods_config.get("detail_intros", "")
            }

            return goods_ui

        except Exception as e:
            print("[ERROR] [ShopServerSystem] 商品UI生成异常: goods={}, error={}".format(
                goods_config.get("id"), str(e)))
            import traceback
            traceback.print_exc()
            return None

    def _format_currencies(self, player_id):
        """
        格式化货币显示

        从ShopPresetDefServer._format_currencies_new()迁移

        返回: " 4 §f 10 §e 0" (图标 + 数量,空格分隔)

        Args:
            player_id (str): 玩家ID

        Returns:
            str: 格式化的货币字符串
        """
        try:
            from Script_NeteaseMod.systems.util.CurrencyManager import CurrencyManager
            from Script_NeteaseMod.config.shop_config import SHOP_CONFIG

            # 货币图标
            currency_icons = {
                "iron": u"\uE1AC",
                "gold": u"\uE1AD",
                "diamond": u"\uE1AE",
                "emerald": u"\uE1AF"
            }

            # 货币颜色
            currency_colors = {
                "iron": u"§f",     # 白色
                "gold": u"§e",     # 黄色
                "diamond": u"§b",  # 青色
                "emerald": u"§a"   # 绿色
            }

            # 获取商店支持的货币列表
            currencies = SHOP_CONFIG.get("currencies", ["iron", "gold", "diamond", "emerald"])

            # 构建货币字符串
            parts = []
            for currency in currencies:
                amount = CurrencyManager.get_player_currency_count(player_id, currency)
                icon = currency_icons.get(currency, u"")
                color = currency_colors.get(currency, u"§f")

                parts.append(u"{}{} {}".format(icon, amount, color))

            return u" ".join(parts)

        except Exception as e:
            print("[ERROR] [ShopServerSystem] 货币格式化异常: player={}, error={}".format(
                player_id, str(e)))
            import traceback
            traceback.print_exc()
            return ""

    def _format_price(self, player_id, goods_config):
        """
        格式化价格字符串

        从ShopPresetDefServer._format_price_new()迁移

        返回: "§6 4 铁锭" 或 "§6 4 铁锭 §e 2 金锭"

        Args:
            player_id (str): 玩家ID
            goods_config (dict): 商品配置

        Returns:
            str: 格式化的价格字符串
        """
        try:
            # 货币图标
            currency_icons = {
                "iron": u"\uE1AC",
                "gold": u"\uE1AD",
                "diamond": u"\uE1AE",
                "emerald": u"\uE1AF"
            }

            # 货币颜色
            currency_colors = {
                "iron": u"§f",     # 白色
                "gold": u"§e",     # 黄色
                "diamond": u"§b",  # 青色
                "emerald": u"§a"   # 绿色
            }

            # 货币名称
            currency_names = {
                "iron": u"铁锭",
                "gold": u"金锭",
                "diamond": u"钻石",
                "emerald": u"绿宝石"
            }

            # 1. 获取价格配置
            price_config = goods_config.get("price")
            if not price_config:
                return u"免费"

            # 2. 处理多级价格
            if isinstance(price_config, dict) and not price_config.get("currency"):
                # 多级价格,获取当前等级
                current_level = self._get_current_upgrade_level(player_id, goods_config)
                price = price_config.get(current_level)
                if not price:
                    return u"价格错误"
            else:
                price = price_config

            # 3. 格式化价格
            currency = price.get("currency", "iron")
            amount = price.get("amount", 0)

            icon = currency_icons.get(currency, u"")
            color = currency_colors.get(currency, u"§f")
            name = currency_names.get(currency, currency)

            return u"{}{} {} {}".format(color, icon, amount, name)

        except Exception as e:
            print("[ERROR] [ShopServerSystem] 价格格式化异常: goods={}, error={}".format(
                goods_config.get("id"), str(e)))
            import traceback
            traceback.print_exc()
            return u"价格错误"

    def _get_show_item(self, player_id, goods_config):
        """
        获取UI显示物品

        从ShopPresetDefServer._get_show_item_new()迁移

        处理:
        - show_item存在 → 使用show_item
        - show_item不存在 → 使用item
        - Lambda函数 → 调用函数
        - item_upgrade类型 → 显示下一级物品图标

        老项目逻辑:
        - 对于可升级物品,通过CurrentItemFromSet.find_player_item_from_set()查找当前等级
        - 显示 shop_item_next_level (下一级物品)

        Args:
            player_id (str): 玩家ID
            goods_config (dict): 商品配置

        Returns:
            dict: 物品字典
        """
        try:
            goods_type = goods_config.get("type")

            # 1. 优先使用show_item
            show_item = goods_config.get("show_item")
            if show_item:
                if callable(show_item):
                    return show_item(self, player_id)
                return show_item

            # 2. 对于可升级物品,显示下一级物品图标
            # 参考老项目: simple_item_upgrade() - show_item_dict_factory返回shop_item_next_level
            if goods_type == "item_upgrade":
                item_levels = goods_config.get("item_levels")
                upgrade_path = goods_config.get("upgrade_path")

                if item_levels and upgrade_path:
                    # 查找当前等级
                    item_comp = serverApi.GetEngineCompFactory().CreateItem(player_id)
                    current_level = -1

                    for slot in range(36):
                        item_dict = item_comp.GetPlayerItem(
                            serverApi.GetMinecraftEnum().ItemPosType.INVENTORY,
                            slot
                        )
                        if item_dict:
                            item_name = item_dict.get("newItemName")
                            if item_name in upgrade_path:
                                level = upgrade_path.index(item_name)
                                if level > current_level:
                                    current_level = level

                    # 返回下一级物品图标
                    next_level = current_level + 1
                    if next_level < len(item_levels):
                        return item_levels[next_level]

            # 3. 使用item
            item = goods_config.get("item")
            if item:
                if callable(item):
                    item = item(self, player_id)

                # 如果是列表,取第一个
                if isinstance(item, list) and len(item) > 0:
                    return item[0]

                return item

            # 4. 默认物品
            return {
                "newItemName": "minecraft:barrier",
                "newAuxValue": 0,
                "count": 1
            }

        except Exception as e:
            print("[ERROR] [ShopServerSystem] 显示物品获取异常: goods={}, error={}".format(
                goods_config.get("id"), str(e)))
            import traceback
            traceback.print_exc()
            return {
                "newItemName": "minecraft:barrier",
                "newAuxValue": 0,
                "count": 1
            }

    def _get_current_upgrade_level(self, player_id, goods_config):
        """
        获取当前升级等级 (用于多级价格商品和可升级物品)

        从ShopPresetDefServer._get_current_upgrade_level()迁移

        Args:
            player_id (str): 玩家ID
            goods_config (dict): 商品配置

        Returns:
            int: 当前等级
        """
        try:
            goods_type = goods_config.get("type")

            if goods_type == "team_upgrade":
                # 队伍升级,获取队伍升级管理器
                game_system = self._get_bedwars_game_system()
                if game_system and hasattr(game_system, "team_module"):
                    player_team = game_system.team_module.get_player_team(player_id)
                    if player_team and hasattr(game_system, "team_upgrades"):
                        team_upgrade_mgr = game_system.team_upgrades.get(player_team)
                        if team_upgrade_mgr:
                            upgrade_key = goods_config.get("upgrade_key")
                            return team_upgrade_mgr.get_upgrade_level(upgrade_key)

            elif goods_type == "item_upgrade":
                # 可升级物品(镐子/斧子),扫描背包查找当前等级
                # 参考老项目: CurrentItemFromSet.find_player_item_from_set()
                upgrade_path = goods_config.get("upgrade_path")
                if not upgrade_path:
                    return 0

                item_comp = serverApi.GetEngineCompFactory().CreateItem(player_id)
                current_level = -1  # -1表示未拥有任何等级

                for slot in range(36):
                    item_dict = item_comp.GetPlayerItem(
                        serverApi.GetMinecraftEnum().ItemPosType.INVENTORY,
                        slot
                    )
                    if item_dict:
                        item_name = item_dict.get("newItemName")
                        if item_name in upgrade_path:
                            level = upgrade_path.index(item_name)
                            if level > current_level:
                                current_level = level

                # 返回下一级等级(用于价格查询)
                # 如果未拥有,返回0(购买第一级)
                # 如果拥有N级,返回N+1(购买下一级)
                return current_level + 1

            return 0
        except Exception as e:
            print("[ERROR] [ShopServerSystem] 获取升级等级异常: {}".format(str(e)))
            return 0

    def _get_bedwars_game_system(self):
        """
        获取BedWarsGameSystem实例

        从ShopPresetDefServer._get_bedwars_game_system()迁移

        Returns:
            BedWarsGameSystem实例,如果不存在返回None
        """
        try:
            from Script_NeteaseMod.modConfig import MOD_NAME, SERVER_SYSTEMS
            BEDWARS_GAME_SYSTEM = SERVER_SYSTEMS[1][0]  # "BedWarsGameSystem"
            game_system = serverApi.GetSystem(MOD_NAME, BEDWARS_GAME_SYSTEM)
            return game_system
        except Exception as e:
            print("[ERROR] [ShopServerSystem] 获取游戏系统失败: {}".format(str(e)))
            return None

    def _get_currency_display_name(self, currency_type):
        """
        获取货币显示名称

        从ShopPresetDefServer._get_currency_display_name()迁移

        Args:
            currency_type (str): 货币类型

        Returns:
            str: 货币显示名称
        """
        currency_map = {
            'iron': u'铁锭',
            'gold': u'金锭',
            'diamond': u'钻石',
            'emerald': u'绿宝石',
            'copper': u'铜锭',
            'exp': u'经验'
        }
        return currency_map.get(currency_type, currency_type)

    # ========== 购买处理 ==========

    def handle_player_buy_goods(self, event_data):
        """
        处理玩家购买商品

        从ShopPresetDefServer._on_try_buy()和_buy_goods_new()迁移

        Args:
            event_data (dict): 事件数据
                - player_id: 玩家ID
                - goods_key: 商品键
                - category_index: 分类索引
        """
        player_id = event_data.get('player_id')
        goods_key = event_data.get('goods_key')
        category_index = event_data.get('category_index')

        print("[ShopServerSystem] 收到购买请求: player={}, goods_key={}, category={}".format(
            player_id, goods_key, category_index))

        # 1. 查找商品配置
        goods_config = self.goods_pool.get(goods_key)
        if not goods_config:
            print("[ERROR] [ShopServerSystem] 商品未找到: goods_key={}".format(goods_key))
            self._send_buy_result(player_id, False, u"商品不存在")
            return

        # 2. 调用购买流程
        success, message = self._buy_goods(player_id, goods_config)

        # 3. 发送结果到客户端（音效由客户端播放）
        self._send_buy_result(player_id, success, message)

        # 4. 刷新商店UI
        # 购买成功：更新货币显示、刷新可购买商品状态
        # 购买失败：刷新商品锁定状态（如果是因为余额不足）
        # 参考老项目: BedWarsShopPart.server_on_bedwars_shop_try_buy() 第291行
        self._refresh_shop_ui(player_id)

    def _buy_goods(self, player_id, goods_config):
        """
        处理商品购买

        从ShopPresetDefServer._buy_goods_new()迁移

        流程:
        1. 限购检查
        2. 货币检查
        3. 扣除货币
        4. 发放物品/效果
        5. 广播事件

        Args:
            player_id (str): 玩家ID
            goods_config (dict): 商品配置字典

        Returns:
            tuple: (bool, str) - (是否成功, 消息)
        """
        try:
            goods_id = goods_config.get("id")
            goods_name = goods_config.get("name", goods_id)
            goods_type = goods_config.get("type", "item")

            print("[ShopServerSystem] 新架构购买: player={}, goods={}, type={}".format(
                player_id, goods_id, goods_type))

            # 1. 限购检查
            cannot_buy_msg = self._check_cannot_buy(player_id, goods_config)
            if cannot_buy_msg:
                print("[WARN] [ShopServerSystem] 限购拦截: player={}, goods={}, reason={}".format(
                    player_id, goods_id, cannot_buy_msg))
                return False, cannot_buy_msg

            # 2. 获取价格 (处理多级价格)
            price_config = goods_config.get("price")
            if isinstance(price_config, dict) and not price_config.get("currency"):
                # 多级价格,需要获取当前等级
                current_level = self._get_current_upgrade_level(player_id, goods_config)
                price = price_config.get(current_level)
                if not price:
                    return False, u"价格配置错误"
            else:
                price = price_config

            # 3. 货币检查
            from Script_NeteaseMod.systems.util.CurrencyManager import CurrencyManager
            if not CurrencyManager.can_afford(player_id, price):
                currency_name = self._get_currency_display_name(price.get("currency", "iron"))
                return False, u"{}不足".format(currency_name)

            # 4. 扣除货币
            if not CurrencyManager.pay_price(player_id, price):
                return False, u"货币扣除失败"

            # 5. 根据商品类型发放
            if goods_type == "item":
                success = self._give_item(player_id, goods_config)
                if not success:
                    # 物品发放失败,退还货币
                    CurrencyManager.refund_price(player_id, price)
                    return False, u"物品发放失败"

            elif goods_type == "team_upgrade":
                success, msg = self._process_team_upgrade(player_id, goods_config)
                if not success:
                    # 升级失败,退还货币
                    CurrencyManager.refund_price(player_id, price)
                    return False, msg

            elif goods_type == "trap":
                success, msg = self._process_trap(player_id, goods_config)
                if not success:
                    # 陷阱购买失败,退还货币
                    CurrencyManager.refund_price(player_id, price)
                    return False, msg

            elif goods_type == "item_upgrade":
                success, msg = self._process_item_upgrade(player_id, goods_config)
                if not success:
                    # 可升级物品失败,退还货币
                    CurrencyManager.refund_price(player_id, price)
                    return False, msg

            else:
                # 未知类型
                CurrencyManager.refund_price(player_id, price)
                return False, u"未知商品类型: {}".format(goods_type)

            # 6. 更新购买记录 (剑类和护甲类)
            if goods_type == "item":
                self._update_purchase_record(player_id, goods_config)

            # 7. 广播购买事件
            self._broadcast_purchase_event(player_id, goods_config, price)

            # 8. 成功
            print("[ShopServerSystem] 购买成功: player={}, goods={}".format(player_id, goods_id))
            return True, u"购买成功: {}".format(goods_name)

        except Exception as e:
            print("[ERROR] [ShopServerSystem] 购买处理异常: player={}, goods={}, error={}".format(
                player_id, goods_config.get("id"), str(e)))
            import traceback
            traceback.print_exc()
            return False, u"购买失败"

    def _give_item(self, player_id, goods_config):
        """
        给予玩家物品

        从ShopPresetDefServer._give_item_new()迁移

        Args:
            player_id (str): 玩家ID
            goods_config (dict): 商品配置

        Returns:
            bool: 是否成功
        """
        try:
            item = goods_config.get("item")

            if item is None:
                print("[WARN] [ShopServerSystem] 商品没有item配置: {}".format(goods_config.get("id")))
                return True  # 某些商品(如队伍升级)不需要发放物品

            # 处理Lambda函数
            if callable(item):
                item = item(self, player_id)

            # 处理列表物品
            if isinstance(item, list):
                for single_item in item:
                    if not self._give_single_item(player_id, single_item):
                        return False
                return True

            # 处理单个物品
            return self._give_single_item(player_id, item)

        except Exception as e:
            print("[ERROR] [ShopServerSystem] 物品发放异常: player={}, error={}".format(
                player_id, str(e)))
            import traceback
            traceback.print_exc()
            return False

    def _give_single_item(self, player_id, item_dict):
        """
        发放单个物品

        从ShopPresetDefServer._give_single_item_new()迁移

        处理:
        - 护甲 → 穿戴到护甲槽
        - 普通物品 → 放入背包
        - 应用队伍锋利附魔 (如果是剑类)

        Args:
            player_id (str): 玩家ID
            item_dict (dict): 物品字典

        Returns:
            bool: 是否成功
        """
        try:
            item_comp = serverApi.GetEngineCompFactory().CreateItem(player_id)

            item_name = item_dict.get("newItemName")
            if not item_name:
                print("[ERROR] [ShopServerSystem] 物品字典缺少newItemName")
                return False

            # 检查是否是护甲
            armor_map = {
                "minecraft:leather_helmet": 0,
                "minecraft:chainmail_helmet": 0,
                "minecraft:iron_helmet": 0,
                "minecraft:gold_helmet": 0,
                "minecraft:diamond_helmet": 0,
                "minecraft:netherite_helmet": 0,
                "minecraft:leather_chestplate": 1,
                "minecraft:chainmail_chestplate": 1,
                "minecraft:iron_chestplate": 1,
                "minecraft:gold_chestplate": 1,
                "minecraft:diamond_chestplate": 1,
                "minecraft:netherite_chestplate": 1,
                "minecraft:leather_leggings": 2,
                "minecraft:chainmail_leggings": 2,
                "minecraft:iron_leggings": 2,
                "minecraft:gold_leggings": 2,
                "minecraft:diamond_leggings": 2,
                "minecraft:netherite_leggings": 2,
                "minecraft:leather_boots": 3,
                "minecraft:chainmail_boots": 3,
                "minecraft:iron_boots": 3,
                "minecraft:gold_boots": 3,
                "minecraft:diamond_boots": 3,
                "minecraft:netherite_boots": 3,
            }

            # 检查是否是剑类(需要应用队伍锋利)
            sword_types = [
                "minecraft:wooden_sword",
                "minecraft:stone_sword",
                "minecraft:iron_sword",
                "minecraft:diamond_sword",
                "minecraft:netherite_sword"
            ]

            # 应用队伍锋利附魔(如果是剑类)
            # ⚠️ 注意：这里必须在深拷贝之前修改item_dict，因为后续护甲/普通物品都需要这个附魔
            # 但为了避免污染商品配置，应该先检查是否需要附魔，如果需要则创建新的item_dict
            needs_sharpness = False
            sharpness_level = 0

            if item_name in sword_types:
                game_system = self._get_bedwars_game_system()
                if game_system and hasattr(game_system, "team_module") and game_system.team_module:
                    player_team = game_system.team_module.get_player_team(player_id)
                    if player_team:
                        team_upgrades = game_system.team_upgrades.get(player_team)
                        if team_upgrades:
                            sharpness_level = team_upgrades.get_upgrade_level("sword")
                            if sharpness_level > 0:
                                needs_sharpness = True
                                print("[ShopServerSystem] 队伍锋利附魔: player={}, team={}, level={}".format(
                                    player_id, player_team, sharpness_level))

            # ✅ 修复：如果需要附魔，深拷贝item_dict后再添加附魔
            if needs_sharpness:
                import copy
                item_dict = copy.deepcopy(item_dict)
                if "enchantData" not in item_dict:
                    item_dict["enchantData"] = []
                item_dict["enchantData"].append(
                    (serverApi.GetMinecraftEnum().EnchantType.WeaponDamage, sharpness_level)
                )

            # 护甲穿戴
            if item_name in armor_map:
                slot = armor_map[item_name]

                # ✅ 修复：深拷贝item_dict，避免污染商品配置
                # 原因：直接修改item_dict会影响商品池中的原始配置
                # 导致第二次购买时userData已存在，可能引发异常
                import copy
                armor_item = copy.deepcopy(item_dict)

                # 护甲需要锁定,防止玩家脱下
                if "userData" not in armor_item:
                    armor_item["userData"] = {}
                armor_item["userData"]["minecraft:item_lock"] = {"__type__": 1, "__value__": True}

                success = item_comp.SetEntityItem(
                    serverApi.GetMinecraftEnum().ItemPosType.ARMOR,
                    armor_item,
                    slot
                )
                if success:
                    print("[ShopServerSystem] 护甲穿戴成功: player={}, item={}, slot={}".format(
                        player_id, item_name, slot))
                else:
                    print("[ERROR] [ShopServerSystem] 护甲穿戴失败: player={}, item={}".format(
                        player_id, item_name))
                return success

            # 普通物品发放到背包
            # ⚠️ CRITICAL: SpawnItemToPlayerInv不带slot参数时必须使用'itemName'字段
            # 原因: 网易API要求，newItemName只用于带slot的调用
            # 参考: BedWarsGameSystem.py:2219-2224, CurrencyManager.py:234-240
            spawn_dict = {
                'itemName': item_dict.get('newItemName'),
                'count': item_dict.get('count', 1),
                'auxValue': item_dict.get('newAuxValue', 0)
            }

            # 复制附魔数据(如果存在)
            if 'enchantData' in item_dict:
                spawn_dict['enchantData'] = item_dict['enchantData']

            # 复制自定义提示(如果存在)
            if 'customTips' in item_dict:
                spawn_dict['customTips'] = item_dict['customTips']

            success = item_comp.SpawnItemToPlayerInv(spawn_dict, player_id)
            if success:
                print("[ShopServerSystem] 物品发放成功: player={}, item={}, count={}".format(
                    player_id, item_name, item_dict.get("count", 1)))
            else:
                print("[ERROR] [ShopServerSystem] 物品发放失败: player={}, item={}".format(
                    player_id, item_name))
            return success

        except Exception as e:
            print("[ERROR] [ShopServerSystem] 单个物品发放异常: player={}, error={}".format(
                player_id, str(e)))
            import traceback
            traceback.print_exc()
            return False

    def _process_team_upgrade(self, player_id, goods_config):
        """
        处理队伍升级购买

        从ShopPresetDefServer._process_team_upgrade_new()迁移

        Args:
            player_id (str): 玩家ID
            goods_config (dict): 商品配置

        Returns:
            tuple: (bool, str) - (是否成功, 消息)
        """
        try:
            # 1. 获取游戏系统
            game_system = self._get_bedwars_game_system()
            if not game_system:
                return False, u"游戏系统未初始化"

            # 2. 获取玩家队伍
            if not hasattr(game_system, "team_module") or not game_system.team_module:
                return False, u"队伍系统未初始化"

            player_team = game_system.team_module.get_player_team(player_id)
            if not player_team:
                return False, u"你不在任何队伍中"

            # 3. 获取队伍升级管理器
            if not hasattr(game_system, "team_upgrades"):
                return False, u"升级系统未初始化"

            team_upgrade_mgr = game_system.team_upgrades.get(player_team)
            if not team_upgrade_mgr:
                return False, u"队伍升级管理器未找到"

            # 4. 应用升级
            upgrade_key = goods_config.get("upgrade_key")
            if not upgrade_key:
                return False, u"升级键缺失"

            success = team_upgrade_mgr.purchase_upgrade(upgrade_key)
            if success:
                print("[ShopServerSystem] 队伍升级成功: team={}, key={}".format(
                    player_team, upgrade_key))
                return True, u"升级成功"
            else:
                return False, u"升级失败"

        except Exception as e:
            print("[ERROR] [ShopServerSystem] 队伍升级处理异常: player={}, error={}".format(
                player_id, str(e)))
            import traceback
            traceback.print_exc()
            return False, u"升级失败"

    def _process_trap(self, player_id, goods_config):
        """
        处理陷阱购买

        从ShopPresetDefServer._process_trap_new()迁移

        Args:
            player_id (str): 玩家ID
            goods_config (dict): 商品配置

        Returns:
            tuple: (bool, str) - (是否成功, 消息)
        """
        try:
            # 1. 获取游戏系统
            game_system = self._get_bedwars_game_system()
            if not game_system:
                return False, u"游戏系统未初始化"

            # 2. 获取玩家队伍
            if not hasattr(game_system, "team_module") or not game_system.team_module:
                return False, u"队伍系统未初始化"

            player_team = game_system.team_module.get_player_team(player_id)
            if not player_team:
                return False, u"你不在任何队伍中"

            # 3. 获取陷阱管理器
            if not hasattr(game_system, "team_trap_managers"):
                return False, u"陷阱系统未初始化"

            trap_manager = game_system.team_trap_managers.get(player_team)
            if not trap_manager:
                return False, u"陷阱管理器未找到"

            # 4. 添加陷阱
            trap_type = goods_config.get("trap_type")
            if not trap_type:
                return False, u"陷阱类型缺失"

            success = trap_manager.add_trap(trap_type)
            if success:
                print("[ShopServerSystem] 陷阱购买成功: team={}, trap={}".format(
                    player_team, trap_type))
                return True, u"陷阱购买成功"
            else:
                return False, u"陷阱队列已满"

        except Exception as e:
            print("[ERROR] [ShopServerSystem] 陷阱购买处理异常: player={}, error={}".format(
                player_id, str(e)))
            import traceback
            traceback.print_exc()
            return False, u"陷阱购买失败"

    def _process_item_upgrade(self, player_id, goods_config):
        """
        处理可升级物品购买 (镐子/斧子)

        从ShopPresetDefServer._process_item_upgrade_new()迁移

        老项目逻辑（CurrentItemFromSet.find_player_item_from_set）:
        1. 扫描玩家背包查找item_levels数组中的任意物品
        2. 找到当前等级(index)
        3. 如果有当前等级物品,替换为下一级
        4. 如果没有,发放第一级(index=0)

        Args:
            player_id (str): 玩家ID
            goods_config (dict): 商品配置

        Returns:
            tuple: (bool, str) - (是否成功, 消息)
        """
        try:
            item_comp = serverApi.GetEngineCompFactory().CreateItem(player_id)

            # 1. 获取物品等级配置(用于查找当前等级并发放对应等级物品)
            item_levels = goods_config.get("item_levels")
            if not item_levels:
                print("[ERROR] [ShopServerSystem] item_levels缺失: goods={}".format(goods_config.get("id")))
                return False, u"配置错误: item_levels缺失"

            # 2. 获取upgrade_path (用于快速匹配物品名称)
            upgrade_path = goods_config.get("upgrade_path")
            if not upgrade_path:
                print("[ERROR] [ShopServerSystem] upgrade_path缺失: goods={}".format(goods_config.get("id")))
                return False, u"配置错误: upgrade_path缺失"

            # 3. 查找玩家背包中的当前物品等级
            # 参考老项目: CurrentItemFromSet.find_player_item_from_set()
            current_level = -1  # -1表示未拥有任何等级
            current_slot = None
            for slot in range(36):
                item_dict = item_comp.GetPlayerItem(
                    serverApi.GetMinecraftEnum().ItemPosType.INVENTORY,
                    slot
                )
                if item_dict:
                    item_name = item_dict.get("newItemName")
                    if item_name in upgrade_path:
                        level = upgrade_path.index(item_name)
                        if level > current_level:
                            current_level = level
                            current_slot = slot

            # 4. 确定下一级物品
            # 如果玩家没有任何等级,给第一级(index=0)
            # 如果玩家有N级,给N+1级
            next_level = current_level + 1

            if next_level >= len(item_levels):
                return False, u"已达到最高等级"

            # 5. 获取下一级物品的完整配置(包括附魔等)
            next_item_dict = item_levels[next_level]

            # 6. 删除旧物品(如果存在)
            if current_slot is not None:
                item_comp.SetInvItemNum(current_slot, 0)
                print("[ShopServerSystem] 删除旧物品: player={}, slot={}, level={} -> {}".format(
                    player_id, current_slot, current_level, next_level))
            else:
                print("[ShopServerSystem] 首次购买: player={}, level={}".format(
                    player_id, next_level))

            # 7. 发放新等级的物品(从item_levels中获取完整配置)
            success = self._give_single_item(player_id, next_item_dict)
            if success:
                item_name = next_item_dict.get("newItemName", "未知物品")
                print("[ShopServerSystem] 可升级物品购买成功: player={}, goods={}, level={} -> {}, item={}".format(
                    player_id, goods_config.get("id"), current_level, next_level, item_name))
                return True, u"升级成功"
            else:
                return False, u"物品发放失败"

        except Exception as e:
            print("[ERROR] [ShopServerSystem] 可升级物品处理异常: player={}, error={}".format(
                player_id, str(e)))
            import traceback
            traceback.print_exc()
            return False, u"升级失败"

    def _update_purchase_record(self, player_id, goods_config):
        """
        更新购买记录 (剑类和护甲类)

        从ShopPresetDefServer._update_purchase_record()迁移

        用于防止玩家丢剑/护甲后重复购买低品质物品绕过限购

        Args:
            player_id (str): 玩家ID
            goods_config (dict): 商品配置
        """
        try:
            from Script_NeteaseMod.config.shop_config import ORDERED_SWORDS

            # 获取BedWarsGameSystem
            game_system = self._get_bedwars_game_system()
            if not game_system:
                return

            # 获取物品
            item = goods_config.get("item")
            if callable(item):
                item = item(self, player_id)

            if not item:
                return

            # 处理列表物品 (护甲套装)
            items_to_check = []
            if isinstance(item, list):
                items_to_check = item
            else:
                items_to_check = [item]

            # 检查每个物品
            for single_item in items_to_check:
                item_name = single_item.get("newItemName")
                if not item_name:
                    continue

                # 剑类记录
                if item_name in ORDERED_SWORDS:
                    if not hasattr(game_system, 'player_sword_record'):
                        game_system.player_sword_record = {}

                    # 获取当前记录的剑品质
                    current_record = game_system.player_sword_record.get(player_id, "minecraft:wooden_sword")
                    current_level = 0
                    if current_record in ORDERED_SWORDS:
                        current_level = ORDERED_SWORDS.index(current_record)

                    # 新购买的剑品质
                    new_level = ORDERED_SWORDS.index(item_name)

                    # 只记录更高品质的剑
                    if new_level > current_level:
                        game_system.player_sword_record[player_id] = item_name
                        print("[ShopServerSystem] 更新剑购买记录: player={}, old={}, new={}, level={}".format(
                            player_id, current_record, item_name, new_level))

                # 护甲类记录
                elif "chestplate" in item_name or "leggings" in item_name or "boots" in item_name:
                    if not hasattr(game_system, 'player_armor_record'):
                        game_system.player_armor_record = {}

                    if player_id not in game_system.player_armor_record:
                        game_system.player_armor_record[player_id] = {}

                    # 确定护甲部位
                    armor_slot = None
                    if "chestplate" in item_name:
                        armor_slot = "chestplate"
                    elif "leggings" in item_name:
                        armor_slot = "leggings"
                    elif "boots" in item_name:
                        armor_slot = "boots"

                    if armor_slot:
                        game_system.player_armor_record[player_id][armor_slot] = item_name
                        print("[ShopServerSystem] 更新护甲购买记录: player={}, slot={}, item={}".format(
                            player_id, armor_slot, item_name))

        except Exception as e:
            print("[ERROR] [ShopServerSystem] 更新购买记录异常: player={}, error={}".format(
                player_id, str(e)))
            import traceback
            traceback.print_exc()

    def _broadcast_purchase_event(self, player_id, goods_config, price):
        """
        广播购买事件

        Args:
            player_id (str): 玩家ID
            goods_config (dict): 商品配置
            price (dict): 价格信息
        """
        try:
            # TODO: 实现事件广播逻辑
            # 这里暂时不实现，因为需要EventBus系统
            pass
        except Exception as e:
            print("[ERROR] [ShopServerSystem] 购买事件广播失败: {}".format(str(e)))

    def _send_buy_result(self, player_id, success, message):
        """
        发送购买结果到客户端

        Args:
            player_id (str): 玩家ID
            success (bool): 是否成功
            message (str): 提示消息
        """
        # 使用NotifyToClient通信而非GetSystem获取客户端系统
        # 原因：网易引擎的双端隔离原则（开发规范.md:1075）
        self.NotifyToClient(
            player_id,
            "BedWarsShopBuyResult",
            {
                'success': success,
                'msg': message
            }
        )
        print("[ShopServerSystem] 已发送购买结果: player={}, success={}, msg={}".format(
            player_id, success, message))

    def _refresh_shop_ui(self, player_id):
        """
        刷新商店UI

        购买成功后调用，重新生成UI数据并发送到客户端
        这将更新：
        1. 货币显示（购买后余额变化）
        2. 商品锁定状态（余额不足时显示"余额不足"）
        3. 商品价格（多级商品升级后价格变化）

        参考老项目: BedWarsShopPart.notify_client_refresh_ui()

        Args:
            player_id (str): 玩家ID
        """
        # 获取玩家当前打开的商店类型
        shop_type = self.player_shop_types.get(player_id)
        if not shop_type:
            print("[WARN] [ShopServerSystem] 刷新UI失败: 未找到玩家{}的商店类型".format(player_id))
            return

        # 重新生成UI数据（会重新计算货币、cannot_buy_msg等）
        ui_dict = self.generate_ui_dict(player_id, shop_type)

        # 发送刷新事件到客户端
        self.NotifyToClient(
            player_id,
            "BedWarsShopRefresh",
            {
                'ui_dict': ui_dict
            }
        )
        print("[ShopServerSystem] 已发送UI刷新: player={}, shop_type={}".format(player_id, shop_type))

    # ========== 限购检查 ==========

    def _check_cannot_buy(self, player_id, goods_config):
        """
        统一的限购检查入口

        从ShopPresetDefServer._check_cannot_buy_new()迁移

        处理:
        - None → 无限购
        - Lambda函数 → 直接调用
        - 字符串 → 调用对应方法 (如"check_team_upgrade_limit")
        - 余额检查 → 检查玩家是否有足够货币

        Args:
            player_id (str): 玩家ID
            goods_config (dict): 商品配置

        Returns:
            str|None: 错误消息或None (None表示可以购买)
        """
        try:
            # 1. 首先执行自定义限购检查
            check_can_buy = goods_config.get("check_can_buy")

            if callable(check_can_buy):
                # Lambda函数检查
                msg = check_can_buy(self, player_id)
                if msg:
                    return msg

            elif isinstance(check_can_buy, str):
                # 字符串方法名检查
                method = getattr(self, check_can_buy, None)
                if method and callable(method):
                    msg = method(player_id, goods_config)
                    if msg:
                        return msg
                else:
                    print("[WARN] [ShopServerSystem] 限购检查方法未找到: {}".format(check_can_buy))

            # 2. 然后检查余额 (参考老项目ShopGoods.py第89-97行)
            # 这是关键修复:确保货币不足的道具显示"余额不足"并禁用购买按钮
            price = self._get_price_for_player(player_id, goods_config)
            if price:
                from Script_NeteaseMod.systems.util.CurrencyManager import CurrencyManager
                if not CurrencyManager.can_afford(player_id, price):
                    return u"余额不足"

            return None

        except Exception as e:
            print("[ERROR] [ShopServerSystem] 限购检查异常: player={}, error={}".format(
                player_id, str(e)))
            import traceback
            traceback.print_exc()
            return None

    def _get_price_for_player(self, player_id, goods_config):
        """
        获取玩家购买该商品的实际价格

        从ShopPresetDefServer._get_price_for_player()迁移

        处理多级价格商品 (如队伍升级)

        Args:
            player_id (str): 玩家ID
            goods_config (dict): 商品配置

        Returns:
            dict|None: 价格字典 {'currency': 'iron', 'amount': 10} 或 None
        """
        try:
            price_config = goods_config.get("price")
            if not price_config:
                return None

            # 处理多级价格
            if isinstance(price_config, dict) and not price_config.get("currency"):
                # 多级价格,获取当前等级
                current_level = self._get_current_upgrade_level(player_id, goods_config)
                return price_config.get(current_level)
            else:
                # 固定价格
                return price_config

        except Exception as e:
            print("[ERROR] [ShopServerSystem] 获取价格异常: goods={}, error={}".format(
                goods_config.get("id"), str(e)))
            return None

    def check_sword_limit(self, player_id, goods_config):
        """
        检查剑类限购

        从ShopPresetDefServer.check_sword_limit()迁移

        使用: shop_config.is_player_sword_better_than()

        Args:
            player_id (str): 玩家ID
            goods_config (dict): 商品配置

        Returns:
            str|None: 错误消息或None
        """
        try:
            from Script_NeteaseMod.config.shop_config import is_player_sword_better_than

            item = goods_config.get("item")
            if callable(item):
                item = item(self, player_id)

            if not item:
                return None

            item_name = item.get("newItemName")
            if not item_name:
                return None

            # 检查是否已拥有更好的剑
            if is_player_sword_better_than(self, player_id, item_name):
                return u"你已拥有更好的剑"

            return None

        except Exception as e:
            print("[ERROR] [ShopServerSystem] 剑类限购检查异常: player={}, error={}".format(
                player_id, str(e)))
            import traceback
            traceback.print_exc()
            return None

    def check_armor_limit(self, player_id, goods_config):
        """
        检查护甲限购

        从ShopPresetDefServer.check_armor_limit()迁移

        使用: shop_config.is_player_chestplate_better_than()
              shop_config.is_player_leggings_better_than()

        Args:
            player_id (str): 玩家ID
            goods_config (dict): 商品配置

        Returns:
            str|None: 错误消息或None
        """
        try:
            from Script_NeteaseMod.config.shop_config import (
                is_player_chestplate_better_than,
                is_player_leggings_better_than
            )

            item = goods_config.get("item")
            if callable(item):
                item = item(self, player_id)

            if not item:
                return None

            # 处理列表物品(护甲套装)
            if isinstance(item, list):
                for single_item in item:
                    item_name = single_item.get("newItemName")
                    if not item_name:
                        continue

                    # 检查胸甲
                    if "chestplate" in item_name:
                        if is_player_chestplate_better_than(player_id, item_name):
                            return u"你已拥有更好的胸甲"

                    # 检查护腿
                    if "leggings" in item_name:
                        if is_player_leggings_better_than(player_id, item_name):
                            return u"你已拥有更好的护腿"

                return None

            # 单个护甲
            item_name = item.get("newItemName")
            if not item_name:
                return None

            # 检查胸甲
            if "chestplate" in item_name:
                if is_player_chestplate_better_than(player_id, item_name):
                    return u"你已拥有更好的胸甲"

            # 检查护腿
            if "leggings" in item_name:
                if is_player_leggings_better_than(player_id, item_name):
                    return u"你已拥有更好的护腿"

            return None

        except Exception as e:
            print("[ERROR] [ShopServerSystem] 护甲限购检查异常: player={}, error={}".format(
                player_id, str(e)))
            import traceback
            traceback.print_exc()
            return None

    def check_team_upgrade_limit(self, player_id, goods_config):
        """
        检查队伍升级限购

        从ShopPresetDefServer.check_team_upgrade_limit()迁移

        检查:
        1. 玩家是否在队伍中
        2. 升级是否已达最高等级

        Args:
            player_id (str): 玩家ID
            goods_config (dict): 商品配置

        Returns:
            str|None: 错误消息或None
        """
        try:
            # 1. 获取游戏系统
            game_system = self._get_bedwars_game_system()
            if not game_system:
                return None  # 游戏未启动,不检查

            # 2. 获取玩家队伍
            if not hasattr(game_system, "team_module") or not game_system.team_module:
                return None

            player_team = game_system.team_module.get_player_team(player_id)
            if not player_team:
                return u"你不在任何队伍中"

            # 3. 获取升级管理器
            if not hasattr(game_system, "team_upgrades"):
                return None

            team_upgrade_mgr = game_system.team_upgrades.get(player_team)
            if not team_upgrade_mgr:
                return None

            # 4. 检查升级等级
            upgrade_key = goods_config.get("upgrade_key")
            max_level = goods_config.get("max_level", 1)

            if not upgrade_key:
                return None

            current_level = team_upgrade_mgr.get_upgrade_level(upgrade_key)

            # 检查是否已达最高等级
            if current_level >= max_level:
                return u"该升级已达到最高等级"

            # 检查是否升级类型要求队伍无床
            upgrade_type = goods_config.get("upgrade_type")
            if upgrade_type == "trap":
                # 陷阱需要床存在
                if hasattr(game_system, "team_beds"):
                    if player_team not in game_system.team_beds or not game_system.team_beds[player_team]:
                        return u"队伍床已被破坏,无法购买陷阱"

            return None

        except Exception as e:
            print("[ERROR] [ShopServerSystem] 队伍升级限购检查异常: player={}, error={}".format(
                player_id, str(e)))
            import traceback
            traceback.print_exc()
            return None

    def check_trap_limit(self, player_id, goods_config):
        """
        检查陷阱限购

        从ShopPresetDefServer.check_trap_limit()迁移

        检查:
        1. 玩家是否在队伍中
        2. 队伍是否有床
        3. 陷阱是否已满 (最多3个)

        Args:
            player_id (str): 玩家ID
            goods_config (dict): 商品配置

        Returns:
            str|None: 错误消息或None
        """
        try:
            # 1. 获取游戏系统
            game_system = self._get_bedwars_game_system()
            if not game_system:
                return None  # 游戏未启动,不检查

            # 2. 获取玩家队伍
            if not hasattr(game_system, "team_module") or not game_system.team_module:
                return None

            player_team = game_system.team_module.get_player_team(player_id)
            if not player_team:
                return u"你不在任何队伍中"

            # 3. 检查队伍是否有床
            if hasattr(game_system, "team_beds"):
                if player_team not in game_system.team_beds or not game_system.team_beds[player_team]:
                    return u"队伍床已被破坏,无法购买陷阱"

            # 4. 检查陷阱是否已满
            if not hasattr(game_system, "team_trap_managers"):
                return None

            trap_manager = game_system.team_trap_managers.get(player_team)
            if not trap_manager:
                return None

            if trap_manager.is_trap_full():
                return u"陷阱已满(最多3个)"

            return None

        except Exception as e:
            print("[ERROR] [ShopServerSystem] 陷阱限购检查异常: player={}, error={}".format(
                player_id, str(e)))
            import traceback
            traceback.print_exc()
            return None

    def check_item_upgrade_limit(self, player_id, goods_config):
        """
        检查可升级物品限购

        从ShopPresetDefServer.check_item_upgrade_limit()迁移

        检查:
        1. 扫描背包查找当前等级
        2. 是否已达最高级

        Args:
            player_id (str): 玩家ID
            goods_config (dict): 商品配置

        Returns:
            str|None: 错误消息或None
        """
        try:
            item_comp = serverApi.GetEngineCompFactory().CreateItem(player_id)

            # 1. 获取升级路径
            upgrade_path = goods_config.get("upgrade_path")
            if not upgrade_path:
                return None

            # 2. 查找玩家背包中的当前物品等级
            current_level = 0
            for slot in range(36):
                item_dict = item_comp.GetPlayerItem(
                    serverApi.GetMinecraftEnum().ItemPosType.INVENTORY,
                    slot
                )
                if item_dict:
                    item_name = item_dict.get("newItemName")
                    if item_name in upgrade_path:
                        level = upgrade_path.index(item_name)
                        if level > current_level:
                            current_level = level

            # 3. 检查是否已达最高级
            if current_level >= len(upgrade_path) - 1:
                return u"已达到最高等级"

            return None

        except Exception as e:
            print("[ERROR] [ShopServerSystem] 可升级物品限购检查异常: player={}, error={}".format(
                player_id, str(e)))
            import traceback
            traceback.print_exc()
            return None
