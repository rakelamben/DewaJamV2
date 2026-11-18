from typing import Any

from .core.scenario_helpers import criteria_from, make_promo_alternative, make_restock_alternative, make_supplier_alternative, number, round_recommendation_qty
from .core.types import Alternative, Criterion


class Scenario:
    def __init__(self, code: str, name: str, alternative_type: str, criteria: list[Criterion], params: dict[str, Any], pairwise: dict[tuple[int, int], float]):
        self.code, self.name, self.alternative_type = code, name, alternative_type
        self.criteria, self.default_params, self.default_pairwise = criteria, params, pairwise


RESTOCK = Scenario(
    "RESTOCK", "Prioritas Restock Produk", "product",
    criteria_from([("R1", "Kecepatan jual", "unit/hari", True), ("R2", "Days of cover", "hari", False), ("R3", "Profit periode", "Rp", True), ("R4", "Rasio stok/ROP", "rasio", False), ("R5", "Tren penjualan", "%", True), ("R6", "Modal per unit", "Rp", False)]),
    {"window_days": 30, "target_cover_days": 30, "safety_days": 3, "default_lead_time_days": 7, "days_of_cover_cap": 999, "prefilter_max_stok_rop_ratio": 2.0, "threshold_high": 0.60, "threshold_mid": 0.40},
    {(0, 1): .5, (0, 2): 2, (0, 3): 3, (0, 4): 4, (0, 5): 5, (1, 2): 3, (1, 3): 3, (1, 4): 5, (1, 5): 6, (2, 3): 2, (2, 4): 3, (2, 5): 4, (3, 4): 2, (3, 5): 3, (4, 5): 2},
)
PROMO = Scenario(
    "PROMO", "Strategi Promo Produk", "product",
    criteria_from([("P1", "Days of cover", "hari", True), ("P2", "Umur stok", "hari", True), ("P3", "Modal tertahan", "Rp", True), ("P4", "Ruang margin", "%", True), ("P5", "Tren penjualan", "%", False)]),
    {"window_days": 30, "margin_min_pct": 10, "discount_cap_high": 20, "discount_cap_mid": 10, "days_of_cover_cap": 999, "threshold_high": .60, "threshold_mid": .40},
    {(0, 1): 3, (0, 2): 2, (0, 3): 4, (0, 4): 5, (1, 2): .5, (1, 3): 2, (1, 4): 3, (2, 3): 3, (2, 4): 4, (3, 4): 2},
)
SUPPLIER = Scenario(
    "SUPPLIER", "Evaluasi Supplier", "supplier",
    criteria_from([("S1", "Indeks harga", "rasio", False), ("S2", "Lead time", "hari", False), ("S3", "Fill rate", "%", True), ("S4", "Tingkat cacat", "%", False), ("S5", "Ketepatan waktu", "%", True)]),
    {"window_days": 180, "min_purchases": 3, "threshold_high": .70, "threshold_mid": .40},
    {(0, 1): 4, (0, 2): 2, (0, 3): 1, (0, 4): 3, (1, 2): 1/3, (1, 3): 1/4, (1, 4): .5, (2, 3): .5, (2, 4): 2, (3, 4): 3},
)
SCENARIOS = {item.code: item for item in (RESTOCK, PROMO, SUPPLIER)}


def build_alternative(scenario: Scenario, row: dict[str, Any]) -> Alternative:
    if scenario.code == "RESTOCK": return make_restock_alternative(row)
    if scenario.code == "PROMO": return make_promo_alternative(row)
    return make_supplier_alternative(row)


def prefilter(scenario: Scenario, alternative: Alternative, params: dict[str, Any]) -> str | None:
    row = alternative.meta["row"]
    if row.get("_excluded_reason"):
        return str(row["_excluded_reason"])
    if scenario.code == "RESTOCK":
        if row.get("harga_beli") is None: return "harga beli tidak ada"
        reorder = number(row.get("reorder_point"))
        if reorder <= 0: return "reorder point belum diatur"
        if number(row.get("stok")) > params["prefilter_max_stok_rop_ratio"] * reorder: return "stok masih aman"
    elif scenario.code == "PROMO":
        if number(row.get("stok")) <= 0: return "stok kosong"
        if row.get("harga_beli") is None: return "harga beli tidak ada"
        if number(row.get("harga")) <= 0: return "harga jual tidak valid"
    return None


def classify(scenario: Scenario, score: float, params: dict[str, Any]) -> str:
    if scenario.code == "RESTOCK": return "Restock Segera" if score >= params["threshold_high"] else "Restock Terjadwal" if score >= params["threshold_mid"] else "Tidak Perlu"
    if scenario.code == "PROMO": return "Promo Agresif" if score >= params["threshold_high"] else "Promo Ringan" if score >= params["threshold_mid"] else "Tidak Perlu Promo"
    return "Direkomendasikan" if score >= params["threshold_high"] else "Cadangan" if score >= params["threshold_mid"] else "Tidak Direkomendasikan"


def recommendation(scenario: Scenario, alternative: Alternative, score: float, status: str, params: dict[str, Any]) -> dict[str, Any]:
    row = alternative.meta["row"]
    if scenario.code == "RESTOCK": return round_recommendation_qty(row, score, status, params)
    if scenario.code == "SUPPLIER": return {"produk_tercakup": row.get("product_count", 0), "total_po": row.get("purchase_count", 0), "catatan": "Berdasarkan histori PO dan penerimaan."}
    cap = params["discount_cap_high"] if status == "Promo Agresif" else params["discount_cap_mid"] if status == "Promo Ringan" else 0
    margin = number(alternative.values.get("P4"))
    discount = max(0.0, min(float(cap), margin - params["margin_min_pct"]))
    sale_price = number(row.get("harga"))
    result = {"diskon_pct": round(discount, 2), "harga_setelah_diskon": round(sale_price * (1 - discount / 100), 2)}
    if status != "Tidak Perlu Promo" and discount == 0: result["catatan"] = "Margin tidak cukup untuk diskon."
    return result
