"""Swab-Based Biological Verification Engine.
Processes structured hematology swab panels (WBC, RBC, HGB, PLT, blood group)
as an authorized clinical verification layer.
"""
from typing import Dict, Any, Optional
from config import SWAB_REFERENCE_RANGES


# ABO / Rh Compatibility Matrix (Child compatibility given parental types or direct identity match)
def are_blood_types_compatible(type_a: str, type_b: str, relation_type: str = "same_person") -> bool:
    """Check blood type compatibility.
    If relation is 'same_person' (missing report vs found person), blood group must match exactly.
    If relation is 'parent_child', biological heredity rules apply.
    """
    if not type_a or not type_b:
        return True  # Unknown blood group is not a direct conflict
        
    a = type_a.strip().upper()
    b = type_b.strip().upper()
    
    if relation_type in ("same_person", "self"):
        return a == b
        
    # Parent - Child ABO heredity rules:
    # O + O -> only O
    # AB + O -> A or B (cannot have AB or O)
    # AB + AB -> A, B, or AB (cannot have O)
    abo_a = a.replace("+", "").replace("-", "")
    abo_b = b.replace("+", "").replace("-", "")
    
    if abo_a == "O" and abo_b == "AB":
        return False  # Biologically impossible for parent/child
    if abo_a == "AB" and abo_b == "O":
        return False
        
    return True


def evaluate_parameter_tolerance(val_a: float, val_b: float, max_variance_ratio: float = 0.25) -> float:
    """Calculate parameter agreement score between 0.0 and 1.0 based on physiological drift."""
    if val_a <= 0 or val_b <= 0:
        return 0.5
        
    diff = abs(val_a - val_b)
    avg = (val_a + val_b) / 2.0
    ratio = diff / avg
    
    if ratio <= 0.08:
        return 1.0  # Extremely tight match
    elif ratio <= max_variance_ratio:
        return max(0.5, 1.0 - (ratio / max_variance_ratio) * 0.5)
    else:
        return max(0.0, 0.5 - (ratio - max_variance_ratio))


def compare_swab_profiles(
    swab_a: Optional[Dict[str, Any]],
    swab_b: Optional[Dict[str, Any]],
    relationship: str = "same_person"
) -> Dict[str, Any]:
    """Compare two structured swab records.
    Returns:
    - match_score: 0.0 to 1.0
    - is_conflict: bool
    - conflict_reason: str or None
    - blood_compatible: bool
    - parameter_breakdown: detailed scores
    - status: 'VERIFIED_SUPPORT', 'PARTIAL_SUPPORT', 'BIOLOGICAL_CONFLICT', 'NO_SWAB'
    """
    if not swab_a or not swab_b:
        return {
            "has_swab": False,
            "match_score": 0.5,
            "is_conflict": False,
            "conflict_reason": None,
            "blood_compatible": True,
            "status": "NO_SWAB",
            "note": "Biological swab record not available for one or both profiles."
        }
        
    # Check Blood Group Compatibility
    bg_a = swab_a.get("blood_group") or swab_a.get("blood") or ""
    bg_b = swab_b.get("blood_group") or swab_b.get("blood") or ""
    
    blood_compatible = are_blood_types_compatible(bg_a, bg_b, relationship)
    
    if not blood_compatible:
        return {
            "has_swab": True,
            "match_score": 0.0,
            "is_conflict": True,
            "conflict_reason": f"Biological Blood Group Mismatch: {bg_a} is incompatible with {bg_b}",
            "blood_compatible": False,
            "status": "BIOLOGICAL_CONFLICT",
            "note": f"CRITICAL CONFLICT: Incompatible blood groups ({bg_a} vs {bg_b}). Candidate halted."
        }
        
    # Hematology Parameter Comparison (WBC, RBC, HGB, PLT)
    wbc_a, wbc_b = float(swab_a.get("wbc", 0)), float(swab_b.get("wbc", 0))
    rbc_a, rbc_b = float(swab_a.get("rbc", 0)), float(swab_b.get("rbc", 0))
    hgb_a, hgb_b = float(swab_a.get("hgb", 0)), float(swab_b.get("hgb", 0))
    plt_a, plt_b = float(swab_a.get("plt", 0)), float(swab_b.get("plt", 0))
    
    scores = {}
    valid_count = 0
    total_score = 0.0
    
    # Hematological parameters shift under trauma/dehydration, so tolerances account for clinical stress
    if wbc_a > 0 and wbc_b > 0:
        s = evaluate_parameter_tolerance(wbc_a, wbc_b, 0.40)  # WBC can spike under stress/infection
        scores["WBC"] = round(s, 2)
        total_score += s * 0.20
        valid_count += 0.20
        
    if rbc_a > 0 and rbc_b > 0:
        s = evaluate_parameter_tolerance(rbc_a, rbc_b, 0.20)
        scores["RBC"] = round(s, 2)
        total_score += s * 0.25
        valid_count += 0.25
        
    if hgb_a > 0 and hgb_b > 0:
        s = evaluate_parameter_tolerance(hgb_a, hgb_b, 0.22)
        scores["HGB"] = round(s, 2)
        total_score += s * 0.30
        valid_count += 0.30
        
    if plt_a > 0 and plt_b > 0:
        s = evaluate_parameter_tolerance(plt_a, plt_b, 0.35)
        scores["PLT"] = round(s, 2)
        total_score += s * 0.25
        valid_count += 0.25
        
    # Baseline score
    if valid_count > 0:
        param_score = total_score / valid_count
    else:
        param_score = 0.7 if (bg_a and bg_a == bg_b) else 0.5
        
    # If blood groups match explicitly, boost certainty
    if bg_a and bg_b and bg_a == bg_b:
        param_score = min(1.0, param_score * 0.7 + 0.30)
        
    param_score = round(param_score, 3)
    
    if param_score >= 0.75:
        status = "VERIFIED_SUPPORT"
        note = (f"Biological swab profile consistent (Score: {param_score*100:.1f}%). "
                f"Blood group ({bg_a or 'Known'}) and hematology indicators align.")
        is_conflict = False
        conflict_reason = None
    elif param_score >= 0.50:
        status = "PARTIAL_SUPPORT"
        note = f"Swab parameters within acceptable clinical variance ({param_score*100:.1f}%)."
        is_conflict = False
        conflict_reason = None
    else:
        status = "BIOLOGICAL_CONFLICT"
        note = "Hematological indices differ significantly beyond expected trauma variance."
        is_conflict = True
        conflict_reason = "Significant discrepancy across RBC/HGB/PLT baseline swab indices"

    return {
        "has_swab": True,
        "match_score": param_score,
        "is_conflict": is_conflict,
        "conflict_reason": conflict_reason,
        "blood_compatible": blood_compatible,
        "blood_group_a": bg_a,
        "blood_group_b": bg_b,
        "parameter_scores": scores,
        "status": status,
        "note": note,
        "sample_a_id": swab_a.get("sample_id", "N/A"),
        "sample_b_id": swab_b.get("sample_id", "N/A")
    }

