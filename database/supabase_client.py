"""Supabase PostgreSQL Client Interface.
Manages centralized cloud data access and synchronization with graceful offline fallback.
"""
from typing import Dict, Any, List, Optional
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY


_client: Optional[Client] = None
_is_connected: Optional[bool] = None


def get_supabase() -> Optional[Client]:
    """Obtains the singleton Supabase client."""
    global _client
    if _client is None:
        try:
            if SUPABASE_URL and SUPABASE_KEY:
                _client = create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception:
            _client = None
    return _client


def check_supabase_health() -> Dict[str, Any]:
    """Checks whether the Supabase PostgreSQL backend is reachable."""
    global _is_connected
    client = get_supabase()
    if not client:
        _is_connected = False
        return {"online": False, "message": "Supabase client unconfigured"}
        
    try:
        # Ping profiles or cases
        res = client.table("profiles").select("id").limit(1).execute()
        _is_connected = True
        return {"online": True, "message": "Connected to Supabase PostgreSQL", "latency": "OK"}
    except Exception as e:
        _is_connected = False
        return {"online": False, "message": f"Connection unavailable: {str(e)}"}


def push_case_to_supabase(case_dict: Dict[str, Any]) -> bool:
    """Attempts to upsert a case to Supabase PostgreSQL."""
    client = get_supabase()
    if not client:
        return False
        
    try:
        # Sanitize for remote table
        payload = {
            "case_code": case_dict.get("case_code"),
            "person_name": case_dict.get("declared_name", "ANONYMOUS"),
            "age": int(case_dict.get("age") or 25),
            "gender": case_dict.get("gender", "UNKNOWN"),
            "blood_group": case_dict.get("blood_group"),
            "marks": case_dict.get("marks", []),
            "clothes": case_dict.get("clothing_description", ""),
            "last_seen_place": case_dict.get("last_seen_place", ""),
            "disaster_name": "Disaster Relief Operation",
            "contact_phone": case_dict.get("contact_phone", "")
        }
        
        # We try to push to missing_reports if missing, or found_persons if unidentified
        target_table = "missing_reports" if case_dict.get("case_type") == "MISSING" else "found_persons"
        
        if target_table == "found_persons":
            payload_found = {
                "temp_id": case_dict.get("case_code"),
                "est_age": int(case_dict.get("age") or 25),
                "gender": case_dict.get("gender", "UNKNOWN"),
                "blood_group": case_dict.get("blood_group"),
                "marks": case_dict.get("marks", []),
                "clothes": case_dict.get("clothing_description", ""),
                "found_place": case_dict.get("found_place") or case_dict.get("last_seen_place", ""),
                "condition": case_dict.get("condition", "conscious"),
                "source_name": "Relief Camp Field Team",
                "source_type": "shelter"
            }
            client.table("found_persons").insert(payload_found).execute()
        else:
            client.table("missing_reports").insert(payload).execute()
            
        return True
    except Exception as e:
        # Ignore and allow offline queue to retain
        print(f"Supabase push notice: {e}")
        return False

