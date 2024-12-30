from langchain_rag.message.base import BaseCustomMessage


class RelatedQuestionSuggestMessage(BaseCustomMessage):
    role: str = "assistant"
    type: str = "related question suggest"
