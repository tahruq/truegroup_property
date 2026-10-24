"""Onboarding adapter regressions; real Frappe/MariaDB staging remains required."""
import importlib
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch


class Doc(dict):
    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return self.get(name)
    def __setattr__(self, name, value):
        self[name] = value
    def check_permission(self, permission):
        if self.get("_deny"):
            raise PermissionError(permission)
    def reload(self):
        return self
    def get_doc_before_save(self):
        return self.get("_old")
    def is_new(self):
        return not self.get("_saved")
    def set(self, key, value):
        self[key] = value
    def append(self, key, value):
        self.setdefault(key, []).append(Doc(value))
    def as_dict(self):
        return dict(self)


def fail(message):
    raise ValueError(message)


class OnboardingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fake = SimpleNamespace(whitelist=lambda **kw: lambda f: f, throw=fail)
        with patch.dict(sys.modules, {"frappe": fake}):
            cls.service = importlib.import_module("truegroup_property.services.onboarding")

    def setUp(self):
        self.docs = {}
        self.lead = Doc(name="L1", status="Qualified", first_name="Tenant", lead_owner="agent")
        self.deal = Doc(name="D1", status="Won", custom_unit_name="U1", erpnext_customer="C1",
                        custom_expected_move_in_date="2026-10-15", custom_contract_duration_in_months=12,
                        custom_deal_type="Rental", currency="KES", contacts=[])
        self.customer = Doc(name="C1", crm_deal="D1")
        self.prop = Doc(name="U1", is_group=0, workflow_state="Approved", company="Company",
                        custom_utility_bill_structure="BS1", status="Available")
        self.request = Doc(name="R1", docstatus=1, customer="C1", tg_crm_deal="D1",
                           start_date="2026-10-15", end_date="2027-10-15",
                           requested_properties=[Doc(utility_property="U1")])
        for dt, doc in (("CRM Lead", self.lead), ("CRM Deal", self.deal), ("Customer", self.customer),
                        ("Utility Property", self.prop), ("Utility Service Request", self.request)):
            self.docs[dt, doc.name] = doc
        self.all = Mock(return_value=[])
        self.sql = Mock(return_value=[])
        self.fake = SimpleNamespace(throw=fail, get_all=self.all,
            get_doc=Mock(side_effect=lambda dt, name: self.docs[dt, name]),
            get_meta=lambda dt: SimpleNamespace(has_field=lambda key: True),
            new_doc=Mock(side_effect=self.new_doc),
            db=SimpleNamespace(sql=self.sql, set_value=Mock(), exists=Mock(return_value=True)))
        self.patches = [patch.object(self.service, "frappe", self.fake),
                        patch.object(self.service, "lock", Mock())]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)
        self.created = []

    def new_doc(self, dt):
        doc = Doc(doctype=dt, name="NEW")
        doc.insert = Mock(return_value=doc)
        self.created.append(doc)
        return doc

    def customer_link(self):
        self.all.side_effect = lambda dt, **kwargs: ["C1"] if dt == "Customer" else []

    def contract(self, **values):
        doc = Doc(name="CON1", utility_service_request="R1", party_type="Customer",
                  party_name="C1", start_date="2026-10-15", end_date="2027-10-15",
                  properties=[Doc(utility_property="U1", is_active=1)])
        doc.update(values)
        return doc

    def test_unqualified_lead_cannot_create_deal(self):
        self.lead.status = "New"
        with self.assertRaisesRegex(ValueError, "Qualify"):
            self.service.create_deal("L1")
        self.fake.new_doc.assert_not_called()

    def test_existing_deal_is_reused(self):
        self.all.return_value = ["D1"]
        self.assertEqual(self.service.create_deal("L1"), {"deal": "D1", "existing": True})
        self.fake.new_doc.assert_not_called()

    def test_create_deal_maps_source_and_uses_normal_insert(self):
        result = self.service.create_deal("L1")
        self.assertFalse(result["existing"])
        self.assertEqual(self.created[0].custom_crm_lead, "L1")
        self.created[0].insert.assert_called_once_with()

    def test_source_permission_denial_prevents_creation(self):
        self.lead._deny = True
        with self.assertRaises(PermissionError):
            self.service.create_deal("L1")
        self.fake.new_doc.assert_not_called()

    def test_duplicate_deal_direct_save_is_blocked(self):
        self.all.return_value = ["OTHER"]
        with self.assertRaisesRegex(ValueError, "already has"):
            self.service.validate_deal(Doc(name="NEW", custom_crm_lead="L1"))

    def test_customer_prefill_does_not_insert(self):
        self.deal.erpnext_customer = None
        result = self.service.prepare_customer("D1")
        self.assertEqual(result["values"]["crm_deal"], "D1")
        self.fake.new_doc.assert_not_called()
        self.fake.db.set_value.assert_not_called()

    def test_customer_requires_won(self):
        self.deal.status = "Qualification"
        with self.assertRaisesRegex(ValueError, "Won"):
            self.service.prepare_customer("D1")

    def test_customer_prefill_reuses_explicit_link(self):
        self.customer_link()
        self.assertEqual(self.service.prepare_customer("D1")["customer"], "C1")

    def test_mismatched_customer_pointer_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "links disagree"):
            self.service.prepare_customer("D1")

    def test_duplicate_customer_direct_insert_is_blocked(self):
        self.customer_link()
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.service.validate_customer(Doc(name="NEW", crm_deal="D1"))

    def test_customer_source_cannot_be_changed(self):
        with self.assertRaisesRegex(ValueError, "change crm_deal"):
            self.service.validate_customer(Doc(crm_deal="D2", _old=Doc(crm_deal="D1")))

    def test_unrelated_primary_contact_is_rejected(self):
        self.deal.erpnext_customer = None
        with self.assertRaisesRegex(ValueError, "source Deal contact"):
            self.service.validate_customer(Doc(name="NEW", crm_deal="D1", customer_primary_contact="OTHER"))

    def test_contact_link_is_deduplicated(self):
        person = Doc(name="P1", links=[Doc(link_doctype="Customer", link_name="C1")], save=Mock())
        self.docs["Contact", "P1"] = person
        self.customer.customer_primary_contact = "P1"
        self.service.link_customer(self.customer)
        person.save.assert_not_called()
        self.fake.db.set_value.assert_called_once_with("CRM Deal", "D1", "erpnext_customer", "C1")

    def test_request_reuses_existing_without_inserting(self):
        self.customer_link()
        self.sql.return_value = [Doc(name="R1")]
        self.assertTrue(self.service.create_service_request("D1")["existing"])
        self.fake.new_doc.assert_not_called()

    def test_request_does_not_adopt_another_deals_request(self):
        self.customer_link()
        self.sql.return_value = [Doc(name="R1")]
        self.request.tg_crm_deal = "OTHER"
        with self.assertRaisesRegex(ValueError, "existing request claims"):
            self.service.create_service_request("D1")

    def test_request_rejects_unapproved_unit(self):
        self.customer_link()
        self.prop.workflow_state = "Draft"
        with self.assertRaisesRegex(ValueError, "approved"):
            self.service.create_service_request("D1")

    def test_request_rejects_invalid_duration(self):
        self.customer_link()
        self.deal.custom_contract_duration_in_months = 1.5
        with self.assertRaisesRegex(ValueError, "whole-month"):
            self.service.create_service_request("D1")

    def test_request_customer_unit_and_company_cannot_be_forged(self):
        self.customer_link()
        for field, wrong in (("customer", "OTHER"), ("party_name", "OTHER"), ("company", "OTHER"),
                             ("requested_properties", [Doc(utility_property="OTHER")])):
            with self.subTest(field=field):
                doc = Doc(name="R1", _saved=True, tg_crm_deal="D1", service_request_from="Customer",
                          customer="C1", party_name="C1", company="Company",
                          requested_properties=[Doc(utility_property="U1")])
                doc[field] = wrong
                with self.assertRaisesRegex(ValueError, "must match"):
                    self.service.validate_service_request(doc)

    def test_contract_requires_submitted_source(self):
        self.request.docstatus = 0
        with self.assertRaisesRegex(ValueError, "Submit"):
            self.service.prepare_contract("R1")

    def test_contract_prepare_has_no_insert_submit_or_signature_side_effect(self):
        result = self.service.prepare_contract("R1")
        self.assertEqual(result["values"]["party_name"], "C1")
        self.assertNotIn("is_signed", result["values"])
        self.fake.new_doc.assert_not_called()
        self.fake.db.set_value.assert_not_called()

    def test_contract_duplicate_direct_save_is_blocked(self):
        self.all.return_value = ["OTHER"]
        with self.assertRaisesRegex(ValueError, "active Contract"):
            self.service.contract_source(self.contract())

    def test_contract_wrong_customer_or_units_is_blocked(self):
        for values in ({"party_name": "OTHER"}, {"properties": [Doc(utility_property="OTHER")]}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.service.contract_source(self.contract(**values))

    def test_contract_dates_cannot_exceed_request(self):
        with self.assertRaisesRegex(ValueError, "within"):
            self.service.contract_source(self.contract(end_date="2028-01-01"))

    def test_matching_contract_source_passes(self):
        self.service.contract_source(self.contract())

    def test_multiple_requests_require_reconciliation(self):
        self.sql.return_value = [Doc(name="R1"), Doc(name="R2")]
        with self.assertRaisesRegex(ValueError, "Multiple"):
            self.service.request_match("D1", "C1", "U1")


    def test_create_request_reserves_then_inserts_draft(self):
        self.customer_link()
        fake = SimpleNamespace(whitelist=lambda **kw: lambda f: f)
        with patch.dict(sys.modules, {"frappe": fake}):
            reservations = importlib.import_module("truegroup_property.services.reservations")
            with patch.object(reservations, "reserve_deal_unit") as reserve:
                result = self.service.create_service_request("D1")
        reserve.assert_called_once_with("D1")
        self.assertFalse(result["existing"])
        doc = self.created[0]
        self.assertEqual((doc.customer, doc.company, doc.tg_crm_deal), ("C1", "Company", "D1"))
        self.assertEqual(doc.requested_properties[0].utility_property, "U1")
        doc.insert.assert_called_once_with()
        self.assertNotIn("docstatus", doc)

    def test_direct_request_duplicate_cannot_bypass_button(self):
        self.customer_link()
        self.sql.return_value = [Doc(name="OTHER")]
        doc = Doc(name="R1", _saved=True, tg_crm_deal="D1", service_request_from="Customer",
                  customer="C1", party_name="C1", company="Company",
                  requested_properties=[Doc(utility_property="U1")])
        with self.assertRaisesRegex(ValueError, "active Service Request"):
            self.service.validate_service_request(doc)

    def test_native_lead_and_custom_source_must_agree(self):
        with self.assertRaisesRegex(ValueError, "must agree"):
            self.service.validate_deal(Doc(name="NEW", lead="L2", custom_crm_lead="L1"))

    def test_deal_unit_cannot_change_after_request(self):
        self.all.return_value = ["R1"]
        doc = Doc(name="D1", custom_unit_name="U2", _saved=True, _old=Doc(custom_unit_name="U1"))
        with self.assertRaisesRegex(ValueError, "Cancel"):
            self.service.validate_deal(doc)

    def test_native_source_is_normalized_for_duplicate_checks(self):
        self.all.return_value = ["D1"]
        doc = Doc(name="NEW", lead="L1")
        with self.assertRaisesRegex(ValueError, "already has"):
            self.service.validate_deal(doc)
        self.assertEqual(doc.custom_crm_lead, "L1")

    def test_contract_creation_uses_normal_insert_and_reuses_existing(self):
        result = self.service.create_contract("R1")
        self.assertEqual(result, "NEW")
        self.created[0].insert.assert_called_once_with()
        self.fake.new_doc.reset_mock()
        self.docs["Contract", "CON1"] = Doc(name="CON1")
        self.all.return_value = ["CON1"]
        self.assertEqual(self.service.create_contract("R1"), "CON1")
        self.fake.new_doc.assert_not_called()


    def test_lead_organization_text_maps_to_existing_link(self):
        self.lead.organization = "Tenant Company"
        self.docs["CRM Organization", "Tenant Company"] = Doc(name="Tenant Company")
        self.service.create_deal("L1")
        self.assertEqual(self.created[0].organization, "Tenant Company")

    def test_lead_contact_is_created_normally_and_copied(self):
        self.lead.email = "tenant@example.invalid"
        original = self.new_doc
        def create(dt):
            doc = original(dt)
            self.docs[dt, doc.name] = doc
            return doc
        self.fake.new_doc.side_effect = create
        self.service.create_deal("L1")
        contact, deal = self.created
        self.assertEqual(contact.doctype, "Contact")
        self.assertEqual(contact.email_ids[0].email_id, "tenant@example.invalid")
        contact.insert.assert_called_once_with()
        self.assertEqual(deal.contacts[0]["contact"], contact.name)
        self.fake.db.set_value.assert_called_once_with("CRM Lead", "L1", "tg_tenant_contact", contact.name)

    def test_source_contract_cannot_hide_inactive_unit(self):
        with self.assertRaisesRegex(ValueError, "remain active"):
            self.service.contract_source(self.contract(properties=[Doc(utility_property="U1", is_active=0)]))


if __name__ == "__main__":
    unittest.main()
