from typing import Any


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def match_products_for_conclusion(
    recommendation: dict[str, Any],
    products: list[dict[str, Any]],
    *,
    working_facts: dict[str, Any] | None = None,
    main_product: dict[str, Any] | None = None,
    limit: int = 6,
) -> list[dict[str, Any]]:
    facts = working_facts or {}
    product_filter = recommendation.get("product_filter")
    if not isinstance(product_filter, dict):
        return []

    target_categories = set(product_filter.get("categories") or [])
    preferred_movements = {str(item).lower() for item in (product_filter.get("movements") or [])}
    preferred_straps = {str(item).lower() for item in (product_filter.get("strap_materials") or [])}
    min_water_atm = _num(product_filter.get("min_water_atm"), 0.0)
    match_lug = bool(product_filter.get("match_lug_width"))

    budget_tier = str(facts.get("C_BUDGET_TIER") or "")
    max_price = _num(product_filter.get("max_price"), 0.0)
    if budget_tier == "ekonomis_lt_2jt":
        max_price = 2_000_000.0
    elif budget_tier == "menengah_2jt_5jt":
        max_price = 5_000_000.0

    main_id = str(main_product.get("product_id")) if main_product else None
    main_specs = (main_product or {}).get("specs") or {}
    if not isinstance(main_specs, dict):
        main_specs = {}
    target_lug_width = _num(main_specs.get("lug_width_mm") or facts.get("P_LUG_WIDTH"), 20.0)

    scored: list[tuple[float, dict[str, Any]]] = []
    for product in products:
        if int(product.get("stok") or 0) <= 0:
            continue
        if main_id and str(product.get("product_id")) == main_id:
            continue

        category = str(product.get("kategori") or "")
        price = _num(product.get("harga"), 0.0)
        specs = product.get("specs") if isinstance(product.get("specs"), dict) else {}
        tags = {str(tag).lower() for tag in (product.get("tags") or [])}

        if target_categories and category not in target_categories:
            continue

        score = 10.0
        reasons: list[str] = []

        if max_price > 0:
            if price <= max_price:
                score += 4.0
                reasons.append("Sesuai rentang anggaran")
            else:
                score -= 3.0

        movement = str(specs.get("movement") or "").lower()
        if preferred_movements:
            if movement in preferred_movements or (preferred_movements & tags):
                score += 4.0
                reasons.append(f"Mesin {movement or 'sesuai preferensi'}")

        strap = str(specs.get("strap_material") or "").lower()
        if preferred_straps:
            if strap in preferred_straps or (preferred_straps & tags):
                score += 3.5
                reasons.append(f"Material {strap or 'kompatibel'}")

        water_atm = _num(specs.get("water_resistance_atm"), 3.0)
        if min_water_atm > 0 and water_atm >= min_water_atm:
            score += 3.0
            reasons.append(f"Water resistance {int(water_atm)} ATM")

        if match_lug:
            prod_lug = _num(specs.get("lug_width_mm"), 20.0)
            if abs(prod_lug - target_lug_width) < 0.5:
                score += 5.0
                reasons.append(f"Ukuran lug pas ({int(prod_lug)} mm)")
            else:
                score -= 2.0

        if not reasons:
            reasons.append(f"Tersedia di kategori {category}")

        scored.append(
            (
                score,
                {
                    "product_id": product.get("product_id"),
                    "nama_barang": product.get("nama_barang"),
                    "kategori": category,
                    "brand": product.get("brand"),
                    "harga": price,
                    "stok": int(product.get("stok") or 0),
                    "gambar_url": product.get("gambar_url"),
                    "specs": specs,
                    "alasan_kecocokan": ", ".join(reasons),
                },
            )
        )

    scored.sort(key=lambda item: (-item[0], item[1].get("harga") or 0))
    return [item[1] for item in scored[:limit]]
