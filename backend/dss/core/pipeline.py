import math
from collections.abc import Callable
from typing import Any

from .topsis import topsis
from .types import Alternative, Criterion, Excluded, PipelineResult


def run_pipeline(
    alternatives: list[Alternative],
    criteria: list[Criterion],
    weights: dict[str, float],
    *,
    prefilter: Callable[[Alternative, dict[str, Any]], str | None],
    group_key: Callable[[Alternative], str | None],
    classify: Callable[[float, dict[str, Any]], str],
    recommend: Callable[[Alternative, float, str, dict[str, Any]], dict[str, Any]],
    params: dict[str, Any],
) -> PipelineResult:
    excluded: list[Excluded] = []
    kept: list[Alternative] = []
    codes = [criterion.code for criterion in sorted(criteria, key=lambda item: item.order)]
    for alternative in alternatives:
        reason = prefilter(alternative, params)
        if reason:
            excluded.append(Excluded(alternative.id, alternative.label, reason))
            continue
        missing = [code for code in codes if code not in alternative.values or not math.isfinite(alternative.values[code])]
        if missing:
            excluded.append(Excluded(alternative.id, alternative.label, f"Nilai kriteria kosong/tidak valid: {', '.join(missing)}"))
            continue
        kept.append(alternative)

    warnings: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    grouped: dict[str | None, list[Alternative]] = {}
    for alternative in kept:
        grouped.setdefault(group_key(alternative), []).append(alternative)

    ordered_criteria = sorted(criteria, key=lambda item: item.order)
    criteria_weights = [weights[item.code] for item in ordered_criteria]
    benefits = [item.is_benefit for item in ordered_criteria]
    for group, group_alternatives in grouped.items():
        if len(group_alternatives) == 1:
            scores = [0.5]
            contributions = [[0.0 for _ in ordered_criteria]]
            warnings.append({"kode": "SINGLE_ALTERNATIVE", "group_key": group, "pesan": "Grup hanya memiliki satu alternatif."})
        else:
            matrix = [[alternative.values[item.code] for item in ordered_criteria] for alternative in group_alternatives]
            scores, contributions = topsis(matrix, criteria_weights, benefits)
        ranked = sorted(zip(group_alternatives, scores, contributions), key=lambda item: (-item[1], item[0].id))
        for rank, (alternative, score, contribution) in enumerate(ranked, start=1):
            status = classify(score, params)
            results.append({
                "id": alternative.id,
                "type": alternative.type,
                "label": alternative.label,
                "group_key": group,
                "ranking": rank,
                "skor": round(score, 4),
                "status": status,
                "input_values": alternative.values,
                "contributions": {item.code: round(contribution[index], 6) for index, item in enumerate(ordered_criteria)},
                "recommendation": recommend(alternative, score, status, params),
                "meta": alternative.meta,
            })
    return PipelineResult(results, excluded, warnings)
