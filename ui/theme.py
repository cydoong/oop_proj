"""
ui.theme
==========
A single cohesive dark "neon purple" theme for the whole app, built
from the same palette as the original system's css/style.css
(--pink:#E040FB, --purple-mid:#a855f7, --cyan:#22d3ee, dark
backgrounds, etc). One QSS stylesheet, applied once at startup.
"""
from pathlib import Path

# Real icon files on disk, referenced by absolute path. An earlier
# version tried embedding these as base64 data: URIs directly in the
# stylesheet, but Qt's QSS `url()` does not reliably load inline data
# URIs across Qt versions/platforms — real file paths are the robust,
# guaranteed-to-work option, so that's what every icon reference below
# uses. Path().as_posix() ensures forward slashes even on Windows,
# which is what Qt's stylesheet parser expects.
_ICONS_DIR = (Path(__file__).resolve().parent.parent / "assets" / "icons")


def _icon(name: str) -> str:
    return (_ICONS_DIR / name).as_posix()

# ── Palette ────────────────────────────────────────────────────────────
BG_DARKEST = "#0e0b1a"
BG_DARK = "#120e21"
BG_CARD = "#181329"
BG_CARD_HOVER = "#1e1836"
BG_ELEVATED = "#221c3d"
BORDER = "#2c2547"
BORDER_LIGHT = "#3a3163"

PINK = "#E040FB"
PINK_DIM = "#a855c9"
PURPLE = "#a855f7"
CYAN = "#22d3ee"
SUCCESS = "#4ade80"
WARNING = "#fbbf24"
DANGER = "#f87171"
INFO = "#60a5fa"

TEXT = "#e8e0f7"
TEXT_DIM = "#a89fc4"
TEXT_MUTED = "#7c6f9e"

GRADIENT_PRIMARY = f"qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {PINK}, stop:1 {PURPLE})"


