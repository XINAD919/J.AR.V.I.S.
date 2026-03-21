import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel


class STT:
    def __init__(
        self,
        model_size: str = "large-v3",
        device: str = "cuda",
        compute_type: str = "float16",
        sample_rate: int = 16000,
        language: str = "es",
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.sample_rate = sample_rate
        self.language = language
        self._model: WhisperModel | None = None

    def load(self) -> None:
        """Carga el modelo en memoria (se llama automáticamente si no se hizo antes)."""
        if self._model is None:
            print("Cargando modelo...")
            self._model = WhisperModel(
                self.model_size, device=self.device, compute_type=self.compute_type
            )
            print("Modelo listo.")

    def _record(self, seconds: int = 5) -> np.ndarray:
        audio = sd.rec(
            int(seconds * self.sample_rate),
            samplerate=self.sample_rate,
            channels=1,
            dtype=np.float32,
        )
        sd.wait()
        return audio.flatten()

    def transcribe(self, audio: np.ndarray) -> str:
        self.load()
        segments, info = self._model.transcribe(
            audio, language=self.language, vad_filter=True
        )
        return " ".join(segment.text for segment in segments)

    def listen(self, seconds: int = 15) -> str:
        audio = self._record(seconds)
        result = self.transcribe(audio)
        print(f"Usuario: {result}")
        return result
