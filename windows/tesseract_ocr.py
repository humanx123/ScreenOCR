"""OCR local con Tesseract (código abierto, Apache-2.0). Requiere Tesseract instalado en Windows.

Los datos de idioma (eng/spa) se leen de %APPDATA%\\ScreenOCR\\tessdata, o de la carpeta
por defecto de Tesseract si ya están ahí.
"""
import os
from pathlib import Path

from PIL import Image

from ocr_client import OCRError

TESSERACT_CANDIDATES = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]
TESSDATA_DIR = Path(os.getenv("APPDATA", Path.home())) / "ScreenOCR" / "tessdata"
LANG_MAP = {"auto": "eng+spa", "eng": "eng", "spa": "spa"}


def _find_tesseract():
    for p in TESSERACT_CANDIDATES:
        if os.path.exists(p):
            return p
    return None


def ocr_tesseract(path, language="auto"):
    try:
        import pytesseract
    except ImportError as e:
        raise OCRError("Falta el paquete pytesseract. Ejecuta: pip install pytesseract") from e

    exe = _find_tesseract()
    if exe is None:
        raise OCRError(
            "Tesseract no está instalado. Descárgalo gratis de https://github.com/UB-Mannheim/tesseract/wiki "
            "o ejecuta: winget install -e --id UB-Mannheim.TesseractOCR"
        )
    pytesseract.pytesseract.tesseract_cmd = exe
    # Sin comillas: pytesseract separa la configuración por espacios.
    config = f"--tessdata-dir {TESSDATA_DIR.as_posix()}" if TESSDATA_DIR.exists() else ""
    lang = LANG_MAP.get(language, "eng+spa")
    try:
        text = pytesseract.image_to_string(Image.open(path).convert("RGB"), lang=lang, config=config)
    except pytesseract.TesseractError as e:
        raise OCRError(f"Tesseract no pudo leer el idioma «{lang}». Revisa tessdata. Detalle: {e}") from e
    return text.strip()
