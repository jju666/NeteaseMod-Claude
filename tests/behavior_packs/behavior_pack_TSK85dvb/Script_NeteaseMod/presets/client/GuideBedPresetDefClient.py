# -*- coding: utf-8 -*-
"""
GuideBedPresetDefClient - 床位保护演示预设 (客户端)

功能:
- 接收服务端的方块放置/清除事件
- 在对应位置播放白色粒子效果
- 增强视觉反馈，提升教学效果

原预设: BedWarsGuideBedPart
"""

from ECPresetServerScripts import PresetDefinitionClient
import mod.client.extraClientApi as clientApi


class GuideBedPresetDefClient(PresetDefinitionClient):
    """
    床位保护演示预设 - 客户端

    职责:
    - 监听服务端发送的guide_bed_effect事件
    - 播放白色粒子效果（复用ecbedwars:generator粒子）
    """

    def __init__(self):
        super(GuideBedPresetDefClient, self).__init__()

        self.is_listening = False  # 是否已注册事件监听

    def on_init(self, instance):
        """
        预设初始化

        Args:
            instance: PresetInstanceClient对象
        """
        print("[INFO] [bedwars:guide_bed-客户端] 初始化")

    def on_start(self, instance):
        """
        预设启动 - 通过receive_server_message接收事件

        Args:
            instance: PresetInstanceClient对象
        """
        print("[INFO] [bedwars:guide_bed-客户端] 启动")
        # 注意: 不需要手动注册事件监听
        # 服务端通过instance.send_to_client()发送消息时,
        # 会自动触发on_server_message()回调

    def _on_play_particle_effect(self, args):
        """
        播放粒子效果 - 事件回调

        Args:
            args: dict 事件参数
                - pos_list: list 位置列表 [(x, y, z), ...]
        """
        pos_list = args.get("pos_list", [])

        # print("[DEBUG] [bedwars:guide_bed-客户端] 收到粒子效果事件，位置数: {}".format(len(pos_list)))

        try:
            comp_factory = clientApi.GetEngineCompFactory()

            for pos in pos_list:
                # 创建粒子系统（复用ecbedwars:generator粒子）
                comp_particle = comp_factory.CreateParticleSystem(None)
                par_id = comp_particle.Create("ecbedwars:generator", pos)

                if par_id:
                    # 设置白色粒子
                    # RGB(224, 224, 224) → 归一化 (224/255, 224/255, 224/255)
                    color_value = 224.0 / 255.0
                    comp_particle.SetVariable(par_id, "variable.color_r", color_value)
                    comp_particle.SetVariable(par_id, "variable.color_g", color_value)
                    comp_particle.SetVariable(par_id, "variable.color_b", color_value)

                    # print("[DEBUG] [bedwars:guide_bed-客户端] 播放白色粒子: {}".format(pos))
                else:
                    print("[ERROR] [bedwars:guide_bed-客户端] 粒子创建失败: {}".format(pos))

        except Exception as e:
            print("[ERROR] [bedwars:guide_bed-客户端] 播放粒子效果异常: {}".format(e))
            import traceback
            traceback.print_exc()

    def on_server_message(self, instance, message_type, data):
        """
        接收服务端消息回调 - ECPreset框架标准接口

        Args:
            instance: PresetInstanceClient对象
            message_type: str 消息类型
            data: dict 消息数据
        """
        if message_type == "guide_bed_effect":
            self._on_play_particle_effect(data)

    def on_stop(self, instance):
        """
        预设停止

        Args:
            instance: PresetInstanceClient对象
        """
        print("[INFO] [bedwars:guide_bed-客户端] 停止")

    def on_destroy(self, instance):
        """
        预设销毁

        Args:
            instance: PresetInstanceClient对象
        """
        print("[INFO] [bedwars:guide_bed-客户端] 销毁")
