"""
API 581 Brittle Fracture Damage Factor Calculator
Section 8 - Low-temperature service brittle fracture
"""

from typing import Dict, Optional
from dataclasses import dataclass
import math


@dataclass
class BrittleFractureData:
    """Data for Brittle Fracture assessment"""
    material: str = 'carbon_steel'
    minimum_design_temp_f: float = -20.0  # °F
    charpy_impact_value_ft_lb: Optional[float] = None  # ft-lb at test temp
    charpy_test_temp_f: Optional[float] = None  # °F
    pwht_applied: bool = False
    age_since_inspection: float = 0.0
    num_inspections_A: int = 0
    num_inspections_B: int = 0
    num_inspections_C: int = 0
    manual_susceptibility: Optional[str] = None


class BrittleFractureCalculator:
    """
    Brittle Fracture DF Calculator
    Based on temperature relative to material toughness transition
    """
    
    # Material MDMT limits (°F) without impact testing required
    MATERIAL_MDMT = {
        'carbon_steel': -20,
        '304_stainless': -425,
        '316_stainless': -425,
        'duplex_stainless': -50,
        '9Cr-1Mo': 0,
        '5Cr-0.5Mo': 0,
        '2.25Cr-1Mo': -20,
        '1.25Cr-0.5Mo': -20
    }
    
    SEVERITY_INDEX = {'high': 1000, 'medium': 100, 'low': 10, 'none': 0}
    
    BASE_DF_TABLE = {
        0: {'E': 0, 'D': 0, 'C': 0, 'B': 0, 'A': 0},
        10: {'E': 10, 'D': {1: 8, 2: 6, 3: 4}, 'C': {1: 3, 2: 2, 3: 1}, 'B': {1: 1, 2: 1, 3: 1}, 'A': {1: 1, 2: 1, 3: 1}},
        100: {'E': 100, 'D': {1: 80, 2: 60, 3: 40}, 'C': {1: 33, 2: 20, 3: 10}, 'B': {1: 10, 2: 4, 3: 2}, 'A': {1: 5, 2: 1, 3: 1}},
        1000: {'E': 1000, 'D': {1: 800, 2: 600, 3: 400}, 'C': {1: 333, 2: 200, 3: 100}, 'B': {1: 100, 2: 40, 3: 20}, 'A': {1: 50, 2: 10, 3: 2}}
    }
    
    def calculate(self, data: BrittleFractureData) -> Dict:
        steps = []
        
        step1 = self._step1_temperature_assessment(data)
        steps.append(('Step 1 - Temperature Assessment', step1))
        
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
            'df_brittle_fracture': step7['df_brittle_fracture'],
            'susceptibility': step2['susceptibility'],
            'temp_margin_f': step1['temp_margin'],
            'severity_index': step3['svi'],
            'base_df': step6['df_base'],
            'all_steps': steps
        }
    
    def _step1_temperature_assessment(self, data: BrittleFractureData) -> Dict:
        """Step 1: Check operating temperature vs material limits"""
        mdmt = data.minimum_design_temp_f
        material = data.material if data.material in self.MATERIAL_MDMT else 'carbon_steel'
        mat_limit = self.MATERIAL_MDMT[material]
        
        temp_margin = mdmt - mat_limit
        
        return {
            'minimum_design_temp_f': mdmt,
            'material_limit_f': mat_limit,
            'temp_margin': temp_margin,
            'material': material
        }
    
    def _step2_susceptibility(self, step1: Dict, data: BrittleFractureData) -> Dict:
        """Step 2: Susceptibility from temperature margin"""
        if data.manual_susceptibility:
            return {'susceptibility': data.manual_susceptibility, 'reason': 'Manual override'}
        
        temp_margin = step1['temp_margin']
        mdmt = step1['minimum_design_temp_f']
        
        # Very low temp = high risk
        if mdmt < -100:
            if temp_margin < -20:
                return {'susceptibility': 'high', 'reason': 'Cryogenic service, inadequate material'}
            elif temp_margin < 0:
                return {'susceptibility': 'medium', 'reason': 'Cryogenic service, marginal material'}
            else:
                return {'susceptibility': 'low', 'reason': 'Cryogenic service, adequate material'}
        
        # Normal low temp
        if temp_margin < -20:
            return {'susceptibility': 'high', 'reason': 'Below material limit by >20°F'}
        elif temp_margin < 0:
            return {'susceptibility': 'medium', 'reason': 'Below material limit'}
        elif temp_margin < 20:
            return {'susceptibility': 'low', 'reason': 'Close to material limit'}
        else:
            return {'susceptibility': 'none', 'reason': 'Adequate temperature margin'}
    
    def _inspection_effectiveness(self, data: BrittleFractureData) -> Dict:
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
        df_brittle_fracture = min(df_base * age_factor, 5000.0)
        
        return {'df_brittle_fracture': df_brittle_fracture, 'df_base': df_base, 'age_factor': age_factor}


def calculate_brittle_fracture_df(data: BrittleFractureData) -> Dict:
    return BrittleFractureCalculator().calculate(data)
