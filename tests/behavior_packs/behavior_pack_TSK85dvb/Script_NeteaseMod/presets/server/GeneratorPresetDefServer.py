# -*- coding: utf-8 -*-
"""
产矿机预设 - 服务端

功能:
- 定时生成资源 (铜/铁/金/钻石/绿宝石)
- 等级升级机制
- 资源数量上限控制
- 共享产出机制 (everybody模式)
- 物品拾取白名单
"""

from ECPresetServerScripts import PresetDefinitionServer
import time
import random


class GeneratorPresetDefServer(PresetDefinitionServer):
    """
    产矿机预设服务端实现

    核心功能:
    1. 定时生成资源物品
    2. 等级管理 (不同等级产矿速度不同)
    3. 资源数量上限控制 (避免堆积过多)
    4. 共享产出 (everybody模式: 直接发到附近玩家背包)
    5. 物品拾取白名单 (队伍专属产矿机)
    """

    # ===== [CRITICAL FIX] 启用Tick更新 =====
    # 根据ECPreset框架要求,必须设置enable_tick=True才能让on_tick被调用
    enable_tick = True

    def __init__(self):
        super(GeneratorPresetDefServer, self).__init__()

        # 配置数据
        self.resource_type_id = None  # type: str | None  # 资源类型ID (IRON, GOLD, DIAMOND, EMERALD等)
        self.team = None  # type: str | None  # 队伍ID (如果是None表示公共产矿机)
        self.display_floating = True  # type: bool  # 是否显示浮空物品和文字
        self.everybody = False  # type: bool  # 是否开启共享产出 (直接发到附近玩家背包)
        self.default_level = 1  # type: int  # 默认等级

        # 运行时状态
        self.level = 1  # type: int  # 当前等级
        self.next_generate = 0.0  # type: float  # 下次生成时间 (时间戳)
        self.resource_type = None  # type: dict | None  # 资源类型配置
        self.levels_config = None  # type: list | None  # 不同等级的配置列表
        self.item_pickup_whitelist = {}  # type: dict  # 物品拾取白名单 {entity_id: (timeout, player_id)}
        self.generated_items = []  # type: list  # 已生成的物品实体ID列表
        self.max_items = 5  # type: int  # 最大物品数量

    def on_init(self, instance):
        """
        预设初始化

        解析配置数据:
        - resource_type_id: 资源类型
        - team: 队伍ID
        - display_floating: 是否显示浮空
        - everybody: 是否共享产出
        - default_level: 默认等级

        Args:
            instance: PresetInstance对象
        """
        self.resource_type_id = instance.get_config("resource_type_id", "IRON")
        self.team = instance.get_config("team", "NONE")
        self.display_floating = instance.get_config("display_floating", True)
        self.everybody = instance.get_config("everybody", False)
        self.default_level = instance.get_config("default_level", 1)

        # 保存配置到instance
        instance.set_data("resource_type_id", self.resource_type_id)
        instance.set_data("team", self.team)
        instance.set_data("level", self.default_level)

    def on_start(self, instance):
        """
        预设启动

        执行步骤:
        1. 设置初始等级
        2. 加载资源类型配置
        3. 加载等级配置
        4. 注册事件监听
        5. 启动产矿
        6. 同步数据到客户端

        Args:
            instance: PresetInstance对象
        """
        # 1. 设置初始等级
        self.level = self.default_level

        # 2. 加载资源类型配置
        self._load_resource_type_config()

        # 3. 加载等级配置
        self._load_levels_config(instance)

        # 保存instance引用
        self.instance = instance

        # 4. 注册事件监听
        import mod.server.extraServerApi as serverApi
        server_system = instance.manager.server_api

        if server_system:
            # 监听物品拾取事件 - 引擎事件
            server_system.ListenForEvent(
                serverApi.GetEngineNamespace(),
                serverApi.GetEngineSystemName(),
                "ServerPlayerTryTouchEvent",
                self,
                self._on_player_try_pickup
            )

        # 监听等级升级事件 - 自定义事件
        instance.subscribe_event("GeneratorLevelUp", self._on_level_up)

        # 监听游戏运行事件 - 用于在游戏开始后通知客户端创建浮动文字
        instance.subscribe_event("BedWarsRunning", self._on_game_running)

        # 5. 启动产矿
        self._start_generator()

        # 6. 同步数据到客户端 (P1.2功能需要)
        self._sync_generator_data_to_client(instance)

    def on_tick(self, instance, dt):
        """
        每Tick更新

        检查是否到达生成时间,如果是则生成资源

        Args:
            instance: PresetInstance对象
            dt: 距离上次tick的时间间隔(秒)
        """
        if self.levels_config is None:
            return

        # 检查游戏是否正在运行
        if not self._is_game_running():
            return

        # 如果等级为0,暂停产矿
        if self.level == 0:
            return

        now = time.time()
        if now >= self.next_generate:
            # 计算下次生成时间
            current_config = self._get_current_level_config()
            if current_config:
                period_ms = current_config.get('period', 5000)  # 默认5秒
                self.next_generate = now + (period_ms / 1000.0)

                # 生成资源
                self._generate_item(instance)

                # ⚠️ 关键修复：同步新的next_generate到客户端，以便客户端倒计时正确更新
                self._sync_generator_data_to_client(instance)

            # 清理过期的白名单条目
            self._cleanup_whitelist(now)

    def on_stop(self, instance):
        """
        预设停止

        清理工作:
        1. 取消事件监听
        2. 清理生成的物品
        3. 清空白名单

        Args:
            instance: PresetInstance对象
        """
        # 取消事件监听
        # EventBus事件会自动取消订阅
        # EventBus事件会自动取消订阅

        # ⚠️ 关键修复：清理所有生成的物品实体（参考GuideGenerator实现）
        self._cleanup_generated_items(instance)

        # 清空白名单
        self.item_pickup_whitelist = {}

    def on_destroy(self, instance):
        """
        预设销毁

        最终清理工作

        Args:
            instance: PresetInstance对象
        """
        # ⚠️ 关键修复：清理所有生成的物品实体
        self._cleanup_generated_items(instance)

        # 清理数据
        self.levels_config = None
        self.resource_type = None

    def _cleanup_generated_items(self, instance):
        """
        清理所有生成的物品实体（参考GuideGenerator实现）

        Args:
            instance: PresetInstance对象
        """
        for entity_id in self.generated_items:
            try:
                server_system = instance.manager.server_api
                if server_system:
                    server_system.DestroyEntity(entity_id)
            except Exception as e:
                print("[ERROR] [产矿机] 清理物品异常: {}".format(e))

        self.generated_items = []

    # ========== 事件处理方法 ==========

    def _on_player_try_pickup(self, event_data):
        """
        处理玩家尝试拾取物品事件

        如果物品在白名单中且不是对应玩家,则阻止拾取

        Args:
            event_data: 事件数据
                - playerId: 玩家ID
                - entityId: 实体ID
                - cancel: 是否取消拾取
        """
        player_id = event_data.get('playerId')
        entity_id = event_data.get('entityId')

        if entity_id in self.item_pickup_whitelist:
            timeout, whitelisted_player = self.item_pickup_whitelist[entity_id]

            # 检查是否过期
            if time.time() < timeout:
                # 如果不是白名单玩家,阻止拾取
                if player_id != whitelisted_player:
                    event_data['cancel'] = True
            else:
                # 已过期,删除白名单条目
                del self.item_pickup_whitelist[entity_id]

    def _on_level_up(self, event_name, event_data):
        """
        处理产矿机等级升级事件

        Args:
            event_name (str): 事件名称
            event_data (dict): 事件数据
                - resource_types (list): 要升级的资源类型列表（大写）
                - teams (list): 要升级的队伍列表（大写）
                - new_level (int): 新等级
        """
        # 解析事件数据
        resource_types = event_data.get('resource_types', [])
        teams = event_data.get('teams', [])
        new_level = event_data.get('new_level')

        # 兼容旧格式（单个资源类型）
        if not resource_types and 'generator_type' in event_data:
            resource_types = [event_data.get('generator_type')]

        # 检查本产矿机的资源类型和队伍是否在升级列表中
        my_resource_type = self.resource_type_id.upper()
        my_team = self.team.upper() if self.team else 'NONE'

        if my_resource_type in resource_types and my_team in teams:
            old_level = self.level

            # 更新等级
            self.level = new_level

            # 获取新等级的配置
            new_config = self._get_current_level_config()
            if new_config:
                # 计算新周期的下次生成时间
                new_period_ms = new_config.get('period', 5000)
                new_period_sec = new_period_ms / 1000.0
                new_next_generate = time.time() + new_period_sec

                # 如果新周期更短(等级提升),立即调整下次生成时间
                # 这样可以让升级后的产矿速度立即生效
                if new_next_generate < self.next_generate:
                    self.next_generate = new_next_generate

            # 同步数据到客户端 (P1.2功能需要)
            self._sync_generator_data_to_client(self.instance)

    def _on_game_running(self, event_name, event_data):
        """
        处理游戏运行事件（状态机进入running状态）

        此时所有玩家已传送到游戏维度并播放完运镜
        通知客户端创建浮动文字，确保TextBoard在正确的维度创建

        Args:
            event_name (str): 事件名称
            event_data (dict): 事件数据
        """
        # 只有display_floating为True的产矿机才发送创建消息
        if not self.display_floating:
            return

        # 通知所有客户端创建浮动文字
        self.instance.send_to_client("CreateFloatingText", {})

    # ========== 内部辅助方法 ==========

    def _load_resource_type_config(self):
        """
        加载资源类型配置 - 从Python配置模块导入

        从配置模块中获取资源类型的详细信息:
        - item: 物品名称
        - top_count: 最大数量
        - floating_item: 浮空物品
        - particle_color: 粒子颜色
        """
        try:
            # 从配置模块导入
            from Script_NeteaseMod.config.generator_config import RESOURCE_TYPES

            # 获取资源类型配置
            self.resource_type = RESOURCE_TYPES.get(self.resource_type_id.upper())

            if not self.resource_type:
                print("[ERROR] [产矿机] 未知的资源类型: {}".format(self.resource_type_id))
                # 使用默认铁锭配置
                self.resource_type = RESOURCE_TYPES.get('IRON')

        except Exception as e:
            print("[ERROR] [产矿机] 加载资源类型配置失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

            # 使用默认配置
            self.resource_type = {
                'name': '铁锭',
                'item': 'minecraft:iron_ingot',
                'top_count': 64,
                'particle_color': [224, 224, 224],
                'floating_item': {'itemName': 'minecraft:iron_ingot', 'count': 1, 'auxValue': 0}
            }

    def _load_levels_config(self, instance):
        """
        加载等级配置 - 从Python配置模块导入

        从配置模块中获取不同等级的产矿速度和数量配置

        Args:
            instance: PresetInstance对象
        """
        try:
            # 从配置模块导入
            from Script_NeteaseMod.config.generator_config import UPGRADE_LEVELS

            # 获取资源类型配置键
            resource_config_key = self.resource_type_id.upper()

            # [P0修复] 针对8队模式的绿宝石,使用专用配置
            if resource_config_key == "EMERALD":
                # 尝试从RoomManagementSystem获取当前游戏模式
                try:
                    import mod.server.extraServerApi as serverApi
                    room_system = serverApi.GetSystem("ECBedWars", "RoomManagementSystem")

                    if room_system and hasattr(room_system, 'current_stage_config'):
                        game_mode = room_system.current_stage_config.get("mode", "team2")

                        # 8队模式使用专用绿宝石配置
                        if game_mode == "team8":
                            resource_config_key = "EMERALD_TEAM8"
                except Exception as e:
                    pass  # 使用默认绿宝石配置

            # 获取升级等级配置
            self.levels_config = UPGRADE_LEVELS.get(resource_config_key)

            if not self.levels_config:
                print("[ERROR] [产矿机] 未找到等级配置: {}".format(resource_config_key))
                # 使用默认配置
                self.levels_config = [
                    {'level': 1, 'period': 5000, 'count': 1},
                    {'level': 2, 'period': 3000, 'count': 1},
                    {'level': 3, 'period': 2000, 'count': 1},
                    {'level': 4, 'period': 1000, 'count': 2},
                ]

        except Exception as e:
            print("[ERROR] [产矿机] 加载等级配置失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

            # 使用默认配置
            self.levels_config = [
                {'level': 1, 'period': 5000, 'count': 1},
                {'level': 2, 'period': 3000, 'count': 1},
                {'level': 3, 'period': 2000, 'count': 1},
                {'level': 4, 'period': 1000, 'count': 2},
            ]

    def _start_generator(self):
        """
        启动产矿机

        设置下次生成时间为当前时间,立即开始产矿
        """
        self.next_generate = time.time()

    def _get_current_level_config(self):
        """
        获取当前等级的配置

        Returns:
            dict: 等级配置 {'level': 1, 'period': 5000, 'count': 1}
                  如果配置不存在,返回None
        """
        if not self.levels_config:
            return None

        if self.level < 1 or self.level > len(self.levels_config):
            print("[ERROR] [产矿机] 无效的等级: {}".format(self.level))
            return None

        return self.levels_config[self.level - 1]

    def _generate_item(self, instance):
        """
        生成资源物品

        步骤:
        1. ⚠️ 关键优化：生成前验证队列中实体存在性（清理已被拾取的物品）
        2. ⚠️ 关键修复：使用FIFO队列管理上限（参考GuideGenerator实现）
        3. 根据everybody模式决定生成方式:
           - True: 直接发到附近玩家背包
           - False: 生成掉落物实体
        4. 发送特效事件到客户端

        Args:
            instance: PresetInstance对象
        """
        # 1. ⚠️ 关键优化：生成前清理已被拾取/销毁的物品（验证实体存在性）
        self._validate_and_cleanup_items()

        # 2. 检查FIFO队列是否已达上限
        top_count = self.resource_type.get('top_count', 64)
        current_count = len(self.generated_items)

        # 如果达到上限，删除最早的物品（FIFO）
        if current_count >= top_count:
            oldest_item = self.generated_items.pop(0)
            try:
                server_system = instance.manager.server_api
                if server_system:
                    server_system.DestroyEntity(oldest_item)
            except Exception as e:
                print("[ERROR] [产矿机] 清理旧物品异常: {}".format(e))

        # 2. 获取生成数量
        current_config = self._get_current_level_config()
        if not current_config:
            return

        count = current_config.get('count', 1)

        # 3. 生成物品
        if self.everybody:
            # 共享产出模式: 获取附近玩家
            nearby_players = self._get_nearby_players(instance, distance=2.0)
            if nearby_players:
                # 直接发到玩家背包
                for player_id in nearby_players:
                    for i in range(count):
                        self._spawn_item_to_player(player_id)
            else:
                # 没有附近玩家,生成掉落物
                for i in range(count):
                    self._spawn_entity_item(instance)
        else:
            # 普通模式: 生成掉落物
            for i in range(count):
                self._spawn_entity_item(instance)

        # 4. 播放音效
        self._play_spawn_sound(instance)

        # 5. 发送粒子特效消息到客户端
        self._send_particle_effect_to_client(instance)

    def _count_around_items(self, instance):
        """
        统计周围的资源物品数量

        检测产矿机周围±1格范围内的物品掉落

        Args:
            instance: PresetInstance对象

        Returns:
            int: 周围物品总数量
        """
        try:
            import mod.server.extraServerApi as serverApi
            pos = instance.get_config("pos")
            # ⚠️ 关键修复：使用与生成时相同的维度获取方式
            dimension = self._get_current_dimension(instance)

            # 获取游戏组件
            comp_game = serverApi.GetEngineCompFactory().CreateGame(serverApi.GetLevelId())
            comp_item = serverApi.GetEngineCompFactory().CreateItem(serverApi.GetLevelId())

            # 获取周围±1格范围内的所有实体
            # 注意: pos是列表格式[x, y, z],不是字典
            entities = comp_game.GetEntitiesInSquareArea(
                dimension,
                (pos[0] - 1, pos[1] - 1, pos[2] - 1),
                (pos[0] + 1, pos[1] + 2, pos[2] + 1)
            )

            count = 0
            item_count_found = 0
            for entity_id in entities:
                # 检查是否是物品实体
                comp_type = serverApi.GetEngineCompFactory().CreateEngineType(entity_id)
                entity_type = comp_type.GetEngineType()

                # 获取物品实体类型枚举
                EntityTypeEnum = serverApi.GetMinecraftEnum().EntityType
                if entity_type == EntityTypeEnum.ItemEntity:
                    # 获取掉落物品信息
                    item_info = comp_item.GetDroppedItem(entity_id)
                    if item_info:
                        item_name = item_info.get('itemName')
                        item_stack_count = item_info.get('count', 0)
                        if item_name == self.resource_type.get('item'):
                            count += item_stack_count
                            item_count_found += 1

            return count

        except Exception as e:
            print("[ERROR] [产矿机] 统计周围物品失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()
            return 0

    def _get_nearby_players(self, instance, distance=2.0):
        """
        获取附近的玩家列表

        Args:
            instance: PresetInstance对象
            distance: 检测距离

        Returns:
            list: 玩家ID列表
        """
        try:
            import mod.server.extraServerApi as serverApi
            pos = instance.get_config("pos")
            dimension = instance.get_config("dimension_id", 0)

            # 获取游戏组件
            comp_game = serverApi.GetEngineCompFactory().CreateGame(serverApi.GetLevelId())

            # 获取附近范围内的所有实体
            # 注意: pos是列表格式[x, y, z],不是字典
            entities = comp_game.GetEntitiesInSquareArea(
                dimension,
                (pos[0] - distance, pos[1] - distance, pos[2] - distance),
                (pos[0] + distance, pos[1] + distance, pos[2] + distance)
            )

            players = []
            for entity_id in entities:
                # 检查是否是玩家实体
                comp_type = serverApi.GetEngineCompFactory().CreateEngineType(entity_id)
                entity_type = comp_type.GetEngineType()

                # 获取实体类型枚举
                EntityTypeEnum = serverApi.GetMinecraftEnum().EntityType
                if entity_type == EntityTypeEnum.Player:
                    players.append(entity_id)

            return players

        except Exception as e:
            print("[ERROR] [产矿机] 获取附近玩家失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()
            return []

    def _spawn_item_to_player(self, player_id):
        """
        生成物品到玩家背包

        Args:
            player_id: 玩家ID
        """
        try:
            import mod.server.extraServerApi as serverApi

            # 获取物品组件
            item_comp = serverApi.GetEngineCompFactory().CreateItem(player_id)

            # 构造物品数据
            item_dict = {
                'itemName': self.resource_type.get('item'),
                'count': 1,
                'auxValue': 0
            }

            # 给予物品到玩家背包
            success = item_comp.SpawnItemToPlayerInv(item_dict, player_id)
            return success

        except Exception as e:
            print("[ERROR] [产矿机] 发送物品到玩家异常: player={}, error={}".format(
                player_id, str(e)
            ))
            import traceback
            traceback.print_exc()
            return False

    def _spawn_entity_item(self, instance):
        """
        生成掉落物实体（使用CreateEngineItemEntity获取entity_id）

        Args:
            instance: PresetInstance对象
        """
        try:
            import mod.server.extraServerApi as serverApi
            import random

            pos = instance.get_config("pos")

            # 从RoomManagementSystem获取当前对局的维度ID
            dimension = self._get_current_dimension(instance)

            # 构造物品数据
            item_dict = {
                'itemName': self.resource_type.get('item'),
                'count': 1,
                'auxValue': 0,
                'enchantData': []
            }

            # 在产矿机位置上方0.5格生成掉落物
            spawn_pos = (pos[0], pos[1] + 0.5, pos[2])

            # ⚠️ 关键修复：使用CreateEngineItemEntity（参考GuideGenerator实现）
            # 这个API会返回entity_id（不是True/False），可以被追踪
            server_system = instance.manager.server_api
            if not server_system:
                print("[WARN] [产矿机] server_api未初始化，跳过生成")
                return

            entity_id = server_system.CreateEngineItemEntity(item_dict, dimension, spawn_pos)

            # entity_id可能是None(失败)或实体ID字符串(成功)
            if entity_id:
                # ⚠️ 关键修复：记录生成的物品ID到FIFO队列
                self.generated_items.append(entity_id)
            else:
                # 返回None表示失败，可能是区块未加载
                print("[WARN] [产矿机] 生成掉落物失败（可能区块未加载）: type={}".format(
                    self.resource_type_id
                ))

        except Exception as e:
            print("[ERROR] [产矿机] 生成掉落物异常: type={}, error={}".format(
                self.resource_type_id, str(e)
            ))
            import traceback
            traceback.print_exc()

    def _get_current_dimension(self, instance):
        """
        获取当前对局的维度ID

        参考BedPresetDefServer的实现,从RoomManagementSystem获取维度

        Args:
            instance: PresetInstance对象

        Returns:
            int: 维度ID
        """
        try:
            import mod.server.extraServerApi as serverApi

            # 从RoomManagementSystem获取当前对局的维度ID
            room_system = serverApi.GetSystem("ECBedWars", "RoomManagementSystem")

            # 优先使用RoomManagementSystem的维度
            if room_system and hasattr(room_system, 'current_dimension') and room_system.current_dimension is not None:
                dimension_id = room_system.current_dimension
                return dimension_id

            # 备用方案1：从配置获取
            dimension_id = instance.get_config("dimension_id", None)
            if dimension_id is not None:
                return dimension_id

            # 备用方案2：从预设实例属性获取
            if hasattr(self, 'dimension_id') and self.dimension_id is not None:
                return self.dimension_id

            # 最后使用默认维度0
            print("[WARN] [产矿机] 无法获取维度ID，使用默认维度0")
            return 0

        except Exception as e:
            print("[ERROR] [产矿机] 获取维度ID失败: {}".format(str(e)))
            return 0

    def _get_team_players(self):
        """
        获取队伍玩家列表

        Returns:
            list: 玩家ID列表
        """
        try:
            # 从BedWarsGameSystem获取队伍模块
            import mod.server.extraServerApi as serverApi
            from Script_NeteaseMod.modConfig import MOD_NAME, SERVER_SYSTEMS

            BEDWARS_GAME_SYSTEM = SERVER_SYSTEMS[0][0]
            game_system = serverApi.GetSystem(MOD_NAME, BEDWARS_GAME_SYSTEM)

            if game_system and hasattr(game_system, 'team_module') and game_system.team_module:
                team_players = game_system.team_module.get_team_players(self.team)
                return team_players if team_players else []

            return []

        except Exception as e:
            print("[ERROR] [产矿机] 获取队伍玩家失败: team={}, error={}".format(
                self.team, str(e)
            ))
            return []

    def _cleanup_whitelist(self, now):
        """
        清理过期的白名单条目

        Args:
            now: 当前时间戳
        """
        expired_ids = []
        for entity_id, (timeout, player_id) in self.item_pickup_whitelist.items():
            if now >= timeout:
                expired_ids.append(entity_id)

        for entity_id in expired_ids:
            del self.item_pickup_whitelist[entity_id]

    def _validate_and_cleanup_items(self):
        """
        ⚠️ 关键优化：验证队列中物品实体的存在性，清理已被拾取/销毁的物品

        原理：
        - 玩家拾取物品后，实体会被销毁，但entity_id仍在队列中
        - 通过GetFootPos()验证实体是否存在（不存在会返回None或抛异常）
        - 清理不存在的entity_id，确保队列准确反映实际物品数量

        参考：用户建议 - "生成矿物之前获取一下当前队列中全部矿物的实体位置"
        """
        if not self.generated_items:
            return

        import mod.server.extraServerApi as serverApi

        # 存储仍然存在的物品ID
        valid_items = []
        removed_count = 0

        for entity_id in self.generated_items:
            try:
                # 尝试获取实体位置来验证存在性
                pos_comp = serverApi.GetEngineCompFactory().CreatePos(entity_id)
                pos = pos_comp.GetFootPos()

                # 如果能成功获取位置，说明实体还存在
                if pos is not None:
                    valid_items.append(entity_id)
                else:
                    removed_count += 1
            except:
                # 获取位置失败，说明实体已被销毁（被拾取或其他原因）
                removed_count += 1

        # 更新队列
        self.generated_items = valid_items

    def _is_game_running(self):
        """
        检查游戏是否正在运行

        从BedWarsGameSystem获取当前游戏状态

        Returns:
            bool: True表示游戏正在运行,False表示游戏未运行
        """
        try:
            import mod.server.extraServerApi as serverApi
            from Script_NeteaseMod.modConfig import MOD_NAME

            # 获取BedWarsGameSystem
            game_system = serverApi.GetSystem(MOD_NAME, "BedWarsGameSystem")
            if not game_system:
                # 游戏系统不存在,默认暂停产矿
                return False

            # 检查游戏系统的root_state
            if not hasattr(game_system, 'root_state') or not game_system.root_state:
                return False

            # 检查当前状态是否是运行状态
            # 注意: RootGamingState没有get_current_state()方法,应该访问current_sub_state属性
            current_state = game_system.root_state.current_sub_state
            if not current_state:
                return False

            # 获取状态名称
            state_name = current_state.__class__.__name__

            # 只在BedWarsRunningState状态下产矿
            # 也可以检查其他状态,根据具体需求调整
            if state_name == "BedWarsRunningState":
                return True

            # 其他状态暂停产矿
            return False

        except Exception as e:
            # 出错时默认允许产矿(保险起见)
            print("[WARN] [产矿机] 检查游戏状态失败,默认允许产矿: {}".format(str(e)))
            return True

    # ========== P1.2功能实现 ==========

    def _sync_generator_data_to_client(self, instance):
        """
        同步产矿机数据到客户端

        P1.2功能需要：客户端需要这些数据来显示浮动文字和倒计时

        同步数据：
        - resource_type_id: 资源类型ID
        - team: 队伍ID
        - level: 当前等级
        - next_generate: 下次生成时间（时间戳）
        - resource_name: 资源名称（中文）
        - period_ms: 当前等级的生成周期（毫秒）

        Args:
            instance: PresetInstance对象
        """
        try:
            # 获取当前等级配置
            current_config = self._get_current_level_config()
            period_ms = current_config.get('period', 5000) if current_config else 5000

            # 获取资源名称
            resource_name = self.resource_type.get('name', '资源') if self.resource_type else '资源'

            # 构建同步数据
            sync_data = {
                'resource_type_id': self.resource_type_id,
                'team': self.team,
                'level': self.level,
                'next_generate': self.next_generate,
                'resource_name': resource_name,
                'period_ms': period_ms,
                'display_floating': self.display_floating  # 添加浮空文字显示配置
            }

            # 发送到客户端
            instance.send_to_client("SyncGeneratorData", sync_data)

            # print("[INFO] [产矿机-服务端] 同步数据到客户端: type={}, level={}, period={}ms, display_floating={}".format(
            #     self.resource_type_id, self.level, period_ms, self.display_floating
            # ))

        except Exception as e:
            print("[ERROR] [产矿机-服务端] 同步数据到客户端失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _play_spawn_sound(self, instance):
        """
        播放资源生成音效（参考guide产矿机实现）

        使用playsound命令播放random.pop2音效
        """
        try:
            import mod.server.extraServerApi as serverApi

            pos = instance.get_config("pos")

            # 随机音调（1.1 ~ 1.5）
            pitch = random.uniform(1.1, 1.5)

            # 执行命令播放音效
            command = "playsound {sound} @a {pos} {volume} {pitch}".format(
                sound="random.pop2",
                pos="{} {} {}".format(pos[0], pos[1], pos[2]),
                volume=0.5,
                pitch=pitch
            )

            # 使用命令组件执行命令
            comp_command = serverApi.GetEngineCompFactory().CreateCommand(serverApi.GetLevelId())
            comp_command.SetCommand(command)

        except Exception as e:
            print("[ERROR] [产矿机] 播放音效失败: {}".format(e))

    def _send_particle_effect_to_client(self, instance):
        """
        发送粒子特效消息到客户端（参考guide产矿机实现）

        使用send_to_client发送消息，客户端通过on_server_message接收
        """
        try:
            pos = instance.get_config("pos")

            # 发送消息到客户端
            instance.send_to_client(
                "generator_particle_effect",
                {
                    "pos": pos,
                    "resource_type": self.resource_type_id
                }
            )

        except Exception as e:
            print("[ERROR] [产矿机] 发送粒子特效消息失败: {}".format(e))