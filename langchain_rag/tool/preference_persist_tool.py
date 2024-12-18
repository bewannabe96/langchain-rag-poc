from typing import Type

from langchain_core.tools import BaseTool
from pydantic import Field, BaseModel


class PreferenceField(BaseModel):
    field_type: str = Field(description="Type (i.e. time, region, companion, etc.")
    field_values: list[str] = Field(description="Value")


class PreferencePersistInput(BaseModel):
    fields: list[PreferenceField] = Field(description="Fields to be updated")


class PreferencePersistTool(BaseTool):
    name: str = "PreferencePersist"
    description: str = "Persist preference of user"
    args_schema: Type[BaseModel] = PreferencePersistInput
    return_direct: bool = True

    def _run(self, fields: list[PreferenceField]) -> str:
        result = ""
        for field in fields:
            result += f"Persisted \"{field.field_type}\" preference with values \"{', '.join(field.field_values)}\"\n"
        return result
