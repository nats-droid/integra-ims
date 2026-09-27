"""
API 581 HIC/SOHIC in HF Damage Factor Calculator
Section 2.C.6 - Hydrogen-Induced Cracking in Hydrofluoric Acid
"""

from typing import Dict, Optional
from dataclasses import dataclass
import math


@dataclass
class HICSOHICHFData:
    """Data for HIC/SOHIC in HF assessment"""
    hf_present: bool = True
    sulfur_content_ppm: float = 100.0
    product_form: str = 'plate'  # 'plate' or 'pipe'
    pwht_applied: bool = False
    cracks_present: bool = False
    age_since_inspection: float = 0.0
    num_inspections_A: int = 0
    num_inspections_B: int = 0
    num_inspections_C: int = 0
    num_inspections_D: int = 0
    num_inspections_E: int = 0
    hydrogen_probes: bool = False
    key_process_monitoring: bool = False
    manual_susceptibility: Optional[str] = None


class HICSOHICHFCalculator:
    """HIC/SOHIC-HF Calculator - 7 steps (simpler than H2S)"""
    
    SEVERITY_INDEX = {'high': 1000, 'medium': 100, 'low': 10, 'none': 0}
    
    BASE_DF_TABLE = {
        0: {'E': 0, 'D': 0, 'C': 0, 'B': 0, 'A': 0},
        10: {'E': 10, 'D': {1: 8, 2: 6, 3: 4}, 'C': {1: 3, 2: 2, 3: 1}, 'B': {1: 1, 2: 1, 3: 1}, 'A': {1: 1, 2: 1, 3: 1}},
        100: {'E': 100, 'D': {1: 80, 2: 60, 3: 40}, 'C': {1: 33, 2: 20, 3: 10}, 'B': {1: 10, 2: 4, 3: 2}, 'A': {1: 5, 2: 1, 3: 1}},
        1000: {'E': 1000, 'D': {1: 800, 2: 600, 3: 400}, 'C': {1: 333, 2: 200, 3: 100}, 'B': {1: 100, 2: 40, 3: 20}, 'A': {1: 50, 2: 10, 3: 2}}
    }
    
    def calculate(self, data: HICSOHICHFData) -> Dict:
        steps = []
        
        step1 = self._step1_susceptibility(data)
        steps.append(('Step 1 - Susceptibility', step1))
        
        step2 = self._step2_severity_index(step1['susceptibility'])
        steps.append(('Step 2 - Severity Index', step2))
        
        step3 = {'age': max(data.age_since_inspection, 0.0)}
        steps.append(('Step 3 - Time Since Inspection', step3))
        
        step4 = self._step4_inspection_effectiveness(data)
        steps.append(('Step 4 - Inspection Effectiveness', step4))
        
        step5 = self._step5_base_df(step2, step4)
        steps.append(('Step 5 - Base DF', step5))
        
        step6 = self._step6_online_monitoring(data)
        steps.append(('Step 6 - Online Monitoring Factor', step6))
        
        step7 = self._step7_final_df(step5, step3, step6)
        steps.append(('Step 7 - Final DF', step7))
        
        return {
            'df_hic_sohic_hf': step7['df_hic_sohic_hf'],
            'susceptibility': step1['susceptibility'],
            'severity_index': step2['svi'],
            'base_df': step5['df_base'],
            'online_monitoring_factor': step6['f_om'],
            'all_steps': steps
        }
    
    def _step1_susceptibility(self, data: HICSOHICHFData) -> Dict:
        """Step 1: Susceptibility from Table 2.C.6.2"""
        if not data.hf_present:
            return {'susceptibility': 'none', 'reason': 'No HF present'}
        
        if data.cracks_present:
            return {'susceptibility': 'high', 'reason': 'Cracks detected'}
        
        if data.manual_susceptibility:
            return {'susceptibility': data.manual_susceptibility, 'reason': 'Manual override'}
        
        # Pipe is always Low for seamless
        if data.product_form == 'pipe':
            return {'susceptibility': 'low', 'reason': 'Seamless pipe'}
        
        # Plate depends on S content and PWHT
        sulfur_pct = data.sulfur_content_ppm / 10000.0
        
        if sulfur_pct > 0.01:  # High sulfur
            if data.pwht_applied:
                susc = 'medium'
            else:
                susc = 'high'
        else:  # Low sulfur
            susc = 'low'
        
        return {
            'susceptibility': susc,
            'sulfur_content_pct': sulfur_pct,
            'pwht_applied': data.pwht_applied,
            'product_form': data.product_form
        }
    
    def _step2_severity_index(self, susceptibility: str) -> Dict:
        return {'svi': self.SEVERITY_INDEX[susceptibility], 'susceptibility': susceptibility}
    
    def _step4_inspection_effectiveness(self, data: HICSOHICHFData) -> Dict:
        insp = {'A': data.num_inspections_A, 'B': data.num_inspections_B, 'C': data.num_inspections_C, 
                'D': data.num_inspections_D, 'E': data.num_inspections_E}
        for level in ['A', 'B', 'C', 'D', 'E']:
            if insp[level] > 0:
                return {'highest_effectiveness': level, 'num_inspections': min(insp[level], 3)}
        return {'highest_effectiveness': 'E', 'num_inspections': 0}
    
    def _step5_base_df(self, step2: Dict, step4: Dict) -> Dict:
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
    
    def _step6_online_monitoring(self, data: HICSOHICHFData) -> Dict:
        if data.hydrogen_probes and data.key_process_monitoring:
            return {'f_om': 4.0, 'method': 'both'}
        elif data.hydrogen_probes or data.key_process_monitoring:
            return {'f_om': 2.0, 'method': 'one'}
        return {'f_om': 1.0, 'method': 'none'}
    
    def _step7_final_df(self, step5: Dict, step3: Dict, step6: Dict) -> Dict:
        df_base = step5['df_base']
        age = step3['age']
        f_om = step6['f_om']
        
        age_factor = max(age, 1.0) ** 1.1
        df_hic_sohic_hf = min((df_base * age_factor) / f_om, 5000.0)
        
        return {'df_hic_sohic_hf': df_hic_sohic_hf, 'df_base': df_base, 'age_factor': age_factor, 'f_om': f_om}


def calculate_hic_sohic_hf_df(data: HICSOHICHFData) -> Dict:
    return HICSOHICHFCalculator().calculate(data)
