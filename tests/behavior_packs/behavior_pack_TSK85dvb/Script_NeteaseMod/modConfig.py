# -*- coding: utf-8 -*-
"""
EC起床战争 - Mod配置文件

功能:
- 定义Mod的基本配置
- 定义服务端系统注册配置
- 定义客户端预设类型注册配置
"""

# ========== Mod基本配置 ==========
MOD_NAME = "ECBedWars"
MOD_VERSION = "0.0.1"

# ========== 服务端系统注册配置 ==========
# 服务端系统配置列表
# 每个系统配置包含: (系统名, 系统类路径)
#
# 注册顺序说明:
# 1. RoomManagementSystem - 最先注册,提供队伍数据、房间管理等基础数据
# 2. BedWarsGameSystem - 依赖RoomManagementSystem的team_players等数据
# 3. 其他系统 - 无特殊依赖顺序
SERVER_SYSTEMS = [
    ("RoomManagementSystem", "Script_NeteaseMod.systems.RoomManagementSystem.RoomManagementSystem"),
    ("BedWarsGameSystem", "Script_NeteaseMod.systems.BedWarsGameSystem.BedWarsGameSystem"),
    ("ShopServerSystem", "Script_NeteaseMod.systems.shop.ShopServerSystem.ShopServerSystem"),
    ("PropsManagementSystem", "Script_NeteaseMod.systems.PropsManagementSystem.PropsManagementSystem"),
    ("IronGolemAISystem", "Script_NeteaseMod.systems.IronGolemAISystem.IronGolemAISystem"),
    ("SilverfishAISystem", "Script_NeteaseMod.systems.SilverfishAISystem.SilverfishAISystem"),
    ("ServerFormServerSystem", "Script_NeteaseMod.systems.server_form.ServerFormServerSystem.ServerFormServerSystem"),
]

# ========== 客户端系统注册配置 ==========
# 客户端系统配置列表
# 每个系统配置包含: (系统名, 系统类路径)
CLIENT_SYSTEMS = [
    ("RoomManagementClientSystem", "Script_NeteaseMod.systems.RoomManagementClientSystem.RoomManagementClientSystem"),
    ("HUDSystem", "Script_NeteaseMod.systems.HUDSystem.HUDSystem"),
    ("ParticleClientSystem", "Script_NeteaseMod.systems.client.ParticleClientSystem.ParticleClientSystem"),
    ("ChangeDimensionAnimClient", "Script_NeteaseMod.systems.ChangeDimensionClientSystem.ChangeDimensionClientSystem"),
    ("CameraPreviewClientSystem", "Script_NeteaseMod.systems.CameraPreviewClientSystem.CameraPreviewClientSystem"),
    ("FocusHUDClientSystem", "Script_NeteaseMod.systems.FocusHUDClientSystem.FocusHUDClientSystem"),
    ("ServerFormClientSystem", "Script_NeteaseMod.systems.server_form.ServerFormClientSystem.ServerFormClientSystem"),
    ("ShopClientSystem", "Script_NeteaseMod.systems.shop.ShopClientSystem.ShopClientSystem"),
]

# ========== 预设类型配置（双端统一） ==========
# 预设类型基础定义
# 格式: (预设类型名称, 预设类基础名)
PRESET_TYPE_DEFINITIONS = [
    ("bedwars:bed", "BedPresetDef"),
    ("bedwars:generator", "GeneratorPresetDef"),
    ("bedwars:shop", "ShopPresetDef"),
    ("bedwars:spawn", "SpawnPresetDef"),
    ("bedwars:practice", "PracticePresetDef"),
    ("bedwars:guide", "GuidePresetDef"),
    ("bedwars:guide_bed", "GuideBedPresetDef"),
    ("bedwars:guide_shop", "GuideShopPresetDef"),
    ("bedwars:guide_generator", "GuideGeneratorPresetDef"),
    ("camera:track_point", "CameraTrackPointPresetDef"),  # 相机追踪点预设
]

# ========== 服务端预设类型注册配置 ==========
# 服务端预设类的导入路径和类名
# 格式: (类名, 模块路径)
# 注意: 服务端预设文件名和类名都是 XXXServer 格式
SERVER_PRESET_IMPORTS = [
    (class_name + "Server", "Script_NeteaseMod.presets.server.{}Server".format(class_name))
    for _, class_name in PRESET_TYPE_DEFINITIONS
]

# 服务端预设类型映射
# 格式: (预设类型名称, 类名)
SERVER_PRESET_TYPES = [
    (preset_type, class_name + "Server")
    for preset_type, class_name in PRESET_TYPE_DEFINITIONS
]

# ========== 客户端预设类型注册配置 ==========
# 客户端预设类的导入路径
# 格式: (类名, 模块路径)
CLIENT_PRESET_IMPORTS = [
    (class_name + "Client", "Script_NeteaseMod.presets.client.{}".format(class_name + "Client"))
    for _, class_name in PRESET_TYPE_DEFINITIONS
]

# 客户端预设类型映射
CLIENT_PRESET_TYPES = [
    (preset_type, class_name + "Client")
    for preset_type, class_name in PRESET_TYPE_DEFINITIONS
]