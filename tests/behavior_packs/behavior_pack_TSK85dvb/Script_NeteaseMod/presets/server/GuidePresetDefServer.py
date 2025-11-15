# -*- coding: utf-8 -*-
"""
GuidePresetDefServer - 教程指引预设 (服务端)

功能:
- 创建教程指引实体
- 配置教程指引实体的类型 (采矿物、保护床、买东西)
- 主要用于大厅练习区域
- 客户端预设负责渲染控制（设置query.mod.guide变量）

原预设: BedWarsGuidePart
"""

from Script_NeteaseMod.presets.server.EntityPresetServerBase import EntityPresetServerBase
from ECPresetServerScripts import get_preset_system
import mod.server.extraServerApi as serverApi


class GuidePresetDefServer(EntityPresetServerBase):
    """
    教程指引预设 - 服务端

    支持的guide_type:
    - PROTECT: 保护床
    - COLLECT: 采矿物
    - BUY: 买东西
    """

    def __init__(self):
        super(GuidePresetDefServer, self).__init__()

        # 预设配置
        self.guide_type = "PROTECT"  # 默认类型
        self.entity_id = None  # 创建的实体ID
        self.instance = None  # PresetInstance引用

    def on_init(self, instance):
        """
        预设初始化 - 读取配置并注册事件监听

        Args:
            instance: PresetInstance对象
        """
        print("[INFO] [bedwars:guide] 预设初始化: {}".format(instance.instance_id))

        # 获取配置
        self.guide_type = instance.get_config("guide_type", "PROTECT")

        # 监听玩家客户端初始化完毕事件
        get_preset_system().ListenForEvent(
            serverApi.GetEngineNamespace(),
            serverApi.GetEngineSystemName(),
            'ClientLoadAddonsFinishServerEvent',
            self,
            self.on_client_load_end
        )

        # 立即设置到instance.data，确保客户端可以在on_init中读取
        instance.set_data("guide_type", self.guide_type)

        print("  - guide_type: {}".format(self.guide_type))

    def on_start(self, instance):
        """
        预设启动 - 异步加载区块后创建实体

        Args:
            instance: PresetInstance对象
        """
        print("[INFO] [bedwars:guide] 预设启动: {}".format(instance.instance_id))
        print("  - guide_type: {}".format(self.guide_type))

        # 保存instance引用
        self.instance = instance

        # 获取实体标识符
        entity_identifier = instance.get_config("runtime_entity_id")
        if not entity_identifier:
            print("[ERROR] [bedwars:guide] 缺少 runtime_entity_id 配置")
            return

        # 获取位置和维度信息
        pos = instance.get_config("pos", [0, 64, 0])
        rotation = instance.get_config("rotation", {"pitch": 0, "yaw": 0, "roll": 0})
        dimension_id = instance.get_config("dimension_id", 0)

        # 使用基类的异步创建实体方法
        self.create_entity_async(
            entity_identifier=entity_identifier,
            pos=pos,
            rotation=rotation,
            dimension_id=dimension_id,
            callback=self._on_entity_created
        )

    def on_client_load_end(self, args):
        """
        客户端加载完成回调 - 向新加入的玩家发送实体创建消息

        Args:
            args: 事件参数，包含 playerId
        """
        player_id = args['playerId']

        print("[DEBUG] [bedwars:guide] 玩家加入事件触发: player_id={}, instance_id={}".format(
            player_id, self.instance.instance_id
        ))

        # 检查实体是否已创建
        if self.entity_id:
            print("[INFO] [bedwars:guide] 发送entity_created给玩家{}: entity_id={}, guide_type={}".format(
                player_id, self.entity_id, self.guide_type
            ))
            self.instance.send_to_client("entity_created", {
                "entity_id": self.entity_id,
                "guide_type": self.guide_type
            })
        else:
            print("[WARN] [bedwars:guide] 玩家{}加入时实体尚未创建，跳过发送".format(player_id))

    def _on_entity_created(self, entity_id):
        """
        实体创建完成回调

        Args:
            entity_id: str|None 实体ID，失败为None
        """
        if entity_id:
            self.entity_id = entity_id
            print("[INFO] [bedwars:guide] Guide实体创建成功: entity_id={}".format(entity_id))

            # 保存实体ID到instance，供客户端预设使用
            self.instance.set_data("entity_id", entity_id)

        else:
            print("[ERROR] [bedwars:guide] Guide实体创建失败")

    def on_stop(self, instance):
        """
        预设停止

        Args:
            instance: PresetInstance对象
        """
        print("[INFO] [bedwars:guide] 预设停止: {}".format(instance.instance_id))

    def on_destroy(self, instance):
        """
        预设销毁 - 销毁实体并取消事件监听

        Args:
            instance: PresetInstance对象
        """
        print("[INFO] [bedwars:guide] 预设销毁: {}".format(instance.instance_id))

        # 取消事件监听，避免内存泄漏
        get_preset_system().UnListenForEvent(
            serverApi.GetEngineNamespace(),
            serverApi.GetEngineSystemName(),
            'ClientLoadAddonsFinishServerEvent',
            self,
            self.on_client_load_end
        )

        # 使用基类的销毁实体方法
        if self.entity_id:
            self.destroy_entity(self.entity_id)
            self.entity_id = None
