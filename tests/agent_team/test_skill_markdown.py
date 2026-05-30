from llm_werewolf.agent_team.skill_support.skill_markdown import (
    parse_frontmatter,
    extract_description,
    split_description_line,
    ensure_description_format,
    render_frontmatter_markdown,
    strip_legacy_description_line,
)


def test_parse_frontmatter_keeps_simple_yaml_like_behavior() -> None:
    text = "---\nskill_id: wolf_demo\nnote: a:b:c\n---\n\n# Body\n"

    meta, body = parse_frontmatter(text)

    assert meta == {"skill_id": "wolf_demo", "note": "a:b:c"}
    assert body == "# Body"


def test_parse_frontmatter_falls_back_to_plain_body_on_broken_header() -> None:
    text = "---\nskill_id: wolf_demo\n# Body"

    meta, body = parse_frontmatter(text)

    assert meta == {}
    assert body == text


def test_description_line_and_when_to_use_share_fixed_format() -> None:
    description, body = split_description_line("描述：首夜狼队需要统一刀口\n\n# 正文")

    assert description == "首夜狼队需要统一刀口的情况下，使用该 skill"
    assert body == "# 正文"
    assert (
        ensure_description_format("首夜狼队需要统一刀口的情况下")
        == "首夜狼队需要统一刀口的情况下，使用该 skill"
    )


def test_extract_description_prefers_when_to_use_section() -> None:
    content = (
        "# 技能\n"
        "## 提取依据\n"
        "这段不是触发条件。\n"
        "## 何时使用\n"
        "- 首夜狼队私密频道，落刀前需要统一目标。\n"
        "## 行动\n"
        "先报建议刀口。"
    )

    assert (
        extract_description(content)
        == "首夜狼队私密频道，落刀前需要统一目标的情况下，使用该 skill"
    )


def test_strip_legacy_description_only_when_when_to_use_exists():
    legacy = "描述：旧描述\n\n# 技能\n## 何时使用\n首夜\n"
    plain = "描述：旧描述\n\n# 技能"

    assert not strip_legacy_description_line(legacy).startswith("描述：")
    assert strip_legacy_description_line(plain).startswith("# 技能")


def test_render_frontmatter_markdown_skips_empty_values() -> None:
    rendered = render_frontmatter_markdown(
        {"skill_id": "wolf_demo", "status": "", "weight": "1.00"}, "# Body"
    )

    assert "skill_id: wolf_demo" in rendered
    assert "status:" not in rendered
    assert rendered.rstrip().endswith("# Body")
