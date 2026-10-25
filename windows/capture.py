"""Overlay de recorte: congela la pantalla (todos los monitores) y permite arrastrar un área."""
from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget


class SnipOverlay(QWidget):
    captured = Signal(QPixmap)
    cancelled = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setCursor(Qt.CrossCursor)

        screens = QGuiApplication.screens()
        desktop = QRect()
        for s in screens:
            desktop = desktop.united(s.geometry())
        self._origin = desktop.topLeft()
        self.setGeometry(desktop)

        # Captura de todos los monitores en un único lienzo (en píxeles físicos)
        self._dpr = max(s.devicePixelRatio() for s in screens)
        self._shot = QPixmap(int(desktop.width() * self._dpr), int(desktop.height() * self._dpr))
        self._shot.setDevicePixelRatio(self._dpr)
        self._shot.fill(QColor(0, 0, 0))
        painter = QPainter(self._shot)
        for s in screens:
            painter.drawPixmap(s.geometry().topLeft() - self._origin, s.grabWindow(0))
        painter.end()

        self._start = None
        self._end = None

    def _selection(self):
        if self._start is None or self._end is None:
            return QRect()
        return QRect(self._start, self._end).normalized()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.drawPixmap(self.rect(), self._shot)
        p.fillRect(self.rect(), QColor(0, 0, 0, 150))

        sel = self._selection()
        if sel.width() > 0 and sel.height() > 0:
            d = self._dpr
            src = QRect(int(sel.x() * d), int(sel.y() * d), int(sel.width() * d), int(sel.height() * d))
            p.drawPixmap(sel, self._shot, src)
            p.setPen(QPen(QColor(255, 255, 255), 1))
            p.setBrush(Qt.NoBrush)
            p.drawRect(sel.adjusted(0, 0, -1, -1))
            label_y = sel.y() - 8 if sel.y() > 24 else sel.y() + 20
            p.setPen(QColor(235, 235, 235))
            p.drawText(sel.x(), label_y, f"{sel.width()} × {sel.height()}")
        p.end()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._start = e.position().toPoint()
            self._end = self._start
            self.update()
        elif e.button() == Qt.RightButton:
            self.cancel()

    def mouseMoveEvent(self, e):
        if self._start is not None:
            self._end = e.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.LeftButton or self._start is None:
            return
        sel = self._selection()
        if sel.width() < 4 or sel.height() < 4:
            self.cancel()
            return
        d = self._dpr
        crop = self._shot.copy(QRect(int(sel.x() * d), int(sel.y() * d), int(sel.width() * d), int(sel.height() * d)))
        crop.setDevicePixelRatio(1.0)
        self.captured.emit(crop)
        self.close()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.cancel()

    def cancel(self):
        self.cancelled.emit()
        self.close()
