@echo off
REM ============================================================
REM  AI Werewolf - 纯 LLM 观战模式 一键启动
REM  双击本文件即可：起 Python 后端 + Vite 前端 + 开浏览器
REM ============================================================
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo   ====== AI Werewolf 纯 LLM 观战 一键启动 ======
echo   后端 (FastAPI) : http://127.0.0.1:8000
echo   前端 (Vite)    : http://127.0.0.1:5173
echo   首次启动会自动装依赖(可能要几分钟)，请耐心等两个新窗口就绪。
echo.

REM --- 后端：Python FastAPI，端口 8000（uv run 会自动同步依赖）---
start "Werewolf Backend :8000" cmd /k "set PYTHONUTF8=1&&set PYTHONIOENCODING=utf-8&&uv run werewolf-api --host 127.0.0.1 --port 8000"

REM --- 前端：Vite dev server，端口 5173（首跑自动 npm install）---
start "Werewolf Frontend :5173" cmd /k "cd frontend && (if not exist node_modules npm install) && npm run dev:spectate"

REM --- 等服务起来后自动打开浏览器（首次较慢，没开就手动刷新）---
timeout /t 8 >nul
start "" http://127.0.0.1:5173

echo.
echo   浏览器已尝试打开 http://127.0.0.1:5173
echo   用法：配置页里给每个座位选 provider/model，在对应 provider 栏填 API Key，开局观战。
echo   停止：运行 stop-spectate.bat，或直接关掉那两个新开的命令行窗口。
echo.
pause
