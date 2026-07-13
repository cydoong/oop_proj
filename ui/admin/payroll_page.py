"""
ui.admin.payroll_page
=========================
Payroll processing (with dynamic allowance/deduction rows), status
management, and a payslip viewer/printer — exact port of
admin/payroll.php.
"""
from __future__ import annotations

from decimal import Decimal

from PyQt6.QtPrintSupport import QPrinter
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QHBoxLayout, QLabel,
    QTextEdit, QVBoxLayout, QWidget, QFrame, QFileDialog,
)

import core.pay_period_service as pps
import core.payroll_engine as pe
import core.reference_service as rs
from core.session import current_session
from core.utils import format_currency, format_date
from database.db_manager import get_db
from database.models import Employee, PayPeriod, Payroll, PayrollAllowance, PayrollDeduction
from ui.widgets.common import Badge, SectionHeader, confirm, error as show_err, info as show_info, make_button
from ui.widgets.dialogs import BaseFormDialog
from ui.widgets.table import DataTable, action_bar

STATUS_OPTIONS = ["draft", "approved", "paid", "cancelled"]


class ProcessPayrollDialog(BaseFormDialog):
    def __init__(self, parent, employees, periods, allowance_types, deduction_types):
        super().__init__("Process Payroll", "Calculates pay automatically based on the employee's position.",
                          parent, width=560)
        self.employee_combo = QComboBox()
        for e in employees:
            self.employee_combo.addItem(f"{e.full_name} ({e.employee_code})", e.employee_id)
        self.period_combo = QComboBox()
        for p in periods:
            self.period_combo.addItem(p.period_name, p.period_id)
        self.days_worked = QDoubleSpinBox()
        self.days_worked.setRange(0, 31)
        self.days_worked.setValue(22)
        self.overtime_hours = QDoubleSpinBox()
        self.overtime_hours.setRange(0, 200)
        self.overtime_hours.setValue(0)

        self.add_row("Employee*", self.employee_combo)
        self.add_row("Pay Period*", self.period_combo)
        self.add_row("Days Worked*", self.days_worked)
        self.add_row("Overtime Hours", self.overtime_hours)

        sep = QFrame()
        sep.setProperty("divider", "true")
        sep.setFixedHeight(1)
        self.add_full_row(sep)

        self.allowance_checks = []
        if allowance_types:
            self.add_full_row(QLabel("<b>Allowances</b>"))
            for at in allowance_types:
                row = QWidget()
                rl = QHBoxLayout(row)
                rl.setContentsMargins(0, 0, 0, 0)
                cb = QCheckBox(at.type_name)
                amt = QDoubleSpinBox()
                amt.setRange(0, 1_000_000)
                amt.setPrefix("\u20b1 ")
                amt.setEnabled(False)
                cb.toggled.connect(amt.setEnabled)
                rl.addWidget(cb, 1)
                rl.addWidget(amt)
                self.add_full_row(row)
                self.allowance_checks.append((at.allowance_type_id, cb, amt))

        self.deduction_checks = []
        if deduction_types:
            self.add_full_row(QLabel("<b>Deductions</b>"))
            for dt in deduction_types:
                row = QWidget()
                rl = QHBoxLayout(row)
                rl.setContentsMargins(0, 0, 0, 0)
                cb = QCheckBox(dt.type_name)
                amt = QDoubleSpinBox()
                amt.setRange(0, 1_000_000)
                amt.setPrefix("\u20b1 ")
                amt.setEnabled(False)
                cb.toggled.connect(amt.setEnabled)
                if dt.is_mandatory:
                    cb.setChecked(True)
                rl.addWidget(cb, 1)
                rl.addWidget(amt)
                self.add_full_row(row)
                self.deduction_checks.append((dt.deduction_type_id, cb, amt))

        self.save_btn.setText("Process & Finalize")

    def get_allowances(self):
        return [(tid, Decimal(str(amt.value()))) for tid, cb, amt in self.allowance_checks if cb.isChecked() and amt.value() > 0]

    def get_deductions(self):
        return [(tid, Decimal(str(amt.value()))) for tid, cb, amt in self.deduction_checks if cb.isChecked() and amt.value() > 0]


