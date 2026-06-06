"""WebHumanAgent：把每个决策点 await 给 HumanInputBroker（镜像 stdin 人类的归一化）。"""

from llm_werewolf.agent_team.agents.web_human_agent import WebHumanAgent


class _FakeBroker:
    """脚本化 broker：记录 request 入参，回放预设回复（不依赖真实 broker/SSE）。"""

    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.calls: list[dict] = []

    async def request(self, **kwargs) -> str:
        self.calls.append(kwargs)
        return self.reply


async def test_seat_decision_awaits_broker() -> None:
    broker = _FakeBroker("2")
    agent = WebHumanAgent(name="P1", seat=1, broker=broker)
    msg = "请只回复目标玩家的全局座位号\n可选目标:\n- 座位 2\n- 座位 3"
    out = await agent.get_response(msg)
    assert out == "2"
    assert broker.calls[0]["kind"] == "seat"
    assert broker.calls[0]["valid_targets"] == [2, 3]
    assert broker.calls[0]["prompt"] == msg


async def test_no_broker_returns_empty() -> None:
    agent = WebHumanAgent(name="P1", seat=1)
    assert await agent.get_response("任意") == ""
