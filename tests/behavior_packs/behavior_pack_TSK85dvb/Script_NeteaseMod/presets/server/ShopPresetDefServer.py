# -*- coding: utf-8 -*-
"""
商店预设 - 服务端

功能:
- 管理商店NPC
- 处理玩家交互
- 处理购买交易
- 管理商店配置
"""

from Script_NeteaseMod.presets.server.EntityPresetServerBase import EntityPresetServerBase
# 使用完整路径导入modConfig（开发规范.md - 模块导入规范第369节）
# 原因：子目录文件必须使用完整包路径，不能使用相对导入
from Script_NeteaseMod.modConfig import MOD_NAME


class ShopPresetDefServer(EntityPresetServerBase):
    """
    商店预设服务端实现

    核心功能:
    1. 商店NPC管理 (创建、销毁)
    2. 玩家交互检测 (右键点击NPC)
    3. 商店UI打开 (通知客户端)
    4. 购买交易处理 (物品、货币验证)
    5. 队伍限制 (只有队伍成员可使用)
    """

    def __init__(self):
        super(ShopPresetDefServer, self).__init__()

        # 配置数据
        self.team = None  # type: str | None  # 队伍ID (如果是None表示公共商店)
        self.shop_type = None  # type: str | None  # 商店类型 (items/upgrades等)

        # 运行时状态
        self.shop_npc_id = None  # type: str | None  # 商店NPC实体ID
        self.shop_config = None  # type: dict | None  # 商店配置
        self.shop_instance = None  # type: dict | None  # 商店实例数据
        self.usable_players = []  # type: list  # 可使用商店的玩家列表
        self.shop_npc_name = u"商人"  # type: str  # NPC名称

    def on_init(self, instance):
        """
        预设初始化

        解析配置数据:
        - team: 队伍ID
        - shop_type: 商店类型

        Args:
            instance: PresetInstance对象
        """
        self.team = instance.get_config("team", "NONE")
        self.shop_type = instance.get_config("shop_type", "items")

        # 根据商店类型设置名称（参考老项目配置）
        # 使用Minecraft颜色代码：§e=黄色, §l=加粗
        if self.shop_type == "items":
            self.shop_npc_name = u"§l道具商人\n§e点击打开"
        elif self.shop_type == "upgrade":
            self.shop_npc_name = u"§l升级商人\n§e点击打开"
        else:
            self.shop_npc_name = u"§l商人\n§e点击打开"

        print("[INFO] [商店] 初始化: team={}, type={}".format(self.team, self.shop_type))

        # 保存运行时数据到instance.data
        instance.set_data("team", self.team)
        instance.set_data("shop_type", self.shop_type)

    def on_start(self, instance):
        """
        预设启动

        执行步骤:
        1. 创建商店NPC
        2. 加载商店配置
        3. 初始化可使用玩家列表
        4. 注册事件监听

        Args:
            instance: PresetInstance对象
        """
        print("[INFO] [商店] 启动: team={}".format(self.team))

        # 1. 加载商店配置
        self._load_shop_config()

        # 2. 初始化可使用玩家列表
        self._init_usable_players()

        # 保存instance引用
        self.instance = instance

        # 3. 注册事件监听 - 使用EventBus订阅自定义事件，使用ServerSystem监听引擎事件
        import mod.server.extraServerApi as serverApi
        server_system = instance.manager.server_api

        if server_system:
            # 监听玩家伤害事件 (防止攻击NPC) - 引擎事件
            server_system.ListenForEvent(
                serverApi.GetEngineNamespace(),
                serverApi.GetEngineSystemName(),
                "DamageEvent",
                self,
                self._on_damage
            )

            # 监听玩家交互事件 (右键点击NPC) - 引擎事件
            server_system.ListenForEvent(
                serverApi.GetEngineNamespace(),
                serverApi.GetEngineSystemName(),
                "PlayerDoInteractServerEvent",
                self,
                self._on_player_interact
            )

        # 监听自定义事件 - 通过EventBus
        instance.subscribe_event("BedWarsShopTryBuy", self._on_try_buy)
        instance.subscribe_event("BedWarsRunning", self._on_bedwars_running)
        instance.subscribe_event("BedWarsEnding", self._on_bedwars_ending)
        instance.subscribe_event("TeamModuleUpdateTeamPlayers", self._on_team_update)

        print("[INFO] [商店] 事件监听注册完成,等待BedWarsRunning事件创建NPC")

    def on_tick(self, instance):
        """
        每Tick更新

        商店预设通常不需要Tick更新

        Args:
            instance: PresetInstance对象
        """
        pass

    def on_stop(self, instance):
        """
        预设停止

        清理工作:
        1. 销毁商店NPC
        2. 取消事件监听

        Args:
            instance: PresetInstance对象
        """
        print("[INFO] [商店] 停止: team={}".format(self.team))

        # 销毁商店NPC
        if self.shop_npc_id:
            # TODO: 需要引擎API支持
            # self._destroy_entity(self.shop_npc_id)
            self.shop_npc_id = None

        # 事件监听会在PresetInstance.destroy()时自动取消，这里不需要手动取消

    def on_destroy(self, instance):
        """
        预设销毁

        最终清理工作

        Args:
            instance: PresetInstance对象
        """
        print("[INFO] [商店] 销毁: team={}".format(self.team))

        # 清理数据
        self.shop_config = None
        self.shop_instance = None
        self.usable_players = []

    # ========== 事件处理方法 ==========

    def _on_damage(self, args):
        """
        处理伤害事件 - 保护商店NPC免疫伤害并处理攻击交互

        这是引擎事件回调，只接受1个参数
        参考: ShopPresetDefServer.py.backup:178-200

        Args:
            args: dict 事件参数
                - entityId: str 受伤实体ID
                - srcId: str 攻击者ID (玩家)
                - damage: float 伤害值
                - knock: bool 是否击退
                - ignite: bool 是否点燃
        """
        entity_id = args.get('entityId')

        # 检查是否是本预设的商店NPC
        if entity_id != self.shop_npc_id:
            return

        # 保护商店NPC：伤害归零、取消击退、取消点燃
        args['damage'] = 0       # 伤害归零
        args['knock'] = False    # 取消击退
        args['ignite'] = False   # 取消点燃

        # 获取攻击者(玩家)
        player_id = args.get('srcId')

        # 检查玩家是否可以使用商店
        if not self._can_player_use_shop(player_id):
            print("[INFO] [商店] 玩家无权使用商店: player={}".format(player_id))
            return

        # 打开商店界面 (攻击NPC等同于交互)
        print("[INFO] [商店] 玩家通过攻击交互: player={}, npc={}".format(player_id, entity_id))
        self._open_shop_ui(player_id)

    def _on_player_interact(self, args):
        """
        处理玩家交互事件

        当玩家右键点击商店NPC时,打开商店界面
        这是引擎事件回调，只接受1个参数

        Args:
            args: dict 事件参数
                - playerId: 玩家ID
                - entityId: 实体ID
        """
        player_id = args.get('playerId')
        entity_id = args.get('entityId')

        # 检查是否是商店NPC
        if entity_id != self.shop_npc_id:
            return

        print("[INFO] [商店] 玩家交互: player={}, npc={}".format(player_id, entity_id))

        # 检查玩家是否可以使用商店
        if not self._can_player_use_shop(player_id):
            print("[INFO] [商店] 玩家无权使用商店: {}".format(player_id))
            # TODO: 显示提示消息
            # self._show_tip_message(player_id, "你无法使用这个商店!")
            return

        # 打开商店界面
        self._open_shop_ui(player_id)

    def _on_try_buy(self, event_name, event_data):
        """
        处理购买尝试事件

        验证并处理玩家的购买请求

        Args:
            event_name: 事件名称
            event_data: 事件数据
                - playerId: 玩家ID
                - goods_id: 商品ID
                - category_id: 分类ID
        """
        player_id = event_data.get('playerId')
        goods_id = event_data.get('goods_id')
        category_id = event_data.get('category_id')

        print("[INFO] [商店] 尝试购买: player={}, goods={}".format(player_id, goods_id))

        # 检查玩家是否可以使用商店
        if not self._can_player_use_shop(player_id):
            self._send_buy_result(player_id, False, "你无法使用这个商店!")
            return

        # 处理购买逻辑
        success, message = self._process_purchase(player_id, goods_id, category_id)
        self._send_buy_result(player_id, success, message)

    def _on_bedwars_running(self, event_name, event_data):
        """
        处理游戏开始事件

        Args:
            event_name: 事件名称（固定为"BedWarsRunning"）
            event_data: 事件数据

        Note:
            ECPreset框架的事件回调必须接受2个参数（参考EventBus.py:108）
        """
        print("[INFO] [商店] 游戏开始事件,创建NPC")

        # 游戏进入Running状态后创建NPC
        # 参考: ShopPresetDefServer.py.backup:238-239
        self._create_shop_npc(self.instance)

    def _on_bedwars_ending(self, event_name, event_data):
        """
        处理游戏结束事件

        Args:
            event_name: 事件名称
            event_data: 事件数据
        """
        print("[INFO] [商店] 游戏结束事件,销毁NPC")

        # 销毁商店NPC
        if self.shop_npc_id:
            self.destroy_entity(self.shop_npc_id)
            self.shop_npc_id = None

    def _on_team_update(self, event_name, event_data):
        """
        处理队伍玩家更新事件

        同步最新的可使用玩家列表

        Args:
            event_name: 事件名称
            event_data: 事件数据
                - dimension: 维度ID
                - player_to_team: 玩家ID -> 队伍ID映射
        """
        # 只处理本维度的事件
        if event_data.get('dimension') != self.instance.get_dimension():
            return

        # 更新可使用玩家列表
        player_to_team = event_data.get('player_to_team', {})

        if self.team == "NONE":
            # 公共商店,所有玩家都可以使用
            self.usable_players = player_to_team.keys()
        else:
            # 队伍商店,只有队伍成员可以使用
            self.usable_players = [
                player_id for player_id, team in player_to_team.iteritems()
                if team == self.team
            ]

        print("[INFO] [商店] 更新可使用玩家: {}".format(len(self.usable_players)))

    # ========== 内部辅助方法 ==========

    def _create_shop_npc(self, instance):
        """
        创建商店NPC - 使用异步创建避免区块未加载问题

        参考: GuideShopPresetDefServer.py - 正确的异步创建实现
        原因: 网易引擎限制,实体必须在已加载的区块中创建
        文档: EntityPresetServerBase.create_entity_async() 方法

        Args:
            instance: PresetInstance对象
        """
        if self.shop_npc_id:
            print("[WARN] [商店] NPC已存在,跳过创建")
            return

        # 获取NPC位置
        npc_pos = instance.get_config("pos")
        if not npc_pos:
            print("[ERROR] [商店] NPC位置配置缺失")
            return

        # ⚠️ CRITICAL: 获取当前游戏维度，而非从配置读取
        # 参考: BedPresetDefServer.py:1005-1024 - 正确的维度获取逻辑
        # 原因: 配置中没有dimension_id字段，需要从RoomManagementSystem获取当前游戏维度
        import mod.server.extraServerApi as serverApi
        room_system = serverApi.GetSystem(MOD_NAME, "RoomManagementSystem")

        dimension = None
        if room_system and hasattr(room_system, 'current_dimension') and room_system.current_dimension is not None:
            dimension = room_system.current_dimension
            print("[商店] 从RoomManagementSystem获取维度: {}".format(dimension))
        else:
            # 备用方案：从配置获取
            dimension = instance.get_config("dimension_id", 0)
            print("[WARN] [商店] RoomManagementSystem不可用,使用默认维度: {}".format(dimension))

        # 准备旋转参数
        rotation = instance.get_config("rotation", {"pitch": 0, "yaw": 0})

        # ⚠️ CRITICAL: 从配置中读取runtime_entity_id,不要硬编码
        # 配置文件中使用 "ecbedwars:shop" 自定义实体
        entity_identifier = instance.get_config("runtime_entity_id", "ecbedwars:shop")

        print("[商店] 准备异步创建NPC: entity={}, pos={}, dimension={}".format(
            entity_identifier, npc_pos, dimension
        ))

        # 使用基类的异步创建实体方法
        # 先加载区块,再创建实体,避免在未加载区块中创建失败
        # ⚠️ CRITICAL: is_npc必须为False，否则NPC无法转向看向玩家
        # 文档依据: GuideShopPresetDefServer.py:90-98 - SDK文档说明isNpc=True会导致实体不会移动、不会转向
        # 参考: GuideShopPresetDefServer.py 的正确实现
        self.create_entity_async(
            entity_identifier=entity_identifier,
            pos=npc_pos,
            rotation=rotation,
            dimension_id=dimension,
            callback=self._on_npc_created,
            is_npc=False,  # 必须为False，否则无法转向看向玩家
            is_global=False,
            chunk_radius=1
        )

    def _on_npc_created(self, entity_id):
        """
        NPC创建完成回调

        Args:
            entity_id: 创建的实体ID,失败为None
        """
        try:
            if not entity_id:
                print("[ERROR] [商店] NPC创建失败")
                return

            self.shop_npc_id = entity_id
            print("[商店] NPC创建成功: id={}".format(self.shop_npc_id))

            # 延迟0.5秒设置名字和皮肤（确保实体完全初始化）
            import mod.server.extraServerApi as serverApi
            game_comp = serverApi.GetEngineCompFactory().CreateGame(serverApi.GetLevelId())
            if game_comp:
                game_comp.AddTimer(0.5, self._apply_npc_settings)
            else:
                print("[ERROR] [商店] 无法获取Game组件，定时器设置失败")

        except Exception as e:
            print("[ERROR] [商店] _on_npc_created异常: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _apply_npc_settings(self):
        """
        应用NPC设置（名字+皮肤）

        在NPC创建后延迟0.5秒调用，确保实体完全初始化
        """
        if not self.shop_npc_id:
            return

        try:
            import mod.server.extraServerApi as serverApi

            # 1. 设置NPC名字
            name_comp = serverApi.GetEngineCompFactory().CreateName(self.shop_npc_id)
            if name_comp:
                # 使用str()包裹名字字符串，避免类型问题（参考MODSDK文档：踩坑总结）
                name_str = str(self.shop_npc_name)
                success = name_comp.SetName(name_str)
                if success:
                    print("[INFO] [商店] NPC名字设置成功: entity_id={}, name={}".format(
                        self.shop_npc_id, self.shop_npc_name))

                    # 通知所有客户端设置名字显示
                    if self.instance:
                        self.instance.send_to_client("ShopNpcShowName", {
                            "entity_id": self.shop_npc_id
                        })
                else:
                    print("[ERROR] [商店] NPC名字设置失败")
            else:
                print("[ERROR] [商店] 无法获取Name组件")

            # 2. 设置村民皮肤变体
            self._apply_npc_skin_variant()

        except Exception as e:
            print("[ERROR] [商店] 应用NPC设置异常: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _apply_npc_skin_variant(self):
        """
        应用NPC皮肤变体

        设置村民皮肤和持久化属性
        """
        if not self.shop_npc_id:
            return

        try:
            import mod.server.extraServerApi as serverApi
            import random

            # 设置村民皮肤变体
            entity_def_comp = serverApi.GetEngineCompFactory().CreateEntityDefinitions(self.shop_npc_id)
            if entity_def_comp:
                biome = random.randrange(0, 6)
                profession = random.randrange(0, 14)
                mark_variant_value = biome * 100 + profession

                success = entity_def_comp.SetMarkVariant(mark_variant_value)
                if success:
                    print("[INFO] [商店] 村民皮肤变体设置成功: biome={}, profession={}".format(biome, profession))
                else:
                    print("[WARN] [商店] 村民皮肤变体设置失败")

            # 设置实体不会因为距离玩家太远而清除
            comp = serverApi.GetEngineCompFactory().CreateAttr(self.shop_npc_id)
            if comp:
                comp.SetPersistent(True)
                print("[INFO] [商店] NPC持久化设置成功")

        except Exception as e:
            print("[ERROR] [商店] 应用皮肤变体异常: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _load_shop_config(self):
        """
        加载商店配置

        从游戏配置系统获取商店的商品配置
        """
        # TODO: 需要从游戏配置系统获取
        # 暂时使用硬编码配置
        self.shop_config = {
            'shop_type': self.shop_type,
            'categories': [
                {
                    'id': 'blocks',
                    'name': '方块',
                    'goods': [
                        {
                            'id': 'wool',
                            'name': '羊毛',
                            'item': 'minecraft:wool',
                            'count': 16,
                            'price': {'currency': 'iron', 'amount': 4}
                        },
                        {
                            'id': 'wood',
                            'name': '木板',
                            'item': 'minecraft:planks',
                            'count': 16,
                            'price': {'currency': 'gold', 'amount': 4}
                        }
                    ]
                },
                {
                    'id': 'weapons',
                    'name': '武器',
                    'goods': [
                        {
                            'id': 'stone_sword',
                            'name': '石剑',
                            'item': 'minecraft:stone_sword',
                            'count': 1,
                            'price': {'currency': 'iron', 'amount': 10}
                        }
                    ]
                }
            ]
        }

        print("[INFO] [商店] 加载配置: type={}".format(self.shop_type))

    def _init_usable_players(self):
        """
        初始化可使用玩家列表

        从游戏系统获取队伍玩家信息
        """
        # TODO: 需要从游戏系统获取
        # 暂时使用空列表
        self.usable_players = []

    def _can_player_use_shop(self, player_id):
        """
        检查玩家是否可以使用商店

        Args:
            player_id: 玩家ID

        Returns:
            bool: 是否可以使用
        """
        # 如果是公共商店,所有玩家都可以使用
        if self.team == "NONE":
            return True

        # 如果是队伍商店,只有队伍成员可以使用
        return player_id in self.usable_players

    def _open_shop_ui(self, player_id):
        """
        打开商店UI

        转发到ShopServerSystem处理
        参考: ShopPresetDefServer.py.backup:487-506

        Args:
            player_id (str): 玩家ID
        """
        import mod.server.extraServerApi as serverApi

        # 获取ShopServerSystem
        shop_system = serverApi.GetSystem(MOD_NAME, "ShopServerSystem")
        if not shop_system:
            print("[ERROR] [商店] ShopServerSystem未找到")
            return

        # 转发到ShopServerSystem
        shop_system.handle_player_open_shop(player_id, self.team, self.shop_type)
        print("[商店] 已转发打开商店请求到ShopServerSystem: player={}, type={}".format(
            player_id, self.shop_type))

    def _process_purchase(self, player_id, goods_id, category_id):
        """
        处理购买逻辑

        步骤:
        1. 查找商品配置
        2. 检查是否为队伍升级
        3. 检查玩家货币是否足够
        4. 扣除货币
        5. 给予物品或应用升级

        Args:
            player_id: 玩家ID
            goods_id: 商品ID
            category_id: 分类ID

        Returns:
            tuple: (是否成功, 消息)
        """
        # 1. 查找商品配置
        goods = self._find_goods(goods_id, category_id)
        if not goods:
            return False, "商品不存在"

        # 2. 检查是否为队伍升级
        if category_id == 'upgrades':
            return self._process_team_upgrade_purchase(player_id, goods_id, goods)

        # 2.5 检查是否为陷阱购买
        if category_id == 'traps':
            return self._process_trap_purchase(player_id, goods_id, goods)

        # 3. 检查玩家货币
        price = goods.get('price', {})
        currency = price.get('currency', 'iron')
        amount = price.get('amount', 0)

        # TODO: 需要引擎API支持检查玩家物品栏
        # has_enough = self._check_player_currency(player_id, currency, amount)
        # if not has_enough:
        #     return False, "货币不足"

        # 4. 扣除货币
        # TODO: 需要引擎API支持扣除物品
        # self._remove_player_currency(player_id, currency, amount)

        # 5. 给予物品
        item_name = goods.get('item')
        item_count = goods.get('count', 1)

        # TODO: 需要引擎API支持给予物品
        # self._give_item_to_player(player_id, item_name, item_count)

        print("[INFO] [商店] 购买成功: player={}, goods={}".format(player_id, goods_id))
        return True, "购买成功"

    def _find_goods(self, goods_id, category_id):
        """
        查找商品配置

        Args:
            goods_id: 商品ID
            category_id: 分类ID

        Returns:
            dict: 商品配置,如果不存在返回None
        """
        if not self.shop_config:
            return None

        for category in self.shop_config.get('categories', []):
            if category['id'] == category_id:
                for goods in category.get('goods', []):
                    if goods['id'] == goods_id:
                        return goods

        return None

    def _send_buy_result(self, player_id, success, message):
        """
        发送购买结果到客户端

        Args:
            player_id: 玩家ID
            success: 是否成功
            message: 消息
        """
        result_data = {
            'success': success,
            'msg': message
        }

        # 发送事件到客户端
        self.instance.manager.event_bus.emit_event('BedWarsShopBuyResult', result_data, target_player=player_id)

    # ========== 队伍升级购买处理 ==========

    def _process_team_upgrade_purchase(self, player_id, upgrade_key, goods):
        """
        处理队伍升级购买

        Args:
            player_id: 玩家ID
            upgrade_key: 升级键名
            goods: 商品配置

        Returns:
            tuple: (是否成功, 消息)
        """
        try:
            # 获取游戏系统
            game_system = self._get_bedwars_game_system()
            if not game_system:
                return False, "游戏系统未启动"

            # 获取玩家队伍
            if not game_system.team_module:
                return False, "队伍系统未初始化"

            player_team = game_system.team_module.get_player_team(player_id)
            if not player_team:
                return False, "你不在任何队伍中"

            # 获取队伍升级管理器
            upgrade_manager = game_system.team_module.get_team_upgrade_manager(player_team)
            if not upgrade_manager:
                return False, "升级管理器未初始化"

            # 检查是否已达最大等级
            if upgrade_manager.is_upgrade_max_level(upgrade_key):
                return False, "该升级已达最大等级"

            # 获取当前等级和价格配置
            current_level = upgrade_manager.get_upgrade_level(upgrade_key)
            levels_config = goods.get('levels', [])

            if current_level >= len(levels_config):
                return False, "升级等级配置错误"

            level_config = levels_config[current_level]
            price = level_config.get('price', {})

            # 检查并扣除资源
            # TODO: 实现资源检查和扣除逻辑
            # for currency, amount in price.items():
            #     if not self._check_player_currency(player_id, currency, amount):
            #         return False, "资源不足: {} x{}".format(currency, amount)
            #
            # for currency, amount in price.items():
            #     self._remove_player_currency(player_id, currency, amount)

            # 购买升级
            success = upgrade_manager.purchase_upgrade(upgrade_key)
            if success:
                print("[INFO] [商店] 队伍升级成功: team={}, upgrade={}, level={}".format(
                    player_team, upgrade_key, current_level + 1))
                return True, "升级购买成功"
            else:
                return False, "升级购买失败"

        except Exception as e:
            print("[ERROR] [商店] 处理队伍升级购买出错: {}".format(str(e)))
            return False, "购买失败: {}".format(str(e))

    def _get_bedwars_game_system(self):
        """
        获取BedWarsGameSystem实例

        Returns:
            BedWarsGameSystem实例,如果不存在返回None
        """
        try:
            # 通过预设管理器获取系统引用
            import mod.server.extraServerApi as serverApi
            # 使用MOD_NAME和系统名称获取游戏系统
            game_system = serverApi.GetSystem(MOD_NAME, "BedWarsGameSystem")
            return game_system
        except Exception as e:
            print("[ERROR] [商店] 获取游戏系统失败: {}".format(str(e)))
            return None

    def _process_trap_purchase(self, player_id, trap_key, goods):
        """
        处理陷阱购买

        Args:
            player_id: 玩家ID
            trap_key: 陷阱键名
            goods: 商品配置

        Returns:
            tuple: (是否成功, 消息)
        """
        try:
            # 获取游戏系统
            game_system = self._get_bedwars_game_system()
            if not game_system:
                return False, "游戏系统未启动"

            # 获取玩家队伍
            if not game_system.team_module:
                return False, "队伍系统未初始化"

            player_team = game_system.team_module.get_player_team(player_id)
            if not player_team:
                return False, "你不在任何队伍中"

            # 获取队伍陷阱管理器
            trap_manager = game_system.get_team_trap_manager(player_team)
            if not trap_manager:
                return False, "陷阱管理器未初始化"

            # 检查陷阱是否已满
            if trap_manager.is_trap_full():
                return False, "陷阱已满（最多3个）"

            # 获取价格配置
            price = goods.get('price', {})

            # 检查并扣除资源
            # TODO: 实现资源检查和扣除逻辑
            # for currency, amount in price.items():
            #     if not self._check_player_currency(player_id, currency, amount):
            #         return False, "资源不足: {} x{}".format(currency, amount)
            #
            # for currency, amount in price.items():
            #     self._remove_player_currency(player_id, currency, amount)

            # 添加陷阱
            success = trap_manager.add_trap(trap_key)
            if success:
                print("[INFO] [商店] 陷阱购买成功: team={}, trap={}, count={}".format(
                    player_team, trap_key, trap_manager.get_trap_count()))
                return True, "陷阱购买成功"
            else:
                return False, "陷阱购买失败"

        except Exception as e:
            print("[ERROR] [商店] 处理陷阱购买出错: {}".format(str(e)))
            return False, "购买失败: {}".format(str(e))