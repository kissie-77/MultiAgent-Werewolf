@echo off
REM ============================================================
REM  AI Werewolf - 一键停止前后端服务（端口 8000 / 5173）
REM ============================================================
chcp 65001 >nul

echo.
echo   正在停止 AI Werewolf 服务 (端口 8000 / 5173) ...

for %%P in (8000 5173) do (
  for /f "tokens=5" %%I in ('netstat -ano ^| findstr ":%%P" ^| findstr LISTENING') do (
    taskkill /F /PID %%I >nul 2>&1 && echo   已结束 PID %%I  ^(端口 %%P^)
  )
)

echo   完成。若仍有残留，可手动 taskkill。
echo.
pause
