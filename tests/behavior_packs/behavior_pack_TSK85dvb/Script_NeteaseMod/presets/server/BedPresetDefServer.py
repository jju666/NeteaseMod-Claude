# -*- coding: utf-8 -*-
"""
床预设 - 服务端

功能:
- 管理床的破坏检测
- 处理队伍床状态
- 发送床破坏事件
- 管理陷阱系统 (trap)
"""

from Script_NeteaseMod.presets.server.BlockPresetServerBase import BlockPresetServerBase


class BedPresetDefServer(BlockPresetServerBase):
    """
    床预设服务端实现

    核心功能:
    1. 床方块检测和管理
    2. 床破坏权限验证 (只能破坏敌方的床)
    3. 床破坏事件广播
    4. 队伍陷阱系统管理
    5. 床颜色初始化
    """

    def __init__(self):
        super(BedPresetDefServer, self).__init__()

        # 配置数据
        self.team = None  # type: str | None  # 队伍ID (RED, BLUE, GREEN等)

        # 运行时状态
        self.bed_blocks = []  # type: list  # 床的方块坐标列表 [(x,y,z), ...]
        self.bed_destroyed = False  # type: bool  # 床是否已被破坏
        self.player_to_team = {}  # type: dict  # 玩家ID -> 队伍ID 映射
        self.ornament_entity_id = None  # type: str | None  # 装饰物实体ID

        # 陷阱管理器
        self.trap_manager = None  # type: object | None  # TeamTrapManager实例

    def on_init(self, instance):
        """
        预设初始化

        解析配置数据:
        - team: 队伍ID
        - pos: 床的位置
        - rotation: 床的朝向

        Args:
            instance: PresetInstance对象
        """
        self.team = instance.get_config("team")
        if not self.team:
            print("[ERROR] BedPresetDefServer.on_init 缺少team配置")
            return

        print("[INFO] [床预设] 初始化: team={}".format(self.team))

        # 保存配置到instance，同步到客户端
        instance.set_data("team", self.team)
        instance.set_data("bed_destroyed", False)

        # 同步位置信息到客户端（用于浮动文字显示）
        pos = instance.get_config("pos")
        if pos:
            instance.set_data("pos", pos)
            print("[INFO] [床预设] 已同步位置到客户端: pos={}".format(pos))
        else:
            print("[WARN] [床预设] 配置中缺少pos，浮动文字将无法显示")

        # 注意: 不在on_init()中放置床方块
        # 原因: on_init()阶段区块可能还没加载，导致SetBlockNew()失败
        # 改为在on_start()中使用异步区块加载机制放置床方块

        # 修复P1.3: 监听玩家客户端加载完毕事件
        # 用于在玩家加载完成后发送浮空文字消息（仅对队伍成员）
        import mod.server.extraServerApi as serverApi
        from ECPresetServerScripts import get_preset_system
        get_preset_system().ListenForEvent(
            serverApi.GetEngineNamespace(),
            serverApi.GetEngineSystemName(),
            'ClientLoadAddonsFinishServerEvent',
            self,
            self._on_client_load_finish
        )
        print("[床预设-服务端] 已注册ClientLoadAddonsFinishServerEvent事件监听")

        # 初始化床就绪标记
        self.bed_ready = False  # 床方块是否已放置完成
        self.instance = None    # PresetInstance引用

        # 记录已发送过浮空文字消息的玩家ID集合，防止重复发送
        # 注意：这个集合在每次游戏开始时会被清空（在_on_bedwars_running中）
        # 用途：防止同一玩家在同一局游戏中收到多次浮动文字消息
        self.sent_floating_text_players = set()

        # 订阅游戏开始事件 - 用于向已在线的同队玩家发送浮空文字消息
        # 事件流程：
        #   1. BedWarsRunningState 进入时广播 "BedWarsRunning" 事件
        #   2. GamingStateSystem.broadcast_preset_event() 发布到 EventBus
        #   3. EventBus 通知所有订阅者（包括这个床预设）
        #   4. 调用 self._on_bedwars_running() 处理事件
        #
        # 历史问题 (已修复 2025-11-04):
        #   修复前：GamingStateSystem 遍历26个预设，每个都发布事件，导致此回调被触发26次
        #   修复后：GamingStateSystem 直接向 EventBus 发布1次，此回调只触发1次
        instance.subscribe_event("BedWarsRunning", self._on_bedwars_running)
        print("[床预设-服务端] 已注册BedWarsRunning事件监听")

    def on_start(self, instance):
        """
        预设启动

        执行步骤:
        1. 异步放置床方块（使用区块加载机制）
        2. 获取床方块坐标
        3. 初始化床颜色
        4. 注册事件监听
        5. 上报床数据到游戏系统

        Args:
            instance: PresetInstance对象
        """
        print("[INFO] [床预设] 启动: team={}".format(self.team))

        # 保存instance引用
        self.instance = instance

        # 1. 异步放置床方块（新项目核心功能）
        # 使用异步区块加载机制，确保区块已加载后再放置床方块
        self._place_bed_blocks_async(instance)

        # 注意: 向客户端发送启动消息会在床方块放置完成后执行
        # 这样可以确保发送消息时床的位置已经确定
        # 参见 _on_bed_blocks_placed() 方法

    def on_tick(self, instance):
        """
        每Tick更新

        更新陷阱管理器

        Args:
            instance: PresetInstance对象
        """
        # 陷阱管理器更新
        if self.trap_manager:
            try:
                self.trap_manager.on_update()
            except Exception as e:
                print("[ERROR] [床预设] 陷阱管理器更新失败: {}".format(str(e)))

    def on_stop(self, instance):
        """
        预设停止

        清理工作:
        1. 取消事件监听
        2. 移除装饰物
        3. 重置床状态
        4. 清理陷阱管理器
        5. 重新放置床方块(如果被破坏了) - 为下一局游戏做准备

        注意: 床方块的完整还原由RoomManagementSystem的维度备份还原机制处理
              这里只负责确保床预设状态重置

        Args:
            instance: PresetInstance对象
        """
        print("[INFO] [床预设] 停止: team={}".format(self.team))

        # 如果床被破坏了，重新放置床方块（使用异步机制）
        # 这确保了即使维度还原失败，床也能在下一局正常工作
        if self.bed_destroyed:
            print("[INFO] [床预设] 床已被破坏，异步重新放置床方块")
            # 使用异步机制重新放置床方块
            # 注意: 这里不等待完成，因为on_stop()可能在游戏结束时调用
            #       维度还原会处理大部分情况，这里只是备用机制
            self._place_bed_blocks_async(instance)

        # 重置床状态
        self.bed_destroyed = False

        # 移除装饰物
        if self.ornament_entity_id:
            try:
                import mod.server.extraServerApi as serverApi
                levelId = serverApi.GetLevelId()
                entity_comp = serverApi.GetEngineCompFactory().CreateEntity(levelId)
                entity_comp.DestroyEntity(self.ornament_entity_id)
                print("[INFO] [床预设] 装饰物实体已移除: {}".format(self.ornament_entity_id))
            except Exception as e:
                print("[ERROR] [床预设] 移除装饰物失败: {}".format(str(e)))
            self.ornament_entity_id = None

        # 清理陷阱管理器
        if self.trap_manager:
            self.trap_manager.clear_all_traps()
            self.trap_manager = None

        # 取消事件监听
        # EventBus事件会自动取消订阅

    def on_destroy(self, instance):
        """
        预设销毁

        最终清理工作

        Args:
            instance: PresetInstance对象
        """
        print("[INFO] [床预设] 销毁: team={}".format(self.team))

        # 清理数据
        self.bed_blocks = []
        self.player_to_team = {}

        # 修复P1.3: 清理床就绪标记
        self.bed_ready = False
        self.instance = None

        # 注意: 事件监听器会由引擎自动清理，不需要手动UnListenForEvent

    # ========== 事件处理方法 ==========

    def _on_player_try_destroy_block(self, event_data):
        """
        处理玩家尝试破坏方块事件

        逻辑:
        1. 检查是否是床方块
        2. 检查玩家是否有权限破坏 (不能破坏自己队伍的床)
        3. 如果可以破坏,触发床破坏逻辑

        Args:
            event_data: 事件数据
                - playerId: 玩家ID
                - x, y, z: 方块坐标
                - cancel: 是否取消破坏
        """
        pos = (event_data.get('x'), event_data.get('y'), event_data.get('z'))

        # 检查是否是床方块
        if pos not in self.bed_blocks:
            return

        player_id = event_data.get('playerId')
        print("[BedWars] 玩家尝试破坏床 - 玩家: {}, 床队伍: {}".format(player_id, self.team))

        # 直接从游戏系统获取玩家队伍
        player_team = self._get_player_team_from_game_system(player_id)

        if player_team is None:
            print("[BedWars] 玩家不在任何队伍中,禁止破坏")
            event_data['cancel'] = True
            return

        print("[BedWars] 玩家队伍: {}, 床队伍: {}".format(player_team, self.team))

        # 不能破坏自己队伍的床
        if player_team == self.team:
            print("[BedWars] 玩家尝试破坏自己队伍的床,禁止破坏")
            event_data['cancel'] = True

            # 显示提示消息（参考老项目BedWarsBedPart.py）
            try:
                import mod.server.extraServerApi as serverApi
                from Script_NeteaseMod.modConfig import MOD_NAME
                from Script_NeteaseMod.systems.util.BetterPlayerObject import BetterPlayerObject

                # 获取游戏系统（BetterPlayerObject需要system参数）
                game_system = serverApi.GetSystem(MOD_NAME, "BedWarsGameSystem")
                if game_system:
                    player_obj = BetterPlayerObject(game_system, player_id)
                    player_obj.send_message(
                        u"\u00a7e\u00bb \u00a7y\u8bf7\u52a1\u5fc5\u4fdd\u62a4\u597d\u5df1\u65b9\u7684\u5e8a\uff0c \u4e00\u65e6\u5e8a\u88ab\u6467\u6bc1\uff0c \u4f60\u5c06\u4e0d\u80fd\u518d\u590d\u6d3b\u3002")
                else:
                    print("[ERROR] [床预设] 无法获取BedWarsGameSystem，无法发送提示消息")
            except Exception as e:
                print("[ERROR] [床预设] 发送破坏提示消息失败: {}".format(str(e)))
                import traceback
                traceback.print_exc()
        else:
            # 可以破坏敌方床
            print("[BedWars] 玩家可以破坏敌方床,执行床破坏逻辑")

            # 拦截床掉落物生成
            # 原因: 床破坏后不应该生成床物品掉落物(开发规范.md - 游戏平衡性)
            # API参考: ServerPlayerTryDestroyBlockEvent的spawnResources参数
            event_data['spawnResources'] = False
            self._destroy_bed(player_id)

    def _on_bedwars_running(self, event_name, event_data):
        """
        处理游戏开始事件（BedWarsRunning）

        触发时机：
            当游戏状态从 BedWarsStartingState 进入 BedWarsRunningState 时触发。
            事件由 GamingStateSystem.broadcast_preset_event() 通过 EventBus 广播，
            所有订阅了 "BedWarsRunning" 的预设都会收到此事件。

        功能:
            1. 重置床状态（bed_destroyed = False）
            2. 重新查询床方块位置（维度备份还原后）
            3. 重新染色床方块（确保队伍颜色正确）
            4. 创建床装饰物（调用 OrnamentSystem）
            5. 清空浮动文字发送记录，允许新一轮游戏重新发送
            6. 向已在线的同队玩家发送浮空文字消息

        Args:
            event_name (str): 事件名称，固定为 "BedWarsRunning"
            event_data (dict): 事件数据（当前为空字典）

        注意事项:
            - 此方法每局游戏只应该被调用1次
            - 如果被多次调用，会创建重复的浮动文字面板（已修复）
            - 浮动文字消息的去重依赖 sent_floating_text_players 集合

        历史Bug修复 (2025-11-04):
            问题：此方法被调用26次（每个预设实例发布事件导致）
            症状：创建26个重复的浮动文字面板在同一位置
            根因：GamingStateSystem.broadcast_preset_event() 遍历预设发布事件
            修复：改为直接向 EventBus 发布1次，此方法现在只被调用1次

        对局循环修复 (2025-11-22 v2):
            问题：对局循环模式下，床被破坏后第二局不会重置
            根因分析：
                1. RoomManagementSystem.end_game()调用_destroy_all_presets()销毁预设实例
                2. RoomManagementSystem.end_game()调用backup_handler.restore()异步还原维度
                3. 下一局start_game()创建全新预设，on_start()异步放置床方块
                4. 原有逻辑在此方法中再次异步放置床方块（第347-369行）
                5. 多次异步放置导致回调混乱，且与维度还原存在竞态条件
            修复方案：
                移除冗余的床方块放置逻辑，依赖维度备份还原机制
                只重新查询床方块位置、染色、创建装饰物
                避免异步回调混乱和竞态条件
        """
        print("[INFO] [床预设] 游戏开始事件: team={}".format(self.team))

        try:
            # [FIX 2025-11-22 v3] 对局循环模式修复
            # 根因：维度还原机制只会清空方块为空气（DimensionBackup.set_block:214行）
            #       不会恢复床方块到初始状态，v2的假设错误
            # 修复：游戏开始时验证床方块存在，不存在则重新异步放置
            if self.instance:
                print("[INFO] [床预设] 游戏开始，验证床方块状态（对局循环修复v3）")

                # 1. 重新查询床方块位置
                self.bed_blocks = self._get_bed_blocks(self.instance)
                print("[INFO] [床预设] 查询到床方块数量: {}".format(len(self.bed_blocks)))

                # 2. 验证床方块是否真实存在（而不只是坐标记录）
                has_real_bed = False
                try:
                    import mod.server.extraServerApi as serverApi
                    levelId = serverApi.GetLevelId()
                    block_comp = serverApi.GetEngineCompFactory().CreateBlockInfo(levelId)
                    dimension_id = self._get_dimension_id(self.instance)

                    # 只检查第一个位置即可（性能优化）
                    if self.bed_blocks:
                        block_dict = block_comp.GetBlockNew(self.bed_blocks[0], dimension_id)
                        has_real_bed = block_dict and block_dict.get('name') == 'minecraft:bed'
                        print("[INFO] [床预设] 床方块存在性验证: {}".format(has_real_bed))
                except Exception as e:
                    print("[ERROR] [床预设] 验证床方块失败: {}".format(str(e)))

                # 3. 如果床方块不存在，重新异步放置
                if not has_real_bed:
                    print("[WARN] [床预设] 床方块不存在（可能被维度还原清空），重新异步放置")
                    # 检查是否有正在进行的异步放置（避免重复放置）
                    if not getattr(self, 'bed_placing', False):
                        self._place_bed_blocks_async(self.instance)
                        # _place_bed_blocks_async()会在完成后自动染色和创建装饰
                    else:
                        print("[WARN] [床预设] 已有异步放置任务进行中，跳过")
                else:
                    # 4. 床方块存在，只需重新染色和创建装饰
                    print("[INFO] [床预设] 床方块已存在，重新染色和装饰")
                    self._init_bed_color(self.instance)
                    self._destroy_bed_ornament()
                    self._create_bed_ornament()
                    print("[INFO] [床预设] 床初始化完成（染色+装饰）")
        except Exception as e:
            print("[ERROR] [床预设] 初始化床失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()
            # 继续执行，不影响其他逻辑

        # 重置床状态（新一轮游戏开始，床未被破坏）
        self.bed_destroyed = False

        # 清空已发送浮空文字消息的玩家记录，允许新一轮游戏重新发送
        # 重要：这个清空操作确保玩家在新一轮游戏中能收到浮动文字提示
        self.sent_floating_text_players.clear()

        # 向已在线的同队玩家发送浮空文字消息
        # 解决时机问题:玩家在Lobby阶段已加载完成,但床预设在Running状态才创建
        # 因此需要在游戏开始时主动向所有已在线的同队玩家发送浮空文字消息
        self._send_floating_text_to_online_teammates()

    def _on_bedwars_ending(self, event_data):
        """
        处理游戏结束事件

        Args:
            event_data: 事件数据
        """
        print("[INFO] [床预设] 游戏结束事件: team={}".format(self.team))

        # 重置床状态
        self.bed_destroyed = False

        # 移除装饰物（参考on_stop方法的实现）
        if self.ornament_entity_id:
            try:
                import mod.server.extraServerApi as serverApi
                levelId = serverApi.GetLevelId()
                entity_comp = serverApi.GetEngineCompFactory().CreateEntity(levelId)
                entity_comp.DestroyEntity(self.ornament_entity_id)
                print("[INFO] [床预设] 装饰物实体已移除: {}".format(self.ornament_entity_id))
            except Exception as e:
                print("[ERROR] [床预设] 移除装饰物失败: {}".format(str(e)))
            self.ornament_entity_id = None

    def _on_team_update(self, event_data):
        """
        处理队伍玩家更新事件

        同步最新的玩家-队伍映射关系

        Args:
            event_data: 事件数据
                - dimension: 维度ID
                - player_to_team: 玩家ID -> 队伍ID映射
        """
        # 只处理本维度的事件
        if event_data.get('dimension') != self.instance.get_config("dimension_id", 0):
            return

        self.player_to_team = event_data.get('player_to_team', {})
        print("[INFO] [床预设] 更新玩家-队伍映射: {}".format(len(self.player_to_team)))

        # P1功能：玩家队伍更新后，重新同步数据到客户端
        self._sync_bed_data_to_client(self.instance)

    # ========== 内部辅助方法 ==========

    def _get_bed_blocks(self, instance):
        """
        获取床的所有方块坐标

        床是由2个方块组成的,需要找到两半

        Args:
            instance: PresetInstance对象

        Returns:
            list: 床方块坐标列表 [(x,y,z), ...]
        """
        pos = instance.get_config("pos")
        dimension_id = instance.get_config("dimension_id", 0)
        blocks = []

        # 将pos转换为坐标
        if isinstance(pos, dict):
            center_pos = (int(pos['x']), int(pos['y']), int(pos['z']))
        else:
            center_pos = (int(pos[0]), int(pos[1]), int(pos[2]))

        try:
            import mod.server.extraServerApi as serverApi

            # 创建方块信息组件
            levelId = serverApi.GetLevelId()
            block_comp = serverApi.GetEngineCompFactory().CreateBlockInfo(levelId)

            # 遍历周围±1格的方块,找到床的两半
            for x in range(-1, 2):
                for z in range(-1, 2):
                    check_pos = (center_pos[0] + x, center_pos[1], center_pos[2] + z)

                    # 获取方块信息
                    block_dict = block_comp.GetBlockNew(check_pos, dimension_id)

                    if block_dict and block_dict.get('name') == 'minecraft:bed':
                        if check_pos not in blocks:
                            blocks.append(check_pos)
                            print("[INFO] [床预设] 找到床方块: pos={}".format(check_pos))

            if len(blocks) == 0:
                # 如果没有找到床方块,使用预设位置作为后备
                print("[WARN] [床预设] 未找到床方块,使用预设位置: pos={}".format(center_pos))
                blocks.append(center_pos)

        except Exception as e:
            print("[ERROR] [床预设] 获取床方块失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()
            # 失败时使用预设位置作为后备
            blocks.append(center_pos)

        return blocks

    def _query_and_color_bed_blocks(self, center_pos, dimension_id, instance):
        """
        在床方块放置成功后，立即查询周围的床方块并设置颜色

        这个方法在床头放置回调中调用，确保在床方块刚放置完成时立即染色

        Args:
            center_pos (tuple): 查询中心位置（床尾位置）
            dimension_id (int): 维度ID
            instance: PresetInstance对象
        """
        print("[INFO] [床预设] 开始查询并染色床方块: center={}, dimension={}".format(center_pos, dimension_id))

        try:
            import mod.server.extraServerApi as serverApi

            # 创建方块信息组件
            levelId = serverApi.GetLevelId()
            block_comp = serverApi.GetEngineCompFactory().CreateBlockInfo(levelId)

            # 在中心位置周围±1格查询床方块
            bed_blocks_found = []
            for x in range(-1, 2):
                for z in range(-1, 2):
                    check_pos = (center_pos[0] + x, center_pos[1], center_pos[2] + z)

                    # 获取方块信息
                    block_dict = block_comp.GetBlockNew(check_pos, dimension_id)

                    if block_dict and block_dict.get('name') == 'minecraft:bed':
                        bed_blocks_found.append(check_pos)
                        print("[INFO] [床预设] 找到床方块: pos={}".format(check_pos))

            if not bed_blocks_found:
                print("[WARN] [床预设] 未找到任何床方块，染色失败")
                return

            # 更新实例的床方块列表
            self.bed_blocks = bed_blocks_found
            print("[INFO] [床预设] 查询到床方块数量: {}".format(len(bed_blocks_found)))

            # 获取队伍颜色
            ItemColor = serverApi.GetMinecraftEnum().ItemColor
            color_map = {
                'RED': ItemColor.Red,
                'YELLOW': ItemColor.Yellow,
                'GREEN': ItemColor.Green,
                'BLUE': ItemColor.Blue,
                'AQUA': ItemColor.Cyan,
                'WHITE': ItemColor.White,
                'LIGHT_PURPLE': ItemColor.Magenta,
                'GRAY': ItemColor.Gray,
            }
            color = color_map.get(self.team, ItemColor.Black)

            # 对每个床方块设置颜色
            success_count = 0
            for pos in bed_blocks_found:
                try:
                    block_comp.SetBedColor(pos, color, dimension_id)
                    success_count += 1
                    print("[INFO] [床预设] 设置床颜色成功: pos={}, color={}".format(pos, self.team))
                except Exception as e:
                    print("[ERROR] [床预设] 设置床颜色失败: pos={}, error={}".format(pos, str(e)))

            print("[INFO] [床预设] 床方块染色完成: 成功{}/{}".format(success_count, len(bed_blocks_found)))

        except Exception as e:
            print("[ERROR] [床预设] 查询并染色床方块失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _init_bed_color(self, instance):
        """
        初始化床的颜色

        根据队伍ID设置床的颜色

        Args:
            instance: PresetInstance对象
        """
        print("[INFO] [床预设] 初始化床颜色: team={}".format(self.team))

        if not self.bed_blocks:
            print("[WARN] [床预设] 床方块列表为空,无法设置颜色")
            return

        try:
            import mod.server.extraServerApi as serverApi

            # 获取ItemColor枚举
            ItemColor = serverApi.GetMinecraftEnum().ItemColor

            # 映射队伍到颜色
            color_map = {
                'RED': ItemColor.Red,
                'YELLOW': ItemColor.Yellow,
                'GREEN': ItemColor.Green,
                'BLUE': ItemColor.Blue,
                'AQUA': ItemColor.Cyan,
                'WHITE': ItemColor.White,
                'LIGHT_PURPLE': ItemColor.Magenta,
                'GRAY': ItemColor.Gray,
            }

            # 获取对应颜色,默认为黑色
            color = color_map.get(self.team, ItemColor.Black)

            # 创建方块信息组件
            levelId = serverApi.GetLevelId()
            block_comp = serverApi.GetEngineCompFactory().CreateBlockInfo(levelId)

            # 设置每个床方块的颜色
            dimension_id = self._get_dimension_id(instance)
            for pos in self.bed_blocks:
                try:
                    block_comp.SetBedColor(pos, color, dimension_id)
                    print("[INFO] [床预设] 设置床颜色成功: pos={}, color={}".format(pos, self.team))
                except Exception as e:
                    print("[ERROR] [床预设] 设置床颜色失败: pos={}, error={}".format(pos, str(e)))

        except Exception as e:
            print("[ERROR] [床预设] 初始化床颜色失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def destroy_bed(self, instance, attacker_id=None):
        """
        公开的床破坏方法（用于游戏系统调用）

        Args:
            instance: PresetInstance对象
            attacker_id: 攻击者玩家ID（可选，床自毁时为None）
        """
        # 保存instance引用（如果还没有的话）
        if not hasattr(self, 'instance') or not self.instance:
            self.instance = instance

        # 调用内部销毁逻辑
        self._destroy_bed(attacker_id)

    def is_destroyed(self, instance):
        """
        检查床是否已被销毁

        Args:
            instance: PresetInstance对象

        Returns:
            bool: 床是否已被销毁
        """
        return self.bed_destroyed

    def _destroy_bed(self, who):
        """
        执行床破坏逻辑（内部方法）

        步骤:
        1. 标记床已破坏
        2. 销毁床装饰
        3. 广播床破坏事件
        4. 移除床方块

        Args:
            who: 破坏者玩家ID
        """
        print("[INFO] [床预设] 床被破坏: team={}, who={}".format(self.team, who))

        # 标记床已破坏
        self.bed_destroyed = True

        # 销毁床装饰
        self._destroy_bed_ornament()

        # P1功能：同步床破坏状态到客户端
        self._sync_bed_data_to_client(self.instance)

        # 计算床中心位置
        bed_center_pos = self._calculate_bed_center()

        # 播放破坏床特效和消息（如果有破坏者）
        if who:
            self._play_bed_destroy_effects(who, bed_center_pos)

        # 通知游戏系统床被破坏
        # 使用直接调用替代事件总线（因为ECPreset框架的emit_event API不兼容）
        self._notify_game_system_bed_destroyed(who, bed_center_pos)

        # 移除床方块
        try:
            import mod.server.extraServerApi as serverApi

            # 创建方块信息组件
            levelId = serverApi.GetLevelId()
            block_comp = serverApi.GetEngineCompFactory().CreateBlockInfo(levelId)

            # 将所有床方块替换为空气方块
            dimension_id = self.instance.get_config("dimension_id", 0)
            for pos in self.bed_blocks:
                try:
                    # 设置为空气方块
                    block_comp.SetBlockNew(pos, {'name': 'minecraft:air'}, 0, dimension_id)
                    print("[INFO] [床预设] 移除床方块成功: pos={}".format(pos))
                except Exception as e:
                    print("[ERROR] [床预设] 移除床方块失败: pos={}, error={}".format(pos, str(e)))

        except Exception as e:
            print("[ERROR] [床预设] 移除床方块异常: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _notify_game_system_bed_destroyed(self, destroyer_id, bed_pos):
        """
        通知游戏系统床被破坏

        Args:
            destroyer_id (str): 破坏者玩家ID
            bed_pos (tuple): 床位置
        """
        try:
            import mod.server.extraServerApi as serverApi
            from Script_NeteaseMod.modConfig import MOD_NAME

            # 获取BedWarsGameSystem
            game_system = serverApi.GetSystem(MOD_NAME, "BedWarsGameSystem")
            if not game_system:
                print("[WARN] [床预设] 无法获取BedWarsGameSystem，跳过床破坏通知")
                return

            # 调用游戏系统的床破坏处理方法
            game_system.on_bed_destroyed(self.team, destroyer_id, bed_pos)

            print("[INFO] [床预设] 已通知游戏系统床被破坏: team={}, destroyer={}".format(
                self.team, destroyer_id
            ))

        except Exception as e:
            print("[ERROR] [床预设] 通知游戏系统失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _play_bed_destroy_effects(self, attacker_id, bed_pos):
        """
        播放破坏床特效和消息

        Args:
            attacker_id (str): 攻击者玩家ID
            bed_pos (tuple): 床位置
        """
        try:
            import mod.server.extraServerApi as serverApi
            from Script_NeteaseMod.modConfig import MOD_NAME

            # 获取BedWarsGameSystem
            game_system = serverApi.GetSystem(MOD_NAME, "BedWarsGameSystem")
            if not game_system:
                print("[WARN] [床预设] 无法获取BedWarsGameSystem，跳过特效播放")
                return

            # 获取BedDestroyEffectSystem
            bed_destroy_system = getattr(game_system, 'bed_destroy_effect_system', None)
            if not bed_destroy_system:
                print("[WARN] [床预设] 无法获取BedDestroyEffectSystem，跳过特效播放")
                return

            # 获取维度ID
            dimension_id = self.instance.get_config("dimension_id", 0)

            # 播放破坏床特效
            bed_destroy_system.play_bed_destroy_effect(attacker_id, bed_pos, dimension_id)

            # 广播破坏床消息
            bed_destroy_system.broadcast_bed_destroy_message(attacker_id, self.team)

            print("[INFO] [床预设] 播放破坏床特效和消息完成: attacker={}, team={}".format(
                attacker_id, self.team
            ))

        except Exception as e:
            print("[ERROR] [床预设] 播放破坏床特效失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _calculate_bed_center(self):
        """
        计算床的中心位置

        Returns:
            tuple: (x, y, z) 中心坐标
        """
        if not self.bed_blocks:
            return (0, 0, 0)

        if len(self.bed_blocks) == 1:
            return self.bed_blocks[0]

        # 计算平均位置
        x_sum = sum(pos[0] for pos in self.bed_blocks)
        y_sum = sum(pos[1] for pos in self.bed_blocks)
        z_sum = sum(pos[2] for pos in self.bed_blocks)

        return (
            x_sum / len(self.bed_blocks),
            y_sum / len(self.bed_blocks),
            z_sum / len(self.bed_blocks)
        )

    def _notify_bed_data_to_game_system(self, instance):
        """
        上报床数据到游戏系统

        用于游戏系统的自检和管理

        Args:
            instance: PresetInstance对象
        """
        bed_id = "bed_{}_{}".format(instance.get_config("dimension_id", 0), self.team)

        bed_data = {
            "bed_id": bed_id,
            "dimension": instance.get_config("dimension_id", 0),
            "team": self.team,
            "pos": instance.get_config("pos"),
        }

        print("[INFO] [床预设] 上报床数据: {}".format(bed_id))

        # 发送床数据事件到游戏系统
        # 注意：ECPreset框架的emit_event API不兼容，改为通过PresetDefinition属性暴露数据
        # instance.manager.event_bus.emit_event("BedDataReport", bed_data)

        # 游戏系统会通过instance.preset_def直接访问team等属性

    def _init_trap_manager(self, instance):
        """
        初始化陷阱管理器

        从BedWarsGameSystem获取引用并创建TeamTrapManager

        Args:
            instance: PresetInstance对象
        """
        try:
            # 1. 获取BedWarsGameSystem引用
            import mod.server.extraServerApi as serverApi
            from Script_NeteaseMod.modConfig import MOD_NAME

            game_system = serverApi.GetSystem(MOD_NAME, "BedWarsGameSystem")
            if not game_system:
                print("[WARN] [床预设] 无法获取BedWarsGameSystem，陷阱管理器未初始化")
                return

            # 2. 计算床的中心位置
            bed_center_pos = self._calculate_bed_center()

            # 3. 创建TeamTrapManager实例
            from Script_NeteaseMod.systems.team.TeamTrapManager import TeamTrapManager

            self.trap_manager = TeamTrapManager(
                game_system=game_system,
                team=self.team,
                bed_pos=bed_center_pos
            )

            print("[INFO] [床预设] 陷阱管理器初始化完成: team={}, pos={}".format(
                self.team, bed_center_pos))

        except Exception as e:
            print("[ERROR] [床预设] 初始化陷阱管理器失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _sync_bed_data_to_client(self, instance):
        """
        同步床数据到客户端

        P1功能：客户端破坏保护需要知道床方块位置和玩家队伍映射

        Args:
            instance: PresetInstance对象
        """
        try:
            # 构造同步数据
            sync_data = {
                'bed_blocks': self.bed_blocks,
                'player_to_team': self.player_to_team,
                'bed_destroyed': self.bed_destroyed
            }

            # 发送到客户端
            instance.send_to_client("SyncBedData", sync_data)

            print("[INFO] [床预设] 同步床数据到客户端: blocks={}, players={}".format(
                len(self.bed_blocks),
                len(self.player_to_team)
            ))

        except Exception as e:
            print("[ERROR] [床预设] 同步床数据到客户端失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _create_bed_ornament(self):
        """
        创建床装饰

        调用时机: 游戏开始时 (_on_bedwars_running)
        """
        try:
            # 获取BedOrnamentSystem
            bed_ornament_system = self._get_bed_ornament_system()
            if not bed_ornament_system:
                print("[WARN] [床预设] BedOrnamentSystem未初始化")
                return

            # 计算床的中心位置
            bed_center_pos = self._calculate_bed_center()

            # 计算床的朝向
            yaw = self._calculate_bed_yaw()

            # 获取维度ID
            dimension_id = self._get_dimension_id(self.instance)

            # 生成床装饰
            entity_id = bed_ornament_system.spawn_bed_ornament(
                self.team,
                bed_center_pos,
                yaw,
                dimension_id
            )

            if entity_id:
                self.ornament_entity_id = entity_id
                print("[INFO] [床预设] 床装饰创建成功: team={}, entity={}".format(self.team, entity_id))
            else:
                print("[INFO] [床预设] 未创建床装饰 (可能使用默认配置)")

        except Exception as e:
            print("[ERROR] [床预设] 创建床装饰失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _destroy_bed_ornament(self):
        """
        销毁床装饰

        调用时机: 床被破坏时 (_destroy_bed)
        """
        try:
            # 获取BedOrnamentSystem
            bed_ornament_system = self._get_bed_ornament_system()
            if not bed_ornament_system:
                return

            # 销毁床装饰
            bed_ornament_system.destroy_bed_ornament(self.team)

            # 清除引用
            if self.ornament_entity_id:
                self.ornament_entity_id = None
                print("[INFO] [床预设] 床装饰已销毁: team={}".format(self.team))

        except Exception as e:
            print("[ERROR] [床预设] 销毁床装饰失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _get_bed_ornament_system(self):
        """
        获取BedOrnamentSystem引用

        Returns:
            BedOrnamentSystem | None: BedOrnamentSystem实例, 失败返回None
        """
        try:
            import mod.server.extraServerApi as serverApi
            from Script_NeteaseMod.modConfig import MOD_NAME

            # 获取BedWarsGameSystem
            game_system = serverApi.GetSystem(MOD_NAME, "BedWarsGameSystem")
            if not game_system:
                print("[WARN] [床预设] 无法获取BedWarsGameSystem")
                return None

            # 获取OrnamentSystem
            ornament_system = game_system.ornament_system
            if not ornament_system:
                print("[WARN] [床预设] OrnamentSystem未初始化")
                return None

            # 获取BedOrnamentSystem
            if not hasattr(ornament_system, 'bed_ornament_system'):
                print("[WARN] [床预设] BedOrnamentSystem未初始化")
                return None

            return ornament_system.bed_ornament_system

        except Exception as e:
            print("[ERROR] [床预设] 获取BedOrnamentSystem失败: {}".format(str(e)))
            return None

    def _calculate_bed_yaw(self):
        """
        计算床的朝向角度

        通过获取床方块的direction状态计算朝向

        Returns:
            float: 朝向角度
        """
        try:
            if not self.bed_blocks or len(self.bed_blocks) == 0:
                return 0

            import mod.server.extraServerApi as serverApi

            # 创建方块信息组件
            levelId = serverApi.GetLevelId()
            block_comp = serverApi.GetEngineCompFactory().CreateBlockInfo(levelId)

            # 获取第一个床方块的状态
            dimension_id = self.instance.get_config("dimension_id", 0)
            block_dict = block_comp.GetBlockNew(self.bed_blocks[0], dimension_id)

            if block_dict:
                # 获取方块状态
                states = block_dict.get('states', {})
                direction = states.get('direction', 0)

                # 根据direction计算yaw
                # direction: 0=南, 1=西, 2=北, 3=东
                # yaw = direction * 90 - 180
                yaw = direction * 90 - 180

                print("[INFO] [床预设] 床朝向: direction={}, yaw={}".format(direction, yaw))
                return yaw

        except Exception as e:
            print("[ERROR] [床预设] 计算床朝向失败: {}".format(str(e)))

        # 默认朝向
        return 0

    def _place_bed_blocks_async(self, instance):
        """
        异步放置床方块（使用BlockPresetServerBase封装的接口）

        核心新功能: 根据配置中的pos和rotation放置床的两个方块(床头+床尾)

        床方块结构:
        - 床由2个方块组成: 床头(head)和床尾(foot)
        - direction状态决定朝向: 0=南(+z), 1=西(-x), 2=北(-z), 3=东(+x)

        Args:
            instance: PresetInstance对象
        """
        # [FIX 2025-11-22 v3] 标记正在异步放置，避免重复放置
        self.bed_placing = True

        try:
            # 1. 获取配置参数
            pos = instance.get_config("pos")
            rotation = instance.get_config("rotation", {})

            # 从RoomManagementSystem获取当前对局的维度ID
            import mod.server.extraServerApi as serverApi
            room_system = serverApi.GetSystem("ECBedWars", "RoomManagementSystem")

            # 优先使用RoomManagementSystem的维度，否则从配置读取，最后使用预设实例的维度
            dimension_id = None
            if room_system and hasattr(room_system, 'current_dimension') and room_system.current_dimension is not None:
                dimension_id = room_system.current_dimension
                print("[INFO] [床预设] 从RoomManagementSystem获取维度: {}".format(dimension_id))
            else:
                # 备用方案1：从配置获取
                dimension_id = instance.get_config("dimension_id", None)
                if dimension_id is not None:
                    print("[INFO] [床预设] 从配置获取维度: {}".format(dimension_id))
                else:
                    # 备用方案2：从预设实例属性获取
                    if hasattr(self, 'dimension_id') and self.dimension_id is not None:
                        dimension_id = self.dimension_id
                        print("[INFO] [床预设] 从预设实例获取维度: {}".format(dimension_id))
                    else:
                        print("[ERROR] [床预设] 无法获取维度ID，使用默认维度0")
                        dimension_id = 0

            # 确保dimension_id是整数类型
            if not isinstance(dimension_id, int):
                print("[ERROR] [床预设] 维度ID类型错误: type={}, value={}".format(type(dimension_id), dimension_id))
                try:
                    dimension_id = int(dimension_id)
                    print("[INFO] [床预设] 已转换维度ID为整数: {}".format(dimension_id))
                except (ValueError, TypeError):
                    print("[ERROR] [床预设] 维度ID转换失败，使用默认维度0")
                    dimension_id = 0

            if not pos:
                print("[ERROR] [床预设] 缺少pos配置，无法放置床方块")
                self._on_bed_blocks_placed(False, instance)
                return

            # 2. 解析位置和朝向
            if isinstance(pos, dict):
                base_pos = (int(pos['x']), int(pos['y']), int(pos['z']))
            else:
                base_pos = (int(pos[0]), int(pos[1]), int(pos[2]))

            # 解析yaw角度到minecraft床的direction状态
            yaw = rotation.get('yaw', 0) if isinstance(rotation, dict) else 0
            direction = self._yaw_to_bed_direction(yaw)

            print("[INFO] [床预设] 准备异步放置床: pos={}, yaw={}, direction={}".format(
                base_pos, yaw, direction
            ))

            # 3. 计算床头和床尾的位置
            foot_pos = base_pos
            head_pos = self._calculate_head_position(base_pos, direction)

            print("[INFO] [床预设] 准备异步放置床方块: foot={}, head={}, direction={}".format(
                foot_pos, head_pos, direction
            ))

            # 4. 使用GetBlockAuxValueFromStates获取正确的aux值
            # minecraft:bed的states:
            #   - direction: int (0=南,1=西,2=北,3=东)
            #   - head_piece_bit: bool (0=床尾,1=床头)
            #   - occupied_bit: bool (是否被占用)
            import mod.server.extraServerApi as serverApi
            levelId = serverApi.GetLevelId()
            comp_state = serverApi.GetEngineCompFactory().CreateBlockState(levelId)

            # 床尾的states
            foot_states = {
                'direction': direction,
                'head_piece_bit': 0,  # 0表示床尾
                'occupied_bit': 0
            }
            bed_foot_aux = comp_state.GetBlockAuxValueFromStates('minecraft:bed', foot_states)

            # 床头的states
            head_states = {
                'direction': direction,
                'head_piece_bit': 1,  # 1表示床头
                'occupied_bit': 0
            }
            bed_head_aux = comp_state.GetBlockAuxValueFromStates('minecraft:bed', head_states)

            print("[INFO] [床预设] 计算床aux值: foot_aux={}, head_aux={}, direction={}".format(
                bed_foot_aux, bed_head_aux, direction
            ))

            # 5. 使用回调链放置床方块
            # 参考GuideBedPresetDefServer的正确实现:
            # 先放置床尾，成功后再放置床头，避免异步冲突

            def on_foot_placed(success_foot):
                if not success_foot:
                    print("[WARN] [床预设] 床尾放置失败(可能地图已有床方块)，继续执行后续初始化")
                    self._on_bed_blocks_placed(True, instance)
                    return

                # 床尾放置成功后，先验证床尾方块确实存在，再放置床头
                # 修复原因: Minecraft床头方块无法单独放置，必须在床尾存在后才能放置
                # 需要等待床尾方块在游戏世界中生效后再放置床头
                import mod.server.extraServerApi as serverApi
                levelId = serverApi.GetLevelId()
                block_comp = serverApi.GetEngineCompFactory().CreateBlockInfo(levelId)

                # 验证床尾方块是否存在
                foot_block = block_comp.GetBlockNew(foot_pos, dimension_id)
                if not foot_block or foot_block.get('name') != 'minecraft:bed':
                    print("[WARN] [床预设] 床尾方块验证失败(name={}), 可能地图中已有床方块，继续初始化".format(
                        foot_block.get('name') if foot_block else 'None'
                    ))
                    self._on_bed_blocks_placed(True, instance)
                    return

                print("[INFO] [床预设] 床尾方块验证成功，准备放置床头")

                # 添加延迟，确保床尾方块在游戏世界中完全生效
                # 延迟1个tick (0.05秒) 后放置床头
                def delayed_place_head():
                    def on_head_placed(success_head):
                        if success_head:
                            print("[INFO] [床预设] 床方块放置成功: foot={}, head={}, direction={}".format(
                                foot_pos, head_pos, direction
                            ))
                        else:
                            # 注意: 这是正常现象!
                            # Minecraft引擎在放置床尾时会自动创建床头方块
                            # 所以我们手动放置床头会失败(因为已经存在了)
                            # 但这不影响功能,床已经是完整的了
                            pass

                        # 在床周围小范围查询床方块并染色
                        # 使用床尾位置作为中心，查询周围±1格的床方块
                        self._query_and_color_bed_blocks(foot_pos, dimension_id, instance)

                        self._on_bed_blocks_placed(True, instance)

                    # 异步放置床头(使用minecraft:bed和正确的aux值)
                    print("[INFO] [床预设] 异步放置床头: pos={}, aux={}".format(head_pos, bed_head_aux))
                    self.set_block_async(head_pos, 'minecraft:bed', bed_head_aux, dimension_id, on_head_placed)

                # 延迟0.05秒（1 tick）后放置床头
                self.add_timer(0.05, delayed_place_head)

            # 异步放置床尾(使用minecraft:bed和正确的aux值)
            print("[INFO] [床预设] 异步放置床尾: pos={}, aux={}".format(foot_pos, bed_foot_aux))
            self.set_block_async(foot_pos, 'minecraft:bed', bed_foot_aux, dimension_id, on_foot_placed)

        except Exception as e:
            print("[ERROR] [床预设] 异步放置床方块异常: {}".format(str(e)))
            import traceback
            traceback.print_exc()
            self._on_bed_blocks_placed(False, instance)

    def _on_bed_blocks_placed(self, success, instance):
        """
        床方块放置完成后的回调

        执行后续的初始化逻辑:
        1. 获取床方块坐标
        2. 初始化床颜色
        3. 注册事件监听
        4. 上报床数据到游戏系统

        Args:
            success (bool): 放置是否成功
            instance: PresetInstance对象
        """
        print("[INFO] [床预设] 开始后续初始化")

        # 注意: 床方块的查询和染色已经在床头放置回调中完成
        # 这里只需要确保bed_blocks有默认值，避免后续代码访问空列表时出错
        if not self.bed_blocks:
            pos = instance.get_config("pos")
            if isinstance(pos, dict):
                temp_pos = (int(pos['x']), int(pos['y']), int(pos['z']))
            else:
                temp_pos = (int(pos[0]), int(pos[1]), int(pos[2]))
            self.bed_blocks = [temp_pos]
            print("[WARN] [床预设] bed_blocks为空，使用预设位置作为后备")

        # 注册事件监听
        import mod.server.extraServerApi as serverApi
        server_system = instance.manager.server_api

        if server_system:
            # 监听方块破坏事件 (引擎事件)
            server_system.ListenForEvent(
                serverApi.GetEngineNamespace(),
                serverApi.GetEngineSystemName(),
                "ServerPlayerTryDestroyBlockEvent",
                self,
                self._on_player_try_destroy_block
            )

        # 4. 上报床数据到游戏系统
        self._notify_bed_data_to_game_system(instance)

        # 5. 同步床数据到客户端（用于客户端破坏保护）
        self._sync_bed_data_to_client(instance)

        # 6. 初始化陷阱管理器
        self._init_trap_manager(instance)

        self.bed_destroyed = False

        # 7. 标记床已就绪，等待玩家客户端加载完毕后发送消息
        # 修复P1.3: 移除立即发送消息的逻辑，改为在玩家加载完成时发送
        self.bed_ready = True
        self.instance = instance

        print("[床预设-服务端] 床方块放置完成，已标记bed_ready=True")
        print("[床预设-服务端] 将在玩家客户端加载完毕时发送浮空文字消息(仅队伍成员)")

        # 注意: 不再调用 instance.send_to_client()
        # 浮空文字消息将在 _on_client_load_finish() 中按需发送

        print("[INFO] [床预设] 完整初始化完成: team={}".format(self.team))

        # [FIX 2025-11-22 v3] 清除异步放置标志
        self.bed_placing = False

    def _yaw_to_bed_direction(self, yaw):
        """
        将yaw角度转换为minecraft床的direction状态

        Args:
            yaw (float): 朝向角度

        Returns:
            int: minecraft床的direction状态
                0 = 南(+z)
                1 = 西(-x)
                2 = 北(-z)
                3 = 东(+x)
        """
        # 归一化yaw到0-360范围
        yaw = yaw % 360
        if yaw < 0:
            yaw += 360

        # 映射yaw到direction
        # 0° = 南(+z) = direction 0
        # 90° = 西(-x) = direction 1
        # 180° = 北(-z) = direction 2
        # 270° = 东(+x) = direction 3
        if 45 <= yaw < 135:
            return 1  # 西
        elif 135 <= yaw < 225:
            return 2  # 北
        elif 225 <= yaw < 315:
            return 3  # 东
        else:
            return 0  # 南

    def _calculate_head_position(self, foot_pos, direction):
        """
        根据床尾位置和朝向计算床头位置

        Args:
            foot_pos (tuple): 床尾位置 (x, y, z)
            direction (int): 床的朝向
                0 = 南(+z)
                1 = 西(-x)
                2 = 北(-z)
                3 = 东(+x)

        Returns:
            tuple: 床头位置 (x, y, z)
        """
        x, y, z = foot_pos

        if direction == 0:  # 南(+z)
            return (x, y, z + 1)
        elif direction == 1:  # 西(-x)
            return (x - 1, y, z)
        elif direction == 2:  # 北(-z)
            return (x, y, z - 1)
        elif direction == 3:  # 东(+x)
            return (x + 1, y, z)
        else:
            # 默认向南
            return (x, y, z + 1)

    def _get_dimension_id(self, instance):
        """
        获取床所在维度ID（统一的维度ID获取逻辑）

        优先级：
        1. RoomManagementSystem.current_dimension（当前对局维度）
        2. 配置 dimension_id
        3. 预设实例属性 self.dimension_id
        4. 默认值 0

        包含类型安全检查，确保返回整数类型

        Args:
            instance: PresetInstance对象

        Returns:
            int: 维度ID
        """
        try:
            # 从RoomManagementSystem获取当前对局的维度ID
            import mod.server.extraServerApi as serverApi
            room_system = serverApi.GetSystem("ECBedWars", "RoomManagementSystem")

            # 优先使用RoomManagementSystem的维度，否则从配置读取，最后使用预设实例的维度
            dimension_id = None
            if room_system and hasattr(room_system, 'current_dimension') and room_system.current_dimension is not None:
                dimension_id = room_system.current_dimension
                print("[INFO] [床预设] 从RoomManagementSystem获取维度: {}".format(dimension_id))
            else:
                # 备用方案1：从配置获取
                dimension_id = instance.get_config("dimension_id", None)
                if dimension_id is not None:
                    print("[INFO] [床预设] 从配置获取维度: {}".format(dimension_id))
                else:
                    # 备用方案2：从预设实例属性获取
                    if hasattr(self, 'dimension_id') and self.dimension_id is not None:
                        dimension_id = self.dimension_id
                        print("[INFO] [床预设] 从预设实例获取维度: {}".format(dimension_id))
                    else:
                        print("[ERROR] [床预设] 无法获取维度ID，使用默认维度0")
                        dimension_id = 0

            # 确保dimension_id是整数类型
            if not isinstance(dimension_id, int):
                print("[ERROR] [床预设] 维度ID类型错误: type={}, value={}".format(type(dimension_id), dimension_id))
                try:
                    dimension_id = int(dimension_id)
                    print("[INFO] [床预设] 已转换维度ID为整数: {}".format(dimension_id))
                except (ValueError, TypeError):
                    print("[ERROR] [床预设] 维度ID转换失败，使用默认维度0")
                    dimension_id = 0

            return dimension_id

        except Exception as e:
            print("[ERROR] [床预设] 获取维度ID异常: {}".format(str(e)))
            import traceback
            traceback.print_exc()
            return 0

    def _get_player_team_from_game_system(self, player_id):
        """
        从游戏系统获取玩家队伍

        直接查询BedWarsGameSystem的team_module,获取实时的玩家队伍信息
        不依赖预设内部缓存的player_to_team字典

        Args:
            player_id: 玩家ID

        Returns:
            str|None: 队伍ID,如果玩家不在任何队伍则返回None
        """
        try:
            import mod.server.extraServerApi as serverApi
            from Script_NeteaseMod.modConfig import MOD_NAME

            # 获取BedWarsGameSystem
            game_system = serverApi.GetSystem(MOD_NAME, "BedWarsGameSystem")
            if not game_system:
                print("[ERROR] [床预设] 无法获取BedWarsGameSystem")
                return None

            # 从team_module获取玩家队伍
            if hasattr(game_system, 'team_module') and game_system.team_module:
                player_team = game_system.team_module.get_player_team(player_id)
                return player_team
            else:
                print("[ERROR] [床预设] BedWarsGameSystem没有team_module")
                return None

        except Exception as e:
            print("[ERROR] [床预设] 获取玩家队伍失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()
            return None

    def _on_client_load_finish(self, args):
        """
        玩家客户端加载完毕事件回调

        修复P1.3: 只向同队玩家发送浮空文字消息
        - 确保客户端已就绪（时序安全）
        - 服务端过滤队伍（可见性控制）
        - 支持中途加入玩家

        参考: GuidePresetDefServer.on_client_load_end()

        Args:
            args: 事件参数
                - playerId: str 玩家ID
        """
        player_id = args.get('playerId')

        if not player_id:
            print("[WARN] [床预设-服务端] ClientLoadAddonsFinishServerEvent缺少playerId")
            return

        # 检查床是否已就绪
        if not self.bed_ready or not self.instance:
            return

        # 获取玩家队伍
        player_team = self._get_player_team(player_id)

        if not player_team:
            return

        # 判断玩家是否与床同队
        if player_team != self.team:
            return

        # 玩家与床同队，发送浮空文字消息
        print("[INFO] [床预设-服务端] 玩家{}(队伍{})加载完成，发送浮空文字消息".format(
            player_id, player_team
        ))
        self._send_floating_text_to_player(player_id)

    def _get_player_team(self, player_id):
        """
        获取玩家所属队伍

        Args:
            player_id (str): 玩家ID

        Returns:
            str|None: 队伍ID (如 "RED", "BLUE") 或 None
        """
        # 直接调用已存在的方法
        return self._get_player_team_from_game_system(player_id)

    def _send_floating_text_to_online_teammates(self):
        """
        向所有已在线的同队玩家发送床浮空文字消息

        调用时机: 游戏开始时(BedWarsRunning事件)
        目的: 解决时机问题 - 玩家在Lobby阶段已加载完成,但床预设在Running状态才创建

        重要: 只有当前游戏维度的床预设才发送消息,避免其他维度的床预设重复发送
        """
        try:

            # 检查床是否已放置
            if not self.bed_blocks:
                return

            # 获取当前游戏维度
            import mod.server.extraServerApi as serverApi
            from Script_NeteaseMod.modConfig import MOD_NAME

            game_system = serverApi.GetSystem(MOD_NAME, "BedWarsGameSystem")
            if not game_system:
                print("[WARN] [床预设-服务端] 无法获取BedWarsGameSystem,跳过发送浮空文字")
                return

            if not hasattr(game_system, 'dimension'):
                print("[WARN] [床预设-服务端] BedWarsGameSystem没有dimension属性,跳过发送浮空文字")
                return

            game_dimension = game_system.dimension

            if game_dimension is None:
                return
        except Exception as e:
            print("[ERROR] [床预设-服务端] 获取游戏维度异常: {}".format(str(e)))
            import traceback
            traceback.print_exc()
            return

        # 获取所有在线玩家
        # 注意: 使用serverApi.GetPlayerList()而不是player_comp.GetPlayerList()
        # PlayerCompServer没有GetPlayerList()方法,应该使用serverApi的全局方法
        try:
            online_players = serverApi.GetPlayerList()
        except Exception as e:
            print("[ERROR] [床预设-服务端] 获取在线玩家列表异常: {}".format(str(e)))
            import traceback
            traceback.print_exc()
            return

        if not online_players:
            return

        # 检查玩家维度,确保只向当前游戏维度的玩家发送消息
        # 这避免了多个地图配置中的床预设重复发送消息
        try:
            comp_factory = serverApi.GetEngineCompFactory()

            # 过滤出在游戏维度中的玩家
            players_in_game_dimension = []
            for player_id in online_players:
                # 使用Dimension组件获取玩家维度
                comp_dim = comp_factory.CreateDimension(player_id)
                player_dimension = comp_dim.GetPlayerDimensionId()
                if player_dimension == game_dimension:
                    players_in_game_dimension.append(player_id)
        except Exception as e:
            print("[ERROR] [床预设-服务端] 检查玩家维度异常: {}".format(str(e)))
            import traceback
            traceback.print_exc()
            return

        if not players_in_game_dimension:
            return

        print("[INFO] [床预设-服务端] 开始遍历{}个游戏维度中的在线玩家,向同队玩家发送浮空文字".format(
            len(players_in_game_dimension)
        ))

        # 遍历所有在游戏维度中的玩家
        sent_count = 0
        for player_id in players_in_game_dimension:
            # 获取玩家队伍
            player_team = self._get_player_team(player_id)

            if not player_team:
                continue

            # 判断玩家是否与床同队
            if player_team != self.team:
                continue

            # 玩家与床同队,发送浮空文字消息
            self._send_floating_text_to_player(player_id)
            sent_count += 1

        print("[INFO] [床预设-服务端] 已向{}个同队玩家发送浮空文字消息".format(sent_count))

    def _send_floating_text_to_player(self, player_id):
        """
        向指定玩家发送床浮空文字消息(单播)

        Args:
            player_id (str): 玩家ID
        """
        if not self.instance or not self.bed_blocks:
            print("[WARN] [床预设-服务端] instance或bed_blocks未初始化,无法发送消息")
            return

        # 检查是否已经向该玩家发送过浮空文字消息
        if player_id in self.sent_floating_text_players:
            return

        bed_pos = self.bed_blocks[0]
        message_data = {
            'pos': bed_pos,
            'team': self.team,
            'ornament_owner': None,
            'instance_id': self.instance.instance_id
        }

        # 使用PresetManagerSystem的单播方法
        from ECPresetServerScripts import get_preset_system
        preset_system = get_preset_system()

        event_data = {
            "context_id": self.instance.manager.context_id,
            "instance_id": self.instance.instance_id,
            "message_type": "bed_blocks_placed",
            "data": message_data
        }

        # 点对点通知(单播)
        preset_system.NotifyToClient(player_id, "ECPreset_Message", event_data)

        # 记录已发送过的玩家，防止重复发送
        self.sent_floating_text_players.add(player_id)

        print("[INFO] [床预设-服务端] 已单播浮空文字消息给玩家: {}(队伍{})".format(
            player_id, self.team
        ))

