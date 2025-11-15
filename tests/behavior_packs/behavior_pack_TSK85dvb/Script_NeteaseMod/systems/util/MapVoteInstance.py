# -*- coding: utf-8 -*-
"""
MapVoteInstance - 地图投票实例

功能:
- 管理地图投票数据
- 处理玩家投票
- 选出得票最高的地图
- 提供UI数据

原文件: Parts/ECStage/MapVoteInstance.py
重构为: systems/util/MapVoteInstance.py
"""

import random
from collections import OrderedDict

MODE_ICONS = {
    "team4": "textures/ui/bw/bw_category_sword",
    "team2": "textures/ui/bw/bw_category_armor",
    "team8": "textures/ui/bw/bw_category_tool",
}

MODE_NAMES = {
    "team4": u"4队2人",
    "team2": u"2队5人",
    "team8": u"8人单挑"
}


class MapVoteEntry(object):
    """
    地图投票条目

    记录单张地图的投票信息
    """

    def __init__(self, map_id, map_name, map_mode, map_image):
        """
        初始化地图投票条目

        Args:
            map_id (str): 地图ID
            map_name (str): 地图名称
            map_mode (str): 队伍模式 (team2/team4/team8)
            map_image (str): 地图图片路径
        """
        self.map_id = map_id
        self.map_name = map_name
        self.map_mode = map_mode
        self.map_image = map_image
        self.voters = []  # 投票玩家ID列表

    def to_ui_dict(self):
        """
        转换为UI数据格式

        Returns:
            dict: UI数据字典
        """
        return {
            "id": self.map_id,
            "name": self.map_name,
            "mode": self.map_mode,
            "mode_name": MODE_NAMES.get(self.map_mode, self.map_mode),
            "image": self.map_image,
            "voters": self.voters
        }


