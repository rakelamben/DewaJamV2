-- ============================================================================
-- EXPERT SYSTEM (ISS-ES) TEST SEED DATA — DEWA JAM
-- Jalankan di Supabase SQL Editor setelah menjalankan docs/es_mvp.sql
-- Script ini idempotent (aman dijalankan berulang kali dengan ON CONFLICT)
-- ============================================================================

create schema if not exists toko_jam;

-- Pastikan kolom specs tersedia pada tabel products
alter table toko_jam.products
  add column if not exists specs jsonb not null default '{}'::jsonb;

-- 1. Seed Produk Jam Tangan dengan Spesifikasi Teknis Horologi (specs JSONB)
--    Digunakan oleh domain:
--    - CUST_WATCH_ADVISOR (Customer & Guest)
--    - STAFF_POS_CROSSSELL (Staf Kasir / Operasional)
--    - WAREHOUSE_STOCK_ANOMALY (Staf Gudang)
insert into toko_jam.products
  (product_id, nama_barang, kategori, harga, stok, deskripsi, tags, brand, minimum_stok, reorder_point, specs)
values
  (
    '70000000-0000-0000-0000-000000000001',
    'Seiko Prospex Diver 200M Automatic',
    'Jam Tangan Pria',
    3850000,
    8,
    'Jam tangan selam mekanis otomatis dengan bezel searah dan ketahanan air 20 ATM (200 meter).',
    array['diver', 'automatic', '200m', 'sport', 'rubber'],
    'Seiko',
    3,
    6,
    '{
      "movement": "automatic",
      "water_resistance_atm": 20,
      "case_diameter_mm": 42,
      "lug_width_mm": 22,
      "strap_material": "rubber",
      "case_material": "stainless_steel",
      "glass": "sapphire",
      "Style": "diver"
    }'::jsonb
  ),
  (
    '70000000-0000-0000-0000-000000000002',
    'Citizen Promaster Tough Titanium Solar 38mm',
    'Jam Tangan Pria',
    2950000,
    5,
    'Jam tangan lapangan berbahan Super Titanium hipoalergenik dengan pengisian daya Eco-Drive Solar.',
    array['titanium', 'solar', 'hypoallergenic', 'field', '38mm'],
    'Citizen',
    2,
    5,
    '{
      "movement": "solar",
      "water_resistance_atm": 10,
      "case_diameter_mm": 38,
      "lug_width_mm": 20,
      "strap_material": "titanium",
      "case_material": "titanium",
      "hypoallergenic": true,
      "glass": "sapphire"
    }'::jsonb
  ),
  (
    '70000000-0000-0000-0000-000000000003',
    'Orient Bambino Dress Mechanical 39mm',
    'Jam Tangan Luxury',
    8500000,
    4,
    'Jam tangan dress formal tipis dengan in-house automatic calibre dan tali kulit calfskin asli.',
    array['dress', 'formal', 'luxury', 'automatic', 'leather'],
    'Orient Star',
    2,
    4,
    '{
      "movement": "automatic",
      "water_resistance_atm": 5,
      "case_diameter_mm": 39,
      "lug_width_mm": 20,
      "strap_material": "leather",
      "case_material": "stainless_steel",
      "glass": "sapphire"
    }'::jsonb
  ),
  (
    '70000000-0000-0000-0000-000000000004',
    'Garmin Instinct 2 Solar Tactical Outdoor',
    'Smartwatch',
    4200000,
    6,
    'Smartwatch outdoor dengan sensor ABC (Altimeter, Barometer, Compass), GPS multi-GNSS, dan ketahanan 10 ATM.',
    array['smartwatch', 'outdoor', 'solar', 'tactical', '100m', 'rubber'],
    'Garmin',
    3,
    5,
    '{
      "movement": "smart",
      "water_resistance_atm": 10,
      "case_diameter_mm": 44,
      "lug_width_mm": 22,
      "strap_material": "rubber",
      "case_material": "resin_fiber",
      "hypoallergenic": true
    }'::jsonb
  ),
  (
    '70000000-0000-0000-0000-000000000005',
    'Casio Edifice Classic Sapphire 38mm',
    'Jam Tangan Wanita',
    1250000,
    12,
    'Jam tangan kasual harian dengan mesin quartz presisi tinggi dan kaca kristal safir.',
    array['daily', 'quartz', 'classic', 'sapphire', '38mm'],
    'Casio',
    4,
    8,
    '{
      "movement": "quartz",
      "water_resistance_atm": 5,
      "case_diameter_mm": 38,
      "lug_width_mm": 20,
      "strap_material": "stainless_steel",
      "case_material": "stainless_steel"
    }'::jsonb
  ),
  -- 2. Seed Produk Strap & Aksesoris Kompatibel untuk Cross-Sell POS (STAFF_POS_CROSSSELL)
  (
    '70000000-0000-0000-0000-000000000006',
    'Strap FKM Fluoroelastomer Rubber Quick-Release 20mm',
    'Strap & Aksesoris',
    380000,
    15,
    'Tali jam tangan karet FKM tahan keringat dan air laut dengan springbar quick-release ukuran 20mm.',
    array['strap', 'rubber', '20mm', 'waterproof', 'hypoallergenic'],
    'Dewa Strap Craft',
    5,
    10,
    '{
      "accessory_type": "strap",
      "lug_width_mm": 20,
      "compatible_lug_width_mm": [20],
      "strap_material": "rubber",
      "water_resistance_atm": 20
    }'::jsonb
  ),
  (
    '70000000-0000-0000-0000-000000000007',
    'Strap FKM Fluoroelastomer Diver 22mm',
    'Strap & Aksesoris',
    390000,
    14,
    'Tali jam tangan selam FKM heavy-duty ukuran lug 22mm untuk jam diver dan outdoor.',
    array['strap', 'rubber', '22mm', 'diver', 'waterproof'],
    'Dewa Strap Craft',
    5,
    10,
    '{
      "accessory_type": "strap",
      "lug_width_mm": 22,
      "compatible_lug_width_mm": [22],
      "strap_material": "rubber",
      "water_resistance_atm": 20
    }'::jsonb
  ),
  (
    '70000000-0000-0000-0000-000000000008',
    'Strap Italian Calfskin Leather Dress 20mm',
    'Strap & Aksesoris',
    450000,
    10,
    'Tali jam kulit sapi Italia jahitan tangan ukuran 20mm untuk acara formal dan eksekutif.',
    array['strap', 'leather', '20mm', 'formal', 'dress'],
    'Dewa Strap Craft',
    4,
    8,
    '{
      "accessory_type": "strap",
      "lug_width_mm": 20,
      "compatible_lug_width_mm": [20],
      "strap_material": "leather"
    }'::jsonb
  ),
  (
    '70000000-0000-0000-0000-000000000009',
    'Watch Winder Single Rotor & Microfiber Care Kit',
    'Strap & Aksesoris',
    650000,
    9,
    'Kotak pemutar jam otomatis (watch winder) silent motor beserta cairan pembersih dan kain microfiber.',
    array['winder', 'care', 'automatic', 'luxury', 'box'],
    'Dewa Horology Care',
    3,
    6,
    '{
      "accessory_type": "winder_and_care",
      "compatible_lug_width_mm": [18, 20, 22, 24]
    }'::jsonb
  )
