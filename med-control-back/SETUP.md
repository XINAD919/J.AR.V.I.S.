# MedAI - Guía de Setup Completa

Esta guía lleva el proyecto desde cero hasta tener todo el sistema funcionando: Supabase (DB + Storage), n8n, Ollama y los canales de notificación.

---

## Índice

1. [Requisitos Previos](#requisitos-previos)
2. [Configuración del entorno](#configuración-del-entorno)
3. [Levantar el stack](#levantar-el-stack)
4. [Inicializar la base de datos](#inicializar-la-base-de-datos)
5. [n8n Setup](#n8n-setup)
6. [Telegram Bot](#telegram-bot)
7. [Entorno Python](#entorno-python)
8. [Probar el sistema](#probar-el-sistema)
9. [Troubleshooting](#troubleshooting)

---

## Requisitos Previos

### Software necesario

- **Docker** y **Docker Compose** v2+
- **Python 3.12+** (para desarrollo local)
- **Ollama** corriendo localmente con los modelos `qwen2.5:32b` y `nomic-embed-text`

### Paquetes del sistema (para OCR)

```bash
# Ubuntu / Debian / WSL
sudo apt install tesseract-ocr tesseract-ocr-spa poppler-utils
```

### Verificar instalaciones

```bash
docker --version          # Docker version 24.0+
docker compose version    # Docker Compose version 2.0+
python --version          # Python 3.12+
tesseract --version       # Tesseract 5.x
ollama list               # debe listar qwen2.5:32b y nomic-embed-text
```

### Modelos Ollama necesarios

```bash
ollama pull qwen2.5:32b
ollama pull nomic-embed-text   # para embeddings RAG
```

---

## Configuración del entorno

El repositorio incluye un `.env` con claves pre-generadas para desarrollo local. Si lo estás clonando por primera vez, crea el `.env` con las variables mínimas necesarias:

```bash
# Variables mínimas para arrancar el stack
cat > .env << 'EOF'
# ── LLM ─────────────────────────────────────────────────────────────────────
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:32b
OLLAMA_HOST=http://localhost:11434
# ANTHROPIC_API_KEY=sk-ant-...  # Solo si LLM_PROVIDER=anthropic

# ── Supabase (se autogenera al hacer docker compose up por primera vez) ──────
# Copia estos valores desde el .env del stack de Supabase después de generarlos
SUPABASE_URL=http://localhost:8000
SUPABASE_SERVICE_ROLE_KEY=<SERVICE_ROLE_KEY_del_stack>

# ── n8n / Recordatorios ──────────────────────────────────────────────────────
N8N_WEBHOOK_URL=http://localhost:5678/webhook/medai-reminder
WEBHOOK_SECRET=cambia_este_secreto

# ── Seguridad ────────────────────────────────────────────────────────────────
AUTH_SECRET_INTERNAL=cambia_este_secreto_interno

# ── Integraciones opcionales ─────────────────────────────────────────────────
TAVILY_API_KEY=              # Para búsqueda web médica (web_search tool)
TELEGRAM_BOT_TOKEN=          # Para verificación de canales Telegram
ONESIGNAL_APP_ID=            # Para WebPush (OneSignal)

# ── CORS ────────────────────────────────────────────────────────────────────
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
EOF
```

> Las variables de Supabase (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, claves JWT, contraseña de postgres, etc.) viven en el mismo `.env` del proyecto — el `docker-compose.yml` las lee para configurar todos los servicios del stack. Si ya tienes el `.env` del repositorio, tiene las claves pre-generadas y no necesitas regenerarlas.

---

## Levantar el stack

El `docker-compose.yml` incluye el stack completo de Supabase self-hosted más n8n:

```bash
# Levantar todo (Supabase: Studio, Kong, Auth, PostgREST, Realtime, Storage + n8n)
docker compose up -d

# Ver estado de todos los servicios
docker compose ps

# Ver logs (esperar a que todos los servicios estén healthy)
docker compose logs -f kong
```

**Servicios y puertos relevantes:**

| Servicio | URL | Descripción |
|---|---|---|
| Kong (API Gateway) | `http://localhost:8000` | Punto de entrada al stack Supabase (`SUPABASE_URL`) |
| Supabase Studio | `http://localhost:3000` | Panel de administración (tablas, Storage, logs) |
| n8n | `http://localhost:5678` | Automatización de recordatorios |
| PostgreSQL | `localhost:5432` | DB directa (para migraciones manuales) |

---

## Inicializar la base de datos

El script `database/init.sql` crea todas las tablas, tipos y extensiones. Ejecutarlo una sola vez contra el PostgreSQL del stack:

```bash
# Opción A: desde el contenedor db
docker compose exec db psql -U postgres -d postgres -f /dev/stdin < database/init.sql

# Opción B: conexión directa (si tienes psql instalado localmente)
psql postgresql://postgres:TU_POSTGRES_PASSWORD@localhost:5432/postgres < database/init.sql
```

La contraseña de postgres está en el `.env` como `POSTGRES_PASSWORD`.

### Verificar las tablas

```bash
docker compose exec db psql -U postgres -d postgres -c "\dt"
```

Deberías ver: `users`, `user_channels`, `sessions`, `messages`, `reminders`, `documents`, `document_embeddings`.

### Seed user (para CLI local)

```bash
docker compose exec db psql -U postgres -d postgres << 'SQL'
INSERT INTO users (id, username, email) VALUES
  ('11111111-1111-1111-1111-111111111111', 'seed_user', 'seed@medai.local')
ON CONFLICT (id) DO NOTHING;

INSERT INTO sessions (id, user_id, session_id) VALUES
  ('22222222-2222-2222-2222-222222222222',
   '11111111-1111-1111-1111-111111111111',
   'default')
ON CONFLICT (session_id) DO NOTHING;
SQL
```

---

## n8n Setup

### 1. Acceder a n8n

Abre [http://localhost:5678](http://localhost:5678)

- **Usuario:** `admin`
- **Contraseña:** `admin123` (o la configurada en `.env`)

### 2. Importar el workflow

1. Ve a **Workflows** → **Import from File**
2. Selecciona `n8n-workflow.json`
3. Haz clic en **Import**
4. **Activa** el workflow (toggle verde)

### 3. Configurar credencial PostgreSQL en n8n

1. **Settings** → **Credentials** → **Add Credential** → **Postgres**
2. Llena los datos:

   ```
   Host: db                  (nombre del servicio Docker)
   Database: postgres
   User: postgres
   Password: TU_POSTGRES_PASSWORD (valor de POSTGRES_PASSWORD en .env)
   Port: 5432
   ```

3. **Save** y asigna la credencial a todos los nodos de Postgres en el workflow.

### 4. Configurar callback al backend

En el nodo "Callback to Backend" del workflow, la URL debe apuntar al backend:
- **Con backend en Docker:** `http://fastapi:8000/webhooks/n8n`
- **Con backend local (desarrollo):** `http://host.docker.internal:8000/webhooks/n8n`

El header `X-Api-Key` debe coincidir con `WEBHOOK_SECRET` del `.env`.

---

## Telegram Bot

Telegram es canal de **solo salida**: el bot envía recordatorios, el chat_id se registra desde el frontend o la API.

### 1. Crear el bot con BotFather

1. En Telegram, busca [@BotFather](https://t.me/botfather)
2. Envía `/newbot` y sigue los pasos
3. Guarda el token (ej. `123456789:ABCdef...`)

### 2. Agregar el token al entorno

```env
TELEGRAM_BOT_TOKEN=123456789:ABCdef...
```

### 3. Configurar credencial en n8n

1. **Settings** → **Credentials** → **Telegram API**
2. Pega el token → **Save** como `Telegram Bot MedAI`
3. Asigna la credencial a los nodos de Telegram en el workflow

### 4. Vincular el chat_id

1. Abre el bot en Telegram (para que pueda escribirte)
2. Obtén tu `chat_id` con [@userinfobot](https://t.me/userinfobot)
3. Registra el canal vía API o frontend:

   ```bash
   curl -X POST http://localhost:8000/api/users/TU_USER_ID/channels \
     -H "Content-Type: application/json" \
     -d '{"channel": "telegram", "notify_id": "TU_CHAT_ID"}'
   ```

   Si el token está configurado, el sistema envía un mensaje de prueba y verifica el canal automáticamente.

---

## Entorno Python

```bash
# Crear entorno virtual
python -m venv .venv
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Opcional: voz (STT/TTS, requiere CUDA)
# pip install faster-whisper kokoro-onnx sounddevice soundfile torch onnxruntime

# Opcional: proveedor Anthropic
# pip install anthropic
```

### Ejecutar el backend en modo desarrollo

```bash
source .venv/bin/activate
uvicorn api.main:app --reload --port 8000
```

### Verificar que el backend responde

```bash
curl http://localhost:8000/health
```

Respuesta esperada:

```json
{
  "status": "ok",
  "provider": "ollama",
  "supabase": "http://localhost:8000"
}
```

---

## Probar el sistema

### Test 1: CLI conversacional

```bash
source .venv/bin/activate
python main.py
```

En la consola del agente:

```
Usuario: Recuérdame tomar ibuprofeno 600mg en 2 minutos
```

El agente debería:
1. Llamar a la tool `create_reminder`
2. Enviar el payload a n8n
3. n8n guarda el reminder en la DB con `status='scheduled'`
4. Tras 2 minutos, envía la notificación al canal configurado
5. Llama al backend → `status='completed'`

### Test 2: Verificar el recordatorio en la DB

```bash
docker compose exec db psql -U postgres -d postgres \
  -c "SELECT reminder_id, medication, status, scheduled_at FROM reminders ORDER BY created_at DESC LIMIT 3;"
```

### Test 3: Upload de receta (OCR + RAG)

```bash
curl -X POST http://localhost:8000/api/users/TU_USER_ID/documents \
  -H "Authorization: Bearer TU_TOKEN" \
  -F "file=@receta.jpg"
```

El backend ejecuta en background: Storage upload → OCR → embeddings → guardado en `document_embeddings`. El agente puede consultarlos con `search_knowledge_base`.

### Test 4: Webhook de n8n → Backend

```bash
curl -X POST http://localhost:8000/webhooks/n8n \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: $WEBHOOK_SECRET" \
  -d '{"event": "reminder.fired", "reminder_id": "rem_test_123"}'
```

Respuesta esperada: `{"status": "received", "reminder_id": "rem_test_123"}`

---

## Comandos útiles

### Docker Compose

```bash
docker compose ps                          # Estado de servicios
docker compose logs -f kong                # Logs del gateway Supabase
docker compose logs -f n8n                 # Logs de n8n
docker compose restart n8n                 # Reiniciar n8n tras cambios de config

docker compose down                        # Detener todo
docker compose down -v                     # Detener y borrar volúmenes (⚠️ borra la DB)
```

### Base de datos (Supabase PostgreSQL)

```bash
# Conectar a psql
docker compose exec db psql -U postgres -d postgres

# Ver usuarios del sistema
docker compose exec db psql -U postgres -d postgres -c "SELECT id, username, email FROM users;"

# Ver recordatorios recientes
docker compose exec db psql -U postgres -d postgres \
  -c "SELECT reminder_id, medication, status, channel FROM reminders ORDER BY created_at DESC LIMIT 10;"

# Ver canales configurados
docker compose exec db psql -U postgres -d postgres \
  -c "SELECT u.username, uc.channel, uc.notify_id, uc.verified, uc.is_primary FROM user_channels uc JOIN users u ON u.id = uc.user_id;"

# Ver documentos subidos
docker compose exec db psql -U postgres -d postgres \
  -c "SELECT filename, processed, chunk_count, uploaded_at FROM documents ORDER BY uploaded_at DESC;"
```

También disponible vía **Supabase Studio** en `http://localhost:3000` (editor de tablas, Storage browser, SQL editor).

---

## Troubleshooting

### El stack de Supabase no levanta correctamente

```bash
# Ver logs de todos los servicios
docker compose logs --tail=50

# Revisar healthchecks
docker compose ps

# Recrear desde cero (⚠️ borra datos)
docker compose down -v
docker compose up -d
```

### n8n no se conecta a PostgreSQL

Asegúrate de que la credencial de Postgres en n8n usa `db` como host (el nombre del servicio Docker), no `localhost`.

```bash
docker compose logs n8n | tail -20
```

### Telegram: el mensaje de prueba falla al vincular

1. Verifica que `TELEGRAM_BOT_TOKEN` esté en `.env` y el backend reiniciado
2. Asegúrate de haber iniciado el bot en Telegram al menos una vez (clic en `/start`)
3. Confirma el `chat_id` correcto con [@userinfobot](https://t.me/userinfobot)

### OCR falla con "tesseract not found"

```bash
# Verificar instalación
which tesseract && tesseract --version

# Instalar si falta
sudo apt install tesseract-ocr tesseract-ocr-spa poppler-utils
```

### Embeddings fallan con "nomic-embed-text not found"

```bash
ollama pull nomic-embed-text
ollama list  # verificar que aparece
```

### El agente no encuentra canales configurados

Verificar en la DB que el canal esté verificado:

```bash
docker compose exec db psql -U postgres -d postgres \
  -c "SELECT channel, verified, receive_reminders FROM user_channels WHERE user_id = 'TU_USER_ID';"
```

Si no está verificado, insertar manualmente para pruebas:

```bash
docker compose exec db psql -U postgres -d postgres << 'SQL'
INSERT INTO user_channels (user_id, channel, notify_id, verified, is_primary)
VALUES ('TU_USER_ID', 'telegram', 'TU_CHAT_ID', true, true)
ON CONFLICT (user_id, channel) DO UPDATE SET verified = true;
SQL
```

### Ollama no responde

```bash
curl http://localhost:11434/api/tags

# Si el backend corre en Docker (no local), usar host.docker.internal:
# OLLAMA_HOST=http://host.docker.internal:11434
```

### Backend no se conecta a Supabase

```bash
# Verificar que el stack está up y Kong responde
curl http://localhost:8000/health

# Verificar variables en .env
grep SUPABASE .env
```
