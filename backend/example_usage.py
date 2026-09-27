"""
Example usage and test cases for API 581 Thinning DF Calculator
"""

from thinning_df import (
    ComponentData,
    CorrosionData,
    InspectionData,
    AdjustmentFactors,
    ThinningDFCalculator,
    calculate_thinning_df
)


def example_1_simple_pipe():
    """
    Example 1: Simple carbon steel pipe with general corrosion
    - No cladding, no liner
    - Medium confidence in corrosion rate
    - Some inspection history
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Carbon Steel Pipe - General Corrosion")
    print("=" * 80)
    
    # Component data
    component = ComponentData(
        tag_number="P-101-A",
        component_type="cylinder",
        diameter=500.0,  # mm
        length=6000.0,  # mm
        yield_strength=250.0,  # MPa
        tensile_strength=400.0,  # MPa
        allowable_stress=138.0,  # MPa
        weld_joint_efficiency=0.85,
        furnished_thickness=12.0,  # mm
        design_pressure=2.0,  # MPa
        age=15.0  # years
    )
    
    # Corrosion data
    corrosion = CorrosionData(
        corrosion_rate_bm=0.3,  # mm/year
        thinning_type="general",
        has_cladding=False,
        has_liner=False
    )
    
    # Inspection data
    inspection = InspectionData(
        measured_thickness=7.5,  # mm after 15 years
        age_since_inspection=5.0,  # years since last inspection
        num_inspections_A=0,
        num_inspections_B=2,  # 2 good inspections
        num_inspections_C=1,
        num_inspections_D=0,
        confidence_level="medium"
    )
    
    # Adjustment factors
    adjustments = AdjustmentFactors(
        has_online_monitoring=False,
        has_injection_point=False,
        has_deadleg=False
    )
    
    # Calculate
    calculator = ThinningDFCalculator()
    result = calculator.calculate(component, corrosion, inspection, adjustments)
    
    # Print report
    print(calculator.print_calculation_report(result))
    
    return result


def example_2_vessel_with_cladding():
    """
    Example 2: Pressure vessel with stainless steel cladding
    - Has cladding protection
    - High confidence in corrosion rate
    - Good inspection program
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Pressure Vessel with Cladding")
    print("=" * 80)
    
    component = ComponentData(
        tag_number="V-201",
        component_type="cylinder",
        diameter=2000.0,  # mm
        yield_strength=240.0,  # MPa
        tensile_strength=400.0,  # MPa
        allowable_stress=130.0,  # MPa
        weld_joint_efficiency=1.0,
        furnished_thickness=25.0,  # mm (base + cladding)
        design_pressure=5.0,  # MPa
        age=20.0  # years
    )
    
    corrosion = CorrosionData(
        corrosion_rate_bm=0.5,  # mm/year for base metal
        thinning_type="general",
        has_cladding=True,
        cladding_thickness=3.0,  # mm
        corrosion_rate_cm=0.05  # mm/year for SS cladding
    )
    
    inspection = InspectionData(
        measured_thickness=24.0,  # mm
        age_since_inspection=3.0,
        num_inspections_A=2,  # Highly effective inspections
        num_inspections_B=1,
        num_inspections_C=0,
        num_inspections_D=0,
        confidence_level="high"
    )
    
    adjustments = AdjustmentFactors(
        has_online_monitoring=True,
        monitoring_effectiveness="corrosion_probe",
        has_injection_point=False,
        has_deadleg=False
    )
    
    calculator = ThinningDFCalculator()
    result = calculator.calculate(component, corrosion, inspection, adjustments)
    
    print(calculator.print_calculation_report(result))
    
    return result


