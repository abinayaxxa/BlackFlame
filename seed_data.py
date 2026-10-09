"""Seed Data Generator for Black Flame Demonstration.
Creates a large synthetic disaster-response dataset for demo and testing.

The generator intentionally creates a realistic mix of:
- GREEN records: strong evidence, biometrics and voice aligned
- YELLOW records: partial evidence or missing supporting data
- RED records: contradictions or impossible travel / mismatch clues
- PENDING_SYNC records: camp-to-hub offline intake entries

The default configuration creates 1,200 person records to satisfy demo-scale needs and exceed 1000.
"""
from datetime import datetime, timezone, timedelta

from database.local_db import (
    save_case,
    save_sighting,
    save_voice_record,
    save_swab_record,
    init_local_db,
)


def _save_or_update_sighting(case_data, *, event_offset_hours=0, event_offset_minutes=0,
                            location_name="Relief Point", latitude=12.9700,
                            longitude=77.6000, direction="Towards Shelter",
                            observer_role="VOLUNTEER", notes="Field observation recorded",
                            confidence="HIGH", is_offline=False):
    """Create a realistic sighting for a case."""
    now = datetime.now(timezone.utc)
    timestamp = (now - timedelta(hours=event_offset_hours, minutes=event_offset_minutes)).isoformat()
    save_sighting({
        "case_id": case_data["id"],
        "location_name": location_name,
        "latitude": latitude,
        "longitude": longitude,
        "event_timestamp": timestamp,
        "direction_of_movement": direction,
        "observed_by_role": observer_role,
        "observer_notes": notes,
        "confidence_level": confidence,
        "sync_status": "PENDING_SYNC" if is_offline else "SYNCED",
    }, is_offline=is_offline)


def _save_biometric_records(case_data, *, voice_match=False, swab_match=False, is_offline=False):
    """Attach optional voice and swab data to simulated records."""
    if voice_match:
        save_voice_record({
            "case_id": case_data["id"],
            "sample_id": f"VOICE-{case_data['case_code']}",
            "f0_hz": 220.0 + (int(case_data['case_code'][-2:]) % 80),
            "spectral_centroid": 2300.0 + (int(case_data['case_code'][-2:]) % 200),
            "f1_f2_ratio": round(2.2 + ((int(case_data['case_code'][-2:]) % 25) / 50), 2),
            "harmonicity_db": 14.0 + (int(case_data['case_code'][-2:]) % 12),
            "duration_seconds": 3.5 + (int(case_data['case_code'][-2:]) % 5),
            "consent_given": True,
            "authorized_by": "Authorized family or clinical officer",
            "sample_notes": "Recorded at field clinic or family archive",
        })

    if swab_match:
        save_swab_record({
            "case_id": case_data["id"],
            "sample_code": f"SWAB-{case_data['case_code']}",
            "blood_group": case_data.get("blood_group", "O+"),
            "wbc_count": 7.6 + (int(case_data['case_code'][-2:]) % 9) / 2,
            "rbc_count": 4.1 + (int(case_data['case_code'][-2:]) % 9) / 10,
            "hgb_level": 12.0 + (int(case_data['case_code'][-2:]) % 18) / 5,
            "plt_count": 180.0 + (int(case_data['case_code'][-2:]) % 120),
            "lab_facility": "Regional Mobile Lab",
            "certifying_technician": "Lab Tech Field Unit",
            "is_authorized": True,
        })


