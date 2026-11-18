# Implementation Plan: DSS Multi-Skenario (Dewa Jam)

Dokumen ini ditujukan untuk code agent. Ikuti urutan fase di Bagian 10. Jangan melompat fase.

## 0. Konteks dan batasan

**Proyek:** Dewa Jam, sistem informasi terpadu toko jam (TPS, OAS, KMS, MIS, ISS). Stack: FastAPI + Alembic (backend), React + TypeScript (frontend), Supabase/PostgreSQL, schema `toko_jam`. Arsitektur modular monolith dengan spec per fitur berprefix `iss-`.

**Tujuan:** menambah modul DSS (bagian ISS) dengan tiga skenario dalam satu engine:

| Kode | Skenario | Alternatif |
|---|---|---|
| `RESTOCK` | Prioritas restock produk | produk |
| `PROMO` | Strategi promo/diskon stok lambat | produk |
| `SUPPLIER` | Pemilihan supplier | supplier |

**Metode:** AHP untuk bobot kriteria, TOPSIS untuk ranking.

### Batasan keras (WAJIB dipatuhi)

1. **Dilarang membuat view, function, trigger, stored procedure, atau konfigurasi logika di database.** DB hanya menyimpan tabel data (master, bobot, hasil). Semua perhitungan, ekstraksi input, klasifikasi, dan rekomendasi ditulis di kode Python.
2. Query agregat (GROUP BY, SUM) boleh ditulis di repository (kode), bukan sebagai objek DB.
3. Modul `core/` (AHP, TOPSIS) harus berupa fungsi murni tanpa import DB, FastAPI, atau I/O.
4. Kode adalah sumber kebenaran untuk definisi kriteria. Tabel `iss_dss_criteria` hanya cerminan hasil sinkronisasi idempotent saat startup.
5. Perubahan schema hanya lewat migrasi Alembic.

### Verifikasi sebelum mulai (agent harus cek, jangan berasumsi)

- Baca `structure.md`, `tech.md`, `product.md` di steering, lalu sesuaikan path folder di dokumen ini dengan struktur repo yang sebenarnya. Path di bawah hanya usulan.
- Cek kolom aktual tabel yang direferensikan: `products`, `mis_product_costs`, `mis_stock_movements`, `mis_product_daily_summary`, `workflow_requests`, `personnel`, `internal_capabilities`, `role_capabilities`, `internal_notifications`, `activity_logs`. Jika ada yang berbeda dari DDL di dokumen ini, sesuaikan dan catat deviasinya.
- Cek pola yang sudah ada untuk repository, service, router, auth (`InternalUser`, `/api/auth/me`), dan RBAC lewat capability, lalu ikuti polanya.
- Cek apakah numpy sudah menjadi dependency. Kalau belum, tambahkan.

---

## 1. Ringkasan alur

1. Manajer mengisi perbandingan berpasangan antar kriteria, sistem menghitung bobot dan CR, lalu bobot diaktifkan jika CR ≤ 0,1.
2. Manajer menjalankan skenario (opsional dengan scope kategori).
3. Sistem mengambil data input dari tabel yang ada, menghitung nilai kriteria di kode, lalu menjalankan TOPSIS.
4. Sistem menyimpan hasil (skor, ranking, status, rekomendasi, snapshot input) dan menampilkannya.
5. Manajer menerima atau menolak tiap rekomendasi. Hasil "mendesak" memicu workflow request dan notifikasi.

---

## 2. Perubahan database (Alembic)

Schema: `toko_jam`. Buat tiga revisi berurutan.

### M1: master supplier

```sql
CREATE TABLE toko_jam.suppliers (
  supplier_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  nama varchar NOT NULL UNIQUE,
  kontak varchar,
  alamat text,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE toko_jam.mis_product_costs
  ADD COLUMN supplier_id uuid REFERENCES toko_jam.suppliers(supplier_id);
```

Data migration (di dalam revisi Alembic, pakai Python): ambil `DISTINCT supplier_nama` non-null dari `mis_product_costs`, insert ke `suppliers`, lalu update `mis_product_costs.supplier_id`. Jangan hapus kolom `supplier_nama`.

### M2: data pembelian (prasyarat skenario SUPPLIER)

