import frappe


def lock(doctype, name):
    # Table names are fixed by the allow-list; names are SQL parameters.
    if doctype not in ("Contract", "Utility Property", "CRM Deal", "CRM Lead", "Utility Service Request"):
        raise ValueError("Unsupported lock target")
    rows = frappe.db.sql("SELECT name FROM `tab" + doctype + "` WHERE name=%s FOR UPDATE", (name,))
    if not rows:
        frappe.throw(f"{doctype} {name} does not exist")
