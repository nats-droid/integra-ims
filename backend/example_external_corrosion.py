"""
Example: External Corrosion DF Calculation
"""

from external_corrosion_df import ExternalCorrosionData, ExternalCorrosionDFCalculator


def example_external_corrosion_severe():
    """
    Example: Severe external corrosion case
    - Coastal environment
    - Poor coating
    - Water pooling design
    """
    print("\n" + "=" * 80)
    print("EXAMPLE: Severe External Corrosion - Coastal Environment")
    print("=" * 80)
    
    # External corrosion data
    ext_corr = ExternalCorrosionData(
        driver_category='severe',  # Coastal, high chloride
        furnished_thickness=12.0,  # mm
        age=25.0,  # years
        operating_temp=60.0,  # °C - in aggressive range
        
        # Design issues
        allows_water_pooling=True,  # Poor drainage
        soil_water_interface=False,
        
        # Coating data
        coating_install_date='2001-01-01',
        expected_coating_life=5.0,  # Low quality coating
        coating_failed_at_inspection=True,
        
        # Inspection data
        measured_thickness=7.0,  # mm - significant loss!
        measured_wall_loss=5.0,  # mm
        age_since_inspection=5.0,  # years
        
        num_inspections_A=0,
        num_inspections_B=1,
        num_inspections_C=1,
        num_inspections_D=0,
        confidence_level='medium'
    )
    
    # Component data
    component = {
        'component_type': 'cylinder',
        'diameter': 500.0,  # mm
        'design_pressure': 2.0,  # MPa
        'yield_strength': 240.0,  # MPa
        'tensile_strength': 400.0,  # MPa
        'allowable_stress': 138.0,  # MPa
        'weld_joint_efficiency': 0.85,
        'furnished_thickness': 12.0  # mm
    }
    
    # Calculate
    calculator = ExternalCorrosionDFCalculator()
    result = calculator.calculate(ext_corr, component)
    
    # Print results
    print(f"\nRESULTS:")
    print(f"  DF External Corrosion: {result['df_external']:.4f}")
    print(f"  Corrosion Rate:        {result['corrosion_rate']:.3f} mm/year")
    print(f"  Art (wall loss):       {result['art']:.4f}")
    print(f"  Strength Ratio:        {result['strength_ratio']:.4f}")
    print(f"  Effective Age:         {result['effective_age']:.1f} years")
    print(f"  Coating Adjustment:    {result['coating_adjustment']:.1f} years")
    
    # Print detailed steps
    print("\n" + "-" * 80)
    print("DETAILED CALCULATION STEPS:")
    print("-" * 80)
    for step_name, step_data in result['all_steps']:
        print(f"\n{step_name}:")
        for key, value in step_data.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.6f}")
            else:
                print(f"  {key}: {value}")
    
    return result


def example_external_corrosion_mild():
    """
    Example: Mild external corrosion with good coating
    """
    print("\n" + "=" * 80)
    print("EXAMPLE: Mild External Corrosion - Good Coating & Maintenance")
    print("=" * 80)
    
    ext_corr = ExternalCorrosionData(
        driver_category='mild',
        furnished_thickness=15.0,  # mm
        age=15.0,  # years
        operating_temp=80.0,  # °C
        
        allows_water_pooling=False,  # Good design
        soil_water_interface=False,
        
        # Good coating
        expected_coating_life=15.0,  # High quality
        coating_failed_at_inspection=False,
        
        # Recent inspection
        measured_thickness=14.5,  # mm - minimal loss
        age_since_inspection=2.0,
        
        num_inspections_A=2,  # Good inspection program
        num_inspections_B=2,
        num_inspections_C=0,
        num_inspections_D=0,
        confidence_level='high'
    )
    
    component = {
        'component_type': 'cylinder',
        'diameter': 800.0,  # mm
        'design_pressure': 1.5,  # MPa
        'yield_strength': 250.0,  # MPa
        'tensile_strength': 400.0,  # MPa
        'allowable_stress': 138.0,  # MPa
        'weld_joint_efficiency': 1.0,
        'furnished_thickness': 15.0
    }
    
    calculator = ExternalCorrosionDFCalculator()
    result = calculator.calculate(ext_corr, component)
    
    print(f"\nRESULTS:")
    print(f"  DF External Corrosion: {result['df_external']:.4f}")
    print(f"  Corrosion Rate:        {result['corrosion_rate']:.3f} mm/year")
    print(f"  Art (wall loss):       {result['art']:.4f}")
    print(f"  Strength Ratio:        {result['strength_ratio']:.4f}")
    print(f"  Effective Age:         {result['effective_age']:.1f} years")
    print(f"  Coating Adjustment:    {result['coating_adjustment']:.1f} years")
    
    return result


def example_external_with_assigned_rate():
    """
    Example: Using corrosion specialist assigned rate
    """
    print("\n" + "=" * 80)
    print("EXAMPLE: External Corrosion with Assigned Rate by Specialist")
    print("=" * 80)
    
    ext_corr = ExternalCorrosionData(
        driver_category='moderate',  # Not used when rate assigned
        furnished_thickness=10.0,
        age=20.0,
        operating_temp=50.0,
        
        # Corrosion rate assigned by specialist
        assigned_corrosion_rate=0.4,  # mm/year
        
        measured_thickness=6.0,
        age_since_inspection=10.0,
        
        num_inspections_A=1,
        num_inspections_B=1,
        num_inspections_C=0,
        num_inspections_D=0,
        confidence_level='high'
    )
    
    component = {
        'component_type': 'cylinder',
        'diameter': 400.0,
        'design_pressure': 2.5,
        'yield_strength': 240.0,
        'tensile_strength': 415.0,
        'allowable_stress': 138.0,
        'weld_joint_efficiency': 0.85,
        'furnished_thickness': 10.0
    }
    
    calculator = ExternalCorrosionDFCalculator()
    result = calculator.calculate(ext_corr, component)
    
    print(f"\nRESULTS:")
    print(f"  DF External Corrosion: {result['df_external']:.4f}")
    print(f"  Corrosion Rate:        {result['corrosion_rate']:.3f} mm/year (ASSIGNED)")
    print(f"  Art (wall loss):       {result['art']:.4f}")
    
    return result


def run_external_corrosion_examples():
    """Run all external corrosion examples"""
    print("\n")
    print("*" * 80)
    print("API 581 EXTERNAL CORROSION DF CALCULATOR - EXAMPLES")
    print("*" * 80)
    
    results = []
    
    results.append(("Severe Coastal", example_external_corrosion_severe()))
    results.append(("Mild w/ Good Coating", example_external_corrosion_mild()))
    results.append(("Assigned Rate", example_external_with_assigned_rate()))
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"{'Case':<30} {'DF External':<15} {'Rate (mm/yr)':<15} {'Art':<10}")
    print("-" * 80)
    
    for name, result in results:
        print(f"{name:<30} {result['df_external']:>14.4f} "
              f"{result['corrosion_rate']:>14.3f} {result['art']:>9.4f}")
    
    print("=" * 80)


if __name__ == "__main__":
    run_external_corrosion_examples()
