"""
Example usage of CUI (Corrosion Under Insulation) DF Calculator
WITH DETAILED STEP-BY-STEP CALCULATIONS
"""

from cui_df import CUIData, calculate_cui_df


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
                    if isinstance(v, float):
                        print(f"      {k}: {v:.6f}")
                    else:
                        print(f"      {k}: {v}")
            elif isinstance(value, (int, float)):
                if isinstance(value, float):
                    print(f"   {key}: {value:.6f}")
                else:
                    print(f"   {key}: {value}")
            else:
                print(f"   {key}: {value}")
    
    print(f"\n{'='*80}")
    print(f"📊 FINAL RESULTS")
    print(f"{'='*80}")
    print(f"   CUI DF: {result['df_cui']:.2f}")
    print(f"   Driver Category: {result.get('driver_category', 'N/A').upper()}")
    print(f"   Insulation Type: {result.get('insulation_type', 'N/A')}")
    print(f"   Operating Temperature: {result.get('operating_temp', 0):.1f}°C")
    print(f"{'='*80}")


def example1_severe_mineral_wool():
    """
    Example 1: Severe CUI - Mineral Wool, Peak Aggression Zone
    """
    print("\n" + "=" * 80)
    print("Example 1: Severe CUI - Mineral Wool Insulation, Peak Aggression (80°C)")
    print("=" * 80)
    
    print("\n📥 INPUT DATA:")
    print(f"   Equipment: Pipe")
    print(f"   Material: Carbon Steel")
    print(f"   Driver: Severe (coastal, high humidity)")
    print(f"   Insulation: Mineral Wool")
    print(f"   Temperature: 80°C (176°F) - PEAK AGGRESSION ZONE")
    print(f"   Coating: None")
    print(f"   Furnished Thickness: 12 mm")
    print(f"   Age: 15 years")
    print(f"   Inspections: None")
    
    cui_data = CUIData(
        driver_category='severe',
        insulation_type='mineral_wool',
        operating_temp=80.0,  # Peak aggression zone (50-100°C)
        furnished_thickness=12.0,
        age=15.0,
        coating_condition='none',
        coating_age=0.0,
        age_since_inspection=15.0,
        num_inspections_A=0,
        num_inspections_B=0,
        num_inspections_C=0,
        num_inspections_D=0,
        confidence_level='low'
    )
    
    component_data = {
        'equipment_type': 'pipe',
        'diameter': 300.0,
        'design_pressure': 3.0
    }
    
    result = calculate_cui_df(cui_data, component_data)
    print_detailed_steps(result)
    
    if result['df_cui'] > 5000:
        print(f"\n⚠️  CRITICAL: Peak aggression zone with mineral wool!")
    
    return result


def example2_excellent_coating():
    """
    Example 2: Low CUI - Excellent Coating Protection
    """
    print("\n" + "=" * 80)
    print("Example 2: Low CUI - Excellent Coating, Good Inspections")
    print("=" * 80)
    
    print("\n📥 INPUT DATA:")
    print(f"   Equipment: Vessel")
    print(f"   Material: Carbon Steel")
    print(f"   Driver: Moderate")
    print(f"   Insulation: Foam Glass")
    print(f"   Temperature: 65°C (149°F)")
    print(f"   Coating: Excellent condition")
    print(f"   Coating Age: 2 years")
    print(f"   Furnished Thickness: 20 mm")
    print(f"   Age: 8 years")
    print(f"   Inspections: 2× Level A")
    
    cui_data = CUIData(
        driver_category='moderate',
        insulation_type='foam_glass',
        operating_temp=65.0,
        furnished_thickness=20.0,
        age=8.0,
        coating_condition='excellent',
        coating_age=2.0,
        age_since_inspection=4.0,
        num_inspections_A=2,
        num_inspections_B=0,
        num_inspections_C=0,
        num_inspections_D=0,
        confidence_level='high'
    )
    
    component_data = {
        'equipment_type': 'vessel',
        'diameter': 1800.0,
        'design_pressure': 4.5
    }
    
    result = calculate_cui_df(cui_data, component_data)
    print_detailed_steps(result)
    
    if result['df_cui'] < 1.0:
        print(f"\n✅ LOW RISK: Excellent coating + good inspections effective")
    
    return result


