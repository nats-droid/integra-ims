"""
Example usage of SSC (Sulfide Stress Cracking) DF Calculator
WITH DETAILED STEP-BY-STEP CALCULATIONS
"""

from ssc_df import SSCData, calculate_ssc_df


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
    print(f"   SSC DF: {result['df_ssc']:.2f}")
    print(f"   Susceptibility: {result['susceptibility'].upper()}")
    print(f"   Environmental Severity: {result['environmental_severity'].upper()}")
    print(f"   Severity Index: {result['severity_index']}")
    print(f"   Base DF: {result['base_df']}")
    print(f"   Age Since Inspection: {result['age_since_inspection']:.1f} years")
    print(f"   Highest Inspection: Level {result['highest_inspection']}")
    print(f"{'='*80}")


def example1_high_susceptibility():
    """
    Example 1: High Susceptibility - Sour Service, High Hardness, No PWHT
    - 500 ppm H2S in water
    - pH 4.0 (acidic)
    - Max hardness 250 BHN (> 237)
    - No PWHT
    """
    print("\n" + "=" * 80)
    print("Example 1: High Susceptibility - Sour Service, High Hardness, No PWHT")
    print("=" * 80)
    
    print("\n📥 INPUT DATA:")
    print(f"   Material: Carbon steel")
    print(f"   H₂S Content: 500 ppm in water")
    print(f"   H₂S Partial Pressure: 0.2 psia")
    print(f"   pH: 4.0 (acidic)")
    print(f"   Max Brinell Hardness: 250 BHN (> 237 = HIGH)")
    print(f"   PWHT: No (as-welded condition)")
    print(f"   Free Cyanide: 0 ppm")
    print(f"   Age Since Inspection: 8 years")
    print(f"   Inspections: None")
    
    ssc_data = SSCData(
        material='carbon_steel',
        h2s_content_ppm=500.0,
        h2s_partial_pressure_psia=0.2,
        ph=4.0,
        free_cyanide_ppm=0.0,
        water_present=True,
        max_brinell_hardness=250.0,
        pwht_applied=False,
        cracks_present=False,
        cracks_removed=False,
        age_since_inspection=8.0,
        num_inspections_A=0,
        num_inspections_B=0,
        num_inspections_C=0,
        num_inspections_D=0,
        num_inspections_E=0
    )
    
    result = calculate_ssc_df(ssc_data)
    print_detailed_steps(result)
    
    if result['df_ssc'] >= 1000:
        print(f"\n⚠️  CRITICAL: Very high SSC risk - immediate action required!")
    
    return result


def example2_with_pwht():
    """
    Example 2: Medium Susceptibility - PWHT Applied
    - 200 ppm H2S
    - pH 5.5
    - Max hardness 220 BHN
    - PWHT applied
    """
    print("\n" + "=" * 80)
    print("Example 2: Medium Susceptibility - PWHT Applied, Good Inspections")
    print("=" * 80)
    
    print("\n📥 INPUT DATA:")
    print(f"   Material: Carbon steel")
    print(f"   H₂S Content: 200 ppm in water")
    print(f"   H₂S Partial Pressure: 0.1 psia")
    print(f"   pH: 5.5")
    print(f"   Max Brinell Hardness: 220 BHN (200-237 = MEDIUM)")
    print(f"   PWHT: Yes (stress relieved)")
    print(f"   Free Cyanide: 0 ppm")
    print(f"   Age Since Inspection: 4 years")
    print(f"   Inspections: 2× Level A, 1× Level B")
    
    ssc_data = SSCData(
        material='carbon_steel',
        h2s_content_ppm=200.0,
        h2s_partial_pressure_psia=0.1,
        ph=5.5,
        free_cyanide_ppm=0.0,
        water_present=True,
        max_brinell_hardness=220.0,
        pwht_applied=True,
        cracks_present=False,
        cracks_removed=False,
        age_since_inspection=4.0,
        num_inspections_A=2,
        num_inspections_B=1,
        num_inspections_C=0,
        num_inspections_D=0,
        num_inspections_E=0
    )
    
    result = calculate_ssc_df(ssc_data)
    print_detailed_steps(result)
    
    if result['df_ssc'] < 10:
        print(f"\n✅ LOW RISK: PWHT + good inspections effective")
    
    return result


