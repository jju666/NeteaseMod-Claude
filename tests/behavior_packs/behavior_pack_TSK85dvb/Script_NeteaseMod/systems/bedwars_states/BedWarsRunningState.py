# -*- coding: utf-8 -*-
"""
BedWarsRunningState - 起床战争运行状态

功能:
- 游戏主要进行阶段
- 监听玩家死亡事件
- 监听床破坏事件
- 监听方块放置/破坏事件
- 处理攻击记录

原文件: Parts/ECBedWars/state/BedWarsRunningState.py
"""

import mod.server.extraServerApi as serverApi
import time
from ..state.GamingState import GamingState


class BedWarsRunningState(GamingState):
    """起床战争运行状态"""

    def __init__(self, parent):
        """
        初始化运行状态

        Args:
            parent: 父状态
        """
        GamingState.__init__(self, parent)

        # HUD更新定时器
        self.next_tick_hud = 0  # 下次HUD更新时间戳

        # 注册生命周期回调
        self.with_enter(self._on_enter)
        self.with_exit(self._on_exit)
        self.with_tick(self._on_tick)

    def _on_enter(self):
        """进入运行状态"""
        system = self.get_system()
        system.LogInfo("BedWarsRunningState entered")

        # ===== [NEW] 清理对局维度的非玩家实体 =====
        # 目的: 清理可能存在的持久化保存实体,避免干预游戏正常流程
        # 时机: 在所有预设初始化之前执行,确保干净的游戏环境
        self._cleanup_non_player_entities()
        system.LogInfo("[CLEANUP] 已清理对局维度的非玩家实体")

        # ===== [P0-1 FIX] 广播BedWarsRunning事件 =====
        # 目的: 通知所有预设(如商店)清理完成,可以安全创建实体
        # 时机: 在清理完成后立即广播,在其他初始化之前
        system.broadcast_preset_event("BedWarsRunning", {})
        system.LogInfo("[P0-1 FIX] 已广播BedWarsRunning事件,商店NPC即将创建")

        # ===== [CRITICAL FIX P0-2] 生成器启动广播 =====
        # 启动所有生成器预设(Generator)开始生成资源
        self._start_all_generators()
        system.LogInfo("[P0-2 FIX] 已启动所有资源生成器")

        # ===== [CRITICAL FIX P0-3] 玩家初始化 =====
        # 传送玩家到出生点并初始化装备
        self._initialize_players()
        system.LogInfo("[P0-3 FIX] 已完成玩家初始化")

        # 初始化游戏阶段
        self.init_from_config()

        # 注册游戏事件监听
        self._register_game_events()

        # 启用标点系统（如果存在）
        if hasattr(system, 'waypoint_manager') and system.waypoint_manager:
            system.waypoint_manager.enable_waypoint()
            system.LogInfo("标点系统已启用")

        # ===== [CRITICAL FIX P0-8] HUD系统启动 =====
        # 清空HUD并准备显示游戏信息
        self._initialize_hud_system()
        system.LogInfo("[P0-8 FIX] 已启动HUD系统")

        # 广播游戏开始消息
        system._broadcast_message(u"游戏开始!", u'\xa7a')

    def _on_exit(self):
        """退出运行状态"""
        system = self.get_system()
        system.LogInfo("BedWarsRunningState exited")

    def _on_tick(self):
        """每帧更新"""
        # 状态机的tick由父类处理

        # 定时更新HUD(每秒1次)
        self._on_tick_hud()

    def _register_game_events(self):
        """注册游戏事件"""
        system = self.get_system()

        # ===== 原有事件保留 =====
        # 玩家死亡事件
        self.listen_engine_event(
            'ServerPlayerDieEvent',
            self._on_player_die
        )

        # 玩家攻击事件
        self.listen_engine_event(
            'ActorHurtEvent',
            self._on_actor_hurt
        )

        # 方块放置事件
        self.listen_engine_event(
            'ServerPlaceBlockEvent',
            self._on_place_block
        )

        # 方块破坏事件
        self.listen_engine_event(
            'ServerBlockUseEvent',
            self._on_block_use
        )

        # ===== [P0-4 FIX] 补充缺失事件监听 =====

        # 1. 方块破坏检测事件 (限制只能破坏玩家放置的方块)
        self.listen_engine_event(
            'ServerPlayerTryDestroyBlockEvent',
            self._on_try_destroy_block
        )

        # 2. 方块放置检测事件 (限制放置区域、记录放置的方块)
        self.listen_engine_event(
            'ServerEntityTryPlaceBlockEvent',
            self._on_try_place_block
        )

        # 3. 实际伤害事件 (用于击杀归属记录)
        self.listen_engine_event(
            'ActuallyHurtServerEvent',
            self._on_actually_hurt
        )

        # 4. 玩家吃食物事件 (神奇牛奶解除陷阱效果)
        self.listen_engine_event(
            'PlayerEatFoodServerEvent',
            self._on_eat_food
        )

        # 5. 玩家离开游戏事件
        self.listen_engine_event(
            'PlayerIntendLeaveServerEvent',
            self._on_player_leave
        )

        # 6. 玩家重生完成事件
        self.listen_engine_event(
            'PlayerRespawnFinishServerEvent',
            self._on_player_respawn
        )

        # 7. 玩家饥饿度变化事件 (禁用饥饿系统)
        self.listen_engine_event(
            'PlayerHungerChangeServerEvent',
            self._on_hunger_change
        )

        # 8. 伤害事件 (队伍友军保护、出生保护)
        self.listen_engine_event(
            'DamageEvent',
            self._on_damage
        )

        # 9. 玩家拾取物品事件 (观战者禁止拾取)
        self.listen_engine_event(
            'ServerPlayerTryTouchEvent',
            self._on_try_pickup
        )

        # 10. 预设事件: 床破坏
        self.listen_preset_event(
            'PresetBedDestroyed',
            self._on_bed_destroyed
        )

        # 11. 预设事件: 商店购买
        self.listen_preset_event(
            'BedWarsShopBuy',
            self._on_shop_buy
        )

        system.LogInfo("[P0-4 FIX] 已注册15个游戏事件监听")

    # ========== 事件处理 ==========

    def _on_player_die(self, args):
        """
        玩家死亡事件

        Args:
            args: {'id': player_id, 'attacker': attacker_id, 'damageCause': str}
        """
        system = self.get_system()
        player_id = args.get('id')
        attacker_id = args.get('attacker')
        damage_cause = args.get('damageCause')  # 伤害原因(void, fall, entity_attack等)

        system.LogInfo("玩家死亡事件 player={} attacker={} cause={}".format(
            player_id, attacker_id, damage_cause))

        # 调用BedWarsGameSystem的死亡处理
        system.on_player_die(player_id, attacker_id, damage_cause)

    def _on_actor_hurt(self, args):
        """
        实体受伤事件

        功能：记录玩家对玩家的攻击，用于虚空击杀归属判定

        Args:
            args: {'id': victim_id, 'attacker': attacker_id, 'damage': damage}
        """
        system = self.get_system()
        victim_id = args.get('id')
        attacker_id = args.get('attacker')

        # 只记录玩家对玩家的攻击
        if not victim_id or not attacker_id:
            return

        # 检查是否都是玩家
        comp = serverApi.GetEngineCompFactory()
        type_comp = comp.CreateEngineType(serverApi.GetLevelId())

        if type_comp.IsPlayer(victim_id) and type_comp.IsPlayer(attacker_id):
            # 使用统一的攻击记录方法
            # 使用 'knockback' 标识击退攻击，便于日志区分
            system.record_player_attack(victim_id, attacker_id, 'knockback')

            system.LogDebug("记录击退攻击: victim={} attacker={} cause=knockback".format(
                victim_id, attacker_id))

    def _on_place_block(self, args):
        """
        方块放置事件

        Args:
            args: {'x': x, 'y': y, 'z': z, 'playerId': player_id}
        """
        system = self.get_system()
        x = args.get('x')
        y = args.get('y')
        z = args.get('z')

        pos = (x, y, z)
        system.on_player_place_block(pos)

    def _on_block_use(self, args):
        """
        方块使用事件(右键点击)

        功能:
        1. 箱子初始化 - 第一次打开时清空内容
        2. 禁用某些交互方块（工作台、熔炉等）

        Args:
            args: {'x': x, 'y': y, 'z': z, 'playerId': player_id, 'blockName': blockName,
                   'dimensionId': int, 'cancel': bool}

        参考: 老项目 ECBedWarsPart.py:985-998 (server_on_block_use_event)
        """
        system = self.get_system()
        block_name = args.get('blockName', '')
        dimension = args.get('dimensionId')

        # 检查维度是否匹配
        if dimension != system.dimension:
            return

        # ===== 1. 箱子初始化逻辑 =====
        if block_name == 'minecraft:chest':
            pos = (args.get('x'), args.get('y'), args.get('z'))

            # 检查箱子是否已初始化过
            if pos not in system.inited_chests:
                system.LogInfo("初始化箱子 pos={}".format(pos))
                system.inited_chests.append(pos)

                # 清空箱子内容
                try:
                    comp_item = serverApi.GetEngineCompFactory().CreateItem(serverApi.GetLevelId())

                    # 获取箱子容器大小（通常是27格）
                    container_size = comp_item.GetContainerSize(pos, dimension)

                    # 清空所有槽位
                    for slot in range(container_size):
                        comp_item.SpawnItemToContainer(
                            {'newItemName': 'minecraft:air', 'count': 0},
                            slot,
                            pos,
                            dimension
                        )

                    system.LogInfo("箱子 {} 已清空，共 {} 个槽位".format(pos, container_size))

                except Exception as e:
                    system.LogError("初始化箱子失败 pos={} error={}".format(pos, str(e)))
                    import traceback
                    system.LogError(traceback.format_exc())

        # ===== 2. 禁用某些交互方块 =====
        # 禁用工作台、熔炉等方块的交互
        CANCEL_INTERACT_BLOCKS = [
            "minecraft:barrel",
            "minecraft:crafting_table",
            "minecraft:stonecutter_block",
            "minecraft:furnace",
            "minecraft:blast_furnace",
            "minecraft:smoker",
            "minecraft:cartography_table",
            "minecraft:loom",
            "minecraft:grindstone",
            "minecraft:lectern",
            "minecraft:smithing_table",
            "minecraft:stonecutter",
        ]

        if block_name in CANCEL_INTERACT_BLOCKS:
            args['cancel'] = True
            system.LogDebug("禁用方块交互: {}".format(block_name))

    # ===== [P0-4 FIX] 补充缺失的事件处理方法 =====

    def _on_try_destroy_block(self, args):
        """
        方块破坏限制检查

        功能:
        1. 检查玩家是否在游戏中(非观战者)
        2. 检查备份区域限制
        3. 只允许破坏: (1)玩家放置的方块 (2)床方块
        4. 阻止破坏原始地形方块

        Args:
            args: {'playerId': str, 'x': int, 'y': int, 'z': int,
                   'dimensionId': int, 'cancel': bool}
        """
        system = self.get_system()
        player_id = args.get('playerId')
        pos = (args.get('x'), args.get('y'), args.get('z'))
        dimension = args.get('dimensionId')

        # 1. 检查维度是否匹配
        if dimension != system.dimension:
            return

        # 2. 检查玩家是否在游戏中
        if not system.team_module.is_player_alive(player_id):
            args['cancel'] = True
            return

        # 3. 检查备份区域限制
        if not self._is_position_in_backup_range(pos, system):
            args['cancel'] = True
            # 通知玩家
            player = system._get_player_object(player_id)
            if player:
                system.NotifyToClient(player_id, 'SendMessage', {
                    'msg': u"\xa7c\xa7l警告：您只能在游戏区域内破坏方块！"
                })
            return

        # 4. 获取方块信息
        comp_block = serverApi.GetEngineCompFactory().CreateBlockInfo(serverApi.GetLevelId())
        block_info = comp_block.GetBlockNew(pos, dimension)
        is_bed_block = block_info and block_info.get('name') == 'minecraft:bed'

        # 5. 检查是否允许破坏: 床方块或玩家放置的方块
        if not is_bed_block and pos not in system.placed_blocks:
            # 不是床方块且不是玩家放置的方块,禁止破坏
            args['cancel'] = True
            return

        # 破坏允许通过,记录日志
        system.LogInfo("玩家 {} 破坏方块: {}".format(player_id, pos))

    def _on_try_place_block(self, args):
        """
        方块放置限制检查

        功能:
        1. 检查玩家是否在游戏中(非观战者)
        2. 检查备份区域限制(防止在区域外放置)
        3. 检查是否正在备份地图(备份时禁止放置)
        4. TNT方块自动点燃
        5. 记录玩家放置的方块到backup系统和placed_blocks列表

        Args:
            args: {'entityId': str, 'x': int, 'y': int, 'z': int,
                   'dimensionId': int, 'blockName': str, 'cancel': bool}
        """
        system = self.get_system()
        player_id = args.get('entityId')
        pos = (args.get('x'), args.get('y'), args.get('z'))
        dimension = args.get('dimensionId')
        block_name = args.get('blockName', '')

        # 1. 检查维度是否匹配
        if dimension != system.dimension:
            return

        # 2. 检查玩家是否在游戏中
        if not system.team_module.is_player_alive(player_id):
            args['cancel'] = True
            return

        # 3. 检查备份区域限制
        if not self._is_position_in_backup_range(pos, system):
            args['cancel'] = True
            # 通知玩家
            system.NotifyToClient(player_id, 'SendMessage', {
                'msg': u"\xa7c\xa7l警告：您只能在游戏区域内放置方块！"
            })
            return

        # 4. 检查是否正在备份地图
        if self._is_map_backup_in_progress(system):
            args['cancel'] = True
            system.NotifyToClient(player_id, 'SendMessage', {
                'msg': u"\xa7e\xa7l提示：地图正在备份中，请稍候再放置方块！"
            })
            return

        # 5. 记录玩家放置的方块
        system.on_player_place_block(pos)
        system.LogInfo("玩家 {} 放置方块: {} at {}".format(player_id, block_name, pos))

        # 6. TNT自动点燃(在放置后下一tick处理)
        if block_name == 'minecraft:tnt':
            self._auto_ignite_tnt(pos, dimension, system, player_id)

    def _on_actually_hurt(self, args):
        """
        实际伤害事件 (用于击杀归属记录和死亡判定)

        功能:
        1. 记录攻击者信息（用于虚空死亡归属判定）
        2. 更新计分板统计（记录伤害数据）
        3. 检查玩家生命值，如果 <= 0 则触发死亡处理

        Args:
            args: {'entityId': str, 'srcId': str, 'damage_f': float, 'cause': int}

        参考: 老项目 BedWarsRunningState.py:717-740
        """
        system = self.get_system()
        victim_id = args.get('entityId')
        attacker_id = args.get('srcId')
        damage_f = args.get('damage_f', 0.0)  # 注意: 老项目使用 'damage_f' 而不是 'damage'
        cause = args.get('cause')

        # 检查受害者是否在游戏中
        if not system.team_module.is_player_alive(victim_id):
            return  # 表示不是本局的玩家

        # === 1. 更新计分板统计（仅当攻击者在游戏中） ===
        if attacker_id is not None and system.team_module.is_player_alive(attacker_id):
            # 记录伤害数据(用于统计)
            if system.scoreboard:
                system.scoreboard.on_player_damage(victim_id, attacker_id, damage_f, cause)

            # === 2. 记录攻击（用于虚空击杀归属等） ===
            attacker_team = system.team_module.get_player_team(attacker_id)
            victim_team = system.team_module.get_player_team(victim_id)

            # 只记录来自不同队伍的攻击
            if attacker_team != victim_team and damage_f > 0:
                system.record_player_attack(victim_id, attacker_id, str(cause))

        # === 3. 检查死亡判定 ===
        # 获取玩家对象并检查生命值
        try:
            player = system.get_better_player_obj(victim_id)
            current_health = player.GetHealth()

            # 检查死亡条件（参考老项目L737: if player.GetHealth() - damage_f <= 0）
            if current_health - damage_f <= 0:
                # 玩家即将死亡，取消本次伤害（防止重复触发死亡事件）
                args['damage_f'] = 0

                # 触发死亡处理（参考老项目L739: self.on_player_die(entity_id, src_id, cause)）
                # 修复: 调用状态类的事件处理方法 _on_player_die，它会转发到 system.on_player_die()
                # _on_player_die 方法位于第199行，负责调用 BedWarsGameSystem.on_player_die()
                self._on_player_die({
                    'id': victim_id,
                    'attacker': attacker_id,
                    'damageCause': str(cause)
                })

                # 触发复活完成事件（参考老项目L740: self.on_player_respawn_finish(entity_id)）
                # 注意：老项目在_on_actually_hurt中同时调用on_player_die和on_player_respawn_finish
                # on_player_die负责死亡处理和记录复活倒计时
                # on_player_respawn_finish立即将玩家切换为观察者模式（显示"你阵亡了"）
                # 修复: 不应该调用_on_player_respawn（那是复活时调用的）
                # 应该只显示Title和启用观战模式
                try:
                    # 发送阵亡Title
                    # 使用BetterPlayerObject.send_title()方法而非SetNotifyMsg
                    # 参考: 老项目 BedWarsRunningState.py:1069 和 BetterPlayerObject.send_title()
                    player_obj = system.get_better_player_obj(victim_id)
                    if player_obj:
                        player_obj.send_title(u"\xa7l\xa7c你阵亡了")

                    # 启用观战模式
                    system.server_enable_viewer(victim_id)
                except Exception as e:
                    system.LogError("死亡后启用观战模式失败: player={} error={}".format(victim_id, str(e)))

                system.LogInfo("死亡判定: {} 被 {} 击杀 (生命: {}, 伤害: {})".format(
                    victim_id, attacker_id, current_health, damage_f))

        except Exception as e:
            system.LogError("死亡判定检查失败: victim={} error={}".format(victim_id, str(e)))

    def _on_eat_food(self, args):
        """
        玩家吃食物事件 (神奇牛奶解除陷阱效果)

        功能:
        - 检测牛奶桶使用
        - 添加30秒陷阱免疫效果
        - 发送提示消息和Title

        参考: 老项目 BedWarsRunningState.py:1512-1553

        Args:
            args: {'playerId': str, 'itemDict': dict}
        """
        system = self.get_system()
        player_id = args.get('playerId')
        item_dict = args.get('itemDict', {})

        # 检查玩家是否在游戏中
        if not system.team_module.is_player_alive(player_id):
            return

        # 处理神奇牛奶 (添加陷阱免疫)
        item_name = item_dict.get('newItemName')
        if item_name == 'minecraft:milk_bucket':
            # 添加30秒陷阱免疫
            system.add_trap_immunity(player_id, 30)

            # 发送提示消息
            try:
                import mod.server.extraServerApi as serverApi
                comp = serverApi.GetEngineCompFactory().CreateMsg(player_id)
                comp.NotifyOneMessage(
                    player_id,
                    u"\xa7a你喝下了神奇牛奶，\xa7e30秒内免疫所有陷阱！",
                    u"\xa7a"
                )

                # 发送Title
                comp.NotifyOneTitle(
                    player_id,
                    u"\xa7l\xa7a陷阱免疫激活",
                    u"\xa7e持续30秒",
                    10,  # fadeIn: 0.5秒
                    40,  # stay: 2秒
                    10   # fadeOut: 0.5秒
                )

                # 播放音效
                pos_comp = serverApi.GetEngineCompFactory().CreatePos(player_id)
                player_pos = pos_comp.GetPos()
                if player_pos:
                    game_comp = serverApi.GetEngineCompFactory().CreateGame(system.GetLevelId())
                    game_comp.PlaySound(player_pos, "random.burp", 1.0, 1.0, False, player_id)

            except Exception as e:
                system.LogError("发送神奇牛奶提示失败: {}".format(str(e)))

            # 记录日志
            system.LogInfo("玩家 {} 使用了神奇牛奶，获得30秒陷阱免疫".format(player_id))

            # 记录免疫状态
            status = system.get_trap_immunity_status(player_id)
            system.LogDebug("玩家 {} 陷阱免疫状态: {}".format(player_id, status))

    def _on_player_leave(self, args):
        """
        玩家离开游戏事件

        功能:
        - 从队伍中移除玩家
        - 清理玩家数据
        - 检查游戏是否应该结束

        参考: 老项目 BedWarsRunningState.py:742-764

        Args:
            args: {'playerId': str}
        """
        system = self.get_system()
        player_id = args.get('playerId')

        # 检查玩家是否在对局中
        if not system.team_module.is_player_alive(player_id):
            return

        # 从队伍中移除玩家
        system.team_module.remove_player_from_team(player_id)
        system.LogInfo("玩家 {} 离开游戏".format(player_id))

        # 清理玩家数据
        system.clear_player_attack_record(player_id)

        # 检查游戏是否应该结束
        self._check_game_end()

    def _on_player_respawn(self, args):
        """
        玩家重生完成事件

        功能:
        - 发送阵亡Title提示
        - 启用观战模式

        参考: 老项目 BedWarsRunningState.py:1063-1070

        注意: 装备恢复已在 BedWarsGameSystem._respawn_player() 中完成
        调用链: _respawn_player → _apply_player_equipment_and_upgrades → _init_player_equipment

        Args:
            args: {'playerId': str}
        """
        system = self.get_system()
        player_id = args.get('playerId')

        system.LogInfo("玩家 {} 重生完成（进入观战）".format(player_id))

        # 检查玩家是否还在游戏中（可能已经淘汰）
        team = system.team_module.get_player_team(player_id)

        # 如果玩家不在任何队伍中，说明已被淘汰，显示阵亡Title
        if team is None:
            try:
                # 发送阵亡Title
                # 使用BetterPlayerObject.send_title()方法而非SetNotifyMsg
                player_obj = system.get_better_player_obj(player_id)
                if player_obj:
                    player_obj.send_title(u"\xa7l\xa7c你阵亡了")

                # 启用观战模式
                system.server_enable_viewer(player_id)

            except Exception as e:
                system.LogError("[_on_player_respawn] 发送阵亡Title失败: player={} error={}".format(
                    player_id, str(e)
                ))
        else:
            # 玩家还在游戏中，正常复活
            system.LogInfo("玩家 {} 复活并回到队伍 {}".format(player_id, team))

    def _on_hunger_change(self, args):
        """
        玩家饥饿度变化事件 (禁用饥饿系统)

        Args:
            args: {'playerId': str, 'hunger': int, 'cancel': bool}
        """
        system = self.get_system()
        player_id = args.get('playerId')

        # 在游戏维度禁用饥饿度变化
        comp = serverApi.GetEngineCompFactory().CreateDimension(player_id)
        if comp:
            dimension = comp.GetPlayerDimensionId()
            if dimension == system.config.get('map_dimension'):
                args['cancel'] = True

    def _on_damage(self, args):
        """
        伤害事件 (队伍友军保护、出生保护)

        Args:
            args: {'entityId': str, 'srcId': str, 'damage': float,
                   'cause': int, 'knock': bool, 'ignite': bool}
        """
        system = self.get_system()
        victim_id = args.get('entityId')
        attacker_id = args.get('srcId')

        # 检查受害者是否在游戏中
        if not system.team_module.is_player_alive(victim_id):
            return

        # 检查是否为友军伤害
        if attacker_id and system.team_module.is_player_alive(attacker_id):
            attacker_team = system.team_module.get_player_team(attacker_id)
            victim_team = system.team_module.get_player_team(victim_id)

            if attacker_team == victim_team and attacker_team is not None:
                # 同队伍攻击,取消伤害
                args['knock'] = False
                args['ignite'] = False
                args['damage'] = 0
                return

    def _on_try_pickup(self, args):
        """
        玩家拾取物品事件

        功能:
        1. 观战者禁止拾取物品
        2. 复活中的玩家禁止拾取物品
        3. 钻石/绿宝石拾取时播放装饰音效（meme特效）

        参考: 老项目 BedWarsRunningState.py:925-943

        Args:
            args: {'playerId': str, 'itemDict': dict, 'cancel': bool}
        """
        system = self.get_system()
        player_id = args.get('playerId')
        item_dict = args.get('itemDict', {})

        # 1. 观战者禁止拾取物品
        if not system.team_module.is_player_alive(player_id):
            args['cancel'] = True
            return

        # 2. 复活中的玩家禁止拾取物品
        if player_id in system.respawning:
            args['cancel'] = True
            return

        # 3. 处理特殊物品拾取逻辑：钻石、绿宝石播放装饰音效
        item_name = item_dict.get('newItemName')
        if item_name in ['minecraft:diamond', 'minecraft:emerald']:
            # 调用装饰系统播放meme特效音效
            if hasattr(system, 'ornament_system') and system.ornament_system:
                try:
                    system.ornament_system.play_pickup_meme_effect(player_id, item_name)
                except Exception as e:
                    system.LogError("[_on_try_pickup] 播放装饰音效失败: player={} item={} error={}".format(
                        player_id, item_name, str(e)
                    ))

    def _on_bed_destroyed(self, args):
        """
        床被破坏事件 (预设事件)

        功能:
        1. 更新 system.destroyed_beds 集合
        2. 更新计分板（记录破坏者的床破坏数）
        3. 向被破坏队伍的所有玩家发送Title警告
        4. 广播床破坏消息（带队伍颜色）
        5. 播放床破坏音效和特效（可选）
        6. 检查队伍淘汰条件和胜利条件

        Args:
            args: {'team': str, 'who': str, 'bed_pos': tuple}

        参考: 老项目 BedWarsRunningState.py:1373-1414
        """
        system = self.get_system()
        team = args.get('team')
        destroyer_id = args.get('who')
        bed_pos = args.get('bed_pos')

        system.LogInfo("床被破坏: 队伍={}, 破坏者={}".format(team, destroyer_id))


        # 注意: destroyed_beds的检查和更新已由BedWarsGameSystem.on_bed_destroyed完成
        # 这里不需要重复检查，直接执行后续逻辑
        # === 2. 更新计分板 (记录破坏者分数) ===
        if destroyer_id and destroyer_id != "-1":
            system.scoreboard.on_player_destroy_bed(destroyer_id)


        # === 3. 向所有玩家发送Title和音效 ===
        # 导入TeamType获取队伍颜色
        from ..team.TeamType import team_types, get_team_color_name

        if team and team in team_types:
            team_color_name = get_team_color_name(team)
            team_type = team_types[team]

            # 获取所有玩家ID
            try:
                player_ids = serverApi.GetPlayerList()

                for player_id in player_ids:
                    try:
                        # 获取玩家队伍
                        player_team = system.team_module.get_player_team(player_id)

                        if player_team == team:
                            # === 被破坏队伍的玩家 ===
                            # 发送红色Title警告
                            # 使用BetterPlayerObject.send_title()方法
                            player_obj = system.get_better_player_obj(player_id)
                            if player_obj:
                                player_obj.send_title(
                                    system.format_text(u"{red}\u5e8a\u5df2\u88ab\u7834\u574f\uff01"),  # 床已被破坏！
                                    system.format_text(u"\u6b7b\u4ea1\u540e\u65e0\u6cd5\u91cd\u751f\uff01")  # 死亡后无法重生！
                                )

                            # 播放悲伤音效（凋灵死亡音效）
                            system.NotifyToClient(player_id, 'S2CPlaySoundEvent', {
                                'soundName': 'mob.wither.death',
                                'volume': 1.0,
                                'pitch': 1.0
                            })

                        else:
                            # === 其他队伍的玩家 ===
                            # 发送床破坏通知Title
                            # 使用BetterPlayerObject.send_title()方法
                            player_obj = system.get_better_player_obj(player_id)
                            if player_obj:
                                player_obj.send_title(
                                    system.format_text(
                                        u"\xbb {bold}{team}{white}\u7684\u5e8a{reset}{white} \xab",
                                        team=team_color_name
                                    ),  # » [队伍颜色]的床 «
                                    system.format_text(u"{bold}\u5df2\u88ab\u7834\u574f")  # 已被破坏
                                )

                            # 播放末影龙咆哮音效
                            system.NotifyToClient(player_id, 'S2CPlaySoundEvent', {
                                'soundName': 'mob.enderdragon.growl',
                                'volume': 1.0,
                                'pitch': 1.0
                            })

                    except Exception as e:
                        system.LogError("[_on_bed_destroyed] 处理玩家{}的Title/音效失败: {}".format(
                            player_id, str(e)
                        ))

            except Exception as e:
                system.LogError("[_on_bed_destroyed] 获取玩家列表失败: {}".format(str(e)))

        # === 4. 广播床破坏消息 ===
        if team and team in team_types:
            team_color_name = get_team_color_name(team)

            # 构建破坏消息
            if destroyer_id and destroyer_id != "-1":
                # 有破坏者
                try:
                    comp_name = serverApi.GetEngineCompFactory().CreateName(destroyer_id)
                    destroyer_name = comp_name.GetName()
                except:
                    destroyer_name = destroyer_id

                message = u"{}\u7684\u5e8a\u88ab {} \u7834\u574f\u4e86\uff01".format(team_color_name, destroyer_name)
            else:
                # 无破坏者(例如TNT爆炸)
                message = u"{}\u7684\u5e8a\u88ab\u7834\u574f\u4e86\uff01".format(team_color_name)

            system._broadcast_message(message, u'\xa7c')  # 红色消息
            system.LogInfo("[床破坏] 广播消息: {}".format(message))

        # === 5. 播放床破坏特效 ===
        # 调用装饰系统播放破坏特效（如果玩家装备了特效装饰品）
        if destroyer_id and destroyer_id != "-1" and bed_pos and system.ornament_system:
            try:
                system.ornament_system.play_bed_destroy_effect(destroyer_id, bed_pos, team)
            except Exception as e:
                system.LogError("[_on_bed_destroyed] 播放床破坏特效失败: {}".format(str(e)))

        # === 6. 更新HUD计分板 ===
        # [FIX 2025-11-05] 广播HUD更新事件，更新所有玩家顶部的队伍床状态
        try:
            self._broadcast_hud_update(team)
        except Exception as e:
            system.LogError("[_on_bed_destroyed] 广播HUD更新失败: {}".format(str(e)))

        # === 7. 不检查游戏结束条件 ===
        # [FIX 2025-11-12] 移除错误的_check_game_end调用
        # 原因: 床被破坏不代表队伍被淘汰！队伍玩家还可以继续战斗
        # 正确逻辑: 只有当队伍床被破坏 且 该队伍所有玩家都死亡时，队伍才会被淘汰
        # 游戏结束判定应该在玩家死亡后调用(已在_on_player_death:621实现)，而不是床被破坏后调用
        #
        # 错误示例(2队模式)：
        #   1. 玩家A破坏蓝队床 → 触发_on_bed_destroyed → 调用_check_game_end
        #   2. 此时team_to_player={'RED': [玩家A], 'BLUE': [玩家B]}（蓝队玩家B还活着）
        #   3. 但_check_game_end统计not_empty_teams=['RED']（为什么？需要排查team_to_player逻辑）
        #   4. len(not_empty_teams)=1 ≤ 1 → 判定游戏结束 → 红队获胜 ❌
        #   5. 实际应该：蓝队玩家B还活着，游戏继续
        #
        # 参考: _on_player_death方法已在line 621正确调用_check_game_end
        pass  # 不调用_check_game_end

    def _on_shop_buy(self, args):
        """
        商店购买事件 (预设事件)

        功能:
        1. 获取玩家队伍
        2. 检查购买的物品类型
        3. 如果是队伍升级类物品，应用升级到玩家
        4. 调用 system.team_upgrades[team_id].on_player_respawn(player) 应用所有队伍升级

        Args:
            args: {'player_id': str, 'goods_id': str, 'dimension': int}

        参考: 老项目 BedWarsRunningState.py:1419-1426
        """
        system = self.get_system()
        player_id = args.get('player_id')
        goods_id = args.get('goods_id')
        dimension = args.get('dimension')

        # 检查维度是否匹配
        if dimension != system.dimension:
            system.LogDebug("商店购买事件: 维度不匹配 ({} != {})".format(dimension, system.dimension))
            return

        # 获取玩家队伍
        team = system.team_module.get_player_team(player_id)
        if not team:
            system.LogWarn("商店购买: 玩家{}没有队伍信息".format(player_id))
            return

        system.LogInfo("商店购买: 玩家={}, 商品={}, 队伍={}".format(player_id, goods_id, team))

        # === 应用队伍升级到玩家 ===
        # 注意：老项目调用 team_upgrades[team].on_player_respawn(player)
        # 该方法会遍历所有升级条目并应用到玩家
        # 这确保了玩家获得队伍的所有升级效果（锋利、保护、生命值等）

        if team in system.team_upgrades:
            try:
                upgrade_manager = system.team_upgrades[team]

                # 应用所有队伍升级到玩家
                # 这包括: 锋利、保护、急迫、生命值提升、治疗池等
                upgrade_manager.apply_all_to_player(player_id)

                system.LogInfo("商店购买: 已应用队伍{}的所有升级到玩家{}".format(team, player_id))

            except Exception as e:
                system.LogError("商店购买: 应用队伍升级失败 player={} team={} error={}".format(
                    player_id, team, str(e)
                ))
                import traceback
                system.LogError(traceback.format_exc())
        else:
            system.LogWarn("商店购买: 队伍{}没有升级管理器".format(team))

        # 注意: 护甲升级、剑升级等的记录由ShopPresetDefServer负责
        # 在_process_purchase_item中通过_record_player_sword等方法处理

    # ========== ��Ϸ�׶γ�ʼ�� ==========

    def init_from_config(self):
        """
        �����ó�ʼ����Ϸ�׶���״̬

        ����gaming_states���ô���һϵ��BedWarsSubState
        ÿ����״̬����һ����Ϸ�׶�(����ʯ��II�������Իٵ�)
        """
        system = self.get_system()
        system.LogInfo("BedWarsRunningState.init_from_config")

        if not system.config:
            system.LogError("游戏配置未加载,无法初始化阶段")
            return

        gaming_states = system.config.get("gaming_states", [])
        if not gaming_states:
            system.LogError("gaming_states配置为空")
            return

        system.LogInfo("开始初始化 {} 个游戏阶段".format(len(gaming_states)))

        # 导入阶段状态类
        from phase_states.BedWarsSubState import BedWarsSubState

        # 为每个阶段创建子状态
        index = 0
        for state_config in gaming_states:
            state_name = state_config.get("name", "阶段{}".format(index))
            next_state_name = None

            # 获取下一个阶段的名称(用于HUD显示)
            # 重要: 传递下一个阶段的显示名称(如"钻石II")而不是状态机ID(如"phase_2")
            if index + 1 < len(gaming_states):
                next_state_config = gaming_states[index + 1]
                next_state_name = next_state_config.get("name", "阶段{}".format(index + 1))

            # 创建阶段子状态
            self.add_sub_state(
                "phase_{}".format(index),
                BedWarsSubState,
                config=state_config,
                next_state_name=next_state_name
            )

            system.LogInfo("创建游戏阶段: {} - {}".format(index, state_name))
            index += 1

        # ===== [CRITICAL FIX] 不在这里调用next_sub_state() =====
        # 原因：GamingState.enter()会自动检查sub_states并调用next_sub_state()
        # 如果这里手动调用，会导致：
        #   1. init_from_config()调用next_sub_state() → 进入phase_0
        #   2. GamingState.enter()的最后再次调用next_sub_state() → 进入phase_1 ❌
        # 正确做法：只创建子状态，让GamingState.enter()自动启动第一个
        if gaming_states:
            system.LogInfo("游戏阶段初始化完成,共创建{}个阶段".format(len(gaming_states)))
        else:
            system.LogWarn("没有游戏阶段配置")

    def get_system(self):
        """
        ��ȡBedWarsGameSystemʵ��

        Returns:
            BedWarsGameSystem: ϵͳʵ��
        """
        return self.parent.get_system()

    def _broadcast_hud_update(self, destroyed_team=None):
        """
        [FIX 2025-11-05] 广播HUD更新事件,更新所有玩家顶部的队伍床状态

        Args:
            destroyed_team (str, optional): 刚被破坏的队伍ID
        """
        system = self.get_system()

        try:
            # 构建队伍床状态列表
            from ..team.TeamType import team_types, get_team_color_name

            team_bed_status = []
            for team_id in team_types.keys():
                # 检查队伍是否有玩家
                team_players = system.team_module.get_team_players(team_id)
                if not team_players or len(team_players) == 0:
                    continue

                # 获取队伍颜色名称
                team_color_name = get_team_color_name(team_id)

                # 检查床是否被破坏
                bed_destroyed = team_id in system.destroyed_beds

                # 添加到列表 (格式: "队伍颜色名称 ✓/✗")
                if bed_destroyed:
                    status_text = u"{} \u2717".format(team_color_name)  # ✗
                else:
                    status_text = u"{} \u2713".format(team_color_name)  # ✓

                team_bed_status.append(status_text)

            # 构建HUD事件数据
            hud_event = {
                'type': 'scoreboard',
                'event': 'set_content',
                'value': u'\n'.join(team_bed_status)
            }

            # 通过RoomManagementSystem广播HUD事件
            # 修复参数错误: forward_hud_event需要2个参数(player_id, event_data)
            # player_id=None表示广播给所有玩家
            # 参考: RoomManagementSystem.py:389 forward_hud_event(self, player_id, event_data)
            if hasattr(system, 'room_system') and system.room_system:
                system.room_system.forward_hud_event(None, hud_event)
                system.LogInfo("[_broadcast_hud_update] 已广播HUD更新")
            else:
                system.LogWarn("[_broadcast_hud_update] room_system未初始化,无法广播HUD更新")

        except Exception as e:
            system.LogError("[_broadcast_hud_update] 广播HUD更新失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _check_game_end(self):
        """
        检查游戏是否应该结束

        当只剩一个队伍或没有队伍时,游戏结束
        参考: 老项目 BedWarsRunningState.py:1428-1441

        功能:
        - 统计存活队伍数量
        - 如果只剩一个或零个队伍,设置获胜队伍并切换到结束状态
        """
        system = self.get_system()
        team_to_player = system.team_module.team_to_player
        not_empty_teams = []

        # 统计非空队伍
        for team, players in team_to_player.items():
            if len(players) > 0:
                not_empty_teams.append(team)

        system.LogInfo("BedWarsRunningState._check_game_end: not_empty_teams={}".format(str(not_empty_teams)))

        # 如果只剩1个或0个队伍,游戏结束
        if len(not_empty_teams) <= 1:
            # 设置获胜队伍
            win_team = not_empty_teams[0] if len(not_empty_teams) == 1 else None
            system.scoreboard.set_win_team(win_team)

            # 清空复活队列
            system.respawning.clear()

            # 切换到结束状态
            self.parent.next_sub_state()
            system.LogInfo("游戏结束,获胜队伍: {}".format(win_team))

    # ========== [P0-2/P0-3/P0-8 FIX] 新增辅助方法 ==========

    def _get_presets_by_type(self, preset_type):
        """
        按类型查询预设实例(ECPreset框架适配)

        Args:
            preset_type: str 预设类型,如 "bedwars:generator"

        Returns:
            list: PresetInstance列表
        """
        system = self.get_system()

        # ===== [CRITICAL FIX] 使用ECPreset的API获取预设管理器 =====
        # 注意: context_id必须与RoomManagementSystem中使用的相同("bedwars_room")
        try:
            from ECPresetServerScripts import get_server_mgr
            preset_manager = get_server_mgr("bedwars_room")

            if not preset_manager:
                system.LogDebug("[_get_presets_by_type] 未找到预设管理器: bedwars_room")
                return []

            # 获取所有预设实例
            all_presets = preset_manager.get_all_presets()
            if not all_presets:
                return []

            # 筛选指定类型的预设
            result = []
            for preset_id, preset_instance in all_presets.items():
                if preset_instance.preset_type == preset_type:
                    result.append(preset_instance)

            return result

        except Exception as e:
            system.LogError("[_get_presets_by_type] 获取预设失败: {}".format(str(e)))
            return []

    def _get_presets_by_type_and_config(self, preset_type, config_key, config_value):
        """
        按类型和配置查询预设实例

        Args:
            preset_type: str 预设类型
            config_key: str 配置键
            config_value: 配置值

        Returns:
            list: 符合条件的PresetInstance列表
        """
        instances = self._get_presets_by_type(preset_type)
        return [
            inst for inst in instances
            if inst.config.get(config_key) == config_value
        ]

    def _cleanup_non_player_entities(self):
        """
        清理对局维度中的所有非玩家实体

        目的:
        - 清理可能存在的持久化保存实体(如动物、掉落物等)
        - 避免这些实体干预游戏正常流程

        时机:
        - 在对局进入运行状态时执行
        - 在生成器启动和玩家初始化之前执行

        实现:
        1. 获取对局维度中所有实体
        2. 过滤出非玩家实体
        3. 销毁这些实体
        4. 记录清理统计

        注意:
        - 使用GetEngineActor()获取所有已加载的实体
        - 通过GetPlayerList()排除玩家实体
        - 异常处理确保不影响游戏流程
        """
        system = self.get_system()

        try:
            # 获取当前游戏维度ID
            dimension = system.dimension
            if dimension is None:
                system.LogWarn("[_cleanup_non_player_entities] 游戏维度未初始化,跳过清理")
                return

            # 获取所有已加载的实体(不包含玩家)
            # GetEngineActor()返回: {entityId: {'dimensionId': int, 'identifier': str}, ...}
            all_entities = serverApi.GetEngineActor()

            # 获取所有玩家ID
            player_ids = set(serverApi.GetPlayerList())

            # 统计
            cleaned_count = 0
            skipped_count = 0
            error_count = 0

            # 遍历所有实体
            for entity_id, entity_info in all_entities.items():
                try:
                    # 只处理当前游戏维度的实体
                    if entity_info.get('dimensionId') != dimension:
                        continue

                    # 跳过玩家实体
                    if entity_id in player_ids:
                        skipped_count += 1
                        continue

                    # 销毁非玩家实体（使用System的DestroyEntity方法）
                    if system.DestroyEntity(entity_id):
                        cleaned_count += 1
                        system.LogDebug("[_cleanup_non_player_entities] 已清理实体: id={}, type={}".format(
                            entity_id, entity_info.get('identifier', 'unknown')
                        ))
                    else:
                        error_count += 1
                        system.LogDebug("[_cleanup_non_player_entities] 清理实体失败: id={}".format(entity_id))

                except Exception as e:
                    error_count += 1
                    system.LogDebug("[_cleanup_non_player_entities] 清理实体异常: entity_id={}, error={}".format(
                        entity_id, str(e)
                    ))

            # 记录清理结果
            system.LogInfo(
                "[_cleanup_non_player_entities] 清理完成: "
                "维度={}, 已清理={}, 跳过玩家={}, 失败={}".format(
                    dimension, cleaned_count, skipped_count, error_count
                )
            )

        except Exception as e:
            system.LogError("[_cleanup_non_player_entities] 清理非玩家实体失败: {}".format(str(e)))
            import traceback
            system.LogError(traceback.format_exc())

    def _start_all_generators(self):
        """
        启动所有资源生成器预设

        通过ECPreset框架查询并启动所有Generator预设实例
        """
        system = self.get_system()

        try:
            # 使用辅助方法查询生成器预设
            all_generator_instances = self._get_presets_by_type("bedwars:generator")

            if not all_generator_instances:
                system.LogWarn("[_start_all_generators] 未找到任何生成器预设")
                return

            # 启动所有生成器
            started_count = 0
            for generator_instance in all_generator_instances:
                try:
                    generator_instance.start()
                    started_count += 1
                except Exception as e:
                    system.LogError("[_start_all_generators] 启动生成器失败: instance_id={}, error={}".format(
                        generator_instance.instance_id, str(e)
                    ))

            system.LogInfo("[_start_all_generators] 成功启动 {}/{} 个生成器".format(
                started_count, len(all_generator_instances)
            ))

        except Exception as e:
            system.LogError("[_start_all_generators] 启动生成器失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _initialize_players(self):
        """
        初始化所有玩家

        注意：
        - [FIX 2025-11-06] **需要重新传送玩家到出生点**！
          原因：玩家在运镜期间可能与移动按钮交互导致位置偏移
          虽然玩家在start_game_directly()中被传送过一次，
          但运镜播放完毕后需要确保玩家位置正确
        - 应用装备和升级
        - 发送队伍Title

        参考老项目：
        - 老项目在BedWarsRunningState.on_enter()中调用respawn_player()传送玩家
        - 新项目也需要在进入Running状态时重新传送玩家
        """
        system = self.get_system()

        # 获取队伍模块
        if not hasattr(system, 'team_module') or not system.team_module:
            system.LogError("[_initialize_players] team_module不存在")
            return

        teams_players = system.team_module.get_all_team_players()

        for team_id, player_ids in teams_players.items():
            for player_id in player_ids:
                try:
                    # ===== [FIX 2025-11-06] 运镜完毕后直接调用_respawn_player =====
                    # _respawn_player已经包含：传送、设置游戏模式、取消无敌、装备初始化
                    # 不需要重复这些步骤，避免代码重复
                    # 参考老项目BedWarsRunningState.py:111 直接调用respawn_player
                    system._respawn_player(player_id)

                    # 发送队伍Title
                    self._send_team_title(player_id, team_id)

                    system.LogInfo(u"[_initialize_players] 玩家{}已初始化到队伍{}".format(
                        player_id, team_id
                    ))
                except Exception as e:
                    system.LogError(u"[_initialize_players] 初始化玩家{}失败: {}".format(
                        player_id, str(e)
                    ))
                    import traceback
                    system.LogError(traceback.format_exc())

    def _send_team_title(self, player_id, team_id):
        """
        发送队伍欢迎Title

        Args:
            player_id (str): 玩家ID
            team_id (str): 队伍ID
        """
        system = self.get_system()

        team_names = {
            "RED": u"§c红队",
            "BLUE": u"§9蓝队",
            "YELLOW": u"§e黄队",
            "GREEN": u"§a绿队",
            "AQUA": u"§b青队",
            "WHITE": u"§f白队",
            "PINK": u"§d粉队",
            "GRAY": u"§7灰队",
        }

        team_name = team_names.get(team_id, team_id)

        # 发送Title
        # [FIX 2025-11-04] SetNotifyMsg不支持给单个玩家发送Title
        # 正确方式：使用title命令
        try:
            comp_factory = serverApi.GetEngineCompFactory()
            command_comp = comp_factory.CreateCommand(serverApi.GetLevelId())

            # 使用玩家选择器发送Title
            player_selector = player_id

            # 设置Title显示时间
            command_comp.SetCommand("title {} times {} {} {}".format(
                player_selector, 10, 60, 10  # 淡入0.5秒, 保持3秒, 淡出0.5秒
            ))

            # 设置副标题
            command_comp.SetCommand("title {} subtitle {}".format(
                player_selector,
                u"§7你在 {} §7队伍".format(team_name)
            ))

            # 设置主标题
            command_comp.SetCommand("title {} title {}".format(
                player_selector,
                u"§l游戏开始!"
            ))
        except Exception as e:
            system.LogError("[_send_team_title] 发送Title失败: player_id={}, error={}".format(
                player_id, str(e)
            ))

    def _initialize_hud_system(self):
        """
        初始化HUD系统

        通过RoomManagementSystem转发HUD清空指令,准备显示游戏信息

        说明:
        - 新架构统一由RoomManagementSystem发送HUD事件
        - BedWarsGameSystem通过room_system.forward_hud_event()转发
        - HUDSystem只监听RoomManagementSystem,避免多系统监听

        参考: 老项目 BedWarsRunningState.py:115-118
        """
        system = self.get_system()

        try:
            # 确保room_system引用存在
            if not system.room_system:
                system._initialize_room_system_reference()

            if not system.room_system:
                system.LogError("[_initialize_hud_system] RoomManagementSystem引用未找到,无法发送HUD事件")
                return

            # 广播HUD清空事件(清空顶部队伍栏)
            system.room_system.forward_hud_event(None, {
                'type': 'stack_msg_top',
                'event': 'clear_all'
            })

            # 广播HUD清空事件(清空底部信息栏)
            system.room_system.forward_hud_event(None, {
                'type': 'stack_msg_bottom',
                'event': 'clear_all'
            })

            system.LogInfo("[_initialize_hud_system] HUD系统已清空，准备显示游戏信息")

        except Exception as e:
            system.LogError("[_initialize_hud_system] 初始化HUD失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _on_tick_hud(self):
        """
        HUD定时更新逻辑(每秒1次)

        功能:
        - 更新顶部队伍状态栏(显示各队伍人数和床位状态)
        - 更新底部信息栏(显示游戏阶段倒计时、击杀数、床破坏数)
        - 区分存活玩家和观战者的显示

        参考: 老项目 BedWarsRunningState.py:1105-1196
        """
        now = time.time()
        if now < self.next_tick_hud:
            return

        self.next_tick_hud = now + 1  # 1秒后再次更新
        system = self.get_system()

        # 确保room_system引用存在
        if not system.room_system:
            system._initialize_room_system_reference()

        if not system.room_system:
            return  # 如果仍然无法获取,静默返回

        try:
            # 导入TeamType
            from ..team.TeamType import team_types

            # 检查team_module是否存在
            if not system.team_module:
                system.LogError("[_on_tick_hud] system.team_module 为 None!")
                return

            # 获取队伍分配数据
            team_to_player = system.team_module.team_to_player

            # 获取当前子状态(用于显示倒计时)
            from .phase_states.BedWarsSubState import BedWarsSubState
            sub_state = self.current_sub_state

            # 构建倒计时事件
            if sub_state is not None and isinstance(sub_state, BedWarsSubState):
                timer_event = {
                    'event': 'add_or_set',
                    'key': 'timer',
                    'value': u"{icon} {state} {time}".format(
                        icon=system.format_text(u"{icon-ec-time}"),
                        state=unicode(sub_state.next_state_name),
                        time=sub_state.get_formatted_time_left()
                    ),
                }
            else:
                timer_event = {
                    'event': 'add_or_set',
                    'key': 'timer',
                    'value': u"Timer"
                }

            # 遍历所有维度内玩家，更新各自的HUD
            player_ids = serverApi.GetPlayerList()
            for player_id in player_ids:
                try:
                    # 获取玩家队伍
                    team = system.team_module.get_player_team(player_id)

                    # === 构建顶部队伍状态栏 ===
                    # 重要: 遍历游戏模式中定义的所有队伍,而不是只遍历有玩家的队伍
                    # 这样即使某些队伍没有玩家,也会显示在HUD上(显示0人)
                    events_top = []
                    all_teams = system.config.get('teams', ['RED', 'BLUE', 'GREEN', 'YELLOW'])
                    for t in all_teams:
                        # 判断该队伍的床是否被破坏
                        destroyed = t in system.destroyed_beds

                        # 获取队伍的玩家数量(如果队伍不存在则为0)
                        players_in_team = team_to_player.get(t, [])
                        player_count = len(players_in_team)

                        # 获取队伍的图标(根据床状态显示不同颜色)
                        team_icon = team_types[t].get_text_icon(destroyed)

                        events_top.append({
                            'event': 'add_or_set',
                            'key': 'team_' + t,
                            'value': u"{icon} {color}{count}".format(
                                icon=system.format_text(team_icon),
                                color=u"\xa77" if destroyed else u"\xa7f",  # 灰色或白色
                                count=unicode(player_count)
                            ),
                            'border': (team == t)  # 当前玩家的队伍显示边框
                        })

                    # 发送顶部HUD更新事件(通过RoomManagementSystem转发)
                    system.room_system.forward_hud_event(player_id, {
                        'type': 'stack_msg_top',
                        'events': events_top
                    })

                    # === 构建底部信息栏 ===
                    events_bottom = [timer_event]

                    if team is not None:
                        # 存活玩家：显示击杀数、床破坏数和资源数量
                        player_score = system.scoreboard.get_player_score(player_id)

                        # 获取玩家资源数量
                        resource_counts = self._get_player_resources(player_id)

                        # 显示资源（铁锭、金锭、钻石、绿宝石）
                        # 只显示数量大于0的资源
                        if resource_counts['iron'] > 0:
                            events_bottom.append({
                                'event': 'add_or_set',
                                'key': 'resource_iron',
                                'value': u"{icon} {count}".format(
                                    icon=system.format_text(u"{icon-ec-iron}"),
                                    count=unicode(resource_counts['iron'])
                                ),
                            })
                        else:
                            events_bottom.append({
                                'event': 'remove',
                                'key': 'resource_iron'
                            })

                        if resource_counts['gold'] > 0:
                            events_bottom.append({
                                'event': 'add_or_set',
                                'key': 'resource_gold',
                                'value': u"{icon} {count}".format(
                                    icon=system.format_text(u"{icon-ec-gold}"),
                                    count=unicode(resource_counts['gold'])
                                ),
                            })
                        else:
                            events_bottom.append({
                                'event': 'remove',
                                'key': 'resource_gold'
                            })

                        if resource_counts['diamond'] > 0:
                            events_bottom.append({
                                'event': 'add_or_set',
                                'key': 'resource_diamond',
                                'value': u"{icon} {count}".format(
                                    icon=system.format_text(u"{icon-ec-diamond}"),
                                    count=unicode(resource_counts['diamond'])
                                ),
                            })
                        else:
                            events_bottom.append({
                                'event': 'remove',
                                'key': 'resource_diamond'
                            })

                        if resource_counts['emerald'] > 0:
                            events_bottom.append({
                                'event': 'add_or_set',
                                'key': 'resource_emerald',
                                'value': u"{icon} {count}".format(
                                    icon=system.format_text(u"{icon-ec-emerald}"),
                                    count=unicode(resource_counts['emerald'])
                                ),
                            })
                        else:
                            events_bottom.append({
                                'event': 'remove',
                                'key': 'resource_emerald'
                            })

                        # 显示击杀数和床破坏数
                        events_bottom.append({
                            'event': 'add_or_set',
                            'key': 'kill',
                            'value': u"{icon} {count}".format(
                                icon=system.format_text(u"{icon-ec-sword0}"),
                                count=unicode(player_score.kills)
                            ),
                        })
                        events_bottom.append({
                            'event': 'add_or_set',
                            'key': 'destroy',
                            'value': u"{icon} {count}".format(
                                icon=system.format_text(u"{icon-ec-crystal-destroy}"),
                                count=unicode(player_score.destroys)
                            ),
                        })
                    else:
                        # 观战者：移除击杀和破坏数，显示观战提示
                        events_bottom.append({
                            'event': 'remove',
                            'key': 'kill'
                        })
                        events_bottom.append({
                            'event': 'remove',
                            'key': 'destroy'
                        })
                        events_bottom.append({
                            'event': 'add_or_set',
                            'key': 'team',  # 修复: 老项目使用'team'作为key
                            'value': u"\xa77当前为观战者，本局结束后将自动开始下一局"
                        })

                    # 发送底部HUD更新事件(通过RoomManagementSystem转发)
                    system.room_system.forward_hud_event(player_id, {
                        'type': 'stack_msg_bottom',
                        'events': events_bottom
                    })

                except Exception as e:
                    system.LogError("[_on_tick_hud] 更新玩家{}的HUD失败: {}".format(
                        player_id, str(e)
                    ))

        except Exception as e:
            system.LogError("[_on_tick_hud] HUD更新失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    # ========== 辅助方法 (Agent 12) ==========

    def _get_player_resources(self, player_id):
        """
        获取玩家当前持有的资源数量

        功能:
        - 遍历玩家背包，统计铁锭、金锭、钻石、绿宝石的数量
        - 用于HUD资源显示

        Args:
            player_id (str): 玩家ID

        Returns:
            dict: 资源数量字典 {'iron': int, 'gold': int, 'diamond': int, 'emerald': int}
        """
        resource_counts = {
            'iron': 0,
            'gold': 0,
            'diamond': 0,
            'emerald': 0
        }

        try:
            # 获取玩家背包物品
            comp_item = serverApi.GetEngineCompFactory().CreateItem(player_id)
            inv_items = comp_item.GetPlayerAllItems(
                serverApi.GetMinecraftEnum().ItemPosType.INVENTORY
            )

            # 遍历背包，统计资源
            for item_dict in inv_items:
                if not item_dict or item_dict.get('count', 0) <= 0:
                    continue

                item_name = item_dict.get('newItemName', '')
                item_count = item_dict.get('count', 0)

                # 铁锭
                if item_name == 'minecraft:iron_ingot':
                    resource_counts['iron'] += item_count
                # 金锭
                elif item_name == 'minecraft:gold_ingot':
                    resource_counts['gold'] += item_count
                # 钻石
                elif item_name == 'minecraft:diamond':
                    resource_counts['diamond'] += item_count
                # 绿宝石
                elif item_name == 'minecraft:emerald':
                    resource_counts['emerald'] += item_count

        except Exception as e:
            system = self.get_system()
            system.LogError("[_get_player_resources] 获取玩家{}资源失败: {}".format(
                player_id, str(e)
            ))

        return resource_counts

    def _is_position_in_backup_range(self, pos, system):
        """
        检查位置是否在地图备份范围内

        Args:
            pos (tuple): 方块位置 (x, y, z)
            system: BedWarsGameSystem实例

        Returns:
            bool: 是否在范围内
        """
        # 获取RoomManagementSystem
        room_system = system.room_system
        if not room_system:
            return True  # 如果没有房间系统,默认允许

        # 获取当前地图ID
        current_stage = room_system.current_stage_config
        if not current_stage:
            return True  # 如果没有地图配置,默认允许

        map_id = current_stage.get('id')
        if not map_id:
            return True

        # 获取备份范围
        backup_range = room_system.get_map_backup_range(map_id)
        if not backup_range:
            return True  # 如果没有备份范围,默认允许

        min_pos, max_pos = backup_range
        x, y, z = pos

        # 检查是否在范围内
        in_range = (
            min_pos[0] <= x <= max_pos[0] and
            min_pos[1] <= y <= max_pos[1] and
            min_pos[2] <= z <= max_pos[2]
        )

        return in_range

    def _is_map_backup_in_progress(self, system):
        """
        检查地图备份是否正在进行中

        Args:
            system: BedWarsGameSystem实例

        Returns:
            bool: 是否正在备份
        """
        # 获取RoomManagementSystem
        room_system = system.room_system
        if not room_system:
            return False

        # 获取当前维度的备份管理器
        dimension = system.dimension
        if dimension not in room_system.map_backup_handlers:
            return False

        backup_handler = room_system.map_backup_handlers[dimension]
        if not backup_handler:
            return False

        # 检查是否正在备份
        # DimensionBackupHandler.backup.is_restoring 标识是否正在还原
        return hasattr(backup_handler, 'backup') and \
               hasattr(backup_handler.backup, 'is_restoring') and \
               backup_handler.backup.is_restoring

    def _auto_ignite_tnt(self, pos, dimension, system, player_id):
        """
        自动点燃TNT方块

        Args:
            pos (tuple): TNT位置 (x, y, z)
            dimension (int): 维度ID
            system: BedWarsGameSystem实例
            player_id (str): 放置者ID
        """
        import time

        try:
            # 延迟1tick后点燃TNT
            def ignite():
                try:
                    # 获取方块信息
                    comp_block = serverApi.GetEngineCompFactory().CreateBlockInfo(serverApi.GetLevelId())
                    block_info = comp_block.GetBlockNew(pos, dimension)

                    if block_info and block_info.get('name') == 'minecraft:tnt':
                        # 移除TNT方块
                        comp_block.SetBlockNew(pos, {'name': 'minecraft:air', 'aux': 0}, 0, dimension)

                        # 生成自定义TNT实体（替代CreateEngineTntEntity）
                        comp_game = serverApi.GetEngineCompFactory().CreateGame(serverApi.GetLevelId())
                        entity_id = comp_game.SpawnEntity(
                            'ecbedwars:tnt',  # 使用自定义实体
                            (pos[0] + 0.5, pos[1], pos[2] + 0.5),
                            dimension
                        )

                        if entity_id:
                            # 获取玩家队伍
                            team = system.team_module.get_player_team(player_id) if hasattr(system, 'team_module') else None

                            # 注册到PropTNTHandler的tracking系统
                            props_system = serverApi.GetSystem(system.namespace, "PropsManagementSystem")
                            if props_system and "tnt" in props_system.prop_handlers:
                                tnt_handler = props_system.prop_handlers["tnt"]
                                tnt_handler.tnt_entities[entity_id] = {
                                    'spawn_time': time.time(),
                                    'owner_id': player_id,
                                    'team': team,
                                    'pos': (pos[0] + 0.5, pos[1], pos[2] + 0.5),
                                    'dimension': dimension
                                }
                                system.LogInfo("[_auto_ignite_tnt] TNT已注册到PropTNTHandler: entity_id={}".format(entity_id))
                            else:
                                system.LogWarn("[_auto_ignite_tnt] PropsManagementSystem或TNT处理器未找到")

                            system.LogInfo("[_auto_ignite_tnt] TNT已点燃 pos={} entity_id={} owner={}".format(
                                pos, entity_id, player_id
                            ))
                        else:
                            system.LogError("[_auto_ignite_tnt] 创建TNT实体失败 pos={}".format(pos))

                except Exception as e:
                    system.LogError("[_auto_ignite_tnt] 点燃TNT失败: pos={} error={}".format(
                        pos, str(e)
                    ))
                    import traceback
                    print(traceback.format_exc())

            # 延迟1tick执行
            system.add_timer(0.05, ignite)  # 0.05秒 = 1tick

        except Exception as e:
            system.LogError("[_auto_ignite_tnt] 设置定时器失败: {}".format(str(e)))
