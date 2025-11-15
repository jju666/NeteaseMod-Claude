# -*- coding: utf-8 -*-
"""
TimedGamingState - 定时游戏状态

功能:
- 继承自GamingState,添加定时功能
- 在指定时间后自动切换到下一状态
- 提供超时回调机制

原文件: Parts/GamingState/state/TimedGamingState.py
重构为: systems/state/TimedGamingState.py
"""

import time
from Script_NeteaseMod.systems.state.GamingState import GamingState


class TimedGamingState(GamingState):
    def __init__(self, parent, duration):
        GamingState.__init__(self, parent)
        self.duration = duration
        self.time_end = 0
        self.callbacks_timeout = list()
        # 修复：初始化超时触发标记
        self._timeout_triggered = False
        self.with_enter(self._timed_on_enter)
        self.with_tick(self._timed_on_tick)

    def reset_duration(self, duration):
        """
        @description 设置持续时间
        :param duration: float 持续时间（秒）
        """
        self.duration = duration
        if self.is_state_running():
            self.reset_timer()

    def reset_timer(self):
        """
        @description 重置计时器
        """
        self.get_system().LogDebug("reset_timer {} + {}".format(str(time.time()), str(self.duration)))
        self.time_end = time.time() + self.duration
        # 修复：重置超时触发标记
        self._timeout_triggered = False

    def with_time_out(self, callback):
        """
        @description 设置超时回调
        :param callback: callable 回调函数
        """
        self.callbacks_timeout.append(callback)

    # 内部的状态机回调

    def _timed_on_enter(self):
        self.reset_timer()

    def _timed_on_tick(self):
        # 修复：添加更可靠的超时检测，防止浮点数精度问题
        current_time = time.time()
        if current_time >= self.time_end:
            self.get_system().LogDebug("TimedGamingState超时触发: 当前时间={}, 结束时间={}, 差值={}".format(
                current_time, self.time_end, current_time - self.time_end))
            self._time_out()

    def _time_out(self):
        self.get_system().LogDebug("TimedGamingState._time_out 开始执行")

        # 修复：添加防重复触发机制
        if hasattr(self, '_timeout_triggered') and self._timeout_triggered:
            self.get_system().LogDebug("TimedGamingState._time_out 超时已触发，跳过重复执行")
            return

        # 标记超时已触发
        self._timeout_triggered = True

        # 修复：添加超时回调执行保护
        for i, callback in enumerate(self.callbacks_timeout):
            try:
                callback(self)
            except Exception as e:
                self.get_system().LogError("TimedGamingState超时回调执行失败 [{}]: {}".format(i, str(e)))

        # ===== [CRITICAL FIX] 自动切换到下一个状态 =====
        # 老项目逻辑：定时器超时后，自动调用parent.next_sub_state()切换到下一阶段
        # 这确保了游戏阶段按配置的duration自动推进（游戏开始→钻石II级→绿宝石II级...）
        if self.parent is not None:
            self.get_system().LogDebug("TimedGamingState准备切换到下一个状态")
            try:
                # 添加状态一致性检查
                if self._check_state_consistency_before_switch():
                    self.parent.next_sub_state()
                else:
                    self.get_system().LogWarn("TimedGamingState状态一致性检查失败，取消状态切换")
            except Exception as e:
                self.get_system().LogError("TimedGamingState状态切换失败: {}".format(str(e)))
                import traceback
                self.get_system().LogError(traceback.format_exc())
        else:
            self.get_system().LogDebug("TimedGamingState没有父状态，无法切换")

    def _check_state_consistency_before_switch(self):
        """在状态切换前检查状态一致性"""
        try:
            system = self.get_system()

            # 检查当前状态是否仍然有效
            if not self.is_state_running():
                system.LogDebug("TimedGamingState状态一致性检查：状态已停止运行")
                return False

            # 检查父状态是否存在
            if self.parent is None:
                system.LogDebug("TimedGamingState状态一致性检查：父状态不存在")
                return False

            # 检查是否仍在正确的子状态中
            if hasattr(self.parent, 'current_sub_state') and self.parent.current_sub_state != self:
                system.LogDebug("TimedGamingState状态一致性检查：当前子状态已改变")
                return False

            system.LogDebug("TimedGamingState状态一致性检查通过")
            return True

        except Exception as e:
            system = self.get_system()
            system.LogError("TimedGamingState状态一致性检查失败: {}".format(str(e)))
            return False

    # 额外的接口

    def get_seconds_left(self):
        """
        @description 获取剩余时间
        :return: 剩余时间（秒）
        :rtype: float
        """
        return self.time_end - time.time()

    def get_seconds_passed(self):
        """
        @description 获取已经过去的时间
        :return: 已经过去的时间（秒）
        :rtype: float
        """
        return self.duration - self.get_seconds_left()

    def get_formatted_time_left(self):
        """
        @description 获取格式化的剩余时间
        :return: 格式化的剩余时间
        :rtype: str
        """
        seconds = self.get_seconds_left()
        hours = int(seconds / 3600)
        seconds %= 3600
        minutes = int(seconds / 60)
        seconds = int(seconds % 60)
        if hours > 0:
            return "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)
        else:
            return "{:02d}:{:02d}".format(minutes, seconds)

    def get_formatted_time_left_mill(self):
        """
        @description 获取格式化的剩余时间
        :return: 格式化的剩余时间
        :rtype: str
        """
        seconds = self.get_seconds_left()
        hours = int(seconds / 3600)
        seconds %= 3600
        minutes = int(seconds / 60)
        seconds = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        if hours > 0:
            return "{:02d}:{:02d}:{:02d}.{:03d}".format(hours, minutes, seconds, milliseconds)
        else:
            return "{:02d}:{:02d}.{:03d}".format(minutes, seconds, milliseconds)

    def get_time_end(self):
        """
        @description 获取结束时间
        :return: 结束时间戳（秒）
        :rtype: float
        """
        return self.time_end
