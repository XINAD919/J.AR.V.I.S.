import asyncio
import concurrent.futures
import os
from datetime import datetime, timedelta
from typing import Optional


# ── Async helpers for new tools ────────────────────────────────────────────

async def _search_chunks(user_id: str, query_embedding: list[float]) -> list[dict]:
    from core.db import search_similar_chunks
    return await search_similar_chunks(user_id, query_embedding, top_k=3)


async def _fetch_reminders(
    user_id: str,
    status: Optional[str] = None,
    date: Optional[str] = None,
    medication: Optional[str] = None,
) -> list[dict]:
    from core.supabase_client import create_temp_client
    client = await create_temp_client()
    try:
        res = await client.rpc("get_user_reminders_grouped", {
            "p_user_id": user_id,
            "p_status": status,
            "p_date": date,
            "p_medication": medication,
        }).execute()
        return res.data or []
    finally:
        await client.aclose()


async def _delete_reminders(user_id: str, reminder_ids: list[str]) -> None:
    from core.supabase_client import create_temp_client
    client = await create_temp_client()
    try:
        await client.table("reminders").delete().eq("user_id", user_id).in_("reminder_id", reminder_ids).execute()
    finally:
        await client.aclose()


async def _fetch_notification_channels(user_id: str) -> list[dict]:
    """Cliente temporal — seguro para llamar desde cualquier thread/loop."""
    from core.supabase_client import create_temp_client
    client = await create_temp_client()
    try:
        res = await (
            client.table("user_channels")
            .select("channel, notify_id, metadata")
            .eq("user_id", user_id)
            .or_("verified.eq.true,is_primary.eq.true")
            .eq("receive_reminders", True)
            .order("is_primary", desc=True)
            .order("created_at")
            .execute()
        )
        return res.data or []
    finally:
        await client.aclose()


async def _update_user_reminder(
    reminder_id: str,
    user_id: Optional[str] = None,
    medication: Optional[str] = None,
    schedule: Optional[str] = None,
    message: Optional[str] = None,
    notes: Optional[str] = None,
) -> None:
    updates = {}
    if medication:
        updates["medication"] = medication
    if schedule:
        updates["schedule"] = schedule
    if message:
        updates["message"] = message
    if notes:
        updates["notes"] = notes
    if not updates:
        return

    from core.supabase_client import create_temp_client
    client = await create_temp_client()
    try:
        await client.table("reminders").update(updates).eq("user_id", user_id).eq("reminder_id", reminder_id).execute()
    finally:
        await client.aclose()


def get_current_datetime() -> str:
    return datetime.now().strftime("%A, %d de %B de %Y, %H:%M:%S")


