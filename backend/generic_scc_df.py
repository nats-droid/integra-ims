"""
Generic SCC Damage Factor Calculator
Covers remaining SCC mechanisms with standard 6-step procedure
"""

from typing import Dict, Optional
from dataclasses import dataclass
import math


@dataclass
class GenericSCCData:
    """Generic SCC data structure"""
    mechanism_name: str = 'Generic SCC'
    susceptibility: str = 'medium'  # 'high', 'medium', 'low', 'none'
    age_since_inspection: float = 0.0
    num_inspections_A: int = 0
    num_inspections_B: int = 0
    num_inspections_C: int = 0
    num_inspections_D: int = 0
    num_inspections_E: int = 0


class GenericSCCCalculator:
    """
    Generic SCC Calculator - Standard 6-step procedure
    Used for: Alkaline Carbonate, Carbonate, PWSCC, HSC-HF
    """
    
    SEVERITY_INDEX = {'high': 1000, 'medium': 100, 'low': 10, 'none': 0}
    
    BASE_DF_TABLE = {
        0: {'E': 0, 'D': 0, 'C': 0, 'B': 0, 'A': 0},
        10: {'E': 10, 'D': {1: 8, 2: 6, 3: 4}, 'C': {1: 3, 2: 2, 3: 1}, 'B': {1: 1, 2: 1, 3: 1}, 'A': {1: 1, 2: 1, 3: 1}},
        100: {'E': 100, 'D': {1: 80, 2: 60, 3: 40}, 'C': {1: 33, 2: 20, 3: 10}, 'B': {1: 10, 2: 4, 3: 2}, 'A': {1: 5, 2: 1, 3: 1}},
        1000: {'E': 1000, 'D': {1: 800, 2: 600, 3: 400}, 'C': {1: 333, 2: 200, 3: 100}, 'B': {1: 100, 2: 40, 3: 20}, 'A': {1: 50, 2: 10, 3: 2}}
    }
    
    def calculate(self, data: GenericSCCData) -> Dict:
        steps = []
        
        step1 = {'susceptibility': data.susceptibility, 'mechanism': data.mechanism_name}
        steps.append(('Step 1 - Susceptibility', step1))
        
        step2 = {'svi': self.SEVERITY_INDEX[data.susceptibility]}
        steps.append(('Step 2 - Severity Index', step2))
        
        step3 = {'age': max(data.age_since_inspection, 0.0)}
        steps.append(('Step 3 - Time Since Inspection', step3))
        
        step4 = self._inspection_effectiveness(data)
        steps.append(('Step 4 - Inspection Effectiveness', step4))
        
        step5 = self._base_df(step2, step4)
        steps.append(('Step 5 - Base DF', step5))
        
        step6 = self._final_df(step5, step3)
        steps.append(('Step 6 - Final DF', step6))
        
        return {
            'df': step6['df'],
            'susceptibility': data.susceptibility,
            'severity_index': step2['svi'],
            'base_df': step5['df_base'],
            'mechanism': data.mechanism_name,
            'all_steps': steps
        }
    
    def _inspection_effectiveness(self, data: GenericSCCData) -> Dict:
        insp = {'A': data.num_inspections_A, 'B': data.num_inspections_B, 'C': data.num_inspections_C,
                'D': data.num_inspections_D, 'E': data.num_inspections_E}
        for level in ['A', 'B', 'C', 'D', 'E']:
            if insp[level] > 0:
                return {'highest_effectiveness': level, 'num_inspections': min(insp[level], 3)}
        return {'highest_effectiveness': 'E', 'num_inspections': 0}
    
    def _base_df(self, step2: Dict, step4: Dict) -> Dict:
        svi = step2['svi']
        eff = step4['highest_effectiveness']
        num = step4['num_inspections']
        
        df_row = self.BASE_DF_TABLE[svi]
        if eff == 'E':
            df_base = df_row['E']
        elif isinstance(df_row[eff], dict):
            df_base = df_row[eff].get(num, df_row[eff][3])
        else:
            df_base = df_row[eff]
        
        return {'df_base': df_base}
    
    def _final_df(self, step5: Dict, step3: Dict) -> Dict:
        df_base = step5['df_base']
        age = step3['age']
        
        age_factor = max(age, 1.0) ** 1.1
        df = min(df_base * age_factor, 5000.0)
        
        return {'df': df, 'df_base': df_base, 'age_factor': age_factor, 'capped': df >= 5000.0}


def calculate_generic_scc_df(data: GenericSCCData) -> Dict:
    return GenericSCCCalculator().calculate(data)


# Specific mechanism helpers
def calculate_alkaline_carbonate_scc(susceptibility: str, age: float, num_insp_A: int = 0, num_insp_B: int = 0, num_insp_C: int = 0) -> Dict:
    """Alkaline Carbonate SCC (Section 2.C.2)"""
    data = GenericSCCData(mechanism_name='Alkaline Carbonate SCC', susceptibility=susceptibility, 
                          age_since_inspection=age, num_inspections_A=num_insp_A, 
                          num_inspections_B=num_insp_B, num_inspections_C=num_insp_C)
    return calculate_generic_scc_df(data)


def calculate_carbonate_scc(susceptibility: str, age: float, num_insp_A: int = 0, num_insp_B: int = 0, num_insp_C: int = 0) -> Dict:
    """Carbonate SCC (Section 2.C.8)"""
    data = GenericSCCData(mechanism_name='Carbonate SCC', susceptibility=susceptibility,
                          age_since_inspection=age, num_inspections_A=num_insp_A,
                          num_inspections_B=num_insp_B, num_inspections_C=num_insp_C)
    return calculate_generic_scc_df(data)


def calculate_pwscc(susceptibility: str, age: float, num_insp_A: int = 0, num_insp_B: int = 0, num_insp_C: int = 0) -> Dict:
    """Primary Water SCC (Section 2.C.9)"""
    data = GenericSCCData(mechanism_name='PWSCC', susceptibility=susceptibility,
                          age_since_inspection=age, num_inspections_A=num_insp_A,
                          num_inspections_B=num_insp_B, num_inspections_C=num_insp_C)
    return calculate_generic_scc_df(data)


def calculate_hsc_hf(susceptibility: str, age: float, num_insp_A: int = 0, num_insp_B: int = 0, num_insp_C: int = 0) -> Dict:
    """Hydrogen Stress Cracking in HF (Section 2.C.7)"""
    data = GenericSCCData(mechanism_name='HSC-HF', susceptibility=susceptibility,
                          age_since_inspection=age, num_inspections_A=num_insp_A,
                          num_inspections_B=num_insp_B, num_inspections_C=num_insp_C)
    return calculate_generic_scc_df(data)
