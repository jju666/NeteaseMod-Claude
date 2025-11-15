# -*- coding: utf-8 -*-
"""
ChangeDimensionAnimHelper - 维度切换动画触发工具

功能说明：
    提供简洁的API，用于在维度切换时触发动画效果。
    服务端系统可以通过该工具通知客户端播放过渡动画。

重构说明：
    老项目: 通过预设系统事件BroadcastPresetSystemEvent触发
    新项目: 通过System的BroadcastToAllClient/NotifyToClient触发

使用示例：
    # 在System中初始化
    self.change_dim_anim = ChangeDimensionAnimHelper(self)

    # 触发动画（所有玩家）
    self.change_dim_anim.trigger_animation()

    # 触发动画（指定玩家）
    self.change_dim_anim.trigger_animation(players=['player1', 'player2'])

    # 延迟执行维度切换
    self.change_dim_anim.trigger_animation()
    self.add_timer(0.6, lambda: self._do_dimension_switch(), False)
"""

import mod.server.extraServerApi as serverApi


class ChangeDimensionAnimHelper(object):
    """维度切换动画触发工具"""

    def __init__(self, system):
        """
        初始化工具

        Args:
            system: 游戏系统实例（用于发送事件）
        """
        self.system = system

    def trigger_animation(self, players=None):
        """
        触发维度切换动画

        Args:
            players (list, optional): 指定玩家ID列表。如果为None，则广播给所有玩家。

        说明:
            该方法应在执行维度切换前0.5-0.8秒调用，给客户端留出足够的时间播放淡入动画。

        流程:
            1. 客户端收到事件
            2. 关闭非HUD界面
            3. 播放淡入动画（0.5秒）
            4. 服务端执行维度切换
            5. 客户端播放淡出动画（1秒）

        推荐延迟时间:
            - 本地测试: 0.6秒
            - 局域网: 0.8秒
            - 公网服务器: 1.0秒

        示例:
            # 游戏开始，所有玩家切换维度
            self.change_dim_anim.trigger_animation()
            self.add_timer(0.8, lambda: self._switch_all_players_to_game(), False)

            # 游戏结束，指定玩家返回大厅
            player_ids = [p.GetPlayerId() for p in online_players]
            self.change_dim_anim.trigger_animation(players=player_ids)
            self.add_timer(0.8, lambda: self._teleport_players_to_lobby(player_ids), False)
        """
        event_data = {}

        if players is not None:
            # 模式1：向指定玩家发送
            for player_id in players:
                self.system.NotifyToClient(player_id, "StartChangeDimension", event_data)
            print("[INFO] [ChangeDimensionAnimHelper] 已触发维度切换动画（指定玩家: {}）".format(len(players)))
        else:
            # 模式2：向所有玩家广播
            self.system.BroadcastToAllClient("StartChangeDimension", event_data)
            print("[INFO] [ChangeDimensionAnimHelper] 已触发维度切换动画（所有玩家）")

    def trigger_and_switch(self, dimension, positions_dict, players=None, delay=0.8):
        """
        触发动画并自动延迟执行维度切换（便捷方法）

        Args:
            dimension (int): 目标维度ID
            positions_dict (dict): 玩家ID -> 目标位置 的映射 {player_id: (x, y, z)}
            players (list, optional): 指定玩家ID列表。如果为None，则使用positions_dict的所有玩家。
            delay (float): 延迟时间（秒），默认0.8秒

        示例:
            # 所有玩家传送到游戏地图
            positions = {
                'player1': (100, 65, 100),
                'player2': (110, 65, 110),
            }
            self.change_dim_anim.trigger_and_switch(
                dimension=10000,
                positions_dict=positions,
                delay=0.8
            )
        """
        if players is None:
            players = list(positions_dict.keys())

        # 触发动画
        self.trigger_animation(players=players)

        # 延迟执行切换
        def do_switch():
            self._switch_players_dimension(dimension, positions_dict)

        # 使用System的定时器
        if hasattr(self.system, 'add_timer'):
            self.system.add_timer(delay, do_switch, False)
        else:
            # 兼容没有add_timer方法的系统
            comp_game = serverApi.GetEngineCompFactory().CreateGame(serverApi.GetLevelId())
            comp_game.AddTimer(delay, do_switch, False)

    def _switch_players_dimension(self, dimension, positions_dict):
        """
        执行玩家维度切换

        Args:
            dimension (int): 目标维度ID
            positions_dict (dict): 玩家ID -> 目标位置 的映射
        """
        comp_factory = serverApi.GetEngineCompFactory()

        for player_id, pos in positions_dict.items():
            try:
                # 设置位置
                comp_pos = comp_factory.CreatePos(player_id)
                comp_pos.SetFootPos(pos)

                # 切换维度
                comp_dim = comp_factory.CreateDimension(player_id)
                comp_dim.ChangePlayerDimension(dimension)

                print("[INFO] [ChangeDimensionAnimHelper] 玩家 {} 已切换到维度 {}".format(player_id, dimension))

            except Exception as e:
                print("[ERROR] [ChangeDimensionAnimHelper] 切换玩家 {} 维度失败: {}".format(player_id, e))


# ===== 全局工具函数 =====

def trigger_dimension_animation(system, players=None):
    """
    全局工具函数：触发维度切换动画

    Args:
        system: 游戏系统实例
        players (list, optional): 指定玩家列表

    示例:
        from systems.util.ChangeDimensionAnimHelper import trigger_dimension_animation

        trigger_dimension_animation(self)  # 广播所有玩家
        trigger_dimension_animation(self, players=['p1', 'p2'])  # 指定玩家
    """
    helper = ChangeDimensionAnimHelper(system)
    helper.trigger_animation(players=players)
