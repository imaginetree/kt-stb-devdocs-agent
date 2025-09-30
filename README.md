# KT STB DevDocs Agent

KT 셋톱박스(STB) 관련 개발 문서를 Azure OpenAI + Azure AI Search 기반으로 검색·요약해 주는 문서 어시스턴트입니다. 하이브리드 검색으로 관련 문서를 찾고, LLM이 한국어로 핵심 절차와 샘플 코드를 정리해 줍니다.

## 주요 기능
- **문서 검색**: Azure AI Search 하이브리드(Vector + Keyword) 검색으로 규격서/가이드를 탐색.
- **LLM 응답 생성**: Azure OpenAI Chat 모델이 한국어 답변, 절차, 샘플 코드를 생성.
- **근거 문서 제시**: 응답과 함께 참조한 문서명을 UI에서 하이퍼링크로 제공.
- **대화 히스토리 유지**: 최근 대화 8개를 기반으로 후속 질의 맥락 반영.
- **Streamlit UI**: 브라우저에서 챗 UI로 질문·응답을 확인하고 참고문헌 확인.

## 시스템 구성
| 구성 요소 | 경로 | 설명 |
| --- | --- | --- |
| Flask API | `src/app/main.py` | `/ask` 엔드포인트에서 검색→생성 워크플로우 실행 |
| Retriever | `src/app/retriever.py` | Azure AI Search 하이브리드 검색 래퍼 |
| RAG Chain | `src/app/rag_chain.py` | 검색 결과 컨텍스트 구성 후 Azure Chat 호출 |
| Prompt | `src/app/prompts/system_ko.md` | 한국어 시스템 프롬프트(응답 규칙) |
| Streamlit UI | `src/ui/streamlit_app.py` | 웹 UI, 대화 세션/참고문헌 렌더링 |
| 문서 저장소 | `docs/` | STB 관련 PDF 문서 원본 |

## 요구 사항
- Python 3.11 이상
- Azure OpenAI 리소스 (Chat, Embedding 배포)
- Azure AI Search 리소스 및 인덱스 (문서 업로드/색인 완료)
- 선택: [uv](https://github.com/astral-sh/uv) (가상환경 및 패키지 관리 용도)

## 빠른 시작
```bash
# 1. uv 설치
pip install uv

# 2. 가상환경 생성 및 활성화
uv venv .venv
source .venv/bin/activate

# 3. 의존성 설치
uv sync          # uv.lock 기반 설치

# 4. 환경 변수 파일 준비
touch .env
```

## 환경 변수
루트에 `.env` 파일을 두고 아래 값을 채운다.

| 키 | 설명 |
| --- | --- |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI 리소스 엔드포인트 URL |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API Key |
| `AZURE_OPENAI_API_VERSION` | 사용할 API 버전 (예: `2024-12-01-preview`) |
| `AZURE_OPENAI_CHAT_DEPLOYMENT` | Chat 모델 배포 이름 (예: `gpt-4.1-mini`) |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | Embedding 모델 배포 이름 |
| `AZURE_SEARCH_ENDPOINT` | Azure AI Search 엔드포인트 |
| `AZURE_SEARCH_API_KEY` | Azure AI Search 키 |
| `AZURE_SEARCH_INDEX` | 검색 대상 인덱스 이름 |
| `FLASK_HOST` / `FLASK_PORT` | 백엔드 바인딩 주소/포트 (기본 `0.0.0.0:8000`) |
| `API_URL` | Streamlit UI가 호출할 API 주소 (기본 `http://localhost:8000/ask`) |
| `RETRIEVAL_TOPK` | 검색 상위 문서 수 (기본 5) |

## 실행 방법
### 1. 백엔드 API (Flask)
```bash
uv run python -m src.app.main
# 또는
python -m src.app.main
```

### 2. Streamlit UI
```bash
uv run streamlit run src/ui/streamlit_app.py
# 또는
streamlit run src/ui/streamlit_app.py
```

## 프로젝트 구조
```
.
├── docs/                      # STB 관련 PDF 원문(참고용)
├── setting_docs/              # 구축 단계별 가이드(README랑 겹침..)
├── src/
│   ├── app/
│   │   ├── main.py            # Flask 엔트리포인트
│   │   ├── config.py          # .env 로드 및 설정 객체
│   │   ├── retriever.py       # Azure Search 하이브리드 검색
│   │   ├── rag_chain.py       # 검색 컨텍스트 구성 + LLM 호출
│   │   └── prompts/system_ko.md
│   └── ui/
│       └── streamlit_app.py   # 챗 UI
├── pyproject.toml             # 프로젝트 메타/의존성
├── uv.lock                    # uv 잠금파일
└── README.md
```

## Azure AI Search 색인 준비 메모
1. Azure Storage 컨테이너에 STB 규격서 PDF 업로드.(/docs/*)
2. Azure AI Search에서 Data Source → Skillset → Index를 생성하고 `source`, `path` 필드를 인덱스에 포함.
3. 포털의 "RAG" 템플릿으로 인덱싱 후 필요한 경우 재색인.
4. 인덱스 이름과 관리 키를 `.env`에 입력

## 커스터마이징
- 프롬프트 수정: `src/app/prompts/system_ko.md`에서 응답 스타일과 정책을 조정합니다.
- 검색 파라미터: `RETRIEVAL_TOPK`, `search_hybrid()` 함수의 `max_chars` 등으로 응답 길이와 맥락을 제어 가능.
- UI 확장: Streamlit 컴포넌트를 활용해 답변 요약, 필터 등을 추가할 수 있다.

## 시퀀스 다이어그램
![시퀀스 다이어그램](setting_docs/sequence.png)