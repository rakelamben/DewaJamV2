def clamp_cf(value: float, minimum: float = -1.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, float(value)))


def premise_cf(clauses_cf: list[float]) -> float:
    if not clauses_cf:
        return 0.0
    return clamp_cf(min(float(item) for item in clauses_cf), 0.0, 1.0)


def rule_cf(cf_expert: float, cf_premise: float) -> float:
    return round(clamp_cf(cf_expert) * clamp_cf(cf_premise, 0.0, 1.0), 6)


def combine_cf(cf1: float, cf2: float) -> float:
    first = clamp_cf(cf1)
    second = clamp_cf(cf2)
    if first > 0 and second > 0:
        combined = first + second * (1.0 - first)
    elif first < 0 and second < 0:
        combined = first + second * (1.0 + first)
    else:
        denom = 1.0 - min(abs(first), abs(second))
        combined = 0.0 if denom <= 1e-9 else (first + second) / denom
    return round(clamp_cf(combined), 6)


def classify_confidence(cf: float) -> str:
    if cf >= 0.80:
        return "Sangat Yakin"
    if cf >= 0.60:
        return "Yakin"
    if cf >= 0.40:
        return "Cukup Yakin"
    return "Indikasi Awal"
