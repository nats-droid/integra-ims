"""
API 581 High-Temperature Hydrogen Attack (HTHA) Damage Factor Calculator
Section 5 - HTHA uses Nelson Curves and different calculation approach
"""

from typing import Dict, Optional
from dataclasses import dataclass
import math


@dataclass
class HTHAData:
    """Data for HTHA assessment"""
    operating_temp_f: float = 800.0  # °F
    h2_partial_pressure_psia: float = 500.0  # psia
    carbon_content_pct: float = 0.15  # wt% C
    material_grade: str = 'carbon_steel'  # 'carbon_steel', '0.5Cr-0.5Mo', '1Cr-0.5Mo', '1.25Cr-0.5Mo', etc.
    pwht_applied: bool = False
    age_since_inspection: float = 0.0
    num_inspections_A: int = 0
    num_inspections_B: int = 0
    num_inspections_C: int = 0
    manual_susceptibility: Optional[str] = None


class HTHACalculator:
    """
    HTHA Damage Factor Calculator
    Uses Nelson Curves (API 941) - temperature vs H2 partial pressure
    """
    
    # Simplified Nelson Curve limits (temp_f: max_h2_psia)
    NELSON_CURVES = {
        'carbon_steel': {
            600: 200, 700: 100, 800: 50, 900: 25, 1000: 10
        },
        '0.5Cr-0.5Mo': {
            700: 500, 800: 300, 900: 150, 1000: 80, 1100: 40
        },
        '1Cr-0.5Mo': {
            800: 800, 900: 500, 1000: 300, 1100: 150, 1200: 80
        },
        '1.25Cr-0.5Mo': {
            850: 1000, 950: 700, 1050: 400, 1150: 200, 1250: 100
        },
        '2.25Cr-1Mo': {
            900: 1500, 1000: 1000, 1100: 600, 1200: 350, 1300: 180
        }
    }
    
    SEVERITY_INDEX = {'high': 1000, 'medium': 100, 'low': 10, 'none': 0}
    
    BASE_DF_TABLE = {
        0: {'E': 0, 'D': 0, 'C': 0, 'B': 0, 'A': 0},
        10: {'E': 10, 'D': {1: 8, 2: 6, 3: 4}, 'C': {1: 3, 2: 2, 3: 1}, 'B': {1: 1, 2: 1, 3: 1}, 'A': {1: 1, 2: 1, 3: 1}},
        100: {'E': 100, 'D': {1: 80, 2: 60, 3: 40}, 'C': {1: 33, 2: 20, 3: 10}, 'B': {1: 10, 2: 4, 3: 2}, 'A': {1: 5, 2: 1, 3: 1}},
        1000: {'E': 1000, 'D': {1: 800, 2: 600, 3: 400}, 'C': {1: 333, 2: 200, 3: 100}, 'B': {1: 100, 2: 40, 3: 20}, 'A': {1: 50, 2: 10, 3: 2}}
    }
    
    def calculate(self, data: HTHAData) -> Dict:
        steps = []
        
        step1 = self._step1_nelson_curve_check(data)
        steps.append(('Step 1 - Nelson Curve Check', step1))
        
        step2 = self._step2_susceptibility(step1, data)
        steps.append(('Step 2 - Susceptibility', step2))
        
        step3 = {'svi': self.SEVERITY_INDEX[step2['susceptibility']]}
        steps.append(('Step 3 - Severity Index', step3))
        
        step4 = {'age': max(data.age_since_inspection, 0.0)}
        steps.append(('Step 4 - Time Since Inspection', step4))
        
        step5 = self._step5_inspection_effectiveness(data)
        steps.append(('Step 5 - Inspection Effectiveness', step5))
        
        step6 = self._step6_base_df(step3, step5)
        steps.append(('Step 6 - Base DF', step6))
        
        step7 = self._step7_final_df(step6, step4)
        steps.append(('Step 7 - Final DF', step7))
        
        return {
            'df_htha': step7['df_htha'],
            'susceptibility': step2['susceptibility'],
            'nelson_curve_exceeded': step1['exceeded'],
            'safety_margin': step1.get('safety_margin', 0),
            'severity_index': step3['svi'],
            'base_df': step6['df_base'],
            'all_steps': steps
        }
    
    def _step1_nelson_curve_check(self, data: HTHAData) -> Dict:
        """Step 1: Check against Nelson Curves"""
        temp = data.operating_temp_f
        h2_pressure = data.h2_partial_pressure_psia
        material = data.material_grade
        
        if material not in self.NELSON_CURVES:
            material = 'carbon_steel'  # Default
        
        curve = self.NELSON_CURVES[material]
        
        # Interpolate Nelson curve limit
        temps = sorted(curve.keys())
        if temp <= temps[0]:
            limit = curve[temps[0]]
        elif temp >= temps[-1]:
            limit = curve[temps[-1]]
        else:
            # Linear interpolation
            for i in range(len(temps) - 1):
                if temps[i] <= temp <= temps[i + 1]:
                    t1, t2 = temps[i], temps[i + 1]
                    p1, p2 = curve[t1], curve[t2]
                    limit = p1 + (p2 - p1) * (temp - t1) / (t2 - t1)
                    break
        
        exceeded = h2_pressure > limit
        safety_margin = (limit - h2_pressure) / limit * 100 if limit > 0 else 0
        
        return {
            'exceeded': exceeded,
            'operating_temp_f': temp,
            'h2_partial_pressure_psia': h2_pressure,
            'nelson_limit_psia': limit,
            'safety_margin': safety_margin,
            'material_grade': material
        }
    
    def _step2_susceptibility(self, step1: Dict, data: HTHAData) -> Dict:
        """Step 2: Determine susceptibility"""
        if data.manual_susceptibility:
            return {'susceptibility': data.manual_susceptibility, 'reason': 'Manual override'}
        
        exceeded = step1['exceeded']
        margin = step1['safety_margin']
        
        if exceeded:
            # Above Nelson curve
            if margin < -50:  # 50% above limit
                return {'susceptibility': 'high', 'reason': 'Significantly above Nelson curve'}
            else:
                return {'susceptibility': 'medium', 'reason': 'Above Nelson curve'}
        else:
            # Below Nelson curve
            if margin > 50:  # 50% safety margin
                return {'susceptibility': 'none', 'reason': 'Well below Nelson curve'}
            elif margin > 20:
                return {'susceptibility': 'low', 'reason': 'Below Nelson curve with margin'}
            else:
                return {'susceptibility': 'medium', 'reason': 'Close to Nelson curve'}
    
    def _step5_inspection_effectiveness(self, data: HTHAData) -> Dict:
        insp = {'A': data.num_inspections_A, 'B': data.num_inspections_B, 'C': data.num_inspections_C}
        for level in ['A', 'B', 'C', 'D', 'E']:
            num = getattr(data, f'num_inspections_{level}', 0) if level in ['A', 'B', 'C'] else 0
            if num > 0:
                return {'highest_effectiveness': level, 'num_inspections': min(num, 3)}
        return {'highest_effectiveness': 'E', 'num_inspections': 0}
    
    def _step6_base_df(self, step3: Dict, step5: Dict) -> Dict:
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
    
    def _step7_final_df(self, step6: Dict, step4: Dict) -> Dict:
        df_base = step6['df_base']
        age = step4['age']
        
        age_factor = max(age, 1.0) ** 1.1
        df_htha = min(df_base * age_factor, 5000.0)
        
        return {'df_htha': df_htha, 'df_base': df_base, 'age_factor': age_factor}


def calculate_htha_df(data: HTHAData) -> Dict:
    return HTHACalculator().calculate(data)
