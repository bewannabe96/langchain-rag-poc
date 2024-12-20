from langchain_core.tools import tool


@tool
def HandOffTool(agent: str) -> str:
    """Hand off to another agent"""
    return f"Hand off to {agent}"
