import frappe
from truegroup_property.domain.lifecycle import reservation_allowed
from .locks import lock


def owner_of(prop):
    return (prop.get("tg_reservation_doctype"), prop.get("tg_reservation_name")) if prop.get("tg_reservation_name") else None


@frappe.whitelist(methods=["POST"])
def reserve_deal_unit(deal_name):
    deal = frappe.get_doc("CRM Deal", deal_name)
    deal.check_permission("write")
    lock("CRM Deal", deal_name)
    deal.reload()
    selected, previous = deal.get("custom_unit_name"), deal.get("custom_reserved_utility_property")
    if not selected:
        frappe.throw("Select a unit before reserving")
    for name in sorted(set(filter(None, (selected, previous)))):
        frappe.get_doc("Utility Property", name).check_permission("write")
        lock("Utility Property", name)
    prop = frappe.get_doc("Utility Property", selected)
    expected = ("CRM Deal", deal.name)
    if prop.is_group or prop.get("workflow_state") not in (None, "", "Approved"):
        frappe.throw("Only an approved unit can be reserved")
    if prop.get("tg_contract") or not reservation_allowed(prop.status, owner_of(prop), expected):
        frappe.throw("The unit is unavailable or reserved by another source; legacy reservations require review")
    if previous and previous != selected:
        old = frappe.get_doc("Utility Property", previous)
        if old.status != "Reserved" or owner_of(old) != expected or old.get("tg_contract"):
            frappe.throw("The previous reservation cannot be released by this deal")
        frappe.db.set_value("Utility Property", previous, {"status": "Available", "tg_reservation_doctype": None, "tg_reservation_name": None})
    frappe.db.set_value("Utility Property", selected, {"status": "Reserved", "tg_reservation_doctype": "CRM Deal", "tg_reservation_name": deal.name})
    frappe.db.set_value("CRM Deal", deal.name, "custom_reserved_utility_property", selected)
    # The request transaction commits once; no intermediate release is committed.
    return {"status": "reserved", "utility_property": selected}
