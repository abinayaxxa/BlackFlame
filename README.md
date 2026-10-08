# 🔥 Black Flame — AI-Powered Family Reunification System
### *Emblem: Family Union*

**Black Flame** is an AI-powered disaster-response, missing-person identification, and family reunification system designed for frontline rescue operations, relief camps, evacuation shelters, and field hospitals.

Unlike conventional missing-persons databases, **Black Flame does not depend on searching by a person's name**. In catastrophic scenarios (floods, earthquakes, conflicts), names are often misspelled, unknown to traumatized children, lost due to amnesia, or unstated by disoriented victims. 

Instead, Black Flame cross-correlates multi-factor non-name attributes, spatial-temporal sighting vectors (**Who + Where + When + Direction**), consent-authorized acoustic voice identification, and clinical swab hematology data (**WBC, RBC, HGB, PLT**).

---

## 🛡️ Core System Capabilities

### 1. Zero Name-Dependency & Multi-Factor Matching
- Searches and candidate evaluations operate entirely on physical, demographic, and circumstantial clues:
  - Approximate age with fuzzy tolerance margins
  - Gender & physical build
  - Permanent marks (scars, birthmarks, tattoos, moles, surgical incisions, amputations)
  - Clothing descriptions (color, garment type, fabric)
  - Origin village, district, or evacuation sector
  - Known relatives & kinship links (e.g. matching family mentions of "Uncle Ramesh")
- Matching levels represent supporting statistical correlation only — **never treated as proof of identity**.

### 2. Timeline Continuity: Who + Where + When + Direction
- Tracks the four critical dimensions of every sighting:
  $$\text{Who} + \text{Where} + \text{When} + \text{Direction}$$
- Computes Haversine spatial distance, elapsed time gap ($\Delta t$), and direction vector angle alignment.
- **Velocity Plausibility Check**:
  $$\text{Speed} = \frac{\text{Distance}}{\Delta t}$$
  - Walking evacuation speed ($1 - 6\text{ km/h}$) $\rightarrow$ Strong supporting continuity.
  - Emergency transit speed ($10 - 55\text{ km/h}$) $\rightarrow$ Plausible continuity.
  - Implausible teleportation ($>90\text{ km/h}$) $\rightarrow$ **Critical travel conflict flagged**.

### 3. Voice Identification (Supporting Evidence)
- Captures bedside audio from non-communicative or amnesiac individuals with authorized consent.
- Extracts acoustic pitch ($F_0$), spectral centroid timbre, formant ratios, and harmonicity.
- Compares against authorized family voice samples.
- Strictly marked as **Supporting Evidence**; conflicting vocal profiles trigger human verification alerts.

### 4. Swab-Based Biological Verification
- Integrates structured clinical swab panels:
  - **WBC**: White Blood Cells ($4.0 - 11.0 \times 10^3/\mu\text{L}$)
  - **RBC**: Red Blood Cells ($4.2 - 5.8 \times 10^6/\mu\text{L}$)
  - **HGB**: Hemoglobin ($12.0 - 17.5\text{ g/dL}$)
  - **PLT**: Platelets ($150 - 450 \times 10^3/\mu\text{L}$)
  - Blood Group Compatibility (ABO / Rh factors)
- Controlled access prevents exposing sensitive clinical information unnecessarily.

### 5. Color-Based Match Decision
The system never presents ambiguous standalone percentages like "92% Match". Every candidate is classified into three decision levels:
- 🟢 **GREEN — Strong Supporting Match**: Sufficiently consistent evidence across all vectors. Moves case to the authorized human verification desk.
- 🟡 **YELLOW — Uncertain / Needs Review**: Partial match or missing clinical evidence. Sent for field investigation.
- 🔴 **RED — Conflict / Weak Match**: Critical contradiction detected or insufficient evidence. Candidate halted immediately.

### 6. Active Conflict Detection: Hard Override Rule
> **Golden Principle:** A high numerical score must **NEVER** override a critical conflict.

If any contradiction is discovered (e.g., child vs adult age gap, blood group incompatibility, contradictory travel sequence, or acoustic mismatch), the candidate is **immediately downgraded to 🔴 RED** and halted.

