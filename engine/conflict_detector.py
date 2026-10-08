"""Active Conflict Detection Engine.
Actively searches for contradictions and impossibilities across all evidence vectors.
A high numerical score must NEVER override a critical conflict.
"""
from typing import Dict, Any, List, Tuple


def detect_conflicts(
    case_a: Dict[str, Any],
    case_b: Dict[str, Any],
    timeline_res: Dict[str, Any],
    voice_res: Dict[str, Any],
    swab_res: Dict[str, Any]
) -> Dict[str, Any]:
    """Inspects case attributes and sub-engine evaluations to find contradictions.
    Returns:
    - has_critical_conflict: bool (forces RED)
    - has_warning_conflict: bool (forces YELLOW or review)
    - conflicts: list of critical conflict messages
    - warnings: list of minor discrepancy messages
    """
    conflicts: List[str] = []
    warnings: List[str] = []
    
    # ---------------- 1. Age Contradiction Check ----------------
    age_a = float(case_a.get("age", 0) or case_a.get("est_age", 0))
    age_b = float(case_b.get("age", 0) or case_b.get("est_age", 0))
    
    if age_a > 0 and age_b > 0:
        age_diff = abs(age_a - age_b)
        
        # Child vs Adult boundary check (e.g. 5 y/o child vs 45 y/o adult)
        is_child_a = age_a <= 12
        is_child_b = age_b <= 12
        is_senior_a = age_a >= 60
        is_senior_b = age_b >= 60
        
        if (is_child_a and not is_child_b and age_b > 20) or (is_child_b and not is_child_a and age_a > 20):
            conflicts.append(f"CRITICAL AGE CONFLICT: Reported age {age_a:.0f} vs {age_b:.0f} (Child vs Adult mismatch).")
        elif (is_senior_a and age_b < 35) or (is_senior_b and age_a < 35):
            conflicts.append(f"CRITICAL AGE CONFLICT: Generational gap {age_diff:.0f} yrs ({age_a:.0f} vs {age_b:.0f}).")
        elif age_diff > 18:
            conflicts.append(f"CRITICAL AGE CONFLICT: Age discrepancy of {age_diff:.0f} years exceeds possible estimation margin.")
        elif age_diff > 8:
            warnings.append(f"Age discrepancy of {age_diff:.0f} years requires human verification.")
            
    # ---------------- 2. Gender Contradiction Check ----------------
    gender_a = str(case_a.get("gender", "")).strip().upper()
    gender_b = str(case_b.get("gender", "")).strip().upper()
    
    if gender_a and gender_b and gender_a != "U" and gender_b != "U":
        # Direct gender conflict (e.g. M vs F)
        if (gender_a.startswith("M") and gender_b.startswith("F")) or (gender_a.startswith("F") and gender_b.startswith("M")):
            conflicts.append(f"CRITICAL GENDER CONFLICT: Incompatible genders reported ({gender_a} vs {gender_b}).")
            
    # ---------------- 3. Timeline / Travel Impossibility Check ----------------
    if timeline_res.get("conflict_flag"):
        reason = timeline_res.get("conflict_reason", "Impossible travel velocity between sightings.")
        conflicts.append(f"CRITICAL TIMELINE CONFLICT: {reason}")
    elif timeline_res.get("implied_speed_kmh", 0) > 65.0:
        warnings.append(f"High transit speed between sightings ({timeline_res.get('implied_speed_kmh')} km/h) in disaster zone.")
        
    # Check opposite direction conflict
    dir_align = timeline_res.get("direction_alignment", 0.5)
    dir_a = timeline_res.get("direction_a", "")
    dir_b = timeline_res.get("direction_b", "")
    if dir_align <= 0.15 and dir_a and dir_b and "Stationary" not in dir_a and "Stationary" not in dir_b:
        warnings.append(f"Contradictory movement directions: One reported heading '{dir_a}' while other reported '{dir_b}'.")

    # ---------------- 4. Voice Contradiction Check ----------------
    if voice_res.get("is_conflict"):
        conflicts.append(f"CRITICAL VOICE CONFLICT: {voice_res.get('note', 'Acoustic vocal profile contradiction.')}")
        
    # ---------------- 5. Biological / Swab Contradiction Check ----------------
    if swab_res.get("is_conflict"):
        conflicts.append(f"CRITICAL BIOLOGICAL CONFLICT: {swab_res.get('conflict_reason', 'Biological incompatibility.')}")
        
    # ---------------- 6. Physical Identifying Marks Contradiction ----------------
    # If permanent marks directly contradict (e.g., amputations or birthmarks declared on opposite sides)
    marks_a = set(case_a.get("marks") or [])
    marks_b = set(case_b.get("marks") or [])
    
    # Specific permanent contradiction rules
    if "missing_finger" in marks_a and "missing_finger" in marks_b:
        pass  # Agree
    # If both cases have several permanent marks documented, but zero overlap after 3+ marks
    if len(marks_a) >= 3 and len(marks_b) >= 3 and len(marks_a & marks_b) == 0:
        warnings.append("Zero common marks despite extensive physical marking documentation (3+ recorded on both).")
        
    has_critical = len(conflicts) > 0
    has_warning = len(warnings) > 0
    
    return {
        "has_critical_conflict": has_critical,
        "has_warning_conflict": has_warning,
        "critical_conflicts": conflicts,
        "warnings": warnings,
        "total_conflict_count": len(conflicts) + len(warnings)
    }

