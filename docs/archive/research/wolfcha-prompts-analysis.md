# Wolfcha 提示词系统深度分析

> **状态**：archived / reference  
> **最后更新**：2026-06-04  
> 项目地址: https://github.com/oil-oil/wolfcha  
> 目的: 提取 Wolfcha 提示词设计精华，为 MultiAgent-Werewolf 项目提供借鉴方向

---

## 一、整体架构

### 1.1 三层提示词结构

Wolfcha 采用 **System → User → Response** 三层结构，每层职责明确：

```
┌─────────────────────────────────────────────────┐
│  System Prompt (角色身份 + 规则 + 指导)           │
│  ├─ Cacheable 部分（静态，可缓存）                │
│  └─ Dynamic 部分（动态，每局变化）                │
├─────────────────────────────────────────────────┤
│  User Prompt (游戏状态 + 历史记录 + 当前任务)     │
│  ├─ <current_status>  当前局势                   │
│  ├─ <game_state>      结构化状态                 │
│  ├─ <alive_players>   存活玩家列表               │
│  ├─ <history>         历史 transcript            │
│  ├─ <todayTranscript> 今日讨论记录               │
│  └─ <selfSpeech>      自己已说的话               │
├─────────────────────────────────────────────────┤
│  Response Format (JSON 结构化输出)               │
│  └─ 严格 JSON，无代码块，无多余文字              │
└─────────────────────────────────────────────────┘
```

### 1.2 提示词组装流程

```
PhaseManager.getPrompt(phase, context, player)
    │
    ├── GamePhase.getPrompt(context, player)
    │       │
    │       ├── buildGameContext(state, player)     ← 游戏状态上下文
    │       ├── buildPersonaSection(player)          ← 人设配置
    │       ├── buildTodayTranscript(state)          ← 历史 transcript
    │       ├── buildFocusAngle(state, player)       ← 视角提示
    │       └── buildSystemTextFromParts(parts)      ← 组装 system prompt
    │
    └── PromptResult { system, user, systemParts }
```

---

## 二、System Prompt 设计

### 2.1 缓存拆分策略（核心亮点）

Wolfcha 将 system prompt 拆分为 **cacheable** 和 **dynamic** 两部分，利用 Anthropic prompt caching 降低成本：

```typescript
interface SystemPromptPart {
  text: string;
  cacheable?: boolean;    // 是否可缓存
  ttl?: "1h";             // 缓存过期时间
}

// 实际使用示例（DaySpeechPhase）
const systemParts: SystemPromptPart[] = [
  { text: baseCacheable, cacheable: true, ttl: "1h" },      // 身份+角色+胜利条件
  { text: taskSection },                                     // 当前任务（动态）
  ...(focusAngle ? [{ text: focusAngle }] : []),             // 视角提示（动态）
  { text: guidelinesSection, cacheable: true, ttl: "1h" },   // 发言规则（静态）
];
```

**缓存断点设计**：
- 最多 4 个 cacheable 部分（`cacheCount < 4`）
- 静态部分放前面，动态部分放后面
- 缓存断点在最后一个 cacheable 部分之后

### 2.2 各角色 System Prompt 模板

#### 白天发言（DaySpeech）

```
【身份】
你是 {seat}号「{name}」
身份: {role}

【场景】
这是一个线上狼人杀游戏，玩家通过打字交流。

{winCondition}

{persona}

【当前处境】
你正在参与一局实时狼人杀。你不是旁观解说，也不是裁判。
你只知道自己视角内的信息。你有自己的性格、记忆、阵营目标和当下压力。
现在轮到你发言。{taskLine}
{campaignRequirements}

【底线规则】
- 只基于本局实际信息发言，严禁编造不存在的发言、投票、查验或死亡。
- 只讨论当前存活玩家；涉及已出局玩家时只引用公开事实。
- 第一个发言不要引用"前面"的话。
- 时间线约束：昨夜刀口在今天白天发言前已确定，禁止把今天的上警/跳身份/发言当作昨夜被刀的直接原因。
- 用"X号"称呼玩家。
- 严禁职业相关类比、行业术语和场外经历，只说狼人杀桌上的话。

【发言方式】
你可以坦诚、含糊、试探、反驳、带节奏、保护别人、隐藏信息，或者暂时保留判断。
你的发言不需要覆盖所有玩家，也不需要显得完美。
只说你此刻会在桌上说的话。
可以只说一句，也可以分成几条消息；如果你的玩家心智适合，偶尔可以有很短的反应、小动作或 emoji，但不要每轮都装饰。

【输出格式】
返回 JSON 字符串数组，每个元素是一条消息气泡。
```

