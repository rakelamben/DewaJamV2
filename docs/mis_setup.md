# Panduan Setup Data MIS

Dokumen ini berisi query dan panduan pengisian data untuk dashboard MIS Dewa Jam.

## Urutan Eksekusi

Jalankan query dengan urutan berikut pada Supabase SQL Editor:

1. Tambahkan kolom minimum stok.
2. Tambahkan index summary MIS.
3. Buat fungsi refresh summary.
4. Isi harga beli produk.
5. Jalankan refresh summary.
6. Isi definisi KPI.
7. Isi target KPI.
8. Validasi hasil summary.
9. Opsional: aktifkan refresh otomatis dengan `pg_cron`.

> Jalankan query pada schema `toko_jam`. Jangan menggunakan harga beli dummy untuk data produksi.

---

## 1. Kolom Minimum Stok

```sql
alter table toko_jam.products
    add column if not exists minimum_stok integer default 0,
    add column if not exists reorder_point integer default 0;
```

Isi nilai default untuk produk yang belum memiliki batas stok:

```sql
update toko_jam.products
set
    minimum_stok = 5,
    reorder_point = 5
where minimum_stok is null
   or minimum_stok = 0;
```

Validasi:

```sql
select
    product_id,
    nama_barang,
    harga,
    stok,
    minimum_stok,
    reorder_point
from toko_jam.products
order by nama_barang;
```

---

## 2. Index Summary MIS

```sql
create unique index if not exists uq_mis_daily_sales_summary
    on toko_jam.mis_daily_sales_summary(summary_date, channel);

create unique index if not exists uq_mis_product_daily_summary
    on toko_jam.mis_product_daily_summary(summary_date, product_id);

create index if not exists idx_mis_daily_sales_date_channel
    on toko_jam.mis_daily_sales_summary(summary_date, channel);

create index if not exists idx_mis_product_daily_date_product
    on toko_jam.mis_product_daily_summary(summary_date, product_id);

create index if not exists idx_mis_stock_movements_created_product
    on toko_jam.mis_stock_movements(created_at, product_id);
```

---

## 3. Membuat Fungsi Refresh Summary

Fungsi ini menghitung ulang:

- `mis_daily_sales_summary`
- `mis_product_daily_summary`

Fungsi aman dijalankan berulang kali karena summary pada periode target akan dihapus dan dibuat ulang.

