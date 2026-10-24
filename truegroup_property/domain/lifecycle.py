"""Contract/reservation decisions, independently testable."""
from .calculations import as_date


def overlaps(start_a, end_a, start_b, end_b):
    start_a, end_a, start_b, end_b = [as_date(v) if v else None for v in (start_a, end_a, start_b, end_b)]
    if start_a and end_a and start_a > end_a or start_b and end_b and start_b > end_b:
        raise ValueError("Contract start must not follow its end")
    return not (end_a and start_b and end_a < start_b or end_b and start_a and end_b < start_a)


def reservation_allowed(status, owner, requested_owner):
    if status == "Available":
        return not owner or owner == requested_owner
    return status == "Reserved" and bool(owner) and owner == requested_owner


def contract_property_status(status, signed):
    if status == "Active" and signed:
        return "Occupied"
    if status in ("Active", "Unsigned"):
        return "Reserved"
    return None
