# Implementation Plan DSS — Dewa Jam

## 1. Tujuan

Menambahkan modul Decision Support System (DSS) ke proyek Dewa Jam untuk membantu pengambilan keputusan dalam tiga skenario:

| Kode | Skenario | Alternatif |
|---|---|---|
| `RESTOCK` | Prioritas pengadaan ulang produk | Produk |
| `PROMO` | Prioritas promo untuk stok lambat | Produk |
| `SUPPLIER` | Evaluasi dan pemilihan supplier | Supplier |

Metode yang digunakan:

- AHP untuk menghitung bobot kriteria.
- TOPSIS untuk menghitung skor dan ranking alternatif.

## 2. Batasan implementasi

Implementasi harus menyesuaikan proyek yang tersedia saat ini.

### Tidak menambahkan tech stack baru

Tidak menambahkan:

- Alembic atau migration framework lain.
- NumPy atau library kalkulasi baru.
- ORM atau database driver baru.
- Queue, scheduler, atau service terpisah.
- Library frontend baru.

Komponen yang digunakan:

- Backend: FastAPI yang sudah tersedia.
- Akses database: Supabase REST menggunakan `httpx` yang sudah tersedia.
- Frontend: React, TypeScript, React Router, dan komponen UI yang sudah tersedia.
- Perhitungan: Python standard library (`math`, `statistics`, `datetime`, `json`).

### Batasan database

Database hanya menyimpan data dan hasil. Dilarang membuat:

- View.
- Function.
- Trigger.
- Stored procedure.
- Perhitungan AHP/TOPSIS.
- Klasifikasi atau rekomendasi di database.

SQL pada bagian database hanya berisi tabel, kolom, foreign key, check constraint, dan index.

SQL dijalankan manual oleh pemilik akses database. Proyek tidak membuat sistem migrasi otomatis.

## 3. Kondisi proyek saat ini

Struktur backend saat ini masih minimal:

```text
backend/
  main.py
  auth.py
  config.py
```

Auth internal yang sudah tersedia:

- `InternalUser`.
- `get_current_internal_user`.
- Endpoint `/api/auth/me`.
- Role `admin`, `manager`, `staf_gudang`, dan `staf_operasional`.

Database yang sudah tersedia dan dapat digunakan DSS:

- `products`.
- `mis_product_costs`.
- `mis_stock_movements`.
- `mis_product_daily_summary`.
- `personnel`.
- `workflow_requests`.
- `internal_capabilities`.
- `role_capabilities`.
- `internal_notifications`.
- `activity_logs`.

Struktur existing yang sudah memenuhi kebutuhan DSS:

- `products.minimum_stok` dan `products.reorder_point` sudah tersedia.
- `internal_notifications.dedupe_key`, `severity`, dan `target_role` sudah tersedia.
- `mis_stock_movements.workflow_request_id` sudah tersedia.

Struktur yang masih perlu ditambahkan melalui SQL:

- Tabel `suppliers`.
- Tabel `supplier_purchases`.
- Tabel `supplier_purchase_items`.
- Kolom `mis_product_costs.supplier_id`.
- Kolom `mis_stock_movements.purchase_id`.
- Tabel `iss_dss_*`.

## 4. Struktur kode DSS yang direncanakan

Struktur berikut ditambahkan tanpa mengubah tech stack:

```text
backend/
  dss/
    __init__.py
    core/
      __init__.py
      types.py
      ahp.py
      topsis.py
      pipeline.py
    scenarios/
      __init__.py
      base.py
      registry.py
      restock.py
      promo.py
      supplier.py
    repositories/
      __init__.py
      database.py
      inputs.py
      weights.py
      runs.py
      suppliers.py
    services/
      __init__.py
      weights.py
      runs.py
      decisions.py
    schemas.py
    routes.py
```

Repository menggunakan request HTTP ke Supabase REST dengan pola yang sudah dipakai di `auth.py`.

