from pathlib import Path

import sounddevice as sd
from kokoro_onnx import Kokoro
from scipy.signal import resample_poly

MODELS_DIR = Path(__file__).parent.parent / "models"
PULSE_SAMPLE_RATE = 44100


class TTS:
    def __init__(self):
        self.model: str = str(MODELS_DIR / "kokoro-v1.0.onnx")
        self.voices: str = str(MODELS_DIR / "voices-v1.0.bin")
        self._kokoro: Kokoro | None = None

    def load(self):
        """Carga el modelo en memoria (se llama automáticamente si no se hizo antes)."""
        if self._kokoro is None:
            print("Cargando modelo...")
            self._kokoro = Kokoro(
                self.model,
                self.voices,
            )
            print("Modelo listo.")

    def speak(self, texto: str, voz: str = "ef_dora", velocidad: float = 1.0) -> None:
        if not texto.strip():
            return
        self.load()

        samples, sample_rate = self._kokoro.create(
            texto, voice=voz, speed=velocidad, lang="es"
        )

        samples_resampled = resample_poly(samples, PULSE_SAMPLE_RATE, sample_rate)
        sd.play(samples_resampled, PULSE_SAMPLE_RATE, blocksize=8192)
        sd.wait()
