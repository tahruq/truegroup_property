"""Contract-scoped lifecycle: no invoice property-column assumptions."""
import frappe
from truegroup_property.domain.lifecycle import overlaps, contract_property_status
from .locks import lock
from .reservations import owner_of


def active_rows(doc):
    return [r for r in (doc.get("properties") or []) if r.get("is_active") and r.get("utility_property")]


def other_claims(property_name, contract_name):
    return frappe.db.sql("""SELECT c.name, c.start_date, c.end_date, p.start_date AS unit_start,
        p.end_date AS unit_end FROM `tabContract` c
        INNER JOIN `tabContract Utility Property Item` p ON p.parent=c.name
        WHERE p.parenttype='Contract' AND p.parentfield='properties'
        AND p.utility_property=%s AND p.is_active=1 AND c.docstatus=1
        AND c.status IN ('Active', 'Unsigned') AND c.name!=%s""", (property_name, contract_name), as_dict=True)


def before_submit(doc, method=None):
    rows = active_rows(doc)
    if len({r.utility_property for r in rows}) != len(rows):
        frappe.throw("A unit cannot appear twice in a contract")
    request = frappe.get_doc("Utility Service Request", doc.utility_service_request) if doc.get("utility_service_request") else None
    permitted = {("Utility Service Request", request.name)} if request else set()
    if request and request.get("tg_crm_deal"):
        permitted.add(("CRM Deal", request.tg_crm_deal))
    for row in sorted(rows, key=lambda r: r.utility_property):
        lock("Utility Property", row.utility_property)
        prop = frappe.get_doc("Utility Property", row.utility_property)
        prop.check_permission("write")
        if prop.is_group or prop.status not in ("Available", "Reserved"):
            frappe.throw("The unit must be Available or reserved by this contract's source")
        if prop.get("tg_contract") and prop.tg_contract != doc.name:
            frappe.throw("The unit belongs to another contract")
        if prop.status == "Reserved" and owner_of(prop) not in permitted:
            frappe.throw("The reservation does not belong to this contract's source")
        for claim in other_claims(prop.name, doc.name):
            if overlaps(row.get("start_date") or doc.get("start_date"), row.get("end_date") or doc.get("end_date"), claim.get("unit_start") or claim.start_date, claim.get("unit_end") or claim.end_date):
                frappe.throw("Another submitted contract claims this unit for overlapping dates")


def on_submit(doc, method=None):
    synchronize(doc)


def on_update_after_submit(doc, method=None):
    previous = doc.get_doc_before_save()
    if previous and {r.get("utility_property") for r in previous.get("properties") or []} != {r.get("utility_property") for r in doc.get("properties") or []}:
        frappe.throw("Amend the contract to change its unit list")
    if previous and {r.get("utility_property"): r.get("is_active") for r in previous.get("properties") or []} != {r.get("utility_property"): r.get("is_active") for r in doc.get("properties") or []}:
        frappe.throw("Amend the contract to change unit activation")
    synchronize(doc)
    if contract_property_status(doc.status, doc.get("is_signed")) is None:
        cancel_contract_repeats(doc.name)


def synchronize(doc):
    target = contract_property_status(doc.status, doc.get("is_signed"))
    for row in sorted(doc.get("properties") or [], key=lambda r: r.get("utility_property") or ""):
        if not row.get("utility_property"):
            continue
        lock("Utility Property", row.utility_property)
        prop = frappe.get_doc("Utility Property", row.utility_property)
        if target and row.get("is_active"):
            if not prop.get("tg_contract"):
                request = frappe.get_doc("Utility Service Request", doc.utility_service_request) if doc.get("utility_service_request") else None
                permitted = {("Utility Service Request", request.name)} if request else set()
                if request and request.get("tg_crm_deal"):
                    permitted.add(("CRM Deal", request.tg_crm_deal))
                if prop.status != "Available" and not (prop.status == "Reserved" and owner_of(prop) in permitted):
                    frappe.throw("The unit is not available or owned by this contract source")
            if prop.get("tg_contract") not in (None, "", doc.name):
                frappe.throw("The unit belongs to another contract")
            for claim in other_claims(prop.name, doc.name):
                if overlaps(row.get("start_date") or doc.get("start_date"), row.get("end_date") or doc.get("end_date"), claim.get("unit_start") or claim.start_date, claim.get("unit_end") or claim.end_date):
                    frappe.throw("A conflicting contract already claims this unit")
            frappe.db.set_value("Utility Property", prop.name, {"status": target, "tg_contract": doc.name, "tg_reservation_doctype": None, "tg_reservation_name": None})
        elif prop.get("tg_contract") == doc.name:
            if other_claims(prop.name, doc.name):
                frappe.throw("Conflicting claims require review before releasing this unit")
            frappe.db.set_value("Utility Property", prop.name, {"status": "Available", "tg_contract": None})


def cancel_contract_repeats(contract_name):
    # Invoice linkage is by Contract; never query Sales Invoice.utility_property.
    invoices = frappe.get_all("Sales Invoice", filters={"custom_contract": contract_name}, pluck="name") if frappe.get_meta("Sales Invoice").has_field("custom_contract") else []
    names = set()
    if invoices:
        names.update(frappe.get_all("Auto Repeat", filters={"reference_doctype": "Sales Invoice", "reference_document": ["in", invoices]}, pluck="name"))
    if frappe.get_meta("Auto Repeat").has_field("tg_contract"):
        names.update(frappe.get_all("Auto Repeat", filters={"tg_contract": contract_name}, pluck="name"))
    for name in sorted(names):
        repeat = frappe.get_doc("Auto Repeat", name)
        if not repeat.disabled:
            repeat.disabled = 1
            repeat.save()
    return sorted(names)


def on_cancel(doc, method=None):
    for row in sorted(doc.get("properties") or [], key=lambda r: r.get("utility_property") or ""):
        if not row.get("utility_property"):
            continue
        lock("Utility Property", row.utility_property)
        prop = frappe.get_doc("Utility Property", row.utility_property)
        # Never free a unit claimed by someone else or an unidentified legacy record.
        if prop.get("tg_contract") == doc.name:
            if other_claims(prop.name, doc.name):
                frappe.throw("Another submitted contract claims this unit; review ownership before cancellation")
            frappe.db.set_value("Utility Property", prop.name, {"status": "Available", "tg_contract": None})
    cancel_contract_repeats(doc.name)
