"""Motor de keywords "legacy": imperfecto a propósito, es lo que el reviewer revisa."""
import re

# El orden es la precedencia: gana el primer grupo con alguna keyword presente.
RULES = [
    ("internal_transfer", ["TRANSFER", "XFER"]),
    ("nsf", ["NSF", "RETURNED ITEM"]),
    ("overdraft", ["OVERDRAFT"]),
    ("revenue_verification", ["SQUARE", "SQ *", "TOAST", "STRIPE", "SHOPIFY", "MERCH DEP", "AMERICAN EXPRESS"]),
    ("active_advance", ["CAPITAL", "FUNDING", "ADVANCE", "FORWARD FIN"]),
    ("ucc", ["EQUIP FIN", "UCC"]),
    ("auto_deposit", ["DIRECT DEP", "DIR DEP", "SSA TREAS"]),
    ("not_avg_revenue", ["REFUND", "IRS TREAS", "INTEREST", "REVERSAL", "LOAN"]),
    ("hr_gambling", ["DRAFTKINGS", "FANDUEL", "CASINO"]),
    ("hr_bankruptcy", ["CHAPTER 13", "BANKRUPTCY"]),
    ("hr_debt_settlement", ["DEBT RELIEF", "DEBT SETTLEMENT"]),
    ("hr_garnishment", ["GARNISHMENT", "LEVY"]),
    ("hr_other", ["PAYDAY", "CRYPTO.COM", "PAWN"]),
]
PERSONAL = ["ZELLE", "VENMO", "NETFLIX", "SPOTIFY", "KROGER", "COSTCO"]


def label(description):
    # Se limpia la puntuación de la descripción pero no de las keywords:
    # por eso "SQ *" o "CRYPTO.COM" nunca matchean (el bug que menciona el enunciado).
    text = " ".join(re.sub(r"[^A-Z0-9 ]", " ", description.upper()).split())
    group = next((g for g, words in RULES if any(w in text for w in words)), None)
    return group, not any(w in text for w in PERSONAL)
