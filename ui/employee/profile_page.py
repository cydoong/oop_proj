"""
ui.employee.profile_page
============================
Employee self-service profile: view/update name, contact & banking
info, change username (passcode-gated), change password
(passcode-gated), and security info card — exact port of
user/my_profile.php.
"""
from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QTextEdit, QVBoxLayout, QWidget

import core.profile_service as ps
from core.session import current_session
from core.utils import format_passcode
from database.db_manager import get_db
from database.models import Employee, User
from ui import theme
from ui.widgets.common import SectionHeader, error as show_err, info as show_info, make_button


class Card(QFrame):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setProperty("card", "true")
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(24, 20, 24, 20)
        self.lay.setSpacing(10)
        t = QLabel(title)
        t.setStyleSheet("font-size: 15px; font-weight: 700; color: #fff;")
        self.lay.addWidget(t)


def _labeled(parent_lay, label, widget):
    parent_lay.addWidget(QLabel(label))
    parent_lay.addWidget(widget)


class ProfilePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.lay = QVBoxLayout(self)
        self.lay.setSpacing(20)
        self.refresh()

    def refresh(self):
        while self.lay.count():
            item = self.lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        db = get_db()
        with db.session() as s:
            emp = s.get(Employee, current_session.employee_id)
            user = s.get(User, current_session.user_id)

        if not emp or not user:
            self.lay.addWidget(QLabel("Employee record not found."))
            return

        self.lay.addWidget(SectionHeader("My Profile", "Manage your personal information and account security"))

        sec_card = Card("\U0001F510 Account Security")
        info_row = QHBoxLayout()
        info_row.addWidget(QLabel(f"<b>Username:</b> {user.username}"))
        info_row.addWidget(QLabel(f"<b>Status:</b> {'Activated' if user.account_activated else 'Pending'}"))
        info_row.addWidget(QLabel(f"<b>Passcode:</b> {format_passcode(user.passcode)}"))
        info_row.addStretch()
        sec_card.lay.addLayout(info_row)
        note = QLabel("Keep your passcode private \u2014 it's required to change your username or password.")
        note.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 11px;")
        sec_card.lay.addWidget(note)
        self.lay.addWidget(sec_card)

        name_card = Card("\U0001F464 Personal Name")
        self.first_name = QLineEdit(emp.first_name)
        self.last_name = QLineEdit(emp.last_name)
        self.middle_name = QLineEdit(emp.middle_name or "")
        row = QHBoxLayout()
        col1 = QVBoxLayout()
        _labeled(col1, "First Name", self.first_name)
        row.addLayout(col1)
        col2 = QVBoxLayout()
        _labeled(col2, "Last Name", self.last_name)
        row.addLayout(col2)
        col3 = QVBoxLayout()
        _labeled(col3, "Middle Name", self.middle_name)
        row.addLayout(col3)
        name_card.lay.addLayout(row)
        save_name_btn = make_button("Save Name", "primary")
        save_name_btn.clicked.connect(self.save_name)
        name_card.lay.addWidget(save_name_btn)
        self.lay.addWidget(name_card)

        contact_card = Card("\U0001F4DE Contact & Banking")
        self.phone = QLineEdit(emp.phone or "")
        self.address = QTextEdit(emp.address or "")
        self.address.setFixedHeight(60)
        self.bank_name = QLineEdit(emp.bank_name or "")
        self.bank_account = QLineEdit(emp.bank_account or "")
        _labeled(contact_card.lay, "Phone", self.phone)
        _labeled(contact_card.lay, "Address", self.address)
        row2 = QHBoxLayout()
        col4 = QVBoxLayout()
        _labeled(col4, "Bank Name", self.bank_name)
        row2.addLayout(col4)
        col5 = QVBoxLayout()
        _labeled(col5, "Bank Account #", self.bank_account)
        row2.addLayout(col5)
        contact_card.lay.addLayout(row2)
        save_contact_btn = make_button("Save Profile", "primary")
        save_contact_btn.clicked.connect(self.save_profile)
        contact_card.lay.addWidget(save_contact_btn)
        self.lay.addWidget(contact_card)

        gov_card = Card("\U0001F4C4 Government Numbers (managed by HR)")
        gov_row = QHBoxLayout()
        gov_row.addWidget(QLabel(f"<b>SSS:</b> {emp.sss_number or '\u2014'}"))
        gov_row.addWidget(QLabel(f"<b>PhilHealth:</b> {emp.philhealth_number or '\u2014'}"))
        gov_row.addWidget(QLabel(f"<b>Pag-IBIG:</b> {emp.pagibig_number or '\u2014'}"))
        gov_row.addWidget(QLabel(f"<b>TIN:</b> {emp.tin_number or '\u2014'}"))
        gov_card.lay.addLayout(gov_row)
        self.lay.addWidget(gov_card)

        uname_card = Card("\u270F\uFE0F Change Username")
        self.uname_passcode = QLineEdit()
        self.uname_passcode.setPlaceholderText("ABCD-1234")
        self.new_username = QLineEdit()
        self.new_username.setPlaceholderText("new.username")
        row3 = QHBoxLayout()
        col6 = QVBoxLayout()
        _labeled(col6, "Your Passcode", self.uname_passcode)
        row3.addLayout(col6)
        col7 = QVBoxLayout()
        _labeled(col7, "New Username", self.new_username)
        row3.addLayout(col7)
        uname_card.lay.addLayout(row3)
        change_uname_btn = make_button("Change Username", "primary")
        change_uname_btn.clicked.connect(self.change_username)
        uname_card.lay.addWidget(change_uname_btn)
        self.lay.addWidget(uname_card)

        pw_card = Card("\U0001F511 Change Password")
        self.pw_passcode = QLineEdit()
        self.pw_passcode.setPlaceholderText("ABCD-1234")
        self.current_pw = QLineEdit()
        self.current_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_pw = QLineEdit()
        self.new_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_pw = QLineEdit()
        self.confirm_pw.setEchoMode(QLineEdit.EchoMode.Password)
        _labeled(pw_card.lay, "Your Passcode", self.pw_passcode)
        _labeled(pw_card.lay, "Current Password", self.current_pw)
        row4 = QHBoxLayout()
        col8 = QVBoxLayout()
        _labeled(col8, "New Password", self.new_pw)
        row4.addLayout(col8)
        col9 = QVBoxLayout()
        _labeled(col9, "Confirm New Password", self.confirm_pw)
        row4.addLayout(col9)
        pw_card.lay.addLayout(row4)
        change_pw_btn = make_button("Change Password", "primary")
        change_pw_btn.clicked.connect(self.change_password)
        pw_card.lay.addWidget(change_pw_btn)
        self.lay.addWidget(pw_card)

        self.lay.addStretch()

    # ------------------------------------------------------------------
    def save_name(self):
        db = get_db()
        with db.session() as s:
            result = ps.update_name(s, current_session.employee_id, self.first_name.text(),
                                     self.last_name.text(), self.middle_name.text(), current_session.user_id)
        if result.success:
            current_session.full_name = f"{self.first_name.text()} {self.last_name.text()}"
            show_info(self, "Saved", "Name updated successfully.")
            self.refresh()
        else:
            show_err(self, "Error", result.error)

    def save_profile(self):
        db = get_db()
        with db.session() as s:
            result = ps.update_profile(s, current_session.employee_id, self.phone.text(),
                                        self.address.toPlainText(), self.bank_name.text(),
                                        self.bank_account.text(), current_session.user_id)
        if result.success:
            show_info(self, "Saved", "Profile updated successfully.")
            self.refresh()
        else:
            show_err(self, "Error", result.error)

    def change_username(self):
        db = get_db()
        with db.session() as s:
            result = ps.change_username(s, current_session.user_id, self.uname_passcode.text(),
                                         self.new_username.text())
        if result.success:
            current_session.username = result.data["new_username"]
            show_info(self, "Username Changed", f"Your username is now: {result.data['new_username']}")
            self.refresh()
        else:
            show_err(self, "Error", result.error)

    def change_password(self):
        db = get_db()
        with db.session() as s:
            result = ps.change_password(s, current_session.user_id, self.pw_passcode.text(),
                                         self.current_pw.text(), self.new_pw.text(), self.confirm_pw.text())
        if result.success:
            show_info(self, "Password Changed", "Your password has been changed successfully.")
            self.refresh()
        else:
            show_err(self, "Error", result.error)
