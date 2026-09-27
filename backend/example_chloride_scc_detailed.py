"""
Example usage of Chloride SCC (Stress Corrosion Cracking) DF Calculator
WITH DETAILED STEP-BY-STEP CALCULATIONS
"""

from chloride_scc_df import ChlorideSCCData, calculate_chloride_scc_df


def print_detailed_steps(result):
    """Print detailed step-by-step calculation"""
    print(f"\n{'='*80}")
    print(f"📋 DETAILED STEP-BY-STEP CALCULATION")
    print(f"{'='*80}")
    
    for step_name, step_data in result['all_steps']:
        print(f"\n{step_name}:")
        print("-" * 80)
        for key, value in step_data.items():
            if isinstance(value, list):
                print(f"   {key}:")
                for item in value:
                    print(f"      - {item}")
            elif isinstance(value, dict):
                print(f"   {key}:")
                for k, v in value.items():
                    print(f"      {k}: {v}")
            elif isinstance(value, (int, float)):
                if isinstance(value, float):
                    print(f"   {key}: {value:.4f}")
                else:
                    print(f"   {key}: {value}")
            else:
                print(f"   {key}: {value}")
    
    print(f"\n{'='*80}")
    print(f"📊 FINAL RESULTS")
    print(f"{'='*80}")
    print(f"   Chloride SCC DF: {result['df_chloride_scc']:.2f}")
    print(f"   Susceptibility: {result['susceptibility'].upper()}")
    print(f"   Severity Index: {result['severity_index']}")
    print(f"   Base DF: {result['base_df']}")
    print(f"   Age Since Inspection: {result['age_since_inspection']:.1f} years")
    if 'highest_inspection' in result:
        print(f"   Highest Inspection: Level {result['highest_inspection']}")
    print(f"{'='*80}")


def example1_high_susceptibility():
    """
    Example 1: High Susceptibility - High Temp + Low pH + High Cl
    - 180°F (82°C) operating temperature
    - pH 4.0 (acidic)
    - 500 ppm Cl- (high concentration)
    - Austenitic stainless steel (304/316)
    """
    print("\n" + "=" * 80)
    print("Example 1: High Susceptibility - High Temp + Low pH + High Cl")
    print("=" * 80)
    
    print("\n📥 INPUT DATA:")
    print(f"   Material: 300-series stainless steel")
    print(f"   Cl⁻ Concentration: 500 ppm (HIGH)")
    print(f"   Operating Temperature: 82°C (180°F)")
    print(f"   pH: 4.0 (acidic)")
    print(f"   O₂: 300 ppb")
    print(f"   Deposits: Yes")
    print(f"   Age Since Inspection: 10 years")
    print(f"   Inspections: None")
    
    scc_data = ChlorideSCCData(
        material='300_series_ss',
        cl_concentration=500.0,
        operating_temp=82.0,
        ph=4.0,
        oxygen_ppb=300.0,
        has_deposits=True,
        cracks_present=False,
        cracks_removed=False,
        age_since_inspection=10.0,
        num_inspections_A=0,
        num_inspections_B=0,
        num_inspections_C=0,
        num_inspections_D=0,
        num_inspections_E=0
    )
    
    result = calculate_chloride_scc_df(scc_data)
    print_detailed_steps(result)
    
    if result['df_chloride_scc'] >= 5000:
        print(f"\n⚠️  CRITICAL: Maximum DF reached (capped at 5000)")
    elif result['df_chloride_scc'] > 1000:
        print(f"\n⚠️  VERY HIGH: Immediate inspection required!")
    
    return result


