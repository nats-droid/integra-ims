"""
Example usage of Amine SCC (Stress Corrosion Cracking) DF Calculator
"""

from amine_scc_df import AmineSCCData, calculate_amine_scc_df


def example1_mea_high_temp():
    """
    Example 1: High Susceptibility - MEA at High Temperature
    - MEA amine (most susceptible)
    - 200°F (93°C) operating temperature
    - Lean amine solution
    - No stress relief
    """
    print("=" * 80)
    print("Example 1: High Susceptibility - MEA at High Temperature")
    print("=" * 80)
    
    scc_data = AmineSCCData(
        material='carbon_steel',
        amine_type='MEA',
        amine_solution='lean',
        max_process_temp=93.0,  # °C (200°F)
        stress_relieved=False,
        heat_traced=False,
        steamed_out=False,
        cracks_present=False,
        cracks_removed=False,
        age_since_inspection=8.0,
        num_inspections_A=0,
        num_inspections_B=0,
        num_inspections_C=0,
        num_inspections_D=0,
        num_inspections_E=0
    )
    
    result = calculate_amine_scc_df(scc_data)
    
    print(f"\n📊 RESULTS:")
    print(f"   Amine SCC DF: {result['df_amine_scc']:.1f}")
    print(f"   Susceptibility: {result['susceptibility'].upper()}")
    print(f"   Severity Index: {result['severity_index']}")
    print(f"   Base DF: {result['base_df']}")
    print(f"   Age Since Inspection: {result['age_since_inspection']:.1f} years")
    
    if result['df_amine_scc'] >= 5000:
        print(f"   ⚠️  CRITICAL: Maximum DF reached (capped at 5000)")
    elif result['df_amine_scc'] > 1000:
        print(f"   ⚠️  VERY HIGH: Immediate inspection required!")
    
    return result


def example2_dipa_with_inspections():
    """
    Example 2: DIPA with Good Inspection Program
    - DIPA amine (high susceptibility like MEA)
    - 170°F (77°C) moderate temperature
    - Good A-level inspection history
    """
    print("\n" + "=" * 80)
    print("Example 2: DIPA with Good Inspection Program")
    print("=" * 80)
    
    scc_data = AmineSCCData(
        material='carbon_steel',
        amine_type='DIPA',
        amine_solution='lean',
        max_process_temp=77.0,  # °C (170°F)
        stress_relieved=False,
        heat_traced=False,
        steamed_out=False,
        cracks_present=False,
        cracks_removed=False,
        age_since_inspection=2.5,
        num_inspections_A=2,
        num_inspections_B=1,
        num_inspections_C=0,
        num_inspections_D=0,
        num_inspections_E=0
    )
    
    result = calculate_amine_scc_df(scc_data)
    
    print(f"\n📊 RESULTS:")
    print(f"   Amine SCC DF: {result['df_amine_scc']:.2f}")
    print(f"   Susceptibility: {result['susceptibility'].upper()}")
    print(f"   Severity Index: {result['severity_index']}")
    print(f"   Base DF: {result['base_df']}")
    print(f"   Age Since Inspection: {result['age_since_inspection']:.1f} years")
    print(f"   Highest Inspection: Level {result['highest_inspection']}")
    
    if result['df_amine_scc'] < 10:
        print(f"   ✅ LOW: Good inspection program effectiveness")
    
    return result


