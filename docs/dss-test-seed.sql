-- DSS test data for Dewa Jam.
-- Run this in Supabase SQL Editor after the base schema.
-- Then call POST /api/dss/admin/sync once while logged in as manager/admin.

create schema if not exists toko_jam;

insert into toko_jam.internal_capabilities (code, name, description, module)
values
  ('dss.view', 'View DSS', 'Melihat skenario dan hasil DSS', 'iss'),
  ('dss.run', 'Run DSS', 'Menjalankan analisis DSS', 'iss'),
  ('dss.weights.manage', 'Manage DSS Weights', 'Mengelola bobot AHP DSS', 'iss'),
  ('dss.decide', 'Decide DSS Result', 'Menerima atau menolak rekomendasi DSS', 'iss')
on conflict (code) do update set name = excluded.name, description = excluded.description, module = excluded.module;

insert into toko_jam.role_capabilities (role, capability_id)
select roles.role, capabilities.capability_id
from (values
  ('manager', 'dss.view'), ('manager', 'dss.run'), ('manager', 'dss.weights.manage'), ('manager', 'dss.decide'),
  ('staf_gudang', 'dss.view'), ('staf_gudang', 'dss.run')
) as roles(role, code)
join toko_jam.internal_capabilities capabilities on capabilities.code = roles.code
on conflict (role, capability_id) do nothing;

alter table toko_jam.mis_product_costs
  add column if not exists supplier_id uuid;
alter table toko_jam.mis_stock_movements
  add column if not exists purchase_id uuid;