```sql
CREATE TABLE toko_jam.supplier_purchases (
  purchase_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  no_po varchar NOT NULL UNIQUE,
  supplier_id uuid NOT NULL REFERENCES toko_jam.suppliers(supplier_id),
  tanggal_pesan date NOT NULL,
  tanggal_estimasi_terima date,
  tanggal_terima date,
  status varchar NOT NULL DEFAULT 'dipesan'
    CHECK (status IN ('dipesan','diterima_sebagian','diterima','dibatalkan')),
  workflow_request_id uuid REFERENCES toko_jam.workflow_requests(request_id),
  catatan text,
  created_by uuid REFERENCES toko_jam.personnel(personnel_id),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE toko_jam.supplier_purchase_items (
  item_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  purchase_id uuid NOT NULL REFERENCES toko_jam.supplier_purchases(purchase_id) ON DELETE CASCADE,
  product_id uuid NOT NULL REFERENCES toko_jam.products(product_id),
  qty_pesan int NOT NULL CHECK (qty_pesan > 0),
  qty_terima int NOT NULL DEFAULT 0 CHECK (qty_terima >= 0),
  qty_rusak int NOT NULL DEFAULT 0 CHECK (qty_rusak >= 0),
  qty_retur int NOT NULL DEFAULT 0 CHECK (qty_retur >= 0),
  harga_beli_satuan numeric NOT NULL CHECK (harga_beli_satuan >= 0)
);

ALTER TABLE toko_jam.mis_stock_movements
  ADD COLUMN purchase_id uuid REFERENCES toko_jam.supplier_purchases(purchase_id);

CREATE INDEX ix_purchases_supplier_date ON toko_jam.supplier_purchases (supplier_id, tanggal_pesan);
CREATE INDEX ix_purchase_items_purchase ON toko_jam.supplier_purchase_items (purchase_id);
```

### M3: tabel engine DSS

```sql
CREATE TABLE toko_jam.iss_dss_scenarios (
  scenario_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  kode varchar NOT NULL UNIQUE,
  nama varchar NOT NULL,
  deskripsi text,
  alternative_type varchar NOT NULL CHECK (alternative_type IN ('product','supplier')),
  is_active boolean NOT NULL DEFAULT true
);

CREATE TABLE toko_jam.iss_dss_criteria (
  criteria_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  scenario_id uuid NOT NULL REFERENCES toko_jam.iss_dss_scenarios(scenario_id),
  kode varchar NOT NULL,
  nama varchar NOT NULL,
  satuan varchar,
  is_benefit boolean NOT NULL,
  urutan int NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  UNIQUE (scenario_id, kode)
);

CREATE TABLE toko_jam.iss_dss_weight_sets (
  weight_set_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  scenario_id uuid NOT NULL REFERENCES toko_jam.iss_dss_scenarios(scenario_id),
  nama varchar NOT NULL,
  lambda_max double precision,
  ci double precision,
  cr double precision NOT NULL,
  status varchar NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','active','archived')),
  created_by uuid REFERENCES toko_jam.personnel(personnel_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  activated_at timestamptz
);
CREATE UNIQUE INDEX uq_dss_active_weight
  ON toko_jam.iss_dss_weight_sets (scenario_id) WHERE status = 'active';

CREATE TABLE toko_jam.iss_dss_pairwise (
  weight_set_id uuid NOT NULL REFERENCES toko_jam.iss_dss_weight_sets(weight_set_id) ON DELETE CASCADE,
  criteria_1 uuid NOT NULL REFERENCES toko_jam.iss_dss_criteria(criteria_id),
  criteria_2 uuid NOT NULL REFERENCES toko_jam.iss_dss_criteria(criteria_id),
  nilai double precision NOT NULL CHECK (nilai > 0),
  PRIMARY KEY (weight_set_id, criteria_1, criteria_2)
);

CREATE TABLE toko_jam.iss_dss_weights (
  weight_set_id uuid NOT NULL REFERENCES toko_jam.iss_dss_weight_sets(weight_set_id) ON DELETE CASCADE,
  criteria_id uuid NOT NULL REFERENCES toko_jam.iss_dss_criteria(criteria_id),
  bobot double precision NOT NULL,
  PRIMARY KEY (weight_set_id, criteria_id)
);

CREATE TABLE toko_jam.iss_dss_runs (
  run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  scenario_id uuid NOT NULL REFERENCES toko_jam.iss_dss_scenarios(scenario_id),
  weight_set_id uuid NOT NULL REFERENCES toko_jam.iss_dss_weight_sets(weight_set_id),
  scope jsonb NOT NULL DEFAULT '{}',
  params jsonb NOT NULL,
  warnings jsonb NOT NULL DEFAULT '[]',
  excluded jsonb NOT NULL DEFAULT '[]',
  workflow_request_id uuid REFERENCES toko_jam.workflow_requests(request_id),
  run_by uuid REFERENCES toko_jam.personnel(personnel_id),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_dss_runs_scenario ON toko_jam.iss_dss_runs (scenario_id, created_at DESC);

CREATE TABLE toko_jam.iss_dss_results (
  result_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id uuid NOT NULL REFERENCES toko_jam.iss_dss_runs(run_id) ON DELETE CASCADE,
  product_id uuid REFERENCES toko_jam.products(product_id),
  supplier_id uuid REFERENCES toko_jam.suppliers(supplier_id),
  group_key varchar,                          -- kategori produk; NULL untuk SUPPLIER
  skor double precision NOT NULL,
  ranking int NOT NULL,                       -- ranking di dalam group_key
  status varchar NOT NULL,
  input_values jsonb NOT NULL,                -- nilai mentah per kriteria
  contributions jsonb NOT NULL,               -- v_ij per kriteria
  recommendation jsonb NOT NULL DEFAULT '{}',
  decision varchar NOT NULL DEFAULT 'pending' CHECK (decision IN ('pending','accepted','rejected')),
  decision_by uuid REFERENCES toko_jam.personnel(personnel_id),
  decision_note text,
  decided_at timestamptz,
  CHECK ((product_id IS NOT NULL) <> (supplier_id IS NOT NULL))
);
CREATE INDEX ix_dss_results_run ON toko_jam.iss_dss_results (run_id, group_key, ranking);
```

