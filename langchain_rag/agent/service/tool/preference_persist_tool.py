from langchain_core.tools import tool
from pydantic import Field, BaseModel


class PreferenceField(BaseModel):
    field_type: str = Field(description="Type (i.e. time, region, companion, etc.")
    field_values: list[str] = Field(description="Value")


class PreferencePersistInput(BaseModel):
    fields: list[PreferenceField] = Field(description="Fields to be updated")


@tool(args_schema=PreferencePersistInput)
def PreferencePersist(
        fields: list[PreferenceField],
) -> str:
    """
    Persist preference of user
    """

    result = ""
    for field in fields:
        result += f"Persisted \"{field.field_type}\" preference with values \"{', '.join(field.field_values)}\"\n"
    return result
