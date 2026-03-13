"""Agents router: Generate NYT-style articles using LangChain and OpenAI."""

import os
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, HTTPException

from langchain.chat_models import init_chat_model
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from langchain_tavily import TavilySearch
from langgraph.prebuilt import ToolNode, tools_condition

router = APIRouter(
    prefix="/agents",
    tags=["agents"],
    responses={404: {"description": "Not found"}}
)

class State(TypedDict):
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: Annotated[list, add_messages]


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is not configured. Add it to your .env file.")
    return value


@lru_cache(maxsize=1)
def get_graph():
    _require_env("GROQ_API_KEY")
    _require_env("TAVILY_API_KEY")

    graph_builder = StateGraph(State)
    llm = init_chat_model("llama3-8b-8192", model_provider="groq")

    tool = TavilySearch(max_results=2)
    tools = [tool]
    llm_with_tools = llm.bind_tools(tools)

    def chatbot(state: State):
        return {"messages": [llm_with_tools.invoke(state["messages"])]}

    graph_builder.add_node("chatbot", chatbot)

    tool_node = ToolNode(tools=[tool])
    graph_builder.add_node("tools", tool_node)

    graph_builder.add_conditional_edges(
        "chatbot",
        tools_condition,
    )
    graph_builder.add_edge("tools", "chatbot")
    graph_builder.add_edge(START, "chatbot")
    graph_builder.add_edge("chatbot", END)

    return graph_builder.compile()

# FastAPI endpoint to get graph PNG
from fastapi.responses import Response

@router.get("/graph", response_class=Response, summary="Get LangGraph structure as PNG")
async def get_graph_png():
    """
    Returns the LangGraph structure as a PNG image.
    """
    try:
        graph = get_graph()
        png_bytes = graph.get_graph().draw_mermaid_png()
        return Response(content=png_bytes, media_type="image/png")
    except RuntimeError as e:
        return Response(content=str(e), media_type="text/plain", status_code=503)
    except Exception as e:
        return Response(content=f"Gagal menyimpan gambar: {e}", media_type="text/plain", status_code=500)

def stream_graph_updates(user_input: str):
    graph = get_graph()
    for event in graph.stream({"messages": [{"role": "user", "content": user_input}]}):
        for value in event.values():
            print("Assistant:", value["messages"][-1].content)


from pydantic import BaseModel

# Request model for chat endpoint
class ChatRequest(BaseModel):
    message: str

    class Config:
        json_schema_extra = {
            "example": {
                "message": "tell me about president jokowi"
            }
        }

@router.post("/ask")
async def chat_endpoint(request: ChatRequest):
    """
    Chat with LangGraph agent. Send a message and get response.
    """
    try:
        graph = get_graph()
        user_input = request.message
        responses = []
        for event in graph.stream({"messages": [{"role": "user", "content": user_input}]}):
            for value in event.values():
                responses.append(value["messages"][-1].content)
        return {"responses": responses}
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e