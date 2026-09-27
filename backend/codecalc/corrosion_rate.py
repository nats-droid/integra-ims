"""
Corrosion Rate and Remaining Life Calculator
References: API 570 §7.1, API 510 §7.1

Calculates long-term and short-term corrosion rates from thickness history,
and remaining life based on current thickness.
"""

from datetime import datetime
from typing import List, Dict, Union


def calculate_corrosion_rate(thickness_history: List[Dict]) -> Dict:
    """
    Calculate long-term (LT) and short-term (ST) corrosion rates
    API 570 §7.1.1, API 510 §7.1
    
    Args:
        thickness_history: List of thickness readings
            [
                {'date': '2020-01-01', 'thickness': 0.500, 'location': 'CML-1'},
                {'date': '2023-01-01', 'thickness': 0.485, 'location': 'CML-1'},
                {'date': '2026-01-01', 'thickness': 0.470, 'location': 'CML-1'}
            ]
            Date format: 'YYYY-MM-DD' or datetime object
            Thickness in inches
    
    Returns:
        dict: {
            'CR_LT': float,           # Long-term rate (mpy)
            'CR_ST': float,           # Short-term rate (mpy)
            'governing': 'LT'|'ST',   # Which rate is larger
            'years_LT': float,        # Years span for LT
            'years_ST': float,        # Years span for ST
            'n_readings': int,        # Number of readings
            'initial_thickness': float,
            'current_thickness': float,
            'calculation_date': str
        }
    """
    if not thickness_history or len(thickness_history) < 2:
        return {
            'CR_LT': 0.0,
            'CR_ST': 0.0,
            'governing': 'LT',
            'years_LT': 0,
            'years_ST': 0,
            'n_readings': len(thickness_history) if thickness_history else 0,
            'initial_thickness': thickness_history[0]['thickness'] if thickness_history else None,
            'current_thickness': thickness_history[0]['thickness'] if thickness_history else None,
            'calculation_date': datetime.now().strftime('%Y-%m-%d'),
            'error': 'Insufficient data - need at least 2 readings'
        }
    
    # Sort by date
    history = sorted(thickness_history, key=lambda x: _parse_date(x['date']))
    
    # Parse dates
    dates = [_parse_date(reading['date']) for reading in history]
    thicknesses = [reading['thickness'] for reading in history]
    
    # Long-term rate: first to last
    t_initial = thicknesses[0]
    t_actual = thicknesses[-1]
    date_initial = dates[0]
    date_actual = dates[-1]
    
    years_LT = (date_actual - date_initial).days / 365.25
    
    if years_LT > 0:
        CR_LT_in_per_yr = (t_initial - t_actual) / years_LT
        CR_LT_mpy = max(CR_LT_in_per_yr * 1000, 0)  # Convert to mpy
    else:
        CR_LT_mpy = 0.0
    
    # Short-term rate: last two readings
    if len(history) >= 2:
        t_previous = thicknesses[-2]
        date_previous = dates[-2]
        
        years_ST = (date_actual - date_previous).days / 365.25
        
        if years_ST > 0:
            CR_ST_in_per_yr = (t_previous - t_actual) / years_ST
            CR_ST_mpy = max(CR_ST_in_per_yr * 1000, 0)
        else:
            CR_ST_mpy = CR_LT_mpy
    else:
        CR_ST_mpy = CR_LT_mpy
        years_ST = years_LT
    
    # Governing rate: larger is more conservative
    governing = 'LT' if CR_LT_mpy >= CR_ST_mpy else 'ST'
    
    return {
        'CR_LT': CR_LT_mpy,
        'CR_ST': CR_ST_mpy,
        'governing': governing,
        'governing_rate': max(CR_LT_mpy, CR_ST_mpy),
        'years_LT': years_LT,
        'years_ST': years_ST,
        'n_readings': len(history),
        'initial_thickness': t_initial,
        'current_thickness': t_actual,
        'calculation_date': datetime.now().strftime('%Y-%m-%d'),
        'thickness_loss_LT': t_initial - t_actual,
        'thickness_loss_ST': t_previous - t_actual if len(history) >= 2 else t_initial - t_actual
    }


