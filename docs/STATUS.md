# Development status

## Implemented in this milestone
- Independent package; 23 inherited business DocTypes and five reports retained.
- Seven site-specific deposit/property/proration masters (the empty Lease prototype is excluded).
- New lock-based reservation API; explicit ownership and atomic unit switching.
- Contract-scoped cancellation and recurring-schedule disablement; no query of a missing invoice property column.
- Decimal calculation library: interval-aware escalation, deposits, actual-days first-month proration and threshold rounding.
- Service request server pricing, property hierarchy validation and draft first-month Rent-only invoice API.
- Fresh-site setup and additive custom fields.
- Reviewed CRM tenant onboarding, explicit Customer linking and Contact/Address link deduplication.
- Duplicate/source guards on normal document writes, not just action buttons.
- Packaged Desk buttons and additive Frappe CRM Form Scripts; standard CRM scripts/settings remain untouched.

## Remaining before a production release
- Run installation/migration and full accounting/lifecycle/concurrency tests in Frappe v16 on MariaDB.
- Existing-site module ownership transfer, reservation backfill, record reconciliation and rollback tooling.
- Validate CRM onboarding against the exact installed CRM release; complete property deposit inheritance UI and remaining optional CRM field mappings from the inspected configuration.
- Configurable Rent/Deposit item mapping; manual negotiated-rate policy.
- Full legacy controller/API permission audit and multi-company/currency integration validation.
- Scheduler and penalty rewrite, end-date billing, credit notes and reversals. Inherited custom scheduling is not active in hooks.
- Recurring invoice/contract linkage through every generation path; legacy schedules without explicit links need reconciliation.
- Maintenance cost allocation, owner settlements, signature integration, and rental web frontend.
- No demonstration data, credentials, tenant records or live exports are included.

Do not treat inherited source presence or passing pure Python tests as proof that all upstream features are operational. Tests and exact limitations are reported in the repository and chat.

## Local verification
61 Python unit/regression/packaging tests and 9 JavaScript action checks pass locally. Python compilation passes. These use adapter doubles and do not establish transaction, installation or UI compatibility on a running Frappe site. Frappe DB/integration checks have not run.
