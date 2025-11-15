# -*- coding: utf-8 -*-
"""
UnlockUpgradeManager - 解锁升级管理器

功能:
- 管理装扮解锁
- 管理装扮升级
- 玩家数据持久化

原文件: Parts/ECBedWarsOrnament/UnlockUpgrade/UnlockUpgradeManager.py
重构为: systems/ornament_system/unlock_upgrade/UnlockUpgradeManager.py
"""

import mod.server.extraServerApi as serverApi


class UnlockUpgradeManager(object):
    """
    解锁升级管理器

    负责装扮的解锁和升级逻辑
    """

    def __init__(self, ornament_system):
        """
        初始化解锁升级管理器

        Args:
            ornament_system: OrnamentSystem实例
        """
        self.ornament_system = ornament_system
        self.game_system = ornament_system.game_system

        # 玩家解锁数据 {player_id: {'unlocked': [], 'equipped': {}}}
        self.player_unlock_data = {}

        # 装扮价格配置
        self.ornament_prices = {}

        # 获取RoomManagementSystem引用（用于数据持久化和货币系统）
        self.room_system = None
        self._get_room_system_reference()

        print("[INFO] [UnlockUpgradeManager] 初始化完成")

    def _get_room_system_reference(self):
        """获取RoomManagementSystem引用"""
        try:
            from Script_NeteaseMod.modConfig import MOD_NAME

            self.room_system = serverApi.GetSystem(MOD_NAME, "RoomManagementSystem")
            if self.room_system:
                print("[INFO] [UnlockUpgradeManager] RoomManagementSystem引用获取成功")
            else:
                print("[WARN] [UnlockUpgradeManager] RoomManagementSystem未找到")
        except Exception as e:
            print("[ERROR] [UnlockUpgradeManager] 获取RoomManagementSystem失败: {}".format(str(e)))

    def initialize(self):
        """初始化解锁升级管理器"""
        try:
            # 加载装扮价格配置
            self._load_price_config()

            print("[INFO] [UnlockUpgradeManager] 解锁升级管理器初始化成功")
        except Exception as e:
            print("[ERROR] [UnlockUpgradeManager] 初始化失败: {}".format(str(e)))

    def cleanup(self):
        """清理解锁升级管理器"""
        try:
            # 保存所有玩家数据
            self._save_all_player_data()

            # 清理内存数据
            self.player_unlock_data = {}

            print("[INFO] [UnlockUpgradeManager] 清理完成")
        except Exception as e:
            print("[ERROR] [UnlockUpgradeManager] 清理失败: {}".format(str(e)))

    def _load_price_config(self):
        """加载装扮价格配置（从配置文件）"""
        try:
            from Script_NeteaseMod.config import ornament_config

            # 合并所有装扮配置
            self.unlock_items = {}

            # 添加击杀音效
            for ornament_id, ornament_data in ornament_config.KILL_SOUND_CONFIG.items():
                self.unlock_items[ornament_id] = {
                    "type": "kill_sound",
                    "id": ornament_id,
                    "name": ornament_data.get("name", u"未知"),
                    "price": ornament_data.get("price", 0),
                    "unlocked_by_default": ornament_data.get("unlocked_by_default", False)
                }

            # 添加胜利舞蹈
            for ornament_id, ornament_data in ornament_config.VICTORY_DANCE_CONFIG.items():
                self.unlock_items[ornament_id] = {
                    "type": "victory_dance",
                    "id": ornament_id,
                    "name": ornament_data.get("name", u"未知"),
                    "price": ornament_data.get("price", 0),
                    "unlocked_by_default": ornament_data.get("unlocked_by_default", False)
                }

            # 添加Meme特效
            for ornament_id, ornament_data in ornament_config.MEME_EFFECT_CONFIG.items():
                self.unlock_items[ornament_id] = {
                    "type": "meme_effect",
                    "id": ornament_id,
                    "name": ornament_data.get("name", u"未知"),
                    "price": ornament_data.get("price", 0),
                    "unlocked_by_default": ornament_data.get("unlocked_by_default", False)
                }

            # 添加喷漆
            for ornament_id, ornament_data in ornament_config.SPRAY_CONFIG.items():
                self.unlock_items[ornament_id] = {
                    "type": "spray",
                    "id": ornament_id,
                    "name": ornament_data.get("name", u"未知"),
                    "price": ornament_data.get("price", 0),
                    "unlocked_by_default": ornament_data.get("unlocked_by_default", False)
                }

            # 添加床破坏特效
            for ornament_id, ornament_data in ornament_config.BED_DESTROY_EFFECT_CONFIG.items():
                self.unlock_items[ornament_id] = {
                    "type": "bed_destroy_effect",
                    "id": ornament_id,
                    "name": ornament_data.get("name", u"未知"),
                    "price": ornament_data.get("price", 0),
                    "unlocked_by_default": ornament_data.get("unlocked_by_default", False)
                }

            print("[INFO] [UnlockUpgradeManager] 从配置文件加载 {} 个装扮".format(len(self.unlock_items)))

            # 兼容性：保留旧的ornament_prices字典
            self.ornament_prices = {}
            for ornament_id, data in self.unlock_items.items():
                ornament_type = data["type"]
                if ornament_type not in self.ornament_prices:
                    self.ornament_prices[ornament_type] = {}
                self.ornament_prices[ornament_type][ornament_id] = {
                    "unlock_cost": data["price"],
                    "currency": "coin"
                }

        except Exception as e:
            print("[ERROR] [UnlockUpgradeManager] 加载配置失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()
            # 使用默认配置
            self._load_default_price_config()

    def _load_default_price_config(self):
        """加载默认装扮价格配置（降级方案）"""
        print("[WARN] [UnlockUpgradeManager] 使用默认装扮价格配置")

        self.unlock_items = {
            "default": {
                "type": "spray",
                "id": "default",
                "name": u"默认",
                "price": 0,
                "unlocked_by_default": True
            }
        }

        self.ornament_prices = {
            "spray": {
                "default": {"unlock_cost": 0, "currency": "coin"}
            }
        }

    # ========== 玩家数据管理 ==========

    def load_player_data(self, player_id):
        """
        加载玩家解锁数据

        Args:
            player_id (str): 玩家ID
        """
        # TODO: 从数据库或文件加载玩家数据
        # 临时使用默认数据
        self.player_unlock_data[player_id] = {
            'unlocked': ['spray:default'],  # 已解锁的装扮列表
            'equipped': {
                'spray': 'default',
                'kill_effect': None,
                'victory_dance': None
            }
        }

        print("[INFO] [UnlockUpgradeManager] 已加载玩家 {} 的数据".format(player_id))

    def load_player_ornaments(self, player_id):
        """
        从LobbyAPI加载玩家装扮数据

        Args:
            player_id: 玩家ID
        """
        if not self.room_system:
            print("[WARN] [UnlockUpgradeManager] RoomManagementSystem未找到，无法加载装扮数据")
            return

        try:
            # 从RoomManagementSystem的缓存中读取装扮数据
            # 数据键格式: "ornament_unlocked" (JSON字符串，存储解锁的装扮ID列表)
            unlocked_json = self.room_system.get_player_data(player_id, "ornament_unlocked", "[]")

            # 解析JSON
            import json
            unlocked_list = json.loads(unlocked_json)

            # 转换为字典格式
            if player_id not in self.player_unlock_data:
                self.player_unlock_data[player_id] = {
                    'unlocked': [],
                    'equipped': {
                        'spray': None,
                        'kill_effect': None,
                        'victory_dance': None
                    }
                }

            # 更新解锁列表
            self.player_unlock_data[player_id]['unlocked'] = unlocked_list

            print("[INFO] [UnlockUpgradeManager] 玩家 {} 加载装扮数据: {} 个".format(
                player_id, len(unlocked_list)
            ))

        except Exception as e:
            print("[ERROR] [UnlockUpgradeManager] 加载玩家 {} 装扮数据失败: {}".format(
                player_id, str(e)
            ))
            import traceback
            traceback.print_exc()

    def save_player_ornaments(self, player_id):
        """
        保存玩家装扮数据到LobbyAPI

        Args:
            player_id: 玩家ID
        """
        if not self.room_system:
            print("[WARN] [UnlockUpgradeManager] RoomManagementSystem未找到，无法保存装扮数据")
            return

        try:
            # 获取玩家解锁的装扮列表
            unlocked_list = []
            if player_id in self.player_unlock_data:
                unlocked_list = self.player_unlock_data[player_id].get('unlocked', [])

            # 转换为JSON字符串
            import json
            unlocked_json = json.dumps(unlocked_list)

            # 保存到RoomManagementSystem的缓存
            self.room_system.set_player_data(player_id, "ornament_unlocked", unlocked_json, force=True)

            print("[INFO] [UnlockUpgradeManager] 保存玩家 {} 装扮数据: {} 个".format(
                player_id, len(unlocked_list)
            ))

        except Exception as e:
            print("[ERROR] [UnlockUpgradeManager] 保存玩家 {} 装扮数据失败: {}".format(
                player_id, str(e)
            ))
            import traceback
            traceback.print_exc()

    def save_player_data(self, player_id):
        """
        保存玩家解锁数据

        Args:
            player_id (str): 玩家ID
        """
        if player_id not in self.player_unlock_data:
            return

        # TODO: 保存到数据库或文件
        data = self.player_unlock_data[player_id]
        print("[INFO] [UnlockUpgradeManager] 已保存玩家 {} 的数据".format(player_id))

    def _save_all_player_data(self):
        """保存所有玩家数据"""
        for player_id in self.player_unlock_data.keys():
            self.save_player_data(player_id)

    # ========== 解锁逻辑 ==========

    def unlock_ornament(self, player_id, ornament_type, ornament_id):
        """
        解锁装扮

        Args:
            player_id (str): 玩家ID
            ornament_type (str): 装扮类型(spray/kill_effect/victory_dance)
            ornament_id (str): 装扮ID

        Returns:
            bool: 是否解锁成功
        """
        # 检查玩家数据
        if player_id not in self.player_unlock_data:
            self.load_player_data(player_id)

        player_data = self.player_unlock_data[player_id]
        ornament_full_id = "{}:{}".format(ornament_type, ornament_id)

        # 检查是否已解锁
        if ornament_full_id in player_data['unlocked']:
            self._send_message(player_id, u"该装扮已解锁")
            return False

        # 获取价格
        price_info = self._get_ornament_price(ornament_type, ornament_id)
        if not price_info:
            print("[ERROR] [UnlockUpgradeManager] 装扮 {} 价格配置不存在".format(ornament_full_id))
            return False

        unlock_cost = price_info.get('unlock_cost', 0)
        currency = price_info.get('currency', 'coin')

        # 检查货币
        if not self._check_player_currency(player_id, currency, unlock_cost):
            self._send_message(player_id, u"货币不足,无法解锁")
            return False

        # 扣除货币
        if not self._deduct_currency(player_id, currency, unlock_cost):
            return False

        # 解锁装扮
        player_data['unlocked'].append(ornament_full_id)

        # 保存数据
        self.save_player_data(player_id)

        # 保存到数据库
        self.save_player_ornaments(player_id)

        self._send_message(player_id, u"成功解锁装扮: {}".format(ornament_id))
        print("[INFO] [UnlockUpgradeManager] 玩家 {} 解锁装扮 {}".format(player_id, ornament_full_id))

        return True

    def is_ornament_unlocked(self, player_id, ornament_type, ornament_id):
        """
        检查装扮是否已解锁

        Args:
            player_id (str): 玩家ID
            ornament_type (str): 装扮类型
            ornament_id (str): 装扮ID

        Returns:
            bool: 是否已解锁
        """
        if player_id not in self.player_unlock_data:
            self.load_player_data(player_id)

        player_data = self.player_unlock_data[player_id]
        ornament_full_id = "{}:{}".format(ornament_type, ornament_id)

        return ornament_full_id in player_data['unlocked']

    def get_unlocked_ornaments(self, player_id, ornament_type=None):
        """
        获取玩家已解锁的装扮列表

        Args:
            player_id (str): 玩家ID
            ornament_type (str, optional): 装扮类型,不传则返回所有类型

        Returns:
            list: 已解锁的装扮ID列表
        """
        if player_id not in self.player_unlock_data:
            self.load_player_data(player_id)

        player_data = self.player_unlock_data[player_id]
        unlocked = player_data.get('unlocked', [])

        if ornament_type:
            # 过滤指定类型
            prefix = "{}:".format(ornament_type)
            return [item.split(':')[1] for item in unlocked if item.startswith(prefix)]
        else:
            return unlocked

    # ========== 装备逻辑 ==========

    def equip_ornament(self, player_id, ornament_type, ornament_id):
        """
        装备装扮

        Args:
            player_id (str): 玩家ID
            ornament_type (str): 装扮类型
            ornament_id (str): 装扮ID

        Returns:
            bool: 是否装备成功
        """
        # 检查是否已解锁
        if not self.is_ornament_unlocked(player_id, ornament_type, ornament_id):
            self._send_message(player_id, u"该装扮未解锁")
            return False

        # 装备装扮
        player_data = self.player_unlock_data[player_id]
        player_data['equipped'][ornament_type] = ornament_id

        # 同步到OrnamentSystem
        self.ornament_system.set_player_ornament(player_id, ornament_type, ornament_id)

        # 保存数据
        self.save_player_data(player_id)

        self._send_message(player_id, u"已装备装扮: {}".format(ornament_id))
        print("[INFO] [UnlockUpgradeManager] 玩家 {} 装备 {} = {}".format(
            player_id, ornament_type, ornament_id        ))

        return True

    def unequip_ornament(self, player_id, ornament_type):
        """
        卸下装扮

        Args:
            player_id (str): 玩家ID
            ornament_type (str): 装扮类型

        Returns:
            bool: 是否卸下成功
        """
        if player_id not in self.player_unlock_data:
            return False

        player_data = self.player_unlock_data[player_id]
        player_data['equipped'][ornament_type] = None

        # 同步到OrnamentSystem
        self.ornament_system.set_player_ornament(player_id, ornament_type, None)

        # 保存数据
        self.save_player_data(player_id)

        self._send_message(player_id, u"已卸下装扮")
        return True

    def get_equipped_ornament(self, player_id, ornament_type):
        """
        获取玩家装备的装扮

        Args:
            player_id (str): 玩家ID
            ornament_type (str): 装扮类型

        Returns:
            str: 装扮ID,如果未装备则返回None
        """
        if player_id not in self.player_unlock_data:
            self.load_player_data(player_id)

        player_data = self.player_unlock_data[player_id]
        return player_data['equipped'].get(ornament_type)

    # ========== 货币相关 ==========

    def _get_ornament_price(self, ornament_type, ornament_id):
        """
        获取装扮价格信息

        Args:
            ornament_type (str): 装扮类型
            ornament_id (str): 装扮ID

        Returns:
            dict: 价格信息 {'unlock_cost': ..., 'currency': ...}
        """
        type_prices = self.ornament_prices.get(ornament_type, {})
        return type_prices.get(ornament_id)

    def _check_player_currency(self, player_id, currency, amount):
        """
        检查玩家货币是否足够

        Args:
            player_id (str): 玩家ID
            currency (str): 货币类型(coin/diamond等)
            amount (int): 数量

        Returns:
            bool: 是否足够
        """
        if not self.room_system:
            print("[WARN] [UnlockUpgradeManager] RoomManagementSystem未找到，返回默认货币检查失败")
            return False

        try:
            # 从RoomManagementSystem的缓存中读取货币数据
            # 目前只支持coin类型
            if currency == 'coin':
                coin = self.room_system.get_player_data(player_id, "coin", 0)
                return int(coin) >= amount
            else:
                print("[WARN] [UnlockUpgradeManager] 不支持的货币类型: {}".format(currency))
                return False
        except Exception as e:
            print("[ERROR] [UnlockUpgradeManager] 检查玩家 {} 货币失败: {}".format(player_id, str(e)))
            return False

    def _deduct_currency(self, player_id, currency, amount):
        """
        扣除玩家货币

        Args:
            player_id (str): 玩家ID
            currency (str): 货币类型
            amount (int): 数量

        Returns:
            bool: 是否扣除成功
        """
        if not self.room_system:
            print("[WARN] [UnlockUpgradeManager] RoomManagementSystem未找到，无法扣除货币")
            return False

        try:
            # 目前只支持coin类型
            if currency != 'coin':
                print("[WARN] [UnlockUpgradeManager] 不支持的货币类型: {}".format(currency))
                return False

            # 获取当前货币
            current_coin = self.room_system.get_player_data(player_id, "coin", 0)
            current_coin = int(current_coin)

            # 检查是否足够
            if current_coin < amount:
                print("[INFO] [UnlockUpgradeManager] 玩家 {} 货币不足: 需要 {} 当前 {}".format(
                    player_id, amount, current_coin
                ))
                return False

            # 扣除货币
            new_coin = current_coin - amount
            self.room_system.set_player_data(player_id, "coin", new_coin, force=False)

            print("[INFO] [UnlockUpgradeManager] 玩家 {} 货币扣除成功: -{} ({} -> {})".format(
                player_id, amount, current_coin, new_coin
            ))
            return True

        except Exception as e:
            print("[ERROR] [UnlockUpgradeManager] 扣除玩家 {} 货币失败: {}".format(player_id, str(e)))
            return False

    # ========== 工具方法 ==========

    def _send_message(self, player_id, message):
        """
        发送消息给玩家

        Args:
            player_id (str): 玩家ID
            message (str): 消息内容
        """
        comp = serverApi.GetEngineCompFactory()
        msg_comp = comp.CreateMsg(player_id)
        msg_comp.NotifyOneMessage(player_id, message, "§e")