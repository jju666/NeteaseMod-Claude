# -*- coding: utf-8 -*-
"""
KillBroadcastManager - 击杀广播管理器

功能:
- 管理击杀广播配置
- 生成个性化击杀消息
- 支持多种击杀广播包
- 支持占位符替换和颜色代码转换

原文件: Parts/ECBedWarsOrnament/ornament/BedWarsOrnamentKillBroadcast.py
重构为: systems/ornament_system/ornament/KillBroadcastManager.py
"""

import random


class KillBroadcastConfig(object):
    """击杀广播配置"""

    def __init__(self, broadcast_id, name, messages):
        """
        初始化击杀广播配置

        Args:
            broadcast_id (str): 广播ID
            name (str): 广播名称
            messages (list): 广播消息模板列表
        """
        self.broadcast_id = broadcast_id
        self.name = name
        self.messages = messages if messages else []

    def get_random_message(self):
        """
        获取随机广播消息模板

        Returns:
            str: 消息模板,如果没有消息则返回None
        """
        if len(self.messages) == 0:
            return None
        return random.choice(self.messages)


class KillBroadcastManager(object):
    """
    击杀广播管理器

    负责击杀广播消息的生成和管理
    """

    # 从配置文件加载的击杀广播配置
    KILL_BROADCAST_CONFIGS = {}

    def __init__(self, ornament_system):
        """
        初始化击杀广播管理器

        Args:
            ornament_system: OrnamentSystem实例
        """
        self.ornament_system = ornament_system
        self.game_system = ornament_system.game_system

        # 加载击杀广播配置
        self._load_kill_broadcast_configs()

        print("[INFO] [KillBroadcastManager] 初始化完成")

    def _load_kill_broadcast_configs(self):
        """从配置文件加载击杀广播配置"""
        try:
            from Script_NeteaseMod.config import ornament_config

            # 加载击杀广播配置
            raw_configs = ornament_config.KILL_BROADCAST_CONFIG

            for broadcast_id, config_data in raw_configs.items():
                self.KILL_BROADCAST_CONFIGS[broadcast_id] = KillBroadcastConfig(
                    broadcast_id=broadcast_id,  # 使用字典的key作为ID
                    name=config_data["name"],
                    messages=config_data.get("messages", [])  # 使用get以防没有messages字段
                )

            print("[INFO] [KillBroadcastManager] 加载了 {} 个击杀广播配置".format(
                len(self.KILL_BROADCAST_CONFIGS)
            ))

        except Exception as e:
            print("[ERROR] [KillBroadcastManager] 加载击杀广播配置失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

            # 使用默认配置
            self.KILL_BROADCAST_CONFIGS["default"] = KillBroadcastConfig(
                "default",
                u"默认",
                [u"{victim}\xa73 被 {killer} \xa73终结啦！"]
            )

    def initialize(self):
        """初始化击杀广播管理器"""
        try:
            print("[INFO] [KillBroadcastManager] 击杀广播管理器初始化成功")
        except Exception as e:
            print("[ERROR] [KillBroadcastManager] 初始化失败: {}".format(str(e)))

    def cleanup(self):
        """清理击杀广播管理器"""
        try:
            print("[INFO] [KillBroadcastManager] 清理完成")
        except Exception as e:
            print("[ERROR] [KillBroadcastManager] 清理失败: {}".format(str(e)))

    def get_kill_broadcast_message(self, killer_id, victim_colored_name, killer_colored_name, kill_count=None):
        """
        获取击杀广播消息

        Args:
            killer_id (str): 击杀者ID
            victim_colored_name (str): 被击杀玩家带颜色的名称
            killer_colored_name (str): 击杀者带颜色的名称
            kill_count (int): 击杀次数(可选,用于count-package)

        Returns:
            str: 格式化后的击杀广播消息,如果未装备广播装饰则返回None
        """
        try:
            # 获取击杀者装备的击杀广播
            broadcast_id = self.ornament_system.get_player_ornament(killer_id, 'kill_broadcast')
            if not broadcast_id:
                # 未装备击杀广播,返回None使用默认消息
                return None

            # 获取广播配置
            broadcast_config = self.KILL_BROADCAST_CONFIGS.get(broadcast_id)
            if not broadcast_config:
                print("[WARN] [KillBroadcastManager] 未找到击杀广播配置: {}".format(broadcast_id))
                return None

            # 获取随机消息模板
            message_template = broadcast_config.get_random_message()
            if not message_template:
                return None

            # 格式化消息
            formatted_message = self._format_message(
                message_template,
                victim_colored_name,
                killer_colored_name,
                kill_count
            )

            print("[INFO] [KillBroadcastManager] 玩家 {} 使用击杀广播: {}".format(
                killer_id, broadcast_id
            ))

            return formatted_message

        except Exception as e:
            print("[ERROR] [KillBroadcastManager] 获取击杀广播消息失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()
            return None

    def _format_message(self, template, victim_name, killer_name, kill_count=None):
        """
        格式化击杀广播消息

        替换占位符:
        - {victim}: 被击杀玩家名称
        - {killer}: 击杀者名称
        - {count}: 击杀次数
        - {dark-aqua}, {red}, {gold}等: 颜色代码

        Args:
            template (str): 消息模板
            victim_name (str): 被击杀玩家带颜色的名称
            killer_name (str): 击杀者带颜色的名称
            kill_count (int): 击杀次数(可选)

        Returns:
            str: 格式化后的消息
        """
        try:
            from Script_NeteaseMod.config import ornament_config

            # 1. 替换占位符
            message = template
            message = message.replace(u"{victim}", victim_name)
            message = message.replace(u"{killer}", killer_name)

            # 替换击杀次数(如果提供)
            if kill_count is not None:
                message = message.replace(u"{count}", str(kill_count))

            # 2. 替换颜色代码
            # 遍历颜色代码映射表
            color_map = ornament_config.COLOR_CODE_MAP
            for color_name, color_code in color_map.items():
                placeholder = u"{{{}}}".format(color_name)
                message = message.replace(placeholder, color_code)

            return message

        except Exception as e:
            print("[ERROR] [KillBroadcastManager] 格式化消息失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()
            return template

    def get_all_kill_broadcasts(self):
        """
        获取所有击杀广播配置

        Returns:
            dict: 击杀广播配置字典 {broadcast_id: KillBroadcastConfig}
        """
        return self.KILL_BROADCAST_CONFIGS

    def get_kill_broadcast_config(self, broadcast_id):
        """
        获取指定击杀广播配置

        Args:
            broadcast_id (str): 广播ID

        Returns:
            KillBroadcastConfig: 广播配置,如果不存在则返回None
        """
        return self.KILL_BROADCAST_CONFIGS.get(broadcast_id)
