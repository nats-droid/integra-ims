# IMPLEMENTATION PRIORITY - Critical Gaps

**Date:** September 27, 2026
**Priority:** HIGH - Must implement before production

---

## CRITICAL PATH: 3 Missing Modules

Berdasarkan gap analysis, ada 3 module yang **WAJIB** ada sebelum production:

### 1. CODE CALCULATIONS ⭐⭐⭐ (CRITICAL)
**Why Critical:** 
- RBI intervals harus comply dengan API 570/510 code requirements
- Tanpa ini, hasil "next_inspection_date" tidak valid
- Regulatory requirement (Permenaker 37/2016)

**Effort:** 1 day

### 2. FMS AUDIT ⭐⭐ (HIGH)
**Why Important:**
- POF calculation accuracy depends on FMS
- Fixed FMS=1.0 assumes perfect management (rarely true)
- Under/over-estimates risk significantly

**Effort:** 0.5 day

### 3. INPUT VALIDATION & FLAGS ⭐⭐ (HIGH)
**Why Important:**
- Audit trail requirement
- Regulatory compliance
- Traceability: which results depend on assumptions

**Effort:** 0.5 day

---

## DETAILED IMPLEMENTATION PLAN

### MODULE 1: CODE CALCULATIONS

**File:** `codecalc/tmin_calculator.py`

```python
"""
Required thickness (tmin) calculation per design code
References: B31.3, ASME VIII-1, API 653, API 574
"""

def calculate_tmin_piping_pressure(P, D, S, E, W, Y):
    """
    B31.3 §304.1.2 Eq (3a)
    
    Args:
        P: Design pressure (psig)
        D: Outside diameter (in)
        S: Allowable stress (psi)
        E: Quality factor (0.85-1.0)
        W: Weld joint strength reduction (typ. 1.0)
        Y: Temperature coefficient (Table 304.1.1)
    
    Returns:
        t: Required thickness (in)
    """
    t = (P * D) / (2 * (S * E * W + P * Y))
    return t

def calculate_tmin_piping(P, D, S, E, W, Y, NPS, T_design):
    """
    Piping tmin = max(pressure, structural)
    
    Structural from API 574 table (by NPS and temperature)
    """
    t_pressure = calculate_tmin_piping_pressure(P, D, S, E, W, Y)
    t_structural = get_structural_tmin(NPS, T_design)
    
    return max(t_pressure, t_structural)

def get_structural_tmin(NPS, T_design):
    """
    API 574 structural minimum thickness table
    
    Returns minimum wall for structural integrity
    """
    # Table from API 574 (verify table number in your edition)
    structural_table = {
        # NPS: {temp_range: tmin_in}
        (0, 1): {(-20, 400): 0.065, (400, 650): 0.065, (650, 900): 0.083},
        (1.25, 2): {(-20, 400): 0.065, (400, 650): 0.083, (650, 900): 0.109},
        (2.5, 3): {(-20, 400): 0.083, (400, 650): 0.083, (650, 900): 0.120},
        (4, 6): {(-20, 400): 0.083, (400, 650): 0.109, (650, 900): 0.134},
        (8, 10): {(-20, 400): 0.109, (400, 650): 0.134, (650, 900): 0.188},
        (12, 16): {(-20, 400): 0.156, (400, 650): 0.188, (650, 900): 0.250},
        (18, 24): {(-20, 400): 0.188, (400, 650): 0.219, (650, 900): 0.312}
    }
    
    for nps_range, temp_dict in structural_table.items():
        if nps_range[0] <= NPS <= nps_range[1]:
            for temp_range, tmin in temp_dict.items():
                if temp_range[0] <= T_design < temp_range[1]:
                    return tmin
    
    return 0.083  # Conservative fallback

def calculate_tmin_vessel_shell(P, R, S, E, stress_type='circumferential'):
    """
    ASME VIII-1 UG-27
    
    Args:
        stress_type: 'circumferential', 'longitudinal', or 'sphere'
    """
    if stress_type == 'circumferential':
        t = (P * R) / (S * E - 0.6 * P)
    elif stress_type == 'longitudinal':
        t = (P * R) / (2 * S * E + 0.4 * P)
    elif stress_type == 'sphere':
        t = (P * R) / (2 * S * E - 0.2 * P)
    else:
        raise ValueError(f"Unknown stress_type: {stress_type}")
    
    return t

def calculate_tmin_vessel(P, R_or_D, S, E, component_type='shell'):
    """
    Complete vessel tmin (shell + head)
    
    Returns max of circumferential and longitudinal
    """
    if component_type == 'shell':
        t_circ = calculate_tmin_vessel_shell(P, R_or_D, S, E, 'circumferential')
        t_long = calculate_tmin_vessel_shell(P, R_or_D, S, E, 'longitudinal')
        return max(t_circ, t_long)
    
    elif component_type == 'head_elliptical':
        # 2:1 ellipsoidal head (most common)
        D = R_or_D * 2  # D = 2R
        t = (P * D) / (2 * S * E - 0.2 * P)
        return t
    
    else:
        raise ValueError(f"Unknown component_type: {component_type}")

def calculate_tmin_tank_shell(H, D, G, S, E):
    """
    API 653 §4.3.3.1
    Tank shell minimum thickness
    
    Args:
        H: Design liquid height (ft)
        D: Tank diameter (ft)
        G: Specific gravity of liquid
        S: Allowable stress (psi)
        E: Joint efficiency
    
    Returns:
        tmin (in)
    """
    tmin = 2.6 * (H - 1) * D * G / (S * E)
    return max(tmin, 0.1)  # Absolute minimum 0.1 in
```

