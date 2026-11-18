## Table `admins`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `admin_id` | `uuid` | Primary |
| `username` | `varchar` |  Unique |
| `password_hash` | `text` |  |
| `nama` | `varchar` |  |
| `created_at` | `timestamptz` |  |
| `personnel_id` | `uuid` |  Unique |

## Table `customers`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `customer_id` | `uuid` | Primary |
| `nama` | `varchar` |  |
| `no_hp` | `varchar` |  Unique |
| `created_at` | `timestamptz` |  |

## Table `products`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `product_id` | `uuid` | Primary |
| `nama_barang` | `varchar` |  |
| `kategori` | `varchar` |  |
| `harga` | `numeric` |  |
| `stok` | `int4` |  |
| `deskripsi` | `text` |  Nullable |
| `created_at` | `timestamptz` |  |
| `updated_at` | `timestamptz` |  |
| `gambar_url` | `text` |  Nullable |
| `tags` | `_varchar` |  |
| `brand` | `varchar` |  Nullable |

## Table `transactions`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `transaction_id` | `uuid` | Primary |
| `no_invoice` | `varchar` |  Unique |
| `customer_id` | `uuid` |  |
| `tanggal_transaksi` | `timestamptz` |  |
| `total_harga` | `numeric` |  |
| `status` | `varchar` |  |
| `personnel_id` | `uuid` |  Nullable |
| `channel` | `varchar` |  |
| `order_status` | `varchar` |  |
| `payment_status` | `varchar` |  |
| `payment_method` | `varchar` |  Nullable |
| `fulfillment_method` | `varchar` |  Nullable |
| `subtotal` | `numeric` |  |
| `shipping_fee` | `numeric` |  |
| `paid_amount` | `numeric` |  Nullable |
| `change_amount` | `numeric` |  Nullable |

## Table `transaction_items`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `item_id` | `uuid` | Primary |
| `transaction_id` | `uuid` |  |
| `product_id` | `uuid` |  Nullable |
| `nama_barang_snapshot` | `varchar` |  |
| `harga_satuan` | `numeric` |  |
| `qty` | `int4` |  |
| `subtotal` | `numeric` |  |

## Table `personnel`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `personnel_id` | `uuid` | Primary |
| `personnel_type` | `varchar` |  |
| `created_at` | `timestamptz` |  |

## Table `managers`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `manager_id` | `uuid` | Primary |
| `personnel_id` | `uuid` |  Unique |
| `username` | `varchar` |  Unique |
| `password_hash` | `text` |  |
| `nama` | `varchar` |  |
| `created_at` | `timestamptz` |  |

## Table `staff`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `staff_id` | `uuid` | Primary |
| `personnel_id` | `uuid` |  Unique |
| `manager_id` | `uuid` |  Nullable |
| `username` | `varchar` |  Unique |
| `password_hash` | `text` |  |
| `nama` | `varchar` |  |
| `role` | `varchar` |  |
| `created_at` | `timestamptz` |  |

## Table `documents`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `document_id` | `uuid` | Primary |
| `tipe_dokumen` | `varchar` |  |
| `judul` | `varchar` |  |
| `deskripsi` | `text` |  Nullable |
| `file_url` | `text` |  Nullable |
| `status` | `varchar` |  |
| `created_by` | `uuid` |  |
| `transaction_id` | `uuid` |  Nullable |
| `created_at` | `timestamptz` |  |

## Table `messages`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `message_id` | `uuid` | Primary |
| `sender_id` | `uuid` |  |
| `receiver_id` | `uuid` |  Nullable |
| `subject` | `varchar` |  Nullable |
| `body` | `text` |  |
| `is_read` | `bool` |  |
| `created_at` | `timestamptz` |  |

## Table `notifications`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `notification_id` | `uuid` | Primary |
| `tipe` | `varchar` |  |
| `reference_table` | `varchar` |  Nullable |
| `reference_id` | `uuid` |  Nullable |
| `message` | `text` |  |
| `is_read` | `bool` |  |
| `target_personnel_id` | `uuid` |  Nullable |
| `created_at` | `timestamptz` |  |

