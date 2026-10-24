"""Reviewed tenant onboarding; writes share the caller's transaction and permissions."""
import frappe
from truegroup_property.domain.calculations import as_date
from .locks import lock


def source(dt, name, permission="write"):
    doc = frappe.get_doc(dt, name)
    doc.check_permission(permission)
    lock(dt, name)
    doc.reload()
    return doc


def unique(dt, filters, exclude=None):
    names = [n for n in frappe.get_all(dt, filters=filters, pluck="name") if n != exclude]
    if len(names) > 1:
        frappe.throw("Multiple linked records exist; reconcile them before continuing")
    return names[0] if names else None


def immutable(doc, field):
    old = doc.get_doc_before_save()
    if old and old.get(field) != doc.get(field):
        frappe.throw(f"Amend or recreate the record to change {field}")


def known_values(dt, values):
    meta = frappe.get_meta(dt)
    return {k: v for k, v in values.items() if v is not None and meta.has_field(k)}


def deal_for_lead(name, exclude=None):
    names = frappe.get_all("CRM Deal", or_filters={"custom_crm_lead": name, "lead": name}, pluck="name")
    names = [n for n in names if n != exclude]
    if len(names) > 1:
        frappe.throw("Multiple Deals already exist for this Lead; reconcile them first")
    return names[0] if names else None


@frappe.whitelist(methods=["POST"])
def create_deal(lead_name):
    lead = source("CRM Lead", lead_name)
    if lead.get("status") != "Qualified":
        frappe.throw("Qualify the Lead before creating its Deal")
    existing = deal_for_lead(lead.name)
    if existing:
        frappe.get_doc("CRM Deal", existing).check_permission("read")
        return {"deal": existing, "existing": True}
    values = {k: lead.get(k) for k in ("first_name", "last_name", "email", "mobile_no", "organization", "territory", "website", "source", "currency", "custom_introducing_agent")}
    values.update(custom_crm_lead=lead.name, lead=lead.name, lead_name=lead.get("lead_name"), deal_owner=lead.get("lead_owner"))
    organization = lead.get("organization")
    if organization:
        name = organization if frappe.db.exists("CRM Organization", organization) else unique("CRM Organization", {"organization_name": organization})
        if not name:
            org = frappe.new_doc("CRM Organization")
            org.organization_name = organization
            org.insert()
            name = org.name
        frappe.get_doc("CRM Organization", name).check_permission("read")
        values["organization"] = name
    contact = lead.get("tg_tenant_contact") or lead.get("contact")
    if not contact and (lead.get("email") or lead.get("mobile_no")):
        person = frappe.new_doc("Contact")
        person.update(known_values("Contact", {k: lead.get(k) for k in ("first_name", "last_name", "salutation")}))
        if lead.get("email"):
            person.append("email_ids", {"email_id": lead.email, "is_primary": 1})
        if lead.get("mobile_no"):
            person.append("phone_nos", {"phone": lead.mobile_no, "is_primary_mobile_no": 1})
        person.insert()
        contact = person.name
        frappe.db.set_value("CRM Lead", lead.name, "tg_tenant_contact", contact)
    if contact:
        person = frappe.get_doc("Contact", contact)
        person.check_permission("read")
        values["contacts"] = [{"contact": contact, "is_primary": 1}]
    doc = frappe.new_doc("CRM Deal")
    doc.update(known_values("CRM Deal", values))
    doc.insert()
    return {"deal": doc.name, "existing": False}


def validate_deal(doc, method=None):
    if doc.get("lead") and doc.get("custom_crm_lead") and doc.lead != doc.custom_crm_lead:
        frappe.throw("Deal Lead links must agree")
    if doc.get("lead") and not doc.get("custom_crm_lead"):
        doc.custom_crm_lead = doc.lead
    immutable(doc, "custom_crm_lead")
    if doc.get("custom_crm_lead"):
        lead = source("CRM Lead", doc.custom_crm_lead)
        if doc.is_new() and lead.get("status") != "Qualified":
            frappe.throw("Qualify the source Lead first")
        if deal_for_lead(lead.name, doc.name):
            frappe.throw("This Lead already has a Deal")
    old = doc.get_doc_before_save()
    if old and old.get("custom_unit_name") != doc.get("custom_unit_name"):
        lock("CRM Deal", doc.name)
        if unique("Utility Service Request", {"tg_crm_deal": doc.name, "docstatus": ["!=", 2]}):
            frappe.throw("Cancel the existing Service Request before changing its unit")
    if doc.get("erpnext_customer"):
        customer = frappe.get_doc("Customer", doc.erpnext_customer)
        customer.check_permission("read")
        if customer.get("crm_deal") != doc.name:
            frappe.throw("The Customer must belong to this Deal")


def won(deal):
    if deal.get("status") != "Won":
        frappe.throw("Mark the Deal Won before preparing its Customer or tenancy")


def linked_customer(deal):
    name = unique("Customer", {"crm_deal": deal.name})
    if deal.get("erpnext_customer") and deal.erpnext_customer != name:
        frappe.throw("The Deal and Customer links disagree; reconcile them first")
    if name:
        frappe.get_doc("Customer", name).check_permission("read")
    return name