#### 预言家夜间（Seer Night）

```
【身份】
你是 {seat}号「{name}」
身份: {role}

{winCondition}

【预言家技能】
每晚可查验一名玩家的身份（狼人/好人）。查验结果只有你知道，可选择公开或隐藏。

【任务】
选择一名玩家查验身份。
{checkedLine}

可选: {options}
```

#### 狼人夜间（Wolf Night）

```
【身份】
你是 {seat}号「{name}」
身份: {role}

{winCondition}

【狼人技能】
每晚狼人集体决定击杀一名玩家。可以选择击杀好人、队友（自刀）或不选（空刀）。

【任务】
选择一名玩家击杀。
{teammateVotesSection}

可选: {options}
```

#### 女巫夜间（Witch Night）

```
【身份】
你是 {seat}号「{name}」
身份: {role}

{winCondition}

【女巫技能】
拥有一瓶解药（救人）和一瓶毒药（杀人），全局各一瓶。

【重要规则】
- 解药可救被狼人杀害的玩家（包括自救）
- 毒药可毒杀任意玩家（通常用于确认的狼人）
- 每晚最多用一瓶药
- 若守卫和女巫同时救同一人（毒奶），该玩家仍会死亡

【药水状态】
解药: {healStatus} | 毒药: {poisonStatus}

【今晚情况】
{tonightInfo}

【任务】
决定是否使用药水。
{saveLine}
{poisonLine}
- 可以不使用药水

可毒目标: {poisonTargets}
```

#### 守卫夜间（Guard Night）

```
【身份】
你是 {seat}号「{name}」
身份: {role}

{winCondition}

【守卫技能】
每晚可保护一名玩家不被狼人杀害。守护成功则刀口存活。

【重要规则】
- 不能连续两晚保护同一人
- 可以保护自己
- 若守卫和女巫同时救同一人（毒奶），该玩家仍会死亡

【任务】
选择一名玩家保护。

可选: {options}
{lastTargetLine}
```

#### 投票阶段（Vote）

```
【身份】
你是 {seat}号「{name}」
身份: {role}

{winCondition}

【投票规则】
每位玩家投票选择一名嫌疑人处决。得票最多者出局。平票则进入 PK 发言后重新投票。

【任务】
选择一名玩家处决。必须基于你的阵营目标、公开查验、身份声明、对跳关系和归票信息判断。
- 如果你是预言家，且你确认的狼人仍然可投，通常应优先投出该狼人。
- 如果你是好人阵营，不能无视单边预言家的查验、警长/可信玩家的归票、以及明确对跳关系。
- 如果你是狼人阵营，可以伪装站边，但不要因为格式或随机性做出明显自爆式选择。

可选: {options}
```

#### 猎人开枪（Hunter Shoot）

```
【身份】
你是 {seat}号「{name}」
身份: {role}

{winCondition}

【猎人技能】
被投票放逐或被狼人击杀时可开枪带走一名玩家；被女巫毒杀时无法开枪。开枪即时生效，无法撤回。

【任务】
选择是否开枪。

可选: {options}
```

#### 白狼王自爆（WhiteWolfKing Boom）

```
【身份】
你是 {seat}号「{name}」
身份: {role}

{winCondition}

【白狼王自爆技能】
你可以选择在白天自爆。自爆时可带走一名存活的玩家（对方无遗言），自爆后直接进入黑夜，跳过投票。

【任务】
根据当前局势，决定是否自爆。如果自爆，只能从存活玩家里选择目标。

存活玩家: {options}
```

#### 警徽竞选（Badge）

```
【身份】
你是 {seat}号「{name}」
身份: {role}

{winCondition}

{persona}

【警徽竞选说明】
警长拥有 1.5 票投票权，死亡时可移交警徽给信任的玩家。警长负责归票和引导讨论方向。

【任务】
现在是警徽竞选报名环节。请根据当前局势决定是否报名竞选警长。

【输出格式】
只输出单个数字：1 表示报名，0 表示不报名
不要解释，不要输出多余文字，不要代码块
```

---

## 三、User Prompt 设计

### 3.1 游戏状态上下文（buildGameContext）

采用 **XML 标签** 组织结构化信息，层次清晰：

