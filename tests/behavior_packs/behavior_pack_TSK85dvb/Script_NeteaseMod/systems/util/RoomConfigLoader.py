# -*- coding: utf-8 -*-
"""
RoomConfigLoader - 房间配置加载器

功能:
- 加载房间配置 (从Python模块)
- 加载预设配置 (从Python模块)
- 提供配置查询接口

注意: 从JSON迁移到Python配置,避免文件系统路径问题
"""


class RoomConfigLoader(object):
    """房间配置加载器 - 使用Python模块导入"""

    def __init__(self):
        """初始化配置加载器"""
        self.room_config = None
        self.preset_configs = {}  # dimension_id -> preset_dict
        self.game_rules = None  # 游戏规则配置

        print("[INFO] [RoomConfigLoader] 初始化 (使用Python配置模块)")

    def load_room_settings(self):
        """
        加载房间配置 - 从Python模块导入

        Returns:
            dict: 房间配置字典
        """
        try:
            print("[DEBUG] [RoomConfigLoader] 开始导入配置模块...")
            # 在NetEase环境中需要使用完整的模块路径
            from Script_NeteaseMod.config.room_settings import ROOM_CONFIG
            print("[DEBUG] [RoomConfigLoader] 配置模块导入成功")

            self.room_config = ROOM_CONFIG

            print("[INFO] [RoomConfigLoader] 加载房间配置成功")
            print("[INFO] [RoomConfigLoader]   - 房间名称: {}".format(
                self.room_config.get('room_name', 'Unknown')))
            print("[INFO] [RoomConfigLoader]   - 开始人数: {}".format(
                self.room_config.get('start_players', 0)))
            print("[INFO] [RoomConfigLoader]   - 地图数量: {}".format(
                len(self.room_config.get('stages', []))))
            print("[DEBUG] [RoomConfigLoader]   - waiting_spawn: {}".format(
                self.room_config.get('waiting_spawn', 'MISSING')))

            return self.room_config

        except Exception as e:
            print("[ERROR] [RoomConfigLoader] 加载房间配置失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()
            print("[WARN] [RoomConfigLoader] 使用默认配置")
            # 返回默认配置
            return self._get_default_room_config()

    def load_preset_config(self, dimension_id):
        """
        加载指定维度的预设配置 - 从Python模块导入

        Args:
            dimension_id (int): 维度ID

        Returns:
            dict: 预设配置字典,包含preset_count和presets列表
        """
        # 检查缓存
        if dimension_id in self.preset_configs:
            return self.preset_configs[dimension_id]

        # 动态导入配置模块 - 使用完整的模块路径
        try:
            module_name = "Script_NeteaseMod.config.rooms.dimension_{}".format(dimension_id)
            config_module = __import__(module_name, fromlist=['PRESET_CONFIG'])
            preset_config = config_module.PRESET_CONFIG

            # 缓存配置
            self.preset_configs[dimension_id] = preset_config

            print("[INFO] [RoomConfigLoader] 加载维度{}预设配置: {}个预设".format(
                dimension_id, preset_config.get('preset_count', 0)))

            return preset_config

        except ImportError as e:
            print("[WARN] [RoomConfigLoader] 维度{}没有预设配置模块: {}".format(
                dimension_id, str(e)))
            return None
        except Exception as e:
            print("[ERROR] [RoomConfigLoader] 加载维度{}预设配置失败: {}".format(
                dimension_id, str(e)))
            import traceback
            traceback.print_exc()
            return None

    def get_room_param(self, key, default=None):
        """
        获取房间配置参数

        Args:
            key (str): 参数键名
            default: 默认值

        Returns:
            配置值
        """
        if not self.room_config:
            self.load_room_settings()

        return self.room_config.get(key, default)

    def get_stages(self):
        """
        获取地图列表

        Returns:
            list: 地图配置列表
        """
        if not self.room_config:
            self.load_room_settings()

        return self.room_config.get('stages', [])

    def get_stage_by_id(self, stage_id):
        """
        根据地图ID获取地图配置

        Args:
            stage_id (str): 地图ID

        Returns:
            dict: 地图配置,如果不存在返回None
        """
        stages = self.get_stages()
        for stage in stages:
            if stage.get('id') == stage_id:
                return stage
        return None

    def get_stage_by_dimension(self, dimension_id):
        """
        根据维度ID获取地图配置

        Args:
            dimension_id (int): 维度ID

        Returns:
            dict: 地图配置,如果不存在返回None
        """
        stages = self.get_stages()
        for stage in stages:
            if stage.get('map_dimension') == dimension_id:
                return stage
        return None

    def load_game_rules(self):
        """
        加载游戏规则配置 - 从Python配置模块导入

        Returns:
            dict: 游戏规则配置字典
        """
        try:
            # 从配置模块导入 - 使用完整的模块路径
            from Script_NeteaseMod.config.game_rules import GAME_RULES_CONFIG

            self.game_rules = GAME_RULES_CONFIG

            print("[INFO] [RoomConfigLoader] 游戏规则配置加载成功")
            print("[INFO] [RoomConfigLoader]   - 规则数量: {}".format(
                len(self.game_rules.get('game_rules', {}))))

            return self.game_rules

        except Exception as e:
            print("[ERROR] [RoomConfigLoader] 加载游戏规则配置失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()
            # 返回默认配置
            return self._get_default_game_rules()

    def get_game_rules(self):
        """
        获取游戏规则配置

        Returns:
            dict: 游戏规则配置
        """
        if not self.game_rules:
            self.load_game_rules()

        return self.game_rules

    def _get_default_game_rules(self):
        """
        获取默认游戏规则配置

        Returns:
            dict: 默认游戏规则
        """
        return {
            "game_rules": {
                "pvp": True,
                "showcoordinates": False,
                "naturalregeneration": False,
                "keepinventory": False,
                "mobgriefing": False,
                "domobspawning": False,
                "doweathercycle": False,
                "dodaylightcycle": False,
                "commandblocksenabled": True,
                "commandblockoutput": False,
                "sendcommandfeedback": False
            },
            "time": {
                "set_time": 6000,
                "lock_time": True
            },
            "weather": {
                "set_weather": "clear",
                "lock_weather": True
            }
        }

    def _get_default_room_config(self):
        """
        获取默认房间配置

        Returns:
            dict: 默认配置
        """
        return {
            "room_name": "EC起床战争",
            "lobby_dimension": 0,
            "waiting_spawn": {"x": 0, "y": 100, "z": 0},
            "waiting_spawn_yaw": 0,
            "broadcast_score_spawn": {"x": 0, "y": 100, "z": 20},
            "broadcast_score_spawn_yaw": 0,
            "broadcast_score_npc_positions": [],
            "max_players": 16,
            "start_players": 2,
            "countdown_time": 10,
            "stages": []
        }
