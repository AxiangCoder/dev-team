from langchain.chat_models import init_chat_model


def load_models(
    *,
    model_provider: str,
    model: str,
    **kwargs: dict(str, Any),
):
    """Load models based on the provided model name and temperature."""

    if kwargs.get("temperature") is None:
        kwargs["temperature"] = 0

    chat_model = init_chat_model(
        model=model, provider=model_provider , **kwargs
    )
    return chat_model
