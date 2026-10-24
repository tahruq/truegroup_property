// Standard submission is atomic; no temporary Available status or custom Submit button.
frappe.ui.form.on("Contract", {
  refresh(frm) {
    if (!frm.is_new() && frm.doc.docstatus === 0) {
      frm.set_intro(__("Submit normally. Reserved units must belong to the linked service request or CRM deal."));
    }
  }
});
