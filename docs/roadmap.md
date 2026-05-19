# Roadmap

## 当前迭代
- [x] 游戏引擎核心流程（异步化完成 → ADR-0003）
- [x] 多模型支持（OpenAI/Anthropic/DeepSeek/Ollama via AsyncOpenAI）
- [x] 20+ 角色系统
- [x] YAML 配置 + 自动按人数配角色
- [x] Demo 模式验证（DemoAgent 无 API 跑通）
- [x] 修复 AlphaWolf super() chain bug
- [ ] AgentScope 接入 → 待写 ADR
- [ ] 信息隔离层（ObservationBuilder 完整化）

## 下个迭代
- [ ] 结构化日志（JSON 事件流，供 Web 端订阅）
- [ ] Web 观战 UI（FastAPI + WebSocket）→ 待写 ADR
- [ ] 同一夜多角色 LLM 调用并发化（ADR-0003 留的 TODO）

## 想做但还没排期
- 评测与复盘体系（一局录像 + 复盘报告）
- 多策略对照实验（同模型不同 prompt）
- 模型胜率统计 dashboard
