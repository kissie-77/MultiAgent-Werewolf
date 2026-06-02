# 角色卡 Schema 迁移报告

> **状态**：deprecated
> **说明**：一次性迁移记录（2026-06-01）；现行 Prompt 见 [strategy/DESIGN.md](../../strategy/DESIGN.md) per-role 小包。

## 迁移概况

- **迁移日期**: 2026-06-01
- **旧 schema**: `role_name` + `role_instruction` + `suggestion`（3 字段，自由文本）
- **新 schema**: `role_name` + `role_instruction` + `core_principles` + `phase_strategies` + `forbidden_actions` + `examples`（6 字段，结构化）
- **向后兼容**: `_render_legacy_suggestion()` 将新 schema 渲染为 `suggestion` 字段，旧代码无需改动

## 迁移状态

### 全部 22/22 角色已迁移

| # | 角色 | prompt_key | YAML 文件 | 状态 |
|---|------|-----------|-----------|------|
| 1 | 村民 | villager | villager.yaml | ✅ 已迁移 |
| 2 | 预言家 | prophet | prophet.yaml | ✅ 已迁移 |
| 3 | 女巫 | witch | witch.yaml | ✅ 已迁移 |
| 4 | 狼人 | wolf | wolf.yaml | ✅ 已迁移 |
| 5 | 狼王 | wolf_king | wolf_king.yaml | ✅ 已迁移 |
| 6 | 守卫 | guard | guard.yaml | ✅ 已迁移 |
| 7 | 猎人 | hunter | hunter.yaml | ✅ 已迁移 |
| 8 | 白狼 | white_wolf | white_wolf.yaml | ✅ 已迁移 |
| 9 | 狼美人 | wolf_beauty | wolf_beauty.yaml | ✅ 已迁移 |
| 10 | 守墓狼 | guardian_wolf | guardian_wolf.yaml | ✅ 已迁移 |
| 11 | 隐狼 | hidden_wolf | hidden_wolf.yaml | ✅ 已迁移 |
| 12 | 噩梦狼 | nightmare_wolf | nightmare_wolf.yaml | ✅ 已迁移 |
| 13 | 血月使徒 | blood_moon_apostle | blood_moon_apostle.yaml | ✅ 已迁移 |
| 14 | 白痴 | idiot | idiot.yaml | ✅ 已迁移 |
| 15 | 长老 | elder | elder.yaml | ✅ 已迁移 |
| 16 | 骑士 | knight | knight.yaml | ✅ 已迁移 |
| 17 | 魔术师 | magician | magician.yaml | ✅ 已迁移 |
| 18 | 丘比特 | cupid | cupid.yaml | ✅ 已迁移 |
| 19 | 乌鸦 | raven | raven.yaml | ✅ 已迁移 |
| 20 | 守墓人 | graveyard_keeper | graveyard_keeper.yaml | ✅ 已迁移 |
| 21 | 盗贼 | thief | thief.yaml | ✅ 已迁移 |
| 22 | 恋人 | lover | lover.yaml | ✅ 已迁移 |

## 新 Schema 结构

```yaml
role_name: 狼人                    # 角色名称
role_instruction: 你属于狼人阵营...  # 身份描述
core_principles:                   # 长期规则（list[str]）
  - 你的目标不是单纯活下去...
  - 白天不能只做防守...
  - 狼队整体收益高于个人表演...
phase_strategies:                  # 阶段策略（dict[str, str]）
  opening: 前期优先观察...
  counterclaim: 场上出现真神跳身份时...
  peaceful_night: 平安夜后优先推动...
  vote_closing: 如果今天推不出...
  endgame: 残局优先做轮次管理...
forbidden_actions:                 # 禁止项（list[str]）
  - 禁止整队复读同一条怀疑链。
  - 禁止白天全程只防守。
  - 禁止悍跳失败后第二天没有续接叙事。
examples:                          # 示例（list[str]）
  - 如果队友已经把某个好人打成焦点...
  - 夜里定刀前先判断目标价值...
```

## 向后兼容机制

`prompt_registry.py` 中的 `_render_legacy_suggestion(data)` 函数：
- 如果 YAML 中有旧格式 `suggestion` 字段，直接返回
- 如果没有，从 `core_principles` + `phase_strategies` + `forbidden_actions` + `examples` 拼接生成
- `suggestion` key 始终存在，`agent_base.md` 的 `{suggestion}` 占位符不需要改

## Registry 读取链路

`PromptRegistry.get_role_card()` 返回的 dict 包含：
- `role_name` — 字符串
- `role_instruction` — 字符串
- `suggestion` — 由 `_render_legacy_suggestion()` 生成的兼容字段
- `core_principles` — 换行分隔的字符串
- `phase_strategies` — 换行分隔的字符串（格式：`key: value`）
- `forbidden_actions` — 换行分隔的字符串
- `examples` — 换行分隔的字符串

## 兼容风险点

| 风险 | 状态 | 说明 |
|------|------|------|
| `PromptManager.build_prompt_key_strategy_prompt()` | ✅ 无风险 | 读取 `role_config["suggestion"]`，新 schema 兼容 |
| `agent_base.md` 模板 | ✅ 无风险 | `{suggestion}` 占位符不变 |
| `prompt_evolver.py` 的 `_append_to_role_suggestion()` | ⚠️ 需关注 | 当前追加到 `suggestion` 字段，新 schema 下会追加到旧格式文本而非结构化字段 |
| `role_prompts.py` 的 `_hydrate_role_prompts_from_registry()` | ✅ 无风险 | 读取 role_card dict，新 schema 兼容 |
| `variables.yaml` 的 `kind: role_card` | ✅ 无风险 | Registry 按 kind 路由，不需要改 |

## 测试覆盖

| 测试 | 文件 | 状态 |
|------|------|------|
| 所有 22 角色有结构化字段 | test_prompt_registry.py | ✅ 通过 |
| 结构化字段类型正确 | test_prompt_registry.py | ✅ 通过 |
| PromptManager 能为所有角色构建 prompt | test_prompt_registry.py | ✅ 通过 |
| `_coerce_text_list` / `_coerce_text_dict` 边界情况 | test_prompt_registry.py | ✅ 通过 |
| 扩展角色注册 | test_prompt_registry.py | ✅ 通过 |
| 结构化字段渲染到 prompt | test_prompt_registry.py | ✅ 通过 |

## 后续待做

1. **`prompt_evolver.py` 适配** — `_append_to_role_suggestion()` 需要改为追加到 `core_principles` 或 `forbidden_actions`，而不是追加到 `suggestion` 文本
2. **Proposal schema 升级** — 支持 `add_rule`、`update_rule`、`delete_rule`、`add_forbidden_rule`、`promote_quote_to_example` 操作
3. **Few-shot 示例增强** — `agent_base.md` 已加 2 个 few-shot，可以按角色扩展
