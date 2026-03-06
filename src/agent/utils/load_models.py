from typing import Any
from functools import lru_cache
from langchain.chat_models import init_chat_model
import os

MODEL = os.getenv("MODEL", "anthropic/claude-sonnet-4-5-20250929")
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "anthropic")
API_KEY = os.getenv("OPENAI_API_KEY", "")


@lru_cache(maxsize=16)
def load_models(
    *,
    model_provider: str = MODEL_PROVIDER,
    model: str = MODEL,
    api_key: str = API_KEY,
    **kwargs: Any,
):
    """Load models based on the provided model name and temperature."""

    if kwargs.get("temperature") is None:
        kwargs["temperature"] = 0

    chat_model = init_chat_model(
        model=model,
        model_provider=model_provider,
        # api_key=api_key,
        **kwargs,
    )
    return chat_model
