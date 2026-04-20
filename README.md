# Backend — Detector de Distracciones

## Stack
- FastAPI + Uvicorn
- FastAPI Users (auth JWT)
- SQLAlchemy 2 (async) + pyodbc → Azure SQL
- Azure Blob Storage (sincronización de sesiones)
- Docker + Railway

## Estructura
```
app/
├── core/
│   ├── config.py       # Settings con pydantic-settings
│   ├── database.py     # Engine async + sesión
│   └── auth.py         # FastAPI Users + JWT
├── models/
│   └── models.py       # User, SessionModel, DistractionEvent
├── schemas/
│   └── schemas.py      # Pydantic schemas
├── routers/
│   └── sessions.py     # REST + WebSocket
├── services/
│   └── storage.py      # Azure Blob sync
└── main.py             # App entry point
```

## Endpoints principales

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | /auth/register | Registro de usuario |
| POST | /auth/jwt/login | Login → JWT |
| POST | /sessions/ | Crear sesión |
| GET | /sessions/ | Listar sesiones del usuario |
| GET | /sessions/{id} | Detalle de sesión |
| GET | /sessions/{id}/events | Eventos de distracción |
| POST | /sessions/{id}/end | Cerrar sesión + sync Azure |
| WS | /sessions/{id}/ws | WebSocket de eventos en tiempo real |

## WebSocket — Protocolo

### 1. Autenticarse (primer mensaje)
```json
{ "token": "<JWT>" }
```

### 2. Enviar evento de distracción
```json
{
  "type": "desvío de mirada",
  "timestamp": "2026-04-13|14:35:22",
  "duration_seconds": 6.3
}
```

### 3. Respuesta del servidor
```json
{
  "action": "event_saved",
  "payload": {
    "event_id": 42,
    "toast": {
      "type": "desvío de mirada",
      "message": "Desvío de mirada detectado"
    }
  }
}
```

## Despliegue en Railway

### 1. Variables de entorno en Railway
Copia `.env.example` y configura en Railway → Variables:
```
DATABASE_URL
SECRET_KEY
AZURE_STORAGE_CONNECTION_STRING
AZURE_STORAGE_CONTAINER
ALLOWED_ORIGINS
```

### 2. Deploy desde CLI
```bash
npm install -g @railway/cli
railway login
railway init
railway up
```

### 3. Deploy desde GitHub
1. Conecta tu repo en railway.app
2. Railway detecta el Dockerfile automáticamente
3. Agrega las variables de entorno en el dashboard

## Desarrollo local
```bash
cp .env.example .env
# Edita .env con tus credenciales

# Opción A: con Docker
docker build -t detector-api .
docker run -p 8000:8000 --env-file .env detector-api

# Opción B: sin Docker (SQLite para desarrollo)
# Cambia DATABASE_URL=sqlite+aiosqlite:///./dev.db en .env
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Docs interactivas
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
