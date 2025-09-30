from flask import Flask, request, jsonify
from flask_cors import CORS
from .config import settings
from .retriever import search_hybrid
from .rag_chain import generate_answer

app = Flask(__name__)
CORS(app)

#헬스체크용 - 서버 올리고 나서 정상적으로 작동하는지 확인
@app.get("/health")
def health():
    return jsonify({"status": "ok"})

# UI에서 호출하는 질문 처리 API
@app.post("/ask")
def ask():
    try:
        # JSON으로 요청 파라메터 파싱
        payload = request.get_json(force=True) or {}
        question = (payload.get("question") or "").strip()  # 질문
        k = int(payload.get("k") or 5)  # 검색 결과 개수
        history = payload.get("history") or []  # 대화 히스토리(최대 8개)

        if not question:
            return jsonify({"error": "question required"}), 400

        # 1) 검색 (하이브리드)
        try:
            docs = search_hybrid(question, k=k)
        except Exception as e:
            return jsonify({"error": f"search_failed: {e}"}), 500

        # 2) 생성 (LLM)
        try:
            answer = generate_answer(question, docs, history=history)
        except Exception as e:
            return jsonify({"error": f"llm_failed: {e}"}), 500

        # 3) 인용 정보 구성
        citations = [
            {
                "source": d.get("source"),
                "path": d.get("path"),
                "url": d.get("url"),
            }
            for d in docs
        ]
        # 4) 응답 반환
        return jsonify({"answer": answer, "citations": citations})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 메인
if __name__ == "__main__":
    # 서버 실행
    app.run(host=settings.host, port=settings.port)