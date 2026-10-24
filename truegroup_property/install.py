"""Fresh-site installation only; existing-site ownership transfer is separate."""
import json
from pathlib import Path
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def before_install():
    if "utility_billing" in frappe.get_installed_apps():
        frappe.throw("Navari utility_billing is installed. This development build cannot coexist with it. Do not uninstall it: use a reviewed staging ownership-transfer migration.")
    if int(frappe.__version__.split(".")[0]) != 16:
        frappe.throw("Truegroup Property requires Frappe version 16")
    # A detached legacy module can still own records after an incomplete uninstall.
    if frappe.db.exists("Module Def", "Utility Billing"):
        frappe.throw("A legacy Utility Billing module exists; ownership migration must be reviewed before installation")
    for role in ("Property Manager", "Property User", "Utility Manager", "Utility User"):
        if not frappe.db.exists("Role", role):
            frappe.get_doc({"doctype": "Role", "role_name": role}).insert()



def after_install():
    for role in ("Property Manager", "Property User"):
        if not frappe.db.exists("Role", role):
            frappe.get_doc({"doctype": "Role", "role_name": role}).insert()
    ensure_custom_fields()
    create_onboarding_workflow()


def create_onboarding_workflow():
    config = json.loads((Path(__file__).parent / "configuration" / "workflow.json").read_text())
    if frappe.db.exists("Workflow", config["workflow_name"]):
        return
    for row in config["states"]:
        if not frappe.db.exists("Workflow State", row["state"]):
            frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": row["state"]}).insert()
    for row in config["transitions"]:
        if not frappe.db.exists("Workflow Action Master", row["action"]):
            frappe.get_doc({"doctype": "Workflow Action Master", "workflow_action_name": row["action"]}).insert()
    frappe.get_doc(config).insert()


def ensure_custom_fields():
    config = json.loads((Path(__file__).parent / "configuration" / "custom_fields.json").read_text())
    # Fail on incompatible existing business fields rather than changing their type.
    for dt, fields in config.items():
        meta = frappe.get_meta(dt)
        for f in fields:
            existing = meta.get_field(f["fieldname"])
            if existing and (existing.fieldtype != f["fieldtype"] or (f.get("options") and existing.options != f["options"])):
                frappe.throw(f"Incompatible existing field: {dt}.{f['fieldname']}")
    create_custom_fields(config, update=False)
