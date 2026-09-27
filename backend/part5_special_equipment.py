"""
Part 5 Special Equipment Calculations
API 581 Part 5 - Tanks, Heat Exchangers, PRDs, Steam Systems

Special equipment types not covered by standard piping/vessel calculations.
"""

import math
from typing import Dict, Optional, List
from datetime import datetime


# ============================================================================
# TANK BOTTOM CALCULATIONS (API 653)
# ============================================================================

def calculate_tank_bottom_pof(
    tank_age_years: float,
    welded: bool = True,
    maintained: bool = True,
    settlement_monitoring: str = 'meets',
    soil_corrosivity: str = 'low',
    cathodic_protection: bool = False,
    release_prevention_barrier: bool = False
) -> Dict:
    """
    API 581 Part 5 - Tank Bottom POF
    
    POF_tank = F_WD × F_AM × F_SM × F_soil × F_cp × base_rate
    
    Args:
        tank_age_years: Age of tank (years)
        welded: True if welded construction, False if riveted
        maintained: True if well-maintained (regular inspections)
        settlement_monitoring: 'exceeds', 'meets', 'never' performed
        soil_corrosivity: 'low', 'medium', 'high'
        cathodic_protection: True if CP system installed and working
        release_prevention_barrier: True if RPB (liner) installed
    
    Returns:
        {
            'pof': float,           # Probability of failure (yr^-1)
            'factors': dict,        # Individual factors
            'base_rate': float,
            'age_factor': float
        }
    """
    # F_WD: Welded vs Riveted
    # Welded construction is more reliable
    F_WD = 1.0 if welded else 10.0
    
    # F_AM: Asset Management (maintenance quality)
    # Regular inspections and maintenance reduce risk
    F_AM = 1.0 if maintained else 5.0
    
    # F_SM: Settlement Monitoring
    # Settlement monitoring frequency
    settlement_factors = {
        'exceeds': 2.0,   # Monitoring exceeds requirements
        'meets': 1.0,     # Meets requirements
        'never': 1.5      # Never monitored
    }
    F_SM = settlement_factors.get(settlement_monitoring, 1.0)
    
    # F_soil: Soil Corrosivity
    soil_factors = {
        'low': 1.0,
        'medium': 2.0,
        'high': 4.0
    }
    F_soil = soil_factors.get(soil_corrosivity, 1.0)
    
    # F_cp: Cathodic Protection
    F_cp = 0.5 if cathodic_protection else 1.0
    
    # F_rpb: Release Prevention Barrier
    F_rpb = 0.3 if release_prevention_barrier else 1.0
    
    # Base rate (API 581 typical value)
    # This is a simplified model - actual API 581 has more detailed tables
    base_rate = 0.0001  # yr^-1
    
    # Age factor (POF increases with age)
    if tank_age_years < 20:
        age_factor = 1.0
    elif tank_age_years < 40:
        age_factor = 1.5
    else:
        age_factor = 2.0
    
    # Total POF
    pof = base_rate * F_WD * F_AM * F_SM * F_soil * F_cp * F_rpb * age_factor
    
    return {
        'pof': pof,
        'factors': {
            'F_WD': F_WD,
            'F_AM': F_AM,
            'F_SM': F_SM,
            'F_soil': F_soil,
            'F_cp': F_cp,
            'F_rpb': F_rpb,
            'age_factor': age_factor
        },
        'base_rate': base_rate,
        'interpretation': _interpret_tank_pof(pof)
    }


def _interpret_tank_pof(pof: float) -> str:
    """Interpret tank bottom POF"""
    if pof < 0.0001:
        return "Very Low - Excellent condition"
    elif pof < 0.001:
        return "Low - Good condition"
    elif pof < 0.01:
        return "Medium - Monitor closely"
    else:
        return "High - Action required"


# ============================================================================
# HEAT EXCHANGER BUNDLE (Weibull Distribution)
# ============================================================================

