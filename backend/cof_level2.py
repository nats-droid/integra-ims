"""
Consequence of Failure (COF) Level 2
API 581 Part 3 - Advanced Consequence Modeling

Includes:
- Flash calculations
- Dispersion modeling (simplified Gaussian plume)
- Advanced consequence categories
- Equipment-specific COF
"""

import math
from typing import Dict, Optional


# ============================================================================
# FLASH CALCULATIONS
# ============================================================================

def calculate_flash_fraction(
    pressure_psig: float,
    temperature_f: float,
    molecular_weight: float,
    vapor_pressure_psia: Optional[float] = None
) -> Dict:
    """
    Calculate flash fraction for liquid release
    
    Simplified flash calculation for depressurization.
    Full implementation would use Antoine equation and thermodynamic properties.
    
    Args:
        pressure_psig: Operating pressure (psig)
        temperature_f: Operating temperature (°F)
        molecular_weight: Molecular weight (g/mol)
        vapor_pressure_psia: Vapor pressure at temperature (psia)
    
    Returns:
        {
            'flash_fraction': float,  # Fraction that flashes (0-1)
            'liquid_fraction': float,
            'vapor_fraction': float
        }
    """
    # Convert to absolute pressure
    P_abs = pressure_psig + 14.7
    
    # Estimate vapor pressure if not provided (crude approximation)
    if vapor_pressure_psia is None:
        # Simplified: Pvap increases exponentially with temperature
        # This is a placeholder - use Antoine equation in production
        T_kelvin = (temperature_f - 32) * 5/9 + 273.15
        vapor_pressure_psia = 14.7 * math.exp((T_kelvin - 273.15) / 100)
    
    # Flash fraction (simplified)
    if P_abs > vapor_pressure_psia:
        # Above vapor pressure: some liquid flashes to vapor
        # Flash fraction ≈ (P - Pvap) / P
        flash_fraction = min((P_abs - vapor_pressure_psia) / P_abs, 1.0)
    else:
        # Below vapor pressure: all vapor
        flash_fraction = 1.0
    
    # Ensure reasonable bounds
    flash_fraction = max(0.0, min(1.0, flash_fraction))
    
    liquid_fraction = 1.0 - flash_fraction
    vapor_fraction = flash_fraction
    
    return {
        'flash_fraction': flash_fraction,
        'liquid_fraction': liquid_fraction,
        'vapor_fraction': vapor_fraction,
        'vapor_pressure_psia': vapor_pressure_psia,
        'operating_pressure_psia': P_abs
    }


# ============================================================================
# DISPERSION MODELING (Gaussian Plume)
# ============================================================================

def calculate_dispersion(
    release_rate_kg_s: float,
    wind_speed_m_s: float,
    atmospheric_stability: str = 'D',
    distance_m: float = 100
) -> Dict:
    """
    Simplified Gaussian plume dispersion model
    
    C(x,y,z) = (Q / (2π u σy σz)) × exp(-y²/(2σy²)) × exp(-z²/(2σz²))
    
    Args:
        release_rate_kg_s: Release rate (kg/s)
        wind_speed_m_s: Wind speed (m/s)
        atmospheric_stability: Pasquill stability class (A-F)
        distance_m: Downwind distance (m)
    
    Returns:
        {
            'concentration_ppm': float,  # Ground-level centerline concentration
            'sigma_y': float,            # Lateral dispersion coefficient
            'sigma_z': float,            # Vertical dispersion coefficient
            'plume_width': float         # Plume width at distance (m)
        }
    """
    # Pasquill-Gifford dispersion coefficients
    # Simplified parameterization
    stability_params = {
        'A': {'a_y': 0.22, 'b_y': 0.894, 'a_z': 0.20, 'b_z': 0.894},  # Very unstable
        'B': {'a_y': 0.16, 'b_y': 0.894, 'a_z': 0.12, 'b_z': 0.894},  # Unstable
        'C': {'a_y': 0.11, 'b_y': 0.894, 'a_z': 0.08, 'b_z': 0.894},  # Slightly unstable
        'D': {'a_y': 0.08, 'b_y': 0.894, 'a_z': 0.06, 'b_z': 0.894},  # Neutral
        'E': {'a_y': 0.06, 'b_y': 0.894, 'a_z': 0.03, 'b_z': 0.894},  # Slightly stable
        'F': {'a_y': 0.04, 'b_y': 0.894, 'a_z': 0.016, 'b_z': 0.894}  # Stable
    }
    
    params = stability_params.get(atmospheric_stability, stability_params['D'])
    
    # Dispersion coefficients at distance x
    sigma_y = params['a_y'] * (distance_m ** params['b_y'])
    sigma_z = params['a_z'] * (distance_m ** params['b_z'])
    
    # Ground-level centerline concentration (y=0, z=0)
    # C = Q / (π u σy σz)
    if wind_speed_m_s > 0 and sigma_y > 0 and sigma_z > 0:
        concentration_kg_m3 = release_rate_kg_s / (math.pi * wind_speed_m_s * sigma_y * sigma_z)
    else:
        concentration_kg_m3 = 0.0
    
    # Convert to ppm (very approximate - depends on molecular weight)
    # Assume air density ~1.2 kg/m³, MW~50 g/mol
    concentration_ppm = concentration_kg_m3 * 1000  # Simplified
    
    # Plume width (2σy at ground level)
    plume_width = 2 * sigma_y
    
    return {
        'concentration_ppm': concentration_ppm,
        'concentration_kg_m3': concentration_kg_m3,
        'sigma_y': sigma_y,
        'sigma_z': sigma_z,
        'plume_width': plume_width,
        'distance_m': distance_m,
        'atmospheric_stability': atmospheric_stability
    }


