"""
Webhooks endpoint para recibir eventos de n8n.

Este módulo maneja:
- reminder.fired: cuando n8n envía una notificación exitosamente
- reminder.failed: cuando falla el envío de una notificación

El registro de canales (Telegram, email, etc.) se gestiona desde
el frontend a través de api/routes/channels.py.
"""

import logging
import os
from typing import Any, Dict

from fastapi import APIRouter, Header, HTTPException

from core.db import update_reminder_status

logger = logging.getLogger(__name__)
router = APIRouter()


def verify_api_key(x_api_key: str | None = Header(None)) -> None:
    """Verifica que la request venga de n8n con API key válida."""
    expected_key = os.getenv("WEBHOOK_SECRET")

    if not expected_key:
        # Si no hay API key configurada, permitir (solo para desarrollo)
        logger.warning("WEBHOOK_SECRET no configurada. Permitiendo acceso sin autenticación.")
        return

    if x_api_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


@router.post("/webhooks/n8n")
async def n8n_webhook(
    payload: Dict[str, Any],
    x_api_key: str | None = Header(None),
):
    """
    Recibe eventos de n8n.

    Eventos soportados:
    - reminder.fired: notificación enviada exitosamente
    - reminder.failed: error al enviar notificación
    - telegram.registered: usuario registró su chat_id de Telegram
    """
    verify_api_key(x_api_key)

    event = payload.get("event")
    data = payload.get("data", {})

    logger.info(f"Received n8n webhook: event={event}, data={data}")

    if event == "reminder.fired":
        # n8n notifica que la notificación fue enviada
        reminder_id = data.get("reminder_id")
        if not reminder_id:
            raise HTTPException(400, "Missing reminder_id in payload")

        # Actualizar estado en DB (redundante, n8n ya lo hizo, pero por si acaso)
        await update_reminder_status(reminder_id, "completed")

        logger.info(f"Reminder {reminder_id} marked as completed")

        # TODO: Si el usuario está conectado por WebSocket, notificar
        # user_id = data.get("user_id")
        # if user_id in active_websockets:
        #     await active_websockets[user_id].send_json({
        #         "type": "reminder_sent",
        #         "reminder_id": reminder_id
        #     })

        return {"status": "received", "reminder_id": reminder_id}

    elif event == "reminder.failed":
        # n8n notifica que falló el envío
        reminder_id = data.get("reminder_id")
        error = data.get("error", "Unknown error")

        if not reminder_id:
            raise HTTPException(400, "Missing reminder_id in payload")

        await update_reminder_status(reminder_id, "failed", error_message=error)

        logger.error(f"Reminder {reminder_id} failed: {error}")

        return {"status": "received", "reminder_id": reminder_id}

    else:
        logger.warning(f"Unknown event type: {event}")
        raise HTTPException(400, f"Unknown event type: {event}")


