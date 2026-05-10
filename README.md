# MedAI - Asistente de Adherencia a Tratamientos Médicos

Sistema completo de IA conversacional para ayudar a pacientes a mantener la adherencia a sus tratamientos médicos mediante recordatorios inteligentes y gestión de documentación.

## 🎯 Características

- 🤖 **Agente conversacional** multimodal (texto, voz)
- 💊 **Recordatorios inteligentes** de medicación
- 📱 **Multi-canal** - Telegram, Email, Discord, Web Push (100% gratis)
- 🔄 **n8n integration** para automatizaciones complejas
- 📄 **RAG** - sube recetas/planes médicos y pregunta sobre ellos
- 🌐 **Multi-proveedor LLM** - Ollama (local), Claude, GPT, Gemini
- 🗣️ **STT/TTS** - interacción por voz (offline)
- 💾 **PostgreSQL** con búsqueda vectorial (pgvector)

## 🚀 Quick Start

### Requisitos

- Docker y Docker Compose
- Ollama con `qwen2.5:32b` (o cualquier otro modelo)

### 1. Clonar y configurar

```bash
git clone <repo_url>
cd ai-lab

# Crear archivo .env (ver SETUP.md para detalles)
cp .env.example .env
# Editar .env con tus credenciales
```

### 2. Levantar servicios

```bash
# Levantar PostgreSQL, n8n y FastAPI
docker compose up -d

# Ver logs
docker compose logs -f
```

### 3. Configurar Telegram (opcional pero recomendado)

