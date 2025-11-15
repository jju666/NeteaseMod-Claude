# -*- coding: utf-8 -*-
"""
OrnamentSystem - 饰品系统

功能:
- 管理玩家装扮(喷漆、击杀特效、胜利之舞等)
- 装扮商店UI
- 解锁/升级道具管理
- 玩家数据缓存

原文件: Parts/ECBedWarsOrnament/ECBedWarsOrnamentPart.py
重构为: systems/ornament_system/OrnamentSystem.py

注意: 这是简化版实现,包含核心框架和接口
完整功能需要后续补充
"""

import mod.server.extraServerApi as serverApi


class OrnamentSystem(object):
    """
    饰品系统

    管理玩家装扮和个性化内容
    """

    def __init__(self, bedwars_game_system):
        """
        初始化饰品系统

        Args:
            bedwars_game_system: BedWarsGameSystem实例
        """
        self.game_system = bedwars_game_system
        self.spray_manager = None  # 喷漆管理器
        self.unlock_upgrade_manager = None  # 解锁升级管理器
        self.ornament_shop = None  # 装扮商店
        self.kill_sound_manager = None  # 击杀音效管理器
        self.kill_broadcast_manager = None  # 击杀广播管理器
        self.victory_dance_manager = None  # 胜利之舞管理器
        self.bed_destroy_effect_manager = None  # 床破坏特效管理器
        self.bed_ornament_system = None  # [FIX 2025-11-05] 床装饰系统
        self.shop_npc_skin_manager = None  # 商店NPC皮肤管理器
        self.ornament_config = {}  # 装扮配置
        self.player_ornaments = {}  # 玩家装扮数据 {player_id: {...}}

        print("[INFO] [OrnamentSystem] 初始化完成")

    def initialize(self):
        """初始化饰品系统"""
        try:
            # 初始化解锁升级管理器
            from ornament.UnlockUpgradeManager import UnlockUpgradeManager
            self.unlock_upgrade_manager = UnlockUpgradeManager(self)
            self.unlock_upgrade_manager.initialize()

            # 初始化喷漆管理器
            from spray.SprayManager import SprayManager
            self.spray_manager = SprayManager(self)
            self.spray_manager.initialize()

            # 初始化装扮商店
            from ornament.OrnamentShop import OrnamentShop
            self.ornament_shop = OrnamentShop(self)
            self.ornament_shop.initialize()

            # 初始化击杀音效管理器
            from ornament.KillSoundManager import KillSoundManager
            self.kill_sound_manager = KillSoundManager(self)
            self.kill_sound_manager.initialize()

            # 初始化击杀广播管理器
            from ornament.KillBroadcastManager import KillBroadcastManager
            self.kill_broadcast_manager = KillBroadcastManager(self)
            self.kill_broadcast_manager.initialize()

            # 初始化胜利之舞管理器
            from ornament.VictoryDanceManager import VictoryDanceManager
            self.victory_dance_manager = VictoryDanceManager(self)
            self.victory_dance_manager.initialize()

            # 初始化床破坏特效管理器
            from ornament.BedDestroyEffectManager import BedDestroyEffectManager
            self.bed_destroy_effect_manager = BedDestroyEffectManager(self)
            self.bed_destroy_effect_manager.initialize()

            # [FIX 2025-11-05] 初始化床装饰系统
            from ornament.BedOrnamentSystem import BedOrnamentSystem
            self.bed_ornament_system = BedOrnamentSystem(self.game_system)
            self.bed_ornament_system.initialize()

            # 初始化商店NPC皮肤管理器
            from ornament.ShopNPCSkinManager import ShopNPCSkinManager
            self.shop_npc_skin_manager = ShopNPCSkinManager(self)
            self.shop_npc_skin_manager.initialize()

            # 加载装扮配置
            self._load_ornament_config()

            # 注册事件监听
            self._register_events()

            print("[INFO] [OrnamentSystem] 系统初始化成功")
        except Exception as e:
            print("[ERROR] [OrnamentSystem] 初始化失败: {}".format(str(e)))

    def cleanup(self):
        """清理饰品系统"""
        try:
            if self.spray_manager:
                self.spray_manager.cleanup()

            if self.unlock_upgrade_manager:
                self.unlock_upgrade_manager.cleanup()

            if self.ornament_shop:
                self.ornament_shop.cleanup()

            if self.kill_sound_manager:
                self.kill_sound_manager.cleanup()

            if self.kill_broadcast_manager:
                self.kill_broadcast_manager.cleanup()

            if self.victory_dance_manager:
                self.victory_dance_manager.cleanup()

            if self.bed_destroy_effect_manager:
                self.bed_destroy_effect_manager.cleanup()

            # [FIX 2025-11-05] 清理床装饰系统
            if self.bed_ornament_system:
                self.bed_ornament_system.cleanup()

            if self.shop_npc_skin_manager:
                self.shop_npc_skin_manager.cleanup()

            self.player_ornaments = {}
            print("[INFO] [OrnamentSystem] 清理完成")
        except Exception as e:
            print("[ERROR] [OrnamentSystem] 清理失败: {}".format(str(e)))

    def _load_ornament_config(self):
        """加载装扮配置（从配置文件）"""
        try:
            # 导入配置模块
            from Script_NeteaseMod.config import ornament_config

            # 加载击杀音效配置
            self.kill_sounds = ornament_config.KILL_SOUND_CONFIG
            print("[INFO] [OrnamentSystem] 加载击杀音效配置: {} 个".format(len(self.kill_sounds)))

            # 加载击杀广播配置
            self.kill_broadcasts = ornament_config.KILL_BROADCAST_CONFIG
            print("[INFO] [OrnamentSystem] 加载击杀广播配置: {} 个".format(len(self.kill_broadcasts)))

            # 加载胜利舞蹈配置
            self.victory_dances = ornament_config.VICTORY_DANCE_CONFIG
            print("[INFO] [OrnamentSystem] 加载胜利舞蹈配置: {} 个".format(len(self.victory_dances)))

            # 加载Meme特效配置
            self.meme_effects = ornament_config.MEME_CONFIG
            print("[INFO] [OrnamentSystem] 加载Meme特效配置: {} 个".format(len(self.meme_effects)))

            # 加载喷漆配置
            self.sprays = ornament_config.SPRAY_CONFIG
            print("[INFO] [OrnamentSystem] 加载喷漆配置: {} 个".format(len(self.sprays)))

            # 加载床破坏特效配置
            self.bed_destroy_effects = ornament_config.BED_DESTROY_EFFECT_CONFIG
            print("[INFO] [OrnamentSystem] 加载床破坏特效配置: {} 个".format(len(self.bed_destroy_effects)))

            # 兼容旧代码，保留ornament_config字典
            self.ornament_config = {
                "kill_sound": self.kill_sounds,
                "kill_broadcast": self.kill_broadcasts,
                "victory_dance": self.victory_dances,
                "meme_effect": self.meme_effects,
                "spray": self.sprays,
                "bed_destroy_effect": self.bed_destroy_effects
            }

            print("[INFO] [OrnamentSystem] 装扮配置加载成功，共 {} 种装扮类型".format(len(self.ornament_config)))

        except Exception as e:
            print("[ERROR] [OrnamentSystem] 加载配置失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

            # 使用默认配置
            self._load_default_ornament_config()

    def _load_default_ornament_config(self):
        """加载默认装扮配置（降级方案）"""
        print("[WARN] [OrnamentSystem] 使用默认装扮配置")

        self.kill_sounds = {"default": {"id": "default", "name": u"默认", "sounds": ["random.orb"], "price": 0}}
        self.victory_dances = {"default": {"id": "default", "name": u"默认", "effect_type": "default", "price": 0}}
        self.meme_effects = {"default": {"id": "default", "name": u"默认", "pickup_sound": "random.levelup", "price": 0}}
        self.sprays = {"default": {"id": "default", "name": u"默认喷漆", "variant": 0, "price": 0}}
        self.bed_destroy_effects = {"default": {"id": "default", "name": u"默认", "effect_type": "default", "price": 0}}

        self.ornament_config = {
            "kill_sound": self.kill_sounds,
            "victory_dance": self.victory_dances,
            "meme_effect": self.meme_effects,
            "spray": self.sprays,
            "bed_destroy_effect": self.bed_destroy_effects
        }

    def _register_events(self):
        """注册事件监听"""
        # 玩家加入事件
        self.game_system.ListenForEvent(
            serverApi.GetEngineNamespace(),
            serverApi.GetEngineSystemName(),
            'AddServerPlayerEvent',
            self,
            self.on_player_join
        )

        # 玩家离开事件
        self.game_system.ListenForEvent(
            serverApi.GetEngineNamespace(),
            serverApi.GetEngineSystemName(),
            'RemoveServerPlayerEvent',
            self,
            self.on_player_leave
        )

        # 注意：打开装扮商店不使用事件监听
        # 直接由StageWaitingState调用open_ornament_shop()方法
        # 原因：OrnamentSystem不是预设,无法通过ECPreset EventBus接收事件
        # 修复日期: 2025-11-06

    # ========== 事件处理 ==========

    def on_player_join(self, args):
        """
        玩家加入事件

        Args:
            args: {'id': player_id}
        """
        player_id = args.get('id')
        if not player_id:
            return

        # 初始化玩家装扮数据
        self.player_ornaments[player_id] = {
            "spray": None,
            "kill_effect": None,
            "victory_dance": None,
            "shop_npc_skin": None,
            "unlocked_items": []
        }

        # 加载玩家解锁数据（旧方法，临时保留）
        if self.unlock_upgrade_manager:
            self.unlock_upgrade_manager.load_player_data(player_id)

        # 加载玩家装扮数据（从LobbyAPI加载）
        if self.unlock_upgrade_manager:
            self.unlock_upgrade_manager.load_player_ornaments(player_id)

        print("[INFO] [OrnamentSystem] 玩家 {} 装扮数据已初始化".format(player_id))

    def on_player_leave(self, args):
        """
        玩家离开事件

        Args:
            args: {'id': player_id}
        """
        player_id = args.get('id')

        # 保存玩家数据（旧方法，临时保留）
        if self.unlock_upgrade_manager:
            self.unlock_upgrade_manager.save_player_data(player_id)

        # 保存玩家装扮数据（到LobbyAPI）
        if self.unlock_upgrade_manager:
            self.unlock_upgrade_manager.save_player_ornaments(player_id)

        # 清理玩家喷漆
        if self.spray_manager:
            self.spray_manager.clear_player_sprays(player_id)

        if player_id in self.player_ornaments:
            del self.player_ornaments[player_id]

    # ========== 装扮商店 ==========

    def open_ornament_shop(self, player_id):
        """
        打开装扮商店

        Args:
            player_id (str): 玩家ID
        """
        if self.ornament_shop:
            self.ornament_shop.open_shop(player_id)
        else:
            print("[WARN] [OrnamentSystem] 装扮商店未初始化")

    # ========== 胜利之舞 ==========

    def start_victory_dance(self, player_scores):
        """
        启动胜利之舞

        Args:
            player_scores (list): 玩家积分列表,按排名排序
                格式: [{'player_id': str, 'score': int, 'pos': (x, y, z)}, ...]
        """
        if not self.victory_dance_manager:
            print("[WARN] [OrnamentSystem] 胜利之舞管理器未初始化")
            return

        self.victory_dance_manager.play_victory_dance(player_scores)

    # ========== 击杀音效 ==========

    def play_kill_sound(self, killer_id, victim_id, death_pos):
        """
        播放击杀音效

        Args:
            killer_id (str): 击杀者ID
            victim_id (str): 受害者ID
            death_pos (tuple): 死亡位置 (x, y, z)
        """
        if not self.kill_sound_manager:
            print("[WARN] [OrnamentSystem] 击杀音效管理器未初始化")
            return

        self.kill_sound_manager.play_kill_sound(killer_id, victim_id, death_pos)

    def get_kill_broadcast_message(self, killer_id, victim_colored_name, killer_colored_name, kill_count=None):
        """
        获取击杀广播消息（装扮系统）

        如果玩家装备了自定义击杀广播装扮，则返回自定义消息；
        否则返回None，使用默认消息

        Args:
            killer_id (str): 击杀者ID
            victim_colored_name (str): 被击杀玩家带颜色的名称
            killer_colored_name (str): 击杀者带颜色的名称
            kill_count (int): 击杀次数(可选,用于count-package)

        Returns:
            str: 自定义击杀广播消息，或None（使用默认消息）
        """
        if not self.kill_broadcast_manager:
            print("[WARN] [OrnamentSystem] 击杀广播管理器未初始化")
            return None

        return self.kill_broadcast_manager.get_kill_broadcast_message(
            killer_id,
            victim_colored_name,
            killer_colored_name,
            kill_count
        )

    # ========== 床破坏特效 ==========

    def play_bed_destroy_effect(self, destroyer_id, bed_pos, team_id):
        """
        播放床破坏特效

        Args:
            destroyer_id (str): 破坏者ID
            bed_pos (tuple): 床位置 (x, y, z)
            team_id (str): 队伍ID
        """
        if not self.bed_destroy_effect_manager:
            print("[WARN] [OrnamentSystem] 床破坏特效管理器未初始化")
            return

        self.bed_destroy_effect_manager.play_bed_destroy_effect(destroyer_id, bed_pos, team_id)

    def play_pickup_meme_effect(self, player_id, item_name):
        """
        播放拾取钻石/绿宝石时的meme特效音效

        功能:
        - 检查玩家是否装备了"meme"类型装饰
        - 如果装备了，在玩家位置播放特效

        参考: 老项目 BedWarsRunningState.py:936-943

        Args:
            player_id (str): 玩家ID
            item_name (str): 拾取的物品名称(minecraft:diamond/emerald)
        """
        # 检查玩家是否装备了meme装饰
        meme_ornament = self.get_player_ornament(player_id, "meme")
        if not meme_ornament:
            return

        try:
            # 获取玩家位置
            comp_pos = serverApi.GetEngineCompFactory().CreatePos(player_id)
            player_pos = comp_pos.GetPos()
            if not player_pos:
                return

            # 获取玩家维度
            comp_dim = serverApi.GetEngineCompFactory().CreateDimension(player_id)
            dimension_id = comp_dim.GetPlayerDimensionId()

            # 特效生成位置（玩家上方1格）
            effect_pos = (player_pos[0], player_pos[1] + 1, player_pos[2])

            # === 1. 播放音效 ===
            comp_game = serverApi.GetEngineCompFactory().CreateGame(serverApi.GetLevelId())

            if item_name == 'minecraft:diamond':
                # 钻石音效（高音）
                sound_name = "random.levelup"
                pitch = 1.5
                title = u"§b§l钻石！"
                subtitle = u"§7+1 钻石"
                particle_color = (60 / 255.0, 253 / 255.0, 255 / 255.0)  # 青色
            else:  # minecraft:emerald
                # 绿宝石音效（更高音）
                sound_name = "random.levelup"
                pitch = 2.0
                title = u"§a§l绿宝石！"
                subtitle = u"§7+1 绿宝石"
                particle_color = (40 / 255.0, 255 / 255.0, 52 / 255.0)  # 绿色

            # 播放音效（只对玩家本人）
            comp_game.PlaySound(effect_pos, sound_name, 1.0, pitch, False, player_id)

            # === 2. 生成粒子特效 ===
            # 使用村民高兴粒子形成环绕效果
            if hasattr(self.game_system, 'particle_manager') and self.game_system.particle_manager:
                try:
                    import math

                    # 生成多个粒子形成环绕效果
                    particle_count = 8
                    radius = 0.5

                    for i in range(particle_count):
                        angle = (2 * math.pi * i) / particle_count

                        # 计算粒子位置（围绕玩家）
                        particle_pos = [
                            effect_pos[0] + radius * math.cos(angle),
                            effect_pos[1],
                            effect_pos[2] + radius * math.sin(angle)
                        ]

                        # 发送粒子到客户端（只向拾取者显示）
                        self.game_system.particle_manager.spawn_particle(
                            "minecraft:villager_happy",  # 粒子类型
                            particle_pos,
                            players=[player_id],
                            variables={
                                "variable.color_r": particle_color[0],
                                "variable.color_g": particle_color[1],
                                "variable.color_b": particle_color[2]
                            }
                        )

                except Exception as e:
                    print("[ERROR] [OrnamentSystem] 生成粒子失败: {}".format(str(e)))

            # === 3. 显示Title提示 ===
            try:
                comp_game.SetNotifyMsg(
                    player_id,
                    title,
                    subtitle
                )
            except Exception as e:
                print("[ERROR] [OrnamentSystem] 显示Title失败: {}".format(str(e)))

            print("[INFO] [OrnamentSystem] 播放完整meme特效: player={} item={}".format(
                player_id, item_name
            ))

        except Exception as e:
            print("[ERROR] [OrnamentSystem] 播放meme特效失败: player={} error={}".format(
                player_id, str(e)
            ))
            import traceback
            traceback.print_exc()

    # ========== 更新方法 ==========

    def update(self):
        """
        更新饰品系统 - 需要在游戏主循环中调用
        主要用于更新特效定时器
        """
        if self.victory_dance_manager:
            self.victory_dance_manager.update()

        # 床破坏特效管理器使用同一个定时器,不需要单独update

    # ========== 游戏事件处理 ==========

    def on_game_starting(self, dimension):
        """
        游戏开始时调用

        Args:
            dimension (int): 游戏所在维度ID
        """
        # 清理该维度的所有喷漆
        if self.spray_manager:
            self.spray_manager.clear_dimension_sprays(dimension)
            print("[INFO] [OrnamentSystem] 游戏开始，清理维度 {} 的喷漆".format(dimension))

    def on_game_ending(self, dimension):
        """
        游戏结束时调用

        Args:
            dimension (int): 游戏所在维度ID
        """
        # 清理该维度的所有喷漆
        if self.spray_manager:
            self.spray_manager.clear_dimension_sprays(dimension)
            print("[INFO] [OrnamentSystem] 游戏结束，清理维度 {} 的喷漆".format(dimension))

    # ========== 商店NPC皮肤 ==========

    def apply_shop_npc_skin(self, npc_entity_id, npc_type, team_id):
        """
        应用商店NPC皮肤
        [P2-9 FIX] 返回元组(是否成功, NPC名称)，用于显示感谢消息

        Args:
            npc_entity_id (str): NPC实体ID
            npc_type (str): NPC类型 ("default_shop" 或 "upgrade_shop")
            team_id (str): 队伍ID

        Returns:
            tuple: (bool是否成功应用皮肤, str NPC名称)
        """
        if not self.shop_npc_skin_manager:
            print("[WARN] [OrnamentSystem] 商店NPC皮肤管理器未初始化")
            return False, "商人"

        return self.shop_npc_skin_manager.apply_npc_skin(npc_entity_id, npc_type, team_id)

    # ========== 工具方法 ==========

    def get_player_ornament(self, player_id, ornament_type):
        """
        获取玩家装备的装扮

        Args:
            player_id (str): 玩家ID
            ornament_type (str): 装扮类型(spray/kill_effect/victory_dance)

        Returns:
            str: 装扮ID,如果未装备则返回None
        """
        if player_id not in self.player_ornaments:
            return None

        return self.player_ornaments[player_id].get(ornament_type)

    def set_player_ornament(self, player_id, ornament_type, ornament_id):
        """
        设置玩家装备的装扮

        Args:
            player_id (str): 玩家ID
            ornament_type (str): 装扮类型
            ornament_id (str): 装扮ID
        """
        if player_id not in self.player_ornaments:
            self.player_ornaments[player_id] = {}

        self.player_ornaments[player_id][ornament_type] = ornament_id
        print("[INFO] [OrnamentSystem] 玩家 {} 装备 {} = {}".format(
            player_id, ornament_type, ornament_id        ))