### Seed data (lewat kode, bukan SQL migrasi)

- Capability baru di `internal_capabilities` (module `iss`): `dss.view`, `dss.run`, `dss.weights.manage`, `dss.decide`. Petakan di `role_capabilities`: manager mendapat semuanya, staf gudang mendapat `dss.view` dan `dss.run` untuk RESTOCK dan PROMO (sesuaikan dengan pola RBAC yang ada).
- Skenario, kriteria, dan weight set default dibuat oleh sinkronisasi registry (Bagian 4) dan seeder bobot default (Bagian 3).

---

## 3. Definisi skenario

Konvensi: **benefit** berarti makin besar nilai, makin diprioritaskan. **cost** berarti makin kecil nilai, makin diprioritaskan.

Notasi jendela waktu: `W` = `window_days`, 30 hari terakhir adalah `(hari_ini − 30, hari_ini]`, periode sebelumnya `(hari_ini − 60, hari_ini − 30]`.

### 3.1 RESTOCK (alternatif: produk)

TOPSIS dijalankan **per kategori** (`products.kategori`), supaya produk murah dan produk luxury tidak berada di skala yang sama.

| Kode | Nama | Rumus | Jenis | Bobot default |
|---|---|---|---|---|
| R1 | Kecepatan jual (unit/hari) | Σ `qty_terjual` 30 hari ÷ 30 | benefit | 0,2524 |
| R2 | Days of cover (hari) | `stok` ÷ R1; jika R1 = 0 maka `days_of_cover_cap` | cost | 0,3664 |
| R3 | Profit 30 hari (Rp) | Σ `profit` 30 hari | benefit | 0,1628 |
| R4 | Rasio stok terhadap reorder point | `stok` ÷ `reorder_point`; jika reorder_point = 0 maka dikeluarkan dari alternatif | cost | 0,1089 |
| R5 | Tren penjualan (%) | (qty30 − qty_prev) ÷ qty_prev × 100; jika qty_prev = 0 maka 0 | benefit | 0,0658 |
| R6 | Modal per unit (Rp) | `harga_beli` berlaku dari `mis_product_costs` | cost | 0,0436 |

Pairwise default (baris vs kolom, urutan R1..R6): R1/R2 = 1/2, R1/R3 = 2, R1/R4 = 3, R1/R5 = 4, R1/R6 = 5, R2/R3 = 3, R2/R4 = 3, R2/R5 = 5, R2/R6 = 6, R3/R4 = 2, R3/R5 = 3, R3/R6 = 4, R4/R5 = 2, R4/R6 = 3, R5/R6 = 2. CR yang diharapkan ≈ 0,0204.

**Parameter default:** `window_days=30`, `target_cover_days=30`, `safety_days=3`, `default_lead_time_days=7`, `days_of_cover_cap=999`, `prefilter_max_stok_rop_ratio=2.0`, `threshold_high=0.60`, `threshold_mid=0.40`.

**Prefilter:** produk dengan `stok > 2 × reorder_point` dikeluarkan (alasan: "stok masih aman"). Produk tanpa `harga_beli` atau tanpa `reorder_point` (0 atau null) juga dikeluarkan dengan alasan tercatat.

**Status:** skor ≥ 0,60 → `Restock Segera`; 0,40 ≤ skor < 0,60 → `Restock Terjadwal`; selain itu `Tidak Perlu`.

**Rekomendasi:** `qty = max(0, ceil(R1 × (lead_time + target_cover_days + safety_days) − stok))`. `lead_time` diambil dari metrik S2 supplier produk itu (supplier dari `mis_product_costs.supplier_id` aktif). Jika tidak tersedia, pakai `default_lead_time_days`. Simpan `{"qty_pesan": n, "lead_time_dipakai": x, "sumber_lead_time": "supplier|default", "supplier_id": ...}`.

### 3.2 PROMO (alternatif: produk dengan `stok > 0`)

Juga per kategori.

| Kode | Nama | Rumus | Jenis | Bobot default |
|---|---|---|---|---|
| P1 | Days of cover (hari) | sama seperti R2 | benefit | 0,4162 |
| P2 | Umur stok (hari) | hari sejak `mis_stock_movements.created_at` terbaru bertipe `purchase_in`; fallback `products.created_at` | benefit | 0,1611 |
| P3 | Modal tertahan (Rp) | `stok` × `harga_beli` | benefit | 0,2618 |
| P4 | Ruang margin (%) | (`harga` − `harga_beli`) ÷ `harga` × 100 | benefit | 0,0986 |
| P5 | Tren penjualan (%) | sama seperti R5 | **cost** | 0,0624 |