```xml
<your_seer_checks>
【你的查验记录】
  第1夜 → 3号Alice = 🐺 狼人
  第2夜 → 5号Bob = ✓ 好人
</your_seer_checks>

<current_status>
第2天 白天 | 你是 1号「Player1」
</current_status>

<game_state>
day: 2
phase: 白天
you: {seat: 1, name: Player1}
total_seats: 10
alive: [1, 2, 3, 5, 6, 7, 8, 9, 10]
dead: [{seat: 4, name: Eve, day: 1, cause: 死亡}]
sheriff: 3
alive_count: 9
</game_state>

<alive_players>
  - 1号 Player1（你）
  - 2号 Bob
  - 3号 Charlie
  ...
</alive_players>

<rules>
- 狼人不能刀队友（除非自刀战术）
- 第一天警徽竞选在死亡公布前进行
- 同一天内，不能用白天信息推断昨夜刀口原因
</rules>

<vote_intentions>
【投票意向记录】（仅记录，不代表最终投票）
- 3号 Charlie 想投 5号
</vote_intentions>
```

### 3.2 历史 Transcript（buildPastDaysTranscript）

完整保留历史对话，按天分组：

```xml
<history>
第1天[夜晚出局: 4号Eve | 投票出局: 7号Henry (5.0票)]
系统: 进入警徽竞选报名环节
系统: 进入警徽竞选发言
1号 Player1: 我是预言家，昨晚验了3号是金水...
2号 Bob: 我怀疑5号，发言太划水了
3号 Charlie: 我是好人，暂时信1号
...

第2天[平安夜]
系统: 天亮了，昨晚是平安夜
系统: 进入发言阶段
1号 Player1: 昨天3号是金水，今天继续验5号
...
</history>
```

### 3.3 今日讨论记录（buildTodayTranscript）

当前天的发言记录，排除自己：

```
【本日讨论记录】
1号 Player1: 我是预言家，昨晚验了3号是金水
2号 Bob: 我怀疑5号，发言太划水了
3号 Charlie: 我是好人，暂时信1号
...

【你本日已说过的话】
（无）/ 1号 Player1: 我是预言家...
```

### 3.4 视角提示（buildFocusAngle）⭐ 创新设计

为每个玩家生成**独特的思考角度**，避免 AI 发言同质化：

```xml
<focus_angle>
【你的视角】
- 你被2号、5号点名提到了，可以考虑是否回应
- 你和出局的玩家座位相邻，可以从这个角度聊一句
- 你是警长，你的发言会影响别人，可以自然给出你的方向
- 昨天3号、7号和你投了同一个目标，可以想想这件事要不要提
- 你是第一个发言，没有人可以参考，可以先抛出一个起手判断
</focus_angle>
```

**生成逻辑**（最多选 2 条）：
1. **被点名**：如果其他玩家提到了你，提示回应
2. **相邻死者**：如果死者座位相邻，提示从空间角度分析
3. **警徽相关**：警长/非警长不同提示
4. **投票模式**：昨天谁和你投了同一目标
5. **发言顺序**：第一个发言 vs 最后一个发言的不同提示

---

## 四、人设系统（Persona）

### 4.1 人设配置结构

```typescript
interface Persona {
  voiceRules: string[];           // 发言风格规则
  basicInfo?: string;             // 基本信息（可选）
  werewolfExperience?: string;    // 狼人杀理解水平
  vocabularyStyle?: string;       // 词汇习惯
  reasoningStyle?: string;        // 推理方式
  speechLengthHabit?: string;     // 发言长短习惯
  pressureStyle?: string;         // 压力反应
  uncertaintyStyle?: string;      // 不确定性表达
  mistakePattern?: string;        // 常见误判模式
  wolfDeceptionStyle?: string;    // 拿狼伪装风格
}
```

### 4.2 人设注入方式

```
【身份】
你是 1号「Player1」
身份: 预言家

【胜利条件】
好人阵营胜利条件：...

【你的玩家配置】
发言风格: 简洁直接，喜欢用数据说话
风险偏好: 平衡

【隐藏沟通画像】（不向其他玩家明说）
- 狼人杀理解：中等偏上，能识别基本狼坑
- 词汇习惯：喜欢用"我觉得"、"可能"等不确定词汇
- 推理方式：偏直觉型，不太喜欢长篇逻辑
- 发言长短：中等，3-5句话
- 压力反应：被质疑时会 defensive
- 不确定性：喜欢表达不确定，不轻易下结论
- 常见误判：容易被带节奏
- 拿狼伪装：喜欢装好人，不太会跳身份

【隐藏玩家心智】（稳定的心智模型）
- 胆量：中等
- 记忆偏好：短期记忆好，长期记忆差
- 怀疑阈值：低，容易怀疑别人
- 自保倾向：高，优先保护自己
- 逻辑水平：中等
- 桌面存在感：中等
```

