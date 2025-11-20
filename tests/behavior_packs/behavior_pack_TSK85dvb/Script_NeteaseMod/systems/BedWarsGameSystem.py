# -*- coding: utf-8 -*-
"""
BedWarsGameSystem - 起床战争游戏逻辑系统(服务端)

功能:
- 管理起床战争游戏逻辑
- 协调队伍系统、复活系统、装备系统等子系统
- 处理床破坏、玩家淘汰、游戏胜利判定
- 状态机管理(starting → running → ending)

原文件: Parts/ECBedWars/ECBedWarsPart.py
重构为: systems/BedWarsGameSystem.py
"""

import mod.server.extraServerApi as serverApi
import time
from .GamingStateSystem import GamingStateSystem


class BedWarsGameSystem(GamingStateSystem):
    """
    起床战争游戏逻辑系统(ServerSystem + 状态机)

    核心职责:
    - 继承GamingStateSystem,获得状态机能力
    - 管理游戏状态(starting → running → ending)
    - 处理床破坏、玩家死亡、淘汰、复活逻辑
    - 协调RoomManagementSystem和子模块
    - 游戏胜利判定

    重构说明:
    - 原ECBedWarsPart继承GamingStatePart
    - 现改为继承GamingStateSystem
    - 保留状态机架构,状态类随后迁移
    """

    def __init__(self, namespace, systemName):
        """
        初始化起床战争游戏系统

        Args:
            namespace: 命名空间
            systemName: 系统名称
        """
        super(BedWarsGameSystem, self).__init__(namespace, systemName)

        # ========== 游戏配置 ==========
        self.dimension = None  # 游戏维度ID
        self.mode = None  # 游戏模式(team2/team4等)
        self.config = None  # 模式配置
        self.stage_config = None  # 地图配置

        # ========== 队伍系统 ==========
        self.team_module = None  # TeamModule实例
        self.team_upgrades = {}  # 队伍ID -> TeamUpgradeManager
        self.team_healing_pools = {}  # 队伍ID -> TeamHealingPool
        self.team_trap_managers = {}  # 队伍ID -> TeamTrapManager

        # ========== 游戏状态数据 ==========
        self.destroyed_beds = []  # 被摧毁的床列表 [team_id, ...]
        self.eliminated_players = []  # 被淘汰的玩家列表 [player_id, ...]
        self.respawning = {}  # 复活中的玩家 {player_id: respawn_time}
        self.respawn_contents = {}  # 复活时的物品 {player_id: {slot: item_dict}}

        # ========== 玩家装备记录 ==========
        self.player_armor_record = {}  # 玩家护具记录 {player_id: {'leggings': name, 'boots': name}}
        self.player_sword_record = {}  # 玩家武器记录 {player_id: sword_name}

        # ========== 方块管理 ==========
        self.placed_blocks = []  # 玩家放置的方块列表 [(x, y, z), ...]
        self.inited_chests = []  # 已初始化的箱子列表 [(x, y, z), ...]

        # ========== 攻击记录系统 ==========
        self.last_attacker_records = {}  # 攻击记录 {player_id: {'attacker_id': str, 'attack_time': float}}

        # ========== 陷阱免疫系统 ==========
        self.trap_immune_players = {}  # 陷阱免疫 {player_id: immunity_end_time}

        # ========== 虚空检测系统 ==========
        self.next_void_check_time = 0  # 下次虚空检测时间

        # ========== 计分板系统 ==========
        self.scoreboard = None  # BedWarsScoreboard实例

        # ========== 标点系统 ==========
        self.waypoint_manager = None  # WaypointManager实例

        # ========== 跨系统引用 ==========
        self.room_system = None  # RoomManagementSystem实例引用

        # ========== 饰品系统 ==========
        self.ornament_system = None  # OrnamentSystem实例
        self.bed_destroy_effect_system = None  # BedDestroyEffectSystem实例

        # ========== 标记Create是否已调用 ==========
        self._create_called = False

        print("[INFO] [BedWarsGameSystem] 初始化完成")

        # ========== 重要：手动调用Create() ==========
        # 说明：网易引擎设计上只自动触发Destroy()，不自动触发Create()
        # 因此需要在__init__中手动调用Create()完成系统初始化
        print("[BedWarsGameSystem] 手动调用Create()完成系统初始化")
        self.Create()

    # ========== ServerSystem生命周期 ==========

    def Create(self):
        """系统创建时调用"""
        self.LogInfo("BedWarsGameSystem.Create")

        # 调用父类Create(GamingStateSystem)
        super(BedWarsGameSystem, self).Create()

        # 获取RoomManagementSystem引用
        self._initialize_room_system_reference()

        # 注册观战系统事件
        self.register_spectator_events()

        # [FIX 2025-11-06] 初始化饰品系统（从_initialize_subsystems移至Create）
        # 原因：玩家在大厅等待阶段就需要使用装扮商店，但OrnamentSystem之前只在游戏开始时初始化
        # 解决：将初始化提前到Create阶段，确保整个系统生命周期都可用
        from Script_NeteaseMod.systems.ornament_system.OrnamentSystem import OrnamentSystem
        self.ornament_system = OrnamentSystem(self)
        self.ornament_system.initialize()
        self.LogInfo("饰品系统初始化完成")

        print("[INFO] [BedWarsGameSystem] Create完成")

    def Destroy(self):
        """系统销毁时调用"""
        self.LogInfo("BedWarsGameSystem.Destroy")

        # 清理子系统
        self._cleanup_subsystems()

        # 调用父类Destroy
        super(BedWarsGameSystem, self).Destroy()

        print("[INFO] [BedWarsGameSystem] Destroy完成")

    def Update(self):
        """系统每帧更新"""
        # 调用父类Update(驱动状态机)
        super(BedWarsGameSystem, self).Update()

        # 更新游戏逻辑
        self._update_game_logic()

        # 更新饰品系统(主要用于特效定时器)
        if self.ornament_system:
            self.ornament_system.update()

        # 更新破坏床特效系统(主要用于定时器)
        if self.bed_destroy_effect_system:
            self.bed_destroy_effect_system.on_tick()

    # ========== 游戏启动接口 ==========

    def start_game_directly(self, dimension, mode, stage_config):
        """
        启动游戏(由RoomManagementSystem直接调用)

        Args:
            dimension (int): 游戏维度ID
            mode (str): 游戏模式(team2/team4)
            stage_config (dict): 地图配置
        """
        self.LogInfo("start_game_directly dimension={} mode={}".format(dimension, mode))

        # 检查是否已经在运行
        if hasattr(self, 'root_state') and self.root_state is not None:
            current_state = getattr(self.root_state, 'current_sub_state_name', None)
            if current_state in ['starting', 'running']:
                self.LogWarn("BedWars已在运行中(状态: {}), 忽略重复启动".format(current_state))
                return

        # 重置游戏数据
        self._reset_game_vars(dimension, mode, stage_config)

        # 创建状态机
        self._create_game_state_machine()

        # 启动状态机
        self.root_state.next_sub_state()

        print("[INFO] [BedWarsGameSystem] 游戏已启动 dimension={} mode={}".format(dimension, mode))

    def _reset_game_vars(self, dimension, mode, stage_config):
        """
        重置游戏变量

        Args:
            dimension (int): 游戏维度ID
            mode (str): 游戏模式
            stage_config (dict): 地图配置
        """
        # 清理旧状态机
        if hasattr(self, 'root_state') and self.root_state is not None:
            try:
                if hasattr(self.root_state, 'stop'):
                    self.root_state.stop()
                self.root_state = None
            except Exception as e:
                self.LogError("清理旧状态机失败: {}".format(str(e)))

        # 设置基本配置
        self.dimension = dimension
        self.mode = mode

        # 加载游戏模式配置
        self._load_game_mode_config(mode)
        self.stage_config = stage_config

        # 重置游戏状态数据
        self.destroyed_beds = []
        self.eliminated_players = []
        self.respawning = {}
        self.respawn_contents = {}
        self.player_armor_record = {}
        self.player_sword_record = {}
        self.placed_blocks = []
        self.inited_chests = []
        self.last_attacker_records = {}
        self.trap_immune_players = {}

        # 初始化子系统
        self._initialize_subsystems()

        self.LogInfo("游戏变量已重置")

    def _initialize_subsystems(self):
        """初始化子系统"""
        # 初始化队伍模块 (每次游戏都重新创建以清空旧数据)
        if self.team_module is not None:
            self.team_module.cleanup()
        from team.TeamModule import TeamModule
        self.team_module = TeamModule(self)
        self.LogInfo("队伍模块初始化完成")

        # 初始化计分板
        from scoreboard.BedWarsScoreboard import BedWarsScoreboard
        self.scoreboard = BedWarsScoreboard(self)
        self.LogInfo("计分板初始化完成")

        # [FIX 2025-11-06] OrnamentSystem初始化已移至Create方法
        # 不在这里重复初始化，避免重复创建子管理器

        # [P0-1 FIX] 不需要广播OrnamentSystemReady事件
        # 商店预设会监听BedWarsRunning事件来应用NPC皮肤
        # 参考老项目: BedWarsShopPart监听BedWarsRunning事件(第136行)

        # 初始化破坏床特效系统
        from Script_NeteaseMod.systems.bed_destroy.BedDestroyEffectSystem import BedDestroyEffectSystem
        self.bed_destroy_effect_system = BedDestroyEffectSystem(self)
        self.bed_destroy_effect_system.initialize()
        self.LogInfo("破坏床特效系统初始化完成")

        # 初始化队伍升级管理器
        self.team_upgrades = {}
        self.team_healing_pools = {}
        self.team_trap_managers = {}

        # 初始化标点管理器
        from waypoint.WaypointManager import WaypointManager
        self.waypoint_manager = WaypointManager(self)
        self.waypoint_manager.initialize()
        self.LogInfo("标点管理器初始化完成")

    def _cleanup_subsystems(self):
        """清理子系统"""
        # 清理队伍模块
        if self.team_module:
            self.team_module.cleanup()
            self.team_module = None

        # 清理计分板
        if self.scoreboard:
            self.scoreboard = None

        # 清理饰品系统
        if self.ornament_system:
            self.ornament_system.cleanup()
            self.ornament_system = None

        # 清理破坏床特效系统
        if hasattr(self, 'bed_destroy_effect_system') and self.bed_destroy_effect_system:
            self.bed_destroy_effect_system.cleanup()
            self.bed_destroy_effect_system = None

        # 清理标点管理器
        if self.waypoint_manager:
            self.waypoint_manager.cleanup()
            self.waypoint_manager = None

        # 清理队伍升级
        self.team_upgrades = {}
        self.team_healing_pools = {}
        self.team_trap_managers = {}

    def _create_game_state_machine(self):
        """创建游戏状态机"""
        from state.RootGamingState import RootGamingState
        from bedwars_states.BedWarsStartingState import BedWarsStartingState
        from bedwars_states.BedWarsRunningState import BedWarsRunningState
        from bedwars_states.BedWarsEndingState import BedWarsEndingState

        # 创建根状态
        self.root_state = RootGamingState(self)

        # 添加子状态
        self.root_state.add_sub_state("starting", BedWarsStartingState)
        self.root_state.add_sub_state("running", BedWarsRunningState)
        self.root_state.add_sub_state("ending", BedWarsEndingState)

        # 状态机结束回调
        def on_no_such_next_sub_state():
            self._notify_game_end_to_room()

        self.root_state.with_no_such_next_sub_state(on_no_such_next_sub_state)

        self.LogInfo("游戏状态机已创建")

    # ========== 游戏结束通知 ==========

    def _notify_game_end_to_room(self):
        """
        通知RoomManagementSystem游戏结束

        [FIX 2025-11-07] 修复胜利结算流程:
        - 调用room_system.end_game()完成清理
        - 然后推进RoomManagementSystem的状态机到broadcast_score状态
        """
        if self.room_system:
            winning_team = getattr(self, '_winning_team', None)
            # 1. 清理游戏状态
            self.room_system.end_game(winning_team)
            self.LogInfo("已通知RoomSystem游戏结束 winning_team={}".format(winning_team))

            # 2. 推进状态机到broadcast_score
            if self.room_system.root_state:
                self.room_system.root_state.next_sub_state()
                self.LogInfo("已推进RoomSystem状态机到broadcast_score")
            else:
                self.LogError("room_system.root_state不存在,无法推进状态机")
        else:
            self.LogError("room_system引用未初始化")

    # ========== 床破坏处理 ==========

    def on_bed_destroyed(self, team_id, destroyer_id, bed_pos=None):
        """
        床被破坏事件处理

        Args:
            team_id (str): 被破坏的床所属队伍
            destroyer_id (str): 破坏者玩家ID
            bed_pos (tuple, optional): 床的位置 (x, y, z)
        """
        if team_id in self.destroyed_beds:
            self.LogWarn("队伍{}的床已经被破坏过了".format(team_id))
            return

        self.destroyed_beds.append(team_id)

        # [FIX 2025-11-07] 向所有玩家发送Title通知
        # 参考: BedWarsRunningState.py:806-869
        # 被破坏队伍: 红色警告Title + 凋灵死亡音效
        # 其他队伍: 床破坏通知Title + 末影龙咆哮音效
        self._send_bed_destroyed_title_notifications(team_id)

        # 广播消息
        self._broadcast_bed_destroyed_message(team_id, destroyer_id)

        # 播放床破坏特效
        if self.ornament_system and bed_pos:
            self.ornament_system.play_bed_destroy_effect(destroyer_id, bed_pos, team_id)

        # [FIX 2025-11-05] 广播PresetBedDestroyed事件到状态机
        # 用于触发BedWarsRunningState的_on_bed_destroyed方法,发送TITLE提示、更新HUD等
        self.broadcast_preset_event("PresetBedDestroyed", {
            'team': team_id,
            'who': destroyer_id,
            'bed_pos': bed_pos
        })

        self.LogInfo("队伍{}的床已被破坏 by {}，已广播PresetBedDestroyed事件".format(team_id, destroyer_id))

        # [FIX 2025-11-12] 直接调用状态机的_on_bed_destroyed方法
        # 原因: EventBus事件只在预设之间传递，状态机需要直接调用
        # 用途: 更新计分板、触发HUD更新
        if hasattr(self, "root_state") and self.root_state:
            current_state = self.root_state.current_sub_state
            if current_state and hasattr(current_state, "_on_bed_destroyed"):
                try:
                    current_state._on_bed_destroyed({
                        "team": team_id,
                        "who": destroyer_id,
                        "bed_pos": bed_pos
                    })
                    self.LogInfo("[FIX] 已调用状态机的_on_bed_destroyed方法")
                except Exception as e:
                    self.LogError("[FIX] 调用状态机_on_bed_destroyed失败: {}".format(str(e)))
                    import traceback
                    traceback.print_exc()

    def _broadcast_bed_destroyed_message(self, team_id, destroyer_id):
        """广播床被破坏消息"""
        team_name = self.team_module.get_colored_team_name(team_id) if self.team_module else team_id
        destroyer_name = self._get_player_name(destroyer_id)

        message = u"{}的床被{}破坏了!".format(team_name, destroyer_name)
        self._broadcast_message(message, u'\xa7c')

    def _send_bed_destroyed_title_notifications(self, team_id):
        """
        向所有玩家发送床破坏Title通知

        参考: BedWarsRunningState.py:806-869 的实现
        100%还原老项目的Title通知功能

        被破坏队伍的玩家:
        - Title: §c床已被破坏！
        - Subtitle: 死亡后无法重生！
        - 音效: mob.wither.death (凋灵死亡音效)

        其他队伍的玩家:
        - Title: » [队伍颜色]的床 «
        - Subtitle: 已被破坏
        - 音效: mob.enderdragon.growl (末影龙咆哮音效)

        Args:
            team_id (str): 被破坏的床所属队伍ID
        """
        try:
            # 导入TeamType获取队伍颜色
            from Script_NeteaseMod.systems.team.TeamType import team_types, get_team_color_name

            if not team_id or team_id not in team_types:
                self.LogWarn("[_send_bed_destroyed_title_notifications] 无效的队伍ID: {}".format(team_id))
                return

            team_color_name = get_team_color_name(team_id)

            # 获取所有玩家ID
            player_ids = serverApi.GetPlayerList()
            if not player_ids:
                self.LogWarn("[_send_bed_destroyed_title_notifications] 没有在线玩家")
                return

            self.LogInfo("[_send_bed_destroyed_title_notifications] 向{}个玩家发送床破坏Title通知".format(
                len(player_ids)
            ))

            # 遍历所有玩家,根据队伍发送不同的Title
            for player_id in player_ids:
                try:
                    # 获取玩家队伍
                    if not self.team_module:
                        continue

                    player_team = self.team_module.get_player_team(player_id)
                    if not player_team:
                        continue

                    # 获取BetterPlayerObject
                    player_obj = self.get_better_player_obj(player_id)
                    if not player_obj:
                        self.LogWarn("[_send_bed_destroyed_title_notifications] 无法获取玩家对象: {}".format(player_id))
                        continue

                    if player_team == team_id:
                        # ===  破坏队伍的玩家 ===
                        # 发送红色Title警告
                        player_obj.send_title(
                            self.format_text(u"{red}床已被破坏！"),  # §c床已被破坏！
                            self.format_text(u"死亡后无法重生！")   # 死亡后无法重生！
                        )

                        # [FIX 2025-11-07] 播放悲伤音效（凋灵死亡音效）
                        # 使用BetterPlayerObject.play_sound()方法，通过/playsound命令播放
                        try:
                            # 获取玩家位置
                            pos_comp = serverApi.GetEngineCompFactory().CreatePos(player_id)
                            player_pos = pos_comp.GetPos()
                            # 播放音效
                            player_obj.play_sound('mob.wither.death', player_pos, 1.0, 1.0)
                            self.LogInfo("[床破坏音效] 已向被破坏队伍玩家播放凋灵死亡音效: {}".format(player_id))
                        except Exception as e:
                            self.LogError("[床破坏音效] 播放凋灵死亡音效失败: {}".format(str(e)))

                        self.LogInfo("[床破坏Title] 已通知被破坏队伍玩家: {} (队伍: {})".format(player_id, player_team))

                    else:
                        # === 其他队伍的玩家 ===
                        # 发送床破坏通知Title
                        player_obj.send_title(
                            self.format_text(
                                u"» {bold}{team}{white}的床{reset}{white} «",
                                team=team_color_name
                            ),  # » [队伍颜色]的床 «
                            self.format_text(u"{bold}已被破坏")  # 已被破坏
                        )

                        # [FIX 2025-11-07] 播放末影龙咆哮音效
                        # 使用BetterPlayerObject.play_sound()方法，通过/playsound命令播放
                        try:
                            # 获取玩家位置
                            pos_comp = serverApi.GetEngineCompFactory().CreatePos(player_id)
                            player_pos = pos_comp.GetPos()
                            # 播放音效
                            player_obj.play_sound('mob.enderdragon.growl', player_pos, 1.0, 1.0)
                            self.LogInfo("[床破坏音效] 已向其他队伍玩家播放末影龙咆哮音效: {}".format(player_id))
                        except Exception as e:
                            self.LogError("[床破坏音效] 播放末影龙咆哮音效失败: {}".format(str(e)))

                        self.LogInfo("[床破坏Title] 已通知其他队伍玩家: {} (队伍: {})".format(player_id, player_team))

                except Exception as e:
                    self.LogError("[_send_bed_destroyed_title_notifications] 处理玩家{}失败: {}".format(
                        player_id, str(e)
                    ))
                    import traceback
                    traceback.print_exc()

            self.LogInfo("[_send_bed_destroyed_title_notifications] 床破坏Title通知发送完成")

        except Exception as e:
            self.LogError("[_send_bed_destroyed_title_notifications] 发送床破坏Title通知失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _broadcast_death_message(self, victim_id, attacker_id, victim_team_id, is_final_kill, damage_cause):
        """
        广播玩家死亡消息

        消息格式:
        - 有击杀者(PVP): "§c玩家A §7被 §a玩家B §7击杀了"
        - 终结击杀: "§c玩家A §7被 §a玩家B §7终结了！§c§l FINAL KILL!"
        - 无击杀者(坠落/虚空等): "§c玩家A §7坠落死亡" / "§c玩家A §7掉入虚空"

        Args:
            victim_id (str): 被击杀玩家ID
            attacker_id (str): 击杀者ID（可能为None）
            victim_team_id (str): 被击杀玩家队伍ID
            is_final_kill (bool): 是否为终结击杀
            damage_cause (str): 伤害原因（可选）
        """
        # [FIX 2025-11-04] 修复Python 2.7导入路径问题
        from Script_NeteaseMod.systems.team.TeamType import team_types

        # 获取被击杀玩家名称和队伍颜色
        victim_name = self._get_player_name(victim_id)
        victim_team = team_types.get(victim_team_id)
        victim_colored_name = u"{}{}§r".format(
            victim_team.color if victim_team else u"§c",  # 修复: 使用color属性而非text_color
            victim_name
        )

        # 构建死亡消息
        if attacker_id and attacker_id != "-1":
            # PVP击杀，获取击杀者信息
            attacker_team_id = self.team_module.get_player_team(attacker_id) if self.team_module else None
            attacker_name = self._get_player_name(attacker_id)
            attacker_team = team_types.get(attacker_team_id) if attacker_team_id else None
            attacker_colored_name = u"{}{}§r".format(
                attacker_team.color if attacker_team else u"§a",  # 修复: 使用color属性而非text_color
                attacker_name
            )

            # 获取击杀者的击杀次数（用于count-package广播）
            kill_count = None
            if self.scoreboard:
                try:
                    killer_score = self.scoreboard.get_player_score(attacker_id)
                    if killer_score:
                        kill_count = killer_score.kills
                except Exception as e:
                    print("[WARN] [BedWarsGameSystem] 获取击杀次数失败: {}".format(str(e)))

            # 检查是否使用装饰系统的击杀广播
            if self.ornament_system:
                ornament_message = self.ornament_system.get_kill_broadcast_message(
                    attacker_id, victim_colored_name, attacker_colored_name, kill_count
                )
                if ornament_message:
                    # 使用装饰系统的自定义消息
                    if is_final_kill:
                        # 添加终结击杀标记
                        message = u"{} §c§l FINAL KILL!".format(ornament_message)
                    else:
                        message = ornament_message
                    self._broadcast_message(message, '\xc2\xa7f')
                    return

            # 默认击杀消息 (与老项目100%一致)
            # 老项目默认: "{victim}{dark-aqua} 被 {killer} {dark-aqua}终结啦！"
            # dark-aqua = §3 (深青色)
            if is_final_kill:
                message = u"{}§3 被 {} §3终结啦！".format(
                    victim_colored_name, attacker_colored_name
                )
            else:
                message = u"{}§3 被 {} §3终结啦！".format(
                    victim_colored_name, attacker_colored_name
                )
        else:
            # 非PVP死亡 (与老项目100%一致)
            # 老项目格式: "» {icon-ec-death} {player_team}{player}"
            # 不显示死亡原因文本,只显示死亡图标和玩家名
            message = self.format_text(u"» {{icon-ec-death}} {}".format(victim_colored_name))

        # 广播消息
        self._broadcast_message(message, '\xc2\xa7f')

    # ========== 玩家死亡与复活 ==========

    def on_player_die(self, player_id, attacker_id=None, damage_cause=None):
        """
        玩家死亡处理

        Args:
            player_id (str): 玩家ID
            attacker_id (str): 攻击者ID(可选)
            damage_cause (str): 伤害原因(可选)
        """
        # 统一处理无效的attacker_id
        # 将 None、-1、"-1" 都标准化为 None
        if attacker_id is None or attacker_id == -1 or attacker_id == "-1":
            attacker_id = None
        else:
            attacker_id = str(attacker_id)  # 转换为字符串

        # 如果没有有效攻击者，尝试从攻击记录中查找
        # 注意：不再限制 damage_cause，所有无效 attacker 都尝试查找
        if not attacker_id:
            last_attacker = self.get_last_attacker(player_id, 5.0)
            if last_attacker:
                attacker_id = last_attacker
                self.LogInfo("从攻击记录找到击杀者: {} 被 {} 击杀(5秒内攻击记录)".format(
                    player_id, attacker_id))

        self.LogInfo("玩家死亡 player_id={} attacker_id={}".format(player_id, attacker_id))

        # 清理攻击记录
        self.clear_player_attack_record(player_id)

        # 播放击杀音效
        if attacker_id and self.ornament_system:
            # 获取玩家死亡位置
            comp = self.comp_factory.CreatePos(player_id)
            death_pos = comp.GetPos()
            self.ornament_system.play_kill_sound(attacker_id, player_id, death_pos)

        # 获取玩家队伍
        team_id = self.team_module.get_player_team(player_id) if self.team_module else None
        if not team_id:
            return

        # 检查床状态，判定是否为终结击杀（Final Kill）
        is_final_kill = team_id in self.destroyed_beds

        # 更新计分板（记录击杀数/终结击杀数）
        if self.scoreboard and attacker_id and attacker_id != "-1":
            self.scoreboard.on_player_death(player_id, attacker_id, is_final_kill)

        # 广播死亡消息到所有玩家
        self._broadcast_death_message(player_id, attacker_id, team_id, is_final_kill, damage_cause)

        # 处理玩家淘汰或复活
        if is_final_kill:
            # 床已被摧毁,玩家淘汰
            self._eliminate_player(player_id)
        else:
            # 床存在,准备复活
            self._start_respawn(player_id)

        # [FIX] 每次玩家死亡后检查游戏是否应该结束
        # 参考老项目 BedWarsRunningState.on_player_die() line 869
        # 老项目在每次死亡后都调用 check_win(),确保及时检测游戏结束条件
        self._check_game_end_after_death()

    def _eliminate_player(self, player_id):
        """
        淘汰玩家

        Args:
            player_id (str): 玩家ID
        """
        if player_id in self.eliminated_players:
            return

        self.eliminated_players.append(player_id)

        # [FIX] 从队伍中移除玩家（关键步骤！）
        # 参考老项目 BedWarsRunningState.on_player_die() line 784
        # 必须先获取队伍ID,再移除玩家,否则无法判断队伍是否全灭
        team_id = self.team_module.get_player_team(player_id) if self.team_module else None
        if self.team_module:
            self.team_module.remove_player_from_team(player_id)
            self.LogInfo("玩家{}已从队伍{}中移除".format(player_id, team_id))

        # 切换为旁观模式
        # [FIX 2025-11-06] 修正API调用: CreateGameMode -> CreatePlayer
        # 参考PracticePresetDefServer.py:308 正确API为CreatePlayer
        # 注意：网易MODSDK的GameType枚举使用首字母大写的Spectator，不是全大写的SPECTATOR
        comp = self.comp_factory.CreatePlayer(player_id)
        comp.SetPlayerGameType(serverApi.GetMinecraftEnum().GameType.Spectator)

        self.LogInfo("玩家{}已被淘汰".format(player_id))

        # 检查队伍是否全灭
        if team_id and self._is_team_eliminated(team_id):
            self._on_team_eliminated(team_id)

    def _start_respawn(self, player_id):
        """
        开始复活倒计时

        Args:
            player_id (str): 玩家ID
        """
        respawn_time = time.time() + 5.0  # 5秒后复活
        self.respawning[player_id] = respawn_time

        # 保存玩家装备
        self._save_respawn_contents(player_id)

        self.LogInfo("玩家{}开始复活倒计时(5秒)".format(player_id))

    def _save_respawn_contents(self, player_id):
        """
        保存玩家复活时的物品

        实现逻辑:
        1. 遍历玩家背包,保留death_keep列表中的物品
        2. 处理death_drop列表物品(掉落到世界)
        3. 执行death_item_demotion降级逻辑(镐子/斧子降级)
        4. 保存最高品质的剑类物品
        5. 保存护甲(根据player_armor_record)

        Args:
            player_id (str): 玩家ID
        """
        try:
            comp_item = self.comp_factory.CreateItem(player_id)
            comp_pos = self.comp_factory.CreatePos(player_id)
            # 修复: 使用CreateDimension获取维度ID，而不是CreatePos
            # PosComponentServer没有GetDimension()方法
            # 参考: BetterPlayerObject.py:258-259
            comp_dim = self.comp_factory.CreateDimension(player_id)
            dimension_id = comp_dim.GetPlayerDimensionId()
            player_pos = comp_pos.GetPos()

            contents = {}  # {(ItemPosType, slot): item_dict}

            # ========== 1. 处理背包物品 ==========
            inv_items = comp_item.GetPlayerAllItems(
                serverApi.GetMinecraftEnum().ItemPosType.INVENTORY
            )

            for slot, item_dict in enumerate(inv_items):
                if not item_dict or item_dict.get('count', 0) <= 0:
                    continue

                item_name = item_dict.get('newItemName', '')

                # 检查是否保留
                if item_name in self.config.get('death_keep', []):
                    contents[(serverApi.GetMinecraftEnum().ItemPosType.INVENTORY, slot)] = item_dict
                # 检查是否掉落
                elif item_name in self.config.get('death_drop', []):
                    comp_item.SpawnItemToLevel(item_dict, dimension_id, player_pos)

            # ========== 2. 添加最高品质的剑 ==========
            if player_id in self.player_sword_record:
                sword_name = self.player_sword_record[player_id]
                sword_item = {
                    'newItemName': sword_name,
                    'count': 1,
                    'enchantData': [],
                    'auxValue': 0
                }

                # 找到空槽位
                for i in range(36):
                    if (serverApi.GetMinecraftEnum().ItemPosType.INVENTORY, i) not in contents:
                        contents[(serverApi.GetMinecraftEnum().ItemPosType.INVENTORY, i)] = sword_item
                        break

            # ========== 3. 处理护甲 ==========
            # ========== 3. 处理护甲（只保存裤子/靴子，slot 2和3） ==========
            # 设计原则：
            # - 头盔（slot 0）和胸甲（slot 1）固定为皮革，不保存
            # - 裤子（slot 2）和靴子（slot 3）支持临时购买和永久升级，需要保存
            # - 优先级：临时购买（respawn_contents） > 永久升级（player_armor_record） > 默认皮革
            armor_items = comp_item.GetPlayerAllItems(
                serverApi.GetMinecraftEnum().ItemPosType.ARMOR
            )

            for slot, armor_dict in enumerate(armor_items):
                if not armor_dict:
                    continue

                # 只处理裤子（slot 2）和靴子（slot 3）
                if slot not in [2, 3]:
                    continue

                armor_name = armor_dict.get('newItemName', '')

                # 保留裤子/靴子到respawn_contents
                if armor_name in self.config.get('death_keep', []):
                    contents[(serverApi.GetMinecraftEnum().ItemPosType.ARMOR, slot)] = armor_dict
                    self.LogInfo("保存护甲: slot={} name={}".format(slot, armor_name))
                # 检查是否需要掉落
                elif armor_name in self.config.get('death_drop', []):
                    comp_item.SpawnItemToLevel(armor_dict, dimension_id, player_pos)

            # ========== 4. 执行物品降级逻辑 ==========
            if 'death_item_demotion' in self.config:
                self._apply_item_demotion(player_id, contents, inv_items)

            # 保存到respawn_contents
            self.respawn_contents[player_id] = contents

            self.LogInfo("玩家{}的复活物品已保存: {}".format(
                player_id, len(contents)
            ))

        except Exception as e:
            self.LogError("保存复活物品失败 player_id={} error={}".format(player_id, str(e)))
            import traceback
            self.LogError(traceback.format_exc())
            self.respawn_contents[player_id] = {}

    def _apply_item_demotion(self, player_id, contents, inv_items):
        """
        应用物品降级逻辑

        降级规则:
        - 钻石镐 → 铁镐
        - 铁镐 → 石镐
        - 石镐 → 木镐
        - 木镐 → 不降级(保留木镐)

        - 钻石斧 → 铁斧
        - 铁斧 → 石斧
        - 石斧 → 木斧
        - 木斧 → 不降级(保留木斧)

        Args:
            player_id (str): 玩家ID
            contents (dict): 复活物品字典 {(ItemPosType, slot): item_dict}
            inv_items (list): 玩家背包物品列表
        """
        # 定义降级映射表
        demotion_map = {
            # 镐子降级
            'minecraft:diamond_pickaxe': 'minecraft:iron_pickaxe',
            'minecraft:iron_pickaxe': 'minecraft:stone_pickaxe',
            'minecraft:stone_pickaxe': 'minecraft:wooden_pickaxe',
            'minecraft:wooden_pickaxe': 'minecraft:wooden_pickaxe',  # 木镐不降级

            # 斧子降级
            'minecraft:diamond_axe': 'minecraft:iron_axe',
            'minecraft:iron_axe': 'minecraft:stone_axe',
            'minecraft:stone_axe': 'minecraft:wooden_axe',
            'minecraft:wooden_axe': 'minecraft:wooden_axe',  # 木斧不降级
        }

        # 检查配置中的降级物品类型
        demotion_configs = self.config.get('death_item_demotion', [])

        for slot, item_dict in enumerate(inv_items):
            if not item_dict or item_dict.get('count', 0) <= 0:
                continue

            item_name = item_dict.get('newItemName', '')

            # 检查是否需要降级
            demoted_name = demotion_map.get(item_name)
            if demoted_name:
                # 创建降级后的物品
                demoted_item = {
                    'newItemName': demoted_name,
                    'count': 1,
                    'enchantData': [],
                    'auxValue': 0
                }

                # 添加到复活物品中
                contents[(serverApi.GetMinecraftEnum().ItemPosType.INVENTORY, slot)] = demoted_item

                self.LogInfo("物品降级: {} → {} (玩家: {})".format(
                    item_name, demoted_name, player_id
                ))

    def _is_team_eliminated(self, team_id):
        """
        检查队伍是否全灭

        Args:
            team_id (str): 队伍ID

        Returns:
            bool: 是否全灭
        """
        if not self.team_module:
            return False

        team_players = self.team_module.get_team_players(team_id)
        for player_id in team_players:
            if player_id not in self.eliminated_players:
                return False
        return True

    def _on_team_eliminated(self, team_id):
        """
        队伍全灭处理（完整实现）

        功能:
        1. 广播队伍淘汰消息（聊天框）
        2. 显示Title通知（大屏幕标题）
        3. 播放淘汰音效
        4. 检查游戏是否结束（只剩1个队伍时触发胜利）
        5. 更新HUD显示

        Args:
            team_id (str): 队伍ID

        参考: 老项目BedWarsRunningState.py没有专门的_on_team_eliminated方法
              但在check_win()中实现了胜利判定逻辑（第1428-1441行）
        """
        if not self.team_module:
            self.LogError("TeamModule未初始化，无法处理队伍淘汰")
            return

        # ========== 1. 获取队伍信息 ==========
        try:
            # [FIX 2025-11-04] 修复Python 2.7导入路径问题
            from Script_NeteaseMod.systems.team.TeamType import team_types
            team_type = team_types.get(team_id)
            if not team_type:
                self.LogError("未找到队伍类型: {}".format(team_id))
                return

            # 获取带颜色的队伍名称
            team_color = team_type.color  # 修复: 使用color属性而非text_color，例如: "\xa7c" (红色)
            team_name = team_type.name  # 修复: 使用name属性而非team_name_cn，例如: "红队"
            colored_team_name = u"{}{}".format(team_color, team_name)

        except Exception as e:
            self.LogError("获取队伍信息失败: {}".format(str(e)))
            return

        # ========== 2. 广播淘汰消息到聊天框 ==========
        try:
            message = u"§c{} §7已被淘汰！".format(colored_team_name)
            self._broadcast_message(message, u'\xa7f')
            self.LogInfo("队伍{}已全灭".format(team_id))

        except Exception as e:
            self.LogError("广播淘汰消息失败: {}".format(str(e)))

        # ========== 3. 显示Title通知（大屏幕标题） ==========
        try:
            # 向所有玩家显示Title
            player_ids = serverApi.GetPlayerList()
            for player_id in player_ids:
                try:
                    # 获取玩家所属队伍
                    player_team = self.team_module.get_player_team(player_id)

                    # 根据玩家队伍显示不同的Title
                    if player_team == team_id:
                        # 被淘汰队伍的玩家
                        title = u"§c§l你的队伍已被淘汰"
                        subtitle = u"§7本局结束后将自动开始下一局"
                    else:
                        # 其他队伍的玩家和观战者
                        title = u"§l{} §7已被淘汰".format(colored_team_name)
                        subtitle = u""

                    # 发送Title通知 (显示时间: 淡入0.5秒, 停留2秒, 淡出0.5秒)
                    msg_comp = self.comp_factory.CreateMsg(player_id)
                    msg_comp.NotifyOneTitle(
                        player_id,
                        title,
                        subtitle,
                        10,  # fadeIn (ticks): 0.5秒 = 10 ticks
                        40,  # stay (ticks): 2秒 = 40 ticks
                        10   # fadeOut (ticks): 0.5秒 = 10 ticks
                    )

                except Exception as e:
                    self.LogError("向玩家{}发送淘汰Title失败: {}".format(player_id, str(e)))

        except Exception as e:
            self.LogError("显示Title通知失败: {}".format(str(e)))

        # ========== 4. 播放淘汰音效 ==========
        try:
            # 向所有玩家播放音效
            player_ids = serverApi.GetPlayerList()
            for player_id in player_ids:
                try:
                    player_team = self.team_module.get_player_team(player_id)

                    # 根据玩家队伍播放不同音效
                    if player_team == team_id:
                        # 被淘汰队伍播放失败音效
                        sound = "mob.wither.death"  # 凋零死亡音效（沉重）
                    else:
                        # 其他队伍播放中性音效
                        sound = "mob.enderdragon.growl"  # 末影龙咆哮音效

                    # 获取玩家位置
                    pos_comp = self.comp_factory.CreatePos(player_id)
                    player_pos = pos_comp.GetPos()

                    if player_pos:
                        # 播放音效
                        game_comp = self.comp_factory.CreateGame(self.GetLevelId())
                        game_comp.PlaySound(player_pos, sound, 1.0, 1.0, False, player_id)

                except Exception as e:
                    self.LogError("向玩家{}播放淘汰音效失败: {}".format(player_id, str(e)))

        except Exception as e:
            self.LogError("播放淘汰音效失败: {}".format(str(e)))

        # ========== 5. 检查游戏是否结束 ==========
        try:
            # 防止重复触发: 如果游戏已经结束,直接返回
            if hasattr(self, '_winning_team') and self._winning_team is not None:
                return
            if hasattr(self, '_game_ended') and self._game_ended:
                return

            remaining_teams = self._get_remaining_teams()
            self.LogInfo("剩余队伍数量: {} (队伍: {})".format(
                len(remaining_teams), remaining_teams
            ))

            if len(remaining_teams) <= 1:
                # 游戏结束条件满足
                if len(remaining_teams) == 1:
                    # 有获胜队伍
                    self._winning_team = remaining_teams[0]
                    self.LogInfo("游戏结束 - 获胜队伍: {}".format(self._winning_team))

                    # 广播胜利消息
                    try:
                        winning_team_type = team_types.get(self._winning_team)
                        if winning_team_type:
                            win_message = u"§e§l游戏结束！§r {}{} §e获得胜利！".format(
                                winning_team_type.color,  # 修复: 使用color属性而非text_color
                                winning_team_type.name  # 修复: 使用name属性而非team_name_cn
                            )
                            self._broadcast_message(win_message, u'\xa7e')
                    except Exception as e:
                        self.LogError("广播胜利消息失败: {}".format(str(e)))

                else:
                    # 无获胜队伍（平局或所有队伍淘汰）
                    self._winning_team = None
                    self._game_ended = True  # 标记游戏已结束(平局)
                    self.LogInfo("游戏结束 - 平局")

                    # 广播平局消息
                    self._broadcast_message(u"§e§l游戏结束！§r §7平局", u'\xa7e')

                # 清空复活队列
                self.respawning.clear()

                # 切换到ending状态
                if hasattr(self, 'root_state') and self.root_state:
                    self.LogInfo("触发状态切换: running -> ending")
                    self.root_state.next_sub_state()  # 切换到ending状态
                else:
                    self.LogError("root_state未初始化，无法切换到ending状态")

        except Exception as e:
            self.LogError("检查游戏结束失败: {}".format(str(e)))
            import traceback
            self.LogError(traceback.format_exc())

        # ========== 6. 触发HUD更新 ==========
        # HUD会在下一个tick周期自动更新（_on_tick_hud方法）
        # 无需在此处手动触发

    def _check_game_end_after_death(self):
        """
        玩家死亡后检查游戏是否应该结束

        参考: 老项目 BedWarsRunningState.on_player_die() line 869
              老项目在每次玩家死亡后都调用 check_win() 检查游戏结束条件

        逻辑:
        1. 获取剩余队伍数量
        2. 如果剩余队伍 <= 1,触发游戏结束
        3. 设置获胜队伍并切换到ending状态

        防重复触发:
        - 如果游戏已经结束(状态已切换),直接返回
        - 使用_winning_team标志位判断是否已经触发过游戏结束
        """
        try:
            # 防止重复触发: 如果已经设置了获胜队伍,说明游戏已经结束
            if hasattr(self, '_winning_team') and self._winning_team is not None:
                return
            # 特殊情况: 平局时_winning_team为None,需要额外标志
            if hasattr(self, '_game_ended') and self._game_ended:
                return

            remaining_teams = self._get_remaining_teams()
            self.LogInfo("[死亡检查] 剩余队伍数量: {} (队伍: {})".format(
                len(remaining_teams), remaining_teams
            ))

            if len(remaining_teams) <= 1:
                # 游戏结束条件满足
                if len(remaining_teams) == 1:
                    # 有获胜队伍
                    self._winning_team = remaining_teams[0]
                    self.LogInfo("[死亡检查] 游戏结束 - 获胜队伍: {}".format(self._winning_team))

                    # 广播胜利消息
                    try:
                        from Script_NeteaseMod.systems.team.TeamType import team_types
                        winning_team_type = team_types.get(self._winning_team)
                        if winning_team_type:
                            win_message = u"§e§l游戏结束！§r {}{} §e获得胜利！".format(
                                winning_team_type.color,
                                winning_team_type.name
                            )
                            self._broadcast_message(win_message, 'YELLOW')
                    except Exception as e:
                        self.LogError("广播胜利消息失败: {}".format(str(e)))

                else:
                    # 无获胜队伍（平局或所有队伍淘汰）
                    self._winning_team = None
                    self._game_ended = True  # 标记游戏已结束(平局)
                    self.LogInfo("[死亡检查] 游戏结束 - 平局")

                    # 广播平局消息
                    self._broadcast_message(u"§e§l游戏结束！§r §7平局", u'\xa7e')

                # 清空复活队列
                self.respawning.clear()

                # 切换到ending状态
                if hasattr(self, 'root_state') and self.root_state:
                    self.LogInfo("[死亡检查] 触发状态切换: running -> ending")
                    self.root_state.next_sub_state()  # 切换到ending状态
                else:
                    self.LogError("root_state未初始化，无法切换到ending状态")

        except Exception as e:
            self.LogError("死亡后检查游戏结束失败: {}".format(str(e)))
            import traceback
            self.LogError(traceback.format_exc())

    def _get_remaining_teams(self):
        """
        获取剩余队伍列表

        判定逻辑: 与老项目check_win()保持100%一致
        - 统计team_module.team_to_player中非空的队伍
        - 当玩家死亡且床被破坏时,会从队伍中移除(team_module.remove_player_team)

        参考: 老项目BedWarsRunningState.check_win() 第1428-1441行

        Returns:
            list: 队伍ID列表
        """
        if not self.team_module:
            return []

        # 修复: 使用与老项目一致的逻辑 - 直接检查team_to_player
        # 老项目代码:
        # for team, players in team_to_player.items():
        #     if len(players) > 0:
        #         not_empty_teams.append(team)
        team_to_player = self.team_module.team_to_player
        remaining = []
        for team_id, players in team_to_player.items():
            if len(players) > 0:
                remaining.append(team_id)
        return remaining

    # ========== 方块管理 ==========

    def on_player_place_block(self, pos):
        """
        玩家放置方块

        Args:
            pos (tuple): 方块位置 (x, y, z)
        """
        if pos not in self.placed_blocks:
            self.placed_blocks.append(pos)

        # 通知RoomSystem记录到备份
        if self.room_system:
            self.room_system.record_block_to_backup(pos, self.dimension)

    # ========== 游戏逻辑更新 ==========

    def _update_game_logic(self):
        """更新游戏逻辑(每帧调用)"""
        # 更新虚空检测系统（每0.1秒检查一次）
        self._update_void_detection()

        # 更新复活系统
        self._update_respawn_system()

        # 更新治疗池系统
        self._update_healing_pools()

        # 更新陷阱系统
        self._update_trap_managers()

        # 更新陷阱免疫状态
        self._update_trap_immunity()

    def _update_void_detection(self):
        """
        更新虚空检测系统（每0.1秒检查一次）

        功能:
        - 检测所有存活玩家的位置
        - 如果玩家Y坐标 < 0，造成1000点虚空伤害
        - 已在复活列表中的玩家会被跳过（防止重复触发）

        参考: 老项目 BedWarsRunningState.py:1091-1103
        """
        import time

        current_time = time.time()

        # 每0.1秒检查一次
        if current_time < self.next_void_check_time:
            return

        self.next_void_check_time = current_time + 0.1

        if not self.team_module:
            return

        # [FIX 2025-11-06] 修复方法调用错误
        # TeamModule 没有 get_all_alive_players() 方法，应该使用 get_all_players() 获取所有玩家ID
        # 然后通过 get_better_player_obj() 获取玩家对象
        all_player_ids = self.team_module.get_all_players()

        for player_id in all_player_ids:
            # 跳过已在复活列表中的玩家（防止重复触发虚空伤害）
            if player_id in self.respawning:
                continue

            # 获取玩家对象
            try:
                player_obj = self.get_better_player_obj(player_id)
                if not player_obj:
                    continue
            except Exception as e:
                continue

            # 获取玩家位置
            pos = player_obj.GetPos()
            if pos is None:
                continue

            # 检查是否坠入虚空（Y < 0）
            if pos[1] < 0:
                # 造成1000点虚空伤害（会触发死亡流程）
                # 使用CreateHurt组件API而非BetterPlayerObject.SetHurt方法
                # 参考: SDK文档 - 接口/实体/行为.md Hurt方法
                comp_hurt = self.comp_factory.CreateHurt(player_id)
                comp_hurt.Hurt(1000, serverApi.GetMinecraftEnum().ActorDamageCause.Void,
                              attackerId=None, childAttackerId=None, knocked=False)
                self.LogDebug("玩家 {} 坠入虚空 Y={:.1f}，造成虚空伤害".format(player_id, pos[1]))

    def _update_respawn_system(self):
        """更新复活系统"""
        if not self.respawning:
            return

        current_time = time.time()
        respawned_players = []

        for player_id, respawn_time in self.respawning.items():
            if current_time >= respawn_time:
                self._respawn_player(player_id)
                respawned_players.append(player_id)

                # 清除复活倒计时消息
                # 使用GamingStateSystem的clear_stack_msg_bottom方法
                if self.room_system:
                    self.room_system.clear_stack_msg_bottom(key='respawn_countdown', player_id=player_id)
            else:
                # 显示复活倒计时（使用底部堆叠消息，避免与ActionBar重叠）
                # 参考: 老项目 BedWarsRunningState.py:1087
                # 使用GamingStateSystem的update_stack_msg_bottom方法
                remaining_seconds = int(respawn_time - current_time)

                # 格式化消息：你死了！你将在 X 秒后重生
                respawn_msg = u"\xa7l\xa7c你死了！\xa7r \xa77你将在 \xa7e{}\xa77 秒后重生".format(remaining_seconds)

                # 只发送给正在复活的玩家
                if self.room_system:
                    self.room_system.update_stack_msg_bottom(
                        key='respawn_countdown',
                        value=respawn_msg,
                        player_id=player_id
                    )

        # 移除已复活的玩家
        for player_id in respawned_players:
            self.respawning.pop(player_id, None)

    def _respawn_player(self, player_id):
        """
        复活玩家

        Args:
            player_id (str): 玩家ID
        """
        if not self.team_module:
            return

        # 获取队伍ID
        team_id = self.team_module.get_player_team(player_id)
        if not team_id:
            self.LogError("玩家{}没有队伍信息，无法复活".format(player_id))
            return

        # 通过ECPreset框架查询出生点
        try:
            from ECPresetServerScripts import get_server_mgr

            # 获取预设管理器
            preset_mgr = get_server_mgr("bedwars_room")
            if not preset_mgr:
                self.LogError("ECPreset管理器未初始化")
                # 回退到配置文件方式
                self._respawn_player_fallback(player_id, team_id)
                return

            # [FIX 2025-11-06] 查询该队伍的所有出生点
            # PresetManager没有get_instances_by_type方法，应该使用get_all_presets()
            # 参考ECPreset文档: PresetManager.get_all_presets() 返回 Dict[str, PresetInstance]
            # [FIX 2025-11-06] 属性名称修正: preset_type_name -> preset_type
            # 参考PresetInstance.py:27 实际属性名为 self.preset_type
            team_spawns = []
            all_presets = preset_mgr.get_all_presets()

            for instance_id, spawn_instance in all_presets.items():
                # 检查预设类型是否为spawn
                if spawn_instance.preset_type == "bedwars:spawn":
                    # [FIX] 修复API调用：使用 instance.data.get() 而不是 instance.get_data()
                    # 参考同文件1597-1599行的正确用法
                    spawn_team = spawn_instance.data.get("team")
                    if spawn_team == team_id:
                        spawn_pos = spawn_instance.data.get("spawn_position")
                        spawn_rot = spawn_instance.data.get("spawn_rotation")
                        if spawn_pos:
                            team_spawns.append((spawn_pos, spawn_rot))

            if not team_spawns:
                self.LogError("队伍{}没有出生点配置".format(team_id))
                # 回退到配置文件方式
                self._respawn_player_fallback(player_id, team_id)
                return

            # 随机选择一个出生点（避免复活碰撞）
            import random
            spawn_pos, spawn_rot = random.choice(team_spawns)

            self.LogInfo("使用出生点复活玩家: pos={}, rot={}".format(spawn_pos, spawn_rot))

        except Exception as e:
            self.LogError("查询出生点失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()
            # 回退到配置文件方式
            self._respawn_player_fallback(player_id, team_id)
            return

        # [FIX] 先设置生存模式，再传送玩家（旁观者模式下传送可能无效）
        try:
            # [FIX 2025-11-06] 修正API调用: CreateGameMode -> CreatePlayer
            # 参考PracticePresetDefServer.py:308 正确API为CreatePlayer + SetPlayerGameType
            comp = self.comp_factory.CreatePlayer(player_id)
            comp.SetPlayerGameType(serverApi.GetMinecraftEnum().GameType.Survival)
        except Exception as e:
            self.LogError("设置游戏模式失败: {}".format(str(e)))

        # 传送玩家到出生点
        try:
            pos_comp = self.comp_factory.CreatePos(player_id)
            pos_comp.SetFootPos(spawn_pos)

            # 设置玩家朝向
            if spawn_rot:
                rot_comp = self.comp_factory.CreateRot(player_id)
                rot_comp.SetRot((spawn_rot[0], spawn_rot[1]))

            # 清除玩家速度（防止摔落伤害）
            actor_motion_comp = self.comp_factory.CreateActorMotion(player_id)
            actor_motion_comp.SetMotion((0, 0, 0))

        except Exception as e:
            self.LogError("传送玩家失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()
            return

        # 取消无敌状态
        try:
            comp_hurt = self.comp_factory.CreateHurt(player_id)
            comp_hurt.ImmuneDamage(False)
        except Exception as e:
            self.LogError("取消无敌状态失败: {}".format(str(e)))

        # ===== [P0-3 FIX] 应用装备和升级（统一入口） =====
        # 替换原有的 _restore_respawn_contents 和 team_module.on_player_respawn
        # 使用统一的装备初始化方法，包含：
        # 1. 清空背包并发放初始装备（木剑、指南针、护甲）
        # 2. 恢复复活保留物品（respawn_contents中的剑和工具）
        # 3. 应用队伍升级效果（锋利、保护等）
        try:
            self._apply_player_equipment_and_upgrades(player_id, team_id)
        except Exception as e:
            self.LogError("应用装备和升级失败: {}".format(str(e)))
            import traceback
            self.LogError(traceback.format_exc())

        # 恢复生命值（在装备应用后，因为升级可能影响最大生命值）
        try:
            attr_comp = self.comp_factory.CreateAttr(player_id)
            max_health = attr_comp.GetAttrMaxValue(serverApi.GetMinecraftEnum().AttrType.HEALTH)
            attr_comp.SetAttrValue(serverApi.GetMinecraftEnum().AttrType.HEALTH, max_health)
        except Exception as e:
            self.LogError("恢复生命值失败: {}".format(str(e)))

        # 播放复活特效
        try:
            particle_comp = self.comp_factory.CreateParticle(player_id)
            particle_comp.SpawnParticle(spawn_pos, "minecraft:portal", self.dimension)
        except Exception as e:
            # 特效失败不影响主流程
            pass

        self.LogInfo("玩家{}已复活 team={} pos={}".format(player_id, team_id, spawn_pos))

    def _respawn_player_fallback(self, player_id, team_id):
        """
        复活玩家（回退方案：使用stage_config配置）

        Args:
            player_id (str): 玩家ID
            team_id (str): 队伍ID
        """
        self.LogWarn("使用回退方案复活玩家")

        spawn_points = self.stage_config.get("spawn_points", {})
        team_spawn = spawn_points.get(team_id, {})
        spawn_pos = team_spawn.get("position", (0, 64, 0))

        # 传送玩家
        try:
            pos_comp = self.comp_factory.CreatePos(player_id)
            pos_comp.SetFootPos(spawn_pos)

            # 恢复生命值
            attr_comp = self.comp_factory.CreateAttr(player_id)
            max_health = attr_comp.GetAttrMaxValue(serverApi.GetMinecraftEnum().AttrType.HEALTH)
            attr_comp.SetAttrValue(serverApi.GetMinecraftEnum().AttrType.HEALTH, max_health)

            # 设置生存模式
            # [FIX 2025-11-06] 修正API调用: CreateGameMode -> CreatePlayer
            # 参考PracticePresetDefServer.py:308 正确API为CreatePlayer + SetPlayerGameType
            comp = self.comp_factory.CreatePlayer(player_id)
            comp.SetPlayerGameType(serverApi.GetMinecraftEnum().GameType.Survival)

            self.LogInfo("玩家{}已复活(回退方案) pos={}".format(player_id, spawn_pos))

        except Exception as e:
            self.LogError("回退方案复活失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _restore_respawn_contents(self, player_id):
        """
        恢复玩家复活时的物品

        保留规则：
        - 护甲（永久装备）
        - 永久购买的工具（镐子、斧头等,已降级处理）
        - 剑类武器（保留最高级的）

        Args:
            player_id (str): 玩家ID
        """
        if player_id not in self.respawn_contents:
            self.LogInfo("玩家{}没有复活物品记录".format(player_id))
            return

        contents = self.respawn_contents.pop(player_id)

        try:
            comp_item = self.comp_factory.CreateItem(player_id)

            # ========== 1. 清空玩家背包 ==========
            # 清空背包槽位（0-35）
            for slot in range(36):
                comp_item.SpawnItemToPlayerInv(
                    {'newItemName': 'minecraft:air', 'count': 0},
                    player_id,
                    slot
                )

            # 清空护甲槽位（0-3: 头盔,胸甲,护腿,靴子）
            for slot in range(4):
                comp_item.SpawnItemToPlayerInv(
                    {'newItemName': 'minecraft:air', 'count': 0},
                    player_id,
                    slot,
                    serverApi.GetMinecraftEnum().ItemPosType.ARMOR
                )

            # ========== 2. 恢复物品到对应槽位 ==========
            for (pos_type, slot), item_dict in contents.items():
                if item_dict and item_dict.get('count', 0) > 0:
                    if pos_type == serverApi.GetMinecraftEnum().ItemPosType.INVENTORY:
                        # 背包物品
                        comp_item.SpawnItemToPlayerInv(item_dict, player_id, slot)
                    elif pos_type == serverApi.GetMinecraftEnum().ItemPosType.ARMOR:
                        # 护甲物品
                        comp_item.SpawnItemToPlayerInv(
                            item_dict, player_id, slot,
                            serverApi.GetMinecraftEnum().ItemPosType.ARMOR
                        )

            self.LogInfo("恢复玩家{}的复活物品: {}个槽位".format(player_id, len(contents)))

        except Exception as e:
            self.LogError("恢复复活物品失败 player_id={} error={}".format(player_id, str(e)))
            import traceback
            self.LogError(traceback.format_exc())

    def _update_healing_pools(self):
        """更新所有治疗池"""
        if not self.team_healing_pools:
            return

        for team_id, healing_pool in self.team_healing_pools.items():
            try:
                healing_pool.on_update()
            except Exception as e:
                self.LogError("更新治疗池 {} 失败: {}".format(team_id, str(e)))

    def _update_trap_managers(self):
        """更新所有陷阱管理器"""
        if not self.team_trap_managers:
            return

        for team_id, trap_manager in self.team_trap_managers.items():
            try:
                trap_manager.on_update()
            except Exception as e:
                self.LogError("更新陷阱管理器 {} 失败: {}".format(team_id, str(e)))

    def _update_trap_immunity(self):
        """更新陷阱免疫状态"""
        import time
        current_time = time.time()

        # 移除过期的免疫状态
        expired_players = []
        for player_id, immunity_end_time in self.trap_immune_players.items():
            if current_time >= immunity_end_time:
                expired_players.append(player_id)

        for player_id in expired_players:
            self.trap_immune_players.pop(player_id, None)

    # ========== 预设查找方法 ==========

    def find_team_spawns(self):
        """
        查找所有队伍的出生点

        Returns:
            dict: 字典 {team_id: [(pos, rot), ...]}
        """
        team_spawns = {}

        try:
            # 从预设管理器获取所有SpawnPreset实例
            from framework.server.PresetManager import PresetManager
            preset_manager = PresetManager.get_instance()
            if not preset_manager:
                self.LogWarn("PresetManager未初始化")
                return team_spawns

            # 遍历所有预设实例,查找SpawnPreset
            # 注意：get_all_presets()返回字典{instance_id: PresetInstance}
            all_presets = preset_manager.get_all_presets()
            for instance_id, instance in all_presets.items():
                if instance.preset_type == "spawn":
                    team_id = instance.data.get("team")
                    spawn_pos = instance.data.get("spawn_position")
                    spawn_rot = instance.data.get("spawn_rotation")

                    if team_id and spawn_pos:
                        if team_id not in team_spawns:
                            team_spawns[team_id] = []
                        team_spawns[team_id].append((spawn_pos, spawn_rot))

            self.LogInfo("找到 {} 个队伍的出生点".format(len(team_spawns)))

        except Exception as e:
            self.LogError("查找出生点失败: {}".format(str(e)))

        return team_spawns

    def find_generators(self, team_id):
        """
        查找指定队伍的所有生成器

        Args:
            team_id (str): 队伍ID

        Returns:
            list: GeneratorPreset实例列表
        """
        generators = []

        try:
            # 从预设管理器获取所有GeneratorPreset实例
            from framework.server.PresetManager import PresetManager
            preset_manager = PresetManager.get_instance()
            if not preset_manager:
                self.LogWarn("PresetManager未初始化")
                return generators

            # 遍历所有预设实例,查找属于指定队伍的GeneratorPreset
            # 注意：get_all_presets()返回字典{instance_id: PresetInstance}
            all_presets = preset_manager.get_all_presets()
            for instance_id, instance in all_presets.items():
                if instance.preset_type == "generator":
                    gen_team = instance.data.get("team")
                    if gen_team == team_id:
                        generators.append(instance)

            self.LogInfo("找到队伍 {} 的 {} 个生成器".format(team_id, len(generators)))

        except Exception as e:
            self.LogError("查找生成器失败: {}".format(str(e)))

        return generators

    # ========== 跨系统引用初始化 ==========

    def _initialize_room_system_reference(self):
        """初始化RoomManagementSystem引用"""
        try:
            self.room_system = self.GetSystem(self.namespace, "RoomManagementSystem")
            if self.room_system:
                self.LogInfo("RoomManagementSystem引用获取成功")
            else:
                self.LogWarn("RoomManagementSystem未找到")
        except Exception as e:
            self.LogError("获取RoomManagementSystem引用失败: {}".format(str(e)))

    # ========== 陷阱免疫系统 ==========

    def is_player_trap_immune(self, player_id):
        """
        检查玩家是否具有陷阱免疫状态

        :param player_id: 玩家ID
        :return: True如果免疫，否则False
        """
        import time
        current_time = time.time()

        if player_id in self.trap_immune_players:
            immunity_end_time = self.trap_immune_players[player_id]
            return current_time < immunity_end_time

        return False

    def set_player_trap_immunity(self, player_id, duration):
        """
        设置玩家的陷阱免疫状态

        :param player_id: 玩家ID
        :param duration: 免疫持续时间（秒）
        """
        import time
        current_time = time.time()
        self.trap_immune_players[player_id] = current_time + duration

        self.LogInfo("玩家{}获得陷阱免疫 {}秒".format(player_id, duration))

    def get_team_trap_manager(self, team_id):
        """
        获取队伍的陷阱管理器

        :param team_id: 队伍ID
        :return: TeamTrapManager实例，如果不存在返回None
        """
        return self.team_trap_managers.get(team_id, None)

    # ========== 辅助方法 ==========

    def _get_player_name(self, player_id):
        """获取玩家昵称"""
        try:
            comp = self.comp_factory.CreateName(player_id)
            name = comp.GetName()
            return name if name else str(player_id)
        except Exception as e:
            self.LogError("获取玩家昵称失败: player_id={}, error={}".format(player_id, str(e)))
            return str(player_id)

    def _broadcast_message(self, message, color='\xc2\xa7f'):
        """
        广播消息给所有玩家 (对局内聊天消息通知)

        使用NotifyOneMessage API向对局内所有玩家逐个发送聊天栏消息通知

        Args:
            message (str): 消息内容
            color (str): 颜色代码 (\xc2\xa7f=白色, \xc2\xa7e=黄色, \xc2\xa7c=红色等)
                        使用UTF-8编码格式 '\xc2\xa7f'

        参考:
        - 老项目: Parts/GamingState/util/BetterPartUtil.py:58 使用 '\xc2\xa7f'
        - 老项目: Parts/GamingState/util/BetterPlayerObject.py:78 使用NotifyOneMessage
        - 新项目: GamingStateSystem.broadcast_message() (systems/GamingStateSystem.py:602)
        """
        # [FIX 2025-11-07] 修复死亡消息不广播的BUG
        # 使用父类的broadcast_message方法，该方法使用NotifyOneMessage逐个通知玩家
        self.broadcast_message(message, color)

    def _load_game_mode_config(self, mode):
        """
        加载游戏模式配置

        Args:
            mode (str): 游戏模式(team2/team4/team8)
        """
        try:
            # 从config/game_modes目录导入配置
            module_name = "Script_NeteaseMod.config.game_modes.{}".format(mode)
            config_module = __import__(module_name, fromlist=['MODE_CONFIG'])
            self.config = config_module.MODE_CONFIG

            self.LogInfo("Loaded game mode config: {}".format(mode))
            self.LogInfo("  - Mode name: {}".format(self.config.get("mode_name", "")))
            self.LogInfo("  - Teams: {}".format(self.config.get("teams", [])))
            self.LogInfo("  - Max players per team: {}".format(self.config.get("teams_max_players", 0)))
            self.LogInfo("  - Game phases: {}".format(len(self.config.get("gaming_states", []))))

        except ImportError as e:
            self.LogError("Failed to load game mode config for {}: {}".format(mode, str(e)))
            # 使用最简单的默认配置
            self.config = {
                "teams": ["RED", "BLUE"],
                "teams_max_players": 1,
                "gaming_states": []
            }

    # ========== 观战系统集成 - 中途加入游戏 ==========

    def register_spectator_events(self):
        """
        注册观战系统相关事件

        在Create()中调用,用于监听客户端的中途加入请求
        """
        # 监听客户端中途加入请求
        self.ListenForEvent(
            self.namespace,
            self.systemName,
            'ClientRequestMidwayGameEvent',
            self,
            self._on_client_request_midway_game
        )

        self.LogInfo("观战系统事件已注册")

    def _on_client_request_midway_game(self, args):
        """
        处理客户端中途加入游戏请求

        Args:
            args: {'player_id': str}
        """
        player_id = args.get('player_id')

        self.LogDebug("收到玩家{}的中途加入请求".format(player_id))

        # 执行中途加入逻辑
        success = self.midway_to_game(player_id)

        # 通知客户端结果
        self.NotifyToClient(player_id, 'ServerResponseMidwayGameEvent', {
            'res': success
        })

        if success:
            self.LogInfo("玩家{}成功中途加入游戏".format(player_id))
        else:
            self.LogInfo("玩家{}中途加入失败".format(player_id))

    def midway_to_game(self, player_id):
        """
        中途加入游戏逻辑

        将观战玩家分配到人数最少的队伍,并传送到出生点

        Args:
            player_id (str): 玩家ID

        Returns:
            bool: True=加入成功, False=加入失败
        """
        try:
            # 条件检查
            if not self.should_show_join_button(player_id):
                self.LogDebug("玩家{}不满足中途加入条件".format(player_id))
                return False

            # 查找人数最少的队伍
            team_to_join = self._find_least_populated_team()
            if not team_to_join:
                self.LogDebug("没有可加入的队伍")
                return False

            # 将玩家添加到队伍
            if not self.team_module.add_player_to_team(player_id, team_to_join):
                self.LogDebug("添加玩家到队伍失败")
                return False

            # 切换游戏模式为生存模式
            comp_game_type = self.comp_factory.CreateGameType(player_id)
            comp_game_type.SetGameType(0)  # 0 = Survival

            # 传送到出生点并发放装备
            if self.current_state and hasattr(self.current_state, 'midway_player'):
                # 调用状态的midway_player方法(如果存在)
                player_obj = self.get_better_player_obj(player_id)
                self.current_state.midway_player(player_obj)
            else:
                # 回退方案: 直接重生玩家
                self._respawn_player(player_id)

            # 广播消息
            # [FIX 2025-11-04] 修复Python 2.7导入路径问题
            from Script_NeteaseMod.systems.team.TeamType import team_types
            team_type = team_types.get(team_to_join)
            if team_type:
                team_display = "{}{}".format(team_type.color, team_type.name)  # 修复: 使用color和name属性
                self._broadcast_message(
                    "§e玩家 §f{} §e中途加入了{}".format(
                        self._get_player_name(player_id),
                        team_display
                    )
                )

            return True

        except Exception as e:
            self.LogError("中途加入游戏失败: {}".format(str(e)))
            import traceback
            print(traceback.format_exc())
            return False

    def should_show_join_button(self, player_id):
        """
        检查是否应该显示中途参战按钮

        条件:
        1. 游戏状态为运行中 (current_sub_state_name == 'running')
        2. 玩家未被淘汰
        3. 玩家不在任何队伍中
        4. 存在床未被破坏且未满员的队伍

        Args:
            player_id (str): 玩家ID

        Returns:
            bool: True=应该显示按钮
        """
        try:
            # 检查游戏状态机是否存在
            if not self.root_state:
                return False

            # 检查当前状态是否为运行中
            if self.root_state.current_sub_state_name != 'running':
                return False

            # 检查玩家是否已被淘汰
            # 修复: is_player_eliminated方法不存在,应检查eliminated_players列表
            if player_id in self.eliminated_players:
                return False

            # 检查玩家是否已在队伍中
            if self.team_module.get_player_team(player_id):
                return False

            # 检查是否存在可加入的队伍
            team = self._find_least_populated_team()
            return team is not None

        except Exception as e:
            self.LogError("检查中途参战条件失败: {}".format(str(e)))
            return False

    def _find_least_populated_team(self):
        """
        查找人数最少的可加入队伍

        只考虑床未被破坏且未满员的队伍

        Returns:
            str: 队伍ID,如果没有可加入的队伍返回None
        """
        try:
            team_player_counts = {}

            # 统计各队伍人数
            for team_id in self.team_module.teams:
                # 跳过床已被破坏的队伍
                if team_id in self.destroyed_beds:
                    continue

                players = self.team_module.get_team_players(team_id)
                team_player_counts[team_id] = len(players)

            if not team_player_counts:
                return None

            # 找到人数最少的队伍
            max_players = self.config.get('teams_max_players', 4)

            min_team = None
            min_count = max_players + 1

            for team_id, count in team_player_counts.items():
                if count < max_players and count < min_count:
                    min_team = team_id
                    min_count = count

            return min_team

        except Exception as e:
            self.LogError("查找最少人数队伍失败: {}".format(str(e)))
            return None

    def notify_show_join_button(self, player_id):
        """
        通知客户端显示中途加入按钮

        当玩家切换为观战者时调用

        Args:
            player_id (str): 玩家ID
        """
        if self.should_show_join_button(player_id):
            self.NotifyToClient(player_id, 'ServerShowJoinButtonVisible', {})

    def server_enable_viewer(self, player_id):
        """
        将玩家设置为观战者模式

        功能:
        1. 切换为旁观模式(Spectator)
        2. 设置伤害免疫
        3. 允许飞行

        Args:
            player_id (str): 玩家ID

        参考: 老项目 ECBedWarsPart.py:1197-1201
        """
        try:
            # 获取玩家对象
            player = self.get_better_player_obj(player_id)

            # 1. 切换为旁观模式
            from mod.common.minecraftEnum import GameType
            player.set_game_type(GameType.Spectator)

            # 2. 设置伤害免疫
            player.SetImmuneDamage(True)

            # 3. 允许飞行
            player.ChangeFlyState(True)

            self.LogInfo("玩家 {} 已切换为观战者模式".format(player_id))

            # 4. 通知观战系统显示加入按钮(如果满足条件)
            self.notify_show_join_button(player_id)

        except Exception as e:
            self.LogError("设置观战者模式失败 player_id={} error={}".format(player_id, str(e)))
            import traceback
            self.LogError(traceback.format_exc())

    # ========== 攻击记录系统 - 击杀归属判定 ==========

    def record_player_attack(self, victim_id, attacker_id, damage_cause=None):
        """
        记录玩家攻击信息,用于虚空死亡时的击杀归属判定

        Args:
            victim_id (str): 受害者玩家ID
            attacker_id (str): 攻击者玩家ID
            damage_cause (str): 伤害原因(可选)
        """
        import time
        current_time = time.time()

        # 记录攻击信息
        self.last_attacker_records[victim_id] = {
            'attacker_id': attacker_id,
            'attack_time': current_time,
            'damage_cause': damage_cause if damage_cause else 'unknown'
        }

        self.LogDebug("记录攻击: {} 被 {} 攻击 (原因: {})".format(
            victim_id, attacker_id, damage_cause if damage_cause else 'unknown'
        ))

    def get_last_attacker(self, victim_id, max_time_diff=5.0):
        """
        获取玩家的最后攻击者,用于虚空死亡时的击杀判定

        Args:
            victim_id (str): 受害者玩家ID
            max_time_diff (float): 最大时间差(秒),默认5秒

        Returns:
            str: 攻击者ID,如果超时或无记录则返回None
        """
        if victim_id not in self.last_attacker_records:
            return None

        import time
        current_time = time.time()
        attack_record = self.last_attacker_records[victim_id]

        # 检查时间差是否在允许范围内
        time_diff = current_time - attack_record['attack_time']
        if time_diff <= max_time_diff:
            attacker_id = attack_record['attacker_id']
            self.LogInfo("虚空死亡击杀判定: {} 在 {:.1f} 秒前被 {} 攻击,判定为被击杀".format(
                victim_id, time_diff, attacker_id))
            return attacker_id
        else:
            self.LogDebug("虚空死亡无归属: {} 最后攻击距今 {:.1f} 秒,超过 {:.1f} 秒有效期".format(
                victim_id, time_diff, max_time_diff))
            return None

    def clear_player_attack_record(self, player_id):
        """
        清除玩家的攻击记录,在玩家死亡后调用

        Args:
            player_id (str): 玩家ID
        """
        if player_id in self.last_attacker_records:
            del self.last_attacker_records[player_id]
            self.LogDebug("已清除玩家 {} 的攻击记录".format(player_id))

    def cleanup_old_attack_records(self, max_age=30.0):
        """
        清理过期的攻击记录,定期调用以释放内存

        Args:
            max_age (float): 最大保留时间(秒),默认30秒
        """
        import time
        current_time = time.time()
        expired_players = []

        for player_id, record in self.last_attacker_records.items():
            if current_time - record['attack_time'] > max_age:
                expired_players.append(player_id)

        for player_id in expired_players:
            del self.last_attacker_records[player_id]

        if expired_players:
            self.LogDebug("清理了 {} 个过期的攻击记录".format(len(expired_players)))

    # ========== 陷阱免疫系统 ==========

    def add_trap_immunity(self, player_id, duration=30):
        """
        为玩家添加陷阱免疫状态

        Args:
            player_id (str): 玩家ID
            duration (int): 免疫持续时间（秒），默认30秒
        """
        import time
        self.trap_immune_players[player_id] = time.time() + duration
        self.LogDebug("玩家 {} 获得陷阱免疫状态，持续 {} 秒".format(player_id, duration))

    def is_player_trap_immune(self, player_id):
        """
        检查玩家是否具有陷阱免疫状态

        Args:
            player_id (str): 玩家ID

        Returns:
            bool: 是否具有陷阱免疫状态
        """
        import time
        if player_id not in self.trap_immune_players:
            return False
        if time.time() > self.trap_immune_players[player_id]:
            # 免疫时间已过，移除记录
            self.trap_immune_players.pop(player_id)
            return False
        return True

    def remove_trap_immunity(self, player_id):
        """
        移除玩家的陷阱免疫状态

        Args:
            player_id (str): 玩家ID
        """
        if player_id in self.trap_immune_players:
            self.trap_immune_players.pop(player_id)
            self.LogDebug("玩家 {} 的陷阱免疫状态已移除".format(player_id))

    def get_trap_immunity_status(self, player_id):
        """
        获取玩家的陷阱免疫状态信息

        Args:
            player_id (str): 玩家ID

        Returns:
            dict: 免疫状态信息 {'immune': bool, 'remaining_time': int}
        """
        import time
        if player_id not in self.trap_immune_players:
            return {"immune": False, "remaining_time": 0}

        remaining_time = max(0, self.trap_immune_players[player_id] - time.time())
        return {
            "immune": remaining_time > 0,
            "remaining_time": int(remaining_time)
        }

    # ========== 装备初始化系统 ==========

    def _init_player_equipment(self, player_id, team_id):
        """
        初始化玩家基础装备（不包含队伍升级效果）

        Args:
            player_id (str): 玩家ID
            team_id (str): 队伍ID

        功能:
        1. 清空玩家背包和护甲槽
        2. 发放初始装备（木剑、指南针）
        3. 发放队伍染色的皮革护甲（或永久购买的高级护甲）
        4. 设置装备不掉落和不掉耐久

        注意:
        - 此方法不应用队伍升级（锋利、保护等）
        - 升级效果由 _apply_player_equipment_and_upgrades() 调用
        """
        try:
            # 导入队伍类型
            # [FIX 2025-11-04] 修复Python 2.7导入路径问题,需要使用完整的模块路径
            from Script_NeteaseMod.systems.team.TeamType import team_types

            if team_id not in team_types:
                self.LogError("无效的队伍ID: {}".format(team_id))
                return False

            # 获取队伍颜色
            team_type = team_types[team_id]
            color_int = team_type.get_rgb_color_int()
            custom_color = {
                "__type__": 3,
                "__value__": color_int
            }

            # 获取物品组件
            comp_item = self.comp_factory.CreateItem(player_id)

            # ========== 1. 清空背包 ==========
            # [FIX 2025-11-06] 修复清空背包方法，使用SetInvItemNum而非SpawnItemToPlayerInv
            # 参考老项目: ECBedWarsPart.py:1279 使用 comp.SetInvItemNum(i, 0) 清空槽位
            # 原因: SpawnItemToPlayerInv 无法正确清空槽位，导致后续物品发放失败
            self.LogInfo("清空玩家{}的背包".format(player_id))
            for i in range(36):
                comp_item.SetInvItemNum(i, 0)

            # ========== 2. 恢复背包物品（剑、工具，不含护甲） ==========
            # 护甲数据在respawn_contents中，但在步骤4单独处理
            # 这里只恢复背包物品，避免与后续护甲设置逻辑冲突
            if player_id in self.respawn_contents:
                contents = self.respawn_contents[player_id]  # FIX: Read only, do not delete

                # 只恢复背包物品，过滤掉护甲槽
                inventory_contents = {}
                for (pos_type, slot), item_dict in contents.items():
                    if pos_type == serverApi.GetMinecraftEnum().ItemPosType.INVENTORY:
                        inventory_contents[(pos_type, slot)] = item_dict

                if inventory_contents:
                    comp_item.SetPlayerAllItems(inventory_contents)
                    self.LogInfo("恢复玩家{}的背包物品: {}个槽位".format(player_id, len(inventory_contents)))

                # 检查是否包含剑
                has_sword = False
                for item_dict in inventory_contents.values():
                    item_name = item_dict.get('newItemName', '') or item_dict.get('itemName', '')
                    if 'sword' in item_name:
                        has_sword = True
                        break

                # 如果复活物品中没有剑，给予记录的剑
                if not has_sword:
                    sword_record = self.player_sword_record.get(player_id, "minecraft:wooden_sword")
                    comp_item.SpawnItemToPlayerInv({
                        "itemName": sword_record,
                        "count": 1,
                        "enchantData": [],
                        "auxValue": 0
                    }, player_id)
                    self.LogInfo("玩家{}获得剑: {}".format(player_id, sword_record))
            else:
                # 没有复活物品，给予记录的剑（或默认木剑）
                sword_record = self.player_sword_record.get(player_id, "minecraft:wooden_sword")
                result = comp_item.SpawnItemToPlayerInv({
                    "itemName": sword_record,
                    "count": 1,
                    "enchantData": [],
                    "auxValue": 0
                }, player_id)
                self.LogInfo("玩家{}获得剑: {} (result={})".format(player_id, sword_record, result))

            # ========== 3. 给予指南针（用于追踪功能） ==========
            # [FIX 2025-11-06] 修复物品字段名: newItemName -> itemName
            # 参考老项目ECBedWarsPart.py:1365 和新项目RoomManagementSystem.py:454 使用itemName
            # 参考老项目ECBedWarsPart.py:1343-1374 需要检查玩家是否已有指南针
            # [FIX 2025-11-06] 修复指南针检查逻辑
            # 问题: GetPlayerAllItems返回list(dict)而非dict,导致检查永远失败
            # 参考SDK文档: 接口/玩家/背包.md:303 返回值是list(dict)
            # 参考老项目: ECBedWarsPart.py:1355-1361 同时处理dict和list两种情况
            has_compass = False
            all_items = comp_item.GetPlayerAllItems(serverApi.GetMinecraftEnum().ItemPosType.INVENTORY)

            # 检查背包中是否已有指南针
            # GetPlayerAllItems返回list(dict),索引0-35对应36个背包槽位
            if isinstance(all_items, list):
                for item_dict in all_items:
                    if item_dict and item_dict.get("itemName") == "minecraft:compass":
                        has_compass = True
                        self.LogInfo("玩家{}已有指南针,跳过发放".format(player_id))
                        break
            elif isinstance(all_items, dict):
                # 兼容性处理:某些情况下可能返回dict
                for slot_id, item_dict in all_items.items():
                    if item_dict and item_dict.get("itemName") == "minecraft:compass":
                        has_compass = True
                        self.LogInfo("玩家{}已有指南针,跳过发放".format(player_id))
                        break

            if not has_compass:
                result = comp_item.SpawnItemToPlayerInv({
                    "itemName": "minecraft:compass",
                    "count": 1,
                    "enchantData": [],
                    "auxValue": 0
                }, player_id)
                self.LogInfo("玩家{}获得物品: minecraft:compass (result={})".format(player_id, result))

            # ========== 4. 发放护甲（优先级：respawn_contents > armor_record > 默认皮革） ==========
            # 获取玩家护甲记录（永久购买的高级护甲）
            if player_id not in self.player_armor_record:
                self.player_armor_record[player_id] = {}

            armor_record = self.player_armor_record[player_id]

            # 从respawn_contents提取护甲（如果有）
            respawn_armors = {}
            if player_id in self.respawn_contents:
                contents_snapshot = self.respawn_contents[player_id]
                for (pos_type, slot), item_dict in contents_snapshot.items():
                    if pos_type == serverApi.GetMinecraftEnum().ItemPosType.ARMOR:
                        respawn_armors[slot] = item_dict.get('newItemName', '') or item_dict.get('itemName', '')

            # 护甲槽位配置
            armor_items = [
                ("minecraft:leather_helmet", 0),       # 头盔 - 固定皮革
                ("minecraft:leather_chestplate", 1),   # 胸甲 - 固定皮革
                ("minecraft:leather_leggings", 2),     # 裤子 - 可升级
                ("minecraft:leather_boots", 3)         # 靴子 - 可升级
            ]

            armor_slots = {}

            for default_item, slot_index in armor_items:
                # 确定实际使用的护甲
                item_name = default_item

                # 头盔和胸甲固定为皮革
                if slot_index in [0, 1]:
                    item_name = default_item  # 固定皮革，不检查armor_record
                # 裤子和靴子支持升级
                elif slot_index == 2:
                    # 优先级：临时购买 > 永久升级 > 默认皮革
                    if 2 in respawn_armors:
                        item_name = respawn_armors[2]
                        self.LogInfo("玩家{}使用临时购买的裤子: {}".format(player_id, item_name))
                    elif 'leggings' in armor_record:
                        item_name = armor_record['leggings']
                        self.LogInfo("玩家{}使用永久升级的裤子: {}".format(player_id, item_name))
                elif slot_index == 3:
                    # 优先级：临时购买 > 永久升级 > 默认皮革
                    if 3 in respawn_armors:
                        item_name = respawn_armors[3]
                        self.LogInfo("玩家{}使用临时购买的靴子: {}".format(player_id, item_name))
                    elif 'boots' in armor_record:
                        item_name = armor_record['boots']
                        self.LogInfo("玩家{}使用永久升级的靴子: {}".format(player_id, item_name))

                # 创建护甲物品
                # [FIX 2025-11-06] 修复字段名: newItemName -> itemName (参考老项目ECBedWarsPart.py:1417)
                # 护甲物品必须使用itemName,否则无法正确装备
                armor_item = {
                    "itemName": item_name,
                    "count": 1,
                    "userData": {
                        "minecraft:item_lock": {
                            "__type__": 1,
                            "__value__": True  # 设置不掉落
                        }
                    }
                }

                # 只有皮革护甲才染色
                if item_name in ["minecraft:leather_helmet", "minecraft:leather_chestplate",
                                 "minecraft:leather_leggings", "minecraft:leather_boots"]:
                    armor_item["userData"]["customColor"] = custom_color

                armor_slots[(serverApi.GetMinecraftEnum().ItemPosType.ARMOR, slot_index)] = armor_item

            # ========== 5. 设置护甲槽 ==========
            # [FIX 2025-11-06] 修复护甲设置方法
            # 参考老项目ECBedWarsPart.py:1446-1454使用SetPlayerAllItems设置护甲
            # 原因: SpawnItemToPlayerInv无法正确设置护甲槽,护甲会掉到背包
            # 正确做法: 先清空护甲槽,再使用SetPlayerAllItems一次性设置所有护甲

            # 先清空现有护甲槽位
            comp_item.SetPlayerAllItems({
                (serverApi.GetMinecraftEnum().ItemPosType.ARMOR, 0): None,
                (serverApi.GetMinecraftEnum().ItemPosType.ARMOR, 1): None,
                (serverApi.GetMinecraftEnum().ItemPosType.ARMOR, 2): None,
                (serverApi.GetMinecraftEnum().ItemPosType.ARMOR, 3): None
            })

            # 设置护甲(不会清空背包,因为只设置ARMOR槽位)
            comp_item.SetPlayerAllItems(armor_slots)

            self.LogInfo("玩家{}的装备初始化完成 team={}".format(player_id, team_id))

            # [FIX 2025-11-18] 清理复活物品记录（在成功完成装备初始化后）
            # 原因：防止内存泄漏，同时确保数据在整个初始化过程中可用
            if player_id in self.respawn_contents:
                try:
                    del self.respawn_contents[player_id]
                    self.LogInfo("清理玩家{}的复活物品记录".format(player_id))
                except KeyError:
                    pass
            return True

        except Exception as e:
            self.LogError("初始化玩家{}装备失败: {}".format(player_id, str(e)))
            import traceback
            self.LogError(traceback.format_exc())
            return False

    def _apply_player_equipment_and_upgrades(self, player_id, team_id):
        """
        应用玩家装备和队伍升级效果（统一入口）

        适用场景:
        1. 游戏开始时的玩家初始化
        2. 玩家死亡后的复活
        3. 中途加入游戏的玩家

        Args:
            player_id (str): 玩家ID
            team_id (str): 队伍ID

        Returns:
            bool: 是否成功
        """
        try:
            # 1. 初始化基础装备（清空背包、发放初始装备）
            success = self._init_player_equipment(player_id, team_id)
            if not success:
                self.LogError("初始化玩家{}基础装备失败".format(player_id))
                return False

            # 2. 应用队伍升级效果（锋利、保护、生命值、急迫等）
            if team_id in self.team_upgrades:
                try:
                    upgrade_manager = self.team_upgrades[team_id]
                    # 对玩家应用所有队伍升级
                    # 注意: apply_all_to_player会应用所有升级，包括:
                    # - 生命值提升 (TeamUpgradeEntryHealth)
                    # - 盔甲保护 (TeamUpgradeEntryArmor)
                    # - 锋利利剑 (TeamUpgradeEntrySword)
                    # - 疯狂矿工急迫效果 (TeamUpgradeEntrySuperMiner)
                    # - 治愈池 (TeamUpgradeEntryHealingPool)
                    upgrade_manager.apply_all_to_player(player_id)
                    self.LogInfo("玩家{}已应用队伍{}的升级效果".format(player_id, team_id))
                except Exception as e:
                    self.LogError("应用队伍升级失败 player={} team={} error={}".format(
                        player_id, team_id, str(e)
                    ))
            else:
                self.LogWarn("队伍{}没有升级管理器".format(team_id))

            self.LogInfo("玩家{}装备和升级应用完成".format(player_id))
            return True

        except Exception as e:
            self.LogError("应用玩家{}装备和升级失败: {}".format(player_id, str(e)))
            import traceback
            self.LogError(traceback.format_exc())
            return False

    # ========== 实体创建/销毁方法 ==========

    def CreateEngineEntityByTypeStr(self, engine_type_str, pos, rot, dimension_id, is_npc=False, is_global=False):
        """
        创建引擎实体（通过类型字符串）

        [FIX 2025-11-08] 直接调用父类ServerSystem的CreateEngineEntityByTypeStr方法
        参考wiki文档: docs/mcdocs/1-ModAPI/接口/世界/实体管理.md
        CreateEngineEntityByTypeStr是ServerSystem的方法,不需要通过EngineCompFactory调用

        Args:
            engine_type_str (str): 实体类型字符串 (如 "ecbedwars:shop")
            pos (tuple): 位置 (x, y, z)
            rot (tuple): 旋转 (pitch, yaw)
            dimension_id (int): 维度ID
            is_npc (bool): 是否为NPC
            is_global (bool): 是否为全局实体

        Returns:
            str|None: 实体ID，失败返回None
        """
        try:
            # 直接调用父类ServerSystem的方法
            entity_id = super(BedWarsGameSystem, self).CreateEngineEntityByTypeStr(
                engine_type_str,
                pos,
                rot,
                dimension_id,
                is_npc,
                is_global
            )

            if entity_id:
                self.LogInfo("实体创建成功: type={} id={} pos={} dimension={}".format(
                    engine_type_str, entity_id, pos, dimension_id))
            else:
                self.LogError("CreateEngineEntityByTypeStr返回None: type={}".format(engine_type_str))

            return entity_id

        except Exception as e:
            self.LogError("创建实体异常: type={} error={}".format(engine_type_str, str(e)))
            import traceback
            self.LogError(traceback.format_exc())
            return None

    def DestroyEntity(self, entity_id):
        """
        销毁实体

        Args:
            entity_id (str): 实体ID

        Returns:
            bool: 是否成功

        注意:
        - DestroyEntity是ServerSystem的方法,不是GameComponent的方法
        - 直接调用父类的DestroyEntity方法即可
        """
        try:
            # 调用父类ServerSystem的DestroyEntity方法
            result = super(BedWarsGameSystem, self).DestroyEntity(entity_id)

            if result:
                self.LogDebug("实体销毁成功: id={}".format(entity_id))
            else:
                self.LogDebug("实体销毁失败: id={}".format(entity_id))

            return result

        except Exception as e:
            self.LogError("销毁实体异常: id={} error={}".format(entity_id, str(e)))
            import traceback
            self.LogError(traceback.format_exc())
            return False
