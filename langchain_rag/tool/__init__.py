from langchain_rag.tool.preference_persist_tool import PreferencePersistTool
from langchain_rag.tool.space_search_tool import SpaceSearchTool

tools = [
    SpaceSearchTool(),
    PreferencePersistTool(),
]
