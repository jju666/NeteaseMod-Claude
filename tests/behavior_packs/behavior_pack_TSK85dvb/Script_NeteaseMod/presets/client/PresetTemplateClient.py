# -*- coding: utf-8 -*-
"""
EC预设模板 - 客户端

这是一个客户端EC预设的开发模板，展示了如何创建客户端预设类型。
客户端预设主要负责特效、音效、粒子效果等表现层逻辑。

使用方法:
1. 复制此文件，重命名为 YourPresetDefClient.py
2. 修改类名为 YourPresetDefClient
3. 实现生命周期钩子方法
4. 在 modMain.py 中注册预设类型 (客户端)
"""

# 导入EC预设框架类
from ECPresetServerScripts import PresetDefinitionClient

# 导入引擎API (按需导入)
# import mod.client.extraClientApi as clientApi
# ClientCompFactory = clientApi.GetClientCompFactory()


class PresetTemplateClient(PresetDefinitionClient):
    """
    预设模板类 - 客户端

    继承自 PresetDefinitionClient，实现预设的客户端表现逻辑。

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
        instance: PresetInstanceClient对象，提供API访问

    客户端预设通常用于:
    - 播放特效和音效
    - 显示粒子效果
    - 更新UI显示
    - 客户端动画
    """

    def __init__(self):
        """
        构造函数

        注意: 不要在__init__中执行复杂逻辑，应该放在on_init中。
        """
        super(PresetTemplateClient, self).__init__()

        # 特效ID列表 (用于清理)
        self._effect_ids = []

        # 粒子效果ID列表
        self._particle_ids = []

    # ========== 生命周期钩子 ==========

    def on_init(self, instance):
        """
        预设初始化钩子

        在预设实例创建后立即调用。用于:
        - 解析预设配置数据
        - 初始化客户端状态
        - 预加载资源

        Args:
            instance: PresetInstanceClient对象

        可用API:
            instance.preset_id       - 获取预设ID
            instance.preset_type     - 获取预设类型
            instance.data            - 获取/设置预设数据
            instance.get_position()  - 获取预设位置
        """
        print("[INFO] [{}] 客户端预设初始化: {}".format(self.preset_type, self.preset_id))

        # 示例: 解析配置数据
        # [FIX 2025-11-04] 修复PresetInstanceClient没有get_position()方法的问题
        position = instance.get_config("position") or instance.get_config("pos")
        print("  - 位置: {}".format(position))

        # 示例: 预加载特效资源
        effect_path = instance.data.get("effect_path")
        if effect_path:
            print("  - 特效路径: {}".format(effect_path))

    def on_start(self, instance):
        """
        预设启动钩子

        在预设启动时调用。用于:
        - 播放启动特效
        - 播放背景音效
        - 开始粒子效果

        Args:
            instance: PresetInstanceClient对象

        可用API:
            instance.emit_event(event_name, event_data)  - 发送客户端事件
            instance.listen_event(event_name, callback)  - 监听客户端事件
        """
        print("[INFO] [{}] 客户端预设启动: {}".format(self.preset_type, self.preset_id))

        # 示例: 播放启动特效
        # [FIX 2025-11-04] 修复PresetInstanceClient没有get_position()方法的问题
        position = instance.get_config("position") or instance.get_config("pos")
        # effect_id = self._play_effect("particles/my_effect.json", position)
        # self._effect_ids.append(effect_id)

        # 示例: 播放音效
        # self._play_sound("sounds/preset_start.ogg", position)

    def on_tick(self, instance):
        """
        预设Tick钩子 (可选)

        每个游戏Tick调用一次。用于:
        - 更新特效位置
        - 更新粒子效果
        - 客户端动画

        注意: 此方法会频繁调用，需要注意性能。
        如果不需要Tick更新，可以不实现此方法。

        Args:
            instance: PresetInstanceClient对象
        """
        # 示例: 更新特效位置
        # if self._effect_ids:
        #     position = instance.get_position()
        #     for effect_id in self._effect_ids:
        #         self._update_effect_position(effect_id, position)

    def on_stop(self, instance):
        """
        预设停止钩子

        在预设停止时调用。用于:
        - 停止特效
        - 停止音效
        - 清理粒子效果

        Args:
            instance: PresetInstanceClient对象
        """
        print("[INFO] [{}] 客户端预设停止: {}".format(self.preset_type, self.preset_id))

        # 示例: 停止所有特效
        self._stop_all_effects()

        # 示例: 停止所有粒子效果
        self._stop_all_particles()

    def on_destroy(self, instance):
        """
        预设销毁钩子

        在预设实例销毁前调用。用于:
        - 释放资源
        - 最终清理

        Args:
            instance: PresetInstanceClient对象
        """
        print("[INFO] [{}] 客户端预设销毁: {}".format(self.preset_type, self.preset_id))

        # 确保所有资源都被清理
        self._effect_ids = []
        self._particle_ids = []

    # ========== 特效相关方法 ==========

    def _play_effect(self, effect_path, position):
        """
        播放特效

        Args:
            effect_path: 特效文件路径
            position: 特效位置 (dict: {x, y, z})

        Returns:
            int: 特效ID (用于后续操作)
        """
        # 示例实现 (需要引擎API支持)
        # comp_factory = ClientCompFactory()
        # effect_comp = comp_factory.CreateComponent(...)
        # effect_id = effect_comp.PlayEffect(effect_path, position)
        # return effect_id

        print("[INFO] 播放特效: {} at {}".format(effect_path, position))
        return 0  # 占位返回

    def _stop_effect(self, effect_id):
        """
        停止特效

        Args:
            effect_id: 特效ID
        """
        # 示例实现
        # comp_factory = ClientCompFactory()
        # effect_comp = comp_factory.CreateComponent(...)
        # effect_comp.StopEffect(effect_id)

        print("[INFO] 停止特效: {}".format(effect_id))

    def _stop_all_effects(self):
        """停止所有特效"""
        for effect_id in self._effect_ids:
            self._stop_effect(effect_id)
        self._effect_ids = []

    # ========== 音效相关方法 ==========

    def _play_sound(self, sound_path, position, volume=1.0, pitch=1.0):
        """
        播放音效

        Args:
            sound_path: 音效文件路径
            position: 播放位置 (dict: {x, y, z})
            volume: 音量 (0.0-1.0)
            pitch: 音调 (0.5-2.0)
        """
        # 示例实现
        # comp_factory = ClientCompFactory()
        # sound_comp = comp_factory.CreateComponent(...)
        # sound_comp.PlaySound(sound_path, position, volume, pitch)

        print("[INFO] 播放音效: {} at {} (volume={}, pitch={})".format(
            sound_path, position, volume, pitch
        ))

    # ========== 粒子效果相关方法 ==========

    def _create_particle(self, particle_type, position):
        """
        创建粒子效果

        Args:
            particle_type: 粒子类型
            position: 粒子位置 (dict: {x, y, z})

        Returns:
            int: 粒子效果ID
        """
        # 示例实现
        # comp_factory = ClientCompFactory()
        # particle_comp = comp_factory.CreateComponent(...)
        # particle_id = particle_comp.CreateParticle(particle_type, position)
        # return particle_id

        print("[INFO] 创建粒子效果: {} at {}".format(particle_type, position))
        return 0  # 占位返回

    def _stop_particle(self, particle_id):
        """
        停止粒子效果

        Args:
            particle_id: 粒子效果ID
        """
        print("[INFO] 停止粒子效果: {}".format(particle_id))

    def _stop_all_particles(self):
        """停止所有粒子效果"""
        for particle_id in self._particle_ids:
            self._stop_particle(particle_id)
        self._particle_ids = []


# ========== 预设类型注册 ==========
#
# 在 modMain.py 中注册此预设类型 (客户端):
#
# from presets.client.PresetTemplateClient import PresetTemplateClient
#
# # 客户端System的Destroy方法中:
# preset_mgr_client = get_client_mgr()
# preset_mgr_client.register_preset_type("preset_template", PresetTemplateClient)
#