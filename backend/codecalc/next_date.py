"""
Next Inspection Date Calculator
Determines final inspection date = earliest of (RBI, Code, Regulatory)

References: API 581 Part 4, API 570/510, Permenaker 37/2016
"""

from datetime import datetime, timedelta
from typing import Dict, Optional


def calculate_next_inspection_date(
    assessment_date: datetime,
    rbi_target_date: Optional[datetime] = None,
    code_interval_years: Optional[float] = None,
    regulatory_interval_years: Optional[float] = None,
    component_type: Optional[str] = None
) -> Dict:
    """
    Determine governing next inspection date
    
    Next Date = earliest of:
    1. RBI target date (from Part 4 timeline planning)
    2. Code interval (API 570/510)
    3. Regulatory cap (Permenaker 37/2016)
    
    Args:
        assessment_date: Current assessment date
        rbi_target_date: Target date from RBI risk analysis (optional)
        code_interval_years: Code-based interval in years (optional)
        regulatory_interval_years: Regulatory max interval in years (optional)
        component_type: Equipment type for auto-lookup of regulatory (optional)
    
    Returns:
        dict: {
            'next_date': datetime,
            'interval_years': float,
            'interval_days': int,
            'governing_criterion': str,
            'candidates': list
        }
    """
    # Convert assessment_date to datetime if string
    if isinstance(assessment_date, str):
        assessment_date = datetime.strptime(assessment_date, '%Y-%m-%d')
    
    candidates = []
    
    # Candidate 1: RBI target date
    if rbi_target_date:
        if isinstance(rbi_target_date, str):
            rbi_target_date = datetime.strptime(rbi_target_date, '%Y-%m-%d')
        
        candidates.append({
            'date': rbi_target_date,
            'criterion': 'RBI (Risk-Based)',
            'source': 'API 581 Part 4',
            'interval_years': (rbi_target_date - assessment_date).days / 365.25
        })
    
    # Candidate 2: Code interval
    if code_interval_years is not None:
        code_date = assessment_date + timedelta(days=int(code_interval_years * 365.25))
        candidates.append({
            'date': code_date,
            'criterion': 'Code (API 570/510)',
            'source': 'API 570 §6.3 or API 510 §6.4',
            'interval_years': code_interval_years
        })
    
    # Candidate 3: Regulatory cap
    if regulatory_interval_years is None and component_type:
        # Auto-lookup regulatory interval
        regulatory_interval_years = get_regulatory_interval(component_type)
    
    if regulatory_interval_years is not None:
        regulatory_date = assessment_date + timedelta(days=int(regulatory_interval_years * 365.25))
        candidates.append({
            'date': regulatory_date,
            'criterion': 'Regulatory Cap',
            'source': 'Permenaker 37/2016',
            'interval_years': regulatory_interval_years
        })
    
    # If no candidates, use default 5 years
    if not candidates:
        default_date = assessment_date + timedelta(days=int(5 * 365.25))
        candidates.append({
            'date': default_date,
            'criterion': 'Default (No specific criteria)',
            'source': 'Conservative default',
            'interval_years': 5.0
        })
    
    # Earliest date governs (most conservative)
    earliest = min(candidates, key=lambda x: x['date'])
    
    interval_days = (earliest['date'] - assessment_date).days
    interval_years = interval_days / 365.25
    
    return {
        'next_date': earliest['date'],
        'next_date_str': earliest['date'].strftime('%Y-%m-%d'),
        'assessment_date': assessment_date,
        'assessment_date_str': assessment_date.strftime('%Y-%m-%d'),
        'interval_years': interval_years,
        'interval_days': interval_days,
        'governing_criterion': earliest['criterion'],
        'governing_source': earliest['source'],
        'candidates': candidates,
        'all_criteria': [c['criterion'] for c in candidates]
    }


