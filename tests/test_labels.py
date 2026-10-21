import unittest
from decimal import Decimal

from labels import is_revenue


class RevenueRuleTest(unittest.TestCase):
    def test_only_business_credits_without_excluding_group_are_revenue(self):
        # Plaid: monto negativo = entra plata.
        cases = [
            (Decimal("-100"), None, True, True),
            (Decimal("-100"), "revenue_verification", True, True),
            (Decimal("-100"), "active_advance", True, False),
            (Decimal("-100"), "nsf", True, False),
            (Decimal("-100"), None, False, False),
            (Decimal("100"), None, True, False),
        ]
        for amount, group, business, expected in cases:
            with self.subTest(amount=amount, group=group, business=business):
                self.assertEqual(is_revenue(amount, group, business), expected)