def customer_values(deal):
    contact = next((r.get("contact") for r in deal.get("contacts") or [] if r.get("is_primary")), None)
    org = None
    if deal.get("organization"):
        org = frappe.get_doc("CRM Organization", deal.organization)
        org.check_permission("read")
    name = (org.get("organization_name") or org.name) if org else deal.get("lead_name")
    if not name and contact:
        person = frappe.get_doc("Contact", contact)
        person.check_permission("read")
        name = person.get("full_name")
    return known_values("Customer", {
        "crm_deal": deal.name, "customer_name": name or deal.get("first_name"),
        "customer_type": "Company" if org else "Individual", "customer_group": "Utility & Rental",
        "territory": deal.get("territory") if frappe.db.exists("Territory", deal.get("territory")) else None, "default_currency": deal.get("currency"),
        "default_sales_partner": deal.get("custom_introducing_agent"), "account_manager": deal.get("deal_owner"),
        "customer_primary_contact": contact, "customer_primary_address": org.get("address") if org else None})


@frappe.whitelist(methods=["POST"])
def prepare_customer(deal_name):
    deal = source("CRM Deal", deal_name)
    won(deal)
    existing = linked_customer(deal)
    return {"customer": existing, "values": {} if existing else customer_values(deal)}


def validate_customer(doc, method=None):
    immutable(doc, "crm_deal")
    if not doc.get("crm_deal"):
        return
    deal = source("CRM Deal", doc.crm_deal)
    if doc.is_new():
        won(deal)
        if linked_customer(deal):
            frappe.throw("A Customer already exists for this Deal")
        values = customer_values(deal)
        for field in ("customer_group", "default_sales_partner", "account_manager"):
            if field in values:
                doc.set(field, values[field])
        for field in ("customer_primary_contact", "customer_primary_address"):
            if doc.get(field) and doc.get(field) != values.get(field):
                frappe.throw("Select the source Deal contact/address or leave it blank")


def link_customer(doc, method=None):
    if not doc.get("crm_deal"):
        return
    for dt, field in (("Contact", "customer_primary_contact"), ("Address", "customer_primary_address")):
        if not doc.get(field):
            continue
        target = frappe.get_doc(dt, doc.get(field))
        target.check_permission("write")
        if not any(r.get("link_doctype") == "Customer" and r.get("link_name") == doc.name for r in target.get("links") or []):
            target.append("links", {"link_doctype": "Customer", "link_name": doc.name})
            target.save()
    frappe.db.set_value("CRM Deal", doc.crm_deal, "erpnext_customer", doc.name)


def request_match(deal_name, customer, unit, exclude=None):
    rows = frappe.db.sql("""SELECT DISTINCT r.name FROM `tabUtility Service Request` r
        LEFT JOIN `tabContract Utility Property Item` p ON p.parent=r.name
          AND p.parenttype='Utility Service Request' AND p.parentfield='requested_properties'
        WHERE r.docstatus!=2 AND (r.tg_crm_deal=%s OR (r.customer=%s AND p.utility_property=%s))
          AND r.name!=%s ORDER BY r.name LIMIT 2""", (deal_name, customer, unit, exclude or ""), as_dict=True)
    if len(rows) > 1:
        frappe.throw("Multiple active Service Requests exist; reconcile them first")
    return rows[0].name if rows else None


def tenancy_source(deal):
    won(deal)
    customer = linked_customer(deal)
    if not customer:
        frappe.throw("Review and save the Deal's Customer first")
    if not deal.get("custom_unit_name"):
        frappe.throw("Select and save the Deal unit first")
    prop = frappe.get_doc("Utility Property", deal.custom_unit_name)
    prop.check_permission("write")
    if prop.get("is_group") or prop.get("workflow_state") != "Approved":
        frappe.throw("Select an approved unit")
    return customer, prop


@frappe.whitelist(methods=["POST"])
def create_service_request(deal_name):
    deal = source("CRM Deal", deal_name)
    customer, prop = tenancy_source(deal)
    # Serialize claims by different Deals for the same unit as well as double clicks.
    for unit in sorted(set(filter(None, (prop.name, deal.get("custom_reserved_utility_property"))))):
        lock("Utility Property", unit)
    existing = request_match(deal.name, customer, prop.name)
    if existing:
        request = frappe.get_doc("Utility Service Request", existing)
        request.check_permission("read")
        if request.get("tg_crm_deal") != deal.name:
            frappe.throw("An existing request claims this Customer/unit; review it first")
        return {"service_request": existing, "existing": True}
    months = deal.get("custom_contract_duration_in_months") or 0
    if not deal.get("custom_expected_move_in_date") or months <= 0 or months != int(months):
        frappe.throw("Set a move-in date and positive whole-month contract duration on the Deal")
    if not prop.get("company") or not prop.get("custom_utility_bill_structure") or not deal.get("custom_deal_type"):
        frappe.throw("Set the unit Company/Bill Structure and the Deal Request Type first")
    from .reservations import reserve_deal_unit
    reserve_deal_unit(deal.name)
    doc = frappe.new_doc("Utility Service Request")
    doc.update({"tg_crm_deal": deal.name, "service_request_from": "Customer", "party_name": customer,
        "customer": customer, "company": prop.company, "currency": deal.get("currency"),
        "cost_center": prop.get("custom_cost_center"), "territory": deal.get("territory") if frappe.db.exists("Territory", deal.get("territory")) else None,
        "customer_group": "Utility & Rental", "request_type": deal.custom_deal_type,
        "start_date": deal.custom_expected_move_in_date, "contract_length_months": months,
        "utility_bill_structure": prop.custom_utility_bill_structure, "utility_property": prop.name})
    doc.append("requested_properties", {"utility_property": prop.name, "is_active": 1,
        "start_date": doc.start_date, "contract_length_months": months,
        "adjustment_rule": prop.get("custom_billing_adjustment_rule")})
    doc.insert()
    return {"service_request": doc.name, "existing": False}


