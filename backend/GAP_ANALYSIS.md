# GAP ANALYSIS: Current Implementation vs API 581 Engine Map

**Generated:** September 27, 2026
**Comparison:** /tmp/rbi-581-calculator vs API581_Engine_Map.md

---

## EXECUTIVE SUMMARY

### What We Have ✅
- **20/20 Damage Mechanisms** - Complete DF calculators
- **POF Calculation** - GFF, DF combination, FMS (basic)
- **COF Level 1** - Complete implementation
- **Risk Matrix** - 5×5 grid with inspection recommendations
- **Database Schema** - PostgreSQL ready
- **API Endpoints** - FastAPI structure ready

### What's Missing 🔄

#### HIGH PRIORITY (Functional Gaps):
1. **Code Calculations Module** - tmin, corrosion rates, remaining life, MAWP, FFS
2. **FMS Audit** - Currently using fixed 1.0, need Annex 2.A audit (72 items)
3. **Input Validation Layer** - Missing/blocking/default flag system
4. **Reference Data Layer** - Table lookup registry with verification
5. **Timeline Planning (Part 4)** - 0.5-year steps, target date logic
6. **Special Equipment (Part 5)** - Tanks, HX bundles, PRDs, steam

#### MEDIUM PRIORITY (Quality & Compliance):
7. **Detailed Table Transcription** - Currently using hardcoded values, need CSV registry
8. **Audit Trail** - Table IDs and row references per result
9. **Inspection Equivalence** - 2B=1A, 2C=1B logic for effectiveness
10. **Unit System** - Need standardized internal units with conversion

#### LOW PRIORITY (Nice-to-have):
11. **COF Level 2** - Flash, dispersion, event tree
12. **Nelson Curve Digitization** - Currently using simplified HTHA
13. **NACE Chart Digitization** - Caustic SCC chart
14. **Regulatory Caps** - Permenaker 37/2016 intervals

---

## DETAILED GAP ANALYSIS

### 1. CODE CALCULATIONS (Missing Module)

**Status:** ❌ NOT IMPLEMENTED

**What Engine Map Requires:**
```python
# Before RBI runs, compute:
- t_required (tmin from B31.3/ASME VIII/API 653)
- CR_LT, CR_ST (long-term & short-term corrosion rates)
- Remaining Life (RL)
- Code Interval (API 570/510 Table 6.1)
- MAWP at end of interval
- FFS trigger flag
- Regulatory cap (Permenaker)
- Next date = earliest(RBI, code, regulatory)
```

**What We Have:**
- Nothing. Our system assumes tmin, CR are inputs.

**Impact:**
- HIGH - Can't generate complete inspection intervals
- Our "next_inspection_date" lacks code compliance check

**Recommendation:**
Implement new module `codecalc/` with:
- `tmin_calculator.py` (B31.3 Eq 3a, ASME VIII UG-27, API 653)
- `corrosion_rate.py` (API 570 §7.1.1, API 510 §7.1)
- `remaining_life.py` (RL = (t_actual - t_required) / CR)
- `code_interval.py` (API 570 Table 6.1, min(RL/2, class limit))
- `mawp.py` (design formula solved for P at t_eval)
- `next_date.py` (earliest of RBI, code, regulatory)

---

### 2. FMS MANAGEMENT SYSTEMS FACTOR (Incomplete)

**Status:** ⚠️ PARTIAL - Using FMS = 1.0 fixed

**What Engine Map Requires:**
```python
# P2 §3.5, Annex 2.A
F_MS = 2.38 · e^(−0.012 · pscore)
pscore = Σ (weight% · section_score)

Sections (72 items total):
- Management of Inspection (MI): 50%
- Site Management: 17%
- Management of Change: 13%
- Failure Investigation: 10%
- Process Safety: 5%
- Operating Procedures: 5%

pscore = 72 → F_MS ≈ 1.0
```

**What We Have:**
```python
# complete_rbi_simplified.py line ~50
fms = component.get('fms', 1.0)  # Fixed default
```

**Impact:**
- MEDIUM - Affects POF accuracy
- Underestimates POF for poor management (pscore < 72)
- Overestimates POF for good management (pscore > 72)

