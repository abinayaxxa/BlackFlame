-- =========================================================================
-- Black Flame - AI-Powered Family Reunification PostgreSQL (Supabase) Schema
-- =========================================================================

-- 1. Cases Table: Stores both missing reports and unidentified found individuals
CREATE TABLE IF NOT EXISTS bf_cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_code VARCHAR(32) UNIQUE NOT NULL,      -- e.g. BF-MISSING-8201 or BF-UNID-4412
    case_type VARCHAR(20) NOT NULL,             -- 'MISSING' or 'UNIDENTIFIED'
    
    -- Demographics & Non-Name Attributes
    age NUMERIC(5, 1),                          -- Exact or estimated age
    age_min NUMERIC(5, 1),                      -- Approximate lower bound
    age_max NUMERIC(5, 1),                      -- Approximate upper bound
    gender VARCHAR(10) NOT NULL,                -- 'M', 'F', 'OTHER', 'UNKNOWN'
    origin_area VARCHAR(120),                   -- Village, city, or district
    
    -- Physical Characteristics
    height_cm NUMERIC(5, 1),
    blood_group VARCHAR(5),                     -- A+, B+, O+, AB+, etc.
    marks JSONB DEFAULT '[]'::jsonb,            -- Scars, moles, birthmarks array
    clothing_description TEXT,                  -- Color, type, fabric
    physical_notes TEXT,
    condition VARCHAR(30) DEFAULT 'STABLE',     -- 'CONSCIOUS', 'INJURED', 'MEMORY_LOSS', etc.
    
    -- Privacy Protected Fields (Masked until officer verification)
    declared_name VARCHAR(120),                 -- Protected PII
    contact_phone VARCHAR(40),                  -- Protected PII
    contact_email VARCHAR(120),                 -- Protected PII
    reporter_relationship VARCHAR(50),          -- Father, Mother, Sibling, Responder
    
    -- Status & Sync
    status VARCHAR(40) DEFAULT 'ACTIVE',        -- 'ACTIVE', 'INVESTIGATING', 'VERIFIED', 'REUNITED'
    sync_status VARCHAR(20) DEFAULT 'SYNCED',   -- 'PENDING_SYNC', 'SYNCED'
    offline_created BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Sightings & Timeline Table: Who + Where + When + Direction
CREATE TABLE IF NOT EXISTS bf_sightings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID REFERENCES bf_cases(id) ON DELETE CASCADE,
    location_name VARCHAR(150) NOT NULL,        -- Sighting landmark or area
    latitude NUMERIC(10, 6),
    longitude NUMERIC(10, 6),
    event_timestamp TIMESTAMPTZ NOT NULL,       -- When sighting occurred
    direction_of_movement VARCHAR(80),          -- Direction vector: 'North', 'Towards Relief Camp Alpha'
    observed_by_role VARCHAR(50),               -- 'CAMP_VOLUNTEER', 'CIVILIAN', 'HOSPITAL_STAFF'
    observer_notes TEXT,
    confidence_level VARCHAR(20) DEFAULT 'HIGH',
    sync_status VARCHAR(20) DEFAULT 'SYNCED',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Known Family Relations Table: Relatives declared for multi-factor link matching
CREATE TABLE IF NOT EXISTS bf_family_relations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID REFERENCES bf_cases(id) ON DELETE CASCADE,
    relative_relation VARCHAR(50) NOT NULL,     -- 'Father', 'Mother', 'Son', 'Daughter', etc.
    relative_name VARCHAR(120),                 -- Protected name
    relative_village VARCHAR(120),
    contact_detail VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Voice Identification Records Table
CREATE TABLE IF NOT EXISTS bf_voice_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID REFERENCES bf_cases(id) ON DELETE CASCADE,
    sample_id VARCHAR(50) UNIQUE NOT NULL,
    f0_hz NUMERIC(8, 2),                        -- Fundamental pitch
    spectral_centroid NUMERIC(8, 2),            -- Timbre / resonance
    f1_f2_ratio NUMERIC(6, 3),                  -- Formant ratio proxy
    harmonicity_db NUMERIC(6, 2),               -- Harmonics-to-noise ratio
    duration_seconds NUMERIC(5, 2),
    consent_given BOOLEAN DEFAULT TRUE,
    authorized_by VARCHAR(100),
    sample_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Authorized Swab Biological & Hematology Records Table
