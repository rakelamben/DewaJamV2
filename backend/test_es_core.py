import unittest

from es.core.certainty_factor import classify_confidence, combine_cf, premise_cf, rule_cf
from es.core.engine import run_inference
from es.core.matcher import match_products_for_conclusion
from es.core.types import ExpertRuleSpec, RuleClause
from es.domains import (
    CUST_WATCH_ADVISOR,
    MGR_KPI_DIAGNOSTIC,
    MGR_WORKFLOW_APPROVAL,
    STAFF_POS_CROSSSELL,
    WAREHOUSE_QC_INBOUND,
    WAREHOUSE_STOCK_ANOMALY,
)


class TestExpertSystemCore(unittest.TestCase):
    def test_certainty_factor_mycin_combination(self):
        cf1 = rule_cf(0.80, premise_cf([1.0, 1.0]))
        cf2 = rule_cf(0.70, premise_cf([0.80, 1.0]))
        self.assertAlmostEqual(cf1, 0.80, places=4)
        self.assertAlmostEqual(cf2, 0.56, places=4)
        combined = combine_cf(cf1, cf2)
        self.assertAlmostEqual(combined, 0.9120, places=4)
        self.assertEqual(classify_confidence(combined), "Sangat Yakin")

    def test_multi_step_forward_chaining_customer_watch_advisor(self):
        output = run_inference(
            CUST_WATCH_ADVISOR.rules,
            user_facts={
                "C_OCCASION": "renang_diving",
                "C_GENDER_PROFILE": "pria",
                "C_WRIST_SIZE": "kecil_lt_16cm",
                "C_MOVEMENT_PREF": "mekanis_automatic",
                "C_BUDGET_TIER": "menengah_2jt_5jt",
            },
            user_cfs={"C_OCCASION": 1.0, "C_MOVEMENT_PREF": 1.0},
        )
        self.assertEqual(output.inferred_facts.get("I_WATER_NEED"), "high_10atm")
        self.assertEqual(output.inferred_facts.get("I_SIZE_FIT"), "compact_34_38")
        self.assertTrue(output.results)
        self.assertEqual(output.results[0].conclusion_code, "REC_PRO_DIVER_SPORT")
        self.assertGreaterEqual(output.results[0].cf_combined, 0.85)

    def test_pos_cross_sell_lug_width_matcher(self):
        output = run_inference(
            STAFF_POS_CROSSSELL.rules,
            user_facts={
                "S_BUYER_INTENT": "pakai_pribadi",
                "S_USAGE_STYLE": "outdoor_aktif",
            },
            db_facts={
                "P_MAIN_CATEGORY": "Jam Tangan Pria",
                "P_MAIN_PRICE": 2_500_000,
                "P_LUG_WIDTH": 22,
                "P_STRAP_MATERIAL": "leather",
            },
        )
        self.assertTrue(output.results)
        self.assertEqual(output.results[0].conclusion_code, "BUNDLE_SPORT_RUBBER_STRAP")

        sample_products = [
            {
                "product_id": "strap-20",
                "nama_barang": "Strap Rubber 20mm",
                "kategori": "Strap & Aksesoris",
                "harga": 250_000,
                "stok": 5,
                "specs": {"lug_width_mm": 20, "strap_material": "rubber"},
            },
            {
                "product_id": "strap-22",
                "nama_barang": "Strap Rubber Diver 22mm",
                "kategori": "Strap & Aksesoris",
                "harga": 280_000,
                "stok": 4,
                "specs": {"lug_width_mm": 22, "strap_material": "rubber"},
            },
        ]
        matched = match_products_for_conclusion(
            output.results[0].recommendation,
            sample_products,
            working_facts={"P_LUG_WIDTH": 22},
            main_product={"product_id": "watch-1", "specs": {"lug_width_mm": 22}},
        )
        self.assertEqual(len(matched), 2)
        self.assertEqual(matched[0]["product_id"], "strap-22")

    def test_warehouse_qc_and_stock_anomaly_domains(self):
        qc_out = run_inference(
            WAREHOUSE_QC_INBOUND.rules,
            user_facts={
                "W_BOX_CONDITION": "utuh_tersegel",
                "W_DEFECT_SEVERITY": "cacat_fungsi_mesin_mati",
            },
            db_facts={
                "W_PO_DEFECT_PCT": 8.5,
                "W_PO_SHORTAGE_PCT": 0.0,
                "W_PO_DELAY_DAYS": 1,
                "W_PO_DEFECT_QTY": 2,
            },
        )
        self.assertTrue(qc_out.results)
        self.assertEqual(qc_out.results[0].conclusion_code, "QC_PARTIAL_ACCEPT_RETURN_DEFECT")

        anom_out = run_inference(
            WAREHOUSE_STOCK_ANOMALY.rules,
            user_facts={
                "W_ANOMALY_TYPE": "stok_fisik_kurang_hilang",
                "W_DIFF_QTY": 3,
                "W_HAS_DOC_PROOF": "belum_ada",
            },
            db_facts={"W_SYS_STOCK": 10, "W_ROP": 5, "W_UNIT_COST": 800_000, "W_MOVEMENT_30D": 4},
        )
        self.assertTrue(anom_out.results)
        self.assertEqual(anom_out.results[0].conclusion_code, "MUTASI_ADJUSTMENT_NEED_DOC")

    def test_manager_kpi_and_workflow_approval_domains(self):
        kpi_out = run_inference(
            MGR_KPI_DIAGNOSTIC.rules,
            user_facts={"M_FOCUS_AREA": "semua_aspek"},
            db_facts={
                "M_KPI_MARGIN_PCT": 28.0,
                "M_KPI_STOCKOUT_PCT": 20.0,
                "M_COST_HIKE_SKU_COUNT": 2,
                "M_DSS_RESTOCK_URGENT_COUNT": 2,
                "M_DSS_PROMO_AGGRESSIVE_COUNT": 1,
                "M_DSS_PROMO_BLOCKED_COUNT": 1,
                "M_PENDING_WORKFLOW_COUNT": 2,
            },
        )
        codes = {item.conclusion_code for item in kpi_out.results}
        self.assertIn("DIAG_CRITICAL_STOCKOUT_RISK", codes)
        self.assertIn("DIAG_MARGIN_COMPRESSION_SUPPLIER", codes)

        wf_out = run_inference(
            MGR_WORKFLOW_APPROVAL.rules,
            user_facts={"MW_VERIFICATION_LEVEL": "alasan_jelas_terverifikasi"},
            db_facts={
                "MW_REQ_TYPE": "stock_damaged",
                "MW_QTY_ABS": 3,
                "MW_FINANCIAL_VALUE": 2_400_000,
                "MW_HAS_ATTACHMENT": "tidak",
                "MW_RESULTING_STOCK": 7,
            },
        )
        self.assertTrue(wf_out.results)
        self.assertEqual(wf_out.results[0].conclusion_code, "WF_RECOMMEND_REJECT_NO_DOC")

    def test_no_rule_fired_returns_warning(self):
        dummy_rule = ExpertRuleSpec(
            code="DUMMY-1",
            name="Dummy",
            conditions=[RuleClause("UNKNOWN_FACT", "eq", "impossible")],
            conclusion_kind="final_conclusion",
            conclusion_code="NONE",
            conclusion_title="None",
            explanation="None",
        )
        out = run_inference([dummy_rule], user_facts={})
        self.assertEqual(len(out.results), 0)
        self.assertEqual(out.warnings[0]["kode"], "NO_RULE_FIRED")


if __name__ == "__main__":
    unittest.main()
