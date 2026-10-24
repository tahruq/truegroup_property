"""Draft first-month rent only; no deposits or unrelated request rows."""
import frappe
from frappe.utils import getdate, today
from truegroup_property.domain.calculations import prorated_rent
from .locks import lock


@frappe.whitelist(methods=["POST"])
def create_invoice(contract_name):
    contract = frappe.get_doc("Contract", contract_name)
    contract.check_permission("read")
    frappe.has_permission("Sales Invoice", "create", throw=True)
    lock("Contract", contract_name)
    contract.reload()
    if contract.docstatus != 1 or not contract.get("is_signed") or contract.status != "Active":
        frappe.throw("A submitted signed Active contract is required")
    if not contract.get("utility_service_request"):
        frappe.throw("Contract must link a service request")
    source = frappe.get_doc("Utility Service Request", contract.utility_service_request)
    source.check_permission("read")
    if source.docstatus != 1 or not source.customer:
        frappe.throw("A submitted customer service request is required")
    if contract.party_type != "Customer" or contract.party_name != source.customer:
        frappe.throw("Contract and service request must have the same Customer")
    existing = frappe.db.get_value("Sales Invoice", {"custom_contract": contract.name, "custom_invoice_purpose": "First Month Rent", "docstatus": ["!=", 2]}, "name")
    if existing:
        frappe.get_doc("Sales Invoice", existing).check_permission("read")
        return {"sales_invoice": existing, "already_exists": 1}
    invoice = frappe.new_doc("Sales Invoice")
    for field in ("company", "currency", "cost_center", "project", "customer_address", "contact_person"):
        if source.get(field):
            invoice.set(field, source.get(field))
    invoice.customer = source.customer
    invoice.posting_date = today()
    invoice.due_date = today()
    invoice.utility_service_request = source.name
    invoice.custom_contract = contract.name
    invoice.custom_invoice_purpose = "First Month Rent"
    allowed = {r.utility_property: r for r in contract.get("properties") or [] if r.get("is_active")}
    for item in source.items:
        if str(item.item_code or "").strip().lower() != "rent":
            continue
        unit = item.get("utility_property") or (next(iter(allowed)) if len(allowed) == 1 else None)
        if unit not in allowed:
            frappe.throw("Rent row must identify an active contract unit")
        if item.qty is None or item.qty <= 0:
            frappe.throw("Rent quantity must be positive")
        prop = frappe.get_doc("Utility Property", unit)
        prop.check_permission("read")
        if not prop.get("custom_proration_rule"):
            frappe.throw("A Proration Rule is required for each rent unit")
        rule = frappe.get_doc("Proration Rule", prop.custom_proration_rule)
        rule.check_permission("read")
        if str(rule.get("calculation_method") or "Actual Days").strip().lower() != "actual days":
            frappe.throw("Only Actual Days proration is supported in this development version")
        start = allowed[unit].get("start_date") or contract.get("start_date")
        if not start:
            frappe.throw("Contract start date is required")
        end = allowed[unit].get("end_date") or contract.get("end_date")
        from calendar import monthrange
        start_date = getdate(start)
        if end and getdate(end) < start_date.replace(day=monthrange(start_date.year, start_date.month)[1]):
            frappe.throw("Short tenancies ending before month-end need an explicit billing period; not supported yet")
        precision = item.precision("rate")
        precision = 2 if precision is None else precision
        try:
            result = prorated_rent(item.rate, start_date, rule.get("min_proration_treshold_days") or 0,
                rule.get("below_threshold_behaviour") or "Charge", rule.get("rounding_method") or "None", precision)
        except ValueError as exc:
            frappe.throw(str(exc))
        invoice.append("items", {"item_code": item.item_code, "qty": item.qty, "rate": float(result["rate"]),
            "utility_property": unit, "item_tax_template": item.get("item_tax_template")})
    if not invoice.items:
        frappe.throw("No Rent item exists on the service request")
    invoice.insert()
    return {"sales_invoice": invoice.name, "already_exists": 0}
