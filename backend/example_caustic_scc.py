"""
Example usage of Caustic SCC (Stress Corrosion Cracking) DF Calculator
"""

from caustic_scc_df import CausticSCCData, calculate_caustic_scc_df


def example1_high_susceptibility_area_c():
    """
    Example 1: High Susceptibility - Area C (High Temp + High Conc)
    - 220°F (104°C) operating temperature
    - 30% NaOH concentration
    - No stress relief
    - No inspections yet
    """
    print("=" * 80)
    print("Example 1: High Susceptibility - Area C (High Temp + High Concentration)")
    print("=" * 80)
    
    scc_data = CausticSCCData(
        material='carbon_steel',
        naoh_concentration=30.0,  # wt%
        max_process_temp=104.0,  # °C (220°F)
        stress_relieved=False,
        heat_traced=False,
        steamed_out=False,
        cracks_present=False,
        cracks_removed=False,
        age_since_inspection=10.0,  # 10 years, no inspection
        num_inspections_A=0,
        num_inspections_B=0,
        num_inspections_C=0,
        num_inspections_D=0,
        num_inspections_E=0
    )
    
    result = calculate_caustic_scc_df(scc_data)
    
    print(f"\n📊 RESULTS:")
    print(f"   Caustic SCC DF: {result['df_caustic_scc']:.1f}")
    print(f"   Susceptibility: {result['susceptibility'].upper()}")
    print(f"   Severity Index: {result['severity_index']}")
    print(f"   Base DF: {result['base_df']}")
    print(f"   Age Since Inspection: {result['age_since_inspection']:.1f} years")
    print(f"   Highest Inspection: {result['highest_inspection']}")
    
    if result['df_caustic_scc'] >= 5000:
        print(f"   ⚠️  CRITICAL: Maximum DF reached (capped at 5000)")
    elif result['df_caustic_scc'] > 1000:
        print(f"   ⚠️  VERY HIGH: Immediate inspection required!")
    
    return result


def example2_medium_susceptibility_area_b():
    """
    Example 2: Medium Susceptibility - Area B with Inspections
    - 180°F (82°C) operating temperature
    - 25% NaOH concentration
    - No stress relief but has inspection history
    """
    print("\n" + "=" * 80)
    print("Example 2: Medium Susceptibility - Area B with Good Inspection History")
    print("=" * 80)
    
    scc_data = CausticSCCData(
        material='carbon_steel',
        naoh_concentration=25.0,  # wt%
        max_process_temp=82.0,  # °C (180°F)
        stress_relieved=False,
        heat_traced=False,
        steamed_out=False,
        cracks_present=False,
        cracks_removed=False,
        age_since_inspection=3.0,  # 3 years since last inspection
        num_inspections_A=2,  # 2 A-level inspections
        num_inspections_B=1,
        num_inspections_C=0,
        num_inspections_D=0,
        num_inspections_E=0
    )
    
    result = calculate_caustic_scc_df(scc_data)
    
    print(f"\n📊 RESULTS:")
    print(f"   Caustic SCC DF: {result['df_caustic_scc']:.1f}")
    print(f"   Susceptibility: {result['susceptibility'].upper()}")
    print(f"   Severity Index: {result['severity_index']}")
    print(f"   Base DF: {result['base_df']}")
    print(f"   Age Since Inspection: {result['age_since_inspection']:.1f} years")
    print(f"   Highest Inspection: Level {result['highest_inspection']}")
    
    if result['df_caustic_scc'] < 50:
        print(f"   ✅ LOW: Good inspection program effectiveness")
    
    return result