class MapVoteInstance(object):
    """
    地图投票实例

    核心功能:
    1. 初始化可投票地图列表
    2. 处理玩家投票
    3. 统计投票结果
    4. 选出得票最高的地图
    5. 提供UI数据
    """

    def __init__(self, room_system):
        """
        初始化地图投票实例

        Args:
            room_system: RoomManagementSystem实例
        """
        self.room_system = room_system
        self.maps = OrderedDict()  # map_id -> MapVoteEntry

        # 只初始化可用的地图(排除正在还原中的地图)
        available_stages = self.room_system.get_available_maps_for_vote()
        for stage in available_stages:
            map_id = stage['id']
            map_name = stage.get('name', u'未知地图')
            map_mode = stage.get('mode', 'team2')
            map_image = stage.get('image', '')
            self.maps[map_id] = MapVoteEntry(map_id, map_name, map_mode, map_image)

    def vote(self, player_id, map_id):
        """
        处理玩家投票

        Args:
            player_id (str): 玩家ID
            map_id (str): 地图ID
        """
        if map_id not in self.maps:
            return

        # 移除该玩家在其他地图的投票
        for entry in self.maps.values():
            if player_id in entry.voters:
                entry.voters.remove(player_id)

        # 添加投票到目标地图
        entry = self.maps[map_id]
        entry.voters.append(player_id)

    def group_and_sort_maps_by_votes(self):
        """
        按投票数分组并排序地图

        Returns:
            list: 按投票数从高到低排序的地图ID列表
        """
        # 创建一个字典,键是投票数,值是具有该投票数的地图列表
        vote_map_dict = {}
        for entry in self.maps.values():
            vote_count = len(entry.voters)
            if vote_count not in vote_map_dict:
                vote_map_dict[vote_count] = []
            vote_map_dict[vote_count].append(entry.map_id)

        # 使用sorted对字典的键进行排序
        sorted_vote_counts = sorted(vote_map_dict.keys(), reverse=True)

        # 创建一个新的列表,地图按投票数排序
        sorted_maps = []
        for vote_count in sorted_vote_counts:
            sorted_maps.extend(vote_map_dict[vote_count])

        return sorted_maps

    def find_most_voted(self):
        """
        选出得票最高的地图

        规则:
        1. 如果无人投票,随机选择任意可用地图
        2. 如果只有一张地图得票最高,直接返回
        3. 如果多张地图得票相同,优先选择2队模式
        4. 如果没有2队模式,从得票最高的地图中随机选择

        Returns:
            str: 选中的地图ID
        """
        sorted_maps = self.group_and_sort_maps_by_votes()
        if not sorted_maps:
            return None

        # 获取最高票数
        max_votes = len(self.maps[sorted_maps[0]].voters)

        # 如果最高票数是0,说明没有人投票,直接随机选择
        if max_votes == 0:
            selected_map = random.choice(list(self.maps.keys()))
            print("[INFO] [MapVote] 无人投票,随机选择地图: {} ({}) 模式: {}".format(
                self.maps[selected_map].map_name,
                selected_map,
                self.maps[selected_map].map_mode
            ))
            return selected_map

        # 获取所有获得最高票数的地图
        most_voted_maps = [map_id for map_id in sorted_maps
                          if len(self.maps[map_id].voters) == max_votes]

        # 如果只有一张地图获得最高票数,直接返回
        if len(most_voted_maps) == 1:
            selected_map = most_voted_maps[0]
            print("[INFO] [MapVote] 选择最高票数地图: {} ({}) 票数: {}".format(
                self.maps[selected_map].map_name,
                selected_map,
                max_votes
            ))
            return selected_map

        # 如果有多张地图获得相同票数,优先选择2队模式
        team2_most_voted = [map_id for map_id in most_voted_maps
                           if self.maps[map_id].map_mode == "team2"]

        if team2_most_voted:
            selected_map = random.choice(team2_most_voted)
            print("[INFO] [MapVote] 平票时选择2队模式地图: {} ({}) 票数: {}".format(
                self.maps[selected_map].map_name,
                selected_map,
                max_votes
            ))
            return selected_map
        else:
            # 否则从所有获得最高票数的地图中随机选择
            selected_map = random.choice(most_voted_maps)
            print("[INFO] [MapVote] 平票时随机选择地图: {} ({}) 票数: {}".format(
                self.maps[selected_map].map_name,
                selected_map,
                max_votes
            ))
            return selected_map

    def refresh_available_maps(self):
        """
        刷新可用地图列表,保持现有投票数据

        用于地图还原完成后更新投票列表
        """
        # 获取当前可用地图
        available_stages = self.room_system.get_available_maps_for_vote()
        available_map_ids = set([stage['id'] for stage in available_stages])

        # 移除不再可用的地图
        for map_id in list(self.maps.keys()):
            if map_id not in available_map_ids:
                del self.maps[map_id]

        # 添加新的可用地图
        for stage in available_stages:
            map_id = stage['id']
            if map_id not in self.maps:
                map_name = stage.get('name', u'未知地图')
                map_mode = stage.get('mode', 'team2')
                map_image = stage.get('image', '')
                self.maps[map_id] = MapVoteEntry(map_id, map_name, map_mode, map_image)

    def to_ui_dict(self):
        """
        转换为UI数据格式

        Returns:
            dict: UI数据字典
        """
        data = {
            "categories": []
        }

        # 按队伍模式分组地图
        categories = OrderedDict()
        for map_id, entry in self.maps.items():
            category = entry.map_mode
            if category not in categories:
                categories[category] = []
            categories[category].append(entry.to_ui_dict())

        # 定义队伍模式的显示顺序: 推荐(2队) -> 4队 -> 2队 -> 8队
        # 首先添加推荐栏(2队模式)
        if "team2" in categories:
            data['categories'].append({
                "name": u"推荐",
                "icon": "textures/ui/bw/bw_category_fast",
                "maps": categories["team2"]
            })

        # 然后添加4队模式橱窗
        if "team4" in categories:
            data['categories'].append({
                "id": "team4",
                "name": MODE_NAMES.get("team4", "team4"),
                "icon": MODE_ICONS.get("team4", "textures/ui/bw/bw_category_fast"),
                "maps": categories["team4"]
            })

        # 添加2队模式橱窗
        if "team2" in categories:
            data['categories'].append({
                "id": "team2",
                "name": MODE_NAMES.get("team2", "team2"),
                "icon": MODE_ICONS.get("team2", "textures/ui/bw/bw_category_fast"),
                "maps": categories["team2"]
            })

        # 添加8队模式橱窗
        if "team8" in categories:
            data['categories'].append({
                "id": "team8",
                "name": MODE_NAMES.get("team8", "team8"),
                "icon": MODE_ICONS.get("team8", "textures/ui/bw/bw_category_fast"),
                "maps": categories["team8"]
            })

        return data
