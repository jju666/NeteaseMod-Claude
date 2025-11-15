#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
跨平台通知辅助模块
为 Claude Code Hooks 提供系统级弹窗通知功能

支持的平台:
- Windows: Windows 通知中心
- macOS: 通知中心
- Linux: libnotify (需要先安装 notify-send)

注意: Claude Code 不支持通过 stderr 触发 IDE 通知，
因此本模块使用系统原生通知（plyer库）

使用方法:
    from vscode_notify import notify_info, notify_warning, notify_error

    notify_info("任务追踪已初始化", "tasks/task-12345/")
    notify_warning("任务失败", "失败次数: 2次")
    notify_error("专家审核未通过", "评分: 6.5/10")

安装依赖:
    pip install plyer
"""

import sys
import json
import os
import platform

# 尝试导入系统通知库
try:
    # plyer是跨平台通知库，支持Windows/Linux/macOS
    from plyer import notification as plyer_notify
    HAS_PLYER = True
except ImportError:
    HAS_PLYER = False

def notify(level, message, detail=""):
    """
    发送跨平台通知

    Args:
        level: 通知级别 ("info", "warning", "error")
        message: 主消息
        detail: 详细信息（可选）

    通知策略:
    1. plyer库可用: 使用系统原生通知（Windows/macOS/Linux）
    2. 降级: 彩色终端输出

    注意: VSCode/Claude Code 不支持通过 stderr 触发 IDE 通知
    """
    try:
        full_message = message
        if detail:
            full_message = "{} - {}".format(message, detail)

        # 策略1: 系统原生通知（Windows/macOS/Linux）
        if HAS_PLYER:
            try:
                # 确保消息是字符串且不包含无法编码的字符
                safe_message = str(full_message).encode('utf-8', errors='replace').decode('utf-8')

                plyer_notify.notify(
                    title="Claude Code - {}".format(level.upper()),
                    message=safe_message,
                    app_name="Claude Code Hooks",
                    timeout=5  # 5秒后自动消失
                )
                # 同时输出到终端确认通知已发送
                sys.stderr.write("[SYSTEM-NOTIFY] {}\n".format(safe_message))
                sys.stderr.flush()
                return
            except Exception as e:
                # plyer通知失败，降级到终端输出
                sys.stderr.write("[PLYER-ERROR] {}\n".format(str(e)))

        # 策略2: 降级为彩色终端输出
        notify_fallback(level, message, detail)

    except Exception as e:
        # 通知失败不应该影响 hook 执行
        sys.stderr.write("[NOTIFY-ERROR] {}\n".format(str(e)))

def notify_info(message, detail=""):
    """发送信息级别通知（蓝色图标）"""
    notify("info", message, detail)

def notify_warning(message, detail=""):
    """发送警告级别通知（黄色图标）"""
    notify("warning", message, detail)

def notify_error(message, detail=""):
    """发送错误级别通知（红色图标）"""
    notify("error", message, detail)

# 降级通知函数：彩色终端输出
def notify_fallback(level, message, detail=""):
    """
    降级通知：使用彩色终端输出

    使用ANSI转义码显示彩色文本（Windows 10+, Linux, macOS支持）
    """
    # ANSI颜色代码
    colors = {
        "info": "\033[94m",      # 蓝色
        "warning": "\033[93m",   # 黄色
        "error": "\033[91m",     # 红色
        "reset": "\033[0m"       # 重置
    }

    # Emoji图标
    icons = {
        "info": "ℹ️",
        "warning": "⚠️",
        "error": "❌"
    }

    color = colors.get(level, colors["reset"])
    icon = icons.get(level, "•")
    reset = colors["reset"]

    # 构建输出
    output = "{}{} {}{}".format(color, icon, message, reset)
    if detail:
        output += " - {}".format(detail)

    sys.stderr.write(output + "\n")
    sys.stderr.flush()

# 测试函数
if __name__ == '__main__':
    import io

    # 修复Windows GBK编码问题
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    print("=== 测试跨平台通知系统 ===\n")

    print("环境检测:")
    print("- plyer库可用: {}".format(HAS_PLYER))
    print("- 操作系统: {}\n".format(platform.system()))

    if not HAS_PLYER:
        print("ERROR: plyer库未安装")
        print("请运行: pip install plyer")
        sys.exit(1)

    print("发送测试通知...\n")
    notify_info("测试信息通知", "这是详细信息")
    notify_warning("测试警告通知", "这是警告详情")
    notify_error("测试错误通知", "这是错误详情")

    print("\n如果你看到了系统弹窗，说明通知功能正常工作！")
    print("\nplyer 支持:")
    print("  - Windows: 原生通知中心")
    print("  - macOS: 通知中心")
    print("  - Linux: libnotify (需先安装 notify-send)")