def calculate_heat_exchanger_pof(
    tube_count: int,
    years_in_service: float,
    mean_time_to_failure: float,
    plugged_tubes: int = 0,
    tube_rotations: int = 0,
    retubed: bool = False,
    retube_percentage: float = 1.0
) -> Dict:
    """
    API 581 Part 5 - Heat Exchanger Bundle POF
    
    Uses Weibull distribution:
    Pf = 1 - exp(-(t/η)^β)
    
    Where:
    - t = time in service
    - η (eta) = characteristic life (MTTF adjusted for maintenance)
    - β (beta) = shape parameter (from tube count)
    
    Args:
        tube_count: Number of tubes in bundle
        years_in_service: Years since installation or last retube
        mean_time_to_failure: MTTF from historical data (years)
        plugged_tubes: Number of tubes plugged
        tube_rotations: Number of times bundle rotated
        retubed: True if bundle was retubed
        retube_percentage: Percentage retubed (0.0-1.0)
    
    Returns:
        {
            'pof': float,
            'beta': float,
            'eta': float,
            'eta_adjusted': float,
            'life_extension_factor': float
        }
    """
    # Beta (shape parameter) from tube count
    # More tubes = higher beta = sharper "wear-out" behavior
    if tube_count < 100:
        beta = 1.5
    elif tube_count < 500:
        beta = 2.0
    elif tube_count < 1000:
        beta = 2.5
    else:
        beta = 3.0
    
    # Life extension factors
    life_extension_factor = 1.0
    
    # Plugging: Each 10% of tubes plugged adds 10% life extension
    plug_percentage = plugged_tubes / tube_count
    plug_extension = 1.0 + (0.1 * (plug_percentage * 10))
    life_extension_factor *= plug_extension
    
    # Rotation: Each rotation adds 50% life extension
    rotation_extension = 1.0 + (0.5 * tube_rotations)
    life_extension_factor *= rotation_extension
    
    # Retube: Significant life extension based on % retubed
    if retubed:
        retube_extension = 1.0 + (retube_percentage * 0.9)  # 90% extension if fully retubed
        life_extension_factor *= retube_extension
    
    # Adjusted eta (characteristic life)
    eta = mean_time_to_failure
    eta_adjusted = eta * life_extension_factor
    
    # Weibull POF
    if years_in_service <= 0:
        pof = 0.0
    else:
        pof = 1.0 - math.exp(-((years_in_service / eta_adjusted) ** beta))
    
    return {
        'pof': pof,
        'beta': beta,
        'eta': eta,
        'eta_adjusted': eta_adjusted,
        'life_extension_factor': life_extension_factor,
        'years_in_service': years_in_service,
        'plugged_percentage': plug_percentage * 100,
        'interpretation': _interpret_hx_pof(pof)
    }


def _interpret_hx_pof(pof: float) -> str:
    """Interpret heat exchanger POF"""
    if pof < 0.1:
        return "Low - Early life"
    elif pof < 0.3:
        return "Medium - Mid life"
    elif pof < 0.5:
        return "High - Approaching end of life"
    else:
        return "Very High - Beyond design life"


# ============================================================================
# PRESSURE RELIEF DEVICE (PRD)
# ============================================================================

def calculate_prd_pof(
    demand_rate_per_year: float,
    test_interval_years: float,
    test_effectiveness: str = 'good',
    last_test_result: str = 'pass',
    service_severity: str = 'clean'
) -> Dict:
    """
    API 581 Part 5 - Pressure Relief Device POF
    
    POF = P_fod × DR × P_f
    
    Where:
    - P_fod = Probability of failure on demand
    - DR = Demand rate (demands per year)
    - P_f = Probability of failure due to fouling/sticking
    
    Args:
        demand_rate_per_year: Expected demands per year
        test_interval_years: Years between tests
        test_effectiveness: 'excellent', 'good', 'fair', 'poor'
        last_test_result: 'pass', 'minor_issues', 'major_issues'
        service_severity: 'clean', 'moderate', 'severe' (fouling/plugging)
    
    Returns:
        {
            'pof': float,
            'p_fod': float,
            'p_fail': float,
            'expected_failures_per_year': float
        }
    """
    # Base failure-on-demand probability
    base_p_fod = 0.01  # 1% base rate
    
    # Test effectiveness modifier
    test_factors = {
        'excellent': 0.5,
        'good': 1.0,
        'fair': 1.5,
        'poor': 2.0
    }
    test_factor = test_factors.get(test_effectiveness, 1.0)
    
    # Last test result modifier
    test_result_factors = {
        'pass': 1.0,
        'minor_issues': 1.5,
        'major_issues': 3.0
    }
    test_result_factor = test_result_factors.get(last_test_result, 1.0)
    
    # Test interval modifier (longer interval = higher POF)
    interval_factor = math.sqrt(test_interval_years)
    
    # Service severity (fouling/plugging)
    severity_factors = {
        'clean': 1.0,
        'moderate': 2.0,
        'severe': 4.0
    }
    severity_factor = severity_factors.get(service_severity, 1.0)
    
    # Probability of failure on demand
    p_fod = base_p_fod * test_factor * test_result_factor * interval_factor * severity_factor
    
    # Probability of failure (leak)
    p_fail = 0.001 * severity_factor  # Simplified
    
    # Total POF (per year)
    pof = (p_fod * demand_rate_per_year) + p_fail
    
    # Expected failures per year
    expected_failures = pof
    
    return {
        'pof': pof,
        'p_fod': p_fod,
        'p_fail': p_fail,
        'demand_rate': demand_rate_per_year,
        'expected_failures_per_year': expected_failures,
        'interpretation': _interpret_prd_pof(pof)
    }


def _interpret_prd_pof(pof: float) -> str:
    """Interpret PRD POF"""
    if pof < 0.01:
        return "Low - Reliable operation"
    elif pof < 0.05:
        return "Medium - Monitor performance"
    else:
        return "High - Frequent testing recommended"


# ============================================================================
# STEAM SYSTEM
# ============================================================================

