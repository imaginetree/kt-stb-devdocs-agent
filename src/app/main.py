# src/app/main.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from .config import settings
from .retriever import search_hybrid
from .rag_chain import generate_answer

app = Flask(__name__)
CORS(app)

@app.get("/health")
def health():
    return jsonify({"status": "ok"})

@app.post("/ask")
def ask():
    try:
        payload = request.get_json(force=True) or {}
        q = (payload.get("question") or "").strip()
        k = int(payload.get("k") or 8)
        history = payload.get("history") or []

        if not q:
            return jsonify({"error": "question required"}), 400

        # 1) 검색 (하이브리드)
        try:
            docs = search_hybrid(q, k=k)
        except Exception as e:
            return jsonify({"error": f"search_failed: {e}"}), 500

        # 2) 생성 (LLM)
        try:
            answer = generate_answer(q, docs, history=history)
        except Exception as e:
            return jsonify({"error": f"llm_failed: {e}"}), 500

        # 3) 인용 정보 구성: page 제거 (문서 링크만 사용)
        citations = [
            {
                "source": d.get("source"),
                "path": d.get("path"),
                "url": d.get("url"),
            }
            for d in docs
        ]

        return jsonify({"answer": answer, "citations": citations})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host=settings.host, port=settings.port)