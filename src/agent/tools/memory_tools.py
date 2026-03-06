"""Define he agent's tools."""

import uuid
from typing import Annotated

from langchain_core.tools import InjectedToolArg
from langgraph.store.base import BaseStore


async def upsert_memory(
    content: str,
    context: str,
    *,
    memory_id: uuid.UUID | None = None,
    # Hide these arguments from the model.
    namescape: Annotated[tuple[str, ...], {"__template_metadata__": {"kind": "hidden"}}],
    store: Annotated[BaseStore, InjectedToolArg],
    **kwargs,
):
    """Upsert a memory in the database.

    If a memory conflicts with an existing one, then just UPDATE the
    existing one by passing in memory_id - don't create two memories
    that are the same. If the user corrects a memory, UPDATE it.

    Args:
        content: The main content of the memory. For example:
            "User expressed interest in learning about French."
        context: Additional context for the memory. For example:
            "This was mentioned while discussing career options in Europe."
        memory_id: ONLY PROVIDE IF UPDATING AN EXISTING MEMORY.
        The memory to overwrite.
    """
    mem_id = memory_id or uuid.uuid4()
    storage_value = {"content": content, "context": context}
    if "base64Image" in kwargs:
        storage_value["base64Image"] = kwargs["base64Image"]

    await store.aput(
        namescape,
        key=str(mem_id),
        value=storage_value
    )
    return f"Stored memory {mem_id}"
