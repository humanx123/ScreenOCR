"""ScreenOCR: captura una zona de pantalla, extrae el texto (EN/ES) con OCR.space y lo deja editable."""
import sys
import uuid
from datetime import datetime
from pathlib import Path

import keyboard
from PySide6.QtCore import QObject, QSize, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QIcon, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from capture import SnipOverlay
from ocr_client import OCRError, ocr_image
from ocr_windows import describe_installed, ocr_windows
from storage import IMAGES_DIR, Store, load_config, save_config
from styles import QSS

ENGINES = [("OCR.space (nube, gratis)", "ocrspace"), ("Windows (local, sin internet)", "windows")]
LANGUAGES = [("Automático (EN + ES)", "auto"), ("Inglés", "eng"), ("Español", "spa")]
STATUS_TEXT = {"pending": "Procesando OCR…", "done": "Listo", "error": "Error"}


class HotkeyBridge(QObject):
    """Puente thread-safe: el hilo de 'keyboard' emite, la UI recibe en el hilo principal."""
    triggered = Signal()


class OcrWorker(QThread):
    done = Signal(str, str, str)  # job_id, texto, error

    def __init__(self, job_id, image_path, cfg):
        super().__init__()
        self.job_id = job_id
        self.image_path = image_path
        self.cfg = dict(cfg)

    def run(self):
        try:
            if self.cfg.get("engine") == "windows":
                text = ocr_windows(self.image_path, self.cfg["language"])
            else:
                text = ocr_image(self.image_path, self.cfg["api_key"], self.cfg["language"])
            self.done.emit(self.job_id, text, "")
        except (OCRError, OSError) as e:
            self.done.emit(self.job_id, "", str(e))
        except Exception as e:  # cualquier fallo inesperado no debe tumbar la app
            self.done.emit(self.job_id, "", f"Error inesperado: {e}")


class ImageView(QLabel):
    """Muestra la captura escalada manteniendo proporción."""

    def __init__(self):
        super().__init__("Sin captura seleccionada")
        self.setAlignment(Qt.AlignCenter)
        self.setObjectName("preview")
        self.setMinimumSize(240, 160)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self._pix = None

    def set_pixmap(self, pix):
        self._pix = pix
        self._rescale()

    def clear_image(self, text="Sin captura seleccionada"):
        self._pix = None
        self.clear()
        self.setText(text)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._rescale()

    def _rescale(self):
        if self._pix and not self._pix.isNull():
            self.setPixmap(self._pix.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))


class JobRow(QWidget):
    edit_requested = Signal(str)
    delete_requested = Signal(str)

    def __init__(self, job):
        super().__init__()
        self.setObjectName("jobRow")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 6, 8, 6)

        info = QVBoxLayout()
        info.setSpacing(2)
        title = QLabel(job["title"])
        title.setObjectName("rowTitle")
        title.setToolTip(job["title"])
        date = datetime.fromtimestamp(job["created_at"]).strftime("%d/%m %H:%M")
        meta = QLabel(f"{STATUS_TEXT.get(job['status'], '')} · {date}")
        meta.setObjectName("rowMeta")
        info.addWidget(title)
        info.addWidget(meta)
        lay.addLayout(info, 1)

        edit = QToolButton()
        edit.setObjectName("iconBtn")
        edit.setText("✎")
        edit.setToolTip("Renombrar")
        edit.clicked.connect(lambda: self.edit_requested.emit(job["id"]))

        delete = QToolButton()
        delete.setObjectName("iconBtn")
        delete.setText("✕")
        delete.setToolTip("Eliminar")
        delete.clicked.connect(lambda: self.delete_requested.emit(job["id"]))

        lay.addWidget(edit)
        lay.addWidget(delete)


