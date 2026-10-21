import unittest

from generate import generate
from labels import GROUPS


class GenerateTest(unittest.TestCase):
    def test_data_is_reproducible_and_covers_every_group(self):
        data, truth = generate()

        self.assertEqual((data, truth), generate())
        self.assertEqual(len(data["accounts"]), 10)
        self.assertTrue(1800 <= len(data["transactions"]) <= 2500)
        self.assertEqual(set(truth), {t["transaction_id"] for t in data["transactions"]})
        self.assertLessEqual(set(GROUPS), {t["group"] for t in truth.values()})
