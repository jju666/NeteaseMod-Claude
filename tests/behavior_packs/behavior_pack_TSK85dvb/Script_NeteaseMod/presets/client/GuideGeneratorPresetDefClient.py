# -*- coding: utf-8 -*-
"""
GuideGeneratorPresetDefClient - 资源生成器演示预设 (客户端)

功能:
- 接收服务端的资源生成事件（通过 ECPreset 框架消息机制）
- 在对应位置播放粒子效果
- 根据资源类型显示不同颜色的粒子
- 增强视觉反馈，提升教学效果

原预设: BedWarsGuideGeneratorPart (客户端部分)
"""

from ECPresetServerScripts import PresetDefinitionClient
import mod.client.extraClientApi as clientApi


class GuideGeneratorPresetDefClient(PresetDefinitionClient):
    """
    资源生成器演示预设 - 客户端

    职责:
    - 通过 on_server_message 接收服务端消息
    - 播放粒子效果（复用ecbedwars:generator粒子）
    - 根据资源类型设置粒子颜色
      - 铁锭：RGB(224, 224, 224) 银白色
      - 金锭：RGB(255, 192, 0) 金黄色
    """

    def __init__(self):
        super(GuideGeneratorPresetDefClient, self).__init__()

    def on_init(self, instance):
        """
        预设初始化

        Args:
            instance: PresetInstanceClient对象
        """
        print("[INFO] [bedwars:guide_generator-客户端] 初始化")

    def on_start(self, instance):
        """
        预设启动

        Args:
            instance: PresetInstanceClient对象
        """
        print("[INFO] [bedwars:guide_generator-客户端] 启动")

    # ========== 接收服务端消息（核心） ==========

    def on_server_message(self, instance, message_type, data):
        """
        接收服务端消息 - ECPreset 框架消息机制

        Args:
            instance: PresetInstanceClient对象
            message_type: 消息类型（字符串）
            data: 消息数据（字典）
        """
        if message_type == "guide_generator_effect":
            # 收到生成器粒子效果消息
            self._on_play_particle_effect(data)
        else:
            print("[WARN] [bedwars:guide_generator-客户端] 未知消息类型: {}".format(message_type))

    def _on_play_particle_effect(self, data):
        """
        播放粒子效果 - 消息处理（参考老项目BedWarsGuideGeneratorPart.client_generator_effect）

        Args:
            data: dict 消息数据
                - pos: list/tuple (x, y, z) 粒子位置
                - color_id: str 物品名称（用于确定粒子颜色）
        """
        pos = data.get("pos")
        item_name = data.get("color_id")  # 注意：服务端发送的是color_id

        if not pos or not item_name:
            print("[ERROR] [bedwars:guide_generator-客户端] 粒子效果消息参数不完整: {}".format(data))
            return

        try:
            comp_factory = clientApi.GetEngineCompFactory()

            # 确保位置是元组格式 (x, y, z)
            if isinstance(pos, list):
                pos = tuple(pos)

            # 创建粒子系统（复用ecbedwars:generator粒子）
            # 参考老项目：comp_particle.Create("ecbedwars:generator", pos)
            comp_particle = comp_factory.CreateParticleSystem(None)
            par_id = comp_particle.Create("ecbedwars:generator", pos)

            if par_id:
                # 根据物品类型获取粒子颜色
                color_r, color_g, color_b = self._get_particle_color(item_name)

                # 设置粒子颜色变量
                comp_particle.SetVariable(par_id, "variable.color_r", color_r)
                comp_particle.SetVariable(par_id, "variable.color_g", color_g)
                comp_particle.SetVariable(par_id, "variable.color_b", color_b)

                # print("[DEBUG] [bedwars:guide_generator-客户端] 播放粒子: item={}, color=RGB({}, {}, {})".format(
                #     item_name, int(color_r * 255), int(color_g * 255), int(color_b * 255)
                # )

        except Exception as e:
            print("[ERROR] [bedwars:guide_generator-客户端] 播放粒子效果异常: {}".format(e))
            import traceback
            traceback.print_exc()

    def _get_particle_color(self, item_name):
        """
        根据物品类型获取粒子颜色（归一化到0-1）

        Args:
            item_name: str 物品名称

        Returns:
            tuple (r, g, b) 归一化的RGB颜色值（0.0-1.0）
        """
        if item_name == "minecraft:iron_ingot":
            # 铁锭：银白色 RGB(224, 224, 224)
            return 224.0 / 255.0, 224.0 / 255.0, 224.0 / 255.0
        elif item_name == "minecraft:gold_ingot":
            # 金锭：金黄色 RGB(255, 192, 0)
            return 255.0 / 255.0, 192.0 / 255.0, 0.0
        else:
            # 默认：白色 RGB(255, 255, 255)
            return 1.0, 1.0, 1.0

    def on_stop(self, instance):
        """
        预设停止

        Args:
            instance: PresetInstanceClient对象
        """
        print("[INFO] [bedwars:guide_generator-客户端] 停止")

    def on_destroy(self, instance):
        """
        预设销毁

        Args:
            instance: PresetInstanceClient对象
        """
        print("[INFO] [bedwars:guide_generator-客户端] 销毁")
