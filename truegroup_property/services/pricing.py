import frappe
from frappe.utils import getdate, today
from truegroup_property.domain.calculations import escalated_rent, rental_deposit


def before_validate(doc, method=None):
    if not doc.get("items") and doc.get("utility_bill_structure"):
        doc.validate_items()
    requested = [r.utility_property for r in (doc.get("requested_properties") or []) if r.get("utility_property")]
    for row in doc.get("items") or []:
        if str(row.item_code or "").strip().lower() not in ("rent", "deposit"):
            continue
        name = row.get("utility_property") or (requested[0] if len(requested) == 1 else None)
        if not name or name not in requested:
            frappe.throw("Each Rent/Deposit row must identify a requested unit; multiple units cannot use the first row implicitly")
        prop = frappe.get_doc("Utility Property", name)
        prop.check_permission("read")
        if prop.get("custom_base_rent") is None or not prop.get("custom_anchor_date"):
            frappe.throw("Base rent and anchor date are required on the unit")
        if row.qty is None or row.qty <= 0:
            frappe.throw("Rent/Deposit quantity must be positive")
        precision = row.precision("rate")
        precision = 2 if precision is None else precision
        try:
            interval = prop.get("custom_increment_interval")
            rent = escalated_rent(prop.custom_base_rent, prop.get("custom_increment_percentage") or 0,
                getdate(prop.custom_anchor_date), getdate(doc.get("date") or today()),
                interval_months=12 if interval is None else interval,
                effective_after=prop.get("custom_effective_after") or 0,
                places=precision)
            if str(row.item_code).strip().lower() == "rent":
                row.rate = float(rent)
                if prop.get("custom_tax_template"):
                    row.item_tax_template = prop.custom_tax_template
            else:
                policies = [p for p in (prop.get("custom_deposit_policy_details") or []) if str(p.get("deposit_type") or "").strip().lower().startswith("rental")]
                if len(policies) != 1:
                    frappe.throw("Exactly one rental deposit policy is required for automatic Deposit pricing")
                p = policies[0]
                row.rate = float(rental_deposit(rent, p.calculation_method, p.get("fixed_amount") or 0, p.get("multiple_of_rent") or 0, precision))
                row.qty = 1
            row.utility_property = name
            row.amount = row.qty * row.rate
        except ValueError as exc:
            frappe.throw(str(exc))