Pairwise default (baris vs kolom): P1/P2 = 3, P1/P3 = 2, P1/P4 = 4, P1/P5 = 5, P2/P3 = 1/2, P2/P4 = 2, P2/P5 = 3, P3/P4 = 3, P3/P5 = 4, P4/P5 = 2. CR yang diharapkan ≈ 0,0153.

**Parameter default:** `window_days=30`, `margin_min_pct=10`, `discount_cap_high=20`, `discount_cap_mid=10`, `days_of_cover_cap=999`, `threshold_high=0.60`, `threshold_mid=0.40`.

**Prefilter:** keluarkan produk tanpa `harga_beli` atau dengan `harga ≤ 0`.

**Status:** skor ≥ 0,60 → `Promo Agresif`; 0,40 ≤ skor < 0,60 → `Promo Ringan`; selain itu `Tidak Perlu Promo`.

**Rekomendasi diskon:** `cap = discount_cap_high` (Agresif) atau `discount_cap_mid` (Ringan) atau 0; `diskon_pct = max(0, min(cap, margin_pct − margin_min_pct))`. Jika `diskon_pct = 0` padahal status bukan "Tidak Perlu Promo", tambahkan catatan "margin tidak cukup untuk diskon". Simpan juga `harga_setelah_diskon`.

### 3.3 SUPPLIER (alternatif: supplier)

Tanpa group (`group_key = null`). `scope.kategori` opsional: hanya hitung item produk dari kategori itu.

| Kode | Nama | Rumus | Jenis | Bobot default |
|---|---|---|---|---|
| S1 | Indeks harga | rata-rata berbobot qty dari (`harga_beli_satuan` ÷ median harga produk itu lintas supplier dalam jendela) | cost | 0,3186 |
| S2 | Lead time (hari) | rata-rata (`tanggal_terima` − `tanggal_pesan`) untuk PO diterima | cost | 0,0687 |
| S3 | Fill rate (%) | Σ`qty_terima` ÷ Σ`qty_pesan` × 100 | benefit | 0,1841 |
| S4 | Tingkat cacat (%) | (Σ`qty_rusak` + Σ`qty_retur`) ÷ Σ`qty_terima` × 100 | cost | 0,3186 |
| S5 | Ketepatan waktu (%) | % PO dengan `tanggal_terima ≤ tanggal_estimasi_terima` (hanya PO yang punya estimasi) | benefit | 0,1100 |

Pairwise default (baris vs kolom): S1/S2 = 4, S1/S3 = 2, S1/S4 = 1, S1/S5 = 3, S2/S3 = 1/3, S2/S4 = 1/4, S2/S5 = 1/2, S3/S4 = 1/2, S3/S5 = 2, S4/S5 = 3. CR yang diharapkan ≈ 0,0081.

**Parameter default:** `window_days=180`, `min_purchases=3`, `threshold_high=0.70`, `threshold_mid=0.40`.

**Prefilter:** supplier `is_active = true` dengan PO berstatus `diterima` atau `diterima_sebagian` dalam jendela ≥ `min_purchases`. Sisanya masuk `excluded` dengan alasan "data PO kurang (n < min_purchases)". Kriteria S5 diisi dari PO yang punya estimasi, jika tidak ada satupun maka supplier dikeluarkan dengan alasan "tidak ada PO dengan estimasi".

**Status:** skor ≥ 0,70 → `Direkomendasikan`; 0,40 ≤ skor < 0,70 → `Cadangan`; selain itu `Tidak Direkomendasikan`.

**Rekomendasi:** `{"produk_tercakup": n, "total_po": n, "catatan": ...}`.

---

## 4. Arsitektur kode (usulan, sesuaikan dengan struktur repo)

```
backend/app/modules/iss/dss/
  core/
    types.py          # CriterionDef, AlternativeInput, Excluded, ScenarioRunResult
    ahp.py            # build_matrix, compute_weights, consistency
    topsis.py         # normalize, weighted, ideals, distances, scores
    pipeline.py       # orkestrasi (tanpa I/O): matriks -> skor -> klasifikasi
  scenarios/
    base.py           # Protocol ScenarioDefinition
    restock.py
    promo.py
    supplier.py
    registry.py       # daftar skenario + sync idempotent ke tabel
  repositories/
    inputs_repo.py    # query agregat untuk input skenario
    weights_repo.py
    runs_repo.py
  services/
    weight_service.py
    run_service.py
    decision_service.py
  routers/
    dss_router.py
  schemas/
    dss_schemas.py
  tests/
```

### Kontrak skenario