# ============================================================================
# ADVANCED COF CATEGORIES
# ============================================================================

def calculate_advanced_cof(
    flammable_mass_kg: float,
    toxic: bool = False,
    toxic_concentration_ppm: float = 0,
    population_density: str = 'low',
    equipment_density: str = 'low',
    environmental_sensitivity: str = 'low'
) -> Dict:
    """
    Advanced COF calculation with multiple consequence categories
    
    Categories:
    - Flammable consequence
    - Toxic consequence
    - Environmental consequence
    - Business interruption
    
    Args:
        flammable_mass_kg: Mass of flammable material (kg)
        toxic: True if toxic material
        toxic_concentration_ppm: Toxic concentration at receptor
        population_density: 'low', 'medium', 'high'
        equipment_density: 'low', 'medium', 'high'
        environmental_sensitivity: 'low', 'medium', 'high'
    
    Returns:
        {
            'total_cof': float,
            'flammable_cof': float,
            'toxic_cof': float,
            'environmental_cof': float,
            'business_cof': float
        }
    """
    # Flammable consequence (area affected)
    # Simplified: area ∝ mass^(2/3)
    flammable_cof = 100 * (flammable_mass_kg ** (2/3))
    
    # Toxic consequence
    if toxic and toxic_concentration_ppm > 0:
        # Population density factors
        pop_factors = {'low': 1, 'medium': 5, 'high': 10}
        pop_factor = pop_factors.get(population_density, 1)
        
        # Toxic impact ∝ concentration × population
        toxic_cof = toxic_concentration_ppm * pop_factor
    else:
        toxic_cof = 0
    
    # Environmental consequence
    env_factors = {'low': 1, 'medium': 5, 'high': 10}
    env_factor = env_factors.get(environmental_sensitivity, 1)
    environmental_cof = flammable_mass_kg * env_factor * 0.1
    
    # Business interruption
    equip_factors = {'low': 1, 'medium': 5, 'high': 10}
    equip_factor = equip_factors.get(equipment_density, 1)
    business_cof = flammable_mass_kg * equip_factor * 0.2
    
    # Total COF
    total_cof = flammable_cof + toxic_cof + environmental_cof + business_cof
    
    return {
        'total_cof': total_cof,
        'flammable_cof': flammable_cof,
        'toxic_cof': toxic_cof,
        'environmental_cof': environmental_cof,
        'business_cof': business_cof,
        'breakdown': {
            'flammable_pct': (flammable_cof / total_cof * 100) if total_cof > 0 else 0,
            'toxic_pct': (toxic_cof / total_cof * 100) if total_cof > 0 else 0,
            'environmental_pct': (environmental_cof / total_cof * 100) if total_cof > 0 else 0,
            'business_pct': (business_cof / total_cof * 100) if total_cof > 0 else 0
        }
    }


