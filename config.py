"""Configuration and constants for Black Flame - Family Reunification System."""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# App Brand
APP_NAME = os.getenv("APP_NAME", "Black Flame")
APP_TAGLINE = os.getenv("APP_TAGLINE", "AI-Powered Family Reunification & Disaster Response System")
LOGO_PATH = BASE_DIR / "assets" / "logo_family_union.svg"
STYLES_PATH = BASE_DIR / "assets" / "styles.css"
OFFLINE_DB_PATH = BASE_DIR / "database" / "black_flame_offline.db"

# Supabase Credentials
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://ambldsnsfmlpemgmkbto.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "sb_publishable_wcb2P6PpapgoLrTDVMFqTA_KZXr8d0L")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

# Standardized Vocabularies
BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"]

PHYSICAL_MARKS = [
    "scar_left_arm",
    "scar_right_arm",
    "scar_forehead",
    "scar_knee",
    "birthmark_neck",
    "birthmark_back",
    "mole_face",
    "tattoo_wrist",
    "tattoo_shoulder",
    "missing_finger",
    "surgery_scar_abdomen",
    "limp_right_leg",
    "burn_scar_hand",
    "mole_left_cheek",
    "earring_piercing_left"
]

CLOTHING_COLORS = [
    "red", "blue", "green", "black", "white", "yellow", 
    "orange", "pink", "purple", "grey", "brown", "maroon"
]

CLOTHING_ITEMS = [
    "shirt", "t-shirt", "kurta", "saree", "pant", "jeans",
    "dress", "jacket", "sweater", "dhoti", "skirt", "tracksuit"
]

RELATION_TYPES = [
    "Child / Son",
    "Child / Daughter",
    "Parent / Father",
    "Parent / Mother",
    "Sibling / Brother",
    "Sibling / Sister",
    "Spouse / Husband",
    "Spouse / Wife",
    "Grandparent",
    "Extended Family",
    "Guardian / Caretaker"
]

CARDINAL_DIRECTIONS = [
    "North",
    "Northeast",
    "East",
    "Southeast",
    "South",
    "Southwest",
    "West",
    "Northwest",
    "Towards Relief Camp Alpha",
    "Towards Central Hospital",
    "Towards River Crossing Bridge",
    "Towards Highway Shelter 4",
    "Towards Community Stadium",
    "Stationary / Unmoved"
]

# Clinical Reference Ranges for Swab-based Hematology Parameters
SWAB_REFERENCE_RANGES = {
    "WBC": {"min": 4.0, "max": 11.0, "unit": "10^3/µL", "label": "White Blood Cells"},
    "RBC": {"min": 4.2, "max": 5.8, "unit": "10^6/µL", "label": "Red Blood Cells"},
    "HGB": {"min": 12.0, "max": 17.5, "unit": "g/dL", "label": "Hemoglobin"},
    "PLT": {"min": 150, "max": 450, "unit": "10^3/µL", "label": "Platelets"}
}

# Color-based Decisions
DECISION_GREEN = "GREEN"
DECISION_YELLOW = "YELLOW"
DECISION_RED = "RED"

DECISION_LABELS = {
    DECISION_GREEN: "🟢 GREEN — Strong Supporting Match",
    DECISION_YELLOW: "🟡 YELLOW — Uncertain / Needs Review",
    DECISION_RED: "🔴 RED — Conflict / Weak Match"
}

# Verification Stages
STAGE_REGISTERED = "REGISTERED"
STAGE_AI_MATCHED = "AI_MATCHED"
STAGE_TIMELINE_VERIFIED = "TIMELINE_VERIFIED"
STAGE_LAB_VERIFIED = "LAB_VERIFIED"
STAGE_OFFICER_REVIEW = "OFFICER_REVIEW"
STAGE_AUTHORIZED = "AUTHORIZED_FOR_REUNIFICATION"
STAGE_REUNITED = "REUNITED"

