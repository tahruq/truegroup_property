frappe.ui.form.on("CRM Deal", {
  refresh(frm) {
    if (frm.is_new()) return;
    frm.add_custom_button(__("Reserve Selected Unit"), async () => {
      if (frm.is_dirty()) await frm.save();
      const result = await frappe.call({method: "truegroup_property.services.reservations.reserve_deal_unit", args: {deal_name: frm.doc.name}, type: "POST", freeze: true});
      if (result.message?.status === "reserved") {
        await frm.reload_doc();
        frappe.show_alert({message: __("Unit reserved"), indicator: "green"});
      }
    }, __("Property"));
  }
});
