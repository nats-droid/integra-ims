"""
Example usage of CUI (Corrosion Under Insulation) DF Calculator
"""

from cui_df import CUIData, calculate_cui_df


def example1_severe_cui_mineral_wool():
    """
    Example 1: Severe CUI - Mineral Wool Insulation
    - Coastal refinery with high humidity
    - Mineral wool (high water retention)
    - Operating in peak CUI temperature range (77-110°C)
    - Poor insulation condition
    """
    print("=" * 80)
    print("Example 1: Severe CUI - Mineral Wool Insulation, Poor Condition")
    print("=" * 80)
    
    cui_data = CUIData(
        driver_category='severe',
        furnished_thickness=12.0,  # mm
        age=15.0,  # years
        operating_temp=95.0,  # °C - peak CUI range
        
        # Insulation specific
        insulation_type='mineral_wool',  # High water retention (F_INS = 1.5)
        insulation_condition='below_average',  # F_IC = 1.25
        complexity='above_average',  # F_CM = 1.25 (many penetrations)
        
        # Design issues
        allows_water_pooling=True,  # F_EQ = 2.0
        soil_water_interface=False,
        
        # No coating
        expected_coating_life=0.0,
        
        # Some inspection history
        age_since_inspection=5.0,
        measured_thickness=10.5,  # mm
        num_inspections_B=2,
        confidence_level='medium'
    )
    
    component_data = {
        'component_type': 'cylinder',
        'diameter': 600.0,  # mm
        'design_pressure': 2.5,  # MPa
        'allowable_stress': 138.0,  # MPa
        'weld_joint_efficiency': 1.0,
        'yield_strength': 240.0,  # MPa
        'tensile_strength': 400.0,  # MPa
    }
    
    result = calculate_cui_df(cui_data, component_data)
    
    print(f"\n📊 RESULTS:")
    print(f"   CUI Damage Factor: {result['df_cui']:.1f}")
    print(f"   Corrosion Rate: {result['corrosion_rate']:.2f} mm/year")
    print(f"   Art Parameter: {result['art']:.3f}")
    print(f"   Strength Ratio: {result['strength_ratio']:.3f}")
    print(f"   Effective Age: {result['effective_age']:.1f} years")
    print(f"   Insulation Factor: {result['insulation_factor']:.2f}")
    
    if result['df_cui'] > 1000:
        print(f"   ⚠️  CRITICAL: Very high CUI susceptibility!")
    elif result['df_cui'] > 100:
        print(f"   ⚠️  HIGH: Significant CUI risk")
    
    return result


def example2_mild_cui_with_coating():
    """
    Example 2: Mild CUI with Good Coating
    - Dry climate
    - Cellular glass insulation (low water retention)
    - Good coating protection
    - Good insulation condition
    """
    print("\n" + "=" * 80)
    print("Example 2: Mild CUI - Cellular Glass + Good Coating")
    print("=" * 80)
    
    cui_data = CUIData(
        driver_category='mild',
        furnished_thickness=10.0,  # mm
        age=10.0,  # years
        operating_temp=120.0,  # °C
        
        # Insulation specific
        insulation_type='cellular_glass',  # Low water retention (F_INS = 0.75)
        insulation_condition='above_average',  # F_IC = 0.75
        complexity='below_average',  # F_CM = 0.75 (simple piping)
        
        # Good design
        allows_water_pooling=False,
        soil_water_interface=False,
        
        # High-quality coating applied 8 years ago
        expected_coating_life=15.0,
        
        # Recent inspection
        age_since_inspection=2.0,
        measured_thickness=9.8,  # mm
        num_inspections_A=1,
        num_inspections_B=1,
        confidence_level='high'
    )
    
    component_data = {
        'component_type': 'cylinder',
        'diameter': 400.0,  # mm
        'design_pressure': 1.5,  # MPa
        'allowable_stress': 138.0,  # MPa
        'weld_joint_efficiency': 1.0,
        'yield_strength': 240.0,  # MPa
        'tensile_strength': 400.0,  # MPa
    }
    
    result = calculate_cui_df(cui_data, component_data)
    
    print(f"\n📊 RESULTS:")
    print(f"   CUI Damage Factor: {result['df_cui']:.2f}")
    print(f"   Corrosion Rate: {result['corrosion_rate']:.3f} mm/year")
    print(f"   Art Parameter: {result['art']:.4f}")
    print(f"   Strength Ratio: {result['strength_ratio']:.3f}")
    print(f"   Effective Age: {result['effective_age']:.1f} years")
    print(f"   Insulation Factor: {result['insulation_factor']:.2f}")
    
    if result['df_cui'] < 10:
        print(f"   ✅ LOW: Good CUI protection")
    
    return result


