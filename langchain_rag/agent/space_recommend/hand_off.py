from typing import Type

from pydantic import BaseModel, Field

from langchain_rag.agent.hand_off import HandOff


class SpaceRecommendHandOffArgs(BaseModel):
    query: str = Field(description="Detailed English query for space recommendation")
    exclude_space_ids: list[str] = Field(description="Space IDs to exclude from the result")


class SpaceRecommendHandOff(HandOff):
    name: str = "SpaceRecommendHandOff"
    description: str = "Hand off to SpaceRecommend Agent"
    args_schema: Type[BaseModel] = SpaceRecommendHandOffArgs

    def _run(self, query: str, exclude_space_ids: list[str]) -> str:
        return f"[SpaceRecommendHandOff] {query}"


