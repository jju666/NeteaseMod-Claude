# -*- coding: utf-8 -*-
r"""
TeamType.py - 队伍类型定义模块

该模块定义了起床战争中所有队伍类型的属性，包括：
- 队伍ID
- 队伍名称
- 颜色代码
- RGB颜色值
- 文本图标
- 羊毛状态

参考文件：D:\EcWork\NetEaseMapECBedWars备份\...\Parts\ECBedWars\team\TeamType.py
"""


def unsigned_to_signed(unsigned_int):
    """
    将无符号整数转换为有符号整数（用于颜色值转换）

    :param unsigned_int: 无符号整数
    :return: 有符号整数
    """
    max_signed = 2 ** 31 - 1

    if unsigned_int > max_signed:
        signed_argb_int = unsigned_int - 2 ** 32
    else:
        signed_argb_int = unsigned_int
    return signed_argb_int


class TeamType(object):
    """
    队伍类型类

    定义队伍的所有属性：ID、名称、颜色、图标等
    """

    def __init__(self, team_id, name, color, item_color, rgb_color, text_icon, text_icon_gray, wool_state):
        """
        初始化队伍类型

        :param team_id: 队伍ID (如 "RED", "BLUE")
        :param name: 队伍名称 (如 "红队", "蓝队")
        :param color: Minecraft颜色代码 (如 "§c", "§9")
        :param item_color: 物品颜色ID (如 14=红色, 11=蓝色)
        :param rgb_color: RGB颜色元组 (r, g, b)
        :param text_icon: 文本图标 (如 "{icon-ec-wool-red}")
        :param text_icon_gray: 灰色文本图标 (如 "{icon-ec-wool-red-died}")
        :param wool_state: 羊毛方块状态 (如 {"color": "red"})
        """
        self.team_id = team_id
        self.name = name
        self.color = color
        self.item_color = item_color
        self.rgb_color = rgb_color
        self.text_icon = text_icon
        self.text_icon_gray = text_icon_gray
        self.wool_state = wool_state

    def get_formatted_name(self):
        """
        获取带颜色代码的队伍名称

        :return: 格式化的队伍名称 (如 "§c红队")
        """
        return self.color + self.name

    def get_text_icon(self, gray=False):
        """
        获取文本图标

        :param gray: 是否使用灰色图标（队伍被淘汰时）
        :return: 文本图标字符串
        """
        return self.text_icon_gray if gray else self.text_icon

    def get_rgb_color_int(self):
        """
        获取RGB颜色的整数表示（ARGB格式）

        :return: ARGB颜色整数值
        """
        return unsigned_to_signed(0xff << 24 | self.rgb_color[0] << 16 | self.rgb_color[1] << 8 | self.rgb_color[2])


# 全局队伍类型字典
# 定义了8个队伍类型：红、蓝、黄、绿、白、青、粉、灰
team_types = {
    "RED": TeamType(
        "RED", "红队", "§c", 14, (255, 20, 20),
        "{icon-ec-wool-red}", "{icon-ec-wool-red-died}",
        {"color": "red"}
    ),
    "BLUE": TeamType(
        "BLUE", "蓝队", "§9", 11, (50, 100, 250),
        "{icon-ec-wool-blue}", "{icon-ec-wool-blue-died}",
        {"color": "blue"}
    ),
    "YELLOW": TeamType(
        "YELLOW", "黄队", "§e", 4, (250, 250, 20),
        "{icon-ec-wool-yellow}", "{icon-ec-wool-yellow-died}",
        {"color": "yellow"}
    ),
    "GREEN": TeamType(
        "GREEN", "绿队", "§a", 5, (20, 220, 20),
        "{icon-ec-wool-green}", "{icon-ec-wool-green-died}",
        {"color": "lime"}
    ),
    "WHITE": TeamType(
        "WHITE", "白队", "§f", 0, (235, 235, 235),
        "{icon-ec-wool-white}", "{icon-ec-wool-white-died}",
        {"color": "white"}
    ),
    "AQUA": TeamType(
        "AQUA", "青队", "§b", 3, (76, 224, 222),
        "{icon-ec-wool-aqua}", "{icon-ec-wool-aqua-died}",
        {"color": "light_blue"}
    ),
    "LIGHT_PURPLE": TeamType(
        "LIGHT_PURPLE", "粉队", "§d", 2, (255, 60, 255),
        "{icon-ec-wool-light-purple}", "{icon-ec-wool-light-purple-died}",
        {"color": "magenta"}
    ),
    "GRAY": TeamType(
        "GRAY", "灰队", "§7", 8, (138, 138, 138),
        "{icon-ec-wool-gray}", "{icon-ec-wool-gray-died}",
        {"color": "silver"}
    ),
}


def get_team_type(team_id):
    """
    通过队伍ID获取队伍类型对象

    :param team_id: 队伍ID
    :return: TeamType对象，如果不存在返回None
    """
    return team_types.get(team_id, None)


def get_all_team_ids():
    """
    获取所有队伍ID列表

    :return: 队伍ID列表
    """
    return list(team_types.keys())


def get_team_color_name(team_id):
    """
    获取队伍的带颜色格式化名称

    :param team_id: 队伍ID
    :return: 格式化的队伍名称，如果不存在返回默认格式
    """
    team_type = get_team_type(team_id)
    if team_type:
        return team_type.get_formatted_name()
    else:
        return "§7{}队".format(team_id)
