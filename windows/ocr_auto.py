"""Motor OCR unificado: ejecuta los motores disponibles y devuelve el de mejor resultado.

Motores: Windows (local), Tesseract (local, si está instalado) y OCR.space (nube).
Un motor que falla o no está instalado simplemente no compite.
"""
import re
from concurrent.futures import ThreadPoolExecutor

from ocr_client import OCRError, ocr_image
from ocr_windows import ocr_windows
from tesseract_ocr import ocr_tesseract

WORD = re.compile(r"[A-Za-zÀ-ÿ]{2,}")
ALLOWED_PUNCT = set(".,;:!?¿¡()'\"-/%$@#&+_*")


def score(text):
    """Calidad aproximada: letras reconocibles en palabras, penalizando símbolos raros."""
    if not text or not text.strip():
        return 0.0
    letters = sum(len(w) for w in WORD.findall(text))
    weird = sum(1 for c in text if not (c.isalnum() or c.isspace() or c in ALLOWED_PUNCT))
    ratio = weird / len(text)
    return letters * max(0.0, 1.0 - ratio * 3)


def ocr_auto(path, language="auto", api_key="helloworld"):
    engines = [
        ("Windows", lambda: ocr_windows(path, language)),
        ("Tesseract", lambda: ocr_tesseract(path, language)),
        ("OCR.space", lambda: ocr_image(path, api_key, language)),
    ]
    results, errors = [], []
    with ThreadPoolExecutor(max_workers=len(engines)) as pool:
        futures = [(name, pool.submit(fn)) for name, fn in engines]
        for name, fut in futures:
            try:
                text = fut.result()
                results.append((score(text), name, text))
            except Exception as e:  # un motor caído no detiene a los demás
                errors.append(f"{name}: {e}")
    if not results:
        raise OCRError("Ningún motor OCR respondió.\n" + "\n".join(errors))
    best_score, best_name, best_text = max(results, key=lambda r: r[0])
    return best_text
