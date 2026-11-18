from typing import Any, Literal

from pydantic import BaseModel, Field


class ConsultBody(BaseModel):
    reference_id: str | None = None
    user_facts: dict[str, Any] = Field(default_factory=dict)
    facts: dict[str, Any] = Field(default_factory=dict)
    user_cfs: dict[str, float] = Field(default_factory=dict)
    cf_inputs: dict[str, float] = Field(default_factory=dict)
    persist: bool = True
    create_workflow_action: bool = False
    create_workflow: bool = False


class RuleConditionInput(BaseModel):
    fact: str
    op: Literal[
        "eq", "neq", "gt", "gte", "lt", "lte", "in", "not_in", "contains",
        "==", "!=", ">", ">=", "<", "<="
    ]
    value: Any
    weight: float = 1.0


class RuleCreateBody(BaseModel):
    kode: str = Field(min_length=2, max_length=60)
    nama: str = Field(min_length=3, max_length=200)
    kondisi: list[RuleConditionInput] = Field(min_length=1)
    jenis_konklusi: Literal["intermediate_fact", "final_conclusion"] = "final_conclusion"
    kesimpulan_kode: str = Field(min_length=2, max_length=100)
    kesimpulan_nilai: str | None = None
    kesimpulan_judul: str = Field(min_length=3, max_length=255)
    penjelasan: str = Field(min_length=5)
    rekomendasi: dict[str, Any] = Field(default_factory=dict)
    cf_pakar: float = Field(default=0.8, ge=-1.0, le=1.0)
    prioritas: int = Field(default=10, ge=1, le=999)
    knowledge_source_table: str | None = None
    knowledge_source_id: str | None = None
    status: Literal["draft", "active", "archived"] = "active"


class RuleUpdateBody(BaseModel):
    nama: str | None = Field(default=None, min_length=3, max_length=200)
    kondisi: list[RuleConditionInput] | None = None
    jenis_konklusi: Literal["intermediate_fact", "final_conclusion"] | None = None
    kesimpulan_kode: str | None = None
    kesimpulan_nilai: str | None = None
    kesimpulan_judul: str | None = Field(default=None, min_length=3, max_length=255)
    penjelasan: str | None = Field(default=None, min_length=5)
    rekomendasi: dict[str, Any] | None = None
    cf_pakar: float | None = Field(default=None, ge=-1.0, le=1.0)
    prioritas: int | None = Field(default=None, ge=1, le=999)
    knowledge_source_table: str | None = None
    knowledge_source_id: str | None = None
    status: Literal["draft", "active", "archived"] | None = None


class DecisionBody(BaseModel):
    decision: Literal["accepted", "rejected"]
    note: str | None = Field(default=None, max_length=1000)
