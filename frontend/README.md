# AI 狼人杀 · 前端（frontend）

基于 **React 19 + Three.js + Vite** 的狼人杀对局界面，自带一个 **Express + Gemini** 的临时后端（`server.ts`），开发时前后端跑在**同一个进程、同一个端口（3000）**。

> 本目录是 `MultiAgent-Werewolf` 仓库的前端子项目，与同级的 Python 项目（`../src`、`../pyproject.toml` 等）相互独立、互不影响。
> 后续计划：把 `server.ts` 里的对局逻辑移植到 Python 后端，前端改为对接它（接口路径见文末）。

---

## 环境要求

- **Node.js ≥ 18**（已在 v22 验证）
- npm（随 Node.js 一起安装）
- 可选：**Gemini API Key**（不配也能跑，AI 发言会退化为预设文案）

---

## 快速开始

```bash
# 1. 进入前端目录
cd D:/AI_werewolf/NewforFront/MultiAgent-Werewolf/frontend

# 2. 安装依赖（首次或依赖变动时）
npm install

# 3. 启动开发服务器
npm run dev
```

启动成功后控制台会打印：

```
[Werewolf Backend] Standing trial on port 3000
```

然后浏览器打开 **http://localhost:3000** 即可开始游戏。

> `npm run dev` 实际执行 `tsx server.ts`：用 Express 起后端，并以中间件模式内嵌 Vite 提供 React 前端——所以一条命令同时拉起前后端。

---

## 配置 Gemini（可选）

不配置时，AI 玩家会走预写好的发言逻辑，控制台会反复打印：

```
GEMINI_API_KEY is not defined. AI player speeches will fallback to pre-written logic.
```

要启用真正的 AI 发言，在本目录新建 `.env.local`（已被 `.gitignore` 忽略，不会提交）：

```ini
# .env.local
GEMINI_API_KEY="你的_Gemini_API_密钥"
```

保存后重启 `npm run dev` 生效。可参考 `.env.example`。

---

## 可用脚本

| 命令              | 作用                                                                 |
| ----------------- | -------------------------------------------------------------------- |
| `npm run dev`     | 开发模式：Express + Vite 中间件，端口 3000，改代码自动热更           |
| `npm run build`   | 构建：`vite build` 打包前端，再用 esbuild 把 `server.ts` 打成 `dist/server.cjs` |
| `npm run start`   | 生产模式：运行 `node dist/server.cjs`（需先 `build`，并设 `NODE_ENV=production`） |
| `npm run preview` | 用 Vite 预览生产构建产物                                             |
| `npm run lint`    | `tsc --noEmit` 仅做类型检查                                          |
| `npm run clean`   | 删除 `dist`、`server.js`                                             |

### 生产部署示例

```bash
npm run build

# Windows（PowerShell）
$env:NODE_ENV="production"; npm run start

# macOS / Linux / Git-Bash
NODE_ENV=production npm run start
```

> 生产模式下 `server.ts` 会从 `dist/` 提供已构建的静态资源，否则默认走开发模式。

---

## 常见问题

- **端口 3000 被占用**：先结束占用进程再启动。
  - 查看占用：`netstat -ano | findstr :3000`
  - 结束进程：`taskkill /F /PID <上一步查到的PID>`
- **`npm run dev` 报模块找不到**：先执行 `npm install`。
- **改了 `.env.local` 不生效**：环境变量只在启动时读取，需重启 `npm run dev`。

---

## 技术栈

- **框架**：React 19 + TypeScript
- **构建**：Vite 6 +（开发期）tsx 直跑 TS 服务端
- **3D**：Three.js + @react-three/fiber + @react-three/drei
- **状态管理**：Zustand
- **动画**：GSAP、motion
- **样式**：Tailwind CSS v4
- **后端（临时）**：Express + @google/genai（Gemini）

---

## 目录结构

```
frontend/
├── server.ts                # Express 后端 + Vite 中间件 + 全部对局逻辑（临时，后续迁往 Python）
├── index.html               # 页面入口
├── vite.config.ts           # Vite 配置
├── tsconfig.json
├── package.json
├── .env.example             # 环境变量示例
└── src/
    ├── main.tsx             # React 挂载入口
    ├── App.tsx              # 顶层布局：开局界面 / 对局界面切换
    ├── store.ts             # Zustand 全局状态 + 所有 /api 请求封装
    ├── types.ts             # GameState / Player 等类型
    ├── index.css
    └── components/
        ├── ThreeCanvas.tsx      # 3D 圆桌场景
        ├── GameSetup.tsx        # 开局设置（角色 / 人数 / 模式）
        ├── CardDeck.tsx         # 左侧玩家卡牌列表
        ├── TopHeader.tsx        # 顶部信息栏（天数 / 阶段）
        ├── SpeechConsole.tsx    # 发言日志时间线
        ├── ControlPanel.tsx     # 底部操作区（发言输入 / 自动推进）
        ├── SkillBar.tsx         # 技能 / 投票动作
        └── GameOverPanel.tsx    # 结算面板
```

---

## 前后端接口（供后续迁移到 Python 对接）

前端所有请求都在 `src/store.ts` 中，统一打到以下路径：

| 方法 + 路径               | 用途                                                                    |
| ------------------------- | ----------------------------------------------------------------------- |
| `GET /api/game/state`     | 拉取当前完整对局状态                                                     |
| `POST /api/game/reset`    | 开新局，body：`{ userRole, playerCount, gameMode, startImmediately }`    |
| `POST /api/game/action`   | 通用动作，靠 body 里的 `action` 字段区分（见下）                         |
| `POST /api/game/exit`     | 退出当前对局                                                             |

`/api/game/action` 支持的 `action`（body 形如 `{ action, targetId?, text?, ... }`）：

`SPEECH_SUBMIT`（提交玩家发言）、`USER_VOTE`（投票）、`SIMULATE_NEXT_SPEAKER`（推进下一位 AI 发言）、`NIGHT_KILL`（狼刀）、`NIGHT_INSPECT`（预言家查验）、`NIGHT_SAVED_OR_POISON`（女巫救/毒）、`HUNTER_SHOOT`（猎人开枪）、`TRANSITION_TO_DEBATE`（进入白天辩论）。

所有接口都返回最新的完整 `GameState`（结构见 `src/types.ts`），前端据此整屏刷新。
