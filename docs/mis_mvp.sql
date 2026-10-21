-- MIS Dashboard MVP migration.
-- Jalankan manual di Supabase SQL Editor.

alter table toko_jam.products
    add column if not exists minimum_stok integer default 0,
    add column if not exists reorder_point integer default 0;

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

insert into toko_jam.mis_kpi_definitions
    (kpi_id, kode_kpi, nama_kpi, deskripsi, satuan, rumus_deskripsi, sumber_data, arah_baik, periode_default, is_active, created_at, updated_at)
values
    (gen_random_uuid(), 'KPI_TOTAL_SALES', 'Total Pendapatan', 'Total pendapatan berdasarkan periode laporan', 'IDR', 'sum(total_pendapatan)', 'mis_daily_sales_summary', 'higher', 'monthly', true, now(), now()),
    (gen_random_uuid(), 'KPI_GROSS_PROFIT', 'Gross Profit', 'Laba kotor berdasarkan periode laporan', 'IDR', 'sum(gross_profit)', 'mis_daily_sales_summary', 'higher', 'monthly', true, now(), now()),
    (gen_random_uuid(), 'KPI_TRANSACTION_COUNT', 'Jumlah Transaksi', 'Jumlah transaksi berdasarkan periode laporan', 'transaction', 'sum(jumlah_transaksi)', 'mis_daily_sales_summary', 'higher', 'monthly', true, now(), now()),
    (gen_random_uuid(), 'KPI_GROSS_MARGIN', 'Gross Margin', 'Persentase gross profit terhadap pendapatan', 'percent', 'gross_profit / total_pendapatan * 100', 'mis_daily_sales_summary', 'higher', 'monthly', true, now(), now()),
    (gen_random_uuid(), 'KPI_STOCKOUT_RATE', 'Stockout Rate', 'Persentase SKU dengan stok habis', 'percent', 'sku_stok_nol / total_sku * 100', 'products', 'lower', 'monthly', true, now(), now())
on conflict (kode_kpi) do nothing;

notify pgrst, 'reload schema';
