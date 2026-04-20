import uuid
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db, AsyncSessionLocal
from app.core.auth import current_active_user
from app.models.models import User, SessionModel, DistractionEvent, DistractionType
from app.schemas.schemas import SessionOut, DistractionEventIn, DistractionEventOut
from app.services.storage import storage_service

router = APIRouter(prefix="/sessions", tags=["sessions"])

TOAST_MESSAGES = {
    DistractionType.GAZE_AWAY:    "Desvío de mirada detectado",
    DistractionType.OUT_OF_FRAME: "No se detecta tu rostro",
}


@router.post("/", response_model=SessionOut, status_code=201)
async def create_session(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    session = SessionModel(user_id=user.id)
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return _session_to_out(session, event_count=0)


@router.get("/", response_model=list[SessionOut])
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    result = await db.execute(
        select(SessionModel)
        .where(SessionModel.user_id == user.id)
        .order_by(SessionModel.started_at.desc())
    )
    return [_session_to_out(s) for s in result.scalars().all()]


@router.get("/{session_id}", response_model=SessionOut)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    session = await _get_session_or_404(session_id, user.id, db)
    count_result = await db.execute(
        select(func.count()).where(DistractionEvent.session_id == session_id)
    )
    return _session_to_out(session, event_count=count_result.scalar() or 0)


@router.get("/{session_id}/events", response_model=list[DistractionEventOut])
async def get_session_events(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    await _get_session_or_404(session_id, user.id, db)
    result = await db.execute(
        select(DistractionEvent).where(DistractionEvent.session_id == session_id)
    )
    return result.scalars().all()


@router.post("/{session_id}/end", response_model=SessionOut)
async def end_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    session = await _get_session_or_404(session_id, user.id, db)
    if session.ended_at:
        raise HTTPException(400, "La sesión ya fue cerrada.")

    events_result = await db.execute(
        select(DistractionEvent).where(DistractionEvent.session_id == session_id)
    )
    session.events = events_result.scalars().all()
    session.ended_at = datetime.utcnow()

    blob_url = storage_service.upload_session_log_sync(session)
    if blob_url:
        session.synced = True

    await db.flush()
    return _session_to_out(session, event_count=len(session.events))


@router.websocket("/{session_id}/ws")
async def session_websocket(websocket: WebSocket, session_id: str):
    await websocket.accept()
    async with AsyncSessionLocal() as db:
        try:
            auth_data = await websocket.receive_json()
            token = auth_data.get("token", "")
            user = await _authenticate_ws(token, db)

            if not user:
                await websocket.send_json({"action": "error", "payload": {"detail": "Token inválido"}})
                await websocket.close(code=4001)
                return

            result = await db.execute(
                select(SessionModel).where(
                    SessionModel.id == session_id,
                    SessionModel.user_id == user.id,
                )
            )
            session = result.scalar_one_or_none()

            if not session or session.ended_at:
                await websocket.send_json({"action": "error", "payload": {"detail": "Sesión inválida o cerrada"}})
                await websocket.close(code=4003)
                return

            await websocket.send_json({"action": "connected", "payload": {"session_id": session_id}})

            while True:
                raw = await websocket.receive_json()
                event_in = DistractionEventIn(**raw)

                event = DistractionEvent(
                    session_id=session_id,
                    type=event_in.type,
                    timestamp=event_in.timestamp,
                    duration_seconds=event_in.duration_seconds,
                )
                db.add(event)
                await db.flush()
                await db.refresh(event)
                await db.commit()

                await websocket.send_json({
                    "action": "event_saved",
                    "payload": {
                        "event_id": event.id,
                        "toast": {
                            "type": event.type.value,
                            "message": TOAST_MESSAGES[event.type],
                        },
                    },
                })

        except WebSocketDisconnect:
            pass
        except Exception as e:
            try:
                await websocket.send_json({"action": "error", "payload": {"detail": str(e)}})
            except Exception:
                pass


async def _authenticate_ws(token: str, db: AsyncSession) -> User | None:
    from app.core.config import settings
    from jose import jwt
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            return None
        result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
        return result.scalar_one_or_none()
    except Exception:
        return None


async def _get_session_or_404(session_id: str, user_id, db: AsyncSession) -> SessionModel:
    result = await db.execute(
        select(SessionModel).where(
            SessionModel.id == session_id,
            SessionModel.user_id == user_id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Sesión no encontrada.")
    return session


def _session_to_out(session: SessionModel, event_count: int = 0) -> SessionOut:
    return SessionOut(
        id=session.id,
        started_at=session.started_at,
        ended_at=session.ended_at,
        synced=session.synced,
        event_count=event_count,
    )