def example3_low_susceptibility_area_a():
    """
    Example 3: Low Susceptibility - Area A (Low Concentration)
    - 130°F (54°C) operating temperature
    - 3% NaOH concentration
    - No stress relief needed per graph
    """
    print("\n" + "=" * 80)
    print("Example 3: Low Susceptibility - Area A (Low Concentration)")
    print("=" * 80)
    
    scc_data = CausticSCCData(
        material='carbon_steel',
        naoh_concentration=3.0,  # wt% (< 5%)
        max_process_temp=54.0,  # °C (130°F)
        stress_relieved=False,
        heat_traced=False,
        steamed_out=False,
        cracks_present=False,
        cracks_removed=False,
        age_since_inspection=5.0,
        num_inspections_A=0,
        num_inspections_B=1,
        num_inspections_C=2,
        num_inspections_D=0,
        num_inspections_E=0
    )
    
    result = calculate_caustic_scc_df(scc_data)
    
    print(f"\n📊 RESULTS:")
    print(f"   Caustic SCC DF: {result['df_caustic_scc']:.2f}")
    print(f"   Susceptibility: {result['susceptibility'].upper()}")
    print(f"   Severity Index: {result['severity_index']}")
    print(f"   Base DF: {result['base_df']}")
    print(f"   Age Since Inspection: {result['age_since_inspection']:.1f} years")
    print(f"   Highest Inspection: Level {result['highest_inspection']}")
    
    if result['df_caustic_scc'] < 50:
        print(f"   ✅ LOW RISK: Area A, low concentration")
    
    return result


def example4_stress_relieved():
    """
    Example 4: Not Susceptible - PWHT Performed
    - High temperature and concentration BUT stress relieved
    - Should show no susceptibility
    """
    print("\n" + "=" * 80)
    print("Example 4: Not Susceptible - PWHT (Stress Relief) Performed")
    print("=" * 80)
    
    scc_data = CausticSCCData(
        material='carbon_steel',
        naoh_concentration=40.0,  # wt% - would be Area C
        max_process_temp=120.0,  # °C (248°F) - high temp
        stress_relieved=True,  # PWHT performed - key mitigation!
        heat_traced=False,
        steamed_out=False,
        cracks_present=False,
        cracks_removed=False,
        age_since_inspection=15.0,
        num_inspections_A=0,
        num_inspections_B=0,
        num_inspections_C=0,
        num_inspections_D=0,
        num_inspections_E=0
    )
    
    result = calculate_caustic_scc_df(scc_data)
    
    print(f"\n📊 RESULTS:")
    print(f"   Caustic SCC DF: {result['df_caustic_scc']:.1f}")
    print(f"   Susceptibility: {result['susceptibility'].upper()}")
    print(f"   Severity Index: {result['severity_index']}")
    print(f"   Base DF: {result['base_df']}")
    
    if result['susceptibility'] == 'none':
        print(f"   ✅ NOT SUSCEPTIBLE: PWHT eliminates caustic SCC risk")
    
    return result


def example5_cracks_present():
    """
    Example 5: Cracks Detected - Automatic High Susceptibility
    - Regardless of other factors, cracks present = HIGH
    """
    print("\n" + "=" * 80)
    print("Example 5: High Susceptibility - Cracks Detected During Inspection")
    print("=" * 80)
    
    scc_data = CausticSCCData(
        material='carbon_steel',
        naoh_concentration=15.0,  # wt%
        max_process_temp=90.0,  # °C
        stress_relieved=False,
        heat_traced=False,
        steamed_out=False,
        cracks_present=True,  # Cracks found!
        cracks_removed=False,  # Not yet repaired
        age_since_inspection=0.5,  # Recent inspection
        num_inspections_A=1,
        num_inspections_B=0,
        num_inspections_C=0,
        num_inspections_D=0,
        num_inspections_E=0
    )
    
    result = calculate_caustic_scc_df(scc_data)
    
    print(f"\n📊 RESULTS:")
    print(f"   Caustic SCC DF: {result['df_caustic_scc']:.1f}")
    print(f"   Susceptibility: {result['susceptibility'].upper()}")
    print(f"   Severity Index: {result['severity_index']}")
    print(f"   Base DF: {result['base_df']}")
    print(f"   Age Since Inspection: {result['age_since_inspection']:.1f} years")
    
    print(f"   ⚠️  CRACKS DETECTED: Requires FFS evaluation and repair!")
    
    return result


