# Derived from Navari Utility Billing (AGPL-3.0); see NOTICE.md.
app_name = "truegroup_property"
app_title = "Truegroup Property"
app_publisher = "Truegroup"
app_description = "Property, tenancy and utility billing for ERPNext v16"
app_email = "maintainers@example.invalid"
app_license = "agpl-3.0"
required_apps = ["erpnext", "crm"]
before_install = "truegroup_property.install.before_install"
after_install = "truegroup_property.install.after_install"
after_migrate = "truegroup_property.install.after_migrate"

accounting_dimension_doctypes = ["Utility Bill Structure", "Utility Service Request", "Utility Service Request Item", "Meter Reading"]

doctype_js = {
    "Contract": "public/js/contract.js",
    "Utility Service Request": "public/js/first_month.js",
    "CRM Deal": "public/js/deal.js",
    "CRM Lead": "public/js/lead.js",
    "Customer": "public/js/customer.js",
    "Item Price": "truegroup_property/overrides/client/item_price.js",
    "Auto Repeat": "truegroup_property/overrides/client/auto_repeat.js",
}
doctype_list_js = {"Sales Order": "truegroup_property/overrides/client/sales_order_list.js"}
doc_events = {
    "Contract": {
        "validate": "truegroup_property.services.onboarding.contract_source",
        "before_submit": "truegroup_property.services.contracts.before_submit",
        "on_submit": "truegroup_property.services.contracts.on_submit",
        "on_cancel": "truegroup_property.services.contracts.on_cancel",
        "on_update_after_submit": "truegroup_property.services.contracts.on_update_after_submit",
    },
    "CRM Deal": {"validate": "truegroup_property.services.onboarding.validate_deal"},
    "Customer": {"validate": "truegroup_property.services.onboarding.validate_customer", "after_insert": "truegroup_property.services.onboarding.link_customer"},
    "Utility Property": {"validate": "truegroup_property.services.properties.validate"},
    "Utility Service Request": {
        "before_validate": "truegroup_property.services.pricing.before_validate",
        "validate": "truegroup_property.services.onboarding.validate_service_request",
        "before_update_after_submit": "truegroup_property.services.onboarding.validate_service_request",
    },
    "Sales Order": {"validate": "truegroup_property.truegroup_property.overrides.server.sales_order.validate"},
    "Sales Invoice": {
        "before_validate": "truegroup_property.truegroup_property.overrides.server.sales_invoice.before_validate",
        "validate": "truegroup_property.truegroup_property.overrides.server.sales_invoice.validate",
        "on_submit": "truegroup_property.truegroup_property.overrides.server.sales_invoice.on_submit",
    },
    "Item": {"validate": "truegroup_property.truegroup_property.overrides.server.item.validate"},
}
# Recurring/penalty jobs are intentionally not enabled until staging integration tests pass.