CREATE TABLE IF NOT EXISTS bf_biological_swabs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID REFERENCES bf_cases(id) ON DELETE CASCADE,
    sample_code VARCHAR(50) UNIQUE NOT NULL,    -- Lab barcode
    blood_group VARCHAR(5) NOT NULL,            -- A+, O+, etc.
    wbc_count NUMERIC(6, 2),                    -- White Blood Cells (10^3/uL)
    rbc_count NUMERIC(6, 2),                    -- Red Blood Cells (10^6/uL)
    hgb_level NUMERIC(5, 2),                    -- Hemoglobin (g/dL)
    plt_count NUMERIC(6, 1),                    -- Platelets (10^3/uL)
    lab_facility VARCHAR(120),
    certifying_technician VARCHAR(100),
    is_authorized BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Match Evaluations Table: Multi-Factor Decision (GREEN / YELLOW / RED)
CREATE TABLE IF NOT EXISTS bf_matches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    missing_case_id UUID REFERENCES bf_cases(id) ON DELETE CASCADE,
    unidentified_case_id UUID REFERENCES bf_cases(id) ON DELETE CASCADE,
    decision_level VARCHAR(10) NOT NULL,        -- 'GREEN', 'YELLOW', 'RED'
    numerical_score NUMERIC(5, 3) NOT NULL,     -- Overall score (supporting only)
    has_critical_conflict BOOLEAN DEFAULT FALSE,
    supporting_factors JSONB DEFAULT '[]'::jsonb,
    conflicting_factors JSONB DEFAULT '[]'::jsonb,
    pending_factors JSONB DEFAULT '[]'::jsonb,
    evaluation_breakdown JSONB DEFAULT '{}'::jsonb,
    status VARCHAR(30) DEFAULT 'PROPOSED',      -- 'PROPOSED', 'INVESTIGATING', 'VERIFIED', 'REJECTED'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_case_pair UNIQUE (missing_case_id, unidentified_case_id)
);

-- 7. Human Verification & Reunification Audits Table
CREATE TABLE IF NOT EXISTS bf_verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id UUID REFERENCES bf_matches(id) ON DELETE CASCADE,
    stage VARCHAR(50) NOT NULL,                 -- 'OFFICER_REVIEW', 'FAMILY_CONFIRMED', 'REUNITED'
    verified_by_officer VARCHAR(120) NOT NULL,
    officer_badge_id VARCHAR(50) NOT NULL,
    verification_notes TEXT NOT NULL,
    photo_verified BOOLEAN DEFAULT FALSE,
    swab_confirmed BOOLEAN DEFAULT FALSE,
    voice_confirmed BOOLEAN DEFAULT FALSE,
    reunification_certificate_code VARCHAR(40),
    action_timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 8. Audit Log for Sensitive Privacy Actions
CREATE TABLE IF NOT EXISTS bf_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id VARCHAR(100) NOT NULL,
    action_type VARCHAR(60) NOT NULL,           -- 'CASE_REGISTERED', 'MATCH_EVALUATED', 'PII_ACCESSED', 'REUNIFICATION_APPROVED'
    target_case_code VARCHAR(40),
    details JSONB DEFAULT '{}'::jsonb,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for attribute queries without searching by name
CREATE INDEX IF NOT EXISTS idx_cases_age ON bf_cases(age);
CREATE INDEX IF NOT EXISTS idx_cases_gender ON bf_cases(gender);
CREATE INDEX IF NOT EXISTS idx_cases_origin ON bf_cases(origin_area);
CREATE INDEX IF NOT EXISTS idx_cases_blood ON bf_cases(blood_group);
CREATE INDEX IF NOT EXISTS idx_sightings_time ON bf_sightings(event_timestamp);
CREATE INDEX IF NOT EXISTS idx_sightings_loc ON bf_sightings(location_name);
CREATE INDEX IF NOT EXISTS idx_matches_decision ON bf_matches(decision_level);

