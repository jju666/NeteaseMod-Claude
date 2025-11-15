# -*- coding: utf-8 -*-
"""
性能监控工具

功能:
- 实时TPS监控
- Tick时间统计
- 事件频率分析
- 内存使用跟踪
- 自动生成性能报告
"""

import time
import json
import codecs


class PerformanceMonitor:
    """
    性能监控器

    使用方法:
    1. 创建实例: monitor = PerformanceMonitor(system)
    2. 启用监控: monitor.enable()
    3. 在Update中调用: monitor.on_tick_start() / monitor.on_tick_end()
    4. 记录事件: monitor.record_event(event_name, duration)
    """

    def __init__(self, system):
        """
        初始化性能监控器

        Args:
            system: 游戏系统实例
        """
        self.system = system
        self.enabled = False

        # ===== Tick统计 =====
        self.tick_times = []  # 最近100个tick的耗时列表
        self.tick_start_time = 0
        self.total_ticks = 0
        self.start_time = time.time()

        # ===== 事件统计 =====
        self.event_counts = {}  # {event_name: count}
        self.event_times = {}   # {event_name: total_time_sec}

        # ===== 内存统计 =====
        self.memory_samples = []  # [(timestamp, memory_mb), ...]
        self.last_memory_sample = 0

        # ===== 报告配置 =====
        self.report_interval = 60  # 每60秒生成一次报告
        self.last_report = time.time()

        # ===== 性能统计 =====
        self.tps_history = []  # TPS历史记录
        self.max_tick_time = 0
        self.min_tick_time = float('inf')

    def enable(self):
        """启用性能监控"""
        self.enabled = True
        self.start_time = time.time()
        self.last_report = time.time()
        print("[PerformanceMonitor] 性能监控已启用")

    def disable(self):
        """禁用性能监控"""
        self.enabled = False
        print("[PerformanceMonitor] 性能监控已禁用")

    def on_tick_start(self):
        """
        Tick开始时调用

        在系统Update()方法的开始处调用
        """
        if not self.enabled:
            return
        self.tick_start_time = time.time()

    def on_tick_end(self):
        """
        Tick结束时调用

        在系统Update()方法的结束处调用
        """
        if not self.enabled:
            return

        # 计算本次tick耗时
        tick_duration = time.time() - self.tick_start_time
        self.tick_times.append(tick_duration)
        self.total_ticks += 1

        # 更新最大最小值
        if tick_duration > self.max_tick_time:
            self.max_tick_time = tick_duration
        if tick_duration < self.min_tick_time:
            self.min_tick_time = tick_duration

        # 每100个tick统计一次
        if len(self.tick_times) >= 100:
            self._analyze_tick_performance()
            self.tick_times = []

        # 定期采样内存
        self._sample_memory()

        # 定期生成报告
        self._check_and_generate_report()

    def record_event(self, event_name, duration=0):
        """
        记录事件

        Args:
            event_name (str): 事件名称
            duration (float): 事件处理时间（秒），默认为0
        """
        if not self.enabled:
            return

        if event_name not in self.event_counts:
            self.event_counts[event_name] = 0
            self.event_times[event_name] = 0.0

        self.event_counts[event_name] += 1
        if duration > 0:
            self.event_times[event_name] += duration

    def get_current_tps(self):
        """
        获取当前TPS

        Returns:
            float: 当前TPS（基于最近100个tick的平均值）
        """
        if not self.tick_times:
            return 0.0

        avg_tick_time = sum(self.tick_times) / len(self.tick_times)
        if avg_tick_time <= 0:
            return 0.0

        return 1.0 / avg_tick_time

    def _analyze_tick_performance(self):
        """分析Tick性能（每100个tick执行一次）"""
        if not self.tick_times:
            return

        # 计算统计数据
        avg_tick_time = sum(self.tick_times) / len(self.tick_times)
        max_tick_time = max(self.tick_times)
        min_tick_time = min(self.tick_times)

        # 计算TPS
        tps = 1.0 / avg_tick_time if avg_tick_time > 0 else 0.0
        self.tps_history.append((time.time(), tps))

        # 只保留最近10分钟的TPS历史
        cutoff_time = time.time() - 600
        self.tps_history = [(t, v) for t, v in self.tps_history if t > cutoff_time]

        # 输出统计信息
        print("[PerformanceMonitor] TPS: {:.2f} | 平均: {:.2f}ms | 最大: {:.2f}ms | 最小: {:.2f}ms".format(
            tps,
            avg_tick_time * 1000,
            max_tick_time * 1000,
            min_tick_time * 1000
        ))

        # 性能警告
        if tps < 18:
            print("[PerformanceMonitor] [WARNING] TPS过低: {:.2f} < 18".format(tps))
        if avg_tick_time > 0.040:  # 40ms
            print("[PerformanceMonitor] [WARNING] 平均Tick时间过长: {:.2f}ms".format(
                avg_tick_time * 1000
            ))

    def _sample_memory(self):
        """采样内存使用（每10秒执行一次）"""
        now = time.time()
        if now - self.last_memory_sample < 10:
            return

        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024

            self.memory_samples.append((now, memory_mb))
            self.last_memory_sample = now

            # 只保留最近1小时的数据
            cutoff_time = now - 3600
            self.memory_samples = [
                (t, m) for t, m in self.memory_samples if t > cutoff_time
            ]

            # 内存警告
            if memory_mb > 800:
                print("[PerformanceMonitor] [WARNING] 内存使用过高: {:.2f}MB".format(
                    memory_mb
                ))

        except ImportError:
            # psutil未安装，跳过内存监控
            if not hasattr(self, '_psutil_warning_shown'):
                print("[PerformanceMonitor] [INFO] psutil未安装，跳过内存监控")
                self._psutil_warning_shown = True
        except Exception as e:
            print("[PerformanceMonitor] [ERROR] 内存采样失败: {}".format(str(e)))

    def _check_and_generate_report(self):
        """检查并生成性能报告"""
        now = time.time()
        if now - self.last_report < self.report_interval:
            return

        self._generate_report()
        self.last_report = now

    def _generate_report(self):
        """生成性能报告"""
        now = time.time()
        uptime = now - self.start_time

        # 计算平均TPS
        if self.tps_history:
            avg_tps = sum(v for _, v in self.tps_history) / len(self.tps_history)
        else:
            avg_tps = self.total_ticks / uptime if uptime > 0 else 0

        # 构建报告
        report = {
            "timestamp": now,
            "uptime_seconds": uptime,
            "performance": {
                "total_ticks": self.total_ticks,
                "avg_tps": avg_tps,
                "avg_tick_time_ms": (1000.0 / avg_tps) if avg_tps > 0 else 0,
                "max_tick_time_ms": self.max_tick_time * 1000,
                "min_tick_time_ms": self.min_tick_time * 1000 if self.min_tick_time != float('inf') else 0,
            },
            "events": self._build_event_report(),
            "memory": self._build_memory_report(),
            "health": self._evaluate_health(avg_tps)
        }

        # 输出报告
        self._output_report(report)

        return report

    def _build_event_report(self):
        """构建事件统计报告"""
        events = {}
        for event_name in self.event_counts:
            count = self.event_counts[event_name]
            total_time = self.event_times.get(event_name, 0)
            avg_time = (total_time / count * 1000) if count > 0 else 0

            events[event_name] = {
                "count": count,
                "total_time_ms": total_time * 1000,
                "avg_time_ms": avg_time
            }

        # 按调用次数排序（前10名）
        sorted_events = sorted(
            events.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )[:10]

        return dict(sorted_events)

    def _build_memory_report(self):
        """构建内存统计报告"""
        if not self.memory_samples:
            return {
                "current_mb": 0,
                "growth_mb_per_hour": 0,
                "status": "no_data"
            }

        current_mb = self.memory_samples[-1][1]
        growth_rate = self._calculate_memory_growth()

        # 评估内存状态
        if current_mb > 800:
            status = "critical"
        elif current_mb > 600:
            status = "warning"
        else:
            status = "healthy"

        return {
            "current_mb": current_mb,
            "growth_mb_per_hour": growth_rate,
            "status": status
        }

    def _calculate_memory_growth(self):
        """计算内存增长率（MB/小时）"""
        if len(self.memory_samples) < 2:
            return 0.0

        # 使用线性回归计算增长率
        first_sample = self.memory_samples[0]
        last_sample = self.memory_samples[-1]

        time_diff_hours = (last_sample[0] - first_sample[0]) / 3600
        if time_diff_hours <= 0:
            return 0.0

        memory_diff_mb = last_sample[1] - first_sample[1]
        return memory_diff_mb / time_diff_hours

    def _evaluate_health(self, avg_tps):
        """
        评估系统健康状态

        Args:
            avg_tps (float): 平均TPS

        Returns:
            str: 健康状态（"healthy", "warning", "critical"）
        """
        if avg_tps >= 19:
            return "healthy"
        elif avg_tps >= 18:
            return "warning"
        else:
            return "critical"

    def _output_report(self, report):
        """
        输出性能报告

        Args:
            report (dict): 报告数据
        """
        # 输出到控制台
        print("=" * 60)
        print("[PerformanceMonitor] ===== 性能报告 =====")
        print("运行时间: {:.2f}秒 ({:.2f}分钟)".format(
            report['uptime_seconds'],
            report['uptime_seconds'] / 60
        ))
        print("TPS: {:.2f} | 平均Tick: {:.2f}ms | 最大Tick: {:.2f}ms".format(
            report['performance']['avg_tps'],
            report['performance']['avg_tick_time_ms'],
            report['performance']['max_tick_time_ms']
        ))
        print("内存: {:.2f}MB | 增长率: {:.2f}MB/h | 状态: {}".format(
            report['memory']['current_mb'],
            report['memory']['growth_mb_per_hour'],
            report['memory']['status']
        ))
        print("健康状态: {}".format(report['health']))

        # 输出事件统计（前5名）
        if report['events']:
            print("\n最频繁事件（前5名）:")
            for i, (event_name, data) in enumerate(list(report['events'].items())[:5], 1):
                print("  {}. {} - 调用{}次 | 平均{:.2f}ms".format(
                    i, event_name, data['count'], data['avg_time_ms']
                ))

        print("=" * 60)

        # 保存到文件
        self._save_report_to_file(report)

    def _save_report_to_file(self, report):
        """
        保存报告到文件

        Args:
            report (dict): 报告数据
        """
        try:
            filename = "performance_report_{}.json".format(int(report['timestamp']))
            # Python 2.7兼容方式
            with codecs.open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print("[PerformanceMonitor] 报告已保存: {}".format(filename))
        except Exception as e:
            print("[PerformanceMonitor] [ERROR] 保存报告失败: {}".format(str(e)))

    def get_summary(self):
        """
        获取性能摘要

        Returns:
            dict: 性能摘要数据
        """
        if not self.enabled:
            return {"status": "disabled"}

        now = time.time()
        uptime = now - self.start_time

        # 计算平均TPS
        if self.tps_history:
            avg_tps = sum(v for _, v in self.tps_history) / len(self.tps_history)
        else:
            avg_tps = self.total_ticks / uptime if uptime > 0 else 0

        return {
            "status": "enabled",
            "uptime_seconds": uptime,
            "total_ticks": self.total_ticks,
            "avg_tps": avg_tps,
            "current_tps": self.get_current_tps(),
            "health": self._evaluate_health(avg_tps)
        }


# ===== 辅助函数 =====

def profile_function(func):
    """
    函数性能分析装饰器

    自动记录函数执行时间

    Usage:
        @profile_function
        def my_function(self, args):
            pass
    """
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start_time

        # 如果第一个参数是self且有performance_monitor，记录到监控器
        if args and hasattr(args[0], 'performance_monitor'):
            system = args[0]
            if hasattr(system, 'performance_monitor'):
                system.performance_monitor.record_event(
                    func.__name__,
                    duration
                )

        return result

    return wrapper
