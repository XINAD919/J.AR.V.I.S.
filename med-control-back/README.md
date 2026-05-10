# MedAI - Asistente de Adherencia a Tratamientos Médicos

Sistema de IA conversacional para ayudar a pacientes a mantener la adherencia a sus tratamientos médicos: recordatorios inteligentes, gestión de recetas médicas con OCR, búsqueda semántica RAG y notificaciones multi-canal.

## Características

- **Agente conversacional** con 7 tools: recordatorios, RAG, búsqueda web médica
- **Recordatorios inteligentes** con recurrencia completa (diaria, semanal, mensual, por intervalos)
- **Multi-canal**: Telegram, Email, Discord, Web Push
- **OCR de recetas**: sube una foto o PDF de tu receta y el agente la procesa automáticamente
- **RAG sobre documentos**: pregunta sobre tus recetas o planes médicos subidos
- **Búsqueda web médica** vía Tavily API
- **Autenticación**: registro/login con email+contraseña y OAuth
- **Multi-proveedor LLM**: Ollama (local), Anthropic Claude
- **STT/TTS** (opcional, requiere CUDA): interacción por voz offline

## Quick Start

### Requisitos

- Docker y Docker Compose
- Ollama con `qwen2.5:32b` y `nomic-embed-text`
- Sistema: `tesseract-ocr tesseract-ocr-spa poppler-utils` (para OCR)

### 1. Clonar y configurar

```bash
git clone <repo_url>
cd med-control-back

# Editar .env con tus credenciales (tiene claves pre-generadas para desarrollo)
cp .env.example .env  # o editar el .env existente
```

### 2. Levantar el stack

```bash
# Supabase completo (DB, Storage, Studio, Kong) + n8n
docker compose up -d

# Inicializar la base de datos (solo la primera vez)
docker compose exec db psql -U postgres -d postgres -f /dev/stdin < database/init.sql
```

### 3. Configurar n8n

