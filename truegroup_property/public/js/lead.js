frappe.ui.form.on("CRM Lead", {
  refresh(frm) {
    if (frm.is_new() || frm.doc.status !== "Qualified") return;
    frm.add_custom_button(__("Create / Open Tenant Deal"), async () => {
      if (frm.is_dirty()) return frappe.msgprint(__("Save your changes first."));
      const r = await frappe.call({method: "truegroup_property.services.onboarding.create_deal", args: {lead_name: frm.doc.name}, type: "POST", freeze: true});
      if (r.message?.deal) frappe.set_route("Form", "CRM Deal", r.message.deal);
    });
  }
});
