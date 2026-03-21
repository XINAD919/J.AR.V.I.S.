# J.A.R.V.I.S.

Asistente de IA conversacional con capacidades multimodales (texto, voz). Usa un modelo LLM local via Ollama y modelos de voz offline.

## Requisitos previos

- [Ollama](https://ollama.com/) corriendo localmente con el modelo `qwen2.5:32b` descargado
- GPU con CUDA 12.8+ (requerida para STT y ML en general)
- Python 3.12.3

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate
pip install ollama faster_whisper kokoro_onnx sounddevice soundfile torch onnxruntime pyfiglet
```

### Modelos de TTS

Los modelos no están en el repositorio. Descárgalos manualmente y colócalos en `models/`:

```bash
mkdir -p models
# Kokoro ONNX (TTS)
wget -O models/kokoro-v1.0.onnx https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/kokoro-v1.0.onnx
wget -O models/voices-v1.0.bin https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/voices-v1.0.bin
```

## Uso

```bash
source .venv/bin/activate   # Activar entorno virtual
python main.py              # Iniciar el asistente
deactivate                  # Salir del entorno virtual
```

## Comandos en tiempo de ejecución

| Comando | Descripción |
|---------|-------------|
| `/voice` | Alternar modo de voz (STT + TTS) |
| `salir` / `exit` / `quit` | Cerrar el asistente |

## Arquitectura

```
main.py          — Punto de entrada
core/
  llm.py         — Agente LLM (Ollama, historial, herramientas)
  stt.py         — Speech-to-Text (Whisper faster-v3, CUDA)
  tts.py         — Text-to-Speech (Kokoro ONNX, voz ef_dora)
  tools.py       — Herramientas disponibles para el agente
  ocr.py         — Placeholder (no implementado)
models/          — Modelos ONNX de TTS
historial.json   — Historial de conversación persistente
```

## Notas

- El historial de conversación se guarda automáticamente en `historial.json` al salir.
- El modo de voz requiere micrófono y los modelos Whisper descargados.
