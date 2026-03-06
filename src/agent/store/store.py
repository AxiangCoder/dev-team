from langchain.embeddings import init_embeddings
from langgraph.store.memory import InMemoryStore
import os

store = InMemoryStore(
    index={
        "embed": init_embeddings(
            model=os.getenv("EMBEDDING_MODEL", ""),
            provider=os.getenv("EMBEDDING_PROVIDER", ""),
            api_key=os.getenv("OPENAI_EMBEDDING_KEY", ""),
        ),  # Embedding provider
        "dims": 1536,  # Embedding dimensions
        "fields": ["food_preference", "$"],  # Fields to embed
    }
)
