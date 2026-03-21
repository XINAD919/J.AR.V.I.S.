# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Jarvis is a Spanish-first conversational AI assistant with multi-modal capabilities (text, STT, TTS). It uses a local Ollama LLM backend and offline speech models.

## Development Commands

```bash
source .venv/bin/activate   # Activate virtual environment (Python 3.12.3)
python main.py              # Run the assistant
deactivate                  # Exit virtual environment
```

To exit the running assistant: type `salir`, `exit`, or `quit`.

No build system, test runner, or lint CLI is configured. Ruff is available via VS Code on save.

## Architecture

**Entry point:** `main.py` instantiates `Agent` from `core/llm.py` and calls `.run()`.

**`core/llm.py` — LLM Agent (main component)**
- Connects to a local Ollama instance running `qwen2.5:32b`
- Maintains multi-turn conversation history, persisted to `historial.json`
- System prompt defines Jarvis personality: Spanish-first, addresses user as "Señor/Señorita", creator is Daniel, birth date Feb 27 2026
- Streams responses to console

**`core/stt.py` — Speech-to-Text**
- Uses `faster_whisper` with the `larger-v3` Whisper model
- CUDA/float16, 16kHz mono audio, language: Spanish
- Integration is present but **commented out** in `main.py`

**`core/tts.py` — Text-to-Speech**
- Uses Kokoro ONNX model from `models/kokoro-v1.0.onnx` + `models/voices-v1.0.bin`
- Default voice: `ef_dora`, output resampled to 44.1kHz
- Integration is not yet wired into the main loop

**`core/ocr.py`** — Empty placeholder, not implemented.

**`learning/`** — Standalone experimental scripts (calculator, mic test); not integrated into main app.

## Key Dependencies

Installed in `.venv/` (no requirements.txt):
- `ollama` — LLM inference via local Ollama server
- `faster_whisper` — optimized Whisper STT
- `kokoro_onnx` — TTS inference
- `sounddevice`, `soundfile` — audio I/O
- `torch`, `onnxruntime` — ML runtime (CUDA 12.8+)
- `pyfiglet` — ASCII title banner

## Notes

- Ollama must be running locally with `qwen2.5:32b` pulled before starting.
- GPU with CUDA is expected for STT (Whisper) and general ML inference.
- `historial.json` stores full conversation history across sessions.
