from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator


class BaseProvider(ABC):
    """
    Contrato que todo proveedor LLM debe cumplir.

    El método `stream` yield dicts con dos posibles formas:
      - {"type": "token",      "content": str}
      - {"type": "tool_calls", "calls": [{"name": str, "arguments": dict}]}
    """

    @abstractmethod
    async def stream(
        self,
        messages: list[dict],
        tools: list[dict],
    ) -> AsyncGenerator[dict, None]:
        """Envía mensajes y yield tokens o tool_calls uno a uno."""
        ...

    @property
    @abstractmethod
    def supports_tools(self) -> bool:
        """Indica si el proveedor soporta function calling."""
        ...
