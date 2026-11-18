from dataclasses import dataclass
from typing import Any

from .core.types import ExpertRuleSpec, FactSpec, RuleClause


@dataclass(frozen=True)
class DomainDefinition:
    code: str
    name: str
    description: str
    target_role: str
    entity_type: str
    facts: list[FactSpec]
    rules: list[ExpertRuleSpec]


def _opt(*pairs: tuple[str, str]) -> list[dict[str, str]]:
    return [{"value": val, "label": label} for val, label in pairs]


def _clause(fact: str, op: str, value: Any) -> RuleClause:
    return RuleClause(fact=fact, op=op, value=value)


CUST_WATCH_ADVISOR = DomainDefinition(
    code="CUST_WATCH_ADVISOR",
    name="Personal Horology & Watch Finder",
    description="Konsultasi pakar pemilihan jam tangan ideal berdasarkan acara, ukuran pergelangan, preferensi mesin, dan anggaran.",
    target_role="customer",
    entity_type="product",
    facts=[
        FactSpec(
            code="C_OCCASION",
            name="Tujuan Pemakaian Utama",
            value_type="enum",
            source="user_input",
            question="Untuk aktivitas atau momen apa jam tangan ini paling sering digunakan?",
            options=_opt(
                ("formal_bisnis", "Acara Formal, Kerja Kantoran & Pertemuan Bisnis"),
                ("kasual_harian", "Pemakaian Kasual Sehari-hari"),
                ("olahraga_outdoor", "Olahraga & Aktivitas Luar Ruangan"),
                ("renang_diving", "Berenang, Snorkeling & Aktivitas Air"),
                ("koleksi_luxury", "Investasi, Prestise & Koleksi Horologi"),
                ("anak_sekolah", "Aktivitas Harian Anak & Sekolah"),
            ),
            order=1,
        ),
        FactSpec(
            code="C_GENDER_PROFILE",
            name="Profil Pemakai",
            value_type="enum",
            source="user_input",
            question="Siapa yang akan mengenakan jam tangan ini?",
            options=_opt(
                ("pria", "Pria Dewasa"),
                ("wanita", "Wanita Dewasa"),
                ("anak", "Anak-anak / Remaja Awal"),
            ),
            order=2,
        ),
        FactSpec(
            code="C_WRIST_SIZE",
            name="Ukuran Pergelangan Tangan",
            value_type="enum",
            source="user_input",
            question="Bagaimana perkiraan lingkar pergelangan tangan pemakai?",
            options=_opt(
                ("kecil_lt_16cm", "Ramping / Kecil (< 16 cm)"),
                ("sedang_16_18cm", "Proporsional / Sedang (16 - 18 cm)"),
                ("besar_gt_18cm", "Besar / Lebar (> 18 cm)"),
            ),
            order=3,
        ),
        FactSpec(
            code="C_MOVEMENT_PREF",
            name="Preferensi Karakter Mesin",
            value_type="enum",
            source="user_input",
            question="Karakter mesin jam tangan seperti apa yang paling Anda sukai?",
            options=_opt(
                ("praktis_quartz", "Praktis & Akurat Tanpa Perlu Diatur Ulang (Quartz)"),
                ("mekanis_automatic", "Seni Mekanikal Tanpa Baterai (Automatic / Mechanical)"),
                ("fitur_smartwatch", "Fitur Pemantau Kesehatan, Olahraga & Notifikasi (Smartwatch)"),
            ),
            order=4,
        ),
        FactSpec(
            code="C_BUDGET_TIER",
            name="Rentang Anggaran",
            value_type="enum",
            source="user_input",
            question="Berapa kisaran anggaran yang Anda siapkan?",
            options=_opt(
                ("ekonomis_lt_2jt", "Di bawah Rp 2.000.000"),
                ("menengah_2jt_5jt", "Rp 2.000.000 s/d Rp 5.000.000"),
                ("premium_gt_5jt", "Di atas Rp 5.000.000"),
            ),
            order=5,
        ),
        FactSpec(
            code="I_WATER_NEED",
            name="Kebutuhan Tahan Air (Fakta Antara)",
            value_type="text",
            source="inferred",
            order=10,
            is_required=False,
        ),
        FactSpec(
            code="I_SIZE_FIT",
            name="Rekomendasi Proporsi Case (Fakta Antara)",
            value_type="text",
            source="inferred",
            order=11,
            is_required=False,
        ),
    ],
    rules=[
        ExpertRuleSpec(
            code="CW-I01",
            name="Derivasi Kebutuhan Ketahanan Air Tinggi",
            conditions=[_clause("C_OCCASION", "in", ["olahraga_outdoor", "renang_diving"])],
            conclusion_kind="intermediate_fact",
            conclusion_code="I_WATER_NEED",
            conclusion_value="high_10atm",
            conclusion_title="Wajib Ketahanan Air >= 10 ATM",
            explanation="Aktivitas air dan olahraga berat membutuhkan ketahanan tekanan air minimal 10 ATM serta material anti-korosi.",
            cf_expert=0.95,
            priority=1,
        ),
        ExpertRuleSpec(
            code="CW-I02",
            name="Derivasi Proporsi Case Ramping",
            conditions=[_clause("C_WRIST_SIZE", "eq", "kecil_lt_16cm")],
            conclusion_kind="intermediate_fact",
            conclusion_code="I_SIZE_FIT",
            conclusion_value="compact_34_38",
            conclusion_title="Proporsi Case Ideal 34-38 mm",
            explanation="Pergelangan tangan di bawah 16 cm terlihat paling proporsional dengan diameter case 34-38 mm agar lug tidak melewati tepi tangan.",
            cf_expert=0.90,
            priority=2,
        ),
        ExpertRuleSpec(
            code="CW-R01",
            name="Executive Mechanical / Automatic Dress Watch",
            conditions=[
                _clause("C_OCCASION", "eq", "formal_bisnis"),
                _clause("C_MOVEMENT_PREF", "eq", "mekanis_automatic"),
                _clause("C_GENDER_PROFILE", "eq", "pria"),
            ],
            conclusion_kind="final_conclusion",
            conclusion_code="REC_EXEC_AUTOMATIC_MEN",
            conclusion_title="Executive Automatic Dress Watch (Pria)",
            explanation="Untuk kebutuhan bisnis formal dengan apresiasi mesin mekanis, jam tangan Automatic berdesain tipis dengan strap kulit atau rantai baja halus memberikan kesan profesional dan berkelas.",
            recommendation={
                "spesifikasi_ideal": "Movement Automatic, Case 38-41mm, Strap Leather/Stainless Steel, Water Resistance 5 ATM",
                "tips_pakar": "Putar crown 15-20 kali saat jam pertama kali dikenakan setelah berhenti.",
                "product_filter": {
                    "categories": ["Jam Tangan Pria", "Jam Tangan Luxury"],
                    "movements": ["automatic", "mechanical"],
                    "strap_materials": ["leather", "stainless_steel"],
                },
            },
            cf_expert=0.92,
            priority=10,
        ),
        ExpertRuleSpec(
            code="CW-R02",
            name="Elegant Women Dress & Daily Timepiece",
            conditions=[
                _clause("C_GENDER_PROFILE", "eq", "wanita"),
                _clause("C_OCCASION", "in", ["formal_bisnis", "kasual_harian", "koleksi_luxury"]),
            ],
            conclusion_kind="final_conclusion",
            conclusion_code="REC_ELEGANT_WOMEN",
            conclusion_title="Elegant Women Horology Collection",
            explanation="Koleksi jam tangan wanita dengan profil case ramping dan dial bersih dirancang untuk menunjang penampilan profesional maupun kasual harian.",
            recommendation={
                "spesifikasi_ideal": "Diameter Case 28-36mm, Bobot Ringan, Kaca Sapphire/Mineral",
                "tips_pakar": "Hindari menyemprotkan parfum langsung ke bagian tali kulit atau seal case.",
                "product_filter": {
                    "categories": ["Jam Tangan Wanita", "Jam Tangan Luxury"],
                    "movements": ["quartz", "automatic"],
                },
            },
            cf_expert=0.90,
            priority=11,
        ),
        ExpertRuleSpec(
            code="CW-R03",
            name="Classic Precision Quartz Everyday Watch",
            conditions=[
                _clause("C_OCCASION", "in", ["formal_bisnis", "kasual_harian"]),
                _clause("C_MOVEMENT_PREF", "eq", "praktis_quartz"),
            ],
            conclusion_kind="final_conclusion",
            conclusion_code="REC_CLASSIC_QUARTZ",
            conclusion_title="Classic Precision Quartz Timepiece",
            explanation="Mesin Quartz memberikan akurasi tinggi dengan deviasi kurang dari 15 detik per bulan dan selalu siap pakai tanpa perlu diatur ulang meski jarang dikenakan.",
            recommendation={
                "spesifikasi_ideal": "Movement Quartz Jepang/Swiss, Water Resistance 3-5 ATM, Perawatan Mudah",
                "tips_pakar": "Ganti baterai segera apabila jarum detik mulai melompat setiap 2 detik.",
                "product_filter": {
                    "categories": ["Jam Tangan Pria", "Jam Tangan Wanita"],
                    "movements": ["quartz"],
                },
            },
            cf_expert=0.90,
            priority=12,
        ),
        ExpertRuleSpec(
            code="CW-R04",
            name="Sport & High Water-Resistance Dive Watch",
            conditions=[
                _clause("I_WATER_NEED", "eq", "high_10atm"),
                _clause("C_MOVEMENT_PREF", "in", ["praktis_quartz", "mekanis_automatic"]),
            ],
            conclusion_kind="final_conclusion",
            conclusion_code="REC_PRO_DIVER_SPORT",
            conclusion_title="Sport & High Water-Resistance Timepiece",
            explanation="Diturunkan dari kebutuhan aktivitas air/olahraga: Anda memerlukan konstruksi case tahan tekanan minimal 10 ATM dengan strap karet (rubber) atau baja tahan karat.",
            recommendation={
                "spesifikasi_ideal": "Water Resistance >= 10 ATM, Screw-down Crown, Strap Rubber/Steel, Luminous Hands",
                "tips_pakar": "Bilas jam tangan dengan air tawar bersih setelah terkena air laut atau klorin kolam renang.",
                "product_filter": {
                    "categories": ["Jam Tangan Pria", "Jam Tangan Wanita", "Jam Tangan Luxury"],
                    "min_water_atm": 10,
                    "strap_materials": ["rubber", "stainless_steel", "nylon"],
                },
            },
            cf_expert=0.94,
            priority=13,
        ),
        ExpertRuleSpec(
            code="CW-R05",
            name="Connected Active Smartwatch",
            conditions=[_clause("C_MOVEMENT_PREF", "eq", "fitur_smartwatch")],
            conclusion_kind="final_conclusion",
            conclusion_code="REC_ACTIVE_SMARTWATCH",
            conclusion_title="Multi-Sensor Connected Smartwatch",
            explanation="Pilihan terbaik bagi Anda yang memprioritaskan pemantauan detak jantung, pelacakan olahraga GPS, serta notifikasi pintar di pergelangan tangan.",
            recommendation={
                "spesifikasi_ideal": "Smartwatch Sensor Detak Jantung & SpO2, Strap Quick-Release Silicone, IP68 / 5 ATM",
                "tips_pakar": "Gunakan adaptor pengisi daya standar agar kesehatan baterai lithium tetap awet.",
                "product_filter": {
                    "categories": ["Smartwatch"],
                },
            },
            cf_expert=0.95,
            priority=14,
        ),
        ExpertRuleSpec(
            code="CW-R06",
            name="Prestige Luxury Horology Timepiece",
            conditions=[
                _clause("C_OCCASION", "eq", "koleksi_luxury"),
                _clause("C_BUDGET_TIER", "eq", "premium_gt_5jt"),
            ],
            conclusion_kind="final_conclusion",
            conclusion_code="REC_PRESTIGE_LUXURY",
            conclusion_title="Prestige Luxury Collector Timepiece",
            explanation="Untuk tujuan koleksi dan prestise pada anggaran premium, lini Jam Tangan Luxury menawarkan penyelesaian akhir (finishing) tingkat tinggi dan ketahanan nilai jangka panjang.",
            recommendation={
                "spesifikasi_ideal": "Sapphire Crystal Anti-Reflective, In-House / High-Grade Movement, Solid 316L/904L Steel",
                "tips_pakar": "Simpan lengkap bersama box asli dan kartu garansi untuk menjaga nilai koleksi.",
                "product_filter": {
                    "categories": ["Jam Tangan Luxury", "Jam Tangan Pria", "Jam Tangan Wanita"],
                },
            },
            cf_expert=0.95,
            priority=15,
        ),
        ExpertRuleSpec(
            code="CW-R07",
            name="Durable Kids Everyday Watch",
            conditions=[_clause("C_GENDER_PROFILE", "eq", "anak")],
            conclusion_kind="final_conclusion",
            conclusion_code="REC_KIDS_DURABLE",
            conclusion_title="Jam Tangan Anak Tahan Benturan & Nyaman",
            explanation="Anak-anak membutuhkan jam tangan berbobot ringan dengan material resin/silikon hipoalergenik yang tahan guncangan dan mudah dibaca.",
            recommendation={
                "spesifikasi_ideal": "Diameter 28-34mm, Material Resin/Silicone Lembut, Kaca Acrylic/Mineral Tahan Benturan",
                "tips_pakar": "Pilih dial dengan angka Arab yang jelas untuk memudahkan anak membaca waktu.",
                "product_filter": {
                    "categories": ["Jam Tangan Anak-anak"],
                },
            },
            cf_expert=0.96,
            priority=16,
        ),
    ],
)