def create_reminder(
    medication: str,
    schedule: str,
    message: str,
    notes: str = "",
    # Inyectados por el Agent, no vienen del LLM
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    # Recurrencia (opcionales)
    recurrence_type: Optional[str] = None,
    recurrence_days: Optional[list] = None,
    recurrence_interval: Optional[int] = None,
    recurrence_end_date: Optional[str] = None,
) -> str:
    import httpx

    if not user_id:
        return "Error: user_id no proporcionado. No se puede crear recordatorio."

    _VALID_RECURRENCE = {
        "daily", "weekdays", "weekends", "weekly",
        "monthly", "interval_days", "interval_hours",
    }
    if recurrence_type is not None:
        if recurrence_type not in _VALID_RECURRENCE:
            return (
                f"Error: recurrence_type '{recurrence_type}' no válido. "
                f"Valores aceptados: {', '.join(sorted(_VALID_RECURRENCE))}"
            )
        if not recurrence_end_date:
            return (
                "Error: recurrence_end_date es requerido cuando se especifica recurrence_type. "
                "Formato: YYYY-MM-DD."
            )
        try:
            datetime.strptime(recurrence_end_date, "%Y-%m-%d")
        except ValueError:
            return f"Error: recurrence_end_date '{recurrence_end_date}' debe tener formato YYYY-MM-DD."
    if recurrence_type == "weekly" and not recurrence_days:
        return "Error: recurrence_days es requerido para recurrence_type='weekly'. Ejemplo: [1, 3, 5]"

    webhook_url = os.getenv(
        "N8N_WEBHOOK_URL", "http://localhost:5678/webhook/medai-reminder"
    )

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            db_channels = executor.submit(
                asyncio.run, _fetch_notification_channels(user_id)
            ).result(timeout=10)
    except Exception as e:
        return f"Error al obtener canales de notificación: {e}"

    webpush_entry = {"channel": "webpush", "notify_id": user_id, "metadata": {}}
    channels_to_notify = [webpush_entry] + [
        ch for ch in db_channels if ch["channel"] != "webpush"
    ]

    # Fan-out por (schedule_time, canal) — construye payloads y dispara en paralelo
    schedule_times = [t.strip() for t in schedule.split(",")]
    errors: list[str] = []
    sent_channels: list[str] = []
    tasks: list[dict] = []

    now = datetime.now()
    for time_str in schedule_times:
        try:
            target_time = datetime.strptime(time_str, "%H:%M")
            target = now.replace(
                hour=target_time.hour, minute=target_time.minute, second=0, microsecond=0
            )
            if target <= now:
                target += timedelta(days=1)
            delay_minutes = max(1, int((target - now).total_seconds() / 60))
        except ValueError:
            errors.append(f"Horario '{time_str}': formato inválido (se esperaba HH:MM)")
            continue

        reminder_id = f"rem_{user_id.replace('-', '')[:8]}_{int(target.timestamp())}"

        for ch in channels_to_notify:
            payload: dict = {
                "user_id": user_id,
                "session_id": session_id or "unknown",
                "reminder_id": reminder_id,
                "medication": medication,
                "schedule": time_str,
                "message": message,
                "notes": notes,
                "channel": ch["channel"],
                "notify_id": ch["notify_id"],
                "delay_minutes": delay_minutes,
                "created_at": now.isoformat(),
                "is_recurring": recurrence_type is not None,
                "recurrence_type": recurrence_type or "",
                "recurrence_days": recurrence_days or [],
                "recurrence_interval": recurrence_interval or 1,
                "recurrence_end_date": recurrence_end_date or "",
                "n8n_webhook_url": webhook_url,
            }

            metadata = ch.get("metadata", {})
            if ch["channel"] == "discord" and "webhook_url" in metadata:
                payload["discord_webhook_url"] = metadata["webhook_url"]
            elif ch["channel"] == "webpush":
                onesignal_app_id = os.getenv("ONESIGNAL_APP_ID")
                if onesignal_app_id:
                    payload["onesignal_app_id"] = onesignal_app_id

            tasks.append(payload)

    def _post(p: dict) -> tuple[str, str | None]:
        try:
            httpx.post(webhook_url, json=p, timeout=10).raise_for_status()
            return p["channel"], None
        except httpx.HTTPStatusError as e:
            return p["channel"], f"{p['channel']}@{p['schedule']}: HTTP {e.response.status_code}"
        except httpx.RequestError as e:
            return p["channel"], f"{p['channel']}@{p['schedule']}: sin conexión ({e})"

    if tasks:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(tasks), 8)) as ex:
            for channel, err in ex.map(_post, tasks):
                if err is None:
                    sent_channels.append(channel)
                else:
                    errors.append(err)

    if not sent_channels:
        return (
            "Error al crear recordatorio: no se pudo contactar con n8n. "
            f"Detalles: {'; '.join(errors)}"
        )

    first_time = schedule_times[0]
    try:
        t = datetime.strptime(first_time, "%H:%M")
        now_ref = datetime.now()
        t_target = now_ref.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
        if t_target <= now_ref:
            t_target += timedelta(days=1)
        fecha_programada = t_target.strftime("%d/%m/%Y a las %H:%M")
        delay_first = max(1, int((t_target - now_ref).total_seconds() / 60))
    except ValueError:
        fecha_programada = first_time
        delay_first = 0

    canal_labels = ", ".join(sorted(set(ch.title() for ch in sent_channels)))
    recurrence_info = (
        f"\nRecurrencia: {recurrence_type} hasta {recurrence_end_date}"
        if recurrence_type
        else ""
    )
    result = (
        f"Recordatorio creado exitosamente.\n\n"
        f"Medicamento: {medication}\n"
        f"Programado para: {fecha_programada}\n"
        f"Canales: {canal_labels}"
        f"{recurrence_info}\n"
        f"Te notificaremos en {delay_first} minuto{'s' if delay_first != 1 else ''}."
    )
    if errors:
        result += f"\n\nAdvertencia: algunos envíos fallaron: {'; '.join(errors)}"
    return result


