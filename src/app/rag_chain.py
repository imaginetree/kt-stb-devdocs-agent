# src/app/rag_chain.py
import os
from typing import List, Dict, Any
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from .config import settings

SYSTEM = open(
    os.path.join(os.path.dirname(__file__), "prompts", "system_ko.md"),
    "r",
    encoding="utf-8",
).read()

def build_context(docs: List[Dict[str, Any]], max_chars: int = 1800) -> str:
    lines, used = [], 0
    for d in docs:
        text = d.get("chunk") or d.get("content", "") or ""
        src = d.get("source", "") or "문서"
        snippet = (text.strip().replace("\n", " "))[:400]
        line = f"- {src}: {snippet}"
        if used + len(line) > max_chars:
            break
        lines.append(line)
        used += len(line)
    return "\n".join(lines)

def make_llm() -> AzureChatOpenAI:
    return AzureChatOpenAI(
        azure_endpoint=settings.aoai_endpoint,
        api_key=settings.aoai_key,
        azure_deployment=settings.aoai_chat,     # ex) gpt-4.1-mini
        api_version=settings.aoai_api_version,   # 중요
        temperature=0.2,
    )

def generate_answer(
    question: str,
    docs: List[Dict[str, Any]],
    llm: AzureChatOpenAI | None = None,
    history: List[Dict[str, str]] | None = None,
) -> str:
    llm = llm or make_llm()
    ctx = build_context(docs)

    messages = [SystemMessage(content=SYSTEM)]

    # 최근 히스토리(최대 8개) 반영
    for m in (history or [])[-8:]:
        role = (m.get("role") or "").lower()
        content = m.get("content") or ""
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))

    messages.append(HumanMessage(content=f"질문: {question}\n\n참고 자료:\n{ctx}"))
    return llm.invoke(messages).content