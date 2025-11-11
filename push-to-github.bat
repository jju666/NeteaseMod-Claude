@echo off
REM ========================================
REM NeteaseMod-Claude v16.1.0 发布脚本
REM ========================================

echo.
echo ===================================
echo   NeteaseMod-Claude v16.1.0 发布
echo ===================================
echo.

echo [1/3] 推送main分支到GitHub...
git push origin main
if %errorlevel% neq 0 (
    echo.
    echo ❌ 错误: 推送main分支失败
    echo 请检查网络连接或GitHub认证状态
    pause
    exit /b 1
)
echo ✅ main分支推送成功

echo.
echo [2/3] 推送标签v16.1.0到GitHub...
git push origin v16.1.0
if %errorlevel% neq 0 (
    echo.
    echo ❌ 错误: 推送标签失败
    pause
    exit /b 1
)
echo ✅ 标签v16.1.0推送成功

echo.
echo [3/3] 验证推送结果...
git log --oneline -3
git tag -l | findstr "v16.1.0"

echo.
echo ===================================
echo   ✅ 推送完成！
echo ===================================
echo.
echo 下一步操作：
echo 1. 访问: https://github.com/jju666/NeteaseMod-Claude/releases/new
echo 2. 选择标签: v16.1.0
echo 3. 发布标题: v16.1.0 - 双重定制架构
echo 4. 发布描述: 从CHANGELOG.md复制v16.1.0内容
echo 5. 点击 "Publish release"
echo.

pause