```sql
create or replace function toko_jam.refresh_mis_summary(
    p_date_from date,
    p_date_to date
)
returns jsonb
language plpgsql
security definer
set search_path = toko_jam, public
as $$
declare
    v_daily_count integer;
    v_product_count integer;
begin
    if p_date_from is null or p_date_to is null then
        raise exception 'Tanggal awal dan akhir wajib diisi';
    end if;

    if p_date_from > p_date_to then
        raise exception 'Tanggal awal tidak boleh lebih besar dari tanggal akhir';
    end if;

    delete from mis_daily_sales_summary
    where summary_date between p_date_from and p_date_to;

    delete from mis_product_daily_summary
    where summary_date between p_date_from and p_date_to;

    with all_transactions as (
        select
            t.transaction_id,
            t.customer_id,
            t.tanggal_transaksi::date as summary_date,
            lower(coalesce(t.channel, 'unknown')) as channel,
            coalesce(t.subtotal, 0)::numeric as subtotal,
            coalesce(t.shipping_fee, 0)::numeric as shipping_fee,
            lower(coalesce(t.status, '')) as status,
            lower(coalesce(t.payment_status, '')) as payment_status
        from transactions t
        where t.tanggal_transaksi::date between p_date_from and p_date_to
    ),
    eligible_transactions as (
        select *
        from all_transactions
        where status not in ('canceled', 'cancelled')
          and (
              payment_status = 'paid'
              or status in ('completed', 'selesai')
          )
    ),
    sales_by_day as (
        select
            summary_date,
            channel,
            count(*)::integer as jumlah_transaksi,
            sum(subtotal)::numeric as gross_sales,
            sum(shipping_fee)::numeric as pendapatan_ongkir,
            count(distinct customer_id)::integer as pelanggan_unik
        from eligible_transactions
        group by summary_date, channel
    ),
    items_by_day as (
        select
            et.summary_date,
            et.channel,
            coalesce(sum(ti.qty), 0)::integer as jumlah_item_terjual,
            coalesce(sum(ti.qty * coalesce(cost.harga_beli, 0)), 0)::numeric as total_hpp
        from eligible_transactions et
        join transaction_items ti
            on ti.transaction_id = et.transaction_id
        left join lateral (
            select pc.harga_beli
            from mis_product_costs pc
            where pc.product_id = ti.product_id
              and pc.berlaku_dari <= et.summary_date
              and (
                  pc.berlaku_sampai is null
                  or pc.berlaku_sampai >= et.summary_date
              )
            order by pc.berlaku_dari desc
            limit 1
        ) cost on true
        group by et.summary_date, et.channel
    ),
    canceled_by_day as (
        select
            summary_date,
            channel,
            count(*)::integer as jumlah_transaksi_batal
        from all_transactions
        where status in ('canceled', 'cancelled')
           or payment_status = 'canceled'
        group by summary_date, channel
    ),
    new_customers_by_day as (
        select
            et.summary_date,
            et.channel,
            count(distinct et.customer_id)::integer as pelanggan_baru
        from eligible_transactions et
        join customers c
            on c.customer_id = et.customer_id
        where c.created_at::date = et.summary_date
        group by et.summary_date, et.channel
    )
    insert into mis_daily_sales_summary (
        summary_id,
        summary_date,
        channel,
        jumlah_transaksi,
        jumlah_transaksi_batal,
        jumlah_item_terjual,
        gross_sales,
        pendapatan_ongkir,
        total_pendapatan,
        total_hpp,
        gross_profit,
        pelanggan_unik,
        pelanggan_baru,
        generated_at
    )
    select
        gen_random_uuid(),
        s.summary_date,
        s.channel,
        s.jumlah_transaksi,
        coalesce(c.jumlah_transaksi_batal, 0),
        coalesce(i.jumlah_item_terjual, 0),
        s.gross_sales,
        s.pendapatan_ongkir,
        s.gross_sales + s.pendapatan_ongkir,
        coalesce(i.total_hpp, 0),
        s.gross_sales
            + s.pendapatan_ongkir
            - coalesce(i.total_hpp, 0),
        s.pelanggan_unik,
        coalesce(n.pelanggan_baru, 0),
        now()
    from sales_by_day s
    left join items_by_day i
        on i.summary_date = s.summary_date
       and i.channel = s.channel
    left join canceled_by_day c
        on c.summary_date = s.summary_date
       and c.channel = s.channel
    left join new_customers_by_day n
        on n.summary_date = s.summary_date
       and n.channel = s.channel;

    get diagnostics v_daily_count = row_count;

    with eligible_transactions as (
        select
            t.transaction_id,
            t.tanggal_transaksi::date as summary_date,
            lower(coalesce(t.status, '')) as status,
            lower(coalesce(t.payment_status, '')) as payment_status
        from transactions t
        where t.tanggal_transaksi::date between p_date_from and p_date_to
          and lower(coalesce(t.status, '')) not in ('canceled', 'cancelled')
          and (
              lower(coalesce(t.payment_status, '')) = 'paid'
              or lower(coalesce(t.status, '')) in ('completed', 'selesai')
          )
    ),
    item_details as (
        select
            et.summary_date,
            ti.product_id,
            coalesce(p.kategori, 'Tanpa kategori') as kategori_snapshot,
            coalesce(p.brand, 'Tanpa brand') as brand_snapshot,
            ti.qty,
            ti.subtotal,
            coalesce(cost.harga_beli, 0)::numeric as harga_beli
        from eligible_transactions et
        join transaction_items ti
            on ti.transaction_id = et.transaction_id
        left join products p
            on p.product_id = ti.product_id
        left join lateral (
            select pc.harga_beli
            from mis_product_costs pc
            where pc.product_id = ti.product_id
              and pc.berlaku_dari <= et.summary_date
              and (
                  pc.berlaku_sampai is null
                  or pc.berlaku_sampai >= et.summary_date
              )
            order by pc.berlaku_dari desc
            limit 1
        ) cost on true
        where ti.product_id is not null
    ),
    product_totals as (
        select
            summary_date,
            product_id,
            kategori_snapshot,
            brand_snapshot,
            sum(qty)::integer as qty_terjual,
            sum(subtotal)::numeric as pendapatan,
            sum(qty * harga_beli)::numeric as total_hpp
        from item_details
        group by
            summary_date,
            product_id,
            kategori_snapshot,
            brand_snapshot
    )
    insert into mis_product_daily_summary (
        summary_id,
        summary_date,
        product_id,
        kategori_snapshot,
        brand_snapshot,
        qty_terjual,
        pendapatan,
        total_hpp,
        profit,
        stok_akhir,
        generated_at
    )
    select
        gen_random_uuid(),
        pt.summary_date,
        pt.product_id,
        pt.kategori_snapshot,
        pt.brand_snapshot,
        pt.qty_terjual,
        pt.pendapatan,
        pt.total_hpp,
        pt.pendapatan - pt.total_hpp,
        coalesce(p.stok, 0),
        now()
    from product_totals pt
    left join products p
        on p.product_id = pt.product_id;

    get diagnostics v_product_count = row_count;

    return jsonb_build_object(
        'date_from', p_date_from,
        'date_to', p_date_to,
        'daily_summary_rows', v_daily_count,
        'product_summary_rows', v_product_count,
        'generated_at', now()
    );
end;
$$;
```

