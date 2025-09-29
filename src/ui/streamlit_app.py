# src/ui/streamlit_app.py
import os
import uuid
import requests
import datetime as dt
import streamlit as st
import re

API_URL = os.getenv("API_URL", "http://localhost:8000/ask")
K_TOP = int(os.getenv("RETRIEVAL_TOPK", "8"))

st.set_page_config(page_title="KT STB 개발 도우미", layout="wide", initial_sidebar_state="expanded")

# --- 세션 상태 초기화 ---
if "sessions" not in st.session_state:
    st.session_state.sessions = {}
if "current_sid" not in st.session_state:
    sid = str(uuid.uuid4())[:8]
    st.session_state.current_sid = sid
    st.session_state.sessions[sid] = {
        "title": "새 채팅",
        "created": dt.datetime.now().isoformat(),
        "messages": [],
    }

# --- 세션 조작 ---
def new_chat():
    cur = st.session_state.sessions.get(st.session_state.current_sid)
    if cur and not cur["messages"]:
        return
    sid = str(uuid.uuid4())[:8]
    st.session_state.sessions[sid] = {
        "title": "새 채팅",
        "created": dt.datetime.now().isoformat(),
        "messages": [],
    }
    st.session_state.current_sid = sid

def select_chat(sid: str):
    st.session_state.current_sid = sid

def delete_chat(sid: str):
    was = sid == st.session_state.current_sid
    st.session_state.sessions.pop(sid, None)
    if not st.session_state.sessions:
        new_chat()
        return
    if was:
        rest = sorted(
            st.session_state.sessions.items(),
            key=lambda x: x[1]["created"],
            reverse=True,
        )
        st.session_state.current_sid = rest[0][0]

# --- 표시 유틸 ---
def sanitize_answer(text: str) -> str:
    if not text:
        return text
    # '#page=숫자' 형태의 페이지 앵커 제거
    return re.sub(r'#page=\d+', '', text, flags=re.IGNORECASE)

def render_references(citations: list[dict]) -> str:
    if not citations:
        return ""
    seen = set()
    items = []
    for c in citations:
        src = (c.get("source") or "").strip()
        if src and src not in seen:
            seen.add(src)
            items.append(c)
    if not items:
        return ""
    lines = ["**참고문헌**"]
    for c in items:
        src = (c.get("source") or "문서").strip()
        url = (c.get("path") or "").strip()
        if url.startswith("http://") or url.startswith("https://"):
            lines.append(f"- 📎 [{src}]({url})")
        else:
            lines.append(f"- 📎 {src}")
    return "\n".join(lines)

# --- 메인 영역 ---
sid = st.session_state.current_sid
session = st.session_state.sessions[sid]

st.title("KT STB 개발 도우미")

# 과거 메시지 렌더
for msg in session["messages"]:
    with st.chat_message("user" if msg["role"] == "user" else "assistant"):
        content = sanitize_answer(msg["content"]) if msg["role"] == "assistant" else msg["content"]
        st.markdown(content)
        if msg["role"] == "assistant" and msg.get("citations"):
            st.markdown(render_references(msg["citations"]))

# 입력 → 백엔드 호출 → 응답 표시
prompt = st.chat_input("메시지를 입력하세요.")
if prompt:
    # 사용자 메시지 저장/표시
    session["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 첫 질문으로 세션 타이틀 설정
    if session["title"] == "새 채팅":
        t = prompt.strip()
        session["title"] = t if len(t) <= 24 else t[:24] + "…"

    # 최근 대화 일부만 히스토리로 전달
    hist = [
        {"role": m["role"], "content": m["content"]}
        for m in session["messages"][-8:]
        if m["role"] in ("user", "assistant")
    ]

    with st.chat_message("assistant"):
        with st.spinner("답변 생성 중..."):
            try:
                r = requests.post(
                    API_URL,
                    json={"question": prompt, "k": K_TOP, "history": hist},
                    timeout=120,
                )
                r.raise_for_status()
                data = r.json()
                answer = (data.get("answer") or "").strip() or "_(빈 응답)_"
                citations = data.get("citations", [])
                st.markdown(sanitize_answer(answer))
                if citations:
                    st.markdown(render_references(citations))
                session["messages"].append(
                    {"role": "assistant", "content": answer, "citations": citations}
                )
            except Exception as e:
                err = f"요청 실패: {e}"
                st.error(err)
                session["messages"].append(
                    {"role": "assistant", "content": err, "citations": []}
                )

# 상태 저장 (사이드바는 아래에서 렌더)
st.session_state.sessions[sid] = session

# --- 사이드바 (맨 아래로 이동: 같은 런에서 최신 타이틀 반영) ---
with st.sidebar:
    st.markdown("### 채팅 히스토리")
    st.button("➕ 새 채팅", use_container_width=True, on_click=new_chat)
    st.divider()
    items = sorted(
        st.session_state.sessions.items(),
        key=lambda x: x[1]["created"],
        reverse=True,
    )[:30]
    for sid, meta in items:
        is_cur = sid == st.session_state.current_sid
        title = meta["title"] if meta["title"] != "새 채팅" else sid
        c1, c2 = st.columns([1.0, 0.2])
        with c1:
            st.button(
                title,
                key=f"open_{sid}",
                use_container_width=True,
                type="primary" if is_cur else "secondary",
                on_click=select_chat,
                args=(sid,),
            )
        with c2:
            st.button(
                "✖",
                key=f"del_{sid}",
                use_container_width=True,
                on_click=delete_chat,
                args=(sid,),
            )