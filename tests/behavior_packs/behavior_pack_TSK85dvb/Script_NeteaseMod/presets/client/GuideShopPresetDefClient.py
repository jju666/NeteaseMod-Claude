# -*- coding: utf-8 -*-
"""
GuideShopPresetDefClient - 教程指引商店预设 (客户端)

功能:
- 配置教程指引中的商店NPC客户端渲染
- 主要用于大厅练习区域展示商店购买机制

原预设: BedWarsGuideShopPart
"""

from ECPresetServerScripts import PresetDefinitionClient


class GuideShopPresetDefClient(PresetDefinitionClient):
    """
    教程指引商店预设 - 客户端

    注意: 商店NPC由ECPreset框架自动创建
          客户端预设只负责渲染相关的配置
    """

    def __init__(self):
        super(GuideShopPresetDefClient, self).__init__()

    def on_init(self, instance):
        """
        预设初始化

        Args:
            instance: PresetInstanceClient对象
        """
        print("[INFO] [bedwars:guide_shop-客户端] 初始化")

    def on_start(self, instance):
        """
        预设启动

        Args:
            instance: PresetInstanceClient对象
        """
        print("[INFO] [bedwars:guide_shop-客户端] 启动")

    def on_stop(self, instance):
        """
        预设停止

        Args:
            instance: PresetInstanceClient对象
        """
        print("[INFO] [bedwars:guide_shop-客户端] 停止")

    def on_destroy(self, instance):
        """
        预设销毁

        Args:
            instance: PresetInstanceClient对象
        """
        print("[INFO] [bedwars:guide_shop-客户端] 销毁")