## Table `shifts`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `shift_id` | `uuid` | Primary |
| `personnel_id` | `uuid` |  |
| `tanggal` | `date` |  |
| `jam_mulai` | `time` |  |
| `jam_selesai` | `time` |  |
| `status_kehadiran` | `varchar` |  |
| `created_by` | `uuid` |  |
| `created_at` | `timestamptz` |  |

## Table `activity_logs`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `log_id` | `uuid` | Primary |
| `personnel_id` | `uuid` |  |
| `action` | `varchar` |  |
| `table_name` | `varchar` |  |
| `record_id` | `uuid` |  Nullable |
| `detail` | `jsonb` |  Nullable |
| `created_at` | `timestamptz` |  |

## Table `workflow_requests`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `request_id` | `uuid` | Primary |
| `tipe_request` | `varchar` |  |
| `reference_table` | `varchar` |  Nullable |
| `reference_id` | `uuid` |  Nullable |
| `deskripsi` | `text` |  Nullable |
| `requested_by` | `uuid` |  |
| `current_status` | `varchar` |  |
| `created_at` | `timestamptz` |  |

## Table `workflow_approvals`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `approval_id` | `uuid` | Primary |
| `request_id` | `uuid` |  Unique |
| `approver_id` | `uuid` |  Nullable |
| `status` | `varchar` |  |
| `catatan` | `text` |  Nullable |
| `approved_at` | `timestamptz` |  Nullable |
| `created_at` | `timestamptz` |  |

## Table `correspondence`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `correspondence_id` | `uuid` | Primary |
| `nomor_agenda` | `varchar` |  Unique |
| `tipe` | `varchar` |  |
| `perihal` | `varchar` |  |
| `asal_tujuan` | `varchar` |  |
| `tanggal_surat` | `date` |  Nullable |
| `tanggal_terima` | `date` |  Nullable |
| `file_url` | `text` |  Nullable |
| `status` | `varchar` |  |
| `created_by` | `uuid` |  |
| `created_at` | `timestamptz` |  |

## Table `correspondence_dispositions`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `disposition_id` | `uuid` | Primary |
| `correspondence_id` | `uuid` |  |
| `disposisi_ke` | `uuid` |  |
| `instruksi` | `text` |  Nullable |
| `status` | `varchar` |  |
| `catatan` | `text` |  Nullable |
| `created_at` | `timestamptz` |  |

## Table `knowledge_categories`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `category_id` | `uuid` | Primary |
| `nama_kategori` | `varchar` |  Unique |
| `deskripsi` | `varchar` |  Nullable |
| `urutan` | `int4` |  Nullable |
| `created_at` | `timestamptz` |  Nullable |

## Table `knowledge_policies`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `policy_id` | `uuid` | Primary |
| `category_id` | `uuid` |  Nullable |
| `judul` | `varchar` |  |
| `ringkasan` | `text` |  |
| `konten` | `text` |  |
| `prioritas` | `int4` |  |
| `nomor_versi` | `varchar` |  |
| `catatan_revisi` | `text` |  Nullable |
| `tags` | `_text` |  Nullable |
| `created_by` | `uuid` |  Nullable |
| `is_published` | `bool` |  Nullable |
| `view_count` | `int4` |  Nullable |
| `created_at` | `timestamptz` |  Nullable |
| `updated_at` | `timestamptz` |  Nullable |

## Table `knowledge_faqs`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `faq_id` | `uuid` | Primary |
| `category_id` | `uuid` |  Nullable |
| `pertanyaan` | `text` |  |
| `jawaban` | `text` |  |
| `nomor_versi` | `varchar` |  |
| `catatan_revisi` | `text` |  Nullable |
| `tags` | `_text` |  Nullable |
| `created_by` | `uuid` |  Nullable |
| `is_published` | `bool` |  Nullable |
| `view_count` | `int4` |  Nullable |
| `created_at` | `timestamptz` |  Nullable |
| `updated_at` | `timestamptz` |  Nullable |

