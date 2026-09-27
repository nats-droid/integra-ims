"""
API 581 Embrittlement Damage Factor Calculators
Covers: Sigma Phase, Temper Embrittlement, 885°F Embrittlement
"""

from typing import Dict, Optional
from dataclasses import dataclass
import math


@dataclass
class EmbrittlementData:
    """Generic embrittlement data"""
    mechanism: str = 'sigma_phase'  # 'sigma_phase', 'temper', '885f'
    material: str = 'duplex_stainless'
    operating_temp_f: float = 800.0
    exposure_time_hours: float = 10000.0
    age_since_inspection: float = 0.0
    num_inspections_A: int = 0
    num_inspections_B: int = 0
    num_inspections_C: int = 0
    manual_susceptibility: Optional[str] = None


class EmbrittlementCalculator:
    """
    Embrittlement DF Calculator
    - Sigma Phase: Duplex SS, 600-1000°F
    - Temper: Cr-Mo steels, 650-1100°F
    - 885°F: Ferritic SS, 700-950°F
    """
    
    # Critical temperature ranges and time thresholds
    CRITICAL_RANGES = {
        'sigma_phase': {
            'temp_range': (600, 1000),
            'peak_temp': 800,
            'critical_time_hours': 1000,
            'susceptible_materials': ['duplex_stainless', '2205', '2507']
        },
        'temper': {
            'temp_range': (650, 1100),
            'peak_temp': 875,
            'critical_time_hours': 10000,
            'susceptible_materials': ['2.25Cr-1Mo', '1.25Cr-0.5Mo', '3Cr-1Mo']
        },
        '885f': {
            'temp_range': (700, 950),
            'peak_temp': 885,
            'critical_time_hours': 5000,
            'susceptible_materials': ['409_stainless', '430_stainless', '446_stainless']
        }
    }
    
    SEVERITY_INDEX = {'high': 1000, 'medium': 100, 'low': 10, 'none': 0}
    
    BASE_DF_TABLE = {
        0: {'E': 0, 'D': 0, 'C': 0, 'B': 0, 'A': 0},
        10: {'E': 10, 'D': {1: 8, 2: 6, 3: 4}, 'C': {1: 3, 2: 2, 3: 1}, 'B': {1: 1, 2: 1, 3: 1}, 'A': {1: 1, 2: 1, 3: 1}},
        100: {'E': 100, 'D': {1: 80, 2: 60, 3: 40}, 'C': {1: 33, 2: 20, 3: 10}, 'B': {1: 10, 2: 4, 3: 2}, 'A': {1: 5, 2: 1, 3: 1}},
        1000: {'E': 1000, 'D': {1: 800, 2: 600, 3: 400}, 'C': {1: 333, 2: 200, 3: 100}, 'B': {1: 100, 2: 40, 3: 20}, 'A': {1: 50, 2: 10, 3: 2}}
    }
    
    def calculate(self, data: EmbrittlementData) -> Dict:
        steps = []
        
        step1 = self._step1_material_check(data)
        steps.append(('Step 1 - Material Susceptibility Check', step1))
        
        step2 = self._step2_temperature_time_assessment(data, step1)
        steps.append(('Step 2 - Temperature-Time Assessment', step2))
        
        step3 = self._step3_susceptibility(step2, data)
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
            'df_embrittlement': step8['df'],
            'mechanism': data.mechanism,
            'susceptibility': step3['susceptibility'],
            'in_critical_range': step2['in_critical_range'],
            'exposure_ratio': step2.get('exposure_ratio', 0),
            'severity_index': step4['svi'],
            'base_df': step7['df_base'],
            'all_steps': steps
        }
    
    def _step1_material_check(self, data: EmbrittlementData) -> Dict:
        """Step 1: Check if material is susceptible"""
        mechanism = data.mechanism
        material = data.material
        
        if mechanism not in self.CRITICAL_RANGES:
            mechanism = 'sigma_phase'
        
        critical = self.CRITICAL_RANGES[mechanism]
        susceptible = material in critical['susceptible_materials']
        
        return {
            'mechanism': mechanism,
            'material': material,
            'susceptible_material': susceptible,
            'susceptible_materials': critical['susceptible_materials']
        }
    
    def _step2_temperature_time_assessment(self, data: EmbrittlementData, step1: Dict) -> Dict:
        """Step 2: Assess temperature-time exposure"""
        mechanism = step1['mechanism']
        critical = self.CRITICAL_RANGES[mechanism]
        
        temp = data.operating_temp_f
        time = data.exposure_time_hours
        
        temp_min, temp_max = critical['temp_range']
        peak_temp = critical['peak_temp']
        critical_time = critical['critical_time_hours']
        
        in_critical_range = temp_min <= temp <= temp_max
        
        # Severity based on proximity to peak temp
        if in_critical_range:
            temp_deviation = abs(temp - peak_temp)
            temp_severity = 1.0 - (temp_deviation / ((temp_max - temp_min) / 2))
            temp_severity = max(0, min(1, temp_severity))
        else:
            temp_severity = 0
        
        # Time exposure ratio
        exposure_ratio = time / critical_time if critical_time > 0 else 0
        
        return {
            'operating_temp_f': temp,
            'temp_range': critical['temp_range'],
            'in_critical_range': in_critical_range,
            'temp_severity': temp_severity,
            'exposure_time_hours': time,
            'critical_time_hours': critical_time,
            'exposure_ratio': exposure_ratio
        }
    
    def _step3_susceptibility(self, step2: Dict, data: EmbrittlementData) -> Dict:
        """Step 3: Determine susceptibility"""
        if data.manual_susceptibility:
            return {'susceptibility': data.manual_susceptibility, 'reason': 'Manual override'}
        
        in_range = step2['in_critical_range']
        exposure_ratio = step2['exposure_ratio']
        temp_severity = step2['temp_severity']
        
        if not in_range:
            return {'susceptibility': 'none', 'reason': 'Outside critical temperature range'}
        
        # Combined severity from temp and time
        combined_severity = temp_severity * min(exposure_ratio, 2.0)
        
        if combined_severity > 1.5:
            return {'susceptibility': 'high', 'reason': f'High exposure (severity={combined_severity:.2f})'}
        elif combined_severity > 0.8:
            return {'susceptibility': 'medium', 'reason': f'Moderate exposure (severity={combined_severity:.2f})'}
        elif combined_severity > 0.3:
            return {'susceptibility': 'low', 'reason': f'Low exposure (severity={combined_severity:.2f})'}
        else:
            return {'susceptibility': 'none', 'reason': f'Minimal exposure (severity={combined_severity:.2f})'}
    
    def _inspection_effectiveness(self, data: EmbrittlementData) -> Dict:
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