---

## 4. Mengisi Harga Beli Produk

### Cek produk tanpa harga beli aktif

```sql
select
    p.product_id,
    p.nama_barang,
    p.harga,
    p.stok
from toko_jam.products p
where not exists (
    select 1
    from toko_jam.mis_product_costs c
    where c.product_id = p.product_id
      and c.berlaku_dari <= current_date
      and (
          c.berlaku_sampai is null
          or c.berlaku_sampai >= current_date
      )
);
```

### Input harga beli aktual

Ganti UUID dan nilai harga berikut sesuai data supplier atau invoice pembelian.

```sql
insert into toko_jam.mis_product_costs (
    cost_id,
    product_id,
    harga_beli,
    berlaku_dari,
    berlaku_sampai,
    supplier_nama,
    catatan,
    created_at
)
values
(
    gen_random_uuid(),
    'PRODUCT_UUID_1'::uuid,
    75000,
    current_date,
    null,
    'Supplier Utama',
    'Harga beli awal',
    now()
),
(
    gen_random_uuid(),
    'PRODUCT_UUID_2'::uuid,
    125000,
    current_date,
    null,
    'Supplier Utama',
    'Harga beli awal',
    now()
);
```

Validasi:

```sql
select
    p.nama_barang,
    c.harga_beli,
    c.berlaku_dari,
    c.berlaku_sampai,
    c.supplier_nama
from toko_jam.mis_product_costs c
join toko_jam.products p
    on p.product_id = c.product_id
order by p.nama_barang, c.berlaku_dari desc;
```

### Harga beli dummy untuk testing saja

Query ini mengasumsikan harga beli sebesar 60% dari harga jual. Jangan gunakan untuk produksi.

```sql
insert into toko_jam.mis_product_costs (
    cost_id,
    product_id,
    harga_beli,
    berlaku_dari,
    berlaku_sampai,
    supplier_nama,
    catatan,
    created_at
)
select
    gen_random_uuid(),
    p.product_id,
    round((p.harga * 0.60)::numeric, 2),
    current_date,
    null,
    'Dummy Supplier',
    'Data dummy untuk pengujian MIS',
    now()
from toko_jam.products p
where coalesce(p.harga, 0) > 0
  and not exists (
      select 1
      from toko_jam.mis_product_costs c
      where c.product_id = p.product_id
        and c.berlaku_dari <= current_date
        and (
            c.berlaku_sampai is null
            or c.berlaku_sampai >= current_date
        )
  );
```

