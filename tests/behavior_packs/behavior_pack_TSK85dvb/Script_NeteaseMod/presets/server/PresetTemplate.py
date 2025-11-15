# -*- coding: utf-8 -*-
"""
EC预设模板 - 服务端

这是一个服务端EC预设的开发模板，展示了如何创建一个新的预设类型。
复制此文件并修改为你的预设名称，然后实现生命周期钩子方法。

使用方法:
1. 复制此文件，重命名为 YourPresetDefServer.py
2. 修改类名为 YourPresetDefServer
3. 实现生命周期钩子方法
4. 在 modMain.py 中注册预设类型
"""

# 导入EC预设框架类
from ECPresetServerScripts.framework.server.PresetDefinitionServer import PresetDefinitionServer

# 导入引擎API (按需导入)
# import mod.server.extraServerApi as serverApi
# ServerCompFactory = serverApi.GetServerCompFactory()


class PresetTemplate(PresetDefinitionServer):
    """
    预设模板类 - 服务端

    继承自 PresetDefinitionServer，实现预设的服务端逻辑。

    生命周期顺序:
    1. __init__()       - 类初始化
    2. on_init()        - 预设实例创建时
    3. on_start()       - 预设启动时
    4. on_tick()        - 每Tick调用 (可选)
    5. on_stop()        - 预设停止时
    6. on_destroy()     - 预设销毁时

    属性:
        preset_id: 预设实例ID (字符串)
        preset_type: 预设类型 (字符串)
        data: 预设自定义数据 (字典)
        instance: PresetInstance对象，提供API访问
    """

    def __init__(self):
        """
        构造函数

        注意: 不要在__init__中执行复杂逻辑，应该放在on_init中。
        """
        super(PresetTemplate, self).__init__()

        # 预设状态
        self._is_active = False

        # 预设数据缓存
        self._cached_data = {}

    # ========== 生命周期钩子 ==========

    def on_init(self, instance):
        """
        预设初始化钩子

        在预设实例创建后立即调用。用于:
        - 解析预设配置数据
        - 初始化预设状态
        - 设置预设属性

        Args:
            instance: PresetInstance对象

        可用API:
            instance.preset_id       - 获取预设ID
            instance.preset_type     - 获取预设类型
            instance.data            - 获取/设置预设数据
            instance.get_dimension() - 获取预设所在维度
            instance.get_position()  - 获取预设位置
        """
        print("[INFO] [{}] 预设初始化: {}".format(self.preset_type, self.preset_id))

        # 示例: 解析配置数据
        position = instance.get_position()
        dimension = instance.get_dimension()

        print("  - 位置: {}".format(position))
        print("  - 维度: {}".format(dimension))

        # 示例: 初始化自定义数据
        if "custom_field" not in instance.data:
            instance.data["custom_field"] = "default_value"

    def on_start(self, instance):
        """
        预设启动钩子

        在预设启动时调用 (房间开始时)。用于:
        - 创建实体
        - 注册事件监听
        - 启动定时器

        Args:
            instance: PresetInstance对象

        可用API:
            instance.emit_event(event_name, event_data)  - 发送事件
            instance.listen_event(event_name, callback)  - 监听事件
        """
        print("[INFO] [{}] 预设启动: {}".format(self.preset_type, self.preset_id))

        self._is_active = True

        # 示例: 注册事件监听
        # instance.listen_event("PlayerInteractEvent", self._on_player_interact)

        # 示例: 发送启动事件
        # instance.emit_event("PresetStarted", {"preset_id": self.preset_id})

    def on_tick(self, instance):
        """
        预设Tick钩子 (可选)

        每个游戏Tick调用一次。用于:
        - 更新预设状态
        - 检测玩家距离
        - 执行定时逻辑

        注意: 此方法会频繁调用，需要注意性能。
        如果不需要Tick更新，可以不实现此方法。

        Args:
            instance: PresetInstance对象
        """
        if not self._is_active:
            return

        # 示例: 定时逻辑
        # tick_count = instance.data.get("tick_count", 0)
        # tick_count += 1
        # instance.data["tick_count"] = tick_count
        #
        # if tick_count % 20 == 0:  # 每秒执行一次
        #     self._do_something()

    def on_stop(self, instance):
        """
        预设停止钩子

        在预设停止时调用 (房间结束时)。用于:
        - 清理实体
        - 取消事件监听
        - 停止定时器

        Args:
            instance: PresetInstance对象
        """
        print("[INFO] [{}] 预设停止: {}".format(self.preset_type, self.preset_id))

        self._is_active = False

        # 示例: 取消事件监听
        # instance.unlisten_event("PlayerInteractEvent", self._on_player_interact)

    def on_destroy(self, instance):
        """
        预设销毁钩子

        在预设实例销毁前调用。用于:
        - 保存数据
        - 释放资源
        - 最终清理

        Args:
            instance: PresetInstance对象
        """
        print("[INFO] [{}] 预设销毁: {}".format(self.preset_type, self.preset_id))

        # 示例: 清理缓存数据
        self._cached_data.clear()

    # ========== 自定义方法 ==========

    def _on_player_interact(self, event_data):
        """
        示例: 玩家交互事件处理

        Args:
            event_data: 事件数据
        """
        player_id = event_data.get("player_id")
        print("[INFO] 玩家交互: player_id={}".format(player_id))

        # 在这里实现交互逻辑

    def _do_something(self):
        """示例: 自定义方法"""
        pass

    # ========== 辅助方法 ==========

    def get_players_nearby(self, instance, radius):
        """
        获取附近的玩家列表

        Args:
            instance: PresetInstance对象
            radius: 检测半径

        Returns:
            list: 玩家实体ID列表
        """
        # 示例实现 (需要引擎API支持)
        # position = instance.get_position()
        # dimension = instance.get_dimension()
        #
        # # 使用引擎API获取附近玩家
        # comp_factory = ServerCompFactory()
        # # ... 实现获取逻辑
        #
        # return player_ids

        return []  # 占位返回

    def is_player_near(self, instance, player_id, radius):
        """
        检查玩家是否在附近

        Args:
            instance: PresetInstance对象
            player_id: 玩家实体ID
            radius: 检测半径

        Returns:
            bool: 玩家是否在范围内
        """
        # 示例实现
        players = self.get_players_nearby(instance, radius)
        return player_id in players


# ========== 预设类型注册 ==========
#
# 在 modMain.py 中注册此预设类型:
#
# from presets.server.PresetTemplate import PresetTemplate
#
# # 服务端System的Destroy方法中:
# preset_mgr = get_server_mgr("dimension_id")
# preset_mgr.register_preset_type("preset_template", PresetTemplate)
#)))))))