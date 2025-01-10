from typing import TypedDict, Annotated, Sequence, Optional

from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages, MessagesState


class State(MessagesState):
    language: str
    exclude_space_ids: list[str]
