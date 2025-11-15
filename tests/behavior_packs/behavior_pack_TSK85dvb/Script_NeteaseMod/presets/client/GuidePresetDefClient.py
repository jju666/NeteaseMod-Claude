# -*- coding: utf-8 -*-
"""
GuidePresetDefClient - 教程指引预设 (客户端)

功能:
- 控制教程指引实体的渲染效果
- 设置query.mod.guide变量控制实体外观
- 支持三种类型: COLLECT(采矿物), BUY(买东西), PROTECT(保护床)

原预设: BedWarsGuidePart
"""

from ECPresetServerScripts import PresetDefinitionClient
import mod.client.extraClientApi as clientApi


class GuidePresetDefClient(PresetDefinitionClient):
    """
    教程指引预设 - 客户端

    支持的guide_type:
    - COLLECT: 采矿物 (query.mod.guide = 0)
    - BUY: 买东西 (query.mod.guide = 1)
    - PROTECT: 保护床 (query.mod.guide = 2)
    """

    def __init__(self):
        super(GuidePresetDefClient, self).__init__()

        # 配置数据
        self.guide_type = None  # type: str | None
        self.entity_id = None   # type: str | None

    def on_init(self, instance):
        """
        预设初始化 - 读取配置

        Args:
            instance: PresetInstanceClient对象
        """
        print("[DEBUG] [bedwars:guide-客户端] on_init被调用")
        print("[DEBUG] [bedwars:guide-客户端] instance: {}".format(instance))
        print("[DEBUG] [bedwars:guide-客户端] instance.instance_id: {}".format(instance.instance_id))

        # 详细打印config内容
        if hasattr(instance, 'config'):
            print("[DEBUG] [bedwars:guide-客户端] instance.config存在，完整内容:")
            import json
            try:
                config_str = json.dumps(instance.config, indent=2, ensure_ascii=False)
                print("[DEBUG] {}".format(config_str))
            except:
                print("[DEBUG] {}".format(instance.config))
        else:
            print("[DEBUG] [bedwars:guide-客户端] instance.config不存在!")

        # 从配置中读取guide_type
        # 注意：entity_id在此时还不存在，需要等待服务端创建实体后通过on_server_message获取
        self.guide_type = instance.get_config("guide_type", "PROTECT")

        print("[INFO] [bedwars:guide-客户端] 初始化完成:")
        print("  - instance_id: {}".format(instance.instance_id))
        print("  - guide_type: {}".format(self.guide_type))
        print("  - entity_id: {} (将在服务端创建实体后获取)".format(self.entity_id))

    def on_start(self, instance):
        """
        预设启动

        等待服务端发送entity_created消息

        注意：如果玩家在服务端启动很久后才加入游戏，可能无法收到entity_created消息。
        这种情况下需要服务端在玩家加入时重新发送状态，或者房间重启。
        实际游戏中这种情况很少见，因为等待大厅的实体是随房间启动而创建的。

        Args:
            instance: PresetInstanceClient对象
        """
        print("[INFO] [bedwars:guide-客户端] 启动: guide_type={}".format(self.guide_type))
        print("[INFO] [bedwars:guide-客户端] 等待服务端发送entity_created消息...")

    def on_stop(self, instance):
        """
        预设停止

        Args:
            instance: PresetInstanceClient对象
        """
        print("[INFO] [bedwars:guide-客户端] 停止: guide_type={}".format(self.guide_type))

    def on_destroy(self, instance):
        """
        预设销毁

        Args:
            instance: PresetInstanceClient对象
        """
        print("[INFO] [bedwars:guide-客户端] 销毁: guide_type={}".format(self.guide_type))

    def on_server_message(self, instance, message_type, data):
        """
        接收服务端消息

        Args:
            instance: PresetInstanceClient对象
            message_type: 消息类型
            data: 消息数据
        """
        print("[DEBUG] [bedwars:guide-客户端] 收到服务端消息: type={}, data={}".format(
            message_type, data))

        if message_type == "entity_created":
            # 服务端实体创建完成，获取entity_id
            entity_id = data.get("entity_id")
            guide_type = data.get("guide_type")

            print("[INFO] [bedwars:guide-客户端] 收到entity_created事件:")
            print("  - entity_id: {}".format(entity_id))
            print("  - guide_type: {}".format(guide_type))

            if entity_id:
                # 更新成员变量
                self.entity_id = entity_id
                if guide_type:
                    self.guide_type = guide_type

                # 现在实体已创建，可以设置molang了
                print("[INFO] [bedwars:guide-客户端] 实体已创建，设置molang")
                self._set_render_controller(instance)
            else:
                print("[ERROR] [bedwars:guide-客户端] entity_created事件中entity_id为空")

    def _set_render_controller(self, instance):
        """
        设置渲染控制器 - 通过query变量控制实体外观

        Args:
            instance: PresetInstanceClient对象
        """
        print("[DEBUG] [bedwars:guide-客户端] _set_render_controller被调用")
        print("[DEBUG] [bedwars:guide-客户端] instance: {}".format(instance))

        try:
            # 使用成员变量中存储的entity_id
            print("[DEBUG] [bedwars:guide-客户端] 使用entity_id: {}".format(self.entity_id))

            if not self.entity_id:
                print("[ERROR] [bedwars:guide-客户端] 无法获取实体ID，entity_id为None或空")
                print("[DEBUG] [bedwars:guide-客户端] 请检查服务端是否在配置中传递了entity_id")
                return

            print("[DEBUG] [bedwars:guide-客户端] 实体ID: {}".format(self.entity_id))

            comp_factory = clientApi.GetEngineCompFactory()

            # 注册query变量（0-2三种状态）
            for i in range(0, 3):
                comp_query = comp_factory.CreateQueryVariable(clientApi.GetLevelId())
                comp_query.Register("query.mod.guide", i)

            # 根据guide_type设置query值
            guide_value = 0  # 默认值

            if self.guide_type == "COLLECT":
                guide_value = 0
            elif self.guide_type == "BUY":
                guide_value = 1
            elif self.guide_type == "PROTECT":
                guide_value = 2

            # 设置实体的query.mod.guide值
            comp_query = comp_factory.CreateQueryVariable(self.entity_id)
            comp_query.Set("query.mod.guide", guide_value)

            print("[INFO] [bedwars:guide-客户端] 设置query.mod.guide={} (type={})".format(
                guide_value, self.guide_type
            ))

        except Exception as e:
            print("[ERROR] [bedwars:guide-客户端] 设置渲染控制器失败: {}".format(e))
            import traceback
            traceback.print_exc()