def list_reminders(
    status: Optional[str] = None,
    date: Optional[str] = None,
    medication: Optional[str] = None,
    user_id: Optional[str] = None,
) -> str:
    """
    Obtiene los recordatorios del usuario.
    Args:
        user_id:  ID del usuario (inyectado automáticamente).
        status: Estado del recordatorio (scheduled, completed, firing, failed). Por defecto 'all'.
        date: Fecha del recordatorio en formato YYYY-MM-DD. Por defecto 'all'.
        medication: Nombre del medicamento. Por defecto 'all'.
    """

    if not user_id:
        return (
            "Error: user_id no proporcionado. No se pueden obtener los recordatorios."
        )

    if status and status.lower() in ("all", "todos", "todas"):
        status = None

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            reminders = executor.submit(
                asyncio.run, _fetch_reminders(user_id, status, date, medication)
            ).result(timeout=10)
    except Exception as e:
        return f"Error al obtener recordatorios: {e}"

    if not reminders:
        return "No se encontraron recordatorios."

    from collections import defaultdict

    grouped: dict = defaultdict(lambda: None)
    for r in reminders:
        rid = r["reminder_id"]
        if grouped[rid] is None:
            grouped[rid] = {**r, "channels": [r["channel"]]}
        else:
            grouped[rid]["channels"].append(r["channel"])

    lines = []
    for r in grouped.values():
        canales = ", ".join(ch.title() for ch in r["channels"])
        lines.append(
            f"ID: {r['reminder_id']}\n"
            f"Medicamento: {r['medication']}\n"
            f"Programado para: {r['scheduled_at']}\n"
            f"Estado: {r['status']}\n"
            f"Canales: {canales}\n"
        )

    return "\n".join(lines)


def delete_reminders(
    reminder_ids: list[str],
    user_id: Optional[str] = None,
) -> str:
    """
    Elimina los recordatorios suministrados por el usuario.
    Args:
        user_id:  ID del usuario (inyectado automáticamente).
        reminder_ids: Lista de IDs de los recordatorios a eliminar.
    """

    if not user_id:
        return "Error: user_id no proporcionado. No se puede eliminar recordatorio."

    if not reminder_ids:
        return (
            "Error: reminder_ids no proporcionado. No se puede eliminar recordatorio."
        )

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(
                asyncio.run, _delete_reminders(user_id, reminder_ids)
            ).result(timeout=10)
    except Exception as e:
        return f"Error al eliminar recordatorio: {e}"

    ids_str = ", ".join(reminder_ids)

    return f"Recordatorios eliminados exitosamente: {ids_str}."


