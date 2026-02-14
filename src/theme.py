"""
Ash Album — Dark theme stylesheet and colour palette.
"""

COLORS = {
    "bg_darkest": "#0b0b12",
    "bg_dark": "#111119",
    "bg_mid": "#1a1a28",
    "bg_light": "#232336",
    "bg_lighter": "#2d2d48",
    "accent": "#7c5cfc",
    "accent_hover": "#9b7dff",
    "accent_pressed": "#6344e0",
    "text": "#ededf4",
    "text_dim": "#8686a4",
    "text_muted": "#55556e",
    "border": "#2a2a3e",
    "success": "#43c667",
    "danger": "#ef5350",
    "warning": "#ffab40",
    "card": "#1c1c2e",
    "card_hover": "#24243c",
    "scrollbar": "#38385a",
    "scrollbar_hover": "#4a4a72",
}


def get_stylesheet() -> str:
    c = COLORS
    return f"""
    /* ======== Global ======== */
    QMainWindow, QDialog {{
        background-color: {c['bg_dark']};
    }}
    QWidget {{
        color: {c['text']};
        font-family: 'Segoe UI', 'Arial', sans-serif;
        font-size: 13px;
    }}

    /* ======== Buttons ======== */
    QPushButton {{
        background-color: {c['bg_light']};
        color: {c['text']};
        border: 1px solid {c['border']};
        padding: 8px 18px;
        border-radius: 7px;
        font-weight: 600;
        font-size: 12px;
    }}
    QPushButton:hover {{
        background-color: {c['bg_lighter']};
        border-color: {c['accent']};
    }}
    QPushButton:pressed {{
        background-color: {c['accent_pressed']};
    }}
    QPushButton:disabled {{
        color: {c['text_muted']};
        background-color: {c['bg_mid']};
        border-color: {c['bg_mid']};
    }}
    QPushButton#accentBtn {{
        background-color: {c['accent']};
        color: #ffffff;
        border: none;
    }}
    QPushButton#accentBtn:hover {{
        background-color: {c['accent_hover']};
    }}
    QPushButton#accentBtn:pressed {{
        background-color: {c['accent_pressed']};
    }}
    QPushButton#dangerBtn {{
        background-color: {c['danger']};
        color: #ffffff;
        border: none;
    }}
    QPushButton#dangerBtn:hover {{
        background-color: #f44336;
    }}
    QPushButton#successBtn {{
        background-color: {c['success']};
        color: #ffffff;
        border: none;
    }}
    QPushButton#successBtn:hover {{
        background-color: #50d870;
    }}

    /* Tab-style toggle buttons */
    QPushButton#tabBtn {{
        background-color: transparent;
        color: {c['text_dim']};
        border: none;
        border-bottom: 3px solid transparent;
        border-radius: 0px;
        padding: 10px 18px;
        font-weight: 700;
        font-size: 12px;
        letter-spacing: 0.6px;
    }}
    QPushButton#tabBtn:hover {{
        color: {c['text']};
        background-color: {c['bg_mid']};
    }}
    QPushButton#tabBtn:checked {{
        color: {c['accent']};
        border-bottom: 3px solid {c['accent']};
        background-color: {c['bg_dark']};
    }}

    /* ======== ComboBox ======== */
    QComboBox {{
        background-color: {c['bg_light']};
        color: {c['text']};
        border: 1px solid {c['border']};
        padding: 7px 14px;
        border-radius: 7px;
        min-width: 210px;
        font-size: 12px;
    }}
    QComboBox:hover {{
        border-color: {c['accent']};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 30px;
    }}
    QComboBox::down-arrow {{
        image: none;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 6px solid {c['text_dim']};
        margin-right: 10px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {c['bg_mid']};
        color: {c['text']};
        border: 1px solid {c['border']};
        selection-background-color: {c['accent']};
        selection-color: #ffffff;
        padding: 4px;
        outline: none;
    }}

    /* ======== List Widget (Gallery) ======== */
    QListWidget {{
        background-color: {c['bg_dark']};
        border: none;
        outline: none;
    }}
    QListWidget::item {{
        background-color: transparent;
        border: none;
    }}

    /* ======== Scroll bars ======== */
    QScrollBar:vertical {{
        background-color: transparent;
        width: 8px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background-color: {c['scrollbar']};
        min-height: 40px;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical:hover {{
        background-color: {c['scrollbar_hover']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: none;
    }}
    QScrollBar:horizontal {{
        background-color: transparent;
        height: 8px;
        margin: 0;
    }}
    QScrollBar::handle:horizontal {{
        background-color: {c['scrollbar']};
        min-width: 40px;
        border-radius: 4px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background-color: {c['scrollbar_hover']};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
    }}

    /* ======== Labels ======== */
    QLabel {{
        color: {c['text']};
    }}
    QLabel#dimLabel {{
        color: {c['text_dim']};
        font-size: 12px;
    }}
    QLabel#titleLabel {{
        font-size: 22px;
        font-weight: 800;
        color: {c['accent']};
        letter-spacing: 1px;
    }}
    QLabel#subtitleLabel {{
        font-size: 12px;
        color: {c['text_dim']};
    }}

    /* ======== Status Bar ======== */
    QStatusBar {{
        background-color: {c['bg_darkest']};
        color: {c['text_dim']};
        border-top: 1px solid {c['border']};
        font-size: 11px;
        padding: 2px 8px;
    }}

    /* ======== Line Edit ======== */
    QLineEdit {{
        background-color: {c['bg_light']};
        color: {c['text']};
        border: 1px solid {c['border']};
        padding: 8px 14px;
        border-radius: 7px;
    }}
    QLineEdit:focus {{
        border-color: {c['accent']};
    }}

    /* ======== Progress Bar ======== */
    QProgressBar {{
        background-color: {c['bg_light']};
        border: none;
        border-radius: 3px;
        height: 6px;
        text-align: center;
    }}
    QProgressBar::chunk {{
        background-color: {c['accent']};
        border-radius: 3px;
    }}

    /* ======== ToolTip ======== */
    QToolTip {{
        background-color: {c['bg_light']};
        color: {c['text']};
        border: 1px solid {c['border']};
        padding: 6px 10px;
        border-radius: 5px;
        font-size: 11px;
    }}

    /* ======== Message Box ======== */
    QMessageBox {{
        background-color: {c['bg_mid']};
    }}
    QMessageBox QLabel {{
        color: {c['text']};
        font-size: 13px;
    }}

    /* ======== Separator line ======== */
    QFrame#separator {{
        background-color: {c['border']};
        max-height: 1px;
    }}
    """
