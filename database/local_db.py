"""Local SQLite Storage Engine for Offline-First Operation.
Ensures zero-connectivity functionality in relief camps, shelters, and field hospitals.
"""
import sqlite3
import json
import uuid
import os
import hmac
import hashlib
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
            photo_path TEXT,
            voice_path TEXT,
            created_by TEXT,
            family_member_id TEXT,
            status TEXT DEFAULT 'ACTIVE',
            sync_status TEXT DEFAULT 'SYNCED',
            offline_created INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        )
        """)

        # Migration for older DB files without the newer columns
        try:
            cursor.execute("SELECT family_member_id FROM cases LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("ALTER TABLE cases ADD COLUMN family_member_id TEXT")
        try:
            cursor.execute("SELECT created_by FROM cases LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("ALTER TABLE cases ADD COLUMN created_by TEXT")
        try:
            cursor.execute("SELECT photo_path FROM cases LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("ALTER TABLE cases ADD COLUMN photo_path TEXT")
        try:
            cursor.execute("SELECT voice_path FROM cases LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("ALTER TABLE cases ADD COLUMN voice_path TEXT")
        conn.commit()
        
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

        # 2a. Staff Accounts + Family Accounts for role-based access control
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS staff_accounts (
            id TEXT PRIMARY KEY,
            staff_id TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            must_change_password INTEGER DEFAULT 1,
            email_verified INTEGER DEFAULT 0,
            created_by TEXT,
            created_at TEXT,
            last_login TEXT
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS family_members (
            id TEXT PRIMARY KEY,
            member_id TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            phone TEXT,
            relation_to_missing TEXT,
            is_active INTEGER DEFAULT 1,
            must_change_password INTEGER DEFAULT 1,
            created_at TEXT,
            last_login TEXT
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS family_verification_answers (
            id TEXT PRIMARY KEY,
            family_member_id TEXT NOT NULL,
            case_id TEXT NOT NULL,
            match_score REAL NOT NULL,
            status TEXT NOT NULL,
            question_text TEXT NOT NULL,
            answer_text TEXT,
            private_notes TEXT,
            created_at TEXT,
            updated_at TEXT
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
        _ensure_demo_accounts()


def _hash_password(password: str) -> str:
    """Hash a password using PBKDF2-HMAC-SHA256."""
    if not password:
        raise ValueError("Password cannot be empty.")
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200000)
    return f"pbkdf2_sha256${salt.hex()}${digest.hex()}"


def _verify_password(password: str, password_hash: str) -> bool:
    if not password or not password_hash:
        return False
    if not password_hash.startswith("pbkdf2_sha256$"):
        return False
    _, salt_hex, digest_hex = password_hash.split("$")
    salt = bytes.fromhex(salt_hex)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200000)
    return hmac.compare_digest(derived.hex(), digest_hex)


def add_audit_log(actor_id: str, action_type: str, target_case_code: Optional[str] = None, details: str = "") -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO audit_log (id, actor_id, action_type, target_case_code, details, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), actor_id, action_type, target_case_code, details, datetime.now(timezone.utc).isoformat())
        )
        conn.commit()


def _ensure_demo_accounts() -> None:
    """Create default secure demo accounts for authorized roles and family access."""
    default_staff = [
        {"full_name": "System Administrator", "email": "admin@blackflame.local", "password": "Admin@123", "role": "SYSTEM_ADMINISTRATOR", "staff_id": "STAFF-ADM-1001"},
        {"full_name": "Hospital Intake Officer", "email": "hospital@blackflame.local", "password": "Hospital@123", "role": "HOSPITAL_STAFF", "staff_id": "STAFF-HOSP-1001"},
        {"full_name": "Rescue Camp Coordinator", "email": "rescue@blackflame.local", "password": "Rescue@123", "role": "RESCUE_CAMP_STAFF", "staff_id": "STAFF-RESC-1001"},
    ]
    for account in default_staff:
        existing = get_user_by_email(account["email"])
        if existing:
            continue
        create_staff_account(
            full_name=account["full_name"],
            email=account["email"],
            password=account["password"],
            role=account["role"],
            created_by="SYSTEM",
            staff_id=account["staff_id"],
            email_verified=True,
            must_change_password=True,
        )

    family_email = "family@blackflame.local"
    if not get_user_by_email(family_email, account_type="family"):
        create_family_member(
            full_name="Priya Kumar",
            email=family_email,
            password="Family@123",
            phone="+91 90000 00000",
            relation_to_missing="Mother",
        )


def get_user_by_email(email: str, account_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        if account_type == "family":
            cursor.execute("SELECT * FROM family_members WHERE email = ?", (email.lower(),))
            row = cursor.fetchone()
            if row:
                data = dict(row)
                data["account_type"] = "family"
                return data
            return None
        cursor.execute("SELECT * FROM staff_accounts WHERE email = ?", (email.lower(),))
        row = cursor.fetchone()
        if row:
            data = dict(row)
            data["account_type"] = "staff"
            return data
        cursor.execute("SELECT * FROM family_members WHERE email = ?", (email.lower(),))
        row = cursor.fetchone()
        if row:
            data = dict(row)
            data["account_type"] = "family"
            return data
        return None


def create_staff_account(full_name: str, email: str, password: str, role: str, created_by: str = "SYSTEM", staff_id: Optional[str] = None, email_verified: bool = False, must_change_password: bool = True) -> Dict[str, Any]:
    normalized_role = role.upper()
    allowed = {"SYSTEM_ADMINISTRATOR", "HOSPITAL_STAFF", "RESCUE_CAMP_STAFF"}
    if normalized_role not in allowed:
        raise ValueError(f"Unsupported staff role: {role}")
    if staff_id is None:
        staff_id = f"STAFF-{normalized_role[:4]}-{len(list_staff_accounts()) + 1:04d}"
    account_id = str(uuid.uuid4())
    password_hash = _hash_password(password)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO staff_accounts (id, staff_id, full_name, email, password_hash, role, is_active, must_change_password, email_verified, created_by, created_at, last_login) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (account_id, staff_id, full_name, email.lower(), password_hash, normalized_role, 1, 1 if must_change_password else 0, 1 if email_verified else 0, created_by, datetime.now(timezone.utc).isoformat(), None)
        )
        conn.commit()
    return {"id": account_id, "staff_id": staff_id, "full_name": full_name, "email": email.lower(), "role": normalized_role}


def create_family_member(full_name: str, email: str, password: str, phone: str = "", relation_to_missing: str = "Relative", must_change_password: bool = True) -> Dict[str, Any]:
    member_id = f"FAM-{len(list_family_members()) + 1:04d}"
    member_uuid = str(uuid.uuid4())
    password_hash = _hash_password(password)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO family_members (id, member_id, full_name, email, password_hash, phone, relation_to_missing, is_active, must_change_password, created_at, last_login) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (member_uuid, member_id, full_name, email.lower(), password_hash, phone, relation_to_missing, 1, 1 if must_change_password else 0, datetime.now(timezone.utc).isoformat(), None)
        )
        conn.commit()
    return {"id": member_uuid, "member_id": member_id, "full_name": full_name, "email": email.lower(), "relation_to_missing": relation_to_missing}


def authenticate_user(email: str, password: str, account_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
    user = get_user_by_email(email, account_type=account_type)
    if not user:
        return None
    stored_hash = user.get("password_hash") or user.get("password")
    if not _verify_password(password, stored_hash):
        return None
    if not user.get("is_active", True) and "family" in user.get("account_type", ""):
        return None
    if user.get("account_type") == "staff":
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE staff_accounts SET last_login = ? WHERE id = ?", (datetime.now(timezone.utc).isoformat(), user["id"]))
            conn.commit()
        return {"account_type": "staff", **user}
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE family_members SET last_login = ? WHERE id = ?", (datetime.now(timezone.utc).isoformat(), user["id"]))
        conn.commit()
    return {"account_type": "family", **user}


def list_staff_accounts() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        rows = cursor.execute("SELECT * FROM staff_accounts ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


def list_family_members() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        rows = cursor.execute("SELECT * FROM family_members ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


def save_family_verification_record(family_member_id: str, case_id: str, match_score: float, status: str, question_text: str, answer_text: str = "", private_notes: str = "") -> Dict[str, Any]:
    record_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO family_verification_answers (id, family_member_id, case_id, match_score, status, question_text, answer_text, private_notes, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (record_id, family_member_id, case_id, float(match_score), status, question_text, answer_text, private_notes, now, now)
        )
        conn.commit()
    return {"id": record_id, "status": status, "match_score": float(match_score)}


def get_family_verification_records(family_member_id: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        if family_member_id:
            rows = cursor.execute("SELECT * FROM family_verification_answers WHERE family_member_id = ? ORDER BY created_at DESC", (family_member_id,)).fetchall()
        else:
            rows = cursor.execute("SELECT * FROM family_verification_answers ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


def generate_family_questions(case_data: Dict[str, Any]) -> List[str]:
    clues = []
    if case_data.get("marks"):
        clues.append(f"One identifying detail: {', '.join(case_data.get('marks', [])[:2])}")
    if case_data.get("clothing_description"):
        clues.append(f"A clothing detail: {case_data.get('clothing_description')}")
    if case_data.get("origin_area"):
        clues.append(f"A place detail: {case_data.get('origin_area')}")
    if case_data.get("reporter_relationship"):
        clues.append(f"The relationship to the person: {case_data.get('reporter_relationship')}")

    question_bank = [
        "What is your relationship to this person?",
        "Which identifying detail would only a close family member know?",
        "Can you describe a known family characteristic or a memorable fact about them?",
        "What other detail helps confirm your relationship to this missing person?",
    ]

    generated = []
    for index, question in enumerate(question_bank):
        if index == 0:
            generated.append(question)
        elif clues:
            generated.append(f"{question} Use a detail such as: {clues[index % len(clues)]}")
        else:
            generated.append(question)
    return generated[:4]


def evaluate_family_response(case_data: Dict[str, Any], answers: List[str]) -> Dict[str, Any]:
    text = " ".join(a.lower() for a in answers if a).strip()
    if not text:
        return {"status": "AWAITING_VERIFICATION", "score": 0.0, "is_confirmed": False}

    score = 0.0
    case_text = " ".join([
        str(case_data.get("origin_area") or ""),
        str(case_data.get("clothing_description") or ""),
        str(case_data.get("physical_notes") or ""),
        " ".join(case_data.get("marks") or [])
    ]).lower()

    for token in ["mother", "father", "sister", "brother", "son", "daughter", "uncle", "aunt", "grandparent", "wife", "husband"]:
        if token in text:
            score += 0.15
    for token in ["scar", "mole", "tattoo", "birthmark", "earring", "wrist", "forehead", "knee", "arm", "leg", "shirt", "kurta", "saree", "dress", "jeans"]:
        if token in case_text and token in text:
            score += 0.2
    if case_data.get("origin_area") and case_data.get("origin_area").lower() in text:
        score += 0.2
    if case_data.get("reporter_relationship") and case_data.get("reporter_relationship").lower() in text:
        score += 0.15

    score = min(1.0, score)
    if score >= 0.75:
        status = "POTENTIAL_MATCH"
    elif score >= 0.45:
        status = "VERIFICATION_IN_PROGRESS"
    else:
        status = "AWAITING_VERIFICATION"

    return {"status": status, "score": round(score, 3), "is_confirmed": score >= 0.75 and False}


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
    family_member_id = case_data.get("family_member_id") or case_data.get("created_by")
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO cases (
            id, case_code, case_type, age, age_min, age_max, gender, origin_area,
            height_cm, blood_group, marks, clothing_description, physical_notes,
            condition, declared_name, contact_phone, contact_email,
            reporter_relationship, photo_path, voice_path, created_by, family_member_id,
            status, sync_status, offline_created, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            case_id, case_code, case_data.get("case_type", "MISSING"),
            case_data.get("age"), case_data.get("age_min"), case_data.get("age_max"),
            case_data.get("gender", "UNKNOWN"), case_data.get("origin_area"),
            case_data.get("height_cm"), case_data.get("blood_group"),
            marks_json, case_data.get("clothing_description"),
            case_data.get("physical_notes"), case_data.get("condition", "STABLE"),
            case_data.get("declared_name"), case_data.get("contact_phone"),
            case_data.get("contact_email"), case_data.get("reporter_relationship"),
            case_data.get("photo_path"), case_data.get("voice_path"), case_data.get("created_by"), family_member_id,
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


def get_family_cases(family_member_id: str) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        rows = cursor.execute("SELECT * FROM cases WHERE family_member_id = ? ORDER BY created_at DESC", (family_member_id,)).fetchall()
        return [_row_to_case_dict(r) for r in rows]


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

