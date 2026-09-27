"""
Required Thickness (tmin) Calculator
References: B31.3, ASME VIII-1, API 653, API 574

Calculates minimum required thickness per design code before RBI analysis.
"""

import math


def calculate_tmin_piping_pressure(P, D, S, E, W=1.0, Y=0.4):
    """
    B31.3 §304.1.2 Eq (3a) - Straight pipe under internal pressure
    
    Args:
        P: Design pressure (psig)
        D: Outside diameter (in)
        S: Allowable stress at design temperature (psi)
        E: Quality factor (0.85-1.0, typically 1.0 for seamless)
        W: Weld joint strength reduction factor (default 1.0)
        Y: Temperature coefficient from Table 304.1.1 (default 0.4)
    
    Returns:
        dict: {
            't': Required thickness (in),
            'formula': 'B31.3 Eq (3a)',
            'parameters': {...}
        }
    """
    t = (P * D) / (2 * (S * E * W + P * Y))
    
    return {
        't': t,
        'formula': 'B31.3 §304.1.2 Eq (3a)',
        'parameters': {
            'P': P,
            'D': D,
            'S': S,
            'E': E,
            'W': W,
            'Y': Y
        }
    }


def get_structural_tmin(NPS, T_design):
    """
    API 574 structural minimum thickness table
    
    Provides minimum wall thickness for structural integrity
    independent of pressure requirements.
    
    Args:
        NPS: Nominal pipe size (in)
        T_design: Design temperature (°F)
    
    Returns:
        float: Structural minimum thickness (in)
    """
    # API 574 Table (verify table number in your edition)
    # NPS range: (min_NPS, max_NPS): {(min_temp, max_temp): tmin}
    structural_table = {
        (0, 1): {
            (-20, 400): 0.065,
            (400, 650): 0.065,
            (650, 900): 0.083
        },
        (1.25, 2): {
            (-20, 400): 0.065,
            (400, 650): 0.083,
            (650, 900): 0.109
        },
        (2.5, 3): {
            (-20, 400): 0.083,
            (400, 650): 0.083,
            (650, 900): 0.120
        },
        (4, 6): {
            (-20, 400): 0.083,
            (400, 650): 0.109,
            (650, 900): 0.134
        },
        (8, 10): {
            (-20, 400): 0.109,
            (400, 650): 0.134,
            (650, 900): 0.188
        },
        (12, 16): {
            (-20, 400): 0.156,
            (400, 650): 0.188,
            (650, 900): 0.250
        },
        (18, 24): {
            (-20, 400): 0.188,
            (400, 650): 0.219,
            (650, 900): 0.312
        }
    }
    
    # Find matching NPS range
    for nps_range, temp_dict in structural_table.items():
        if nps_range[0] <= NPS <= nps_range[1]:
            # Find matching temperature range
            for temp_range, tmin in temp_dict.items():
                if temp_range[0] <= T_design < temp_range[1]:
                    return tmin
    
    # Conservative fallback if outside table range
    return 0.083


def calculate_tmin_piping(P, D, S, E, NPS, T_design, W=1.0, Y=0.4, corrosion_allowance=0.0):
    """
    Complete piping tmin = max(pressure, structural) + corrosion allowance
    
    Args:
        P: Design pressure (psig)
        D: Outside diameter (in)
        S: Allowable stress (psi)
        E: Quality factor
        NPS: Nominal pipe size
        T_design: Design temperature (°F)
        W: Weld joint factor (default 1.0)
        Y: Temperature coefficient (default 0.4)
        corrosion_allowance: Additional thickness for corrosion (in)
    
    Returns:
        dict: Complete tmin calculation with breakdown
    """
    # Pressure requirement
    pressure_result = calculate_tmin_piping_pressure(P, D, S, E, W, Y)
    t_pressure = pressure_result['t']
    
    # Structural requirement
    t_structural = get_structural_tmin(NPS, T_design)
    
    # Governing thickness
    t_required_base = max(t_pressure, t_structural)
    
    # With corrosion allowance (B31.3 §304.1.1)
    tm = t_required_base + corrosion_allowance
    
    return {
        't_pressure': t_pressure,
        't_structural': t_structural,
        't_required_base': t_required_base,
        'corrosion_allowance': corrosion_allowance,
        'tm': tm,
        'governing': 'pressure' if t_pressure > t_structural else 'structural',
        'code': 'B31.3',
        'formula_pressure': 'B31.3 §304.1.2 Eq (3a)',
        'formula_structural': 'API 574 Table',
        'parameters': pressure_result['parameters']
    }


