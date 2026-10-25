"""Persistencia local: base SQLite de trabajos, imágenes y configuración."""
import json
import os
import sqlite3
import time
from pathlib import Path

DATA_DIR = Path(os.getenv("APPDATA", Path.home())) / "ScreenOCR"
IMAGES_DIR = DATA_DIR / "images"
DB_PATH = DATA_DIR / "jobs.db"
CONFIG_PATH = DATA_DIR / "config.json"

DEFAULT_CONFIG = {
    "engine": "ocrspace",      # ocrspace (nube), windows (local) o custom (endpoint propio)
    "endpoint": "",
    "api_key": "helloworld",   # clave demo de OCR.space; pon la tuya en Configuración
    "language": "auto",        # auto (EN+ES), eng o spa
    "hotkey": "ctrl+shift+s",
}


def ensure_dirs():
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)


def load_config():
    ensure_dirs()
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_PATH.exists():
        try:
            cfg.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            pass
    return cfg


def save_config(cfg):
    ensure_dirs()
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


class Store:
    def __init__(self, path=DB_PATH):
        ensure_dirs()
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                image_path TEXT NOT NULL,
                text TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                error TEXT NOT NULL DEFAULT '',
                created_at REAL NOT NULL
            )
            """
        )
        self.conn.commit()

    def _write(self, sql, params):
        with self.conn:
            self.conn.execute(sql, params)

    def add_job(self, job_id, title, image_path):
        self._write(
            "INSERT INTO jobs (id, title, image_path, status, created_at) VALUES (?, ?, ?, 'pending', ?)",
            (job_id, title, image_path, time.time()),
        )

    def list_jobs(self):
        rows = self.conn.execute("SELECT * FROM jobs ORDER BY created_at DESC")
        return [dict(r) for r in rows]

    def get_job(self, job_id):
        row = self.conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return dict(row) if row else None

    def set_result(self, job_id, text, status, error=""):
        self._write(
            "UPDATE jobs SET text = ?, status = ?, error = ? WHERE id = ?",
            (text, status, error, job_id),
        )

    def set_status(self, job_id, status):
        self._write("UPDATE jobs SET status = ?, error = '' WHERE id = ?", (status, job_id))

    def update_text(self, job_id, text):
        self._write("UPDATE jobs SET text = ? WHERE id = ?", (text, job_id))

    def rename(self, job_id, title):
        self._write("UPDATE jobs SET title = ? WHERE id = ?", (title, job_id))

    def delete(self, job_id):
        job = self.get_job(job_id)
        self._write("DELETE FROM jobs WHERE id = ?", (job_id,))
        if job:
            try:
                Path(job["image_path"]).unlink(missing_ok=True)
            except OSError:
                pass