create table if not exists toko_jam.suppliers (
  supplier_id uuid primary key default gen_random_uuid(),
  nama varchar not null unique,
  kontak varchar,
  alamat text,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists toko_jam.supplier_purchases (
  purchase_id uuid primary key default gen_random_uuid(),
  no_po varchar not null unique,
  supplier_id uuid not null references toko_jam.suppliers(supplier_id),
  tanggal_pesan date not null,
  tanggal_estimasi_terima date,
  tanggal_terima date,
  status varchar not null default 'dipesan'
    check (status in ('dipesan', 'diterima_sebagian', 'diterima', 'dibatalkan')),
  workflow_request_id uuid references toko_jam.workflow_requests(request_id),
  catatan text,
  created_by uuid references toko_jam.personnel(personnel_id),
  created_at timestamptz not null default now()
);

create table if not exists toko_jam.supplier_purchase_items (
  item_id uuid primary key default gen_random_uuid(),
  purchase_id uuid not null references toko_jam.supplier_purchases(purchase_id) on delete cascade,
  product_id uuid not null references toko_jam.products(product_id),
  qty_pesan integer not null check (qty_pesan > 0),
  qty_terima integer not null default 0 check (qty_terima >= 0),
  qty_rusak integer not null default 0 check (qty_rusak >= 0),
  qty_retur integer not null default 0 check (qty_retur >= 0),
  harga_beli_satuan numeric not null check (harga_beli_satuan >= 0)
);

create table if not exists toko_jam.iss_dss_scenarios (
  scenario_id uuid primary key default gen_random_uuid(),
  kode varchar not null unique,
  nama varchar not null,
  deskripsi text,
  alternative_type varchar not null check (alternative_type in ('product', 'supplier')),
  is_active boolean not null default true
);
create table if not exists toko_jam.iss_dss_criteria (
  criteria_id uuid primary key default gen_random_uuid(),
  scenario_id uuid not null references toko_jam.iss_dss_scenarios(scenario_id),
  kode varchar not null,
  nama varchar not null,
  satuan varchar,
  is_benefit boolean not null,
  urutan integer not null,
  is_active boolean not null default true,
  unique (scenario_id, kode)
);
create table if not exists toko_jam.iss_dss_weight_sets (
  weight_set_id uuid primary key default gen_random_uuid(),
  scenario_id uuid not null references toko_jam.iss_dss_scenarios(scenario_id),
  nama varchar not null,
  lambda_max double precision,
  ci double precision,
  cr double precision not null,
  status varchar not null default 'draft' check (status in ('draft', 'active', 'archived')),
  created_by uuid references toko_jam.personnel(personnel_id),
  created_at timestamptz not null default now(),
  activated_at timestamptz
);
create unique index if not exists uq_iss_dss_active_weight
  on toko_jam.iss_dss_weight_sets(scenario_id) where status = 'active';
create table if not exists toko_jam.iss_dss_pairwise (
  weight_set_id uuid not null references toko_jam.iss_dss_weight_sets(weight_set_id) on delete cascade,
  criteria_1 uuid not null references toko_jam.iss_dss_criteria(criteria_id),
  criteria_2 uuid not null references toko_jam.iss_dss_criteria(criteria_id),
  nilai double precision not null check (nilai > 0),
  primary key (weight_set_id, criteria_1, criteria_2)
);
create table if not exists toko_jam.iss_dss_weights (
  weight_set_id uuid not null references toko_jam.iss_dss_weight_sets(weight_set_id) on delete cascade,
  criteria_id uuid not null references toko_jam.iss_dss_criteria(criteria_id),
  bobot double precision not null,
  primary key (weight_set_id, criteria_id)
);
create table if not exists toko_jam.iss_dss_runs (
  run_id uuid primary key default gen_random_uuid(),
  scenario_id uuid not null references toko_jam.iss_dss_scenarios(scenario_id),
  weight_set_id uuid not null references toko_jam.iss_dss_weight_sets(weight_set_id),
  scope jsonb not null default '{}',
  params jsonb not null,
  warnings jsonb not null default '[]',
  excluded jsonb not null default '[]',
  workflow_request_id uuid references toko_jam.workflow_requests(request_id),
  run_by uuid references toko_jam.personnel(personnel_id),
  created_at timestamptz not null default now()
);
create table if not exists toko_jam.iss_dss_results (
  result_id uuid primary key default gen_random_uuid(),
  run_id uuid not null references toko_jam.iss_dss_runs(run_id) on delete cascade,
  product_id uuid references toko_jam.products(product_id),
  supplier_id uuid references toko_jam.suppliers(supplier_id),
  group_key varchar,
  skor double precision not null,
  ranking integer not null,
  status varchar not null,
  input_values jsonb not null,
  contributions jsonb not null,
  recommendation jsonb not null default '{}',
  decision varchar not null default 'pending' check (decision in ('pending', 'accepted', 'rejected')),
  decision_by uuid references toko_jam.personnel(personnel_id),
  decision_note text,
  decided_at timestamptz,
  check ((product_id is not null) <> (supplier_id is not null))
);

create index if not exists ix_iss_dss_runs_scenario
  on toko_jam.iss_dss_runs(scenario_id, created_at desc);
create index if not exists ix_iss_dss_results_run
  on toko_jam.iss_dss_results(run_id, group_key, ranking);
create index if not exists ix_supplier_purchases_supplier_date
  on toko_jam.supplier_purchases(supplier_id, tanggal_pesan);
create index if not exists ix_supplier_purchase_items_purchase
  on toko_jam.supplier_purchase_items(purchase_id);

-- Fixed IDs make this script safe to run repeatedly.
insert into toko_jam.products
  (product_id, nama_barang, kategori, harga, stok, deskripsi, tags, brand, minimum_stok, reorder_point)
values
  ('10000000-0000-0000-0000-000000000001', 'DSS Watch Alpha', 'Jam Tangan Pria', 1500000, 3, 'Produk uji DSS', '{}', 'DSS Demo', 5, 10),
  ('10000000-0000-0000-0000-000000000002', 'DSS Watch Beta', 'Jam Tangan Pria', 2200000, 18, 'Produk uji DSS', '{}', 'DSS Demo', 5, 10),
  ('10000000-0000-0000-0000-000000000003', 'DSS Watch Gamma', 'Jam Tangan Wanita', 3200000, 2, 'Produk uji DSS', '{}', 'DSS Demo', 4, 8),
  ('10000000-0000-0000-0000-000000000004', 'DSS Smart Delta', 'Smartwatch', 2800000, 6, 'Produk uji DSS', '{}', 'DSS Demo', 4, 8)
on conflict (product_id) do update set
  harga = excluded.harga,
  stok = excluded.stok,
  reorder_point = excluded.reorder_point,
  minimum_stok = excluded.minimum_stok;

insert into toko_jam.suppliers (supplier_id, nama, kontak, alamat)
values
  ('20000000-0000-0000-0000-000000000001', 'Supplier DSS Prima', '081200000001', 'Jakarta'),
  ('20000000-0000-0000-0000-000000000002', 'Supplier DSS Nusantara', '081200000002', 'Bandung'),
  ('20000000-0000-0000-0000-000000000003', 'Supplier DSS Makmur', '081200000003', 'Surabaya')
on conflict (supplier_id) do update set is_active = true;

insert into toko_jam.mis_product_costs
  (cost_id, product_id, harga_beli, berlaku_dari, supplier_nama, supplier_id, catatan)
values
  ('30000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', 800000, current_date - 30, 'Supplier DSS Prima', '20000000-0000-0000-0000-000000000001', 'Seed DSS'),
  ('30000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-000000000002', 1200000, current_date - 30, 'Supplier DSS Nusantara', '20000000-0000-0000-0000-000000000002', 'Seed DSS'),
  ('30000000-0000-0000-0000-000000000003', '10000000-0000-0000-0000-000000000003', 1900000, current_date - 30, 'Supplier DSS Prima', '20000000-0000-0000-0000-000000000001', 'Seed DSS'),
  ('30000000-0000-0000-0000-000000000004', '10000000-0000-0000-0000-000000000004', 1800000, current_date - 30, 'Supplier DSS Makmur', '20000000-0000-0000-0000-000000000003', 'Seed DSS')
on conflict (cost_id) do update set harga_beli = excluded.harga_beli, supplier_id = excluded.supplier_id;

insert into toko_jam.mis_product_daily_summary
  (summary_id, summary_date, product_id, kategori_snapshot, qty_terjual, pendapatan, total_hpp, profit, stok_akhir, generated_at)
select gen_random_uuid(), current_date - days, p.product_id, p.kategori,
       case when p.product_id in ('10000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000004') then 2 else 1 end,
       p.harga, p.harga * 0.5, p.harga * 0.5, p.stok, now()
from generate_series(1, 30) as days
cross join toko_jam.products p
where p.product_id in (
  '10000000-0000-0000-0000-000000000001',
  '10000000-0000-0000-0000-000000000002',
  '10000000-0000-0000-0000-000000000003',
  '10000000-0000-0000-0000-000000000004'
)
and not exists (
  select 1 from toko_jam.mis_product_daily_summary s
  where s.product_id = p.product_id and s.summary_date = current_date - days
);

insert into toko_jam.supplier_purchases
  (purchase_id, no_po, supplier_id, tanggal_pesan, tanggal_estimasi_terima, tanggal_terima, status, catatan)
values
  ('40000000-0000-0000-0000-000000000001', 'DSS-PO-001', '20000000-0000-0000-0000-000000000001', current_date - 20, current_date - 15, current_date - 14, 'diterima', 'Seed DSS'),
  ('40000000-0000-0000-0000-000000000002', 'DSS-PO-002', '20000000-0000-0000-0000-000000000001', current_date - 12, current_date - 7, current_date - 6, 'diterima', 'Seed DSS'),
  ('40000000-0000-0000-0000-000000000003', 'DSS-PO-003', '20000000-0000-0000-0000-000000000001', current_date - 5, current_date, current_date, 'diterima', 'Seed DSS'),
  ('40000000-0000-0000-0000-000000000004', 'DSS-PO-004', '20000000-0000-0000-0000-000000000002', current_date - 25, current_date - 20, current_date - 17, 'diterima', 'Seed DSS'),
  ('40000000-0000-0000-0000-000000000005', 'DSS-PO-005', '20000000-0000-0000-0000-000000000002', current_date - 18, current_date - 13, current_date - 12, 'diterima', 'Seed DSS'),
  ('40000000-0000-0000-0000-000000000006', 'DSS-PO-006', '20000000-0000-0000-0000-000000000002', current_date - 8, current_date - 3, current_date - 2, 'diterima', 'Seed DSS')
on conflict (purchase_id) do nothing;

insert into toko_jam.supplier_purchase_items
  (item_id, purchase_id, product_id, qty_pesan, qty_terima, harga_beli_satuan)
values
  ('50000000-0000-0000-0000-000000000001', '40000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', 20, 19, 800000),
  ('50000000-0000-0000-0000-000000000002', '40000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-000000000001', 20, 20, 810000),
  ('50000000-0000-0000-0000-000000000003', '40000000-0000-0000-0000-000000000003', '10000000-0000-0000-0000-000000000001', 20, 20, 790000),
  ('50000000-0000-0000-0000-000000000004', '40000000-0000-0000-0000-000000000004', '10000000-0000-0000-0000-000000000002', 20, 20, 1200000),
  ('50000000-0000-0000-0000-000000000005', '40000000-0000-0000-0000-000000000005', '10000000-0000-0000-0000-000000000002', 20, 19, 1210000),
  ('50000000-0000-0000-0000-000000000006', '40000000-0000-0000-0000-000000000006', '10000000-0000-0000-0000-000000000002', 20, 20, 1190000)
on conflict (item_id) do nothing;

insert into toko_jam.mis_stock_movements
  (movement_id, product_id, tipe_mutasi, qty_change, stok_sebelum, stok_sesudah, alasan, created_at)
values
  ('60000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', 'purchase_in', 20, 0, 20, 'Seed DSS purchase', now() - interval '20 days'),
  ('60000000-0000-0000-0000-000000000002', '10000000-0000-0000-0000-000000000002', 'purchase_in', 20, 0, 20, 'Seed DSS purchase', now() - interval '25 days')
on conflict (movement_id) do nothing;

-- Verify after execution:
-- select * from toko_jam.iss_dss_scenarios order by kode;
-- select * from toko_jam.suppliers order by nama;
-- select * from toko_jam.supplier_purchases order by tanggal_pesan;
