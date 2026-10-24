# Development status

## Implemented in this milestone
- Independent package; 23 inherited business DocTypes and five reports retained.
- Seven site-specific deposit/property/proration masters (the empty Lease prototype is excluded).
- New lock-based reservation API; explicit ownership and atomic unit switching.
- Contract-scoped cancellation and recurring-schedule disablement; no query of a missing invoice property column.
- Decimal calculation library: interval-aware escalation, deposits, actual-days first-month proration and threshold rounding.
- Service request server pricing, property hierarchy validation and draft first-month Rent-only invoice API.
- Fresh-site setup and additive custom fields.

## Remaining before a production release
- Run installation/migration and full accounting/lifecycle/concurrency tests in Frappe v16 on MariaDB.
- Existing-site module ownership transfer, reservation backfill, record reconciliation and rollback tooling.
- Complete CRM onboarding/customer linking, property deposit inheritance UI and remaining CRM field mappings from the inspected configuration.
- Configurable Rent/Deposit item mapping; manual negotiated-rate policy.
- Full legacy controller/API permission audit and multi-company/currency integration validation.
- Scheduler and penalty rewrite, end-date billing, credit notes and reversals. Inherited custom scheduling is not active in hooks.
- Recurring invoice/contract linkage through every generation path; legacy schedules without explicit links need reconciliation.
- Maintenance cost allocation, owner settlements, signature integration, and rental web frontend.
- No demonstration data, credentials, tenant records or live exports are included.

Do not treat inherited source presence or passing pure Python tests as proof that all upstream features are operational. Tests and exact limitations are reported in the repository and chat.

## Local verification
27 unit/regression/packaging tests pass on bundled Python. Frappe DB/integration checks have not run.