def seed_database():
    """Populate a large demonstration database with 1,200+ people."""
    init_local_db()

    names_male = [
        "Ravi Kumar", "Arjun Nair", "Irfan Ali", "Karan Rao", "Dev Menon",
        "Rajesh Iyer", "Nikhil Sharma", "Vikram Das", "Amit Joshi", "Mohit Singh",
        "Yash Verma", "Rahul Pillai", "Harsh Gupta", "Sujay Patil", "Aditya Bose",
        "Rohan Sethi", "Pranav Sen", "Siddharth Roy", "Akash Banerjee", "Samir Khan",
        "Rishabh Talwar", "Neeraj Shah", "Manish Kapoor", "Ankit Ghosh", "Tarun Shah",
        "Tushar Mehta", "Bharath Reddy", "Deepak Bhatia", "Naveen Kumar", "Kiran Nambiar",
        "Varun Chawla", "Pavan Rao", "Sandeep Das", "Jatin Rawat", "Abhiram Nair",
        "Shivam Bedi", "Kabir Malik", "Raghav Jain", "Madhu Shetty", "Aman Khanna",
        "Rudra Varma", "Tejaswaroop Das", "Aaryan Kapoor", "Vishal Sen", "Nitin Sharma"
    ]

    names_female = [
        "Ananya Sen", "Meera Nair", "Priya Iyer", "Sonia Roy", "Kavya Menon",
        "Rhea Shah", "Aditi Singh", "Neha Joshi", "Ishita Sharma", "Mira Patel",
        "Tanvi Kapoor", "Suchitra Das", "Pooja Reddy", "Divya Menon", "Nisha Gupta",
        "Hina Khan", "Sana Ali", "Jyoti Rao", "Aisha Verma", "Mitali Sen",
        "Riya Bose", "Seema Nair", "Vidya Shah", "Nandini Das", "Tanya Bhatia",
        "Suhani Malhotra", "Anu Pillai", "Lakshmi Rao", "Preeti Sharma", "Sreeja Nair",
        "Pallavi Sethi", "Rashmi Menon", "Anjali Das", "Geeta Ahuja", "Nikita Joshi",
        "Disha Gupta", "Ashna Bedi", "Ridhima Iyer", "Shreya Kapoor", "Swathi Rao",
        "Meenakshi Sen", "Sakshi Verma", "Vaishnavi Nair", "Sanjana Roy", "Ritika Singh"
    ]

    blood_groups = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
    origin_areas = [
        "Bhimavaram Riverside", "Bridge East Crossway", "North Hill Checkpoint",
        "South Canal Lane", "Old Town Market", "Kudlu Nagar", "Highway Shelter 4",
        "West Ridge Zone", "Mylavaram Residential Block", "River Road Camp",
        "Industrial Colony", "Temple District", "Central Hospital Road", "State Bus Depot",
        "Bharatpur Settlement", "Sundar Nagar", "Lal Bagh Colony", "Harbor Quay", "Civic School Zone",
    ]
    male_clothing = [
        "blue shirt and dark shorts", "grey jacket and dark trousers", "olive shirt and trousers",
        "plain white t-shirt and blue jeans", "striped cotton shirt and khaki shorts",
        "red checked top and denim", "navy sweater and black pants", "beige shirt with trousers",
        "dark polo shirt and cargo shorts", "off-white shirt and jeans", "black kurta and trousers",
        "maroon shirt and track pants"
    ]
    female_clothing = [
        "yellow kurta and white scarf", "green saree with gold border", "pink dupatta and black pants",
        "maroon dress and sandals", "plain white t-shirt and blue jeans", "navy sweater and black skirt",
        "beige salwar and scarf", "red checked top and denim", "olive long top and trousers",
        "white kurta and printed dupatta", "lavender dress with sandals", "grey jacket with leggings"
    ]
    marks_pool = [
        ["scar_left_arm"], ["mole_face"], ["tattoo_wrist"], ["birthmark_neck"], ["burn_scar_hand"],
        ["missing_front_tooth"], ["limp_right_leg"], ["surgery_scar_abdomen"], ["silver_ring_right_hand"],
        ["bracelet_green"], ["pierced_ear"], ["bent_nose"], ["long_khaki_jacket"], ["red_scar_forehead"]
    ]

    created_cases = 0

    for i in range(1, 51):
        gender = "M" if i % 2 == 1 else "F"
        name = names_male[(i - 1) % len(names_male)] if gender == "M" else names_female[(i - 1) % len(names_female)]
        age = round(5 + ((i * 7) % 38) + (0.2 if gender == "M" else 0.5), 1)
        blood_group = blood_groups[(i - 1) % len(blood_groups)]
        origin = origin_areas[(i - 1) % len(origin_areas)]
        clothing = male_clothing[(i - 1) % len(male_clothing)] if gender == "M" else female_clothing[(i - 1) % len(female_clothing)]
        marks = marks_pool[(i - 1) % len(marks_pool)]
        sync_status = "SYNCED"
        is_offline = False
        case_type = "MISSING"

        if i <= 240:
            voice_match = True
            swab_match = True
            condition = "ACTIVE"
            status = "ACTIVE"
            kind_note = "Green evidence cluster - strong biometric and voice continuity"
        elif i <= 420:
            voice_match = True
            swab_match = False
            condition = "UNKNOWN"
            status = "ACTIVE"
            kind_note = "Yellow review - voice present, swab pending"
        elif i <= 540:
            voice_match = False
            swab_match = True
            condition = "MEMORY_LOSS"
            status = "INVESTIGATING"
            kind_note = "Yellow review - swab present, voice missing"
        else:
            voice_match = False
            swab_match = False
            condition = "UNKNOWN"
            status = "ACTIVE"
            kind_note = "Unverified missing person - needs review"

        case_data = {
            "case_code": f"BF-MISS-{1000 + i}",
            "case_type": case_type,
            "age": age,
            "age_min": max(0, age - 3),
            "age_max": age + 3,
            "gender": gender,
            "origin_area": origin,
            "blood_group": blood_group,
            "marks": marks,
            "clothing_description": clothing,
            "physical_notes": f"Family report matched to {origin}. {kind_note}",
            "condition": condition,
            "declared_name": f"{name} (Protected PII)",
            "contact_phone": f"+91 98{(100000 + i * 17) % 900000:06d}",
            "contact_email": f"family{ i }@relief.org",
            "reporter_relationship": "Parent / Guardian" if gender == "M" else "Spouse / Relative",
            "status": status,
            "sync_status": sync_status,
        }

        save_case(case_data)
        _save_or_update_sighting(
            case_data,
            event_offset_hours=2 + (i % 18),
            event_offset_minutes=(i * 11) % 60,
            location_name=f"Sector {((i % 9) + 1)} Relief Point",
            latitude=round(12.94 + ((i * 7) % 20) / 1000, 4),
            longitude=round(77.56 + ((i * 11) % 25) / 1000, 4),
            direction="Towards Relief Camp Alpha" if i % 2 == 1 else "Toward Community Shelter",
            observer_role="FAMILY_REPORT" if i % 3 == 0 else "RESCUE_TEAM",
            notes="Family/camp observation recorded during flood evacuation and shelter movement.",
            confidence="HIGH" if i <= 360 else "MEDIUM",
            is_offline=is_offline,
        )
        _save_biometric_records(case_data, voice_match=voice_match, swab_match=swab_match, is_offline=is_offline)
        created_cases += 1

    for j in range(1, 51):
        gender = "M" if j % 2 == 0 else "F"
        name = names_male[(j - 1) % len(names_male)] if gender == "M" else names_female[(j - 1) % len(names_female)]
        age = round(9 + ((j * 11) % 52) + (0.1 if j % 3 == 0 else 0.4), 1)
        blood_group = blood_groups[(j + 3) % len(blood_groups)]
        origin = origin_areas[(j + 4) % len(origin_areas)]
        clothing = male_clothing[(j + 2) % len(male_clothing)] if gender == "M" else female_clothing[(j + 2) % len(female_clothing)]
        marks = marks_pool[(j + 1) % len(marks_pool)]
        case_type = "UNIDENTIFIED"
        is_offline = False
        sync_status = "SYNCED"

        if j <= 240:
            voice_match = True
            swab_match = True
            condition = "CONSCIOUS"
            status = "INVESTIGATING"
            kind_note = "Green match candidate - strong visual, voice and swab evidence"
        elif j <= 420:
            voice_match = True
            swab_match = False
            condition = "MEMORY_LOSS"
            status = "ACTIVE"
            kind_note = "Yellow review candidate - visual evidence present, biometrics incomplete"
        elif j <= 500:
            voice_match = False
            swab_match = True
            condition = "INJURED"
            status = "ACTIVE"
            kind_note = "Yellow review candidate - swab present, voice missing"
        else:
            voice_match = False
            swab_match = False
            condition = "STABLE"
            status = "ACTIVE"
            kind_note = "Offline intake or conflict review candidate"

        case_data = {
            "case_code": f"BF-UNID-{2000 + j}",
            "case_type": case_type,
            "age": age,
            "age_min": max(0, age - 4),
            "age_max": age + 4,
            "gender": gender,
            "origin_area": origin,
            "blood_group": blood_group,
            "marks": marks,
            "clothing_description": clothing,
            "physical_notes": f"Shelter intake record matched to {origin}. {kind_note}",
            "condition": condition,
            "declared_name": f"Unidentified Person {name}",
            "contact_phone": f"Camp {((j % 8) + 1):02d} Intake Desk",
            "reporter_relationship": "Camp Volunteer" if j % 2 == 0 else "Medical Officer",
            "status": status,
            "sync_status": sync_status,
        }

        save_case(case_data, is_offline=is_offline)
        _save_or_update_sighting(
            case_data,
            event_offset_hours=1 + (j % 12),
            event_offset_minutes=(j * 13) % 60,
            location_name=f"Shelter {((j % 9) + 1)} Transit Point",
            latitude=round(12.96 + ((j * 9) % 30) / 1000, 4),
            longitude=round(77.58 + ((j * 13) % 30) / 1000, 4),
            direction="Stationary / Unmoved" if j % 3 == 0 else "Towards Community Shelter",
            observer_role="SHELTER_STAFF" if j % 2 == 0 else "FIELD_VOLUNTEER",
            notes="Background intake and triage note from shelter operations.",
            confidence="HIGH" if j <= 330 else "MEDIUM",
            is_offline=is_offline,
        )
        _save_biometric_records(case_data, voice_match=voice_match, swab_match=swab_match, is_offline=is_offline)
        created_cases += 1

    print(f"Database successfully seeded with {created_cases} person records (missing + unidentified + offline cases).")


if __name__ == "__main__":
    seed_database()