```python
from typing import Protocol, Literal

class ScenarioDefinition(Protocol):
    kode: str                                   # "RESTOCK" | "PROMO" | "SUPPLIER"
    alternative_type: Literal["product", "supplier"]
    criteria: list[CriterionDef]                # kode, nama, satuan, is_benefit, urutan
    default_params: dict
    default_pairwise: dict[tuple[str, str], float]

    async def load_inputs(self, repo, scope: dict, params: dict) -> list[AlternativeInput]: ...
    def prefilter(self, alts: list[AlternativeInput], params: dict) -> tuple[list[AlternativeInput], list[Excluded]]: ...
    def group_key(self, alt: AlternativeInput) -> str | None: ...     # kategori atau None
    def classify(self, skor: float, params: dict) -> str: ...
    def recommend(self, alt: AlternativeInput, skor: float, status: str, params: dict) -> dict: ...
```

`AlternativeInput` minimal berisi: `id`, `type` (`product`/`supplier`), `label`, `values: dict[kode_kriteria, float]`, `meta: dict`.

### Registry dan sinkronisasi

Saat startup (atau lewat command terpisah), `registry.sync()`:
1. Upsert `iss_dss_scenarios` berdasarkan `kode`.
2. Upsert `iss_dss_criteria` berdasarkan `(scenario_id, kode)`. Kriteria yang tidak ada lagi di kode ditandai `is_active = false`, tidak dihapus.
3. Jika skenario belum punya weight set `active`, buat satu dari `default_pairwise` (hitung AHP lewat `core/ahp.py`, status `active`, nama "Default").
Sinkronisasi harus idempotent: menjalankannya dua kali tidak mengubah apa pun.

---

## 5. Pengambilan data input (inputs_repo)

Semua query ditulis sebagai kode di repository. Kembalikan data agregat, jangan seluruh baris harian.

### RESTOCK dan PROMO

1. **Produk:** `product_id, nama_barang, kategori, brand, harga, stok, minimum_stok, reorder_point, created_at` dari `products` (filter `kategori` jika ada di scope).
2. **Penjualan:** dari `mis_product_daily_summary`, per `product_id`: `SUM(qty_terjual)` dan `SUM(profit)` untuk jendela 30 hari terakhir, plus `SUM(qty_terjual)` untuk jendela 30 hari sebelumnya.
3. **Modal berlaku:** dari `mis_product_costs`, satu baris per produk dengan `berlaku_dari <= hari_ini` dan (`berlaku_sampai IS NULL` atau `berlaku_sampai >= hari_ini`), ambil `berlaku_dari` terbaru. Sertakan `supplier_id`.
4. **PROMO saja:** per produk, `MAX(created_at)` dari `mis_stock_movements` dengan `tipe_mutasi = 'purchase_in'`.
5. **RESTOCK saja:** metrik lead time per supplier (dari Bagian SUPPLIER, S2), dipakai untuk rekomendasi qty.
6. **Kesegaran data:** `MAX(generated_at)` dari `mis_product_daily_summary`. Jika lebih dari 1 hari dari sekarang, tambahkan warning `{"kode": "MIS_STALE", "pesan": "..."}` ke run. Jangan blokir.

### SUPPLIER

1. Supplier aktif dari `suppliers`.
2. PO beserta item dalam `window_days` dengan status `diterima` atau `diterima_sebagian` (join `supplier_purchases` dan `supplier_purchase_items`), plus info produk (`product_id`, `kategori` untuk filter scope).
3. Median harga per produk (lintas supplier, dalam jendela) dihitung di kode Python dari data di atas, bukan di SQL.

---

## 6. Algoritma (modul `core/`)

### 6.1 AHP (`ahp.py`)

```python
RI = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}

def build_matrix(pairs: dict[tuple[int, int], float], n: int) -> np.ndarray:
    # pairs hanya berisi i<j; isi A[i][j]=v dan A[j][i]=1/v; diagonal 1.
    # validasi: semua pasangan i<j harus ada, nilai > 0 (disarankan dalam [1/9, 9]).

def compute_weights(A: np.ndarray) -> np.ndarray:
    # normalisasi tiap kolom (bagi jumlah kolom), bobot = rata-rata baris.

def consistency(A, w) -> tuple[float, float, float]:
    # lambda_max = mean((A @ w) / w); CI = (lambda_max - n) / (n - 1)
    # CR = CI / RI[n]; jika n <= 2 maka CR = 0.
```

Aturan: weight set hanya boleh diaktifkan jika `CR ≤ 0,1`. Bobot harus berjumlah 1 (toleransi 1e-9).

### 6.2 TOPSIS (`topsis.py`)

Input: matriks `X` (n alternatif × m kriteria), `w` (m), `is_benefit` (m, bool).

```python
def topsis(X, w, is_benefit):
    norm = np.sqrt((X ** 2).sum(axis=0))
    R = np.divide(X, norm, out=np.zeros_like(X, dtype=float), where=norm != 0)   # kolom nol -> 0
    V = R * w
    ideal_pos = np.where(is_benefit, V.max(axis=0), V.min(axis=0))
    ideal_neg = np.where(is_benefit, V.min(axis=0), V.max(axis=0))
    d_pos = np.sqrt(((V - ideal_pos) ** 2).sum(axis=1))
    d_neg = np.sqrt(((V - ideal_neg) ** 2).sum(axis=1))
    denom = d_pos + d_neg
    score = np.where(denom == 0, 0.5, d_neg / np.where(denom == 0, 1, denom))
    return score, V
```