**File:** `codecalc/corrosion_rate.py`

```python
"""
Corrosion rate calculation per API 570/510
"""

def calculate_corrosion_rate(thickness_history):
    """
    Args:
        thickness_history: [
            {'date': '2020-01-01', 'thickness': 0.500},
            {'date': '2023-01-01', 'thickness': 0.485},
            {'date': '2026-01-01', 'thickness': 0.470}
        ]
    
    Returns:
        {
            'CR_LT': long-term rate (mpy),
            'CR_ST': short-term rate (mpy),
            'governing': 'LT' or 'ST'
        }
    """
    if len(thickness_history) < 2:
        return {'CR_LT': 0, 'CR_ST': 0, 'governing': 'LT'}
    
    # Sort by date
    history = sorted(thickness_history, key=lambda x: x['date'])
    
    # Long-term: first to last
    t_initial = history[0]['thickness']
    t_actual = history[-1]['thickness']
    date_initial = pd.to_datetime(history[0]['date'])
    date_actual = pd.to_datetime(history[-1]['date'])
    years_LT = (date_actual - date_initial).days / 365.25
    
    CR_LT = (t_initial - t_actual) / years_LT if years_LT > 0 else 0
    CR_LT_mpy = CR_LT * 1000  # inches/yr to mpy
    
    # Short-term: last two readings
    if len(history) >= 2:
        t_previous = history[-2]['thickness']
        date_previous = pd.to_datetime(history[-2]['date'])
        years_ST = (date_actual - date_previous).days / 365.25
        
        CR_ST = (t_previous - t_actual) / years_ST if years_ST > 0 else 0
        CR_ST_mpy = CR_ST * 1000
    else:
        CR_ST_mpy = CR_LT_mpy
    
    # Governing: use the larger (conservative)
    governing = 'LT' if CR_LT_mpy >= CR_ST_mpy else 'ST'
    
    return {
        'CR_LT': max(CR_LT_mpy, 0),
        'CR_ST': max(CR_ST_mpy, 0),
        'governing': governing,
        'years_LT': years_LT,
        'years_ST': years_ST if len(history) >= 2 else years_LT
    }

def calculate_remaining_life(t_actual, t_required, corrosion_rate):
    """
    API 570 §7.1.1
    
    RL = (t_actual - t_required) / CR
    """
    if corrosion_rate <= 0:
        return float('inf')  # No corrosion
    
    RL = (t_actual - t_required) / (corrosion_rate / 1000)  # mpy to in/yr
    return max(RL, 0)
```

**File:** `codecalc/code_interval.py`