STAFF_POS_CROSSSELL = DomainDefinition(
    code="STAFF_POS_CROSSSELL",
    name="POS Smart Cross-Sell & Bundle Advisor",
    description="Asisten pakar kasir untuk merekomendasikan Strap & Aksesoris yang kompatibel secara teknis dengan jam tangan yang dibeli pelanggan.",
    target_role="kasir",
    entity_type="product",
    facts=[
        FactSpec("P_MAIN_CATEGORY", "Kategori Produk Utama", "text", "db_derived", order=1, is_required=False),
        FactSpec("P_MAIN_PRICE", "Harga Produk Utama (IDR)", "number", "db_derived", order=2, is_required=False),
        FactSpec("P_LUG_WIDTH", "Lebar Lug Tali Jam (mm)", "number", "db_derived", order=3, is_required=False),
        FactSpec("P_STRAP_MATERIAL", "Material Strap Bawaan", "text", "db_derived", order=4, is_required=False),
        FactSpec(
            code="S_BUYER_INTENT",
            name="Tujuan Pembelian Pelanggan",
            value_type="enum",
            source="user_input",
            question="Apa tujuan pembelian jam tangan ini menurut pelanggan?",
            options=_opt(
                ("pakai_pribadi", "Dipakai Sendiri"),
                ("hadiah_kado", "Untuk Hadiah / Kado Spesial"),
                ("kolektor_jam", "Menambah Koleksi Pribadi"),
            ),
            order=5,
        ),
        FactSpec(
            code="S_USAGE_STYLE",
            name="Gaya Pemakaian Dominan",
            value_type="enum",
            source="user_input",
            question="Bagaimana rencana gaya pemakaian pelanggan?",
            options=_opt(
                ("kantoran_formal", "Fokus Kerja Kantoran / Acara Resmi"),
                ("fleksibel_harian", "Ingin Fleksibel Formal & Santai"),
                ("outdoor_aktif", "Sering Aktivitas Luar Ruangan / Berkeringat"),
            ),
            order=6,
        ),
    ],
    rules=[
        ExpertRuleSpec(
            code="SC-R01",
            name="Cross-Sell Strap Kulit Formal untuk Jam Rantai/Rubber",
            conditions=[
                _clause("P_MAIN_CATEGORY", "in", ["Jam Tangan Pria", "Jam Tangan Wanita", "Jam Tangan Luxury"]),
                _clause("P_STRAP_MATERIAL", "in", ["stainless_steel", "rubber", "nylon"]),
                _clause("S_USAGE_STYLE", "in", ["kantoran_formal", "fleksibel_harian"]),
            ],
            conclusion_kind="final_conclusion",
            conclusion_code="BUNDLE_FORMAL_LEATHER_STRAP",
            conclusion_title="Rekomendasi Cross-Sell: Strap Kulit (Leather) Ukuran Lug Kompatibel",
            explanation="Pelanggan membeli jam dengan rantai baja/rubber namun membutuhkan tampilan formal/fleksibel. Menambahkan strap kulit cadangan dengan ukuran lug yang sama mengubah tampilan jam menjadi dress watch.",
            recommendation={
                "talking_point_kasir": "Bapak/Ibu, jam ini menggunakan rantai/rubber bawaan. Dengan menambah strap kulit ukuran lug yang pas, Bapak/Ibu bisa mendapatkan dua gaya sekaligus untuk acara resmi.",
                "product_filter": {
                    "categories": ["Strap & Aksesoris"],
                    "strap_materials": ["leather"],
                    "match_lug_width": True,
                },
            },
            cf_expert=0.88,
            priority=10,
        ),
        ExpertRuleSpec(
            code="SC-R02",
            name="Cross-Sell Strap Rubber/Nylon Pelindung Strap Kulit Bawaan",
            conditions=[
                _clause("P_STRAP_MATERIAL", "eq", "leather"),
                _clause("S_USAGE_STYLE", "in", ["outdoor_aktif", "fleksibel_harian"]),
            ],
            conclusion_kind="final_conclusion",
            conclusion_code="BUNDLE_SPORT_RUBBER_STRAP",
            conclusion_title="Rekomendasi Cross-Sell: Strap Rubber / Nylon Tahan Keringat",
            explanation="Tali kulit bawaan rentan lembap dan berbau jika sering terkena keringat atau aktivitas luar ruangan. Strap rubber/nylon cadangan melindungi keawetan tali kulit asli.",
            recommendation={
                "talking_point_kasir": "Agar tali kulit asli jam ini tetap awet dan tidak cepat rusak terkena keringat saat aktivitas luar ruangan, kami sarankan menambah strap rubber/nylon ukuran lug yang sesuai.",
                "product_filter": {
                    "categories": ["Strap & Aksesoris"],
                    "strap_materials": ["rubber", "nylon", "silicone"],
                    "match_lug_width": True,
                },
            },
            cf_expert=0.92,
            priority=11,
        ),
        ExpertRuleSpec(
            code="SC-R03",
            name="Paket Pelengkap Hadiah / Kolektor",
            conditions=[_clause("S_BUYER_INTENT", "in", ["hadiah_kado", "kolektor_jam"])],
            conclusion_kind="final_conclusion",
            conclusion_code="BUNDLE_GIFT_COLLECTOR_ACC",
            conclusion_title="Rekomendasi Bundle: Aksesoris & Strap Ekstra untuk Hadiah/Koleksi",
            explanation="Pembeli untuk hadiah atau kolektor memiliki konversi tinggi terhadap paket pelengkap penampilan (strap cadangan atau aksesoris perawatan).",
            recommendation={
                "talking_point_kasir": "Karena jam ini untuk hadiah/koleksi spesial, menambahkan satu strap cadangan di dalam paket akan membuat penerimanya memiliki opsi warna tambahan.",
                "product_filter": {
                    "categories": ["Strap & Aksesoris"],
                    "match_lug_width": True,
                },
            },
            cf_expert=0.86,
            priority=12,
        ),
        ExpertRuleSpec(
            code="SC-R04",
            name="Cross-Sell Strap Cadangan Smartwatch",
            conditions=[_clause("P_MAIN_CATEGORY", "eq", "Smartwatch")],
            conclusion_kind="final_conclusion",
            conclusion_code="BUNDLE_SMARTWATCH_STRAP",
            conclusion_title="Rekomendasi Cross-Sell: Strap Quick-Release Smartwatch",
            explanation="Pengguna Smartwatch sangat sering mengganti strap antara sesi olahraga (silicone) dan jam kerja (leather/steel).",
            recommendation={
                "talking_point_kasir": "Smartwatch ini mendukung penggantian tali cepat (quick-release). Kami memiliki pilihan strap kompatibel agar mudah diganti antara olahraga dan kerja.",
                "product_filter": {
                    "categories": ["Strap & Aksesoris"],
                    "match_lug_width": True,
                },
            },
            cf_expert=0.90,
            priority=13,
        ),
    ],
)


