"""Tesseract.js dentro de la app: el mismo motor (Apache-2.0) que usa la versión web.

Corre en un componente de navegador interno (Qt WebEngine), sin instalar nada extra.
La primera vez necesita internet para descargar el motor y los idiomas desde jsDelivr.
"""
import base64
import json
from collections import deque

from PySide6.QtCore import QObject, QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView

TESSERACT_JS = "https://cdn.jsdelivr.net/npm/tesseract.js@5.1.1/dist/tesseract.min.js"

HTML = f"""<!doctype html>
<html><head><meta charset="utf-8"></head>
<body>
<script src="{TESSERACT_JS}"></script>
<script>
function enc(s) {{ return btoa(unescape(encodeURIComponent(s))); }}
window.runOcr = async function (dataUrl, langs) {{
  document.title = "";
  try {{
    const r = await Tesseract.recognize(dataUrl, langs, {{ logger: () => {{}} }});
    document.title = "OK:" + enc(r.data.text || "");
  }} catch (e) {{
    document.title = "ERR:" + enc(String((e && e.message) || e));
  }}
}};
window.__ready = typeof Tesseract !== "undefined";
</script>
</body></html>
"""

LANG_MAP = {"auto": "eng+spa", "eng": "eng", "spa": "spa"}


class TesseractWebOCR(QObject):
    """Cola de reconocimientos. Un trabajo a la vez; el resultado vuelve por el título de la página."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.view = QWebEngineView()
        self.view.resize(10, 10)
        self.view.titleChanged.connect(self._on_title)
        self.view.loadFinished.connect(self._on_loaded)
        self._loaded = False
        self._queue = deque()
        self._current = None  # callback del trabajo en curso
        self.view.setHtml(HTML, QUrl("https://screenocr.local/"))

    def recognize(self, path, language, callback):
        """callback(texto, error) se llama al terminar, en el hilo de la interfaz."""
        self._queue.append((path, language, callback))
        self._pump()

    def _pump(self):
        if self._current is not None or not self._loaded or not self._queue:
            return
        path, language, callback = self._queue.popleft()
        self._current = callback
        with open(path, "rb") as f:
            data_url = "data:image/png;base64," + base64.b64encode(f.read()).decode("ascii")
        langs = LANG_MAP.get(language, "eng+spa")
        self.view.page().runJavaScript(f"runOcr({json.dumps(data_url)}, {json.dumps(langs)});")

    def _on_loaded(self, ok):
        self._loaded = bool(ok)
        if not ok and self._current is not None:
            self._finish("", "No se pudo cargar el motor Tesseract.js. Revisa tu internet.")
        self._pump()

    def _on_title(self, title):
        if title.startswith("OK:"):
            self._finish(base64.b64decode(title[3:]).decode("utf-8").strip(), "")
        elif title.startswith("ERR:"):
            self._finish("", base64.b64decode(title[4:]).decode("utf-8"))

    def _finish(self, text, error):
        callback, self._current = self._current, None
        if callback is not None:
            callback(text, error)
        self._pump()
