"""Màu sắc, font và stylesheet dùng chung."""
from PySide6.QtGui import QFont

BG = "#F3F5FA"
CARD = "#FFFFFF"
BORDER = "#E4E8F0"
TEXT = "#0F172A"
TEXT_2 = "#334155"
MUTED = "#64748B"
FAINT = "#94A3B8"

FONT_FAMILIES = ["Segoe UI", "Inter", "Roboto", "Helvetica Neue", "Arial"]
MONO_FAMILIES = ["Cascadia Mono", "Consolas", "JetBrains Mono", "DejaVu Sans Mono", "Courier New"]

MODES = {
    "CLASS": {
        "accent": "#3B5BDB", "accent_hover": "#2F4AC0", "soft": "#EEF2FF", "soft_border": "#D9E1FF",
        "box": "#5BD69A", "eyebrow": "CHẾ ĐỘ TRÌNH CHIẾU", "icon": "presentation",
        "title": "Điều khiển bài giảng bằng cử chỉ",
        "subtitle": "Camera đang nhận diện người thuyết trình và các thao tác điều khiển slide.",
    },
    "AFTER": {
        "accent": "#E07A1F", "accent_hover": "#C9690F", "soft": "#FFF4E8", "soft_border": "#FBDDBD",
        "box": "#F59E2B", "eyebrow": "CHẾ ĐỘ AN NINH", "icon": "shield",
        "title": "Giám sát lớp học ngoài giờ",
        "subtitle": "AI đang theo dõi hiện diện và sẵn sàng gửi cảnh báo đến giáo viên chủ nhiệm.",
    },
}

# tone -> (chữ/icon, nền, viền)
TONES = {
    "class":   ("#3B5BDB", "#EEF2FF", "#D9E1FF"),
    "after":   ("#E07A1F", "#FFF4E8", "#FBDDBD"),
    "success": ("#16A34A", "#ECFDF3", "#BBF7D0"),
    "warning": ("#D97706", "#FFF7ED", "#FED7AA"),
    "danger":  ("#DC2626", "#FEF2F2", "#FECACA"),
    "neutral": ("#64748B", "#F1F5F9", "#E2E8F0"),
    "violet":  ("#7C3AED", "#F3EEFF", "#E2D6FE"),
}


def font(px=13, weight=QFont.Normal, spacing=0.0, mono=False):
    f = QFont()
    f.setFamilies(MONO_FAMILIES if mono else FONT_FAMILIES)
    f.setPixelSize(px)
    f.setWeight(weight)
    if spacing:
        f.setLetterSpacing(QFont.AbsoluteSpacing, spacing)
    return f


def stylesheet(mode="CLASS"):
    m = MODES[mode]
    return f"""
    QWidget {{ color: {TEXT}; }}
    QMainWindow, QWidget#root {{ background: {BG}; }}
    QLabel {{ background: transparent; }}
    QToolTip {{ background: #0F172A; color: white; border: none; padding: 6px 8px; border-radius: 6px; }}

    QFrame#card {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 16px; }}
    QFrame#soft {{ background: #F8FAFF; border: 1px solid {BORDER}; border-radius: 14px; }}

    QPushButton {{
        background: {CARD}; color: {TEXT_2}; border: 1px solid #DDE2EC; border-radius: 10px;
        padding: 8px 14px; font-weight: 600;
    }}
    QPushButton:hover {{ background: #F8FAFC; border-color: #C7CFDC; }}
    QPushButton:pressed {{ background: #EEF2F7; }}
    QPushButton:disabled {{ color: {FAINT}; background: #F8FAFC; }}
    QPushButton#primary {{ background: {m['accent']}; color: white; border: none; }}
    QPushButton#primary:hover {{ background: {m['accent_hover']}; }}
    QPushButton#danger {{ background: #DC2626; color: white; border: none; }}
    QPushButton#danger:hover {{ background: #B91C1C; }}
    QPushButton#preset {{ padding: 7px 12px; font-weight: 600; font-size: 12px; border-radius: 9px; }}
    QPushButton#preset:checked {{ background: {m['soft']}; color: {m['accent']}; border: 1px solid {m['accent']}; }}
    QPushButton#ghost {{ background: transparent; border: none; padding: 6px; }}
    QPushButton#ghost:hover {{ background: #EEF1F6; }}

    QFrame#segment {{ background: #E9EDF5; border-radius: 14px; }}
    QFrame#segment QPushButton {{
        background: transparent; border: none; color: {MUTED}; padding: 9px 16px; border-radius: 10px;
        font-weight: 600;
    }}
    QFrame#segment QPushButton:checked {{ background: white; color: {m['accent']}; }}

    QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QTimeEdit {{
        background: white; border: 1px solid #DDE2EC; border-radius: 8px; padding: 6px 8px; color: {TEXT};
        selection-background-color: {m['accent']};
    }}
    QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTimeEdit:focus {{
        border-color: {m['accent']};
    }}
    QComboBox::drop-down {{ border: none; width: 22px; }}
    QComboBox QAbstractItemView {{
        background: white; border: 1px solid {BORDER}; selection-background-color: {m['soft']};
        selection-color: {TEXT}; outline: 0;
    }}
    QCheckBox {{ spacing: 8px; }}
    QScrollArea {{ background: transparent; border: none; }}
    QScrollArea > QWidget > QWidget {{ background: transparent; }}
    QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: #D5DBE6; border-radius: 4px; min-height: 30px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
    QTabWidget::pane {{ border: none; }}
    QDialog {{ background: {BG}; }}
    QPlainTextEdit {{ background: white; border: 1px solid {BORDER}; border-radius: 10px; padding: 8px; }}
    """
