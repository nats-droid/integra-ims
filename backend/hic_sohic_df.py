"""
API 581 HIC/SOHIC in H2S Damage Factor Calculator
Section 2.C.9 - Hydrogen-Induced Cracking / Stress-Oriented Hydrogen-Induced Cracking
"""

from typing import Dict, Optional
from dataclasses import dataclass
import math


@dataclass
class HICSOHICData:
    """Data specific to HIC/SOHIC in H2S assessment"""
    # Material and environment
    material: str = 'carbon_steel'
    h2s_content_ppm: float = 100.0  # ppm H2S in water
    h2s_partial_pressure_psia: float = 0.1  # psia H2S partial pressure
    ph: float = 5.0  # pH of water
    free_cyanide_ppm: float = 0.0  # ppm free cyanide
    water_present: bool = True
    
    # Material properties - KEY DIFFERENCE FROM SSC
    sulfur_content_ppm: float = 100.0  # ppm S in steel (critical for HIC!)
    product_form: str = 'plate'  # 'plate' or 'pipe'
    pwht_applied: bool = False
    
    # Online monitoring (unique to HIC/SOHIC)
    hydrogen_probes: bool = False
    key_process_monitoring: bool = False
    
    # Cracking history
    cracks_present: bool = False
    cracks_removed: bool = False
    
    # Time and inspection
    age_since_inspection: float = 0.0
    num_inspections_A: int = 0
    num_inspections_B: int = 0
    num_inspections_C: int = 0
    num_inspections_D: int = 0
    num_inspections_E: int = 0
    
    manual_susceptibility: Optional[str] = None


