"""Explainable AI (XAI) Factor Breakdown Engine.
Generates human-readable, auditable checklists of supporting, conflicting,
and pending factors for every candidate evaluation.
"""
from typing import Dict, Any, List
from config import DECISION_GREEN, DECISION_YELLOW, DECISION_RED


def generate_explanation(
    decision_level: str,
    combined_score: float,
    attribute_breakdown: Dict[str, Any],
    timeline_eval: Dict[str, Any],
    voice_eval: Dict[str, Any],
    swab_eval: Dict[str, Any],
    conflict_eval: Dict[str, Any]
) -> Dict[str, Any]:
    """Generates an exhaustive, auditable breakdown for field officers and families."""
    supporting_factors: List[str] = []
    conflicting_factors: List[str] = []
    pending_factors: List[str] = []
    
    # 1. Attribute Factors
    age_diff = attribute_breakdown.get("age_diff", 99)
    if age_diff <= 2:
        supporting_factors.append(f"Age match exact/tight (difference: {age_diff:.0f} yr)")
    elif age_diff <= 5:
        supporting_factors.append(f"Age estimate consistent within field tolerance (difference: {age_diff:.0f} yrs)")
        
    if attribute_breakdown.get("gender_match"):
        supporting_factors.append("Gender attributes fully aligned")
        
    marks_shared = attribute_breakdown.get("marks_shared", 0)
    if marks_shared > 0:
        supporting_factors.append(f"Physical identifying marks verified: {marks_shared} distinct mark(s) match")
    else:
        pending_factors.append("No common physical scars/birthmarks verified yet")
        
    if attribute_breakdown.get("clothing_sim", 0) >= 0.7:
        supporting_factors.append("Clothing color and garment description consistent with report")
        
    if attribute_breakdown.get("area_match"):
        supporting_factors.append("Origin village / district / rescue area matches reported sector")
        
    if attribute_breakdown.get("family_link_match"):
        supporting_factors.append("Known relative details and kinship relationship consistent")

    # 2. Timeline and Direction Continuity Factors
    dist_km = timeline_eval.get("distance_km", 999)
    delta_mins = timeline_eval.get("delta_minutes", 9999)
    speed = timeline_eval.get("implied_speed_kmh", 0)
    dir_align = timeline_eval.get("direction_alignment", 0.5)
    
    if dist_km <= 1.5 and delta_mins <= 60:
        supporting_factors.append(f"Last-seen proximity close: {dist_km:.1f} km apart within {delta_mins:.0f} mins")
    elif dist_km <= 6.0 and delta_mins <= 240:
        supporting_factors.append(f"Spatial-temporal continuity plausible: {dist_km:.1f} km within {delta_mins:.0f} mins")
        
    if dir_align >= 0.8:
        supporting_factors.append(f"Direction of movement aligned: '{timeline_eval.get('direction_a')}'")
    elif dir_align <= 0.2:
        conflicting_factors.append(f"Direction vectors diverge: '{timeline_eval.get('direction_a')}' vs '{timeline_eval.get('direction_b')}'")
        
    if speed <= 15.0 and dist_km <= 10.0:
        supporting_factors.append(f"Transit velocity realistic for terrain ({speed:.1f} km/h)")

    # 3. Voice Factors
    if voice_eval.get("has_data"):
        if voice_eval.get("status") in ("STRONG_SUPPORT", "MODERATE_SUPPORT"):
            supporting_factors.append(f"Voice acoustic signature consistent ({voice_eval.get('similarity', 0)*100:.0f}% similarity)")
        elif voice_eval.get("is_conflict"):
            conflicting_factors.append(f"Voice acoustic signature mismatch: {voice_eval.get('note')}")
    else:
        pending_factors.append("Voice sample pending recording or consent authorization")

    # 4. Biological / Swab Factors
    if swab_eval.get("has_swab"):
        if swab_eval.get("status") in ("VERIFIED_SUPPORT", "PARTIAL_SUPPORT"):
            supporting_factors.append(f"Biological swab metrics consistent (Blood group: {swab_eval.get('blood_group_a') or 'Matched'})")
        elif swab_eval.get("is_conflict"):
            conflicting_factors.append(f"Biological swab conflict: {swab_eval.get('conflict_reason')}")
    else:
        pending_factors.append("Swab laboratory test parameters pending analysis")

    # 5. Integrate Detected Conflicts
    for c in conflict_eval.get("critical_conflicts", []):
        if c not in conflicting_factors:
            conflicting_factors.append(c)
            
    for w in conflict_eval.get("warnings", []):
        pending_factors.append(f"Warning: {w}")

    # Recommended Action Text
    if decision_level == DECISION_GREEN:
        next_action = "PROCEED_TO_OFFICER_VERIFICATION"
        status_guidance = "Proceed to authorized human officer interview & identity verification."
    elif decision_level == DECISION_YELLOW:
        next_action = "SEND_FOR_FIELD_INVESTIGATION"
        status_guidance = "Send for additional field investigation, missing evidence capture, or supervisor review."
    else:
        next_action = "STOP_CANDIDATE"
        status_guidance = "Stop candidate matching process due to critical conflict or insufficient correlation."

    return {
        "decision_level": decision_level,
        "combined_score": round(combined_score, 3),
        "score_percentage": f"{combined_score * 100:.1f}%",
        "supporting_factors": supporting_factors,
        "conflicting_factors": conflicting_factors,
        "pending_factors": pending_factors,
        "next_action": next_action,
        "status_guidance": status_guidance
    }

