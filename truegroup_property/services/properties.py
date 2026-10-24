import frappe


def validate(doc, method=None):
    parent_name = doc.get("parent_utility_property")
    if not parent_name:
        if not doc.is_group:
            frappe.throw("A unit must belong to an approved sub-property")
        return
    parent = frappe.get_doc("Utility Property", parent_name)
    parent.check_permission("read")
    if not parent.is_group or parent.get("workflow_state") != "Approved":
        frappe.throw("Parent must be an approved property group")
    if doc.is_group and parent.get("parent_utility_property"):
        frappe.throw("A sub-property group must belong directly to a main property")
    if not doc.is_group and not parent.get("parent_utility_property"):
        frappe.throw("Create units under a sub-property, not directly under a main property")
