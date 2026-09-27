"""
Example usage of External Corrosion DF Calculator
WITH DETAILED STEP-BY-STEP CALCULATIONS
"""

from external_corrosion_df import ExternalCorrosionData, calculate_external_corrosion_df


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
    print(f"   External Corrosion DF: {result['df_external']:.2f}")
    print(f"   Driver Category: {result.get('driver_category', 'N/A').upper()}")
    print(f"   Base Corrosion Rate: {result.get('base_corrosion_rate', 0):.3f} mm/year")
    print(f"{'='*80}")


def example1_severe_coastal():
    """
    Example 1: Severe Coastal Environment - No Coating
    """
    print("\n" + "=" * 80)
    print("Example 1: Severe Coastal Environment - Uncoated Carbon Steel")
    print("=" * 80)
    
    print("\n📥 INPUT DATA:")
    print(f"   Equipment Type: Pipe")
    print(f"   Material: Carbon Steel")
    print(f"   Driver Category: Severe (coastal, high humidity)")
    print(f"   Temperature: 60°C (140°F)")
    print(f"   Coating: None")
    print(f"   Furnished Thickness: 10 mm")
    print(f"   Age: 12 years")
    print(f"   Inspections: 1× Level C")
    
    ext_data = ExternalCorrosionData(
        driver_category='severe',
        furnished_thickness=10.0,
        age=12.0,
        operating_temp=60.0,
        allows_water_pooling=False,
        soil_water_interface=False,
        coating_install_date=None,
        expected_coating_life=0.0,
        coating_failed_at_inspection=False,
        age_since_inspection=12.0,
        num_inspections_A=0,
        num_inspections_B=0,
        num_inspections_C=1,
        num_inspections_D=0,
        confidence_level='low'
    )
    
    component_data = {
        'equipment_type': 'pipe',
        'diameter': 400.0,
        'design_pressure': 2.5
    }
    
    result = calculate_external_corrosion_df(ext_data, component_data)
    print_detailed_steps(result)
    
    if result['df_external'] > 1000:
        print(f"\n⚠️  HIGH RISK: Severe environment with no coating protection")
    
    return result


def example2_mild_with_coating():
    """
    Example 2: Mild Environment with Good Coating
    """
    print("\n" + "=" * 80)
    print("Example 2: Mild Environment with Effective Coating System")
    print("=" * 80)
    
    print("\n📥 INPUT DATA:")
    print(f"   Equipment Type: Vessel")
    print(f"   Material: Carbon Steel")
    print(f"   Driver Category: Mild (indoor, dry)")
    print(f"   Temperature: 40°C (104°F)")
    print(f"   Coating: Yes, expected life 15 years")
    print(f"   Coating Age: 3 years")
    print(f"   Furnished Thickness: 20 mm")
    print(f"   Age: 5 years")
    print(f"   Inspections: 2× Level A")
    
    ext_data = ExternalCorrosionData(
        driver_category='mild',
        furnished_thickness=20.0,
        age=5.0,
        operating_temp=40.0,
        allows_water_pooling=False,
        soil_water_interface=False,
        coating_install_date='2023-01-01',
        expected_coating_life=15.0,
        coating_failed_at_inspection=False,
        age_since_inspection=5.0,
        num_inspections_A=2,
        num_inspections_B=0,
        num_inspections_C=0,
        num_inspections_D=0,
        confidence_level='high'
    )
    
    component_data = {
        'equipment_type': 'vessel',
        'diameter': 1500.0,
        'design_pressure': 4.0
    }
    
    result = calculate_external_corrosion_df(ext_data, component_data)
    print_detailed_steps(result)
    
    if result['df_external'] < 1.0:
        print(f"\n✅ LOW RISK: Effective coating system provides good protection")
    
    return result


def example3_moderate_assigned_rate():
    """
    Example 3: Moderate Environment with Assigned Corrosion Rate
    """
    print("\n" + "=" * 80)
    print("Example 3: Moderate Environment - Assigned Corrosion Rate from Data")
    print("=" * 80)
    
    print("\n📥 INPUT DATA:")
    print(f"   Equipment Type: Tank")
    print(f"   Material: Carbon Steel")
    print(f"   Driver Category: Moderate (industrial)")
    print(f"   Temperature: 50°C (122°F)")
    print(f"   Coating: Yes, but aged (8 years old)")
    print(f"   Expected Coating Life: 10 years")
    print(f"   Assigned Corrosion Rate: 0.15 mm/year (from inspection data)")
    print(f"   Furnished Thickness: 12 mm")
    print(f"   Age: 8 years")
    print(f"   Inspections: 1× Level B")
    
    ext_data = ExternalCorrosionData(
        driver_category='moderate',
        furnished_thickness=12.0,
        age=8.0,
        operating_temp=50.0,
        allows_water_pooling=False,
        soil_water_interface=False,
        coating_install_date='2018-01-01',
        expected_coating_life=10.0,
        coating_failed_at_inspection=False,
        assigned_corrosion_rate=0.15,  # Use measured rate
        age_since_inspection=4.0,
        num_inspections_A=0,
        num_inspections_B=1,
        num_inspections_C=0,
        num_inspections_D=0,
        confidence_level='medium'
    )
    
    component_data = {
        'equipment_type': 'tank',
        'diameter': 10000.0,
        'design_pressure': 0.1
    }
    
    result = calculate_external_corrosion_df(ext_data, component_data)
    print_detailed_steps(result)
    
    print(f"\n📌 NOTE: Using assigned corrosion rate from inspection data")
    
    return result


if __name__ == '__main__':
    print("\n🔧 External Corrosion Damage Factor Calculator")
    print("API 581 Section 2.D.2")
    print("WITH DETAILED STEP-BY-STEP CALCULATIONS\n")
    
    # Run examples
    result1 = example1_severe_coastal()
    result2 = example2_mild_with_coating()
    result3 = example3_moderate_assigned_rate()
    
    # Summary
    print("\n" + "=" * 80)
    print("📋 SUMMARY COMPARISON")
    print("=" * 80)
    print(f"{'Scenario':<50} {'Driver':>12} {'DF':>15}")
    print("-" * 80)
    print(f"{'1. Severe Coastal, No Coating':<50} {'severe':>12} {result1['df_external']:>15.2f}")
    print(f"{'2. Mild with Good Coating':<50} {'mild':>12} {result2['df_external']:>15.2f}")
    print(f"{'3. Moderate, Assigned Rate':<50} {'moderate':>12} {result3['df_external']:>15.2f}")
    print("=" * 80)
    
    print("\n📌 KEY INSIGHTS:")
    print("   • Driver categories: Severe > Moderate > Mild > Dry")
    print("   • Base rates depend on temperature range")
    print("   • Coating reduces DF significantly when within expected life")
    print("   • Temperature factor: Peak corrosion typically 50-100°C")
    print("   • Assigned rates override driver-based estimates when available")
    print("   • Water pooling and soil interface increase severity")