1. Crear bot con [@BotFather](https://t.me/botfather)
2. Copiar el token
3. En n8n ([http://localhost:5678](http://localhost:5678)):
   - Importar workflows de `n8n-*.json`
   - Configurar credencial de Telegram
   - Activar workflows
4. Enviar `/start` a tu bot

### 4. Usar el agente

```bash
# CLI (local)
source .venv/bin/activate
python main.py

# API (http://localhost:8000/docs)
curl http://localhost:8000/health
```

**¡Listo!** 🎉 Ahora puedes crear recordatorios desde la CLI y recibirlos en Telegram.

---

## 📚 Documentación

| Archivo | Descripción |
|---------|-------------|
| **[SETUP.md](SETUP.md)** | Guía paso a paso completa |
| **[ROADMAP.md](ROADMAP.md)** | Plan de desarrollo (Frontend, n8n, RAG) |
| **[docs/FREE_NOTIFICATIONS_SETUP.md](docs/FREE_NOTIFICATIONS_SETUP.md)** | Configurar canales gratuitos (Telegram, Email, etc.) |
| **[docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md)** | Schema de PostgreSQL con pgvector |
| **[docs/INTEGRATION_PLAN.md](docs/INTEGRATION_PLAN.md)** | Arquitectura completa del sistema |
| **[docs/COST_COMPARISON.md](docs/COST_COMPARISON.md)** | Análisis de costos por canal |

---

## 🏗️ Arquitectura

```
┌──────────────┐
│  Usuario     │
│  (CLI/Web)   │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────┐
│  Agent (core/llm.py)         │
│  ├─ Provider (LLM)           │
│  ├─ Tools                    │
│  │  ├─ create_reminder()    │───┐
│  │  └─ search_knowledge()   │   │
│  └─ RAG Module               │   │
└──────────────────────────────┘   │
                                   │ HTTP
                                   ▼
                         ┌─────────────────┐
                         │  n8n Workflows  │
                         │  ├─ Reminders   │
                         │  └─ Telegram    │
                         └────────┬────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
              ┌─────▼────┐  ┌────▼────┐  ┌────▼────┐
              │ Telegram │  │  Email  │  │ Discord │
              │   API    │  │  SMTP   │  │ Webhook │
              └──────────┘  └─────────┘  └─────────┘
```

---

## 🗂️ Estructura del Proyecto

```
ai-lab/
├── core/                   # Motor del agente
│   ├── llm.py             # Agent principal
│   ├── providers/         # Ollama, Anthropic, OpenAI, Gemini
│   ├── tools.py           # Function calling (n8n, RAG)
│   ├── db.py              # PostgreSQL queries
│   ├── stt.py             # Speech-to-Text (Whisper)
│   └── tts.py             # Text-to-Speech (Kokoro)
├── api/                   # FastAPI backend
│   ├── main.py
│   └── routes/
│       ├── webhooks.py    # n8n callbacks
│       └── channels.py    # Gestión de canales
├── database/
│   └── init.sql           # Schema PostgreSQL + pgvector
├── docs/                  # Documentación detallada
├── n8n-*.json             # Workflows de n8n
├── docker-compose.yml     # Stack completo
├── main.py                # CLI del agente
├── SETUP.md               # Setup paso a paso
└── README.md              # Este archivo
```

---

## 💡 Ejemplo de Uso

### CLI

```
Usuario: Recuérdame tomar ibuprofeno 600mg a las 2pm

J.A.R.V.I.S: Claro, voy a crear el recordatorio.

[Llama a create_reminder tool]

✅ Recordatorio creado exitosamente.

💊 Medicamento: Ibuprofeno 600mg
🕐 Programado para: 13/04/2026 a las 14:00
📱 Canal: Telegram
⏱️ Te notificaré en 120 minutos.
```

### A las 2pm, recibes en Telegram:

```
🔔 Recordatorio de Medicación

💊 Ibuprofeno 600mg
🕐 Hora: 14:00

Hora de tomar tu ibuprofeno

Con agua, después de comer

[✅ Ya lo tomé] [⏰ Posponer 10 min]

📅 reminder.ics (archivo adjunto)
```

---

## 🛠️ Stack Tecnológico

| Componente | Tecnología |
|------------|-----------|
| **LLM** | Ollama (local), Anthropic, OpenAI, Gemini |
| **Backend** | FastAPI + Python 3.12 |
| **Database** | PostgreSQL 16 + pgvector |
| **Automation** | n8n |
| **Notificaciones** | Telegram (gratis), Email SMTP, Discord, OneSignal |
| **STT** | faster-whisper (Whisper large-v3) |
| **TTS** | Kokoro ONNX |
| **Deployment** | Docker Compose |

---

## 📊 Canales de Notificación

| Canal | Costo | Límite | Recomendación |
|-------|-------|--------|---------------|
| **Telegram** | $0/mes | Ilimitado | ⭐⭐⭐⭐⭐ Primario |
| **Email (Gmail)** | $0/mes | 500/día | ⭐⭐⭐⭐ Fallback |
| **Discord** | $0/mes | Ilimitado | ⭐⭐⭐ Usuarios tech |
| **Web Push (OneSignal)** | $0/mes | 10k usuarios | ⭐⭐⭐ Web-only |
| WhatsApp | ❌ $1080/mes | 1000 users | No viable |
| SMS | ❌ $9600/mes | 1000 users | No viable |

Ver [docs/COST_COMPARISON.md](docs/COST_COMPARISON.md) para análisis completo.

---

## 🔜 Roadmap

- [x] CLI conversacional con Ollama
- [x] Multi-proveedor LLM (Ollama, Claude, GPT, Gemini)
- [x] Integración n8n + PostgreSQL
- [x] Telegram bot registration
- [x] Sistema de recordatorios completo
- [x] Docker Compose stack
- [ ] Frontend en Next.js
- [ ] RAG con documentos médicos (PDFs)
- [ ] Autenticación JWT
- [ ] Dashboard de recordatorios
- [ ] Tests automatizados
- [ ] Deploy en producción

Ver [ROADMAP.md](ROADMAP.md) para detalles.

---

## 🤝 Contribuir

1. Fork el repo
2. Crea una branch (`git checkout -b feature/amazing-feature`)
3. Commit tus cambios (`git commit -m 'Add amazing feature'`)
4. Push a la branch (`git push origin feature/amazing-feature`)
5. Abre un Pull Request

---

## 📝 Licencia

MIT License - ver [LICENSE](LICENSE) para detalles.

---

## 🙏 Agradecimientos

- [Ollama](https://ollama.ai) - LLM local
- [n8n](https://n8n.io) - Workflow automation
- [Anthropic](https://anthropic.com) - Claude API
- [FastAPI](https://fastapi.tiangolo.com) - Web framework
- [pgvector](https://github.com/pgvector/pgvector) - Vector similarity

---

## 📧 Contacto

Creado por Daniel

---

**⚠️ Disclaimer:** Este sistema es una herramienta de apoyo. No reemplaza la consulta médica profesional. Siempre consulta con tu médico antes de tomar decisiones sobre tu tratamiento.
