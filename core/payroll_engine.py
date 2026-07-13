"""
core.payroll_engine
=======================
Exact re-implementation of the original MySQL stored procedures and
the admin/payroll.php action handlers, so payroll math is identical
byte-for-byte regardless of which database backend is active:

    sp_process_payroll   -> process_payroll()
    sp_finalize_payroll  -> finalize_payroll()
    trg_payroll_status_change -> update_payroll_status() calls
                                  core.audit.log_payroll_status_change()

The "Process Payroll" button in the original admin UI actually calls
sp_process_payroll, inserts allowance/deduction rows, THEN
immediately calls sp_finalize_payroll and fires an employee
notification — all in one request. That combined flow is
process_and_finalize_payroll() below.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Sequence, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.audit import log_action, log_payroll_status_change
from database.models import (
    Employee, PayPeriod, Payroll, PayrollAllowance, PayrollDeduction, Position, User,
)

TWO_PLACES = Decimal("0.01")


def _round2(value: Decimal) -> Decimal:
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


@dataclass
class PayrollResult:
    success: bool
    error: Optional[str] = None
    payroll_id: Optional[int] = None
    extra: Optional[dict] = None


def _get_employee_or_none(session: Session, employee_id: int) -> Optional[Employee]:
    return session.get(Employee, employee_id)


# ─────────────────────────────────────────────────────────────────────────
#  sp_process_payroll
# ─────────────────────────────────────────────────────────────────────────

def process_payroll(session: Session, employee_id: int, period_id: int,
                     days_worked: Decimal, overtime_hours: Decimal,
                     processed_by: Optional[int]) -> PayrollResult:
    emp = session.execute(
        select(Employee).where(Employee.employee_id == employee_id)
    ).scalar_one_or_none()
    if not emp:
        return PayrollResult(False, "Employee not found.")

    position = session.get(Position, emp.position_id)
    base_salary = Decimal(position.base_salary) if position else Decimal(0)

    days_worked = Decimal(str(days_worked))
    overtime_hours = Decimal(str(overtime_hours))

    daily_rate = _round2(base_salary / Decimal(22))
    basic_pay = _round2(daily_rate * days_worked)
    overtime_pay = _round2((daily_rate / Decimal(8)) * Decimal("1.25") * overtime_hours)
    gross_pay = _round2(basic_pay + overtime_pay)

    existing = session.execute(
        select(Payroll).where(Payroll.employee_id == employee_id, Payroll.period_id == period_id)
    ).scalar_one_or_none()

    now = datetime.now()
    if existing:
        existing.basic_pay = basic_pay
        existing.daily_rate = daily_rate
        existing.days_worked = days_worked
        existing.overtime_pay = overtime_pay
        existing.gross_pay = gross_pay
        existing.processed_by = processed_by
        existing.processed_at = now
        existing.payroll_status = "draft"
        session.flush()
        payroll_id = existing.payroll_id
    else:
        row = Payroll(
            employee_id=employee_id, period_id=period_id, basic_pay=basic_pay,
            daily_rate=daily_rate, days_worked=days_worked, overtime_pay=overtime_pay,
            gross_pay=gross_pay, processed_by=processed_by, processed_at=now,
            payroll_status="draft",
        )
        session.add(row)
        session.flush()
        payroll_id = row.payroll_id

    log_action(session, processed_by, "PROCESS_PAYROLL", "payroll", payroll_id, None,
               f"employee:{employee_id} period:{period_id}")
    return PayrollResult(True, payroll_id=payroll_id)


# ─────────────────────────────────────────────────────────────────────────
#  sp_finalize_payroll
# ─────────────────────────────────────────────────────────────────────────

def finalize_payroll(session: Session, payroll_id: int, admin_id: Optional[int]) -> PayrollResult:
    payroll = session.get(Payroll, payroll_id)
    if not payroll:
        return PayrollResult(False, "Payroll record not found.")

    total_allow = session.execute(
        select(PayrollAllowance).where(PayrollAllowance.payroll_id == payroll_id)
    ).scalars().all()
    total_deduct = session.execute(
        select(PayrollDeduction).where(PayrollDeduction.payroll_id == payroll_id)
    ).scalars().all()

    v_gross = Decimal(payroll.gross_pay)
    v_total_allow = sum((Decimal(a.amount) for a in total_allow), Decimal(0))
    v_total_deduct = sum((Decimal(d.amount) for d in total_deduct), Decimal(0))

    base = v_gross + v_total_allow
    v_tax = _round2(base * Decimal("0.15")) if base > Decimal(20000) else _round2(base * Decimal("0.10"))
    v_net = _round2(base - v_total_deduct)

    payroll.total_allowances = _round2(v_total_allow)
    payroll.total_deductions = _round2(v_total_deduct)
    payroll.tax_withheld = v_tax
    payroll.net_pay = v_net
    payroll.payroll_status = "approved"
    payroll.updated_at = datetime.now()
    session.flush()

    log_action(session, admin_id, "FINALIZE_PAYROLL", "payroll", payroll_id, None, f"net_pay:{v_net}")
    return PayrollResult(True, payroll_id=payroll_id, extra={"net_pay": v_net})


# ─────────────────────────────────────────────────────────────────────────
#  Combined "Process Payroll" admin action (process + allowances/
#  deductions + finalize + notify), matching admin/payroll.php exactly.
# ─────────────────────────────────────────────────────────────────────────

def process_and_finalize_payroll(
    session: Session,
    employee_id: int,
    period_id: int,
    days_worked: Decimal,
    overtime_hours: Decimal,
    processed_by: Optional[int],
    allowances: Sequence[Tuple[int, Decimal]] = (),
    deductions: Sequence[Tuple[int, Decimal]] = (),
) -> PayrollResult:
    result = process_payroll(session, employee_id, period_id, days_worked, overtime_hours, processed_by)
    if not result.success:
        return result
    payroll_id = result.payroll_id

    # Replace allowance/deduction rows (mirrors DELETE-then-INSERT in payroll.php)
    session.query(PayrollAllowance).filter(PayrollAllowance.payroll_id == payroll_id).delete()
    session.query(PayrollDeduction).filter(PayrollDeduction.payroll_id == payroll_id).delete()
    for at_id, amt in allowances:
        amt = Decimal(str(amt))
        if at_id and amt > 0:
            session.add(PayrollAllowance(payroll_id=payroll_id, allowance_type_id=at_id, amount=amt))
    for dt_id, amt in deductions:
        amt = Decimal(str(amt))
        if dt_id and amt > 0:
            session.add(PayrollDeduction(payroll_id=payroll_id, deduction_type_id=dt_id, amount=amt))
    session.flush()

    fin = finalize_payroll(session, payroll_id, processed_by)
    if not fin.success:
        return fin

    # Notify employee (best-effort — failures never block the payroll operation)
    from core.payroll_notify import notify_payroll_generated
    notif = notify_payroll_generated(session, payroll_id)
    return PayrollResult(True, payroll_id=payroll_id, extra={
        "net_pay": fin.extra.get("net_pay") if fin.extra else None,
        "notif_success": notif.success,
        "notif_error": notif.error,
    })


# ─────────────────────────────────────────────────────────────────────────
#  Status update (admin/payroll.php action=update_status)
# ─────────────────────────────────────────────────────────────────────────

ALLOWED_STATUSES = ("draft", "approved", "paid", "cancelled")


def update_payroll_status(session: Session, payroll_id: int, new_status: str,
                           admin_id: Optional[int]) -> PayrollResult:
    if new_status not in ALLOWED_STATUSES:
        return PayrollResult(False, "Invalid status.")
    payroll = session.get(Payroll, payroll_id)
    if not payroll:
        return PayrollResult(False, "Payroll record not found.")

    old_status = payroll.payroll_status
    old_net = Decimal(payroll.net_pay)

    payroll.payroll_status = new_status
    payroll.updated_at = datetime.now()
    session.flush()

    log_action(session, admin_id, "UPDATE_PAYROLL_STATUS", "payroll", payroll_id, None, new_status)
    log_payroll_status_change(session, payroll_id, old_status, old_net, new_status, Decimal(payroll.net_pay))

    from core.payroll_notify import notify_payroll_status
    notif = notify_payroll_status(session, payroll_id, new_status)
    return PayrollResult(True, payroll_id=payroll_id, extra={
        "notif_success": notif.success, "notif_error": notif.error, "notif_skipped": notif.skipped,
    })


def delete_payroll(session: Session, payroll_id: int) -> PayrollResult:
    payroll = session.get(Payroll, payroll_id)
    if not payroll:
        return PayrollResult(False, "Payroll record not found.")
    if payroll.payroll_status == "paid":
        return PayrollResult(False, "Cannot delete a paid payroll record.")
    session.delete(payroll)
    session.flush()
    return PayrollResult(True)
