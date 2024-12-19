from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode

from langchain_rag.prompt.load_prompt import load_system_prompt
from langchain_rag.state import State
from langchain_rag.tool import PreferencePersistTool

tools = [
    PreferencePersistTool()
]

model = ChatOpenAI(model="gpt-4o", temperature=0).bind_tools(tools=tools)
prompt_template = ChatPromptTemplate.from_messages([
    load_system_prompt("agent/service/main"),
    MessagesPlaceholder(variable_name="messages"),
])


def main_node(state: State):
    prompt = prompt_template.invoke(state)
    message = model.invoke(prompt)
    return {"messages": [message]}


def tool_router(state: State):
    message = state["messages"][-1]
    if not isinstance(message, AIMessage):
        return END

    if len(message.tool_calls) > 0:
        return "tool"
    else:
        return END


builder = StateGraph(state_schema=State)

builder.add_node("main", main_node)
builder.add_node("tool", ToolNode(tools=tools))

builder.add_edge(START, "main")
builder.add_conditional_edges("main", tool_router, ["tool", END])
builder.add_edge("tool", "main")

service_agent = builder.compile()
