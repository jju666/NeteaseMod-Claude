# -*- coding: utf-8 -*-
"""
服务端API封装辅助类

提供常用服务端API的便捷封装，包括：
- 浮空物品实体（ItemEntity）

API调研完成时间：2025-01-30
MODSDK文档位置：D:\EcWork\netease-modsdk-wiki
"""

from __future__ import print_function
import mod.server.extraServerApi as serverApi
import traceback


class ServerAPIHelper(object):
    """服务端API封装辅助类"""

    # ========== 浮空物品实体（ItemEntity）相关 ==========

    @staticmethod
    def create_floating_item(item_dict, pos, dimension_id=0):
        # type: (dict, tuple, int) -> str or None
        """
        创建浮空物品实体（掉落物）

        Args:
            item_dict (dict): 物品信息字典，格式如下：
                {
                    'itemName': str,      # 物品identifier（必填）
                    'count': int,         # 物品数量（默认1）
                    'auxValue': int,      # 附加值（默认0）
                    'enchantData': list,  # 附魔列表（可选）
                    'customTips': str,    # 自定义提示（可选）
                    'extraId': str,       # 额外ID（可选）
                }
            pos (tuple): 位置 (x, y, z)
            dimension_id (int): 维度ID（默认0，主世界）

        Returns:
            str or None: 物品实体ID，失败返回None

        注意：
            - 物品实体会受重力影响掉落
            - 需要配合定期位置更新来实现"悬浮"效果
            - 可通过ServerPlayerTryTouchEvent事件控制是否可拾取

        API文档位置：
            D:\EcWork\netease-modsdk-wiki\docs\mcdocs\1-ModAPI\接口\世界\实体管理.md (第132-170行)
        """
        try:
            # 获取System类来调用CreateEngineItemEntity
            # 注意：这是ServerSystem的方法，需要在System中调用
            # 这里提供的是封装示例，实际使用时需要在System实例中调用

            print("[ServerAPIHelper] 创建浮空物品: item={}, pos={}, dim={}".format(
                item_dict.get('itemName', 'unknown'), pos, dimension_id
            ))

            # ⚠️ 注意：CreateEngineItemEntity是ServerSystem的方法
            # 无法通过静态方法直接调用，需要在System实例中使用
            # 使用示例见类底部注释

            return None  # 占位符，实际需要在System中调用

        except Exception as e:
            print("[ERROR] [ServerAPIHelper] 创建浮空物品异常: {}".format(str(e)))
            traceback.print_exc()
            return None

    @staticmethod
    def get_dropped_item_info(system, item_entity_id, get_user_data=False):
        # type: (object, str, bool) -> dict or None
        """
        获取掉落物品信息

        Args:
            system (ServerSystem): ServerSystem实例（用于调用组件工厂）
            item_entity_id (str): 物品实体ID
            get_user_data (bool): 是否获取userData（默认False）

        Returns:
            dict or None: 物品信息字典，不存在返回None
                {
                    'itemName': str,
                    'count': int,
                    'auxValue': int,
                    'enchantData': list,
                    ...
                }
        """
        try:
            comp_factory = serverApi.GetEngineCompFactory()
            item_comp = comp_factory.CreateItem(serverApi.GetLevelId())

            item_dict = item_comp.GetDroppedItem(item_entity_id, get_user_data)

            return item_dict

        except Exception as e:
            print("[ERROR] [ServerAPIHelper] 获取掉落物品信息异常: {}".format(str(e)))
            traceback.print_exc()
            return None

    @staticmethod
    def cancel_item_pickup(event_data):
        # type: (dict) -> bool
        """
        取消物品拾取（在ServerPlayerTryTouchEvent事件中使用）

        Args:
            event_data (dict): 事件数据字典
                {
                    'playerId': str,
                    'entityId': str,
                    'itemDict': dict,
                    'cancel': bool,      # 设置为True取消拾取
                    'pickupDelay': int   # 拾取延迟（tick）
                }

        Returns:
            bool: 是否成功取消拾取

        使用示例：
            def on_player_try_pickup(self, event_data):
                entity_id = event_data.get('entityId')
                if entity_id in self.forbidden_pickup_items:
                    ServerAPIHelper.cancel_item_pickup(event_data)
        """
        try:
            event_data['cancel'] = True
            return True

        except Exception as e:
            print("[ERROR] [ServerAPIHelper] 取消物品拾取异常: {}".format(str(e)))
            traceback.print_exc()
            return False