def _parse_date(date_input: Union[str, datetime]) -> datetime:
    """
    Parse date from string or datetime object
    
    Args:
        date_input: 'YYYY-MM-DD' string or datetime object
    
    Returns:
        datetime object
    """
    if isinstance(date_input, datetime):
        return date_input
    
    # Try common date formats
    formats = [
        '%Y-%m-%d',
        '%Y/%m/%d',
        '%d-%m-%Y',
        '%d/%m/%Y',
        '%m/%d/%Y'
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_input, fmt)
        except ValueError:
            continue
    
    raise ValueError(f"Unable to parse date: {date_input}")


def calculate_remaining_life(
    t_actual: float,
    t_required: float,
    corrosion_rate: float,
    units: str = 'mpy'
) -> Dict:
    """
    Calculate remaining life (RL)
    API 570 §7.1.1, API 510 §7.1
    
    RL = (t_actual - t_required) / CR
    
    Args:
        t_actual: Current measured thickness (in)
        t_required: Minimum required thickness (in)
        corrosion_rate: Corrosion rate (mpy or in/yr based on units)
        units: 'mpy' (mils per year) or 'in/yr' (inches per year)
    
    Returns:
        dict: {
            'remaining_life': float,  # years
            't_actual': float,
            't_required': float,
            'corrosion_rate': float,
            'units': str,
            'status': str,
            'retired': bool
        }
    """
    # Convert corrosion rate to in/yr if needed
    if units == 'mpy':
        CR_in_per_yr = corrosion_rate / 1000
    elif units == 'in/yr':
        CR_in_per_yr = corrosion_rate
    else:
        raise ValueError(f"Unknown units: {units}")
    
    # Check if already below tmin
    if t_actual <= t_required:
        return {
            'remaining_life': 0.0,
            't_actual': t_actual,
            't_required': t_required,
            'corrosion_rate': corrosion_rate,
            'corrosion_rate_in_per_yr': CR_in_per_yr,
            'units': units,
            'status': 'RETIRED - Below tmin',
            'retired': True,
            'margin': t_actual - t_required
        }
    
    # Calculate remaining life
    if CR_in_per_yr <= 0:
        return {
            'remaining_life': float('inf'),
            't_actual': t_actual,
            't_required': t_required,
            'corrosion_rate': corrosion_rate,
            'corrosion_rate_in_per_yr': CR_in_per_yr,
            'units': units,
            'status': 'No corrosion detected',
            'retired': False,
            'margin': t_actual - t_required
        }
    
    RL = (t_actual - t_required) / CR_in_per_yr
    
    # Determine status
    if RL < 2:
        status = 'CRITICAL - RL < 2 years'
    elif RL < 5:
        status = 'WARNING - RL < 5 years'
    elif RL < 10:
        status = 'MONITOR - RL < 10 years'
    else:
        status = 'GOOD - RL ≥ 10 years'
    
    return {
        'remaining_life': RL,
        't_actual': t_actual,
        't_required': t_required,
        'corrosion_rate': corrosion_rate,
        'corrosion_rate_in_per_yr': CR_in_per_yr,
        'units': units,
        'status': status,
        'retired': False,
        'margin': t_actual - t_required,
        'years_to_retirement': RL
    }


def calculate_future_thickness(
    t_actual: float,
    corrosion_rate: float,
    years_future: float,
    units: str = 'mpy'
) -> Dict:
    """
    Project future thickness based on corrosion rate
    
    t_future = t_actual - (CR × years)
    
    Args:
        t_actual: Current thickness (in)
        corrosion_rate: Corrosion rate (mpy or in/yr)
        years_future: Years into the future
        units: 'mpy' or 'in/yr'
    
    Returns:
        dict: {
            't_future': float,
            't_loss': float,
            'years': float
        }
    """
    if units == 'mpy':
        CR_in_per_yr = corrosion_rate / 1000
    else:
        CR_in_per_yr = corrosion_rate
    
    t_loss = CR_in_per_yr * years_future
    t_future = t_actual - t_loss
    
    return {
        't_future': max(t_future, 0),
        't_actual': t_actual,
        't_loss': t_loss,
        'years': years_future,
        'corrosion_rate': corrosion_rate,
        'units': units
    }


