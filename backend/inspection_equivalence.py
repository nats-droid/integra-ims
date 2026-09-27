"""
Inspection Equivalence and Effectiveness
API 581 Part 2 - Inspection Effectiveness Categories

Handles:
- Inspection effectiveness grading (A/B/C/D/E)
- Partial credit system (2 Type B = 1 Type A)
- Cumulative effectiveness calculation
- Reset logic on findings
"""

from datetime import datetime
from typing import List, Dict, Optional
from enum import Enum


class InspectionEffectiveness(Enum):
    """
    API 581 Part 2 Inspection Effectiveness Categories
    """
    A = "A"  # Highly Effective
    B = "B"  # Usually Effective
    C = "C"  # Fairly Effective
    D = "D"  # Poorly Effective
    E = "E"  # Ineffective


class InspectionType(Enum):
    """
    Inspection types with different effectiveness levels
    """
    INTERNAL = "internal"
    EXTERNAL = "external"
    ONLINE = "online"
    NDE = "nde"


class InspectionRecord:
    """
    Single inspection record
    """
    def __init__(
        self,
        inspection_date: datetime,
        effectiveness: InspectionEffectiveness,
        inspection_type: InspectionType,
        findings: bool = False,
        notes: str = ""
    ):
        self.inspection_date = inspection_date
        self.effectiveness = effectiveness
        self.inspection_type = inspection_type
        self.findings = findings
        self.notes = notes
    
    def to_dict(self) -> Dict:
        return {
            'inspection_date': self.inspection_date.strftime('%Y-%m-%d'),
            'effectiveness': self.effectiveness.value,
            'inspection_type': self.inspection_type.value,
            'findings': self.findings,
            'notes': self.notes
        }


def calculate_equivalence_credit(
    inspections: List[InspectionRecord],
    target_effectiveness: InspectionEffectiveness = InspectionEffectiveness.A
) -> Dict:
    """
    Calculate inspection equivalence credit
    
    Rules (API 581):
    - 2 Type B inspections = 1 Type A inspection
    - 2 Type C inspections = 1 Type B inspection
    - 4 Type C inspections = 1 Type A inspection
    
    Simplified: Each effectiveness level = 0.5 credit toward next higher level
    
    Args:
        inspections: List of InspectionRecord
        target_effectiveness: Target effectiveness level
    
    Returns:
        {
            'equivalent_count': float,  # Equivalent Type A inspections
            'credit_breakdown': dict,
            'meets_requirement': bool
        }
    """
    # Effectiveness weights (relative to Type A)
    effectiveness_weights = {
        InspectionEffectiveness.A: 1.0,
        InspectionEffectiveness.B: 0.5,
        InspectionEffectiveness.C: 0.25,
        InspectionEffectiveness.D: 0.1,
        InspectionEffectiveness.E: 0.0
    }
    
    # Count by effectiveness
    count_by_effectiveness = {
        InspectionEffectiveness.A: 0,
        InspectionEffectiveness.B: 0,
        InspectionEffectiveness.C: 0,
        InspectionEffectiveness.D: 0,
        InspectionEffectiveness.E: 0
    }
    
    # Filter out inspections with findings (they reset credit)
    valid_inspections = [insp for insp in inspections if not insp.findings]
    
    for insp in valid_inspections:
        count_by_effectiveness[insp.effectiveness] += 1
    
    # Calculate equivalent Type A credit
    equivalent_count = 0.0
    credit_breakdown = {}
    
    for effectiveness, count in count_by_effectiveness.items():
        weight = effectiveness_weights[effectiveness]
        credit = count * weight
        equivalent_count += credit
        
        if count > 0:
            credit_breakdown[effectiveness.value] = {
                'count': count,
                'weight': weight,
                'credit': credit
            }
    
    # Check if requirement met
    target_weight = effectiveness_weights[target_effectiveness]
    meets_requirement = equivalent_count >= target_weight
    
    return {
        'equivalent_count': equivalent_count,
        'credit_breakdown': credit_breakdown,
        'target_effectiveness': target_effectiveness.value,
        'target_credit_required': target_weight,
        'meets_requirement': meets_requirement,
        'total_inspections': len(valid_inspections),
        'inspections_with_findings': len([i for i in inspections if i.findings])
    }


