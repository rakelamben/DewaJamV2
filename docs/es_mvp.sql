-- ============================================================================
-- EXPERT SYSTEM (ISS-ES) MANUAL MIGRATION — DEWA JAM
-- Jalankan langsung di Supabase SQL Editor
-- ============================================================================

create schema if not exists toko_jam;

-- 1. Tambah kolom spesifikasi teknis terstruktur pada tabel products
alter table toko_jam.products
  add column if not exists specs jsonb not null default '{}'::jsonb;

-- 2. Tabel Master Domain Sistem Pakar
create table if not exists toko_jam.iss_es_domains (
  domain_id uuid primary key default gen_random_uuid(),
  kode varchar not null unique,
  nama varchar not null,
  deskripsi text,
  target_role varchar not null
    check (target_role in ('customer', 'kasir', 'gudang', 'manager')),
  entity_type varchar not null
    check (entity_type in ('product', 'transaction', 'purchase', 'kpi', 'workflow', 'general')),
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

-- 3. Tabel Definisi Fakta (Pertanyaan Kuesioner, Fakta Otomatis DB, & Fakta Antara)
create table if not exists toko_jam.iss_es_facts (
  fact_id uuid primary key default gen_random_uuid(),
  domain_id uuid not null references toko_jam.iss_es_domains(domain_id) on delete cascade,
  kode varchar not null,
  nama varchar not null,
  pertanyaan text,
  tipe_nilai varchar not null
    check (tipe_nilai in ('enum', 'number', 'boolean', 'text')),
  sumber_fakta varchar not null
    check (sumber_fakta in ('user_input', 'db_derived', 'inferred')),
  opsi_nilai jsonb not null default '[]'::jsonb,
  urutan integer not null default 0,
  is_required boolean not null default true,
  is_active boolean not null default true,
  unique (domain_id, kode)
);

-- 4. Tabel Basis Aturan Pakar (Rule Base: IF kondisi THEN kesimpulan + CF Pakar)
create table if not exists toko_jam.iss_es_rules (
  rule_id uuid primary key default gen_random_uuid(),
  domain_id uuid not null references toko_jam.iss_es_domains(domain_id) on delete cascade,
  kode varchar not null,
  nama varchar not null,
  kondisi jsonb not null default '[]'::jsonb,
  jenis_konklusi varchar not null default 'final_conclusion'
    check (jenis_konklusi in ('intermediate_fact', 'final_conclusion')),
  kesimpulan_kode varchar not null,
  kesimpulan_nilai varchar,
  kesimpulan_judul varchar not null,
  penjelasan text not null,
  rekomendasi jsonb not null default '{}'::jsonb,
  cf_pakar double precision not null default 0.8
    check (cf_pakar >= -1.0 and cf_pakar <= 1.0),
  prioritas integer not null default 10,
  knowledge_source_table varchar
    check (knowledge_source_table is null or knowledge_source_table in (
      'knowledge_policies', 'knowledge_faqs', 'knowledge_articles', 'knowledge_case_studies', 'knowledge_videos'
    )),
  knowledge_source_id uuid,
  status varchar not null default 'active'
    check (status in ('draft', 'active', 'archived')),
  created_by uuid references toko_jam.personnel(personnel_id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (domain_id, kode)
);

-- 5. Tabel Sesi Konsultasi / Run Inferensi (Mendukung personnel, customer, & guest)
create table if not exists toko_jam.iss_es_consultations (
  consultation_id uuid primary key default gen_random_uuid(),
  domain_id uuid not null references toko_jam.iss_es_domains(domain_id),
  actor_type varchar not null
    check (actor_type in ('personnel', 'customer', 'guest')),
  personnel_id uuid references toko_jam.personnel(personnel_id),
  customer_id uuid references toko_jam.customers(customer_id),
  reference_table varchar,
  reference_id uuid,
  user_facts jsonb not null default '{}'::jsonb,
  db_facts jsonb not null default '{}'::jsonb,
  inferred_facts jsonb not null default '{}'::jsonb,
  warnings jsonb not null default '[]'::jsonb,
  workflow_request_id uuid references toko_jam.workflow_requests(request_id),
  created_at timestamptz not null default now(),
  check (
    (actor_type = 'personnel' and personnel_id is not null and customer_id is null)
    or
    (actor_type = 'customer' and customer_id is not null and personnel_id is null)
    or
    (actor_type = 'guest' and personnel_id is null and customer_id is null)
  )
);

-- Jika tabel iss_es_consultations sudah sempat dibuat dengan constraint lama (tanpa 'guest'),
-- pastikan constraint diperbarui secara aman:
alter table toko_jam.iss_es_consultations
  drop constraint if exists iss_es_consultations_actor_type_check,
  drop constraint if exists iss_es_consultations_check;

alter table toko_jam.iss_es_consultations
  add constraint iss_es_consultations_actor_type_check
    check (actor_type in ('personnel', 'customer', 'guest')),
  add constraint iss_es_consultations_check
    check (
      (actor_type = 'personnel' and personnel_id is not null and customer_id is null)
      or
      (actor_type = 'customer' and customer_id is not null and personnel_id is null)
      or
      (actor_type = 'guest' and personnel_id is null and customer_id is null)
    );

-- 6. Tabel Hasil Diagnosis, Rekomendasi & Explanation Trace
create table if not exists toko_jam.iss_es_results (
  result_id uuid primary key default gen_random_uuid(),
  consultation_id uuid not null references toko_jam.iss_es_consultations(consultation_id) on delete cascade,
  ranking integer not null,
  kesimpulan_kode varchar not null,
  kesimpulan_judul varchar not null,
  cf_kombinasi double precision not null,
  tingkat_keyakinan varchar not null,
  ringkasan_diagnosis text not null,
  rekomendasi jsonb not null default '{}'::jsonb,
  matched_rules jsonb not null default '[]'::jsonb,
  matched_products jsonb not null default '[]'::jsonb,
  knowledge_refs jsonb not null default '[]'::jsonb,
  decision varchar not null default 'pending'
    check (decision in ('pending', 'accepted', 'rejected')),
  decision_by uuid references toko_jam.personnel(personnel_id),
  decision_note text,
  decided_at timestamptz
);

-- 7. Indexes untuk Performa Query Engine & Riwayat Konsultasi
create index if not exists ix_iss_es_facts_domain_order
  on toko_jam.iss_es_facts(domain_id, is_active, urutan);

create index if not exists ix_iss_es_rules_domain_status
  on toko_jam.iss_es_rules(domain_id, status, prioritas);

create index if not exists ix_iss_es_consultations_domain_created
  on toko_jam.iss_es_consultations(domain_id, created_at desc);

create index if not exists ix_iss_es_consultations_customer
  on toko_jam.iss_es_consultations(customer_id, created_at desc);

create index if not exists ix_iss_es_results_consultation
  on toko_jam.iss_es_results(consultation_id, ranking);

-- 8. Seed Capabilities RBAC untuk Expert System
insert into toko_jam.internal_capabilities (code, name, description, module)
values
  ('es.view', 'View Expert System', 'Melihat domain, riwayat, dan penjelasan Sistem Pakar', 'iss'),
  ('es.consult', 'Run Expert Consultation', 'Menjalankan sesi konsultasi dan diagnosis Sistem Pakar', 'iss'),
  ('es.rules.manage', 'Manage Expert Rules', 'Mengelola basis aturan (rule base) dan CF pakar', 'iss'),
  ('es.decide', 'Decide Expert Result', 'Menerima atau menolak rekomendasi hasil Sistem Pakar', 'iss')
on conflict (code) do update set
  name = excluded.name,
  description = excluded.description,
  module = excluded.module;

insert into toko_jam.role_capabilities (role, capability_id)
select mapping.role, capability.capability_id
from (values
  ('manager', 'es.view'),
  ('manager', 'es.consult'),
  ('manager', 'es.rules.manage'),
  ('manager', 'es.decide'),
  ('staf_gudang', 'es.view'),
  ('staf_gudang', 'es.consult'),
  ('staf_gudang', 'es.decide'),
  ('gudang', 'es.view'),
  ('gudang', 'es.consult'),
  ('gudang', 'es.decide'),
  ('staf_operasional', 'es.view'),
  ('staf_operasional', 'es.consult'),
  ('staf_operasional', 'es.decide'),
  ('kasir', 'es.view'),
  ('kasir', 'es.consult'),
  ('kasir', 'es.decide')
) as mapping(role, capability_code)
join toko_jam.internal_capabilities capability
  on capability.code = mapping.capability_code
on conflict (role, capability_id) do nothing;

-- 9. Reload schema cache Supabase PostgREST
notify pgrst, 'reload schema';