## 5. Model data DSS

### 5.1 Supplier

`suppliers` menyimpan master supplier. Data lama dari `mis_product_costs.supplier_nama` tidak dipindahkan melalui function atau trigger database. Backfill dilakukan satu kali melalui backend atau SQL manual setelah tabel tersedia, dan kolom `supplier_nama` tetap dipertahankan untuk kompatibilitas.

### 5.2 Pembelian supplier

`supplier_purchases` dan `supplier_purchase_items` menyimpan PO serta penerimaan barang. Data ini menjadi sumber perhitungan skenario `SUPPLIER` dan lead time untuk rekomendasi `RESTOCK`.

### 5.3 Skenario dan kriteria

`iss_dss_scenarios` dan `iss_dss_criteria` menyimpan metadata skenario. Definisi sebenarnya tetap berada di kode Python pada registry.

### 5.4 Bobot

`iss_dss_weight_sets` menyimpan versi bobot. `iss_dss_pairwise` menyimpan input perbandingan berpasangan dan `iss_dss_weights` menyimpan bobot hasil AHP.

Aktivasi weight set hanya boleh dilakukan backend jika `CR <= 0.1`. Partial unique index memastikan maksimal satu weight set berstatus `active` per skenario.

### 5.5 Run dan hasil

`iss_dss_runs` menyimpan parameter, scope, warning, dan daftar data yang dikeluarkan. `iss_dss_results` menyimpan ranking, skor, input mentah, kontribusi, rekomendasi, dan keputusan manajer.

## 6. Definisi skenario

### 6.1 RESTOCK

Kriteria:

| Kode | Kriteria | Jenis |
|---|---|---|
| R1 | Kecepatan jual | Benefit |
| R2 | Days of cover | Cost |
| R3 | Profit periode berjalan | Benefit |
| R4 | Rasio stok terhadap reorder point | Cost |
| R5 | Tren penjualan | Benefit |
| R6 | Modal per unit | Cost |

Perhitungan dilakukan di Python. Produk dikeluarkan jika:

- Harga beli tidak tersedia.
- `reorder_point` kosong atau nol.
- Stok masih lebih besar dari batas prefilter.
- Nilai kriteria tidak valid.

Produk dikelompokkan berdasarkan `products.kategori`.

Status:

- Skor `>= 0.60`: `Restock Segera`.
- Skor `>= 0.40`: `Restock Terjadwal`.
- Selain itu: `Tidak Perlu`.

### 6.2 PROMO

Kriteria:

| Kode | Kriteria | Jenis |
|---|---|---|
| P1 | Days of cover | Benefit |
| P2 | Umur stok | Benefit |
| P3 | Modal tertahan | Benefit |
| P4 | Ruang margin | Benefit |
| P5 | Tren penjualan | Cost |

Hanya produk dengan stok lebih besar dari nol yang diproses. Produk tanpa harga jual positif atau harga beli dikeluarkan.

Status:

- Skor `>= 0.60`: `Promo Agresif`.
- Skor `>= 0.40`: `Promo Ringan`.
- Selain itu: `Tidak Perlu Promo`.

Diskon dihitung backend dan tidak boleh menurunkan margin di bawah `margin_min_pct`.

### 6.3 SUPPLIER

Kriteria:

| Kode | Kriteria | Jenis |
|---|---|---|
| S1 | Indeks harga | Cost |
| S2 | Lead time | Cost |
| S3 | Fill rate | Benefit |
| S4 | Tingkat cacat | Cost |
| S5 | Ketepatan waktu | Benefit |

Supplier aktif dengan jumlah PO kurang dari `min_purchases` masuk ke `excluded`. Median harga produk dihitung menggunakan Python, bukan SQL.

Status:

- Skor `>= 0.70`: `Direkomendasikan`.
- Skor `>= 0.40`: `Cadangan`.
- Selain itu: `Tidak Direkomendasikan`.

## 7. Core AHP dan TOPSIS