def calculate_equipment_specific_cof(
    equipment_type: str,
    inventory_kg: float,
    operating_pressure_psig: float,
    diameter_m: float
) -> Dict:
    """
    Equipment-specific COF adjustments
    
    Different equipment types have different consequence profiles
    
    Args:
        equipment_type: 'pipe', 'vessel', 'tank', 'heat_exchanger', 'compressor'
        inventory_kg: Material inventory (kg)
        operating_pressure_psig: Operating pressure
        diameter_m: Characteristic dimension
    
    Returns:
        {
            'base_cof': float,
            'equipment_factor': float,
            'adjusted_cof': float
        }
    """
    # Base COF from inventory
    base_cof = 100 * (inventory_kg ** (2/3))
    
    # Equipment-specific factors
    equipment_factors = {
        'pipe': 0.5,            # Small inventory, distributed
        'vessel': 1.0,          # Standard
        'tank': 1.5,            # Large inventory
        'heat_exchanger': 0.8,  # Medium inventory
        'compressor': 1.2,      # High energy, mechanical
        'reactor': 1.5,         # High consequence
        'column': 1.3           # Large inventory, tall
    }
    
    equipment_factor = equipment_factors.get(equipment_type, 1.0)
    
    # Pressure adjustment (higher pressure = higher consequence)
    if operating_pressure_psig > 600:
        pressure_factor = 1.5
    elif operating_pressure_psig > 300:
        pressure_factor = 1.2
    else:
        pressure_factor = 1.0
    
    # Size adjustment (larger equipment = higher consequence)
    if diameter_m > 3:
        size_factor = 1.3
    elif diameter_m > 1:
        size_factor = 1.1
    else:
        size_factor = 1.0
    
    adjusted_cof = base_cof * equipment_factor * pressure_factor * size_factor
    
    return {
        'base_cof': base_cof,
        'equipment_factor': equipment_factor,
        'pressure_factor': pressure_factor,
        'size_factor': size_factor,
        'adjusted_cof': adjusted_cof
    }


# Example usage
if __name__ == '__main__':
    print("=" * 70)
    print("COF LEVEL 2 - EXAMPLE CALCULATIONS")
    print("=" * 70)
    
    # Example 1: Flash calculation
    print("\n1. FLASH CALCULATION (Liquid release at 300 psig, 600°F)")
    flash = calculate_flash_fraction(
        pressure_psig=300,
        temperature_f=600,
        molecular_weight=100
    )
    print(f"  Flash fraction:     {flash['flash_fraction']:.3f}")
    print(f"  Liquid fraction:    {flash['liquid_fraction']:.3f}")
    print(f"  Vapor fraction:     {flash['vapor_fraction']:.3f}")
    print(f"  Vapor pressure:     {flash['vapor_pressure_psia']:.1f} psia")
    
    # Example 2: Dispersion modeling
    print("\n2. DISPERSION MODELING (10 kg/s release, 100m downwind)")
    dispersion = calculate_dispersion(
        release_rate_kg_s=10.0,
        wind_speed_m_s=3.0,
        atmospheric_stability='D',
        distance_m=100
    )
    print(f"  Concentration:      {dispersion['concentration_ppm']:.1f} ppm")
    print(f"  Sigma Y:            {dispersion['sigma_y']:.2f} m")
    print(f"  Sigma Z:            {dispersion['sigma_z']:.2f} m")
    print(f"  Plume width:        {dispersion['plume_width']:.1f} m")
    
    # Example 3: Advanced COF
    print("\n3. ADVANCED COF (1000 kg flammable, toxic)")
    advanced_cof = calculate_advanced_cof(
        flammable_mass_kg=1000,
        toxic=True,
        toxic_concentration_ppm=100,
        population_density='medium',
        equipment_density='high',
        environmental_sensitivity='medium'
    )
    print(f"  Total COF:          {advanced_cof['total_cof']:.1f}")
    print(f"  Flammable COF:      {advanced_cof['flammable_cof']:.1f} ({advanced_cof['breakdown']['flammable_pct']:.1f}%)")
    print(f"  Toxic COF:          {advanced_cof['toxic_cof']:.1f} ({advanced_cof['breakdown']['toxic_pct']:.1f}%)")
    print(f"  Environmental COF:  {advanced_cof['environmental_cof']:.1f} ({advanced_cof['breakdown']['environmental_pct']:.1f}%)")
    print(f"  Business COF:       {advanced_cof['business_cof']:.1f} ({advanced_cof['breakdown']['business_pct']:.1f}%)")
    
    # Example 4: Equipment-specific COF
    print("\n4. EQUIPMENT-SPECIFIC COF (Pressure vessel)")
    equip_cof = calculate_equipment_specific_cof(
        equipment_type='vessel',
        inventory_kg=500,
        operating_pressure_psig=400,
        diameter_m=1.5
    )
    print(f"  Base COF:           {equip_cof['base_cof']:.1f}")
    print(f"  Equipment factor:   {equip_cof['equipment_factor']:.2f}")
    print(f"  Pressure factor:    {equip_cof['pressure_factor']:.2f}")
    print(f"  Size factor:        {equip_cof['size_factor']:.2f}")
    print(f"  Adjusted COF:       {equip_cof['adjusted_cof']:.1f}")
    
    print("\n" + "=" * 70)
