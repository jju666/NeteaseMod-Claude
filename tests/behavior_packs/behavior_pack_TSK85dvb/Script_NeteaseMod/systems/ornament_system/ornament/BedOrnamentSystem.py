# -*- coding: utf-8 -*-
"""
BedOrnamentSystem - 床装饰系统

功能:
- 加载床装饰配置
- 在游戏开始时为队伍生成床装饰
- 支持队伍颜色变体
- 床被破坏时销毁装饰实体

配置文件: config/ornaments/bed_ornament.json
"""

import mod.server.extraServerApi as serverApi
import json
import random
import os


class BedOrnamentSystem(object):
    """
    床装饰系统

    职责:
    - 管理床装饰配置
    - 从队伍玩家中随机选择一个玩家的床饰
    - 创建床装饰实体
    - 支持队伍颜色变体(mark_variant_by_team)
    - 销毁床装饰实体
    """

    def __init__(self, game_system):
        """
        初始化床装饰系统

        Args:
            game_system: BedWarsGameSystem实例
        """
        self.game_system = game_system
        self.config = {}  # 床装饰配置 {ornament_id: config_dict}
        self.team_bed_entities = {}  # 队伍床装饰实体 {team_id: entity_id}

        print("[INFO] [BedOrnamentSystem] 初始化完成")

    def initialize(self):
        """初始化系统"""
        try:
            # 加载配置文件
            self._load_config()

            print("[INFO] [BedOrnamentSystem] 加载了 {} 个床装饰配置".format(len(self.config)))
        except Exception as e:
            print("[ERROR] [BedOrnamentSystem] 初始化失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def cleanup(self):
        """清理系统"""
        try:
            # 销毁所有床装饰实体
            for team_id in list(self.team_bed_entities.keys()):
                self.destroy_bed_ornament(team_id)

            print("[INFO] [BedOrnamentSystem] 清理完成")
        except Exception as e:
            print("[ERROR] [BedOrnamentSystem] 清理失败: {}".format(str(e)))

    def _load_config(self):
        """
        加载床装饰配置文件

        配置文件路径: config/ornaments/bed_ornament.json
        """
        try:
            # 获取配置文件路径
            # 注意: 网易开发环境中, 配置文件在行为包目录下
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
                'config', 'ornaments', 'bed_ornament.json'
            )

            print("[INFO] [BedOrnamentSystem] 加载配置文件: {}".format(config_path))

            # 读取配置文件
            if not os.path.exists(config_path):
                print("[WARN] [BedOrnamentSystem] 配置文件不存在: {}".format(config_path))
                # 使用默认配置
                self._load_default_config()
                return

            with open(config_path, 'r') as f:
                data = json.load(f)

            # 解析配置
            ornaments = data.get('bed_ornaments', [])
            for ornament in ornaments:
                ornament_id = ornament.get('id')
                if ornament_id:
                    self.config[ornament_id] = ornament

            print("[INFO] [BedOrnamentSystem] 配置加载完成: {} 个床装饰".format(len(self.config)))

        except Exception as e:
            print("[ERROR] [BedOrnamentSystem] 配置加载失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()
            # 使用默认配置
            self._load_default_config()

    def _load_default_config(self):
        """加载默认配置"""
        print("[INFO] [BedOrnamentSystem] 使用默认配置")
        self.config = {
            "bed-ornament.default": {
                "id": "bed-ornament.default",
                "name": "默认无装饰",
                "entity_type": "ecbedwars:bed_ornament",
                "variant": 0,
                "mark_variant": 0,
                "scale": 1.0,
                "team_color_support": False,
                "default": True
            }
        }

    def spawn_bed_ornament(self, team_id, bed_pos, yaw, dimension):
        """
        生成床装饰

        逻辑:
        1. 从队伍中选择装备最贵床饰的玩家(基于价格优先级)
        2. 获取玩家装备的床饰配置
        3. 创建床装饰实体
        4. 设置variant、mark_variant、scale

        优先级规则:
        - 活动限定装饰(-1价格) > 碎片装饰 > 金币装饰
        - 同价格时随机选择一个玩家
        - 所有玩家都是默认装饰时不创建实体

        Args:
            team_id (str): 队伍ID (RED, BLUE, GREEN, YELLOW等)
            bed_pos (tuple): 床位置 (x, y, z)
            yaw (float): 朝向角度
            dimension (int): 维度ID

        Returns:
            str | None: 生成的实体ID, 失败返回None
        """
        try:
            print("[INFO] [BedOrnamentSystem] 为队伍 {} 生成床装饰".format(team_id))

            # 1. 从队伍中基于价格优先级选择玩家
            team_module = self.game_system.team_module
            if not team_module:
                print("[WARN] [BedOrnamentSystem] 队伍模块未初始化")
                return None

            team_players = team_module.get_team_players(team_id)
            if not team_players or len(team_players) == 0:
                print("[WARN] [BedOrnamentSystem] 队伍 {} 没有玩家".format(team_id))
                return None

            # 基于价格优先级选择玩家
            ornament_system = self.game_system.ornament_system
            if not ornament_system:
                print("[WARN] [BedOrnamentSystem] 装饰系统未初始化")
                return None

            max_price = -1
            candidates = []  # 价格最高的玩家列表

            for player_id in team_players:
                # 获取玩家装备的床装饰ID
                player_ornaments = ornament_system.player_ornaments.get(player_id, {})
                ornament_id = player_ornaments.get('bed-ornament')

                if not ornament_id:
                    continue

                price_value = self._get_ornament_price_value(ornament_id)

                if price_value > max_price:
                    max_price = price_value
                    candidates = [player_id]
                elif price_value == max_price and price_value > 0:
                    candidates.append(player_id)

            # 如果没有找到有效装饰,返回None
            if not candidates or max_price == 0:
                print("[INFO] [BedOrnamentSystem] 队伍 {} 所有玩家都使用默认装饰".format(team_id))
                return None

            # 从价格最高的玩家中随机选择一个
            selected_player_id = random.choice(candidates)
            print("[INFO] [BedOrnamentSystem] 选择玩家 {} 的床饰 (价格值: {}, 候选人数: {})".format(
                selected_player_id, max_price, len(candidates)))

            # 2. 获取玩家装备的床饰配置
            ornament_config = self._get_player_bed_ornament_config(selected_player_id)
            if not ornament_config:
                print("[WARN] [BedOrnamentSystem] 玩家 {} 没有装备床饰, 使用默认配置".format(selected_player_id))
                ornament_config = self._get_default_bed_ornament_config()

            # 如果是默认配置,不创建实体
            if ornament_config.get('default', False):
                print("[INFO] [BedOrnamentSystem] 使用默认床饰,不创建装饰实体")
                return None

            # 3. 创建床装饰实体
            entity_id = self._create_bed_entity(ornament_config, team_id, bed_pos, yaw, dimension)

            if entity_id:
                # 记录实体ID
                self.team_bed_entities[team_id] = entity_id
                print("[INFO] [BedOrnamentSystem] 床装饰创建成功: entity_id={}".format(entity_id))

            return entity_id

        except Exception as e:
            print("[ERROR] [BedOrnamentSystem] 生成床装饰失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()
            return None

    def _get_player_bed_ornament_config(self, player_id):
        """
        获取玩家装备的床饰配置

        Args:
            player_id (str): 玩家ID

        Returns:
            dict | None: 床饰配置, 未装备返回None
        """
        try:
            # 从OrnamentSystem获取玩家装备数据
            ornament_system = self.game_system.ornament_system
            if not ornament_system:
                return None

            # 获取玩家装扮数据
            player_ornaments = ornament_system.player_ornaments.get(player_id, {})
            equipped_bed_ornament = player_ornaments.get('bed-ornament')

            if equipped_bed_ornament:
                # 获取配置
                ornament_id = equipped_bed_ornament
                return self.config.get(ornament_id)

            return None

        except Exception as e:
            print("[ERROR] [BedOrnamentSystem] 获取玩家床饰配置失败: {}".format(str(e)))
            return None

    def _get_default_bed_ornament_config(self):
        """
        获取默认床饰配置

        Returns:
            dict: 默认床饰配置
        """
        return self.config.get("bed-ornament.default", {
            "id": "bed-ornament.default",
            "name": "默认无装饰",
            "entity_type": "ecbedwars:bed_ornament",
            "variant": 0,
            "mark_variant": 0,
            "scale": 1.0,
            "team_color_support": False,
            "default": True
        })

    def _get_ornament_price_value(self, ornament_id):
        """
        从配置中获取装饰的价格数值(用于优先级比较)

        Args:
            ornament_id (str): 装饰ID

        Returns:
            int: 价格数值,数值越大优先级越高
        """
        try:
            from Script_NeteaseMod.config import ornament_config

            bed_config = ornament_config.BED_ORNAMENT_CONFIG.get(ornament_id)
            if not bed_config:
                return 0

            price = bed_config.get('price', 0)

            # 活动限定装饰(-1)优先级最高
            if price == -1:
                return 999999

            # 碎片价格 "ornament-fragment:X"
            if isinstance(price, str) and price.startswith("ornament-fragment:"):
                try:
                    fragment_count = int(price.split(":")[1])
                    return fragment_count * 20  # 系数20,确保碎片装饰优先级高于所有金币装饰
                except (ValueError, IndexError):
                    return 0

            # 数值型价格
            if isinstance(price, int):
                return price

            return 0

        except Exception as e:
            print("[ERROR] [BedOrnamentSystem] 获取价格失败: {}".format(str(e)))
            return 0

    def _create_bed_entity(self, config, team_id, pos, yaw, dimension):
        """
        创建床装饰实体

        Args:
            config (dict): 床饰配置
            team_id (str): 队伍ID
            pos (tuple): 位置 (x, y, z)
            yaw (float): 朝向角度
            dimension (int): 维度ID

        Returns:
            str | None: 实体ID, 失败返回None
        """
        try:
            comp_factory = serverApi.GetEngineCompFactory()

            # 1. 创建实体
            entity_type = config.get('entity_type', 'ecbedwars:bed_ornament')

            # 使用引擎工厂创建实体
            levelId = serverApi.GetLevelId()
            entity_comp = comp_factory.CreateEngineEntity(levelId)

            # 创建实体
            entity_id = entity_comp.CreateEngineEntityByTypeStr(
                entity_type,
                pos,
                (0, yaw),  # (pitch, yaw)
                dimension
            )

            if not entity_id:
                print("[ERROR] [BedOrnamentSystem] 创建实体失败: entity_type={}".format(entity_type))
                return None

            print("[INFO] [BedOrnamentSystem] 创建实体成功: entity_id={}, type={}".format(entity_id, entity_type))

            # 2. 设置variant
            variant = config.get('variant', 0)
            variant_comp = comp_factory.CreateEntityDefinitions(entity_id)
            if variant_comp:
                variant_comp.SetVariant(variant)
                print("[INFO] [BedOrnamentSystem] 设置variant: {}".format(variant))

            # 3. 设置mark_variant (支持队伍颜色)
            mark_variant = self._get_mark_variant(config, team_id)
            if variant_comp:
                variant_comp.SetMarkVariant(mark_variant)
                print("[INFO] [BedOrnamentSystem] 设置mark_variant: {}".format(mark_variant))

            # 4. 设置缩放
            scale = config.get('scale', 1.0)
            if scale != 1.0:
                scale_comp = comp_factory.CreateScale(entity_id)
                if scale_comp:
                    scale_comp.SetEntityScale(entity_id, scale)
                    print("[INFO] [BedOrnamentSystem] 设置scale: {}".format(scale))

            return entity_id

        except Exception as e:
            print("[ERROR] [BedOrnamentSystem] 创建床装饰实体失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()
            return None

    def _get_mark_variant(self, config, team_id):
        """
        获取mark_variant (根据队伍颜色)

        Args:
            config (dict): 床饰配置
            team_id (str): 队伍ID

        Returns:
            int: mark_variant值
        """
        if config.get('team_color_support', False):
            # 支持队伍颜色
            mark_variant_by_team = config.get('mark_variant_by_team', {})
            return mark_variant_by_team.get(team_id, config.get('mark_variant', 0))
        else:
            # 不支持队伍颜色
            return config.get('mark_variant', 0)

    def destroy_bed_ornament(self, team_id):
        """
        销毁床装饰 (床被破坏时调用)

        Args:
            team_id (str): 队伍ID
        """
        try:
            if team_id not in self.team_bed_entities:
                print("[WARN] [BedOrnamentSystem] 队伍 {} 没有床装饰实体".format(team_id))
                return

            entity_id = self.team_bed_entities[team_id]

            # 销毁实体
            comp_factory = serverApi.GetEngineCompFactory()
            levelId = serverApi.GetLevelId()
            entity_comp = comp_factory.CreateEngineEntity(levelId)

            if entity_comp:
                entity_comp.RemoveEntity(entity_id)
                print("[INFO] [BedOrnamentSystem] 销毁床装饰: team={}, entity={}".format(team_id, entity_id))

            # 从记录中移除
            del self.team_bed_entities[team_id]

        except Exception as e:
            print("[ERROR] [BedOrnamentSystem] 销毁床装饰失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def get_bed_ornament_entity(self, team_id):
        """
        获取队伍的床装饰实体ID

        Args:
            team_id (str): 队伍ID

        Returns:
            str | None: 实体ID, 不存在返回None
        """
        return self.team_bed_entities.get(team_id)
