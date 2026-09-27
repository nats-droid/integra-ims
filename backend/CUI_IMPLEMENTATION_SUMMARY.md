# CUI (Corrosion Under Insulation) Implementation Summary

## ✅ Implementation Complete

**Date:** 2026-09-26
**Module:** `cui_df.py`
**Examples:** `example_cui.py`

---

## 📋 What Was Implemented

### Module: `cui_df.py` (15.9 KB)

Complete 18-step CUI damage factor calculation per API 581 Section 2.D.3:

1. ✅ Furnished thickness and age determination
2. ✅ Assigned rate check (skip to Step 5 if provided)
3. ✅ Base corrosion rate from Table 2.D.3.2 (driver + temperature)
4. ✅ **CUI-specific adjustments** (Equation 2.D.14):
   - F_INS: Insulation type factor
   - F_CM: Complexity factor
   - F_IC: Insulation condition factor
   - F_EQ: Equipment design (water pooling)
   - F_IF: Soil/water interface
5. ✅ Inspection time calculation
6. ✅ Coating installation time
7. ✅ Expected coating life
8. ✅ Coating adjustment calculation
9. ✅ Effective age determination
10. ✅ Minimum required thickness (tmin)
11. ✅ Art parameter calculation
12. ✅ Flow stress (FSCUIF)
13. ✅ Strength ratio parameter (SRpCUIF)
14. ✅ Inspection counts (A/B/C/D levels)
15. ✅ Inspection effectiveness factors (Bayesian)
16. ✅ Posterior probabilities
17. ✅ Beta reliability parameters
18. ✅ Final CUI damage factor

---

## 🔑 Key Features

### CUI-Specific Factors

**Insulation Type Factors (Table 2.D.3.3):**
- Foam: 0.5x (low water retention)
- Cellular Glass: 0.75x
- Mineral Wool: 1.5x (high water retention)
- Calcium Silicate: 2.0x (highest retention)

**Complexity Factors:**
- Below Average: 0.75x (simple piping)
- Average: 1.0x
- Above Average: 1.25x (many penetrations, complex geometry)

**Insulation Condition:**
- Above Average: 0.75x (well-maintained)
- Average: 1.0x
- Below Average: 1.25x (damaged jacketing, missing bands)

**Design Factors:**
- Water Pooling: 2.0x penalty
- Soil/Water Interface: 2.0x penalty

### Temperature Ranges

CUI most aggressive in **50-100°C (77-110°C)** range:
- Severe driver: 0.75 mm/year peak
- Moderate: 0.40 mm/year peak
- Mild: 0.20 mm/year peak
- Dry: 0.08 mm/year peak

---

## 🧪 Test Results

### Example 1: Severe CUI - Mineral Wool, Poor Condition
- **DF:** 6,370.5 ⚠️ CRITICAL
- **Rate:** 3.52 mm/year
- **Factors:** Mineral wool (1.5x) + Poor condition (1.25x) + High complexity (1.25x) + Water pooling (2.0x)
- **Scenario:** Coastal refinery, 95°C operating temp, no coating

### Example 2: Mild CUI - Cellular Glass + Good Coating
- **DF:** 0.02 ✅ LOW
- **Rate:** 0.055 mm/year
- **Factors:** Cellular glass (0.75x) + Good condition (0.75x) + Low complexity (0.75x) + Good coating (15-year life)
- **Scenario:** Dry climate, 120°C, high-quality coating

### Example 3: Calcium Silicate - Failed Coating
- **DF:** 6,384.5 ⚠️ CRITICAL
- **Rate:** 2.00 mm/year
- **Factors:** Calcium silicate (2.0x) + Poor condition (1.25x) + Water pooling (2.0x) + Failed coating
- **Scenario:** Temperature cycling through dew point, 20 years old

### Example 4: User-Assigned Rate
- **DF:** 901.4
- **Rate:** 1.20 mm/year (site-specific monitoring data)
- **Scenario:** Bypasses table lookup, uses direct corrosion rate from field measurements

---

## 🔄 Calculation Flow

```
START
  ↓
[1] Get thickness, age
  ↓
[2] Assigned rate? → YES → Skip to [5]
  ↓ NO
[3] Base rate from table (driver + temp)
  ↓
[4] Apply CUI adjustments: Cr = CrB × F_INS × F_CM × F_IC × max(F_EQ, F_IF)
  ↓
[5-9] Coating effectiveness & age calculation
  ↓
[10-13] Structural analysis (Art, Flow Stress, Strength Ratio)
  ↓
[14-16] Bayesian inspection update
  ↓
[17-18] Beta parameters → Final DF
  ↓
END
```

---

## 📊 Comparison: CUI vs External Corrosion

| Aspect | External Corrosion | CUI |
|--------|-------------------|-----|
| **Base Rate Source** | Table 2.D.2.2 | Table 2.D.3.2 |
| **Peak Temperature** | 50-100°C | 50-100°C (same) |
| **Insulation Factor** | ❌ No | ✅ F_INS (0.5-2.0x) |
| **Complexity Factor** | ❌ No | ✅ F_CM (0.75-1.25x) |
| **Condition Factor** | ❌ No | ✅ F_IC (0.75-1.25x) |
| **Coating Logic** | Same (age-based) | Same (age-based) |
| **Structural Analysis** | Same (Art, SRp, Beta) | Same (Art, SRp, Beta) |

**Key Difference:** CUI adds 3 multipliers (F_INS, F_CM, F_IC) to account for insulation-specific factors.

---

## 💾 Files Created

1. **`cui_df.py`** (15.9 KB)
   - `CUIData` dataclass
   - `CUIDFCalculator` class
   - 18-step calculation procedure
   - All tables and equations

2. **`example_cui.py`** (9.7 KB)
   - 4 validation examples
   - Different scenarios (severe/mild/failed coating/assigned rate)
   - Summary comparison table

3. **`CUI_IMPLEMENTATION_SUMMARY.md`** (this file)

---

## 🎯 Next Damage Mechanism

**Recommended:** Caustic SCC (Section 2.C.4)
- Common in refining units
- Well-documented screening criteria
- Similar structural reliability framework

---

## 📚 References

- API 581 4th Edition (2025), Section 2.D.3
- Table 2.D.3.2: CUI Corrosion Rates
- Table 2.D.3.3: Insulation Type Factors
- Equation 2.D.14: Final corrosion rate calculation
- Part 2, Table 4.5: Prior probabilities
- Part 2, Table 4.6: Conditional probabilities

---

**Status:** ✅ Complete and tested
**Progress:** 3/20 damage mechanisms (15%)
