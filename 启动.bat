@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo 正在启动后台（服务端）...
start "后台-服务端" cmd /k "python 后台.py"

echo 正在启动客户端...
start "客户端" cmd /k "python 客户端.py"

echo 两个窗口已启动！
pause
