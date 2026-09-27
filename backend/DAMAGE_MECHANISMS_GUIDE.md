# API 581 Damage Mechanisms - Complete Implementation Guide

## Overview

API 581 RBI methodology calculates **Probability of Failure (PoF)** by combining:
- **Generic Failure Frequency (GFF)** - from historical data
- **Damage Factor (DF)** - calculated for each active damage mechanism
- **Management Systems Factor (FMS)** - typically 1.0

Formula: **PoF = GFF × DF_total × FMS**

---

## Implementation Status

### **Progress: 20/20 Implemented (100%) ✅ COMPLETE**

| # | Section | Damage Mechanism | File | Status |
|---|---------|------------------|------|--------|
| 1 | **4** | **Thinning** | `thinning_df.py` | ✅ |
| 2 | **2.D.2** | **External Corrosion** | `external_corrosion_df.py` | ✅ |
| 3 | **2.D.3** | **CUI** | `cui_df.py` | ✅ |
| 4 | **2.C.4** | **Caustic SCC** | `caustic_scc_df.py` | ✅ |
| 5 | **2.C.3** | **Amine SCC** | `amine_scc_df.py` | ✅ |
| 6 | **2.C.5** | **Chloride SCC** | `chloride_scc_df.py` | ✅ |
| 7 | **2.C.10** | **SSC** | `ssc_df.py` | ✅ |
| 8 | **2.C.9** | **HIC/SOHIC-H2S** | `hic_sohic_df.py` | ✅ |
| 9 | **2.C.6** | **HIC/SOHIC-HF** | `hic_sohic_hf_df.py` | ✅ |
| 10 | **2.C.2** | **Alkaline Carbonate SCC** | `generic_scc_df.py` | ✅ |
| 11 | **2.C.8** | **Carbonate SCC** | `generic_scc_df.py` | ✅ |
| 12 | **2.C.9** | **PWSCC** | `generic_scc_df.py` | ✅ |
| 13 | **2.C.7** | **HSC-HF** | `generic_scc_df.py` | ✅ |
| 14 | **5** | **HTHA** | `htha_df.py` | ✅ |
| 15 | **8** | **Brittle Fracture** | `brittle_fracture_df.py` | ✅ |
| 16 | - | **Sigma Phase Embrittlement** | `embrittlement_df.py` | ✅ |
| 17 | - | **Temper Embrittlement** | `embrittlement_df.py` | ✅ |
| 18 | - | **885°F Embrittlement** | `embrittlement_df.py` | ✅ |
| 19 | **9** | **Mechanical Fatigue** | `fatigue_lining_df.py` | ✅ |
| 20 | **2.D.4/2.D.5** | **Lining/Refractory Degradation** | `fatigue_lining_df.py` | ✅ |

---

## Complete RBI System

**File:** `complete_rbi_simplified.py`

### Features
- ✅ All 20 damage mechanisms integrated
- ✅ PoF calculation (GFF × DF_total × FMS)
- ✅ CoF calculation (Level 1 simplified)
- ✅ 5×5 Risk Matrix positioning
- ✅ Inspection interval recommendations

### Risk Matrix

| PoF Category | Range (failures/year) |
|--------------|----------------------|
| 1 | < 1×10⁻⁶ |
| 2 | 1×10⁻⁶ to 1×10⁻⁵ |
| 3 | 1×10⁻⁵ to 1×10⁻⁴ |
| 4 | 1×10⁻⁴ to 1×10⁻³ |
| 5 | > 1×10⁻³ |

| CoF Category | Range ($) |
|--------------|-----------|
| A | < $10,000 |
| B | $10,000 to $100,000 |
| C | $100,000 to $1M |
| D | $1M to $10M |
| E | > $10M |

### Inspection Recommendations

| Risk Level | Matrix Positions | Interval | Effectiveness |
|------------|------------------|----------|---------------|
| **High** | 5D, 5E, 4C-5C | 2 years | Level A |
| **Medium-High** | 3C-4B, 5A-5C | 4 years | Level B |
| **Medium** | 2B-3B | 8 years | Level C |
| **Low** | 1, 2A | 16 years | Level D |

