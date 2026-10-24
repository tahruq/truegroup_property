# Derived from Navari Utility Billing; see NOTICE.md.
from frappe.model.document import Document


class UtilityBillingSettings(Document):
    # Notification scheduling is configured explicitly after staging validation.
    # Do not create an expiry reminder 180 days after expiry or commit inside on_change.
    pass