```python
"""
Code-based inspection interval per API 570/510
"""

def calculate_code_interval_piping(remaining_life, piping_class):
    """
    API 570 §6.3, Table 6.1
    
    Args:
        remaining_life: years
        piping_class: 1, 2, or 3
    
    Returns:
        interval (years)
    """
    class_limits = {
        1: 5,   # Class 1: 5 years max
        2: 10,  # Class 2: 10 years max
        3: 10   # Class 3: 10 years max
    }
    
    max_interval = class_limits.get(piping_class, 5)
    
    # Interval = min(RL/2, class limit)
    interval = min(remaining_life / 2, max_interval)
    
    return max(interval, 0.5)  # Minimum 6 months

def calculate_code_interval_vessel(remaining_life):
    """
    API 510 §6.4-6.5
    
    Returns:
        {
            'internal_onstream': years,
            'external_visual': years
        }
    """
    # Internal / on-stream: min(RL/2, 10 years)
    internal = min(remaining_life / 2, 10)
    
    # External visual: 5 years
    external = 5
    
    return {
        'internal_onstream': max(internal, 0.5),
        'external_visual': external
    }

def calculate_mawp(t_eval, design_code_params):
    """
    MAWP at end of interval
    
    Args:
        t_eval: thickness at end of interval (in)
        design_code_params: dict with P, D, S, E, etc.
    
    Returns:
        MAWP (psig)
    """
    component_type = design_code_params['component_type']
    
    if component_type == 'pipe':
        # B31.3 solved for P
        D = design_code_params['D']
        S = design_code_params['S']
        E = design_code_params['E']
        W = design_code_params.get('W', 1.0)
        Y = design_code_params.get('Y', 0.4)
        
        MAWP = (2 * S * E * W * t_eval) / (D - 2 * Y * t_eval)
        
    elif component_type == 'vessel_circ':
        # ASME VIII-1 UG-27(c)(1) solved for P
        R = design_code_params['R']
        S = design_code_params['S']
        E = design_code_params['E']
        
        MAWP = (S * E * t_eval) / (R + 0.6 * t_eval)
    
    else:
        raise ValueError(f"Unknown component_type: {component_type}")
    
    return MAWP
```

**File:** `codecalc/next_date.py`

```python
"""
Final next inspection date = earliest of RBI, code, regulatory
"""
from datetime import datetime, timedelta

def calculate_next_inspection_date(
    assessment_date,
    rbi_target_date,
    code_interval_years,
    regulatory_interval_years=None
):
    """
    Determine governing inspection date
    
    Returns:
        {
            'next_date': datetime,
            'interval_years': float,
            'governing_criterion': 'RBI' | 'Code' | 'Regulatory'
        }
    """
    candidates = []
    
    # RBI target date
    if rbi_target_date:
        candidates.append({
            'date': rbi_target_date,
            'criterion': 'RBI'
        })
    
    # Code interval
    code_date = assessment_date + timedelta(days=int(code_interval_years * 365.25))
    candidates.append({
        'date': code_date,
        'criterion': 'Code (API 570/510)'
    })
    
    # Regulatory cap (Permenaker 37/2016)
    if regulatory_interval_years:
        regulatory_date = assessment_date + timedelta(days=int(regulatory_interval_years * 365.25))
        candidates.append({
            'date': regulatory_date,
            'criterion': 'Regulatory (Permenaker 37/2016)'
        })
    
    # Earliest date governs
    earliest = min(candidates, key=lambda x: x['date'])
    
    interval_days = (earliest['date'] - assessment_date).days
    interval_years = interval_days / 365.25
    
    return {
        'next_date': earliest['date'],
        'interval_years': interval_years,
        'governing_criterion': earliest['criterion']
    }

def get_regulatory_interval(component_type):
    """
    Permenaker 37/2016 intervals
    
    UNSURE - verify pasal numbers in your copy
    
    Returns:
        interval (years) or None if not applicable
    """
    regulatory_intervals = {
        'pressure_vessel': 3,
        'storage_tank': 5,
        'heat_exchanger': 3,
        'boiler': 1,
        'piping': None  # Not covered
    }
    
    return regulatory_intervals.get(component_type)
```

---

### MODULE 2: FMS AUDIT

**File:** `fms_audit.py`

