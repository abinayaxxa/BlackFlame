"""Multi-Factor Family Matching Engine.
Evaluates cases without depending on person names.
Combines attributes, timeline/direction continuity, voice, and swab biological data.
Enforces that a high score NEVER overrides a critical conflict.
"""
from typing import Dict, Any, List, Optional
from rapidfuzz import fuzz

from config import (
    DECISION_GREEN, DECISION_YELLOW, DECISION_RED,
    CLOTHING_COLORS, CLOTHING_ITEMS
)
from engine.timeline_matcher import analyze_timeline_continuity
from engine.voice_matcher import compare_voice_samples
from engine.swab_matcher import compare_swab_profiles
from engine.conflict_detector import detect_conflicts
from engine.explainability import generate_explanation


def compute_attribute_similarity(case_a: Dict[str, Any], case_b: Dict[str, Any]) -> Dict[str, Any]:
    """Compare pure non-name attributes:
    - Age difference (fuzzy tolerance)
    - Gender match
    - Physical marks (Jaccard similarity)
    - Clothing color & item match
    - Village/city/area similarity
    - Known relatives & kinship links
    """
    # 1. Age similarity
    age_a = float(case_a.get("age", 0) or case_a.get("est_age", 0))
    age_b = float(case_b.get("age", 0) or case_b.get("est_age", 0))
    age_diff = abs(age_a - age_b) if (age_a > 0 and age_b > 0) else 10.0
    
    if age_diff <= 2:
        age_score = 1.0
    elif age_diff <= 5:
        age_score = 0.8
    elif age_diff <= 10:
        age_score = 0.45
    else:
        age_score = max(0.0, 1.0 - (age_diff / 15.0))

    # 2. Gender match
    gen_a = str(case_a.get("gender", "")).upper()
    gen_b = str(case_b.get("gender", "")).upper()
    gender_match = (gen_a == gen_b) if (gen_a and gen_b) else True
    gender_score = 1.0 if gender_match else 0.0

    # 3. Physical identifying marks (Jaccard & overlap)
    marks_a = set(case_a.get("marks") or [])
    marks_b = set(case_b.get("marks") or [])
    shared_marks = marks_a & marks_b
    total_marks = marks_a | marks_b
    marks_jaccard = len(shared_marks) / len(total_marks) if total_marks else 0.5
    marks_score = min(1.0, len(shared_marks) * 0.4 + marks_jaccard * 0.6) if shared_marks else (0.4 if not marks_a or not marks_b else 0.1)

    # 4. Clothing analysis (color + garment item)
    clothes_a = (str(case_a.get("clothes") or "") + " " + str(case_a.get("clothing_description") or "")).lower()
    clothes_b = (str(case_b.get("clothes") or "") + " " + str(case_b.get("clothing_description") or "")).lower()
    
    color_a = next((c for c in CLOTHING_COLORS if c in clothes_a), "")
    color_b = next((c for c in CLOTHING_COLORS if c in clothes_b), "")
    color_match = (color_a == color_b and bool(color_a))
    
    item_a = next((i for i in CLOTHING_ITEMS if i in clothes_a), "")
    item_b = next((i for i in CLOTHING_ITEMS if i in clothes_b), "")
    item_match = (item_a == item_b and bool(item_a))
    
    fuzz_clothing = fuzz.token_set_ratio(clothes_a, clothes_b) / 100.0 if (clothes_a and clothes_b) else 0.5
    clothing_score = (0.4 * float(color_match) + 0.3 * float(item_match) + 0.3 * fuzz_clothing) if (clothes_a and clothes_b) else 0.5

    # 5. Village / city / area match
    area_a = str(case_a.get("village_city") or case_a.get("origin_area") or case_a.get("last_seen_place") or "").strip().lower()
    area_b = str(case_b.get("village_city") or case_b.get("origin_area") or case_b.get("found_place") or "").strip().lower()
    
    area_sim = fuzz.token_sort_ratio(area_a, area_b) / 100.0 if (area_a and area_b) else 0.4
    area_match = area_sim >= 0.70

    # 6. Known relatives & kinship links
    # Matches if family mentions a relative's name/relation that matches responder's notes or family query
    relatives_a = str(case_a.get("known_relatives") or case_a.get("relatives_summary") or "").lower()
    relatives_b = str(case_b.get("known_relatives") or case_b.get("relatives_summary") or "").lower()
    
    family_link_match = False
    if relatives_a and relatives_b:
        fam_sim = fuzz.token_set_ratio(relatives_a, relatives_b) / 100.0
        family_link_match = fam_sim >= 0.65
        family_score = fam_sim
    else:
        family_score = 0.5  # Neutral if not provided

    # Composite attribute score
    composite_attr = (
        0.25 * age_score +
        0.15 * gender_score +
        0.25 * marks_score +
        0.15 * clothing_score +
        0.10 * area_sim +
        0.10 * family_score
    )

    return {
        "composite_attribute_score": round(composite_attr, 3),
        "age_diff": age_diff,
        "age_score": round(age_score, 3),
        "gender_match": gender_match,
        "gender_score": gender_score,
        "marks_shared": len(shared_marks),
        "shared_marks_list": list(shared_marks),
        "marks_score": round(marks_score, 3),
        "clothing_sim": round(clothing_score, 3),
        "area_match": area_match,
        "area_sim": round(area_sim, 3),
        "family_link_match": family_link_match,
        "family_score": round(family_score, 3)
    }


