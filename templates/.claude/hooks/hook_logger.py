#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
统一Hook日志记录器 (v19.4.0)
功能: 为所有Hook提供统一的日志记录、性能监控和调试功能

设计理念:
1. 统一日志格式 - 所有Hook使用相同的日志结构
2. 性能追踪 - 记录每个Hook的执行时间
3. 错误收集 - 自动记录Hook执行过程中的异常
4. 调试友好 - 支持多级别日志输出

使用方法:
    from hook_logger import HookLogger

    logger = HookLogger("check-critical-rules")
    logger.start()
    logger.info("开始检查CRITICAL规范")
    logger.decision("allow", "跳过非Python文件")
    logger.success("检查通过", {"violations": 0})
    logger.finish(success=True)

日志文件路径: .claude/hooks/hook-execution.log
"""

import sys
import json
import os
import io
from datetime import datetime
import traceback

# 修复Windows GBK编码问题（避免重复包装）
if sys.platform == 'win32':
    try:
        # 只在未被包装时执行
        if hasattr(sys.stdout, 'buffer') and not isinstance(sys.stdout, io.TextIOWrapper):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        if hasattr(sys.stderr, 'buffer') and not isinstance(sys.stderr, io.TextIOWrapper):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except (AttributeError, ValueError):
        pass  # 如果已经被包装或不支持，忽略错误


class HookLogger:
    """统一Hook日志记录器"""

    # 日志级别
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3

    # 日志文件路径（相对于项目根目录）
    LOG_FILE = ".claude/hooks/hook-execution.log"

    # 最大日志文件大小（10MB）
    MAX_LOG_SIZE = 10 * 1024 * 1024

    def __init__(self, hook_name, log_level=INFO):
        """
        初始化Hook日志记录器

        Args:
            hook_name: Hook名称（如 "check-critical-rules"）
            log_level: 日志级别（默认INFO）
        """
        self.hook_name = hook_name
        self.log_level = log_level
        self.session_id = datetime.now().strftime('%Y%m%d-%H%M%S-%f')[:20]
        self.start_time = None
        self.execution_data = {
            "hook_name": hook_name,
            "session_id": self.session_id,
            "start_time": None,
            "end_time": None,
            "duration_ms": None,
            "success": None,
            "events": [],
            "errors": []
        }

        # 获取项目根目录
        self.project_dir = os.environ.get('CLAUDE_PROJECT_DIR', os.getcwd())
        self.log_path = os.path.join(self.project_dir, self.LOG_FILE)

        # 确保日志目录存在
        log_dir = os.path.dirname(self.log_path)
        if not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir)
            except:
                pass  # 创建失败不影响Hook执行

    def start(self):
        """记录Hook开始执行"""
        self.start_time = datetime.now()
        self.execution_data["start_time"] = self.start_time.isoformat()

        self._log_event("START", "Hook触发", level=self.INFO)
        self._write_to_stderr(u"🔗 [{hook}] 触发 | Session: {session}".format(
            hook=self.hook_name,
            session=self.session_id
        ))

    def finish(self, success=True, message=""):
        """
        记录Hook执行完成

        Args:
            success: 执行是否成功
            message: 完成消息
        """
        end_time = datetime.now()
        self.execution_data["end_time"] = end_time.isoformat()
        self.execution_data["success"] = success

        if self.start_time:
            duration = (end_time - self.start_time).total_seconds() * 1000
            self.execution_data["duration_ms"] = round(duration, 2)

        event_type = "SUCCESS" if success else "FAILURE"
        self._log_event(event_type, message or "Hook执行完成", level=self.INFO)

        # 写入统一日志文件
        self._write_to_log_file()

        # 输出到stderr
        icon = "✅" if success else "❌"
        duration_str = "{:.2f}ms".format(self.execution_data["duration_ms"]) if self.execution_data["duration_ms"] else "N/A"
        self._write_to_stderr(u"{} [{hook}] {result} | 耗时: {duration}".format(
            icon,
            hook=self.hook_name,
            result=message or ("完成" if success else "失败"),
            duration=duration_str
        ))

    def info(self, message, data=None):
        """记录INFO级别日志"""
        self._log_event("INFO", message, data, level=self.INFO)

    def debug(self, message, data=None):
        """记录DEBUG级别日志"""
        self._log_event("DEBUG", message, data, level=self.DEBUG)

    def warning(self, message, data=None):
        """记录WARNING级别日志"""
        self._log_event("WARNING", message, data, level=self.WARNING)
        self._write_to_stderr(u"⚠️  [{hook}] {msg}".format(
            hook=self.hook_name,
            msg=message
        ))

    def error(self, message, error=None):
        """
        记录ERROR级别日志

        Args:
            message: 错误消息
            error: 异常对象（可选）
        """
        error_data = {
            "message": message,
            "timestamp": datetime.now().isoformat()
        }

        if error:
            error_data["exception_type"] = type(error).__name__
            error_data["exception_message"] = str(error)
            error_data["traceback"] = traceback.format_exc()

        self.execution_data["errors"].append(error_data)
        self._log_event("ERROR", message, error_data, level=self.ERROR)

        self._write_to_stderr(u"❌ [{hook}] 错误: {msg}".format(
            hook=self.hook_name,
            msg=message
        ))

    def decision(self, decision_type, reason, data=None):
        """
        记录Hook决策（用于PreToolUse等需要返回决策的Hook）

        Args:
            decision_type: 决策类型（如 "allow", "deny", "skip"）
            reason: 决策原因
            data: 附加数据
        """
        event_data = {
            "decision": decision_type,
            "reason": reason
        }
        if data:
            event_data.update(data)

        self._log_event("DECISION", reason, event_data, level=self.INFO)

        # 根据决策类型选择图标
        icons = {
            "allow": "✓",
            "deny": "✗",
            "skip": "⊘",
            "block": "🛑"
        }
        icon = icons.get(decision_type, "→")

        self._write_to_stderr(u"{} [{hook}] {decision}: {reason}".format(
            icon,
            hook=self.hook_name,
            decision=decision_type.upper(),
            reason=reason
        ))

    def success_block(self, title, items):
        """记录成功块（多项成功结果）"""
        self._log_event("SUCCESS_BLOCK", title, {"items": items}, level=self.INFO)

        output = u"\n✅ [{hook}] {title}\n".format(
            hook=self.hook_name,
            title=title
        )
        for item in items:
            output += u"  ✓ {}\n".format(item)

        self._write_to_stderr(output)

    def error_block(self, title, errors):
        """记录错误块（多项错误）"""
        error_data = {
            "title": title,
            "errors": errors,
            "timestamp": datetime.now().isoformat()
        }
        self.execution_data["errors"].append(error_data)
        self._log_event("ERROR_BLOCK", title, {"errors": errors}, level=self.ERROR)

        output = u"\n❌ [{hook}] {title}\n".format(
            hook=self.hook_name,
            title=title
        )
        for error in errors:
            output += u"  • {}\n".format(error)

        self._write_to_stderr(output)

    def _log_event(self, event_type, message, data=None, level=INFO):
        """
        内部方法：记录事件到执行数据

        Args:
            event_type: 事件类型
            message: 事件消息
            data: 附加数据
            level: 日志级别
        """
        if level < self.log_level:
            return  # 跳过低于当前日志级别的消息

        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "message": message,
            "level": self._level_name(level)
        }

        if data:
            event["data"] = data

        self.execution_data["events"].append(event)

    def _level_name(self, level):
        """将日志级别转换为名称"""
        names = {
            self.DEBUG: "DEBUG",
            self.INFO: "INFO",
            self.WARNING: "WARNING",
            self.ERROR: "ERROR"
        }
        return names.get(level, "UNKNOWN")

    def _write_to_stderr(self, message):
        """写入stderr供Claude Code显示"""
        try:
            sys.stderr.write(message + "\n")
            sys.stderr.flush()
        except:
            pass  # 写入失败不影响Hook执行

    def _write_to_log_file(self):
        """将执行数据写入统一日志文件"""
        try:
            # 检查日志文件大小，超过限制则轮转
            if os.path.exists(self.log_path):
                if os.path.getsize(self.log_path) > self.MAX_LOG_SIZE:
                    self._rotate_log_file()

            # 追加日志记录
            with open(self.log_path, 'a', encoding='utf-8') as f:
                # 写入单行JSON（便于解析）
                json_line = json.dumps(self.execution_data, ensure_ascii=False)
                f.write(json_line + "\n")

        except Exception as e:
            # 日志写入失败不影响Hook执行
            self._write_to_stderr(u"⚠️  日志写入失败: {}".format(str(e)))

    def _rotate_log_file(self):
        """日志文件轮转（保留最近的记录）"""
        try:
            backup_path = self.log_path + ".old"
            if os.path.exists(backup_path):
                os.remove(backup_path)
            os.rename(self.log_path, backup_path)
        except:
            pass  # 轮转失败不影响Hook执行


# ========================================
# 便捷函数（兼容旧Hook代码）
# ========================================

def create_logger(hook_name, log_level=HookLogger.INFO):
    """
    创建Hook日志记录器的便捷函数

    Args:
        hook_name: Hook名称
        log_level: 日志级别

    Returns:
        HookLogger实例
    """
    return HookLogger(hook_name, log_level)


# ========================================
# 测试代码
# ========================================

if __name__ == '__main__':
    print("=== Hook日志记录器测试 ===\n")

    # 测试1: 基本日志记录
    logger = HookLogger("test-hook")
    logger.start()
    logger.info("开始执行测试")
    logger.debug("调试信息", {"key": "value"})
    logger.decision("allow", "测试决策")
    logger.success_block("测试成功块", ["项目1", "项目2", "项目3"])
    logger.finish(success=True, message="测试完成")

    print("\n测试1: 基本日志记录 ✅")

    # 测试2: 错误处理
    logger2 = HookLogger("test-error-hook")
    logger2.start()
    logger2.warning("这是警告信息")
    logger2.error_block("错误列表", ["错误1", "错误2"])
    try:
        raise ValueError("测试异常")
    except Exception as e:
        logger2.error("捕获异常", e)
    logger2.finish(success=False, message="测试失败")

    print("测试2: 错误处理 ✅")

    # 显示日志文件路径
    print("\n日志文件路径: {}".format(logger.log_path))
    print("\n请检查日志文件内容！")