def example3_dea_medium():
    """
    Example 3: DEA - Medium Susceptibility
    - DEA amine (medium susceptibility)
    - 190°F (88°C) high temperature
    - Some inspection history
    """
    print("\n" + "=" * 80)
    print("Example 3: DEA - Medium Susceptibility at High Temperature")
    print("=" * 80)
    
    scc_data = AmineSCCData(
        material='carbon_steel',
        amine_type='DEA',
        amine_solution='lean',
        max_process_temp=88.0,  # °C (190°F)
        stress_relieved=False,
        heat_traced=False,
        steamed_out=False,
        cracks_present=False,
        cracks_removed=False,
        age_since_inspection=5.0,
        num_inspections_A=0,
        num_inspections_B=1,
        num_inspections_C=1,
        num_inspections_D=0,
        num_inspections_E=0
    )
    
    result = calculate_amine_scc_df(scc_data)
    
    print(f"\n📊 RESULTS:")
    print(f"   Amine SCC DF: {result['df_amine_scc']:.1f}")
    print(f"   Susceptibility: {result['susceptibility'].upper()}")
    print(f"   Severity Index: {result['severity_index']}")
    print(f"   Base DF: {result['base_df']}")
    print(f"   Age Since Inspection: {result['age_since_inspection']:.1f} years")
    print(f"   Highest Inspection: Level {result['highest_inspection']}")
    
    return result


def example4_mdea_low():
    """
    Example 4: MDEA - Low Susceptibility
    - MDEA amine (low susceptibility)
    - 190°F (88°C) high temperature
    - Steamed out (increases risk slightly)
    """
    print("\n" + "=" * 80)
    print("Example 4: MDEA - Low Susceptibility (Steamed Out)")
    print("=" * 80)
    
    scc_data = AmineSCCData(
        material='carbon_steel',
        amine_type='MDEA',
        amine_solution='lean',
        max_process_temp=88.0,  # °C (190°F)
        stress_relieved=False,
        heat_traced=False,
        steamed_out=True,  # Increases local temperature
        cracks_present=False,
        cracks_removed=False,
        age_since_inspection=6.0,
        num_inspections_A=0,
        num_inspections_B=0,
        num_inspections_C=2,
        num_inspections_D=0,
        num_inspections_E=0
    )
    
    result = calculate_amine_scc_df(scc_data)
    
    print(f"\n📊 RESULTS:")
    print(f"   Amine SCC DF: {result['df_amine_scc']:.2f}")
    print(f"   Susceptibility: {result['susceptibility'].upper()}")
    print(f"   Severity Index: {result['severity_index']}")
    print(f"   Base DF: {result['base_df']}")
    print(f"   Age Since Inspection: {result['age_since_inspection']:.1f} years")
    
    if result['susceptibility'] == 'low':
        print(f"   ✅ LOW RISK: MDEA has lower cracking tendency")
    
    return result


def example5_stress_relieved():
    """
    Example 5: Not Susceptible - PWHT Performed
    - MEA (would be high risk)
    - High temperature
    - BUT stress relieved = complete protection
    """
    print("\n" + "=" * 80)
    print("Example 5: Not Susceptible - PWHT (Stress Relief) Performed")
    print("=" * 80)
    
    scc_data = AmineSCCData(
        material='carbon_steel',
        amine_type='MEA',
        amine_solution='lean',
        max_process_temp=95.0,  # °C (203°F)
        stress_relieved=True,  # PWHT - key mitigation!
        heat_traced=False,
        steamed_out=False,
        cracks_present=False,
        cracks_removed=False,
        age_since_inspection=12.0,
        num_inspections_A=0,
        num_inspections_B=0,
        num_inspections_C=0,
        num_inspections_D=0,
        num_inspections_E=0
    )
    
    result = calculate_amine_scc_df(scc_data)
    
    print(f"\n📊 RESULTS:")
    print(f"   Amine SCC DF: {result['df_amine_scc']:.1f}")
    print(f"   Susceptibility: {result['susceptibility'].upper()}")
    print(f"   Severity Index: {result['severity_index']}")
    print(f"   Base DF: {result['base_df']}")
    
    if result['susceptibility'] == 'none':
        print(f"   ✅ NOT SUSCEPTIBLE: PWHT eliminates amine SCC risk")
    
    return result


