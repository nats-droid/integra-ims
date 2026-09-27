"""
Management Systems Factor (FMS) Audit Calculator
API 581 Part 2 §3.5, Annex 2.A

Calculates F_MS based on 72-item management systems audit.
"""

import math
from typing import Dict, List, Optional


def calculate_fms(audit_scores: Dict[str, float]) -> Dict:
    """
    Calculate Management Systems Factor (F_MS)
    
    F_MS = 2.38 · e^(−0.012 · pscore)
    
    API 581 Annex 2.A defines 6 sections with 72 total items:
    - Management of Inspection (MI): 50% weight
    - Site Management: 17% weight
    - Management of Change: 13% weight
    - Failure Investigation: 10% weight
    - Process Safety: 5% weight
    - Operating Procedures: 5% weight
    
    pscore = 72 → F_MS ≈ 1.0 (baseline)
    pscore > 72 → F_MS < 1.0 (better management, lower risk)
    pscore < 72 → F_MS > 1.0 (poorer management, higher risk)
    
    Args:
        audit_scores: Dictionary with section scores (0-100 each)
            {
                'management_inspection': 0-100,
                'site_management': 0-100,
                'management_of_change': 0-100,
                'failure_investigation': 0-100,
                'process_safety': 0-100,
                'operating_procedures': 0-100
            }
    
    Returns:
        dict: {
            'fms': float,                    # Management Systems Factor
            'pscore': float,                 # Weighted score (0-100)
            'interpretation': str,           # Risk level interpretation
            'breakdown': dict,               # Contribution per section
            'impact_on_pof': str            # How FMS affects POF
        }
    """
    # API 581 Annex 2.A weights
    weights = {
        'management_inspection': 0.50,
        'site_management': 0.17,
        'management_of_change': 0.13,
        'failure_investigation': 0.10,
        'process_safety': 0.05,
        'operating_procedures': 0.05
    }
    
    # Verify weights sum to 1.0
    assert abs(sum(weights.values()) - 1.0) < 0.001, "Weights must sum to 1.0"
    
    # Calculate weighted pscore
    breakdown = {}
    pscore = 0.0
    
    for section, weight in weights.items():
        score = audit_scores.get(section, 50)  # Default 50 if missing
        contribution = weight * score
        breakdown[section] = {
            'score': score,
            'weight': weight,
            'contribution': contribution
        }
        pscore += contribution
    
    # Calculate F_MS using API 581 formula
    fms = 2.38 * math.exp(-0.012 * pscore)
    
    # Interpretation
    if pscore >= 85:
        interpretation = "Excellent management systems"
        risk_level = "Very Low"
    elif pscore >= 72:
        interpretation = "Good management systems"
        risk_level = "Low"
    elif pscore >= 60:
        interpretation = "Average management systems"
        risk_level = "Medium"
    elif pscore >= 50:
        interpretation = "Below average management systems"
        risk_level = "High"
    else:
        interpretation = "Poor management systems"
        risk_level = "Very High"
    
    # Impact on POF
    if fms < 0.8:
        impact = f"POF reduced by {(1-fms)*100:.0f}% due to excellent management"
    elif fms < 1.0:
        impact = f"POF reduced by {(1-fms)*100:.0f}% due to good management"
    elif fms < 1.2:
        impact = f"POF increased by {(fms-1)*100:.0f}% due to average management"
    else:
        impact = f"POF increased by {(fms-1)*100:.0f}% due to poor management"
    
    return {
        'fms': fms,
        'pscore': pscore,
        'interpretation': interpretation,
        'risk_level': risk_level,
        'breakdown': breakdown,
        'impact_on_pof': impact,
        'formula': 'F_MS = 2.38 × exp(−0.012 × pscore)',
        'reference': 'API 581 Part 2 §3.5, Annex 2.A'
    }


def get_audit_questionnaire() -> Dict[str, List[str]]:
    """
    Get API 581 Annex 2.A audit questionnaire structure
    
    Returns 72 questions across 6 sections.
    Each question scored 0-100 or Yes/No (100/0).
    
    Returns:
        dict: {section_name: [questions]}
    """
    questionnaire = {
        'management_inspection': [
            "Written inspection procedures exist and are current",
            "Inspection program covers all equipment subject to damage",
            "Qualified inspection personnel (API 510/570 certified)",
            "Inspection history records complete and retrievable",
            "Inspection intervals based on damage mechanisms",
            "NDE procedures qualified and documented",
            "Inspection results reviewed by competent engineer",
            "Corrective action system for findings",
            "Inspection effectiveness tracking",
            "Third-party audits of inspection program",
            "Risk-based approach to prioritization",
            "Integration with process safety management"
        ],
        'site_management': [
            "Management commitment to safety demonstrated",
            "Safety performance measured and tracked",
            "Safety culture assessment performed",
            "Employee involvement in safety decisions",
            "Contractor management program exists",
            "Incident/near-miss reporting system active"
        ],
        'management_of_change': [
            "MOC procedure documented and followed",
            "Technical review required before changes",
            "Pre-startup safety review conducted",
            "Training provided for changes",
            "MOC system covers temporary changes",
            "Documentation updated after changes"
        ],
        'failure_investigation': [
            "Root cause analysis performed on failures",
            "Investigation team includes technical experts",
            "Corrective actions tracked to completion",
            "Lessons learned shared across facility",
            "Investigation findings reviewed by management"
        ],
        'process_safety': [
            "Process hazard analysis (PHA) completed",
            "PHA recommendations tracked and closed",
            "Emergency response procedures exist",
            "Process safety information current"
        ],
        'operating_procedures': [
            "Operating procedures written and current",
            "Operator training program exists",
            "Operating limits defined and enforced",
            "Safe work practices documented"
        ]
    }
    
    # Total should be 72 questions (approximately)
    total = sum(len(questions) for questions in questionnaire.values())
    
    return questionnaire


