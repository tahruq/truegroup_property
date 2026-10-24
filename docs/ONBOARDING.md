# Tenant onboarding development milestone

## Implemented path

1. Save a Qualified CRM Lead; **Create / Open Tenant Deal** reuses an existing Deal by either native Lead link or the app source field. New Deals copy supported identity/source fields, introducing agent and owner. Lead Organization text is resolved to an existing CRM Organization or inserted normally as a new Organization. An existing Lead Contact is copied; if none exists and email/mobile is supplied, a Contact is inserted with normal permissions in the same transaction.
2. Review the Deal, select a unit, fill Request Type, Expected Move-in Date and a positive whole-month duration, then mark it Won.
3. **Review / Open Customer** opens an unsaved Customer form or the explicitly linked existing Customer. Review required details and save. The app applies Utility & Rental group and source partner/manager, checks the primary contact/address against the Deal, adds missing Dynamic Links once and sets the Deal Customer pointer. A name match alone never adopts another Customer.
4. **Create / Open Service Request** reserves an approved unit and inserts a draft using the linked Customer, property Company, Bill Structure and billing adjustment rule. Server pricing uses the existing rent/deposit service. Repeated actions reopen the existing request; conflicting Customer/unit requests require reconciliation. The inherited date rule remains add_months(start, duration).
5. Review pricing, terms and dates, then submit the Service Request. **Prepare / Open Tenancy Contract** opens a review form without inserting, submitting or signing a Contract. The compatibility create_contract endpoint may insert a draft using normal mandatory/permission validation; it never bypasses mandatory fields.
6. Save and submit the reviewed Contract. Source Customer, unit set, active flags and date bounds are validated. Existing ownership/overlap checks govern reservation and occupancy. Sign using the standard Contract controls only after agreement; no onboarding action signs automatically.
7. The existing First Month Rent Invoice action requires exactly one submitted, signed Active Contract. It inserts a draft rent-only invoice, with actual-days proration and explicit Contract/request links.

Desk actions reject unsaved source changes. The separate Frappe CRM actions operate on the server-saved source and navigate to Desk for Customer, Service Request and Contract review.

## Installation configuration

Fresh staging only. Frappe/ERPNext 16 and Frappe CRM are required. The installer adds missing fields including Contract source/properties and Sales Invoice request linkage, the Utility & Rental Customer Group under the existing root, and named Truegroup Tenant Lead/Deal CRM Form Scripts. Existing named scripts, enabled states, custom-field settings and global CRM settings are preserved. ERPNext CRM integration should keep automatic Customer creation on status change disabled for the reviewed Customer flow.

Required roles depend on the document: the operator needs source write access, target create access and Contact/Address write access when linking those records. Normal framework permissions and mandatory fields apply. No permission bypass or internal transaction commit was introduced by the onboarding service.

## Validation and release boundary

61 Python tests include adapter regressions for duplicate creation, native/custom source disagreement, permissions, Customer review without writes, contact linking, mismatched unit/company/customer, draft request creation, submitted request requirement, Contract duplicate/date guards and normal insertion. Nine JavaScript checks exercise saved-form guards, review routing and CRM actions. Compilation is checked in CI.

Still required on a disposable Frappe v16/MariaDB site: install/migrate twice; verify the exact installed CRM action API and field layout; exercise the full flow as manager and restricted user; race two clients on the same Lead/Deal/unit/request; verify rollback on permission/mandatory errors; review cancellation/amendment and accounting/tax/currency results.

This is a development milestone, not a production release. The inherited controller/API permission audit, remaining optional field mappings, existing-site ownership/data migration, recurring scheduler work and broader feature completion remain listed in STATUS.md. No live site was changed.
