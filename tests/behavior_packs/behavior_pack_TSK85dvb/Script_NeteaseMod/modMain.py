# -*- coding: utf-8 -*-
"""
EC起床战争 - Mod入口文件

功能:
- 注册服务端和客户端系统
- 注册EC预设类型
"""

from mod.common.mod import Mod
import mod.client.extraClientApi as clientApi
import mod.server.extraServerApi as serverApi
# 避免在模块级别导入modConfig，防止引擎误将其识别为Mod类
from modConfig import MOD_NAME, MOD_VERSION, SERVER_SYSTEMS, CLIENT_SYSTEMS
from modConfig import CLIENT_PRESET_IMPORTS, CLIENT_PRESET_TYPES


@Mod.Binding(name=MOD_NAME, version=MOD_VERSION)
class Script_NeteaseMod(object):

    def __init__(self):
        pass

    @Mod.InitServer()
    def Script_NeteaseModServerInit(self):
        """服务端初始化 - 注册服务端系统和预设类型"""
        print("[INFO] [EC起床战争] 服务端初始化开始...")

        try:
            from ECPresetServerScripts import get_server_system
            print("[INFO] [EC起床战争] 开始注册服务端预设类型...")

            # 获取ECPreset框架的服务端系统
            preset_system = get_server_system()
            print("[INFO] [EC起床战争] 成功获取 ECPreset 服务端系统")

            # 导入服务端预设定义
            from Script_NeteaseMod.presets.server.BedPresetDefServer import BedPresetDefServer
            from Script_NeteaseMod.presets.server.GeneratorPresetDefServer import GeneratorPresetDefServer
            from Script_NeteaseMod.presets.server.ShopPresetDefServer import ShopPresetDefServer
            from Script_NeteaseMod.presets.server.SpawnPresetDefServer import SpawnPresetDefServer
            from Script_NeteaseMod.presets.server.PracticePresetDefServer import PracticePresetDefServer
            from Script_NeteaseMod.presets.server.GuidePresetDefServer import GuidePresetDefServer
            from Script_NeteaseMod.presets.server.GuideBedPresetDefServer import GuideBedPresetDefServer
            from Script_NeteaseMod.presets.server.GuideShopPresetDefServer import GuideShopPresetDefServer
            from Script_NeteaseMod.presets.server.GuideGeneratorPresetDefServer import GuideGeneratorPresetDefServer
            from Script_NeteaseMod.presets.server.CameraTrackPointPresetDefServer import CameraTrackPointPresetDefServer

            # 注册预设类型（使用bedwars:前缀作为命名空间）
            preset_types = [
                ("bedwars:bed", BedPresetDefServer),
                ("bedwars:generator", GeneratorPresetDefServer),
                ("bedwars:shop", ShopPresetDefServer),
                ("bedwars:spawn", SpawnPresetDefServer),
                ("bedwars:practice", PracticePresetDefServer),
                ("bedwars:guide", GuidePresetDefServer),
                ("bedwars:guide_bed", GuideBedPresetDefServer),
                ("bedwars:guide_shop", GuideShopPresetDefServer),
                ("bedwars:guide_generator", GuideGeneratorPresetDefServer),
                ("camera:track_point", CameraTrackPointPresetDefServer),  # 相机追踪点预设
            ]

            for preset_type, preset_class in preset_types:
                preset_system.RegisterPresetType(preset_type, preset_class)
                print("[INFO] [EC起床战争] 服务端预设类型 '{}' 注册完成".format(preset_type))

        except Exception as e:
            print("[ERROR] [EC起床战争] 注册服务端预设类型失败 - {}".format(e))
            import traceback
            traceback.print_exc()

        # 从配置文件注册服务端系统
        for system_name, system_path in SERVER_SYSTEMS:
            serverApi.RegisterSystem(
                MOD_NAME,
                system_name,
                system_path
            )
            print("[INFO] [EC起床战争] {} 已注册".format(system_name))

        print("[INFO] [EC起床战争] 服务端初始化完成")

    @Mod.DestroyServer()
    def Script_NeteaseModServerDestroy(self):
        """服务端销毁"""
        print("[INFO] [EC起床战争] 服务端销毁")

    @Mod.InitClient()
    def Script_NeteaseModClientInit(self):
        """客户端初始化 - 注册客户端系统和预设类型"""
        print("[INFO] [EC起床战争] 客户端初始化开始...")

        # ECHUDScreenNode UI将在HUDSystem的UiInitFinished事件中注册
        # 不在这里提前注册，避免时序问题
        print("[INFO] [EC起床战争] ECHUDScreenNode 将在UI初始化完成后注册")

        # 注册客户端系统
        for system_name, system_path in CLIENT_SYSTEMS:
            clientApi.RegisterSystem(
                MOD_NAME,
                system_name,
                system_path
            )
            print("[INFO] [EC起床战争] 客户端系统 {} 已注册".format(system_name))

        # 注册客户端预设类型
        from ECPresetServerScripts import get_client_mgr
        print("[INFO] [EC起床战争] 开始注册客户端预设类型...")

        # 获取ECPreset框架的客户端管理器
        client_mgr = get_client_mgr()
        print("[INFO] [EC起床战争] 成功获取 ECPreset 客户端管理器")

        # 从配置文件动态导入客户端预设定义
        preset_classes = {}
        for class_name, module_path in CLIENT_PRESET_IMPORTS:
            module = __import__(module_path, fromlist=[class_name])
            preset_classes[class_name] = getattr(module, class_name)
            print("[INFO] [EC起床战争] 已导入预设类 '{}'".format(class_name))

        # 从配置文件注册预设类型
        for preset_type, class_name in CLIENT_PRESET_TYPES:
            preset_class = preset_classes.get(class_name)
            if preset_class:
                client_mgr.register_preset_type(preset_type, preset_class)
                print("[INFO] [EC起床战争] 客户端预设类型 '{}' 注册完成".format(preset_type))
            else:
                print("[WARNING] [EC起床战争] 未找到预设类 '{}'".format(class_name))

        print("[INFO] [EC起床战争] 客户端初始化完成")

    @Mod.DestroyClient()
    def Script_NeteaseModClientDestroy(self):
        """客户端销毁"""
        print("[INFO] [EC起床战争] 客户端销毁")
