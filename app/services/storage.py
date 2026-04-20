import json
from app.core.config import settings
from app.models.models import SessionModel


class StorageService:
    def upload_session_log_sync(self, session: SessionModel) -> str:
        if not settings.AZURE_STORAGE_CONNECTION_STRING:
            return ""
        try:
            from azure.storage.blob import BlobServiceClient, ContentSettings
            payload = {
                "session_id": session.id,
                "user_id": str(session.user_id),
                "started_at": session.started_at.isoformat(),
                "ended_at": session.ended_at.isoformat() if session.ended_at else None,
                "events": [
                    {
                        "type": e.type.value,
                        "timestamp": e.timestamp,
                        "duration_seconds": e.duration_seconds,
                    }
                    for e in (session.events or [])
                ],
            }
            client = BlobServiceClient.from_connection_string(
                settings.AZURE_STORAGE_CONNECTION_STRING
            )
            container = client.get_container_client(settings.AZURE_STORAGE_CONTAINER)
            try:
                container.create_container()
            except Exception:
                pass
            blob_name = f"{session.user_id}/{session.id}.json"
            blob_client = container.get_blob_client(blob_name)
            blob_client.upload_blob(
                json.dumps(payload, ensure_ascii=False, indent=2),
                overwrite=True,
                content_settings=ContentSettings(content_type="application/json"),
            )
            return blob_client.url
        except Exception as e:
            print(f"[StorageService] Error: {e}")
            return ""


storage_service = StorageService()
