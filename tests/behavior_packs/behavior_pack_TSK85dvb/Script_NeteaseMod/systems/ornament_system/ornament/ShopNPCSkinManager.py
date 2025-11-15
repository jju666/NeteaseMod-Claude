# -*- coding: utf-8 -*-
"""
ShopNPCSkinManager - 商店NPC皮肤管理器

功能:
- 加载商店NPC皮肤配置
- 应用NPC皮肤（variant设置）
- 支持玩家纹理克隆
- 根据队伍玩家装备选择NPC皮肤

原文件: Parts/ECBedWarsOrnament/ornament/BedWarsOrnamentShopNPCSkin.py
重构为: systems/ornament_system/ornament/ShopNPCSkinManager.py
"""

import mod.server.extraServerApi as serverApi
import json
import random


class ShopNPCSkinManager(object):
    """
    商店NPC皮肤管理器

    管理商店NPC的外观皮肤配置和应用
    """

    def __init__(self, ornament_system):
        """
        初始化商店NPC皮肤管理器

        Args:
            ornament_system: OrnamentSystem实例
        """
        self.ornament_system = ornament_system
        self.game_system = ornament_system.game_system
        self.config = {}  # 配置数据
        self.npc_variants = {}  # variant映射
        self.shop_npc_skins = []  # NPC皮肤列表

        print("[INFO] [ShopNPCSkinManager] 初始化完成")

    def initialize(self):
        """初始化管理器"""
        try:
            # 加载配置
            self.load_config()

            print("[INFO] [ShopNPCSkinManager] 管理器初始化成功")
        except Exception as e:
            print("[ERROR] [ShopNPCSkinManager] 初始化失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def cleanup(self):
        """清理管理器"""
        try:
            self.config = {}
            self.npc_variants = {}
            self.shop_npc_skins = []

            print("[INFO] [ShopNPCSkinManager] 清理完成")
        except Exception as e:
            print("[ERROR] [ShopNPCSkinManager] 清理失败: {}".format(str(e)))

    def load_config(self):
        """
        加载商店NPC皮肤配置

        从 config/shop_npc_skin_config.json 读取配置
        """
        try:
            import os

            # 获取配置文件路径
            config_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            config_path = os.path.join(config_dir, 'config', 'shop_npc_skin_config.json')

            # 读取配置文件
            if not os.path.exists(config_path):
                print("[WARN] [ShopNPCSkinManager] 配置文件不存在: {}".format(config_path))
                self._load_default_config()
                return

            with open(config_path, 'r') as f:
                self.config = json.load(f)

            # 解析配置
            self.npc_variants = self.config.get('npc_variants', {})
            self.shop_npc_skins = self.config.get('shop_npc_skins', [])

            print("[INFO] [ShopNPCSkinManager] 配置加载成功: {} 种NPC皮肤".format(
                len(self.shop_npc_skins)))

        except Exception as e:
            print("[ERROR] [ShopNPCSkinManager] 加载配置失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

            # 使用默认配置
            self._load_default_config()

    def _load_default_config(self):
        """加载默认配置（降级方案）"""
        print("[WARN] [ShopNPCSkinManager] 使用默认配置")

        self.npc_variants = {
            "villager": 0,
            "zombie": 20,
            "skeleton": 21
        }

        self.shop_npc_skins = [
            {
                "id": "default",
                "name": "村民",
                "price": 0,
                "unlocked_by_default": True,
                "npc_configs": {
                    "default_shop": {
                        "variant": 0,
                        "clone_player_texture": False
                    },
                    "upgrade_shop": {
                        "variant": 0,
                        "clone_player_texture": False
                    }
                }
            }
        ]

    def apply_npc_skin(self, npc_entity_id, npc_type, team_id):
        """
        应用NPC皮肤
        [P2-9 FIX] 返回元组(是否成功, NPC名称)，用于显示感谢消息

        根据队伍中玩家装备的NPC皮肤设置NPC外观

        Args:
            npc_entity_id (str): NPC实体ID
            npc_type (str): NPC类型 ("default_shop" 或 "upgrade_shop")
            team_id (str): 队伍ID

        Returns:
            tuple: (bool是否成功应用皮肤, str NPC名称)
        """
        try:
            # 1. 获取队伍中的玩家列表
            team_players = self._get_team_players(team_id)

            # 2. 选择NPC皮肤配置
            if not team_players:
                # 队伍无玩家，使用默认皮肤
                skin_config = self._get_default_npc_skin_config()
                selected_player_id = None
            else:
                # [P0-1 FIX] 修复随机皮肤选择逻辑：收集所有已装备皮肤的玩家
                equipped_players = []
                equipped_configs = []

                for player_id in team_players:
                    player_skin_config = self._get_player_npc_skin_config(player_id)
                    if player_skin_config:
                        equipped_players.append(player_id)
                        equipped_configs.append(player_skin_config)

                # 如果有玩家装备了NPC皮肤，从中随机选择
                if equipped_players:
                    random_index = random.randint(0, len(equipped_players) - 1)
                    selected_player_id = equipped_players[random_index]
                    skin_config = equipped_configs[random_index]
                else:
                    # 没有玩家装备NPC皮肤，使用默认皮肤
                    selected_player_id = None
                    skin_config = self._get_default_npc_skin_config()

            if not skin_config:
                print("[ERROR] [ShopNPCSkinManager] 无法获取NPC皮肤配置")
                return False, "商人"

            # 3. 获取对应类型的NPC配置
            npc_config = skin_config.get('npc_configs', {}).get(npc_type)

            if not npc_config:
                print("[ERROR] [ShopNPCSkinManager] 未找到NPC类型配置: {}".format(npc_type))
                return False, "商人"

            # 4. 应用variant
            variant = npc_config.get('variant', 0)
            self._set_npc_variant(npc_entity_id, variant)

            # 5. 如果需要克隆玩家纹理
            if npc_config.get('clone_player_texture', False):
                if selected_player_id:
                    self._clone_player_texture(npc_entity_id, selected_player_id)
                else:
                    print("[WARN] [ShopNPCSkinManager] 需要克隆玩家纹理但无玩家可用")

            # [P2-9 FIX] 获取NPC名称
            npc_name = skin_config.get('name', '商人')

            print("[INFO] [ShopNPCSkinManager] NPC皮肤应用成功: npc={}, type={}, team={}, skin={}, variant={}, name={}".format(
                npc_entity_id, npc_type, team_id, skin_config.get('id'), variant, npc_name))

            return True, npc_name

        except Exception as e:
            print("[ERROR] [ShopNPCSkinManager] 应用NPC皮肤失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()
            return False, "商人"

    def _get_team_players(self, team_id):
        """
        获取队伍中的玩家列表

        Args:
            team_id (str): 队伍ID

        Returns:
            list: 玩家ID列表
        """
        try:
            # 从游戏系统获取队伍模块
            if not hasattr(self.game_system, 'team_module') or not self.game_system.team_module:
                print("[WARN] [ShopNPCSkinManager] 队伍模块未初始化")
                return []

            team_module = self.game_system.team_module

            # 获取队伍玩家
            team_players = team_module.get_team_players(team_id)

            return team_players if team_players else []

        except Exception as e:
            print("[ERROR] [ShopNPCSkinManager] 获取队伍玩家失败: {}".format(str(e)))
            return []

    def _get_player_npc_skin_config(self, player_id):
        """
        获取玩家装备的NPC皮肤配置

        Args:
            player_id (str): 玩家ID

        Returns:
            dict: NPC皮肤配置，如果未装备返回None
        """
        try:
            # 从玩家装扮数据中读取（通过OrnamentSystem）
            if not hasattr(self.ornament_system, 'player_ornaments'):
                return None

            player_ornaments = self.ornament_system.player_ornaments.get(player_id, {})
            skin_id = player_ornaments.get('shop_npc_skin')

            if not skin_id:
                return None

            # 从配置中查找
            for skin in self.shop_npc_skins:
                if skin.get('id') == skin_id:
                    return skin

            return None

        except Exception as e:
            print("[ERROR] [ShopNPCSkinManager] 获取玩家NPC皮肤配置失败: {}".format(str(e)))
            return None

    def _get_default_npc_skin_config(self):
        """
        获取默认NPC皮肤配置

        Returns:
            dict: 默认NPC皮肤配置
        """
        # 查找id为"default"的皮肤
        for skin in self.shop_npc_skins:
            if skin.get('id') == 'default':
                return skin

        # 如果没有找到，返回第一个
        if self.shop_npc_skins:
            return self.shop_npc_skins[0]

        return None

    def _set_npc_variant(self, npc_entity_id, variant):
        """
        设置NPC的variant值
        [P0-1 FIX] 当variant=0时(默认村民),随机应用村民职业皮肤

        Args:
            npc_entity_id (str): NPC实体ID
            variant (int): variant值
        """
        try:
            comp_factory = serverApi.GetEngineCompFactory()

            # [P0-1 FIX] 当variant=0时,随机应用村民职业皮肤
            if variant == 0:
                # 使用SetMarkVariant随机设置村民职业和生物群系
                # biome: 0-5 (6种生物群系: 平原、沙漠、草原、雪地、丛林、沼泽)
                # profession: 0-13 (14种职业)
                biome = random.randrange(0, 6)
                profession = random.randrange(0, 14)
                random_variant = biome * 100 + profession

                # 使用EntityDefinitions组件的SetMarkVariant方法
                entity_def_comp = comp_factory.CreateEntityDefinitions(npc_entity_id)
                if entity_def_comp:
                    entity_def_comp.SetMarkVariant(random_variant)
                    print("[INFO] [ShopNPCSkinManager] 设置NPC随机村民职业: npc={}, biome={}, profession={}, mark_variant={}".format(
                        npc_entity_id, biome, profession, random_variant))
                else:
                    print("[WARN] [ShopNPCSkinManager] 无法创建EntityDefinitions组件: {}".format(npc_entity_id))
            else:
                # 使用自定义variant
                variant_comp = comp_factory.CreateVariant(npc_entity_id)
                if variant_comp:
                    variant_comp.SetVariant(variant)
                    print("[INFO] [ShopNPCSkinManager] 设置NPC variant: npc={}, variant={}".format(
                        npc_entity_id, variant))
                else:
                    print("[WARN] [ShopNPCSkinManager] 无法创建variant组件: {}".format(npc_entity_id))

        except Exception as e:
            print("[ERROR] [ShopNPCSkinManager] 设置NPC variant失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _clone_player_texture(self, npc_entity_id, player_id):
        """
        克隆玩家纹理到NPC

        将玩家的皮肤应用到NPC实体上

        Args:
            npc_entity_id (str): NPC实体ID
            player_id (str): 玩家ID
        """
        try:
            comp_factory = serverApi.GetEngineCompFactory()

            # 获取玩家皮肤
            player_skin_comp = comp_factory.CreatePlayerSkin(player_id)

            if not player_skin_comp:
                print("[WARN] [ShopNPCSkinManager] 无法获取玩家皮肤组件: {}".format(player_id))
                return

            skin_id = player_skin_comp.GetSkinId()

            if not skin_id:
                print("[WARN] [ShopNPCSkinManager] 玩家皮肤ID为空: {}".format(player_id))
                return

            # 应用到NPC
            npc_skin_comp = comp_factory.CreatePlayerSkin(npc_entity_id)

            if npc_skin_comp:
                npc_skin_comp.SetSkinId(skin_id)
                print("[INFO] [ShopNPCSkinManager] 克隆玩家纹理成功: npc={}, player={}, skin={}".format(
                    npc_entity_id, player_id, skin_id))
            else:
                print("[WARN] [ShopNPCSkinManager] 无法创建NPC皮肤组件: {}".format(npc_entity_id))

        except Exception as e:
            print("[ERROR] [ShopNPCSkinManager] 克隆玩家纹理失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    # ========== 工具方法 ==========

    def get_all_npc_skins(self):
        """
        获取所有NPC皮肤配置

        Returns:
            list: NPC皮肤配置列表
        """
        return self.shop_npc_skins

    def get_npc_skin_by_id(self, skin_id):
        """
        根据ID获取NPC皮肤配置

        Args:
            skin_id (str): 皮肤ID

        Returns:
            dict: NPC皮肤配置，如果不存在返回None
        """
        for skin in self.shop_npc_skins:
            if skin.get('id') == skin_id:
                return skin
        return None

    def is_skin_unlocked(self, player_id, skin_id):
        """
        检查玩家是否解锁了指定NPC皮肤

        Args:
            player_id (str): 玩家ID
            skin_id (str): 皮肤ID

        Returns:
            bool: 是否已解锁
        """
        try:
            # 检查是否默认解锁
            skin_config = self.get_npc_skin_by_id(skin_id)
            if not skin_config:
                return False

            if skin_config.get('unlocked_by_default', False):
                return True

            # 从玩家解锁数据检查
            if not hasattr(self.ornament_system, 'player_ornaments'):
                return False

            player_ornaments = self.ornament_system.player_ornaments.get(player_id, {})
            unlocked_items = player_ornaments.get('unlocked_items', [])

            # 完整装饰ID为 "shop_npc_skin.{skin_id}"
            ornament_id = "shop_npc_skin.{}".format(skin_id)

            return ornament_id in unlocked_items

        except Exception as e:
            print("[ERROR] [ShopNPCSkinManager] 检查皮肤解锁状态失败: {}".format(str(e)))
            return False