def example3_low_hardness():
    """
    Example 3: Low Susceptibility - Low Hardness, PWHT
    - 100 ppm H2S
    - pH 6.0
    - Max hardness 180 BHN (< 200)
    - PWHT applied
    """
    print("\n" + "=" * 80)
    print("Example 3: Low Susceptibility - Low Hardness < 200 BHN, PWHT")
    print("=" * 80)
    
    print("\n📥 INPUT DATA:")
    print(f"   Material: Carbon steel")
    print(f"   H₂S Content: 100 ppm in water")
    print(f"   H₂S Partial Pressure: 0.08 psia")
    print(f"   pH: 6.0 (near neutral)")
    print(f"   Max Brinell Hardness: 180 BHN (< 200 = LOW)")
    print(f"   PWHT: Yes")
    print(f"   Free Cyanide: 0 ppm")
    print(f"   Age Since Inspection: 5 years")
    print(f"   Inspections: 1× Level B, 2× Level C")
    
    ssc_data = SSCData(
        material='carbon_steel',
        h2s_content_ppm=100.0,
        h2s_partial_pressure_psia=0.08,
        ph=6.0,
        free_cyanide_ppm=0.0,
        water_present=True,
        max_brinell_hardness=180.0,
        pwht_applied=True,
        cracks_present=False,
        cracks_removed=False,
        age_since_inspection=5.0,
        num_inspections_A=0,
        num_inspections_B=1,
        num_inspections_C=2,
        num_inspections_D=0,
        num_inspections_E=0
    )
    
    result = calculate_ssc_df(ssc_data)
    print_detailed_steps(result)
    
    print(f"\n✅ LOW RISK: Low hardness + PWHT = good resistance")
    
    return result


def example4_high_ph_with_cyanide():
    """
    Example 4: High pH with Cyanide - Increased Severity
    - 2000 ppm H2S
    - pH 8.0 (alkaline)
    - 25 ppm free cyanide (> 20 ppm)
    - Hardness 230 BHN
    """
    print("\n" + "=" * 80)
    print("Example 4: High pH with Cyanide - Severity Increased")
    print("=" * 80)
    
    print("\n📥 INPUT DATA:")
    print(f"   Material: Carbon steel")
    print(f"   H₂S Content: 2000 ppm in water")
    print(f"   H₂S Partial Pressure: 0.3 psia")
    print(f"   pH: 8.0 (alkaline)")
    print(f"   Max Brinell Hardness: 230 BHN")
    print(f"   PWHT: No")
    print(f"   Free Cyanide: 25 ppm (> 20 ppm = severity increases!)")
    print(f"   Age Since Inspection: 6 years")
    print(f"   Inspections: 1× Level C")
    
    ssc_data = SSCData(
        material='carbon_steel',
        h2s_content_ppm=2000.0,
        h2s_partial_pressure_psia=0.3,
        ph=8.0,
        free_cyanide_ppm=25.0,
        water_present=True,
        max_brinell_hardness=230.0,
        pwht_applied=False,
        cracks_present=False,
        cracks_removed=False,
        age_since_inspection=6.0,
        num_inspections_A=0,
        num_inspections_B=0,
        num_inspections_C=1,
        num_inspections_D=0,
        num_inspections_E=0
    )
    
    result = calculate_ssc_df(ssc_data)
    print_detailed_steps(result)
    
    print(f"\n⚠️  NOTE: Cyanide > 20 ppm at high pH increases severity!")
    
    return result