on conflict (product_id) do update set
  nama_barang = excluded.nama_barang,
  kategori = excluded.kategori,
  harga = excluded.harga,
  stok = excluded.stok,
  deskripsi = excluded.deskripsi,
  tags = excluded.tags,
  brand = excluded.brand,
  minimum_stok = excluded.minimum_stok,
  reorder_point = excluded.reorder_point,
  specs = excluded.specs;

-- 3. Seed Supplier & Purchase Order (PO) untuk Pengujian WAREHOUSE_QC_INBOUND
insert into toko_jam.suppliers (supplier_id, nama, kontak, alamat)
values
  ('20000000-0000-0000-0000-000000000010', 'PT Horologi Distribusi Indonesia', '081199887766', 'Jakarta Pusat')
on conflict (supplier_id) do update set is_active = true;

insert into toko_jam.supplier_purchases
  (purchase_id, no_po, supplier_id, tanggal_pesan, tanggal_estimasi_terima, tanggal_terima, status, catatan)
values
  (
    '40000000-0000-0000-0000-000000000010',
    'ES-PO-QC-001 (Cacat Tinggi)',
    '20000000-0000-0000-0000-000000000010',
    current_date - 14,
    current_date - 7,
    current_date - 2,
    'diterima_sebagian',
    'Pengiriman batch diver dengan indikasi guncangan kurir'
  ),
  (
    '40000000-0000-0000-0000-000000000011',
    'ES-PO-QC-002 (Normal / Minor)',
    '20000000-0000-0000-0000-000000000010',
    current_date - 7,
    current_date - 2,
    current_date - 1,
    'diterima',
    'Pengiriman rutin batch jam titanium dan dress'
  )
