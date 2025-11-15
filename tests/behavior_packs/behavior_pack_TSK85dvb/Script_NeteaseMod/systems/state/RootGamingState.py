# -*- coding: utf-8 -*-
"""
RootGamingState - 根游戏状态

功能:
- 作为状态机的根节点
- 持有GamingStateSystem引用
- 提供get_system()接口

重构说明:
- 从原Parts/GamingState/state/RootGamingState.py复制
- 将part改为system
- 将get_part()改为get_system()
"""

from .GamingState import GamingState
if False:
    from ..GamingStateSystem import GamingStateSystem


class RootGamingState(GamingState):
    """根游戏状态"""

    def __init__(self, system):
        """
        初始化根状态

        Args:
            system: GamingStateSystem实例
        """
        GamingState.__init__(self, None)
        self.system = system  # type: GamingStateSystem
        self.init()
        self.with_enter(self._on_enter)
        self.with_no_such_next_sub_state(self._on_no_such_next_sub_state)

    def get_system(self):
        """
        获取System实例

        Returns:
            GamingStateSystem: System实例
        """
        return self.system

    def start(self):
        """启动状态机"""
        self.enter()

    def stop(self):
        """停止状态机"""
        if self.current_sub_state:
            self.current_sub_state.exit()
        self.exit()

    def _on_enter(self):
        """进入根状态时的回调

        注意: 不需要手动调用next_sub_state()!
        GamingState.enter()会在执行完所有回调后自动调用next_sub_state()进入第一个子状态。
        如果在这里手动调用，会导致进入两次子状态（waiting -> running）!
        """
        self.system.LogInfo("RootGamingState entered.")

    def _on_no_such_next_sub_state(self):
        """没有下一个子状态时的回调

        [DEBUG 2025-11-07] 添加详细日志，帮助追踪状态机是否正确循环
        """
        self.system.LogInfo("RootGamingState is over.")
        self.system.LogInfo("[DEBUG] RootGamingState._on_no_such_next_sub_state 被调用")
        self.system.LogInfo("[DEBUG] - current_sub_state_name: {}".format(self.current_sub_state_name))
        self.system.LogInfo("[DEBUG] - loop: {}".format(self.loop))
        self.system.LogInfo("[DEBUG] - sub_states: {}".format(list(self.sub_states.keys())))