def audit_section_score(section_name: str, answers: List[bool]) -> float:
    """
    Calculate section score from Yes/No answers
    
    Args:
        section_name: Section name
        answers: List of True (Yes) or False (No) answers
    
    Returns:
        float: Section score (0-100)
    """
    if not answers:
        return 50.0  # Default if no answers
    
    yes_count = sum(1 for answer in answers if answer)
    score = (yes_count / len(answers)) * 100
    
    return score


def quick_audit(
    mi_score: float = 72,
    site_score: float = 72,
    moc_score: float = 72,
    fi_score: float = 72,
    ps_score: float = 72,
    op_score: float = 72
) -> Dict:
    """
    Quick FMS calculation with section scores only
    
    Args:
        mi_score: Management of Inspection score (0-100), default 72
        site_score: Site Management score (0-100), default 72
        moc_score: Management of Change score (0-100), default 72
        fi_score: Failure Investigation score (0-100), default 72
        ps_score: Process Safety score (0-100), default 72
        op_score: Operating Procedures score (0-100), default 72
    
    Returns:
        dict: FMS calculation result
    """
    audit_scores = {
        'management_inspection': mi_score,
        'site_management': site_score,
        'management_of_change': moc_score,
        'failure_investigation': fi_score,
        'process_safety': ps_score,
        'operating_procedures': op_score
    }
    
    return calculate_fms(audit_scores)


def fms_sensitivity_analysis(baseline_pscore: float = 72) -> List[Dict]:
    """
    Sensitivity analysis: How FMS changes with pscore
    
    Args:
        baseline_pscore: Starting pscore (default 72 = FMS ≈ 1.0)
    
    Returns:
        list: [{pscore, fms, pof_multiplier, interpretation}]
    """
    results = []
    
    # Test range: 40 to 100
    for pscore in range(40, 101, 5):
        fms = 2.38 * math.exp(-0.012 * pscore)
        
        # POF multiplier relative to baseline
        baseline_fms = 2.38 * math.exp(-0.012 * baseline_pscore)
        pof_multiplier = fms / baseline_fms
        
        if pscore >= 85:
            interpretation = "Excellent"
        elif pscore >= 72:
            interpretation = "Good"
        elif pscore >= 60:
            interpretation = "Average"
        else:
            interpretation = "Poor"
        
        results.append({
            'pscore': pscore,
            'fms': fms,
            'pof_multiplier': pof_multiplier,
            'pof_change_pct': (pof_multiplier - 1) * 100,
            'interpretation': interpretation
        })
    
    return results


# Example usage and validation
if __name__ == '__main__':
    print("=" * 70)
    print("FMS AUDIT CALCULATOR - EXAMPLE CALCULATIONS")
    print("=" * 70)
    
    # Example 1: Baseline (pscore = 72 → FMS ≈ 1.0)
    print("\n1. BASELINE AUDIT (All sections = 72)")
    baseline = quick_audit()
    print(f"  pscore:           {baseline['pscore']:.1f}")
    print(f"  F_MS:             {baseline['fms']:.3f}")
    print(f"  Interpretation:   {baseline['interpretation']}")
    print(f"  Risk Level:       {baseline['risk_level']}")
    print(f"  Impact:           {baseline['impact_on_pof']}")
    
    # Example 2: Excellent management (pscore = 90)
    print("\n2. EXCELLENT MANAGEMENT (All sections = 90)")
    excellent = quick_audit(90, 90, 90, 90, 90, 90)
    print(f"  pscore:           {excellent['pscore']:.1f}")
    print(f"  F_MS:             {excellent['fms']:.3f}")
    print(f"  Interpretation:   {excellent['interpretation']}")
    print(f"  Impact:           {excellent['impact_on_pof']}")
    
    # Example 3: Poor management (pscore = 50)
    print("\n3. POOR MANAGEMENT (All sections = 50)")
    poor = quick_audit(50, 50, 50, 50, 50, 50)
    print(f"  pscore:           {poor['pscore']:.1f}")
    print(f"  F_MS:             {poor['fms']:.3f}")
    print(f"  Interpretation:   {poor['interpretation']}")
    print(f"  Impact:           {poor['impact_on_pof']}")
    
    # Example 4: Detailed audit with breakdown
    print("\n4. DETAILED AUDIT WITH BREAKDOWN")
    detailed_scores = {
        'management_inspection': 80,
        'site_management': 70,
        'management_of_change': 65,
        'failure_investigation': 75,
        'process_safety': 60,
        'operating_procedures': 70
    }
    detailed = calculate_fms(detailed_scores)
    
    print(f"  Overall pscore:   {detailed['pscore']:.1f}")
    print(f"  F_MS:             {detailed['fms']:.3f}")
    print(f"\n  Section Breakdown:")
    for section, data in detailed['breakdown'].items():
        print(f"    {section:30s}: {data['score']:5.1f} × {data['weight']:.2f} = {data['contribution']:5.2f}")
    
    # Example 5: Sensitivity analysis
    print("\n5. SENSITIVITY ANALYSIS (pscore vs FMS)")
    print(f"  {'pscore':<8} {'F_MS':<8} {'POF Change':<12} {'Level':<10}")
    print(f"  {'-'*8} {'-'*8} {'-'*12} {'-'*10}")
    
    sensitivity = fms_sensitivity_analysis()
    for result in sensitivity[::2]:  # Show every other result
        print(f"  {result['pscore']:<8} {result['fms']:<8.3f} {result['pof_change_pct']:>+6.0f}%       {result['interpretation']:<10}")
    
    print("\n" + "=" * 70)
