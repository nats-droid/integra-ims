# API 581 RBI Calculator - Quick Start Guide

## 🚀 Cara Cepat Menggunakan

### 1. Test Complete RBI System

```bash
cd /tmp/rbi-581-calculator
python3 complete_rbi_simplified.py
```

**Output:**
- 3 contoh lengkap (High/Medium/Low risk)
- Risk Matrix position (5×5)
- Inspection recommendations
- JSON export ke `complete_rbi_examples.json`

---

### 2. Test Individual Mechanisms

#### Thinning
```bash
python3 example_usage.py
```

#### External Corrosion
```bash
python3 example_external_detailed.py
```

#### CUI
```bash
python3 example_cui.py
```

#### SCC (Chloride)
```bash
python3 example_chloride_scc_detailed.py
```

#### HIC/SOHIC
```bash
python3 example_hic_sohic.py
```

---

### 3. Import dan Gunakan di Python

```python
from complete_rbi_simplified import CompleteRBICalculator

# Setup component
component = {
    'component_id': 'P-101',
    'component_type': 'pipe',  # pipe, vessel, heat_exchanger, tank
    'operating_pressure_psig': 500.0,
    'operating_temp_f': 450.0,
    'diameter_inches': 16.0,
    'fluid_type': 'hydrocarbon',
    'fms': 1.0  # Management Systems Factor
}

# Setup damage factors (dari individual calculators)
damage_factors = {
    'thinning': 450.0,
    'external_corrosion': 120.0,
    'cui': 85.0,
    'chloride_scc': 280.0,
    'hic_sohic_h2s': 350.0
}

# Calculate complete RBI
calculator = CompleteRBICalculator()
result = calculator.calculate_complete_rbi(component, damage_factors)

# Access results
print(f"Risk Position: {result['risk_matrix_position']}")  # e.g., "5D"
print(f"Risk Level: {result['risk']['risk_level']}")       # e.g., "High"
print(f"PoF: {result['pof']['pof_per_year']:.6e} /year")
print(f"CoF: ${result['cof']['cof_financial']:,.0f}")
print(f"Inspection: {result['inspection_recommendation']['interval_years']} years")
```

---

## 📊 Risk Matrix Reference

```
     CoF →
PoF  A        B        C        D        E
↓    (Low)                          (High)

5    5A       5B       5C       5D       5E
     (CRITICAL - Inspect in 2 years, Level A)

4    4A       4B       4C
     (HIGH - Inspect in 2-4 years)

3    3A       3B       3C
     (MEDIUM-HIGH - Inspect in 4 years, Level B)

2    2A       2B       2C
     (MEDIUM - Inspect in 8 years, Level C)

1    1
     (LOW - Inspect in 16 years, Level D)
```

### PoF Categories
| Category | Range (failures/year) |
|----------|-----------------------|
| 1 | < 1×10⁻⁶ |
| 2 | 1×10⁻⁶ to 1×10⁻⁵ |
| 3 | 1×10⁻⁵ to 1×10⁻⁴ |
| 4 | 1×10⁻⁴ to 1×10⁻³ |
| 5 | > 1×10⁻³ |

### CoF Categories
| Category | Range ($) |
|----------|-----------|
| A | < $10,000 |
| B | $10,000 to $100,000 |
| C | $100,000 to $1M |
| D | $1M to $10M |
| E | > $10M |

---

## 🔧 All 20 Damage Mechanisms

### Group 1: Corrosion (3)
1. **Thinning** - `thinning_df.py`
2. **External Corrosion** - `external_corrosion_df.py`
3. **CUI** - `cui_df.py`

### Group 2: SCC (9)
4. **Caustic SCC** - `caustic_scc_df.py`
5. **Amine SCC** - `amine_scc_df.py`
6. **Chloride SCC** - `chloride_scc_df.py`
7. **SSC** - `ssc_df.py`
8. **HIC/SOHIC-H2S** - `hic_sohic_df.py`
9. **HIC/SOHIC-HF** - `hic_sohic_hf_df.py`
10-13. **Generic SCC** (4 types) - `generic_scc_df.py`

### Group 3: High-Temp (1)
14. **HTHA** - `htha_df.py`

### Group 4: Low-Temp (1)
15. **Brittle Fracture** - `brittle_fracture_df.py`

### Group 5: Embrittlement (3)
16. **Sigma Phase** - `embrittlement_df.py`
17. **Temper Embrittlement** - `embrittlement_df.py`
18. **885°F Embrittlement** - `embrittlement_df.py`

### Group 6: Fatigue & Lining (3)
19. **Mechanical Fatigue** - `fatigue_lining_df.py`
20. **Lining/Refractory** - `fatigue_lining_df.py`

---

## 📚 Documentation Files

| File | Description |
|------|-------------|
| **FINAL_REPORT.md** | Complete implementation report with statistics |
| **DAMAGE_MECHANISMS_GUIDE.md** | Technical guide for all 20 mechanisms |
| **COMPLETE_IMPLEMENTATION.md** | Implementation summary and next steps |
| **QUICK_START.md** | This file - quick reference |
| **README.md** | Project overview |

---

## 🎯 Common Use Cases

### Use Case 1: Sour Service Pipe
```python
# High H2S, high pressure hydrocarbon pipe
component = {
    'component_id': 'P-201-Sour',
    'component_type': 'pipe',
    'operating_pressure_psig': 1000.0,
    'operating_temp_f': 350.0,
    'diameter_inches': 20.0,
    'fluid_type': 'hydrocarbon'
}

damage_factors = {
    'thinning': 300.0,
    'ssc': 800.0,           # High hardness steel in H2S
    'hic_sohic_h2s': 450.0  # High sulfur content plate
}
```

### Use Case 2: CUI-Prone Equipment
```python
# Insulated pipe in coastal area
component = {
    'component_id': 'P-301-CUI',
    'component_type': 'pipe',
    'operating_pressure_psig': 300.0,
    'operating_temp_f': 150.0,  # Peak CUI temperature
    'diameter_inches': 12.0
}

damage_factors = {
    'cui': 1200.0,              # Calcium silicate, poor condition
    'external_corrosion': 250.0  # Marine environment
}
```

### Use Case 3: Stainless Steel Chloride Exposure
```python
# 304 SS in chloride service
component = {
    'component_id': 'V-401-SS',
    'component_type': 'vessel',
    'operating_pressure_psig': 200.0,
    'operating_temp_f': 180.0,  # Above 140°F threshold
    'diameter_inches': 48.0
}

damage_factors = {
    'chloride_scc': 950.0  # High Cl, neutral pH, elevated temp
}
```

---

## 📞 Next Steps

1. ✅ **Calculation Engine** - COMPLETE (20/20 mechanisms)
2. 🔄 **Database Schema** - Design ready, implement next
3. 🔄 **FastAPI Endpoints** - Start with top 5 mechanisms
4. 🔄 **React UI** - Equipment list + assessment forms

---

**Version:** 1.0  
**Date:** September 27, 2026  
**Status:** ✅ Production Ready
