from dataclasses import dataclass, field
from typing import Any, Literal

FactSource = Literal["user_input", "db_derived", "inferred"]
FactValueType = Literal["enum", "number", "boolean", "text"]
ConclusionKind = Literal["intermediate_fact", "final_conclusion"]


@dataclass(frozen=True)
class FactSpec:
    code: str
    name: str
    value_type: FactValueType
    source: FactSource
    question: str | None = None
    options: list[dict[str, str]] = field(default_factory=list)
    order: int = 0
    is_required: bool = True


@dataclass(frozen=True)
class RuleClause:
    fact: str
    op: str
    value: Any


@dataclass(frozen=True)
class ExpertRuleSpec:
    code: str
    name: str
    conditions: list[RuleClause]
    conclusion_kind: ConclusionKind
    conclusion_code: str
    conclusion_title: str
    explanation: str
    recommendation: dict[str, Any] = field(default_factory=dict)
    cf_expert: float = 0.8
    priority: int = 10
    conclusion_value: Any = None
    knowledge_source_table: str | None = None
    knowledge_source_id: str | None = None


@dataclass
class FiredRuleTrace:
    rule_code: str
    rule_name: str
    conclusion_kind: ConclusionKind
    conclusion_code: str
    cf_expert: float
    cf_premise: float
    cf_rule: float
    explanation: str
    matched_facts: dict[str, Any]


@dataclass
class ConclusionResult:
    ranking: int
    conclusion_code: str
    conclusion_title: str
    cf_combined: float
    confidence_level: str
    diagnosis_summary: str
    recommendation: dict[str, Any]
    matched_rules: list[dict[str, Any]]
    matched_products: list[dict[str, Any]] = field(default_factory=list)
    knowledge_refs: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class InferenceOutput:
    inferred_facts: dict[str, Any]
    inferred_cfs: dict[str, float]
    intermediate_traces: list[dict[str, Any]]
    results: list[ConclusionResult]
    warnings: list[dict[str, str]]
