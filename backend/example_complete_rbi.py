"""
Complete RBI Example - Integrating all calculators
"""

from thinning_df import ComponentData, CorrosionData, InspectionData, AdjustmentFactors
from pof_calculator import DamageFactors
from cof_calculator import FluidData, ConsequenceModifiers
from rbi_calculator import RBICalculator


def example_complete_rbi_high_risk():
    """
    Complete RBI example: High-risk crude oil piping
    - Significant thinning
    - Flammable fluid
    - High consequence
    """
    print("\n" + "=" * 80)
    print("COMPLETE RBI EXAMPLE: High-Risk Crude Oil Piping")
    print("=" * 80)
    
    # Component data
    component = ComponentData(
        tag_number="P-101-CR-001",
        component_type="cylinder",
        diameter=300.0,  # mm
        length=6000.0,  # mm
        yield_strength=240.0,  # MPa
        tensile_strength=415.0,  # MPa
        allowable_stress=138.0,  # MPa
        weld_joint_efficiency=0.85,
        furnished_thickness=10.0,  # mm
        design_pressure=3.0,  # MPa
        age=20.0  # years
    )
    
    # Corrosion data
    corrosion = CorrosionData(
        corrosion_rate_bm=0.5,  # mm/year - high corrosion
        thinning_type="localized",
        has_cladding=False,
        has_liner=False
    )
    
    # Inspection data
    inspection = InspectionData(
        measured_thickness=5.0,  # mm - significant loss!
        age_since_inspection=5.0,
        num_inspections_A=0,
        num_inspections_B=1,
        num_inspections_C=1,
        num_inspections_D=0,
        confidence_level="medium"
    )
    
    # Adjustment factors
    adjustments = AdjustmentFactors(
        has_online_monitoring=False,
        has_injection_point=True,
        injection_inspected=False,  # Critical!
        has_deadleg=False
    )
    
    # Other damage factors (none active in this example)
    damage_factors = DamageFactors(
        df_thinning=0.0,  # Will be calculated
        thinning_type="localized",
        df_external=0.0,
        df_scc_caustic=0.0,
        df_htha=0.0,
        df_mfat=0.0,
        df_brittle=0.0
    )
    
    # Fluid data - Crude oil
    fluid = FluidData(
        fluid_type='flammable',
        phase='liquid',
        molecular_weight=200.0,
        liquid_density=850.0,  # kg/m³
        boiling_point=350.0,  # °C
        is_flammable=True,
        autoignition_temp=250.0,  # °C
        heat_of_combustion=42000.0,  # kJ/kg
        is_toxic=False,
        operating_temp=80.0,  # °C
        operating_pressure=3.0,  # bara
        inventory_mass=50000.0  # kg
    )
    
    # Consequence modifiers
    consequence_mods = ConsequenceModifiers(
        has_detection=True,
        has_isolation=True,
        isolation_time=10.0,  # minutes
        has_deluge_system=False,
        population_density='medium',
        environmental_factor=1.5  # Sensitive area
    )
    
    # Calculate complete RBI
    calculator = RBICalculator()
    result = calculator.calculate_complete_rbi(
        tag_number="P-101-CR-001",
        component_type="pipe",
        component_data=component,
        corrosion_data=corrosion,
        inspection_data=inspection,
        adjustment_factors=adjustments,
        damage_factors=damage_factors,
        fluid_data=fluid,
        consequence_modifiers=consequence_mods,
        fms=1.0
    )
    
    # Print report
    print(calculator.print_complete_report(result))
    
    return result


def example_complete_rbi_low_risk():
    """
    Complete RBI example: Low-risk vessel with good inspection
    - Minimal thinning
    - Non-hazardous fluid
    - Good inspection program
    """
    print("\n" + "=" * 80)
    print("COMPLETE RBI EXAMPLE: Low-Risk Water Service Vessel")
    print("=" * 80)
    
    component = ComponentData(
        tag_number="V-201-W",
        component_type="cylinder",
        diameter=1500.0,  # mm
        yield_strength=250.0,  # MPa
        tensile_strength=400.0,  # MPa
        allowable_stress=138.0,  # MPa
        weld_joint_efficiency=1.0,
        furnished_thickness=20.0,  # mm
        design_pressure=2.0,  # MPa
        age=10.0  # years
    )
    
    corrosion = CorrosionData(
        corrosion_rate_bm=0.1,  # mm/year - low corrosion
        thinning_type="general",
        has_cladding=False,
        has_liner=False
    )
    
    inspection = InspectionData(
        measured_thickness=19.0,  # mm - minimal loss
        age_since_inspection=2.0,
        num_inspections_A=2,  # Good inspections
        num_inspections_B=2,
        num_inspections_C=0,
        num_inspections_D=0,
        confidence_level="high"
    )
    
    adjustments = AdjustmentFactors(
        has_online_monitoring=True,
        monitoring_effectiveness='process_monitoring',
        has_injection_point=False,
        has_deadleg=False
    )
    
    damage_factors = DamageFactors(
        df_thinning=0.0,
        thinning_type="general",
        df_external=0.0
    )
    
    # Water - non-hazardous
    fluid = FluidData(
        fluid_type='nonflammable',
        phase='liquid',
        molecular_weight=18.0,
        liquid_density=1000.0,  # kg/m³
        boiling_point=100.0,  # °C
        is_flammable=False,
        is_toxic=False,
        operating_temp=25.0,  # °C
        operating_pressure=2.0,  # bara
        inventory_mass=20000.0  # kg
    )
    
    consequence_mods = ConsequenceModifiers(
        has_detection=True,
        has_isolation=True,
        isolation_time=5.0,
        population_density='low',
        environmental_factor=0.5  # Not sensitive
    )
    
    calculator = RBICalculator()
    result = calculator.calculate_complete_rbi(
        tag_number="V-201-W",
        component_type="vessel",
        component_data=component,
        corrosion_data=corrosion,
        inspection_data=inspection,
        adjustment_factors=adjustments,
        damage_factors=damage_factors,
        fluid_data=fluid,
        consequence_modifiers=consequence_mods,
        fms=1.0
    )
    
    print(calculator.print_complete_report(result))
    
    return result


def run_complete_examples():
    """Run all complete RBI examples"""
    print("\n")
    print("*" * 80)
    print("API 581 COMPLETE RBI CALCULATOR - COMPREHENSIVE EXAMPLES")
    print("*" * 80)
    
    results = []
    
    # Run examples
    results.append(("High Risk Piping", example_complete_rbi_high_risk()))
    results.append(("Low Risk Vessel", example_complete_rbi_low_risk()))
    
    # Summary comparison
    print("\n" + "=" * 80)
    print("COMPARATIVE SUMMARY")
    print("=" * 80)
    print(f"{'Equipment':<25} {'PoF':<8} {'CoF':<8} {'Risk':<15} {'Priority':<30}")
    print("-" * 80)
    
    for name, result in results:
        risk = result['risk_assessment']
        print(f"{result['tag_number']:<25} "
              f"{risk['pof_category']:<8} "
              f"{risk['cof_category']:<8} "
              f"{risk['risk_level']:<15} "
              f"{result['inspection_priority'][:30]:<30}")
    
    print("=" * 80)


if __name__ == "__main__":
    run_complete_examples()
