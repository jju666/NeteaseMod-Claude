# -*- coding: utf-8 -*-
"""
UnlockUpgradeManager - 装扮解锁与升级管理器

功能:
- 管理10种装扮类型的完整配置数据
- 提供玩家装扮数据的读写接口
- 实现装扮解锁/购买/装备/升级逻辑
- 集成LobbyAPI实现数据持久化

对应老项目: Parts/ECBedWarsOrnament/unlockupgrade/UnlockUpgradeConfig.py
"""

import json


class UnlockUpgradeManager(object):
    """装扮解锁与升级管理器"""

    def __init__(self, ornament_system):
        """
        初始化管理器

        Args:
            ornament_system: OrnamentSystem实例
        """
        self.ornament_system = ornament_system
        self.game_system = ornament_system.game_system

        # 装扮类型配置 (10种类型,按顺序)
        self.type_configs = []

        # 缓存玩家装扮数据 {player_id: {type_id: {prop_id: entry}}}
        self.player_data_cache = {}

        print("[INFO] [UnlockUpgradeManager] 初始化完成")

    def initialize(self):
        """初始化管理器 - 加载配置"""
        try:
            # 从config加载10种装扮类型配置
            from Script_NeteaseMod.config import ornament_config
            self.type_configs = ornament_config.ORNAMENT_TYPES

            print("[INFO] [UnlockUpgradeManager] 加载了 {} 种装扮类型".format(len(self.type_configs)))
        except Exception as e:
            print("[ERROR] [UnlockUpgradeManager] 初始化失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def cleanup(self):
        """清理管理器"""
        self.player_data_cache = {}
        print("[INFO] [UnlockUpgradeManager] 清理完成")

    # ========== 配置数据获取 ==========

    def get_all_type_data(self):
        """
        获取所有装扮类型数据 (10种)

        Returns:
            list: 装扮类型数据列表,每个元素包含:
                - type_id: 类型ID
                - type_name: 类型名称(含颜色代码)
                - have_state: 是否支持装备状态
                - introduce: 类型介绍
                - have_count: 玩家已拥有数量(需在获取时计算)
                - total_count: 总数量
                - ornaments: 装扮列表
        """
        result = []
        for type_config in self.type_configs:
            type_data = {
                'type_id': type_config['type_id'],
                'type_name': type_config['type_name'],
                'have_state': type_config.get('have_state', False),
                'introduce': type_config['introduce'],
                'total_count': len(type_config.get('ornaments', [])),
                'have_count': 0,  # 默认为0,需要在UI显示时根据player_id计算
                'ornaments': type_config.get('ornaments', [])
            }
            result.append(type_data)
        return result

    def get_type_data(self, type_id):
        """
        获取指定类型的配置数据

        Args:
            type_id (str): 类型ID

        Returns:
            dict: 类型配置数据,包含:
                - type_id: 类型ID
                - type_name: 类型名称
                - have_state: 是否支持装备状态
                - introduce: 类型介绍
                - ornaments: 装扮列表
            如果不存在返回None
        """
        for type_config in self.type_configs:
            if type_config['type_id'] == type_id:
                return {
                    'type_id': type_config['type_id'],
                    'type_name': type_config['type_name'],
                    'have_state': type_config.get('have_state', False),
                    'introduce': type_config['introduce'],
                    'ornaments': type_config.get('ornaments', [])
                }
        return None

    def get_ornament(self, type_id, prop_id):
        """
        获取指定装扮的配置

        Args:
            type_id (str): 类型ID
            prop_id (str): 装扮ID

        Returns:
            dict: 装扮配置数据,包含:
                - prop_id: 装扮ID
                - name: 装扮名称
                - introduce: 装扮介绍
                - price: 价格
                - default_own: 是否默认拥有
            如果不存在返回None
        """
        type_data = self.get_type_data(type_id)
        if not type_data:
            return None

        for ornament in type_data['ornaments']:
            if ornament['prop_id'] == prop_id:
                return ornament

        return None

    # ========== 玩家装扮数据 ==========

    def get_player_entry(self, player_id, type_id, prop_id):
        """
        获取玩家的装扮数据(等级、是否装备等)

        Args:
            player_id (str): 玩家ID
            type_id (str): 类型ID
            prop_id (str): 装扮ID

        Returns:
            dict: 玩家装扮数据,包含:
                - level: 等级 (0表示未解锁)
                - equipped: 是否装备 (仅have_state=True时有效)
                - unlock_time: 解锁时间戳
        """
        # 从缓存获取
        if player_id in self.player_data_cache:
            type_cache = self.player_data_cache[player_id].get(type_id, {})
            if prop_id in type_cache:
                return type_cache[prop_id]

        # 从持久化存储加载
        player_data = self._load_player_ornament_data(player_id, type_id)

        # 检查是否默认拥有
        ornament = self.get_ornament(type_id, prop_id)
        if ornament and ornament.get('default_own', False):
            # 默认拥有的装扮
            return {
                'level': 1,
                'equipped': False,
                'unlock_time': 0
            }

        # 检查玩家数据
        if prop_id in player_data:
            return player_data[prop_id]

        # 未解锁
        return {
            'level': 0,
            'equipped': False,
            'unlock_time': 0
        }

    def get_player_have_count(self, player_id, type_id):
        """
        获取玩家在指定类型下已拥有的装扮数量

        Args:
            player_id (str): 玩家ID
            type_id (str): 类型ID

        Returns:
            int: 已拥有数量
        """
        type_data = self.get_type_data(type_id)
        if not type_data:
            return 0

        count = 0
        for ornament in type_data['ornaments']:
            prop_id = ornament['prop_id']
            entry = self.get_player_entry(player_id, type_id, prop_id)
            if entry['level'] > 0:
                count += 1

        return count

    def get_equipped_ornament(self, player_id, type_id):
        """
        获取玩家在指定类型下当前装备的装扮ID

        Args:
            player_id (str): 玩家ID
            type_id (str): 类型ID

        Returns:
            str: 装备的装扮prop_id,如果没有装备返回None
        """
        type_data = self.get_type_data(type_id)
        if not type_data:
            return None

        # 检查类型是否支持装备状态
        if not type_data.get('have_state', False):
            return None

        # 查找装备的装扮
        for ornament in type_data['ornaments']:
            prop_id = ornament['prop_id']
            entry = self.get_player_entry(player_id, type_id, prop_id)
            if entry.get('equipped', False):
                return prop_id

        return None

    # ========== 装扮操作 ==========

    def buy_ornament(self, player_id, type_id, prop_id):
        """
        购买/解锁装扮

        Args:
            player_id (str): 玩家ID
            type_id (str): 类型ID
            prop_id (str): 装扮ID

        Returns:
            dict: 购买结果,包含:
                - success: bool - 是否成功
                - message: str - 结果消息
        """
        try:
            # 获取装扮配置
            ornament = self.get_ornament(type_id, prop_id)
            if not ornament:
                return {
                    'success': False,
                    'message': u"装扮不存在"
                }

            # 检查是否已拥有
            entry = self.get_player_entry(player_id, type_id, prop_id)
            if entry['level'] > 0:
                return {
                    'success': False,
                    'message': u"您已经拥有该装扮"
                }

            # 获取价格
            price = ornament.get('price', 0)
            if price < 0:
                return {
                    'success': False,
                    'message': u"该装扮为非卖品"
                }

            # 检查是否为测试模式
            if self._is_test_mode():
                # 测试模式下直接解锁
                self._unlock_ornament_internal(player_id, type_id, prop_id)
                return {
                    'success': True,
                    'message': u"解锁成功 (测试模式)"
                }

            # 检查硬币是否足够
            coin = self._get_player_coin(player_id)
            if coin < price:
                return {
                    'success': False,
                    'message': u"硬币不足,需要 {} 硬币".format(price)
                }

            # 扣除硬币
            if not self._deduct_player_coin(player_id, price):
                return {
                    'success': False,
                    'message': u"扣除硬币失败"
                }

            # 解锁装扮
            self._unlock_ornament_internal(player_id, type_id, prop_id)

            return {
                'success': True,
                'message': u"购买成功！花费 {} 硬币".format(price)
            }

        except Exception as e:
            print("[ERROR] [UnlockUpgradeManager] 购买装扮失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'message': u"购买失败: {}".format(str(e))
            }

    def equip_ornament(self, player_id, type_id, prop_id):
        """
        装备装扮(自动卸载旧装备)

        Args:
            player_id (str): 玩家ID
            type_id (str): 类型ID
            prop_id (str): 装扮ID

        Returns:
            bool: 是否成功
        """
        try:
            # 检查类型是否支持装备
            type_data = self.get_type_data(type_id)
            if not type_data or not type_data.get('have_state', False):
                print("[WARN] [UnlockUpgradeManager] 该类型不支持装备: {}".format(type_id))
                return False

            # 检查是否已拥有
            entry = self.get_player_entry(player_id, type_id, prop_id)
            if entry['level'] == 0:
                print("[WARN] [UnlockUpgradeManager] 玩家未拥有该装扮: {} {}".format(type_id, prop_id))
                return False

            # 卸载该类型下的所有装扮
            self._unequip_all_ornaments(player_id, type_id)

            # 装备新装扮
            self._equip_ornament_internal(player_id, type_id, prop_id)

            print("[INFO] [UnlockUpgradeManager] 装备成功: player={} type={} prop={}".format(
                player_id, type_id, prop_id
            ))
            return True

        except Exception as e:
            print("[ERROR] [UnlockUpgradeManager] 装备装扮失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()
            return False

    # ========== 内部方法 ==========

    def _unlock_ornament_internal(self, player_id, type_id, prop_id):
        """
        内部方法: 解锁装扮(不检查条件)

        Args:
            player_id (str): 玩家ID
            type_id (str): 类型ID
            prop_id (str): 装扮ID
        """
        import time

        # 加载玩家数据
        player_data = self._load_player_ornament_data(player_id, type_id)

        # 更新装扮数据
        player_data[prop_id] = {
            'level': 1,
            'equipped': False,
            'unlock_time': int(time.time())
        }

        # 保存数据
        self._save_player_ornament_data(player_id, type_id, player_data)

        # 更新缓存
        if player_id not in self.player_data_cache:
            self.player_data_cache[player_id] = {}
        if type_id not in self.player_data_cache[player_id]:
            self.player_data_cache[player_id][type_id] = {}
        self.player_data_cache[player_id][type_id][prop_id] = player_data[prop_id]

    def _equip_ornament_internal(self, player_id, type_id, prop_id):
        """
        内部方法: 装备装扮(不检查条件)

        Args:
            player_id (str): 玩家ID
            type_id (str): 类型ID
            prop_id (str): 装扮ID
        """
        # 加载玩家数据
        player_data = self._load_player_ornament_data(player_id, type_id)

        # 更新装备状态
        if prop_id in player_data:
            player_data[prop_id]['equipped'] = True
        else:
            # 如果数据不存在,创建新数据
            import time
            player_data[prop_id] = {
                'level': 1,
                'equipped': True,
                'unlock_time': int(time.time())
            }

        # 保存数据
        self._save_player_ornament_data(player_id, type_id, player_data)

        # 更新缓存
        if player_id not in self.player_data_cache:
            self.player_data_cache[player_id] = {}
        if type_id not in self.player_data_cache[player_id]:
            self.player_data_cache[player_id][type_id] = {}
        self.player_data_cache[player_id][type_id][prop_id] = player_data[prop_id]

    def _unequip_all_ornaments(self, player_id, type_id):
        """
        内部方法: 卸载指定类型下的所有装扮

        Args:
            player_id (str): 玩家ID
            type_id (str): 类型ID
        """
        # 加载玩家数据
        player_data = self._load_player_ornament_data(player_id, type_id)

        # 卸载所有装扮
        for prop_id in player_data:
            player_data[prop_id]['equipped'] = False

        # 保存数据
        self._save_player_ornament_data(player_id, type_id, player_data)

        # 清除缓存
        if player_id in self.player_data_cache:
            if type_id in self.player_data_cache[player_id]:
                del self.player_data_cache[player_id][type_id]

    # ========== 玩家数据加载 (兼容OrnamentSystem调用) ==========

    def load_player_data(self, player_id):
        """
        加载玩家装扮数据 (兼容接口)

        Args:
            player_id (str): 玩家ID

        注意: 这是兼容接口,实际数据加载在get_player_entry中按需进行
        """
        try:
            print("[INFO] [UnlockUpgradeManager] 加载玩家 {} 的装扮数据".format(player_id))
            # 初始化缓存
            if player_id not in self.player_data_cache:
                self.player_data_cache[player_id] = {}
        except Exception as e:
            print("[ERROR] [UnlockUpgradeManager] 加载玩家数据失败: player={} error={}".format(
                player_id, str(e)
            ))

    def load_player_ornaments(self, player_id):
        """
        加载玩家装扮数据 (兼容接口,与load_player_data相同)

        Args:
            player_id (str): 玩家ID
        """
        self.load_player_data(player_id)

    # ========== 数据持久化 ==========

    def _load_player_ornament_data(self, player_id, type_id):
        """
        从持久化存储加载玩家装扮数据

        Args:
            player_id (str): 玩家ID
            type_id (str): 类型ID

        Returns:
            dict: {prop_id: {level, equipped, unlock_time}}
        """
        try:
            # 检查是否有room_system
            room_system = getattr(self.game_system, 'room_system', None)
            if not room_system:
                print("[WARN] [UnlockUpgradeManager] room_system不存在,无法加载玩家数据")
                return {}

            # 构造存储键
            data_key = "ornament_{}".format(type_id)

            # 从LobbyAPI加载
            player_data = room_system.get_player_data(player_id, data_key)
            if player_data is None or not isinstance(player_data, dict):
                return {}

            return player_data

        except Exception as e:
            print("[ERROR] [UnlockUpgradeManager] 加载玩家数据失败: player={} type={} error={}".format(
                player_id, type_id, str(e)
            ))
            return {}

    def _save_player_ornament_data(self, player_id, type_id, player_data):
        """
        保存玩家装扮数据到持久化存储

        Args:
            player_id (str): 玩家ID
            type_id (str): 类型ID
            player_data (dict): 玩家装扮数据
        """
        try:
            # 检查是否有room_system
            room_system = getattr(self.game_system, 'room_system', None)
            if not room_system:
                print("[WARN] [UnlockUpgradeManager] room_system不存在,无法保存玩家数据")
                return

            # 构造存储键
            data_key = "ornament_{}".format(type_id)

            # 保存到LobbyAPI（必须使用force=True，因为player_data是字典而不是数值）
            room_system.set_player_data(player_id, data_key, player_data, force=True)

        except Exception as e:
            print("[ERROR] [UnlockUpgradeManager] 保存玩家数据失败: player={} type={} error={}".format(
                player_id, type_id, str(e)
            ))
            import traceback
            traceback.print_exc()

    # ========== 工具方法 ==========

    def _get_player_coin(self, player_id):
        """
        获取玩家硬币数量

        Args:
            player_id (str): 玩家ID

        Returns:
            int: 硬币数量
        """
        try:
            room_system = getattr(self.game_system, 'room_system', None)
            if room_system:
                coin = room_system.get_player_data(player_id, "coin")
                return coin if isinstance(coin, (int, long)) else 0
            return 0
        except Exception as e:
            print("[ERROR] [UnlockUpgradeManager] 获取玩家硬币失败: {}".format(str(e)))
            return 0

    def _deduct_player_coin(self, player_id, amount):
        """
        扣除玩家硬币

        Args:
            player_id (str): 玩家ID
            amount (int): 扣除数量

        Returns:
            bool: 是否成功
        """
        try:
            room_system = getattr(self.game_system, 'room_system', None)
            if not room_system:
                return False

            coin = room_system.get_player_data(player_id, "coin")
            if not isinstance(coin, (int, long)) or coin < amount:
                return False

            new_coin = coin - amount
            room_system.set_player_data(player_id, "coin", new_coin)
            return True

        except Exception as e:
            print("[ERROR] [UnlockUpgradeManager] 扣除玩家硬币失败: {}".format(str(e)))
            return False

    def _is_test_mode(self):
        """
        检查是否为测试模式

        Returns:
            bool: 是否为测试模式
        """
        try:
            room_system = getattr(self.game_system, 'room_system', None)
            if room_system:
                return getattr(room_system, 'ornament_shop_test_mode', False)
            return False
        except:
            return False

    # ========== 兼容接口 ==========

    def is_ornament_unlocked(self, player_id, type_id, prop_id):
        """
        检查装扮是否已解锁(兼容接口)

        Args:
            player_id (str): 玩家ID
            type_id (str): 类型ID
            prop_id (str): 装扮ID

        Returns:
            bool: 是否已解锁
        """
        entry = self.get_player_entry(player_id, type_id, prop_id)
        return entry['level'] > 0

    def unlock_ornament(self, player_id, type_id, prop_id):
        """
        解锁装扮(免费,兼容接口)

        Args:
            player_id (str): 玩家ID
            type_id (str): 类型ID
            prop_id (str): 装扮ID

        Returns:
            bool: 是否成功
        """
        try:
            self._unlock_ornament_internal(player_id, type_id, prop_id)
            return True
        except:
            return False

    def unequip_ornament(self, player_id, type_id):
        """
        卸载指定类型的装扮(兼容接口)

        Args:
            player_id (str): 玩家ID
            type_id (str): 类型ID

        Returns:
            bool: 是否成功
        """
        try:
            self._unequip_all_ornaments(player_id, type_id)
            return True
        except:
            return False