def calculate_cumulative_effectiveness(
    inspection_history: List[InspectionRecord],
    assessment_date: datetime
) -> Dict:
    """
    Calculate cumulative inspection effectiveness over time
    
    Rules:
    - Recent inspections have more weight
    - Findings reset effectiveness counter
    - Effectiveness degrades with time since last inspection
    
    Args:
        inspection_history: List of InspectionRecord (sorted by date)
        assessment_date: Current assessment date
    
    Returns:
        {
            'current_effectiveness': str,
            'inspection_count': int,
            'years_since_last': float,
            'effectiveness_degraded': bool
        }
    """
    if not inspection_history:
        return {
            'current_effectiveness': 'E',  # No inspection = ineffective
            'inspection_count': 0,
            'years_since_last': float('inf'),
            'effectiveness_degraded': True
        }
    
    # Sort by date
    sorted_history = sorted(inspection_history, key=lambda x: x.inspection_date)
    
    # Find last inspection without findings
    last_valid_inspection = None
    inspection_count = 0
    
    for insp in reversed(sorted_history):
        if insp.findings:
            # Finding resets counter
            break
        else:
            if last_valid_inspection is None:
                last_valid_inspection = insp
            inspection_count += 1
    
    if last_valid_inspection is None:
        return {
            'current_effectiveness': 'E',
            'inspection_count': 0,
            'years_since_last': float('inf'),
            'effectiveness_degraded': True
        }
    
    # Calculate time since last inspection
    years_since_last = (assessment_date - last_valid_inspection.inspection_date).days / 365.25
    
    # Effectiveness degrades if > 5 years since last inspection
    effectiveness_degraded = years_since_last > 5.0
    
    if effectiveness_degraded:
        # Degrade by one level
        degradation_map = {
            InspectionEffectiveness.A: InspectionEffectiveness.B,
            InspectionEffectiveness.B: InspectionEffectiveness.C,
            InspectionEffectiveness.C: InspectionEffectiveness.D,
            InspectionEffectiveness.D: InspectionEffectiveness.E,
            InspectionEffectiveness.E: InspectionEffectiveness.E
        }
        current_effectiveness = degradation_map[last_valid_inspection.effectiveness]
    else:
        current_effectiveness = last_valid_inspection.effectiveness
    
    return {
        'current_effectiveness': current_effectiveness.value,
        'inspection_count': inspection_count,
        'years_since_last': years_since_last,
        'effectiveness_degraded': effectiveness_degraded,
        'last_inspection_date': last_valid_inspection.inspection_date.strftime('%Y-%m-%d'),
        'last_inspection_effectiveness': last_valid_inspection.effectiveness.value
    }


def recommend_inspection_plan(
    current_effectiveness: str,
    target_effectiveness: str,
    inspection_history: List[InspectionRecord]
) -> Dict:
    """
    Recommend inspection plan to achieve target effectiveness
    
    Args:
        current_effectiveness: Current effectiveness level (A/B/C/D/E)
        target_effectiveness: Target effectiveness level
        inspection_history: Historical inspections
    
    Returns:
        {
            'recommendation': str,
            'inspections_needed': int,
            'suggested_types': list,
            'rationale': str
        }
    """
    current = InspectionEffectiveness(current_effectiveness)
    target = InspectionEffectiveness(target_effectiveness)
    
    # Calculate credit needed
    equivalence = calculate_equivalence_credit(inspection_history, target)
    
    if equivalence['meets_requirement']:
        return {
            'recommendation': 'Maintain current inspection program',
            'inspections_needed': 0,
            'suggested_types': [],
            'rationale': f"Current equivalence credit ({equivalence['equivalent_count']:.1f}) meets target requirement ({equivalence['target_credit_required']:.1f})"
        }
    
    # Calculate gap
    credit_gap = equivalence['target_credit_required'] - equivalence['equivalent_count']
    
    # Recommend inspection types to close gap
    if target == InspectionEffectiveness.A:
        if credit_gap >= 1.0:
            # Need Type A inspection
            return {
                'recommendation': 'Perform 1 Type A (Highly Effective) inspection',
                'inspections_needed': 1,
                'suggested_types': ['Internal inspection with full coverage'],
                'rationale': f"Credit gap: {credit_gap:.2f}. One Type A inspection will satisfy requirement."
            }
        elif credit_gap >= 0.5:
            # Need Type B inspection
            return {
                'recommendation': 'Perform 1 Type B (Usually Effective) inspection OR 2 Type C inspections',
                'inspections_needed': 1,
                'suggested_types': ['External inspection with NDE sampling', 'Online monitoring with spot checks'],
                'rationale': f"Credit gap: {credit_gap:.2f}. 2 Type B = 1 Type A equivalent."
            }
        else:
            # Small gap
            return {
                'recommendation': 'Perform 1 Type C (Fairly Effective) inspection',
                'inspections_needed': 1,
                'suggested_types': ['External visual inspection'],
                'rationale': f"Credit gap: {credit_gap:.2f}. Small gap can be closed with Type C."
            }
    
    return {
        'recommendation': 'Perform inspection to improve effectiveness',
        'inspections_needed': 1,
        'suggested_types': ['Internal or external inspection'],
        'rationale': f"Current effectiveness ({current.value}) below target ({target.value})"
    }


def reset_on_findings(
    inspection_history: List[InspectionRecord],
    finding_date: datetime
) -> List[InspectionRecord]:
    """
    Reset inspection credit after findings discovered
    
    Args:
        inspection_history: Full inspection history
        finding_date: Date when findings were discovered
    
    Returns:
        List of inspections valid after reset (after finding_date)
    """
    # Only count inspections after the finding
    valid_inspections = [
        insp for insp in inspection_history
        if insp.inspection_date > finding_date
    ]
    
    return valid_inspections