---

## 5. Validasi Data Transaksi

```sql
select count(*) as jumlah_transaksi
from toko_jam.transactions;
```

```sql
select count(*) as jumlah_item_transaksi
from toko_jam.transaction_items;
```

```sql
select
    channel,
    status,
    payment_status,
    count(*) as jumlah
from toko_jam.transactions
group by channel, status, payment_status
order by channel, status;
```

Transaksi yang digunakan oleh fungsi summary adalah transaksi dengan:

```text
status = completed
status = selesai
atau payment_status = paid
```

Transaksi canceled tidak dihitung sebagai pendapatan.

---

## 6. Menjalankan Refresh Summary Manual

### Tiga puluh hari terakhir

```sql
select toko_jam.refresh_mis_summary(
    current_date - interval '29 days',
    current_date
);
```

### Bulan berjalan

```sql
select toko_jam.refresh_mis_summary(
    date_trunc('month', current_date)::date,
    current_date
);
```

### Seluruh periode transaksi

```sql
select toko_jam.refresh_mis_summary(
    (
        select min(tanggal_transaksi)::date
        from toko_jam.transactions
    ),
    current_date
);
```

### Periode tertentu

```sql
select toko_jam.refresh_mis_summary(
    date '2026-01-01',
    date '2026-01-31'
);
```

---

## 7. Validasi Summary MIS

```sql
select
    summary_date,
    channel,
    jumlah_transaksi,
    jumlah_item_terjual,
    total_pendapatan,
    total_hpp,
    gross_profit
from toko_jam.mis_daily_sales_summary
order by summary_date desc
limit 30;
```

```sql
select
    summary_date,
    product_id,
    qty_terjual,
    pendapatan,
    total_hpp,
    profit
from toko_jam.mis_product_daily_summary
order by summary_date desc, pendapatan desc
limit 30;
```

Validasi agregasi channel:

```sql
select
    channel,
    count(*) as jumlah_baris,
    sum(total_pendapatan) as total_pendapatan,
    sum(gross_profit) as total_profit
from toko_jam.mis_daily_sales_summary
group by channel
order by total_pendapatan desc;
```

---

## 8. Definisi KPI

```sql
insert into toko_jam.mis_kpi_definitions (
    kpi_id,
    kode_kpi,
    nama_kpi,
    deskripsi,
    satuan,
    rumus_deskripsi,
    sumber_data,
    arah_baik,
    periode_default,
    is_active,
    created_at,
    updated_at
)
values
(
    gen_random_uuid(),
    'KPI_TOTAL_SALES',
    'Total Pendapatan',
    'Total pendapatan penjualan',
    'IDR',
    'sum(total_pendapatan)',
    'mis_daily_sales_summary',
    'higher',
    'monthly',
    true,
    now(),
    now()
),
(
    gen_random_uuid(),
    'KPI_GROSS_PROFIT',
    'Gross Profit',
    'Laba kotor penjualan',
    'IDR',
    'sum(gross_profit)',
    'mis_daily_sales_summary',
    'higher',
    'monthly',
    true,
    now(),
    now()
),
(
    gen_random_uuid(),
    'KPI_TRANSACTION_COUNT',
    'Jumlah Transaksi',
    'Total transaksi berhasil',
    'transaction',
    'sum(jumlah_transaksi)',
    'mis_daily_sales_summary',
    'higher',
    'monthly',
    true,
    now(),
    now()
),
(
    gen_random_uuid(),
    'KPI_GROSS_MARGIN',
    'Gross Margin',
    'Persentase profit terhadap pendapatan',
    'percent',
    'gross_profit / total_pendapatan * 100',
    'mis_daily_sales_summary',
    'higher',
    'monthly',
    true,
    now(),
    now()
),
(
    gen_random_uuid(),
    'KPI_STOCKOUT_RATE',
    'Stockout Rate',
    'Persentase produk dengan stok nol',
    'percent',
    'produk_stok_nol / total_produk * 100',
    'products',
    'lower',
    'monthly',
    true,
    now(),
    now()
)
on conflict (kode_kpi) do nothing;
```

