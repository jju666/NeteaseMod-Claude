#!/bin/bash
# 安装通知依赖库脚本
# 用于在非VSCode环境中启用系统原生通知

set -e

echo "========================================"
echo "  MODSDK 通知系统 - 依赖安装工具"
echo "========================================"
echo ""

# 检测Python环境
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "❌ 错误: 未找到 Python 环境"
    echo "   请先安装 Python 3.7+"
    exit 1
fi

PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

echo "✅ 检测到 Python: $($PYTHON_CMD --version)"
echo ""

# 检测操作系统
OS_TYPE=$(uname -s)
echo "📍 操作系统: $OS_TYPE"
echo ""

# Linux特殊处理: 检查notify-send
if [[ "$OS_TYPE" == "Linux" ]]; then
    if ! command -v notify-send &> /dev/null; then
        echo "⚠️  Linux系统需要安装 libnotify 工具"
        echo ""
        echo "请根据你的发行版执行以下命令之一:"
        echo ""
        echo "  Ubuntu/Debian:"
        echo "    sudo apt-get install libnotify-bin"
        echo ""
        echo "  Fedora/CentOS:"
        echo "    sudo yum install libnotify"
        echo ""
        echo "  Arch Linux:"
        echo "    sudo pacman -S libnotify"
        echo ""
        read -p "是否继续安装 plyer 库? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "已取消安装"
            exit 0
        fi
    else
        echo "✅ 检测到 notify-send"
    fi
    echo ""
fi

# 检查plyer是否已安装
if $PYTHON_CMD -c "import plyer" 2>/dev/null; then
    echo "✅ plyer 库已安装"
    PLYER_VERSION=$($PYTHON_CMD -c "import plyer; print(plyer.__version__)")
    echo "   版本: $PLYER_VERSION"
    echo ""
    echo "✨ 通知系统已就绪!"
    echo ""
    echo "测试通知:"
    echo "  python templates/.claude/hooks/vscode_notify.py"
    exit 0
fi

# 安装plyer
echo "📦 开始安装 plyer 通知库..."
echo ""

if $PYTHON_CMD -m pip install plyer; then
    echo ""
    echo "✅ plyer 安装成功!"
    echo ""
    echo "✨ 通知系统已就绪!"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  测试通知功能"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "运行以下命令测试通知:"
    echo "  python templates/.claude/hooks/vscode_notify.py"
    echo ""
    echo "或者在项目中触发实际通知:"
    echo "  /mc \"测试任务\""
    echo ""
else
    echo ""
    echo "❌ plyer 安装失败"
    echo ""
    echo "可能的原因:"
    echo "  1. 网络连接问题"
    echo "  2. pip 版本过旧"
    echo "  3. 权限不足"
    echo ""
    echo "手动安装命令:"
    echo "  $PYTHON_CMD -m pip install --user plyer"
    echo ""
    echo "注意: 即使不安装 plyer,通知系统仍会工作"
    echo "      (降级为彩色终端输出)"
    exit 1
fi