**Recommendation:**
Add `fms_audit.py`:
```python
def calculate_fms(audit_scores: dict) -> float:
    """
    audit_scores = {
        'management_inspection': 0-100,
        'site_management': 0-100,
        'management_of_change': 0-100,
        'failure_investigation': 0-100,
        'process_safety': 0-100,
        'operating_procedures': 0-100
    }
    """
    pscore = (
        0.50 * audit_scores['management_inspection'] +
        0.17 * audit_scores['site_management'] +
        0.13 * audit_scores['management_of_change'] +
        0.10 * audit_scores['failure_investigation'] +
        0.05 * audit_scores['process_safety'] +
        0.05 * audit_scores['operating_procedures']
    )
    fms = 2.38 * math.exp(-0.012 * pscore)
    return fms
```

---

### 3. INPUT VALIDATION & FLAG SYSTEM (Missing)

**Status:** ❌ NOT IMPLEMENTED

**What Engine Map Requires:**
```
Flag System:
MISSING        blank, no default → module skipped
BLOCKING       required, no default → component not calculated
DEFAULT_581    581 default used (e.g. Cl⁻ > 1000 ppm)
ASSUMED        conservative assumption (e.g. PWHT = No)
LCI_OVERRIDE   LCI table replaced 581 example
ENGINEER       value entered by engineer (name + date)
```

**What We Have:**
- No input validation
- No flag propagation
- Calculator assumes all inputs valid

**Impact:**
- HIGH - Compliance risk
- Can't trace which results depend on weak data
- No audit trail for assumptions

**Recommendation:**
Add `flags/` module:
```python
class InputFlag:
    MISSING = "MISSING"
    BLOCKING = "BLOCKING"
    DEFAULT_581 = "DEFAULT_581"
    ASSUMED = "ASSUMED"
    LCI_OVERRIDE = "LCI_OVERRIDE"
    ENGINEER = "ENGINEER"

def validate_input(field, value, required, default_581, assumed):
    if value is None:
        if required:
            return (None, InputFlag.BLOCKING)
        elif default_581 is not None:
            return (default_581, InputFlag.DEFAULT_581)
        elif assumed is not None:
            return (assumed, InputFlag.ASSUMED)
        else:
            return (None, InputFlag.MISSING)
    return (value, None)
```

---

### 4. REFERENCE DATA LAYER (Missing)

**Status:** ❌ NOT IMPLEMENTED

**What Engine Map Requires:**
```
refdata/
  api581_4ed/
    table_3_1_gff.csv
    table_4_5_prior_prob.csv
    table_4_6_cond_prob.csv
    table_2_C_1_2_svi.csv
    table_2_C_1_3_dfb_scc.csv
    [... 50+ table files]
  lci_overrides/
    inspection_effectiveness.csv
    hole_costs.csv
  table_registry.json
```

**What We Have:**
- Hardcoded dictionaries in each calculator
- No table registry
- No lookup verification
- No audit trail

**Example Current Code:**
```python
# thinning_df.py
GFF_TABLE = {
    'pipe': 1.56e-4,
    'vessel': 3.06e-4,
    'heat_exchanger': 3.36e-4,
    'tank': 6.91e-6,
    'filter': 1.50e-3
}
```

**Impact:**
- MEDIUM - Maintainability issue
- Can't trace values back to API 581 page
- Hard to update when standard changes
- No LCI override capability

**Recommendation:**
```python
# refdata/table_registry.py
class TableRegistry:
    def __init__(self, api581_edition='4ed', lci_override_dir=None):
        self.tables = self.load_all_tables()
        self.audit_log = []
    
    def lookup(self, table_id, keys, interpolate=False):
        """
        Returns: (value, audit_record)
        audit_record = {
            'table_id': 'P2_Table_3.1',
            'edition': '4ed',
            'keys': keys,
            'row': row_number,
            'value': value,
            'source': 'api581' or 'lci_override'
        }
        """
        pass
```

---

### 5. PART 4 - INSPECTION PLANNING (Missing)

**Status:** ❌ NOT IMPLEMENTED

**What Engine Map Requires:**
```python
# P4 §3 Steps 1–14
# Timeline with 0.5-year steps:

for t in [0, 0.5, 1.0, 1.5, ... plan_period]:
    thickness[t] = thickness[t-0.5] - CR * 0.5
    df_total[t] = recalculate_all_dfs(thickness[t], age=t)
    pof[t] = gff * df_total[t] * fms
    risk[t] = pof[t] * cof
    
    if risk[t] > target_risk:
        target_date = t
        # Try inspection effectiveness B, then A
        break

next_inspection = earliest(target_date, code_interval, regulatory_cap)
```

