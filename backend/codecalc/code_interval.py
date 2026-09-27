"""
Code-Based Inspection Interval Calculator
References: API 570 §6.3, API 510 §6.4-6.5, ASME VIII-1

Calculates inspection intervals based on code requirements (API 570/510)
and MAWP at end of interval.
"""

from typing import Dict


def calculate_code_interval_piping(
    remaining_life: float,
    piping_class: int,
    service_severity: str = 'normal'
) -> Dict:
    """
    API 570 §6.3, Table 6.1 - Piping inspection interval
    
    Interval = min(RL/2, class limit)
    
    Args:
        remaining_life: Remaining life in years
        piping_class: 1, 2, or 3
            Class 1: High consequence (flammable, toxic)
            Class 2: Medium consequence
            Class 3: Low consequence (non-flammable, non-toxic)
        service_severity: 'normal' or 'severe' (optional modifer)
    
    Returns:
        dict: {
            'interval_thickness': float,     # Thickness inspection interval (years)
            'interval_external': float,      # External visual interval (years)
            'piping_class': int,
            'class_limit': float,
            'formula': str
        }
    """
    # API 570 Table 6.1 class limits
    class_limits = {
        1: 5,   # Class 1: 5 years maximum
        2: 10,  # Class 2: 10 years maximum
        3: 10   # Class 3: 10 years maximum
    }
    
    # External visual inspection intervals
    external_intervals = {
        1: 5,   # Class 1: 5 years
        2: 5,   # Class 2: 5 years
        3: 10   # Class 3: 10 years
    }
    
    if piping_class not in [1, 2, 3]:
        raise ValueError(f"Invalid piping_class: {piping_class}. Must be 1, 2, or 3")
    
    max_interval = class_limits[piping_class]
    external_interval = external_intervals[piping_class]
    
    # Thickness inspection: min(RL/2, class limit)
    if remaining_life <= 0:
        interval_thickness = 0.5  # Immediate re-inspection
    elif remaining_life == float('inf'):
        interval_thickness = max_interval
    else:
        interval_thickness = min(remaining_life / 2, max_interval)
    
    # Apply severity modifier if needed
    if service_severity == 'severe':
        interval_thickness = min(interval_thickness, max_interval / 2)
    
    # Minimum 6 months between inspections
    interval_thickness = max(interval_thickness, 0.5)
    
    return {
        'interval_thickness': interval_thickness,
        'interval_external': external_interval,
        'piping_class': piping_class,
        'class_limit': max_interval,
        'remaining_life': remaining_life,
        'service_severity': service_severity,
        'formula': 'API 570 §6.3 Table 6.1: min(RL/2, class_limit)',
        'code': 'API 570'
    }


def calculate_code_interval_vessel(
    remaining_life: float,
    inspection_type: str = 'internal'
) -> Dict:
    """
    API 510 §6.4-6.5 - Pressure vessel inspection interval
    
    Args:
        remaining_life: Remaining life in years
        inspection_type: 'internal', 'onstream', or 'external'
    
    Returns:
        dict: {
            'interval': float,
            'interval_type': str,
            'remaining_life': float,
            'formula': str
        }
    """
    if inspection_type in ['internal', 'onstream']:
        # Internal/on-stream: min(RL/2, 10 years)
        if remaining_life <= 0:
            interval = 0.5  # Immediate
        elif remaining_life == float('inf'):
            interval = 10
        else:
            interval = min(remaining_life / 2, 10)
        
        formula = 'API 510 §6.4: min(RL/2, 10 years)'
        
    elif inspection_type == 'external':
        # External visual: 5 years
        interval = 5
        formula = 'API 510 §6.5: 5 years (external visual)'
        
    else:
        raise ValueError(f"Invalid inspection_type: {inspection_type}")
    
    # Minimum 6 months
    interval = max(interval, 0.5)
    
    return {
        'interval': interval,
        'interval_type': inspection_type,
        'remaining_life': remaining_life,
        'formula': formula,
        'code': 'API 510'
    }


