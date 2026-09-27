"""
Part 4 Timeline Planning - Risk Planning Over Time
API 581 Part 4 - Planning for Inspections

Calculates risk trajectory over 10-year horizon with 0.5-year time steps,
optimizes target inspection dates, and ranks equipment by risk.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import math


class RiskTimeline:
    """
    Risk planning timeline with 0.5-year steps
    """
    def __init__(
        self,
        assessment_date: datetime,
        plan_horizon_years: float = 10.0,
        time_step_years: float = 0.5
    ):
        self.assessment_date = assessment_date
        self.plan_horizon_years = plan_horizon_years
        self.time_step_years = time_step_years
        self.time_steps = self._generate_time_steps()
    
    def _generate_time_steps(self) -> List[datetime]:
        """Generate time step dates"""
        steps = []
        current_years = 0.0
        
        while current_years <= self.plan_horizon_years:
            days = int(current_years * 365.25)
            step_date = self.assessment_date + timedelta(days=days)
            steps.append(step_date)
            current_years += self.time_step_years
        
        return steps
    
    def calculate_risk_trajectory(
        self,
        pof_0: float,
        cof: float,
        corrosion_rate_mpy: float,
        t_actual: float,
        t_required: float,
        inspection_dates: Optional[List[datetime]] = None,
        inspection_effectiveness: str = 'A'
    ) -> List[Dict]:
        """
        Calculate risk at each time step
        
        POF increases with time due to corrosion (wall thinning).
        POF resets after inspection based on effectiveness.
        
        Args:
            pof_0: Initial POF (yr^-1)
            cof: Consequence of failure (area-ft²)
            corrosion_rate_mpy: Corrosion rate (mils per year)
            t_actual: Current thickness (in)
            t_required: Required thickness (in)
            inspection_dates: List of planned inspection dates
            inspection_effectiveness: 'A', 'B', 'C', or 'D'
        
        Returns:
            List[{
                'date': datetime,
                'years_from_assessment': float,
                'thickness': float,
                'pof': float,
                'cof': float,
                'risk': float,
                'risk_category': str,
                'inspection_event': bool
            }]
        """
        trajectory = []
        
        # Inspection effectiveness reduction factors (API 581 Table 2-1 logic)
        effectiveness_factors = {
            'A': 0.1,   # Highly effective: 90% reduction
            'B': 0.25,  # Usually effective: 75% reduction
            'C': 0.5,   # Fairly effective: 50% reduction
            'D': 0.75,  # Poorly effective: 25% reduction
            'E': 1.0    # Ineffective: no reduction
        }
        
        reduction_factor = effectiveness_factors.get(inspection_effectiveness, 0.25)
        
        current_pof = pof_0
        current_thickness = t_actual
        
        for step_date in self.time_steps:
            years_elapsed = (step_date - self.assessment_date).days / 365.25
            
            # Calculate thickness at this time
            thickness_loss = (corrosion_rate_mpy / 1000) * years_elapsed
            current_thickness = t_actual - thickness_loss
            
            # Check if inspection occurs at this step
            inspection_event = False
            if inspection_dates:
                for insp_date in inspection_dates:
                    days_diff = abs((step_date - insp_date).days)
                    if days_diff < 90:  # Within 3 months = inspection event
                        inspection_event = True
                        # Reset POF after inspection
                        current_pof = current_pof * reduction_factor
                        break
            
            # POF increases with wall loss (simplified model)
            # More accurate: use DF calculation with updated thickness
            if current_thickness > t_required:
                # POF grows as thickness approaches tmin
                margin_ratio = (current_thickness - t_required) / (t_actual - t_required)
                # POF increases exponentially as margin decreases
                pof_multiplier = 1.0 / max(margin_ratio, 0.1)
            else:
                # Below tmin: very high POF
                pof_multiplier = 10.0
            
            current_pof = pof_0 * pof_multiplier
            
            # Risk = POF × COF
            risk = current_pof * cof
            
            # Risk category (5×5 matrix)
            risk_category = self._categorize_risk(risk)
            
            trajectory.append({
                'date': step_date,
                'date_str': step_date.strftime('%Y-%m-%d'),
                'years_from_assessment': years_elapsed,
                'thickness': current_thickness,
                'pof': current_pof,
                'cof': cof,
                'risk': risk,
                'risk_category': risk_category,
                'inspection_event': inspection_event,
                'below_tmin': current_thickness < t_required
            })
        
        return trajectory
    
    def _categorize_risk(self, risk: float) -> str:
        """
        Categorize risk into 5×5 matrix categories
        
        Risk = POF × COF
        """
        if risk < 100:
            return "1 - Low"
        elif risk < 1000:
            return "2 - Medium-Low"
        elif risk < 10000:
            return "3 - Medium"
        elif risk < 100000:
            return "4 - Medium-High"
        else:
            return "5 - High"
    
    def optimize_target_date(
        self,
        trajectory: List[Dict],
        max_acceptable_risk: float,
        code_interval_years: float,
        regulatory_interval_years: Optional[float] = None
    ) -> Dict:
        """
        Find optimal target inspection date that:
        1. Keeps risk below max acceptable
        2. Respects code and regulatory intervals
        
        Args:
            trajectory: Risk trajectory from calculate_risk_trajectory()
            max_acceptable_risk: Maximum acceptable risk (e.g., 10000 for Medium)
            code_interval_years: Code-based interval
            regulatory_interval_years: Regulatory cap
        
        Returns:
            {
                'optimal_date': datetime,
                'optimal_years': float,
                'risk_at_date': float,
                'risk_category': str,
                'governing_constraint': str
            }
        """
        # Find last date where risk <= max_acceptable_risk
        rbi_target_date = None
        rbi_target_risk = None
        
        for point in trajectory:
            if point['risk'] <= max_acceptable_risk:
                rbi_target_date = point['date']
                rbi_target_risk = point['risk']
            else:
                break  # Risk exceeded threshold
        
        if rbi_target_date is None:
            # Risk already above threshold
            rbi_target_date = self.assessment_date
            rbi_target_years = 0.0
        else:
            rbi_target_years = (rbi_target_date - self.assessment_date).days / 365.25
        
        # Code interval
        code_date = self.assessment_date + timedelta(days=int(code_interval_years * 365.25))
        
        # Regulatory interval
        if regulatory_interval_years:
            regulatory_date = self.assessment_date + timedelta(days=int(regulatory_interval_years * 365.25))
        else:
            regulatory_date = None
        
        # Find earliest (most conservative)
        candidates = [
            {'date': rbi_target_date, 'constraint': 'RBI (Risk-Based)', 'risk': rbi_target_risk},
            {'date': code_date, 'constraint': 'Code (API 570/510)', 'risk': None},
        ]
        
        if regulatory_date:
            candidates.append({'date': regulatory_date, 'constraint': 'Regulatory Cap', 'risk': None})
        
        optimal = min(candidates, key=lambda x: x['date'])
        optimal_years = (optimal['date'] - self.assessment_date).days / 365.25
        
        # Get risk at optimal date
        optimal_risk = None
        optimal_category = None
        for point in trajectory:
            if abs((point['date'] - optimal['date']).days) < 90:
                optimal_risk = point['risk']
                optimal_category = point['risk_category']
                break
        
        return {
            'optimal_date': optimal['date'],
            'optimal_date_str': optimal['date'].strftime('%Y-%m-%d'),
            'optimal_years': optimal_years,
            'risk_at_date': optimal_risk,
            'risk_category': optimal_category,
            'governing_constraint': optimal['constraint'],
            'rbi_target_years': rbi_target_years,
            'code_interval_years': code_interval_years,
            'regulatory_interval_years': regulatory_interval_years
        }


def rank_equipment_by_risk(
    equipment_list: List[Dict],
    sort_by: str = 'current_risk'
) -> List[Dict]:
    """
    Rank equipment by risk for prioritization
    
    Args:
        equipment_list: List of equipment with risk data
            [{
                'equipment_id': str,
                'current_risk': float,
                'peak_risk': float,
                'years_to_peak': float,
                'next_inspection_date': datetime
            }]
        sort_by: 'current_risk', 'peak_risk', 'next_inspection_date'
    
    Returns:
        Sorted list with rank added
    """
    if sort_by == 'current_risk':
        sorted_list = sorted(equipment_list, key=lambda x: x['current_risk'], reverse=True)
    elif sort_by == 'peak_risk':
        sorted_list = sorted(equipment_list, key=lambda x: x['peak_risk'], reverse=True)
    elif sort_by == 'next_inspection_date':
        sorted_list = sorted(equipment_list, key=lambda x: x['next_inspection_date'])
    else:
        sorted_list = equipment_list
    
    # Add rank
    for idx, equipment in enumerate(sorted_list, start=1):
        equipment['rank'] = idx
    
    return sorted_list


def calculate_inspection_cost_benefit(
    trajectory_no_inspection: List[Dict],
    trajectory_with_inspection: List[Dict],
    inspection_cost: float,
    failure_cost: float
) -> Dict:
    """
    Calculate cost-benefit of inspection
    
    Args:
        trajectory_no_inspection: Risk trajectory without inspection
        trajectory_with_inspection: Risk trajectory with inspection
        inspection_cost: Cost of inspection ($)
        failure_cost: Cost of failure ($)
    
    Returns:
        {
            'risk_reduction': float,
            'expected_cost_without': float,
            'expected_cost_with': float,
            'net_benefit': float,
            'benefit_cost_ratio': float
        }
    """
    # Calculate total expected cost over horizon
    # Expected cost = sum(POF × COF × time_step)
    
    cost_without = 0.0
    for point in trajectory_no_inspection:
        expected_failure_cost = point['pof'] * failure_cost * 0.5  # 0.5 year time step
        cost_without += expected_failure_cost
    
    cost_with = inspection_cost
    for point in trajectory_with_inspection:
        expected_failure_cost = point['pof'] * failure_cost * 0.5
        cost_with += expected_failure_cost
    
    net_benefit = cost_without - cost_with
    
    if inspection_cost > 0:
        benefit_cost_ratio = net_benefit / inspection_cost
    else:
        benefit_cost_ratio = float('inf')
    
    risk_reduction = cost_without - (cost_with - inspection_cost)
    
    return {
        'risk_reduction': risk_reduction,
        'expected_cost_without': cost_without,
        'expected_cost_with': cost_with,
        'net_benefit': net_benefit,
        'benefit_cost_ratio': benefit_cost_ratio,
        'recommendation': 'Inspect' if net_benefit > 0 else 'Defer'
    }


# Example usage
if __name__ == '__main__':
    print("=" * 70)
    print("PART 4 TIMELINE PLANNING - EXAMPLE CALCULATIONS")
    print("=" * 70)
    
    # Initialize timeline
    assessment_date = datetime(2026, 9, 27)
    timeline = RiskTimeline(assessment_date, plan_horizon_years=10.0)
    
    print(f"\nAssessment Date: {assessment_date.strftime('%Y-%m-%d')}")
    print(f"Plan Horizon: {timeline.plan_horizon_years} years")
    print(f"Time Steps: {len(timeline.time_steps)} (every {timeline.time_step_years} years)")
    
    # Example 1: Risk trajectory without inspection
    print("\n1. RISK TRAJECTORY (No Inspection)")
    trajectory_no_insp = timeline.calculate_risk_trajectory(
        pof_0=0.001,         # Initial POF = 0.001 yr^-1
        cof=1000,            # COF = 1000 area-ft²
        corrosion_rate_mpy=5.0,
        t_actual=0.500,
        t_required=0.250
    )
    
    print(f"\n  {'Year':<6} {'Thickness':<12} {'POF':<12} {'Risk':<12} {'Category':<15}")
    print(f"  {'-'*6} {'-'*12} {'-'*12} {'-'*12} {'-'*15}")
    for point in trajectory_no_insp[::4]:  # Every 2 years
        print(f"  {point['years_from_assessment']:>5.1f}  {point['thickness']:>10.4f}\"  {point['pof']:>10.6f}  {point['risk']:>10.1f}  {point['risk_category']:<15}")
    
    # Example 2: Risk trajectory with inspection
    print("\n2. RISK TRAJECTORY (With Inspection at Year 5)")
    inspection_date = datetime(2031, 9, 27)
    trajectory_with_insp = timeline.calculate_risk_trajectory(
        pof_0=0.001,
        cof=1000,
        corrosion_rate_mpy=5.0,
        t_actual=0.500,
        t_required=0.250,
        inspection_dates=[inspection_date],
        inspection_effectiveness='A'
    )
    
    print(f"\n  {'Year':<6} {'Thickness':<12} {'POF':<12} {'Risk':<12} {'Inspection':<12}")
    print(f"  {'-'*6} {'-'*12} {'-'*12} {'-'*12} {'-'*12}")
    for point in trajectory_with_insp[::4]:  # Every 2 years
        insp_marker = "✓ INSPECTED" if point['inspection_event'] else ""
        print(f"  {point['years_from_assessment']:>5.1f}  {point['thickness']:>10.4f}\"  {point['pof']:>10.6f}  {point['risk']:>10.1f}  {insp_marker:<12}")
    
    # Example 3: Optimize target date
    print("\n3. OPTIMIZE TARGET INSPECTION DATE")
    optimal = timeline.optimize_target_date(
        trajectory=trajectory_no_insp,
        max_acceptable_risk=10000,  # Medium risk threshold
        code_interval_years=5.0,
        regulatory_interval_years=3.0
    )
    
    print(f"  RBI target:        {optimal['rbi_target_years']:.1f} years")
    print(f"  Code interval:     {optimal['code_interval_years']:.1f} years")
    print(f"  Regulatory cap:    {optimal['regulatory_interval_years']:.1f} years")
    print(f"\n  Optimal date:      {optimal['optimal_date_str']}")
    print(f"  Optimal interval:  {optimal['optimal_years']:.1f} years")
    print(f"  Governing:         {optimal['governing_constraint']}")
    print(f"  Risk at date:      {optimal['risk_at_date']:.1f}")
    print(f"  Risk category:     {optimal['risk_category']}")
    
    print("\n" + "=" * 70)
