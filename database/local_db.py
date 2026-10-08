"""Local SQLite Storage Engine for Offline-First Operation.
Ensures zero-connectivity functionality in relief camps, shelters, and field hospitals.
"""
import sqlite3
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from config import OFFLINE_DB_PATH


def get_connection() -> sqlite3.Connection:
    """Obtain SQLite connection with row dictionary factory."""
    conn = sqlite3.connect(OFFLINE_DB_PATH, timeout=15.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_local_db():
    """Initializes local tables for offline persistence."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Cases Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            id TEXT PRIMARY KEY,
            case_code TEXT UNIQUE NOT NULL,
            case_type TEXT NOT NULL,
            age REAL,
            age_min REAL,
            age_max REAL,
            gender TEXT NOT NULL,
            origin_area TEXT,
            height_cm REAL,
            blood_group TEXT,
            marks TEXT,
            clothing_description TEXT,
            physical_notes TEXT,
            condition TEXT DEFAULT 'STABLE',
            declared_name TEXT,
            contact_phone TEXT,
            contact_email TEXT,
            reporter_relationship TEXT,
            status TEXT DEFAULT 'ACTIVE',
            sync_status TEXT DEFAULT 'SYNCED',
            offline_created INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        )
        """)
        
        # 2. Sightings Table: Who + Where + When + Direction
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sightings (
            id TEXT PRIMARY KEY,
            case_id TEXT,
            location_name TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            event_timestamp TEXT NOT NULL,
            direction_of_movement TEXT,
            observed_by_role TEXT,
            observer_notes TEXT,
            confidence_level TEXT DEFAULT 'HIGH',
            sync_status TEXT DEFAULT 'SYNCED',
            created_at TEXT
        )
        """)
        
        # 3. Family Relations
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS family_relations (
            id TEXT PRIMARY KEY,
            case_id TEXT,
            relative_relation TEXT NOT NULL,
            relative_name TEXT,
            relative_village TEXT,
            contact_detail TEXT,
            notes TEXT,
            created_at TEXT
        )
        """)
        
        # 4. Voice Records
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS voice_records (
            id TEXT PRIMARY KEY,
            case_id TEXT,
            sample_id TEXT UNIQUE NOT NULL,
            f0_hz REAL,
            spectral_centroid REAL,
            f1_f2_ratio REAL,
            harmonicity_db REAL,
            duration_seconds REAL,
            consent_given INTEGER DEFAULT 1,
            authorized_by TEXT,
            sample_notes TEXT,
            created_at TEXT
        )
        """)
        
        # 5. Swabs Table: Biological hematology parameters
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS biological_swabs (
            id TEXT PRIMARY KEY,
            case_id TEXT,
            sample_code TEXT UNIQUE NOT NULL,
            blood_group TEXT NOT NULL,
            wbc_count REAL,
            rbc_count REAL,
            hgb_level REAL,
            plt_count REAL,
            lab_facility TEXT,
            certifying_technician TEXT,
            is_authorized INTEGER DEFAULT 1,
            created_at TEXT
        )
        """)
        
        # 6. Matches Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id TEXT PRIMARY KEY,
            missing_case_id TEXT,
            unidentified_case_id TEXT,
            decision_level TEXT NOT NULL,
            numerical_score REAL NOT NULL,
            has_critical_conflict INTEGER DEFAULT 0,
            supporting_factors TEXT,
            conflicting_factors TEXT,
            pending_factors TEXT,
            evaluation_breakdown TEXT,
            status TEXT DEFAULT 'PROPOSED',
            created_at TEXT,
            updated_at TEXT
        )
        """)
        
        # 7. Verifications Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS verifications (
            id TEXT PRIMARY KEY,
            match_id TEXT,
            stage TEXT NOT NULL,
            verified_by_officer TEXT NOT NULL,
            officer_badge_id TEXT NOT NULL,
            verification_notes TEXT NOT NULL,
            photo_verified INTEGER DEFAULT 0,
            swab_confirmed INTEGER DEFAULT 0,
            voice_confirmed INTEGER DEFAULT 0,
            reunification_certificate_code TEXT,
            action_timestamp TEXT
        )
        """)
        
        # 8. Audit Log
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id TEXT PRIMARY KEY,
            actor_id TEXT NOT NULL,
            action_type TEXT NOT NULL,
            target_case_code TEXT,
            details TEXT,
            timestamp TEXT
        )
        """)
        
        conn.commit()


# Helper to convert sqlite rows to dicts
def _row_to_case_dict(row: sqlite3.Row) -> Dict[str, Any]:
    d = dict(row)
    if d.get("marks"):
        try:
            d["marks"] = json.loads(d["marks"])
        except Exception:
            d["marks"] = [m.strip() for m in d["marks"].split(",") if m.strip()]
    else:
        d["marks"] = []
    return d


# ---------------- CRUD Operations ----------------

def save_case(case_data: Dict[str, Any], is_offline: bool = False) -> Dict[str, Any]:
    """Saves or updates a case in the local database."""
    case_id = case_data.get("id") or str(uuid.uuid4())
    case_code = case_data.get("case_code") or (
        f"BF-{'MISS' if case_data.get('case_type') == 'MISSING' else 'UNID'}-{uuid.uuid4().hex[:6].upper()}"
    )
    now = datetime.now(timezone.utc).isoformat()
    
    marks_json = json.dumps(case_data.get("marks", [])) if isinstance(case_data.get("marks"), (list, set)) else str(case_data.get("marks") or "[]")
    sync_status = "PENDING_SYNC" if is_offline else case_data.get("sync_status", "SYNCED")
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO cases (
            id, case_code, case_type, age, age_min, age_max, gender, origin_area,
            height_cm, blood_group, marks, clothing_description, physical_notes,
            condition, declared_name, contact_phone, contact_email,
            reporter_relationship, status, sync_status, offline_created,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            case_id, case_code, case_data.get("case_type", "MISSING"),
            case_data.get("age"), case_data.get("age_min"), case_data.get("age_max"),
            case_data.get("gender", "UNKNOWN"), case_data.get("origin_area"),
            case_data.get("height_cm"), case_data.get("blood_group"),
            marks_json, case_data.get("clothing_description"),
            case_data.get("physical_notes"), case_data.get("condition", "STABLE"),
            case_data.get("declared_name"), case_data.get("contact_phone"),
            case_data.get("contact_email"), case_data.get("reporter_relationship"),
            case_data.get("status", "ACTIVE"), sync_status,
            1 if is_offline else 0,
            case_data.get("created_at") or now, now
        ))
        conn.commit()
        
    case_data["id"] = case_id
    case_data["case_code"] = case_code
    case_data["sync_status"] = sync_status
    return case_data


def save_sighting(sighting_data: Dict[str, Any], is_offline: bool = False) -> Dict[str, Any]:
    """Saves a sighting / timeline record (Who + Where + When + Direction)."""
    sight_id = sighting_data.get("id") or str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    sync_status = "PENDING_SYNC" if is_offline else sighting_data.get("sync_status", "SYNCED")
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO sightings (
            id, case_id, location_name, latitude, longitude, event_timestamp,
            direction_of_movement, observed_by_role, observer_notes,
            confidence_level, sync_status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sight_id, sighting_data.get("case_id"),
            sighting_data.get("location_name", "Unknown Area"),
            sighting_data.get("latitude"), sighting_data.get("longitude"),
            sighting_data.get("event_timestamp") or now,
            sighting_data.get("direction_of_movement", "Stationary / Unmoved"),
            sighting_data.get("observed_by_role", "VOLUNTEER"),
            sighting_data.get("observer_notes"),
            sighting_data.get("confidence_level", "HIGH"),
            sync_status, sighting_data.get("created_at") or now
        ))
        conn.commit()
    sighting_data["id"] = sight_id
    sighting_data["sync_status"] = sync_status
    return sighting_data


def save_voice_record(voice_data: Dict[str, Any]) -> Dict[str, Any]:
    """Saves a voice acoustic signature record."""
    v_id = voice_data.get("id") or str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO voice_records (
            id, case_id, sample_id, f0_hz, spectral_centroid, f1_f2_ratio,
            harmonicity_db, duration_seconds, consent_given, authorized_by,
            sample_notes, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            v_id, voice_data.get("case_id"), voice_data.get("sample_id"),
            voice_data.get("f0_hz"), voice_data.get("spectral_centroid"),
            voice_data.get("f1_f2_ratio"), voice_data.get("harmonicity_db"),
            voice_data.get("duration_seconds", 3.0),
            1 if voice_data.get("consent_given", True) else 0,
            voice_data.get("authorized_by"), voice_data.get("sample_notes"),
            voice_data.get("created_at") or now
        ))
        conn.commit()
    voice_data["id"] = v_id
    return voice_data


def save_swab_record(swab_data: Dict[str, Any]) -> Dict[str, Any]:
    """Saves a swab biological record (WBC, RBC, HGB, PLT)."""
    s_id = swab_data.get("id") or str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO biological_swabs (
            id, case_id, sample_code, blood_group, wbc_count, rbc_count,
            hgb_level, plt_count, lab_facility, certifying_technician,
            is_authorized, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            s_id, swab_data.get("case_id"), swab_data.get("sample_code"),
            swab_data.get("blood_group", "O+"),
            swab_data.get("wbc_count") or swab_data.get("wbc"),
            swab_data.get("rbc_count") or swab_data.get("rbc"),
            swab_data.get("hgb_level") or swab_data.get("hgb"),
            swab_data.get("plt_count") or swab_data.get("plt"),
            swab_data.get("lab_facility", "Field Diagnostic Unit"),
            swab_data.get("certifying_technician", "Dr. A. Sharma"),
            1 if swab_data.get("is_authorized", True) else 0,
            swab_data.get("created_at") or now
        ))
        conn.commit()
    swab_data["id"] = s_id
    return swab_data


def save_match_evaluation(match_res: Dict[str, Any]) -> None:
    """Saves match evaluation (GREEN, YELLOW, RED) with explainability details."""
    m_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    exp = match_res.get("explanation", {})
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO matches (
            id, missing_case_id, unidentified_case_id, decision_level,
            numerical_score, has_critical_conflict, supporting_factors,
            conflicting_factors, pending_factors, evaluation_breakdown,
            status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            m_id, match_res.get("case_a_id"), match_res.get("case_b_id"),
            match_res.get("decision_level"), match_res.get("numerical_score", 0.0),
            1 if match_res.get("conflicts", {}).get("has_critical_conflict") else 0,
            json.dumps(exp.get("supporting_factors", [])),
            json.dumps(exp.get("conflicting_factors", [])),
            json.dumps(exp.get("pending_factors", [])),
            json.dumps(match_res),
            "PROPOSED", now, now
        ))
        conn.commit()


def save_verification(verif_data: Dict[str, Any]) -> str:
    """Records human verification sign-off and returns certificate code if authorized."""
    v_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    cert_code = f"BF-CERT-{uuid.uuid4().hex[:8].upper()}" if verif_data.get("stage") == "AUTHORIZED_FOR_REUNIFICATION" else None
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO verifications (
            id, match_id, stage, verified_by_officer, officer_badge_id,
            verification_notes, photo_verified, swab_confirmed, voice_confirmed,
            reunification_certificate_code, action_timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            v_id, verif_data.get("match_id"), verif_data.get("stage"),
            verif_data.get("verified_by_officer"), verif_data.get("officer_badge_id"),
            verif_data.get("verification_notes"),
            1 if verif_data.get("photo_verified") else 0,
            1 if verif_data.get("swab_confirmed") else 0,
            1 if verif_data.get("voice_confirmed") else 0,
            cert_code, now
        ))
        conn.commit()
    return cert_code


def get_all_cases(case_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves all cases, with related sightings and clinical data attached."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if case_type:
            cursor.execute("SELECT * FROM cases WHERE case_type = ? ORDER BY created_at DESC", (case_type,))
        else:
            cursor.execute("SELECT * FROM cases ORDER BY created_at DESC")
        cases = [_row_to_case_dict(r) for r in cursor.fetchall()]
        
        # Attach latest sighting, voice, and swab if available
        for c in cases:
            cid = c["id"]
            # Sighting
            cursor.execute("SELECT * FROM sightings WHERE case_id = ? ORDER BY event_timestamp DESC LIMIT 1", (cid,))
            s = cursor.fetchone()
            if s:
                c["last_seen_place"] = s["location_name"]
                c["found_place"] = s["location_name"]
                c["last_seen_time"] = s["event_timestamp"]
                c["found_time"] = s["event_timestamp"]
                c["direction_of_movement"] = s["direction_of_movement"]
                c["latitude"] = s["latitude"]
                c["longitude"] = s["longitude"]
                
            # Voice
            cursor.execute("SELECT * FROM voice_records WHERE case_id = ? LIMIT 1", (cid,))
            v = cursor.fetchone()
            if v:
                c["voice_record"] = dict(v)
                
            # Swab
            cursor.execute("SELECT * FROM biological_swabs WHERE case_id = ? LIMIT 1", (cid,))
            sw = cursor.fetchone()
            if sw:
                sw_d = dict(sw)
                sw_d["wbc"] = sw_d["wbc_count"]
                sw_d["rbc"] = sw_d["rbc_count"]
                sw_d["hgb"] = sw_d["hgb_level"]
                sw_d["plt"] = sw_d["plt_count"]
                c["swab_record"] = sw_d
                
    return cases


def get_case_by_code(case_code: str) -> Optional[Dict[str, Any]]:
    """Look up a single case by case code."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cases WHERE case_code = ?", (case_code,))
        row = cursor.fetchone()
        if not row:
            return None
        c = _row_to_case_dict(row)
        
        cursor.execute("SELECT * FROM sightings WHERE case_id = ? ORDER BY event_timestamp ASC", (c["id"],))
        c["all_sightings"] = [dict(s) for s in cursor.fetchall()]
        
        cursor.execute("SELECT * FROM voice_records WHERE case_id = ?", (c["id"],))
        v = cursor.fetchone()
        if v:
            c["voice_record"] = dict(v)
            
        cursor.execute("SELECT * FROM biological_swabs WHERE case_id = ?", (c["id"],))
        sw = cursor.fetchone()
        if sw:
            c["swab_record"] = dict(sw)
            
        return c


def get_pending_sync_items() -> Dict[str, List[Dict[str, Any]]]:
    """Retrieves all locally created or modified records waiting to sync to Supabase."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cases WHERE sync_status = 'PENDING_SYNC'")
        cases = [dict(r) for r in cursor.fetchall()]
        
        cursor.execute("SELECT * FROM sightings WHERE sync_status = 'PENDING_SYNC'")
        sightings = [dict(r) for r in cursor.fetchall()]
        
        return {"cases": cases, "sightings": sightings}


def mark_items_as_synced(case_ids: List[str], sighting_ids: List[str]) -> None:
    """Marks items as synced once pushed to Supabase."""
    with get_connection() as conn:
        cursor = conn.cursor()
        for cid in case_ids:
            cursor.execute("UPDATE cases SET sync_status = 'SYNCED' WHERE id = ?", (cid,))
        for sid in sighting_ids:
            cursor.execute("UPDATE sightings SET sync_status = 'SYNCED' WHERE id = ?", (sid,))
        conn.commit()


# Initialize database automatically
init_local_db()

