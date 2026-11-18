from dataclasses import asdict
from typing import Any

from .certainty_factor import clamp_cf, classify_confidence, combine_cf, premise_cf, rule_cf
from .types import ConclusionResult, ExpertRuleSpec, FiredRuleTrace, InferenceOutput, RuleClause

MAX_CHAIN_PASSES = 10


def _to_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def evaluate_clause(clause: RuleClause, facts: dict[str, Any]) -> bool:
    if clause.fact not in facts:
        return False
    actual = facts[clause.fact]
    if actual is None:
        return False
    op_map = {
        "==": "eq",
        "!=": "neq",
        ">=": "gte",
        "<=": "lte",
        ">": "gt",
        "<": "lt",
    }
    op = op_map.get(clause.op.strip().lower(), clause.op.strip().lower())
    target = clause.value

    if op == "eq":
        num_a, num_t = _to_number(actual), _to_number(target)
        if num_a is not None and num_t is not None:
            return abs(num_a - num_t) < 1e-9
        return str(actual).strip().lower() == str(target).strip().lower()

    if op == "neq":
        return not evaluate_clause(RuleClause(clause.fact, "eq", target), facts)

    if op in {"gt", "gte", "lt", "lte"}:
        num_a, num_t = _to_number(actual), _to_number(target)
        if num_a is None or num_t is None:
            return False
        if op == "gt":
            return num_a > num_t
        if op == "gte":
            return num_a >= num_t
        if op == "lt":
            return num_a < num_t
        return num_a <= num_t

    if op == "in":
        items = target if isinstance(target, (list, tuple, set)) else [item.strip() for item in str(target).split(",")]
        normalized = {str(item).strip().lower() for item in items}
        return str(actual).strip().lower() in normalized

    if op == "not_in":
        return not evaluate_clause(RuleClause(clause.fact, "in", target), facts)

    if op == "contains":
        if isinstance(actual, (list, tuple, set)):
            normalized = {str(item).strip().lower() for item in actual}
            return str(target).strip().lower() in normalized
        return str(target).strip().lower() in str(actual).strip().lower()

    return False