def evaluate_case_pair(
    case_a: Dict[str, Any],
    case_b: Dict[str, Any],
    sighting_a: Optional[Dict[str, Any]] = None,
    sighting_b: Optional[Dict[str, Any]] = None,
    voice_a: Optional[Dict[str, Any]] = None,
    voice_b: Optional[Dict[str, Any]] = None,
    swab_a: Optional[Dict[str, Any]] = None,
    swab_b: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Master evaluator for a pair of cases (e.g. Missing Report vs Unidentified Found Person).
    Returns complete decision object with color status, explainability, and conflict log.
    """
    # 1. Attribute Evaluation (No name used)
    attr_eval = compute_attribute_similarity(case_a, case_b)
    
    # 2. Timeline, Proximity, and Direction Continuity
    # Prepare sighting representations
    s_a = sighting_a or {
        "location": case_a.get("last_seen_place") or case_a.get("found_place") or "",
        "timestamp": case_a.get("last_seen_time") or case_a.get("found_time"),
        "direction": case_a.get("direction_of_movement") or case_a.get("last_seen_direction") or "Stationary / Unmoved",
        "lat": case_a.get("latitude"),
        "lon": case_a.get("longitude")
    }
    s_b = sighting_b or {
        "location": case_b.get("last_seen_place") or case_b.get("found_place") or "",
        "timestamp": case_b.get("last_seen_time") or case_b.get("found_time"),
        "direction": case_b.get("direction_of_movement") or case_b.get("last_seen_direction") or "Stationary / Unmoved",
        "lat": case_b.get("latitude"),
        "lon": case_b.get("longitude")
    }
    timeline_eval = analyze_timeline_continuity(s_a, s_b)

    # 3. Voice Acoustic Evaluation
    v_a = voice_a or case_a.get("voice_record")
    v_b = voice_b or case_b.get("voice_record")
    voice_eval = compare_voice_samples(v_a, v_b)

    # 4. Swab-Based Biological Evaluation
    sw_a = swab_a or case_a.get("swab_record")
    sw_b = swab_b or case_b.get("swab_record")
    swab_eval = compare_swab_profiles(sw_a, sw_b)

    # 5. Conflict Detection Pass (CRITICAL CHECK)
    conflict_eval = detect_conflicts(case_a, case_b, timeline_eval, voice_eval, swab_eval)

    # 6. Multi-Factor Score Calculation
    # Weights:
    # Attributes: 40%
    # Timeline & Direction: 25%
    # Voice (if available): 15% (or distributed if absent)
    # Biological Swab (if available): 20% (or distributed if absent)
    w_attr = 0.45
    w_timeline = 0.25
    w_voice = 0.15 if voice_eval.get("has_data") else 0.0
    w_swab = 0.15 if swab_eval.get("has_swab") else 0.0
    
    # Normalize weights
    total_w = w_attr + w_timeline + w_voice + w_swab
    norm_w_attr = w_attr / total_w
    norm_w_timeline = w_timeline / total_w
    norm_w_voice = w_voice / total_w if w_voice > 0 else 0.0
    norm_w_swab = w_swab / total_w if w_swab > 0 else 0.0
    
    numerical_score = (
        norm_w_attr * attr_eval["composite_attribute_score"] +
        norm_w_timeline * timeline_eval["continuity_score"] +
        norm_w_voice * voice_eval.get("similarity", 0.5) +
        norm_w_swab * swab_eval.get("match_score", 0.5)
    )
    numerical_score = round(numerical_score, 3)

    # 7. Decision Level Determination
    # RULE: A high numerical score must NEVER override a critical conflict!
    if conflict_eval["has_critical_conflict"]:
        decision_level = DECISION_RED
        decision_rationale = "CRITICAL CONFLICT DETECTED: The candidate is stopped due to contradictory evidence."
    elif numerical_score < 0.40:
        decision_level = DECISION_RED
        decision_rationale = "INSUFFICIENT EVIDENCE: Multi-factor correlation is below acceptable matching threshold."
    elif conflict_eval["has_warning_conflict"] or numerical_score < 0.70 or timeline_eval["continuity_score"] < 0.50:
        decision_level = DECISION_YELLOW
        decision_rationale = "UNCERTAIN / NEEDS REVIEW: Moderate matching evidence with discrepancies or missing clinical records."
    else:
        # High score, zero critical conflicts, solid timeline continuity
        decision_level = DECISION_GREEN
        decision_rationale = "STRONG SUPPORTING MATCH: Sufficiently consistent multi-factor evidence. Ready for officer verification."

    # 8. Generate Full Explainability Breakdown
    explanation = generate_explanation(
        decision_level=decision_level,
        combined_score=numerical_score,
        attribute_breakdown=attr_eval,
        timeline_eval=timeline_eval,
        voice_eval=voice_eval,
        swab_eval=swab_eval,
        conflict_eval=conflict_eval
    )

    return {
        "case_a_id": case_a.get("case_code") or case_a.get("id"),
        "case_b_id": case_b.get("temp_id") or case_b.get("case_code") or case_b.get("id"),
        "decision_level": decision_level,
        "numerical_score": numerical_score,
        "decision_rationale": decision_rationale,
        "attributes": attr_eval,
        "timeline": timeline_eval,
        "voice": voice_eval,
        "swab": swab_eval,
        "conflicts": conflict_eval,
        "explanation": explanation
    }


def match_candidate_against_database(
    query_case: Dict[str, Any],
    candidate_records: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Evaluates query case against all candidates in database, returns ranked results
    with full GREEN/YELLOW/RED decisions.
    """
    results = []
    for cand in candidate_records:
        evaluation = evaluate_case_pair(query_case, cand)
        results.append(evaluation)
        
    # Sort order: GREEN first, then YELLOW, then RED; within tier sort by score desc
    tier_order = {DECISION_GREEN: 0, DECISION_YELLOW: 1, DECISION_RED: 2}
    results.sort(key=lambda r: (tier_order.get(r["decision_level"], 3), -r["numerical_score"]))
    return results

