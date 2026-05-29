"""game_runtime/locale.py 模块的测试。"""

from llm_werewolf.game_runtime.locale import Locale


class TestLocale:
    """Locale 类的测试。"""

    def test_default_language(self) -> None:
        """测试默认语言为 en-US。"""
        locale = Locale()
        assert locale.language == "en-US"

    def test_english_locale(self) -> None:
        """测试英语区域初始化。"""
        locale = Locale("en-US")
        assert locale.language == "en-US"
        assert "night_begins" in locale.messages

    def test_traditional_chinese_locale(self) -> None:
        """测试繁体中文区域初始化。"""
        locale = Locale("zh-TW")
        assert locale.language == "zh-TW"
        assert "night_begins" in locale.messages

    def test_simplified_chinese_locale(self) -> None:
        """测试简体中文区域初始化。"""
        locale = Locale("zh-CN")
        assert locale.language == "zh-CN"
        assert "night_begins" in locale.messages

    def test_unsupported_language_fallback(self) -> None:
        """测试不支持的语言回退到英语。"""
        locale = Locale("fr-FR")
        assert locale.language == "en-US"
        # 仍应有英语消息
        assert locale.get("night_begins") == "Night {round_number} begins"

    def test_get_message_without_formatting(self) -> None:
        """测试获取未格式化的消息。"""
        locale = Locale("en-US")
        message = locale.get("voting_phase")
        assert message == "Voting Phase"

    def test_get_message_with_formatting(self) -> None:
        """测试获取带格式化的消息。"""
        locale = Locale("en-US")
        message = locale.get("night_begins", round_number=3)
        assert message == "Night 3 begins"

    def test_get_message_with_multiple_params(self) -> None:
        """测试获取带多个参数的消息。"""
        locale = Locale("en-US")
        message = locale.get("game_started", player_count=9)
        assert message == "Game started with 9 players"

    def test_get_nonexistent_key(self) -> None:
        """测试不存在的键返回键本身。"""
        locale = Locale("en-US")
        message = locale.get("nonexistent_key")
        assert message == "nonexistent_key"

    def test_get_message_with_wrong_format_params(self) -> None:
        """测试使用错误格式参数获取消息。"""
        locale = Locale("en-US")
        # night_begins 需要 round_number，此处传入 player_count
        message = locale.get("night_begins", player_count=5)
        # 格式化失败时应原样返回模板
        assert message == "Night {round_number} begins"

    def test_set_language_to_chinese(self) -> None:
        """测试切换语言为中文。"""
        locale = Locale("en-US")
        assert locale.language == "en-US"

        locale.set_language("zh-TW")
        assert locale.language == "zh-TW"
        # 检查消息已切换为中文
        message = locale.get("voting_phase")
        assert message == "投票階段"

    def test_set_language_to_english(self) -> None:
        """测试切换语言为英语。"""
        locale = Locale("zh-TW")
        assert locale.language == "zh-TW"

        locale.set_language("en-US")
        assert locale.language == "en-US"
        # 检查消息已切换为英语
        message = locale.get("voting_phase")
        assert message == "Voting Phase"

    def test_set_language_invalid(self) -> None:
        """测试设置无效语言无效果。"""
        locale = Locale("en-US")
        assert locale.language == "en-US"

        locale.set_language("invalid-LANG")
        # 应保持英语
        assert locale.language == "en-US"
        message = locale.get("voting_phase")
        assert message == "Voting Phase"

    def test_all_locales_have_same_keys(self) -> None:
        """测试所有区域具有相同的消息键。"""
        en_keys = set(Locale.MESSAGES["en-US"].keys())
        tw_keys = set(Locale.MESSAGES["zh-TW"].keys())
        cn_keys = set(Locale.MESSAGES["zh-CN"].keys())

        assert en_keys == tw_keys
        assert en_keys == cn_keys

    def test_phase_separator_messages(self) -> None:
        """测试阶段分隔消息。"""
        locale = Locale("en-US")
        assert locale.get("phase_separator") == "=" * 60
        assert "🌙" in locale.get("night_separator")
        assert "☀️" in locale.get("day_separator")

    def test_vote_messages(self) -> None:
        """测试投票相关消息。"""
        locale = Locale("en-US")
        vote_cast = locale.get("vote_cast", voter="Alice", target="Bob")
        assert "Alice" in vote_cast
        assert "Bob" in vote_cast

    def test_death_messages(self) -> None:
        """测试死亡相关消息。"""
        locale = Locale("en-US")
        killed = locale.get("killed_by_werewolves", player="Alice")
        assert "Alice" in killed
        assert "werewolves" in killed.lower()

    def test_role_action_messages(self) -> None:
        """测试角色行动消息。"""
        locale = Locale("en-US")

        witch_saved = locale.get("witch_saved", target="Bob")
        assert "Witch" in witch_saved
        assert "Bob" in witch_saved

        guard_protected = locale.get("guard_protected", target="Charlie")
        assert "Guard" in guard_protected
        assert "Charlie" in guard_protected

    def test_chinese_messages_formatting(self) -> None:
        """测试中文消息支持格式化。"""
        locale = Locale("zh-TW")

        message = locale.get("night_begins", round_number=5)
        assert "5" in message
        assert "黑夜" in message

        message = locale.get("game_started", player_count=10)
        assert "10" in message