class SettingsDialog(QDialog):
    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración")
        self.setMinimumWidth(440)

        form = QFormLayout(self)
        form.setSpacing(14)
        form.setContentsMargins(20, 20, 20, 20)

        self.engine = QComboBox()
        for label, code in ENGINES:
            self.engine.addItem(label, code)
        self.engine.setCurrentIndex(max(0, self.engine.findData(cfg["engine"])))

        self.engine_info = QLabel(describe_installed())
        self.engine_info.setObjectName("status")
        self.engine_info.setWordWrap(True)

        self.api_key = QLineEdit(cfg["api_key"])
        self.api_key.setEchoMode(QLineEdit.Password)
        self.api_key.setPlaceholderText("Clave gratuita de ocr.space/ocrapi/freekey")

        self.language = QComboBox()
        for label, code in LANGUAGES:
            self.language.addItem(label, code)
        self.language.setCurrentIndex(max(0, self.language.findData(cfg["language"])))

        self.hotkey = QLineEdit(cfg["hotkey"])

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        form.addRow("Motor OCR", self.engine)
        form.addRow("", self.engine_info)
        form.addRow("API key OCR.space", self.api_key)
        form.addRow("Idioma", self.language)
        form.addRow("Atajo global", self.hotkey)
        form.addRow(buttons)

    def values(self):
        return {
            "engine": self.engine.currentData(),
            "api_key": self.api_key.text().strip(),
            "language": self.language.currentData(),
            "hotkey": self.hotkey.text().strip() or "ctrl+shift+s",
        }


DONATIONS = [
    ("Bitcoin (BTC)", "bc1qd9j45f4t0jwyhjhqh2kvz2cr7k8xye460rr2y7"),
    ("Monero (XMR)", "447gTj6Hg6gaAEAUmjqfhqDZr1PziUTvbT4LYLpmLVnTNVFK6cqeqPfh6P4neMKLWX5jDXAr94fWHacJwDvjmCzBBH8wPBt"),
    ("USDC (Arbitrum)", "0xAC43f9b0E7F0ae6386cfC8ef6BFf62CE9c3006A1"),
]


class DonateDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Apoyar ScreenOCR")
        self.setMinimumWidth(620)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(14)

        intro = QLabel(
            "ScreenOCR es gratis y de código abierto. Si te ahorra tiempo, "
            "puedes apoyar su desarrollo con una donación voluntaria:"
        )
        intro.setWordWrap(True)
        lay.addWidget(intro)

        for name, address in DONATIONS:
            title = QLabel(name.upper())
            title.setObjectName("sectionTitle")
            lay.addWidget(title)

            row = QHBoxLayout()
            field = QLineEdit(address)
            field.setReadOnly(True)
            field.setCursorPosition(0)
            copy_btn = QPushButton("Copiar")
            copy_btn.clicked.connect(lambda _=False, a=address, b=copy_btn: self._copy(a, b))
            row.addWidget(field, 1)
            row.addWidget(copy_btn)
            lay.addLayout(row)

        close = QDialogButtonBox(QDialogButtonBox.Close)
        close.rejected.connect(self.reject)
        close.accepted.connect(self.accept)
        lay.addWidget(close)

    def _copy(self, text, button):
        QApplication.clipboard().setText(text)
        button.setText("¡Copiado!")
        QTimer.singleShot(1500, lambda: button.setText("Copiar"))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ScreenOCR")
        self.resize(1240, 780)

        self.store = Store()
        self.cfg = load_config()
        self._workers = set()
        self._current_id = None
        self._overlay = None
        self._hotkey_handle = None

        self._bridge = HotkeyBridge()
        self._bridge.triggered.connect(self.start_capture)

        self._build_ui()
        self.refresh_list()
        self.register_hotkey()

    # ---------- UI ----------
    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Barra superior
        top = QFrame()
        top.setObjectName("topbar")
        top.setFixedHeight(64)
        tl = QHBoxLayout(top)
        tl.setContentsMargins(24, 0, 24, 0)
        title = QLabel("SCREEN OCR")
        title.setObjectName("appTitle")
        tl.addWidget(title)
        tl.addStretch()

        btn_donate = QPushButton("Donar")
        btn_donate.setToolTip("Apoyar el proyecto (BTC, XMR, USDC)")
        btn_donate.clicked.connect(lambda: DonateDialog(self).exec())
        btn_settings = QPushButton("Configuración")
        btn_settings.clicked.connect(self.open_settings)
        tl.addWidget(btn_donate)
        tl.addSpacing(8)
        btn_capture = QPushButton(f"Nueva captura   {self.cfg['hotkey'].upper()}")
        btn_capture.setObjectName("primary")
        btn_capture.clicked.connect(self.start_capture)
        tl.addWidget(btn_settings)
        tl.addSpacing(8)
        tl.addWidget(btn_capture)
        outer.addWidget(top)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        outer.addLayout(body, 1)

        # Columna izquierda: trabajos
        side = QFrame()
        side.setObjectName("sidebar")
        side.setFixedWidth(340)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(0, 20, 0, 16)
        hdr = QLabel("TRABAJOS")
        hdr.setObjectName("sectionTitle")
        hdr.setContentsMargins(24, 0, 0, 8)
        sl.addWidget(hdr)
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self.on_select)
        sl.addWidget(self.list, 1)
        body.addWidget(side)

        # Columna derecha: captura arriba, texto editable abajo
        main = QWidget()
        ml = QVBoxLayout(main)
        ml.setContentsMargins(28, 24, 28, 20)
        ml.setSpacing(14)

        self.preview = ImageView()
        ml.addWidget(self.preview, 3)

        lbl = QLabel("TEXTO RECONOCIDO")
        lbl.setObjectName("sectionTitle")
        ml.addWidget(lbl)

        self.editor = QPlainTextEdit()
        self.editor.setObjectName("editor")
        self.editor.setPlaceholderText("El texto extraído aparecerá aquí. Puedes editarlo.")
        ml.addWidget(self.editor, 2)

        bar = QHBoxLayout()
        self.status = QLabel("")
        self.status.setObjectName("status")
        bar.addWidget(self.status, 1)

        self.btn_retry = QPushButton("Reintentar OCR")
        self.btn_retry.clicked.connect(self.retry_ocr)
        self.btn_copy = QPushButton("Copiar")
        self.btn_copy.clicked.connect(self.copy_text)
        self.btn_save = QPushButton("Guardar")
        self.btn_save.clicked.connect(self.save_text)
        for b in (self.btn_retry, self.btn_copy, self.btn_save):
            bar.addWidget(b)
        ml.addLayout(bar)

        body.addWidget(main, 1)

        QShortcut(QKeySequence("Ctrl+S"), self, activated=self.save_text)
        self._set_detail_enabled(False)

    def _set_detail_enabled(self, enabled, job=None):
        self.editor.setEnabled(enabled)
        busy = bool(job and job["status"] == "pending")
        self.editor.setReadOnly(busy)
        self.btn_copy.setEnabled(enabled and not busy)
        self.btn_save.setEnabled(enabled and not busy)
        self.btn_retry.setEnabled(enabled and bool(job and job["status"] == "error"))

    # ---------- Lista ----------
    def refresh_list(self, select_id=None):
        self.list.blockSignals(True)
        self.list.clear()
        target = None
        wanted = select_id or self._current_id
        for job in self.store.list_jobs():
            item = QListWidgetItem()
            item.setData(Qt.UserRole, job["id"])
            item.setSizeHint(QSize(0, 66))
            self.list.addItem(item)
            row = JobRow(job)
            row.edit_requested.connect(self.rename_job)
            row.delete_requested.connect(self.delete_job)
            self.list.setItemWidget(item, row)
            if job["id"] == wanted:
                target = item
        self.list.blockSignals(False)

        if target is not None:
            self.list.setCurrentItem(target)  # on_select ignora si ya está cargado
        elif self.list.count():
            self.list.setCurrentRow(0)
        else:
            self.on_select(None, None)

    def on_select(self, current, _previous):
        job_id = current.data(Qt.UserRole) if current else None
        if job_id == self._current_id:
            return
        self._current_id = job_id
        if job_id is None:
            self.preview.clear_image()
            self.editor.clear()
            self.status.setText("")
            self._set_detail_enabled(False)
            return
        self.load_job(job_id)

    def load_job(self, job_id):
        job = self.store.get_job(job_id)
        if job is None:
            return
        self._current_id = job_id
        self.preview.set_pixmap(QPixmap(job["image_path"]))
        self.editor.setPlainText(job["text"])
        self._set_detail_enabled(True, job)

        if job["status"] == "pending":
            self.status.setText("Procesando OCR…")
        elif job["status"] == "error":
            self.status.setText(f"Error: {job['error']}")
        elif not job["text"].strip():
            self.status.setText("No se detectó texto en la captura.")
        else:
            self.status.setText("Listo")

    # ---------- Acciones de trabajo ----------
    def rename_job(self, job_id):
        job = self.store.get_job(job_id)
        if not job:
            return
        name, ok = QInputDialog.getText(self, "Renombrar", "Nombre del trabajo:", text=job["title"])
        if ok and name.strip():
            self.store.rename(job_id, name.strip())
            self.refresh_list()

    def delete_job(self, job_id):
        job = self.store.get_job(job_id)
        if not job:
            return
        answer = QMessageBox.question(
            self, "Eliminar", f"¿Eliminar «{job['title']}» y su captura?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        if job_id == self._current_id:
            self._current_id = None
        self.store.delete(job_id)
        self.refresh_list()

    def save_text(self):
        if self._current_id is None or not self.editor.isEnabled() or self.editor.isReadOnly():
            return
        self.store.update_text(self._current_id, self.editor.toPlainText())
        self.status.setText("Guardado")

    def copy_text(self):
        QApplication.clipboard().setText(self.editor.toPlainText())
        self.status.setText("Texto copiado al portapapeles")

    def retry_ocr(self):
        job = self.store.get_job(self._current_id) if self._current_id else None
        if not job:
            return
        self.store.set_status(job["id"], "pending")
        self._run_ocr(job["id"], job["image_path"])
        self.refresh_list()
        self.load_job(job["id"])

    # ---------- Captura ----------
    def register_hotkey(self):
        try:
            if self._hotkey_handle is not None:
                keyboard.remove_hotkey(self._hotkey_handle)
            self._hotkey_handle = keyboard.add_hotkey(self.cfg["hotkey"], self._bridge.triggered.emit)
        except Exception as e:
            self._hotkey_handle = None
            QMessageBox.warning(self, "Atajo", f"No se pudo registrar el atajo «{self.cfg['hotkey']}»:\n{e}")

    def start_capture(self):
        if self._overlay is not None:
            return
        self.hide()
        QTimer.singleShot(250, self._open_overlay)  # deja que la ventana desaparezca

    def _open_overlay(self):
        self._overlay = SnipOverlay()
        self._overlay.captured.connect(self.on_captured)
        self._overlay.cancelled.connect(self._restore)
        self._overlay.show()
        self._overlay.activateWindow()
        self._overlay.setFocus()

    def _restore(self):
        self._overlay = None
        self.show()
        self.raise_()
        self.activateWindow()

    def on_captured(self, pix):
        self._overlay = None
        job_id = uuid.uuid4().hex
        path = IMAGES_DIR / f"{job_id}.png"
        pix.save(str(path), "PNG")
        title = f"Captura {datetime.now():%d/%m/%Y %H:%M:%S}"
        self.store.add_job(job_id, title, str(path))
        self._restore()
        self.refresh_list(select_id=job_id)
        self.load_job(job_id)
        self._run_ocr(job_id, str(path))

    def _run_ocr(self, job_id, path):
        worker = OcrWorker(job_id, path, self.cfg)
        worker.done.connect(self.on_ocr_done)
        worker.finished.connect(lambda w=worker: self._workers.discard(w))
        self._workers.add(worker)
        worker.start()

    def on_ocr_done(self, job_id, text, error):
        if error:
            self.store.set_result(job_id, "", "error", error)
        else:
            self.store.set_result(job_id, text, "done")
        self.refresh_list()
        if job_id == self._current_id:
            self.load_job(job_id)

    # ---------- Config / cierre ----------
    def open_settings(self):
        dlg = SettingsDialog(self.cfg, self)
        if dlg.exec() == QDialog.Accepted:
            self.cfg = dlg.values()
            save_config(self.cfg)
            self.register_hotkey()

    def closeEvent(self, event):
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass
        event.accept()
        QApplication.quit()


def resource_path(name):
    """Ruta a un recurso junto al script o dentro del ejecutable empaquetado."""
    base = getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)
    return str(Path(base) / name)


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--selftest-ocr":
        # Diagnóstico: ScreenOCR.exe --selftest-ocr imagen.png  (imprime el texto y sale)
        try:
            print(ocr_windows(sys.argv[2], "auto"))
            sys.exit(0)
        except OCRError as e:
            print(f"ERROR: {e}")
            sys.exit(1)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # el overlay de captura puede cerrarse sin cerrar la app
    app.setStyleSheet(QSS)
    app.setWindowIcon(QIcon(resource_path("icon.ico")))  # barra de tareas y ventanas
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