def calculate_sigma_phase_df(material: str, temp_f: float, exposure_hours: float, age: float, 
                              num_insp_B: int = 0, num_insp_C: int = 0) -> Dict:
    """Sigma Phase Embrittlement"""
    data = EmbrittlementData(mechanism='sigma_phase', material=material, operating_temp_f=temp_f,
                             exposure_time_hours=exposure_hours, age_since_inspection=age,
                             num_inspections_B=num_insp_B, num_inspections_C=num_insp_C)
    return EmbrittlementCalculator().calculate(data)


def calculate_temper_embrittlement_df(material: str, temp_f: float, exposure_hours: float, age: float,
                                       num_insp_B: int = 0, num_insp_C: int = 0) -> Dict:
    """Temper Embrittlement"""
    data = EmbrittlementData(mechanism='temper', material=material, operating_temp_f=temp_f,
                             exposure_time_hours=exposure_hours, age_since_inspection=age,
                             num_inspections_B=num_insp_B, num_inspections_C=num_insp_C)
    return EmbrittlementCalculator().calculate(data)


def calculate_885f_embrittlement_df(material: str, temp_f: float, exposure_hours: float, age: float,
                                     num_insp_B: int = 0, num_insp_C: int = 0) -> Dict:
    """885°F Embrittlement"""
    data = EmbrittlementData(mechanism='885f', material=material, operating_temp_f=temp_f,
                             exposure_time_hours=exposure_hours, age_since_inspection=age,
                             num_inspections_B=num_insp_B, num_inspections_C=num_insp_C)
    return EmbrittlementCalculator().calculate(data)