def example5_no_water():
    """
    Example 5: Not Susceptible - No Water Present
    """
    print("\n" + "=" * 80)
    print("Example 5: Not Susceptible - No Water Present (Dry H2S)")
    print("=" * 80)
    
    print("\n📥 INPUT DATA:")
    print(f"   Material: Carbon steel")
    print(f"   H₂S Content: 1000 ppm")
    print(f"   Water Present: No (dry service)")
    print(f"   pH: N/A")
    print(f"   Max Brinell Hardness: 240 BHN")
    print(f"   PWHT: No")
    
    ssc_data = SSCData(
        material='carbon_steel',
        h2s_content_ppm=1000.0,
        h2s_partial_pressure_psia=0.5,
        ph=5.0,
        free_cyanide_ppm=0.0,
        water_present=False,  # No water!
        max_brinell_hardness=240.0,
        pwht_applied=False,
        cracks_present=False,
        cracks_removed=False,
        age_since_inspection=10.0,
        num_inspections_A=0,
        num_inspections_B=0,
        num_inspections_C=0,
        num_inspections_D=0,
        num_inspections_E=0
    )
    
    result = calculate_ssc_df(ssc_data)
    print_detailed_steps(result)
    
    print(f"\n✅ NOT SUSCEPTIBLE: SSC requires water + H2S (aqueous environment)")
    
    return result


if __name__ == '__main__':
    print("\n🔧 SSC (Sulfide Stress Cracking) Damage Factor Calculator")
    print("API 581 Section 2.C.10")
    print("WITH DETAILED STEP-BY-STEP CALCULATIONS\n")
    
    # Run all examples
    result1 = example1_high_susceptibility()
    result2 = example2_with_pwht()
    result3 = example3_low_hardness()
    result4 = example4_high_ph_with_cyanide()
    result5 = example5_no_water()
    
    # Summary
    print("\n" + "=" * 80)
    print("📋 SUMMARY COMPARISON")
    print("=" * 80)
    print(f"{'Scenario':<55} {'Env Sev':>10} {'Suscept':>10} {'DF':>10}")
    print("-" * 80)
    print(f"{'1. High Hardness, No PWHT':<55} {result1['environmental_severity']:>10} {result1['susceptibility']:>10} {result1['df_ssc']:>10.2f}")
    print(f"{'2. PWHT Applied, Good Inspections':<55} {result2['environmental_severity']:>10} {result2['susceptibility']:>10} {result2['df_ssc']:>10.2f}")
    print(f"{'3. Low Hardness < 200 BHN, PWHT':<55} {result3['environmental_severity']:>10} {result3['susceptibility']:>10} {result3['df_ssc']:>10.2f}")
    print(f"{'4. High pH + Cyanide':<55} {result4['environmental_severity']:>10} {result4['susceptibility']:>10} {result4['df_ssc']:>10.2f}")
    print(f"{'5. No Water (Dry H2S)':<55} {result5['environmental_severity']:>10} {result5['susceptibility']:>10} {result5['df_ssc']:>10.2f}")
    print("=" * 80)
    
    print("\n📌 KEY INSIGHTS:")
    print("   • SSC requires: water + H2S + tensile stress")
    print("   • Most susceptible: High hardness (>237 BHN) + No PWHT")
    print("   • PWHT @ 621°C (1150°F) for 1 hr/inch reduces risk significantly")
    print("   • Environmental severity factors:")
    print("       - H2S content (1-50 ppm low, 50-1000 moderate, >1000 high)")
    print("       - pH (lowest flux at near-neutral pH 5.5-6.5)")
    print("       - Free cyanide > 20 ppm at pH > 7.6 increases severity")
    print("   • Material factors:")
    print("       - Hardness < 200 BHN: Low susceptibility")
    print("       - Hardness 200-237 BHN: Medium susceptibility")
    print("       - Hardness > 237 BHN: High susceptibility")
    print("   • Best practice: PWHT + hardness control < 200 BHN")
    print("   • Common sources: Sour crude, sour gas, hydrotreaters, catalytic crackers")
