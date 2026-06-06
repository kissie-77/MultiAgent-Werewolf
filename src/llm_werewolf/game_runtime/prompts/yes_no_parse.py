"""是/否回答的严格解析（Bridge 与 PromptManager 共用）。"""

from __future__ import annotations

import re


class YesNoParseError(ValueError):
    """无法从模型输出中解析出合法的是/否答案。"""


def parse_yes_no_strict(response: str) -> bool:
    """仅接受 [[0]]/[[1]]、单行 0/1，或整句 yes/no/是/否。

    Raises:
        YesNoParseError: 格式不合法或存在歧义时。
    """
    text = response.strip()
    if not text:
        msg = "empty yes/no response"
        raise YesNoParseError(msg)

    bracketed = re.search(r"\[\[\s*([01])\s*\]\]", text)
    if bracketed:
        if re.search(r"\[\[\s*[01]\s*\]\].*\[\[\s*[01]\s*\]\]", text):
            msg = "multiple [[0]]/[[1]] markers in yes/no response"
            raise YesNoParseError(msg)
        return bracketed.group(1) == "1"

    if re.fullmatch(r"[01]", text):
        return text == "1"

    normalized = text.lower()
    if normalized in {"yes", "y", "是", "同意", "好"}:
        return True
    if normalized in {"no", "n", "否", "不", "不要", "拒绝"}:
        return False

    msg = f"unrecognized yes/no format: {response!r}"
    raise YesNoParseError(msg)
