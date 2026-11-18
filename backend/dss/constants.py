SCENARIO_CODES = {"RESTOCK", "PROMO", "SUPPLIER"}
ROLE_SCENARIO_ACCESS = {
    "admin": SCENARIO_CODES,
    "manager": SCENARIO_CODES,
    "staf_gudang": {"RESTOCK", "PROMO"},
}
