# Truegroup Property

Development version 0.1.0a1 — **not ready for a live Navari replacement**.

An independent ERPNext v16/Frappe CRM app, derived from Navari Utility Billing at commit e2be8c17899cd9830622e3da231bcbb1b807f8f8. Retains existing business DocType names; Python package and module ownership are Truegroup Property. Includes 23 upstream DocTypes and five reports, with additional site-specific deposit/proration masters.

## This development milestone
- Attributed backend baseline under your repository.
- Explicit reservation ownership and transaction locks.
- Contract cancellation selects recurring schedules by contract, never a missing invoice property column.
- Decimal rent escalation, deposit and first-month proration calculations.
- Server-side service-request pricing and property hierarchy checks.
- Normal Contract submission, without committing a temporary Available status.
- Additive custom-field setup; existing field settings are not overwritten.

## Installation status
Requires Frappe/ERPNext version 16 and Frappe CRM. Test only on a **fresh disposable staging site**. The installer rejects coexistence with utility_billing because both apps own the same business DocTypes. **Do not uninstall Navari from an existing site to get past this check.** Existing-site ownership transfer/data migration is not implemented in this milestone.

Frappe Cloud should use this repository and the development branch shown in GitHub. Bench app name: truegroup_property. The independent /rental web frontend is not included; use ERPNext Desk. Installation, DB transactions and accounting still require Frappe integration tests; pure Python tests do not establish deployment readiness.

## Local tests
```sh
python -m unittest discover -s tests -v
python -m compileall -q truegroup_property
```

See docs/STATUS.md and docs/MIGRATION.md for remaining work. No user credentials, business records or live-site exports are included.
