"""
ui.widgets.common
====================
Small reusable widgets shared across every page: stat cards, status
badges, toast notifications, section headers, and a confirm dialog.
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QApplication, QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QSizePolicy, QVBoxLayout, QWidget, QGraphicsDropShadowEffect,
)

from ui import theme


def copy_to_clipboard(text: str):
    QApplication.clipboard().setText(text or "")


_VARIANT_QSS = {
    "primary": f"""
        QPushButton {{
            background-color: {theme.PINK};
            border: 1px solid {theme.PINK};
            color: #1a0a22;
            font-weight: 700;
            border-radius: 8px;
            padding: 8px 16px;
        }}
        QPushButton:hover {{ background-color: #ea6bfc; border-color: #ea6bfc; }}
        QPushButton:pressed {{ background-color: #c930e0; border-color: #c930e0; }}
        QPushButton:disabled {{
            background-color: {theme.BORDER_LIGHT}; color: {theme.TEXT_MUTED}; border-color: {theme.BORDER_LIGHT};
        }}
    """,
    "success": f"""
        QPushButton {{
            background-color: {theme.SUCCESS}; border: 1px solid {theme.SUCCESS};
            color: #06280f; font-weight: 700; border-radius: 8px; padding: 8px 16px;
        }}
        QPushButton:hover {{ background-color: #6ee89a; border-color: #6ee89a; }}
        QPushButton:pressed {{ background-color: #35c56a; border-color: #35c56a; }}
    """,
    "danger": f"""
        QPushButton {{
            background-color: transparent; border: 1px solid {theme.DANGER}; color: {theme.DANGER};
            font-weight: 700; border-radius: 8px; padding: 8px 16px;
        }}
        QPushButton:hover {{ background-color: rgba(248,113,113,0.15); }}
        QPushButton:pressed {{ background-color: rgba(248,113,113,0.28); }}
    """,
    "ghost": f"""
        QPushButton {{
            background-color: transparent; border: 1px solid {theme.BORDER_LIGHT}; color: {theme.TEXT_DIM};
            font-weight: 600; border-radius: 8px; padding: 8px 16px;
        }}
        QPushButton:hover {{ background-color: {theme.BG_CARD_HOVER}; color: {theme.TEXT}; }}
        QPushButton:pressed {{ background-color: {theme.BG_DARKEST}; }}
    """,
    "link": f"""
        QPushButton {{
            background-color: transparent; border: none; color: {theme.PINK};
            font-weight: 700; padding: 2px;
        }}
        QPushButton:hover {{ color: {theme.CYAN}; text-decoration: underline; }}
    """,
}


def make_button(text: str, variant: str = "default", parent=None, compact: bool = False) -> QPushButton:
    """Create a themed QPushButton. Styling is applied directly to the
    widget (not just via dynamic-property + global stylesheet), so it
    renders correctly regardless of Qt version, platform, or style
    (Fusion/native) quirks around dynamic-property polish timing."""
    btn = QPushButton(text, parent)
    if variant != "default":
        btn.setProperty("variant", variant)
        if variant in _VARIANT_QSS:
            css = _VARIANT_QSS[variant]
            if compact:
                # Properly wrapped in its own selector block — never
                # concatenate bare "property: value;" pairs onto an
                # existing stylesheet string, that produces invalid CSS
                # that Qt can silently fail to apply (this was the cause
                # of action-bar buttons rendering with no visible
                # background/text).
                css += "\nQPushButton { padding: 4px 10px; font-size: 11px; }"
            btn.setStyleSheet(css)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setMinimumHeight(28 if compact else 36)
    return btn


class StatCard(QFrame):
    """A KPI card: icon + big number + label, optional trend/subtext."""

    def __init__(self, label: str, value: str, icon: str = "\U0001F4CA", accent: str = theme.PINK,
                 subtext: str = "", parent=None):
        super().__init__(parent)
        self.setProperty("card", "stat")
        self.setMinimumHeight(100)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(4)

        top = QHBoxLayout()
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(f"font-size: 22px; background: rgba(255,255,255,0.04); "
                                f"border-radius: 10px; padding: 6px 10px; color: {accent};")
        top.addWidget(icon_lbl)
        top.addStretch()
        lay.addLayout(top)

        self.value_lbl = QLabel(value)
        self.value_lbl.setProperty("role", "stat-value")
        lay.addWidget(self.value_lbl)

        label_lbl = QLabel(label)
        label_lbl.setProperty("role", "stat-label")
        lay.addWidget(label_lbl)

        if subtext:
            sub = QLabel(subtext)
            sub.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 11px;")
            lay.addWidget(sub)

    def set_value(self, value: str):
        self.value_lbl.setText(value)


class Badge(QLabel):
    """A small rounded status pill, e.g. 'Approved', 'Active'."""

    def __init__(self, text: str, color: Optional[str] = None, parent=None):
        super().__init__(text.replace("_", " ").title(), parent)
        color = color or theme.status_color(text)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(f"""
            background-color: rgba({self._to_rgb(color)}, 0.16);
            color: {color};
            border: 1px solid rgba({self._to_rgb(color)}, 0.4);
            border-radius: 10px;
            padding: 3px 10px;
            font-weight: 700;
            font-size: 11px;
        """)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)

    @staticmethod
    def _to_rgb(hex_color: str) -> str:
        hex_color = hex_color.lstrip("#")
        if len(hex_color) != 6:
            return "124,111,158"
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        return f"{r},{g},{b}"


class SectionHeader(QWidget):
    """Page title + subtitle + optional right-side action button."""

    def __init__(self, title: str, subtitle: str = "", action_text: str = "", parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        text_box = QVBoxLayout()
        text_box.setSpacing(2)
        t = QLabel(title)
        t.setProperty("role", "title")
        text_box.addWidget(t)
        if subtitle:
            s = QLabel(subtitle)
            s.setProperty("role", "subtitle")
            text_box.addWidget(s)
        lay.addLayout(text_box)
        lay.addStretch()
        self.action_btn: Optional[QPushButton] = None
        if action_text:
            self.action_btn = make_button(action_text, "primary")
            lay.addWidget(self.action_btn, alignment=Qt.AlignmentFlag.AlignTop)


class SearchBox(QLineEdit):
    def __init__(self, placeholder: str = "Search...", parent=None):
        super().__init__(parent)
        self.setPlaceholderText("\U0001F50D  " + placeholder)
        self.setMinimumHeight(36)
        self.setMinimumWidth(240)


def confirm(parent, title: str, message: str, danger: bool = False) -> bool:
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(message)
    box.setIcon(QMessageBox.Icon.Warning if danger else QMessageBox.Icon.Question)
    yes_btn = box.addButton("Yes, Continue" if not danger else "Yes, Proceed", QMessageBox.ButtonRole.YesRole)
    box.addButton("Cancel", QMessageBox.ButtonRole.NoRole)
    box.exec()
    return box.clickedButton() is yes_btn


def info(parent, title: str, message: str):
    QMessageBox.information(parent, title, message)


def warn(parent, title: str, message: str):
    QMessageBox.warning(parent, title, message)


def error(parent, title: str, message: str):
    QMessageBox.critical(parent, title, message)


class Toast(QFrame):
    """A transient notification banner that fades away on its own."""

    def __init__(self, parent: QWidget, message: str, kind: str = "success", duration_ms: int = 3200):
        super().__init__(parent)
        colors = {"success": theme.SUCCESS, "error": theme.DANGER, "info": theme.CYAN, "warning": theme.WARNING}
        color = colors.get(kind, theme.SUCCESS)
        icons = {"success": "\u2713", "error": "\u2717", "info": "\u2139", "warning": "\u26A0"}
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.BG_ELEVATED};
                border: 1px solid {color};
                border-radius: 10px;
            }}
            QLabel {{ color: {theme.TEXT}; font-weight: 600; background: transparent; }}
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        icon = QLabel(icons.get(kind, ""))
        icon.setStyleSheet(f"color: {color}; font-size: 15px; font-weight: 800; background: transparent;")
        lay.addWidget(icon)
        lbl = QLabel(message)
        lbl.setWordWrap(True)
        lay.addWidget(lbl, 1)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        self.adjustSize()
        self._position(parent)
        self.show()
        self.raise_()
        QTimer.singleShot(duration_ms, self.close)

    def _position(self, parent: QWidget):
        margin = 24
        x = parent.width() - self.width() - margin
        y = margin
        self.move(max(x, margin), y)


def show_toast(parent: QWidget, message: str, kind: str = "success"):
    t = Toast(parent, message, kind)
    return t


class CopyableInfoDialog(QDialog):
    """Info dialog for showing generated credentials (username, passcode,
    employee code, etc.) with a one-click Copy button next to each value,
    instead of making people manually select/retype them."""

    def __init__(self, parent, title: str, message: str, fields: list[tuple[str, str]] = None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(440)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 20)
        lay.setSpacing(14)

        if message:
            msg_lbl = QLabel(message)
            msg_lbl.setWordWrap(True)
            msg_lbl.setStyleSheet(f"color: {theme.TEXT}; font-size: 13px; line-height: 150%;")
            lay.addWidget(msg_lbl)

        for field_label, field_value in (fields or []):
            row = QFrame()
            row.setProperty("card", "true")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(14, 10, 10, 10)
            text_box = QVBoxLayout()
            text_box.setSpacing(2)
            lbl = QLabel(field_label.upper())
            lbl.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 10px; font-weight: 700; "
                               f"letter-spacing: 0.06em;")
            text_box.addWidget(lbl)
            val_lbl = QLabel(str(field_value))
            val_lbl.setStyleSheet(f"color: {theme.PINK}; font-weight: 800; font-size: 14px; "
                                   f"font-family: Consolas, 'Courier New', monospace;")
            text_box.addWidget(val_lbl)
            rl.addLayout(text_box, 1)
            copy_btn = make_button("\U0001F4CB Copy", "ghost")
            copy_btn.setMinimumHeight(30)
            copy_btn.clicked.connect(lambda _, v=str(field_value), b=None: self._copy(v, copy_btn))
            rl.addWidget(copy_btn)
            lay.addWidget(row)

        lay.addSpacing(4)
        ok_btn = make_button("Done", "primary")
        ok_btn.setMinimumHeight(40)
        ok_btn.clicked.connect(self.accept)
        lay.addWidget(ok_btn)

    def _copy(self, value: str, btn: QPushButton):
        copy_to_clipboard(value)
        original = btn.text()
        btn.setText("\u2713 Copied!")
        QTimer.singleShot(1200, lambda: btn.setText(original) if btn else None)