Aturan:
- Minimal 2 alternatif per grup. Jika grup hanya punya 1 alternatif, beri skor 0,5, status mengikuti klasifikasi, dan catat warning "grup kategori X hanya 1 alternatif".
- Gunakan float64. Pembulatan hanya di lapisan output (4 desimal).
- Ranking: skor menurun, tie-break dengan id agar stabil.

### 6.3 Pipeline (`pipeline.py`, tanpa I/O)

```
run_pipeline(scenario, alternatives, weights, params):
  1. prefilter -> (kept, excluded)
  2. kelompokkan kept berdasarkan scenario.group_key
  3. per grup: bentuk X sesuai urutan kriteria aktif, panggil topsis(), hitung ranking
  4. per alternatif: status = classify(), recommendation = recommend()
  5. kembalikan hasil, excluded, warnings
```

### 6.4 Penanganan data bermasalah

| Kasus | Perlakuan |
|---|---|
| Nilai kriteria NaN/None | Alternatif dikeluarkan dengan alasan menyebut kriteria yang kosong |
| Pembagi nol (R1 = 0, qty_prev = 0, dst.) | Gunakan aturan per kriteria di Bagian 3 |
| Seluruh alternatif identik | Skor 0,5 semua |
| Kolom konstan | Setelah normalisasi vektor kolom itu tidak membedakan alternatif, tidak perlu penanganan khusus selain norma ≠ 0 |
| Weight set tidak lengkap | Tolak run dengan error 422 |
| `CR > 0,1` | Tolak aktivasi dengan error 422 yang menyertakan nilai CR |

---

## 7. API dan output

Semua endpoint di bawah prefix `/api/dss`, dilindungi capability.

| Method | Path | Capability | Fungsi |
|---|---|---|---|
| GET | `/scenarios` | `dss.view` | Daftar skenario, kriteria, parameter default, bobot aktif |
| POST | `/scenarios/{kode}/weights` | `dss.weights.manage` | Body: pairwise segitiga atas. Hitung AHP, simpan `draft`, kembalikan bobot, λmax, CI, CR |
| GET | `/scenarios/{kode}/weights` | `dss.view` | Daftar weight set |
| POST | `/weights/{id}/activate` | `dss.weights.manage` | Aktifkan jika CR ≤ 0,1. Set lama menjadi `archived` dalam satu transaksi |
| POST | `/scenarios/{kode}/runs` | `dss.run` | Body: `scope`, `weight_set_id?`, `params?` (override), `persist` (default true) |
| GET | `/scenarios/{kode}/runs` | `dss.view` | Riwayat run |
| GET | `/runs/{id}` | `dss.view` | Hasil lengkap |
| POST | `/results/{id}/decision` | `dss.decide` | Body: `decision` (`accepted`/`rejected`), `note` |

`persist = false` menjalankan perhitungan dan mengembalikan hasil tanpa menulis ke DB (untuk simulasi what-if).

### Bentuk respons run

```json
{
  "run_id": "uuid",
  "scenario": "PROMO",
  "weight_set": {"id": "uuid", "cr": 0.0153},
  "scope": {"kategori": null},
  "params": {"margin_min_pct": 10},
  "warnings": [],
  "excluded": [{"id": "uuid", "label": "…", "alasan": "harga beli tidak ada"}],
  "groups": [{
    "group_key": "Jam Tangan Luxury",
    "results": [{
      "result_id": "uuid",
      "ranking": 1,
      "alternative": {"id": "uuid", "label": "…"},
      "skor": 0.8724,
      "status": "Promo Agresif",
      "input_values": {"P1": 40, "P2": 150, "P3": 190000000, "P4": 18, "P5": 0},
      "contributions": {"P1": 0.21, "P3": 0.33},
      "recommendation": {"diskon_pct": 8, "catatan": "dibatasi margin minimum 10%"},
      "decision": "pending"
    }]
  }]
}
```

### Integrasi sistem yang ada

- Setiap run (persist = true) menulis `activity_logs` (`action = 'create'`, `table_name = 'iss_dss_runs'`). Aktivasi bobot juga dicatat.
- Run RESTOCK dengan minimal satu hasil `Restock Segera` membuat satu `workflow_requests` (`tipe_request = 'dss_restock'`, `reference_table = 'iss_dss_runs'`, `reference_id = run_id`) dan mengisi `iss_dss_runs.workflow_request_id`. Buat juga `internal_notifications` dengan `dedupe_key = 'dss:restock:{run_id}'`, `target_role = 'manager'`, `severity = 'warning'`.
- Hindari duplikasi: jika `dedupe_key` sudah ada, lewati pembuatan notifikasi.

---

## 8. Frontend (React + TypeScript)

