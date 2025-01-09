from typing import Type

from pydantic import BaseModel, Field

from langchain_rag.agent.hand_off import HandOff


class SpaceQuestionHandOffArgs(BaseModel):
    question: str = Field(description="Detailed question about DayTrip spaces.")


class SpaceQuestionHandOff(HandOff):
    name: str = "SpaceQuestionHandOff"
    description: str = "Hand off to SpaceQuestion Agent"
    args_schema: Type[BaseModel] = SpaceQuestionHandOffArgs

    def _run(self, question: str) -> str:
        return f"[SpaceQuestionHandOff] {question}"
