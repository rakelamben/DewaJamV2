from datetime import date, datetime, timezone
from math import ceil
from statistics import median
from typing import Any

from .types import Alternative, Criterion


def parse_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()


def number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def velocity(row: dict[str, Any]) -> float:
    return number(row.get("qty30")) / max(1, int(row.get("window_days", 30)))


def trend(row: dict[str, Any]) -> float:
    current = number(row.get("qty30"))
    previous = number(row.get("qty_prev"))
    return 0.0 if previous == 0 else (current - previous) / previous * 100


def criteria_from(values: list[tuple[str, str, str | None, bool]]) -> list[Criterion]:
    return [Criterion(code, name, unit, benefit, index) for index, (code, name, unit, benefit) in enumerate(values)]


def cost_value(row: dict[str, Any]) -> float:
    return number(row.get("harga_beli"), 0)


def make_restock_alternative(row: dict[str, Any]) -> Alternative:
    sales_velocity = velocity(row)
    stock = number(row.get("stok"))
    reorder = number(row.get("reorder_point"))
    cover = number(row.get("days_of_cover_cap"), 999) if sales_velocity == 0 else stock / sales_velocity
    return Alternative(
        id=str(row["product_id"]), type="product", label=str(row.get("nama_barang") or row["product_id"]),
        values={"R1": sales_velocity, "R2": cover, "R3": number(row.get("profit30")), "R4": stock / reorder if reorder else 0, "R5": trend(row), "R6": cost_value(row)},
        meta={"row": row, "category": row.get("kategori")},
    )


def make_promo_alternative(row: dict[str, Any]) -> Alternative:
    sales_velocity = velocity(row)
    stock = number(row.get("stok"))
    cost = cost_value(row)
    sale_price = number(row.get("harga"))
    cover = number(row.get("days_of_cover_cap"), 999) if sales_velocity == 0 else stock / sales_velocity
    margin = (sale_price - cost) / sale_price * 100 if sale_price else 0
    age = max(0, (date.today() - (parse_date(row.get("last_purchase_in")) or parse_date(row.get("created_at")) or date.today())).days)
    return Alternative(
        id=str(row["product_id"]), type="product", label=str(row.get("nama_barang") or row["product_id"]),
        values={"P1": cover, "P2": float(age), "P3": stock * cost, "P4": margin, "P5": trend(row)},
        meta={"row": row, "category": row.get("kategori")},
    )


def make_supplier_alternative(row: dict[str, Any]) -> Alternative:
    return Alternative(
        id=str(row["supplier_id"]), type="supplier", label=str(row.get("nama") or row["supplier_id"]),
        values={"S1": number(row.get("price_index"), 1), "S2": number(row.get("lead_time")), "S3": number(row.get("fill_rate")), "S4": number(row.get("defect_rate")), "S5": number(row.get("on_time_rate"))},
        meta={"row": row},
    )


def round_recommendation_qty(row: dict[str, Any], score: float, status: str, params: dict[str, Any]) -> dict[str, Any]:
    velocity_value = number(row.get("qty30")) / max(1, int(params["window_days"]))
    lead_time = row.get("lead_time")
    source = "supplier" if lead_time is not None else "default"
    lead_time_value = number(lead_time, number(params["default_lead_time_days"]))
    qty = max(0, ceil(velocity_value * (lead_time_value + params["target_cover_days"] + params["safety_days"]) - number(row.get("stok"))))
    return {"qty_pesan": qty, "lead_time_dipakai": lead_time_value, "sumber_lead_time": source, "supplier_id": row.get("supplier_id")}
