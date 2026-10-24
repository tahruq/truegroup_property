# Truegroup Property hierarchical master.
from frappe.utils.nestedset import NestedSet

class PropertyType(NestedSet):
    nsm_parent_field = "parent_property_type"