def example3_stainless_steel():
    """
    Example 3: Stainless Steel - Low Susceptibility
    """
    print("\n" + "=" * 80)
    print("Example 3: Stainless Steel - Inherently Low CUI Susceptibility")
    print("=" * 80)
    
    print("\n📥 INPUT DATA:")
    print(f"   Equipment: Pipe")
    print(f"   Material: Stainless Steel 304")
    print(f"   Driver: Mild")
    print(f"   Insulation: Mineral Wool")
    print(f"   Temperature: 70°C (158°F)")
    print(f"   Coating: None (SS doesn't need it)")
    print(f"   Furnished Thickness: 8 mm")
    print(f"   Age: 10 years")
    print(f"   Inspections: 1× Level C")
    
    cui_data = CUIData(
        driver_category='mild',
        insulation_type='mineral_wool',
        operating_temp=70.0,
        furnished_thickness=8.0,
        age=10.0,
        coating_condition='none',
        coating_age=0.0,
        material_type='stainless_steel',  # SS has much lower CUI rates
        age_since_inspection=5.0,
        num_inspections_A=0,
        num_inspections_B=0,
        num_inspections_C=1,
        num_inspections_D=0,
        confidence_level='low'
    )
    
    component_data = {
        'equipment_type': 'pipe',
        'diameter': 250.0,
        'design_pressure': 2.5
    }
    
    result = calculate_cui_df(cui_data, component_data)
    print_detailed_steps(result)
    
    print(f"\n✅ LOW RISK: Stainless steel much more resistant to CUI than carbon steel")
    
    return result


def example4_calcium_silicate():
    """
    Example 4: Calcium Silicate - Highest Insulation Factor
    """
    print("\n" + "=" * 80)
    print("Example 4: Calcium Silicate Insulation - Highest CUI Risk Factor")
    print("=" * 80)
    
    print("\n📥 INPUT DATA:")
    print(f"   Equipment: Vessel")
    print(f"   Material: Carbon Steel")
    print(f"   Driver: Moderate")
    print(f"   Insulation: Calcium Silicate (highest factor 2.0×)")
    print(f"   Temperature: 90°C (194°F)")
    print(f"   Coating: Average condition")
    print(f"   Furnished Thickness: 15 mm")
    print(f"   Age: 12 years")
    print(f"   Inspections: 1× Level B")
    
    cui_data = CUIData(
        driver_category='moderate',
        insulation_type='calcium_silicate',  # Factor 2.0×
        operating_temp=90.0,
        furnished_thickness=15.0,
        age=12.0,
        coating_condition='average',
        coating_age=6.0,
        age_since_inspection=6.0,
        num_inspections_A=0,
        num_inspections_B=1,
        num_inspections_C=0,
        num_inspections_D=0,
        confidence_level='medium'
    )
    
    component_data = {
        'equipment_type': 'vessel',
        'diameter': 2500.0,
        'design_pressure': 3.5
    }
    
    result = calculate_cui_df(cui_data, component_data)
    print_detailed_steps(result)
    
    print(f"\n⚠️  NOTE: Calcium silicate has highest insulation factor (2.0×)")
    
    return result


if __name__ == '__main__':
    print("\n🔧 CUI (Corrosion Under Insulation) Damage Factor Calculator")
    print("API 581 Section 2.D.3")
    print("WITH DETAILED STEP-BY-STEP CALCULATIONS\n")
    
    # Run all examples
    result1 = example1_severe_mineral_wool()
    result2 = example2_excellent_coating()
    result3 = example3_stainless_steel()
    result4 = example4_calcium_silicate()
    
    # Summary
    print("\n" + "=" * 80)
    print("📋 SUMMARY COMPARISON")
    print("=" * 80)
    print(f"{'Scenario':<50} {'Insulation':>15} {'Temp (°C)':>12} {'DF':>12}")
    print("-" * 80)
    print(f"{'1. Severe + Mineral Wool':<50} {'mineral_wool':>15} {80.0:>12.1f} {result1['df_cui']:>12.2f}")
    print(f"{'2. Excellent Coating + Foam Glass':<50} {'foam_glass':>15} {65.0:>12.1f} {result2['df_cui']:>12.2f}")
    print(f"{'3. Stainless Steel':<50} {'mineral_wool':>15} {70.0:>12.1f} {result3['df_cui']:>12.2f}")
    print(f"{'4. Calcium Silicate':<50} {'calcium_silicate':>15} {90.0:>12.1f} {result4['df_cui']:>12.2f}")
    print("=" * 80)
    
    print("\n📌 KEY INSIGHTS:")
    print("   • Peak aggression zone: 50-100°C (most aggressive)")
    print("   • Insulation type factors:")
    print("       - Calcium Silicate: 2.0× (highest)")
    print("       - Mineral Wool: 1.5×")
    print("       - Foam Glass: 1.2× (lowest)")
    print("   • Excellent coating can reduce DF by 95%+")
    print("   • Stainless steel much more resistant than carbon steel")
    print("   • Wetting/drying cycles under insulation accelerate corrosion")
