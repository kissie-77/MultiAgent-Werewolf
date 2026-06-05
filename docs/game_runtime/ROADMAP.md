# Game Runtime 开发进度

> **模块**：game_runtime
> **状态**：active
> **最后更新**：2026-06-05（毒奶规则 + 女巫守卫测试）

## 总览

| 阶段 | 状态 | 说明 |
|------|------|------|
| 基础游戏引擎 | ✅ Done | GameEngine + Mixin 架构 |
| 角色系统 | ✅ Done | 狼人系、好人系、中立角色 |
| 状态管理 | ✅ Done | GameState + Player + 序列化 |
| 事件系统 | ✅ Done | 事件定义、可见性控制、格式化 |
| 投票系统 | ✅ Done | 投票、平票处理、PK 发言 |
| 警长选举 | ✅ Done | 警上发言、投票、平票重投 |
| 死亡处理 | ✅ Done | 死亡技能、死亡信息、死亡原因；**死亡链递归传播** |
| 胜负判定 | ✅ Done | VictoryChecker |
| 配置系统 | ✅ Done | GameConfig、预设、序列化 |
| 夜间调度 | ✅ Done | NightScheduler、超时处理 |
| 信念矩阵 | 🔄 In Progress | B1/B2/狼队 W 面板运行时接入 |
| 扩展角色规则完善 | ✅ Done | 狼美人魅惑跨轮状态修复；白狼**白天自爆** |
| 更多中立角色 | 📋 Planned | 乌鸦、吹笛者等 |
| 目录重组 | ✅ Done | `rules/` `interaction/` `scheduling/` `i18n/` `support/` 子包 |

## 已完成

- [x] GameEngine Mixin 架构（Day/Night/Voting/Sheriff/Death/Action）
- [x] 角色目录与注册系统（catalog.py + registry.py）
- [x] GameState 状态管理与序列化
- [x] 事件系统与可见性控制
- [x] 投票意向追踪与快照
- [x] 平票 PK 发言逻辑
- [x] 猎人/狼王死亡技能
- [x] 女巫解药/毒药逻辑
- [x] 守卫守护逻辑
- [x] 预言家查验逻辑
- [x] 扩展角色 catalog（AlphaWolf、WhiteWolf、WolfBeauty、BloodMoonApostle 等）
- [x] VictoryChecker 胜负判定
- [x] 游戏配置与预设系统
- [x] 夜间行动调度器
- [x] Agent 决策 observation 不暴露隐藏阵营存活数量
- [x] 白狼王白天发言自爆：`self_explode` → `skip_day_voting` 进黑夜
- [x] `setup_game`：`information_hub is None` fail-fast
- [x] `wolf_beauty_charmed` 跨轮状态清空（DAY_VOTING→NIGHT 重置）
- [x] 死亡链递归传播：魅惑死亡 → 情侣殉情；情侣殉情加入 `night_deaths` 使 `_handle_death_abilities` 正常触发
- [x] 6 项死亡链回归测试（`tests/game_runtime/test_death_chain.py`）
- [x] 女巫 / 守卫毒奶规则：同夜同救刀口仍死亡（`guard_witch_conflict`）
- [x] 11 项女巫守卫专项测试（`tests/game_runtime/test_witch_guard_logic.py`）
- [x] 目录重组：10 个根目录 `.py` 归入 5 个子包；`support/__init__` 惰性导出防循环依赖
- [x] 警长投票使用独立 `SHERIFF_VOTE` action phase，避免串入夜间角色行动 prompt
- [x] 引擎驱动观战所需信号：`engine.step()` 与 `play_game()` 行为对齐（可被 API 逐阶段泵）、补全 `phase_changed`（警长竞选/投票/结束）、子阶段信号、5 个技能结构化事件（白狼/狼美人/噩梦/守卫狼→`guardian_wolf_guard`/乌鸦）、拓宽 `role_data`（Hunter/Seer）

## 进行中

- [ ] 信念矩阵（B1/B2/狼队 W 面板）与 strategy 运行时对齐

## 计划中

- [ ] 更多中立角色（乌鸦、吹笛者等）
- [ ] 自定义角色扩展机制
- [ ] 游戏规则热加载
- [ ] 多语言支持完善

## 变更记录

| 日期 | 摘要 |
|------|------|
| 2026-06-05 | `GameConfig.role_shuffle_seed`：`setup_game` 角色洗牌可复现；评测/CLI 透传种子 |
| 2026-06-05 | `_handle_vote_tie` 改为迭代收尾（`_append_vote_tie_no_elimination`），消除自我递归 |
| 2026-06-05 | `phase_interaction` 超时匹配改用 `GamePhase` 枚举 |
| 2026-06-05 | 目录重组：rules/interaction/scheduling/i18n/support 子包；README 目录结构图 |
| 2026-06-05 | 毒奶规则（守卫+女巫同救仍死亡）；女巫/守卫 11 项专项测试 |
| 2026-06-05 | 修复 wolf_beauty_charmed 跨轮状态泄漏；死亡链递归传播（魅惑→情侣）；6 项回归测试 |
| 2026-06-04 | 引擎信号补全（供引擎驱动观战）：step()↔play_game() 对齐、phase_changed 补全、子阶段信号、5 技能结构化事件、role_data 拓宽 |
| 2026-06-02 | 白狼白天自爆进黑夜；setup_game hub fail-fast；文档与 agent_team/strategy 批次对齐 |
| 2026-06-02 | 人机混战信息隔离：observation 隐藏阵营存活数；警长投票 prompt 阶段修正 |
| 2026-05-24 | 初始化 game_runtime 三件套文档 |
| 2026-05-23 | 修复 PK 发言方法名冲突（sheriff_election vs voting_phase） |
| 2026-05-22 | 添加狼美人魅惑状态字段 |
| 2026-05-21 | 完善投票意向追踪与快照功能 |

状态图例：`✅ Done` · `🔄 In Progress` · `📋 Planned` · `⏸ Blocked`
