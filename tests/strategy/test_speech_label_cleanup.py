"""清理模型把 Schema 字段名写进正文的发言（deepseek-v4-flash 标签泄漏修复）。

样本取自真实对局 ``artifacts/runs/6p-deepseek-20260606-122318``：当模型不调用
``generate_response`` 工具、而是直接吐出带 ``public_speech:`` / ``private_thought:``
标签（或带首尾引号的 JSON 串）时，旧解析会把标签与私域推理一并泄漏进公开发言。
"""

from __future__ import annotations

import pytest

from llm_werewolf.agent_team.bridge import WerewolfAdapterBridge
from llm_werewolf.strategy.contracts.decisions import (
    extract_public_text,
    split_labeled_speech,
    is_valid_public_speech,
)

# --- 真实泄漏样本 -------------------------------------------------------------

P4_REAL = (
    'public_speech: 1号提到"先看4号"，我不太理解，首夜没信息我有什么好看的？'  # noqa: RUF001
    "我反而觉得1号这个点提得有点突兀，像是想带节奏。\n"
    "private_thought: 我是狼，要把火力引到1号身上。"
)
P6_REAL = (
    '"我是预言家，昨晚验了4号是狼人。我首夜选择验4号是因为这个位置居中、是信息增量的好选择。"'
)
WOLF_P4 = (
    "public_speech: 我建议刀5号，首夜盲刀位置居中，不容易被抿出刀法倾向。 "
    "private_thought: 同时观察队友反应。"
)
JSON_ISH = (
    '"public_speech": "我觉得5号发言前后矛盾，需要重点听他解释。", "private_thought": "装好人"'
)


# --- split_labeled_speech -----------------------------------------------------


def test_split_strips_public_label_and_separates_private() -> None:
    public, private = split_labeled_speech(P4_REAL)
    assert "public_speech" not in public.lower()
    assert "private_thought" not in public.lower()
    assert "1号" in public
    assert private is not None
    assert "狼" in private


def test_split_json_ish_unwraps_quotes() -> None:
    public, private = split_labeled_speech(JSON_ISH)
    assert public.startswith("我觉得5号")
    assert '"' not in public
    assert private == "装好人"


def test_split_leaves_clean_speech_untouched() -> None:
    raw = "我觉得3号昨晚的发言前后矛盾，建议今天重点听他的解释再决定投票。"
    public, private = split_labeled_speech(raw)
    assert public == raw
    assert private is None


def test_split_does_not_overstrip_real_colon_speech() -> None:
    raw = "我的判断是：4号发言逻辑最顺，建议先出5号。"
    public, private = split_labeled_speech(raw)
    assert public == raw
    assert private is None


# --- extract_public_text ------------------------------------------------------


def test_extract_strips_leading_public_label() -> None:
    out = extract_public_text(P4_REAL)
    assert "public_speech" not in out.lower()
    assert "private_thought" not in out.lower()
    assert out.startswith("1号提到")
    assert is_valid_public_speech(out)


def test_extract_strips_leading_json_quote() -> None:
    out = extract_public_text(P6_REAL)
    assert not out.startswith('"')
    assert out.startswith("我是预言家")
    assert is_valid_public_speech(out)


# --- parse_speech -------------------------------------------------------------


def test_parse_speech_routes_label_private_out_of_public() -> None:
    decision = WerewolfAdapterBridge.parse_speech(WOLF_P4)
    assert "public_speech" not in decision.public_speech.lower()
    assert "private_thought" not in decision.public_speech.lower()
    assert "刀5号" in decision.public_speech
    assert decision.private_thought is not None
    assert "队友" in decision.private_thought


@pytest.mark.parametrize("raw", [P4_REAL, P6_REAL, WOLF_P4, JSON_ISH])
def test_no_sample_leaks_field_names(raw: str) -> None:
    decision = WerewolfAdapterBridge.parse_speech(raw)
    assert "public_speech" not in decision.public_speech.lower()
    assert "private_thought" not in decision.public_speech.lower()
    assert is_valid_public_speech(decision.public_speech)


# --- 对抗验证发现的回归用例（adversarial hunters）-----------------------------
# 这些样本曾击穿初版实现：详见 verify-speech-label-cleanup 工作流报告。

# 过度剥离：含「内心想法/心理活动/内心独白」等普通中文词 + 冒号的正常发言，
# 没有 public 标签前缀时绝不能被当成 private 标签而清空公开发言。
OVERSTRIP_CN = [
    "我说说我的内心想法：5号的票型很奇怪，我认为他大概率是狼。",
    "分析他的心理活动：他急于跳过我，说明他心里多半有鬼，投他。",
    "讲讲我的内心独白：我昨晚就觉得5号不对劲，今天更确定他是狼了。",
]


@pytest.mark.parametrize("raw", OVERSTRIP_CN)
def test_chinese_phrase_with_colon_not_treated_as_label(raw: str) -> None:
    public, private = split_labeled_speech(raw)
    assert public == raw
    assert private is None
    assert extract_public_text(raw) == raw
    assert WerewolfAdapterBridge.parse_speech(raw).public_speech == raw