def calculate_steam_system_pof(
    base_pof: float,
    design_factor: float = 1.0,
    operation_factor: float = 1.0,
    maintenance_factor: float = 1.0,
    configuration: str = 'single',
    redundancy_factor: float = 1.0
) -> Dict:
    """
    API 581 Part 5 - Steam System POF
    
    η_adj = η_def × F_D × F_O × F_M × F_config
    
    Args:
        base_pof: Base POF for component type
        design_factor: Design quality factor (0.5-2.0)
        operation_factor: Operating severity factor (0.5-2.0)
        maintenance_factor: Maintenance quality factor (0.5-2.0)
        configuration: 'single', 'series', 'parallel'
        redundancy_factor: Redundancy factor (0.5-1.0)
    
    Returns:
        {
            'pof': float,
            'adjusted_pof': float,
            'configuration': str
        }
    """
    # Configuration modifiers
    config_factors = {
        'single': 1.0,
        'series': 1.5,    # Series: failure of any component fails system
        'parallel': 0.5   # Parallel: redundancy reduces risk
    }
    config_factor = config_factors.get(configuration, 1.0)
    
    # Adjusted POF
    adjusted_pof = (
        base_pof * 
        design_factor * 
        operation_factor * 
        maintenance_factor * 
        config_factor *
        redundancy_factor
    )
    
    return {
        'pof': adjusted_pof,
        'base_pof': base_pof,
        'factors': {
            'design': design_factor,
            'operation': operation_factor,
            'maintenance': maintenance_factor,
            'configuration': config_factor,
            'redundancy': redundancy_factor
        },
        'configuration': configuration,
        'interpretation': _interpret_steam_pof(adjusted_pof)
    }


def _interpret_steam_pof(pof: float) -> str:
    """Interpret steam system POF"""
    if pof < 0.001:
        return "Low - Well designed and maintained"
    elif pof < 0.01:
        return "Medium - Standard system"
    else:
        return "High - Attention needed"


# Example usage and validation
if __name__ == '__main__':
    print("=" * 70)
    print("PART 5 SPECIAL EQUIPMENT - EXAMPLE CALCULATIONS")
    print("=" * 70)
    
    # Example 1: Tank Bottom
    print("\n1. TANK BOTTOM POF (30-year old, welded, well-maintained)")
    tank = calculate_tank_bottom_pof(
        tank_age_years=30,
        welded=True,
        maintained=True,
        settlement_monitoring='meets',
        soil_corrosivity='medium',
        cathodic_protection=True,
        release_prevention_barrier=False
    )
    print(f"  POF:           {tank['pof']:.6f} yr^-1")
    print(f"  Interpretation: {tank['interpretation']}")
    print(f"  Factors:")
    for factor, value in tank['factors'].items():
        print(f"    {factor:15s}: {value:.2f}")
    
    # Example 2: Heat Exchanger
    print("\n2. HEAT EXCHANGER POF (500 tubes, 10 years service)")
    hx = calculate_heat_exchanger_pof(
        tube_count=500,
        years_in_service=10,
        mean_time_to_failure=15,
        plugged_tubes=25,
        tube_rotations=1,
        retubed=False
    )
    print(f"  POF:             {hx['pof']:.4f}")
    print(f"  Beta (shape):    {hx['beta']:.2f}")
    print(f"  Eta (MTTF):      {hx['eta']:.1f} years")
    print(f"  Eta adjusted:    {hx['eta_adjusted']:.1f} years")
    print(f"  Life extension:  {hx['life_extension_factor']:.2f}x")
    print(f"  Plugged:         {hx['plugged_percentage']:.1f}%")
    print(f"  Interpretation:  {hx['interpretation']}")
    
    # Example 3: Pressure Relief Device
    print("\n3. PRESSURE RELIEF DEVICE POF (2 demands/year, 3-year test)")
    prd = calculate_prd_pof(
        demand_rate_per_year=2.0,
        test_interval_years=3.0,
        test_effectiveness='good',
        last_test_result='pass',
        service_severity='clean'
    )
    print(f"  POF:                      {prd['pof']:.6f} yr^-1")
    print(f"  P(failure on demand):     {prd['p_fod']:.4f}")
    print(f"  P(leak):                  {prd['p_fail']:.6f}")
    print(f"  Expected failures/year:   {prd['expected_failures_per_year']:.4f}")
    print(f"  Interpretation:           {prd['interpretation']}")
    
    # Example 4: Steam System
    print("\n4. STEAM SYSTEM POF (Parallel configuration)")
    steam = calculate_steam_system_pof(
        base_pof=0.005,
        design_factor=0.8,
        operation_factor=1.2,
        maintenance_factor=0.9,
        configuration='parallel',
        redundancy_factor=0.7
    )
    print(f"  Base POF:       {steam['base_pof']:.6f} yr^-1")
    print(f"  Adjusted POF:   {steam['pof']:.6f} yr^-1")
    print(f"  Configuration:  {steam['configuration']}")
    print(f"  Interpretation: {steam['interpretation']}")
    print(f"  Factor breakdown:")
    for factor, value in steam['factors'].items():
        print(f"    {factor:15s}: {value:.2f}")
    
    print("\n" + "=" * 70)