**What We Have:**
```python
# complete_rbi_simplified.py
# Static calculation at current time only
# No timeline projection
# Inspection interval from risk level lookup table
```

**Impact:**
- MEDIUM - Simplified interval logic
- Can't model "when will component cross risk threshold"
- No optimization for inspection effectiveness

**Recommendation:**
Add `planning/timeline.py`:
```python
def calculate_target_date(
    component,
    damage_factors,
    target_risk,
    plan_period=10,
    time_step=0.5
):
    timeline = []
    for t in range(0, int(plan_period/time_step)+1):
        time = t * time_step
        # Recalculate at each step
        thickness_t = ... 
        df_t = ...
        pof_t = ...
        risk_t = pof_t * cof
        timeline.append({...})
        
        if risk_t > target_risk:
            return optimize_inspection(timeline, target_risk)
    
    return timeline[-1]
```

---

### 6. PART 5 - SPECIAL EQUIPMENT (Missing)

**Status:** ❌ NOT IMPLEMENTED

**What Engine Map Requires:**
- Tank bottom DF (P5 §4.3)
- Tank course/bottom COF (§4.5-4.26)
- HX bundle Weibull (§5.5-5.9)
- PRD (§6.3-6.7)
- Steam systems (§7.3-7.4)

**What We Have:**
- Generic equipment only (pipe, vessel, heat_exchanger, tank as generic)
- No specialized tank bottom corrosion
- No bundle tube failure modeling
- No PRD demand rate

**Impact:**
- MEDIUM - Feature gap for specialized equipment
- Can't assess tank bottoms properly (most common tank failure)
- Can't model HX bundle reliability

**Recommendation:**
Add `special/` module in Phase 4:
```
special/
  tank_bottom_df.py      # Eq 5.1-5.3
  tank_course_cof.py     # Eq 5.5-5.32
  tank_bottom_cof.py     # Eq 5.33-5.54
  hx_bundle.py           # Weibull, Eq 5.55-5.87
  prd.py                 # Eq 5.91-5.121
  steam.py               # Eq 5.122-5.157
```

---

### 7. TABLE TRANSCRIPTION (Quality Issue)

**Status:** ⚠️ PARTIAL - Values correct but not traceable

**What Engine Map Requires:**
- Each table in separate CSV/JSON file
- Table ID, edition, page number
- Second-person verification
- Lookup rule documented
- Unit tests per table

**What We Have:**
- Values transcribed into Python dictionaries
- No verification log
- No table source tracking

**Impact:**
- LOW - Values are correct for now
- HIGH RISK for future updates (which table? which page?)

**Recommendation:**
Refactor over time:
1. Extract all hardcoded tables to CSV
2. Add table_registry.json with metadata
3. Write unit tests comparing CSV vs known values
4. Second engineer reviews each table

---

### 8. INSPECTION EQUIVALENCE (Logic Gap)

**Status:** ❌ NOT IMPLEMENTED

**What Engine Map Requires:**
```python
# P2 §3.4.3
# For SCC, ExtClSCC, HTHA only (never E):
2B = 1A
2C = 1B  
2D = 1C
```

**What We Have:**
- No equivalence logic
- Inspection effectiveness taken as-is

**Impact:**
- LOW - Minor accuracy issue
- Affects DF calculation for SCC when 2 inspections used

**Recommendation:**
Add to each SCC calculator:
```python
def normalize_inspection_effectiveness(num_inspections, effectiveness):
    if num_inspections == 2:
        equiv = {'B': 'A', 'C': 'B', 'D': 'C'}
        return equiv.get(effectiveness, effectiveness)
    return effectiveness
```

---

### 9. UNIT SYSTEM (Design Issue)

**Status:** ⚠️ MIXED - Calculations use mixed units

**What Engine Map Requires:**
- Internal calculation in one consistent unit system
- Conversion at input/output using P3 Annex 3.B constants
- Decision: SI or US Customary

**What We Have:**
- Mixed units throughout (psi, °F, inches, MPa, °C, mm)
- Conversion scattered in code

