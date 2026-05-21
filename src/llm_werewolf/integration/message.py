"""Message adapter for converting between LLMWerewolf str and AgentScope Msg formats."""

from typing import Literal, Sequence
from datetime import datetime

import shortuuid

from llm_werewolf.core.types.enums import GamePhase


class ContentBlock:
    """Content block for multi-modal messages."""

    @staticmethod
    def text(text: str) -> dict:
        """Create a text block."""
        return {"type": "text", "text": text}

    @staticmethod
    def tool_use(name: str, input_data: dict) -> dict:
        """Create a tool use block."""
        return {"type": "tool_use", "name": name, "input": input_data}

    @staticmethod
    def tool_result(output: str) -> dict:
        """Create a tool result block."""
        return {"type": "tool_result", "output": output}


class Msg:
    """Message object compatible with AgentScope format.

    This is a lightweight implementation that mirrors AgentScope's Msg class
    without requiring the full AgentScope dependency.
    """

    def __init__(
        self,
        name: str,
        content: str | Sequence[dict],
        role: Literal["user", "assistant", "system"],
        metadata: dict | None = None,
        timestamp: str | None = None,
        invocation_id: str | None = None,
        msg_id: str | None = None,
    ) -> None:
        """Initialize the Msg object.

        Args:
            name: The name of the message sender.
            content: The content of the message (string or content blocks).
            role: The role of the message sender (user/assistant/system).
            metadata: Additional metadata for the message.
            timestamp: The timestamp of the message. Auto-generated if None.
            invocation_id: The related API invocation ID.
            msg_id: Optional message ID. Auto-generated if None.
        """
        self.name = name
        self.content = content
        self.role = role
        self.metadata = metadata or {}
        self.id = msg_id or shortuuid.uuid()
        self.timestamp = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        self.invocation_id = invocation_id

    def to_dict(self) -> dict:
        """Convert the message to a dictionary."""
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
        """Create a Msg from a dictionary."""
        return cls(
            name=data["name"],
            content=data["content"],
            role=data["role"],
            metadata=data.get("metadata"),
            timestamp=data.get("timestamp"),
            invocation_id=data.get("invocation_id"),
            msg_id=data.get("id"),
        )

    def get_text_content(self, separator: str = "\n") -> str | None:
        """Extract text content from the message.

        Args:
            separator: Separator for joining multiple text blocks.

        Returns:
            The text content, or None if no text content exists.
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
        """Return string representation."""
        return (
            f"Msg(id='{self.id}', "
            f"name='{self.name}', "
            f"content={repr(self.content)}, "
            f"role='{self.role}')"
        )


class MessageAdapter:
    """Adapter for converting between LLMWerewolf str and AgentScope Msg formats.

    This adapter provides bidirectional conversion:
    - str → Msg: Convert game engine prompts to AgentScope messages
    - Msg → str: Convert AgentScope responses to game engine format
    """

    @staticmethod
    def str_to_msg(
        text: str,
        name: str = "Moderator",
        role: Literal["user", "assistant", "system"] = "system",
        metadata: dict | None = None,
    ) -> Msg:
        """Convert a string prompt to an AgentScope-compatible Msg.

        Args:
            text: The prompt text from the game engine.
            name: The name of the message sender.
            role: The role of the message sender.
            metadata: Additional metadata for the message.

        Returns:
            A Msg object compatible with AgentScope.
        """
        return Msg(
            name=name,
            content=text,
            role=role,
            metadata=metadata or {},
        )

    @staticmethod
    def msg_to_str(msg: Msg) -> str:
        """Convert an AgentScope Msg to a string for the game engine.

        Args:
            msg: The Msg object from AgentScope.

        Returns:
            The text content of the message.
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
        """Create a game-specific message with metadata.

        Args:
            text: The message content.
            name: The name of the message sender.
            role_type: The role of the message sender.
            round_number: The current game round number.
            phase: The current game phase.
            player_id: The target player ID (for private messages).
            role_name: The role name of the sender.
            action_type: The type of action (vote/kill/save/etc.).
            visible_to: List of player IDs who can see this message.

        Returns:
            A Msg object with game-specific metadata.
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

        return Msg(
            name=name,
            content=text,
            role=role_type,
            metadata=metadata,
        )

    @staticmethod
    def chat_history_to_msgs(history: list[dict]) -> list[Msg]:
        """Convert OpenAI-format chat history to Msg list.

        Args:
            history: List of dicts with 'role' and 'content' keys.

        Returns:
            List of Msg objects.
        """
        msgs = []
        for item in history:
            role = item.get("role", "user")
            if role not in ("user", "assistant", "system"):
                role = "user"

            msgs.append(Msg(
                name="Player",
                content=item.get("content", ""),
                role=role,
            ))
        return msgs

    @staticmethod
    def msgs_to_chat_history(msgs: list[Msg]) -> list[dict]:
        """Convert Msg list to OpenAI-format chat history.

        Args:
            msgs: List of Msg objects.

        Returns:
            List of dicts with 'role' and 'content' keys.
        """
        history = []
        for msg in msgs:
            content = msg.get_text_content() or ""
            history.append({
                "role": msg.role,
                "content": content,
            })
        return history

    @staticmethod
    def create_system_msg(text: str, name: str = "System") -> Msg:
        """Create a system message.

        Args:
            text: The system message content.
            name: The name of the message sender.

        Returns:
            A Msg object with role='system'.
        """
        return Msg(name=name, content=text, role="system")

    @staticmethod
    def create_user_msg(text: str, name: str = "Moderator") -> Msg:
        """Create a user message.

        Args:
            text: The user message content.
            name: The name of the message sender.

        Returns:
            A Msg object with role='user'.
        """
        return Msg(name=name, content=text, role="user")

    @staticmethod
    def create_assistant_msg(text: str, name: str = "Player") -> Msg:
        """Create an assistant message.

        Args:
            text: The assistant message content.
            name: The name of the message sender.

        Returns:
            A Msg object with role='assistant'.
        """
        return Msg(name=name, content=text, role="assistant")
