# Los 13 grupos del enunciado. La clave es el id que usan el código y el modelo;
# el texto es mi lectura de cada grupo y va tal cual al prompt.
GROUPS = {
    "not_avg_revenue": "Not average monthly revenue: one-off business credits that are not sales "
                       "(loan or SBA proceeds, tax refunds, refunds, reversals, owner capital, interest)",
    "revenue_verification": "Revenue verification: sales settlements from card processors and marketplaces",
    "nsf": "NSFs: insufficient-funds fees and payments returned for insufficient funds",
    "overdraft": "Overdraft: overdraft fees and charges",
    "internal_transfer": "Internal transfer: money moved between the business's own accounts",
    "ucc": "UCC: payments to lenders secured by a lien (equipment and vehicle finance)",
    "active_advance": "Active advance: merchant cash advance funders, both the funding deposit "
                      "and the fixed daily or weekly payments",
    "auto_deposit": "Auto deposit: recurring automatic deposits of personal income (paychecks, benefits)",
    "hr_gambling": "High risk - gambling",
    "hr_bankruptcy": "High risk - bankruptcy (trustee payments)",
    "hr_debt_settlement": "High risk - debt settlement payments",
    "hr_garnishment": "High risk - garnishment (tax levies, wage or court garnishments)",
    "hr_other": "High risk - other (payday lenders, earned-wage apps, crypto exchanges, pawn shops)",
}
HIGH_RISK = {g for g in GROUPS if g.startswith("hr_")}


def is_revenue(amount, group, business):
    # Plaid: amount < 0 es plata que entra. Todo grupo excluye salvo revenue_verification.
    return amount < 0 and business and group in (None, "revenue_verification")
