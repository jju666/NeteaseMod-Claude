@echo off
chcp 65001 >nul
echo ========================================
echo Hook缓存和日志清理工具
echo ========================================
echo.

echo [1/3] 清理Python字节码缓存...
if exist ".claude\hooks\orchestrator\__pycache__" (
    rmdir /s /q ".claude\hooks\orchestrator\__pycache__"
    echo ✓ orchestrator缓存已清理
) else (
    echo - orchestrator缓存不存在
)

if exist ".claude\hooks\core\__pycache__" (
    rmdir /s /q ".claude\hooks\core\__pycache__"
    echo ✓ core缓存已清理
) else (
    echo - core缓存不存在
)

if exist ".claude\hooks\lifecycle\__pycache__" (
    rmdir /s /q ".claude\hooks\lifecycle\__pycache__"
    echo ✓ lifecycle缓存已清理
) else (
    echo - lifecycle缓存不存在
)

if exist ".claude\hooks\archiver\__pycache__" (
    rmdir /s /q ".claude\hooks\archiver\__pycache__"
    echo ✓ archiver缓存已清理
) else (
    echo - archiver缓存不存在
)

echo.
echo [2/3] 清理DEBUG日志文件...
if exist "pretooluse-debug.log" (
    del /f "pretooluse-debug.log"
    echo ✓ pretooluse-debug.log已删除
) else (
    echo - pretooluse-debug.log不存在
)

if exist "posttooluse-debug.log" (
    del /f "posttooluse-debug.log"
    echo ✓ posttooluse-debug.log已删除
) else (
    echo - posttooluse-debug.log不存在
)

if exist "subagent-stop-debug.log" (
    del /f "subagent-stop-debug.log"
    echo ✓ subagent-stop-debug.log已删除
) else (
    echo - subagent-stop-debug.log不存在
)

echo.
echo [3/3] 清理完成！
echo.
echo ⚠️  提醒:
echo   - 如果Claude Code正在运行，请重启以加载最新Hook代码
echo   - 重启VS Code或Claude Code CLI进程
echo.
echo ========================================
pause
