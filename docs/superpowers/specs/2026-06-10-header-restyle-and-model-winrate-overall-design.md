# 对局顶栏换皮 + 模型总胜率对比页 — 设计文档

> 日期:2026-06-10
> 分支:integrate/seatui-fix-godrole
> 状态:已与用户确认设计,待实施

## 背景

1. 当前对局界面顶栏(`frontend/src/components/UnifiedGameHeader.tsx`)右侧为鎏金石雕风控件(ALIVE/DEAD 金框计数、金框图标按钮)。用户希望按设计原型 `D:\AI_werewolf\werewolf_6_6\front_end (2)`(AI Studio 木刻暗黑风原型,内含旧版 `TopHeader.tsx`)的**外观**改造,只参考外观、不改功能。
2. 模型排行榜(`/models`)目前把「模型+角色」条目与「仅模型」聚合条目混在同一张表里(如 "GPT-5.5(守卫)" 与 "GPT-5.5" 并列)。用户希望新增一个页面,**不区分角色**直接对比每个模型的胜率。

## 需求确认(用户已答复)

- 需求 1 范围:**仅对局顶栏**(UnifiedGameHeader),不动其余对局界面与内容页。
- 需求 2 形态:**独立新页面** `/models/overall`,横向条形图对比,模型页加入口。
- 两项均采用推荐方案:顶栏原地换皮;胜率页纯前端实现,不改后端。

## 设计 1:对局顶栏换皮(UnifiedGameHeader)

**原则:功能零变化,只换外观。** 实况台词逻辑(actorInfo/cueFallback)、音量控件(AudioControls)、退出二次确认、座位视角信息隐藏规则全部原样保留。

参考视觉语言(来自 front_end (2) `TopHeader.tsx`):纤细紧凑(高度约 48px)、`bg-black/45 backdrop-blur-md`、细 zinc 描边(`border-zinc-800/900` 系)、文字按钮、石碑梯形阶段牌(`clip-path: polygon(0 0, 100% 0, 95% 100%, 5% 100%)`)。

### 布局(左 / 中 / 右)

- **左侧**:红色双竖条 logo(`w-1.5 h-5` + `w-0.5 h-5`,色值取标准 red-600/red-800;参考代码的 `red-650` 非标准色)+ 两行小字「狼人杀神圣审判厅」/ 状态行(`gameState.winner ? "已结案" : "对决轮转中"`),同参考版。替换现有大号日月圆形图标 + 大号日期文字。
- **中央**:石碑梯形框,内含:
  - 小号圆形日/月图标(7×7,夜=红描边红光 Moon,日=黄描边黄光 Sun,候场=Hourglass);
  - 「夜暮降临 • 第 N 晚」/「曙光黎明 • 第 N 日」/「候场集结」serif 粗体小字;
  - 阶段副标(现有 `phaseSubText`,金色 mono 小字大写);
  - 竖分隔条;
  - **现有实况台词**(玩家N号 正在…… + 呼吸点 BreathingDots),即现有 actorInfo/cueFallback 文案装进石碑框,替换现有独立的黄框台词牌。
- **右侧**(全部改为参考版文字按钮风格):
  - 「返回上一级」:zinc 细描边文字钮(`border-zinc-800 bg-zinc-950/30 text-zinc-400` hover 亮);
  - 「回到主界面」:靛蓝描边蓝字 + Home 图标(`border-indigo-900/60 bg-indigo-950/30 text-blue-200`);
  - 存活统计两行右对齐小字:「存活已降临: N名」(黄色)/「已被撕咬放逐: N名」(红色),替换 ALIVE/DEAD 金框;
  - 「退出游戏」:暗红描边(`border-red-900/60 bg-red-950/30 text-red-100`)+ LogOut 图标;二次确认态红底白字脉冲(沿用现有 confirmExit 状态机与文案「二次点击确认退出」);
  - **音量控件 AudioControls 保留**,外观微调(细描边、压扁尺寸)融入细线风格;
  - 按钮点击音效(soundManager.playUi)全部保留。

### 不做的事

- 参考版的 30 秒倒计时器、自动播放暂停按钮**不加**(当前应用无此功能,只参考外观)。
- 不改 `stageBadge` / `liveCue` / store 逻辑,不动其他对局组件(SeatCommandDock、RightPanelColumn 等)。
- 不改内容页(ContentPageLayout 导航本就已是参考风格)。

## 设计 2:模型总胜率对比页(/models/overall)

### 数据

- 复用 `ApiClient.getModelsPageData()`(`/api/v1/pages/models` → `modelsMap.ts` 映射后的 `ModelUsageStat[]`,`win_rate` 已是 0-100 百分比)。
- 过滤 `role_name == null/空` 的聚合条目(后端 `aggregate_model_usage` 已按 (model, role) 与 model 两个粒度产出,无需改后端)。

### 页面

- 新路由 `/models/overall`(AppRouter 中 AppLayout 包裹),新文件 `frontend/src/pages/ModelOverallPage.tsx`,视觉风格与 ModelsPage 一致(zinc-950 卡片、amber 强调、mono 小字)。
- 每行:模型名 + 横向胜率条(amber 渐变,宽度 = win_rate%)+ 胜率 % + 对局数 + 平均 MVP。
- 默认按胜率降序;提供「按胜率 / 按对局数」排序切换。
- `run_count < 3` 的行加灰色「样本少」小标。
- 加载/错误/空态复用 `PageLoadState`。

### 入口

- `ModelsPage` 排行榜标题栏(「全网出战模型总序」一行)加「总胜率对比 →」链接按钮,跳 `/models/overall`。

### 纯函数与测试

- 过滤+排序逻辑抽成纯函数(如 `frontend/src/utils/modelOverall.ts` 的 `selectOverallStats(models, sortKey)`),vitest 单测覆盖:过滤掉带角色条目、胜率/对局数排序、空数组。
- 顶栏为纯样式改动:以现有测试套件不红 + 实跑(Playwright)截图验证布局。

## 影响文件清单

| 文件 | 变更 |
|------|------|
| `frontend/src/components/UnifiedGameHeader.tsx` | 重排布局、替换样式类(逻辑不动) |
| `frontend/src/components/AudioControls.tsx` | 外观微调(细描边、紧凑) |
| `frontend/src/pages/ModelOverallPage.tsx` | 新增 |
| `frontend/src/utils/modelOverall.ts` | 新增(纯函数) |
| `frontend/src/utils/modelOverall.test.ts` | 新增(vitest) |
| `frontend/src/components/AppRouter.tsx` | 加 `/models/overall` 路由 |
| `frontend/src/pages/ModelsPage.tsx` | 标题栏加入口按钮 |

## 验收标准

1. 对局顶栏视觉与 front_end (2) 顶栏风格一致(细线、文字按钮、石碑框),且实况台词、音量、二次确认退出等现有功能行为不变。
2. `/models/overall` 只显示不带角色的模型聚合条目,胜率条形对比正确,排序切换可用,样本少标记正确。
3. 前端现有测试全绿,新增纯函数单测通过。
