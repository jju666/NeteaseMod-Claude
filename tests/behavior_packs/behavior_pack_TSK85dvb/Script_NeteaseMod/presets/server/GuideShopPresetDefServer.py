# -*- coding: utf-8 -*-
"""
GuideShopPresetDefServer - 教程指引商店预设 (服务端)

功能:
- 创建教程指引中的商店NPC
- 保护商店NPC免受伤害（监听DamageEvent）
- 主要用于大厅练习区域展示商店购买机制
- NPC会自动看向附近玩家（通过实体定义中的minecraft:behavior.look_at_player组件实现）

原预设: BedWarsGuideShopPart

技术说明:
- "看向玩家"功能由Minecraft原生行为组件实现，无需Python代码控制
- 使用的实体（如ecbedwars:entity_5）必须包含以下组件：
  * minecraft:behavior.look_at_player (look_distance: 8, priority: 10, probability: 1)
  * runtime_identifier: minecraft:villager_v2 (村民基础实体)
- 如果NPC不看向玩家，请检查：
  1. 实体定义是否包含look_at_player组件
  2. 玩家是否在8方块范围内
  3. 是否有其他更高优先级的行为组件干扰
"""

from Script_NeteaseMod.presets.server.EntityPresetServerBase import EntityPresetServerBase
from ECPresetServerScripts import get_preset_system
import mod.server.extraServerApi as serverApi


class GuideShopPresetDefServer(EntityPresetServerBase):
    """
    教程指引商店预设 - 服务端

    核心功能:
    1. 异步创建商店NPC实体
    2. 监听伤害事件，保护商店NPC不受伤害
    3. 取消击退和点燃效果
    """

    def __init__(self):
        super(GuideShopPresetDefServer, self).__init__()
        self.entity_id = None
        self.instance = None

    def on_init(self, instance):
        """
        预设初始化 - 注册伤害事件监听

        Args:
            instance: PresetInstance对象
        """
        print("[INFO] [bedwars:guide_shop] 预设初始化: {}".format(instance.instance_id))

        # 保存instance引用
        self.instance = instance

        # 注册伤害事件监听，保护商店NPC
        # 参考GuidePresetDefServer的事件订阅方式
        get_preset_system().ListenForEvent(
            serverApi.GetEngineNamespace(),
            serverApi.GetEngineSystemName(),
            'DamageEvent',
            self,
            self._on_damage
        )
        print("[INFO] [bedwars:guide_shop] 已注册伤害事件监听")

    def on_start(self, instance):
        """
        预设启动 - 异步加载区块后创建商店NPC

        Args:
            instance: PresetInstance对象
        """
        print("[INFO] [bedwars:guide_shop] 预设启动: {}".format(instance.instance_id))

        self.instance = instance

        # 获取实体标识符
        entity_identifier = instance.get_config("runtime_entity_id")
        if not entity_identifier:
            print("[ERROR] [bedwars:guide_shop] 缺少 runtime_entity_id 配置")
            return

        # 获取位置和维度信息
        pos = instance.get_config("pos", [0, 64, 0])
        rotation = instance.get_config("rotation", {"pitch": 0, "yaw": 0, "roll": 0})
        dimension_id = instance.get_config("dimension_id", 0)

        # 使用基类的异步创建实体方法
        # 注意：is_npc=False 允许实体转向看向玩家
        # SDK文档说明：isNpc=True会导致实体不会移动、不会转向
        self.create_entity_async(
            entity_identifier=entity_identifier,
            pos=pos,
            rotation=rotation,
            dimension_id=dimension_id,
            callback=self._on_entity_created,
            is_npc=False  # 必须为False，否则无法转向看向玩家
        )

    def _on_entity_created(self, entity_id):
        """
        实体创建完成回调

        Args:
            entity_id: str|None 实体ID，失败为None
        """
        if entity_id:
            self.entity_id = entity_id
            print("[INFO] [bedwars:guide_shop] 商店NPC创建成功: entity_id={}".format(entity_id))

            # 保存实体ID到instance
            self.instance.set_data("entity_id", entity_id)
        else:
            print("[ERROR] [bedwars:guide_shop] 商店NPC创建失败")

    def _on_damage(self, args):
        """
        伤害事件处理 - 保护商店NPC免疫伤害

        Args:
            args: dict 事件参数
                - entityId: str 受伤实体ID
                - damage: float 伤害值
                - knock: bool 是否击退
                - ignite: bool 是否点燃
        """
        # 检查是否是本预设的商店NPC
        if not self.entity_id or args.get('entityId') != self.entity_id:
            return

        # 保护商店NPC：伤害归零、取消击退、取消点燃
        args['damage'] = 0       # 伤害归零
        args['knock'] = False    # 取消击退
        args['ignite'] = False   # 取消点燃

        # print("[DEBUG] [bedwars:guide_shop] 商店NPC受到攻击，已免疫伤害")

    def on_stop(self, instance):
        """
        预设停止

        Args:
            instance: PresetInstance对象
        """
        print("[INFO] [bedwars:guide_shop] 预设停止: {}".format(instance.instance_id))

    def on_destroy(self, instance):
        """
        预设销毁 - 取消事件监听、销毁商店NPC

        Args:
            instance: PresetInstance对象
        """
        print("[INFO] [bedwars:guide_shop] 预设销毁: {}".format(instance.instance_id))

        # 取消伤害事件监听
        get_preset_system().UnListenForEvent(
            serverApi.GetEngineNamespace(),
            serverApi.GetEngineSystemName(),
            'DamageEvent',
            self,
            self._on_damage
        )
        print("[INFO] [bedwars:guide_shop] 已取消伤害事件监听")

        # 使用基类的销毁实体方法
        if self.entity_id:
            self.destroy_entity(self.entity_id)
            self.entity_id = None