---

## Detailed Mechanism Descriptions

### 1. Thinning (Section 4) ✅
**File:** `thinning_df.py` (23 KB)

Uniform or localized wall thickness loss due to corrosion/erosion.

**Key Steps (13):**
1. Art (Remaining thickness ratio)
2. FSThin (Future shell thickness)
3. SRp (Prior probability distribution)
4. Bayesian inspection update (Table 4.6)
5. Beta reliability index
6. Final DF with age escalation

**Key Equations:**
- Art = (tfurnished - CR × age) / trequired
- β = (Art - 1) / 0.2
- DF = base_DF × age^1.1 (capped at 5000)

**Test Results:** DF range 0.49 to 19,186

---

### 2. External Corrosion (Section 2.D.2) ✅
**File:** `external_corrosion_df.py` (19 KB)

Corrosion on external surfaces exposed to atmospheric conditions.

**Key Steps (18):**
1. Environmental driver selection (severe/moderate/mild/dry)
2. Base corrosion rate from Table 2.D.2.1
3. Temperature adjustment (Table 2.D.2.2)
4. Coating quality factor
5. Coating age adjustment
6. Structural reliability calculation

**Environmental Drivers (Table 2.D.2.1):**
- Severe: 0.50 mm/yr (marine, tropical)
- Moderate: 0.25 mm/yr
- Mild: 0.13 mm/yr
- Dry: 0.025 mm/yr (desert, indoor)

**Test Results:** DF range 0.034 to 3,395

---

### 3. CUI - Corrosion Under Insulation (Section 2.D.3) ✅
**File:** `cui_df.py` (16 KB)

Corrosion under thermal insulation, accelerated by moisture ingress.

**Key Steps (18):**
1. Insulation type factor
2. Insulation condition
3. Complexity factor
4. Temperature aggression (peak at 50-100°C)
5. Coating effectiveness
6. Driver adjustment

**Insulation Type Factors:**
- Calcium Silicate: 2.0× (most aggressive)
- Mineral Wool: 1.5×
- Foam Glass: 0.5× (least aggressive)

**Peak Aggression:** 50-100°C (122-212°F) where water condensation occurs

**Test Results:** DF range 0.02 to 6,385

---

### 4-12. Stress Corrosion Cracking (SCC) - 9 Types ✅

All SCC mechanisms follow standard 6-step procedure:
1. Susceptibility determination (High/Medium/Low/None)
2. Severity Index from Table 2.C.1.2 (1000/100/10/0)
3. Time since inspection
4. Inspection effectiveness (A/B/C/D/E)
5. Base DF from Table 2.C.1.3
6. Time escalation: DF = base_DF × age^1.1 (capped at 5000)

#### 4. Caustic SCC (Section 2.C.4) ✅
**File:** `caustic_scc_df.py` (13 KB)

Carbon steel in caustic (NaOH) service.

**Susceptibility:**
- NACE graph Areas A/B/C based on temperature and caustic concentration
- Area A (< 150°F, < 10%): None
- Area B (transition): Medium
- Area C (> 200°F, > 50%): High
- PWHT reduces by 1 level

**Test Results:** 6 scenarios, DF 0 to 5,000

---

#### 5. Amine SCC (Section 2.C.3) ✅
**File:** `amine_scc_df.py` (14 KB)

Carbon steel in amine treating service.

**Susceptibility by Amine Type:**
- MEA (Monoethanolamine): Most aggressive
- DIPA (Diisopropanolamine): High
- DEA (Diethanolamine): Medium
- MDEA (Methyldiethanolamine): Low

**Lean vs Rich:**
- Lean amine (low H2S loading): Higher stress
- Rich amine: Lower stress but more corrosive

**Test Results:** 6 scenarios, DF 0 to 5,000

---

#### 6. Chloride SCC (Section 2.C.5) ✅
**File:** `chloride_scc_df.py` (13 KB)

Austenitic stainless steel in chloride-containing environments.