on conflict (purchase_id) do nothing;

insert into toko_jam.supplier_purchase_items
  (item_id, purchase_id, product_id, qty_pesan, qty_terima, qty_rusak, qty_retur, harga_beli_satuan)
values
  (
    '50000000-0000-0000-0000-000000000010',
    '40000000-0000-0000-0000-000000000010',
    '70000000-0000-0000-0000-000000000001',
    20,
    18,
    3,
    0,
    2400000
  ),
  (
    '50000000-0000-0000-0000-000000000011',
    '40000000-0000-0000-0000-000000000011',
    '70000000-0000-0000-0000-000000000002',
    15,
    15,
    1,
    0,
    1850000
  )
on conflict (item_id) do update set
  qty_pesan = excluded.qty_pesan,
  qty_terima = excluded.qty_terima,
  qty_rusak = excluded.qty_rusak;

-- 4. Seed HPP Produk & Mutasi Stok untuk WAREHOUSE_STOCK_ANOMALY & MGR_KPI_DIAGNOSTIC
insert into toko_jam.mis_product_costs
  (cost_id, product_id, harga_beli, berlaku_dari, supplier_nama, supplier_id, catatan)
values
  (
    '30000000-0000-0000-0000-000000000010',
    '70000000-0000-0000-0000-000000000001',
    2400000,
    current_date - 20,
    'PT Horologi Distribusi Indonesia',
    '20000000-0000-0000-0000-000000000010',
    'HPP Seiko Prospex Diver'
  ),
  (
    '30000000-0000-0000-0000-000000000011',
    '70000000-0000-0000-0000-000000000003',
    5200000,
    current_date - 20,
    'PT Horologi Distribusi Indonesia',
    '20000000-0000-0000-0000-000000000010',
    'HPP Orient Bambino Luxury'
  )
on conflict (cost_id) do update set harga_beli = excluded.harga_beli;

insert into toko_jam.mis_stock_movements
  (movement_id, product_id, tipe_mutasi, qty_change, stok_sebelum, stok_sesudah, alasan, created_at)
values
  (
    '60000000-0000-0000-0000-000000000010',
    '70000000-0000-0000-0000-000000000001',
    'purchase_in',
    10,
    0,
    10,
    'Penerimaan awal PO Seiko Diver',
    now() - interval '10 days'
  ),
  (
    '60000000-0000-0000-0000-000000000011',
    '70000000-0000-0000-0000-000000000001',
    'sale_out',
    -2,
    10,
    8,
    'Penjualan POS',
    now() - interval '3 days'
  )
on conflict (movement_id) do nothing;

-- Reload schema cache PostgREST
notify pgrst, 'reload schema';