def example_3_high_risk_piping():
    """
    Example 3: High-risk piping with injection point
    - Localized corrosion
    - Injection point (not inspected)
    - Low confidence in corrosion rate
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 3: High-Risk Piping with Injection Point")
    print("=" * 80)
    
    component = ComponentData(
        tag_number="P-301-B",
        component_type="cylinder",
        diameter=300.0,  # mm
        yield_strength=240.0,  # MPa
        tensile_strength=415.0,  # MPa
        allowable_stress=138.0,  # MPa
        weld_joint_efficiency=0.85,
        furnished_thickness=10.0,  # mm
        design_pressure=3.0,  # MPa
        age=25.0  # years
    )
    
    corrosion = CorrosionData(
        corrosion_rate_bm=0.8,  # mm/year - aggressive environment
        thinning_type="localized",  # Localized corrosion at injection point
        has_cladding=False,
        has_liner=False
    )
    
    inspection = InspectionData(
        measured_thickness=5.0,  # mm - significant thinning
        age_since_inspection=10.0,  # Long time since last inspection
        num_inspections_A=0,
        num_inspections_B=0,
        num_inspections_C=1,  # Only one fairly effective inspection
        num_inspections_D=0,
        confidence_level="low"  # Low confidence
    )
    
    adjustments = AdjustmentFactors(
        has_online_monitoring=False,
        has_injection_point=True,
        injection_inspected=False,  # NOT inspected - multiply by 3
        has_deadleg=False
    )
    
    calculator = ThinningDFCalculator()
    result = calculator.calculate(component, corrosion, inspection, adjustments)
    
    print(calculator.print_calculation_report(result))
    
    return result


def example_4_vessel_with_liner():
    """
    Example 4: Vessel with organic coating liner
    - Has internal coating protection
    - Liner degradation over time
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Vessel with Organic Coating Liner")
    print("=" * 80)
    
    component = ComponentData(
        tag_number="V-401",
        component_type="cylinder",
        diameter=1500.0,  # mm
        yield_strength=250.0,  # MPa
        tensile_strength=400.0,  # MPa
        allowable_stress=138.0,  # MPa
        weld_joint_efficiency=1.0,
        furnished_thickness=20.0,  # mm
        design_pressure=4.0,  # MPa
        age=12.0  # years
    )
    
    corrosion = CorrosionData(
        corrosion_rate_bm=1.0,  # mm/year if no liner
        thinning_type="general",
        has_cladding=False,
        has_liner=True,
        liner_type="organic_coating",
        liner_age=12.0,  # years
        liner_expected_life=15.0,  # years
        liner_condition="good"  # Still in good condition
    )
    
    inspection = InspectionData(
        measured_thickness=19.5,  # mm - minimal loss due to liner protection
        age_since_inspection=2.0,
        num_inspections_A=1,
        num_inspections_B=2,
        num_inspections_C=0,
        num_inspections_D=0,
        confidence_level="high"
    )
    
    adjustments = AdjustmentFactors(
        has_online_monitoring=False,
        has_injection_point=False,
        has_deadleg=False,
        has_liner_monitoring=True  # Liner condition monitored
    )
    
    calculator = ThinningDFCalculator()
    result = calculator.calculate(component, corrosion, inspection, adjustments)
    
    print(calculator.print_calculation_report(result))
    
    return result


def run_all_examples():
    """Run all example calculations"""
    print("\n")
    print("*" * 80)
    print("API 581 THINNING DF CALCULATOR - EXAMPLE CALCULATIONS")
    print("*" * 80)
    
    results = []
    
    # Run examples
    results.append(("Example 1", example_1_simple_pipe()))
    results.append(("Example 2", example_2_vessel_with_cladding()))
    results.append(("Example 3", example_3_high_risk_piping()))
    results.append(("Example 4", example_4_vessel_with_liner()))
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY OF ALL EXAMPLES")
    print("=" * 80)
    print(f"{'Example':<30} {'DF Thinning':<15} {'PoF Category':<15}")
    print("-" * 80)
    
    for name, result in results:
        print(f"{name:<30} {result['df_thinning']:>14.4f} {result['pof_category']:>14}")
    
    print("=" * 80)


if __name__ == "__main__":
    run_all_examples()
