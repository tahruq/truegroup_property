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

frappe.ui.form.on("Utility Service Request", {
  refresh(frm) {
    if (frm.doc.docstatus !== 1 || !frm.doc.customer) return;
    frm.add_custom_button(__("Prepare / Open Tenancy Contract"), async () => {
      if (frm.is_dirty()) return frappe.msgprint(__("Save your changes first."));
      const r = await frappe.call({method: "truegroup_property.services.onboarding.prepare_contract", args: {request_name: frm.doc.name}, type: "POST", freeze: true});
      if (r.message?.contract) return frappe.set_route("Form", "Contract", r.message.contract);
      await frappe.model.with_doctype("Contract");
      const doc = frappe.model.get_new_doc("Contract");
      const values = {...r.message.values};
      const properties = values.properties || [];
      const terms = values.fulfilment_terms || [];
      delete values.fulfilment_terms;
      delete values.properties;
      Object.assign(doc, values);
      for (const row of properties) Object.assign(frappe.model.add_child(doc, "Contract Utility Property Item", "properties"), row);
      for (const row of terms) Object.assign(frappe.model.add_child(doc, "Contract Fulfilment Checklist", "fulfilment_terms"), row);
      frappe.set_route("Form", "Contract", doc.name);
    }, __("Create"));
  }
});