WAREHOUSE_QC_INBOUND = DomainDefinition(
    code="WAREHOUSE_QC_INBOUND",
    name="Inspeksi Kualitas Penerimaan PO (Inbound QC)",
    description="Sistem pakar staf gudang untuk mengevaluasi barang datang dari Purchase Order (PO) supplier dan memutuskan penerimaan, retur, atau karantina batch.",
    target_role="gudang",
    entity_type="purchase",
    facts=[
        FactSpec("W_PO_DEFECT_PCT", "Persentase Unit Rusak pada PO (%)", "number", "db_derived", order=1, is_required=False),
        FactSpec("W_PO_SHORTAGE_PCT", "Persentase Kekurangan Kirim (%)", "number", "db_derived", order=2, is_required=False),
        FactSpec("W_PO_DELAY_DAYS", "Keterlambatan Pengiriman (Hari)", "number", "db_derived", order=3, is_required=False),
        FactSpec("W_PO_DEFECT_QTY", "Total Unit Rusak (Qty)", "number", "db_derived", order=4, is_required=False),
        FactSpec(
            code="W_BOX_CONDITION",
            name="Kondisi Kemasan Kargo / Kardus",
            value_type="enum",
            source="user_input",
            question="Bagaimana kondisi fisik kardus/segel pengiriman saat tiba di gudang?",
            options=_opt(
                ("utuh_tersegel", "Utuh & Segel Rapi"),
                ("penyok_ringan", "Penyok Ringan di Luar, Segel Utuh"),
                ("rusak_berat_terbuka", "Kemasan Rusak Berat / Basah / Segel Terbuka"),
            ),
            order=5,
        ),
        FactSpec(
            code="W_DEFECT_SEVERITY",
            name="Temuan Cacat pada Sampel Fisik",
            value_type="enum",
            source="user_input",
            question="Apa temuan utama dari pemeriksaan fisik unit jam tangan?",
            options=_opt(
                ("tidak_ada_cacat", "Seluruh Unit Normal & Sesuai Spesifikasi PO"),
                ("cacat_kosmetik_baret", "Cacat Kosmetik (Baret Case/Kaca/Strap)"),
                ("cacat_fungsi_mesin_mati", "Cacat Fungsi (Mesin Mati / Crown Lepas)"),
                ("salah_model_sku", "Model / Nomor Seri Tidak Sesuai PO"),
            ),
            order=6,
        ),
    ],
    rules=[
        ExpertRuleSpec(
            code="WQ-R01",
            name="Karantina Batch & Klaim Retur Supplier (Cacat Berat / Segel Rusak)",
            conditions=[_clause("W_BOX_CONDITION", "eq", "rusak_berat_terbuka")],
            conclusion_kind="final_conclusion",
            conclusion_code="QC_HOLD_AND_ESCALATE",
            conclusion_title="KARANTINA BATCH: Kemasan/Segel Rusak — Tahan Stok & Eskalasi",
            explanation="Kemasan tiba dalam kondisi rusak berat atau segel terbuka. Sesuai SOP Gudang, batch tidak boleh langsung digabung ke rak utama sebelum dibuat Berita Acara Pemeriksaan.",
            recommendation={
                "prosedur_gudang": "1. Pisahkan seluruh batch di area karantina. 2. Foto kemasan & unit. 3. Unggah Berita Acara di OAS Documents. 4. Ajukan Workflow return_out untuk unit terdampak.",
                "workflow_action": {
                    "can_trigger": True,
                    "tipe_mutasi": "return_out",
                    "alasan_template": "Retur supplier dari QC Inbound: kemasan rusak / cacat batch PO.",
                },
            },
            cf_expert=0.95,
            priority=1,
        ),
        ExpertRuleSpec(
            code="WQ-R02",
            name="Karantina Batch karena Rasio Cacat >= 15% atau Salah SKU",
            conditions=[_clause("W_PO_DEFECT_PCT", "gte", 15)],
            conclusion_kind="final_conclusion",
            conclusion_code="QC_HOLD_AND_ESCALATE",
            conclusion_title="KARANTINA BATCH: Rasio Cacat Melebihi Ambang Toleransi (>= 15%)",
            explanation="Persentase barang rusak pada PO ini mencapai atau melebihi batas toleransi 15%, mengindikasikan kegagalan kontrol kualitas batch dari supplier.",
            recommendation={
                "prosedur_gudang": "Tahan penerimaan batch, dokumentasikan bukti cacat di OAS Documents, dan ajukan Workflow return_out untuk pengembalian ke supplier.",
                "workflow_action": {
                    "can_trigger": True,
                    "tipe_mutasi": "return_out",
                    "alasan_template": "Retur supplier: rasio cacat PO >= 15% pada inspeksi Inbound QC.",
                },
            },
            cf_expert=0.94,
            priority=2,
        ),
        ExpertRuleSpec(
            code="WQ-R03",
            name="Karantina karena Salah Model SKU",
            conditions=[_clause("W_DEFECT_SEVERITY", "eq", "salah_model_sku")],
            conclusion_kind="final_conclusion",
            conclusion_code="QC_HOLD_AND_ESCALATE",
            conclusion_title="KARANTINA BATCH: Ketidaksesuaian Model / SKU dengan Dokumen PO",
            explanation="Barang yang dikirim tidak sesuai dengan spesifikasi SKU pada Purchase Order sehingga akan mengacaukan saldo stok per produk bila dimasukkan.",
            recommendation={
                "prosedur_gudang": "Jangan catat mutasi purchase_in untuk SKU yang salah. Buat pengajuan retur supplier dan hubungi Manajer Pengadaan.",
                "workflow_action": {
                    "can_trigger": True,
                    "tipe_mutasi": "return_out",
                    "alasan_template": "Retur supplier: pengiriman salah model/SKU pada PO.",
                },
            },
            cf_expert=0.96,
            priority=3,
        ),
        ExpertRuleSpec(
            code="WQ-R04",
            name="Penerimaan Parsial + Pengajuan Retur Unit Cacat",
            conditions=[
                _clause("W_PO_DEFECT_PCT", "gt", 0),
                _clause("W_PO_DEFECT_PCT", "lt", 15),
                _clause("W_DEFECT_SEVERITY", "in", ["cacat_kosmetik_baret", "cacat_fungsi_mesin_mati"]),
            ],
            conclusion_kind="final_conclusion",
            conclusion_code="QC_PARTIAL_ACCEPT_RETURN_DEFECT",
            conclusion_title="TERIMA PARSIAL: Masukkan Unit Lulus QC & Retur Unit Cacat",
            explanation="Terdapat unit rusak di bawah ambang 15% dengan kemasan utama masih layak. Unit yang lulus inspeksi dapat masuk ke stok penjualan, sedangkan unit cacat diajukan ke Workflow return_out.",
            recommendation={
                "prosedur_gudang": "1. Pastikan qty_rusak tercatat pada item PO. 2. Masukkan stok unit bagus ke rak utama. 3. Ajukan Workflow return_out untuk unit cacat.",
                "workflow_action": {
                    "can_trigger": True,
                    "tipe_mutasi": "return_out",
                    "alasan_template": "Retur unit cacat hasil pemeriksaan Inbound QC PO.",
                },
            },
            cf_expert=0.90,
            priority=5,
        ),
        ExpertRuleSpec(
            code="WQ-R05",
            name="Lulus QC Fisik dengan Catatan Keterlambatan Pengiriman",
            conditions=[
                _clause("W_PO_DEFECT_PCT", "eq", 0),
                _clause("W_DEFECT_SEVERITY", "eq", "tidak_ada_cacat"),
                _clause("W_PO_DELAY_DAYS", "gt", 2),
            ],
            conclusion_kind="final_conclusion",
            conclusion_code="QC_ACCEPT_WITH_SLA_WARNING",
            conclusion_title="LULUS QC FISIK (Catatan Peringatan SLA Keterlambatan Supplier)",
            explanation="Fisik barang 100% lulus pemeriksaan kualitas, namun pengiriman terlambat lebih dari 2 hari dari tanggal estimasi terima.",
            recommendation={
                "prosedur_gudang": "Masukkan seluruh barang ke stok gudang (purchase_in). Catatan keterlambatan ini otomatis memperbarui metrik ketepatan waktu pada evaluasi DSS SUPPLIER.",
                "workflow_action": {"can_trigger": False},
            },
            cf_expert=0.88,
            priority=6,
        ),
        ExpertRuleSpec(
            code="WQ-R06",
            name="Lulus QC Penuh Sesuai Standar",
            conditions=[
                _clause("W_PO_DEFECT_PCT", "eq", 0),
                _clause("W_DEFECT_SEVERITY", "eq", "tidak_ada_cacat"),
                _clause("W_BOX_CONDITION", "in", ["utuh_tersegel", "penyok_ringan"]),
            ],
            conclusion_kind="final_conclusion",
            conclusion_code="QC_ACCEPT_FULL",
            conclusion_title="LULUS QC PENUH: Barang Siap Masuk Stok Penjualan",
            explanation="Seluruh pemeriksaan kuantitas, kondisi fisik, dan kesesuaian SKU memenuhi standar kualitas gudang Dewa Jam.",
            recommendation={
                "prosedur_gudang": "Tempatkan unit pada rak sesuai kategori dan pastikan mutasi purchase_in tercatat.",
                "workflow_action": {"can_trigger": False},
            },
            cf_expert=0.96,
            priority=7,
        ),
    ],
)