## Table `knowledge_videos`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `video_id` | `uuid` | Primary |
| `category_id` | `uuid` |  Nullable |
| `judul` | `varchar` |  |
| `deskripsi` | `text` |  |
| `video_url` | `varchar` |  |
| `durasi_menit` | `int4` |  |
| `thumbnail_url` | `varchar` |  Nullable |
| `nomor_versi` | `varchar` |  |
| `catatan_revisi` | `text` |  Nullable |
| `tags` | `_text` |  Nullable |
| `created_by` | `uuid` |  Nullable |
| `is_published` | `bool` |  Nullable |
| `view_count` | `int4` |  Nullable |
| `created_at` | `timestamptz` |  Nullable |
| `updated_at` | `timestamptz` |  Nullable |

## Table `knowledge_case_studies`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `case_study_id` | `uuid` | Primary |
| `category_id` | `uuid` |  Nullable |
| `judul` | `varchar` |  |
| `ringkasan` | `text` |  |
| `kronologi` | `text` |  |
| `analisis` | `text` |  |
| `solusi` | `text` |  |
| `pelajaran` | `text` |  |
| `nomor_versi` | `varchar` |  |
| `catatan_revisi` | `text` |  Nullable |
| `tags` | `_text` |  Nullable |
| `created_by` | `uuid` |  Nullable |
| `is_published` | `bool` |  Nullable |
| `view_count` | `int4` |  Nullable |
| `created_at` | `timestamptz` |  Nullable |
| `updated_at` | `timestamptz` |  Nullable |

## Table `knowledge_articles`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `article_id` | `uuid` | Primary |
| `category_id` | `uuid` |  Nullable |
| `judul` | `varchar` |  |
| `ringkasan` | `text` |  |
| `konten` | `text` |  |
| `nomor_versi` | `varchar` |  |
| `catatan_revisi` | `text` |  Nullable |
| `tags` | `_text` |  Nullable |
| `created_by` | `uuid` |  Nullable |
| `is_published` | `bool` |  Nullable |
| `view_count` | `int4` |  Nullable |
| `created_at` | `timestamptz` |  Nullable |
| `updated_at` | `timestamptz` |  Nullable |

## Table `knowledge_attachments`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `attachment_id` | `uuid` | Primary |
| `source_table` | `varchar` |  |
| `source_id` | `uuid` |  |
| `nama_file` | `varchar` |  |
| `file_url` | `varchar` |  |
| `tipe_file` | `varchar` |  |
| `ukuran_bytes` | `int4` |  |
| `created_at` | `timestamptz` |  Nullable |

## Table `knowledge_bookmarks`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `bookmark_id` | `uuid` | Primary |
| `source_table` | `varchar` |  |
| `source_id` | `uuid` |  |
| `personnel_id` | `uuid` |  |
| `created_at` | `timestamptz` |  Nullable |

## Table `knowledge_versions`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `version_id` | `uuid` | Primary |
| `source_table` | `varchar` |  |
| `source_id` | `uuid` |  |
| `nomor_versi` | `varchar` |  |
| `catatan_perubahan` | `text` |  |
| `snapshot_data` | `jsonb` |  |
| `diubah_oleh` | `uuid` |  Nullable |
| `created_at` | `timestamptz` |  Nullable |

## Table `alembic_version`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `version_num` | `varchar` | Primary |

## Table `user_profiles`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `auth_user_id` | `uuid` | Primary |
| `entity_type` | `varchar` |  |
| `entity_id` | `uuid` |  |
| `created_at` | `timestamptz` |  |
| `updated_at` | `timestamptz` |  |

## Table `carts`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `cart_id` | `uuid` | Primary |
| `customer_id` | `uuid` |  Unique |
| `created_at` | `timestamptz` |  |
| `updated_at` | `timestamptz` |  |

## Table `cart_items`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `cart_item_id` | `uuid` | Primary |
| `cart_id` | `uuid` |  |
| `product_id` | `uuid` |  |
| `qty` | `int4` |  |
| `created_at` | `timestamptz` |  |
| `updated_at` | `timestamptz` |  |

