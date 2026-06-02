# PostGame 产物地图

> **状态**：deprecated
> **替代文档**：[DESIGN.md](../../evaluation/DESIGN.md) §9
> **说明**：结论已合并进 DESIGN；本文仅备查，请勿再更新。

---

项目一局结束后会自动运行 `PostGame` 流水线，并生成一组复盘、评分、Skill、Coach 相关产物。

这份文档用于回答三个问题：

1. 当前 `PostGame` 会产出什么
2. 每个产物是干什么的
3. 哪些产物已经能用于答辩，哪些还缺“显式闭环证明”

## 一、总索引类

### `post_game_manifest.json`

作用：

- 整个 `PostGame` 流水线的总索引
- 记录本局上下文、步骤状态、产物列表

可以证明：

- 赛后流水线确实被触发了
- 这不是手工零散脚本，而是一条结构化流程

### `post_game_steps.json`

作用：

- 记录每一步是否成功、跳过还是失败
- 记录每一步关联的产物

可以证明：

- 流水线是“分步骤可追踪”的
- 出问题时可以定位具体卡在哪一步

## 二、情景记忆与事件复盘类

### `episodic_reports.json`

作用：

- 按玩家 POV 导出 episode 复盘数据
- 来源与运行时 `EpisodicMemory` 同源

包含内容：

- 每个玩家的 episode 数
- 每轮可见事件
- 关键事件
- 决策事件
- 单轮摘要

可以证明：

- 你们有情景记忆导出能力
- 运行时记忆和赛后复盘不是两套割裂系统

### `vote_swing_report.md`
### `vote_swing_summary.json`

作用：

- 分析投票意向变化
- 关注“谁影响了谁”

可以证明：

- 项目不是只看胜负
- 已经在分析说服与投票过程

### `camp_persuasion_report.md`
### `camp_persuasion_summary.json`

作用：

- 在 `vote_swing` 基础上加入阵营视角
- 分析说服行为是否对本阵营有利

可以证明：

- 你们开始在做“博弈质量”分析，而不仅仅是事件记录

## 三、日志视图与评分上下文类

### `views/`
### `views_manifest.json`

作用：

- 输出可视化/可浏览的日志视图材料

可以证明：

- 系统可观测性不是只有原始日志
- 复盘材料可被整理成人类可看的形式

### `views/score_contexts/`
### `views/score_contexts/manifest.json`

作用：

- 给评分、复盘、LLM replay 提供按维度隔离后的上下文材料

可以证明：

- 你们在控制复盘/评分时使用的证据来源
- 有意识避免不同通道信息混用

## 四、评分类

### `intention_scores.json`

作用：

- 评估投票意向相关表现

### `mvp_scores.json`

作用：

- 输出 MVP 与多维评分结果

### `benefit_scores.json`

作用：

- 汇总收益相关评分

可以共同证明：

- 你们不是只按“输赢”评估 Agent
- 已经具备多维评分能力

## 五、LLM 复盘与总报告类

### `post_game_analysis.json`
### `post_game_report.md`

作用：

- LLM 赛后复盘分析
- 产出人类可读的总结、建议或提示词方向

说明：

- 当 `skip_llm=True` 时可能不会完整产出

可以证明：

- 赛后复盘不只是规则统计，也有总结层分析

### `game_quality_report.md`
### `game_quality_report.json`

作用：

- 汇总本局整体质量
- 串联转折点、MVP、Prompt 建议、Skill 结果等

可以证明：

- 你们已经有“总览报告”层，而不是一堆散产物

## 六、Prompt 与 Skill / Coach 类

### `prompt_proposals.json`

作用：

- 提炼 Prompt 优化建议

可以证明：

- 项目具备把复盘结果反推到 Prompt 调优的能力

### `role_skills.json`

作用：

- 本局提取出的 Skill 列表

包含内容通常有：

- `skill_id`
- 角色
- 来源玩家
- 证据
- 质量门结果
- `skill_card`

可以证明：

- 你们已经能把对局经验结构化成 Skill 候选

### `skills/`

作用：

- 将 Skill 渲染为 Markdown 文件

可以证明：

- Skill 不只是内存对象，也有独立可审阅产物

### `coach_summary.json`

作用：

- Coach 层总结
- 统计 enrich 了多少 Skill
- 记录 episode 证据补全情况

可以证明：

- Coach 已经真实参与赛后链路
- 不只是概念设计，而是有实际产物输出

## 七、当前已经能用于答辩证明什么

你现在这套产物，已经足以证明下面这些能力：

1. 对局结束后有完整的 `PostGame` 流水线
2. 有情景记忆导出能力
3. 有说服/投票分析能力
4. 有多维评分能力
5. 有 Prompt 提案能力
6. 有 Skill 提炼能力
7. 有 Coach 层参与赛后处理

## 八、当前还缺什么“显式闭环证明”

虽然产物已经很多，但还缺一类特别关键的产物：

### 1. Skill 版本变化证明

目前还缺少非常显眼的：

- 本局新增了哪些 Skill
- 本局合并了哪些 Skill
- 哪些 Skill 权重变化了

### 2. 写回后使用证明

目前还缺少非常直观的：

- 下次对局是否真的使用了这些新 Skill
- 使用了哪几张

### 3. 前后效果对比证明

目前还缺少：

- 写回前后版本对比
- A/B 对比结果
- 是否真的带来更好的评分或胜率

## 九、结论

当前项目不是“没有复盘产物”，而是已经有一整套较完整的 `PostGame` 产物体系。

现在最值得继续补的，不是再多造一种复盘文件，而是补上：

- 版本变化
- 写回使用
- 前后效果对比

这样你们的系统就不只是“会复盘”，而是能更明确地证明：

**它会复盘、会提炼、会写回、还会形成可验证的策略演化闭环。**
