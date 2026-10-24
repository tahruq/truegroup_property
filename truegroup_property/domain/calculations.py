"""Money calculations without a Frappe dependency."""
from calendar import monthrange
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, ROUND_CEILING


def number(value):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("A finite number is required") from exc
    if not result.is_finite():
        raise ValueError("A finite number is required")
    return result


def money(value, places=2):
    if not isinstance(places, int) or not 0 <= places <= 9:
        raise ValueError("Currency precision must be between zero and nine")
    try:
        return number(value).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise ValueError("Amount exceeds supported decimal precision") from exc


def as_date(value):
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def add_months(value, months):
    value = as_date(value)
    offset = value.year * 12 + value.month - 1 + months
    year, month0 = divmod(offset, 12)
    month = month0 + 1
    return date(year, month, min(value.day, monthrange(year, month)[1]))


def completed_months(anchor, at):
    anchor, at = as_date(anchor), as_date(at)
    months = (at.year - anchor.year) * 12 + at.month - anchor.month
    if at < add_months(anchor, months):
        months -= 1
    return max(0, months)


def escalated_rent(base, percentage, anchor, at, interval_months=12, effective_after=0, places=2):
    base, percentage = number(base), number(percentage)
    interval, delay = number(interval_months), number(effective_after)
    if base < 0 or percentage < 0 or interval != int(interval) or interval <= 0 or delay != int(delay) or delay < 0:
        raise ValueError("Rent, percentage and whole-month escalation intervals must be valid")
    interval, delay = int(interval), int(delay)
    elapsed = completed_months(anchor, at)
    first = delay or interval
    cycles = 0 if elapsed < first else 1 + (elapsed - first) // interval
    return money(base * (1 + percentage / 100) ** cycles, places)


def rental_deposit(rent, method, fixed=0, multiple=0, places=2):
    method = str(method).strip().lower()
    if method in ("fixed", "fixed amount"):
        result = number(fixed)
    elif method in ("multiple of rent", "rent multiple"):
        rent, multiple = number(rent), number(multiple)
        if rent < 0 or multiple < 0:
            raise ValueError("Rent and deposit multiplier cannot be negative")
        result = rent * multiple
    else:
        raise ValueError("Unknown deposit calculation method")
    if result < 0:
        raise ValueError("Deposit cannot be negative")
    return money(result, places)


def prorated_rent(monthly, start, minimum_days=0, below_threshold="Charge", rounding="None", places=2):
    monthly, start, minimum = number(monthly), as_date(start), number(minimum_days)
    if monthly < 0 or minimum != int(minimum) or not 0 <= minimum <= 31:
        raise ValueError("Invalid monthly rent or minimum proration days")
    behavior = str(below_threshold).strip().lower()
    if behavior not in ("charge", "waive"):
        raise ValueError("Threshold behavior must be Charge or Waive")
    mode = str(rounding or "None").strip().lower()
    allowed_rounding = ("none", "no rounding", "round up to nearest 100", "round up to 100", "up to nearest 100")
    if mode not in allowed_rounding:
        raise ValueError("Unsupported proration rounding method")
    days_in_month = monthrange(start.year, start.month)[1]
    days = days_in_month - start.day + 1
    if days < minimum:
        result = Decimal(0) if behavior == "waive" else monthly
    else:
        result = monthly * days / days_in_month
        if mode not in ("none", "no rounding"):
            result = (result / 100).to_integral_value(rounding=ROUND_CEILING) * 100
    return {"rate": money(result, places), "days": days, "days_in_month": days_in_month}
