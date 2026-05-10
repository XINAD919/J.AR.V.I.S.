from collections.abc import AsyncGenerator

from ollama import AsyncClient

from .base import BaseProvider


class OllamaProvider(BaseProvider):
    def __init__(self, model: str = "qwen2.5:32b", host: str = "http://localhost:11434"):
        self.model = model
        self._client = AsyncClient(host=host)

    @property
    def supports_tools(self) -> bool:
        return True

    async def stream(
        self,
        messages: list[dict],
        tools: list[dict],
    ) -> AsyncGenerator[dict, None]:
        response = await self._client.chat(
            model=self.model,
            messages=messages,
            stream=True,
            think=False,
            tools=tools or [],
        )

        tool_calls: list = []
        async for chunk in response:
            if chunk.message.content:
                yield {"type": "token", "content": chunk.message.content}
            if chunk.message.tool_calls:
                tool_calls.extend(chunk.message.tool_calls)

        if tool_calls:
            yield {
                "type": "tool_calls",
                "calls": [
                    {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments or {},
                    }
                    for tc in tool_calls
                ],
            }