def test_prose_seat_token_does_not_hijack_speech() -> None:
    # [[5号]] 是散文里的座位引用，不能让整句坍缩成「（无公开发言）」。
    raw = "我觉得[[5号]]和[[3号]]是狼人同伙，建议本轮先把5号投出去。"
    out = extract_public_text(raw)
    assert is_valid_public_speech(out)
    assert "狼人同伙" in out
    assert "5号投出去" in out


def test_full_json_object_keeps_public_value() -> None:
    raw = '{"public_speech": "我是预言家昨晚查验了3号结果是金水请大家相信我", "private_thought": "稳住金水别翻车"}'
    decision = WerewolfAdapterBridge.parse_speech(raw)
    assert decision.public_speech == "我是预言家昨晚查验了3号结果是金水请大家相信我"
    assert "public_speech" not in decision.public_speech.lower()
    assert decision.private_thought is not None
    assert "稳住金水" in decision.private_thought


def test_markdown_bold_labels_stripped_en() -> None:
    raw = "**public_speech**: 我是预言家昨晚查杀4号请大家投他出局 **private_thought**: 4号是狼"
    decision = WerewolfAdapterBridge.parse_speech(raw)
    assert "public_speech" not in decision.public_speech.lower()
    assert "private_thought" not in decision.public_speech.lower()
    assert "4号是狼" not in decision.public_speech
    assert "查杀4号" in decision.public_speech
    assert decision.private_thought is not None
    assert "4号是狼" in decision.private_thought


def test_markdown_bold_labels_stripped_cn() -> None:
    raw = "**公开发言**：我建议先验5号的身份这样比较稳妥 **私人推理**：5号是关键先盘他"
    decision = WerewolfAdapterBridge.parse_speech(raw)
    assert "公开发言" not in decision.public_speech
    assert "私人推理" not in decision.public_speech
    assert "先验5号" in decision.public_speech
    assert decision.private_thought is not None
    assert "5号是关键" in decision.private_thought


def test_private_label_before_public_label() -> None:
    raw = "private_thought：我要稳住金水别让他翻车 public_speech：我是预言家昨晚查了3号是金水请跟我投票"
    decision = WerewolfAdapterBridge.parse_speech(raw)
    assert "public_speech" not in decision.public_speech.lower()
    assert "private_thought" not in decision.public_speech.lower()
    assert "我是预言家" in decision.public_speech
    assert "查了3号" in decision.public_speech
    assert decision.private_thought is not None
    assert "稳住金水" in decision.private_thought


def test_speech_opening_with_quoted_term_keeps_quote() -> None:
    # 以引号开头但不是成对包裹整句，不应被剥引号（曾留下不配对的右引号）。
    raw = "“跳预言家”这种说法太草率了，我建议大家先看完整整一轮发言再下结论。"
    out = extract_public_text(raw)
    assert is_valid_public_speech(out)
    assert "跳预言家" in out
    assert "太草率" in out


# --- 第二轮对抗验证发现的回归用例 --------------------------------------------

# 仅含中文 private 标签的“字段倾倒”：私域计划绝不能被广播成公开发言（信息泄漏）。
CN_PRIVATE_DUMP = [
    "私人推理：我今晚去毒4号收掉这个预言家。",
    "私域推理：先观望一轮不急着站边，今晚我打算空过。",
    "内心独白：我是狼王身份千万要藏好别暴露给场上任何人。",
]


@pytest.mark.parametrize("raw", CN_PRIVATE_DUMP)
def test_chinese_only_private_dump_not_broadcast(raw: str) -> None:
    decision = WerewolfAdapterBridge.parse_speech(raw)
    # 公开发言不得包含私域内容或标签本身。
    assert "私人推理" not in decision.public_speech
    assert "私域推理" not in decision.public_speech
    assert "内心独白" not in decision.public_speech
    assert decision.public_speech == "（无公开发言）"
    # 私域计划应被回收进 private_thought。
    assert decision.private_thought is not None
    body = raw.split("：", 1)[1]
    assert body[:6] in decision.private_thought


def test_chinese_private_label_before_public_label() -> None:
    raw = (
        "私人推理：今晚我打算去刀掉预言家这个大雷。\n"
        "公开发言：我是普通村民没什么信息建议大家听警长的安排。"
    )
    decision = WerewolfAdapterBridge.parse_speech(raw)
    assert "私人推理" not in decision.public_speech
    assert "公开发言" not in decision.public_speech
    assert "刀掉预言家" not in decision.public_speech
    assert "我是普通村民" in decision.public_speech
    assert decision.private_thought is not None
    assert "刀掉预言家" in decision.private_thought


def test_two_quoted_terms_keep_their_quotes() -> None:
    # 开头与结尾各含一个引号词，不是整段包裹，引号必须保留。
    raw = "“金水”这个标签我并不认可，我更相信自己盘出来的“银水”位置。"
    out = extract_public_text(raw)
    assert is_valid_public_speech(out)
    assert "“金水”" in out
    assert "“银水”" in out
    public, private = split_labeled_speech(raw)
    assert public == raw
    assert private is None


def test_prose_seat_reference_is_preserved() -> None:
    # 散文里的 [[2号]] 应展开为 2号，不能丢掉座位信息。
    raw = "昨晚的刀法说明狼在[[2号]]附近，但这只是我的推测，先别急着归票。"
    out = extract_public_text(raw)
    assert is_valid_public_speech(out)
    assert "2号" in out
    assert "[[" not in out