def example6_rich_amine():
    """
    Example 6: Not Susceptible - Rich Amine Solution
    - Rich amine (not lean) = not susceptible
    - Other forms of cracking may apply (SSC, HIC)
    """
    print("\n" + "=" * 80)
    print("Example 6: Not Susceptible - Rich Amine Solution")
    print("=" * 80)
    
    scc_data = AmineSCCData(
        material='carbon_steel',
        amine_type='MEA',
        amine_solution='rich',  # Rich amine - different cracking mechanisms
        max_process_temp=80.0,  # °C
        stress_relieved=False,
        heat_traced=False,
        steamed_out=False,
        cracks_present=False,
        cracks_removed=False,
        age_since_inspection=5.0,
        num_inspections_A=0,
        num_inspections_B=0,
        num_inspections_C=0,
        num_inspections_D=0,
        num_inspections_E=0
    )
    
    result = calculate_amine_scc_df(scc_data)
    
    print(f"\n📊 RESULTS:")
    print(f"   Amine SCC DF: {result['df_amine_scc']:.1f}")
    print(f"   Susceptibility: {result['susceptibility'].upper()}")
    print(f"   Severity Index: {result['severity_index']}")
    print(f"   Base DF: {result['base_df']}")
    
    if result['susceptibility'] == 'none':
        print(f"   ⚠️  NOTE: Rich amine not susceptible to amine SCC")
        print(f"            But check for SSC/HIC/SOHIC in rich amine!")
    
    return result


if __name__ == '__main__':
    print("\n🔧 Amine SCC (Stress Corrosion Cracking) Damage Factor Examples")
    print("API 581 Section 2.C.3\n")
    
    # Run all examples
    result1 = example1_mea_high_temp()
    result2 = example2_dipa_with_inspections()
    result3 = example3_dea_medium()
    result4 = example4_mdea_low()
    result5 = example5_stress_relieved()
    result6 = example6_rich_amine()
    
    # Summary
    print("\n" + "=" * 80)
    print("📋 SUMMARY COMPARISON")
    print("=" * 80)
    print(f"{'Scenario':<50} {'Suscept':>12} {'DF':>10}")
    print("-" * 80)
    print(f"{'1. MEA High Temp (No Insp)':<50} {result1['susceptibility']:>12} {result1['df_amine_scc']:>10.1f}")
    print(f"{'2. DIPA with Good Inspections':<50} {result2['susceptibility']:>12} {result2['df_amine_scc']:>10.2f}")
    print(f"{'3. DEA Medium Temp':<50} {result3['susceptibility']:>12} {result3['df_amine_scc']:>10.1f}")
    print(f"{'4. MDEA (Steamed Out)':<50} {result4['susceptibility']:>12} {result4['df_amine_scc']:>10.2f}")
    print(f"{'5. PWHT Performed (Not Susceptible)':<50} {result5['susceptibility']:>12} {result5['df_amine_scc']:>10.1f}")
    print(f"{'6. Rich Amine (Not Susceptible)':<50} {result6['susceptibility']:>12} {result6['df_amine_scc']:>10.1f}")
    print("=" * 80)
    
    print("\n📌 KEY INSIGHTS:")
    print("   • PWHT (1150°F for 1 hr/inch) eliminates amine SCC risk completely")
    print("   • Amine cracking ONLY in LEAN amine (alkaline, low H2S/CO2)")
    print("   • Rich amine → check SSC/HIC/SOHIC instead (different mechanisms)")
    print("   • Susceptibility ranking: MEA = DIPA > DEA > MDEA = DGA = Sulfinol")
    print("   • Temperature thresholds:")
    print("       - MEA/DIPA: High risk >180°F, Medium 140-180°F")
    print("       - DEA: Medium >180°F")
    print("       - MDEA/DGA: Low >180°F with heating")
    print("   • Heat tracing/steam out increases local temperature → higher risk")
    print("   • Fresh amine (never exposed to H2S/CO2) = not susceptible")
    print("   • Good inspection programs (A-level) significantly reduce DF")