### 7.1 AHP

Implementasikan dengan list dan operasi numerik standard library:

1. Bentuk matriks perbandingan.
2. Isi diagonal dengan `1`.
3. Isi nilai kebalikan untuk pasangan simetris.
4. Normalisasi setiap kolom.
5. Hitung rata-rata setiap baris sebagai bobot.
6. Hitung `lambda_max`, `CI`, dan `CR`.

Weight set tidak dapat diaktifkan jika `CR > 0.1`.

### 7.2 TOPSIS

1. Validasi setiap nilai input.
2. Normalisasi matriks dengan akar jumlah kuadrat setiap kolom.
3. Kalikan matriks normalisasi dengan bobot.
4. Tentukan solusi ideal positif dan negatif berdasarkan benefit/cost.
5. Hitung jarak ke solusi ideal.
6. Hitung skor preferensi.
7. Urutkan skor menurun dengan ID sebagai tie-breaker.

Jika hanya ada satu alternatif dalam grup, skor ditetapkan `0.5` dan warning dicatat. Jika semua alternatif identik, semua skor juga `0.5`.

## 8. Endpoint backend

Tambahkan router DSS ke `backend/main.py`.

```text
GET  /api/dss/scenarios
POST /api/dss/scenarios/{kode}/weights
GET  /api/dss/scenarios/{kode}/weights
POST /api/dss/weights/{id}/activate
POST /api/dss/scenarios/{kode}/runs
GET  /api/dss/scenarios/{kode}/runs
GET  /api/dss/runs/{id}
POST /api/dss/results/{id}/decision
```

Hak akses menggunakan capability yang sudah tersedia pada schema:

| Capability | Admin | Manager | Staf gudang | Staf operasional |
|---|---:|---:|---:|---:|
| `dss.view` | Ya | Ya | Ya | Tidak |
| `dss.run` | Ya | Ya | Ya | Tidak |
| `dss.weights.manage` | Ya | Ya | Tidak | Tidak |
| `dss.decide` | Ya | Ya | Tidak | Tidak |

Capability di-seed ke `internal_capabilities`, lalu dipetakan ke `role_capabilities`. Pembatasan skenario untuk staf gudang dilakukan pada service berdasarkan role dan kode skenario.

## 9. Integrasi sistem existing

### Activity log

Run dan keputusan dicatat ke `activity_logs` melalui backend.

### Workflow restock

Jika run `RESTOCK` memiliki hasil `Restock Segera`, backend membuat satu row di `workflow_requests` dan menyimpan `workflow_request_id` pada run.

### Notification

Gunakan `internal_notifications` karena tabel tersebut sudah menyediakan `dedupe_key`, `severity`, dan `target_role`:

```text
type = 'dss_restock'
reference_table = 'iss_dss_runs'
reference_id = run_id
target_role = 'manager'
severity = 'warning'
dedupe_key = 'dss:restock:{run_id}'
```

Tidak perlu menambahkan tabel atau kolom notification baru.

## 10. Frontend

Tambahkan route:

```text
/internal/dss
/internal/dss/weights
/internal/dss/restock
/internal/dss/promo
/internal/dss/supplier
```

Halaman yang dibuat:

1. Overview DSS.
2. Form bobot AHP.
3. Halaman run RESTOCK.
4. Halaman run PROMO.
5. Halaman run SUPPLIER.
6. Tabel hasil dan ranking.
7. Detail input dan kontribusi.
8. Form keputusan terima/tolak.
9. Form supplier dan PO.

Semua komponen menggunakan UI yang sudah tersedia dalam proyek.

## 11. Urutan implementasi

### Tahap 1 — Database manual

- Jalankan SQL bertanda `DSS SQL SECTION` pada `docs/schema.sql`.
- Jangan menambahkan ulang kolom `products.minimum_stok` atau `products.reorder_point` karena sudah tersedia.
- Pastikan seluruh foreign key mengarah ke tabel existing terbaru.
- Seed capability `dss.view`, `dss.run`, `dss.weights.manage`, dan `dss.decide`.
- Isi data supplier lama secara manual jika diperlukan.

