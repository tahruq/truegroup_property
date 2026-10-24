frappe.ui.form.on("Utility Service Request", {
  refresh(frm) {
    if (frm.doc.docstatus !== 1 || !frm.doc.customer) return;
    frm.add_custom_button(__("First Month Rent Invoice"), async () => {
      const contracts = await frappe.db.get_list("Contract", {filters: {utility_service_request: frm.doc.name, docstatus: 1, is_signed: 1, status: "Active"}, fields: ["name"], limit: 2});
      if (contracts.length !== 1) {
        frappe.msgprint(__("Exactly one signed Active contract must be linked. Review the contracts before billing."));
        return;
      }
      const result = await frappe.call({method: "truegroup_property.services.first_month.create_invoice", args: {contract_name: contracts[0].name}, type: "POST", freeze: true});
      if (result.message?.sales_invoice) frappe.set_route("Form", "Sales Invoice", result.message.sales_invoice);
    }, __("Create"));
  }
});