def run_inference(
    rules: list[ExpertRuleSpec],
    *,
    user_facts: dict[str, Any],
    user_cfs: dict[str, float] | None = None,
    db_facts: dict[str, Any] | None = None,
) -> InferenceOutput:
    db_values = dict(db_facts or {})
    user_values = {key: value for key, value in (user_facts or {}).items() if value is not None and value != ""}
    working_facts: dict[str, Any] = {**db_values, **user_values}

    working_cfs: dict[str, float] = {key: 1.0 for key in db_values}
    raw_user_cfs = user_cfs or {}
    for key in user_values:
        working_cfs[key] = clamp_cf(raw_user_cfs.get(key, 1.0), 0.0, 1.0)

    ordered_rules = sorted(rules, key=lambda item: (item.priority, item.code))
    intermediate_rules = [rule for rule in ordered_rules if rule.conclusion_kind == "intermediate_fact"]
    final_rules = [rule for rule in ordered_rules if rule.conclusion_kind == "final_conclusion"]

    inferred_facts: dict[str, Any] = {}
    inferred_cfs: dict[str, float] = {}
    intermediate_traces: list[dict[str, Any]] = []
    fired_intermediate: set[str] = set()

    for _ in range(MAX_CHAIN_PASSES):
        progressed = False
        for rule in intermediate_rules:
            if rule.code in fired_intermediate or not rule.conditions:
                continue
            if all(evaluate_clause(clause, working_facts) for clause in rule.conditions):
                clause_cfs = [working_cfs.get(clause.fact, 1.0) for clause in rule.conditions]
                cf_p = premise_cf(clause_cfs)
                if cf_p <= 0:
                    continue
                cf_r = rule_cf(rule.cf_expert, cf_p)
                fact_code = rule.conclusion_code
                fact_val = rule.conclusion_value if rule.conclusion_value is not None else rule.conclusion_title
                working_facts[fact_code] = fact_val
                inferred_facts[fact_code] = fact_val
                if fact_code in inferred_cfs:
                    inferred_cfs[fact_code] = combine_cf(inferred_cfs[fact_code], cf_r)
                else:
                    inferred_cfs[fact_code] = cf_r
                working_cfs[fact_code] = inferred_cfs[fact_code]
                fired_intermediate.add(rule.code)
                progressed = True
                trace = FiredRuleTrace(
                    rule_code=rule.code,
                    rule_name=rule.name,
                    conclusion_kind="intermediate_fact",
                    conclusion_code=fact_code,
                    cf_expert=rule.cf_expert,
                    cf_premise=cf_p,
                    cf_rule=cf_r,
                    explanation=rule.explanation,
                    matched_facts={clause.fact: working_facts.get(clause.fact) for clause in rule.conditions},
                )
                intermediate_traces.append(asdict(trace))
        if not progressed:
            break

    grouped_conclusions: dict[str, dict[str, Any]] = {}
    for rule in final_rules:
        if not rule.conditions:
            continue
        if not all(evaluate_clause(clause, working_facts) for clause in rule.conditions):
            continue
        clause_cfs = [working_cfs.get(clause.fact, 1.0) for clause in rule.conditions]
        cf_p = premise_cf(clause_cfs)
        if cf_p <= 0:
            continue
        cf_r = rule_cf(rule.cf_expert, cf_p)
        trace = FiredRuleTrace(
            rule_code=rule.code,
            rule_name=rule.name,
            conclusion_kind="final_conclusion",
            conclusion_code=rule.conclusion_code,
            cf_expert=rule.cf_expert,
            cf_premise=cf_p,
            cf_rule=cf_r,
            explanation=rule.explanation,
            matched_facts={clause.fact: working_facts.get(clause.fact) for clause in rule.conditions},
        )
        bucket = grouped_conclusions.get(rule.conclusion_code)
        if not bucket:
            grouped_conclusions[rule.conclusion_code] = {
                "conclusion_code": rule.conclusion_code,
                "conclusion_title": rule.conclusion_title,
                "cf_combined": cf_r,
                "explanations": [rule.explanation],
                "recommendation": dict(rule.recommendation or {}),
                "matched_rules": [asdict(trace)],
            }
        else:
            bucket["cf_combined"] = combine_cf(bucket["cf_combined"], cf_r)
            if rule.explanation not in bucket["explanations"]:
                bucket["explanations"].append(rule.explanation)
            bucket["recommendation"] = {**bucket["recommendation"], **(rule.recommendation or {})}
            bucket["matched_rules"].append(asdict(trace))

    sorted_items = sorted(
        grouped_conclusions.values(),
        key=lambda item: (-float(item["cf_combined"]), str(item["conclusion_code"])),
    )

    results: list[ConclusionResult] = []
    for index, item in enumerate(sorted_items, start=1):
        cf_val = round(float(item["cf_combined"]), 4)
        results.append(
            ConclusionResult(
                ranking=index,
                conclusion_code=item["conclusion_code"],
                conclusion_title=item["conclusion_title"],
                cf_combined=cf_val,
                confidence_level=classify_confidence(cf_val),
                diagnosis_summary=" ".join(item["explanations"]),
                recommendation=item["recommendation"],
                matched_rules=item["matched_rules"],
            )
        )

    warnings: list[dict[str, str]] = []
    if not results:
        warnings.append(
            {
                "kode": "NO_RULE_FIRED",
                "code": "NO_RULE_FIRED",
                "pesan": "Belum ada aturan pakar yang terpenuhi secara spesifik dari kombinasi fakta yang dimasukkan.",
                "message": "Belum ada aturan pakar yang terpenuhi secara spesifik dari kombinasi fakta yang dimasukkan.",
            }
        )

    return InferenceOutput(
        inferred_facts=inferred_facts,
        inferred_cfs=inferred_cfs,
        intermediate_traces=intermediate_traces,
        results=results,
        warnings=warnings,
    )