### Tahap 2 — Core

- Implementasikan `types.py`.
- Implementasikan AHP.
- Implementasikan TOPSIS.
- Implementasikan pipeline tanpa akses database.

### Tahap 3 — Registry

- Tambahkan definisi RESTOCK.
- Tambahkan definisi PROMO.
- Tambahkan definisi SUPPLIER.
- Tambahkan sinkronisasi metadata melalui endpoint/backend.

### Tahap 4 — Repository dan service

- Tambahkan akses Supabase REST.
- Tambahkan repository input.
- Tambahkan repository bobot.
- Tambahkan repository run dan result.
- Tambahkan service keputusan.

### Tahap 5 — API

- Tambahkan router DSS.
- Tambahkan validasi input Pydantic yang sudah tersedia.
- Tambahkan role guard menggunakan `InternalUser`.

### Tahap 6 — Frontend

- Tambahkan halaman DSS.
- Tambahkan form bobot.
- Tambahkan tabel hasil.
- Tambahkan fitur keputusan.

### Tahap 7 — Pengujian

Uji minimal:

- Bobot AHP.
- CR lebih dari `0.1`.
- TOPSIS benefit dan cost.
- Alternatif tunggal.
- Nilai identik.
- Kolom konstan.
- Produk tanpa harga beli.
- Produk tanpa reorder point.
- Supplier dengan PO kurang.
- `persist=false` tidak menulis data.
- Diskon tidak melanggar margin minimum.
- Deduplikasi workflow dan notification.

## 12. Simulasi input-output

Contoh input PROMO:

```json
{
  "scope": {"kategori": "Luxury"},
  "params": {
    "margin_min_pct": 10,
    "threshold_high": 0.6,
    "threshold_mid": 0.4
  },
  "persist": false
}
```

Input alternatif yang sudah dihitung backend:

```json
[
  {"id": "A", "P1": 30, "P2": 120, "P3": 46.8, "P4": 22, "P5": -4},
  {"id": "B", "P1": 24, "P2": 95, "P3": 31.2, "P4": 30, "P5": 5},
  {"id": "C", "P1": 40, "P2": 150, "P3": 190, "P4": 18, "P5": 0}
]
```

Bobot:

```json
{"P1": 0.4162, "P2": 0.1611, "P3": 0.2618, "P4": 0.0986, "P5": 0.0624}
```

Output:

```json
{
  "scenario": "PROMO",
  "persisted": false,
  "results": [
    {
      "id": "C",
      "ranking": 1,
      "score": 0.8724,
      "status": "Promo Agresif",
      "recommendation": {
        "diskon_pct": 8,
        "catatan": "margin minimum tetap terpenuhi"
      }
    },
    {
      "id": "A",
      "ranking": 2,
      "score": 0.4876,
      "status": "Promo Ringan",
      "recommendation": {
        "diskon_pct": 10
      }
    }
  ]
}
```

Karena `persist=false`, backend hanya mengembalikan hasil simulasi dan tidak membuat row baru pada `iss_dss_runs` maupun `iss_dss_results`.

## 13. Definition of Done

- Tidak ada dependency baru.
- Tidak ada Alembic atau migration framework.
- Tidak ada function, trigger, view, atau procedure database.
- Tidak menduplikasi kolom atau tabel yang sudah tersedia pada schema terbaru.
- SQL DSS tersedia di `docs/schema.sql`.
- AHP dan TOPSIS berjalan tanpa database.
- Tiga skenario menghasilkan ranking.
- Hasil dapat disimpan dan dibaca kembali.
- Keputusan manager tersimpan.
- `persist=false` tidak mengubah database.
- Workflow dan notification memakai tabel existing.
- Semua perhitungan tetap dilakukan di backend.
