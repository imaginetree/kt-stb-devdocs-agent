# src/app/retriever.py
from typing import List, Dict, Any
import base64
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from langchain_openai import AzureOpenAIEmbeddings
from .config import settings

search = SearchClient(
    settings.search_endpoint,
    settings.search_index,
    AzureKeyCredential(settings.search_key),
)

emb = AzureOpenAIEmbeddings(
    azure_endpoint=settings.aoai_endpoint,
    api_key=settings.aoai_key,
    azure_deployment=settings.aoai_embed,
    api_version=settings.aoai_api_version,
)

def search_hybrid(query: str, k: int = 8) -> List[Dict[str, Any]]:
    qvec = emb.embed_query(query)
    vectorizedQuery = VectorizedQuery(vector=qvec, k_nearest_neighbors=k, fields="text_vector")

    results = search.search(
        search_text=query,
        vector_queries=[vectorizedQuery],
        select=["chunk", "source", "path"],
        top=k,
    )

    out: List[Dict[str, Any]] = []
    for r in results:
        out.append({
            "content": r.get("chunk"),
            "source":  r.get("source"),
            "path":    r.get("path")
        })
    return out