## Table `fulfillments`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `fulfillment_id` | `uuid` | Primary |
| `transaction_id` | `uuid` |  Unique |
| `method` | `varchar` |  |
| `status` | `varchar` |  |
| `recipient_name` | `varchar` |  Nullable |
| `recipient_phone` | `varchar` |  Nullable |
| `address` | `text` |  Nullable |
| `distance_km` | `numeric` |  Nullable |
| `rate_per_km` | `numeric` |  Nullable |
| `shipping_fee` | `numeric` |  |
| `tracking_number` | `varchar` |  Nullable |
| `notes` | `text` |  Nullable |
| `created_at` | `timestamptz` |  |
| `updated_at` | `timestamptz` |  |
| `store_id` | `uuid` |  Nullable |
| `shipping_method` | `varchar` |  Nullable |

## Table `customer_addresses`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `address_id` | `uuid` | Primary |
| `customer_id` | `uuid` |  |
| `label` | `varchar` |  |
| `recipient_name` | `varchar` |  |
| `recipient_phone` | `varchar` |  |
| `address` | `text` |  |
| `is_default` | `bool` |  |
| `created_at` | `timestamptz` |  |
| `updated_at` | `timestamptz` |  |

## Table `stores`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `store_id` | `uuid` | Primary |
| `name` | `varchar` |  |
| `address` | `text` |  |
| `google_maps_url` | `text` |  |
| `opening_hours` | `varchar` |  Nullable |
| `is_active` | `bool` |  |

## Table `payments`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `payment_id` | `uuid` | Primary |
| `transaction_id` | `uuid` |  Unique |
| `payment_method` | `varchar` |  |
| `amount` | `numeric` |  |
| `status` | `varchar` |  |
| `reference` | `varchar` |  Nullable |
| `paid_at` | `timestamptz` |  Nullable |
| `created_at` | `timestamptz` |  |

## Table `mis_product_costs`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `cost_id` | `uuid` | Primary |
| `product_id` | `uuid` |  |
| `harga_beli` | `numeric` |  |
| `berlaku_dari` | `date` |  |
| `berlaku_sampai` | `date` |  Nullable |
| `supplier_nama` | `varchar` |  Nullable |
| `catatan` | `text` |  Nullable |
| `created_by` | `uuid` |  Nullable |
| `created_at` | `timestamptz` |  |

## Table `mis_stock_movements`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `movement_id` | `uuid` | Primary |
| `product_id` | `uuid` |  |
| `tipe_mutasi` | `varchar` |  |
| `qty_change` | `int4` |  |
| `stok_sebelum` | `int4` |  |
| `stok_sesudah` | `int4` |  |
| `transaction_id` | `uuid` |  Nullable |
| `alasan` | `text` |  Nullable |
| `created_by` | `uuid` |  Nullable |
| `created_at` | `timestamptz` |  |

## Table `mis_kpi_definitions`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `kpi_id` | `uuid` | Primary |
| `kode_kpi` | `varchar` |  Unique |
| `nama_kpi` | `varchar` |  |
| `deskripsi` | `text` |  Nullable |
| `satuan` | `varchar` |  |
| `rumus_deskripsi` | `text` |  Nullable |
| `sumber_data` | `varchar` |  Nullable |
| `arah_baik` | `varchar` |  |
| `periode_default` | `varchar` |  |
| `is_active` | `bool` |  |
| `created_at` | `timestamptz` |  |
| `updated_at` | `timestamptz` |  |

## Table `mis_kpi_targets`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `target_id` | `uuid` | Primary |
| `kpi_id` | `uuid` |  |
| `personnel_id` | `uuid` |  Nullable |
| `periode_tipe` | `varchar` |  |
| `periode_mulai` | `date` |  |
| `periode_selesai` | `date` |  |
| `nilai_target` | `numeric` |  |
| `nilai_peringatan` | `numeric` |  Nullable |
| `catatan` | `text` |  Nullable |
| `created_by` | `uuid` |  |
| `created_at` | `timestamptz` |  |
| `updated_at` | `timestamptz` |  |

## Table `mis_daily_sales_summary`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `summary_id` | `uuid` | Primary |
| `summary_date` | `date` |  |
| `channel` | `varchar` |  |
| `jumlah_transaksi` | `int4` |  |
| `jumlah_transaksi_batal` | `int4` |  |
| `jumlah_item_terjual` | `int4` |  |
| `gross_sales` | `numeric` |  |
| `pendapatan_ongkir` | `numeric` |  |
| `total_pendapatan` | `numeric` |  |
| `total_hpp` | `numeric` |  |
| `gross_profit` | `numeric` |  |
| `pelanggan_unik` | `int4` |  |
| `pelanggan_baru` | `int4` |  |
| `generated_at` | `timestamptz` |  |

