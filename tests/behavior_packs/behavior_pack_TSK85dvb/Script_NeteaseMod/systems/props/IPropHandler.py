# -*- coding: utf-8 -*-
"""
IPropHandler - 道具处理器接口

功能:
- 定义道具处理器的标准接口
- 生命周期管理(on_create/on_destroy/on_update)
- 道具触发(on_trigger)
"""


class IPropHandler(object):
    """
    道具处理器接口

    所有道具处理器必须继承此类并实现相应方法
    """

    # 是否需要每帧更新
    enable_tick = False

    def __init__(self):
        """初始化道具处理器"""
        self.system = None  # PropsManagementSystem实例

    def on_create(self, system):
        """
        道具处理器创建时调用

        Args:
            system: PropsManagementSystem实例
        """
        self.system = system
        system.LogDebug("{}已创建".format(self.__class__.__name__))

    def on_destroy(self):
        """道具处理器销毁时调用"""
        if self.system:
            self.system.LogDebug("{}已销毁".format(self.__class__.__name__))
        self.system = None

    def on_update(self):
        """
        每帧更新(仅当enable_tick=True时调用)

        子类可以重写此方法实现每帧逻辑
        """
        pass

    def on_trigger(self, player_id, **kwargs):
        """
        道具触发时调用

        Args:
            player_id (str): 玩家ID
            **kwargs: 道具参数

        子类必须重写此方法
        """
        raise NotImplementedError("子类必须实现on_trigger方法")

    # ========== 辅助方法 ==========

    def get_game_system(self):
        """
        获取BedWarsGameSystem引用

        Returns:
            BedWarsGameSystem: 游戏系统实例
        """
        if self.system:
            return self.system.get_bedwars_game_system()
        return None

    def get_team_module(self):
        """
        获取TeamModule引用

        Returns:
            TeamModule: 队伍模块实例
        """
        game_system = self.get_game_system()
        if game_system:
            return getattr(game_system, 'team_module', None)
        return None