```python
"""
Management Systems Factor (FMS) calculation
API 581 Part 2 §3.5, Annex 2.A
"""
import math

def calculate_fms(audit_scores):
    """
    F_MS = 2.38 · e^(−0.012 · pscore)
    
    Args:
        audit_scores: {
            'management_inspection': 0-100,      # 50% weight
            'site_management': 0-100,            # 17% weight
            'management_of_change': 0-100,       # 13% weight
            'failure_investigation': 0-100,      # 10% weight
            'process_safety': 0-100,             # 5% weight
            'operating_procedures': 0-100        # 5% weight
        }
    
    Returns:
        {
            'fms': float,
            'pscore': float,
            'interpretation': str
        }
    """
    # Weights from API 581 Annex 2.A
    weights = {
        'management_inspection': 0.50,
        'site_management': 0.17,
        'management_of_change': 0.13,
        'failure_investigation': 0.10,
        'process_safety': 0.05,
        'operating_procedures': 0.05
    }
    
    # Calculate weighted pscore
    pscore = sum(
        weights[key] * audit_scores.get(key, 50)  # Default 50 if missing
        for key in weights
    )
    
    # F_MS formula
    fms = 2.38 * math.exp(-0.012 * pscore)
    
    # Interpretation
    if pscore >= 85:
        interpretation = "Excellent management systems (FMS < 0.7)"
    elif pscore >= 72:
        interpretation = "Good management systems (FMS ≈ 1.0)"
    elif pscore >= 60:
        interpretation = "Average management systems (FMS ≈ 1.2-1.4)"
    else:
        interpretation = "Poor management systems (FMS > 1.5)"
    
    return {
        'fms': fms,
        'pscore': pscore,
        'interpretation': interpretation,
        'breakdown': {key: weights[key] * audit_scores.get(key, 50) for key in weights}
    }

# Example audit questionnaire structure
AUDIT_QUESTIONS = {
    'management_inspection': [
        "Inspection program procedures documented",
        "Qualified inspection personnel",
        "Inspection history records maintained",
        # ... (12 questions total per API 581 Annex 2.A)
    ],
    'site_management': [
        "Management commitment to safety",
        "Safety culture assessment",
        # ... (6 questions)
    ],
    # ... other sections
}
```

---

### MODULE 3: INPUT VALIDATION

**File:** `input_validation.py`

```python
"""
Input validation and flag system
"""
from enum import Enum
from datetime import datetime

class InputFlag(Enum):
    MISSING = "MISSING"           # Blank, no default → module skipped
    BLOCKING = "BLOCKING"         # Required, no default → component not calculated
    DEFAULT_581 = "DEFAULT_581"   # API 581 default used
    ASSUMED = "ASSUMED"           # Conservative assumption
    LCI_OVERRIDE = "LCI_OVERRIDE" # LCI value replaced 581 example
    ENGINEER = "ENGINEER"         # Value entered by engineer

class ValidationResult:
    def __init__(self, value, flag=None, message="", source=""):
        self.value = value
        self.flag = flag
        self.message = message
        self.source = source
        self.timestamp = datetime.now()

def validate_input(
    field_name,
    value,
    required=False,
    default_581=None,
    assumed=None,
    data_type=None,
    value_range=None
):
    """
    Validate single input field
    
    Returns ValidationResult
    """
    # Check if value exists
    if value is None or value == "":
        if required:
            return ValidationResult(
                value=None,
                flag=InputFlag.BLOCKING,
                message=f"{field_name} is required but missing",
                source="input_validation"
            )
        elif default_581 is not None:
            return ValidationResult(
                value=default_581,
                flag=InputFlag.DEFAULT_581,
                message=f"{field_name} using API 581 default: {default_581}",
                source="API 581"
            )
        elif assumed is not None:
            return ValidationResult(
                value=assumed,
                flag=InputFlag.ASSUMED,
                message=f"{field_name} assumed (conservative): {assumed}",
                source="engine_assumption"
            )
        else:
            return ValidationResult(
                value=None,
                flag=InputFlag.MISSING,
                message=f"{field_name} is missing, no default available",
                source="input_validation"
            )
    
    # Type validation
    if data_type and not isinstance(value, data_type):
        try:
            value = data_type(value)
        except:
            return ValidationResult(
                value=None,
                flag=InputFlag.BLOCKING,
                message=f"{field_name} has invalid type, expected {data_type.__name__}",
                source="input_validation"
            )
    
    # Range validation
    if value_range:
        min_val, max_val = value_range
        if not (min_val <= value <= max_val):
            return ValidationResult(
                value=None,
                flag=InputFlag.BLOCKING,
                message=f"{field_name} out of range [{min_val}, {max_val}]: {value}",
                source="input_validation"
            )
    
    # Valid input
    return ValidationResult(
        value=value,
        flag=None,
        message="",
        source="user_input"
    )

class ComponentValidator:
    """
    Validate complete component input
    """
    def __init__(self):
        self.flags = []
        self.blocking_flags = []
    
    def validate_component(self, component_data):
        """
        Validate all required fields for RBI assessment
        
        Returns:
            {
                'valid': bool,
                'validated_data': dict,
                'flags': list of ValidationResult,
                'blocking': list of blocking flags
            }
        """
        validated = {}
        
        # Critical fields
        result = validate_input(
            'equipment_id',
            component_data.get('equipment_id'),
            required=True
        )
        validated['equipment_id'] = result.value
        if result.flag == InputFlag.BLOCKING:
            self.blocking_flags.append(result)
        
        result = validate_input(
            'component_type',
            component_data.get('component_type'),
            required=True
        )
        validated['component_type'] = result.value
        if result.flag == InputFlag.BLOCKING:
            self.blocking_flags.append(result)
        
        # Operating conditions
        result = validate_input(
            'operating_pressure',
            component_data.get('operating_pressure_psig'),
            required=True,
            data_type=float,
            value_range=(0, 10000)
        )
        validated['operating_pressure_psig'] = result.value
        if result.flag:
            self.flags.append(result)
        
        # ... validate all 50+ fields from input dictionary
        
        return {
            'valid': len(self.blocking_flags) == 0,
            'validated_data': validated,
            'flags': self.flags,
            'blocking': self.blocking_flags
        }
```

