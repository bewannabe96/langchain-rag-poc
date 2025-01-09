from typing import Annotated

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedStore, InjectedState
from langgraph.store.base import BaseStore
from pydantic import Field, BaseModel

from langchain_rag.state import State


class PreferenceField(BaseModel):
    field_type: str = Field(description="Type (i.e. time, region, companion, etc.)")
    field_values: list[str] = Field(description="Value")


@tool
def PreferencePersist(
        # visible
        fields: Annotated[list[PreferenceField], "Fields to be updated"],
        # hidden
        state: Annotated[State, InjectedState],
        store: Annotated[BaseStore, InjectedStore],
) -> str:
    """
    Persist preference of user
    """

    memory_namespace = ("user", state["user_id"])
    memory_key = "preference"

    preference_memory_item = store.get(namespace=memory_namespace, key=memory_key)
    preference = preference_memory_item.value if preference_memory_item else {}

    result = ""
    for field in fields:
        value_set = set(preference[field.field_type] if field.field_type in preference else [])
        value_set.add(*field.field_values)

        preference[field.field_type] = list(value_set)

        result += f"Persisted \"{field.field_type}\" preference with values \"{', '.join(field.field_values)}\"\n"

    store.put(namespace=memory_namespace, key=memory_key, value=preference)

    return result
