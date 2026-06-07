# LLM 供应商与 `.env` 模板

标准对局默认 **豆包**；同台竞技时按座位选择供应商，密钥统一从 `.env`（或设置 API）读取，**不按座位、不按对局复制变量**。

代码真源：`src/llm_werewolf/game_runtime/config/provider_registry.py`

## 支持的 8 个 `provider_id`

| provider_id | 名称 | 必填 env | 可选 env | 默认 base_url |
|-------------|------|----------|----------|---------------|
| `doubao` | 豆包 | `ARK_API_KEY`, `ARK_EP` | — | `https://ark.cn-beijing.volces.com/api/v3` |
| `deepseek` | DeepSeek | `DEEPSEEK_API_KEY` | `DEEPSEEK_MODEL` | `https://api.deepseek.com/v1` |
| `openai` | GPT | `OPENAI_API_KEY` | `OPENAI_MODEL` | `https://api.openai.com/v1` |
| `gemini` | Gemini | `GEMINI_API_KEY` | `GEMINI_MODEL` | Google OpenAI 兼容端点 |
| `claude` | Claude | `ANTHROPIC_API_KEY` | `ANTHROPIC_MODEL` | `https://api.anthropic.com/v1` |
| `kimi` | Kimi | `KIMI_API_KEY` | `KIMI_BASE_URL`, `KIMI_MODEL` | `https://api.moonshot.cn/v1` |
| `glm` | 智谱 GLM | `GLM_API_KEY` | `GLM_MODEL` | `https://open.bigmodel.cn/api/paas/v4` |
| `minimax` | MiniMax | `MINIMAX_API_KEY`, `MINIMAX_GROUP_ID` | `MINIMAX_MODEL` | `https://api.minimaxi.com/v1` |

## 命名约定

```text
{供应商}_API_KEY     # 密钥（敏感）
{供应商}_MODEL       # 模型名或部署 id（非敏感，可注释掉用默认）
豆包特例              # ARK_API_KEY + ARK_EP（与 standard-*.yaml 一致）
Kimi 代理             # KIMI_BASE_URL=https://www.vibeapi.cn/v1
```

## 如何使用

1. 复制模板：`cp .env.example .env`
2. **只填会用到的供应商**；未使用的块保持空或注释
3. 标准 6 人局至少配置：`ARK_API_KEY` + `ARK_EP`
4. 网页「密钥档案」当前写入：`deepseek/openai/gemini/claude/doubao` 的 Key；豆包 endpoint (`ARK_EP`) 与 `kimi/glm/minimax` 暂请手填 `.env`（后续 Phase 2 扩展设置 API）

## env 变多时的原则

| 做法 | 说明 |
|------|------|
| 每供应商固定槽位 | 最多 ~15 个 LLM 相关变量，不随座位数增长 |
| 稀疏填写 | 未用的供应商整段注释掉 |
| 不落盘明文 Key | `launch_roster.json` 只记 `api_key_env` 名字 |
| 后续可选 | 迁到 `configs/secrets/providers.json`（gitignore） |

## 同台竞技（规划中的开局形态）

```json
{
  "config_id": "standard-6p",
  "players": [
    { "provider": "doubao" },
    { "provider": "deepseek" },
    { "provider": "openai" },
    { "provider": "doubao" },
    { "provider": "kimi" },
    { "provider": "glm" }
  ]
}
```

后端将 `provider` 解析为 `base_url` + `api_key_env` + `model`/`model_env`，再合并进 roster（复用现有 `roster_customize`）。

## 历史别名

| 旧变量 | 新推荐 |
|--------|--------|
| `VIBE_API_KEY` | `KIMI_API_KEY` + `KIMI_BASE_URL=https://www.vibeapi.cn/v1` |
| `MOONSHOT_API_KEY` | `KIMI_API_KEY` |

`/ready` 健康检查仍识别 `VIBE_API_KEY` / `MOONSHOT_API_KEY` 等旧名，便于过渡。