class StatusUpdateDialog(BaseFormDialog):
    def __init__(self, parent, current_status: str):
        super().__init__("Update Payroll Status", parent=parent, width=420)
        self.status = QComboBox()
        self.status.addItems([s.title() for s in STATUS_OPTIONS])
        self.status.setCurrentText(current_status.title())
        self.add_row("New Status", self.status)
        self.save_btn.setText("Update Status")


class PayslipDialog(QDialog):
    def __init__(self, parent, html: str):
        super().__init__(parent)
        self.setWindowTitle("Payslip")
        self.resize(560, 700)
        lay = QVBoxLayout(self)
        self.view = QTextEdit()
        self.view.setReadOnly(True)
        self.view.setHtml(html)
        lay.addWidget(self.view, 1)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        # NOTE: A "Print" button that opened the native OS print dialog
        # used to live here too, but printing goes through the Windows
        # print spooler / driver stack, which can hard-crash the whole
        # app on machines with missing or misbehaving printer drivers —
        # a Python try/except can't catch that since it happens outside
        # Python entirely. Exporting straight to a PDF file sidesteps
        # the OS printing system altogether, so it's the only option
        # here now. To print, open the saved PDF in any PDF viewer and
        # print from there.
        pdf_btn = make_button("\U0001F4C4 Save Payslip as PDF", "primary")
        pdf_btn.setMinimumHeight(42)
        pdf_btn.clicked.connect(self._save_pdf)
        btn_row.addWidget(pdf_btn)
        lay.addLayout(btn_row)

    def _save_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Payslip as PDF", "payslip.pdf", "PDF Files (*.pdf)")
        if not path:
            return
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(path)
        self.view.print_(printer)
        show_info(self, "Saved", f"Payslip saved to:\n{path}\n\nYou can print it from any PDF viewer.")


def build_payslip_html(payroll, employee, department, position, period, allowances, deductions) -> str:
    allow_rows = "".join(
        f"<tr><td>{a.allowance_type.type_name}</td><td align='right'>{format_currency(a.amount)}</td></tr>"
        for a in allowances
    ) or "<tr><td colspan='2' style='color:#888'>No allowances</td></tr>"
    deduct_rows = "".join(
        f"<tr><td>{d.deduction_type.type_name}</td><td align='right'>{format_currency(d.amount)}</td></tr>"
        for d in deductions
    ) or "<tr><td colspan='2' style='color:#888'>No deductions</td></tr>"

    return f"""
    <div style="font-family: Segoe UI, Arial; color: #222;">
    <h2 style="color:#a020c0; margin-bottom:0;">PayrollPro Payslip</h2>
    <p style="color:#888; margin-top:2px;">{period.period_name} &middot; Pay Date: {format_date(period.pay_date)}</p>
    <hr>
    <table width="100%" cellspacing="4">
      <tr><td><b>Employee</b></td><td align="right">{employee.full_name} ({employee.employee_code})</td></tr>
      <tr><td><b>Department</b></td><td align="right">{department.department_name if department else ''}</td></tr>
      <tr><td><b>Position</b></td><td align="right">{position.position_title if position else ''}</td></tr>
      <tr><td><b>Status</b></td><td align="right">{payroll.payroll_status.title()}</td></tr>
    </table>
    <hr>
    <table width="100%" cellspacing="4">
      <tr><td><b>Days Worked</b></td><td align="right">{payroll.days_worked}</td></tr>
      <tr><td><b>Daily Rate</b></td><td align="right">{format_currency(payroll.daily_rate)}</td></tr>
      <tr><td><b>Basic Pay</b></td><td align="right">{format_currency(payroll.basic_pay)}</td></tr>
      <tr><td><b>Overtime Pay</b></td><td align="right">{format_currency(payroll.overtime_pay)}</td></tr>
      <tr><td><b>Gross Pay</b></td><td align="right"><b>{format_currency(payroll.gross_pay)}</b></td></tr>
    </table>
    <hr>
    <p><b>Allowances</b></p>
    <table width="100%" cellspacing="4">{allow_rows}
      <tr><td><b>Total Allowances</b></td><td align="right"><b>{format_currency(payroll.total_allowances)}</b></td></tr>
    </table>
    <p><b>Deductions</b></p>
    <table width="100%" cellspacing="4">{deduct_rows}
      <tr><td><b>Total Deductions</b></td><td align="right"><b>{format_currency(payroll.total_deductions)}</b></td></tr>
    </table>
    <hr>
    <table width="100%" cellspacing="4">
      <tr><td><b>Tax Withheld</b></td><td align="right">{format_currency(payroll.tax_withheld)}</td></tr>
      <tr><td style="font-size:16px;"><b>NET PAY</b></td>
          <td align="right" style="font-size:18px; color:#0a0;"><b>{format_currency(payroll.net_pay)}</b></td></tr>
    </table>
    </div>
    """


class PayrollPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.period_filter = 0
        self.status_filter = ""

        lay = QVBoxLayout(self)
        lay.setSpacing(16)
        header = SectionHeader("Payroll", "Process and manage employee payroll", "+ Process Payroll")
        header.action_btn.clicked.connect(self.open_process_dialog)
        lay.addWidget(header)

        filters = QHBoxLayout()
        self.period_combo = QComboBox()
        self.period_combo.addItem("All Periods", 0)
        self.period_combo.currentIndexChanged.connect(self._on_filter_change)
        filters.addWidget(self.period_combo)
        self.status_combo = QComboBox()
        self.status_combo.addItem("All Statuses", "")
        for st in STATUS_OPTIONS:
            self.status_combo.addItem(st.title(), st)
        self.status_combo.currentIndexChanged.connect(self._on_filter_change)
        filters.addWidget(self.status_combo)
        filters.addStretch()
        lay.addLayout(filters)

        self.table = DataTable(["Employee", "Period", "Gross Pay", "Net Pay", "Status", "Actions"])
        lay.addWidget(self.table, 1)
        self.refresh()

    def refresh(self):
        db = get_db()
        with db.session() as s:
            from sqlalchemy import select
            q = (
                select(Payroll, Employee, PayPeriod)
                .join(Employee, Payroll.employee_id == Employee.employee_id)
                .join(PayPeriod, Payroll.period_id == PayPeriod.period_id)
                .order_by(Payroll.created_at.desc())
            )
            if self.period_filter:
                q = q.where(Payroll.period_id == self.period_filter)
            if self.status_filter:
                q = q.where(Payroll.payroll_status == self.status_filter)
            rows = s.execute(q).all()
            periods = pps.list_pay_periods(s)

        current_period = self.period_combo.currentData()
        self.period_combo.blockSignals(True)
        self.period_combo.clear()
        self.period_combo.addItem("All Periods", 0)
        for p in periods:
            self.period_combo.addItem(p.period_name, p.period_id)
        if current_period:
            idx = self.period_combo.findData(current_period)
            if idx >= 0:
                self.period_combo.setCurrentIndex(idx)
        self.period_combo.blockSignals(False)

        self.table.clear_rows()
        for payroll, emp, period in rows:
            r = self.table.add_row([
                f"{emp.full_name} ({emp.employee_code})", period.period_name,
                format_currency(payroll.gross_pay), format_currency(payroll.net_pay), "", None,
            ])
            self.table.set_widget(r, 4, Badge(payroll.payroll_status))
            actions = action_bar([
                ("\U0001F4C4", "ghost", lambda _, pid=payroll.payroll_id: self.view_payslip(pid), "View payslip"),
                ("\U0001F504", "ghost", lambda _, pid=payroll.payroll_id, st=payroll.payroll_status: self.update_status(pid, st), "Update status"),
                ("\U0001F5D1\uFE0F", "danger", lambda _, pid=payroll.payroll_id, st=payroll.payroll_status: self.delete(pid, st), "Delete payroll record"),
            ])
            self.table.set_widget(r, 5, actions)

    def _on_filter_change(self):
        self.period_filter = self.period_combo.currentData() or 0
        self.status_filter = self.status_combo.currentData() or ""
        self.refresh()

    # ------------------------------------------------------------------
    def open_process_dialog(self):
        db = get_db()
        with db.session() as s:
            from sqlalchemy import select
            emp_rows = s.execute(select(Employee).where(Employee.employment_status == "active")
                                  .order_by(Employee.first_name)).scalars().all()
            employees = [type("E", (), {"employee_id": e.employee_id, "full_name": e.full_name,
                                         "employee_code": e.employee_code}) for e in emp_rows]
            periods = pps.list_pay_periods(s)
            allowance_types = rs.list_allowance_types(s, active_only=True)
            deduction_types = rs.list_deduction_types(s, active_only=True)

        if not employees:
            show_err(self, "No Employees", "Please add active employees first.")
            return
        if not periods:
            show_err(self, "No Pay Periods", "Please add a pay period first.")
            return

        dlg = ProcessPayrollDialog(self, employees, periods, allowance_types, deduction_types)
        dlg.save_btn.clicked.connect(lambda: self._submit_process(dlg))
        dlg.exec()

    def _submit_process(self, dlg: ProcessPayrollDialog):
        dlg.clear_error()
        db = get_db()
        with db.session() as s:
            result = pe.process_and_finalize_payroll(
                s, dlg.employee_combo.currentData(), dlg.period_combo.currentData(),
                Decimal(str(dlg.days_worked.value())), Decimal(str(dlg.overtime_hours.value())),
                current_session.user_id, dlg.get_allowances(), dlg.get_deductions(),
            )
        if not result.success:
            dlg.show_error(result.error)
            return
        dlg.accept()
        msg = f"Payroll processed successfully. Net Pay: {format_currency(result.extra.get('net_pay'))}"
        if not result.extra.get("notif_success"):
            msg += f"\n\nNote: employee notification email was not sent ({result.extra.get('notif_error')})."
        show_info(self, "Payroll Processed", msg)
        self.refresh()

    def view_payslip(self, payroll_id: int):
        db = get_db()
        with db.session() as s:
            payroll = s.get(Payroll, payroll_id)
            employee = s.get(Employee, payroll.employee_id)
            from database.models import Department, Position
            department = s.get(Department, employee.department_id)
            position = s.get(Position, employee.position_id)
            period = s.get(PayPeriod, payroll.period_id)
            from sqlalchemy import select
            allowances = s.execute(select(PayrollAllowance).where(PayrollAllowance.payroll_id == payroll_id)).scalars().all()
            for a in allowances:
                _ = a.allowance_type.type_name
            deductions = s.execute(select(PayrollDeduction).where(PayrollDeduction.payroll_id == payroll_id)).scalars().all()
            for dd in deductions:
                _ = dd.deduction_type.type_name
            html = build_payslip_html(payroll, employee, department, position, period, allowances, deductions)
        dlg = PayslipDialog(self, html)
        dlg.exec()

    def update_status(self, payroll_id: int, current_status: str):
        dlg = StatusUpdateDialog(self, current_status)

        def do_update():
            new_status = dlg.status.currentText().lower()
            db = get_db()
            with db.session() as s:
                result = pe.update_payroll_status(s, payroll_id, new_status, current_session.user_id)
            if not result.success:
                dlg.show_error(result.error)
                return
            dlg.accept()
            self.refresh()
        dlg.save_btn.clicked.connect(do_update)
        dlg.exec()

    def delete(self, payroll_id: int, status: str):
        if status == "paid":
            show_err(self, "Cannot Delete", "Paid payroll records cannot be deleted.")
            return
        if not confirm(self, "Delete Payroll Record?", "This cannot be undone.", danger=True):
            return
        db = get_db()
        with db.session() as s:
            result = pe.delete_payroll(s, payroll_id)
        if result.success:
            self.refresh()
        else:
            show_err(self, "Error", result.error)
