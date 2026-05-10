from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from core.db import get_user_reminders
from deps import CurrentUser, get_current_user

router = APIRouter()


class ReminderResponse(BaseModel):
    reminder_id: str
    medication: str
    schedule: str
    message: str
    notes: Optional[str]
    channels: list[str]
    scheduled_at: str
    fired_at: Optional[str]
    status: str
    created_at: str


@router.get("/users/{user_id}/reminders", response_model=list[ReminderResponse])
async def list_reminders(
    user_id: str,
    status: Optional[str] = None,
    date: Optional[str] = None,
    medication: Optional[str] = None,
    current_user: CurrentUser = Depends(get_current_user),
):
    if user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="No autorizado")
    try:
        rows = await get_user_reminders(user_id, status=status, date=date, medication=medication)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    def fmt(dt) -> Optional[str]:
        if dt is None:
            return None
        if isinstance(dt, datetime):
            return dt.isoformat()
        return str(dt)

    return [
        ReminderResponse(
            reminder_id=r["reminder_id"],
            medication=r["medication"],
            schedule=r["schedule"],
            message=r["message"],
            notes=r.get("notes"),
            channels=list(r["channels"]),
            scheduled_at=fmt(r["scheduled_at"]),
            fired_at=fmt(r.get("fired_at")),
            status=str(r["status"]),
            created_at=fmt(r["created_at"]),
        )
        for r in rows
    ]
