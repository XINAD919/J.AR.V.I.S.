# 🧠 J.A.R.V.I.S. — MedControl

> **Asistente de IA conversacional para adherencia a tratamientos médicos**

Sistema inteligente que ayuda a pacientes a gestionar sus medicamentos mediante recordatorios, OCR de recetas, búsqueda semántica RAG y notificaciones multi-canal.

---

## 📦 Estructura del Monorepo

```
ai-lab/
├── med-control-back/    # API + Agente IA (FastAPI, Python)
├── med-control-front/   # Interfaz web (Next.js, TypeScript)
├── TODO.md
├── LICENSE
└── README.md            ← estás aquí
```

| Proyecto | Descripción | Puerto |
|---|---|---|
| [`med-control-back`](./med-control-back/) | Backend: API REST, WebSocket, agente conversacional con tools | `:8080` |
| [`med-control-front`](./med-control-front/) | Frontend: interfaz web para pacientes | `:3000` |

---

## ✨ Características Principales

- 🤖 **Agente conversacional** con 7 tools: recordatorios, RAG, búsqueda web médica
- ⏰ **Recordatorios inteligentes** con recurrencia (diaria, semanal, mensual, por intervalos)
- 📲 **Multi-canal**: Telegram, Email, Discord, Web Push
- 📄 **OCR de recetas**: sube una foto o PDF y el agente la procesa automáticamente
- 🔍 **RAG sobre documentos**: pregunta sobre tus recetas o planes médicos subidos
- 🌐 **Búsqueda web médica** vía Tavily API
- 🔐 **Autenticación**: registro/login con email+contraseña y OAuth
- 🧩 **Multi-proveedor LLM**: Ollama (local), Anthropic Claude
- 🎙️ **STT/TTS** (opcional): interacción por voz offline

---

## 🚀 Quick Start

### Requisitos previos

- [Docker](https://docs.docker.com/get-docker/) y Docker Compose
- [Ollama](https://ollama.ai/) con modelos `qwen2.5:32b` y `nomic-embed-text`
- [Node.js](https://nodejs.org/) >= 18 y Yarn
- Python 3.12+
- Sistema: `tesseract-ocr tesseract-ocr-spa poppler-utils` (para OCR)

### 1. Clonar el repositorio

```bash
git clone https://github.com/XINAD919/J.AR.V.I.S..git
cd J.AR.V.I.S.
```

### 2. Backend

```bash
cd med-control-back

# Configurar variables de entorno
cp .env.example .env   # editar con tus credenciales

# Levantar servicios (Supabase + n8n)
docker compose up -d

# Inicializar la BD (solo la primera vez)
docker compose exec db psql -U postgres -d postgres -f /dev/stdin < database/init.sql

# Instalar dependencias Python
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Iniciar el servidor
uvicorn api.main:app --reload --port 8080
```

> 📖 Ver [med-control-back/SETUP.md](./med-control-back/SETUP.md) para la guía completa.

### 3. Frontend

```bash
cd med-control-front

# Instalar dependencias
yarn install

# Iniciar el servidor de desarrollo
yarn dev
```

Abrir [http://localhost:3000](http://localhost:3000) en el navegador.

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                │
│               http://localhost:3000                  │
└────────────────────────┬────────────────────────────┘
                         │ WebSocket / REST
                         ▼
┌─────────────────────────────────────────────────────┐
│                  Backend (FastAPI)                   │
│               http://localhost:8080                  │
│                                                     │
│  ┌─────────────┐    ┌──────────────────────────┐    │
│  │   API REST   │    │    Agente IA (LLM)       │    │
│  │  /api/auth   │    │  ┌────────────────────┐  │    │
│  │  /api/users  │◄──►│  │      7 Tools       │  │    │
│  │  /ws/chat    │    │  │  - Recordatorios    │  │    │
│  └─────────────┘    │  │  - RAG / Embeddings │  │    │
│                      │  │  - Búsqueda web     │  │    │
│                      │  │  - OCR recetas      │  │    │
│                      │  └────────────────────┘  │    │
│                      └──────────┬───────────────┘    │
└─────────────────────────────────┼────────────────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              ▼                   ▼                   ▼
     ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
     │   Supabase    │   │     n8n      │   │    Ollama    │
     │  PostgreSQL   │   │  Workflows   │   │   LLM local  │
     │  + pgvector   │   │  + Webhooks  │   │  Embeddings  │
     │  + Storage    │   └──────┬───────┘   └──────────────┘
     └──────────────┘          │
                     ┌─────────┼─────────┐
                     ▼         ▼         ▼
                 Telegram    Email    Discord
```

---

## 🛠️ Stack Tecnológico

| Capa | Tecnología |
|---|---|
| **Frontend** | Next.js 15, React, TypeScript |
| **Backend** | FastAPI, Python 3.12 |
| **LLM** | Ollama (qwen2.5:32b), Anthropic Claude |
| **Base de datos** | PostgreSQL + pgvector (Supabase self-hosted) |
| **Automatización** | n8n (self-hosted) |
| **OCR** | Tesseract + Pillow + pdf2image |
| **Embeddings** | nomic-embed-text (Ollama) + pgvector |
| **Búsqueda web** | Tavily API |
| **Auth** | JWT (PyJWT) + bcrypt |
| **Notificaciones** | Telegram, Email SMTP, Discord, OneSignal |
| **STT/TTS** | faster-whisper + Kokoro ONNX (opcional) |

---

## 📋 Roadmap

- [x] Agente conversacional con multi-proveedor LLM
- [x] Recordatorios inteligentes con recurrencia completa
- [x] Integración n8n + notificaciones multi-canal
- [x] OCR de recetas médicas
- [x] RAG con documentos médicos (pgvector)
- [x] Autenticación JWT + OAuth
- [x] Búsqueda web médica (Tavily)
- [ ] Frontend completo en Next.js
- [ ] WebPush con OneSignal
- [ ] Autenticación en WebSocket
- [ ] Tests automatizados
- [ ] Despliegue en producción

---

## 📄 Licencia

Este proyecto está bajo la licencia MIT. Ver [LICENSE](./LICENSE) para más detalles.

---

> ⚠️ **Disclaimer:** Este sistema es una herramienta de apoyo. No reemplaza la consulta médica profesional.