def example3_calcium_silicate_cycling():
    """
    Example 3: Calcium Silicate with Temperature Cycling
    - Calcium silicate (highest water retention)
    - Temperature cycling through dew point
    - Moderate environment
    - Failed coating
    """
    print("\n" + "=" * 80)
    print("Example 3: Calcium Silicate - Temperature Cycling, Failed Coating")
    print("=" * 80)
    
    cui_data = CUIData(
        driver_category='moderate',
        furnished_thickness=14.0,  # mm
        age=20.0,  # years
        operating_temp=85.0,  # °C - within peak range
        
        # Insulation specific
        insulation_type='calcium_silicate',  # Highest water retention (F_INS = 2.0)
        insulation_condition='below_average',  # F_IC = 1.25
        complexity='average',  # F_CM = 1.0
        
        # Design
        allows_water_pooling=True,  # F_EQ = 2.0
        soil_water_interface=False,
        
        # Coating failed at last inspection
        expected_coating_life=10.0,
        coating_failed_at_inspection=True,
        
        # Old inspection data
        age_since_inspection=8.0,
        measured_thickness=11.5,  # mm - significant loss already
        num_inspections_C=3,
        confidence_level='low'
    )
    
    component_data = {
        'component_type': 'cylinder',
        'diameter': 800.0,  # mm
        'design_pressure': 3.0,  # MPa
        'allowable_stress': 138.0,  # MPa
        'weld_joint_efficiency': 0.85,
        'yield_strength': 240.0,  # MPa
        'tensile_strength': 400.0,  # MPa
    }
    
    result = calculate_cui_df(cui_data, component_data)
    
    print(f"\n📊 RESULTS:")
    print(f"   CUI Damage Factor: {result['df_cui']:.1f}")
    print(f"   Corrosion Rate: {result['corrosion_rate']:.2f} mm/year")
    print(f"   Art Parameter: {result['art']:.3f}")
    print(f"   Strength Ratio: {result['strength_ratio']:.3f}")
    print(f"   Effective Age: {result['effective_age']:.1f} years")
    print(f"   Insulation Factor: {result['insulation_factor']:.2f}")
    
    if result['df_cui'] > 1000:
        print(f"   ⚠️  CRITICAL: Immediate inspection required!")
    
    return result


def example4_assigned_rate():
    """
    Example 4: User-Assigned Corrosion Rate
    - Based on site-specific data
    - Skip table lookup
    """
    print("\n" + "=" * 80)
    print("Example 4: User-Assigned CUI Rate (Site-Specific Data)")
    print("=" * 80)
    
    cui_data = CUIData(
        driver_category='severe',  # Not used when rate assigned
        furnished_thickness=15.0,  # mm
        age=12.0,  # years
        operating_temp=90.0,  # °C
        
        # Assigned rate from corrosion monitoring program
        assigned_corrosion_rate=1.2,  # mm/year
        
        # Insulation (not used in rate calculation when assigned)
        insulation_type='mineral_wool',
        insulation_condition='average',
        complexity='average',
        allows_water_pooling=False,
        
        # Inspection history
        age_since_inspection=3.0,
        measured_thickness=12.5,  # mm
        num_inspections_A=2,
        confidence_level='high'
    )
    
    component_data = {
        'component_type': 'cylinder',
        'diameter': 1000.0,  # mm
        'design_pressure': 4.0,  # MPa
        'allowable_stress': 138.0,  # MPa
        'weld_joint_efficiency': 1.0,
        'yield_strength': 240.0,  # MPa
        'tensile_strength': 400.0,  # MPa
    }
    
    result = calculate_cui_df(cui_data, component_data)
    
    print(f"\n📊 RESULTS:")
    print(f"   CUI Damage Factor: {result['df_cui']:.1f}")
    print(f"   Corrosion Rate: {result['corrosion_rate']:.2f} mm/year (assigned)")
    print(f"   Art Parameter: {result['art']:.3f}")
    print(f"   Strength Ratio: {result['strength_ratio']:.3f}")
    print(f"   Effective Age: {result['effective_age']:.1f} years")
    
    return result


if __name__ == '__main__':
    print("\n🔧 CUI (Corrosion Under Insulation) Damage Factor Examples")
    print("API 581 Section 2.D.3\n")
    
    # Run all examples
    result1 = example1_severe_cui_mineral_wool()
    result2 = example2_mild_cui_with_coating()
    result3 = example3_calcium_silicate_cycling()
    result4 = example4_assigned_rate()
    
    # Summary
    print("\n" + "=" * 80)
    print("📋 SUMMARY COMPARISON")
    print("=" * 80)
    print(f"{'Scenario':<50} {'DF':>10} {'Rate (mm/y)':>12}")
    print("-" * 80)
    print(f"{'1. Severe + Mineral Wool + Poor Condition':<50} {result1['df_cui']:>10.1f} {result1['corrosion_rate']:>12.2f}")
    print(f"{'2. Mild + Cellular Glass + Good Coating':<50} {result2['df_cui']:>10.2f} {result2['corrosion_rate']:>12.3f}")
    print(f"{'3. Moderate + Calcium Silicate + Failed Coating':<50} {result3['df_cui']:>10.1f} {result3['corrosion_rate']:>12.2f}")
    print(f"{'4. Site-Specific Assigned Rate':<50} {result4['df_cui']:>10.1f} {result4['corrosion_rate']:>12.2f}")
    print("=" * 80)
    
    print("\n📌 KEY INSIGHTS:")
    print("   • CUI is most aggressive in 50-100°C range (77-110°C)")
    print("   • Insulation type matters: Calcium Silicate (2.0x) > Mineral Wool (1.5x)")
    print("   • Water pooling doubles the corrosion rate")
    print("   • Good coatings can reduce effective age significantly")
    print("   • Temperature cycling through dew point increases severity")