def calculate_mawp(
    t_eval: float,
    component_type: str,
    design_params: Dict
) -> Dict:
    """
    Calculate MAWP (Maximum Allowable Working Pressure) at evaluated thickness
    
    Used for: MAWP at end of interval = design code formula solved for P
    
    Args:
        t_eval: Thickness at evaluation (in)
            Typically: t_eval = t_actual - (2 × CR × interval)
        component_type: 'pipe', 'vessel_circ', 'vessel_long', 'head_elliptical'
        design_params: Dict containing:
            For pipe: D, S, E, W, Y
            For vessel: R, S, E
            For head: D, S, E
    
    Returns:
        dict: {
            'MAWP': float (psig),
            't_eval': float,
            'component_type': str,
            'formula': str
        }
    """
    if component_type == 'pipe':
        # B31.3 Eq (3a) solved for P
        D = design_params['D']
        S = design_params['S']
        E = design_params.get('E', 1.0)
        W = design_params.get('W', 1.0)
        Y = design_params.get('Y', 0.4)
        
        # P = (2 × S × E × W × t) / (D - 2 × Y × t)
        MAWP = (2 * S * E * W * t_eval) / (D - 2 * Y * t_eval)
        formula = 'B31.3 §304.1.2 Eq (3a) solved for P'
        
    elif component_type == 'vessel_circ':
        # ASME VIII-1 UG-27(c)(1) solved for P - Circumferential stress
        R = design_params['R']
        S = design_params['S']
        E = design_params.get('E', 1.0)
        
        # P = (S × E × t) / (R + 0.6 × t)
        MAWP = (S * E * t_eval) / (R + 0.6 * t_eval)
        formula = 'ASME VIII-1 UG-27(c)(1) solved for P'
        
    elif component_type == 'vessel_long':
        # ASME VIII-1 UG-27(c)(2) solved for P - Longitudinal stress
        R = design_params['R']
        S = design_params['S']
        E = design_params.get('E', 1.0)
        
        # P = (2 × S × E × t) / (R - 0.4 × t)
        MAWP = (2 * S * E * t_eval) / (R - 0.4 * t_eval)
        formula = 'ASME VIII-1 UG-27(c)(2) solved for P'
        
    elif component_type == 'head_elliptical':
        # ASME VIII-1 UG-32(d) solved for P - 2:1 ellipsoidal head
        D = design_params['D']
        S = design_params['S']
        E = design_params.get('E', 1.0)
        
        # P = (2 × S × E × t) / (D + 0.2 × t)
        MAWP = (2 * S * E * t_eval) / (D + 0.2 * t_eval)
        formula = 'ASME VIII-1 UG-32(d) solved for P'
        
    elif component_type == 'tank':
        # API 653 - Tanks typically don't use MAWP concept
        # Use hydrostatic pressure instead
        H = design_params.get('H', 0)  # Liquid height (ft)
        G = design_params.get('G', 1.0)  # Specific gravity
        
        # Hydrostatic pressure at bottom (psi)
        MAWP = 0.433 * H * G
        formula = 'API 653: Hydrostatic pressure = 0.433 × H × G'
        
    else:
        raise ValueError(f"Unknown component_type: {component_type}")
    
    return {
        'MAWP': MAWP,
        't_eval': t_eval,
        'component_type': component_type,
        'formula': formula,
        'design_params': design_params
    }


def calculate_thickness_at_interval_end(
    t_actual: float,
    corrosion_rate: float,
    interval_years: float,
    units: str = 'mpy'
) -> Dict:
    """
    Calculate thickness at end of inspection interval
    
    t_eval = t_actual - (2 × CR × interval)
    
    Factor of 2 is conservative per API 570 §7.2
    
    Args:
        t_actual: Current thickness (in)
        corrosion_rate: Corrosion rate (mpy or in/yr)
        interval_years: Inspection interval (years)
        units: 'mpy' or 'in/yr'
    
    Returns:
        dict: {
            't_eval': float,
            't_loss': float,
            't_actual': float,
            'interval_years': float
        }
    """
    if units == 'mpy':
        CR_in_per_yr = corrosion_rate / 1000
    else:
        CR_in_per_yr = corrosion_rate
    
    # Conservative: 2 × CR × interval
    t_loss = 2 * CR_in_per_yr * interval_years
    t_eval = t_actual - t_loss
    
    return {
        't_eval': max(t_eval, 0),
        't_loss': t_loss,
        't_actual': t_actual,
        'interval_years': interval_years,
        'corrosion_rate': corrosion_rate,
        'units': units,
        'formula': 't_eval = t_actual - (2 × CR × interval)'
    }


