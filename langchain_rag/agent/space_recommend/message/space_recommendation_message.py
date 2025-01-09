from langchain_rag.message.base import BaseCustomMessage


class SpaceRecommendationMessage(BaseCustomMessage):
    role: str = "assistant"
    type: str = "space recommendation"
