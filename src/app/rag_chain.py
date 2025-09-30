import os
from typing import List, Dict, Any
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from .config import settings

# prompts load
SYSTEM = open(
    os.path.join(os.path.dirname(__file__), "prompts", "system_ko.md"),
    "r",
    encoding="utf-8",
).read()

# 문서 출처 조회
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

# LLM 생성
def make_llm() -> AzureChatOpenAI:
    return AzureChatOpenAI(
        azure_endpoint=settings.aoai_endpoint,
        api_key=settings.aoai_key,
        azure_deployment=settings.aoai_chat,     
        api_version=settings.aoai_api_version,   
        temperature=0.2,
    )

# 답변 생성
def generate_answer(
    question: str,
    docs: List[Dict[str, Any]],
    llm: AzureChatOpenAI | None = None,
    history: List[Dict[str, str]] | None = None,
) -> str:
    llm = llm or make_llm()
    ctx = build_context(docs)   

    # SYSTEM 프롬프트 구성
    messages = [SystemMessage(content=SYSTEM)]

    # 최근 히스토리(최대 8개) 반영
    for m in (history or [])[-8:]:
        role = (m.get("role") or "").lower()
        content = m.get("content") or ""
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))

    # 최종 질문과 문서 출처 반영
    messages.append(HumanMessage(content=f"질문: {question}\n\n참고 자료:\n{ctx}"))

    # LLM 호출 
    return llm.invoke(messages).content