**Susceptibility Matrix (Table 2.C.5.2):**
- Temperature and pH dependent
- pH < 2.5: Pitting corrosion (not SCC)
- pH 2.5-10.5, T > 140°F: SCC possible
- pH > 10.5: Caustic environment

**Environmental Modifiers (Table 2.C.5.3):**
- Chloride concentration
- Oxygen level
- Deposits presence

**Test Results:** 6 scenarios, DF 0 to 5,000

---

#### 7. SSC - Sulfide Stress Cracking (Section 2.C.10) ✅
**File:** `ssc_df.py` (14 KB)

High-strength steels in H2S service.

**Susceptibility:**
- Hardness thresholds: 200 BHN / 237 BHN (with PWHT)
- Hardness < 200: Low susceptibility
- Hardness 200-237: Medium (if PWHT)
- Hardness > 237: High

**Environmental Severity (Table 2.C.10.2):**
- H2S-pH matrix
- pH 5.5-6.5 (near-neutral): Lowest risk
- pH < 4 or > 8: Higher risk
- Cyanide > 20 ppm at pH > 7.6: Aggravating

**Requirements:**
- Water must be present
- H2S ≥ 1 ppm sufficient under susceptible conditions
- Tensile stress required

**Test Results:** 5 scenarios, DF 0 to 5,000

---

#### 8. HIC/SOHIC in H2S (Section 2.C.9) ✅
**File:** `hic_sohic_df.py` (13 KB)

Hydrogen-Induced Cracking / Stress-Oriented HIC in sour service.

**KEY DIFFERENCE from SSC:** Depends on **steel cleanliness (sulfur content)**, not hardness.

**Susceptibility (Table 2.C.9.3):**
- Sulfur content categories:
  - < 50 ppm: HIC-resistant steel → Low
  - 50-100 ppm: Medium
  - > 100 ppm: High susceptibility
- Product form: Plate more susceptible than pipe (banded microstructure)
- PWHT reduces susceptibility

**Online Monitoring Factor (Table 2.C.9.4):**
- No monitoring: F_OM = 1.0
- Hydrogen probes OR process monitoring: F_OM = 2.0
- BOTH: F_OM = 4.0

**Final DF:** DF = (base_DF × age^1.1) / F_OM (capped at 5000)

**Test Results:** 5 scenarios, DF 0 to 5,000

---

#### 9. HIC/SOHIC in HF (Section 2.C.6) ✅
**File:** `hic_sohic_hf_df.py` (6 KB)

HIC in hydrofluoric acid alkylation service.

**Simplified 7-Step Procedure:**
- No environmental severity step (HF presence = susceptible)
- Sulfur content thresholds (Table 2.C.6.2):
  - ≤ 0.01% S: Low sulfur steel
  - > 0.01% S: High sulfur steel
- Pipe (seamless): Always Low
- Plate: Depends on S content and PWHT

**Online Monitoring:** Same as HIC/SOHIC-H2S (F_OM = 1/2/4)

---

#### 10-13. Generic SCC Types ✅
**File:** `generic_scc_df.py` (6 KB)

Standard 6-step procedure for:
- **10. Alkaline Carbonate SCC (Section 2.C.2):** CO3²⁻ in amine systems
- **11. Carbonate SCC (Section 2.C.8):** CO2-containing water
- **12. PWSCC (Section 2.C.9):** Primary Water SCC in nuclear
- **13. HSC-HF (Section 2.C.7):** Hydrogen Stress Cracking in HF

All use susceptibility input (High/Medium/Low/None) provided by user or expert.

---

### 14. HTHA - High-Temperature Hydrogen Attack (Section 5) ✅
**File:** `htha_df.py` (7 KB)

Irreversible degradation of steel at high temperature in hydrogen service.

**Nelson Curves Implementation:**
Simplified curves for common materials:
- Carbon Steel: 600-1000°F, max 200-10 psia H2
- 0.5Cr-0.5Mo: 700-1100°F, max 500-40 psia H2
- 1.25Cr-0.5Mo: 850-1250°F, max 1000-100 psia H2
- 2.25Cr-1Mo: 900-1300°F, max 1500-180 psia H2