WAREHOUSE_STOCK_ANOMALY = DomainDefinition(
    code="WAREHOUSE_STOCK_ANOMALY",
    name="Diagnosa Selisih Stok & Klasifikasi Mutasi",
    description="Memandu staf gudang menentukan jenis pengajuan Workflow mutasi stok (damaged, adjustment, return_in, return_out) beserta syarat dokumen buktinya.",
    target_role="gudang",
    entity_type="product",
    facts=[
        FactSpec("W_SYS_STOCK", "Stok Sistem Saat Ini (Unit)", "number", "db_derived", order=1, is_required=False),
        FactSpec("W_ROP", "Reorder Point Produk", "number", "db_derived", order=2, is_required=False),
        FactSpec("W_UNIT_COST", "Harga Beli HPP per Unit (IDR)", "number", "db_derived", order=3, is_required=False),
        FactSpec("W_MOVEMENT_30D", "Frekuensi Mutasi 30 Hari Terakhir", "number", "db_derived", order=4, is_required=False),
        FactSpec(
            code="W_ANOMALY_TYPE",
            name="Jenis Temuan di Gudang",
            value_type="enum",
            source="user_input",
            question="Apa jenis temuan fisik atau anomali stok yang Anda hadapi?",
            options=_opt(
                ("unit_rusak_di_rak", "Ditemukan Unit Fisik Rusak / Cacat di Rak Gudang"),
                ("stok_fisik_kurang_hilang", "Stok Fisik Lebih Sedikit dari Sistem (Selisih Kurang Opname)"),
                ("stok_fisik_lebih", "Stok Fisik Lebih Banyak dari Sistem (Selisih Lebih Opname)"),
                ("retur_masuk_pembeli", "Penerimaan Barang Retur dari Pelanggan"),
                ("retur_keluar_supplier", "Pengembalian Barang Rusak/Retur ke Supplier"),
            ),
            order=5,
        ),
        FactSpec(
            code="W_DIFF_QTY",
            name="Jumlah Unit Terdampak / Selisih",
            value_type="number",
            source="user_input",
            question="Berapa jumlah unit yang rusak, selisih, atau diretur? (Masukkan angka positif)",
            order=6,
        ),
        FactSpec(
            code="W_HAS_DOC_PROOF",
            name="Ketersediaan Dokumen Bukti di OAS Documents",
            value_type="enum",
            source="user_input",
            question="Apakah foto bukti fisik / Berita Acara Stock Opname sudah diunggah ke menu Dokumen Internal (OAS)?",
            options=_opt(
                ("sudah_ada", "Sudah Diunggah ke Dokumen Internal"),
                ("belum_ada", "Belum Diunggah"),
            ),
            order=7,
        ),
    ],
    rules=[
        ExpertRuleSpec(
            code="WS-R01",
            name="Klasifikasi Mutasi Barang Rusak Fisik (damaged)",
            conditions=[_clause("W_ANOMALY_TYPE", "eq", "unit_rusak_di_rak")],
            conclusion_kind="final_conclusion",
            conclusion_code="MUTASI_DAMAGED_WORKFLOW",
            conclusion_title="Gunakan Workflow Mutasi 'damaged' (Barang Rusak)",
            explanation="Karena fisik barang yang rusak ditemukan secara nyata di gudang, jangan gunakan 'adjustment'. Gunakan tipe 'damaged' agar laporan kerugian inventori di MIS tercatat akurat.",
            recommendation={
                "tipe_mutasi_wajib": "damaged",
                "syarat_dokumen": "Wajib melampirkan foto unit rusak dan nomor seri pada Dokumen Internal OAS apabila nilai HPP signifikan.",
                "workflow_action": {
                    "can_trigger": True,
                    "tipe_mutasi": "damaged",
                    "alasan_template": "Penghapusan stok unit rusak di gudang hasil pemeriksaan fisik.",
                },
            },
            cf_expert=0.95,
            priority=1,
        ),
        ExpertRuleSpec(
            code="WS-R02",
            name="Peringatan Pengajuan Adjustment Tanpa Berita Acara",
            conditions=[
                _clause("W_ANOMALY_TYPE", "in", ["stok_fisik_kurang_hilang", "stok_fisik_lebih"]),
                _clause("W_HAS_DOC_PROOF", "eq", "belum_ada"),
            ],
            conclusion_kind="final_conclusion",
            conclusion_code="MUTASI_ADJUSTMENT_NEED_DOC",
            conclusion_title="TAHAN PENGAJUAN: Unggah Berita Acara Stock Opname Terlebih Dahulu",
            explanation="Selisih jumlah stok fisik tanpa wujud barang rusak diklasifikasikan sebagai 'adjustment', namun SOP Manajer mewajibkan lampiran Berita Acara Stock Opname sebelum pengajuan disetujui.",
            recommendation={
                "tipe_mutasi_wajib": "adjustment",
                "syarat_dokumen": "1. Hitung ulang rak terkait & cek riwayat PO/Transaksi batal. 2. Unggah Berita Acara Opname di menu Dokumen Internal. 3. Baru ajukan Workflow adjustment.",
                "workflow_action": {"can_trigger": False},
            },
            cf_expert=0.94,
            priority=2,
        ),
        ExpertRuleSpec(
            code="WS-R03",
            name="Klasifikasi Penyesuaian Stok Opname Siap Ajukan (adjustment)",
            conditions=[
                _clause("W_ANOMALY_TYPE", "in", ["stok_fisik_kurang_hilang", "stok_fisik_lebih"]),
                _clause("W_HAS_DOC_PROOF", "eq", "sudah_ada"),
            ],
            conclusion_kind="final_conclusion",
            conclusion_code="MUTASI_ADJUSTMENT_READY",
            conclusion_title="Siap Ajukan Workflow Mutasi 'adjustment' (Koreksi Stock Opname)",
            explanation="Dokumen bukti Berita Acara sudah tersedia. Anda dapat langsung mengajukan koreksi stok melalui Workflow Approval.",
            recommendation={
                "tipe_mutasi_wajib": "adjustment",
                "syarat_dokumen": "Pastikan tanda perubahan stok sesuai (negatif untuk selisih kurang, positif untuk selisih lebih).",
                "workflow_action": {
                    "can_trigger": True,
                    "tipe_mutasi": "adjustment",
                    "alasan_template": "Koreksi selisih stok hasil Stock Opname terverifikasi.",
                },
            },
            cf_expert=0.92,
            priority=3,
        ),
        ExpertRuleSpec(
            code="WS-R04",
            name="Klasifikasi Mutasi Retur Masuk Pelanggan (return_in)",
            conditions=[_clause("W_ANOMALY_TYPE", "eq", "retur_masuk_pembeli")],
            conclusion_kind="final_conclusion",
            conclusion_code="MUTASI_RETURN_IN_WORKFLOW",
            conclusion_title="Gunakan Workflow Mutasi 'return_in' (Retur Masuk)",
            explanation="Barang yang dikembalikan pelanggan dalam kondisi layak masuk kembali ke inventori wajib diajukan melalui Workflow 'return_in' dengan mencantumkan referensi transaksi.",
            recommendation={
                "tipe_mutasi_wajib": "return_in",
                "syarat_dokumen": "Sertakan nomor invoice transaksi asal pada alasan pengajuan.",
                "workflow_action": {
                    "can_trigger": True,
                    "tipe_mutasi": "return_in",
                    "alasan_template": "Penerimaan kembali barang retur pelanggan ke gudang.",
                },
            },
            cf_expert=0.92,
            priority=4,
        ),
        ExpertRuleSpec(
            code="WS-R05",
            name="Klasifikasi Mutasi Retur Keluar ke Supplier (return_out)",
            conditions=[_clause("W_ANOMALY_TYPE", "eq", "retur_keluar_supplier")],
            conclusion_kind="final_conclusion",
            conclusion_code="MUTASI_RETURN_OUT_WORKFLOW",
            conclusion_title="Gunakan Workflow Mutasi 'return_out' (Retur ke Supplier)",
            explanation="Pengeluaran barang dari gudang untuk dikembalikan ke supplier mengurangi stok aktif dan wajib melalui persetujuan Workflow 'return_out'.",
            recommendation={
                "tipe_mutasi_wajib": "return_out",
                "syarat_dokumen": "Cantumkan nomor PO supplier terkait pada deskripsi pengajuan.",
                "workflow_action": {
                    "can_trigger": True,
                    "tipe_mutasi": "return_out",
                    "alasan_template": "Pengembalian unit retur kepada supplier resmi.",
                },
            },
            cf_expert=0.92,
            priority=5,
        ),
    ],
)


