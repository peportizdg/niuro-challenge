import unittest
from decimal import Decimal

from credit import features


def tx(i, date, amount):
    return {"transaction_id": str(i), "date": date, "amount": Decimal(amount)}


class FeaturesTest(unittest.TestCase):
    def test_features_and_offer_over_a_90_day_window(self):
        # 2026-07-01 a 2026-09-28: 90 días, 64 hábiles.
        txns = [
            tx(1, "2026-07-01", "-9000"),   # venta
            tx(2, "2026-08-01", "-1000"),   # fondeo de un MCA
            tx(3, "2026-08-02", "640"),     # pagos al MCA en el período
            tx(4, "2026-09-28", "360"),     # apuesta
        ]
        labels = {"1": (None, True), "2": ("active_advance", True),
                  "3": ("active_advance", True), "4": ("hr_gambling", False)}

        f = features(txns, labels)

        self.assertEqual(f["revenue_share"], Decimal("0.9"))
        self.assertEqual(f["high_risk_share"], Decimal("0.36"))
        self.assertEqual(f["monthly_revenue"], Decimal("3000"))
        self.assertEqual(f["funder_daily"], Decimal("10"))
        self.assertEqual(f["offer"], Decimal("3400"))  # 1.2 * 3000 - 20 * 10

    def test_offer_is_zero_above_five_nsfs(self):
        sale = tx(0, "2026-07-01", "-9000")
        fees = [tx(i, "2026-07-02", "35") for i in range(1, 7)]
        labels = {"0": (None, True), **{str(i): ("nsf", True) for i in range(1, 7)}}

        self.assertEqual(features([sale, *fees], labels)["offer"], 0)
        self.assertGreater(features([sale, *fees[:5]], labels)["offer"], 0)

    def test_offer_is_never_negative(self):
        txns = [tx(1, "2026-07-01", "-300"), tx(2, "2026-07-02", "5000")]
        labels = {"1": (None, True), "2": ("active_advance", True)}

        self.assertEqual(features(txns, labels)["offer"], 0)
