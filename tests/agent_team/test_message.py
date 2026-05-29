"""MessageAdapter 的测试。"""

from llm_werewolf.agent_team.communication.message import Msg, MessageAdapter


class TestMsg:
    """Msg 类的测试用例。"""

    def test_msg_creation(self) -> None:
        msg = Msg(name="Test", content="Hello", role="user")
        assert msg.name == "Test"
        assert msg.content == "Hello"
        assert msg.role == "user"
        assert msg.id is not None
        assert msg.timestamp is not None

    def test_msg_to_dict(self) -> None:
        msg = Msg(name="Test", content="Hello", role="user")
        data = msg.to_dict()
        assert data["name"] == "Test"
        assert data["content"] == "Hello"
        assert data["role"] == "user"
        assert data["id"] == msg.id

    def test_msg_from_dict(self) -> None:
        data = {"name": "Test", "content": "Hello", "role": "user", "id": "test-id-123"}
        msg = Msg.from_dict(data)
        assert msg.name == "Test"
        assert msg.content == "Hello"
        assert msg.role == "user"
        assert msg.id == "test-id-123"

    def test_get_text_content_string(self) -> None:
        msg = Msg(name="Test", content="Hello World", role="user")
        assert msg.get_text_content() == "Hello World"

    def test_get_text_content_blocks(self) -> None:
        msg = Msg(
            name="Test",
            content=[{"type": "text", "text": "Hello"}, {"type": "text", "text": "World"}],
            role="user",
        )
        assert msg.get_text_content() == "Hello\nWorld"

    def test_get_text_content_with_separator(self) -> None:
        msg = Msg(
            name="Test",
            content=[{"type": "text", "text": "Hello"}, {"type": "text", "text": "World"}],
            role="user",
        )
        assert msg.get_text_content(separator=" ") == "Hello World"

    def test_msg_repr(self) -> None:
        msg = Msg(name="Test", content="Hello", role="user")
        repr_str = repr(msg)
        assert "Msg(" in repr_str
        assert "name='Test'" in repr_str
        assert "role='user'" in repr_str


class TestMessageAdapter:
    """MessageAdapter 类的测试用例。"""

    def test_str_to_msg(self) -> None:
        msg = MessageAdapter.str_to_msg("测试消息", name="Test", role="user")
        assert msg.content == "测试消息"
        assert msg.name == "Test"
        assert msg.role == "user"

    def test_str_to_msg_default_role(self) -> None:
        msg = MessageAdapter.str_to_msg("测试消息")
        assert msg.role == "system"

    def test_str_to_msg_with_metadata(self) -> None:
        msg = MessageAdapter.str_to_msg("测试消息", metadata={"round": 1, "phase": "day"})
        assert msg.metadata["round"] == 1
        assert msg.metadata["phase"] == "day"

    def test_msg_to_str(self) -> None:
        msg = Msg(name="Test", content="测试消息", role="user")
        text = MessageAdapter.msg_to_str(msg)
        assert text == "测试消息"

    def test_msg_to_str_with_blocks(self) -> None:
        msg = Msg(
            name="Test",
            content=[{"type": "text", "text": "Hello"}, {"type": "text", "text": "World"}],
            role="user",
        )
        text = MessageAdapter.msg_to_str(msg)
        assert text == "Hello\nWorld"

    def test_roundtrip(self) -> None:
        original = "这是一条测试消息"
        msg = MessageAdapter.str_to_msg(original, name="Test", role="user")
        result = MessageAdapter.msg_to_str(msg)
        assert result == original

    def test_create_game_msg(self) -> None:
        msg = MessageAdapter.create_game_msg(
            text="狼人请睁眼",
            name="Moderator",
            role_type="system",
            round_number=1,
            phase="night",
            player_id="player_1",
            visible_to=["werewolf"],
        )
        assert msg.content == "狼人请睁眼"
        assert msg.name == "Moderator"
        assert msg.role == "system"
        assert msg.metadata["round_number"] == 1
        assert msg.metadata["phase"] == "night"
        assert msg.metadata["player_id"] == "player_1"
        assert msg.metadata["visible_to"] == ["werewolf"]

    def test_create_system_msg(self) -> None:
        msg = MessageAdapter.create_system_msg("系统消息", name="System")
        assert msg.content == "系统消息"
        assert msg.name == "System"
        assert msg.role == "system"

    def test_create_user_msg(self) -> None:
        msg = MessageAdapter.create_user_msg("用户消息", name="Player1")
        assert msg.content == "用户消息"
        assert msg.name == "Player1"
        assert msg.role == "user"

    def test_create_assistant_msg(self) -> None:
        msg = MessageAdapter.create_assistant_msg("助手消息", name="Agent1")
        assert msg.content == "助手消息"
        assert msg.name == "Agent1"
        assert msg.role == "assistant"

    def test_chat_history_to_msgs(self) -> None:
        history = [
            {"role": "system", "content": "系统提示"},
            {"role": "user", "content": "用户消息"},
            {"role": "assistant", "content": "助手回复"},
        ]
        msgs = MessageAdapter.chat_history_to_msgs(history)
        assert len(msgs) == 3
        assert msgs[0].role == "system"
        assert msgs[0].content == "系统提示"
        assert msgs[1].role == "user"
        assert msgs[1].content == "用户消息"
        assert msgs[2].role == "assistant"
        assert msgs[2].content == "助手回复"

    def test_msgs_to_chat_history(self) -> None:
        msgs = [
            Msg(name="System", content="系统提示", role="system"),
            Msg(name="Player", content="用户消息", role="user"),
            Msg(name="Agent", content="助手回复", role="assistant"),
        ]
        history = MessageAdapter.msgs_to_chat_history(msgs)
        assert len(history) == 3
        assert history[0]["role"] == "system"
        assert history[0]["content"] == "系统提示"
        assert history[1]["role"] == "user"
        assert history[1]["content"] == "用户消息"
        assert history[2]["role"] == "assistant"
        assert history[2]["content"] == "助手回复"

    def test_chat_history_roundtrip(self) -> None:
        original = [
            {"role": "system", "content": "系统提示"},
            {"role": "user", "content": "用户消息"},
            {"role": "assistant", "content": "助手回复"},
        ]
        msgs = MessageAdapter.chat_history_to_msgs(original)
        result = MessageAdapter.msgs_to_chat_history(msgs)
        assert result == original
