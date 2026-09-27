"""
Unit System - Conversion and Standardization
Handles SI ↔ USC (US Customary) conversions for RBI calculations

Internal calculations use SI units for consistency.
Display can be in either SI or USC based on preference.
"""

from typing import Dict, Any, Optional, Union
from enum import Enum


class UnitSystem(Enum):
    """Unit system selection"""
    SI = "SI"        # Metric (mm, MPa, °C, kg)
    USC = "USC"      # US Customary (in, psi, °F, lb)


class UnitConverter:
    """
    Bidirectional unit converter for RBI calculations
    """
    
    # Conversion factors (USC → SI)
    CONVERSIONS = {
        # Length
        'in_to_mm': 25.4,
        'ft_to_m': 0.3048,
        
        # Pressure
        'psi_to_mpa': 0.00689476,
        'psi_to_kpa': 6.89476,
        
        # Temperature (handled separately - not linear)
        
        # Corrosion Rate
        'mpy_to_mmpy': 0.0254,  # mils/year to mm/year
        
        # Mass
        'lb_to_kg': 0.453592,
        
        # Area
        'sqft_to_sqm': 0.092903,
        
        # Volume
        'gal_to_liter': 3.78541,
        'bbl_to_m3': 0.158987
    }
    
    @staticmethod
    def convert(value: float, from_unit: str, to_unit: str) -> float:
        """
        Convert value between units
        
        Args:
            value: Value to convert
            from_unit: Source unit (e.g., 'in', 'psi', 'F')
            to_unit: Target unit (e.g., 'mm', 'mpa', 'C')
        
        Returns:
            Converted value
        """
        # Normalize unit names
        from_unit = from_unit.lower().strip()
        to_unit = to_unit.lower().strip()
        
        # Temperature conversions (non-linear)
        if from_unit == 'f' and to_unit == 'c':
            return (value - 32) * 5/9
        elif from_unit == 'c' and to_unit == 'f':
            return value * 9/5 + 32
        elif from_unit == 'f' and to_unit == 'k':
            return (value - 32) * 5/9 + 273.15
        elif from_unit == 'k' and to_unit == 'f':
            return (value - 273.15) * 9/5 + 32
        
        # Linear conversions
        conversion_key = f"{from_unit}_to_{to_unit}"
        
        if conversion_key in UnitConverter.CONVERSIONS:
            return value * UnitConverter.CONVERSIONS[conversion_key]
        
        # Reverse conversion
        reverse_key = f"{to_unit}_to_{from_unit}"
        if reverse_key in UnitConverter.CONVERSIONS:
            return value / UnitConverter.CONVERSIONS[reverse_key]
        
        # Same unit
        if from_unit == to_unit:
            return value
        
        raise ValueError(f"No conversion available from {from_unit} to {to_unit}")
    
    @staticmethod
    def standardize_to_si(value: float, unit: str) -> float:
        """
        Convert any unit to SI standard
        
        Args:
            value: Value in original unit
            unit: Original unit name
        
        Returns:
            Value in SI unit
        """
        unit_lower = unit.lower().strip()
        
        # Map USC units to SI
        usc_to_si = {
            'in': 'mm',
            'ft': 'm',
            'psi': 'mpa',
            'psig': 'mpa',
            'f': 'c',
            'mpy': 'mmpy',
            'lb': 'kg',
            'sqft': 'sqm',
            'gal': 'liter',
            'bbl': 'm3'
        }
        
        # Already SI?
        if unit_lower in ['mm', 'm', 'mpa', 'kpa', 'c', 'k', 'mmpy', 'kg', 'sqm', 'liter', 'm3']:
            return value
        
        # Convert USC to SI
        if unit_lower in usc_to_si:
            si_unit = usc_to_si[unit_lower]
            return UnitConverter.convert(value, unit_lower, si_unit)
        
        raise ValueError(f"Unknown unit: {unit}")
    
    @staticmethod
    def format_for_display(
        value: float,
        quantity_type: str,
        unit_system: UnitSystem = UnitSystem.USC,
        precision: int = 2
    ) -> str:
        """
        Format value for display in chosen unit system
        
        Args:
            value: Value in SI units (internal standard)
            quantity_type: Type of quantity ('length', 'pressure', 'temperature', etc.)
            unit_system: Display unit system
            precision: Decimal places
        
        Returns:
            Formatted string with units (e.g., "0.25 in", "300 psi")
        """
        # Define display units per quantity type
        display_units = {
            'length': {'SI': 'mm', 'USC': 'in'},
            'length_large': {'SI': 'm', 'USC': 'ft'},
            'pressure': {'SI': 'MPa', 'USC': 'psi'},
            'temperature': {'SI': '°C', 'USC': '°F'},
            'corrosion_rate': {'SI': 'mm/yr', 'USC': 'mpy'},
            'mass': {'SI': 'kg', 'USC': 'lb'},
            'area': {'SI': 'm²', 'USC': 'ft²'},
            'volume': {'SI': 'm³', 'USC': 'gal'}
        }
        
        if quantity_type not in display_units:
            return f"{value:.{precision}f}"
        
        target_unit = display_units[quantity_type][unit_system.value]
        
        # Value is in SI, convert to display unit if needed
        if unit_system == UnitSystem.USC:
            # Convert from SI to USC
            si_unit = display_units[quantity_type]['SI'].replace('°', '').replace('²', '').replace('³', '').lower()
            usc_unit = target_unit.replace('°', '').lower()
            
            try:
                display_value = UnitConverter.convert(value, si_unit, usc_unit)
            except ValueError:
                display_value = value  # Fallback
        else:
            display_value = value
        
        return f"{display_value:.{precision}f} {target_unit}"


