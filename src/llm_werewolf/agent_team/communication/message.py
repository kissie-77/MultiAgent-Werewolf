"""LLMWerewolf 字符串与 AgentScope Msg 格式之间的消息适配器。

.. deprecated::
    对局内消息请优先使用 InformationHub。Msg metadata 上的 ``visible_to``
    未接入引擎事件日志；仅保留供 AgentScope Agent 辅助使用。
"""

from typing import Literal
from datetime import datetime
from collections.abc import Sequence

import shortuuid

from llm_werewolf.game_runtime.types.enums import GamePhase


class ContentBlock:
    """多模态消息的内容块。"""

    @staticmethod
    def text(text: str) -> dict:
        """创建文本块。"""
        return {"type": "text", "text": text}

    @staticmethod
    def tool_use(name: str, input_data: dict) -> dict:
        """创建 tool_use 块。"""
        return {"type": "tool_use", "name": name, "input": input_data}

    @staticmethod
    def tool_result(output: str) -> dict:
        """创建 tool_result 块。"""
        return {"type": "tool_result", "output": output}


class Msg:
    """与 AgentScope 格式兼容的消息对象。

    轻量实现，镜像 AgentScope 的 Msg 类，无需完整 AgentScope 依赖。
    """

    def __init__(
        self,
        name: str,
        content: str | Sequence[dict],
        role: Literal["user", "assistant", "system"],
        metadata: dict | None = None,
        timestamp: str | None = None,
        invocation_id: str | None = None,
        id: str | None = None,
    ) -> None:
        """初始化 Msg 对象。

        Args:
            name: 消息发送者名称。
            content: 消息内容（字符串或 content 块）。
            role: 发送者角色（user/assistant/system）。
            metadata: 附加元数据。
            timestamp: 消息时间戳；为 None 时自动生成。
            invocation_id: 关联的 API 调用 ID。
        """
        self.name = name
        self.content = content
        self.role = role
        self.metadata = metadata or {}
        self.id = id or shortuuid.uuid()
        self.timestamp = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        self.invocation_id = invocation_id

    def to_dict(self) -> dict:
        """将消息转换为字典。"""
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Msg":
        """从字典创建 Msg。"""
        return cls(
            name=data["name"],
            content=data["content"],
            role=data["role"],
            metadata=data.get("metadata"),
            timestamp=data.get("timestamp"),
            invocation_id=data.get("invocation_id"),
            id=data.get("id"),
        )

    def get_text_content(self, separator: str = "\n") -> str | None:
        """从消息中提取文本内容。

        Args:
            separator: 拼接多个文本块的分隔符。

        Returns:
            文本内容；若无文本则 None。
        """
        if isinstance(self.content, str):
            return self.content

        if isinstance(self.content, list):
            texts = []
            for block in self.content:
                if isinstance(block, dict) and block.get("type") == "text":
                    texts.append(block.get("text", ""))
            return separator.join(texts) if texts else None

        return None

    def __repr__(self) -> str:
        """返回字符串表示。"""
        return (
            f"Msg(id='{self.id}', "
            f"name='{self.name}', "
            f"content={self.content!r}, "
            f"role='{self.role}')"
        )


class MessageAdapter:
    """LLMWerewolf 字符串与 AgentScope Msg 格式之间的适配器。

    提供双向转换：
    - str → Msg：将游戏引擎 prompt 转为 AgentScope 消息
    - Msg → str：将 AgentScope 回复转为游戏引擎格式
    """

    @staticmethod
    def str_to_msg(
        text: str,
        name: str = "Moderator",
        role: Literal["user", "assistant", "system"] = "system",
        metadata: dict | None = None,
    ) -> Msg:
        """将字符串 prompt 转为 AgentScope 兼容的 Msg。

        Args:
            text: 游戏引擎下发的 prompt 文本。
            name: 消息发送者名称。
            role: 发送者角色。
            metadata: 附加元数据。

        Returns:
            与 AgentScope 兼容的 Msg 对象。
        """
        return Msg(name=name, content=text, role=role, metadata=metadata or {})

    @staticmethod
    def msg_to_str(msg: Msg) -> str:
        """将 AgentScope Msg 转为游戏引擎使用的字符串。

        Args:
            msg: AgentScope 的 Msg 对象。

        Returns:
            消息的文本内容。
        """
        text = msg.get_text_content()
        return text if text is not None else ""

    @staticmethod
    def create_game_msg(
        text: str,
        name: str,
        role_type: Literal["user", "assistant", "system"] = "system",
        round_number: int | None = None,
        phase: str | GamePhase | None = None,
        player_id: str | None = None,
        role_name: str | None = None,
        action_type: str | None = None,
        visible_to: list[str] | None = None,
    ) -> Msg:
        """创建带元数据的游戏专用消息。

        Args:
            text: 消息内容。
            name: 发送者名称。
            role_type: 发送者角色。
            round_number: 当前回合数。
            phase: 当前游戏阶段。
            player_id: 目标玩家 ID（私密消息）。
            role_name: 发送者角色名。
            action_type: 行动类型（vote/kill/save 等）。
            visible_to: 可见此消息的玩家 ID 列表。

        Returns:
            带游戏元数据的 Msg 对象。
        """
        metadata: dict = {}

        if round_number is not None:
            metadata["round_number"] = round_number
        if phase is not None:
            metadata["phase"] = str(phase)
        if player_id is not None:
            metadata["player_id"] = player_id
        if role_name is not None:
            metadata["role_name"] = role_name
        if action_type is not None:
            metadata["action_type"] = action_type
        if visible_to is not None:
            metadata["visible_to"] = visible_to

        return Msg(name=name, content=text, role=role_type, metadata=metadata)

    @staticmethod
    def chat_history_to_msgs(history: list[dict]) -> list[Msg]:
        """将 OpenAI 格式聊天历史转为 Msg 列表。

        Args:
            history: 含 'role' 与 'content' 键的字典列表。

        Returns:
            Msg 对象列表。
        """
        msgs = []
        for item in history:
            role = item.get("role", "user")
            if role not in ("user", "assistant", "system"):
                role = "user"

            msgs.append(Msg(name="Player", content=item.get("content", ""), role=role))
        return msgs

    @staticmethod
    def msgs_to_chat_history(msgs: list[Msg]) -> list[dict]:
        """将 Msg 列表转为 OpenAI 格式聊天历史。

        Args:
            msgs: Msg 对象列表。

        Returns:
            含 'role' 与 'content' 键的字典列表。
        """
        history = []
        for msg in msgs:
            content = msg.get_text_content() or ""
            history.append({"role": msg.role, "content": content})
        return history

    @staticmethod
    def create_system_msg(text: str, name: str = "System") -> Msg:
        """创建 system 消息。

        Args:
            text: system 消息内容。
            name: 发送者名称。

        Returns:
            role='system' 的 Msg 对象。
        """
        return Msg(name=name, content=text, role="system")

    @staticmethod
    def create_user_msg(text: str, name: str = "Moderator") -> Msg:
        """创建 user 消息。

        Args:
            text: user 消息内容。
            name: 发送者名称。

        Returns:
            role='user' 的 Msg 对象。
        """
        return Msg(name=name, content=text, role="user")

    @staticmethod
    def create_assistant_msg(text: str, name: str = "Player") -> Msg:
        """创建 assistant 消息。

        Args:
            text: assistant 消息内容。
            name: 发送者名称。

        Returns:
            role='assistant' 的 Msg 对象。
        """
        return Msg(name=name, content=text, role="assistant")
