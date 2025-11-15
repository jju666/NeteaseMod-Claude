# -*- coding: utf-8 -*-
"""
练习区域预设 - 客户端

功能:
- 客户端不需要特殊逻辑
- 预留接口以备后续扩展(如显示边界粒子效果)
"""

from ECPresetServerScripts import PresetDefinitionClient


class PracticePresetDefClient(PresetDefinitionClient):
    """
    练习区域预设客户端实现

    当前版本:
    - 仅作为框架占位
    - 未来可扩展: 显示练习区域边界粒子效果等
    """

    def __init__(self):
        super(PracticePresetDefClient, self).__init__()

    def on_init(self, instance):
        """
        预设初始化

        Args:
            instance: PresetInstanceClient对象
        """
        print("[INFO] [练习区域Client] 初始化")

    def on_start(self, instance):
        """
        预设启动

        Args:
            instance: PresetInstanceClient对象
        """
        print("[INFO] [练习区域Client] 启动")

    def on_tick(self, instance, dt):
        """
        每帧更新

        Args:
            instance: PresetInstanceClient对象
            dt: 自上一帧以来的时间增量（秒）
        """
        pass

    def on_stop(self, instance):
        """
        预设停止

        Args:
            instance: PresetInstanceClient对象
        """
        print("[INFO] [练习区域Client] 停止")

    def on_destroy(self, instance):
        """
        预设销毁

        Args:
            instance: PresetInstanceClient对象
        """
        print("[INFO] [练习区域Client] 销毁")
