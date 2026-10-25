"""Tema oscuro minimalista."""

QSS = """
QWidget {
    background: #000000;
    color: #e8e8e8;
    font-family: 'Segoe UI';
    font-size: 10pt;
}
QLabel, QToolButton { background: transparent; }

#topbar { background: #000000; border-bottom: 1px solid #1c1c1c; }
#appTitle { font-size: 12pt; font-weight: 600; letter-spacing: 3px; }
#sectionTitle { color: #7a7a7a; font-size: 8pt; letter-spacing: 2px; }
#status { color: #7a7a7a; font-size: 9pt; }

#sidebar { background: #070707; border-right: 1px solid #1c1c1c; }
QListWidget { background: transparent; border: none; outline: none; }
QListWidget::item { border-radius: 10px; margin: 2px 10px; }
QListWidget::item:hover { background: #111111; }
QListWidget::item:selected { background: #1a1a1a; }
#jobRow { background: transparent; }
#rowTitle { font-weight: 500; }
#rowMeta { color: #6b6b6b; font-size: 8pt; }

QToolButton#iconBtn {
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 3px 7px;
    color: #8a8a8a;
}
QToolButton#iconBtn:hover { background: #1f1f1f; color: #ffffff; border-color: #2c2c2c; }
QToolButton#dangerBtn:hover { color: #ff6b6b; }

QPushButton {
    background: #0c0c0c;
    border: 1px solid #262626;
    border-radius: 8px;
    padding: 8px 16px;
}
QPushButton:hover { background: #161616; border-color: #3a3a3a; }
QPushButton:disabled { color: #4a4a4a; border-color: #1a1a1a; }
QPushButton#primary {
    background: #ffffff;
    color: #000000;
    border: none;
    font-weight: 600;
}
QPushButton#primary:hover { background: #d6d6d6; }

#preview {
    background: #050505;
    border: 1px solid #1c1c1c;
    border-radius: 12px;
    color: #4a4a4a;
}

QPlainTextEdit, QLineEdit, QComboBox {
    background: #080808;
    border: 1px solid #1f1f1f;
    border-radius: 10px;
    padding: 10px;
    selection-background-color: #3a3a3a;
}
QPlainTextEdit:focus, QLineEdit:focus, QComboBox:focus { border-color: #4a4a4a; }
#editor { font-family: 'Consolas'; font-size: 11pt; }

QComboBox QAbstractItemView {
    background: #0a0a0a;
    border: 1px solid #262626;
    selection-background-color: #1f1f1f;
}

QScrollBar:vertical { background: transparent; width: 8px; margin: 0; }
QScrollBar::handle:vertical { background: #2a2a2a; border-radius: 4px; min-height: 30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
"""