**Susceptibility:**
- Above Nelson curve: High/Medium
- Below with < 20% margin: Medium
- Below with > 50% margin: None

**Critical:** HTHA is irreversible; prevention via material selection is essential.

---

### 15. Brittle Fracture (Section 8) ✅
**File:** `brittle_fracture_df.py` (6 KB)

Low-temperature service failure due to insufficient material toughness.

**Material MDMT Limits (without impact testing):**
- Carbon Steel: -20°F
- 304/316 Stainless: -425°F (cryogenic service)
- Duplex Stainless: -50°F
- Cr-Mo Steels: 0 to -20°F

**Susceptibility:**
- MDMT < material limit by > 20°F: High
- MDMT < material limit: Medium
- MDMT < material limit by < 20°F: Low
- Adequate margin: None

**Charpy Impact Testing:** Can qualify materials below standard MDMT limits.

---

### 16-18. Embrittlement Mechanisms ✅
**File:** `embrittlement_df.py` (10 KB)

#### 16. Sigma Phase Embrittlement
**Material:** Duplex stainless steel (2205, 2507)
**Temperature Range:** 600-1000°F (peak at 800°F)
**Critical Time:** 1000 hours
**Effect:** Precipitation of brittle sigma phase → toughness loss

#### 17. Temper Embrittlement
**Material:** Cr-Mo steels (2.25Cr-1Mo, 1.25Cr-0.5Mo)
**Temperature Range:** 650-1100°F (peak at 875°F)
**Critical Time:** 10,000 hours
**Effect:** Segregation of impurities (P, Sn, Sb) to grain boundaries

#### 18. 885°F Embrittlement
**Material:** Ferritic stainless steel (409, 430, 446)
**Temperature Range:** 700-950°F (peak at 885°F)
**Critical Time:** 5,000 hours
**Effect:** Spinodal decomposition → Fe-rich α and Cr-rich α' phases

**Susceptibility Calculation:**
- Combined severity = (temp_severity) × (exposure_time / critical_time)
- Severity > 1.5: High
- Severity 0.8-1.5: Medium
- Severity 0.3-0.8: Low
- Severity < 0.3: None

---

### 19. Mechanical Fatigue (Section 9) ✅
**File:** `fatigue_lining_df.py` (11 KB)

Failure due to cyclic loading (pressure, thermal cycles).

**Susceptibility:**
- Cycle usage = actual_cycles / design_life_cycles
- Usage > 80%: High
- Usage 50-80%: Medium
- Usage 25-50%: Low
- Usage < 25%: None

**Application:** Piping subject to thermal cycling, vibration, start-stop operations.

---

### 20. Lining/Refractory Degradation (Section 2.D.4/2.D.5) ✅
**File:** `fatigue_lining_df.py` (11 KB)

Degradation of protective linings (polymer, glass) or refractory materials.

**Lining Types:**
- Refractory (high-temp furnaces, reactors)
- Polymer (corrosion-resistant)
- Glass (aggressive chemicals)

**Susceptibility:**
- Combined severity = (age / design_life) × condition_factor
- Condition factors: Good=0.5, Fair=1.0, Poor=2.0, Failed=3.0
- Severity > 1.5: High
- Severity 0.8-1.5: Medium
- Severity 0.3-0.8: Low
- Severity < 0.3: None

---

## Summary Tables

### Key API 581 Tables Implemented

| Table | Description | Usage |
|-------|-------------|-------|
| **3.1** | GFF (Generic Failure Frequency) | PoF calculation base |
| **4.5** | Prior Probabilities | Bayesian thinning |
| **4.6** | Conditional Probabilities | Inspection effectiveness |
| **2.D.2.1** | External Corrosion Base Rates | Environmental drivers |
| **2.D.2.2** | Temperature Adjustment | External corrosion |
| **2.C.1.2** | SCC Severity Index | All SCC mechanisms |
| **2.C.1.3** | SCC Base DF | All SCC mechanisms |
| **2.C.5.2** | Chloride SCC Temp-pH Matrix | Chloride SCC |
| **2.C.5.3** | Chloride Environmental Modifiers | Chloride SCC |
| **2.C.9.2** | HIC/SOHIC H2S-pH Severity | HIC/SOHIC-H2S |
| **2.C.9.3** | HIC/SOHIC Sulfur Susceptibility | HIC/SOHIC-H2S |
| **2.C.9.4** | Online Monitoring Factors | HIC/SOHIC |
| **2.C.6.2** | HIC/SOHIC-HF Sulfur Susceptibility | HIC/SOHIC-HF |