class ComponentDataStandardizer:
    """
    Standardize component input data to SI units
    """
    
    @staticmethod
    def standardize_component(component_data: Dict, input_unit_system: UnitSystem = UnitSystem.USC) -> Dict:
        """
        Convert all component data fields to SI units
        
        Args:
            component_data: Raw component data (may be mixed units)
            input_unit_system: Source unit system
        
        Returns:
            Standardized component data (all SI)
        """
        standardized = component_data.copy()
        
        # Define field → unit mapping
        field_units = {
            'operating_pressure_psig': ('pressure', 'psi'),
            'design_pressure_psig': ('pressure', 'psi'),
            'operating_temp_f': ('temperature', 'f'),
            'design_temp_f': ('temperature', 'f'),
            'diameter_inches': ('length', 'in'),
            'thickness_inches': ('length', 'in'),
            't_actual': ('length', 'in'),
            't_required': ('length', 'in'),
            'corrosion_rate_mpy': ('corrosion_rate', 'mpy'),
            'corrosion_allowance': ('length', 'in')
        }
        
        # Convert each field
        for field, (qty_type, unit) in field_units.items():
            if field in component_data:
                value = component_data[field]
                if value is not None:
                    try:
                        si_value = UnitConverter.standardize_to_si(value, unit)
                        # Rename field to SI-named field
                        si_field = field.replace('_psig', '_mpa').replace('_f', '_c').replace('_inches', '_mm').replace('_mpy', '_mmpy')
                        standardized[si_field] = si_value
                    except (ValueError, TypeError):
                        pass  # Keep original if conversion fails
        
        return standardized


def validate_unit(value: float, unit: str, expected_range: tuple) -> Dict:
    """
    Validate that a value with units is within expected range
    
    Args:
        value: Numeric value
        unit: Unit string
        expected_range: (min, max) in SI units
    
    Returns:
        {
            'valid': bool,
            'value_si': float,
            'unit_si': str,
            'message': str
        }
    """
    try:
        # Convert to SI
        value_si = UnitConverter.standardize_to_si(value, unit)
        
        # Check range
        min_val, max_val = expected_range
        if min_val <= value_si <= max_val:
            return {
                'valid': True,
                'value_si': value_si,
                'message': ''
            }
        else:
            return {
                'valid': False,
                'value_si': value_si,
                'message': f"Value {value} {unit} ({value_si:.2f} SI) outside expected range [{min_val}, {max_val}]"
            }
    
    except ValueError as e:
        return {
            'valid': False,
            'value_si': None,
            'message': str(e)
        }


# Example usage
if __name__ == '__main__':
    print("=" * 70)
    print("UNIT SYSTEM - CONVERSION EXAMPLES")
    print("=" * 70)
    
    # Example 1: Basic conversions
    print("\n1. BASIC CONVERSIONS")
    conversions = [
        (6.625, 'in', 'mm'),
        (300, 'psi', 'mpa'),
        (600, 'f', 'c'),
        (5.0, 'mpy', 'mmpy'),
        (0.5, 'in', 'mm')
    ]
    
    for value, from_u, to_u in conversions:
        result = UnitConverter.convert(value, from_u, to_u)
        print(f"  {value:8.2f} {from_u:<5} → {result:8.3f} {to_u}")
    
    # Example 2: Standardize to SI
    print("\n2. STANDARDIZE TO SI")
    values = [
        (0.500, 'in'),
        (300, 'psi'),
        (600, 'F'),
        (5.0, 'mpy')
    ]
    
    for value, unit in values:
        si_value = UnitConverter.standardize_to_si(value, unit)
        print(f"  {value:8.2f} {unit:<5} → {si_value:8.3f} (SI)")
    
    # Example 3: Display formatting
    print("\n3. DISPLAY FORMATTING")
    
    # Value in SI, format for display
    thickness_mm = 12.7  # mm (SI)
    
    usc_display = UnitConverter.format_for_display(thickness_mm, 'length', UnitSystem.USC, precision=3)
    si_display = UnitConverter.format_for_display(thickness_mm, 'length', UnitSystem.SI, precision=2)
    
    print(f"  Internal (SI):  {thickness_mm} mm")
    print(f"  Display (USC):  {usc_display}")
    print(f"  Display (SI):   {si_display}")
    
    # Example 4: Component data standardization
    print("\n4. COMPONENT DATA STANDARDIZATION")
    
    component_usc = {
        'equipment_id': 'P-101',
        'operating_pressure_psig': 300.0,
        'operating_temp_f': 600.0,
        'diameter_inches': 6.625,
        't_actual': 0.500,
        'corrosion_rate_mpy': 5.0
    }
    
    print("  Input (USC):")
    for key, value in component_usc.items():
        if isinstance(value, (int, float)):
            print(f"    {key:25s}: {value:8.2f}")
    
    standardizer = ComponentDataStandardizer()
    component_si = standardizer.standardize_component(component_usc, UnitSystem.USC)
    
    print("\n  Output (SI):")
    for key, value in component_si.items():
        if isinstance(value, (int, float)) and key not in component_usc:
            print(f"    {key:25s}: {value:8.3f}")
    
    # Example 5: Unit validation
    print("\n5. UNIT VALIDATION")
    
    validations = [
        (300, 'psi', (0, 10)),        # 300 psi in MPa range
        (600, 'F', (-50, 650)),       # 600°F in °C range
        (0.5, 'in', (5, 20))          # 0.5" in mm range
    ]
    
    for value, unit, range_si in validations:
        result = validate_unit(value, unit, range_si)
        status = "✓ VALID" if result['valid'] else "✗ INVALID"
        print(f"  {value} {unit:<5} → {result.get('value_si', 0):8.3f} SI  {status}")
        if result['message']:
            print(f"    {result['message']}")
    
    print("\n" + "=" * 70)
