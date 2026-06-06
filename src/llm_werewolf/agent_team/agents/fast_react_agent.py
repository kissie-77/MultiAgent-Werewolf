"""消除 agentscope 结构化决策后那次被丢弃的纯文本 round-trip（性能报告 ③）。

需要结构化输出、且模型同一步只吐 tool_use 不吐 text 时（doubao 必然如此），上游
ReActAgent.reply() 会再打一次 _reasoning 仅为产出文本，而游戏只读 Msg.metadata。
这里覆写 _reasoning：给该消息补一个空 TextBlock，使 reply() 现有的退出条件
（has_content_blocks("text")）在首轮即命中并 break，省掉第二次 HTTP。

守卫只在「需结构化 + 有 tool_use + 无 text」时触发，故普通文本调用、以及模型本就
同时吐 text 的调用都完全走基类原逻辑。
"""

from __future__ import annotations

from typing import Literal

from agentscope.agent import ReActAgent
from agentscope.message import Msg, TextBlock


class FastReActAgent(ReActAgent):
    """跳过结构化决策后被丢弃的第二次纯文本往返。"""

    async def _reasoning(
        self, tool_choice: Literal["auto", "none", "required"] | None = None
    ) -> Msg:
        msg = await super()._reasoning(tool_choice)
        if (
            self._required_structured_model is not None
            and isinstance(msg.content, list)
            and msg.has_content_blocks("tool_use")
            and not msg.has_content_blocks("text")
        ):
            msg.content.append(TextBlock(type="text", text=""))
        return msg
