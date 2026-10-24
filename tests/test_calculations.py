import unittest
from decimal import Decimal
from truegroup_property.domain.calculations import escalated_rent, rental_deposit, prorated_rent, money
from truegroup_property.domain.lifecycle import overlaps, reservation_allowed, contract_property_status


class CalculationTests(unittest.TestCase):
    def test_rent_anniversary(self):
        self.assertEqual(escalated_rent(10000, 10, "2024-07-15", "2026-07-14"), Decimal("11000.00"))
        self.assertEqual(escalated_rent(10000, 10, "2024-07-15", "2026-07-15"), Decimal("12100.00"))

    def test_nonannual_interval_and_delay(self):
        self.assertEqual(escalated_rent(100, 10, "2024-01-01", "2025-01-01", 6, 12), Decimal("110.00"))
        self.assertEqual(escalated_rent(100, 10, "2024-01-01", "2025-07-01", 6, 12), Decimal("121.00"))

    def test_before_anchor(self):
        self.assertEqual(escalated_rent(100, 10, "2026-01-01", "2025-01-01"), Decimal("100.00"))

    def test_leap_anniversary(self):
        self.assertEqual(escalated_rent(100, 10, "2024-02-29", "2025-02-28"), Decimal("110.00"))

    def test_invalid_escalation(self):
        for interval in (0, -1, "1.5"):
            with self.subTest(interval=interval), self.assertRaises(ValueError):
                escalated_rent(100, 10, "2024-01-01", "2025-01-01", interval)

    def test_deposit_fixed_and_multiple(self):
        self.assertEqual(rental_deposit(12345, "Fixed", fixed=4000), Decimal("4000.00"))
        self.assertEqual(rental_deposit("123.45", "Multiple of Rent", multiple=2), Decimal("246.90"))

    def test_invalid_deposit(self):
        for method, fixed, multiple in (("Unknown",0,0),("Fixed",-1,0),("Multiple of Rent",0,-1)):
            with self.subTest(method=method), self.assertRaises(ValueError):
                rental_deposit(100, method, fixed, multiple)

    def test_january_inclusive_proration(self):
        r = prorated_rent(31000, "2026-01-16")
        self.assertEqual((r["rate"], r["days"], r["days_in_month"]), (Decimal("16000.00"),16,31))

    def test_leap_february(self):
        self.assertEqual(prorated_rent(2900,"2024-02-29")["rate"], Decimal("100.00"))

    def test_threshold_charge_and_waive(self):
        self.assertEqual(prorated_rent(31000,"2026-01-30",3,"Charge")["rate"], Decimal("31000.00"))
        self.assertEqual(prorated_rent(31000,"2026-01-30",3,"Waive")["rate"], Decimal("0.00"))
        self.assertEqual(prorated_rent(31000,"2026-01-29",3,"Waive")["rate"], Decimal("3000.00"))

    def test_upward_rounding(self):
        self.assertEqual(prorated_rent(10000,"2026-01-31",rounding="Round up to nearest 100")["rate"], Decimal("400.00"))

    def test_invalid_proration(self):
        for args in ({"minimum_days":32},{"below_threshold":"Unknown"},{"rounding":"unknown"}):
            with self.subTest(args=args), self.assertRaises(ValueError):
                prorated_rent(100,"2026-01-01",**args)

    def test_finite_money_and_precision(self):
        self.assertEqual(money("1.005"), Decimal("1.01"))
        self.assertEqual(money("1.5",0), Decimal("2"))
        for value in ("NaN", "Infinity", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                money(value)


class LifecycleTests(unittest.TestCase):
    def test_overlapping_endpoints(self):
        self.assertTrue(overlaps("2026-01-01","2026-02-01","2026-02-01","2026-03-01"))
        self.assertFalse(overlaps("2026-01-01","2026-01-31","2026-02-01",None))
        self.assertTrue(overlaps(None,None,"2026-02-01",None))

    def test_invalid_period(self):
        with self.assertRaises(ValueError):
            overlaps("2026-02-01","2026-01-01",None,None)

    def test_reservations_require_explicit_owner(self):
        owner = ("CRM Deal","D1")
        self.assertTrue(reservation_allowed("Available",None,owner))
        self.assertTrue(reservation_allowed("Reserved",owner,owner))
        self.assertFalse(reservation_allowed("Reserved",None,owner))
        self.assertFalse(reservation_allowed("Reserved",("CRM Deal","D2"),owner))
        self.assertFalse(reservation_allowed("Occupied",owner,owner))

    def test_unsigned_does_not_occupy(self):
        self.assertEqual(contract_property_status("Active",True),"Occupied")
        self.assertEqual(contract_property_status("Active",False),"Reserved")
        self.assertEqual(contract_property_status("Unsigned",False),"Reserved")
        self.assertIsNone(contract_property_status("Inactive",True))


if __name__ == "__main__":
    unittest.main()
