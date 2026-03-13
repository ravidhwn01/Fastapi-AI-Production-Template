"""Chatbot router: Simple generative AI using LangChain for text-to-response."""

import os
from functools import lru_cache

from fastapi import APIRouter, HTTPException
from langchain.prompts import PromptTemplate
from langchain_groq import ChatGroq
from pydantic import BaseModel

from dotenv import load_dotenv

load_dotenv()

prompt = PromptTemplate(
    input_variables=["question"],
    template="Jawab pertanyaan berikut dengan jelas dan ringkas:\nPertanyaan: {question}"
)


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is not configured. Add it to your .env file.")
    return value


@lru_cache(maxsize=1)
def get_chain():
    llm = ChatGroq(
        model="gemma2-9b-it",
        api_key=_require_env("GROQ_API_KEY")
    )
    return prompt | llm

router = APIRouter(
    prefix="/chatbot",
    tags=["chatbot"],
    responses={404: {"description": "Not found"}}
)

class ChatRequest(BaseModel):
    question: str
        
class ChatResponse(BaseModel):
    answer: str

@router.post("/ask", response_model=ChatResponse, summary="Ask chatbot a question")
async def ask_question(request: ChatRequest):
    """
    Ask a question to the generative AI chatbot.
    """
    try:
        chain = get_chain()
        result = chain.invoke({"question": request.question})
        # Extract the string content from the AIMessage object
        answer = getattr(result, "content", str(result))
        return ChatResponse(answer=answer)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))