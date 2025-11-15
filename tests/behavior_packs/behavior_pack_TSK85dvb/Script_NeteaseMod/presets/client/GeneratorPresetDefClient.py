# -*- coding: utf-8 -*-
"""
产矿机预设 - 客户端

功能:
- 显示产矿机生成特效
- 播放资源生成音效
- 显示产矿机等级提升特效
- 显示资源类型标识特效
- P1.1: 浮空物品指示器（粒子方案）
- P1.2: 浮空文字倒计时显示

重要注意事项:
1. PresetDefinitionClient是单例，所有同类型预设共享同一个对象
2. 实例级数据必须存储在instance.data中，不能存储在self中
3. on_tick()方法签名必须为 on_tick(self, instance, dt)
4. 使用instance.get_config()读取位置，PresetInstanceClient没有get_position()方法
"""

from ECPresetServerScripts import PresetDefinitionClient


class GeneratorPresetDefClient(PresetDefinitionClient):
    """
    产矿机预设客户端实现

    核心功能:
    1. 资源生成特效和音效
    2. 产矿机等级提升特效
    3. 资源类型标识显示 (铁、金、钻石、绿宝石)
    4. 循环粒子效果
    5. P1.1: 浮空物品指示器
    6. P1.2: 浮空文字倒计时（每秒更新）

    架构说明:
    - 本类是PresetDefinitionClient的单例实例
    - 所有产矿机预设实例（如10个产矿机）共享同一个GeneratorPresetDefClient对象
    - 每个产矿机有独立的PresetInstanceClient对象
    - 实例级数据（如floating_text_board_id）必须存储在instance.data中
    """

    # 启用tick更新，使on_tick()被ECPreset框架每帧调用
    enable_tick = True

    def __init__(self):
        super(GeneratorPresetDefClient, self).__init__()

        # 配置数据
        self.resource_type_id = None  # type: str | None  # 资源类型ID
        self.level = 1  # type: int  # 当前等级

        # 特效ID列表
        self._effect_ids = []

        # 资源类型标识特效ID
        self._resource_indicator_effect_id = None

        # 循环粒子效果ID
        self._particle_loop_id = None

        # ========== P1.2功能数据成员 ==========
        self.floating_text_board_id = None  # type: int | None  # 浮动文字面板ID
        self.next_text_update = 0.0  # type: float  # 下次更新浮动文字的时间戳
        # 从服务端同步的数据
        self.team = None  # type: str | None  # 队伍ID
        self.next_generate = 0.0  # type: float  # 下次生成时间（时间戳）
        self.resource_name = None  # type: str | None  # 资源名称（中文）
        self.period_ms = 5000  # type: int  # 生成周期（毫秒）
        self.display_floating = True  # type: bool  # 是否显示浮动文字（从服务端同步）

        # ========== P1.1功能数据成员 ==========
        self.floating_item_particle_id = None  # type: int | None  # 浮空物品粒子ID（简化方案）

    def on_init(self, instance):
        """
        预设初始化

        注意:
        - 客户端在on_init时，服务端尚未通过send_to_client同步数据
        - instance.data此时为空，不应该从中读取配置
        - 等待on_server_message接收"SyncGeneratorData"消息后再初始化

        Args:
            instance: PresetInstanceClient对象
        """
        # 设置默认值，后续会被服务端同步的数据覆盖
        self.resource_type_id = "IRON"

        print("[INFO] [产矿机-客户端] 初始化，等待服务端同步数据...")

    def on_start(self, instance):
        """
        预设启动

        执行步骤:
        1. 创建资源类型标识特效
        2. 开始循环粒子效果
        3. 创建浮空物品指示器 (P1.1)
        4. 注册事件监听

        Args:
            instance: PresetInstanceClient对象
        """
        # 1. 创建资源类型标识特效
        self._create_resource_indicator(instance)

        # 2. 开始循环粒子效果
        self._start_particle_loop(instance)

        # 3. P1.1功能：创建浮空物品指示器
        self._create_floating_item_indicator(instance)

    def on_tick(self, instance, dt):
        """
        每Tick更新

        P1.2功能：每秒更新浮动文字倒计时

        Args:
            instance: PresetInstanceClient对象
            dt: 时间增量（秒），ECPreset框架传入，默认0.05秒
        """
        import time
        now = time.time()

        # 从instance.data读取浮动文字板ID和下次更新时间
        # 注意：所有产矿机预设共享同一个GeneratorPresetDefClient对象，
        # 因此必须将实例级数据存储在instance.data中，而不是self中
        floating_text_board_id = instance.get_data("floating_text_board_id")
        next_text_update = instance.get_data("next_text_update", 0.0)

        # 每秒更新一次浮动文字倒计时
        if floating_text_board_id and now >= next_text_update:
            instance.set_data("next_text_update", now + 1.0)
            self._update_floating_text(instance)

    def on_stop(self, instance):
        """
        预设停止

        清理工作:
        1. 移除资源标识特效
        2. 停止粒子循环
        3. 取消事件监听
        4. 清理浮动文字 (P1.2)
        5. 清理浮空物品指示器 (P1.1)

        Args:
            instance: PresetInstanceClient对象
        """
        print("[INFO] [产矿机-客户端] 停止: type={}".format(self.resource_type_id))

        # 移除资源标识特效
        if self._resource_indicator_effect_id:
            self._stop_effect(self._resource_indicator_effect_id)
            self._resource_indicator_effect_id = None

        # 停止粒子循环
        if self._particle_loop_id:
            self._stop_particle(self._particle_loop_id)
            self._particle_loop_id = None

        # 停止所有特效
        self._stop_all_effects()

        # P1.2功能：清理浮动文字
        self._cleanup_floating_text()

        # P1.1功能：清理浮空物品指示器
        self._cleanup_floating_item_indicator()

    def on_destroy(self, instance):
        """
        预设销毁

        最终清理工作

        Args:
            instance: PresetInstanceClient对象
        """
        print("[INFO] [产矿机-客户端] 销毁: type={}".format(self.resource_type_id))

        # 清理数据
        self._effect_ids = []
        self._resource_indicator_effect_id = None
        self._particle_loop_id = None

    # ========== 接收服务端消息 ==========

    def on_server_message(self, instance, message_type, data):
        """
        接收服务端消息回调 - ECPreset框架标准接口

        Args:
            instance: PresetInstanceClient对象
            message_type: str 消息类型
            data: dict 消息数据
        """
        if message_type == "GeneratorItemSpawned":
            self._on_item_spawned(data)
        elif message_type == "GeneratorLevelUpgrade":
            self._on_level_upgrade(data)
        elif message_type == "SyncGeneratorData":
            self._on_sync_generator_data(instance, data)
        elif message_type == "generator_particle_effect":
            # 产矿粒子特效消息
            self._on_play_particle_effect(data)
        elif message_type == "CreateFloatingText":
            # 游戏运行状态时创建浮动文字（避免维度切换问题）
            self._on_create_floating_text(instance)

    # ========== 事件处理方法 ==========

    def _on_item_spawned(self, event_data):
        """
        处理资源生成事件

        播放资源生成特效和音效

        Args:
            event_data: 事件数据
                - resource_type: 资源类型
                - position: 生成位置
                - dimension: 维度ID
        """
        resource_type = event_data.get('resource_type')

        # 只处理本产矿机对应的资源类型
        if resource_type != self.resource_type_id:
            return

        position = event_data.get('position')
        print("[INFO] [产矿机-客户端] 资源生成: type={}, pos={}".format(
            resource_type, position
        ))

        # 播放资源生成特效
        self._play_item_spawn_effect(position)

        # 播放资源生成音效
        self._play_item_spawn_sound(position)

    def _on_level_upgrade(self, event_data):
        """
        处理等级升级事件

        播放等级提升特效和音效

        Args:
            event_data: 事件数据
                - dimension: 维度ID
                - resource_type: 资源类型
                - new_level: 新等级
                - position: 产矿机位置（可选）
        """
        resource_type = event_data.get('resource_type')

        # 只处理本产矿机对应的资源类型
        if resource_type != self.resource_type_id:
            return

        new_level = event_data.get('new_level', 1)
        self.level = new_level

        print("[INFO] [产矿机-客户端] 等级提升: type={}, level={}".format(
            resource_type, new_level
        ))

        # 获取位置信息（从事件数据或跳过特效）
        position = event_data.get('position')
        if position:
            # 播放等级提升特效
            self._play_level_upgrade_effect(position)

            # 播放等级提升音效（可选）
            # self._play_level_upgrade_sound()  # 暂时禁用音效
        else:
            print("[INFO] [产矿机-客户端] 等级提升事件缺少position，跳过特效播放")

    # ========== 内部辅助方法 ==========

    def _create_resource_indicator(self, instance):
        """
        创建资源类型标识特效

        在产矿机上方显示资源图标或颜色标识

        Args:
            instance: PresetInstanceClient对象
        """
        # 从配置中读取位置（PresetInstanceClient没有get_position方法）
        position = instance.get_config("position") or instance.get_config("pos")

        # TODO: 需要引擎API支持
        # 在产矿机上方偏移位置创建资源标识特效
        # indicator_pos = {
        #     'x': position['x'],
        #     'y': position['y'] + 2.0,  # 产矿机上方2格
        #     'z': position['z']
        # }
        #
        # # 根据资源类型选择标识特效
        # effect_path = self._get_resource_indicator_path(self.resource_type_id)
        # self._resource_indicator_effect_id = self._play_effect(effect_path, indicator_pos)

    def _start_particle_loop(self, instance):
        """
        开始循环粒子效果

        在产矿机周围显示循环粒子

        Args:
            instance: PresetInstanceClient对象
        """
        # 从配置中读取位置
        position = instance.get_config("position") or instance.get_config("pos")

        # TODO: 需要引擎API支持
        # 创建循环粒子效果 (根据资源类型显示不同颜色)
        # particle_type = self._get_resource_particle_type(self.resource_type_id)
        # self._particle_loop_id = self._create_looping_particle(particle_type, position)

    def _on_play_particle_effect(self, data):
        """
        播放粒子效果 - 接收服务端消息（参考guide产矿机实现）

        Args:
            data: dict 消息数据
                - pos: list/tuple (x, y, z) 粒子位置
                - resource_type: str 资源类型 (IRON, GOLD, DIAMOND, EMERALD, COPPER)
        """
        pos = data.get("pos")
        resource_type = data.get("resource_type", "IRON")

        if not pos:
            print("[ERROR] [产矿机-客户端] 粒子效果消息缺少位置信息")
            return

        try:
            # 转换位置格式并居中
            if isinstance(pos, list):
                pos_tuple = (pos[0] + 0.5, pos[1] + 0.5, pos[2] + 0.5)
            else:
                pos_tuple = (pos['x'] + 0.5, pos['y'] + 0.5, pos['z'] + 0.5)

            # 播放产矿粒子特效
            self._play_generator_particle_effect(pos_tuple, resource_type)

        except Exception as e:
            print("[ERROR] [产矿机-客户端] 播放粒子效果异常: {}".format(e))
            import traceback
            traceback.print_exc()

    def _play_generator_particle_effect(self, position, resource_type):
        """
        播放产矿机自定义粒子特效

        使用 ecbedwars:generator 自定义粒子，并设置颜色变量

        Args:
            position: 粒子位置 (x, y, z)
            resource_type: 资源类型 (IRON, GOLD, DIAMOND, EMERALD, COPPER)
        """
        try:
            import mod.client.extraClientApi as clientApi

            # 创建粒子系统组件
            comp_particle = clientApi.GetEngineCompFactory().CreateParticleSystem(None)

            # 创建自定义粒子
            par_id = comp_particle.Create("ecbedwars:generator", position)

            # 获取资源类型对应的颜色
            color = self._get_particle_color(resource_type)

            # 设置粒子颜色变量
            comp_particle.SetVariable(par_id, "variable.color_r", color[0])
            comp_particle.SetVariable(par_id, "variable.color_g", color[1])
            comp_particle.SetVariable(par_id, "variable.color_b", color[2])

            # print("[INFO] [产矿机-客户端] 播放产矿粒子特效: type={}, color={}".format(
            #     resource_type, color
            # ))

        except Exception as e:
            print("[ERROR] [产矿机-客户端] 播放产矿粒子特效失败: {}".format(e))

    def _get_particle_color(self, resource_type):
        """
        获取资源类型对应的粒子颜色

        Args:
            resource_type: 资源类型 (IRON, GOLD, DIAMOND, EMERALD, COPPER)

        Returns:
            tuple: RGB颜色值 (r, g, b)，取值范围 0.0-1.0
        """
        # 资源类型颜色映射 (与老项目一致)
        color_map = {
            'IRON': (0.8, 0.8, 0.8),      # 铁 - 灰白色
            'GOLD': (1.0, 0.84, 0.0),     # 金 - 金黄色
            'DIAMOND': (0.0, 0.7, 1.0),   # 钻石 - 青蓝色
            'EMERALD': (0.0, 1.0, 0.3),   # 绿宝石 - 翠绿色
            'COPPER': (0.72, 0.45, 0.2)   # 铜 - 棕橙色
        }

        return color_map.get(resource_type.upper(), (1.0, 1.0, 1.0))  # 默认白色

    def _play_item_spawn_effect(self, position):
        # type: (tuple) -> None
        """
        播放资源生成特效

        P2.2功能实现 - 播放资源颜色粒子

        Args:
            position: 生成位置 (x, y, z)
        """
        try:
            from Script_NeteaseMod.systems.util.ClientAPIHelper import ClientAPIHelper

            # 播放资源生成粒子特效（绿色爱心粒子）
            # 连续播放5个粒子，形成生成特效
            for i in range(5):
                particle_id = ClientAPIHelper.play_particle(
                    "minecraft:villager_happy",  # 粒子类型：绿色爱心粒子
                    position                     # 播放位置
                )
                if particle_id:
                    print("[INFO] [产矿机-客户端] 播放生成粒子: id={}, pos={}".format(particle_id, position))

            print("[INFO] [产矿机-客户端] 播放生成特效完成: pos={}".format(position))

        except Exception as e:
            print("[ERROR] [产矿机-客户端] 播放生成特效异常: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _play_item_spawn_sound(self, position):
        # type: (tuple) -> None
        """
        播放资源生成音效

        P2.1功能实现

        Args:
            position: 生成位置 (x, y, z)
        """
        try:
            import mod.client.extraClientApi as clientApi

            # 获取游戏组件
            game_comp = clientApi.GetEngineCompFactory().CreateGame(clientApi.GetLevelId())

            # 播放音效："random.orb" - 经验球拾取音效（类似"叮"的声音）
            # 参数: (音效名称, 位置, 音量, 音调)
            game_comp.PlaySound(
                "random.orb",           # 音效名称
                position,               # 播放位置
                0.5,                    # 音量 (0.0-1.0)
                1.2                     # 音调 (0.5-2.0，越高越尖锐)
            )

            print("[INFO] [产矿机-客户端] 播放生成音效: pos={}".format(position))

        except Exception as e:
            print("[ERROR] [产矿机-客户端] 播放音效异常: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _play_level_upgrade_effect(self, position):
        # type: (object) -> None
        """
        播放等级提升特效

        P2.3功能实现（粒子特效部分）

        Args:
            position: 产矿机位置 (dict或list/tuple)
        """
        try:
            from Script_NeteaseMod.systems.util.ClientAPIHelper import ClientAPIHelper

            # ⚠️ 修复：直接使用传入的position参数
            if isinstance(position, dict):
                pos = (position['x'] + 0.5, position['y'] + 0.5, position['z'] + 0.5)
            else:
                pos = (position[0] + 0.5, position[1] + 0.5, position[2] + 0.5)

            print("[INFO] [产矿机-客户端] 播放等级提升特效: level={}, pos={}".format(self.level, pos))

            # 播放金色粒子向上飞溅（30个粒子）
            for i in range(30):
                particle_id = ClientAPIHelper.play_particle(
                    "minecraft:villager_happy",  # 绿色爱心粒子（作为金色粒子的简化替代）
                    pos
                )
                if particle_id:
                    print("[INFO] [产矿机-客户端] 播放升级粒子: id={}, pos={}".format(particle_id, pos))

            print("[INFO] [产矿机-客户端] 等级提升特效播放完成")

        except Exception as e:
            print("[ERROR] [产矿机-客户端] 播放升级特效异常: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _play_level_upgrade_sound(self):
        # type: () -> None
        """
        播放等级提升音效

        P2.3功能实现（音效部分）
        """
        try:
            import mod.client.extraClientApi as clientApi

            # 获取位置
            if not hasattr(self, 'instance') or not self.instance:
                print("[WARN] [产矿机-客户端] instance未初始化，无法播放升级音效")
                return

            # [FIX 2025-11-04] 修复PresetInstanceClient没有get_position()方法的问题
            # 正确方式：从config中读取position
            position = self.instance.get_config("position") or self.instance.get_config("pos")
            if not position:
                print("[WARN] [产矿机-客户端] 无法获取position配置")
                return

            if isinstance(position, dict):
                pos = (position['x'] + 0.5, position['y'] + 0.5, position['z'] + 0.5)
            else:
                pos = (position[0] + 0.5, position[1] + 0.5, position[2] + 0.5)

            # 获取游戏组件
            game_comp = clientApi.GetEngineCompFactory().CreateGame(clientApi.GetLevelId())

            # 播放升级音效："random.levelup" - 升级音效
            game_comp.PlaySound(
                "random.levelup",       # 音效名称
                pos,                    # 播放位置
                1.0,                    # 音量
                1.0                     # 音调
            )

            print("[INFO] [产矿机-客户端] 播放等级提升音效: level={}, pos={}".format(self.level, pos))

        except Exception as e:
            print("[ERROR] [产矿机-客户端] 播放升级音效异常: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _get_resource_indicator_path(self, resource_type):
        """
        获取资源标识特效路径

        Args:
            resource_type: 资源类型

        Returns:
            str: 特效路径
        """
        # 根据资源类型返回不同的标识特效
        indicator_map = {
            'iron': 'particles/indicator_iron.json',
            'gold': 'particles/indicator_gold.json',
            'diamond': 'particles/indicator_diamond.json',
            'emerald': 'particles/indicator_emerald.json',
        }

        return indicator_map.get(resource_type, 'particles/indicator_default.json')

    def _get_resource_particle_type(self, resource_type):
        """
        获取资源粒子类型

        Args:
            resource_type: 资源类型

        Returns:
            str: 粒子类型
        """
        # 根据资源类型返回不同颜色的粒子
        particle_map = {
            'iron': 'minecraft:silver_glint',  # 银白色
            'gold': 'minecraft:gold_glint',    # 金色
            'diamond': 'minecraft:blue_glint', # 蓝色
            'emerald': 'minecraft:green_glint',# 绿色
        }

        return particle_map.get(resource_type, 'minecraft:white_glint')

    # ========== 特效和音效工具方法 ==========

    def _play_effect(self, effect_path, position):
        """
        播放特效

        Args:
            effect_path: 特效文件路径
            position: 特效位置 (dict: {x, y, z})

        Returns:
            int: 特效ID
        """
        # TODO: 需要引擎API支持
        print("[INFO] 播放特效: {} at {}".format(effect_path, position))
        return 0  # 占位返回

    def _stop_effect(self, effect_id):
        """
        停止特效

        Args:
            effect_id: 特效ID
        """
        # TODO: 需要引擎API支持
        print("[INFO] 停止特效: {}".format(effect_id))

    def _stop_all_effects(self):
        """停止所有特效"""
        for effect_id in self._effect_ids:
            self._stop_effect(effect_id)
        self._effect_ids = []

    def _play_sound(self, sound_path, position, volume=1.0, pitch=1.0):
        """
        播放音效

        Args:
            sound_path: 音效文件路径
            position: 播放位置
            volume: 音量 (0.0-1.0)
            pitch: 音调 (0.5-2.0)
        """
        # TODO: 需要引擎API支持
        print("[INFO] 播放音效: {} at {} (volume={}, pitch={})".format(
            sound_path, position, volume, pitch
        ))

    def _create_particle(self, particle_type, position):
        """
        创建粒子效果

        Args:
            particle_type: 粒子类型
            position: 粒子位置

        Returns:
            int: 粒子效果ID
        """
        # TODO: 需要引擎API支持
        print("[INFO] 创建粒子效果: {} at {}".format(particle_type, position))
        return 0  # 占位返回

    def _create_looping_particle(self, particle_type, position):
        """
        创建循环粒子效果

        Args:
            particle_type: 粒子类型
            position: 粒子位置

        Returns:
            int: 粒子效果ID
        """
        # TODO: 需要引擎API支持
        print("[INFO] 创建循环粒子: {} at {}".format(particle_type, position))
        return 0  # 占位返回

    def _stop_particle(self, particle_id):
        """
        停止粒子效果

        Args:
            particle_id: 粒子效果ID
        """
        # TODO: 需要引擎API支持
        print("[INFO] 停止粒子效果: {}".format(particle_id))

    # ========== P1.2功能实现 ==========

    def _on_sync_generator_data(self, instance, data):
        """
        接收服务端同步的产矿机数据

        P1.2功能：接收数据后创建浮动文字

        Args:
            instance: PresetInstanceClient对象
            data: dict 同步数据
                - resource_type_id: 资源类型ID
                - team: 队伍ID
                - level: 当前等级
                - next_generate: 下次生成时间（时间戳）
                - resource_name: 资源名称（中文）
                - period_ms: 生成周期（毫秒）
        """
        try:
            # ⚠️ 关键修复：保存到instance.data，而不是self
            # 原因：所有产矿机预设共享同一个GeneratorPresetDefClient对象
            instance.set_data('resource_type_id', data.get('resource_type_id', 'IRON'))
            instance.set_data('team', data.get('team'))
            instance.set_data('level', data.get('level', 1))
            instance.set_data('next_generate', data.get('next_generate', 0.0))
            instance.set_data('resource_name', data.get('resource_name', u'资源'))
            instance.set_data('period_ms', data.get('period_ms', 5000))
            instance.set_data('display_floating', data.get('display_floating', True))

            # 同时更新self（用于特效等非浮动文字功能，这些功能没有多实例问题）
            self.resource_type_id = data.get('resource_type_id', 'IRON')
            self.team = data.get('team')
            self.level = data.get('level', 1)
            self.next_generate = data.get('next_generate', 0.0)
            self.resource_name = data.get('resource_name', u'资源')
            self.period_ms = data.get('period_ms', 5000)
            self.display_floating = data.get('display_floating', True)

            # 注意：不在这里创建浮动文字
            # 等待服务端在游戏运行状态时发送"CreateFloatingText"消息

        except Exception as e:
            print("[ERROR] [产矿机-客户端] 接收同步数据异常: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _on_create_floating_text(self, instance):
        """
        处理创建浮动文字消息（游戏运行状态时）

        此方法在游戏进入运行状态后由服务端触发
        确保玩家已传送到游戏维度，TextBoard能正确显示

        Args:
            instance: PresetInstanceClient对象
        """
        # 从instance读取display_floating配置
        display_floating = instance.get_data("display_floating", True)
        if not display_floating:
            return

        # 如果已经创建，不重复创建
        existing_board_id = instance.get_data("floating_text_board_id")
        if existing_board_id is not None:
            return

        # 创建浮动文字
        self._create_floating_text(instance)

    def _create_floating_text(self, instance):
        # type: (object) -> None
        """
        创建浮动文字

        在产矿机上方显示资源类型、等级、倒计时

        Args:
            instance: PresetInstanceClient对象
        """
        try:
            from Script_NeteaseMod.systems.util.ClientAPIHelper import ClientAPIHelper

            # 计算浮动文字位置（产矿机上方3格）
            pos = instance.get_config("position") or instance.get_config("pos") or [0, 0, 0]
            if isinstance(pos, dict):
                floating_pos = (
                    pos['x'] + 0.5,  # 中心位置
                    pos['y'] + 3.0,  # 上方3格
                    pos['z'] + 0.5   # 中心位置
                )
            else:
                floating_pos = (
                    pos[0] + 0.5,
                    pos[1] + 3.0,
                    pos[2] + 0.5
                )

            # 格式化初始文字
            text = self._format_generator_text(instance)

            # 创建浮动文字
            floating_text_board_id = ClientAPIHelper.create_floating_text(
                text=text,
                pos=floating_pos,
                text_color=(1.0, 1.0, 1.0, 1.0),      # 白色文字
                board_color=(0.0, 0.0, 0.0, 0.3),     # 半透明黑色背景
                scale=(1.0, 1.0),                      # 正常大小
                face_camera=True,                      # 始终朝向相机
                depth_test=False                       # 穿过方块显示
            )

            if floating_text_board_id:
                # 存储浮动文字板ID到instance.data（实例级数据）
                instance.set_data("floating_text_board_id", floating_text_board_id)
                # 立即设置下次更新时间为当前时间，以便立即更新
                import time
                instance.set_data("next_text_update", time.time())
            else:
                print("[WARN] [产矿机-客户端] 创建浮动文字失败")

        except Exception as e:
            print("[ERROR] [产矿机-客户端] 创建浮动文字异常: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _update_floating_text(self, instance):
        # type: (object) -> None
        """
        更新浮动文字内容

        每秒更新一次倒计时

        P1.2功能核心逻辑

        Args:
            instance: PresetInstanceClient对象
        """
        try:
            from Script_NeteaseMod.systems.util.ClientAPIHelper import ClientAPIHelper

            # ⚠️ 关键修复：从instance读取floating_text_board_id
            floating_text_board_id = instance.get_data("floating_text_board_id")
            if not floating_text_board_id:
                return

            # 格式化新文字（需要从instance读取next_generate等数据）
            new_text = self._format_generator_text(instance)

            # 更新文字
            success = ClientAPIHelper.update_floating_text(
                floating_text_board_id,
                text=new_text
            )

            if not success:
                print("[WARN] [产矿机-客户端] 更新浮动文字失败: instance_id={}, board_id={}".format(
                    instance.instance_id, floating_text_board_id
                ))

        except Exception as e:
            print("[ERROR] [产矿机-客户端] 更新浮动文字异常: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _cleanup_floating_text(self):
        # type: () -> None
        """
        清理浮动文字

        P1.2功能清理逻辑
        """
        try:
            if self.floating_text_board_id is not None:
                from Script_NeteaseMod.systems.util.ClientAPIHelper import ClientAPIHelper
                success = ClientAPIHelper.destroy_floating_text(self.floating_text_board_id)

                if success:
                    print("[INFO] [产矿机-客户端] 浮动文字已清理: board_id={}".format(
                        self.floating_text_board_id
                    ))
                self.floating_text_board_id = None

        except Exception as e:
            print("[ERROR] [产矿机-客户端] 清理浮动文字异常: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _format_generator_text(self, instance):
        # type: (object) -> str
        """
        格式化产矿机浮动文字内容（匹配老项目格式）

        显示格式：
        - 公共产矿机：" §e铁锭 §r产矿机 \n§3等级: §b1\n§7||§k||§r §e10s §7||§k||"
        - 队伍产矿机："§c红队 §7- §e铁锭 §r产矿机 \n§3等级: §b1\n§7||§k||§r §e10s §7||§k||"

        Args:
            instance: PresetInstanceClient对象

        Returns:
            str: 格式化后的文字
        """
        try:
            # ⚠️ 关键修复：从instance读取数据
            resource_name = instance.get_data('resource_name', u'资源')
            level = instance.get_data('level', 1)
            team = instance.get_data('team')

            # 计算倒计时
            countdown_text = self._format_countdown(instance)

            # 根据是否有队伍，构建不同的文字
            if team and team != "NONE":
                # 队伍产矿机
                team_color, team_name = self._get_team_info(team)
                text = u"{}{} §7- §e{} §r产矿机 \n§3等级: §b{}\n{}".format(
                    team_color, team_name, resource_name, level, countdown_text
                )
            else:
                # 公共产矿机
                text = u" §e{} §r产矿机 \n§3等级: §b{}\n{}".format(
                    resource_name, level, countdown_text
                )

            return text

        except Exception as e:
            print(u"[ERROR] [产矿机-客户端] 格式化文字异常: {}".format(str(e)))
            return u"§e产矿机"

    def _format_countdown(self, instance):
        # type: (object) -> str
        """
        格式化倒计时文字（匹配老项目格式）

        Args:
            instance: PresetInstanceClient对象

        Returns:
            str: 倒计时文字，例如 "§7||§k||§r §e10s §7||§k||"
        """
        import time
        now = time.time()
        # ⚠️ 关键修复：从instance读取next_generate
        next_generate = instance.get_data('next_generate', 0.0)
        remaining = next_generate - now

        if remaining <= 0:
            seconds = 0
        elif remaining < 1.0:
            seconds = 0
        else:
            seconds = int(remaining)

        # 使用老项目的混淆字符格式
        return u"§7||§k||§r §e{}s §7||§k||".format(seconds)

    def _get_level_roman(self, level):
        # type: (int) -> str
        """
        将等级转换为罗马数字

        Args:
            level: 等级数字 (1-4)

        Returns:
            str: 罗马数字 (I, II, III, IV)
        """
        roman_map = {
            1: 'I',
            2: 'II',
            3: 'III',
            4: 'IV',
            5: 'V',
            6: 'VI',
            7: 'VII',
            8: 'VIII'
        }
        return roman_map.get(level, str(level))

    def _get_team_info(self, team_id):
        # type: (str) -> tuple
        """
        获取队伍颜色和名称

        Args:
            team_id: 队伍ID (RED, BLUE, GREEN, YELLOW等)

        Returns:
            tuple: (颜色代码, 队伍名称)
        """
        team_map = {
            'RED': ('§c', '红队'),
            'BLUE': ('§9', '蓝队'),
            'GREEN': ('§a', '绿队'),
            'YELLOW': ('§e', '黄队'),
            'PINK': ('§d', '粉队'),
            'CYAN': ('§b', '青队'),
            'WHITE': ('§f', '白队'),
            'GRAY': ('§7', '灰队')
        }

        return team_map.get(team_id.upper(), ('§f', team_id))

    # ========== P1.1功能实现 ==========

    def _create_floating_item_indicator(self, instance):
        # type: (object) -> None
        """
        创建浮空物品指示器

        P1.1功能：在产矿机上方显示资源物品图标（使用粒子效果简化方案）

        完整实现说明：
        真实的浮空物品实现需要：
        1. 在服务端使用CreateEngineItemEntity创建掉落物品实体
        2. 在服务端每Tick更新物品位置，维持浮空效果（使用SetPos）
        3. 在服务端监听ServerPlayerTryTouchEvent，阻止玩家拾取
        4. 在服务端预设停止时销毁物品实体

        简化方案：
        使用粒子效果代替真实物品，减少复杂度和性能开销

        Args:
            instance: PresetInstanceClient对象
        """
        try:
            from Script_NeteaseMod.systems.util.ClientAPIHelper import ClientAPIHelper

            # 计算浮空物品位置（产矿机上方2格）
            # ⚠️ 修复：使用get_config读取位置，而不是get_position()
            pos = instance.get_config("position") or instance.get_config("pos")
            if isinstance(pos, dict):
                item_pos = (
                    pos['x'] + 0.5,  # 中心位置
                    pos['y'] + 2.0,  # 上方2格
                    pos['z'] + 0.5   # 中心位置
                )
            else:
                item_pos = (
                    pos[0] + 0.5,
                    pos[1] + 2.0,
                    pos[2] + 0.5
                )

            # 简化方案：使用粒子效果代替真实物品
            # 根据资源类型选择不同颜色的粒子
            particle_name = "minecraft:villager_happy"  # 简化方案使用通用粒子

            # 创建粒子效果
            self.floating_item_particle_id = ClientAPIHelper.play_particle(
                particle_name,
                item_pos
            )

            if self.floating_item_particle_id:
                print("[INFO] [产矿机-客户端] 创建浮空物品指示器成功（粒子方案）: particle_id={}".format(
                    self.floating_item_particle_id
                ))
            else:
                print("[WARN] [产矿机-客户端] 创建浮空物品指示器失败")

            # TODO: 完整实现（使用真实物品实体）
            # 完整实现需要在服务端完成：
            # 1. 在服务端GeneratorPresetDefServer的on_start中创建物品实体
            # 2. 在服务端on_tick中更新物品位置（每Tick调用SetPos维持浮空）
            # 3. 监听ServerPlayerTryTouchEvent阻止拾取
            # 4. 在on_stop中销毁物品实体
            #
            # 示例代码（服务端）：
            # def on_start(self, instance):
            #     # 创建浮空物品
            #     floating_item_config = self.resource_type.get('floating_item', {})
            #     item_dict = {
            #         'itemName': floating_item_config.get('itemName', 'minecraft:iron_ingot'),
            #         'count': 1,
            #         'auxValue': 0
            #     }
            #     pos = instance.get_position()
            #     floating_pos = (pos['x'] + 0.5, pos['y'] + 2.0, pos['z'] + 0.5)
            #
            #     # 使用CreateEngineItemEntity创建掉落物品
            #     self.floating_item_entity_id = serverApi.GetEngineCompFactory().CreateEngineItemEntity(
            #         serverApi.GetLevelId(),
            #         item_dict,
            #         floating_pos,
            #         self.instance.dimension_id
            #     )
            #
            # def on_tick(self, instance):
            #     # 更新浮空物品位置
            #     if self.floating_item_entity_id:
            #         pos = instance.get_position()
            #         floating_pos = (pos['x'] + 0.5, pos['y'] + 2.0, pos['z'] + 0.5)
            #         serverApi.GetEngineCompFactory().CreatePos(self.floating_item_entity_id).SetPos(floating_pos)

        except Exception as e:
            print("[ERROR] [产矿机-客户端] 创建浮空物品指示器异常: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _cleanup_floating_item_indicator(self):
        # type: () -> None
        """
        清理浮空物品指示器

        P1.1功能清理逻辑
        """
        try:
            if self.floating_item_particle_id is not None:
                from Script_NeteaseMod.systems.util.ClientAPIHelper import ClientAPIHelper
                success = ClientAPIHelper.remove_particle(self.floating_item_particle_id)

                if success:
                    print("[INFO] [产矿机-客户端] 浮空物品指示器已清理: particle_id={}".format(
                        self.floating_item_particle_id
                    ))
                self.floating_item_particle_id = None

        except Exception as e:
            print("[ERROR] [产矿机-客户端] 清理浮空物品指示器异常: {}".format(str(e)))
            import traceback
            traceback.print_exc()