MGR_KPI_DIAGNOSTIC = DomainDefinition(
    code="MGR_KPI_DIAGNOSTIC",
    name="Executive KPI, MIS & DSS Diagnostic",
    description="Diagnosis akar masalah performa bisnis secara otomatis lintas data MIS (Sales, Margin, HPP) dan DSS (Restock, Promo, Supplier).",
    target_role="manager",
    entity_type="kpi",
    facts=[
        FactSpec("M_KPI_MARGIN_PCT", "Gross Margin Aktual 30 Hari (%)", "number", "db_derived", order=1, is_required=False),
        FactSpec("M_KPI_STOCKOUT_PCT", "Rasio SKU Stockout Saat Ini (%)", "number", "db_derived", order=2, is_required=False),
        FactSpec("M_COST_HIKE_SKU_COUNT", "Jumlah SKU Mengalami Kenaikan HPP", "number", "db_derived", order=3, is_required=False),
        FactSpec("M_DSS_RESTOCK_URGENT_COUNT", "SKU Status 'Restock Segera' di DSS", "number", "db_derived", order=4, is_required=False),
        FactSpec("M_DSS_PROMO_AGGRESSIVE_COUNT", "SKU Status 'Promo Agresif' di DSS", "number", "db_derived", order=5, is_required=False),
        FactSpec("M_DSS_PROMO_BLOCKED_COUNT", "SKU Promo Tertahan Margin Minimum", "number", "db_derived", order=6, is_required=False),
        FactSpec("M_PENDING_WORKFLOW_COUNT", "Antrean Workflow Pending Approval", "number", "db_derived", order=7, is_required=False),
        FactSpec(
            code="M_FOCUS_AREA",
            name="Fokus Evaluasi Eksekutif",
            value_type="enum",
            source="user_input",
            question="Area manajemen mana yang ingin Anda prioritaskan dalam sesi diagnosis ini?",
            options=_opt(
                ("semua_aspek", "Diagnosis Menyeluruh (Margin, Stok, DSS & Operasional)"),
                ("profitabilitas_margin", "Fokus Profitabilitas, HPP & Strategi Harga"),
                ("kesehatan_stok_gudang", "Fokus Ketersediaan Stok, Restock & Perputaran Barang"),
            ),
            order=8,
        ),
    ],
    rules=[
        ExpertRuleSpec(
            code="MK-R01",
            name="Diagnosis Erosi Margin Akibat Kenaikan HPP Supplier",
            conditions=[
                _clause("M_KPI_MARGIN_PCT", "lt", 35),
                _clause("M_COST_HIKE_SKU_COUNT", "gt", 0),
            ],
            conclusion_kind="final_conclusion",
            conclusion_code="DIAG_MARGIN_COMPRESSION_SUPPLIER",
            conclusion_title="Tekanan Gross Margin Akibat Kenaikan Harga Beli (HPP) Supplier",
            explanation="Data MIS menunjukkan adanya produk yang mengalami kenaikan harga beli di tabel biaya produk sehingga menekan rata-rata persentase Gross Margin toko.",
            recommendation={
                "langkah_strategis": [
                    "Buka modul DSS Skenario SUPPLIER untuk mengevaluasi Indeks Harga (S1) dan mencari supplier alternatif yang lebih kompetitif.",
                    "Tinjau penyesuaian harga jual ritel pada menu Master Data Produk untuk SKU yang mengalami kenaikan HPP.",
                ],
                "modul_terkait": "/internal/dss/SUPPLIER",
            },
            cf_expert=0.90,
            priority=1,
        ),
        ExpertRuleSpec(
            code="MK-R02",
            name="Diagnosis Risiko Kehilangan Penjualan pada SKU Prioritas (Restock Segera)",
            conditions=[_clause("M_DSS_RESTOCK_URGENT_COUNT", "gte", 1)],
            conclusion_kind="final_conclusion",
            conclusion_code="DIAG_CRITICAL_STOCKOUT_RISK",
            conclusion_title="Risiko Kehabisan Stok (Stockout) pada Produk Berkecepatan Jual Tinggi",
            explanation="Hasil perhitungan DSS RESTOCK mendeteksi adanya produk dengan Days of Cover kritis dan kecepatan jual tinggi yang berstatus 'Restock Segera'.",
            recommendation={
                "langkah_strategis": [
                    "Tinjau dan setujui rekomendasi kuantitas pesanan (qty_pesan) pada hasil run DSS RESTOCK terbaru.",
                    "Prioritaskan pemesanan ke supplier yang memiliki Lead Time (S2) tercepat dan Fill Rate (S3) tertinggi.",
                ],
                "modul_terkait": "/internal/dss/RESTOCK",
            },
            cf_expert=0.94,
            priority=2,
        ),
        ExpertRuleSpec(
            code="MK-R03",
            name="Diagnosis Rasio Stockout Katalog Tinggi",
            conditions=[_clause("M_KPI_STOCKOUT_PCT", "gte", 15)],
            conclusion_kind="final_conclusion",
            conclusion_code="DIAG_CRITICAL_STOCKOUT_RISK",
            conclusion_title="Peringatan KPI Stockout Rate Tinggi (>= 15% Katalog Habis)",
            explanation="Lebih dari 15% SKU di katalog saat ini memiliki stok nol, yang menurunkan konversi penjualan baik di POS maupun Marketplace.",
            recommendation={
                "langkah_strategis": [
                    "Jalankan ulang analisis DSS RESTOCK untuk seluruh kategori.",
                    "Periksa apakah ada PO supplier yang terlambat diterima di gudang.",
                ],
                "modul_terkait": "/internal/mis/inventory",
            },
            cf_expert=0.88,
            priority=3,
        ),
        ExpertRuleSpec(
            code="MK-R04",
            name="Diagnosis Modal Tertahan & Deadlock Diskon Promo DSS",
            conditions=[
                _clause("M_DSS_PROMO_AGGRESSIVE_COUNT", "gte", 1),
                _clause("M_DSS_PROMO_BLOCKED_COUNT", "gte", 1),
            ],
            conclusion_kind="final_conclusion",
            conclusion_code="DIAG_SLOW_MOVING_MARGIN_DEADLOCK",
            conclusion_title="Deadlock Stok Lambat: Butuh Promo Agresif Namun Terkunci Margin Minimum",
            explanation="Terdapat SKU slow-moving dengan modal tertahan tinggi di DSS PROMO, tetapi ruang marginnya terlalu tipis sehingga diskon otomatis terkunci oleh batas margin_min_pct.",
            recommendation={
                "langkah_strategis": [
                    "Gunakan strategi Bundling di POS (gabungkan jam slow-moving dengan Strap/Aksesoris bermargin tinggi) alih-alih memotong harga tunggal.",
                    "Atau jalankan simulasi DSS PROMO dengan menurunkan parameter margin_min_pct khusus untuk likuidasi modal.",
                ],
                "modul_terkait": "/internal/dss/PROMO",
            },
            cf_expert=0.88,
            priority=4,
        ),
        ExpertRuleSpec(
            code="MK-R05",
            name="Diagnosis Bottleneck Antrean Persetujuan Workflow",
            conditions=[_clause("M_PENDING_WORKFLOW_COUNT", "gte", 1)],
            conclusion_kind="final_conclusion",
            conclusion_code="DIAG_WORKFLOW_APPROVAL_BOTTLENECK",
            conclusion_title="Terdapat Antrean Workflow Mutasi / Restock yang Menunggu Keputusan Manajer",
            explanation="Penundaan persetujuan workflow menyebabkan stok tercatat di sistem belum mencerminkan kondisi fisik terbaru di gudang.",
            recommendation={
                "langkah_strategis": [
                    "Buka menu Workflow Approval atau gunakan domain pakar 'Workflow Risk & Approval Advisor' untuk mempercepat verifikasi.",
                ],
                "modul_terkait": "/internal/workflows",
            },
            cf_expert=0.84,
            priority=5,
        ),
        ExpertRuleSpec(
            code="MK-R06",
            name="Kondisi Operasional & Margin Terkendali",
            conditions=[
                _clause("M_KPI_STOCKOUT_PCT", "lt", 15),
                _clause("M_DSS_RESTOCK_URGENT_COUNT", "eq", 0),
            ],
            conclusion_kind="final_conclusion",
            conclusion_code="DIAG_OPERATIONAL_HEALTHY",
            conclusion_title="Stabilitas Inventori & Operasional Berada dalam Batas Aman",
            explanation="Rasio ketersediaan stok katalog terjaga baik dan tidak ditemukan antrean SKU berstatus Restock Segera yang darurat.",
            recommendation={
                "langkah_strategis": [
                    "Pertahankan pemantauan berkala pada laporan profitabilitas MIS dan evaluasi kuartalan supplier.",
                ],
                "modul_terkait": "/internal/mis/profitability",
            },
            cf_expert=0.82,
            priority=10,
        ),
    ],
)