---

## INTEGRATION PLAN

### Step 1: Implement Code Calc (Day 1)
```bash
mkdir codecalc
# Create all 6 files above
python -m pytest tests/test_codecalc.py
```

### Step 2: Implement FMS (Day 1 afternoon)
```bash
# Create fms_audit.py
python -m pytest tests/test_fms.py
```

### Step 3: Implement Validation (Day 2 morning)
```bash
# Create input_validation.py
python -m pytest tests/test_validation.py
```

### Step 4: Integrate into complete_rbi_simplified.py (Day 2 afternoon)
```python
# Update complete_rbi_simplified.py
from codecalc import calculate_tmin, calculate_corrosion_rate, calculate_next_inspection_date
from fms_audit import calculate_fms
from input_validation import ComponentValidator

# Add to calculation workflow
validator = ComponentValidator()
validation_result = validator.validate_component(component_data)

if not validation_result['valid']:
    return {'error': 'Blocking validation errors', 'flags': validation_result['blocking']}

# Calculate code requirements
tmin = calculate_tmin(...)
CR = calculate_corrosion_rate(thickness_history)
RL = calculate_remaining_life(...)
code_interval = calculate_code_interval(...)

# Calculate FMS
fms_result = calculate_fms(audit_scores)
fms = fms_result['fms']

# Use in POF
pof = gff * df_total * fms

# Final next date
next_date_result = calculate_next_inspection_date(
    assessment_date,
    rbi_target_date,
    code_interval,
    regulatory_interval
)
```

---

## TESTING PLAN

### Test Cases Required:

**Code Calc:**
- [ ] tmin piping: NPS 6, 300 psig, CS A106B
- [ ] tmin vessel: 48" ID, 150 psig, SA-516-70
- [ ] CR: 3 thickness readings over 10 years
- [ ] RL: t_actual=0.300", tmin=0.250", CR=5 mpy → RL=10 yr
- [ ] Code interval: RL=10 yr, Class 1 → interval=5 yr

**FMS:**
- [ ] pscore=72 → FMS ≈ 1.0
- [ ] pscore=85 → FMS ≈ 0.65
- [ ] pscore=50 → FMS ≈ 1.5

**Validation:**
- [ ] Missing required field → BLOCKING
- [ ] Missing optional with default → DEFAULT_581
- [ ] Out of range value → BLOCKING

---

## DELIVERABLES CHECKLIST

- [ ] `codecalc/tmin_calculator.py` (200 lines)
- [ ] `codecalc/corrosion_rate.py` (100 lines)
- [ ] `codecalc/code_interval.py` (100 lines)
- [ ] `codecalc/next_date.py` (100 lines)
- [ ] `fms_audit.py` (150 lines)
- [ ] `input_validation.py` (200 lines)
- [ ] `tests/test_codecalc.py` (200 lines)
- [ ] `tests/test_fms.py` (50 lines)
- [ ] `tests/test_validation.py` (100 lines)
- [ ] Update `complete_rbi_simplified.py` (50 lines changed)
- [ ] Documentation update

**Total:** ~1,250 new lines + integration

**Estimated Time:** 2 days
**Priority:** CRITICAL - Must do before production

---

**Status:** Ready to implement
**Next Action:** Start with `codecalc/tmin_calculator.py`
