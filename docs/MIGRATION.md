# Existing Navari site migration — design, not an executable procedure

The current package rejects installation alongside utility_billing. Both own the same DocType names. Do not uninstall Navari to install this build; ordinary uninstall may remove its records.

A later migration must be rehearsed on a restorable staging backup:
1. Pin installed app versions/source; export complete customizations and count/hash affected records.
2. Transfer module/DocType ownership while preserving names, tables, child rows and all financial links. Coordinate the Frappe Cloud app-source switch and bench rebuild.
3. Backfill tg_contract and reservation owners from unambiguous Contract/Service Request/Deal evidence; leave ambiguous claims unresolved and report them.
4. Disable only reviewed legacy scripts superseded by the new services. Preserve CRM's standard scripts and existing notification preferences.
5. Reconcile Auto Repeat ownership and invoice Contract references. No property-wide billing shutdown.
6. Test draft/unsigned/signed contracts, cancellation with outstanding/paid invoices, shared-property history, multiple units, duplicate/concurrent actions and rollback.
7. Reconcile before/after counts and ledger totals; document acceptance and restore procedure.

The source code is currently a development milestone. No ownership-transfer patch or production installation instructions are supplied yet.