def example2_medium_with_inspections():
    """
    Example 2: Medium Susceptibility with Good Inspections
    - 160°F (71°C) moderate temperature
    - pH 6.5 (slightly acidic)
    - 150 ppm Cl-
    - Good inspection history
    """
    print("\n" + "=" * 80)
    print("Example 2: Medium Susceptibility with Good Inspection Program")
    print("=" * 80)
    
    print("\n📥 INPUT DATA:")
    print(f"   Material: 300-series stainless steel")
    print(f"   Cl⁻ Concentration: 150 ppm")
    print(f"   Operating Temperature: 71°C (160°F)")
    print(f"   pH: 6.5 (slightly acidic)")
    print(f"   O₂: 200 ppb")
    print(f"   Deposits: No")
    print(f"   Age Since Inspection: 3 years")
    print(f"   Inspections: 2× Level A, 1× Level B")
    
    scc_data = ChlorideSCCData(
        material='300_series_ss',
        cl_concentration=150.0,
        operating_temp=71.0,
        ph=6.5,
        oxygen_ppb=200.0,
        has_deposits=False,
        cracks_present=False,
        cracks_removed=False,
        age_since_inspection=3.0,
        num_inspections_A=2,
        num_inspections_B=1,
        num_inspections_C=0,
        num_inspections_D=0,
        num_inspections_E=0
    )
    
    result = calculate_chloride_scc_df(scc_data)
    print_detailed_steps(result)
    
    if result['df_chloride_scc'] < 50:
        print(f"\n✅ LOW: Good inspection program effectiveness")
    
    return result


def example3_low_chloride():
    """
    Example 3: Low Susceptibility - Low Cl + Low O2
    - Moderate temperature
    - Low chloride concentration (< 10 ppm)
    - Low oxygen (< 90 ppb)
    - Modifiers reduce susceptibility
    """
    print("\n" + "=" * 80)
    print("Example 3: Low Susceptibility - Low Cl + Low O2 (Modifiers Applied)")
    print("=" * 80)
    
    print("\n📥 INPUT DATA:")
    print(f"   Material: 300-series stainless steel")
    print(f"   Cl⁻ Concentration: 5 ppm (< 10 ppm = modifier -1)")
    print(f"   Operating Temperature: 65°C (149°F)")
    print(f"   pH: 7.0 (neutral)")
    print(f"   O₂: 50 ppb (< 90 ppb = modifier -1)")
    print(f"   Deposits: No")
    print(f"   Age Since Inspection: 5 years")
    print(f"   Inspections: 1× Level B, 2× Level C")
    
    scc_data = ChlorideSCCData(
        material='300_series_ss',
        cl_concentration=5.0,
        operating_temp=65.0,
        ph=7.0,
        oxygen_ppb=50.0,
        has_deposits=False,
        cracks_present=False,
        cracks_removed=False,
        age_since_inspection=5.0,
        num_inspections_A=0,
        num_inspections_B=1,
        num_inspections_C=2,
        num_inspections_D=0,
        num_inspections_E=0
    )
    
    result = calculate_chloride_scc_df(scc_data)
    print_detailed_steps(result)
    
    print(f"\n✅ LOW RISK: Low Cl + Low O2 modifiers reduce susceptibility")
    
    return result


if __name__ == '__main__':
    print("\n🔧 Chloride SCC (Stress Corrosion Cracking) Damage Factor Calculator")
    print("API 581 Section 2.C.5")
    print("WITH DETAILED STEP-BY-STEP CALCULATIONS\n")
    
    # Run examples with detailed output
    result1 = example1_high_susceptibility()
    result2 = example2_medium_with_inspections()
    result3 = example3_low_chloride()
    
    # Summary comparison
    print("\n" + "=" * 80)
    print("📋 SUMMARY COMPARISON")
    print("=" * 80)
    print(f"{'Scenario':<50} {'Suscept':>12} {'DF':>10}")
    print("-" * 80)
    print(f"{'1. High Temp + Low pH + High Cl':<50} {result1['susceptibility']:>12} {result1['df_chloride_scc']:>10.2f}")
    print(f"{'2. Medium with Good Inspections':<50} {result2['susceptibility']:>12} {result2['df_chloride_scc']:>10.2f}")
    print(f"{'3. Low Cl + Low O2 (Modifiers)':<50} {result3['susceptibility']:>12} {result3['df_chloride_scc']:>10.2f}")
    print("=" * 80)
    
    print("\n📌 KEY INSIGHTS:")
    print("   • ClSCC occurs in austenitic stainless steel (300-series)")
    print("   • Susceptible range: 75-345°F (24-174°C), pH 2.5-10.5")
    print("   • Most susceptible: High temp + Low pH + High Cl + Deposits")
    print("   • Modifiers from Table 2.C.5.3:")
    print("       - Cl < 10 ppm: -1 (reduces susceptibility)")
    print("       - O2 < 90 ppb: -1 (reduces susceptibility)")
    print("       - Cl > 100 ppm: +1 (increases susceptibility)")
    print("       - Deposits: +1 (increases susceptibility)")
