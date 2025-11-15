# -*- coding: utf-8 -*-
"""
练习区域预设 - 服务端

功能:
- 定义练习区域范围
- 管理进入/离开练习区域的玩家
- 提供羊毛和游戏模式切换
- 限制方块放置范围
- 处理玩家坠落

原文件: Parts/BedWarsPractice/BedWarsPracticePart.py
重构为: presets/server/PracticePresetDefServer.py
"""

from ECPresetServerScripts import PresetDefinitionServer
from ECPresetServerScripts import get_preset_system


class PracticePresetDefServer(PresetDefinitionServer):
    """
    练习区域预设服务端实现

    核心功能:
    1. 定义练习区域范围和可放置范围
    2. 检测玩家进入/离开练习区域
    3. 自动给予/移除白色羊毛
    4. 自动切换游戏模式(生存/冒险)
    5. 清理玩家放置的方块
    6. 处理玩家坠落虚空
    """

    # ========== ECPreset框架配置 ==========
    enable_tick = True  # 启用tick更新以检测玩家进出

    def __init__(self):
        super(PracticePresetDefServer, self).__init__()

        # 配置数据
        self.practice_range_min = None  # type: tuple | None  # 练习范围最小坐标 (x, y, z)
        self.practice_range_max = None  # type: tuple | None  # 练习范围最大坐标 (x, y, z)
        self.placeable_range_min = None  # type: tuple | None  # 可放置范围最小坐标 (x, y, z)
        self.placeable_range_max = None  # type: tuple | None  # 可放置范围最大坐标 (x, y, z)
        self.spawn_pos = None  # type: tuple | None  # 练习区出生点 (x, y, z)
        self.spawn_yaw = 0  # type: float  # 出生点朝向
        self.exit_spawn = None  # type: tuple | None  # 离开时的传送点 (x, y, z)
        self.exit_spawn_yaw = 0  # type: float  # 离开时的朝向
        self.dimension_id = 0  # type: int  # 维度ID\
        self.instance = None

        # 运行时状态
        self.in_range_players = []  # type: list  # 在练习范围内的玩家列表
        self.placed_blocks = {}  # type: dict  # 玩家放置的方块 {player_id: [pos, ...]}
        self.failed_blocks = []  # type: list  # 清理失败的方块位置
        self.tick_count = 0  # type: int  # tick计数器
        self.tick_interval = 30  # type: int  # 检测间隔(30 ticks = 1.5秒)

    def on_init(self, instance):
        """
        预设初始化

        解析配置数据:
        - practice_range: 练习范围 [[min_x, min_y, min_z], [max_x, max_y, max_z]]
        - placeable_range: 可放置范围 [[min_x, min_y, min_z], [max_x, max_y, max_z]]
        - spawn_pos: 出生点位置 [x, y, z]
        - spawn_yaw: 出生点朝向 (可选,默认0)
        - dimension_id: 维度ID (可选,默认0)

        Args:
            instance: PresetInstance对象
        """
        # 解析练习范围 - 使用get_config而不是instance.data
        practice_range = instance.get_config("practice_range")
        if not practice_range or len(practice_range) != 2:
            print("[ERROR] PracticePresetDefServer.on_init 缺少practice_range配置")
            return

        self.practice_range_min = tuple(practice_range[0])
        self.practice_range_max = tuple(practice_range[1])

        # 解析可放置范围
        placeable_range = instance.get_config("placeable_range")
        if not placeable_range or len(placeable_range) != 2:
            print("[ERROR] PracticePresetDefServer.on_init 缺少placeable_range配置")
            return

        self.placeable_range_min = tuple(placeable_range[0])
        self.placeable_range_max = tuple(placeable_range[1])

        # 解析出生点
        spawn_pos = instance.get_config("spawn_pos")
        if not spawn_pos or len(spawn_pos) != 3:
            print("[ERROR] PracticePresetDefServer.on_init 缺少spawn_pos配置")
            return

        self.spawn_pos = tuple(spawn_pos)
        self.spawn_yaw = instance.get_config("spawn_yaw", 0)
        self.dimension_id = instance.get_config("dimension_id", 0)

        # 解析离开时的传送点（可选，如果不配置则不传送）
        exit_spawn = instance.get_config("exit_spawn")
        if exit_spawn and len(exit_spawn) == 3:
            self.exit_spawn = tuple(exit_spawn)
            self.exit_spawn_yaw = instance.get_config("exit_spawn_yaw", 0)
        else:
            self.exit_spawn = None  # 如果未配置，离开时不传送

        print("[INFO] [练习区域] 初始化:")
        print("[INFO]   - 练习范围: {} -> {}".format(
            self.practice_range_min, self.practice_range_max
        ))
        print("[INFO]   - 可放置范围: {} -> {}".format(
            self.placeable_range_min, self.placeable_range_max
        ))
        print("[INFO]   - 出生点: {}, yaw={}".format(self.spawn_pos, self.spawn_yaw))
        if self.exit_spawn:
            print("[INFO]   - 离开传送点: {}, yaw={}".format(self.exit_spawn, self.exit_spawn_yaw))

    def on_start(self, instance):
        """
        预设启动

        执行步骤:
        1. 注册事件监听
        2. 设置区域常加载

        Args:
            instance: PresetInstance对象
        """
        print("[INFO] [练习区域] 启动")

        # 保存instance引用以便事件回调使用
        self.instance = instance

        # 1. 注册事件监听
        import mod.server.extraServerApi as serverApi

        # 获取ECPreset管理器注册的服务端system
        # ECPreset框架会自动提供server_system引用
        server_system = get_preset_system()

        if server_system:
            # 监听方块放置事件
            server_system.ListenForEvent(
                serverApi.GetEngineNamespace(),
                serverApi.GetEngineSystemName(),
                "ServerEntityTryPlaceBlockEvent",
                self,
                self._on_entity_try_place_block
            )

            # 监听玩家进入虚空事件（高度 < 0）
            # 注意: 网易引擎没有专门的坠落事件，需要在on_tick中检测Y坐标
            print("[INFO] [练习区域] 事件监听已注册")
        else:
            print("[WARN] [练习区域] 无法获取server_system，将使用备用检测方式")

        # 2. 设置区域常加载
        try:
            comp = serverApi.GetEngineCompFactory().CreateChunkSource(serverApi.GetLevelId())
            comp.SetAddArea(
                'practice_range_{}'.format(instance.instance_id),
                self.dimension_id,
                self.practice_range_min,
                self.practice_range_max
            )
            print("[INFO] [练习区域] 区块常加载已设置")
        except Exception as e:
            print("[ERROR] [练习区域] 设置区块常加载失败: {}".format(e))

    def on_tick(self, instance, dt):
        """
        每帧更新

        执行任务:
        1. 定期检查玩家是否进入/离开练习区域（每30 ticks）
        2. 检测练习区域内玩家是否坠落（每帧）
        3. 重试清理失败的方块

        Args:
            instance: PresetInstance对象
            dt: 自上一帧以来的时间增量（秒）
        """
        self.tick_count += 1

        # 定期检查玩家进出
        if self.tick_count >= self.tick_interval:
            self.tick_count = 0
            self._check_players_in_practice(instance)

        # 每帧检测坠落（练习区域内的玩家）
        self._check_players_fall(instance)

        # 重试清理失败的方块
        self._retry_clear_failed_blocks(instance)

    def on_stop(self, instance):
        """
        预设停止

        清理所有玩家状态和放置的方块

        Args:
            instance: PresetInstance对象
        """
        print("[INFO] [练习区域] 停止")

        # 移除所有在区域内的玩家
        for player_id in list(self.in_range_players):
            self._remove_player_from_practice(player_id, instance)

        # 清理所有放置的方块
        self._clear_all_placed_blocks(instance)

        # 取消事件监听
        import mod.server.extraServerApi as serverApi
        server_system = get_preset_system()

        if server_system:
            try:
                server_system.UnListenForEvent(
                    serverApi.GetEngineNamespace(),
                    serverApi.GetEngineSystemName(),
                    "ServerEntityTryPlaceBlockEvent",
                    self,
                    self._on_entity_try_place_block
                )
                print("[INFO] [练习区域] 事件监听已取消")
            except Exception as e:
                print("[WARN] [练习区域] 取消事件监听失败: {}".format(e))

        # 移除区域常加载
        try:
            comp = serverApi.GetEngineCompFactory().CreateChunkSource(serverApi.GetLevelId())
            # 修复：正确的方法名是DeleteArea（不是RemoveArea）
            comp.DeleteArea('practice_range_{}'.format(instance.instance_id))
            print("[INFO] [练习区域] 区块常加载已移除")
        except Exception as e:
            print("[ERROR] [练习区域] 移除区块常加载失败: {}".format(e))

    def on_destroy(self, instance):
        """
        预设销毁

        Args:
            instance: PresetInstance对象
        """
        print("[INFO] [练习区域] 销毁")

    # ========== 玩家进入/离开检测 ==========

    def _check_players_in_practice(self, instance):
        """
        检查玩家是否在练习范围内

        Args:
            instance: PresetInstance对象
        """
        import mod.server.extraServerApi as serverApi

        # 获取练习范围内的所有实体
        comp = serverApi.GetEngineCompFactory().CreateGame(serverApi.GetLevelId())
        entities = comp.GetEntitiesInSquareArea(
            None,
            self.practice_range_min,
            self.practice_range_max,
            self.dimension_id
        )

        # 过滤出玩家
        players_in_range = []
        for entity in entities:
            comp_type = serverApi.GetEngineCompFactory().CreateEngineType(entity)
            engine_type = comp_type.GetEngineTypeStr()
            if engine_type == "minecraft:player":
                players_in_range.append(entity)

        # 检查新进入的玩家
        for player_id in players_in_range:
            if player_id not in self.in_range_players:
                self._add_player_to_practice(player_id, instance)

        # 检查离开的玩家
        for player_id in list(self.in_range_players):
            if player_id not in players_in_range:
                self._remove_player_from_practice(player_id, instance)

    def _add_player_to_practice(self, player_id, instance):
        """
        玩家进入练习区域

        Args:
            player_id: 玩家ID
            instance: PresetInstance对象
        """
        import mod.server.extraServerApi as serverApi

        self.in_range_players.append(player_id)

        # 给予白色羊毛
        comp_item = serverApi.GetEngineCompFactory().CreateItem(player_id)
        comp_item.SpawnItemToPlayerInv({
            "itemName": "minecraft:white_wool",
            "count": 64
        }, player_id)

        # 切换为生存模式
        comp_player = serverApi.GetEngineCompFactory().CreatePlayer(player_id)
        comp_player.SetPlayerGameType(serverApi.GetMinecraftEnum().GameType.Survival)

        print("[INFO] [练习区域] 玩家进入: {}".format(player_id))

    def _remove_player_from_practice(self, player_id, instance):
        """
        玩家离开练习区域

        执行步骤:
        1. 移除白色羊毛
        2. 清除玩家放置的方块
        3. 切换为冒险模式
        4. 传送回离开点（如果配置了exit_spawn）

        Args:
            player_id: 玩家ID
            instance: PresetInstance对象
        """
        import mod.server.extraServerApi as serverApi

        if player_id in self.in_range_players:
            self.in_range_players.remove(player_id)

        # 1. 移除白色羊毛
        comp_item = serverApi.GetEngineCompFactory().CreateItem(player_id)
        removed_count = 0

        for i in range(0, 36):
            item = comp_item.GetPlayerItem(serverApi.GetMinecraftEnum().ItemPosType.INVENTORY, i)

            if item:
                item_name = item.get('newItemName', item.get('itemName', 'unknown'))

                # 检查是否是白色羊毛
                if item_name == 'minecraft:white_wool':
                    # 使用SetInvItemNum设置数量为0来清除物品（MODSDK推荐方法）
                    success = comp_item.SetInvItemNum(i, 0)
                    if success:
                        removed_count += 1

        if removed_count > 0:
            print("[INFO] [练习区域] 已清除 {} 个羊毛槽位".format(removed_count))

        # 2. 清除该玩家放置的方块
        self._clear_player_blocks(player_id, instance)

        # 3. 切换为冒险模式
        comp_player = serverApi.GetEngineCompFactory().CreatePlayer(player_id)
        comp_player.SetPlayerGameType(serverApi.GetMinecraftEnum().GameType.Adventure)

        # 4. 传送回离开点（如果配置了）
        if self.exit_spawn:
            try:
                comp_pos = serverApi.GetEngineCompFactory().CreatePos(player_id)
                comp_pos.SetFootPos(self.exit_spawn)

                # 设置朝向
                comp_rot = serverApi.GetEngineCompFactory().CreateRot(player_id)
                comp_rot.SetRot((0, self.exit_spawn_yaw))

                print("[INFO] [练习区域] 玩家离开并传送: {} -> {}".format(player_id, self.exit_spawn))
            except Exception as e:
                print("[ERROR] [练习区域] 传送玩家失败: player={}, error={}".format(player_id, e))
        else:
            print("[INFO] [练习区域] 玩家离开: {}".format(player_id))

    # ========== 方块放置限制 ==========

    def _on_entity_try_place_block(self, args):
        """
        处理实体尝试放置方块事件

        Args:
            args: 事件参数
                - entityId: 实体ID
                - x, y, z: 方块坐标
                - dimensionId: 维度ID
        """
        player_id = args.get('entityId')
        pos = (args.get('x'), args.get('y'), args.get('z'))
        dimension_id = args.get('dimensionId')

        # 只处理在练习区域内的玩家
        if dimension_id != self.dimension_id or player_id not in self.in_range_players:
            return

        # 检查是否在可放置范围内
        if not self._is_pos_in_range(pos, self.placeable_range_min, self.placeable_range_max):
            args['cancel'] = True
            return

        # 记录放置的方块
        if player_id not in self.placed_blocks:
            self.placed_blocks[player_id] = []
        self.placed_blocks[player_id].append(pos)

    def _check_players_fall(self, instance):
        """
        检测练习区域内玩家是否坠落

        检测条件:
        - 玩家在练习区域内(in_range_players)
        - Y坐标 < 0 (坠入虚空)

        Args:
            instance: PresetInstance对象
        """
        import mod.server.extraServerApi as serverApi

        for player_id in list(self.in_range_players):
            try:
                # 获取玩家位置
                comp_pos = serverApi.GetEngineCompFactory().CreatePos(player_id)
                pos = comp_pos.GetFootPos()

                if pos is None:
                    continue

                # 检测是否坠入虚空（Y < 0）
                if pos[1] < 0:
                    # 检查是否在练习区域的XZ范围内
                    if (self.placeable_range_min[0] <= pos[0] <= self.placeable_range_max[0] and
                            self.placeable_range_min[2] <= pos[2] <= self.placeable_range_max[2]):
                        # 传送回出生点
                        comp_pos.SetFootPos(self.spawn_pos)
                        # 设置朝向
                        comp_rot = serverApi.GetEngineCompFactory().CreateRot(player_id)
                        comp_rot.SetRot((0, self.spawn_yaw))

                        print("[INFO] [练习区域] 玩家坠落传送: {}".format(player_id))
            except Exception as e:
                print("[ERROR] [练习区域] 检测坠落失败: player={}, error={}".format(player_id, e))

    def _retry_clear_failed_blocks(self, instance):
        """
        重试清理失败的方块

        Args:
            instance: PresetInstance对象
        """
        if not self.failed_blocks:
            return

        import mod.server.extraServerApi as serverApi
        comp_block = serverApi.GetEngineCompFactory().CreateBlockInfo(serverApi.GetLevelId())

        # 尝试清理失败队列中的方块
        for block_pos in list(self.failed_blocks):
            try:
                res = comp_block.SetBlockNew(block_pos, {'name': 'minecraft:air'}, self.dimension_id, 0, True)
                if res:
                    self.failed_blocks.remove(block_pos)
            except:
                pass

    # ========== 方块清理 ==========

    def _clear_player_blocks(self, player_id, instance):
        """
        清除玩家放置的所有方块

        Args:
            player_id: 玩家ID
            instance: PresetInstance对象
        """
        import mod.server.extraServerApi as serverApi

        block_list = self.placed_blocks.get(player_id, [])
        if not block_list:
            return

        comp_block = serverApi.GetEngineCompFactory().CreateBlockInfo(serverApi.GetLevelId())

        cleared_count = 0
        for block_pos in block_list:
            res = comp_block.SetBlockNew(block_pos, {'name': 'minecraft:air'}, self.dimension_id, 0, True)
            if res:
                cleared_count += 1
            else:
                # 清理失败,加入失败队列
                self.failed_blocks.append(block_pos)

        # 清空该玩家的方块记录
        self.placed_blocks[player_id] = []

        print("[INFO] [练习区域] 清除玩家方块: player={}, 成功={}, 失败={}".format(
            player_id, cleared_count, len(block_list) - cleared_count
        ))

    def _clear_all_placed_blocks(self, instance):
        """
        清除所有放置的方块

        Args:
            instance: PresetInstance对象
        """
        for player_id in list(self.placed_blocks.keys()):
            self._clear_player_blocks(player_id, instance)

    # ========== 工具方法 ==========

    def _is_pos_in_range(self, pos, range_min, range_max):
        """
        判断位置是否在指定范围内

        Args:
            pos: 位置 (x, y, z)
            range_min: 范围最小坐标 (x, y, z)
            range_max: 范围最大坐标 (x, y, z)

        Returns:
            bool: 是否在范围内
        """
        return (range_min[0] <= pos[0] <= range_max[0] and
                range_min[1] <= pos[1] <= range_max[1] and
                range_min[2] <= pos[2] <= range_max[2])