# Example usage
if __name__ == '__main__':
    print("=" * 70)
    print("INSPECTION EQUIVALENCE - EXAMPLE CALCULATIONS")
    print("=" * 70)
    
    # Example 1: Equivalence credit calculation
    print("\n1. EQUIVALENCE CREDIT (2 Type B = 1 Type A)")
    
    inspections = [
        InspectionRecord(datetime(2020, 1, 1), InspectionEffectiveness.B, InspectionType.EXTERNAL),
        InspectionRecord(datetime(2022, 1, 1), InspectionEffectiveness.B, InspectionType.ONLINE),
        InspectionRecord(datetime(2024, 1, 1), InspectionEffectiveness.C, InspectionType.EXTERNAL)
    ]
    
    equivalence = calculate_equivalence_credit(inspections, InspectionEffectiveness.A)
    
    print(f"  Target: Type A (Highly Effective)")
    print(f"  Inspections:")
    for insp in inspections:
        print(f"    - {insp.inspection_date.strftime('%Y-%m-%d')}: Type {insp.effectiveness.value} ({insp.inspection_type.value})")
    
    print(f"\n  Credit Breakdown:")
    for eff, data in equivalence['credit_breakdown'].items():
        print(f"    Type {eff}: {data['count']} × {data['weight']:.2f} = {data['credit']:.2f} credit")
    
    print(f"\n  Total Equivalent Credit: {equivalence['equivalent_count']:.2f}")
    print(f"  Target Required:         {equivalence['target_credit_required']:.2f}")
    print(f"  Meets Requirement:       {'YES ✓' if equivalence['meets_requirement'] else 'NO ✗'}")
    
    # Example 2: Cumulative effectiveness with time degradation
    print("\n2. CUMULATIVE EFFECTIVENESS (Time Degradation)")
    
    history = [
        InspectionRecord(datetime(2018, 1, 1), InspectionEffectiveness.A, InspectionType.INTERNAL),
        InspectionRecord(datetime(2021, 1, 1), InspectionEffectiveness.B, InspectionType.EXTERNAL)
    ]
    
    assessment_date = datetime(2026, 9, 27)
    cumulative = calculate_cumulative_effectiveness(history, assessment_date)
    
    print(f"  Last Inspection: {cumulative['last_inspection_date']} (Type {cumulative['last_inspection_effectiveness']})")
    print(f"  Years Since:     {cumulative['years_since_last']:.1f} years")
    print(f"  Degraded:        {'YES (>5 years)' if cumulative['effectiveness_degraded'] else 'NO'}")
    print(f"  Current Effectiveness: Type {cumulative['current_effectiveness']}")
    
    # Example 3: Reset on findings
    print("\n3. RESET ON FINDINGS")
    
    history_with_finding = [
        InspectionRecord(datetime(2018, 1, 1), InspectionEffectiveness.A, InspectionType.INTERNAL, findings=False),
        InspectionRecord(datetime(2021, 1, 1), InspectionEffectiveness.B, InspectionType.EXTERNAL, findings=False),
        InspectionRecord(datetime(2023, 6, 1), InspectionEffectiveness.B, InspectionType.ONLINE, findings=True, notes="Corrosion found"),
        InspectionRecord(datetime(2024, 1, 1), InspectionEffectiveness.A, InspectionType.INTERNAL, findings=False),
        InspectionRecord(datetime(2025, 1, 1), InspectionEffectiveness.B, InspectionType.EXTERNAL, findings=False)
    ]
    
    print(f"  Full History: {len(history_with_finding)} inspections")
    print(f"  Finding Date: 2023-06-01")
    
    valid_after_finding = reset_on_findings(history_with_finding, datetime(2023, 6, 1))
    print(f"  Valid After Finding: {len(valid_after_finding)} inspections")
    
    equivalence_after_reset = calculate_equivalence_credit(valid_after_finding, InspectionEffectiveness.A)
    print(f"  Equivalent Credit (after reset): {equivalence_after_reset['equivalent_count']:.2f}")
    
    # Example 4: Inspection plan recommendation
    print("\n4. INSPECTION PLAN RECOMMENDATION")
    
    recommendation = recommend_inspection_plan(
        current_effectiveness='C',
        target_effectiveness='A',
        inspection_history=inspections
    )
    
    print(f"  Current:       Type C (Fairly Effective)")
    print(f"  Target:        Type A (Highly Effective)")
    print(f"\n  Recommendation: {recommendation['recommendation']}")
    print(f"  Rationale:      {recommendation['rationale']}")
    if recommendation['suggested_types']:
        print(f"  Suggested Types:")
        for stype in recommendation['suggested_types']:
            print(f"    - {stype}")
    
    print("\n" + "=" * 70)
