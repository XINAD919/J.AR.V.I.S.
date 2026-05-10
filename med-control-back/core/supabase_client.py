"""
Singleton del cliente async de Supabase.
Inicializado una vez en startup de FastAPI; los tools.py usan create_temp_client().
"""

import os
from typing import Optional

from supabase._async.client import AsyncClient, create_client


_client: Optional[AsyncClient] = None


async def init_supabase_client() -> AsyncClient:
    global _client
    if _client is not None:
        return _client
    _client = await create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )
    return _client


async def close_supabase_client() -> None:
    global _client
    _client = None


def get_supabase() -> AsyncClient:
    """Getter síncrono para usar dentro de request handlers (después del startup)."""
    if _client is None:
        raise RuntimeError("Supabase client not initialized. Call init_supabase_client() first.")
    return _client


class _TempClient:
    """Wrapper de cliente temporal con contexto de cierre para tools.py."""

    def __init__(self, client: AsyncClient):
        self._client = client

    def __getattr__(self, name: str):
        return getattr(self._client, name)

    async def aclose(self) -> None:
        pass  # supabase 2.x no expone cierre explícito; el GC limpia httpx


async def create_temp_client() -> _TempClient:
    """Cliente temporal para asyncio.run() en ThreadPoolExecutor (tools.py)."""
    client = await create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )
    return _TempClient(client)
