import unittest

from engine import label


class KeywordEngineTest(unittest.TestCase):
    def test_first_matching_group_wins(self):
        self.assertEqual(label("OVERDRAFT PROTECTION XFER FROM SAV 2231"), ("internal_transfer", True))
        self.assertEqual(label("SQUARE CAPITAL DES:LOAN ID:1"), ("revenue_verification", True))

    def test_keyword_with_punctuation_never_matches(self):
        # Defecto heredado a propósito: se limpia la descripción pero no la keyword.
        self.assertEqual(label("CRYPTO.COM DES:PURCHASE"), (None, True))

    def test_personal_keywords_mark_personal(self):
        self.assertEqual(label("ZELLE FROM AMY CHEN ON 07/14 REF # 1"), (None, False))
        self.assertEqual(label("SYSCO CORP DES:PAYMENT"), (None, True))