---

## 五、输出格式设计

### 5.1 白天发言 → JSON 数组

```json
["我是预言家，昨晚验了3号是金水。", "今天重点听5号发言。"]
```

### 5.2 夜间行动 → JSON 对象

```json
// 预言家查验
{"seat": 5}

// 狼人击杀
{"seat": 3}

// 女巫行动
{"action": "save"}
{"action": "poison", "target": 5}
{"action": "pass"}

// 守卫守护
{"seat": 2}

// 投票
{"seat": 5, "reason": "发言划水，身份不明"}

// 猎人开枪
{"action": "shoot", "target": 3}
{"action": "pass"}

// 白狼王自爆
{"action": "boom", "target": 2}
{"action": "pass"}

// 警徽竞选报名
1 或 0（纯数字）
```

---

## 六、Prompt 缓存实现细节

### 6.1 缓存构建函数

```typescript
export function buildCachedSystemMessageFromParts(
  parts: SystemPromptPart[] | undefined,
  fallbackSystem: string,
  useCache: boolean = true
): LLMMessage {
  // 最多 4 个缓存部分
  let cacheCount = 0;
  const contentParts = [];

  parts.forEach((part) => {
    const cacheable = part.cacheable === true;
    const allowCache = cacheable && cacheCount < 4;
    const cache_control = allowCache
      ? { type: "ephemeral", ...(part.ttl === "1h" ? { ttl: "1h" } : {}) }
      : undefined;

    if (allowCache) cacheCount += 1;

    contentParts.push({
      type: "text",
      text: part.text.trim(),
      ...(cache_control ? { cache_control } : {}),
    });
  });

  return { role: "system", content: contentParts };
}
```

### 6.2 缓存命中策略

| 部分 | 是否缓存 | 原因 |
|------|---------|------|
| 身份+角色+胜利条件 | ✅ 缓存 | 整局不变 |
| 发言规则/底线 | ✅ 缓存 | 全局通用 |
| 当前任务 | ❌ 不缓存 | 每轮变化 |
| 视角提示 | ❌ 不缓存 | 每人不同 |
| 游戏状态上下文 | ❌ 不缓存 | 每局变化 |

---

## 七、对 MultiAgent-Werewolf 的借鉴点

### 7.1 高优先级借鉴

#### ① 视角提示系统（buildFocusAngle）

**价值**：解决 AI 发言同质化问题，让每个玩家有独特思考角度

**实现建议**：
```python
def build_focus_angle(state: GameState, player: Player) -> str:
    hints = []
    
    # 1. 被点名
    mentioned_by = get_mentioned_by(state, player)
    if mentioned_by:
        hints.append(f"你被{mentioned_by}点名了，可以考虑是否回应")
    
    # 2. 相邻死者
    if is_adjacent_to_dead(state, player):
        hints.append("你和出局的玩家座位相邻，可以从这个角度聊一句")
    
    # 3. 发言顺序
    if is_first_speaker(state, player):
        hints.append("你是第一个发言，可以先抛出一个起手判断")
    elif is_last_speaker(state, player):
        hints.append("你是最后一个发言，可以挑你最在意的一点回应")
    
    # 最多选 2 条
    selected = hints[:2]
    return f"\n【你的视角】\n" + "\n".join(f"- {h}" for h in selected)
```

#### ② Prompt 缓存拆分

**价值**：降低 LLM 调用成本 50-80%

**实现建议**：
```python
@dataclass
class SystemPromptPart:
    text: str
    cacheable: bool = False
    ttl: str | None = None

def build_system_prompt(parts: list[SystemPromptPart]) -> list[dict]:
    content = []
    cache_count = 0
    
    for part in parts:
        if part.cacheable and cache_count < 4:
            cache_count += 1
            content.append({
                "type": "text",
                "text": part.text,
                "cache_control": {"type": "ephemeral"}
            })
        else:
            content.append({
                "type": "text",
                "text": part.text
            })
    
    return [{"role": "system", "content": content}]
```

#### ③ XML 标签组织上下文

**价值**：结构化信息，LLM 更容易理解

**实现建议**：
```python
def build_game_context(state, player):
    return f"""
<current_status>
第{state.day}天 {state.phase} | 你是 {player.seat}号「{player.name}」
</current_status>

<game_state>
day: {state.day}
phase: {state.phase}
you: {{seat: {player.seat}, name: {player.name}}}
alive: [{alive_seats}]
dead: [{dead_info}]
sheriff: {sheriff_seat}
</game_state>

<alive_players>
{alive_players_list}
</alive_players>
"""
```