Ikuti design system yang ada (DESIGN2.md, komponen shadcn/Kokonut UI) dan routing role-based (area manager di prefix `/management`).

Halaman dan komponen:
1. **DSS Overview:** kartu per skenario (bobot aktif, run terakhir, tombol Jalankan).
2. **Halaman Bobot:** matriks perbandingan berpasangan dengan input skala 1–9 dan kebalikannya, indikator CR real-time (hijau jika ≤ 0,1), tombol Simpan Draft dan Aktifkan (nonaktif jika CR > 0,1).
3. **Halaman Run per skenario:** filter scope (kategori), pengaturan parameter (override), tombol Jalankan dan Simulasi (`persist=false`).
4. **Hasil:** tabel per grup (ranking, label, skor, status badge, rekomendasi), bar chart skor, panel detail (input mentah dan kontribusi per kriteria) dan tombol Terima/Tolak dengan catatan. Tampilkan `warnings` dan daftar `excluded` beserta alasannya.
5. **Input PO sederhana** (untuk SUPPLIER): form buat PO, catat penerimaan (`qty_terima`, `qty_rusak`, `qty_retur`, `tanggal_terima`). Tanpa ini skenario SUPPLIER tidak punya data.

---

## 9. Parameter dan konfigurasi

Parameter default berada di kode (`default_params` tiap skenario). Override per run lewat body request, lalu disimpan sebagai snapshot di `iss_dss_runs.params` (termasuk bobot yang dipakai). Jangan membuat tabel parameter.

---

## 10. Rencana kerja per fase

Kerjakan berurutan. Tiap fase punya spec Kiro sendiri (folder spec berprefix `iss-`).

### Fase 0: `iss-dss-foundation`
- [ ] Verifikasi item di Bagian 0.
- [ ] Revisi Alembic M1, M2, M3 sesuai Bagian 2 (termasuk data migration supplier).
- [ ] Seeder capability `dss.*` dan mapping role.
- [ ] Kerangka folder modul DSS dan `registry.sync()` (idempotent).
- **Selesai jika:** `alembic upgrade head` dan `alembic downgrade -1` berjalan bersih. Sync dua kali tidak membuat duplikat. Tabel `suppliers` terisi dari `supplier_nama` yang ada.

### Fase 1: `iss-dss-core`
- [ ] `core/ahp.py`, `core/topsis.py`, `core/pipeline.py`, `core/types.py`.
- [ ] Unit test dengan golden fixture Bagian 11 dan kasus tepi Bagian 6.4.
- **Selesai jika:** semua test core lulus tanpa koneksi DB. Tidak ada import DB/FastAPI di `core/`.

### Fase 2: `iss-dss-weights`
- [ ] `weights_repo`, `weight_service`, endpoint bobot (buat draft, daftar, aktifkan).
- [ ] Seeder weight set default dari `default_pairwise` tiap skenario.
- [ ] Halaman Bobot di frontend.
- **Selesai jika:** aktivasi ditolak saat CR > 0,1. Hanya satu weight set `active` per skenario (diuji, termasuk lewat partial unique index).

### Fase 3: `iss-dss-restock`
- [ ] `scenarios/restock.py`, query di `inputs_repo`, `run_service`, `runs_repo`, endpoint run dan decision.
- [ ] UI hasil dan keputusan.
- [ ] Integrasi workflow, notifikasi, activity log.
- **Selesai jika:** run RESTOCK end-to-end menghasilkan ranking per kategori dengan rekomendasi qty. Keputusan manajer tersimpan. `persist=false` tidak menulis ke DB.

### Fase 4: `iss-dss-promo`
- [ ] `scenarios/promo.py` dan query tambahan (`purchase_in` terakhir).
- [ ] Pakai ulang pipeline, service, dan UI dari Fase 3.
- **Selesai jika:** diskon rekomendasi tidak pernah membuat margin di bawah `margin_min_pct`.

### Fase 5: `iss-dss-supplier`
- [ ] CRUD `suppliers`, form PO dan penerimaan barang (Bagian 8 poin 5). Pastikan penerimaan barang juga membuat mutasi `purchase_in` dengan `purchase_id`.
- [ ] `scenarios/supplier.py` (S1–S5, median harga di kode).
- [ ] Hubungkan metrik S2 ke rekomendasi qty RESTOCK.
- **Selesai jika:** supplier dengan data PO kurang muncul di `excluded` dengan alasan. Skenario berjalan di data uji.

### Fase 6: `iss-dss-integration`
- [ ] Polesan notifikasi dan workflow, riwayat run, dan export (CSV) hasil.
- [ ] Dokumentasi singkat penggunaan di KMS (opsional).

---

## 11. Pengujian (golden fixtures)

Gunakan fixture ini di pytest. Toleransi: `abs(diff) < 5e-4` untuk skor dan bobot.

### 11.1 RESTOCK

Urutan kriteria R1..R6. R2 dihitung dari `stok ÷ R1`. Benefit flags: `[1, 0, 1, 0, 1, 0]`.

