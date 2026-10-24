frappe.ui.form.on("CRM Deal", {
  refresh(frm) {
    if (frm.is_new()) return;
    const saved = () => {
      if (!frm.is_dirty()) return true;
      frappe.msgprint(__("Save your changes first."));
      return false;
    };
    frm.add_custom_button(__("Reserve Selected Unit"), async () => {
      if (!saved()) return;
      await frappe.call({method: "truegroup_property.services.reservations.reserve_deal_unit", args: {deal_name: frm.doc.name}, type: "POST", freeze: true});
      await frm.reload_doc();
    });
    if (frm.doc.status !== "Won") return;
    frm.add_custom_button(__("Review / Open Customer"), async () => {
      if (!saved()) return;
      const r = await frappe.call({method: "truegroup_property.services.onboarding.prepare_customer", args: {deal_name: frm.doc.name}, type: "POST", freeze: true});
      if (r.message?.customer) return frappe.set_route("Form", "Customer", r.message.customer);
      frappe.new_doc("Customer", r.message.values);
    });
    frm.add_custom_button(__("Create / Open Service Request"), async () => {
      if (!saved()) return;
      const r = await frappe.call({method: "truegroup_property.services.onboarding.create_service_request", args: {deal_name: frm.doc.name}, type: "POST", freeze: true});
      if (r.message?.service_request) frappe.set_route("Form", "Utility Service Request", r.message.service_request);
    });
  }
});