def search_knowledge_base(
    query: str,
    user_id: Optional[str] = None,
) -> str:
    """Search the user's prescription documents using semantic similarity."""
    if not user_id:
        return "Error: user_id no proporcionado. No se puede buscar en la base de conocimiento."

    import ollama

    try:
        response = ollama.embeddings(model="nomic-embed-text", prompt=query)
        query_embedding = list(response["embedding"])
    except Exception as e:
        return f"Error al generar embedding de búsqueda: {e}"

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            chunks = executor.submit(
                asyncio.run, _search_chunks(user_id, query_embedding)
            ).result(timeout=15)
    except Exception as e:
        return f"Error al buscar en base de conocimiento: {e}"

    if not chunks:
        return (
            "No se encontraron documentos médicos relevantes para esta consulta. "
            "El usuario aún no ha subido ninguna receta."
        )

    sections = []
    for c in chunks:
        sections.append(f"[{c['filename']}]\n{c['chunk_text']}")
    return "\n\n---\n\n".join(sections)


def web_search(query: str) -> str:
    """Search the web for medical information using Tavily."""
    api_key = os.getenv("TAVILY_API_KEY", "")
    if not api_key:
        return "Error: TAVILY_API_KEY no está configurado. La búsqueda web no está disponible."

    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=api_key)
        results = client.search(
            query=query,
            search_depth="basic",
            max_results=3,
        )
        items = results.get("results", [])
        if not items:
            return "No se encontraron resultados relevantes para la búsqueda."

        sections = []
        for r in items:
            sections.append(f"**{r['title']}**\n{r['content']}\nFuente: {r['url']}")
        return "\n\n---\n\n".join(sections)
    except Exception as e:
        return f"Error en búsqueda web: {e}"