def build_stylesheet() -> str:
    return f"""
    * {{
        font-family: 'Segoe UI', 'Segoe UI Emoji', 'Segoe UI Symbol', 'Inter', Arial, sans-serif;
        outline: none;
    }}

    QWidget {{
        background-color: {BG_DARK};
        color: {TEXT};
        font-size: 13px;
    }}

    QMainWindow, QDialog {{
        background-color: {BG_DARK};
    }}

    /* ── Scrollbars ── */
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {BORDER_LIGHT};
        border-radius: 5px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {PINK_DIM}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar:horizontal {{ background: transparent; height: 10px; }}
    QScrollBar::handle:horizontal {{ background: {BORDER_LIGHT}; border-radius: 5px; min-width: 30px; }}

    /* ── Labels ── */
    QLabel {{ background: transparent; color: {TEXT}; }}
    QLabel[role="title"] {{ font-size: 20px; font-weight: 800; color: #ffffff; }}
    QLabel[role="subtitle"] {{ font-size: 13px; color: {TEXT_MUTED}; }}
    QLabel[role="section"] {{ font-size: 15px; font-weight: 700; color: #ffffff; }}
    QLabel[role="muted"] {{ color: {TEXT_MUTED}; font-size: 12px; }}
    QLabel[role="error"] {{ color: {DANGER}; font-size: 12px; font-weight: 600; }}
    QLabel[role="stat-value"] {{ font-size: 26px; font-weight: 800; color: #ffffff; }}
    QLabel[role="stat-label"] {{ font-size: 11px; font-weight: 600; color: {TEXT_MUTED}; text-transform: uppercase; }}
    QLabel[role="code"] {{ font-family: 'Consolas', 'Courier New', monospace; letter-spacing: 2px; font-weight: 800; color: {PINK}; }}

    /* ── Buttons ── */
    QPushButton {{
        background-color: {BG_ELEVATED};
        color: {TEXT};
        border: 1px solid {BORDER_LIGHT};
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 600;
    }}
    QPushButton:hover {{ background-color: {BG_CARD_HOVER}; border-color: {PINK_DIM}; }}
    QPushButton:pressed {{ background-color: {BG_DARKEST}; }}
    QPushButton:disabled {{ color: {TEXT_MUTED}; border-color: {BORDER}; }}

    QPushButton[variant="primary"] {{
        background-color: {PINK};
        border: 1px solid {PINK};
        color: #1a0a22;
        font-weight: 700;
    }}
    QPushButton[variant="primary"]:hover {{ background-color: #ea6bfc; }}
    QPushButton[variant="primary"]:pressed {{ background-color: #c930e0; }}
    QPushButton[variant="primary"]:disabled {{ background-color: {BORDER_LIGHT}; color: {TEXT_MUTED}; border-color: {BORDER_LIGHT}; }}

    QPushButton[variant="success"] {{ background-color: {SUCCESS}; border: 1px solid {SUCCESS}; color: #06280f; }}
    QPushButton[variant="success"]:hover {{ background-color: #6ee89a; }}

    QPushButton[variant="danger"] {{ background-color: transparent; border: 1px solid {DANGER}; color: {DANGER}; }}
    QPushButton[variant="danger"]:hover {{ background-color: rgba(248,113,113,0.15); }}

    QPushButton[variant="ghost"] {{ background-color: transparent; border: 1px solid {BORDER_LIGHT}; color: {TEXT_DIM}; }}
    QPushButton[variant="ghost"]:hover {{ background-color: {BG_CARD_HOVER}; color: {TEXT}; }}

    QPushButton[variant="link"] {{ background: transparent; border: none; color: {PINK}; font-weight: 600; padding: 2px; }}
    QPushButton[variant="link"]:hover {{ color: {CYAN}; text-decoration: underline; }}

    /* ── Inputs ── */
    QLineEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox, QTextEdit, QPlainTextEdit {{
        background-color: {BG_CARD};
        border: 1px solid {BORDER_LIGHT};
        border-radius: 8px;
        padding: 8px 10px;
        color: {TEXT};
        selection-background-color: {PINK};
        selection-color: #1a0a22;
    }}
    QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus {{
        border: 1px solid {PINK};
    }}
    QLineEdit:disabled, QComboBox:disabled {{ color: {TEXT_MUTED}; background-color: {BG_DARK}; }}
    QLineEdit[error="true"] {{ border: 1px solid {DANGER}; }}
    QLineEdit[success="true"] {{ border: 1px solid {SUCCESS}; }}

    /* Dropdown/calendar buttons used to have "border: none" with no
       explicit arrow image — Fusion then didn't draw anything there
       either, so the button existed and worked but was completely
       invisible, giving no hint it was clickable. Giving it a subtle
       left divider plus an explicit icon fixes both problems. */
    QComboBox::drop-down {{
        border: none; border-left: 1px solid {BORDER_LIGHT};
        width: 28px; background: transparent;
    }}
    QComboBox::down-arrow {{
        image: url({_icon('chevron_down.svg')});
        width: 11px; height: 11px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {BG_ELEVATED};
        border: 1px solid {BORDER_LIGHT};
        selection-background-color: {PINK};
        selection-color: #1a0a22;
        outline: none;
        padding: 4px;
    }}
    QDateEdit::drop-down {{
        border: none; border-left: 1px solid {BORDER_LIGHT};
        width: 28px; background: transparent;
    }}
    QDateEdit::down-arrow {{
        image: url({_icon('calendar.svg')});
        width: 14px; height: 14px;
    }}
    QCheckBox {{ color: {TEXT}; spacing: 8px; }}
    QCheckBox::indicator {{
        width: 18px; height: 18px; border-radius: 5px;
        border: 1px solid {BORDER_LIGHT}; background: {BG_CARD};
    }}
    QCheckBox::indicator:checked {{
        background: {PINK}; border-color: {PINK};
        image: url({_icon('check.svg')});
    }}
    QCheckBox::indicator:hover {{ border-color: {PINK_DIM}; }}
    QRadioButton {{ color: {TEXT}; spacing: 8px; }}
    QRadioButton::indicator {{ width: 16px; height: 16px; border-radius: 8px; border: 1px solid {BORDER_LIGHT}; background: {BG_CARD}; }}
    QRadioButton::indicator:checked {{
        background: {PINK}; border-color: {PINK};
        image: url({_icon('radio_dot.svg')});
    }}

    /* ── Calendar popup (QDateEdit's dropdown) ── */
    QCalendarWidget {{ background-color: {BG_ELEVATED}; }}
    QCalendarWidget QWidget#qt_calendar_navigationbar {{ background-color: {BG_ELEVATED}; }}
    QCalendarWidget QToolButton {{
        color: {TEXT}; background-color: transparent; border: none;
        border-radius: 6px; padding: 6px 10px; font-weight: 600; font-size: 12px;
        icon-size: 16px;
    }}
    QCalendarWidget QToolButton:hover {{ background-color: {BG_CARD_HOVER}; }}
    QCalendarWidget QToolButton::menu-indicator {{ image: none; width: 0; }}
    QCalendarWidget QMenu {{ background-color: {BG_ELEVATED}; color: {TEXT}; border: 1px solid {BORDER_LIGHT}; }}
    QCalendarWidget QSpinBox {{
        background-color: {BG_CARD}; color: {TEXT}; border: 1px solid {BORDER_LIGHT};
        border-radius: 4px; padding: 2px 4px;
    }}
    QCalendarWidget QAbstractItemView {{
        background-color: {BG_CARD}; color: {TEXT}; selection-background-color: {PINK};
        selection-color: #1a0a22; border: none; outline: none; gridline-color: {BORDER};
    }}
    QCalendarWidget QAbstractItemView:disabled {{ color: {TEXT_MUTED}; }}
    /* Reset the header row (Sun/Mon/Tue...) separately from data tables —
       the generic QHeaderView padding/uppercase rule below was making
       these truncate to "..." since the day abbreviations are short. */
    QCalendarWidget QHeaderView {{ background-color: {BG_ELEVATED}; }}
    QCalendarWidget QHeaderView::section {{
        background-color: {BG_ELEVATED}; color: {TEXT_DIM}; border: none;
        padding: 4px 0px; font-size: 11px; font-weight: 700; text-transform: none;
    }}

    /* ── Cards / Frames ── */
    QFrame[card="true"] {{
        background-color: {BG_CARD};
        border: 1px solid {BORDER};
        border-radius: 14px;
    }}
    QFrame[card="stat"] {{
        background-color: {BG_CARD};
        border: 1px solid {BORDER};
        border-radius: 14px;
    }}
    QFrame[card="stat"]:hover {{ border: 1px solid {PINK_DIM}; }}
    QFrame[divider="true"] {{ background-color: {BORDER}; max-height: 1px; min-height: 1px; }}

    /* ── Sidebar ── */
    QFrame#sidebar {{ background-color: {BG_DARKEST}; border-right: 1px solid {BORDER}; }}
    QPushButton[nav="true"] {{
        background: transparent;
        border: none;
        border-radius: 10px;
        text-align: left;
        padding: 10px 14px;
        color: {TEXT_DIM};
        font-weight: 600;
        font-size: 13px;
    }}
    QPushButton[nav="true"]:hover {{ background-color: {BG_CARD}; color: {TEXT}; }}
    QPushButton[nav="true"][active="true"] {{
        background-color: rgba(224,64,251,0.14);
        color: {PINK};
        border: 1px solid rgba(224,64,251,0.35);
    }}

    /* ── Top bar ── */
    QFrame#topbar {{ background-color: {BG_DARK}; border-bottom: 1px solid {BORDER}; }}

    /* ── Tables ── */
    QTableWidget, QTableView {{
        background-color: {BG_CARD};
        alternate-background-color: {BG_DARK};
        border: 1px solid {BORDER};
        border-radius: 10px;
        gridline-color: {BORDER};
        selection-background-color: rgba(224,64,251,0.18);
        selection-color: {TEXT};
    }}
    QHeaderView::section {{
        background-color: {BG_ELEVATED};
        color: {TEXT_MUTED};
        padding: 8px;
        border: none;
        border-bottom: 1px solid {BORDER_LIGHT};
        font-weight: 700;
        font-size: 11px;
        text-transform: uppercase;
    }}
    QTableWidget::item, QTableView::item {{ padding: 6px; border-bottom: 1px solid {BORDER}; }}
    QTableCornerButton::section {{ background-color: {BG_ELEVATED}; border: none; }}

    /* ── Tabs ── */
    QTabWidget::pane {{ border: 1px solid {BORDER}; border-radius: 10px; top: -1px; }}
    QTabBar::tab {{
        background: transparent;
        color: {TEXT_MUTED};
        padding: 8px 18px;
        margin-right: 4px;
        border-bottom: 2px solid transparent;
        font-weight: 600;
    }}
    QTabBar::tab:selected {{ color: {PINK}; border-bottom: 2px solid {PINK}; }}
    QTabBar::tab:hover {{ color: {TEXT}; }}

    /* ── ToolTips ── */
    QToolTip {{
        background-color: {BG_ELEVATED};
        color: {TEXT};
        border: 1px solid {BORDER_LIGHT};
        padding: 6px 8px;
        border-radius: 6px;
    }}

    /* ── ProgressBar ── */
    QProgressBar {{
        background-color: {BG_CARD};
        border: 1px solid {BORDER};
        border-radius: 8px;
        text-align: center;
        color: {TEXT};
    }}
    QProgressBar::chunk {{ background-color: {PINK}; border-radius: 7px; }}

    /* ── Menu ── */
    QMenu {{
        background-color: {BG_ELEVATED};
        border: 1px solid {BORDER_LIGHT};
        border-radius: 8px;
        padding: 6px;
    }}
    QMenu::item {{ padding: 8px 24px 8px 12px; border-radius: 6px; }}
    QMenu::item:selected {{ background-color: rgba(224,64,251,0.18); color: {PINK}; }}
    QMenu::separator {{ height: 1px; background: {BORDER}; margin: 4px 8px; }}

    QSplitter::handle {{ background-color: {BORDER}; }}

    QListWidget {{
        background-color: {BG_CARD};
        border: 1px solid {BORDER};
        border-radius: 10px;
        padding: 4px;
    }}
    QListWidget::item {{ padding: 8px; border-radius: 6px; }}
    QListWidget::item:selected {{ background-color: rgba(224,64,251,0.18); color: {PINK}; }}

    QMessageBox {{ background-color: {BG_CARD}; }}
    """


STATUS_COLORS = {
    "draft": TEXT_MUTED,
    "approved": INFO,
    "paid": SUCCESS,
    "cancelled": DANGER,
    "active": SUCCESS,
    "inactive": WARNING,
    "terminated": DANGER,
    "on_leave": INFO,
    "open": SUCCESS,
    "processing": WARNING,
    "closed": TEXT_MUTED,
    "sent": SUCCESS,
    "failed": DANGER,
}


def status_color(status: str) -> str:
    return STATUS_COLORS.get((status or "").lower(), TEXT_MUTED)
