# -*- coding: utf-8 -*-
"""
GamingState - 游戏状态机核心类

功能:
- 提供层级状态机实现
- 支持状态enter/exit/tick生命周期
- 支持事件监听和回调
- 支持子状态管理

重构说明:
- 从原Parts/GamingState/state/GamingState.py复制
- 将get_system()改为get_system()以适配System架构
- 核心逻辑保持不变
"""

import traceback
from collections import OrderedDict


class EventListenContext:
    """
    用于存储需要监听的事件的上下文
    在enter时监听，在exit时取消监听
    """
    def __init__(self, namespace, system_name, event_name, instance, func):
        self.namespace = namespace
        self.system_name = system_name
        self.event_name = event_name
        self.instance = instance
        self.func = func


class EventCallback:
    def __init__(self, state, callback):
        self.state = state
        self.callback = callback

    def call(self, args):
        # 触发时，先判断状态是否还在运行
        if self.state.is_state_running():
            self.callback(args)


class GamingState:

    def __init__(self, parent):
        self.parent = parent  # type: GamingState | None
        self.current_sub_state_name = None  # type: str | None
        self.current_sub_state = None  # type: GamingState | None
        self.loop = False  # type: bool

        self.listened_events = list()  # type: list[EventListenContext]
        self.listened_self_events = list()  # type: list[EventListenContext]

        # 子状态机的工厂，是一个有序dict
        self.sub_states = OrderedDict()  # type: dict[str, callable] # (id) -> state_supplier
        # 状态初始化时的回调
        self.callbacks_init = list()  # type: list[callable]
        # 状态开始时的回调
        self.callbacks_enter = list()  # type: list[callable]
        # 状态结束时的回调
        self.callbacks_exit = list()  # type: list[callable]
        # tick回调
        self.callbacks_tick = list()  # type: list[callable]
        # 当没有下一个子状态时回调
        self.callbacks_no_such_next_sub_state = list()  # type: list[callable]

    # ====== 生命周期方法（不要轻易override） ======

    def init(self):
        """
        @description 创建状态
        """
        for callback in self.callbacks_init:
            try:
                callback()
            except Exception as e:
                self.get_system().LogError("GamingState.init callback error: " + str(e))
                traceback.print_exc()

    def enter(self):
        """
        @description 进入状态（不推荐override，而是调用with_enter）
        """
        # 监听器
        for listener in self.listened_events:
            self.get_system().ListenForEvent(
                listener.namespace, listener.system_name, listener.event_name, listener.instance, listener.func
            )
        for listener in self.listened_self_events:
            self.get_system().ListenSelfEvent(
                listener.event_name, listener.instance, listener.func
            )
        # 回调
        for callback in self.callbacks_enter:
            try:
                callback()
            except Exception as e:
                self.get_system().LogError("GamingState.enter callback error: " + str(e))
                traceback.print_exc()
        # 如果该状态机包含子状态，那么自动进入子状态
        if len(self.sub_states) > 0:
            self.next_sub_state()

    def exit(self):
        """
        @description 退出状态（不推荐override，而是调用with_exit）
        """
        # 监听器
        for listener in self.listened_events:
            self.get_system().UnListenForEvent(
                listener.namespace, listener.system_name, listener.event_name, listener.instance, listener.func
            )
        for listener in self.listened_self_events:
            self.get_system().UnListenSelfEvent(
                listener.event_name, listener.instance, listener.func
            )
        # 回调
        for callback in self.callbacks_exit:
            try:
                callback()
            except Exception as e:
                self.get_system().LogError("GamingState.exit callback error: " + str(e))
                traceback.print_exc()

    def tick(self):
        """
        @description 逻辑驱动（不推荐override，而是调用with_tick）
        """
        if self.current_sub_state_name is not None and self.current_sub_state is not None:
            if self.current_sub_state != self:
                self.current_sub_state.tick()
            else:
                self.get_system().LogError("尝试tick递归的sub_state: {}".format(self.current_sub_state_name))
        for callback in self.callbacks_tick:
            try:
                callback()
            except Exception as e:
                self.get_system().LogError("GamingState.tick callback error: " + str(e))
                traceback.print_exc()

    # ====== API 方法 ======

    def get_system(self):
        """
        @description 获取System实例
        :return: GamingStateSystem
        :rtype: GamingStateSystem | None
        """
        if self.parent is not None:
            return self.parent.get_system()
        else:
            return None

    def listen_engine_event(self, event_name, callback):
        """
        @description 监听引擎事件
        :param event_name: 事件名称
        :type event_name: str
        :param callback: 回调函数(self, args...)
        :type callback: callable
        """
        self.listen_event("Minecraft", "Engine", event_name, callback)

    def listen_preset_event(self, event_name, callback):
        """
        @description 监听预设事件
        :param event_name: 事件名称
        :type event_name: str
        :param callback: 回调函数(self, args...)
        :type callback: callable
        """
        self.listen_event("Minecraft", "preset", event_name, callback)

    def listen_event(self, namespace, system_name, event_name, callback):
        """
        @description 监听引擎事件
        :param namespace: 命名空间
        :type namespace: str
        :param system_name: 系统名称
        :type system_name: str
        :param event_name: 事件名称
        :type event_name: str
        :param callback: 回调函数(self, args...)
        :type callback: callable
        """
        event_callback = EventCallback(self, callback)
        self.listened_events.append(EventListenContext(namespace, system_name, event_name, event_callback, event_callback.call))
        if self.is_state_running():
            self.get_system().ListenForEvent(
                namespace, system_name, event_name, event_callback,
                event_callback.call
            )
        # 会在enter时监听，exit时取消监听

    def listen_self_event(self, event_name, callback):
        """
        @description 监听自定义事件
        :param event_name: 事件名称
        :type event_name: str
        :param callback: 回调函数(self, args...)
        :type callback: callable
        """
        event_callback = EventCallback(self, callback)
        self.listened_self_events.append(EventListenContext(None, None, event_name, event_callback, event_callback.call))
        if self.is_state_running():
            self.get_system().ListenSelfEvent(
                event_name,
                event_callback,
                event_callback.call
            )
        # 会在enter时监听，exit时取消监听

    def notify_event(self, event_name, event_data=None):
        """
        广播状态事件(兼容老API)

        新项目使用broadcast_preset_event,此方法提供向后兼容

        Args:
            event_name: str 事件名称
            event_data: dict 事件数据
        """
        system = self.get_system()
        if not system:
            print("[WARN] [GamingState] notify_event失败: system未初始化")
            return

        # 使用新的事件广播机制
        if hasattr(system, 'broadcast_preset_event'):
            system.broadcast_preset_event(event_name, event_data or {})
        else:
            print("[WARN] [GamingState] broadcast_preset_event方法不存在")

    def add_sub_state(self, name, state_supplier, *args, **kwargs):
        """
        @description 添加子状态
        :param name: 子状态名称
        :type name: str
        :param state_supplier: 一个返回子状态对象的lambda函数，可以接受任意数量的位置参数和关键字参数
        :type state_supplier: callable
        :param args: 传递给state_supplier的位置参数
        :param kwargs: 传递给state_supplier的关键字参数
        """
        if name in self.sub_states:
            raise ValueError("添加子状态时，状态名 {} 已存在".format(name))
        self.sub_states[name] = lambda parent: state_supplier(parent, *args, **kwargs)

    def remove_sub_state(self, state_name):
        """
        @description 移除子状态
        :param state_name: 子状态名称
        :type state_name: str
        :return: 被移除的子状态
        :rtype: GamingState | None
        """
        # 如果移除了一个正在进行中的状态，则自动切换到下一状态
        if self.current_sub_state_name == state_name:
            self.next_sub_state()
        return self.sub_states.pop(state_name)

    def is_state_running(self):
        """
        @description 检查父状态的当前子状态是否是自己（也就是说，当前状态是正在运行生效）
        """
        if self.parent is None:
            return True
        elif self.parent.current_sub_state_name is None:
            return False
        return self.parent.current_sub_state == self

    def get_runtime_state_name(self):
        """
        @description 获取自己正在运行的状态名称
        :return: 状态名称 | 如果没有运行则返回None
        :rtype: str | None
        """
        if self.parent is not None and self.is_state_running():
            return self.parent.current_sub_state_name
        return None

    def next_sub_state(self):
        """
        @description 进入下一个子状态

        [DEBUG 2025-11-07] 添加详细日志追踪状态转换
        """
        keys = list(self.sub_states.keys())

        if self.current_sub_state_name is None:
            if len(keys) > 0:
                next_state_name = keys[0]
                self.get_system().LogDebug("next_sub_state: None -> " + next_state_name)
                self.get_system().LogInfo("[DEBUG] next_sub_state: 从None进入第一个状态 {}".format(next_state_name))
                self.toggle_sub_state(next_state_name)
            else:
                self.get_system().LogInfo("[DEBUG] next_sub_state: 无子状态，通知父状态")
                self.parent.next_sub_state()
                for callback in self.callbacks_no_such_next_sub_state:
                    callback()
        else:
            if self.current_sub_state is None:
                raise ValueError("Current states {} is missing".format(self.current_sub_state_name))
            index = keys.index(self.current_sub_state_name)
            if index + 1 < len(keys):
                previous_state_name = self.current_sub_state_name
                next_state_name = keys[index + 1]
                self.get_system().LogDebug("next_sub_state: {} -> {}".format(previous_state_name, next_state_name))
                self.get_system().LogInfo("[DEBUG] next_sub_state: {} -> {}".format(previous_state_name, next_state_name))
                self.toggle_sub_state(next_state_name)
            else:
                self.get_system().LogInfo("[DEBUG] next_sub_state: 已到达最后一个子状态 {}，loop={}".format(
                    self.current_sub_state_name, self.loop
                ))
                if self.loop:
                    self.get_system().LogInfo("[DEBUG] next_sub_state: 循环模式，重新进入第一个状态")
                    self.current_sub_state.exit()
                    self.current_sub_state_name = None
                    self.current_sub_state = None
                    self.next_sub_state()
                else:
                    self.get_system().LogInfo("[DEBUG] next_sub_state: 非循环模式，触发no_such_next_sub_state回调")
                    for callback in self.callbacks_no_such_next_sub_state:
                        callback()
                    if self.is_state_running() and self.current_sub_state_name == keys[-1]:  # 这边需要判断进行了callback后，目前状态机是否被改变，如果被改变，表示在callback中修改了状态
                        self.get_system().LogInfo("[DEBUG] next_sub_state: 状态未改变，退出当前状态并通知父状态")
                        self.current_sub_state.exit()
                        self.current_sub_state_name = None
                        self.current_sub_state = None
                        if self.parent is not None:
                            self.parent.next_sub_state()

    def toggle_sub_state(self, state_name):
        """
        @description 切换子状态
        :param state_name: 子状态名称
        :type state_name: str
        """
        if state_name not in self.sub_states:
            raise ValueError("State {} not found".format(state_name))
        if self.current_sub_state is not None:
            self.current_sub_state.exit()
        self.current_sub_state_name = state_name
        state_factory = self.sub_states[state_name]
        self.current_sub_state = state_factory(self)
        self.current_sub_state.init()
        self.current_sub_state.enter()

    def set_loop(self, loop=True):
        """
        @description 设置是否循环
        :param loop: 是否循环
        :type loop: bool
        """
        self.loop = loop

    # ====== withCallback 附加回调逻辑 ======

    def with_init(self, callback):
        """
        @description 添加状态初始化时的回调
        :param callback: 回调函数，例如：lambda: print("init")
        :type callback: callable
        """
        self.callbacks_init.append(callback)

    def with_enter(self, callback):
        """
        @description 添加状态开始时的回调
        @param callback: 回调函数，例如：lambda: print("enter")
        :type callback: callable
        """
        self.callbacks_enter.append(callback)

    def with_exit(self, callback):
        """
        @description 添加状态结束时的回调
        :param callback: 回调函数，例如：lambda: print("exit")
        :type callback: callable
        """
        self.callbacks_exit.append(callback)

    def with_tick(self, callback):
        """
        @description 添加tick回调
        :param callback: 回调函数，例如：lambda: print("tick")
        :type callback: callable
        """
        self.callbacks_tick.append(callback)

    def with_no_such_next_sub_state(self, callback):
        """
        @description 添加没有下一个子状态时的回调
        :param callback: 回调函数，例如：lambda: print("no next sub states")
        :type callback: callable
        """
        self.callbacks_no_such_next_sub_state.append(callback)