def get_regulatory_interval(component_type: str) -> Optional[float]:
    """
    Get regulatory inspection interval per Permenaker 37/2016
    
    UNSURE - Verify pasal numbers and intervals in your copy
    
    Args:
        component_type: Type of equipment
            'pressure_vessel', 'storage_tank', 'heat_exchanger', 
            'boiler', 'piping', 'compressor', etc.
    
    Returns:
        float: Interval in years, or None if not regulated
    """
    # Permenaker 37/2016 intervals (VERIFY THESE VALUES)
    # These are typical intervals - confirm with actual regulation
    regulatory_intervals = {
        'pressure_vessel': 3.0,         # Bejana tekan
        'storage_tank': 5.0,            # Tangki timbun
        'storage_tank_elevated': 3.0,   # Tangki tekan elevated
        'heat_exchanger': 3.0,          # Heat exchanger (if pressure)
        'boiler': 1.0,                  # Ketel uap (annual)
        'steam_drum': 1.0,              # Steam drum
        'air_receiver': 3.0,            # Bejana udara
        'compressor': 3.0,              # Kompresor (if pressure vessel)
        'separator': 3.0,               # Separator (if pressure)
        'reactor': 3.0,                 # Reaktor
        'piping': None,                 # Piping not directly regulated
        'valve': None,                  # Valves not directly regulated
        'instrument': None              # Instruments not regulated
    }
    
    # Normalize component type
    comp_type_lower = component_type.lower().replace(' ', '_').replace('-', '_')
    
    return regulatory_intervals.get(comp_type_lower)


def check_overdue_status(
    next_date: datetime,
    check_date: Optional[datetime] = None
) -> Dict:
    """
    Check if inspection is overdue or due soon
    
    Args:
        next_date: Scheduled next inspection date
        check_date: Date to check against (default: today)
    
    Returns:
        dict: {
            'status': str,  # OVERDUE, DUE_SOON, SCHEDULED, FUTURE
            'days_remaining': int,
            'urgency': str  # CRITICAL, HIGH, MEDIUM, LOW
        }
    """
    if check_date is None:
        check_date = datetime.now()
    
    if isinstance(next_date, str):
        next_date = datetime.strptime(next_date, '%Y-%m-%d')
    
    if isinstance(check_date, str):
        check_date = datetime.strptime(check_date, '%Y-%m-%d')
    
    days_remaining = (next_date - check_date).days
    
    if days_remaining < 0:
        status = 'OVERDUE'
        urgency = 'CRITICAL'
    elif days_remaining <= 30:
        status = 'DUE_SOON'
        urgency = 'HIGH'
    elif days_remaining <= 90:
        status = 'SCHEDULED'
        urgency = 'MEDIUM'
    else:
        status = 'FUTURE'
        urgency = 'LOW'
    
    return {
        'status': status,
        'days_remaining': days_remaining,
        'urgency': urgency,
        'next_date': next_date,
        'check_date': check_date,
        'overdue': days_remaining < 0
    }


def generate_inspection_schedule(
    assessment_date: datetime,
    interval_years: float,
    num_inspections: int = 5
) -> list:
    """
    Generate multi-year inspection schedule
    
    Args:
        assessment_date: Starting date
        interval_years: Interval between inspections
        num_inspections: Number of future inspections to schedule
    
    Returns:
        list: [
            {
                'inspection_no': 1,
                'date': datetime,
                'years_from_now': float
            },
            ...
        ]
    """
    schedule = []
    
    for i in range(1, num_inspections + 1):
        years_future = i * interval_years
        days_future = int(years_future * 365.25)
        inspection_date = assessment_date + timedelta(days=days_future)
        
        schedule.append({
            'inspection_no': i,
            'date': inspection_date,
            'date_str': inspection_date.strftime('%Y-%m-%d'),
            'years_from_assessment': years_future,
            'interval_years': interval_years
        })
    
    return schedule


def compare_intervals(
    rbi_interval: Optional[float] = None,
    code_interval: Optional[float] = None,
    regulatory_interval: Optional[float] = None
) -> Dict:
    """
    Compare different interval requirements
    
    Useful for showing which criterion is most restrictive
    
    Args:
        rbi_interval: RBI-based interval (years)
        code_interval: Code-based interval (years)
        regulatory_interval: Regulatory cap (years)
    
    Returns:
        dict: Comparison analysis
    """
    intervals = {}
    
    if rbi_interval is not None:
        intervals['RBI'] = rbi_interval
    
    if code_interval is not None:
        intervals['Code'] = code_interval
    
    if regulatory_interval is not None:
        intervals['Regulatory'] = regulatory_interval
    
    if not intervals:
        return {
            'error': 'No intervals provided',
            'governing': None,
            'interval': None
        }
    
    # Find minimum (most restrictive)
    governing_criterion = min(intervals, key=intervals.get)
    governing_interval = intervals[governing_criterion]
    
    # Calculate savings if RBI allows longer interval
    if 'RBI' in intervals and 'Code' in intervals:
        if intervals['RBI'] > intervals['Code']:
            savings_years = intervals['RBI'] - intervals['Code']
            savings_pct = (savings_years / intervals['Code']) * 100
            savings_msg = f"RBI allows {savings_years:.1f} years longer interval ({savings_pct:.0f}% extension)"
        else:
            savings_msg = "Code interval is longer; RBI governs (higher risk)"
    else:
        savings_msg = None
    
    return {
        'intervals': intervals,
        'governing_criterion': governing_criterion,
        'governing_interval': governing_interval,
        'most_restrictive': governing_criterion,
        'least_restrictive': max(intervals, key=intervals.get),
        'range': max(intervals.values()) - min(intervals.values()),
        'savings_analysis': savings_msg
    }


