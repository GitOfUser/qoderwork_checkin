@echo off
chcp 65001 >nul 2>&1
title QoderWork 签到定时任务管理

echo ============================================
echo   QoderWork 每日签到 - 定时任务管理
echo ============================================
echo.
echo   1. 创建定时任务（每天 9:00 自动签到）
echo   2. 删除定时任务
echo   3. 查看任务状态
echo   4. 立即手动执行一次签到
echo   5. 测试模式运行（不点击）
echo   0. 退出
echo.

set /p choice=请选择操作 [0-5]: 

if "%choice%"=="1" goto create
if "%choice%"=="2" goto delete
if "%choice%"=="3" goto status
if "%choice%"=="4" goto run_now
if "%choice%"=="5" goto test
if "%choice%"=="0" goto end
goto end

:create
echo.
echo 正在创建定时任务...
schtasks /create /tn "QoderWork_DailyCheckin" /tr "\"C:\Python314\python.exe\" \"D:\QoderWork Working Directory\定时任务\领取积分\qoderwork_checkin.py\" --max" /sc daily /st 09:00 /rl highest /f /it
if %errorlevel%==0 (
    echo.
    echo [成功] 定时任务已创建！每天 9:00 将自动执行签到。
) else (
    echo.
    echo [失败] 创建任务失败，请尝试以管理员身份运行此脚本。
)
echo.
pause
goto end

:delete
echo.
echo 正在删除定时任务...
schtasks /delete /tn "QoderWork_DailyCheckin" /f
if %errorlevel%==0 (
    echo.
    echo [成功] 定时任务已删除。
) else (
    echo.
    echo [失败] 删除任务失败，任务可能不存在。
)
echo.
pause
goto end

:status
echo.
echo ---- 任务状态 ----
schtasks /query /tn "QoderWork_DailyCheckin" /fo list /v 2>nul
if %errorlevel% neq 0 (
    echo [提示] 定时任务尚未创建。
)
echo.
pause
goto end

:run_now
echo.
echo 正在执行签到...
C:\Python314\python.exe "D:\QoderWork Working Directory\定时任务\领取积分\qoderwork_checkin.py" --max
echo.
pause
goto end

:test
echo.
echo 正在测试模式运行（仅查找窗口，不点击）...
C:\Python314\python.exe "D:\QoderWork Working Directory\定时任务\领取积分\qoderwork_checkin.py" --dry-run
echo.
pause
goto end

:end
echo 再见！