def check_ffs_trigger(
    t_actual: float,
    t_required: float,
    remaining_life: float,
    plan_period: float = 10
) -> Dict:
    """
    Check if Fitness-For-Service (FFS) assessment is required
    API 579-1/ASME FFS-1
    
    Triggers:
    1. t_actual < t_required
    2. RL < plan period
    
    Args:
        t_actual: Current thickness (in)
        t_required: Minimum required thickness (in)
        remaining_life: Years
        plan_period: Planning period (typically 10 years)
    
    Returns:
        dict: {
            'ffs_required': bool,
            'trigger': str,
            'recommendation': str
        }
    """
    triggers = []
    
    if t_actual < t_required:
        triggers.append('BELOW_TMIN')
    
    if remaining_life < plan_period:
        triggers.append('SHORT_RL')
    
    if triggers:
        ffs_required = True
        trigger = ' & '.join(triggers)
        
        if 'BELOW_TMIN' in triggers:
            recommendation = 'CRITICAL: Thickness below tmin. Immediate FFS assessment required per API 579-1 Part 4 (local thin area) or Part 5 (general metal loss).'
        else:
            recommendation = f'WARNING: Remaining life ({remaining_life:.1f} years) less than plan period ({plan_period} years). FFS assessment recommended to evaluate life extension options.'
    else:
        ffs_required = False
        trigger = 'NONE'
        recommendation = 'No FFS assessment required. Component meets thickness and remaining life criteria.'
    
    return {
        'ffs_required': ffs_required,
        'trigger': trigger,
        'recommendation': recommendation,
        't_actual': t_actual,
        't_required': t_required,
        'margin': t_actual - t_required,
        'remaining_life': remaining_life,
        'plan_period': plan_period
    }


# Example usage
if __name__ == '__main__':
    print("=" * 70)
    print("CODE INTERVAL & MAWP - EXAMPLE CALCULATIONS")
    print("=" * 70)
    
    # Example 1: Piping code interval
    print("\n1. PIPING CODE INTERVAL (Class 1, RL = 15 years)")
    piping_interval = calculate_code_interval_piping(
        remaining_life=15.0,
        piping_class=1
    )
    print(f"  Remaining Life:      {piping_interval['remaining_life']:.1f} years")
    print(f"  Class Limit:         {piping_interval['class_limit']} years")
    print(f"  Thickness Interval:  {piping_interval['interval_thickness']:.1f} years")
    print(f"  External Interval:   {piping_interval['interval_external']:.1f} years")
    print(f"  Formula: {piping_interval['formula']}")
    
    # Example 2: Vessel code interval
    print("\n2. VESSEL CODE INTERVAL (RL = 8 years)")
    vessel_interval = calculate_code_interval_vessel(
        remaining_life=8.0,
        inspection_type='internal'
    )
    print(f"  Remaining Life:      {vessel_interval['remaining_life']:.1f} years")
    print(f"  Internal Interval:   {vessel_interval['interval']:.1f} years")
    print(f"  Formula: {vessel_interval['formula']}")
    
    # Example 3: MAWP calculation
    print("\n3. MAWP AT END OF INTERVAL")
    print("  Current thickness: 0.375 in, CR = 5 mpy, Interval = 5 years")
    
    # Calculate t_eval
    t_eval_result = calculate_thickness_at_interval_end(
        t_actual=0.375,
        corrosion_rate=5.0,
        interval_years=5.0,
        units='mpy'
    )
    print(f"  t_eval = t_actual - 2×CR×interval")
    print(f"  t_eval = {t_eval_result['t_eval']:.4f} in")
    print(f"  Loss   = {t_eval_result['t_loss']:.4f} in")
    
    # Calculate MAWP at t_eval
    mawp_result = calculate_mawp(
        t_eval=t_eval_result['t_eval'],
        component_type='pipe',
        design_params={
            'D': 6.625,    # 6-inch pipe OD
            'S': 15000,    # Allowable stress (psi)
            'E': 1.0,
            'W': 1.0,
            'Y': 0.4
        }
    )
    print(f"  MAWP at end of interval: {mawp_result['MAWP']:.1f} psig")
    print(f"  Formula: {mawp_result['formula']}")
    
    # Example 4: FFS trigger check
    print("\n4. FFS TRIGGER CHECK")
    ffs_check = check_ffs_trigger(
        t_actual=0.245,
        t_required=0.250,
        remaining_life=3.0,
        plan_period=10
    )
    print(f"  FFS Required: {ffs_check['ffs_required']}")
    print(f"  Trigger:      {ffs_check['trigger']}")
    print(f"  Margin:       {ffs_check['margin']:.4f} in")
    print(f"  Recommendation: {ffs_check['recommendation']}")
    
    print("\n" + "=" * 70)