# ========== 使用示例（用于参考） ==========

"""
# 重要提示：由于CreateEngineItemEntity是ServerSystem的方法，
# ServerAPIHelper无法作为静态类直接创建物品实体。
# 需要在System中调用，示例如下：


# ========== 在ServerSystem中使用 ==========

from systems.util.ServerAPIHelper import ServerAPIHelper

class MyServerSystem(ServerSystem):
    def __init__(self, namespace, systemName):
        super(MyServerSystem, self).__init__(namespace, systemName)
        self.floating_items = {}  # 存储浮空物品实体ID
        self.Create()

    def Create(self):
        # 注册事件：控制物品拾取
        self.ListenForEvent(
            "ServerPlayerTryTouchEvent",
            "Minecraft",
            self.on_player_try_pickup
        )

    def create_floating_item_example(self):
        '''创建浮空物品示例'''
        # 1. 定义物品字典
        item_dict = {
            'itemName': 'minecraft:iron_ingot',  # 铁锭
            'count': 1,
            'auxValue': 0
        }

        # 2. 创建物品实体（调用ServerSystem的方法）
        item_entity_id = self.CreateEngineItemEntity(
            item_dict,
            dimensionId=0,
            pos=(0, 5, 0)
        )

        if item_entity_id:
            print("[MySystem] 创建浮空物品成功: {}".format(item_entity_id))

            # 3. 记录物品ID，用于后续控制
            self.floating_items[item_entity_id] = {
                'pos': (0, 5, 0),
                'forbidden_pickup': True  # 禁止拾取
            }

            # 4. 定期更新位置以维持悬浮效果（每tick）
            # 注意：这会消耗性能，建议使用更高效的方法
            # 或者使用ParticleSystem创建视觉效果替代真实物品

            return item_entity_id

        return None

    def on_player_try_pickup(self, event_data):
        '''玩家尝试拾取物品时'''
        entity_id = event_data.get('entityId')

        # 如果是禁止拾取的浮空物品，取消拾取
        if entity_id in self.floating_items:
            if self.floating_items[entity_id].get('forbidden_pickup', False):
                ServerAPIHelper.cancel_item_pickup(event_data)
                print("[MySystem] 取消拾取浮空物品: {}".format(entity_id))

    def update_floating_item_position(self, item_entity_id, new_pos):
        '''更新浮空物品位置（维持悬浮效果）'''
        try:
            comp_factory = serverApi.GetEngineCompFactory()
            pos_comp = comp_factory.CreatePos(item_entity_id)

            # 设置位置
            pos_comp.SetFootPos(new_pos)

            # 清除速度（防止掉落）
            motion_comp = comp_factory.CreateActorMotion(item_entity_id)
            motion_comp.SetMotion((0, 0, 0))

            return True

        except Exception as e:
            print("[ERROR] 更新浮空物品位置异常: {}".format(str(e)))
            return False

    def destroy_floating_item(self, item_entity_id):
        '''销毁浮空物品'''
        try:
            # 从记录中移除
            if item_entity_id in self.floating_items:
                del self.floating_items[item_entity_id]

            # 销毁实体
            self.DestroyEntity(item_entity_id)

            print("[MySystem] 销毁浮空物品: {}".format(item_entity_id))
            return True

        except Exception as e:
            print("[ERROR] 销毁浮空物品异常: {}".format(str(e)))
            return False


# ========== 替代方案：使用粒子特效模拟物品显示 ==========

# 由于维持真实浮空物品需要持续更新位置，性能消耗较大。
# 建议使用以下替代方案：

# 方案1：使用客户端TextBoard显示物品图标（通过§符号）
# 示例："§l§6⚔" 显示武器图标

# 方案2：使用自定义粒子效果显示物品模型
# 需要在资源包中定义粒子JSON文件

# 方案3：使用盔甲架（Armor Stand）实体 + 物品展示
# 更稳定，但需要额外的实体管理
"""
