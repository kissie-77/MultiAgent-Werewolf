@echo off
REM ============================================================
REM  AI Werewolf - 纯 LLM 观战模式 一键启动
REM  等前端真正就绪后再开浏览器（避免"打不开"）
REM ============================================================
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo   ====== AI Werewolf 纯 LLM 观战 一键启动 ======
echo   后端 (FastAPI) : http://127.0.0.1:8000
echo   前端 (Vite)    : http://127.0.0.1:5173
echo   会弹出两个新窗口分别跑后端/前端；本窗口等前端就绪后自动开浏览器。
echo.

REM --- 后端：端口 8000 ---
start "Werewolf Backend :8000" cmd /k "set PYTHONUTF8=1&&set PYTHONIOENCODING=utf-8&&uv run werewolf-api --host 127.0.0.1 --port 8000"

REM --- 前端：端口 5173（首跑自动 npm install）---
start "Werewolf Frontend :5173" cmd /k "cd frontend && (if not exist node_modules npm install) && npm run dev:spectate"

echo   正在等待前端就绪（首次启动或装依赖可能要 1-2 分钟，请耐心）...
set /a tries=0
:waitloop
timeout /t 2 >nul
set /a tries+=1
curl -s -o nul -m 2 http://127.0.0.1:5173/ >nul 2>&1
if not errorlevel 1 goto ready
if %tries% geq 90 goto giveup
goto waitloop

:ready
echo   前端已就绪，正在打开浏览器 http://127.0.0.1:5173
start "" http://127.0.0.1:5173
goto end

:giveup
echo.
echo   [超时] 等了约 180 秒前端仍未就绪。请检查那两个新窗口里是否有报错：
echo     - 提示 'uv' / 'npm' / 'node' 不是内部或外部命令 = 系统 PATH 里找不到它们；
echo     - 提示端口被占用(address in use) = 先运行 stop-spectate.bat 再重来；
echo   也可手动在浏览器打开 http://127.0.0.1:5173 （务必用 127.0.0.1，不要用 localhost）。

:end
echo.
echo   停止服务：运行 stop-spectate.bat，或直接关掉那两个新开的窗口。
echo.
pause