| Produk | R1 velocity | stok | R3 profit (juta) | R4 stok/ROP | R5 tren % | R6 modal (juta) |
|---|---|---|---|---|---|---|
| A | 0,90 | 6 | 13,5 | 0,60 | 18 | 1,4 |
| B | 0,50 | 12 | 9,0 | 1,20 | 5 | 2,6 |
| C | 0,70 | 5 | 11,2 | 0,83 | 25 | 3,8 |
| D | 0,30 | 9 | 7,5 | 1,50 | −4 | 5,2 |
| E | 2,00 | 20 | 3,0 | 1,60 | 10 | 0,04 |
| F | 0,05 | 2 | 22,0 | 1,00 | 0 | 95,0 |

- Bobot: `[0.2524, 0.3664, 0.1628, 0.1089, 0.0658, 0.0436]`
- `λmax ≈ 6.1264`, `CI ≈ 0.0253`, `CR ≈ 0.0204` (RI n=6 = 1,24)
- Skor: `[0.6640, 0.3756, 0.6141, 0.2476, 0.7160, 0.2539]`
- Ranking: `[2, 4, 3, 6, 1, 5]`

### 11.2 PROMO

Urutan P1..P5, benefit flags `[1, 1, 1, 1, 0]`. Matriks langsung (P1 cover, P2 umur, P3 modal juta, P4 margin %, P5 tren %):

| Produk | P1 | P2 | P3 | P4 | P5 |
|---|---|---|---|---|---|
| A | 30 | 120 | 46,8 | 22 | −4 |
| B | 24 | 95 | 31,2 | 30 | 5 |
| C | 40 | 150 | 190 | 18 | 0 |
| D | 7,14 | 40 | 19 | 15 | 25 |
| E | 10 | 60 | 0,8 | 55 | 10 |

- Bobot: `[0.4162, 0.1611, 0.2618, 0.0986, 0.0624]`
- `λmax ≈ 5.0683`, `CI ≈ 0.0171`, `CR ≈ 0.0153` (RI n=5 = 1,12)
- Skor: `[0.4876, 0.3699, 0.8724, 0.0641, 0.1712]`
- Ranking: `[2, 3, 1, 5, 4]`
- Rekomendasi diskon (margin_min 10, cap 20/10): produk C (Promo Agresif, margin 18) → 8%. Produk A (Promo Ringan, margin 22) → 10%.

### 11.3 SUPPLIER

Urutan S1..S5, benefit flags `[0, 0, 1, 0, 1]`:

| Supplier | S1 indeks harga | S2 lead time | S3 fill rate | S4 cacat | S5 on-time |
|---|---|---|---|---|---|
| A | 0,97 | 5 | 96 | 1,2 | 92 |
| B | 1,05 | 3 | 99 | 0,5 | 97 |
| C | 0,92 | 9 | 88 | 3,0 | 78 |
| D | 1,00 | 6 | 93 | 1,0 | 85 |

- Bobot: `[0.3186, 0.0687, 0.1841, 0.3186, 0.1100]`
- `λmax ≈ 5.0365`, `CI ≈ 0.0091`, `CR ≈ 0.0081`
- Skor: `[0.7180, 0.9183, 0.0817, 0.7826]`
- Ranking: `[3, 1, 4, 2]`
- Status (ambang 0,70 / 0,40): A Direkomendasikan, B Direkomendasikan, C Tidak Direkomendasikan, D Direkomendasikan.

### 11.4 Kasus tepi yang wajib diuji

- Satu alternatif dalam grup, semua alternatif identik, kolom konstan.
- Matriks AHP dengan CR > 0,1: aktivasi ditolak (422).
- Aktivasi weight set baru mengarsipkan yang lama, hanya satu `active` tersisa.
- Produk tanpa `harga_beli`, tanpa `reorder_point`, atau R1 = 0: perilaku sesuai Bagian 3.
- Supplier dengan PO < `min_purchases`: masuk `excluded`.
- `persist = false`: tidak ada baris baru di `iss_dss_runs` dan `iss_dss_results`.
- Idempotensi `registry.sync()` dan `dedupe_key` notifikasi.

---

## 12. Definition of Done

- Semua migrasi maju dan mundur tanpa error, tidak ada view, function, atau trigger baru di DB.
- Semua test golden dan kasus tepi lulus.
- Tiga skenario bisa dijalankan dari UI oleh role yang berhak, hasil tersimpan dan bisa diaudit lewat `input_values`.
- Kriteria dan parameter terdokumentasi di kode (docstring tiap skenario).
- Lint (ESLint, Prettier, PEP/ruff sesuai tech.md) bersih.

## 13. Di luar cakupan (jangan dikerjakan)

- Kinerja staf dan RFM pelanggan (kandidat skenario berikutnya).
- Agregasi bobot dari banyak responden (geometric mean). Bisa jadi ekstensi setelah Fase 6.
- Optimasi pemesanan otomatis (EOQ) dan pembuatan PO otomatis dari hasil DSS.