def calculate_tmin_vessel_shell(P, R, S, E, stress_type='circumferential'):
    """
    ASME VIII-1 UG-27 - Cylindrical shell under internal pressure
    
    Args:
        P: Design pressure (psig)
        R: Inside radius (in) or diameter/2
        S: Allowable stress (psi)
        E: Joint efficiency (0.85-1.0)
        stress_type: 'circumferential', 'longitudinal', or 'sphere'
    
    Returns:
        dict: {
            't': Required thickness (in),
            'formula': str,
            'stress_type': str
        }
    """
    if stress_type == 'circumferential':
        # UG-27(c)(1)
        t = (P * R) / (S * E - 0.6 * P)
        formula = 'ASME VIII-1 UG-27(c)(1)'
        
    elif stress_type == 'longitudinal':
        # UG-27(c)(2)
        t = (P * R) / (2 * S * E + 0.4 * P)
        formula = 'ASME VIII-1 UG-27(c)(2)'
        
    elif stress_type == 'sphere':
        # UG-27(d)
        t = (P * R) / (2 * S * E - 0.2 * P)
        formula = 'ASME VIII-1 UG-27(d)'
        
    else:
        raise ValueError(f"Unknown stress_type: {stress_type}")
    
    return {
        't': t,
        'formula': formula,
        'stress_type': stress_type,
        'parameters': {
            'P': P,
            'R': R,
            'S': S,
            'E': E
        }
    }


def calculate_tmin_vessel_head(P, D, S, E, head_type='elliptical_2to1'):
    """
    ASME VIII-1 UG-32 - Formed heads
    
    Args:
        P: Design pressure (psig)
        D: Inside diameter (in)
        S: Allowable stress (psi)
        E: Joint efficiency
        head_type: 'elliptical_2to1', 'hemispherical', 'torispherical', 'conical'
    
    Returns:
        dict: Required thickness for head
    """
    if head_type == 'elliptical_2to1':
        # UG-32(d) - 2:1 ellipsoidal head (most common)
        t = (P * D) / (2 * S * E - 0.2 * P)
        formula = 'ASME VIII-1 UG-32(d)'
        
    elif head_type == 'hemispherical':
        # UG-32(a)
        R = D / 2
        t = (P * R) / (2 * S * E - 0.2 * P)
        formula = 'ASME VIII-1 UG-32(a)'
        
    elif head_type == 'torispherical':
        # UG-32(c) - More complex, needs L, r
        # Simplified for now
        t = (P * D) / (2 * S * E - 0.2 * P) * 1.77  # M factor approximation
        formula = 'ASME VIII-1 UG-32(c) simplified'
        
    else:
        raise ValueError(f"Unknown head_type: {head_type}")
    
    return {
        't': t,
        'formula': formula,
        'head_type': head_type,
        'parameters': {
            'P': P,
            'D': D,
            'S': S,
            'E': E
        }
    }


def calculate_tmin_vessel(P, R_or_D, S, E, component_type='shell', corrosion_allowance=0.0):
    """
    Complete vessel tmin (shell or head)
    
    For shell: returns max of circumferential and longitudinal
    For head: returns head thickness
    
    Args:
        P: Design pressure (psig)
        R_or_D: Inside radius (shell) or diameter (head) (in)
        S: Allowable stress (psi)
        E: Joint efficiency
        component_type: 'shell', 'head_elliptical', 'head_hemispherical'
        corrosion_allowance: Additional thickness (in)
    
    Returns:
        dict: Complete tmin calculation
    """
    if component_type == 'shell':
        # Calculate both stress directions
        t_circ_result = calculate_tmin_vessel_shell(P, R_or_D, S, E, 'circumferential')
        t_long_result = calculate_tmin_vessel_shell(P, R_or_D, S, E, 'longitudinal')
        
        t_circ = t_circ_result['t']
        t_long = t_long_result['t']
        
        # Governing thickness
        t_required_base = max(t_circ, t_long)
        governing = 'circumferential' if t_circ > t_long else 'longitudinal'
        
        tm = t_required_base + corrosion_allowance
        
        return {
            't_circumferential': t_circ,
            't_longitudinal': t_long,
            't_required_base': t_required_base,
            'corrosion_allowance': corrosion_allowance,
            'tm': tm,
            'governing': governing,
            'code': 'ASME VIII-1',
            'formula_circ': t_circ_result['formula'],
            'formula_long': t_long_result['formula'],
            'parameters': t_circ_result['parameters']
        }
    
    elif component_type.startswith('head_'):
        head_type = component_type.replace('head_', '')
        head_result = calculate_tmin_vessel_head(P, R_or_D, S, E, head_type)
        
        tm = head_result['t'] + corrosion_allowance
        
        return {
            't_required_base': head_result['t'],
            'corrosion_allowance': corrosion_allowance,
            'tm': tm,
            'code': 'ASME VIII-1',
            'formula': head_result['formula'],
            'head_type': head_type,
            'parameters': head_result['parameters']
        }
    
    else:
        raise ValueError(f"Unknown component_type: {component_type}")


