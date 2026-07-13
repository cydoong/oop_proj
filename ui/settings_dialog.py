"""
ui.settings_dialog
=====================
Admin-only Settings dialog: choose SQLite vs XAMPP/MySQL backend
(with connection test), configure SMTP mail, and configure SMS
(Semaphore/Twilio). Mirrors includes/config.php constants, exposed
through a GUI instead of hand-editing a PHP file.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
    QSpinBox, QTabWidget, QVBoxLayout, QWidget, QDialog, QStackedWidget,
)

from config.settings import get_settings, save_settings, DatabaseConfig
from database.db_manager import get_db
from ui.widgets.common import error as show_err, info as show_info, make_button


class DatabaseTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        cfg = get_settings().database

        lay.addWidget(QLabel("Database Backend"))
        self.backend_combo = QComboBox()
        self.backend_combo.addItem("SQLite (local file, zero-config)", "sqlite")
        self.backend_combo.addItem("MySQL / MariaDB (XAMPP)", "mysql")
        self.backend_combo.setCurrentIndex(0 if cfg.backend == "sqlite" else 1)
        self.backend_combo.currentIndexChanged.connect(self._switch_backend)
        lay.addWidget(self.backend_combo)

        self.stack = QStackedWidget()

        sqlite_page = QWidget()
        sp = QVBoxLayout(sqlite_page)
        sp.addWidget(QLabel("Database File Path"))
        path_row = QHBoxLayout()
        self.sqlite_path = QLineEdit(cfg.sqlite_path)
        path_row.addWidget(self.sqlite_path)
        browse_btn = make_button("Browse...", "ghost")
        browse_btn.clicked.connect(self._browse)
        path_row.addWidget(browse_btn)
        sp.addLayout(path_row)
        sp.addStretch()
        self.stack.addWidget(sqlite_page)

        mysql_page = QWidget()
        mp = QVBoxLayout(mysql_page)
        note = QLabel("This connects to your existing XAMPP MySQL/MariaDB server. "
                       "If a payroll_db database already exists there (from the original "
                       "PHP system), your existing employees/payroll/audit data will be used as-is.")
        note.setWordWrap(True)
        mp.addWidget(note)
        self.mysql_host = QLineEdit(cfg.mysql_host)
        self.mysql_port = QSpinBox()
        self.mysql_port.setRange(1, 65535)
        self.mysql_port.setValue(cfg.mysql_port)
        self.mysql_db = QLineEdit(cfg.mysql_db)
        self.mysql_user = QLineEdit(cfg.mysql_user)
        self.mysql_password = QLineEdit(cfg.mysql_password)
        self.mysql_password.setEchoMode(QLineEdit.EchoMode.Password)
        for label, widget in [("Host", self.mysql_host), ("Port", self.mysql_port),
                               ("Database Name", self.mysql_db), ("Username", self.mysql_user),
                               ("Password", self.mysql_password)]:
            mp.addWidget(QLabel(label))
            mp.addWidget(widget)
        mp.addStretch()
        self.stack.addWidget(mysql_page)

        self.stack.setCurrentIndex(0 if cfg.backend == "sqlite" else 1)
        lay.addWidget(self.stack)

        test_row = QHBoxLayout()
        test_btn = make_button("Test Connection", "ghost")
        test_btn.clicked.connect(self._test_connection)
        test_row.addWidget(test_btn)
        test_row.addStretch()
        lay.addLayout(test_row)
        lay.addStretch()

    def _switch_backend(self):
        self.stack.setCurrentIndex(self.backend_combo.currentIndex())

    def _browse(self):
        path, _ = QFileDialog.getSaveFileName(self, "Choose SQLite Database File", self.sqlite_path.text(),
                                               "SQLite Database (*.db)")
        if path:
            self.sqlite_path.setText(path)

    def build_config(self) -> DatabaseConfig:
        cfg = DatabaseConfig()
        cfg.backend = self.backend_combo.currentData()
        cfg.sqlite_path = self.sqlite_path.text().strip()
        cfg.mysql_host = self.mysql_host.text().strip()
        cfg.mysql_port = self.mysql_port.value()
        cfg.mysql_db = self.mysql_db.text().strip()
        cfg.mysql_user = self.mysql_user.text().strip()
        cfg.mysql_password = self.mysql_password.text()
        return cfg

    def _test_connection(self):
        cfg = self.build_config()
        db = get_db()
        ok, msg = db.test_connection(cfg)
        if ok:
            show_info(self, "Connection Successful", msg)
        else:
            show_err(self, "Connection Failed", msg)


class MailTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        cfg = get_settings().mail

        self.enabled = QCheckBox("Enable Email Notifications")
        self.enabled.setChecked(cfg.enabled)
        lay.addWidget(self.enabled)

        self.host = QLineEdit(cfg.host)
        self.port = QSpinBox()
        self.port.setRange(1, 65535)
        self.port.setValue(cfg.port)
        self.encryption = QComboBox()
        self.encryption.addItems(["tls", "ssl"])
        self.encryption.setCurrentText(cfg.encryption)
        self.encryption.currentTextChanged.connect(self._sync_port_to_encryption)
        self.username = QLineEdit(cfg.username)
        self.password = QLineEdit(cfg.password)
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.from_email = QLineEdit(cfg.from_email)
        self.from_name = QLineEdit(cfg.from_name)
        self.company_name = QLineEdit(cfg.company_name)

        for label, widget in [
            ("SMTP Host", self.host), ("SMTP Port", self.port), ("Encryption", self.encryption),
            ("SMTP Username", self.username), ("SMTP Password / App Password", self.password),
            ("From Email", self.from_email), ("From Name", self.from_name), ("Company Name", self.company_name),
        ]:
            lay.addWidget(QLabel(label))
            lay.addWidget(widget)
            if label == "Encryption":
                port_hint = QLabel("TLS normally uses port 587, SSL normally uses port 465 — "
                                    "the port above updates automatically when you switch this.")
                port_hint.setWordWrap(True)
                port_hint.setProperty("role", "muted")
                lay.addWidget(port_hint)

        hint = QLabel("For Gmail: enable 2FA, then create an App Password at "
                       "myaccount.google.com/apppasswords and use it here.")
        hint.setWordWrap(True)
        hint.setProperty("role", "muted")
        lay.addWidget(hint)
        lay.addStretch()

    def _sync_port_to_encryption(self, encryption: str):
        # Only auto-adjust if the port is currently one of the two
        # well-known Gmail values — if someone already customized it for
        # a different provider, leave it alone.
        current = self.port.value()
        if encryption == "ssl" and current in (587, 25, 2525):
            self.port.setValue(465)
        elif encryption == "tls" and current in (465,):
            self.port.setValue(587)

    def apply_to(self, cfg):
        cfg.enabled = self.enabled.isChecked()
        cfg.host = self.host.text().strip()
        cfg.port = self.port.value()
        cfg.encryption = self.encryption.currentText()
        cfg.username = self.username.text().strip()
        cfg.password = self.password.text()
        cfg.from_email = self.from_email.text().strip()
        cfg.from_name = self.from_name.text().strip()
        cfg.company_name = self.company_name.text().strip()


class SmsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        cfg = get_settings().sms

        self.enabled = QCheckBox("Enable SMS Notifications")
        self.enabled.setChecked(cfg.enabled)
        lay.addWidget(self.enabled)

        self.provider = QComboBox()
        self.provider.addItems(["semaphore", "twilio"])
        self.provider.setCurrentText(cfg.provider)
        lay.addWidget(QLabel("Provider"))
        lay.addWidget(self.provider)

        self.api_key = QLineEdit(cfg.api_key)
        self.sender_name = QLineEdit(cfg.sender_name)
        lay.addWidget(QLabel("Semaphore API Key"))
        lay.addWidget(self.api_key)
        lay.addWidget(QLabel("Sender Name"))
        lay.addWidget(self.sender_name)

        self.twilio_sid = QLineEdit(cfg.twilio_sid)
        self.twilio_token = QLineEdit(cfg.twilio_token)
        self.twilio_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.twilio_from = QLineEdit(cfg.twilio_from)
        lay.addWidget(QLabel("Twilio Account SID"))
        lay.addWidget(self.twilio_sid)
        lay.addWidget(QLabel("Twilio Auth Token"))
        lay.addWidget(self.twilio_token)
        lay.addWidget(QLabel("Twilio From Number"))
        lay.addWidget(self.twilio_from)
        lay.addStretch()

    def apply_to(self, cfg):
        cfg.enabled = self.enabled.isChecked()
        cfg.provider = self.provider.currentText()
        cfg.api_key = self.api_key.text().strip()
        cfg.sender_name = self.sender_name.text().strip()
        cfg.twilio_sid = self.twilio_sid.text().strip()
        cfg.twilio_token = self.twilio_token.text()
        cfg.twilio_from = self.twilio_from.text().strip()


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(560, 560)
        lay = QVBoxLayout(self)

        tabs = QTabWidget()
        self.db_tab = DatabaseTab()
        self.mail_tab = MailTab()
        self.sms_tab = SmsTab()
        tabs.addTab(self.db_tab, "\U0001F5C4\uFE0F Database")
        tabs.addTab(self.mail_tab, "\U0001F4E7 Mail")
        tabs.addTab(self.sms_tab, "\U0001F4F1 SMS")
        lay.addWidget(tabs, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = make_button("Cancel", "ghost")
        cancel_btn.clicked.connect(self.reject)
        save_btn = make_button("Save Settings", "primary")
        save_btn.clicked.connect(self.save)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        lay.addLayout(btn_row)

    def save(self):
        settings = get_settings()
        old_backend = settings.database.backend
        old_url_key = (settings.database.sqlite_path, settings.database.mysql_host,
                       settings.database.mysql_db, settings.database.mysql_user)

        settings.database = self.db_tab.build_config()
        self.mail_tab.apply_to(settings.mail)
        self.sms_tab.apply_to(settings.sms)
        save_settings(settings)

        new_url_key = (settings.database.sqlite_path, settings.database.mysql_host,
                       settings.database.mysql_db, settings.database.mysql_user)
        backend_changed = (old_backend != settings.database.backend) or (old_url_key != new_url_key)

        if backend_changed:
            from ui.widgets.common import confirm
            if confirm(self, "Switch Database Now?",
                       "Database settings changed. Reconnect now? (Choosing No just saves the "
                       "settings \u2014 restart PayrollPro later to apply them.)"):
                db = get_db()
                try:
                    db.connect(settings.database)
                    from database.seed_data import seed_if_empty
                    with db.session() as s:
                        seed_if_empty(s)
                    show_info(self, "Connected", "Successfully switched database backend.")
                except Exception as e:  # noqa: BLE001
                    show_err(self, "Connection Failed", f"Could not connect: {e}")
            else:
                show_info(self, "Settings Saved",
                           "Settings saved. Restart PayrollPro for the new database connection to take effect.")
        else:
            show_info(self, "Settings Saved", "Your settings have been saved.")
        self.accept()
