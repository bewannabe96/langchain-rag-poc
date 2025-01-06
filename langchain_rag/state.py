from typing import TypedDict, Annotated, Sequence, Optional

from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages


class State(TypedDict):
    language: str
    area: str

    messages: Annotated[Sequence[BaseMessage], add_messages]
    agent_calls: list[str]