### 7.2 中优先级借鉴

#### ④ Transcript 历史记录组织

**当前问题**：记忆系统可能过于复杂，Wolfcha 用简单的 transcript 方式效果很好

**借鉴**：
- 按天分组历史记录
- 每天开头有事件摘要（死亡、投票等）
- 保留完整发言记录，不裁剪

#### ⑤ 人设系统（Persona）

**当前问题**：玩家角色可能缺乏个性化

**借鉴**：
- 为每个 AI 玩家生成独特的沟通画像
- 隐藏沟通画像（不向其他玩家明说）
- 隐藏玩家心智（稳定的心智模型）

#### ⑥ 发言顺序提示

**当前问题**：AI 可能不知道自己是第几个发言

**借鉴**：
```
【发言顺序】
你是第3/8个发言。已发言: 1号、2号；未发言: 4号、5号、6号、7号、8号。
```

### 7.3 低优先级借鉴

#### ⑦ 每日总结（Daily Summary）

Wolfcha 每天结束后生成 bullet-point 总结，压缩上下文：

```
第1天总结:
- 1号跳预言家，给3号发金水
- 5号被投票出局（5票）
- 4号夜晚死亡
- 警长: 3号
```

#### ⑧ 投票意向记录

记录玩家的投票意向（非最终投票），帮助分析：

```
<vote_intentions>
【投票意向记录】
- 3号 Charlie 想投 5号
- 7号 Henry 想投 2号
</vote_intentions>
```

---

## 八、提示词设计原则总结

从 Wolfcha 提取的核心设计原则：

| 原则 | 说明 | 示例 |
|------|------|------|
| **身份前置** | 座位号+名字+身份放在最前面 | `你是 1号「Player1」身份: 预言家` |
| **XML 标签** | 用 XML 标签组织结构化信息 | `<game_state>...</game_state>` |
| **时间线约束** | 明确禁止跨时间线推理 | `禁止把今天的上警当作昨夜被刀的原因` |
| **视角隔离** | 每个玩家只看到自己视角的信息 | `你只知道自己视角内的信息` |
| **输出格式** | 严格 JSON，无代码块，无多余文字 | `{"seat": 5}` |
| **缓存拆分** | 静态部分缓存，动态部分不缓存 | `cacheable: true` |
| **视角提示** | 为每个玩家生成独特思考角度 | `你被2号点名了，可以考虑是否回应` |
| **人设隐藏** | 人设只用于塑造行为，不向其他玩家明说 | `这些信息只用于塑造你的狼人杀水平` |
| **发言顺序** | 明确告知发言顺序和已/未发言玩家 | `你是第3/8个发言` |
| **底线规则** | 明确禁止的行为 | `严禁编造不存在的发言、投票、查验或死亡` |

---

## 九、实施建议

### 9.1 快速实施（1-2 天）

1. **添加视角提示**：在白天发言 prompt 中加入 `build_focus_angle`
2. **优化输出格式**：统一使用 JSON 结构化输出
3. **添加发言顺序提示**：告知 AI 自己是第几个发言

### 9.2 中期实施（3-5 天）

1. **Prompt 缓存拆分**：将 system prompt 拆分为 cacheable + dynamic
2. **XML 标签组织**：用 XML 标签重构游戏状态上下文
3. **Transcript 历史记录**：按天分组组织历史对话

### 9.3 长期实施（1-2 周）

1. **人设系统**：为每个 AI 玩家生成独特的沟通画像和心智模型
2. **每日总结**：每天结束后生成 bullet-point 总结
3. **投票意向记录**：记录玩家的投票意向，帮助分析

---

## 十、与当前项目对比

| 维度 | MultiAgent-Werewolf | Wolfcha | 差距 |
|------|---------------------|---------|------|
| Prompt 缓存 | ❌ 无 | ✅ 支持 | 大 |
| 视角提示 | ❌ 无 | ✅ 有 | 大 |
| XML 标签 | ❌ 无 | ✅ 有 | 中 |
| Transcript | ✅ 有（复杂） | ✅ 有（简单） | 小 |
| 人设系统 | ❌ 无 | ✅ 有 | 大 |
| 发言顺序 | ❌ 无 | ✅ 有 | 中 |
| 输出格式 | ✅ Pydantic | ✅ JSON | 小 |
| 每日总结 | ❌ 无 | ✅ 有 | 中 |

**结论**：Wolfcha 的提示词系统在**个性化**和**成本控制**方面有明显优势，值得借鉴。核心差距在于视角提示、Prompt 缓存和人设系统。
