-- KMS MVP supplemental SQL
-- Jalankan manual di Supabase SQL Editor setelah tabel KMS tersedia.

create unique index if not exists uq_knowledge_bookmark
    on toko_jam.knowledge_bookmarks(source_table, source_id, personnel_id);

insert into toko_jam.internal_capabilities (code, name, description, module)
values
    ('knowledge.view', 'Lihat Knowledge', 'Melihat konten knowledge internal', 'knowledge'),
    ('knowledge.search', 'Cari Knowledge', 'Mencari konten knowledge internal', 'knowledge'),
    ('knowledge.create', 'Buat Knowledge', 'Membuat konten knowledge', 'knowledge'),
    ('knowledge.update', 'Ubah Knowledge', 'Mengubah konten knowledge', 'knowledge'),
    ('knowledge.publish', 'Terbitkan Knowledge', 'Menerbitkan konten knowledge', 'knowledge'),
    ('knowledge.archive', 'Arsipkan Knowledge', 'Mengarsipkan konten knowledge', 'knowledge'),
    ('knowledge.delete', 'Hapus Knowledge', 'Menghapus konten knowledge', 'knowledge'),
    ('knowledge.bookmark', 'Bookmark Knowledge', 'Menyimpan bookmark pribadi', 'knowledge'),
    ('knowledge.category.view', 'Lihat Kategori Knowledge', 'Melihat kategori knowledge', 'knowledge'),
    ('knowledge.category.manage', 'Kelola Kategori Knowledge', 'Mengelola kategori knowledge', 'knowledge')
on conflict (code) do nothing;

insert into toko_jam.role_capabilities (role, capability_id)
select mapping.role, capability.capability_id
from (values
    ('manager', 'knowledge.view'), ('manager', 'knowledge.search'),
    ('manager', 'knowledge.create'), ('manager', 'knowledge.update'),
    ('manager', 'knowledge.publish'), ('manager', 'knowledge.archive'),
    ('manager', 'knowledge.delete'), ('manager', 'knowledge.bookmark'),
    ('manager', 'knowledge.category.view'), ('manager', 'knowledge.category.manage'),
    ('staf_gudang', 'knowledge.view'), ('staf_gudang', 'knowledge.search'),
    ('staf_gudang', 'knowledge.bookmark'), ('staf_gudang', 'knowledge.category.view'),
    ('gudang', 'knowledge.view'), ('gudang', 'knowledge.search'),
    ('gudang', 'knowledge.bookmark'), ('gudang', 'knowledge.category.view'),
    ('staf_operasional', 'knowledge.view'), ('staf_operasional', 'knowledge.search'),
    ('staf_operasional', 'knowledge.bookmark'), ('staf_operasional', 'knowledge.category.view'),
    ('kasir', 'knowledge.view'), ('kasir', 'knowledge.search'),
    ('kasir', 'knowledge.bookmark'), ('kasir', 'knowledge.category.view')
) as mapping(role, capability_code)
join toko_jam.internal_capabilities capability
  on capability.code = mapping.capability_code
on conflict do nothing;

notify pgrst, 'reload schema';