def calculate_tmin_tank_shell(H, D, G, S, E, course_height=None):
    """
    API 653 §4.3.3.1 - Tank shell minimum thickness
    
    Args:
        H: Design liquid height (ft)
        D: Tank diameter (ft)
        G: Specific gravity of liquid
        S: Allowable stress (psi)
        E: Joint efficiency
        course_height: Height of specific course (ft) - if None, uses bottom course
    
    Returns:
        dict: Tank shell tmin calculation
    """
    # API 653 equation (US units)
    if course_height is not None:
        H_effective = H - course_height
    else:
        H_effective = H  # Bottom course
    
    tmin = 2.6 * (H_effective - 1) * D * G / (S * E)
    
    # API 653 absolute minimums
    if H <= 24:
        tmin_absolute = 0.1  # inches
    else:
        tmin_absolute = 0.1 + 0.004 * (H - 24)
    
    tm = max(tmin, tmin_absolute)
    
    return {
        't_calculated': tmin,
        't_absolute_min': tmin_absolute,
        'tm': tm,
        'governing': 'calculated' if tmin > tmin_absolute else 'absolute_minimum',
        'code': 'API 653',
        'formula': 'API 653 §4.3.3.1',
        'parameters': {
            'H': H,
            'H_effective': H_effective,
            'D': D,
            'G': G,
            'S': S,
            'E': E,
            'course_height': course_height
        }
    }


def calculate_tmin_tank_bottom(has_release_prevention_barrier=False):
    """
    API 653 - Tank bottom minimum thickness
    
    Args:
        has_release_prevention_barrier: True if RPB installed under tank
    
    Returns:
        dict: Tank bottom tmin
    """
    if has_release_prevention_barrier:
        tmin_center = 0.05  # inches
        tmin_edge = 0.1     # inches (within 3 ft of shell)
    else:
        tmin_center = 0.1   # inches
        tmin_edge = 0.1     # inches
    
    return {
        'tmin_center': tmin_center,
        'tmin_edge': tmin_edge,
        'has_RPB': has_release_prevention_barrier,
        'code': 'API 653',
        'formula': 'API 653 §4.4.2',
        'notes': 'Edge = within 3 ft of shell'
    }


# Example usage and validation
if __name__ == '__main__':
    print("=" * 70)
    print("TMIN CALCULATOR - EXAMPLE CALCULATIONS")
    print("=" * 70)
    
    # Example 1: Piping
    print("\n1. PIPING (6-inch, Sch 40, 300 psig, 600°F, A106 Gr B)")
    piping = calculate_tmin_piping(
        P=300,
        D=6.625,  # OD for 6-inch pipe
        S=15000,  # Allowable stress at 600°F for A106B
        E=1.0,    # Seamless
        NPS=6,
        T_design=600,
        corrosion_allowance=0.125
    )
    print(f"  t_pressure:    {piping['t_pressure']:.4f} in")
    print(f"  t_structural:  {piping['t_structural']:.4f} in")
    print(f"  Governing:     {piping['governing']}")
    print(f"  tmin (with CA): {piping['tm']:.4f} in")
    
    # Example 2: Vessel shell
    print("\n2. VESSEL SHELL (48-inch ID, 150 psig, SA-516-70)")
    vessel = calculate_tmin_vessel(
        P=150,
        R_or_D=24,  # Radius = 24 in
        S=17500,
        E=0.85,
        component_type='shell',
        corrosion_allowance=0.125
    )
    print(f"  t_circumferential: {vessel['t_circumferential']:.4f} in")
    print(f"  t_longitudinal:    {vessel['t_longitudinal']:.4f} in")
    print(f"  Governing:         {vessel['governing']}")
    print(f"  tmin (with CA):    {vessel['tm']:.4f} in")
    
    # Example 3: Tank shell
    print("\n3. TANK SHELL (40-ft diameter, 30-ft height, water)")
    tank = calculate_tmin_tank_shell(
        H=30,
        D=40,
        G=1.0,
        S=21000,
        E=0.85
    )
    print(f"  t_calculated:     {tank['t_calculated']:.4f} in")
    print(f"  t_absolute_min:   {tank['t_absolute_min']:.4f} in")
    print(f"  Governing:        {tank['governing']}")
    print(f"  tmin:             {tank['tm']:.4f} in")
    
    print("\n" + "=" * 70)