def update_reminder(
    reminder_id: str,
    user_id: Optional[str] = None,
    medication: Optional[str] = None,
    schedule: Optional[str] = None,
    message: Optional[str] = None,
    notes: Optional[str] = None,
):

    if not user_id:
        return (
            "Error: user_id no proporcionado. No se puede actualizar el recordatorio."
        )

    if not reminder_id:
        return "Error: reminder_id no proporcionado. No se puede actualizar el recordatorio."

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(
                asyncio.run,
                _update_user_reminder(
                    reminder_id, user_id, medication, schedule, message, notes
                ),
            ).result(timeout=10)
    except Exception as e:
        return f"Error al actualizar recordatorio: {e}"

    return "Recordatorio actualizado exitosamente."


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_datetime",
            "description": "Obtiene la fecha y hora actual del sistema.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_reminder",
            "description": (
                "Crea un recordatorio de medicamento enviando los datos a n8n, "
                "que se encarga de programar y enviar la notificación al usuario. "
                "Úsala cuando el usuario pida recordar tomar un medicamento a una hora específica, "
                "ya sea una sola vez o de forma recurrente."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "medication": {
                        "type": "string",
                        "description": "Nombre del medicamento a recordar.",
                    },
                    "schedule": {
                        "type": "string",
                        "description": "Horario de toma en formato HH:MM. Para múltiples tomas: '08:00, 14:00, 20:00'.",
                    },
                    "message": {
                        "type": "string",
                        "description": "Mensaje personalizado y empático que n8n enviará al usuario cuando llegue la hora.",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Instrucciones especiales de toma, ej. 'con agua', 'antes de comer'.",
                    },
                    "recurrence_type": {
                        "type": "string",
                        "description": (
                            "Patrón de recurrencia. Valores: 'daily' (cada día), 'weekdays' (lun-vie), "
                            "'weekends' (sab-dom), 'weekly' (días específicos, requiere recurrence_days), "
                            "'monthly' (mismo día cada mes), 'interval_days' (cada N días, requiere recurrence_interval), "
                            "'interval_hours' (cada N horas, requiere recurrence_interval). "
                            "Si se proporciona, recurrence_end_date es obligatorio."
                        ),
                    },
                    "recurrence_days": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": (
                            "Solo para recurrence_type='weekly'. Días de la semana: "
                            "0=Dom, 1=Lun, 2=Mar, 3=Mié, 4=Jue, 5=Vie, 6=Sáb. "
                            "Ejemplo para lun/mié/vie: [1, 3, 5]."
                        ),
                    },
                    "recurrence_interval": {
                        "type": "integer",
                        "description": (
                            "Solo para 'interval_days' o 'interval_hours'. "
                            "Número de días/horas entre repeticiones."
                        ),
                    },
                    "recurrence_end_date": {
                        "type": "string",
                        "description": (
                            "Fecha de fin de la recurrencia en formato YYYY-MM-DD. "
                            "Requerido cuando se especifica recurrence_type."
                        ),
                    },
                },
                "required": ["medication", "schedule", "message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_reminders",
            "description": (
                "Obten la lista de recordatorios programados y su estado actual."
                "Estos datos vienen directamente de la base de datos."
                "Usala cuando el usuario pida listar o pregunte cuales son sus recordatorios."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Campo opcional para filtrar recordatorios por estatus. Valores válidos: scheduled, firing, completed, failed. Omitir para obtener todos.",
                    },
                    "date": {
                        "type": "string",
                        "description": "Campo opcional para filtrar recordatorios por fecha (YYYY-MM-DD).",
                    },
                    "medication": {
                        "type": "string",
                        "description": "Campo opcional para filtrar recordatorios por medicamento.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_reminders",
            "description": (
                "Elimina los recordatorios solicitados por el usuario."
                "Usala cuando el usuario pida eliminar sus recordatorios."
                "siempre pide confirmacion para realizar esta accion."
                "si el usuario no especifica los recordatorios a eliminar, muestra los disponibles para que seleccione uno o varios usando la tool de list_reminders."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "reminder_ids": {
                        "type": "array",
                        "description": "Lista de IDs de los recordatorios a eliminar.",
                    },
                },
                "required": ["reminder_ids"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": (
                "Busca en los documentos médicos del usuario (recetas, planes de medicación) "
                "usando búsqueda semántica. Úsala cuando el usuario pregunte sobre sus medicamentos, "
                "dosis o información de sus recetas subidas. "
                "No uses esta herramienta para buscar información médica general."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Pregunta o términos de búsqueda sobre los documentos del usuario.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Busca información médica actualizada en internet. "
                "Úsala cuando el usuario pregunte sobre medicamentos, efectos secundarios, "
                "interacciones o condiciones médicas y no haya información en sus documentos."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Términos de búsqueda médica en español o inglés.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_reminder",
            "description": (
                "Crea un recordatorio de medicamento enviando los datos a n8n, "
                "que se encarga de programar y enviar la notificación al usuario. "
                "Úsala cuando el usuario pida recordar tomar un medicamento a una hora específica."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "reminder_id": {
                        "type": "string",
                        "description": "ID del recordatorio a actualizar.",
                    },
                    "medication": {
                        "type": "string",
                        "description": "Nombre del medicamento a recordar.",
                    },
                    "schedule": {
                        "type": "string",
                        "description": "Horario de toma en formato HH:MM. Para múltiples tomas: '08:00, 14:00, 20:00'.",
                    },
                    "message": {
                        "type": "string",
                        "description": "Mensaje personalizado y empático que n8n enviará al usuario cuando llegue la hora.",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Instrucciones especiales de toma, ej. 'con agua', 'antes de comer'.",
                    },
                },
                "required": ["reminder_id"],
            },
        },
    },
]

_REGISTRY = {
    "get_current_datetime": get_current_datetime,
    "create_reminder": create_reminder,
    "list_reminders": list_reminders,
    "delete_reminders": delete_reminders,
    "update_reminder": update_reminder,
    "search_knowledge_base": search_knowledge_base,
    "web_search": web_search,
}


def dispatch(name: str, args: dict) -> str:
    import inspect
    fn = _REGISTRY.get(name)
    if fn is None:
        return f"Tool '{name}' not found."
    valid = inspect.signature(fn).parameters
    filtered = {k: v for k, v in args.items() if k in valid}
    return fn(**filtered)
