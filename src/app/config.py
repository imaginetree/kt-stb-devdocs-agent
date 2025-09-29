from dataclasses import dataclass
from dotenv import load_dotenv
import os

load_dotenv()

@dataclass
class Settings:
    aoai_endpoint: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    aoai_key: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    aoai_api_version: str = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
    aoai_chat: str = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4.1-mini")
    aoai_embed: str = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")

    search_endpoint: str = os.getenv("AZURE_SEARCH_ENDPOINT", "")
    search_key: str = os.getenv("AZURE_SEARCH_API_KEY", "")
    search_index: str = os.getenv("AZURE_SEARCH_INDEX", "rag-1759110249946")

    host: str = os.getenv("FLASK_HOST", os.getenv("HOST", "0.0.0.0"))
    port: int = int(os.getenv("FLASK_PORT", os.getenv("PORT", "8000")))

settings = Settings()