# Example usage
if __name__ == '__main__':
    print("=" * 70)
    print("NEXT INSPECTION DATE - EXAMPLE CALCULATIONS")
    print("=" * 70)
    
    assessment_date = datetime(2026, 9, 27)
    
    # Example 1: All three criteria
    print("\n1. COMPLETE ANALYSIS (RBI, Code, Regulatory)")
    
    rbi_target = datetime(2030, 9, 27)  # 4 years from RBI
    code_interval = 5.0  # 5 years from code
    regulatory_interval = 3.0  # 3 years regulatory cap
    
    result = calculate_next_inspection_date(
        assessment_date=assessment_date,
        rbi_target_date=rbi_target,
        code_interval_years=code_interval,
        regulatory_interval_years=regulatory_interval
    )
    
    print(f"  Assessment Date:    {result['assessment_date_str']}")
    print(f"  Next Inspection:    {result['next_date_str']}")
    print(f"  Interval:           {result['interval_years']:.1f} years")
    print(f"  Governing:          {result['governing_criterion']}")
    print(f"  Source:             {result['governing_source']}")
    print(f"\n  All Candidates:")
    for candidate in result['candidates']:
        print(f"    - {candidate['criterion']}: {candidate['date'].strftime('%Y-%m-%d')} ({candidate['interval_years']:.1f} years)")
    
    # Example 2: Auto-lookup regulatory
    print("\n2. AUTO-LOOKUP REGULATORY INTERVAL")
    
    result2 = calculate_next_inspection_date(
        assessment_date=assessment_date,
        code_interval_years=5.0,
        component_type='pressure_vessel'
    )
    
    print(f"  Component Type:     pressure_vessel")
    print(f"  Next Inspection:    {result2['next_date_str']}")
    print(f"  Governing:          {result2['governing_criterion']}")
    
    # Example 3: Overdue check
    print("\n3. OVERDUE STATUS CHECK")
    
    overdue_date = datetime(2026, 8, 1)  # In the past
    overdue = check_overdue_status(overdue_date, assessment_date)
    
    print(f"  Next Date:          {overdue_date.strftime('%Y-%m-%d')}")
    print(f"  Check Date:         {assessment_date.strftime('%Y-%m-%d')}")
    print(f"  Status:             {overdue['status']}")
    print(f"  Days Remaining:     {overdue['days_remaining']} days")
    print(f"  Urgency:            {overdue['urgency']}")
    
    # Example 4: Inspection schedule
    print("\n4. MULTI-YEAR INSPECTION SCHEDULE")
    
    schedule = generate_inspection_schedule(
        assessment_date=assessment_date,
        interval_years=3.0,
        num_inspections=5
    )
    
    print(f"  Assessment: {assessment_date.strftime('%Y-%m-%d')}")
    print(f"  Interval:   3.0 years")
    print(f"\n  Schedule:")
    for insp in schedule:
        print(f"    Inspection #{insp['inspection_no']}: {insp['date_str']} ({insp['years_from_assessment']:.1f} years)")
    
    # Example 5: Interval comparison
    print("\n5. INTERVAL COMPARISON ANALYSIS")
    
    comparison = compare_intervals(
        rbi_interval=6.0,
        code_interval=5.0,
        regulatory_interval=3.0
    )
    
    print(f"  RBI interval:       {comparison['intervals'].get('RBI', 'N/A')} years")
    print(f"  Code interval:      {comparison['intervals'].get('Code', 'N/A')} years")
    print(f"  Regulatory cap:     {comparison['intervals'].get('Regulatory', 'N/A')} years")
    print(f"\n  Governing:          {comparison['governing_criterion']} ({comparison['governing_interval']} years)")
    print(f"  Range:              {comparison['range']:.1f} years")
    if comparison['savings_analysis']:
        print(f"  Analysis:           {comparison['savings_analysis']}")
    
    print("\n" + "=" * 70)
