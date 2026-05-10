# MedAI - Guía de Setup Completa

Esta guía te llevará paso a paso desde cero hasta tener todo el sistema funcionando con n8n, PostgreSQL y canales de notificación gratuitos.

---

## 📋 Índice

1. [Requisitos Previos](#requisitos-previos)
2. [Configuración Básica](#configuración-básica)
3. [Base de Datos](#base-de-datos)
4. [n8n Setup](#n8n-setup)
5. [Telegram Bot](#telegram-bot)
6. [Probar el Sistema](#probar-el-sistema)
7. [Troubleshooting](#troubleshooting)

---

## Requisitos Previos

### Software necesario

- **Docker** y **Docker Compose** (recomendado) o:
  - Python 3.12+
  - PostgreSQL 16+
  - Node.js 18+ (para n8n)
- **Ollama** corriendo localmente con el modelo `qwen2.5:32b`

### Verificar instalaciones

```bash
docker --version          # Docker version 24.0+
docker compose version    # Docker Compose version 2.0+
python --version          # Python 3.12+
```

---

## Configuración Básica

### 1. Clonar/Preparar el proyecto

```bash
cd /home/daniel/projects/ai-lab
```

### 2. Crear archivo `.env`

```bash
cat > .env << 'EOF'
# =============================================================================
# Database
# =============================================================================
DATABASE_URL=postgresql://medai:medai_password@localhost:5432/medai

# =============================================================================
# n8n
# =============================================================================
N8N_WEBHOOK_URL=http://localhost:5678/webhook/medai-reminder

# =============================================================================
# Security
# =============================================================================
API_KEY=secret_api_key_change_me_in_production

# =============================================================================
# LLM Provider
# =============================================================================
LLM_PROVIDER=ollama
OLLAMA_HOST=http://localhost:11434

# Para usar otros providers (opcional):
# ANTHROPIC_API_KEY=sk-ant-...
# OPENAI_API_KEY=sk-...

# =============================================================================
# CORS (para frontend)
# =============================================================================
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# =============================================================================
# Email (opcional, solo si vas a usar email como canal)
# =============================================================================
# Gmail SMTP
# SMTP_HOST=smtp.gmail.com
# SMTP_PORT=587
# SMTP_USER=tubot@gmail.com
# SMTP_PASSWORD=tu_app_password_aqui

# o Resend
# RESEND_API_KEY=re_...

# =============================================================================
# OneSignal (opcional, para Web Push)
# =============================================================================
# ONESIGNAL_APP_ID=abc123...
# ONESIGNAL_REST_API_KEY=xyz789...
EOF
```

### 3. Verificar que Ollama esté corriendo

```bash
# Verificar que Ollama responde
curl http://localhost:11434/api/tags

# Si no tienes el modelo, descargarlo
ollama pull qwen2.5:32b
```

---

## Base de Datos

### Opción A: Usar Docker Compose (Recomendado)

```bash
# Levantar solo PostgreSQL
docker compose up -d postgres

# Esperar a que esté listo
docker compose logs -f postgres
# Ctrl+C cuando veas "database system is ready to accept connections"
```

La base de datos se inicializa automáticamente con el script `database/init.sql`.

### Opción B: PostgreSQL local

```bash
# Crear base de datos
createdb medai

# Ejecutar script de inicialización
psql medai < database/init.sql
```

### Verificar que la DB esté lista

```bash
# Con Docker
docker compose exec postgres psql -U medai -d medai -c "\dt"

# Local
psql medai -c "\dt"
```

Deberías ver las tablas: `users`, `user_channels`, `sessions`, `messages`, `reminders`, `documents`, `document_embeddings`.

---

## n8n Setup

### 1. Levantar n8n

```bash
docker compose up -d n8n
```

### 2. Acceder a la interfaz

Abre [http://localhost:5678](http://localhost:5678)

- **Usuario:** `admin`
- **Contraseña:** `admin123`

### 3. Importar workflows

#### Workflow 1: Medication Reminders

1. En n8n, ve a **Workflows** → **Import from File**
2. Selecciona `n8n-workflow-v2-free.json`
3. Haz clic en **Import**

### 4. Configurar credenciales de PostgreSQL

1. Ve a **Settings** → **Credentials**
2. **Add Credential** → **Postgres**
3. Llena los datos:
   ```
   Host: postgres
   Database: medai
   User: medai
   Password: medai_password
   Port: 5432
   ```
4. **Save**
5. Asigna esta credencial a los nodos de PostgreSQL en ambos workflows

---

## Telegram Bot

Telegram es un canal de **solo salida**: el bot envía recordatorios pero no escucha mensajes entrantes. El registro del chat_id ocurre desde el frontend web.

### 1. Crear el bot con BotFather

1. Abre Telegram y busca [@BotFather](https://t.me/botfather)
2. Envía `/newbot`
3. Nombre: `MedAI Reminder Bot`
4. Username: `medai_reminder_bot` (o el que prefieras, debe terminar en `_bot`)
5. **Guarda el token** (ej. `123456789:ABCdefGHI...`)

### 2. Agregar el token al entorno

En `.env` y en `docker-compose.yml` (sección `fastapi → environment`):

```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHI...
```

### 3. Configurar credencial en n8n (para envío de recordatorios)

1. En n8n: **Settings** → **Credentials** → **Add Credential** → **Telegram API**
2. Pega el token y guarda como `Telegram Bot MedAI`
3. Asigna la credencial a los nodos de Telegram en el workflow **Medication Reminders**
4. Activa el workflow (toggle verde)

### 4. Vincular Telegram desde el frontend

1. Abre el bot una vez en Telegram (para que Telegram permita que el bot te escriba)
2. Obtén tu `chat_id` con [@userinfobot](https://t.me/userinfobot)
3. En la app web → **Ajustes** → **Notificaciones** → ingresa el chat_id
4. El sistema envía un mensaje de prueba automáticamente; si llega, el canal queda verificado

Verificar en la base de datos:

```bash
docker compose exec postgres psql -U medai -d medai -c "SELECT * FROM user_channels;"
```

---

## Levantar el Backend FastAPI

### Opción A: Docker Compose

```bash
docker compose up -d fastapi
```

### Opción B: Local (para desarrollo)

```bash
# Activar entorno virtual
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Correr servidor
uvicorn api.main:app --reload --port 8000
```

### Verificar que esté funcionando

```bash
curl http://localhost:8000/health
```

Deberías ver:
```json
{
  "status": "ok",
  "provider": "ollama",
  "database": "postgres:5432/medai"
}
```

---

## Probar el Sistema

### Test 1: Crear recordatorio desde la CLI

```bash
# Activar entorno virtual
source .venv/bin/activate

# Editar main.py temporalmente para usar un user_id conocido
# O crear un usuario manualmente en la DB:

docker compose exec postgres psql -U medai -d medai << 'SQL'
INSERT INTO users (id, username, email) VALUES
  ('test-user-123', 'test_user', 'test@example.com')
ON CONFLICT DO NOTHING;

INSERT INTO user_channels (user_id, channel, notify_id, verified, is_primary) VALUES
  ('test-user-123', 'telegram', 'TU_CHAT_ID_AQUI', true, true)
ON CONFLICT DO NOTHING;
SQL

# Correr el CLI
python main.py
```

En la consola del agente:

```
Usuario: Recuérdame tomar ibuprofeno 600mg en 2 minutos
```

El agente debería:
1. Llamar a la tool `create_reminder`
2. Enviar el recordatorio a n8n
3. n8n guardarlo en la DB
4. Esperar 2 minutos
5. Enviarte un mensaje en Telegram

### Test 2: Verificar el recordatorio en la DB

```bash
docker compose exec postgres psql -U medai -d medai -c "SELECT * FROM reminders ORDER BY created_at DESC LIMIT 1;"
```

Deberías ver el recordatorio con `status='scheduled'`.

Después de 2 minutos:

```bash
docker compose exec postgres psql -U medai -d medai -c "SELECT reminder_id, medication, status, fired_at FROM reminders ORDER BY created_at DESC LIMIT 1;"
```

El `status` debería ser `'completed'` y `fired_at` debería tener un timestamp.

### Test 3: Probar webhook de n8n → Backend

```bash
curl -X POST http://localhost:8000/webhooks/n8n \
  -H "Content-Type: application/json" \
  -H "X-API-Key: secret_api_key_change_me" \
  -d '{
    "event": "reminder.fired",
    "data": {
      "reminder_id": "rem_test_123",
      "user_id": "test-user-123"
    }
  }'
```

Deberías ver:
```json
{"status": "received", "reminder_id": "rem_test_123"}
```

---

## Arquitectura del Sistema

```
Usuario escribe en CLI/Frontend
        │
        ▼
    Agent (core/llm.py)
        │
        ├─► Provider (Ollama/Claude/GPT)
        │
        └─► Tools (core/tools.py)
                │
                ├─► create_reminder()
                │       │
                │       ▼
                │   Consulta DB → obtiene canal primario
                │       │
                │       ▼
                │   HTTP POST → n8n webhook
                │                   │
                │                   ▼
                │               n8n Workflow
                │                   │
                │                   ├─► Guarda en DB (status='scheduled')
                │                   ├─► Genera .ics
                │                   ├─► Wait {delay_minutes}
                │                   ├─► Switch canal
                │                   │   ├─► Telegram API
                │                   │   ├─► Email SMTP
                │                   │   ├─► Discord Webhook
                │                   │   └─► OneSignal Push
                │                   │
                │                   └─► Callback al backend
                │                           │
                │                           ▼
                │                   POST /webhooks/n8n
                │                   (actualiza status='completed')
                │
                └─► search_knowledge_base() (futuro)
                        └─► RAG con pgvector
```

---

## Troubleshooting

### n8n no se conecta a PostgreSQL

**Síntoma:** n8n muestra error de conexión a DB

**Solución:**
```bash
# Verificar que postgres esté corriendo
docker compose ps

# Ver logs
docker compose logs postgres

# Recrear servicios
docker compose down
docker compose up -d postgres
# Esperar 10 segundos
docker compose up -d n8n
```

### Telegram: el mensaje de prueba falla al vincular

**Síntoma:** `POST /api/users/{id}/channels` devuelve HTTP 400 con "Telegram rechazo el mensaje"

**Soluciones:**

1. Verificar que `TELEGRAM_BOT_TOKEN` esté configurado en `.env`
2. Asegurarse de haber abierto el bot en Telegram al menos una vez (si nunca abriste el bot, no puede enviarte mensajes)
3. Confirmar que el `chat_id` es correcto con [@userinfobot](https://t.me/userinfobot)

### El agente no encuentra canales configurados

**Síntoma:** Al crear recordatorio: "No tienes ningún canal de notificación configurado"

**Solución:**

1. Vincular Telegram desde el frontend (ver sección anterior)
2. O insertar manualmente:
   ```bash
   docker compose exec postgres psql -U medai -d medai << 'SQL'
   INSERT INTO user_channels (user_id, channel, notify_id, verified, is_primary)
   VALUES ('TU_USER_ID', 'telegram', 'TU_CHAT_ID', true, true);
   SQL
   ```

### n8n no llama al backend

**Síntoma:** El recordatorio se envía pero el backend no se entera

**Solución:**

1. Verificar que el nodo "Callback to Backend" tenga la URL correcta:
   - Si usas Docker Compose: `http://fastapi:8000/webhooks/n8n`
   - Si backend es local: `http://host.docker.internal:8000/webhooks/n8n`

2. Verificar API key en el header del nodo:
   ```json
   {
     "name": "X-API-Key",
     "value": "secret_api_key_change_me"
   }
   ```

3. Ver logs del backend:
   ```bash
   docker compose logs -f fastapi
   ```

### Ollama no responde

**Síntoma:** Error "Connection refused" al llamar al agente

**Solución:**

1. Verificar que Ollama esté corriendo:
   ```bash
   curl http://localhost:11434/api/tags
   ```

2. Si usas Docker para el backend, cambiar `OLLAMA_HOST`:
   ```env
   # En .env
   OLLAMA_HOST=http://host.docker.internal:11434
   ```

---

## Comandos Útiles

### Docker Compose

```bash
# Ver estado de todos los servicios
docker compose ps

# Ver logs de un servicio específico
docker compose logs -f postgres
docker compose logs -f n8n
docker compose logs -f fastapi

# Reiniciar un servicio
docker compose restart fastapi

# Detener todo
docker compose down

# Detener y eliminar volúmenes (⚠️ borra la DB)
docker compose down -v

# Reconstruir imágenes
docker compose build --no-cache
docker compose up -d
```

### Base de Datos

```bash
# Conectar a psql
docker compose exec postgres psql -U medai -d medai

# Ver usuarios
docker compose exec postgres psql -U medai -d medai -c "SELECT * FROM users;"

# Ver recordatorios
docker compose exec postgres psql -U medai -d medai -c "SELECT * FROM reminders ORDER BY created_at DESC LIMIT 10;"

# Ver canales configurados
docker compose exec postgres psql -U medai -d medai -c "SELECT u.username, uc.channel, uc.notify_id, uc.is_primary FROM user_channels uc JOIN users u ON u.id = uc.user_id;"

# Limpiar sesiones antiguas
docker compose exec postgres psql -U medai -d medai -c "SELECT cleanup_old_sessions();"
```

### n8n

```bash
# Exportar workflow
# (en la UI de n8n, abre el workflow y Export → Download)

# Reiniciar n8n si haces cambios en variables de entorno
docker compose restart n8n
```

---

## Próximos Pasos

1. **Frontend en Next.js** - Seguir la Fase 3 del [ROADMAP.md](ROADMAP.md)
2. **RAG (documentos)** - Implementar upload de PDFs y búsqueda semántica
3. **Más canales** - Configurar Email, Discord, Web Push según [FREE_NOTIFICATIONS_SETUP.md](docs/FREE_NOTIFICATIONS_SETUP.md)
4. **Producción** - Configurar HTTPS, autenticación JWT, monitoreo

---

## Ayuda

Si encuentras problemas:

1. Revisa la sección [Troubleshooting](#troubleshooting)
2. Lee la documentación completa en `docs/`
3. Verifica los logs con `docker compose logs -f <servicio>`
4. Consulta [INTEGRATION_PLAN.md](docs/INTEGRATION_PLAN.md) para entender el flujo completo

¡Listo! 🎉 Ahora tienes un sistema de recordatorios de medicación completo con notificaciones por Telegram 100% gratis.
