"""教练系统占位 —— 未来职责：从情景记忆提炼经验，写入语义记忆/skill。"""

from __future__ import annotations


class Coach:
    """从全局情景记忆中提炼经验，写入 skill 或语义记忆。

    当前为占位实现，后续将扩展：
    - 分析 AGENT_THOUGHT 心理记录
    - 从赛后报告提取高价值策略
    - 调用 LLM 做经验归纳
    - 将结果写入 agent_team/skills/<role>/
    """