## Table `mis_product_daily_summary`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `summary_id` | `uuid` | Primary |
| `summary_date` | `date` |  |
| `product_id` | `uuid` |  |
| `kategori_snapshot` | `varchar` |  Nullable |
| `brand_snapshot` | `varchar` |  Nullable |
| `qty_terjual` | `int4` |  |
| `pendapatan` | `numeric` |  |
| `total_hpp` | `numeric` |  |
| `profit` | `numeric` |  |
| `stok_akhir` | `int4` |  |
| `generated_at` | `timestamptz` |  |

## Table `iss_es_domains`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `domain_id` | `uuid` | Primary |
| `kode` | `varchar` | Unique |
| `nama` | `varchar` | |
| `deskripsi` | `text` | Nullable |
| `target_role` | `varchar` | |
| `entity_type` | `varchar` | |
| `is_active` | `bool` | |
| `created_at` | `timestamptz` | |

## Table `iss_es_facts`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `fact_id` | `uuid` | Primary |
| `domain_id` | `uuid` | |
| `kode` | `varchar` | |
| `nama` | `varchar` | |
| `pertanyaan` | `text` | Nullable |
| `tipe_nilai` | `varchar` | |
| `sumber_fakta` | `varchar` | |
| `opsi_nilai` | `jsonb` | |
| `urutan` | `int4` | |
| `is_required` | `bool` | |
| `is_active` | `bool` | |

## Table `iss_es_rules`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `rule_id` | `uuid` | Primary |
| `domain_id` | `uuid` | |
| `kode` | `varchar` | |
| `nama` | `varchar` | |
| `kondisi` | `jsonb` | |
| `jenis_konklusi` | `varchar` | |
| `kesimpulan_kode` | `varchar` | |
| `kesimpulan_nilai` | `varchar` | Nullable |
| `kesimpulan_judul` | `varchar` | |
| `penjelasan` | `text` | |
| `rekomendasi` | `jsonb` | |
| `cf_pakar` | `float8` | |
| `prioritas` | `int4` | |
| `knowledge_source_table` | `varchar` | Nullable |
| `knowledge_source_id` | `uuid` | Nullable |
| `status` | `varchar` | |
| `created_by` | `uuid` | Nullable |
| `created_at` | `timestamptz` | |
| `updated_at` | `timestamptz` | |

## Table `iss_es_consultations`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `consultation_id` | `uuid` | Primary |
| `domain_id` | `uuid` | |
| `actor_type` | `varchar` | `personnel` / `customer` / `guest` |
| `personnel_id` | `uuid` | Nullable |
| `customer_id` | `uuid` | Nullable |
| `reference_table` | `varchar` | Nullable |
| `reference_id` | `uuid` | Nullable |
| `user_facts` | `jsonb` | |
| `db_facts` | `jsonb` | |
| `inferred_facts` | `jsonb` | |
| `warnings` | `jsonb` | |
| `workflow_request_id` | `uuid` | Nullable |
| `created_at` | `timestamptz` | |

## Table `iss_es_results`

### Columns

| Name | Type | Constraints |
|------|------|-------------|
| `result_id` | `uuid` | Primary |
| `consultation_id` | `uuid` | |
| `ranking` | `int4` | |
| `kesimpulan_kode` | `varchar` | |
| `kesimpulan_judul` | `varchar` | |
| `cf_kombinasi` | `float8` | |
| `tingkat_keyakinan` | `varchar` | |
| `ringkasan_diagnosis` | `text` | |
| `rekomendasi` | `jsonb` | |
| `matched_rules` | `jsonb` | |
| `matched_products` | `jsonb` | |
| `knowledge_refs` | `jsonb` | |
| `decision` | `varchar` | |
| `decision_by` | `uuid` | Nullable |
| `decision_note` | `text` | Nullable |
| `decided_at` | `timestamptz` | Nullable |
