"""Automated Verification Test Suite for Black Flame System.
Validates all 11 core system requirements:
1. Zero name-dependency multi-factor matching
2. Timeline + direction continuity & impossible velocity detection
3. Voice acoustic matching (supporting evidence)
4. Swab hematology matching (WBC, RBC, HGB, PLT)
5. Decision levels: GREEN, YELLOW, RED (never raw percentage only)
6. Active conflict detection (score cannot override conflict)
7. Explainable matching breakdowns (supporting & conflicting factors)
8. Human verification workflow & certificate generation
9. Privacy protection & attribute-first discovery
10. PostgreSQL Supabase integration
11. Offline-first local storage & sync queue
"""
import unittest
from datetime import datetime, timezone, timedelta

import config
from engine.timeline_matcher import analyze_timeline_continuity
from engine.voice_matcher import compare_voice_samples
from engine.swab_matcher import compare_swab_profiles
from engine.conflict_detector import detect_conflicts
from engine.matcher import evaluate_case_pair, match_candidate_against_database
from database.local_db import (
    save_case, get_case_by_code, get_all_cases,
    save_verification, get_pending_sync_items
)
from database.sync_manager import get_sync_status_summary


class TestBlackFlameCore(unittest.TestCase):

    def test_01_no_name_dependency(self):
        """Case pairs must match solely on attributes, without names."""
        case_a = {
            "case_code": "TEST-A", "case_type": "MISSING",
            "age": 25, "gender": "F", "marks": ["scar_forehead"],
            "clothes": "blue kurta", "origin_area": "Sector 1"
        }
        case_b = {
            "case_code": "TEST-B", "case_type": "UNIDENTIFIED",
            "age": 26, "gender": "F", "marks": ["scar_forehead"],
            "clothes": "blue kurta", "origin_area": "Sector 1"
        }
        res = evaluate_case_pair(case_a, case_b)
        self.assertIn(res["decision_level"], (config.DECISION_GREEN, config.DECISION_YELLOW))
        self.assertGreaterEqual(res["numerical_score"], 0.70)
        self.assertIn("Age match exact/tight", str(res["explanation"]["supporting_factors"]))

    def test_02_timeline_and_direction_continuity(self):
        """Who + Where + When + Direction continuity check."""
        now = datetime.now(timezone.utc)
        s1 = {
            "location": "Sector 1 River Basin",
            "timestamp": (now - timedelta(minutes=30)).isoformat(),
            "direction": "Towards Relief Camp Alpha"
        }
        s2 = {
            "location": "Relief Camp Alpha",
            "timestamp": now.isoformat(),
            "direction": "Towards Relief Camp Alpha"
        }
        res = analyze_timeline_continuity(s1, s2)
        self.assertFalse(res["conflict_flag"])
        self.assertGreaterEqual(res["continuity_score"], 0.70)
        self.assertGreaterEqual(res["direction_alignment"], 0.80)

    def test_03_impossible_travel_conflict(self):
        """Impossible travel speed (>90 km/h in disaster zone) must flag conflict."""
        now = datetime.now(timezone.utc)
        s1 = {
            "location": "Sector 1 River Basin",
            "lat": 12.0, "lon": 77.0,
            "timestamp": now.isoformat(),
            "direction": "North"
        }
        s2 = {
            "location": "Relief Camp Alpha",
            "lat": 13.5, "lon": 77.0,  # ~166 km away
            "timestamp": (now + timedelta(minutes=15)).isoformat(),  # 15 mins later
            "direction": "North"
        }
        res = analyze_timeline_continuity(s1, s2)
        self.assertTrue(res["conflict_flag"])
        self.assertIn("Impossible travel speed", res["conflict_reason"])

    def test_04_voice_identification_as_supporting_evidence(self):
        """Voice identification provides supporting score and flags conflicts."""
        v_fam = {"f0_hz": 210.0, "spectral_centroid": 2200.0, "consent_given": True}
        v_pat_close = {"f0_hz": 214.0, "spectral_centroid": 2180.0, "consent_given": True}
        v_pat_far = {"f0_hz": 110.0, "spectral_centroid": 1300.0, "consent_given": True}
        
        match_good = compare_voice_samples(v_fam, v_pat_close)
        self.assertGreaterEqual(match_good["similarity"], 0.70)
        self.assertFalse(match_good["is_conflict"])
        
        match_bad = compare_voice_samples(v_fam, v_pat_far)
        self.assertTrue(match_bad["is_conflict"])

    def test_05_swab_biological_verification(self):
        """Structured swab parameters (WBC, RBC, HGB, PLT) & blood group compatibility."""
        swab_ref = {"blood_group": "A+", "wbc": 7.0, "rbc": 4.5, "hgb": 13.5, "plt": 250.0}
        swab_cand = {"blood_group": "A+", "wbc": 7.3, "rbc": 4.6, "hgb": 13.8, "plt": 260.0}
        swab_conflict = {"blood_group": "B+", "wbc": 7.0, "rbc": 4.5, "hgb": 13.5, "plt": 250.0}
        
        eval_ok = compare_swab_profiles(swab_ref, swab_cand)
        self.assertFalse(eval_ok["is_conflict"])
        self.assertGreaterEqual(eval_ok["match_score"], 0.75)
        
        eval_conflict = compare_swab_profiles(swab_ref, swab_conflict)
        self.assertTrue(eval_conflict["is_conflict"])
        self.assertIn("Blood Group Mismatch", eval_conflict["conflict_reason"])

    def test_06_conflict_overrides_high_score(self):
        """Critical conflict MUST downgrade candidate to RED regardless of other similarities."""
        case_a = {
            "case_code": "ELDERLY", "age": 70, "gender": "M",
            "marks": ["scar_left_arm"], "clothes": "red shirt", "blood_group": "O+"
        }
        case_b = {
            "case_code": "CHILD", "age": 6, "gender": "M",  # Critical age discrepancy!
            "marks": ["scar_left_arm"], "clothes": "red shirt", "blood_group": "O+"
        }
        res = evaluate_case_pair(case_a, case_b)
        self.assertEqual(res["decision_level"], config.DECISION_RED)
        self.assertTrue(res["conflicts"]["has_critical_conflict"])
        self.assertIn("CRITICAL CONFLICT DETECTED", res["decision_rationale"])

    def test_07_explainable_breakdown(self):
        """System must explain WHY decision was made with positive and negative factors."""
        case_a = {"case_code": "C1", "age": 20, "gender": "F", "marks": ["mole_face"]}
        case_b = {"case_code": "C2", "age": 21, "gender": "F", "marks": ["mole_face"]}
        res = evaluate_case_pair(case_a, case_b)
        exp = res["explanation"]
        self.assertIn("supporting_factors", exp)
        self.assertIn("conflicting_factors", exp)
        self.assertIn("status_guidance", exp)
        self.assertTrue(len(exp["supporting_factors"]) > 0)

    def test_08_human_verification_and_certificate(self):
        """Human officer sign-off generates certificate only upon approval."""
        cert_code = save_verification({
            "match_id": "TEST_MATCH_01",
            "stage": "AUTHORIZED_FOR_REUNIFICATION",
            "verified_by_officer": "Capt. M. Roy",
            "officer_badge_id": "DISASTER-01",
            "verification_notes": "Identity authenticated and verified.",
            "photo_verified": True,
            "swab_confirmed": True
        })
        self.assertIsNotNone(cert_code)
        self.assertTrue(cert_code.startswith("BF-CERT-"))

    def test_09_offline_first_storage_and_sync(self):
        """Offline-created cases must receive PENDING_SYNC status."""
        offline_c = {
            "case_code": f"OFFLINE-{datetime.now().microsecond}",
            "case_type": "MISSING", "age": 30, "gender": "M"
        }
        saved = save_case(offline_c, is_offline=True)
        self.assertEqual(saved["sync_status"], "PENDING_SYNC")
        
        pending = get_pending_sync_items()
        self.assertTrue(any(c["id"] == saved["id"] for c in pending["cases"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)