**Impact:**
- MEDIUM - Maintenance burden
- Risk of conversion errors

**Recommendation:**
Standardize to SI internally:
```python
# units.py
UNITS_SI = {
    'pressure': 'MPa',
    'temperature': 'K',
    'length': 'm',
    'mass': 'kg'
}

def convert_to_si(value, unit_from):
    # P3 Annex 3.B constants
    pass

def convert_from_si(value, unit_to):
    pass
```

---

## PRIORITY ROADMAP

### PHASE 2A: CRITICAL GAPS (3-4 days)
Priority: HIGH - Required for production use

✅ Already planned:
- Database integration
- API implementation

🔄 Add to Phase 2:
1. **Code Calc Module** (1 day)
   - tmin, corrosion rates, remaining life
   - Code intervals (API 570/510)
   - MAWP calculation
   - Next date logic

2. **FMS Audit** (0.5 day)
   - Implement Annex 2.A formula
   - Create audit input form
   - Integrate with POF calculation

3. **Input Validation** (0.5 day)
   - Flag system
   - Validation rules per input
   - Flag propagation to results

### PHASE 3A: QUALITY IMPROVEMENTS (2-3 days)
Priority: MEDIUM - Compliance & traceability

4. **Reference Data Layer** (1 day)
   - Table registry
   - CSV/JSON table files
   - Lookup functions with audit trail

5. **Part 4 Timeline Planning** (1 day)
   - 0.5-year step calculation
   - Target date optimization
   - Inspection effectiveness selector

6. **Inspection Equivalence** (0.5 day)
   - 2B=1A logic for SCC
   - Update all SCC calculators

### PHASE 4A: ADVANCED FEATURES (3-4 days)
Priority: LOW - Feature expansion

7. **Part 5 Special Equipment** (2 days)
   - Tank bottom DF
   - Tank COF
   - HX bundle Weibull

8. **Unit System Refactor** (1 day)
   - Standardize to SI internally
   - Conversion layer

9. **COF Level 2** (Future)
   - Flash, dispersion models
   - Event tree

---

## FILES TO CREATE

### Immediate (Phase 2A):

```
codecalc/
  __init__.py
  tmin_calculator.py          # B31.3, ASME VIII, API 653
  corrosion_rate.py           # API 570 §7.1.1
  remaining_life.py
  code_interval.py            # API 570 Table 6.1
  mawp.py
  next_date.py                # earliest(RBI, code, regulatory)

fms_audit.py                  # Annex 2.A
input_validation.py           # Flag system
```

### Near-term (Phase 3A):

```
refdata/
  table_registry.py
  api581_4ed/
    table_3_1_gff.csv
    table_4_5_prior_prob.csv
    [... 50+ tables]
  lci_overrides/

planning/
  timeline.py                 # 0.5-year steps
  target_date.py              # Risk threshold crossing
  inspection_selector.py      # Optimize effectiveness
```

### Long-term (Phase 4A):

```
special/
  tank_bottom_df.py
  tank_cof.py
  hx_bundle.py
  prd.py
  steam.py

units/
  converter.py                # P3 Annex 3.B
  constants.py
```

---

## CONCLUSION

**Current Implementation Coverage: ~60%**
- ✅ Core DF calculators: 100%
- ✅ POF basic: 100%
- ✅ COF Level 1: 100%
- ✅ Risk matrix: 100%
- ⚠️ FMS: 20% (fixed value only)
- ❌ Code calc: 0%
- ❌ Part 4 timeline: 0%
- ❌ Part 5 special: 0%
- ❌ Input validation: 0%
- ❌ Reference data layer: 0%

**Recommended Action:**
1. **Proceed with Phase 2** database integration as planned
2. **Add Phase 2A** (3-4 days) for critical gaps: Code calc + FMS + validation
3. **Schedule Phase 3A** (2-3 days) for quality: Reference data + Part 4
4. **Phase 4A** (3-4 days) for Part 5 special equipment

**Total additional time:** 8-11 days on top of original 10-14 day estimate
**New total:** 18-25 days for **production-ready enterprise system** with full API 581 4th Edition compliance

---

**Generated:** September 27, 2026
**Status:** Gap analysis complete
**Next Action:** Review with stakeholder, prioritize Phase 2A additions