1. Abrir [http://localhost:5678](http://localhost:5678) (admin / admin123)
2. Importar `n8n-workflow.json`
3. Configurar credencial de Postgres (`host: db`, `db: postgres`)
4. Activar el workflow

### 4. Usar el agente

```bash
# CLI (local)
source .venv/bin/activate
python main.py

# API REST
uvicorn api.main:app --reload --port 8000
curl http://localhost:8000/health
```

Ver [SETUP.md](SETUP.md) para la guía completa paso a paso.

---

## Arquitectura

```
Usuario (CLI / Frontend WebSocket)
        │
        ▼
    Agent (core/llm.py)
        ├─ Provider: OllamaProvider / AnthropicProvider
        └─ Tools (core/tools.py)
               ├─ get_current_datetime
               ├─ create_reminder   ──► n8n webhook ──► [Telegram / Email / Discord / WebPush]
               ├─ list_reminders    ──► Supabase RPC
               ├─ delete_reminders  ──► Supabase
               ├─ update_reminder   ──► Supabase
               ├─ search_knowledge_base ──► pgvector similarity
               └─ web_search        ──► Tavily API

FastAPI (api/)
    ├─ WS  /ws/chat              — streaming del agente
    ├─ POST /api/auth/*          — registro / login / OAuth
    ├─ POST /api/users/{id}/documents — upload OCR + embeddings
    ├─ GET  /api/users/{id}/reminders
    ├─ *    /api/users/{id}/channels
    └─ POST /webhooks/n8n        — callbacks de n8n

Supabase (docker-compose)
    ├─ PostgreSQL + pgvector     — DB principal
    ├─ Storage                   — bucket "prescriptions"
    └─ Studio                    — http://localhost:3000
```

---

## Estructura del proyecto

```
med-control-back/
├── core/
│   ├── llm.py              # Agent principal (multi-sesión, multi-proveedor)
│   ├── providers/          # OllamaProvider, AnthropicProvider
│   ├── tools.py            # 7 tools con function calling
│   ├── db.py               # Funciones de acceso a Supabase
│   ├── supabase_client.py  # Singleton async + create_temp_client()
│   ├── storage.py          # Supabase Storage (bucket prescriptions)
│   ├── ocr.py              # Pipeline OCR: Tesseract + LLM parsing
│   ├── embeddings.py       # Chunking + nomic-embed-text + pgvector
│   ├── stt.py              # Speech-to-Text (Whisper, opcional)
│   └── tts.py              # Text-to-Speech (Kokoro, opcional)
├── api/
│   ├── main.py             # App factory + lifecycle Supabase
│   ├── deps.py             # session_store, JWT auth, get_current_user
│   ├── models.py           # Pydantic schemas
│   └── routes/
│       ├── auth.py         # /api/auth/* (register, login, oauth)
│       ├── chat.py         # WS /ws/chat
│       ├── channels.py     # /api/users/{id}/channels
│       ├── documents.py    # /api/users/{id}/documents (OCR pipeline)
│       ├── reminders.py    # /api/users/{id}/reminders
│       ├── sessions.py     # /api/sessions/
│       └── webhooks.py     # /webhooks/n8n (callbacks n8n)
├── database/
│   └── init.sql            # Schema completo: tablas, tipos, extensiones pgvector
├── docker-compose.yml      # Supabase self-hosted + n8n
├── n8n-workflow.json       # Workflow de recordatorios
├── main.py                 # CLI del agente
├── requirements.txt
├── SETUP.md                # Guía de setup completa
└── CLAUDE.md               # Documentación técnica para Claude Code
```

---

## Stack tecnológico

| Componente | Tecnología |
|---|---|
| **LLM** | Ollama (local), Anthropic Claude |
| **Backend** | FastAPI + Python 3.12 |
| **Base de datos** | Supabase (PostgreSQL + pgvector + Storage) |
| **Automatización** | n8n (self-hosted, incluido en docker-compose) |
| **OCR** | Tesseract + Pillow + pdf2image |
| **Embeddings** | nomic-embed-text (Ollama) + pgvector |
| **Web Search** | Tavily API |
| **Auth** | JWT (PyJWT) + bcrypt |
| **Notificaciones** | Telegram (gratis), Email SMTP, Discord, OneSignal |
| **STT/TTS** | faster-whisper + Kokoro ONNX (opcional, CUDA) |
| **Deployment** | Docker Compose |

---

## Canales de notificación

| Canal | Costo | Recomendación |
|---|---|---|
| **Telegram** | Gratis | Primario (ilimitado) |
| **Email (Gmail SMTP)** | Gratis | Fallback (500/día) |
| **Discord** | Gratis | Usuarios tech |
| **Web Push (OneSignal)** | Gratis | Hasta 10k usuarios |

---

## Ejemplo de uso

```
Usuario: Recuérdame tomar ibuprofeno 600mg a las 2pm todos los días

MedAI: Claro, voy a crear el recordatorio recurrente.
       [Llama a create_reminder con recurrence_type="daily"]

       Recordatorio creado:
       - Medicamento: Ibuprofeno 600mg
       - Horario: 14:00 diariamente
       - Canal: Telegram
```

```
Usuario: Tengo aquí la receta de mi médico [sube foto]

MedAI: [Procesa OCR + embeddings en background]
       He procesado tu receta. Encontré:
       - Medicamento: Metformina 850mg
       - Dosis: 1 comprimido con las comidas
       - Duración: 3 meses
       ¿Quieres que cree los recordatorios?
```

---

## Roadmap

- [x] CLI conversacional con Ollama
- [x] Multi-proveedor LLM (Ollama, Anthropic)
- [x] Integración n8n + recordatorios multi-canal
- [x] Telegram bot (verificación automática)
- [x] Sistema de recordatorios completo con recurrencia
- [x] Docker Compose con Supabase self-hosted
- [x] OCR de recetas médicas (Tesseract + LLM parsing)
- [x] RAG con documentos médicos (pgvector + nomic-embed-text)
- [x] Autenticación JWT (registro, login, OAuth)
- [x] Herramientas de gestión: list/delete/update reminders
- [x] Búsqueda web médica (Tavily)
- [ ] Frontend en Next.js (`med-control-front/`)
- [ ] OneSignal WebPush end-to-end (necesita `ONESIGNAL_APP_ID`)
- [ ] Autenticación en WebSocket (`WS /ws/chat`)
- [ ] Tests automatizados

---

**Disclaimer:** Este sistema es una herramienta de apoyo. No reemplaza la consulta médica profesional.