def example6_heat_traced_steam_out():
    """
    Example 6: Heat Traced with Steam Out - Elevated Risk
    - Area A normally, but heat tracing increases susceptibility
    """
    print("\n" + "=" * 80)
    print("Example 6: Medium/High - Heat Traced + Steam Out (Area A → Elevated)")
    print("=" * 80)
    
    scc_data = CausticSCCData(
        material='carbon_steel',
        naoh_concentration=10.0,  # wt%
        max_process_temp=60.0,  # °C (140°F) - borderline Area A/B
        stress_relieved=False,
        heat_traced=True,  # Steam tracing!
        steamed_out=True,  # Steamed out before flush
        cracks_present=False,
        cracks_removed=False,
        age_since_inspection=7.0,
        num_inspections_A=0,
        num_inspections_B=0,
        num_inspections_C=1,
        num_inspections_D=0,
        num_inspections_E=0
    )
    
    result = calculate_caustic_scc_df(scc_data)
    
    print(f"\n📊 RESULTS:")
    print(f"   Caustic SCC DF: {result['df_caustic_scc']:.1f}")
    print(f"   Susceptibility: {result['susceptibility'].upper()}")
    print(f"   Severity Index: {result['severity_index']}")
    print(f"   Base DF: {result['base_df']}")
    print(f"   Age Since Inspection: {result['age_since_inspection']:.1f} years")
    
    print(f"   ⚠️  ELEVATED RISK: Heat tracing/steam out increases local temperature")
    
    return result


if __name__ == '__main__':
    print("\n🔧 Caustic SCC (Stress Corrosion Cracking) Damage Factor Examples")
    print("API 581 Section 2.C.4\n")
    
    # Run all examples
    result1 = example1_high_susceptibility_area_c()
    result2 = example2_medium_susceptibility_area_b()
    result3 = example3_low_susceptibility_area_a()
    result4 = example4_stress_relieved()
    result5 = example5_cracks_present()
    result6 = example6_heat_traced_steam_out()
    
    # Summary
    print("\n" + "=" * 80)
    print("📋 SUMMARY COMPARISON")
    print("=" * 80)
    print(f"{'Scenario':<50} {'Suscept':>12} {'DF':>10}")
    print("-" * 80)
    print(f"{'1. Area C (High Temp+Conc, No Insp)':<50} {result1['susceptibility']:>12} {result1['df_caustic_scc']:>10.1f}")
    print(f"{'2. Area B (Medium, Good Inspections)':<50} {result2['susceptibility']:>12} {result2['df_caustic_scc']:>10.1f}")
    print(f"{'3. Area A (Low Conc, Some Insp)':<50} {result3['susceptibility']:>12} {result3['df_caustic_scc']:>10.2f}")
    print(f"{'4. PWHT Performed (Not Susceptible)':<50} {result4['susceptibility']:>12} {result4['df_caustic_scc']:>10.1f}")
    print(f"{'5. Cracks Detected (Auto High)':<50} {result5['susceptibility']:>12} {result5['df_caustic_scc']:>10.1f}")
    print(f"{'6. Heat Traced + Steam Out':<50} {result6['susceptibility']:>12} {result6['df_caustic_scc']:>10.1f}")
    print("=" * 80)
    
    print("\n📌 KEY INSIGHTS:")
    print("   • PWHT (stress relief) eliminates caustic SCC risk completely")
    print("   • Temperature < 46°C (115°F) = not susceptible")
    print("   • Heat tracing and steam out increase local temperature → higher risk")
    print("   • Cracks present = automatic HIGH susceptibility (SVI=1000)")
    print("   • Area C (>200°F or high conc) requires nickel alloy consideration")
    print("   • Good inspection programs (A-level) significantly reduce DF")
    print("   • Time escalation: DF increases with age^1.1 (capped at 5000)")
