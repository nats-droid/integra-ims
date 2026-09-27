"""
API 581 Mechanical Fatigue and Lining Degradation Damage Factor Calculators
Covers: Mechanical Fatigue (Section 9), Lining Degradation (Section 2.D.4), Refractory Degradation (Section 2.D.5)
"""

from typing import Dict, Optional
from dataclasses import dataclass
import math


@dataclass
class MechanicalFatigueData:
    """Data for Mechanical Fatigue assessment"""
    component_type: str = 'piping'  # 'piping', 'vessel', 'heat_exchanger'
    operating_cycles_per_year: float = 100.0
    stress_range_ksi: float = 20.0
    design_life_cycles: float = 10000.0
    actual_cycles: float = 5000.0
    age_since_inspection: float = 0.0
    num_inspections_A: int = 0
    num_inspections_B: int = 0
    num_inspections_C: int = 0
    manual_susceptibility: Optional[str] = None


@dataclass
class LiningDegradationData:
    """Data for Lining/Refractory Degradation"""
    lining_type: str = 'refractory'  # 'refractory', 'polymer', 'glass'
    operating_temp_f: float = 800.0
    age_years: float = 10.0
    design_life_years: float = 15.0
    last_inspection_condition: str = 'good'  # 'good', 'fair', 'poor'
    age_since_inspection: float = 0.0
    num_inspections_A: int = 0
    num_inspections_B: int = 0
    num_inspections_C: int = 0
    manual_susceptibility: Optional[str] = None


class MechanicalFatigueCalculator:
    """
    Mechanical Fatigue DF Calculator
    Based on cyclic loading and stress amplitude
    """
    
    SEVERITY_INDEX = {'high': 1000, 'medium': 100, 'low': 10, 'none': 0}
    
    BASE_DF_TABLE = {
        0: {'E': 0, 'D': 0, 'C': 0, 'B': 0, 'A': 0},
        10: {'E': 10, 'D': {1: 8, 2: 6, 3: 4}, 'C': {1: 3, 2: 2, 3: 1}, 'B': {1: 1, 2: 1, 3: 1}, 'A': {1: 1, 2: 1, 3: 1}},
        100: {'E': 100, 'D': {1: 80, 2: 60, 3: 40}, 'C': {1: 33, 2: 20, 3: 10}, 'B': {1: 10, 2: 4, 3: 2}, 'A': {1: 5, 2: 1, 3: 1}},
        1000: {'E': 1000, 'D': {1: 800, 2: 600, 3: 400}, 'C': {1: 333, 2: 200, 3: 100}, 'B': {1: 100, 2: 40, 3: 20}, 'A': {1: 50, 2: 10, 3: 2}}
    }
    
    def calculate(self, data: MechanicalFatigueData) -> Dict:
        steps = []
        
        step1 = self._step1_cycle_assessment(data)
        steps.append(('Step 1 - Cycle Assessment', step1))
        
        step2 = self._step2_susceptibility(step1, data)
        steps.append(('Step 2 - Susceptibility', step2))
        
        step3 = {'svi': self.SEVERITY_INDEX[step2['susceptibility']]}
        steps.append(('Step 3 - Severity Index', step3))
        
        step4 = {'age': max(data.age_since_inspection, 0.0)}
        steps.append(('Step 4 - Time Since Inspection', step4))
        
        step5 = self._inspection_effectiveness(data)
        steps.append(('Step 5 - Inspection Effectiveness', step5))
        
        step6 = self._base_df(step3, step5)
        steps.append(('Step 6 - Base DF', step6))
        
        step7 = self._final_df(step6, step4)
        steps.append(('Step 7 - Final DF', step7))
        
        return {
            'df_fatigue': step7['df'],
            'susceptibility': step2['susceptibility'],
            'cycle_usage_fraction': step1['cycle_usage_fraction'],
            'severity_index': step3['svi'],
            'base_df': step6['df_base'],
            'all_steps': steps
        }
    
    def _step1_cycle_assessment(self, data: MechanicalFatigueData) -> Dict:
        """Step 1: Assess cycle usage"""
        design_cycles = data.design_life_cycles
        actual_cycles = data.actual_cycles
        
        cycle_usage_fraction = actual_cycles / design_cycles if design_cycles > 0 else 0
        
        return {
            'design_life_cycles': design_cycles,
            'actual_cycles': actual_cycles,
            'cycle_usage_fraction': cycle_usage_fraction,
            'operating_cycles_per_year': data.operating_cycles_per_year,
            'stress_range_ksi': data.stress_range_ksi
        }
    
    def _step2_susceptibility(self, step1: Dict, data: MechanicalFatigueData) -> Dict:
        """Step 2: Susceptibility from cycle usage"""
        if data.manual_susceptibility:
            return {'susceptibility': data.manual_susceptibility, 'reason': 'Manual override'}
        
        usage = step1['cycle_usage_fraction']
        
        if usage > 0.8:
            return {'susceptibility': 'high', 'reason': f'Cycle usage {usage*100:.0f}% of design life'}
        elif usage > 0.5:
            return {'susceptibility': 'medium', 'reason': f'Cycle usage {usage*100:.0f}% of design life'}
        elif usage > 0.25:
            return {'susceptibility': 'low', 'reason': f'Cycle usage {usage*100:.0f}% of design life'}
        else:
            return {'susceptibility': 'none', 'reason': f'Cycle usage {usage*100:.0f}% of design life'}
    
    def _inspection_effectiveness(self, data: MechanicalFatigueData) -> Dict:
        insp = {'A': data.num_inspections_A, 'B': data.num_inspections_B, 'C': data.num_inspections_C}
        for level in ['A', 'B', 'C', 'D', 'E']:
            num = insp.get(level, 0)
            if num > 0:
                return {'highest_effectiveness': level, 'num_inspections': min(num, 3)}
        return {'highest_effectiveness': 'E', 'num_inspections': 0}
    
    def _base_df(self, step3: Dict, step5: Dict) -> Dict:
        svi = step3['svi']
        eff = step5['highest_effectiveness']
        num = step5['num_inspections']
        
        df_row = self.BASE_DF_TABLE[svi]
        if eff == 'E':
            df_base = df_row['E']
        elif isinstance(df_row[eff], dict):
            df_base = df_row[eff].get(num, df_row[eff][3])
        else:
            df_base = df_row[eff]
        
        return {'df_base': df_base}
    
    def _final_df(self, step6: Dict, step4: Dict) -> Dict:
        df_base = step6['df_base']
        age = step4['age']
        
        age_factor = max(age, 1.0) ** 1.1
        df = min(df_base * age_factor, 5000.0)
        
        return {'df': df, 'df_base': df_base, 'age_factor': age_factor}


