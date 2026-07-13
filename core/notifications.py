"""
core.notifications
=====================
Email + SMS dispatch, ported from includes/mailer.php,
includes/sms.php and includes/notify.php.

  * Email is sent with Python's built-in smtplib/email (no external
    dependency needed — replaces PHPMailer).
  * SMS supports the same two providers as the original: Semaphore
    (Philippines) and Twilio, via plain HTTP calls with `requests`.
  * Every attempt (success or failure) is written to notification_log,
    exactly like the PHP version, so Admin -> Notifications shows full
    history either way.
"""
from __future__ import annotations

import re
import smtplib
import ssl
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Optional

import requests

from config.settings import get_settings, LOG_DIR
from core.utils import format_currency, format_date
from database.models import NotificationLog
from sqlalchemy.orm import Session


@dataclass
class SendResult:
    success: bool
    error: Optional[str] = None
    skipped: bool = False


# ─────────────────────────────────────────────────────────────────────────
#  Email
# ─────────────────────────────────────────────────────────────────────────

def email_template(title: str, body_html: str) -> str:
    """Branded HTML wrapper — same visual language as the PHP version
    (dark card, pink/purple gradient header)."""
    company = get_settings().mail.company_name
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
  body {{ margin:0; padding:0; background:#0e0b1a; font-family:'Segoe UI',Arial,sans-serif; }}
  .wrapper {{ max-width:560px; margin:0 auto; padding:32px 16px; }}
  .card {{ background:#16112a; border-radius:16px; border:1px solid rgba(224,64,251,0.2); overflow:hidden; }}
  .header {{ background:linear-gradient(135deg,#E040FB,#a855f7); padding:32px; text-align:center; }}
  .header-icon {{ font-size:2.5rem; margin-bottom:10px; }}
  .header-title {{ color:#fff; font-size:1.4rem; font-weight:800; margin:0; }}
  .header-sub {{ color:rgba(255,255,255,0.7); font-size:0.75rem; margin-top:4px; text-transform:uppercase; letter-spacing:0.1em; }}
  .body {{ padding:32px; }}
  .body p {{ color:#e8e0f7; font-size:0.95rem; line-height:1.7; margin:0 0 14px; }}
  .highlight-box {{ background:rgba(224,64,251,0.12); border:1px solid rgba(224,64,251,0.3); border-radius:10px; padding:16px 20px; margin:18px 0; text-align:center; }}
  .highlight-code {{ font-family:'Courier New',monospace; font-size:2rem; font-weight:800; color:#E040FB; letter-spacing:0.15em; }}
  .highlight-label {{ font-size:0.68rem; color:rgba(255,255,255,0.4); text-transform:uppercase; letter-spacing:0.1em; margin-top:4px; }}
  .badge {{ display:inline-block; background:rgba(74,222,128,0.15); border:1px solid rgba(74,222,128,0.3); border-radius:20px; padding:4px 12px; color:#4ade80; font-size:0.78rem; font-weight:600; margin-bottom:12px; }}
  .footer {{ padding:20px 32px; text-align:center; }}
  .footer p {{ color:rgba(255,255,255,0.25); font-size:0.68rem; margin:0; }}
</style></head>
<body><div class="wrapper"><div class="card">
  <div class="header">
    <div class="header-icon">\U0001F4BC</div>
    <div class="header-title">PayrollPro</div>
    <div class="header-sub">{company} &middot; Management System</div>
  </div>
  <div class="body">{body_html}</div>
  <div class="footer"><hr style="border:none;border-top:1px solid rgba(255,255,255,0.07);margin:20px 0;">
    <p>This is an automated message from PayrollPro &middot; {company}<br>Please do not reply to this email.</p>
  </div>
</div></div></body></html>"""


def send_email(to_email: str, to_name: str, subject: str, html_body: str, plain_body: str = "") -> SendResult:
    cfg = get_settings().mail
    if not cfg.enabled:
        return SendResult(False, "Email is disabled in Settings \u2192 Mail.")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = formataddr((cfg.from_name, cfg.from_email))
    msg["To"] = formataddr((to_name or to_email, to_email))
    msg["Reply-To"] = cfg.from_email

    plain = plain_body or re.sub("<[^<]+?>", "", html_body)
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        if cfg.encryption == "ssl":
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(cfg.host, cfg.port, timeout=15, context=context) as server:
                server.login(cfg.username, cfg.password)
                server.sendmail(cfg.from_email, [to_email], msg.as_string())
        else:
            with smtplib.SMTP(cfg.host, cfg.port, timeout=15) as server:
                server.ehlo()
                if cfg.encryption == "tls":
                    context = ssl.create_default_context()
                    server.starttls(context=context)
                    server.ehlo()
                server.login(cfg.username, cfg.password)
                server.sendmail(cfg.from_email, [to_email], msg.as_string())
        return SendResult(True)
    except Exception as e:  # noqa: BLE001
        return SendResult(False, str(e))


def _company() -> str:
    return get_settings().mail.company_name


def welcome_email_html(full_name: str, username: str) -> str:
    body = f"""
    <div class="badge">&#10003; Account Activated</div>
    <p>Hi <strong style="color:#fff;">{full_name}</strong>,</p>
    <p>Welcome to <strong style="color:#E040FB;">{_company()}</strong>! Your PayrollPro employee
    account has been <strong style="color:#4ade80;">successfully activated</strong>.</p>
    <p>You are now officially part of our team. You can log in to the Employee Portal to view
    your payslips, attendance records, and manage your profile.</p>
    <div class="highlight-box">
      <div class="highlight-label">Your Login Username</div>
      <div class="highlight-code" style="font-size:1.3rem;">{username}</div>
    </div>
    <p style="font-size:0.8rem;color:rgba(255,255,255,0.4);">Keep your login credentials safe and
    do not share them with anyone.</p>"""
    return email_template(f"Account Activated \u2014 {_company()}", body)


def otp_email_html(name: str, otp_code: str, expiry_minutes: int) -> str:
    body = f"""
    <p>Hi <strong style="color:#fff;">{name}</strong>,</p>
    <p>You requested a password reset for your PayrollPro account. Use the OTP below to continue:</p>
    <div class="highlight-box">
      <div class="highlight-label">Your One-Time Password (OTP)</div>
      <div class="highlight-code">{otp_code}</div>
      <div class="highlight-label" style="margin-top:8px;">Valid for {expiry_minutes} minutes only</div>
    </div>
    <p>If you did not request this, please ignore this email and contact your HR administrator.</p>
    <p style="font-size:0.8rem;color:rgba(255,255,255,0.4);">&#9888; Do not share this OTP with anyone.</p>"""
    return email_template(f"Password Reset OTP \u2014 {_company()}", body)


def payroll_generated_email_html(name: str, period_name: str, pay_date, net_pay, status: str) -> str:
    body = f"""
    <div class="badge">\U0001F4C4 Payslip Generated</div>
    <p>Hi <strong style="color:#fff;">{name}</strong>,</p>
    <p>A new payslip has been generated for the pay period <strong>{period_name}</strong>.</p>
    <div class="highlight-box">
      <div class="highlight-label">Net Pay</div>
      <div class="highlight-code" style="font-size:1.6rem;">{format_currency(net_pay)}</div>
      <div class="highlight-label" style="margin-top:8px;">Pay Date: {format_date(pay_date)}</div>
    </div>
    <p>Current status: <strong style="color:#fbbf24;">{status.title()}</strong>. Log in to your
    Employee Portal anytime to view the full breakdown.</p>"""
    return email_template(f"Payslip Generated \u2014 {_company()}", body)


_STATUS_INFO = {
    "approved": ("74,222,128", "&#10003; Approved", "Payroll Approved",
                 "Your payslip for <strong>{period}</strong> has been reviewed and approved."),
    "paid": ("74,222,128", "\U0001F4B0 Paid", "Payment Released",
             "Great news! Your salary for <strong>{period}</strong> has been released to your registered bank account."),
    "cancelled": ("248,113,113", "&#10007; Cancelled", "Payroll Cancelled",
                  "Your payslip for <strong>{period}</strong> has been cancelled."),
}


def payroll_status_email_html(name: str, period_name: str, pay_date, net_pay, new_status: str, remarks: str = "") -> Optional[str]:
    info = _STATUS_INFO.get(new_status)
    if not info:
        return None
    badge_color, badge_text, title, msg_template = info
    msg = msg_template.format(period=period_name)
    remarks_html = f"<p style='font-size:0.8rem;color:rgba(255,255,255,0.5);'>Note from HR: {remarks}</p>" if remarks else ""
    body = f"""
    <div class="badge" style="background:rgba({badge_color},0.15);border-color:rgba({badge_color},0.3);color:rgb({badge_color});">{badge_text}</div>
    <p>Hi <strong style="color:#fff;">{name}</strong>,</p>
    <p>{msg}</p>
    <div class="highlight-box">
      <div class="highlight-label">Net Pay</div>
      <div class="highlight-code" style="font-size:1.6rem;">{format_currency(net_pay)}</div>
      <div class="highlight-label" style="margin-top:8px;">Pay Date: {format_date(pay_date)}</div>
    </div>
    {remarks_html}
    <p style="font-size:0.8rem;color:rgba(255,255,255,0.4);">Log in to your Employee Portal to view the complete payslip breakdown.</p>"""
    return email_template(f"{title} \u2014 {_company()}", body)


# ─────────────────────────────────────────────────────────────────────────
#  SMS
# ─────────────────────────────────────────────────────────────────────────

def _normalize_ph_number(raw: str) -> Optional[str]:
    number = re.sub(r"\D", "", raw or "")
    if len(number) == 11 and number[0] == "0":
        return "63" + number[1:]
    if len(number) == 10 and number[0] == "9":
        return "63" + number
    if len(number) == 12 and number[:2] == "63":
        return number
    return None


def _sms_debug_log(number: str, payload: dict, http_status, response_text: str, error: str = "") -> None:
    try:
        log_file = LOG_DIR / "sms_debug.log"
        safe_payload = dict(payload)
        if "apikey" in safe_payload:
            safe_payload["apikey"] = safe_payload["apikey"][:4] + "\u2022\u2022\u2022\u2022(hidden)"
        from datetime import datetime
        line = (f"[{datetime.now():%Y-%m-%d %H:%M:%S}] to={number} http={http_status} "
                f"error={error or '-'} payload={safe_payload} response={response_text}\n")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:  # noqa: BLE001
        pass


def _send_via_semaphore(number: str, message: str) -> SendResult:
    cfg = get_settings().sms
    url = "https://api.semaphore.co/api/v4/messages"
    data = {"apikey": cfg.api_key, "number": number, "message": message}
    if cfg.sender_name.strip():
        data["sendername"] = cfg.sender_name.strip()
    try:
        resp = requests.post(url, data=data, timeout=15)
        _sms_debug_log(number, data, resp.status_code, resp.text)
        if resp.status_code in (200, 201):
            try:
                decoded = resp.json()
            except ValueError:
                decoded = None
            if isinstance(decoded, list) and decoded and decoded[0].get("message_id"):
                return SendResult(True)
            err = _extract_semaphore_error(decoded, resp.text)
            return SendResult(False, f"Semaphore rejected the message: {err}")
        err = _extract_semaphore_error(_safe_json(resp), resp.text)
        return SendResult(False, f"Semaphore HTTP {resp.status_code}: {err}")
    except requests.RequestException as e:
        _sms_debug_log(number, data, "N/A", "", str(e))
        return SendResult(False, f"Connection error reaching Semaphore: {e}")


def _safe_json(resp):
    try:
        return resp.json()
    except ValueError:
        return None


def _extract_semaphore_error(decoded, raw_response: str) -> str:
    if isinstance(decoded, dict):
        if "message" in decoded:
            m = decoded["message"]
            return "; ".join(m) if isinstance(m, list) else str(m)
        if "error" in decoded:
            return str(decoded["error"])
    if isinstance(decoded, list) and decoded and isinstance(decoded[0], dict) and "message" in decoded[0]:
        return str(decoded[0]["message"])
    return raw_response or "Empty response from Semaphore."


def _send_via_twilio(to_number: str, message: str) -> SendResult:
    cfg = get_settings().sms
    url = f"https://api.twilio.com/2010-04-01/Accounts/{cfg.twilio_sid}/Messages.json"
    try:
        resp = requests.post(
            url,
            auth=(cfg.twilio_sid, cfg.twilio_token),
            data={"To": to_number, "From": cfg.twilio_from, "Body": message},
            timeout=15,
        )
        decoded = _safe_json(resp) or {}
        if 200 <= resp.status_code < 300 and decoded.get("sid"):
            return SendResult(True)
        return SendResult(False, decoded.get("message") or f"Twilio HTTP {resp.status_code}: {resp.text}")
    except requests.RequestException as e:
        return SendResult(False, f"Connection error: {e}")


def send_sms(to_number: str, message: str) -> SendResult:
    cfg = get_settings().sms
    if not cfg.enabled:
        return SendResult(False, "SMS is disabled in Settings \u2192 SMS.")
    if not cfg.api_key or cfg.api_key == "YOUR_SEMAPHORE_API_KEY_HERE":
        return SendResult(False, "No SMS API key configured in Settings \u2192 SMS.")

    number = _normalize_ph_number(to_number)
    if not number:
        return SendResult(False, f'Unrecognized phone number format: "{to_number}". Expected an 11-digit PH mobile number, e.g. 09171234567.')

    if cfg.provider == "semaphore":
        return _send_via_semaphore(number, message)
    if cfg.provider == "twilio":
        return _send_via_twilio("+" + number, message)
    return SendResult(False, 'Unknown SMS provider in Settings. Use "semaphore" or "twilio".')


def sms_welcome(name: str, username: str, company: str) -> str:
    return (f"Welcome to {company}, {name}! Your PayrollPro account ({username}) is now active. "
            f"You can log in to the Employee Portal. Keep your credentials safe. - PayrollPro")


def sms_otp(otp_code: str, expiry_minutes: int) -> str:
    return f"PayrollPro: Your One-Time Password (OTP) is: {otp_code}. Valid for {expiry_minutes} minutes. Do NOT share this with anyone."


# ─────────────────────────────────────────────────────────────────────────
#  Logging + dispatch wrappers (mirrors includes/notify.php)
# ─────────────────────────────────────────────────────────────────────────

def log_notification(session: Session, channel: str, notif_type: str, recipient: str,
                      subject: Optional[str], status: str, error: Optional[str] = None,
                      employee_id: Optional[int] = None, user_id: Optional[int] = None) -> None:
    session.add(NotificationLog(
        employee_id=employee_id, user_id=user_id, channel=channel, notif_type=notif_type,
        recipient=recipient, subject=subject, status=status, error_message=error,
    ))
    session.flush()


def notify_send_email(session: Session, to_email: str, to_name: str, subject: str, html: str,
                       plain: str = "", employee_id: Optional[int] = None,
                       notif_type: str = "general", user_id: Optional[int] = None) -> SendResult:
    r = send_email(to_email, to_name, subject, html, plain)
    log_notification(session, "email", notif_type, to_email, subject,
                      "sent" if r.success else "failed", r.error, employee_id, user_id)
    return r


def notify_send_sms(session: Session, to_number: str, message: str, employee_id: Optional[int] = None,
                     notif_type: str = "general", user_id: Optional[int] = None) -> SendResult:
    if not get_settings().sms.enabled:
        return SendResult(False, None, skipped=True)
    r = send_sms(to_number, message)
    log_notification(session, "sms", notif_type, to_number, message[:100],
                      "sent" if r.success else "failed", r.error, employee_id, user_id)
    return r
