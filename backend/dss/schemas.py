from typing import Any, Literal

from pydantic import BaseModel, Field


class PairwiseBody(BaseModel):
    pairs: dict[str, float]
    nama: str = Field(default="Custom", min_length=1, max_length=120)


class RunBody(BaseModel):
    scope: dict[str, Any] = Field(default_factory=dict)
    params: dict[str, Any] = Field(default_factory=dict)
    weight_set_id: str | None = None
    persist: bool = True


class DecisionBody(BaseModel):
    decision: Literal["accepted", "rejected"]
    note: str | None = Field(default=None, max_length=1000)


class SupplierBody(BaseModel):
    nama: str = Field(min_length=1, max_length=255)
    kontak: str | None = None
    alamat: str | None = None
    is_active: bool = True


class PurchaseItemBody(BaseModel):
    product_id: str
    qty_pesan: int = Field(gt=0)
    harga_beli_satuan: float = Field(ge=0)


class PurchaseBody(BaseModel):
    no_po: str = Field(min_length=1, max_length=100)
    supplier_id: str
    tanggal_pesan: str
    tanggal_estimasi_terima: str | None = None
    catatan: str | None = None
    items: list[PurchaseItemBody] = Field(min_length=1)


class ReceiveItemBody(BaseModel):
    item_id: str
    qty_terima: int = Field(ge=0)
    qty_rusak: int = Field(default=0, ge=0)
    qty_retur: int = Field(default=0, ge=0)


class ReceivePurchaseBody(BaseModel):
    tanggal_terima: str
    items: list[ReceiveItemBody] = Field(min_length=1)
