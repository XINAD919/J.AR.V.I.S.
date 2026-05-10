import os

from .base import BaseProvider
from .ollama import OllamaProvider

_PROVIDERS: dict[str, type[BaseProvider]] = {
    "ollama": OllamaProvider,
}

try:
    from .anthropic import AnthropicProvider
    _PROVIDERS["anthropic"] = AnthropicProvider
except ImportError:
    pass


def create_provider(name: str | None = None, model: str | None = None) -> BaseProvider:
    name = name or os.getenv("LLM_PROVIDER", "ollama")
    cls = _PROVIDERS.get(name)
    if cls is None:
        raise ValueError(f"Proveedor desconocido: '{name}'. Disponibles: {list(_PROVIDERS)}")

    kwargs: dict = {}
    if model:
        kwargs["model"] = model
    elif llm_model := os.getenv("LLM_MODEL"):
        kwargs["model"] = llm_model

    if name == "ollama":
        if host := os.getenv("OLLAMA_HOST"):
            kwargs["host"] = host
    elif api_key := os.getenv(f"{name.upper()}_API_KEY"):
        kwargs["api_key"] = api_key

    return cls(**kwargs)
