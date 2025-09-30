# src/ui/gradio_app.py
import os
import re
import time
import uuid
import requests
import gradio as gr

API_URL = os.getenv("API_URL", "http://localhost:8000/ask")
K_TOP = int(os.getenv("RETRIEVAL_TOPK", "5"))

_anchor_re = re.compile(r"#page=\d+", flags=re.IGNORECASE)

def _sanitize(text: str) -> str:
    if not text:
        return text
    return _anchor_re.sub("", text)

def _render_refs(citations: list[dict]) -> str:
    if not citations:
        return ""
    seen, items = set(), []
    for c in citations:
        src = (c.get("source") or "").strip()
        if src and src not in seen:
            seen.add(src)
            items.append(c)
    if not items:
        return ""
    lines = ["\n\n**참고문헌**"]
    for c in items:
        src = (c.get("source") or "문서").strip()
        url = (c.get("url") or "").strip() or (c.get("path") or "").strip()
        if url.startswith(("http://", "https://")):
            lines.append(f"- 📎 [{src}]({url})")
        else:
            lines.append(f"- 📎 {src}")
    return "\n".join(lines)

def _trim_title(s: str, limit: int = 24) -> str:
    s = (s or "").strip()
    return s if len(s) <= limit else s[:limit] + "…"

def _default_session():
    sid = str(uuid.uuid4())[:8]
    return sid, {"title": "새 채팅", "created": time.strftime("%Y-%m-%dT%H:%M:%S"), "messages": []}

def _choices_from_sessions(sessions: dict):
    """세션 최신순으로 라벨(제목 · SID) 리스트와 기본 선택 라벨을 반환"""
    items = sorted(sessions.items(), key=lambda kv: kv[1].get("created", ""), reverse=True)
    labels = [f"{meta.get('title') or '새 채팅'} · {sid}" for sid, meta in items]
    value = labels[0] if labels else None
    return labels, value

def _label_for(sessions: dict, sid: str) -> str:
    meta = sessions.get(sid, {})
    return f"{meta.get('title') or '새 채팅'} · {sid}"

def _parse_sid(choice_label: str, sessions: dict) -> str | None:
    if not choice_label:
        return None
    if "·" in choice_label:
        maybe_sid = choice_label.split("·")[-1].strip()
        if maybe_sid in sessions:
            return maybe_sid
    return choice_label if choice_label in sessions else None

# ---------------- Callbacks ----------------
def respond(message: str, messages: list[dict], sessions: dict, current_choice: str):
    sid = _parse_sid(current_choice, sessions)
    if not sid:
        # 방어적으로 새 세션 만듦
        sid, sess = _default_session()
        sessions[sid] = sess

    history = (messages or [])[-8:]

    try:
        r = requests.post(
            API_URL, json={"question": message, "k": K_TOP, "history": history}, timeout=120
        )
        r.raise_for_status()
        data = r.json()
        answer = _sanitize((data.get("answer") or "").strip() or "_(빈 응답)_")
        refs = _render_refs(data.get("citations", []))
        reply = answer + refs
    except Exception as e:
        reply = f"❌ 요청 실패: {e}"

    new_messages = (messages or []) + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": reply},
    ]

    sess = sessions.get(sid, {"title": "새 채팅", "created": "", "messages": []})
    if sess.get("title") == "새 채팅":
        sess["title"] = _trim_title(message)
    sess["messages"] = new_messages
    sessions[sid] = sess

    # ← 핵심: 제목이 바뀌었을 수 있으므로 choices와 value를 같이 갱신
    labels, _ = _choices_from_sessions(sessions)
    current_label = _label_for(sessions, sid)

    return "", new_messages, sessions, gr.update(choices=labels, value=current_label)

