-- KMS Iterasi 2 migration.
-- Jalankan manual pada Supabase SQL Editor.

do $$
declare
    table_name text;
begin
    foreach table_name in array array[
        'knowledge_policies',
        'knowledge_faqs',
        'knowledge_articles',
        'knowledge_videos',
        'knowledge_case_studies'
    ] loop
        execute format('alter table toko_jam.%I
            add column if not exists status varchar(30) default ''draft'',
            add column if not exists published_at timestamptz,
            add column if not exists published_by uuid,
            add column if not exists archived_at timestamptz,
            add column if not exists archived_by uuid,
            add column if not exists updated_by uuid', table_name);
        execute format('update toko_jam.%I set status = case when is_published = true then ''published'' else ''draft'' end where status is null', table_name);
    end loop;
end $$;

alter table toko_jam.knowledge_versions
    add column if not exists status varchar(30),
    add column if not exists change_type varchar(30),
    add column if not exists restore_source_version_id uuid;

alter table toko_jam.knowledge_attachments
    add column if not exists storage_bucket varchar(150),
    add column if not exists storage_path text,
    add column if not exists file_name varchar(255),
    add column if not exists mime_type varchar(150),
    add column if not exists file_size bigint,
    add column if not exists uploaded_by uuid,
    add column if not exists status varchar(30) default 'active';

update toko_jam.knowledge_attachments
set storage_path = coalesce(storage_path, file_url),
    file_name = coalesce(file_name, nama_file),
    mime_type = coalesce(mime_type, tipe_file),
    file_size = coalesce(file_size, ukuran_bytes),
    status = coalesce(status, 'active')
where storage_path is null or file_name is null or mime_type is null or file_size is null or status is null;

create unique index if not exists uq_knowledge_bookmark
    on toko_jam.knowledge_bookmarks(source_table, source_id, personnel_id);

create index if not exists idx_knowledge_versions_source
    on toko_jam.knowledge_versions(source_table, source_id, created_at desc);

create index if not exists idx_knowledge_attachments_source
    on toko_jam.knowledge_attachments(source_table, source_id, status);

insert into toko_jam.internal_capabilities (code, name, description, module)
values
    ('knowledge.version.view', 'Lihat Versi Knowledge', 'Melihat riwayat versi knowledge', 'knowledge'),
    ('knowledge.version.restore', 'Pulihkan Versi Knowledge', 'Memulihkan versi knowledge', 'knowledge'),
    ('knowledge.publish', 'Terbitkan Knowledge', 'Menerbitkan konten knowledge', 'knowledge'),
    ('knowledge.archive', 'Arsipkan Knowledge', 'Mengarsipkan konten knowledge', 'knowledge'),
    ('knowledge.upload', 'Upload Lampiran Knowledge', 'Mengunggah lampiran knowledge', 'knowledge'),
    ('knowledge.download', 'Download Lampiran Knowledge', 'Mengunduh lampiran knowledge', 'knowledge'),
    ('knowledge.notification.manage', 'Kelola Notifikasi Knowledge', 'Mengelola notifikasi konten penting', 'knowledge'),
    ('knowledge.editor.manage', 'Kelola Editor Knowledge', 'Mengelola editor knowledge', 'knowledge')
on conflict (code) do nothing;

insert into toko_jam.role_capabilities (role, capability_id)
select mapping.role, capability.capability_id
from (values
    ('manager', 'knowledge.version.view'), ('manager', 'knowledge.version.restore'),
    ('manager', 'knowledge.publish'), ('manager', 'knowledge.archive'),
    ('manager', 'knowledge.upload'), ('manager', 'knowledge.download'),
    ('manager', 'knowledge.notification.manage'), ('manager', 'knowledge.editor.manage'),
    ('staf_gudang', 'knowledge.download'), ('gudang', 'knowledge.download'),
    ('staf_operasional', 'knowledge.download'), ('kasir', 'knowledge.download')
) as mapping(role, capability_code)
join toko_jam.internal_capabilities capability on capability.code = mapping.capability_code
on conflict do nothing;

insert into storage.buckets (id, name, public)
values ('internal-documents', 'internal-documents', false)
on conflict (id) do update set public = false;

grant usage on schema toko_jam to authenticated;
grant select on table toko_jam.user_profiles to authenticated;

drop policy if exists "kms personnel can upload attachments" on storage.objects;
create policy "kms personnel can upload attachments"
on storage.objects for insert to authenticated
with check (
    bucket_id = 'internal-documents'
    and name like auth.uid()::text || '/kms/%'
    and exists (
        select 1 from toko_jam.user_profiles profile
        where profile.auth_user_id = auth.uid()
          and profile.entity_type = 'personnel'
    )
);

drop policy if exists "kms personnel can view attachments" on storage.objects;
create policy "kms personnel can view attachments"
on storage.objects for select to authenticated
using (
    bucket_id = 'internal-documents'
    and exists (
        select 1 from toko_jam.user_profiles profile
        where profile.auth_user_id = auth.uid()
          and profile.entity_type = 'personnel'
    )
);

drop policy if exists "kms personnel can delete attachments" on storage.objects;
create policy "kms personnel can delete attachments"
on storage.objects for delete to authenticated
using (
    bucket_id = 'internal-documents'
    and name like auth.uid()::text || '/kms/%'
);

notify pgrst, 'reload schema';