---

## 9. Target KPI Bulanan

Nilai target di bawah adalah contoh dan harus disesuaikan dengan target bisnis.

```sql
insert into toko_jam.mis_kpi_targets (
    target_id,
    kpi_id,
    personnel_id,
    periode_tipe,
    periode_mulai,
    periode_selesai,
    nilai_target,
    nilai_peringatan,
    catatan,
    created_at,
    updated_at
)
select
    gen_random_uuid(),
    k.kpi_id,
    null,
    'monthly',
    date_trunc('month', current_date)::date,
    (
        date_trunc('month', current_date)
        + interval '1 month - 1 day'
    )::date,
    case k.kode_kpi
        when 'KPI_TOTAL_SALES' then 100000000
        when 'KPI_GROSS_PROFIT' then 25000000
        when 'KPI_TRANSACTION_COUNT' then 500
        when 'KPI_GROSS_MARGIN' then 25
        when 'KPI_STOCKOUT_RATE' then 5
    end,
    case k.kode_kpi
        when 'KPI_TOTAL_SALES' then 75000000
        when 'KPI_GROSS_PROFIT' then 15000000
        when 'KPI_TRANSACTION_COUNT' then 350
        when 'KPI_GROSS_MARGIN' then 18
        when 'KPI_STOCKOUT_RATE' then 10
    end,
    'Target awal MIS',
    now(),
    now()
from toko_jam.mis_kpi_definitions k
where k.kode_kpi in (
    'KPI_TOTAL_SALES',
    'KPI_GROSS_PROFIT',
    'KPI_TRANSACTION_COUNT',
    'KPI_GROSS_MARGIN',
    'KPI_STOCKOUT_RATE'
)
and not exists (
    select 1
    from toko_jam.mis_kpi_targets t
    where t.kpi_id = k.kpi_id
      and t.periode_mulai = date_trunc('month', current_date)::date
);
```

---

## 10. Refresh Otomatis dengan pg_cron

Aktifkan extension berikut melalui Supabase Dashboard:

```text
Database → Extensions → pg_cron
```

Jadwalkan refresh setiap hari pukul 01:00:

```sql
select cron.schedule(
    'refresh-mis-summary-daily',
    '0 1 * * *',
    $$
    select toko_jam.refresh_mis_summary(
        current_date - interval '2 days',
        current_date
    );
    $$
);
```

Dua hari terakhir dihitung ulang untuk menangani:

- Pembayaran marketplace yang terlambat.
- Pembatalan transaksi.
- Koreksi transaksi.
- Perubahan status pembayaran.

Melihat jadwal:

```sql
select *
from cron.job;
```

Menghapus jadwal:

```sql
select cron.unschedule('refresh-mis-summary-daily');
```

---

## 11. Pengisian Manual dari Aplikasi

Rencana endpoint backend untuk admin/manager:

```http
POST /api/internal/mis/summary/refresh
```

Payload:

```json
{
  "date_from": "2026-01-01",
  "date_to": "2026-01-31"
}
```

Capability:

```text
mis.summary.refresh
```

Endpoint tersebut dapat memanggil fungsi:

```sql
select toko_jam.refresh_mis_summary(
    '2026-01-01',
    '2026-01-31'
);
```

Pengisian manual melalui aplikasi lebih aman dibanding memberikan akses SQL kepada user karena dapat dibatasi berdasarkan role dan dicatat ke activity log.

---

## 12. Catatan Harga Beli

Perhitungan profit mengambil harga beli aktif berdasarkan aturan:

```text
berlaku_dari <= tanggal transaksi
dan
berlaku_sampai >= tanggal transaksi atau NULL
```

Jika harga beli tidak ditemukan, fungsi menggunakan `0`. Hal ini dapat membuat profit terlihat terlalu besar.

Karena itu, sebelum menjalankan refresh summary produksi, pastikan seluruh produk aktif memiliki data pada:

```text
mis_product_costs
```

Setelah summary berhasil dibuat, dashboard MIS dapat dibuka melalui:

```text
/internal
/internal/mis
```
