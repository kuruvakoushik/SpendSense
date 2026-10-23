"""Server-side input validation and financial helpers."""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

EMAIL_RE = re.compile(r"^[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}$", re.IGNORECASE)
COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

PAYMENT_METHODS = ("UPI", "Cash", "Card", "Net Banking", "Wallet", "Other")
TRANSACTION_TYPES = ("income", "expense")
MAX_NAME_LEN = 80
MAX_DESCRIPTION_LEN = 200
MAX_PASSWORD_LEN = 128
MIN_PASSWORD_LEN = 8
MAX_AMOUNT_RUPEES = Decimal("10000000")  # 1 crore
ICONS = (
    "wallet",
    "food",
    "transport",
    "education",
    "shopping",
    "health",
    "entertainment",
    "bills",
    "housing",
    "travel",
    "salary",
    "freelance",
    "other",
)


class ValidationError(Exception):
    def __init__(self, message: str, field: str | None = None):
        super().__init__(message)
        self.message = message
        self.field = field


def require_str(payload: dict, field: str, *, max_len: int, required: bool = True) -> str:
    value = payload.get(field, "")
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be a string.", field)
    value = value.strip()
    if required and not value:
        raise ValidationError(f"{field.replace('_', ' ').title()} is required.", field)
    if len(value) > max_len:
        raise ValidationError(f"{field.replace('_', ' ').title()} is too long.", field)
    return value


def normalize_email(email: str) -> str:
    email = email.strip().lower()
    if not EMAIL_RE.match(email) or len(email) > 254:
        raise ValidationError("Enter a valid email address.", "email")
    return email


def validate_full_name(name: str) -> str:
    name = name.strip()
    if len(name) < 2:
        raise ValidationError("Full name must be at least 2 characters.", "full_name")
    if len(name) > MAX_NAME_LEN:
        raise ValidationError("Full name is too long.", "full_name")
    return name


def validate_password(password: str, *, field: str = "password") -> str:
    if not isinstance(password, str):
        raise ValidationError("Password is required.", field)
    if len(password) < MIN_PASSWORD_LEN:
        raise ValidationError("Password must be at least 8 characters.", field)
    if len(password) > MAX_PASSWORD_LEN:
        raise ValidationError("Password is too long.", field)
    if password.strip() != password:
        raise ValidationError("Password cannot start or end with spaces.", field)
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise ValidationError("Password must include at least one letter and one number.", field)
    return password


def parse_amount_to_paise(value) -> int:
    if value is None or value == "":
        raise ValidationError("Amount is required.", "amount")
    try:
        amount = Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, AttributeError) as exc:
        raise ValidationError("Enter a valid amount.", "amount") from exc
    if amount <= 0:
        raise ValidationError("Amount must be greater than zero.", "amount")
    if amount > MAX_AMOUNT_RUPEES:
        raise ValidationError("Amount exceeds the allowed maximum.", "amount")
    paise = (amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(paise)


def paise_to_rupees(paise: int) -> float:
    return float(Decimal(paise) / Decimal(100))


def format_inr_from_paise(paise: int) -> str:
    negative = paise < 0
    paise = abs(int(paise))
    rupees, remainder = divmod(paise, 100)
    digits = str(rupees)
    if len(digits) <= 3:
        grouped = digits
    else:
        last3 = digits[-3:]
        rest = digits[:-3]
        parts: list[str] = []
        while rest:
            parts.append(rest[-2:])
            rest = rest[:-2]
        grouped = ",".join(list(reversed(parts)) + [last3])
    sign = "-" if negative else ""
    return f"{sign}₹{grouped}.{remainder:02d}"


def parse_iso_date(value: str, field: str = "transaction_date") -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("Date is required.", field)
    try:
        parsed = datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValidationError("Enter a valid date in YYYY-MM-DD format.", field) from exc
    if parsed.year < 2000 or parsed.year > 2100:
        raise ValidationError("Date is outside the supported range.", field)
    if parsed > date.today():
        raise ValidationError("Date cannot be in the future.", field)
    return parsed.isoformat()


def parse_month_year(month, year) -> tuple[int, int]:
    try:
        month_i = int(month)
        year_i = int(year)
    except (TypeError, ValueError) as exc:
        raise ValidationError("Month and year must be valid numbers.", "month") from exc
    if month_i < 1 or month_i > 12:
        raise ValidationError("Month must be between 1 and 12.", "month")
    if year_i < 2000 or year_i > 2100:
        raise ValidationError("Year is outside the supported range.", "year")
    return month_i, year_i


def parse_type(value) -> str:
    if value not in TRANSACTION_TYPES:
        raise ValidationError("Type must be income or expense.", "type")
    return value


def parse_payment_method(value) -> str:
    if value not in PAYMENT_METHODS:
        raise ValidationError("Select a valid payment method.", "payment_method")
    return value


def parse_color(value: str) -> str:
    if not isinstance(value, str) or not COLOR_RE.match(value.strip()):
        raise ValidationError("Color must be a hex value such as #0F766E.", "color")
    return value.strip().upper()


def parse_icon(value: str) -> str:
    if value not in ICONS:
        raise ValidationError("Select a valid icon.", "icon")
    return value


def parse_positive_int(value, field: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{field} must be a whole number.", field) from exc
    if number < 1:
        raise ValidationError(f"{field} must be greater than zero.", field)
    return number


def clamp_limit(value, default: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(number, maximum))
