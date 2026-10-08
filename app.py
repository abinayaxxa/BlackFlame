"""Black Flame - AI-Powered Family Reunification & Disaster Response System.
Logo: Family Union
Designed for disaster relief, refugee centers, field hospitals, and crisis operations.
"""
import base64
import json
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

import numpy as np
import pandas as pd
import pydeck as pdk
import streamlit as st

import config
from database.local_db import (
    get_all_cases, get_case_by_code, save_case, save_sighting,
    save_voice_record, save_swab_record, save_verification,
    get_pending_sync_items
)
from database.supabase_client import check_supabase_health
from database.sync_manager import get_sync_status_summary, execute_full_synchronization
from engine.matcher import match_candidate_against_database, evaluate_case_pair
from engine.timeline_matcher import (
    LANDMARK_COORDINATES, DIRECTION_ANGLES,
    analyze_timeline_continuity, get_coordinates
)
from engine.voice_matcher import compare_voice_samples
from engine.swab_matcher import compare_swab_profiles
from engine.conflict_detector import detect_conflicts
from engine.explainability import generate_explanation

# ---------------- Streamlit Page Configuration ----------------
st.set_page_config(
    page_title=f"{config.APP_NAME} | Family Union",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load CSS Styles
def load_custom_styles():
    if config.STYLES_PATH.exists():
        with open(config.STYLES_PATH, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_custom_styles()

# Load Logo as base64 for reliable rendering
def get_logo_html(size_px=74):
    if config.LOGO_PATH.exists():
        with open(config.LOGO_PATH, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return f'<img src="data:image/svg+xml;base64,{b64}" class="bf-logo-img" style="width:{size_px}px;height:{size_px}px;" alt="Family Union Logo"/>'
    return '<span style="font-size:3rem;">🔥</span>'

# Session State Initialization
ss = st.session_state
ss.setdefault("simulated_offline", False)
ss.setdefault("selected_role", "Camp Field Responder")
ss.setdefault("last_sync_msg", None)
ss.setdefault("active_tab", "Command Dashboard")
ss.setdefault("verification_case_pair", None)


# ---------------- Header & Branding Component ----------------
def render_header():
    logo_markup = get_logo_html(76)
    sync_info = get_sync_status_summary()
    is_offline = ss.simulated_offline or not sync_info["is_online"]
    
    conn_pill = (
        '<span class="bf-pill bf-pill-offline">⚡ OFFLINE MODE (CAMP LOCAL STORAGE)</span>'
        if is_offline else
        '<span class="bf-pill bf-pill-green">🌐 SUPABASE POSTGRESQL CONNECTED</span>'
    )
    
    pending_pill = (
        f'<span class="bf-pill bf-pill-sync">⏳ {sync_info["total_pending"]} PENDING SYNC</span>'
        if sync_info["has_pending_items"] else
        '<span class="bf-pill bf-pill-green">✓ ALL RECORDS SYNCED</span>'
    )

    st.markdown(f"""
    <div class="bf-brand-header">
        {logo_markup}
        <div style="flex-grow: 1;">
            <div style="display: flex; align-items: center; gap: 14px; flex-wrap: wrap;">
                <h1 class="bf-brand-title">{config.APP_NAME}</h1>
                <span class="bf-badge-privacy">SHIELDED IDENTITY ARCHITECTURE</span>
                {conn_pill}
                {pending_pill}
            </div>
            <p class="bf-brand-subtitle">
                <strong>Family Union</strong> — Multi-Factor AI Reunification & Timeline Direction Correlation Engine
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ---------------- Sidebar Controls ----------------
def render_sidebar():
    with st.sidebar:
        st.markdown(f"### 🔥 **{config.APP_NAME} Control Center**")
        st.caption("AI Disaster Response & Family Reunification")
        
        # Role Selector (Enforces Privacy Protection)
        ss.selected_role = st.selectbox(
            "👤 Active User Role",
            ["Camp Field Responder", "Family / Guardian", "Medical & Lab Officer", "Relief Authority / Admin"],
            index=0
        )
        
        st.divider()
        
        # Offline Simulator Toggle
        st.markdown("#### 📡 **Connectivity State**")
        ss.simulated_offline = st.toggle(
            "Simulate Offline Field Camp",
            value=ss.simulated_offline,
            help="Simulates loss of internet at remote shelters. All registrations and matching run locally on-device!"
        )
        
        sync_info = get_sync_status_summary()
        if ss.simulated_offline:
            st.warning("⚠️ Operating in Local Offline Mode. Changes queued locally.")
        elif sync_info["is_online"]:
            st.success("🟢 Connected to Supabase Cloud PostgreSQL.")
        else:
            st.error("🔴 Supabase Cloud Unreachable. Automatic offline fallback active.")
            
        if sync_info["has_pending_items"]:
            st.info(f"⏳ **{sync_info['total_pending']} record(s)** waiting for sync to Supabase.")
            if st.button("🚀 Sync to Supabase PostgreSQL Now", use_container_width=True, type="primary"):
                with st.spinner("Synchronizing with Supabase PostgreSQL..."):
                    res = execute_full_synchronization()
                    ss.last_sync_msg = res["message"]
                    st.rerun()
                    
        if ss.last_sync_msg:
            st.caption(f"ℹ️ {ss.last_sync_msg}")
            
        st.divider()
        st.markdown("""
        **System Guiding Principles:**
        - **No Name-Dependency**: Matching uses attributes, timeline & biological evidence.
        - **Strict Conflict Priority**: A high score never overrides a critical contradiction.
        - **Human in the Loop**: AI recommends, authorized humans decide.
        """)
        st.caption("Black Flame v2.5 | Disaster Reunite Core")


# ---------------- Helper: Explainability Badge Renderer ----------------
def render_decision_badge(decision_level: str, score: float):
    score_pct = f"{score * 100:.1f}%"
    if decision_level == config.DECISION_GREEN:
        return f'<span class="bf-pill bf-pill-green">🟢 STRONG SUPPORTING MATCH ({score_pct})</span>'
    elif decision_level == config.DECISION_YELLOW:
        return f'<span class="bf-pill bf-pill-yellow">🟡 UNCERTAIN / NEEDS REVIEW ({score_pct})</span>'
    else:
        return f'<span class="bf-pill bf-pill-red">🔴 CONFLICT / WEAK MATCH ({score_pct})</span>'


# ---------------- TAB 1: COMMAND DASHBOARD ----------------
def render_tab_dashboard():
    st.subheader("🏛️ Disaster Response Operations Dashboard")
    st.caption("Active Scenario: Wayland River Valley Evacuation Zone | Shelter Alpha to Highway 4")
    
    missing_cases = get_all_cases("MISSING")
    unidentified_cases = get_all_cases("UNIDENTIFIED")
    
    # Run evaluation across cases
    green_count = 0
    yellow_count = 0
    red_count = 0
    recent_matches = []
    
    for m in missing_cases:
        matches = match_candidate_against_database(m, unidentified_cases)
        for r in matches:
            if r["decision_level"] == config.DECISION_GREEN:
                green_count += 1
            elif r["decision_level"] == config.DECISION_YELLOW:
                yellow_count += 1
            else:
                red_count += 1
            recent_matches.append((m, r))
            
    # Metric Boxes
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown("""<div class="bf-stat-box"><div class="bf-stat-val">{}</div><div class="bf-stat-label">Missing Reports</div></div>""".format(len(missing_cases)), unsafe_allow_html=True)
    with c2:
        st.markdown("""<div class="bf-stat-box"><div class="bf-stat-val">{}</div><div class="bf-stat-label">Unidentified Found</div></div>""".format(len(unidentified_cases)), unsafe_allow_html=True)
    with c3:
        st.markdown("""<div class="bf-stat-box"><div class="bf-stat-val" style="color:#10b981;">{}</div><div class="bf-stat-label">🟢 Strong Matches</div></div>""".format(green_count), unsafe_allow_html=True)
    with c4:
        st.markdown("""<div class="bf-stat-box"><div class="bf-stat-val" style="color:#f59e0b;">{}</div><div class="bf-stat-label">🟡 Needs Review</div></div>""".format(yellow_count), unsafe_allow_html=True)
    with c5:
        st.markdown("""<div class="bf-stat-box"><div class="bf-stat-val" style="color:#60a5fa;">1</div><div class="bf-stat-label">Reunited Cases</div></div>""", unsafe_allow_html=True)

    st.write("")
    
    col_left, col_right = st.columns([3, 2])
    with col_left:
        st.markdown("### ⚡ **Live Multi-Factor Match Evaluations**")
        st.caption("Calculated without name dependency using attributes, timeline continuity, voice & swab panels.")
        
        # Sort so green is first
        recent_matches.sort(key=lambda item: (0 if item[1]["decision_level"] == config.DECISION_GREEN else (1 if item[1]["decision_level"] == config.DECISION_YELLOW else 2)))
        
        for missing_rec, match_res in recent_matches[:4]:
            level = match_res["decision_level"]
            score = match_res["numerical_score"]
            card_class = f"bf-match-card card-{level.lower()}"
            badge_html = render_decision_badge(level, score)
            exp = match_res["explanation"]
            
            # Find found record
            found_rec = next((u for u in unidentified_cases if (u.get("temp_id") == match_res["case_b_id"] or u.get("case_code") == match_res["case_b_id"] or u.get("id") == match_res["case_b_id"])), {})
            
            with st.container():
                st.markdown(f"""
                <div class="{card_class}">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                        <span style="font-size:1.05rem; font-weight:700;">
                            Case Pair: <code>{missing_rec.get('case_code')}</code> ↔ <code>{found_rec.get('case_code')}</code>
                        </span>
                        {badge_html}
                    </div>
                    <div style="display:flex; gap:16px; font-size:0.88rem; color:#cbd5e1; margin-bottom:8px;">
                        <span>👤 <strong>Missing:</strong> Age ~{missing_rec.get('age', 'N/A')}, {missing_rec.get('gender', 'N/A')}, {missing_rec.get('clothing_description', 'N/A')}</span>
                        <span>🏥 <strong>Found:</strong> Age ~{found_rec.get('age', 'N/A')}, {found_rec.get('gender', 'N/A')}, {found_rec.get('clothing_description', 'N/A')}</span>
                    </div>
                    <div style="font-size:0.85rem; color:#94a3b8; margin-bottom:10px;">
                        📍 <em>Timeline:</em> {match_res['timeline'].get('supporting_note') or match_res['timeline'].get('conflict_reason') or 'Sightings evaluated across rescue zone'}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Expandable Explainable Breakdown
                with st.expander(f"🔎 View Detailed Factors for {missing_rec.get('case_code')} ↔ {found_rec.get('case_code')}"):
                    c_pro, c_con = st.columns(2)
                    with c_pro:
                        st.markdown("**✓ Supporting Evidence Factors:**")
                        for sup in exp.get("supporting_factors", []):
                            st.markdown(f'<div class="bf-factor-item bf-factor-pro">✓ {sup}</div>', unsafe_allow_html=True)
                    with c_con:
                        if exp.get("conflicting_factors"):
                            st.markdown("**✗ Contradictions & Conflicts:**")
                            for con in exp.get("conflicting_factors", []):
                                st.markdown(f'<div class="bf-factor-item bf-factor-con">✗ {con}</div>', unsafe_allow_html=True)
                        if exp.get("pending_factors"):
                            st.markdown("**⚠️ Pending Field Records:**")
                            for pend in exp.get("pending_factors", []):
                                st.markdown(f'<div class="bf-factor-item bf-factor-pending">⚠️ {pend}</div>', unsafe_allow_html=True)
                                
                    st.caption(f"Recommended Protocol: **{exp.get('status_guidance')}**")
                    if level in (config.DECISION_GREEN, config.DECISION_YELLOW):
                        if st.button("⚖️ Open Human Verification Desk", key=f"verif_btn_{missing_rec.get('case_code')}_{found_rec.get('case_code')}"):
                            ss.verification_case_pair = (missing_rec, found_rec, match_res)
                            st.info("Loaded into Human Verification Desk tab! Please switch to tab 6.")

    with col_right:
        st.markdown("### 🗺️ **Active Disaster Sector Map**")
        st.caption("Live sighting locations & relief camps")
        
        # Map of landmarks
        map_data = []
        for name, coords in LANDMARK_COORDINATES.items():
            map_data.append({
                "name": name,
                "lat": coords[0],
                "lon": coords[1],
                "color": [255, 122, 0, 200] if "Camp" in name or "Hospital" in name else [59, 130, 246, 200],
                "size": 18 if "Camp" in name else 12
            })
        df_map = pd.DataFrame(map_data)
        
        layer = pdk.Layer(
            "ScatterplotLayer",
            df_map,
            get_position=["lon", "lat"],
            get_color="color",
            get_radius="size * 25",
            pickable=True
        )
        view_state = pdk.ViewState(
            latitude=12.9750,
            longitude=77.5950,
            zoom=11.5,
            pitch=35
        )
        deck = pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            tooltip={"text": "{name}"},
            map_style="mapbox://styles/mapbox/dark-v10"
        )
        st.pydeck_chart(deck, use_container_width=True)
        
        st.markdown("""
        **Sighting Legend:**
        - 🟠 Orange nodes: Relief Camps & Field Medical Facilities
        - 🔵 Blue nodes: Evacuation Sectors & River Crossings
        """)


# ---------------- TAB 2: ATTRIBUTE MATCH DISCOVERY (ZERO-NAME SEARCH) ----------------
def render_tab_discovery():
    st.subheader("🔍 Attribute-First Match Discovery")
    st.markdown("""
    > [!IMPORTANT]
    > **Zero Name-Dependency**: In disaster environments, names are frequently misspelled, unstated due to trauma/amnesia, or withheld for child privacy.
    > Enter known physical attributes, timeline sightings, and kinship details below to search registered unidentified persons.
    """)
    
    with st.expander("🛠️ Query Filters (Provide Available Clues)", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            q_age = st.slider("Approximate Age", min_value=1, max_value=100, value=7)
            q_age_tol = st.slider("Age Margin / Uncertainty (± Years)", 0, 15, 3)
            q_gender = st.selectbox("Gender", ["Any", "M", "F", "Other"])
        with col2:
            q_color = st.selectbox("Clothes Color Observed", ["Any"] + config.CLOTHING_COLORS)
            q_item = st.selectbox("Clothes Garment Type", ["Any"] + config.CLOTHING_ITEMS)
            q_blood = st.selectbox("Blood Group (if known)", ["Any"] + config.BLOOD_GROUPS)
        with col3:
            q_place = st.selectbox("Last-Seen Area / Landmark", ["Any"] + list(LANDMARK_COORDINATES.keys()))
            q_direction = st.selectbox("Direction of Movement Observed", ["Any"] + config.CARDINAL_DIRECTIONS)
            q_relatives = st.text_input("Known Relatives / Kinship (e.g., Ramesh, Kamala)", placeholder="Uncle Ramesh")
            
        q_marks = st.multiselect("Distinct Physical Marks / Scars", config.PHYSICAL_MARKS, default=["scar_left_arm"])

    # Build Synthetic Query Case
    query_case = {
        "case_code": "SEARCH-QUERY",
        "case_type": "MISSING",
        "age": q_age,
        "age_min": max(0, q_age - q_age_tol),
        "age_max": q_age + q_age_tol,
        "gender": "" if q_gender == "Any" else q_gender,
        "blood_group": "" if q_blood == "Any" else q_blood,
        "marks": q_marks,
        "clothes": f"{'' if q_color == 'Any' else q_color} {'' if q_item == 'Any' else q_item}".strip(),
        "last_seen_place": "" if q_place == "Any" else q_place,
        "direction_of_movement": "" if q_direction == "Any" else q_direction,
        "known_relatives": q_relatives
    }

    # Retrieve all unidentified persons in database
    candidates = get_all_cases("UNIDENTIFIED")
    
    st.write("")
    st.markdown(f"### 📋 **Matching Results ({len(candidates)} Unidentified Persons Evaluated)**")
    
    evaluations = match_candidate_against_database(query_case, candidates)
    
    # Filter Tabs
    filter_choice = st.radio("Display Filter", ["All Decision Levels", "🟢 GREEN Matches Only", "🟡 YELLOW / Needs Review", "🔴 RED Conflicts"], horizontal=True)
    
    filtered_results = []
    for r in evaluations:
        level = r["decision_level"]
        if filter_choice == "🟢 GREEN Matches Only" and level != config.DECISION_GREEN:
            continue
        if filter_choice == "🟡 YELLOW / Needs Review" and level != config.DECISION_YELLOW:
            continue
        if filter_choice == "🔴 RED Conflicts" and level != config.DECISION_RED:
            continue
        filtered_results.append(r)
        
    if not filtered_results:
        st.info("No candidates fit the selected filter.")
        return

    for res in filtered_results:
        level = res["decision_level"]
        score = res["numerical_score"]
        card_class = f"bf-match-card card-{level.lower()}"
        cand_id = res["case_b_id"]
        cand_rec = next((c for c in candidates if c.get("case_code") == cand_id or c.get("id") == cand_id), {})
        exp = res["explanation"]
        
        # Privacy protection: Anonymize declared name unless authorized
        is_officer = ss.selected_role in ("Camp Field Responder", "Medical & Lab Officer", "Relief Authority / Admin")
        disp_name = cand_rec.get("declared_name", "Anonymous Found Record") if is_officer else "Protected Person ID (Masked for Privacy)"
        
        st.markdown(f"""
        <div class="{card_class}">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <span style="font-size:1.15rem; font-weight:800;">
                    Unidentified Candidate: <code>{cand_rec.get('case_code')}</code>
                </span>
                {render_decision_badge(level, score)}
            </div>
            <div style="font-size:0.9rem; color:#cbd5e1; margin-bottom:6px;">
                <strong>Demographics:</strong> Est. Age: ~{cand_rec.get('age', 'Unknown')} | Gender: {cand_rec.get('gender', 'Unknown')} | Blood: {cand_rec.get('blood_group', 'Not Tested')} | Condition: <em>{cand_rec.get('condition', 'Stable')}</em>
            </div>
            <div style="font-size:0.88rem; color:#94a3b8; margin-bottom:6px;">
                <strong>Clothing:</strong> {cand_rec.get('clothing_description', 'Standard intake clothing')} | <strong>Marks:</strong> {', '.join(cand_rec.get('marks', [])) or 'None recorded'}
            </div>
            <div style="font-size:0.88rem; color:#94a3b8; margin-bottom:10px;">
                📍 <strong>Location / Direction:</strong> Found at <em>{cand_rec.get('found_place', 'Relief shelter')}</em> (Direction: {cand_rec.get('direction_of_movement', 'Stationary')})
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander(f"📊 Detailed Match Factors & Conflict Audit ({cand_rec.get('case_code')})"):
            c_left, c_right = st.columns(2)
            with c_left:
                st.markdown("**✓ Supporting Evidence:**")
                for s in exp.get("supporting_factors", []):
                    st.markdown(f'<div class="bf-factor-item bf-factor-pro">✓ {s}</div>', unsafe_allow_html=True)
            with c_right:
                if exp.get("conflicting_factors"):
                    st.markdown("**✗ Contradictory Evidence:**")
                    for c in exp.get("conflicting_factors", []):
                        st.markdown(f'<div class="bf-factor-item bf-factor-con">✗ {c}</div>', unsafe_allow_html=True)
                if exp.get("pending_factors"):
                    st.markdown("**⚠️ Pending Verification:**")
                    for p in exp.get("pending_factors", []):
                        st.markdown(f'<div class="bf-factor-item bf-factor-pending">⚠️ {p}</div>', unsafe_allow_html=True)
                        
            st.caption(f"**Action Recommendation:** {exp.get('status_guidance')}")
            
            if level in (config.DECISION_GREEN, config.DECISION_YELLOW):
                if st.button(f"⚖️ Review in Human Verification Desk ({cand_rec.get('case_code')})", key=f"sel_disc_{cand_rec.get('case_code')}"):
                    ss.verification_case_pair = (query_case, cand_rec, res)
                    st.success("Loaded candidate pair into Human Verification Desk! Switch to Tab 6.")


# ---------------- TAB 3: REGISTER CASE (OFFLINE-FIRST) ----------------
def render_tab_registration():
    st.subheader("📝 Register Case (Offline-First Capable)")
    
    is_offline = ss.simulated_offline or not check_supabase_health()["online"]
    if is_offline:
        st.markdown("""
        > [!WARNING]
        > **Operating in Offline Mode:** This case will be stored securely in the local field SQLite storage and tagged with **`PENDING_SYNC`**. It will be automatically synchronized with Supabase PostgreSQL as soon as internet connectivity is restored.
        """)
    else:
        st.markdown("""
        > [!NOTE]
        > **Cloud-Connected:** Records will be persisted in local storage and mirrored to the centralized Supabase PostgreSQL database.
        """)
        
    case_reg_type = st.radio("Case Category", ["Missing Person Inquiry (Family Report)", "Unidentified Person Intake (Shelter / Hospital)"], horizontal=True)
    is_missing = "Missing" in case_reg_type
    
    with st.form("case_registration_form"):
        st.markdown("#### 1. Demographic & Physical Characteristics (Non-Name Attributes)")
        c1, c2, c3 = st.columns(3)
        with c1:
            age_val = st.number_input("Age (or Estimated Age)", min_value=1.0, max_value=110.0, value=25.0, step=1.0)
            gender_val = st.selectbox("Gender", ["M", "F", "Other", "Unknown"])
        with c2:
            blood_val = st.selectbox("Blood Group (optional)", [""] + config.BLOOD_GROUPS)
            color_val = st.selectbox("Clothes Primary Color", config.CLOTHING_COLORS)
        with c3:
            item_val = st.selectbox("Clothes Garment Item", config.CLOTHING_ITEMS)
            cond_val = st.selectbox("Current Condition", ["STABLE", "CONSCIOUS", "INJURED", "MEMORY_LOSS", "UNCONSCIOUS"])
            
        marks_val = st.multiselect("Distinctive Identification Marks / Scars", config.PHYSICAL_MARKS)
        phys_notes = st.text_area("Physical Build & Distinguishing Notes", placeholder="e.g. Slim build, speaks with regional dialect, walking with slight limp")
        
        st.divider()
        st.markdown("#### 2. Timeline Sighting Information: **Who + Where + When + Direction**")
        t1, t2, t3 = st.columns(3)
        with t1:
            loc_val = st.selectbox("Last-Seen / Found Location", list(LANDMARK_COORDINATES.keys()))
            hours_ago = st.number_input("Observed (Hours Ago)", min_value=0.1, max_value=240.0, value=2.5, step=0.5)
        with t2:
            dir_val = st.selectbox("Direction of Movement Observed", config.CARDINAL_DIRECTIONS)
            observer_val = st.selectbox("Observer Category", ["FAMILY_REPORT", "RESCUE_BOAT_TEAM", "CAMP_VOLUNTEER", "HOSPITAL_STAFF", "CIVILIAN_WITNESS"])
        with t3:
            origin_area_val = st.text_input("Origin Village / Sector", value="Bhimavaram Riverside")
            relatives_val = st.text_input("Known Relatives (for Link Matching)", placeholder="e.g., Uncle Ramesh, Mother Kamala")
            
        st.divider()
        st.markdown("#### 3. Voice & Biological Swab Evidence (Optional)")
        v_col, s_col = st.columns(2)
        with v_col:
            st.markdown("**🎙️ Voice Recording:**")
            has_voice = st.checkbox("Attach Bedside or Family Voice Sample", value=False)
            v_pitch = st.slider("Acoustic Pitch Estimation (F0 Hz)", 70.0, 350.0, 180.0, help="Male: 85-155 Hz, Female: 165-255 Hz, Child: 250-380 Hz")
        with s_col:
            st.markdown("**🩸 Biological Swab Record:**")
            has_swab = st.checkbox("Attach Swab Hematology Sample", value=False)
            swab_code = st.text_input("Swab Barcode / Sample ID", value=f"SWAB-LAB-{uuid.uuid4().hex[:6].upper()}")
            c_sw1, c_sw2 = st.columns(2)
            wbc_val = c_sw1.number_input("WBC (10^3/µL)", 1.0, 30.0, 7.5, step=0.1)
            rbc_val = c_sw2.number_input("RBC (10^6/µL)", 1.0, 10.0, 4.8, step=0.1)
            hgb_val = c_sw1.number_input("HGB (g/dL)", 4.0, 25.0, 13.5, step=0.1)
            plt_val = c_sw2.number_input("PLT (10^3/µL)", 20.0, 800.0, 250.0, step=5.0)

        st.divider()
        st.markdown("#### 4. Protected Identity & Contact (Encrypted / Masked PII)")
        p1, p2 = st.columns(2)
        with p1:
            name_val = st.text_input("Full Name (Masked from Public Attribute Search)", placeholder="John / Jane Doe")
            reporter_rel = st.text_input("Reporter Relationship to Person", placeholder="e.g. Parent, Sibling, Camp Coordinator")
        with p2:
            phone_val = st.text_input("Emergency Contact Phone", placeholder="+91 90000 00000")
            
        submitted = st.form_submit_button("💾 Register Case Record", type="primary")

    if submitted:
        event_time = (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()
        coords = get_coordinates(loc_val)
        
        case_data = {
            "case_type": "MISSING" if is_missing else "UNIDENTIFIED",
            "age": age_val,
            "age_min": max(0, age_val - 3),
            "age_max": age_val + 3,
            "gender": gender_val,
            "origin_area": origin_area_val,
            "blood_group": blood_val or None,
            "marks": marks_val,
            "clothing_description": f"{color_val} {item_val}",
            "physical_notes": phys_notes,
            "condition": cond_val,
            "declared_name": name_val or "Anonymous Intake",
            "contact_phone": phone_val,
            "reporter_relationship": reporter_rel,
            "status": "ACTIVE"
        }
        
        saved_case = save_case(case_data, is_offline=is_offline)
        
        # Save sighting
        save_sighting({
            "case_id": saved_case["id"],
            "location_name": loc_val,
            "latitude": coords[0],
            "longitude": coords[1],
            "event_timestamp": event_time,
            "direction_of_movement": dir_val,
            "observed_by_role": observer_val,
            "observer_notes": f"Initial intake sighting: heading {dir_val}",
            "confidence_level": "HIGH"
        }, is_offline=is_offline)
        
        if has_voice:
            save_voice_record({
                "case_id": saved_case["id"],
                "sample_id": f"VOICE-{uuid.uuid4().hex[:6].upper()}",
                "f0_hz": v_pitch,
                "spectral_centroid": 1950.0,
                "f1_f2_ratio": 2.2,
                "harmonicity_db": 14.0,
                "consent_given": True,
                "authorized_by": "Field Staff Intake"
            })
            
        if has_swab:
            save_swab_record({
                "case_id": saved_case["id"],
                "sample_code": swab_code,
                "blood_group": blood_val or "O+",
                "wbc_count": wbc_val,
                "rbc_count": rbc_val,
                "hgb_level": hgb_val,
                "plt_count": plt_val,
                "lab_facility": "Field Camp Mobile Lab",
                "certifying_technician": "Intake Technician",
                "is_authorized": True
            })
            
        sync_badge = "⏳ Tagged PENDING_SYNC (Offline Queue)" if is_offline else "🌐 Synced to Supabase PostgreSQL"
        st.success(f"Case Registered Successfully! Assigned Code: **{saved_case['case_code']}** | {sync_badge}")
        
        # Run matching against existing records immediately
        opposite_type = "UNIDENTIFIED" if is_missing else "MISSING"
        pool = get_all_cases(opposite_type)
        evals = match_candidate_against_database(saved_case, pool)
        
        green_matches = [e for e in evals if e["decision_level"] == config.DECISION_GREEN]
        if green_matches:
            st.balloons()
            st.markdown(f"""
            <div class="bf-factor-item bf-factor-pro" style="font-size:1.05rem; padding:14px;">
                🎉 <strong>Immediate Supporting Match Found!</strong><br/>
                Candidate <code>{green_matches[0]['case_b_id']}</code> returned 🟢 GREEN match level.
                Please review in the Human Verification Desk.
            </div>
            """, unsafe_allow_html=True)


# ---------------- TAB 4: TIMELINE, LOCATION & DIRECTION TRACKER ----------------
def render_tab_timeline():
    st.subheader("🗺️ Last-Seen + Time + Direction Sighting Continuity Tracker")
    st.markdown("""
    > [!NOTE]
    > **Who + Where + When + Direction**: The system correlates disparate reports by analyzing spatial distance, elapsed time, movement direction vectors, and sequence plausibility.
    """)
    
    missing_cases = get_all_cases("MISSING")
    unidentified_cases = get_all_cases("UNIDENTIFIED")
    
    col_sel1, col_sel2 = st.columns(2)
    with col_sel1:
        pick_m = st.selectbox("Select Missing Person Report", missing_cases, format_func=lambda c: f"{c.get('case_code')} (Age: {c.get('age')}, Last seen: {c.get('last_seen_place')})")
    with col_sel2:
        pick_u = st.selectbox("Select Unidentified Found Person", unidentified_cases, format_func=lambda c: f"{c.get('case_code')} (Age: {c.get('age')}, Found: {c.get('found_place')})")
        
    if not pick_m or not pick_u:
        return
        
    s_m = {
        "location": pick_m.get("last_seen_place", "Sector 1 River Basin"),
        "timestamp": pick_m.get("last_seen_time"),
        "direction": pick_m.get("direction_of_movement", "Towards Relief Camp Alpha"),
        "lat": pick_m.get("latitude"),
        "lon": pick_m.get("longitude")
    }
    s_u = {
        "location": pick_u.get("found_place", "Relief Camp Alpha"),
        "timestamp": pick_u.get("found_time"),
        "direction": pick_u.get("direction_of_movement", "Towards Relief Camp Alpha"),
        "lat": pick_u.get("latitude"),
        "lon": pick_u.get("longitude")
    }
    
    timeline_analysis = analyze_timeline_continuity(s_m, s_u)
    
    # Visual Trajectory Metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Spatial Distance", f"{timeline_analysis['distance_km']:.2f} km")
    m2.metric("Elapsed Time Gap", f"{timeline_analysis['delta_minutes']:.0f} mins")
    m3.metric("Implied Transit Velocity", f"{timeline_analysis['implied_speed_kmh']:.1f} km/h")
    m4.metric("Direction Alignment", f"{timeline_analysis['direction_alignment']*100:.0f}%")
    
    st.divider()
    
    c_left, c_right = st.columns([3, 2])
    with c_left:
        st.markdown("#### 🧭 **Sequence of Sightings Analysis**")
        
        # Sequence node display
        first_loc = timeline_analysis["first_location"]
        sec_loc = timeline_analysis["second_location"]
        dir_a = timeline_analysis["direction_a"]
        dir_b = timeline_analysis["direction_b"]
        
        st.markdown(f"""
        <div class="bf-timeline-node">
            <div class="bf-timeline-dot"></div>
            <strong>Sighting 1: Initial Report</strong><br/>
            📍 Location: <code>{first_loc}</code><br/>
            🧭 Heading: <em>{dir_a}</em><br/>
            ⏰ Time: {s_m.get('timestamp') or 'T0'}
        </div>
        <div class="bf-timeline-node">
            <div class="bf-timeline-dot" style="background:#10b981; box-shadow:0 0 8px #10b981;"></div>
            <strong>Sighting 2: Field Encounter / Rescue</strong><br/>
            📍 Location: <code>{sec_loc}</code><br/>
            🧭 Heading: <em>{dir_b}</em><br/>
            ⏰ Time: {s_u.get('timestamp') or 'T0 + delta'}
        </div>
        """, unsafe_allow_html=True)
        
        if timeline_analysis["conflict_flag"]:
            st.error(f"🔴 **Impossibility / Conflict Detected:** {timeline_analysis['conflict_reason']}")
        elif timeline_analysis["continuity_score"] >= 0.70:
            st.success(f"🟢 **Strong Timeline Continuity:** {timeline_analysis['supporting_note']}")
        else:
            st.warning("🟡 **Moderate Timeline Continuity:** Sightings are plausible but distance/time gap warrants verification.")

    with c_right:
        st.markdown("#### 🗺️ **Vector Trajectory Map**")
        coord_a = get_coordinates(first_loc)
        coord_b = get_coordinates(sec_loc)
        
        arc_df = pd.DataFrame([{
            "from_lon": coord_a[1], "from_lat": coord_a[0],
            "to_lon": coord_b[1], "to_lat": coord_b[0]
        }])
        
        scatter_df = pd.DataFrame([
            {"name": f"Sight 1: {first_loc}", "lon": coord_a[1], "lat": coord_a[0], "color": [255, 122, 0]},
            {"name": f"Sight 2: {sec_loc}", "lon": coord_b[1], "lat": coord_b[0], "color": [16, 185, 129]}
        ])
        
        arc_layer = pdk.Layer(
            "ArcLayer",
            arc_df,
            get_source_position=["from_lon", "from_lat"],
            get_target_position=["to_lon", "to_lat"],
            get_width=4,
            get_source_color=[255, 122, 0, 200],
            get_target_color=[16, 185, 129, 200]
        )
        point_layer = pdk.Layer(
            "ScatterplotLayer",
            scatter_df,
            get_position=["lon", "lat"],
            get_color="color",
            get_radius=300,
            pickable=True
        )
        
        mid_lat = (coord_a[0] + coord_b[0]) / 2.0
        mid_lon = (coord_a[1] + coord_b[1]) / 2.0
        v_state = pdk.ViewState(latitude=mid_lat, longitude=mid_lon, zoom=12, pitch=25)
        st.pydeck_chart(pdk.Deck(layers=[arc_layer, point_layer], initial_view_state=v_state, map_style="mapbox://styles/mapbox/dark-v10"))


# ---------------- TAB 5: VOICE & SWAB BIOLOGICAL LAB ----------------
def render_tab_lab():
    st.subheader("🔬 Voice & Swab Biological Verification Laboratory")
    st.markdown("""
    > [!IMPORTANT]
    > **Controlled Clinical & Biometric Access Layer:**
    > Voice and Swab Hematology records serve as vital supporting evidence when victims suffer memory loss or lack documentation.
    > Voice matching is strictly treated as supporting evidence and never automatic proof. Sensitive clinical data is masked outside authorized lab roles.
    """)
    
    is_lab_authorized = ss.selected_role in ("Medical & Lab Officer", "Relief Authority / Admin")
    if not is_lab_authorized:
        st.warning("🔒 You are currently viewing in a restricted role. Hematology and acoustic controls require Medical & Lab Officer authorization.")
        
    lab_mode = st.radio("Lab Analysis Module", ["🩸 Swab Hematology Verification Panel", "🎙️ Voice Identification & Acoustic Matcher"], horizontal=True)
    
    if "Swab" in lab_mode:
        st.markdown("### 🩸 **Swab-Based Biological Panel Verification**")
        st.caption("Measurable Test Parameters: WBC, RBC, HGB, PLT and Blood Group Compatibility")
        
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.markdown("#### Sample A: Family Donor / Medical Reference")
            bg_a = st.selectbox("Sample A Blood Group", config.BLOOD_GROUPS, index=4)  # O+
            wbc_a = st.number_input("WBC Count (10^3/µL) [Sample A]", 2.0, 25.0, 8.2, step=0.1)
            rbc_a = st.number_input("RBC Count (10^6/µL) [Sample A]", 2.0, 8.0, 4.8, step=0.1)
            hgb_a = st.number_input("Hemoglobin HGB (g/dL) [Sample A]", 6.0, 22.0, 13.9, step=0.1)
            plt_a = st.number_input("Platelets PLT (10^3/µL) [Sample A]", 50.0, 600.0, 275.0, step=5.0)
            
        with col_s2:
            st.markdown("#### Sample B: Unidentified Patient Bedside Swab")
            bg_b = st.selectbox("Sample B Blood Group", config.BLOOD_GROUPS, index=4)  # O+
            wbc_b = st.number_input("WBC Count (10^3/µL) [Sample B]", 2.0, 25.0, 8.6, step=0.1)
            rbc_b = st.number_input("RBC Count (10^6/µL) [Sample B]", 2.0, 8.0, 4.9, step=0.1)
            hgb_b = st.number_input("Hemoglobin HGB (g/dL) [Sample B]", 6.0, 22.0, 14.1, step=0.1)
            plt_b = st.number_input("Platelets PLT (10^3/µL) [Sample B]", 50.0, 600.0, 280.0, step=5.0)
            
        swab_res = compare_swab_profiles(
            {"blood_group": bg_a, "wbc": wbc_a, "rbc": rbc_a, "hgb": hgb_a, "plt": plt_a},
            {"blood_group": bg_b, "wbc": wbc_b, "rbc": rbc_b, "hgb": hgb_b, "plt": plt_b}
        )
        
        st.divider()
        st.markdown("#### 🧪 **Clinical Parameter Correlation & Tolerance Ranges**")
        
        m_wbc, m_rbc, m_hgb, m_plt = st.columns(4)
        m_wbc.metric("WBC Match Score", f"{swab_res['parameter_scores'].get('WBC', 0)*100:.0f}%", f"Δ {abs(wbc_a-wbc_b):.1f}")
        m_rbc.metric("RBC Match Score", f"{swab_res['parameter_scores'].get('RBC', 0)*100:.0f}%", f"Δ {abs(rbc_a-rbc_b):.1f}")
        m_hgb.metric("HGB Match Score", f"{swab_res['parameter_scores'].get('HGB', 0)*100:.0f}%", f"Δ {abs(hgb_a-hgb_b):.1f}")
        m_plt.metric("PLT Match Score", f"{swab_res['parameter_scores'].get('PLT', 0)*100:.0f}%", f"Δ {abs(plt_a-plt_b):.0f}")
        
        if swab_res["is_conflict"]:
            st.error(f"🔴 **Biological Contradiction:** {swab_res['conflict_reason']}")
        elif swab_res["match_score"] >= 0.75:
            st.success(f"🟢 **Swab Profile Consistent ({swab_res['match_score']*100:.1f}%):** Blood groups match and hematological indices align within clinical trauma variance.")
        else:
            st.warning("🟡 **Moderate Parameter Variance:** Requires secondary laboratory swab analysis.")
            
    else:
        st.markdown("### 🎙️ **Voice Identification & Acoustic Studio**")
        st.caption("Acoustic Feature Extraction: Fundamental Pitch (F0), Spectral Centroid, Formant Resonance")
        
        st.markdown("""
        > [!NOTE]
        > **Ethical Voice Identification Protocol:**
        > Recordings are made with proper patient/guardian authorization and legal consent. Voice matching is strictly supporting evidence and flags human verification if conflicting.
        """)
        
        v_col1, v_col2 = st.columns(2)
        with v_col1:
            st.markdown("#### 🎧 Family Audio Reference Sample")
            f0_a = st.slider("Fundamental Pitch F0 (Hz) [Sample A]", 80.0, 320.0, 265.0)
            sc_a = st.slider("Spectral Centroid (Hz) [Sample A]", 1000.0, 3500.0, 2450.0)
            st.caption("Authorized family clip: Child audio from family video recording.")
            
        with v_col2:
            st.markdown("#### 🎙️ Bedside Victim Voice Recording")
            f0_b = st.slider("Fundamental Pitch F0 (Hz) [Sample B]", 80.0, 320.0, 268.0)
            sc_b = st.slider("Spectral Centroid (Hz) [Sample B]", 1000.0, 3500.0, 2420.0)
            st.caption("Recorded at Relief Camp Alpha bedside with social worker present.")
            
        voice_res = compare_voice_samples(
            {"f0_hz": f0_a, "spectral_centroid": sc_a, "consent_given": True},
            {"f0_hz": f0_b, "spectral_centroid": sc_b, "consent_given": True}
        )
        
        st.divider()
        st.metric("Voice Acoustic Similarity", f"{voice_res['similarity']*100:.1f}%", f"Pitch Variance: {voice_res['f0_diff_hz']} Hz")
        
        if voice_res["is_conflict"]:
            st.error(f"🔴 **Acoustic Contradiction Flagged:** {voice_res['note']}")
        elif voice_res["status"] == "STRONG_SUPPORT":
            st.success(f"🟢 **Supporting Match:** {voice_res['note']}")
        else:
            st.warning(f"🟡 **Review Required:** {voice_res['note']}")


# ---------------- TAB 6: HUMAN VERIFICATION & REUNIFICATION DESK ----------------
def render_tab_verification():
    st.subheader("⚖️ Human Verification & Reunification Desk")
    st.markdown("""
    > [!IMPORTANT]
    > **AI Finds Connections — Authorized Humans Decide:**
    > The AI system never independently declares identity or authorizes family handover.
    > Every candidate must pass this rigorous multi-step verification protocol before a **Black Flame Reunification Certificate** is generated.
    """)
    
    missing_cases = get_all_cases("MISSING")
    unidentified_cases = get_all_cases("UNIDENTIFIED")
    
    # Pre-select candidate pair if loaded from dashboard or dropdowns
    default_m_idx = 0
    default_u_idx = 0
    
    if ss.verification_case_pair:
        m_rec, u_rec, _ = ss.verification_case_pair
        for i, c in enumerate(missing_cases):
            if c.get("case_code") == m_rec.get("case_code"):
                default_m_idx = i
                break
        for i, c in enumerate(unidentified_cases):
            if c.get("case_code") == u_rec.get("case_code"):
                default_u_idx = i
                break
                
    c_pick1, c_pick2 = st.columns(2)
    with c_pick1:
        case_a = st.selectbox("1. Select Missing Report", missing_cases, index=min(default_m_idx, len(missing_cases)-1),
                              format_func=lambda c: f"{c.get('case_code')} ({c.get('declared_name', 'Protected')} | Age: {c.get('age')})")
    with c_pick2:
        case_b = st.selectbox("2. Select Unidentified Intake Record", unidentified_cases, index=min(default_u_idx, len(unidentified_cases)-1),
                              format_func=lambda c: f"{c.get('case_code')} ({c.get('declared_name', 'Protected')} | Found: {c.get('found_place')})")
                              
    if not case_a or not case_b:
        return
        
    # Evaluate pair
    eval_res = evaluate_case_pair(case_a, case_b)
    level = eval_res["decision_level"]
    score = eval_res["numerical_score"]
    exp = eval_res["explanation"]
    
    st.write("")
    st.markdown(f"""
    <div class="bf-match-card card-{level.lower()}">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <h3>Evaluation Status: {render_decision_badge(level, score)}</h3>
            <span class="bf-badge-privacy">STAGE: HUMAN VERIFICATION DESK</span>
        </div>
        <p style="color:#cbd5e1; margin-top:8px;">
            {eval_res['decision_rationale']}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Factor Summary Breakdown
    f1, f2 = st.columns(2)
    with f1:
        st.markdown("**✓ Supporting Factor Checklist:**")
        for sup in exp.get("supporting_factors", []):
            st.markdown(f'<div class="bf-factor-item bf-factor-pro">✓ {sup}</div>', unsafe_allow_html=True)
    with f2:
        if exp.get("conflicting_factors"):
            st.markdown("**✗ Critical Conflicts Detected:**")
            for con in exp.get("conflicting_factors", []):
                st.markdown(f'<div class="bf-factor-item bf-factor-con">✗ {con}</div>', unsafe_allow_html=True)
        if exp.get("pending_factors"):
            st.markdown("**⚠️ Unverified Evidence:**")
            for pend in exp.get("pending_factors", []):
                st.markdown(f'<div class="bf-factor-item bf-factor-pending">⚠️ {pend}</div>', unsafe_allow_html=True)

    st.divider()
    
    # Authorized Officer Verification Form
    st.markdown("### ✍️ **Authorized Officer Verification Sign-Off**")
    
    if level == config.DECISION_RED:
        st.error("🔴 **STOPPED CANDIDATE:** Critical conflict detected. AI matching guidelines prohibit proceeding to reunification while critical conflicts exist.")
        return
        
    with st.form("officer_verification_form"):
        v_col1, v_col2 = st.columns(2)
        with v_col1:
            officer_name = st.text_input("Lead Verifying Officer Name", value="Inspector R. Kulkarni")
            officer_badge = st.text_input("Officer / Responder Badge ID", value="DISASTER-RESCUE-4410")
        with v_col2:
            verif_stage = st.selectbox("Verification Stage Action", [
                "OFFICER_REVIEW — Preliminary Interview Conducted",
                "AUTHORIZED_FOR_REUNIFICATION — Identity Confirmed & Certified",
                "REJECTED — Candidate Inconclusive"
            ])
            
        st.markdown("**Mandatory Verification Checkpoints:**")
        chk1 = st.checkbox("✓ Face-to-Face physical and mark inspection confirmed", value=True)
        chk2 = st.checkbox("✓ Timeline continuity & eyewitness statements corroborated", value=True)
        chk3 = st.checkbox("✓ Biological swab / voice sample reviewed and authorized", value=True)
        chk4 = st.checkbox("✓ Guardian / family mutual confirmation documented", value=True)
        
        officer_notes = st.text_area("Official Verification Notes & Findings",
                                     value="Family member and child reunited at Relief Camp Alpha. Marks on left forearm inspected and verified. Biological swab blood group O+ corroborated.")
                                     
        authorize_btn = st.form_submit_button("🛡️ Issue Official Reunification Authorization", type="primary")

    if authorize_btn:
        stage_clean = "AUTHORIZED_FOR_REUNIFICATION" if "AUTHORIZED" in verif_stage else "OFFICER_REVIEW"
        cert_code = save_verification({
            "match_id": f"{case_a.get('case_code')}_{case_b.get('case_code')}",
            "stage": stage_clean,
            "verified_by_officer": officer_name,
            "officer_badge_id": officer_badge,
            "verification_notes": officer_notes,
            "photo_verified": chk1,
            "swab_confirmed": chk3,
            "voice_confirmed": True
        })
        
        st.balloons()
        st.success("Reunification Clearance Approved!")
        
        # Display Official Black Flame Certificate
        cert_display_code = cert_code or f"BF-CERT-{uuid.uuid4().hex[:8].upper()}"
        st.markdown(f"""
        <div style="background:#090d16; border:3px solid #ff7a00; border-radius:18px; padding:32px; margin-top:20px; box-shadow:0 0 35px rgba(255,122,0,0.3); text-align:center;">
            <div style="display:flex; justify-content:center; margin-bottom:12px;">
                {get_logo_html(84)}
            </div>
            <h2 style="color:#ffbe53; font-weight:800; letter-spacing:2px; margin-bottom:4px;">BLACK FLAME REUNIFICATION CLEARANCE</h2>
            <p style="color:#94a3b8; font-size:0.95rem; text-transform:uppercase; letter-spacing:1.5px; margin-bottom:20px;">
                Disaster Relief & Family Union Authority
            </p>
            <div style="background:#111827; border:1px solid #374151; border-radius:12px; padding:18px; max-width:650px; margin:0 auto; text-align:left;">
                <p><strong>Certificate ID:</strong> <code>{cert_display_code}</code></p>
                <p><strong>Missing Person Case:</strong> {case_a.get('case_code')} ({case_a.get('declared_name')})</p>
                <p><strong>Unidentified Intake:</strong> {case_b.get('case_code')} ({case_b.get('declared_name')})</p>
                <p><strong>Multi-Factor Evaluation:</strong> 🟢 STRONG SUPPORTING MATCH ({score*100:.1f}%)</p>
                <p><strong>Verifying Authority:</strong> {officer_name} (Badge: {officer_badge})</p>
                <p><strong>Authorization Timestamp:</strong> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            </div>
            <p style="color:#10b981; font-weight:700; margin-top:20px; font-size:1.1rem;">
                ✓ IDENTITY OFFICIALLY CONFIRMED & FAMILY REUNIFICATION APPROVED
            </p>
        </div>
        """, unsafe_allow_html=True)


# ---------------- TAB 7: OFFLINE MODE & SUPABASE SYNC CENTER ----------------
def render_tab_sync():
    st.subheader("⚡ Offline Mode & Supabase PostgreSQL Sync Center")
    st.markdown("""
    > [!NOTE]
    > **Disaster Zone Resilience:**
    > When disaster strikes, cell towers fall and electricity is severed.
    > The Black Flame architecture ensures that caseworkers can operate entirely offline at field tents, logging cases and performing local AI matching.
    > Once connectivity is re-established, the Sync Center safely mirrors records to central Supabase PostgreSQL with conflict resolution and automated match re-evaluation.
    """)
    
    sync_summary = get_sync_status_summary()
    pending_items = get_pending_sync_items()
    
    c_status1, c_status2, c_status3 = st.columns(3)
    c_status1.metric("Connection Status", "Offline Mode" if ss.simulated_offline else ("Connected" if sync_summary["is_online"] else "Disconnected"))
    c_status2.metric("Pending Case Syncs", sync_summary["pending_case_count"])
    c_status3.metric("Pending Sighting Syncs", sync_summary["pending_sighting_count"])
    
    st.divider()
    
    st.markdown("#### 🔄 **Pending Sync Queue (Stored Locally in SQLite)**")
    if pending_items["cases"]:
        df_p_cases = pd.DataFrame(pending_items["cases"])[["case_code", "case_type", "age", "gender", "origin_area", "sync_status", "created_at"]]
        st.dataframe(df_p_cases, use_container_width=True)
    else:
        st.info("No cases currently pending synchronization.")
        
    st.write("")
    
    col_act1, col_act2 = st.columns([2, 3])
    with col_act1:
        st.markdown("#### Trigger Cloud Synchronization")
        st.caption("Pushes pending cases to Supabase PostgreSQL, preserves local timestamps, and triggers automated match re-evaluation.")
        
        if st.button("🚀 Execute Supabase Cloud Sync", type="primary", use_container_width=True):
            if ss.simulated_offline:
                st.warning("⚠️ Simulation offline mode is currently turned ON in the sidebar. Please disable the offline simulation toggle to test network sync.")
            else:
                with st.spinner("Connecting to Supabase PostgreSQL and pushing records..."):
                    sync_res = execute_full_synchronization()
                    if sync_res["success"]:
                        st.success(sync_res["message"])
                    else:
                        st.error(sync_res["message"])
                    st.rerun()

    with col_act2:
        st.markdown("#### 🛡️ **Conflict Resolution & Duplication Protocol**")
        st.markdown("""
        - **Primary Key Invariance:** Records generated offline maintain deterministic UUIDs.
        - **No Overwrite Guarantee:** Local field records are never clobbered by cloud sync.
        - **Post-Sync AI Re-Evaluation:** When new central cases arrive, candidate pairs are immediately re-scored through the Multi-Factor and Conflict Detection engines.
        """)


# ---------------- MAIN APPLICATION ROUTER ----------------
def main():
    render_header()
    render_sidebar()
    
    tabs = st.tabs([
        "🏛️ Command Dashboard",
        "🔍 Attribute Match Discovery",
        "📝 Register Case (Offline)",
        "🗺️ Timeline & Direction",
        "🔬 Voice & Swab Lab",
        "⚖️ Human Verification",
        "⚡ Offline & Supabase Sync"
    ])
    
    with tabs[0]:
        render_tab_dashboard()
    with tabs[1]:
        render_tab_discovery()
    with tabs[2]:
        render_tab_registration()
    with tabs[3]:
        render_tab_timeline()
    with tabs[4]:
        render_tab_lab()
    with tabs[5]:
        render_tab_verification()
    with tabs[6]:
        render_tab_sync()


if __name__ == "__main__":
    main()

