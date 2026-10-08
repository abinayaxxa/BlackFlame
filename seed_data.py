"""Seed Data Generator for Black Flame Demonstration.
Creates realistic disaster relief scenarios:
- GREEN Pair: Multi-factor consistent, timeline continuity verified, swab & voice matched.
- YELLOW Pair: Uncertain / needs review, missing swab or voice, partial match.
- RED Pair: Critical conflict (age gap, blood group mismatch, impossible travel speed).
- PENDING SYNC Cases: Field camp offline registrations.
"""
from datetime import datetime, timezone, timedelta
from database.local_db import (
    save_case, save_sighting, save_voice_record, save_swab_record,
    init_local_db
)


def seed_database():
    """Populates realistic demonstration cases."""
    init_local_db()
    now = datetime.now(timezone.utc)
    
    # ---------------- 1. GREEN MATCH PAIR ----------------
    # Missing Person Report (Child: Ravi, Age 7)
    missing_1 = {
        "case_code": "BF-MISS-7812",
        "case_type": "MISSING",
        "age": 7.0,
        "age_min": 6.0,
        "age_max": 8.0,
        "gender": "M",
        "origin_area": "Bhimavaram Riverside",
        "blood_group": "O+",
        "marks": ["scar_left_arm", "mole_face"],
        "clothing_description": "blue shirt and dark shorts",
        "physical_notes": "Slim build, quiet demeanor, scar from childhood fall on left forearm",
        "condition": "UNKNOWN",
        "declared_name": "Ravi Kumar (Protected PII)",
        "contact_phone": "+91 98450 11223",
        "contact_email": "family.kumar@relief.org",
        "reporter_relationship": "Parent / Mother",
        "status": "ACTIVE",
        "sync_status": "SYNCED"
    }
    save_case(missing_1)
    
    # Missing 1 Sighting: Who + Where + When + Direction
    save_sighting({
        "case_id": missing_1["id"],
        "location_name": "Sector 1 River Basin",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "event_timestamp": (now - timedelta(hours=2, minutes=20)).isoformat(),
        "direction_of_movement": "Towards Relief Camp Alpha",
        "observed_by_role": "FAMILY_REPORT",
        "observer_notes": "Separated during flood flash-surge while running toward the high ground",
        "confidence_level": "HIGH"
    })
    
    # Missing 1 Voice (Mother provided audio of child singing/talking)
    save_voice_record({
        "case_id": missing_1["id"],
        "sample_id": "VOICE-REF-7812",
        "f0_hz": 265.0,  # Child pitch
        "spectral_centroid": 2450.0,
        "f1_f2_ratio": 2.45,
        "harmonicity_db": 16.2,
        "duration_seconds": 4.5,
        "consent_given": True,
        "authorized_by": "Family Guardian",
        "sample_notes": "Authorized voice clip from family phone archive"
    })
    
    # Missing 1 Biological Swab (Family reference donor / known biological panel)
    save_swab_record({
        "case_id": missing_1["id"],
        "sample_code": "SWAB-REF-7812",
        "blood_group": "O+",
        "wbc_count": 8.2,
        "rbc_count": 4.8,
        "hgb_level": 13.9,
        "plt_count": 275.0,
        "lab_facility": "State Central Diagnostics",
        "certifying_technician": "Dr. N. Rao",
        "is_authorized": True
    })

    # Unidentified Found Person 1 (Boy rescued at Camp Alpha)
    found_1 = {
        "case_code": "BF-UNID-1049",
        "case_type": "UNIDENTIFIED",
        "age": 8.0,  # Close estimate
        "age_min": 7.0,
        "age_max": 9.0,
        "gender": "M",
        "origin_area": "Bhimavaram Sector",
        "blood_group": "O+",
        "marks": ["scar_left_arm", "mole_face"],
        "clothing_description": "blue shirt, wet fabric",
        "physical_notes": "Mild dehydration, disoriented, responded to local dialect",
        "condition": "CONSCIOUS",
        "declared_name": "Unidentified Boy (Ward 3)",
        "contact_phone": "Camp Alpha Medical Station",
        "reporter_relationship": "Camp Volunteer",
        "status": "INVESTIGATING",
        "sync_status": "SYNCED"
    }
    save_case(found_1)
    
    # Found 1 Sighting: Who + Where + When + Direction
    # 25 minutes later, 1.8 km away, direction aligned Towards Relief Camp Alpha!
    save_sighting({
        "case_id": found_1["id"],
        "location_name": "Relief Camp Alpha",
        "latitude": 12.9820,
        "longitude": 77.6100,
        "event_timestamp": (now - timedelta(hours=1, minutes=55)).isoformat(),
        "direction_of_movement": "Towards Relief Camp Alpha",
        "observed_by_role": "RESCUE_BOAT_TEAM",
        "observer_notes": "Brought in by volunteer skiff from northern dike road",
        "confidence_level": "HIGH"
    })
    
    # Found 1 Voice (Bedside audio with consent)
    save_voice_record({
        "case_id": found_1["id"],
        "sample_id": "VOICE-REC-1049",
        "f0_hz": 268.0,  # Very close pitch to child reference!
        "spectral_centroid": 2420.0,
        "f1_f2_ratio": 2.42,
        "harmonicity_db": 15.8,
        "duration_seconds": 3.8,
        "consent_given": True,
        "authorized_by": "Medical Officer On-Duty",
        "sample_notes": "Bedside audio recording with social worker present"
    })
    
    # Found 1 Swab Record
    save_swab_record({
        "case_id": found_1["id"],
        "sample_code": "SWAB-TEST-1049",
        "blood_group": "O+",
        "wbc_count": 8.6,
        "rbc_count": 4.9,
        "hgb_level": 14.1,
        "plt_count": 280.0,
        "lab_facility": "Camp Alpha Mobile Lab",
        "certifying_technician": "Lab Tech S. Patel",
        "is_authorized": True
    })

    # ---------------- 2. YELLOW MATCH PAIR (Uncertain / Review Needed) ----------------
    # Missing Person 2 (Young adult woman: Ananya, Age 24)
    missing_2 = {
        "case_code": "BF-MISS-3391",
        "case_type": "MISSING",
        "age": 24.0,
        "gender": "F",
        "origin_area": "Bridge East Crossway",
        "blood_group": "B+",
        "marks": ["tattoo_wrist", "birthmark_neck"],
        "clothing_description": "yellow kurta and white scarf",
        "physical_notes": "Height approx 160cm, silver ring on right hand",
        "condition": "UNKNOWN",
        "declared_name": "Ananya Sen (Protected PII)",
        "contact_phone": "+91 97120 44332",
        "reporter_relationship": "Spouse / Husband",
        "status": "ACTIVE",
        "sync_status": "SYNCED"
    }
    save_case(missing_2)
    save_sighting({
        "case_id": missing_2["id"],
        "location_name": "Bridge East Crossway",
        "latitude": 12.9760,
        "longitude": 77.6010,
        "event_timestamp": (now - timedelta(hours=6, minutes=30)).isoformat(),
        "direction_of_movement": "Towards Central Hospital",
        "observed_by_role": "FAMILY_REPORT",
        "observer_notes": "Heading toward clinic before phone died",
        "confidence_level": "MEDIUM"
    })

    # Unidentified Found Person 2 (Disoriented woman found at Highway Shelter 4)
    found_2 = {
        "case_code": "BF-UNID-5582",
        "case_type": "UNIDENTIFIED",
        "age": 27.0,  # Close age
        "gender": "F",
        "origin_area": "Highway Junction",
        "blood_group": "B+",
        "marks": ["tattoo_wrist"],  # 1 shared mark
        "clothing_description": "yellow kurta, dusty",
        "physical_notes": "Concussion, mild amnesia, unable to state family name",
        "condition": "MEMORY_LOSS",
        "declared_name": "Unidentified Patient 14",
        "contact_phone": "Highway Shelter 4 Admin",
        "reporter_relationship": "Shelter Nurse",
        "status": "ACTIVE",
        "sync_status": "SYNCED"
    }
    save_case(found_2)
    save_sighting({
        "case_id": found_2["id"],
        "location_name": "Highway Shelter 4",
        "latitude": 12.9900,
        "longitude": 77.6250,
        "event_timestamp": (now - timedelta(hours=3, minutes=15)).isoformat(),
        "direction_of_movement": "Stationary / Unmoved",
        "observed_by_role": "SHELTER_STAFF",
        "observer_notes": "Arrived on evacuation truck from bridge district",
        "confidence_level": "HIGH"
    })
    # Notice: Swab & Voice NOT yet recorded for this pair, so system identifies it as YELLOW (Needs Review!)

    # ---------------- 3. RED CONFLICT PAIR (Contradiction Detected) ----------------
    # Unidentified Person 3 (Elderly male age 68, Blood group A-)
    found_3 = {
        "case_code": "BF-UNID-9921",
        "case_type": "UNIDENTIFIED",
        "age": 68.0,
        "gender": "M",
        "origin_area": "West Ridge Zone",
        "blood_group": "A-",
        "marks": ["surgery_scar_abdomen", "limp_right_leg"],
        "clothing_description": "grey jacket and dark trousers",
        "physical_notes": "Elderly man, walking cane lost during evacuation",
        "condition": "INJURED",
        "declared_name": "Unidentified Senior Citizen",
        "contact_phone": "Central General Hospital Ward 2",
        "reporter_relationship": "Hospital Social Worker",
        "status": "ACTIVE",
        "sync_status": "SYNCED"
    }
    save_case(found_3)
    save_sighting({
        "case_id": found_3["id"],
        "location_name": "West Ridge Evacuation Zone",
        "latitude": 12.9500,
        "longitude": 77.5600,
        "event_timestamp": (now - timedelta(hours=2, minutes=0)).isoformat(),
        "direction_of_movement": "South",
        "observed_by_role": "HOSPITAL_AMBULANCE",
        "observer_notes": "Found in flooded basement by search team",
        "confidence_level": "HIGH"
    })
    save_swab_record({
        "case_id": found_3["id"],
        "sample_code": "SWAB-TEST-9921",
        "blood_group": "A-",
        "wbc_count": 12.5,
        "rbc_count": 3.8,
        "hgb_level": 11.2,
        "plt_count": 190.0,
        "lab_facility": "Central Hospital Clinical Lab",
        "certifying_technician": "Dr. P. Sen",
        "is_authorized": True
    })

    # ---------------- 4. OFFLINE-REGISTERED CASE (Pending Sync) ----------------
    # Entered at remote relief shelter without internet connectivity
    offline_case = {
        "case_code": "BF-OFFLINE-4041",
        "case_type": "UNIDENTIFIED",
        "age": 35.0,
        "gender": "F",
        "origin_area": "North Hill Checkpoint",
        "blood_group": "AB+",
        "marks": ["burn_scar_hand"],
        "clothing_description": "green saree with gold border",
        "physical_notes": "Registered offline by frontline relief volunteer at camp gate",
        "condition": "STABLE",
        "declared_name": "Unidentified Woman (Offline Intake)",
        "contact_phone": "Camp North Intake Desk",
        "reporter_relationship": "Relief Volunteer",
        "status": "ACTIVE",
        "sync_status": "PENDING_SYNC"
    }
    save_case(offline_case, is_offline=True)
    save_sighting({
        "case_id": offline_case["id"],
        "location_name": "North Hill Checkpoint",
        "latitude": 12.9950,
        "longitude": 77.5900,
        "event_timestamp": (now - timedelta(minutes=45)).isoformat(),
        "direction_of_movement": "Towards Community Stadium",
        "observed_by_role": "FIELD_VOLUNTEER",
        "observer_notes": "Intake completed on offline tablet during communications blackout",
        "confidence_level": "HIGH"
    }, is_offline=True)


if __name__ == "__main__":
    seed_database()
    print("Database successfully seeded with realistic disaster response cases!")