### 7. Explainable Matching (XAI)
Every 🟢 GREEN or 🟡 YELLOW result generates a plain-language audit breakdown:
- ✓ Supporting Factors Checklist
- ✗ Conflicting Factors
- ⚠️ Pending Field Verification Items
- Recommended Action Guidance

### 8. Human Verification Before Reunification
The AI finds potential connections — **authorized humans decide**.
$$\text{Registration} \rightarrow \text{AI Matching} \rightarrow \text{Timeline Analysis} \rightarrow \text{Lab Review} \rightarrow \text{Conflict Audit} \rightarrow \text{Officer Sign-Off} \rightarrow \text{Reunification Certificate}$$

### 9. Privacy & Identity Protection
- Attribute-first searching masks names and contact numbers until a verified officer unlocks them.
- Role-based views: *Family / Guardian*, *Camp Field Responder*, *Medical & Lab Officer*, *Relief Authority*.

### 10. PostgreSQL via Supabase
- Centralized PostgreSQL cloud database storing cases, sightings, voice signatures, biological swabs, match evaluations, and audit logs.

### 11. Offline-First Architecture
Disaster zones frequently experience total power and cellular blackouts.
```
Field Intake (Offline) ──> Local SQLite ──> Local AI Matching ──> Marked "Pending Sync"
                                                                         │
Internet Restored ───────────────────────────────────────────────────────┘
       │
       ▼
Supabase PostgreSQL Synchronization ──> Conflict Resolution ──> Central Match Re-Evaluation
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Dependencies in [requirements.txt](file:///c:/Users/ABINAYA/disaster_reunite/requirements.txt)

### Launching the Application
Execute the Windows batch launcher:
```powershell
.\run.bat
```
Or run directly with Streamlit:
```powershell
streamlit run app.py
```

### Running the Automated Test Suite
```powershell
python test_system.py
```

---

## 📁 Repository Layout
- [app.py](file:///c:/Users/ABINAYA/disaster_reunite/app.py): Streamlit Web Application with custom dark obsidian UI/UX and Family Union emblem.
- [config.py](file:///c:/Users/ABINAYA/disaster_reunite/config.py): Vocabularies, clinical reference ranges, and system constants.
- [assets/logo_family_union.svg](file:///c:/Users/ABINAYA/disaster_reunite/assets/logo_family_union.svg): Custom vector logo representing the Family Union and Black Flame hearth.
- [assets/styles.css](file:///c:/Users/ABINAYA/disaster_reunite/assets/styles.css): Polished UI/UX stylesheet.
- [engine/matcher.py](file:///c:/Users/ABINAYA/disaster_reunite/engine/matcher.py): Multi-factor non-name matching engine.
- [engine/timeline_matcher.py](file:///c:/Users/ABINAYA/disaster_reunite/engine/timeline_matcher.py): Who + Where + When + Direction trajectory & velocity analyzer.
- [engine/voice_matcher.py](file:///c:/Users/ABINAYA/disaster_reunite/engine/voice_matcher.py): Voice acoustic comparison & consent verification.
- [engine/swab_matcher.py](file:///c:/Users/ABINAYA/disaster_reunite/engine/swab_matcher.py): Structured hematology swab verification (WBC, RBC, HGB, PLT).
- [engine/conflict_detector.py](file:///c:/Users/ABINAYA/disaster_reunite/engine/conflict_detector.py): Contradiction search & conflict override engine.
- [engine/explainability.py](file:///c:/Users/ABINAYA/disaster_reunite/engine/explainability.py): Explainable AI factor breakdown generator.
- [database/schema.sql](file:///c:/Users/ABINAYA/disaster_reunite/database/schema.sql): PostgreSQL / Supabase DDL.
- [database/local_db.py](file:///c:/Users/ABINAYA/disaster_reunite/database/local_db.py): Local SQLite offline-first database.
- [database/sync_manager.py](file:///c:/Users/ABINAYA/disaster_reunite/database/sync_manager.py): Cloud synchronization and queue manager.
- [seed_data.py](file:///c:/Users/ABINAYA/disaster_reunite/seed_data.py): Scenario data generator.
- [test_system.py](file:///c:/Users/ABINAYA/disaster_reunite/test_system.py): Automated test suite for all 11 core requirements.

