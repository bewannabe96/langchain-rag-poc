from typing import TypedDict, Annotated, Sequence

from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages


class State(TypedDict):
    language: Annotated[str, ...]
    messages: Annotated[Sequence[BaseMessage], add_messages]
    agent_calls: Annotated[list[str], ...]