def validate_service_request(doc, method=None):
    immutable(doc, "tg_crm_deal")
    if not doc.get("tg_crm_deal"):
        return
    deal = source("CRM Deal", doc.tg_crm_deal)
    customer, prop = tenancy_source(deal)
    lock("Utility Property", prop.name)
    units = [r.get("utility_property") for r in doc.get("requested_properties") or []]
    if (doc.get("service_request_from") != "Customer" or doc.get("customer") != customer
            or doc.get("party_name") != customer or units != [prop.name] or doc.get("company") != prop.get("company")):
        frappe.throw("Service Request Customer, Company and unit must match the source Deal")
    if request_match(deal.name, customer, prop.name, doc.name):
        frappe.throw("An active Service Request already exists for this Deal or Customer/unit")
    from .reservations import owner_of
    if prop.get("status") == "Reserved" and owner_of(prop) != ("CRM Deal", deal.name):
        frappe.throw("This unit is reserved by another source")
    if doc.is_new():
        from .reservations import reserve_deal_unit
        reserve_deal_unit(deal.name)


def contract_source(doc, method=None):
    immutable(doc, "utility_service_request")
    if not doc.get("utility_service_request"):
        return
    request = source("Utility Service Request", doc.utility_service_request, "read")
    if request.docstatus != 1 or not request.get("customer"):
        frappe.throw("Submit the Customer Service Request before preparing a Contract")
    if doc.get("party_type") != "Customer" or doc.get("party_name") != request.customer:
        frappe.throw("Contract Customer must match its Service Request")
    if unique("Contract", {"utility_service_request": request.name, "docstatus": ["!=", 2]}, doc.name):
        frappe.throw("An active Contract already exists for this Service Request")
    expected = {r.get("utility_property"): r for r in request.get("requested_properties") or []}
    rows = doc.get("properties") or []
    actual = [r.get("utility_property") for r in rows]
    if set(actual) != set(expected) or len(actual) != len(expected):
        frappe.throw("Contract units must match its Service Request exactly")
    for row in rows:
        if not row.get("is_active"):
            frappe.throw("Source Contract units must remain active; amend the tenancy to remove a unit")
        original = expected[row.utility_property]
        start, end = row.get("start_date") or doc.get("start_date"), row.get("end_date") or doc.get("end_date")
        lower, upper = original.get("start_date") or request.get("start_date"), original.get("end_date") or request.get("end_date")
        if not start or not end or as_date(start) > as_date(end):
            frappe.throw("Set valid Contract start and end dates")
        if (lower and as_date(start) < as_date(lower)) or (upper and as_date(end) > as_date(upper)):
            frappe.throw("Contract dates must be within the source Service Request")


@frappe.whitelist(methods=["POST"])
def prepare_contract(request_name):
    request = source("Utility Service Request", request_name, "read")
    if request.docstatus != 1 or not request.get("customer"):
        frappe.throw("Submit the Customer Service Request first")
    existing = unique("Contract", {"utility_service_request": request.name, "docstatus": ["!=", 2]})
    if existing:
        frappe.get_doc("Contract", existing).check_permission("read")
        return {"contract": existing}
    values = {k: request.get(k) for k in ("start_date", "end_date", "contract_template", "contract_terms", "requires_fulfilment", "fulfilment_deadline")}
    values.update(party_type="Customer", party_name=request.customer, utility_service_request=request.name)
    values["properties"] = [{k: row.get(k) for k in ("utility_property", "start_date", "end_date", "contract_length_months", "adjustment_rule")}
        | {"is_active": 1} for row in request.get("requested_properties") or []]
    values["fulfilment_terms"] = [{k: v for k, v in row.as_dict().items() if k not in ("name", "doctype", "parent", "parenttype", "parentfield", "idx", "owner", "creation", "modified", "modified_by", "docstatus")} for row in request.get("fulfilment_terms") or []]
    return {"values": values}


@frappe.whitelist(methods=["POST"])
def create_contract(name):
    result = prepare_contract(name)
    if result.get("contract"):
        return result["contract"]
    doc = frappe.new_doc("Contract")
    doc.update(result["values"])
    doc.insert()
    return doc.name
