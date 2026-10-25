"""Cliente de OCR.space (API gratuita). Docs: https://ocr.space/ocrapi

Motor 2 con language=auto detecta el idioma (inglés/español). También puedes
forzar 'eng' o 'spa' desde Configuración.
"""
import io

import requests
from PIL import Image

OCR_ENDPOINT = "https://api.ocr.space/parse/image"
MAX_UPLOAD_BYTES = 1_000_000  # límite del plan gratuito (1 MB)


class OCRError(Exception):
    pass


def _upload_payload(path):
    """Devuelve bytes que caben en el límite; si el PNG es grande, reduce a JPEG."""
    with open(path, "rb") as f:
        data = f.read()
    if len(data) <= MAX_UPLOAD_BYTES:
        return data, "capture.png", "image/png"

    img = Image.open(path).convert("RGB")
    for scale in (1.0, 0.8, 0.6, 0.45):
        if scale < 1.0:
            size = (int(img.width * scale), int(img.height * scale))
            resized = img.resize(size, Image.LANCZOS)
        else:
            resized = img
        buf = io.BytesIO()
        resized.save(buf, "JPEG", quality=88, optimize=True)
        if len(buf.getvalue()) <= MAX_UPLOAD_BYTES:
            return buf.getvalue(), "capture.jpg", "image/jpeg"
    raise OCRError("La captura es demasiado grande para el plan gratuito (1 MB). Captura un área más pequeña.")


def ocr_image(path, api_key, language="auto"):
    data, filename, mime = _upload_payload(path)
    form = {
        "apikey": api_key or "helloworld",
        "language": language,
        "OCREngine": "2",
        "scale": "true",
        "detectOrientation": "true",
        "isTable": "false",
    }
    try:
        resp = requests.post(
            OCR_ENDPOINT,
            data=form,
            files={"file": (filename, data, mime)},
            timeout=60,
        )
    except requests.RequestException as e:
        raise OCRError(f"Sin conexión con OCR.space: {e}") from e

    if resp.status_code in (401, 403):
        raise OCRError("API key inválida o límite de uso alcanzado.")
    if resp.status_code >= 400:
        raise OCRError(f"OCR.space respondió HTTP {resp.status_code}.")

    payload = resp.json()
    if payload.get("IsErroredOnProcessing"):
        err = payload.get("ErrorMessage") or payload.get("ErrorDetails") or "Error desconocido"
        if isinstance(err, list):
            err = " ".join(str(x) for x in err)
        raise OCRError(str(err))

    parts = [r.get("ParsedText", "") for r in payload.get("ParsedResults") or []]
    return "\n".join(parts).strip()
