# -*- coding: utf-8 -*-
"""
性能优化工具集

提供常用的性能优化工具：
- 事件节流（throttle）
- 事件防抖（debounce）
- 事件批处理（EventBatcher）
- 对象池（ObjectPool）
"""

import time
from functools import wraps


# ===== 事件节流装饰器 =====

def throttle(interval_sec):
    """
    事件节流装饰器

    确保函数在指定时间间隔内最多执行一次

    Args:
        interval_sec (float): 最小调用间隔（秒）

    Usage:
        @throttle(0.1)  # 最多每0.1秒调用一次
        def on_high_frequency_event(self, args):
            pass

    原理:
        记录上次调用时间，如果距离上次调用时间 < interval_sec，则跳过本次调用
    """
    def decorator(func):
        last_call = {}  # {instance_id: last_call_time}

        @wraps(func)
        def wrapper(self, *args, **kwargs):
            now = time.time()
            instance_id = id(self)

            if instance_id not in last_call:
                last_call[instance_id] = 0

            # 检查是否在冷却期
            if now - last_call[instance_id] < interval_sec:
                return None  # 跳过调用

            # 更新时间并执行
            last_call[instance_id] = now
            return func(self, *args, **kwargs)

        return wrapper
    return decorator


# ===== 事件防抖装饰器 =====

def debounce(delay_sec):
    """
    事件防抖装饰器

    确保函数只在最后一次调用后延迟执行

    Args:
        delay_sec (float): 延迟时间（秒）

    Usage:
        @debounce(0.5)  # 停止调用0.5秒后执行
        def on_search_input(self, args):
            pass

    原理:
        每次调用时取消之前的定时器，创建新定时器延迟执行
    """
    def decorator(func):
        timer_ids = {}  # {instance_id: timer_id}

        @wraps(func)
        def wrapper(self, *args, **kwargs):
            instance_id = id(self)

            # 取消旧定时器
            if instance_id in timer_ids:
                try:
                    import mod.server.extraServerApi as serverApi
                    comp = serverApi.GetEngineCompFactory().CreateGame(
                        serverApi.GetLevelId()
                    )
                    comp.CancelTimer(timer_ids[instance_id])
                except:
                    pass

            # 创建新定时器
            def delayed_call():
                timer_ids.pop(instance_id, None)
                func(self, *args, **kwargs)

            import mod.server.extraServerApi as serverApi
            comp = serverApi.GetEngineCompFactory().CreateGame(
                serverApi.GetLevelId()
            )
            timer_ids[instance_id] = comp.AddTimer(delay_sec, delayed_call)

        return wrapper
    return decorator


# ===== 事件批处理器 =====

class EventBatcher:
    """
    事件批量处理器

    将多个事件收集后批量发送，减少网络调用

    Usage:
        batcher = EventBatcher(system, interval=0.1, max_batch=50)

        # 添加事件到队列
        for player_id in players:
            batcher.add_event('UpdateUI', player_id, data)

        # 自动批量发送（达到max_batch或超过interval时）
        # 或手动强制发送
        batcher.flush()
    """

    def __init__(self, system, interval=0.1, max_batch=50):
        """
        Args:
            system: 系统实例（用于发送事件）
            interval (float): 批量发送间隔（秒）
            max_batch (int): 最大批量大小
        """
        self.system = system
        self.interval = interval
        self.max_batch = max_batch
        self.event_queue = []  # [(event_name, player_id, data), ...]
        self.last_flush = time.time()

    def add_event(self, event_name, player_id, data):
        """
        添加事件到队列

        Args:
            event_name (str): 事件名称
            player_id (str): 玩家ID
            data (dict): 事件数据
        """
        self.event_queue.append((event_name, player_id, data))

        # 检查是否需要自动刷新
        if len(self.event_queue) >= self.max_batch:
            self.flush()
        elif time.time() - self.last_flush >= self.interval:
            self.flush()

    def flush(self):
        """批量发送所有事件"""
        if not self.event_queue:
            return

        # 按事件类型分组
        grouped = {}
        for event_name, player_id, data in self.event_queue:
            if event_name not in grouped:
                grouped[event_name] = {}
            grouped[event_name][player_id] = data

        # 批量发送
        for event_name, player_data in grouped.items():
            try:
                self.system.BroadcastToAllClient(event_name + 'Batch', {
                    'updates': player_data
                })
            except Exception as e:
                print("[EventBatcher] 批量发送事件失败: {} - {}".format(
                    event_name, str(e)
                ))

        # 清空队列
        self.event_queue = []
        self.last_flush = time.time()


