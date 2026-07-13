"""
PayrollPro (Python Edition) — Seed Data
==========================================
Populates a *fresh* database (new SQLite file, or an empty MySQL
schema) with the same baseline reference data the original PHP
system shipped with: departments, positions, allowance/deduction
types, and one default administrator account.

This never overwrites existing data — if departments/users already
exist (e.g. you pointed the app at your existing XAMPP payroll_db),
seeding is skipped automatically.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from core.security import hash_password
from database.models import (
    AllowanceType, DeductionType, Department, Position, User,
)


DEPARTMENTS = [
    ("Human Resources", "Manages employee relations, recruitment, and HR policies"),
    ("Information Technology", "Handles all IT infrastructure, development, and support"),
    ("Finance & Accounting", "Manages financial records, budgeting, and payroll"),
    ("Operations", "Oversees daily operational activities and logistics"),
    ("Marketing", "Handles brand, promotions, and customer acquisition"),
]

# (department index into DEPARTMENTS, title, base_salary, employment_type)
POSITIONS = [
    (0, "HR Manager", 45000.00, "full_time"),
    (0, "HR Specialist", 28000.00, "full_time"),
    (0, "HR Assistant", 20000.00, "full_time"),
    (1, "IT Manager", 55000.00, "full_time"),
    (1, "Senior Developer", 45000.00, "full_time"),
    (1, "Junior Developer", 28000.00, "full_time"),
    (1, "IT Support", 22000.00, "full_time"),
    (2, "Finance Manager", 50000.00, "full_time"),
    (2, "Accountant", 32000.00, "full_time"),
    (2, "Bookkeeper", 22000.00, "full_time"),
    (3, "Operations Manager", 48000.00, "full_time"),
    (3, "Operations Supervisor", 35000.00, "full_time"),
    (3, "Operations Staff", 20000.00, "full_time"),
    (4, "Marketing Manager", 46000.00, "full_time"),
    (4, "Marketing Specialist", 30000.00, "full_time"),
    (4, "Marketing Assistant", 20000.00, "probationary"),
]

ALLOWANCE_TYPES = [
    ("Rice Allowance", "Monthly rice subsidy", False),
    ("Transportation", "Daily transportation reimbursement", False),
    ("Meal Allowance", "Daily meal subsidy", False),
    ("Communication", "Mobile and internet allowance", False),
    ("Housing Allowance", "Monthly housing assistance", True),
    ("Medical Allowance", "Annual medical reimbursement", False),
    ("Performance Bonus", "Quarterly performance-based bonus", True),
    ("13th Month Pay", "Annual 13th month salary", False),
]

DEDUCTION_TYPES = [
    ("SSS Contribution", "Social Security System monthly contribution", True),
    ("PhilHealth", "Philippine Health Insurance Corporation", True),
    ("Pag-IBIG", "Home Development Mutual Fund", True),
    ("Withholding Tax", "Government income tax withholding", True),
    ("Late/Absent Deduction", "Deduction for tardiness and absences", False),
    ("Loan Repayment", "Employee loan amortization", False),
    ("Cash Advance", "Salary advance deduction", False),
    ("Uniform Deduction", "Company uniform amortization", False),
]


def seed_if_empty(session: Session, admin_password: str = "admin123") -> bool:
    """Seed reference data + default admin if the database looks empty.
    Returns True if seeding actually happened."""
    if session.query(Department).count() > 0 or session.query(User).count() > 0:
        return False  # Already has data (existing XAMPP DB, or already seeded)

    dept_rows = []
    for name, desc in DEPARTMENTS:
        d = Department(department_name=name, description=desc, is_active=True)
        session.add(d)
        dept_rows.append(d)
    session.flush()  # assign IDs

    for dept_idx, title, salary, emp_type in POSITIONS:
        session.add(Position(
            department_id=dept_rows[dept_idx].department_id,
            position_title=title,
            base_salary=salary,
            employment_type=emp_type,
            is_active=True,
        ))

    for name, desc, taxable in ALLOWANCE_TYPES:
        session.add(AllowanceType(type_name=name, description=desc, is_taxable=taxable, is_active=True))

    for name, desc, mandatory in DEDUCTION_TYPES:
        session.add(DeductionType(type_name=name, description=desc, is_mandatory=mandatory, is_active=True))

    admin = User(
        username="admin",
        password=hash_password(admin_password),
        role="admin",
        is_active=True,
        account_activated=True,
    )
    session.add(admin)

    session.commit()
    return True
