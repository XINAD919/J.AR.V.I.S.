"""
OCR pipeline for prescription images.

Flow:
  1. preprocess_image  — grayscale, upscale if needed, sharpen, binarize
  2. run_tesseract     — extract raw text (spa+eng)
  3. extract_structured — call LLM to parse medication/dose/frequency/duration
  4. process_prescription — orchestrates all steps; handles PDF on the way in
"""

import json
import os
from io import BytesIO

from PIL import Image, ImageFilter


# ── Data models ────────────────────────────────────────────────────────────

class PrescriptionData:
    __slots__ = ("medication", "dose", "frequency", "duration", "prescribing_doctor", "raw_notes")

    def __init__(
        self,
        medication: str = "",
        dose: str | None = None,
        frequency: str | None = None,
        duration: str | None = None,
        prescribing_doctor: str | None = None,
        raw_notes: str | None = None,
    ):
        self.medication = medication
        self.dose = dose
        self.frequency = frequency
        self.duration = duration
        self.prescribing_doctor = prescribing_doctor
        self.raw_notes = raw_notes

    def to_dict(self) -> dict:
        return {
            "medication": self.medication,
            "dose": self.dose,
            "frequency": self.frequency,
            "duration": self.duration,
            "prescribing_doctor": self.prescribing_doctor,
            "raw_notes": self.raw_notes,
        }


class OCRResult:
    __slots__ = ("raw_text", "structured")

    def __init__(self, raw_text: str, structured: PrescriptionData):
        self.raw_text = raw_text
        self.structured = structured


# ── Image preprocessing ────────────────────────────────────────────────────

def preprocess_image(image_bytes: bytes) -> Image.Image:
    img = Image.open(BytesIO(image_bytes)).convert("RGB")
    gray = img.convert("L")

    # Upscale small images so Tesseract has more pixels to work with
    w, h = gray.size
    if w < 1000:
        scale = 1000 / w
        gray = gray.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    sharpened = gray.filter(ImageFilter.SHARPEN)
    # Simple binarization: pixels > 128 → white, else → black
    binarized = sharpened.point(lambda px: 255 if px > 128 else 0, "L")
    return binarized


# ── Tesseract OCR ──────────────────────────────────────────────────────────

def run_tesseract(image: Image.Image) -> str:
    import pytesseract

    raw = pytesseract.image_to_string(
        image,
        lang="spa+eng",
        config="--oem 3 --psm 6",
    )
    lines = [ln.strip() for ln in raw.splitlines()]
    return "\n".join(ln for ln in lines if ln)


# ── LLM-based structured extraction ───────────────────────────────────────

_EXTRACTION_PROMPT = """Eres un asistente médico. Extrae la información de la siguiente receta médica y devuelve ÚNICAMENTE un JSON válido con estas claves:
- "medication": nombre del medicamento (string, requerido — usa "" si no lo encuentras)
- "dose": dosis por toma (string o null)
- "frequency": frecuencia de toma, ej. "cada 8 horas", "1 vez al día" (string o null)
- "duration": duración del tratamiento, ej. "7 días", "1 mes" (string o null)
- "prescribing_doctor": nombre del médico si aparece (string o null)
- "raw_notes": instrucciones adicionales o notas importantes (string o null)

Texto de la receta:
{text}

Devuelve solo el JSON, sin explicaciones ni markdown."""


def extract_structured(raw_text: str) -> PrescriptionData:
    """Call the local LLM to parse structured data from raw OCR text."""
    import ollama

    model = os.getenv("LLM_MODEL", "qwen2.5:32b")
    prompt = _EXTRACTION_PROMPT.format(text=raw_text[:3000])

    try:
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0},
        )
        content = response["message"]["content"].strip()

        # Strip markdown code fences if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        data = json.loads(content)
        return PrescriptionData(
            medication=data.get("medication", ""),
            dose=data.get("dose"),
            frequency=data.get("frequency"),
            duration=data.get("duration"),
            prescribing_doctor=data.get("prescribing_doctor"),
            raw_notes=data.get("raw_notes"),
        )
    except Exception:
        return PrescriptionData(medication="", raw_notes=raw_text[:500])


# ── Main entry point ───────────────────────────────────────────────────────

def process_prescription(image_bytes: bytes, mimetype: str) -> OCRResult:
    """
    Full OCR pipeline. Accepts JPEG, PNG, WEBP, or PDF bytes.
    Raises ValueError if Tesseract returns less than 50 characters.
    """
    if mimetype == "application/pdf":
        from pdf2image import convert_from_bytes

        pages = convert_from_bytes(image_bytes, dpi=200, first_page=1, last_page=1)
        if not pages:
            raise ValueError("PDF has no pages.")
        buf = BytesIO()
        pages[0].save(buf, format="PNG")
        image_bytes = buf.getvalue()

    preprocessed = preprocess_image(image_bytes)
    raw_text = run_tesseract(preprocessed)

    if len(raw_text.strip()) < 50:
        raise ValueError(
            f"OCR produced insufficient text ({len(raw_text.strip())} chars). "
            "The image may be too low quality or upside down."
        )

    structured = extract_structured(raw_text)
    return OCRResult(raw_text=raw_text, structured=structured)
