"""向后兼容的重导出；规范实现见 ``adapter.message``。"""

from llm_werewolf.adapter.message import MessageAdapter, Msg

__all__ = ["MessageAdapter", "Msg"]