class HICSOHICCalculator:
    """
    HIC/SOHIC Damage Factor Calculator
    API 581 Section 2.C.9 - 8 Step Procedure
    """
    
    SEVERITY_INDEX = {
        'high': 1000,
        'medium': 100,
        'low': 10,
        'none': 0
    }
    
    BASE_DF_TABLE = {
        0: {'E': 0, 'D': 0, 'C': 0, 'B': 0, 'A': 0},
        10: {
            'E': 10,
            'D': {1: 8, 2: 6, 3: 4},
            'C': {1: 3, 2: 2, 3: 1},
            'B': {1: 1, 2: 1, 3: 1},
            'A': {1: 1, 2: 1, 3: 1}
        },
        100: {
            'E': 100,
            'D': {1: 80, 2: 60, 3: 40},
            'C': {1: 33, 2: 20, 3: 10},
            'B': {1: 10, 2: 4, 3: 2},
            'A': {1: 5, 2: 1, 3: 1}
        },
        1000: {
            'E': 1000,
            'D': {1: 800, 2: 600, 3: 400},
            'C': {1: 333, 2: 200, 3: 100},
            'B': {1: 100, 2: 40, 3: 20},
            'A': {1: 50, 2: 10, 3: 2}
        }
    }
    
    def __init__(self):
        self.calculation_steps = []
    
    def calculate(self, data: HICSOHICData) -> Dict:
        """Complete 8-step HIC/SOHIC DF calculation"""
        self.calculation_steps = []
        
        # Step 1: Environmental severity
        step1 = self._step1_environmental_severity(data)
        self.calculation_steps.append(('Step 1 - Environmental Severity', step1))
        
        # Step 2: Susceptibility (based on sulfur content!)
        step2 = self._step2_susceptibility(step1, data)
        self.calculation_steps.append(('Step 2 - Susceptibility', step2))
        
        # Step 3: Severity index
        step3 = self._step3_severity_index(step2['final_susceptibility'])
        self.calculation_steps.append(('Step 3 - Severity Index', step3))
        
        # Step 4: Time since inspection
        step4 = self._step4_time_since_inspection(data)
        self.calculation_steps.append(('Step 4 - Time Since Inspection', step4))
        
        # Step 5: Inspection effectiveness
        step5 = self._step5_inspection_effectiveness(data)
        self.calculation_steps.append(('Step 5 - Inspection Effectiveness', step5))
        
        # Step 6: Base DF
        step6 = self._step6_base_df(step3, step5)
        self.calculation_steps.append(('Step 6 - Base DF', step6))
        
        # Step 7: Online monitoring factor
        step7 = self._step7_online_monitoring(data)
        self.calculation_steps.append(('Step 7 - Online Monitoring Factor', step7))
        
        # Step 8: Final DF with online monitoring adjustment
        step8 = self._step8_final_df(step6, step4, step7)
        self.calculation_steps.append(('Step 8 - Final DF', step8))
        
        return {
            'df_hic_sohic': step8['df_hic_sohic'],
            'susceptibility': step2['final_susceptibility'],
            'environmental_severity': step1['severity'],
            'severity_index': step3['svi'],
            'base_df': step6['df_base'],
            'online_monitoring_factor': step7['f_om'],
            'age_since_inspection': step4['age'],
            'highest_inspection': step5['highest_effectiveness'],
            'all_steps': self.calculation_steps
        }
    
    def _step1_environmental_severity(self, data: HICSOHICData) -> Dict:
        """Step 1: Environmental severity (same as SSC logic)"""
        if not data.water_present:
            return {'severity': 'none', 'reason': 'No water present'}
        
        h2s_ppm = data.h2s_content_ppm
        ph = data.ph
        cyanide = data.free_cyanide_ppm
        
        # Determine H2S range
        if h2s_ppm <= 1:
            h2s_range = 'very_low'
        elif h2s_ppm <= 50:
            h2s_range = 'low'
        elif h2s_ppm <= 1000:
            h2s_range = 'moderate'
        elif h2s_ppm <= 10000:
            h2s_range = 'high'
        else:
            h2s_range = 'very_high'
        
        severity = self._lookup_environmental_severity(ph, h2s_range, cyanide)
        
        return {
            'severity': severity,
            'h2s_ppm': h2s_ppm,
            'h2s_range': h2s_range,
            'ph': ph,
            'cyanide_ppm': cyanide
        }
    
    def _lookup_environmental_severity(self, ph: float, h2s_range: str, cyanide: float) -> str:
        """Lookup from Table 2.C.9.2"""
        if h2s_range == 'very_low':
            return 'none'
        
        if ph < 4.5:
            if h2s_range in ['low', 'moderate']:
                return 'low'
            elif h2s_range == 'high':
                return 'moderate'
            else:
                return 'high'
        elif ph < 6.5:
            if h2s_range == 'low':
                return 'none'
            elif h2s_range in ['moderate', 'high']:
                return 'low'
            else:
                return 'moderate'
        elif ph <= 7.6:
            if h2s_range in ['low', 'moderate']:
                return 'none'
            else:
                return 'low'
        else:  # pH > 7.6
            if cyanide > 20:
                return 'moderate' if h2s_range in ['moderate', 'high'] else 'high'
            return 'none' if h2s_range in ['low', 'moderate'] else 'moderate'
    
    def _step2_susceptibility(self, step1: Dict, data: HICSOHICData) -> Dict:
        """
        Step 2: Susceptibility based on SULFUR CONTENT
        KEY DIFFERENCE: HIC depends on steel cleanliness (S content)
        """
        if data.cracks_present and not data.cracks_removed:
            return {'final_susceptibility': 'high', 'reason': 'SOHIC detected'}
        
        if data.manual_susceptibility:
            return {'final_susceptibility': data.manual_susceptibility, 'reason': 'Manual override'}
        
        env_severity = step1['severity']
        sulfur_ppm = data.sulfur_content_ppm
        product_form = data.product_form
        pwht = data.pwht_applied
        
        susceptibility = self._lookup_hic_susceptibility(env_severity, sulfur_ppm, product_form, pwht)
        
        return {
            'final_susceptibility': susceptibility,
            'environmental_severity': env_severity,
            'sulfur_content_ppm': sulfur_ppm,
            'product_form': product_form,
            'pwht_applied': pwht
        }
    
    def _lookup_hic_susceptibility(self, severity: str, sulfur_ppm: float, form: str, pwht: bool) -> str:
        """
        Table 2.C.9.3: Susceptibility based on S content
        Plate more susceptible than pipe
        """
        if severity == 'none':
            return 'none'
        
        # Sulfur content categories
        if sulfur_ppm <= 50:
            s_cat = 'low'  # HIC-resistant steel
        elif sulfur_ppm <= 100:
            s_cat = 'medium'
        else:
            s_cat = 'high'  # Susceptible steel
        
        # Plate vs Pipe (plate more susceptible due to banding)
        form_factor = 1.0 if form == 'pipe' else 1.5  # Plate worse
        
        # High environmental severity
        if severity == 'high':
            if pwht:
                if s_cat == 'low':
                    return 'none'
                elif s_cat == 'medium':
                    return 'low'
                else:
                    return 'medium'
            else:
                if s_cat == 'low':
                    return 'low'
                elif s_cat == 'medium':
                    return 'medium' if form == 'plate' else 'low'
                else:
                    return 'high'
        
        # Moderate severity
        elif severity == 'moderate':
            if pwht:
                return 'none' if s_cat == 'low' else 'low'
            else:
                if s_cat == 'low':
                    return 'low'
                elif s_cat == 'medium':
                    return 'medium' if form == 'plate' else 'low'
                else:
                    return 'high'
        
        # Low severity
        elif severity == 'low':
            if s_cat == 'high' and not pwht:
                return 'medium' if form == 'plate' else 'low'
            return 'low' if s_cat != 'low' else 'none'
        
        return 'none'
    
    def _step3_severity_index(self, susceptibility: str) -> Dict:
        svi = self.SEVERITY_INDEX[susceptibility]
        return {'svi': svi, 'susceptibility': susceptibility}
    
    def _step4_time_since_inspection(self, data: HICSOHICData) -> Dict:
        return {'age': max(data.age_since_inspection, 0.0)}
    
    def _step5_inspection_effectiveness(self, data: HICSOHICData) -> Dict:
        inspections = {
            'A': data.num_inspections_A,
            'B': data.num_inspections_B,
            'C': data.num_inspections_C,
            'D': data.num_inspections_D,
            'E': data.num_inspections_E
        }
        
        for level in ['A', 'B', 'C', 'D', 'E']:
            if inspections[level] > 0:
                return {
                    'highest_effectiveness': level,
                    'num_inspections': min(inspections[level], 3),
                    'all_inspections': inspections
                }
        
        return {'highest_effectiveness': 'E', 'num_inspections': 0, 'all_inspections': inspections}
    
    def _step6_base_df(self, step3: Dict, step5: Dict) -> Dict:
        svi = step3['svi']
        effectiveness = step5['highest_effectiveness']
        num_insp = step5['num_inspections']
        
        if svi not in self.BASE_DF_TABLE:
            svi = min(self.BASE_DF_TABLE.keys(), key=lambda x: abs(x - svi))
        
        df_row = self.BASE_DF_TABLE[svi]
        
        if effectiveness == 'E':
            df_base = df_row['E']
        elif isinstance(df_row[effectiveness], dict):
            df_base = df_row[effectiveness].get(num_insp, df_row[effectiveness][3])
        else:
            df_base = df_row[effectiveness]
        
        return {'df_base': df_base, 'svi': svi}
    
    def _step7_online_monitoring(self, data: HICSOHICData) -> Dict:
        """
        Step 7: Online monitoring adjustment factor
        Table 2.C.9.4: F_OM
        """
        if data.hydrogen_probes and data.key_process_monitoring:
            f_om = 4.0  # Both methods
            method = 'hydrogen_probes + key_process_monitoring'
        elif data.hydrogen_probes or data.key_process_monitoring:
            f_om = 2.0  # One method
            method = 'hydrogen_probes' if data.hydrogen_probes else 'key_process_monitoring'
        else:
            f_om = 1.0  # No monitoring
            method = 'none'
        
        return {
            'f_om': f_om,
            'method': method,
            'hydrogen_probes': data.hydrogen_probes,
            'key_process_monitoring': data.key_process_monitoring
        }
    
    def _step8_final_df(self, step6: Dict, step4: Dict, step7: Dict) -> Dict:
        """
        Step 8: Final DF with online monitoring
        Equation C.2.8: DF = min((DF_base × max(age, 1.0)^1.1) / F_OM, 5000)
        """
        df_base = step6['df_base']
        age = step4['age']
        f_om = step7['f_om']
        
        age_factor = max(age, 1.0) ** 1.1
        df_hic_sohic = min((df_base * age_factor) / f_om, 5000.0)
        
        return {
            'df_hic_sohic': df_hic_sohic,
            'df_base': df_base,
            'age_factor': age_factor,
            'f_om': f_om,
            'capped': df_hic_sohic >= 5000.0
        }


def calculate_hic_sohic_df(data: HICSOHICData) -> Dict:
    """Convenience function"""
    calculator = HICSOHICCalculator()
    return calculator.calculate(data)
