"""Features de riesgo, regla de oferta y sensibilidad a errores de etiqueta."""
import random
from datetime import date, timedelta
from decimal import Decimal

from labels import GROUPS, HIGH_RISK, is_revenue


def features(txns, labels):
    """txns de un solo negocio, labels: id -> (grupo, business)."""
    deposits = revenue = debits = high_risk = funder = Decimal(0)
    nsf = overdraft = 0
    for t in txns:
        amount = t["amount"]
        group, business = labels[t["transaction_id"]]
        if amount < 0:
            deposits -= amount
            if is_revenue(amount, group, business):
                revenue -= amount
        else:
            debits += amount
            high_risk += amount if group in HIGH_RISK else 0
            funder += amount if group == "active_advance" else 0
        nsf += group == "nsf"
        overdraft += group == "overdraft"

    first = date.fromisoformat(min(t["date"] for t in txns))
    days = (date.fromisoformat(max(t["date"] for t in txns)) - first).days + 1
    weekdays = sum((first + timedelta(d)).weekday() < 5 for d in range(days))
    monthly_revenue = revenue * 30 / days
    # Los MCA debitan en días hábiles: el pago diario es el total sobre los días hábiles.
    funder_daily = funder / weekdays
    offer = 0 if nsf > 5 else max(Decimal(0), Decimal("1.2") * monthly_revenue - 20 * funder_daily)
    return {
        "revenue_share": revenue / deposits if deposits else Decimal(0),
        "nsf": nsf,
        "overdraft": overdraft,
        "high_risk_share": high_risk / debits if debits else Decimal(0),
        "monthly_revenue": monthly_revenue,
        "funder_daily": funder_daily,
        "offer": offer,
    }


def debit(t, group):
    return t["amount"] > 0 and group is None


# Un error por tipo: (a qué transacciones le puede pasar, cómo queda la etiqueta).
ERROR_TYPES = {
    "sale labeled non-revenue": (
        lambda t, g, b: is_revenue(t["amount"], g, b), lambda g, b: ("not_avg_revenue", b)),
    "non-revenue credit labeled sale": (
        lambda t, g, b: t["amount"] < 0 and not is_revenue(t["amount"], g, b), lambda g, b: (None, True)),
    "funder payment missed": (
        lambda t, g, b: t["amount"] > 0 and g == "active_advance", lambda g, b: (None, b)),
    "ordinary debit labeled funder": (
        lambda t, g, b: debit(t, g), lambda g, b: ("active_advance", b)),
    "NSF missed": (
        lambda t, g, b: g == "nsf", lambda g, b: (None, b)),
    "ordinary debit labeled NSF": (
        lambda t, g, b: debit(t, g), lambda g, b: ("nsf", b)),
    "ordinary debit labeled high risk": (
        lambda t, g, b: debit(t, g), lambda g, b: ("hr_other", b)),
    "ordinary debit labeled UCC": (
        lambda t, g, b: debit(t, g), lambda g, b: ("ucc", b)),
}


def mislabel_sweep(by_business, truth, rate, error_type=None, runs=50, seed=1):
    """Etiqueta mal una fracción `rate` de transacciones y mide cuánto se mueven las features.
    Sin error_type, cambia el grupo por otro al azar; con error_type, aplica solo ese error.
    Devuelve el promedio, sobre corridas y negocios, del cambio absoluto de cada feature."""
    rng = random.Random(seed)
    options = [None, *GROUPS]

    def corrupt(t, lab):
        if error_type is None:
            return (rng.choice([g for g in options if g != lab[0]]), lab[1]) if rng.random() < rate else lab
        applies, wrong = ERROR_TYPES[error_type]
        return wrong(*lab) if applies(t, *lab) and rng.random() < rate else lab

    keys = ["revenue_share", "nsf", "high_risk_share", "offer"]
    total = {k: Decimal(0) for k in [*keys, "offer_signed"]}
    n = 0
    for txns in by_business.values():
        base = features(txns, truth)
        for _ in range(runs):
            f = features(txns, {t["transaction_id"]: corrupt(t, truth[t["transaction_id"]]) for t in txns})
            for k in keys:
                total[k] += abs(f[k] - base[k])
            total["offer_signed"] += f["offer"] - base["offer"]
            n += 1
    return {k: v / n for k, v in total.items()}
