"""OCR local con el motor integrado de Windows (Windows.Media.Ocr). Sin internet ni límites.

Usa los paquetes de idioma OCR instalados en Windows. Para inglés hace falta el paquete
'Language.OCR~~~en-US' (ver mensaje de error si falta).
"""
import asyncio
import io
import re

from PIL import Image
from winrt.windows.globalization import Language
from winrt.windows.graphics.imaging import BitmapDecoder
from winrt.windows.media.ocr import OcrEngine
from winrt.windows.storage.streams import DataWriter, InMemoryRandomAccessStream

from ocr_client import OCRError

ENGLISH_HINT = "Language.OCR~~~en-US~0.0.1.0"
WORD_RE = re.compile(r"[A-Za-zÀ-ÿ]{2,}")


def installed_languages():
    """Etiquetas de idioma OCR instaladas, p. ej. ['es-ES', 'es-MX']."""
    return [lang.language_tag for lang in OcrEngine.available_recognizer_languages]


def _family_tags(family, installed):
    """Ordena los paquetes de una familia (en/es) con preferencia por la variante principal."""
    preferred = {"en": ["en-US", "en-GB"], "es": ["es-ES", "es-MX"]}[family]
    tags = [t for t in installed if t.lower().startswith(family)]
    tags.sort(key=lambda t: preferred.index(t) if t in preferred else len(preferred))
    return tags


def _select_tags(language, installed):
    """Devuelve un idioma por familia a usar según la opción elegida."""
    families = {"eng": ["en"], "spa": ["es"], "auto": ["es", "en"]}[language]
    selected = []
    for family in families:
        tags = _family_tags(family, installed)
        if tags:
            selected.append(tags[0])
    if not selected:
        if language == "eng":
            raise OCRError(
                "Falta el paquete OCR de inglés en Windows. Ábrelo como administrador y ejecuta:\n"
                f"Add-WindowsCapability -Online -Name '{ENGLISH_HINT}'"
            )
        if language == "spa":
            raise OCRError("Falta el paquete OCR de español en Windows (Configuración > Idioma).")
        raise OCRError(
            "No hay paquetes OCR de Windows instalados (inglés o español).\n"
            f"Instala el de inglés como administrador: Add-WindowsCapability -Online -Name '{ENGLISH_HINT}'"
        )
    return selected


def _prepare_png(path):
    """Escala la imagen para que el motor la lea bien (texto pequeño se amplía)."""
    img = Image.open(path).convert("RGB")
    max_dim = OcrEngine.max_image_dimension
    longest = max(img.width, img.height)
    if longest < 1200:
        factor = min(2.0, 1200 / longest)
        img = img.resize((int(img.width * factor), int(img.height * factor)), Image.LANCZOS)
    elif longest > max_dim:
        factor = max_dim / longest
        img = img.resize((int(img.width * factor), int(img.height * factor)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


async def _decode(png_bytes):
    stream = InMemoryRandomAccessStream()
    writer = DataWriter(stream.get_output_stream_at(0))
    writer.write_bytes(png_bytes)
    await writer.store_async()
    await writer.flush_async()
    writer.detach_stream()
    stream.seek(0)
    decoder = await BitmapDecoder.create_async(stream)
    return await decoder.get_software_bitmap_async()


async def _recognize(png_bytes, tags):
    bitmap = await _decode(png_bytes)
    results = []
    for tag in tags:
        engine = OcrEngine.try_create_from_language(Language(tag))
        if engine is None:
            continue
        result = await engine.recognize_async(bitmap)
        text = "\n".join(line.text for line in result.lines).strip()
        results.append(text)
    return results


def ocr_windows(path, language="auto"):
    """Devuelve el texto de la imagen usando el OCR local de Windows.

    Con 'auto' y ambos idiomas instalados, ejecuta el motor en español e inglés y
    conserva el resultado con más palabras reconocibles (la mezcla de idiomas
    se resuelve por el que mejor encaja con el texto).
    """
    installed = installed_languages()
    tags = _select_tags(language, installed)
    png = _prepare_png(path)
    try:
        candidates = asyncio.run(_recognize(png, tags))
    except OSError as e:
        raise OCRError(f"No se pudo leer la imagen con el OCR de Windows: {e}") from e
    if not candidates:
        raise OCRError("El OCR de Windows no devolvió resultados.")
    return max(candidates, key=lambda t: len(WORD_RE.findall(t)))


def describe_installed():
    """Texto corto para la ventana de configuración."""
    try:
        tags = installed_languages()
    except Exception as e:
        return f"No disponible en este equipo ({e})"
    return "Paquetes instalados: " + (", ".join(tags) if tags else "ninguno")
