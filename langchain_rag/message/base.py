from abc import ABC

from langchain_core.messages import AIMessage


# TODO: should extend ChatMessage instead of AIMessage
# due to error while deserializing, extending AIMessage came in as a temporary fix
class BaseCustomMessage(AIMessage, ABC):
    role: str = "assistant"
    type: str