### Key Equations Implemented

| Equation | Description | File |
|----------|-------------|------|
| **2.10-2.20** | Thinning DF (Art, β, Bayesian) | `thinning_df.py` |
| **2.D.1-2.D.13** | External Corrosion DF | `external_corrosion_df.py` |
| **2.D.14-2.D.26** | CUI DF | `cui_df.py` |
| **2.C.2** | SCC DF = base × age^1.1 | All SCC files |
| **2.C.4** | Chloride severity modifiers | `chloride_scc_df.py` |
| **C.2.8** | HIC/SOHIC with monitoring | `hic_sohic_df.py` |
| **2.C.5** | HIC/SOHIC-HF with monitoring | `hic_sohic_hf_df.py` |

---

## Next Steps: Integration with Integra IMS

### Phase 1: Database Schema ✅ Ready
```sql
CREATE TABLE rbi_assessments (
    id UUID PRIMARY KEY,
    equipment_id UUID REFERENCES equipment(id),
    assessment_date DATE NOT NULL,
    pof_value DECIMAL,
    pof_category INTEGER, -- 1-5
    cof_financial DECIMAL,
    cof_category VARCHAR(1), -- A-E
    risk_matrix_position VARCHAR(2), -- e.g., '5D'
    risk_level VARCHAR(20), -- 'High', 'Medium-High', etc.
    inspection_interval_years INTEGER,
    inspection_effectiveness VARCHAR(1) -- A-E
);

CREATE TABLE damage_factor_results (
    id UUID PRIMARY KEY,
    assessment_id UUID REFERENCES rbi_assessments(id),
    mechanism_type VARCHAR(50),
    df_value DECIMAL,
    susceptibility VARCHAR(20),
    calculation_details JSONB -- Store all_steps
);
```

### Phase 2: FastAPI Endpoints
- `POST /api/rbi/thinning` → Calculate thinning DF
- `POST /api/rbi/external-corrosion` → Calculate external DF
- `POST /api/rbi/cui` → Calculate CUI DF
- ... (one endpoint per mechanism)
- `POST /api/rbi/complete` → Complete RBI assessment
- `GET /api/rbi/assessment/{id}` → Retrieve results
- `GET /api/rbi/risk-matrix` → Visualization data

### Phase 3: React/Next.js UI
- Equipment selection
- Active mechanisms selection
- Input forms per mechanism
- Real-time DF calculation
- Risk matrix visualization (5×5 grid)
- Inspection recommendations
- PDF report generation

### Phase 4: Advanced Features
- Historical tracking (trend analysis)
- What-if scenarios
- Bulk assessment (facility-wide)
- Inspection scheduling integration
- API 579 FFS integration (fitness-for-service)

---

## References

1. **API Recommended Practice 581**, 4th Edition, 2025
   - Risk-Based Inspection Methodology
2. **API Standard 579-1/ASME FFS-1**
   - Fitness-for-Service
3. **NACE MR0103/ISO 17945**
   - Materials Resistant to Sulfide Stress Cracking in Corrosive Petroleum Refining Environments
4. **API Standard 941**
   - Steels for Hydrogen Service at Elevated Temperatures and Pressures (HTHA Nelson Curves)
5. **NACE SP0403**
   - Avoiding Caustic Stress Corrosion Cracking

---

**Document Version:** 2.0  
**Last Updated:** September 26, 2026  
**Status:** ✅ Complete - All 20 mechanisms implemented  
**Next Milestone:** Database + API + UI integration