MGR_WORKFLOW_APPROVAL = DomainDefinition(
    code="MGR_WORKFLOW_APPROVAL",
    name="Workflow Risk & Approval Advisor",
    description="Evaluasi risiko finansial HPP dan kelengkapan bukti dokumen sebelum Manajer menyetujui atau menolak pengajuan Workflow.",
    target_role="manager",
    entity_type="workflow",
    facts=[
        FactSpec("MW_REQ_TYPE", "Tipe Pengajuan Workflow", "text", "db_derived", order=1, is_required=False),
        FactSpec("MW_QTY_ABS", "Kuantitas Unit Mutasi", "number", "db_derived", order=2, is_required=False),
        FactSpec("MW_FINANCIAL_VALUE", "Estimasi Nilai Finansial HPP (IDR)", "number", "db_derived", order=3, is_required=False),
        FactSpec("MW_HAS_ATTACHMENT", "Lampiran Dokumen Bukti OAS", "text", "db_derived", order=4, is_required=False),
        FactSpec("MW_RESULTING_STOCK", "Proyeksi Stok Akhir (Unit)", "number", "db_derived", order=5, is_required=False),
        FactSpec(
            code="MW_VERIFICATION_LEVEL",
            name="Hasil Verifikasi Alasan Pengajuan Staf",
            value_type="enum",
            source="user_input",
            question="Bagaimana penilaian Anda terhadap kronologi/alasan yang ditulis staf pada request ini?",
            options=_opt(
                ("alasan_jelas_terverifikasi", "Kronologi Jelas, Masuk Akal & Sesuai Operasional"),
                ("alasan_kurang_lengkap", "Alasan Terlalu Singkat / Belum Menjelaskan Penyebab"),
                ("indikasi_duplikat_input", "Terindikasi Duplikasi Pengajuan / Salah Pilih Produk"),
            ),
            order=6,
        ),
    ],
    rules=[
        ExpertRuleSpec(
            code="MW-R01",
            name="Tolak Mutasi Bernilai Tinggi (>= Rp 1,5 Juta) Tanpa Lampiran Dokumen Bukti",
            conditions=[
                _clause("MW_REQ_TYPE", "in", ["stock_adjustment", "stock_damaged"]),
                _clause("MW_FINANCIAL_VALUE", "gte", 1_500_000),
                _clause("MW_HAS_ATTACHMENT", "eq", "tidak"),
            ],
            conclusion_kind="final_conclusion",
            conclusion_code="WF_RECOMMEND_REJECT_NO_DOC",
            conclusion_title="REKOMENDASI TOLAK (REJECT): Nilai HPP >= Rp 1,5 Juta Tanpa Dokumen Bukti",
            explanation="Pengajuan koreksi atau penghapusan stok rusak ini memiliki dampak finansial HPP yang besar (>= Rp 1.500.000), namun belum dilampiri dokumen Berita Acara/Foto di OAS Documents.",
            recommendation={
                "keputusan_disarankan": "rejected",
                "catatan_approval_saran": "Ditolak sementara: Nilai mutasi >= Rp 1.500.000 wajib melampirkan Berita Acara / Foto bukti pada menu Dokumen Internal (OAS).",
            },
            cf_expert=0.96,
            priority=1,
        ),
        ExpertRuleSpec(
            code="MW-R02",
            name="Tolak Pengajuan karena Alasan Tidak Lengkap atau Duplikat",
            conditions=[
                _clause("MW_VERIFICATION_LEVEL", "in", ["alasan_kurang_lengkap", "indikasi_duplikat_input"]),
            ],
            conclusion_kind="final_conclusion",
            conclusion_code="WF_RECOMMEND_REJECT_INVALID",
            conclusion_title="REKOMENDASI TOLAK (REJECT): Kronologi Belum Terverifikasi / Duplikat",
            explanation="Pengajuan mutasi stok tidak boleh disetujui apabila alasan kronologis tidak jelas atau terindikasi duplikasi pencatatan oleh staf.",
            recommendation={
                "keputusan_disarankan": "rejected",
                "catatan_approval_saran": "Ditolak: Mohon lengkapi kronologi penyebab selisih/mutasi secara spesifik atau periksa duplikasi pengajuan.",
            },
            cf_expert=0.95,
            priority=2,
        ),
        ExpertRuleSpec(
            code="MW-R03",
            name="Setujui Pengajuan dengan Dokumen Lengkap & Alasan Terverifikasi",
            conditions=[
                _clause("MW_VERIFICATION_LEVEL", "eq", "alasan_jelas_terverifikasi"),
                _clause("MW_HAS_ATTACHMENT", "eq", "ya"),
            ],
            conclusion_kind="final_conclusion",
            conclusion_code="WF_RECOMMEND_APPROVE_VERIFIED",
            conclusion_title="REKOMENDASI SETUJUI (APPROVE): Dokumen Bukti Lengkap & Terverifikasi",
            explanation="Pengajuan telah dilengkapi dokumen lampiran resmi di OAS serta memiliki alasan operasional yang terverifikasi.",
            recommendation={
                "keputusan_disarankan": "approved",
                "catatan_approval_saran": "Disetujui: Dokumen bukti dan kronologi mutasi telah sesuai dengan prosedur audit inventori.",
            },
            cf_expert=0.94,
            priority=3,
        ),
        ExpertRuleSpec(
            code="MW-R04",
            name="Setujui Pengajuan Nilai Risiko Rendah (< Rp 1,5 Juta) & Terverifikasi",
            conditions=[
                _clause("MW_VERIFICATION_LEVEL", "eq", "alasan_jelas_terverifikasi"),
                _clause("MW_FINANCIAL_VALUE", "lt", 1_500_000),
            ],
            conclusion_kind="final_conclusion",
            conclusion_code="WF_RECOMMEND_APPROVE_VERIFIED",
            conclusion_title="REKOMENDASI SETUJUI (APPROVE): Dampak Finansial di Bawah Ambang Risiko",
            explanation="Nilai dampak finansial mutasi berada di bawah ambang batas audit Rp 1.500.000 dan alasan operasional staf telah terverifikasi.",
            recommendation={
                "keputusan_disarankan": "approved",
                "catatan_approval_saran": "Disetujui: Mutasi bernilai risiko terkendali dan kronologi telah diverifikasi.",
            },
            cf_expert=0.88,
            priority=4,
        ),
    ],
)


DOMAINS: dict[str, DomainDefinition] = {
    item.code: item
    for item in (
        CUST_WATCH_ADVISOR,
        STAFF_POS_CROSSSELL,
        WAREHOUSE_QC_INBOUND,
        WAREHOUSE_STOCK_ANOMALY,
        MGR_KPI_DIAGNOSTIC,
        MGR_WORKFLOW_APPROVAL,
    )
}
