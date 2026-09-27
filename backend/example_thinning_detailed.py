"""
Example usage of Thinning DF Calculator
WITH DETAILED STEP-BY-STEP CALCULATIONS
"""

from thinning_df import ThinningData, calculate_thinning_df


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
    print(f"   Thinning DF: {result['df_thinning']:.2f}")
    print(f"   PoF Category: {result['pof_category']}")
    print(f"   Art (remaining life ratio): {result.get('art', 'N/A'):.4f}" if isinstance(result.get('art'), float) else f"   Art: N/A")
    print(f"{'='*80}")


def example1_simple_pipe():
    """
    Example 1: Simple Carbon Steel Pipe
    """
    print("\n" + "=" * 80)
    print("Example 1: Simple Carbon Steel Pipe - Internal Corrosion")
    print("=" * 80)
    
    print("\n📥 INPUT DATA:")
    print(f"   Equipment Type: Pipe")
    print(f"   Material: Carbon Steel")
    print(f"   Nominal Thickness: 10 mm")
    print(f"   Measured Thickness: 7 mm")
    print(f"   Required Thickness: 5 mm")
    print(f"   Corrosion Rate: 0.5 mm/year")
    print(f"   Age: 8 years")
    print(f"   Component Diameter: 300 mm")
    print(f"   Design Pressure: 2.0 MPa")
    
    # Component data
    component_data = {
        'equipment_type': 'pipe',
        'diameter': 300.0,  # mm
        'design_pressure': 2.0,  # MPa
        'joint_efficiency': 1.0,
        'allowable_stress': 138.0,  # MPa
        'weld_quality_factor': 1.0
    }
    
    # Thinning data
    thinning_data = ThinningData(
        nominal_thickness=10.0,  # mm
        measured_thickness=7.0,  # mm
        future_corrosion_allowance=1.0,  # mm
        corrosion_rate=0.5,  # mm/year
        age=8.0,  # years
        inspection_effectiveness='C',
        num_inspections=1,
        has_lining=False,
        has_cladding=False,
        online_monitoring='none',
        is_injection_point=False,
        is_dead_leg=False
    )
    
    result = calculate_thinning_df(thinning_data, component_data)
    print_detailed_steps(result)
    
    return result


def example2_vessel_with_cladding():
    """
    Example 2: Pressure Vessel with Internal Cladding
    """
    print("\n" + "=" * 80)
    print("Example 2: Pressure Vessel with Internal Stainless Steel Cladding")
    print("=" * 80)
    
    print("\n📥 INPUT DATA:")
    print(f"   Equipment Type: Pressure Vessel")
    print(f"   Material: Carbon Steel + SS Cladding")
    print(f"   Nominal Thickness: 25 mm")
    print(f"   Measured Thickness: 22 mm")
    print(f"   Required Thickness: 18 mm")
    print(f"   Corrosion Rate: 0.3 mm/year")
    print(f"   Age: 12 years")
    print(f"   Cladding: 3 mm SS overlay")
    print(f"   Cladding Condition: Good")
    
    component_data = {
        'equipment_type': 'vessel',
        'diameter': 2000.0,  # mm
        'design_pressure': 5.0,  # MPa
        'joint_efficiency': 0.85,
        'allowable_stress': 138.0,
        'weld_quality_factor': 1.0
    }
    
    thinning_data = ThinningData(
        nominal_thickness=25.0,
        measured_thickness=22.0,
        future_corrosion_allowance=2.0,
        corrosion_rate=0.3,
        age=12.0,
        inspection_effectiveness='B',
        num_inspections=2,
        has_lining=False,
        has_cladding=True,
        cladding_thickness=3.0,
        cladding_condition='good',
        online_monitoring='none',
        is_injection_point=False,
        is_dead_leg=False
    )
    
    result = calculate_thinning_df(thinning_data, component_data)
    print_detailed_steps(result)
    
    if result['df_thinning'] < 100:
        print(f"\n✅ MODERATE RISK: Cladding provides good protection")
    
    return result


def example3_injection_point():
    """
    Example 3: High-Risk Injection Point
    """
    print("\n" + "=" * 80)
    print("Example 3: High-Risk Injection Point - Chemical Injection Nozzle")
    print("=" * 80)
    
    print("\n📥 INPUT DATA:")
    print(f"   Equipment Type: Pipe")
    print(f"   Location: Chemical Injection Point")
    print(f"   Nominal Thickness: 12 mm")
    print(f"   Measured Thickness: 6 mm")
    print(f"   Required Thickness: 5 mm")
    print(f"   Corrosion Rate: 1.2 mm/year (HIGH)")
    print(f"   Age: 5 years")
    print(f"   Injection Point Susceptibility: YES")
    
    component_data = {
        'equipment_type': 'pipe',
        'diameter': 400.0,
        'design_pressure': 3.5,
        'joint_efficiency': 1.0,
        'allowable_stress': 138.0,
        'weld_quality_factor': 1.0
    }
    
    thinning_data = ThinningData(
        nominal_thickness=12.0,
        measured_thickness=6.0,
        future_corrosion_allowance=0.5,
        corrosion_rate=1.2,
        age=5.0,
        inspection_effectiveness='D',
        num_inspections=1,
        has_lining=False,
        has_cladding=False,
        online_monitoring='none',
        is_injection_point=True,  # High risk!
        injection_point_factor=2.5,
        is_dead_leg=False
    )
    
    result = calculate_thinning_df(thinning_data, component_data)
    print_detailed_steps(result)
    
    if result['df_thinning'] > 5000:
        print(f"\n⚠️  CRITICAL: Injection point with high corrosion rate!")
        print(f"   Immediate inspection and possible replacement required")
    
    return result


if __name__ == '__main__':
    print("\n🔧 Thinning Damage Factor Calculator")
    print("API 581 Section 4")
    print("WITH DETAILED STEP-BY-STEP CALCULATIONS\n")
    
    # Run examples
    result1 = example1_simple_pipe()
    result2 = example2_vessel_with_cladding()
    result3 = example3_injection_point()
    
    # Summary
    print("\n" + "=" * 80)
    print("📋 SUMMARY COMPARISON")
    print("=" * 80)
    print(f"{'Scenario':<50} {'DF':>15} {'PoF Cat':>12}")
    print("-" * 80)
    print(f"{'1. Simple CS Pipe':<50} {result1['df_thinning']:>15.2f} {result1['pof_category']:>12}")
    print(f"{'2. Vessel with SS Cladding':<50} {result2['df_thinning']:>15.2f} {result2['pof_category']:>12}")
    print(f"{'3. High-Risk Injection Point':<50} {result3['df_thinning']:>15.2f} {result3['pof_category']:>12}")
    print("=" * 80)
    
    print("\n📌 KEY INSIGHTS:")
    print("   • Thinning DF uses Bayesian inspection effectiveness")
    print("   • Injection points can have DF 10-100× higher")
    print("   • Cladding/liners provide significant protection when intact")
    print("   • Online monitoring reduces DF significantly")
    print("   • Art (remaining life ratio) drives structural reliability")