def calculate_statistical_corrosion_rate(
    thickness_history: List[Dict],
    confidence_level: float = 0.95
) -> Dict:
    """
    Calculate statistical corrosion rate with confidence bounds
    
    Uses linear regression on thickness vs time data
    
    Args:
        thickness_history: List of thickness readings
        confidence_level: Confidence level (0.90, 0.95, or 0.99)
    
    Returns:
        dict: {
            'CR_mean': float,
            'CR_95_UCL': float,  # Upper confidence limit (conservative)
            'R_squared': float,
            'std_error': float
        }
    """
    import numpy as np
    from scipy import stats
    
    if len(thickness_history) < 3:
        return {
            'CR_mean': 0.0,
            'CR_95_UCL': 0.0,
            'R_squared': 0.0,
            'std_error': 0.0,
            'error': 'Need at least 3 readings for statistical analysis'
        }
    
    # Sort by date
    history = sorted(thickness_history, key=lambda x: _parse_date(x['date']))
    
    # Convert to time (years from first reading) and thickness arrays
    dates = [_parse_date(reading['date']) for reading in history]
    thicknesses = [reading['thickness'] for reading in history]
    
    date_0 = dates[0]
    times = [(d - date_0).days / 365.25 for d in dates]
    
    # Linear regression: thickness = a - b*time (b is CR)
    slope, intercept, r_value, p_value, std_err = stats.linregress(times, thicknesses)
    
    CR_mean = -slope * 1000  # Convert to mpy (negative because thickness decreases)
    
    # Upper confidence limit (conservative for corrosion rate)
    from scipy.stats import t as t_dist
    n = len(times)
    dof = n - 2  # degrees of freedom
    t_critical = t_dist.ppf(confidence_level, dof)
    
    CR_UCL = (-slope + t_critical * std_err) * 1000
    
    return {
        'CR_mean': max(CR_mean, 0),
        'CR_UCL': max(CR_UCL, 0),
        'R_squared': r_value**2,
        'std_error': std_err * 1000,  # mpy
        'confidence_level': confidence_level,
        'n_readings': n,
        'slope': slope,
        'intercept': intercept,
        'p_value': p_value
    }


# Example usage
if __name__ == '__main__':
    print("=" * 70)
    print("CORROSION RATE & REMAINING LIFE - EXAMPLE CALCULATIONS")
    print("=" * 70)
    
    # Example 1: Typical corrosion
    print("\n1. TYPICAL CORROSION (5 mpy over 10 years)")
    history = [
        {'date': '2016-01-01', 'thickness': 0.500},
        {'date': '2019-01-01', 'thickness': 0.485},
        {'date': '2022-01-01', 'thickness': 0.470},
        {'date': '2026-01-01', 'thickness': 0.450}
    ]
    
    cr_result = calculate_corrosion_rate(history)
    print(f"  CR_LT:        {cr_result['CR_LT']:.2f} mpy")
    print(f"  CR_ST:        {cr_result['CR_ST']:.2f} mpy")
    print(f"  Governing:    {cr_result['governing']} ({cr_result['governing_rate']:.2f} mpy)")
    print(f"  Years span:   {cr_result['years_LT']:.1f} years")
    print(f"  Thickness loss: {cr_result['thickness_loss_LT']:.4f} in")
    
    # Example 2: Remaining life
    print("\n2. REMAINING LIFE CALCULATION")
    rl_result = calculate_remaining_life(
        t_actual=0.450,
        t_required=0.250,
        corrosion_rate=5.0,
        units='mpy'
    )
    print(f"  t_actual:     {rl_result['t_actual']:.3f} in")
    print(f"  t_required:   {rl_result['t_required']:.3f} in")
    print(f"  Margin:       {rl_result['margin']:.3f} in")
    print(f"  CR:           {rl_result['corrosion_rate']:.2f} mpy")
    print(f"  Remaining Life: {rl_result['remaining_life']:.1f} years")
    print(f"  Status:       {rl_result['status']}")
    
    # Example 3: Future thickness
    print("\n3. FUTURE THICKNESS PROJECTION (5 years)")
    future = calculate_future_thickness(
        t_actual=0.450,
        corrosion_rate=5.0,
        years_future=5.0,
        units='mpy'
    )
    print(f"  Current:      {future['t_actual']:.3f} in")
    print(f"  Loss (5 yr):  {future['t_loss']:.4f} in")
    print(f"  Future:       {future['t_future']:.3f} in")
    
    print("\n" + "=" * 70)
