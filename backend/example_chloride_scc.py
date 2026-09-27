"""
Example usage of Chloride SCC (Stress Corrosion Cracking) DF Calculator
"""

from chloride_scc_df import ChlorideSCCData, calculate_chloride_scc_df


def example1_high_susceptibility():
    """
    Example 1: High Susceptibility - High Temp + Low pH + High Cl
    - 180°F (82°C) operating temperature
    - pH 4.0 (acidic)
    - 500 ppm Cl- (high concentration)
    - Austenitic stainless steel (304/316)
    """
    print("=" * 80)
    print("Example 1: High Susceptibility - High Temp + Low pH + High Cl")
    print("=" * 80)
    
    scc_data = ChlorideSCCData(
        material='300_series_ss',
        cl_concentration=500.0,  # ppm (high)
        operating_temp=82.0,  # °C (180°F)
        ph=4.0,  # acidic
        oxygen_ppb=300.0,
        has_deposits=True,  # Scale/deposits present
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
    
    print(f"\n📊 RESULTS:")
    print(f"   Chloride SCC DF: {result['df_chloride_scc']:.1f}")
    print(f"   Susceptibility: {result['susceptibility'].upper()}")
    print(f"   Severity Index: {result['severity_index']}")
    print(f"   Base DF: {result['base_df']}")
    print(f"   Age Since Inspection: {result['age_since_inspection']:.1f} years")
    
    if result['df_chloride_scc'] >= 5000:
        print(f"   ⚠️  CRITICAL: Maximum DF reached (capped at 5000)")
    elif result['df_chloride_scc'] > 1000:
        print(f"   ⚠️  VERY HIGH: Immediate inspection required!")
    
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
    
    scc_data = ChlorideSCCData(
        material='300_series_ss',
        cl_concentration=150.0,  # ppm
        operating_temp=71.0,  # °C (160°F)
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
    
    print(f"\n📊 RESULTS:")
    print(f"   Chloride SCC DF: {result['df_chloride_scc']:.2f}")
    print(f"   Susceptibility: {result['susceptibility'].upper()}")
    print(f"   Severity Index: {result['severity_index']}")
    print(f"   Base DF: {result['base_df']}")
    print(f"   Age Since Inspection: {result['age_since_inspection']:.1f} years")
    print(f"   Highest Inspection: Level {result['highest_inspection']}")
    
    if result['df_chloride_scc'] < 50:
        print(f"   ✅ LOW: Good inspection program effectiveness")
    
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
    
    scc_data = ChlorideSCCData(
        material='300_series_ss',
        cl_concentration=5.0,  # ppm (< 10 = modifier -1)
        operating_temp=65.0,  # °C (149°F)
        ph=7.0,  # neutral
        oxygen_ppb=50.0,  # < 90 ppb = modifier -1
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
    
    print(f"\n📊 RESULTS:")
    print(f"   Chloride SCC DF: {result['df_chloride_scc']:.2f}")
    print(f"   Susceptibility: {result['susceptibility'].upper()}")
    print(f"   Severity Index: {result['severity_index']}")
    print(f"   Base DF: {result['base_df']}")
    print(f"   Age Since Inspection: {result['age_since_inspection']:.1f} years")
    
    print(f"   ✅ LOW RISK: Low Cl + Low O2 modifiers reduce susceptibility")
    
    return result


def example4_not_susceptible_high_ph():
    """
    Example 4: Not Susceptible - High pH (Caustic)
    - pH > 10.5 → caustic cracking, not ClSCC
    """
    print("\n" + "=" * 80)
    print("Example 4: Not Susceptible - High pH > 10.5 (Caustic Regime)")
    print("=" * 80)
    
    scc_data = ChlorideSCCData(
        material='300_series_ss',
        cl_concentration=200.0,  # ppm
        operating_temp=90.0,  # °C (194°F)
        ph=11.0,  # alkaline (> 10.5)
        oxygen_ppb=300.0,
        has_deposits=False,
        cracks_present=False,
        cracks_removed=False,
        age_since_inspection=8.0,
        num_inspections_A=0,
        num_inspections_B=0,
        num_inspections_C=0,
        num_inspections_D=0,
        num_inspections_E=0
    )
    
    result = calculate_chloride_scc_df(scc_data)
    
    print(f"\n📊 RESULTS:")
    print(f"   Chloride SCC DF: {result['df_chloride_scc']:.1f}")
    print(f"   Susceptibility: {result['susceptibility'].upper()}")
    print(f"   Severity Index: {result['severity_index']}")
    print(f"   Base DF: {result['base_df']}")
    
    if result['susceptibility'] == 'none':
        print(f"   ⚠️  NOTE: pH > 10.5 → Check for caustic cracking instead!")
    
    return result


def example5_not_susceptible_low_ph():
    """
    Example 5: Not Susceptible - Low pH < 2.5
    - pH < 2.5 → pitting/HCl corrosion, not ClSCC
    """
    print("\n" + "=" * 80)
    print("Example 5: Not Susceptible - Low pH < 2.5 (Pitting Corrosion)")
    print("=" * 80)
    
    scc_data = ChlorideSCCData(
        material='300_series_ss',
        cl_concentration=300.0,  # ppm
        operating_temp=75.0,  # °C (167°F)
        ph=2.0,  # very acidic (< 2.5)
        oxygen_ppb=400.0,
        has_deposits=False,
        cracks_present=False,
        cracks_removed=False,
        age_since_inspection=6.0,
        num_inspections_A=0,
        num_inspections_B=0,
        num_inspections_C=0,
        num_inspections_D=0,
        num_inspections_E=0
    )
    
    result = calculate_chloride_scc_df(scc_data)
    
    print(f"\n📊 RESULTS:")
    print(f"   Chloride SCC DF: {result['df_chloride_scc']:.1f}")
    print(f"   Susceptibility: {result['susceptibility'].upper()}")
    print(f"   Severity Index: {result['severity_index']}")
    print(f"   Base DF: {result['base_df']}")
    
    if result['susceptibility'] == 'none':
        print(f"   ⚠️  NOTE: pH < 2.5 → Check for HCl corrosion/pitting instead!")
    
    return result


def example6_cracks_detected():
    """
    Example 6: Cracks Detected - Automatic High Susceptibility
    """
    print("\n" + "=" * 80)
    print("Example 6: High Susceptibility - Cracks Detected During Inspection")
    print("=" * 80)
    
    scc_data = ChlorideSCCData(
        material='300_series_ss',
        cl_concentration=80.0,  # ppm
        operating_temp=70.0,  # °C
        ph=6.0,
        oxygen_ppb=150.0,
        has_deposits=False,
        cracks_present=True,  # Cracks found!
        cracks_removed=False,
        age_since_inspection=0.5,  # Recent inspection
        num_inspections_A=1,
        num_inspections_B=0,
        num_inspections_C=0,
        num_inspections_D=0,
        num_inspections_E=0
    )
    
    result = calculate_chloride_scc_df(scc_data)
    
    print(f"\n📊 RESULTS:")
    print(f"   Chloride SCC DF: {result['df_chloride_scc']:.1f}")
    print(f"   Susceptibility: {result['susceptibility'].upper()}")
    print(f"   Severity Index: {result['severity_index']}")
    print(f"   Base DF: {result['base_df']}")
    print(f"   Age Since Inspection: {result['age_since_inspection']:.1f} years")
    
    print(f"   ⚠️  CRACKS DETECTED: Requires FFS evaluation!")
    
    return result


if __name__ == '__main__':
    print("\n🔧 Chloride SCC (Stress Corrosion Cracking) Damage Factor Examples")
    print("API 581 Section 2.C.5\n")
    
    # Run all examples
    result1 = example1_high_susceptibility()
    result2 = example2_medium_with_inspections()
    result3 = example3_low_chloride()
    result4 = example4_not_susceptible_high_ph()
    result5 = example5_not_susceptible_low_ph()
    result6 = example6_cracks_detected()
    
    # Summary
    print("\n" + "=" * 80)
    print("📋 SUMMARY COMPARISON")
    print("=" * 80)
    print(f"{'Scenario':<50} {'Suscept':>12} {'DF':>10}")
    print("-" * 80)
    print(f"{'1. High Temp + Low pH + High Cl':<50} {result1['susceptibility']:>12} {result1['df_chloride_scc']:>10.1f}")
    print(f"{'2. Medium with Good Inspections':<50} {result2['susceptibility']:>12} {result2['df_chloride_scc']:>10.2f}")
    print(f"{'3. Low Cl + Low O2 (Modifiers)':<50} {result3['susceptibility']:>12} {result3['df_chloride_scc']:>10.2f}")
    print(f"{'4. High pH > 10.5 (Not Susceptible)':<50} {result4['susceptibility']:>12} {result4['df_chloride_scc']:>10.1f}")
    print(f"{'5. Low pH < 2.5 (Not Susceptible)':<50} {result5['susceptibility']:>12} {result5['df_chloride_scc']:>10.1f}")
    print(f"{'6. Cracks Detected (Auto High)':<50} {result6['susceptibility']:>12} {result6['df_chloride_scc']:>10.1f}")
    print("=" * 80)
    
    print("\n📌 KEY INSIGHTS:")
    print("   • ClSCC occurs in austenitic stainless steel (300-series)")
    print("   • Susceptible range: 75-345°F (24-174°C), pH 2.5-10.5")
    print("   • Most susceptible: High temp + Low pH + High Cl + Deposits")
    print("   • pH < 2.5 → pitting/HCl corrosion (not ClSCC)")
    print("   • pH > 10.5 → caustic cracking (not ClSCC)")
    print("   • Modifiers from Table 2.C.5.3:")
    print("       - Cl < 10 ppm: -1 (reduces susceptibility)")
    print("       - O2 < 90 ppb: -1 (reduces susceptibility)")
    print("       - Cl > 100 ppm: +1 (increases susceptibility)")
    print("       - Deposits: +1 (increases susceptibility)")
    print("   • Wetting/drying cycles can concentrate Cl- locally")
    print("   • Duplex SS and high-Ni alloys more resistant")
    print("   • Common sources: crude salts, process water, cooling tower drift")