def new_chat(sessions: dict, current_choice: str):
    cur_sid = _parse_sid(current_choice, sessions)
    if cur_sid:
        cur = sessions.get(cur_sid)
        if cur and not cur.get("messages"):
            labels, _ = _choices_from_sessions(sessions)
            return sessions, gr.update(choices=labels, value=_label_for(sessions, cur_sid)), []

    sid, sess = _default_session()
    sessions[sid] = sess
    labels, _ = _choices_from_sessions(sessions)
    return sessions, gr.update(choices=labels, value=_label_for(sessions, sid)), []

def select_chat(choice_label: str, sessions: dict):
    sid = _parse_sid(choice_label, sessions)
    if not sid:
        return gr.update(), []
    msgs = sessions[sid].get("messages", [])
    # 선택값만 바꾸면 됨(choices는 유지)
    return gr.update(value=_label_for(sessions, sid)), msgs

def delete_chat(sessions: dict, current_choice: str):
    sid = _parse_sid(current_choice, sessions)
    if sid and sid in sessions:
        sessions.pop(sid, None)

    if not sessions:
        sid, sess = _default_session()
        sessions[sid] = sess

    labels, _ = _choices_from_sessions(sessions)
    # 최신 세션으로 이동
    latest_label = labels[0]
    latest_sid = _parse_sid(latest_label, sessions)
    msgs = sessions[latest_sid].get("messages", []) if latest_sid else []

    return sessions, gr.update(choices=labels, value=latest_label), msgs

def clear_session_messages(sessions: dict, current_choice: str):
    sid = _parse_sid(current_choice, sessions)
    if sid in sessions:
        sessions[sid]["messages"] = []
        return sessions, [], gr.update(value=_label_for(sessions, sid))
    return sessions, [], gr.update()

# ---------------- UI ----------------
init_sid, init_sess = _default_session()
init_sessions = {init_sid: init_sess}
init_labels, init_value = _choices_from_sessions(init_sessions)

with gr.Blocks(title="KT STB 개발 도우미") as demo:
    gr.Markdown("## 🛠️ KT STB 개발 도우미\nKT OIPF / olleh tv / SCTE-35 / Cue-Tone 문서 기반 개발 도움 챗봇")

    sessions_state = gr.State(init_sessions)

    with gr.Row(equal_height=True):
        with gr.Column(scale=1, min_width=280):
            gr.Markdown("### 채팅 히스토리")
            session_radio = gr.Radio(choices=init_labels, value=init_value, label="세션 목록")
            with gr.Row():
                btn_new = gr.Button("➕ 새 채팅", variant="primary")
                btn_del = gr.Button("✖ 삭제", variant="stop")

        with gr.Column(scale=4):
            chatbot = gr.Chatbot(type="messages", height=520, label="대화", value=[])
            msg = gr.Textbox(placeholder="무엇을 도와드릴까요? 예) Mosaic Window 예제", lines=3, autofocus=True)
            with gr.Row():
                btn_send = gr.Button("질문하기", variant="primary")
                btn_clear = gr.Button("이 세션 비우기", variant="secondary")

    # Wiring
    btn_new.click(
        new_chat,
        inputs=[sessions_state, session_radio],
        outputs=[sessions_state, session_radio, chatbot],
    )

    session_radio.change(
        select_chat,
        inputs=[session_radio, sessions_state],
        outputs=[session_radio, chatbot],
    )

    btn_del.click(
        delete_chat,
        inputs=[sessions_state, session_radio],
        outputs=[sessions_state, session_radio, chatbot],
    )

    btn_clear.click(
        clear_session_messages,
        inputs=[sessions_state, session_radio],
        outputs=[sessions_state, chatbot, session_radio],
        queue=False,
    )

    msg.submit(
        respond,
        inputs=[msg, chatbot, sessions_state, session_radio],
        outputs=[msg, chatbot, sessions_state, session_radio],
    )
    btn_send.click(
        respond,
        inputs=[msg, chatbot, sessions_state, session_radio],
        outputs=[msg, chatbot, sessions_state, session_radio],
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0")