# ===== 对象池 =====

class ObjectPool:
    """
    对象池

    复用对象，减少创建/销毁开销

    Usage:
        class Particle:
            def __init__(self):
                self.active = False
                self.position = (0, 0, 0)

            def reset(self):
                self.active = False
                self.position = (0, 0, 0)

        # 创建对象池
        pool = ObjectPool(Particle, initial_size=100, max_size=500)

        # 获取对象
        particle = pool.acquire()
        if particle:
            particle.active = True
            particle.position = (10, 20, 30)

        # 释放对象
        pool.release(particle)
    """

    def __init__(self, object_class, initial_size=10, max_size=100):
        """
        Args:
            object_class: 对象类
            initial_size (int): 初始对象数量
            max_size (int): 最大对象数量
        """
        self.object_class = object_class
        self.max_size = max_size
        self.available = []  # 可用对象列表
        self.in_use = set()  # 正在使用的对象集合

        # 预创建对象
        for _ in range(initial_size):
            obj = object_class()
            self.available.append(obj)

    def acquire(self):
        """
        获取对象

        Returns:
            object: 对象实例，如果池已满返回None
        """
        # 如果有可用对象，直接返回
        if self.available:
            obj = self.available.pop()
            self.in_use.add(id(obj))
            return obj

        # 如果未达到最大限制，创建新对象
        if len(self.in_use) < self.max_size:
            obj = self.object_class()
            self.in_use.add(id(obj))
            return obj

        # 池已满
        return None

    def release(self, obj):
        """
        释放对象

        Args:
            obj: 要释放的对象
        """
        obj_id = id(obj)
        if obj_id not in self.in_use:
            return

        # 重置对象（如果有reset方法）
        if hasattr(obj, 'reset'):
            obj.reset()

        # 移回可用列表
        self.in_use.remove(obj_id)
        self.available.append(obj)

    def get_stats(self):
        """
        获取统计信息

        Returns:
            dict: 统计数据
        """
        return {
            "available": len(self.available),
            "in_use": len(self.in_use),
            "total": len(self.available) + len(self.in_use),
            "max_size": self.max_size,
            "utilization": len(self.in_use) / self.max_size if self.max_size > 0 else 0
        }


# ===== 缓存装饰器 =====

def cache_result(ttl_seconds=60):
    """
    结果缓存装饰器

    缓存函数返回值，在TTL内直接返回缓存结果

    Args:
        ttl_seconds (float): 缓存有效时间（秒）

    Usage:
        @cache_result(ttl_seconds=5)
        def get_team_players(self, team_id):
            # 复杂查询
            return players
    """
    def decorator(func):
        cache = {}  # {(instance_id, args_key): (result, expire_time)}

        @wraps(func)
        def wrapper(self, *args, **kwargs):
            now = time.time()
            instance_id = id(self)

            # 构建缓存键
            args_key = str(args) + str(sorted(kwargs.items()))
            cache_key = (instance_id, args_key)

            # 检查缓存
            if cache_key in cache:
                result, expire_time = cache[cache_key]
                if now < expire_time:
                    return result

            # 缓存未命中，执行函数
            result = func(self, *args, **kwargs)

            # 存入缓存
            cache[cache_key] = (result, now + ttl_seconds)

            return result

        return wrapper
    return decorator


# ===== 性能计时器上下文管理器 =====

class PerformanceTimer:
    """
    性能计时器上下文管理器

    Usage:
        with PerformanceTimer("my_operation"):
            # 耗时操作
            do_something()

        # 输出: [PerformanceTimer] my_operation: 0.123s
    """

    def __init__(self, name):
        """
        Args:
            name (str): 操作名称
        """
        self.name = name
        self.start_time = 0

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        print("[PerformanceTimer] {}: {:.3f}s".format(self.name, duration))


# ===== 批量操作优化函数 =====

def batch_process(items, batch_size=50, process_func=None):
    """
    批量处理数据

    将大量数据分批处理，避免单次处理时间过长

    Args:
        items (list): 要处理的数据列表
        batch_size (int): 每批处理数量
        process_func (callable): 处理函数，接收批次列表作为参数

    Usage:
        def process_batch(batch):
            for item in batch:
                # 处理单个项
                pass

        batch_process(large_list, batch_size=50, process_func=process_batch)
    """
    if not process_func:
        return

    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        process_func(batch)
