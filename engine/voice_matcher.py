"""Voice Identification Engine.
Extracts acoustic signatures and computes voice similarity for memory-loss
or non-verbal victims. Voice is treated as SUPPORTING EVIDENCE only.
"""
import math
from typing import Dict, Any, Optional


def extract_simulated_acoustic_features(audio_meta: Dict[str, Any]) -> Dict[str, float]:
    """Generate or extract normalized acoustic feature vector.
    Features:
    - f0_hz: Fundamental pitch frequency (typically 85-255 Hz)
    - spectral_centroid: Brightness / resonance of vocal tract (Hz)
    - formants_f1_f2_ratio: Vocal tract length proxy
    - harmonicity_db: Voice quality harmonic-to-noise ratio
    - tempo_rate: Syllable rate
    """
    f0 = float(audio_meta.get("f0_hz", 160.0))
    sc = float(audio_meta.get("spectral_centroid", 1850.0))
    f1_f2 = float(audio_meta.get("f1_f2_ratio", 2.2))
    harm = float(audio_meta.get("harmonicity_db", 14.5))
    
    return {
        "f0_hz": f0,
        "spectral_centroid": sc,
        "f1_f2_ratio": f1_f2,
        "harmonicity_db": harm
    }


def compare_voice_samples(
    sample_a: Optional[Dict[str, Any]],
    sample_b: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Compare two voice recordings.
    Returns:
    - similarity: 0.0 to 1.0
    - is_conflict: bool
    - status: 'STRONG_SUPPORT', 'MODERATE_SUPPORT', 'INCONCLUSIVE', 'CONFLICT', 'NO_SAMPLE'
    - notes: human-readable explanation
    - requires_human_verification: bool
    """
    if not sample_a or not sample_b:
        return {
            "similarity": 0.5,
            "has_data": False,
            "status": "NO_SAMPLE",
            "is_conflict": False,
            "requires_human_verification": False,
            "note": "Voice data not provided for one or both cases (treated as neutral)."
        }
        
    feat_a = extract_simulated_acoustic_features(sample_a)
    feat_b = extract_simulated_acoustic_features(sample_b)
    
    # 1. Pitch distance (normalized: 60 Hz difference is major)
    f0_diff = abs(feat_a["f0_hz"] - feat_b["f0_hz"])
    f0_score = max(0.0, 1.0 - (f0_diff / 55.0))
    
    # 2. Spectral centroid difference (timbre)
    sc_diff = abs(feat_a["spectral_centroid"] - feat_b["spectral_centroid"])
    sc_score = max(0.0, 1.0 - (sc_diff / 800.0))
    
    # 3. Formant ratio (vocal anatomy)
    f12_diff = abs(feat_a["f1_f2_ratio"] - feat_b["f1_f2_ratio"])
    f12_score = max(0.0, 1.0 - (f12_diff / 1.0))
    
    # 4. Harmonicity difference
    harm_diff = abs(feat_a["harmonicity_db"] - feat_b["harmonicity_db"])
    harm_score = max(0.0, 1.0 - (harm_diff / 8.0))
    
    # Weighted composite similarity
    similarity = (
        0.35 * f0_score +
        0.30 * sc_score +
        0.20 * f12_score +
        0.15 * harm_score
    )
    similarity = round(min(1.0, max(0.0, similarity)), 3)
    
    # Thresholding & Conflict logic
    # Adult male typically 85-155 Hz; adult female 165-255 Hz; child 250-400 Hz.
    # Large pitch mismatch (> 80 Hz) indicates strong vocal tract conflict.
    pitch_conflict = f0_diff > 85.0
    
    if pitch_conflict or similarity < 0.35:
        is_conflict = True
        status = "CONFLICT"
        requires_human = True
        note = (f"Acoustic conflict detected: Pitch variance {f0_diff:.1f} Hz exceeds allowable vocal "
                f"profile (Similarity {similarity*100:.1f}%). Flagged for expert review.")
    elif similarity >= 0.75:
        is_conflict = False
        status = "STRONG_SUPPORT"
        requires_human = True  # Always requires human sign-off as supporting evidence
        note = (f"Voice acoustics strongly consistent ({similarity*100:.1f}% match). Pitch and vocal "
                f"timbre align within normal variance. (Supporting evidence only)")
    elif similarity >= 0.55:
        is_conflict = False
        status = "MODERATE_SUPPORT"
        requires_human = True
        note = f"Moderate acoustic compatibility ({similarity*100:.1f}%). Background noise or stress may be present."
    else:
        is_conflict = False
        status = "INCONCLUSIVE"
        requires_human = True
        note = f"Inconclusive voice comparison ({similarity*100:.1f}%). Requires field officer interview."
        
    return {
        "similarity": similarity,
        "has_data": True,
        "f0_diff_hz": round(f0_diff, 1),
        "status": status,
        "is_conflict": is_conflict,
        "requires_human_verification": requires_human,
        "authorized_consent": sample_a.get("consent_given", True) and sample_b.get("consent_given", True),
        "note": note
    }

