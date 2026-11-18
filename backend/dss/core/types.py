from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Criterion:
    code: str
    name: str
    unit: str | None
    is_benefit: bool
    order: int


@dataclass
class Alternative:
    id: str
    type: str
    label: str
    values: dict[str, float]
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Excluded:
    id: str
    label: str
    reason: str


@dataclass
class PipelineResult:
    results: list[dict[str, Any]]
    excluded: list[Excluded]
    warnings: list[dict[str, Any]]
