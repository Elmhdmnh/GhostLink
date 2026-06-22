@echo off
title 一键恢复工具
cd /d "%~dp0"

:: ===== 检查管理员权限 =====
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] 需要管理员权限，正在请求提权...
    powershell Start-Process "%~f0" -Verb RunAs
    exit /b
)

echo ========================================
echo          一键恢复 AMSI ^& 任务管理器
echo ========================================
echo.

:: 恢复 AMSI - 将 AmsiEnable 设为 1（启用）
echo [*] 正在恢复 AMSI...
reg add "HKCU\Software\Microsoft\Windows Script\Settings" /v AmsiEnable /t REG_DWORD /d 1 /f >nul
if %errorlevel% equ 0 ( echo [+] AMSI 已恢复！ ) else ( echo [-] AMSI 恢复失败！ )

echo.

:: 恢复任务管理器 - 将 DisableTaskMgr 设为 0（启用）
echo [*] 正在恢复任务管理器...
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\System" /v DisableTaskMgr /t REG_DWORD /d 0 /f >nul
if %errorlevel% equ 0 ( echo [+] 任务管理器已恢复！ ) else ( echo [-] 任务管理器恢复失败！ )

echo.
echo ========================================
echo 恢复完成！建议重启电脑或重启资源管理器。
echo 按任意键立即重启资源管理器...
echo ========================================
pause >nul

:: 重启资源管理器使注册表生效
taskkill /f /im explorer.exe >nul 2>&1
start explorer.exe

exit
