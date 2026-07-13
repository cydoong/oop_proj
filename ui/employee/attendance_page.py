"""
ui.employee.attendance_page
===============================
Employee's own attendance record view, exact port of
user/my_attendance.php.
"""
from __future__ import annotations

from sqlalchemy import select

from PyQt6.QtWidgets import QVBoxLayout, QWidget

from core.session import current_session
from database.db_manager import get_db
from database.models import Attendance, PayPeriod
from ui.widgets.common import SectionHeader
from ui.widgets.table import DataTable


class AttendancePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setSpacing(16)
        lay.addWidget(SectionHeader("My Attendance", "Your attendance record per pay period"))
        self.table = DataTable(["Period", "Days Worked", "Days Absent", "Days Late", "Overtime Hours", "Notes"])
        lay.addWidget(self.table, 1)
        self.refresh()

    def refresh(self):
        db = get_db()
        with db.session() as s:
            rows = s.execute(
                select(Attendance, PayPeriod)
                .join(PayPeriod, Attendance.period_id == PayPeriod.period_id)
                .where(Attendance.employee_id == current_session.employee_id)
                .order_by(PayPeriod.start_date.desc())
            ).all()

        self.table.clear_rows()
        if not rows:
            self.table.add_row(["No attendance records yet.", "", "", "", "", ""])
            return
        for att, period in rows:
            self.table.add_row([
                period.period_name, str(att.days_worked), str(att.days_absent), str(att.days_late),
                str(att.overtime_hours), att.notes or "\u2014",
            ])