class LiningDegradationCalculator:
    """
    Lining/Refractory Degradation DF Calculator
    Based on age vs design life and condition
    """
    
    SEVERITY_INDEX = {'high': 1000, 'medium': 100, 'low': 10, 'none': 0}
    
    BASE_DF_TABLE = {
        0: {'E': 0, 'D': 0, 'C': 0, 'B': 0, 'A': 0},
        10: {'E': 10, 'D': {1: 8, 2: 6, 3: 4}, 'C': {1: 3, 2: 2, 3: 1}, 'B': {1: 1, 2: 1, 3: 1}, 'A': {1: 1, 2: 1, 3: 1}},
        100: {'E': 100, 'D': {1: 80, 2: 60, 3: 40}, 'C': {1: 33, 2: 20, 3: 10}, 'B': {1: 10, 2: 4, 3: 2}, 'A': {1: 5, 2: 1, 3: 1}},
        1000: {'E': 1000, 'D': {1: 800, 2: 600, 3: 400}, 'C': {1: 333, 2: 200, 3: 100}, 'B': {1: 100, 2: 40, 3: 20}, 'A': {1: 50, 2: 10, 3: 2}}
    }
    
    def calculate(self, data: LiningDegradationData) -> Dict:
        steps = []
        
        step1 = self._step1_age_assessment(data)
        steps.append(('Step 1 - Age Assessment', step1))
        
        step2 = self._step2_condition_assessment(data)
        steps.append(('Step 2 - Condition Assessment', step2))
        
        step3 = self._step3_susceptibility(step1, step2, data)
        steps.append(('Step 3 - Susceptibility', step3))
        
        step4 = {'svi': self.SEVERITY_INDEX[step3['susceptibility']]}
        steps.append(('Step 4 - Severity Index', step4))
        
        step5 = {'age': max(data.age_since_inspection, 0.0)}
        steps.append(('Step 5 - Time Since Inspection', step5))
        
        step6 = self._inspection_effectiveness(data)
        steps.append(('Step 6 - Inspection Effectiveness', step6))
        
        step7 = self._base_df(step4, step6)
        steps.append(('Step 7 - Base DF', step7))
        
        step8 = self._final_df(step7, step5)
        steps.append(('Step 8 - Final DF', step8))
        
        return {
            'df_lining': step8['df'],
            'susceptibility': step3['susceptibility'],
            'life_usage_fraction': step1['life_usage_fraction'],
            'condition': step2['condition_factor'],
            'severity_index': step4['svi'],
            'base_df': step7['df_base'],
            'all_steps': steps
        }
    
    def _step1_age_assessment(self, data: LiningDegradationData) -> Dict:
        """Step 1: Assess age vs design life"""
        life_usage_fraction = data.age_years / data.design_life_years if data.design_life_years > 0 else 0
        
        return {
            'age_years': data.age_years,
            'design_life_years': data.design_life_years,
            'life_usage_fraction': life_usage_fraction
        }
    
    def _step2_condition_assessment(self, data: LiningDegradationData) -> Dict:
        """Step 2: Assess condition from last inspection"""
        condition_map = {'good': 0.5, 'fair': 1.0, 'poor': 2.0, 'failed': 3.0}
        condition_factor = condition_map.get(data.last_inspection_condition, 1.0)
        
        return {
            'last_condition': data.last_inspection_condition,
            'condition_factor': condition_factor
        }
    
    def _step3_susceptibility(self, step1: Dict, step2: Dict, data: LiningDegradationData) -> Dict:
        """Step 3: Combined susceptibility"""
        if data.manual_susceptibility:
            return {'susceptibility': data.manual_susceptibility, 'reason': 'Manual override'}
        
        usage = step1['life_usage_fraction']
        condition = step2['condition_factor']
        
        # Combined severity
        combined = usage * condition
        
        if combined > 1.5:
            return {'susceptibility': 'high', 'reason': f'Combined severity {combined:.2f}'}
        elif combined > 0.8:
            return {'susceptibility': 'medium', 'reason': f'Combined severity {combined:.2f}'}
        elif combined > 0.3:
            return {'susceptibility': 'low', 'reason': f'Combined severity {combined:.2f}'}
        else:
            return {'susceptibility': 'none', 'reason': f'Combined severity {combined:.2f}'}
    
    def _inspection_effectiveness(self, data: LiningDegradationData) -> Dict:
        insp = {'A': data.num_inspections_A, 'B': data.num_inspections_B, 'C': data.num_inspections_C}
        for level in ['A', 'B', 'C', 'D', 'E']:
            num = insp.get(level, 0)
            if num > 0:
                return {'highest_effectiveness': level, 'num_inspections': min(num, 3)}
        return {'highest_effectiveness': 'E', 'num_inspections': 0}
    
    def _base_df(self, step4: Dict, step6: Dict) -> Dict:
        svi = step4['svi']
        eff = step6['highest_effectiveness']
        num = step6['num_inspections']
        
        df_row = self.BASE_DF_TABLE[svi]
        if eff == 'E':
            df_base = df_row['E']
        elif isinstance(df_row[eff], dict):
            df_base = df_row[eff].get(num, df_row[eff][3])
        else:
            df_base = df_row[eff]
        
        return {'df_base': df_base}
    
    def _final_df(self, step7: Dict, step5: Dict) -> Dict:
        df_base = step7['df_base']
        age = step5['age']
        
        age_factor = max(age, 1.0) ** 1.1
        df = min(df_base * age_factor, 5000.0)
        
        return {'df': df, 'df_base': df_base, 'age_factor': age_factor}


def calculate_mechanical_fatigue_df(data: MechanicalFatigueData) -> Dict:
    return MechanicalFatigueCalculator().calculate(data)


def calculate_lining_degradation_df(data: LiningDegradationData) -> Dict:
    return LiningDegradationCalculator().calculate(data)
