"""Contract-scope regression tests using a small Frappe adapter double.
These do not simulate MariaDB transactions or establish integration readiness.
"""
import importlib
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch


class Doc(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError as exc:
            raise AttributeError(key) from exc
    def __setattr__(self, key, value):
        self[key] = value


def fail(message):
    raise ValueError(message)


class ContractRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.adapter = SimpleNamespace(whitelist=lambda **kw: lambda f: f, throw=fail)
        with patch.dict(sys.modules, {"frappe": cls.adapter}):
            cls.service = importlib.import_module("truegroup_property.services.contracts")

    def setUp(self):
        self.frappe = self.adapter
        self.frappe.get_meta = Mock(side_effect=lambda dt: SimpleNamespace(has_field=lambda f: True))
        self.frappe.db = SimpleNamespace(sql=Mock(return_value=[("U1",)]),set_value=Mock())
        self.repeats = {name: Doc(disabled=disabled,save=Mock()) for name,disabled in [("AR1",0),("AR2",0),("AR3",1)]}
        self.frappe.get_doc = Mock(side_effect=lambda dt,name: self.repeats[name])
        self.calls = []
        def get_all(dt, filters, pluck):
            self.calls.append((dt,filters))
            if dt == "Sales Invoice":
                self.assertEqual(filters, {"custom_contract":"CON1"})
                return ["INV1"]
            if "reference_document" in filters:
                self.assertEqual(filters["reference_document"],["in",["INV1"]])
                return ["AR1","AR3"]
            self.assertEqual(filters,{"tg_contract":"CON1"})
            return ["AR1","AR2"]
        self.frappe.get_all = Mock(side_effect=get_all)

    def test_only_contract_scoped_schedules_are_stopped_once(self):
        result = self.service.cancel_contract_repeats("CON1")
        self.assertEqual(result,["AR1","AR2","AR3"])
        self.repeats["AR1"].save.assert_called_once()
        self.repeats["AR2"].save.assert_called_once()
        self.repeats["AR3"].save.assert_not_called()
        self.assertEqual(self.repeats["AR1"].disabled,1)
        self.frappe.db.sql.assert_not_called()

    def test_absent_invoice_contract_field_never_queries_missing_schema(self):
        self.frappe.get_meta = Mock(side_effect=lambda dt: SimpleNamespace(has_field=lambda f: dt=="Auto Repeat"))
        self.service.cancel_contract_repeats("CON1")
        self.assertFalse(any(dt=="Sales Invoice" for dt,_ in self.calls))
        self.frappe.db.sql.assert_not_called()

    def test_no_contract_link_fields_does_not_guess_by_property(self):
        self.frappe.get_meta = Mock(return_value=SimpleNamespace(has_field=lambda f:False))
        self.assertEqual(self.service.cancel_contract_repeats("CON1"),[])
        self.frappe.get_all.assert_not_called()

    def test_cancellation_does_not_release_someone_elses_unit(self):
        prop = Doc(name="U1",tg_contract="CON2",status="Occupied")
        self.frappe.get_doc = Mock(return_value=prop)
        doc = Doc(name="CON1",properties=[Doc(utility_property="U1",is_active=1)])
        with patch.object(self.service,"cancel_contract_repeats") as repeats:
            self.service.on_cancel(doc)
            repeats.assert_called_once_with("CON1")
        self.frappe.db.set_value.assert_not_called()
        self.assertIn("FOR UPDATE",self.frappe.db.sql.call_args.args[0])

    def test_cancellation_releases_own_unit_and_stops_billing(self):
        prop = Doc(name="U1",tg_contract="CON1",status="Occupied")
        self.frappe.get_doc = Mock(return_value=prop)
        doc = Doc(name="CON1",properties=[Doc(utility_property="U1",is_active=1)])
        with patch.object(self.service,"other_claims",return_value=[]), patch.object(self.service,"cancel_contract_repeats") as repeats:
            self.service.on_cancel(doc)
            self.frappe.db.set_value.assert_called_once_with("Utility Property","U1",{"status":"Available","tg_contract":None})
            repeats.assert_called_once_with("CON1")

    def test_conflicting_claim_is_not_silently_freed(self):
        self.frappe.get_doc = Mock(return_value=Doc(name="U1",tg_contract="CON1"))
        doc = Doc(name="CON1",properties=[Doc(utility_property="U1",is_active=1)])
        with patch.object(self.service,"other_claims",return_value=[Doc(name="CON2")]), patch.object(self.service,"cancel_contract_repeats") as repeats:
            with self.assertRaises(ValueError):
                self.service.on_cancel(doc)
            repeats.assert_not_called()
        self.frappe.db.set_value.assert_not_called()

    def test_duplicate_contract_units_rejected(self):
        doc = Doc(name="CON1",properties=[Doc(utility_property="U1",is_active=1),Doc(utility_property="U1",is_active=1)])
        with self.assertRaises(ValueError):
            self.service.before_submit(doc)


if __name__ == "__main__":
    unittest.main()
