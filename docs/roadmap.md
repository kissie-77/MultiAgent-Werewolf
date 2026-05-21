# Roadmap

## 当前迭代
- [x] 游戏引擎核心流程（异步化完成 → ADR-0003）
- [x] 多模型支持（OpenAI/Anthropic/DeepSeek/Ollama via AsyncOpenAI）
- [x] 20+ 角色系统
- [x] YAML 配置 + 自动按人数配角色
- [x] Demo 模式验证（DemoAgent 无 API 跑通）
- [x] 修复 AlphaWolf super() chain bug
- [x] 离线游戏正确性评测第一版（`werewolf-eval` → ADR-0004）
- [x] AgentScope 接入（`adapter/agent.py` + Hub；ADR 待补简短说明）
- [x] 信息隔离层第一版（Event `visible_to` + MsgHub + 评测 checker）
- [ ] 核心重构收尾 → 见 [project-master-plan.md](./project-master-plan.md)

## 下个迭代
- [ ] 结构化日志（JSON 事件流，供 Web 端订阅）
- [ ] Web 观战 UI（FastAPI + WebSocket）→ 待写 ADR
- [ ] 同一夜多角色 LLM 调用并发化（ADR-0003 留的 TODO）

## 想做但还没排期
- Web 化复盘体系（一局录像时间线 + 可视化报告）
- 多策略对照实验（同模型不同 prompt）
- 模型胜率统计 dashboard
