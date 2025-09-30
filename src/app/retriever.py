from typing import List, Dict, Any
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from langchain_openai import AzureOpenAIEmbeddings
from .config import settings

# SearchClient 생성 및 초기화
searchClient = SearchClient(
    settings.search_endpoint,
    settings.search_index,
    AzureKeyCredential(settings.search_key),
)

# Embedding 모델 초기화
openAiembedding = AzureOpenAIEmbeddings(
    azure_endpoint=settings.aoai_endpoint,
    api_key=settings.aoai_key,
    azure_deployment=settings.aoai_embed,
    api_version=settings.aoai_api_version,
)

# 하이브리드 검색
def search_hybrid(query: str, k: int = 8) -> List[Dict[str, Any]]:
    qvec = openAiembedding.embed_query(query)   # query 벡터화
    vectorizedQuery = VectorizedQuery(vector=qvec, k_nearest_neighbors=k, fields="text_vector") # 벡터 검색 조건

    results = searchClient.search(
        search_text=query,                      # 키워드 검색 조건
        vector_queries=[vectorizedQuery],       # 벡터 검색 조건
        select=["chunk", "source", "path"],     # 반환 필드
        top=k,                                  # 최대 검색 개수
    )

    # 검색 결과를 사용하기 편하게 가공
    out: List[Dict[str, Any]] = []
    for r in results:
        out.append({
            "content": r.get("chunk"),      # 문서 내용
            "source":  r.get("source"),     # 문서 출처
            "path":    r.get("path")        # 문서 경로
        })
    return out