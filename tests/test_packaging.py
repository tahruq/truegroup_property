import importlib
import json
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]


class PackagingTests(unittest.TestCase):
    def test_all_business_doctypes_match_module_and_disk_paths(self):
        docs = list((ROOT / "truegroup_property/truegroup_property/doctype").glob("*/*.json"))
        self.assertEqual(len(docs),30)
        for file in docs:
            with self.subTest(file=file.name):
                data = json.loads(file.read_text())
                self.assertEqual(data["module"],"Truegroup Property")
                self.assertEqual(data["name"].lower().replace(" ","_"),file.stem)
                fields = [f["fieldname"] for f in data["fields"]]
                self.assertEqual(len(fields),len(set(fields)))
                self.assertTrue(file.with_suffix(".py").exists())

    def test_every_new_custom_link_target_is_known(self):
        fields = json.loads((ROOT / "truegroup_property/configuration/custom_fields.json").read_text())
        custom_docs = {json.loads(f.read_text())["name"] for f in (ROOT / "truegroup_property/truegroup_property/doctype").glob("*/*.json")}
        standard = {"DocType","Contract","CRM Deal","CRM Lead","Sales Partner","Cost Center","Account","Item Tax Template","Workflow State"}
        for dt, rows in fields.items():
            for row in rows:
                if row["fieldtype"] in ("Link","Table"):
                    with self.subTest(doctype=dt,field=row["fieldname"]):
                        self.assertIn(row["options"],custom_docs | standard)

    def test_install_rejects_navari_without_creating_roles(self):
        fake = SimpleNamespace(get_installed_apps=lambda:["frappe","utility_billing"],throw=Mock(side_effect=ValueError("Migration required")),db=SimpleNamespace(exists=Mock()))
        customfield = SimpleNamespace(create_custom_fields=Mock())
        modules = {"frappe":fake,"frappe.custom":SimpleNamespace(),"frappe.custom.doctype":SimpleNamespace(),"frappe.custom.doctype.custom_field":SimpleNamespace(),"frappe.custom.doctype.custom_field.custom_field":customfield}
        with patch.dict(sys.modules,modules):
            sys.modules.pop("truegroup_property.install",None)
            install = importlib.import_module("truegroup_property.install")
            with self.assertRaises(ValueError):
                install.before_install()
        fake.db.exists.assert_not_called()


if __name__ == "__main__":
    unittest.main()
