frappe.ui.form.on("Customer", {
  async onload(frm) {
    if (!frm.is_new()) return;
    const deal = frm.doc.crm_deal || new URLSearchParams(window.location.search).get("crm_deal");
    if (!deal) return;
    const r = await frappe.call({method: "truegroup_property.services.onboarding.prepare_customer", args: {deal_name: deal}, type: "POST", freeze: true});
    if (r.message?.customer) return frappe.set_route("Form", "Customer", r.message.customer);
    await frm.set_value(r.message.values);
    frm.set_intro(__("Review the Customer details, then save to link this Customer to the source Deal."));
  }
});
