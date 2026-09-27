"""
API 581 Sulfide Stress Cracking (SSC) Damage Factor Calculator
Section 2.C.10 - SSC in Carbon and Low-Alloy Steel
"""

from typing import Dict, Optional
from dataclasses import dataclass
import math


@dataclass
class SSCData:
    """Data specific to SSC assessment"""
    # Material and environment
    material: str = 'carbon_steel'  # carbon or low-alloy steel
    h2s_content_ppm: float = 100.0  # ppm H2S in water phase
    h2s_partial_pressure_psia: float = 0.1  # psia H2S partial pressure
    ph: float = 5.0  # pH of water
    free_cyanide_ppm: float = 0.0  # ppm free cyanide
    water_present: bool = True
    
    # Material properties
    max_brinell_hardness: float = 220.0  # BHN at weldments
    pwht_applied: bool = False  # Post-Weld Heat Treatment
    
    # Cracking history
    cracks_present: bool = False
    cracks_removed: bool = False
    
    # Time and inspection
    age_since_inspection: float = 0.0  # years since last SCC inspection
    num_inspections_A: int = 0
    num_inspections_B: int = 0
    num_inspections_C: int = 0
    num_inspections_D: int = 0
    num_inspections_E: int = 0
    
    # Manual susceptibility override
    manual_susceptibility: Optional[str] = None  # 'high', 'medium', 'low', 'none'


class SSCCalculator:
    """
    Sulfide Stress Cracking Damage Factor Calculator
    API 581 Section 2.C.10 - 7 Step Procedure
    """
    
    # Table 2.C.1.2: Severity Index (same for all SCC)
    SEVERITY_INDEX = {
        'high': 1000,
        'medium': 100,
        'low': 10,
        'none': 0
    }
    
    # Table 2.C.1.3: Base DF by Severity Index and Inspection Effectiveness
    BASE_DF_TABLE = {
        0: {'E': 0, 'D': 0, 'C': 0, 'B': 0, 'A': 0},
        1: {'E': 1, 'D': 1, 'C': 1, 'B': 1, 'A': 1},
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
    
    def calculate(self, ssc_data: SSCData) -> Dict:
        """
        Complete 7-step SSC DF calculation
        """
        self.calculation_steps = []
        
        # Step 1: Environmental severity
        step1 = self._step1_environmental_severity(ssc_data)
        self.calculation_steps.append(('Step 1 - Environmental Severity', step1))
        
        # Step 2: Susceptibility determination
        step2 = self._step2_susceptibility(step1, ssc_data)
        self.calculation_steps.append(('Step 2 - Susceptibility', step2))
        
        susceptibility = step2['final_susceptibility']
        
        # Step 3: Severity index
        step3 = self._step3_severity_index(susceptibility)
        self.calculation_steps.append(('Step 3 - Severity Index', step3))
        
        # Step 4: Time since inspection
        step4 = self._step4_time_since_inspection(ssc_data)
        self.calculation_steps.append(('Step 4 - Time Since Inspection', step4))
        
        # Step 5: Inspection effectiveness
        step5 = self._step5_inspection_effectiveness(ssc_data)
        self.calculation_steps.append(('Step 5 - Inspection Effectiveness', step5))
        
        # Step 6: Base DF
        step6 = self._step6_base_df(step3, step5)
        self.calculation_steps.append(('Step 6 - Base DF', step6))
        
        # Step 7: Final DF with time escalation
        step7 = self._step7_final_df(step6, step4)
        self.calculation_steps.append(('Step 7 - Final DF', step7))
        
        return {
            'df_ssc': step7['df_ssc'],
            'susceptibility': susceptibility,
            'environmental_severity': step1['severity'],
            'severity_index': step3['svi'],
            'base_df': step6['df_base'],
            'age_since_inspection': step4['age'],
            'highest_inspection': step5['highest_effectiveness'],
            'all_steps': self.calculation_steps
        }
    
    def _step1_environmental_severity(self, data: SSCData) -> Dict:
        """
        Step 1: Determine environmental severity from Table 2.C.10.2
        Based on H2S content and pH
        """
        if not data.water_present:
            return {
                'severity': 'none',
                'reason': 'No water present',
                'h2s_ppm': data.h2s_content_ppm,
                'ph': data.ph
            }
        
        h2s_ppm = data.h2s_content_ppm
        ph = data.ph
        h2s_psia = data.h2s_partial_pressure_psia
        cyanide = data.free_cyanide_ppm
        
        # Determine H2S range category
        if h2s_psia < 0.05:
            h2s_range = 'very_low'
        elif h2s_ppm <= 1:
            h2s_range = 'very_low'
        elif h2s_ppm <= 50:
            h2s_range = 'low'
        elif h2s_ppm <= 1000:
            h2s_range = 'moderate'
        elif h2s_ppm <= 10000:
            h2s_range = 'high'
        else:
            h2s_range = 'very_high'
        
        # Lookup severity from Table 2.C.10.2
        severity = self._lookup_environmental_severity(ph, h2s_range, cyanide)
        
        return {
            'severity': severity,
            'h2s_ppm': h2s_ppm,
            'h2s_psia': h2s_psia,
            'h2s_range': h2s_range,
            'ph': ph,
            'cyanide_ppm': cyanide,
            'method': 'table_2.C.10.2'
        }
    
    def _lookup_environmental_severity(self, ph: float, h2s_range: str, cyanide_ppm: float) -> str:
        """
        Lookup environmental severity from Table 2.C.10.2
        """
        # Very simplified logic based on table
        if h2s_range == 'very_low':
            return 'none'
        
        if ph < 4.5:
            if h2s_range == 'low':
                return 'low'
            elif h2s_range == 'moderate':
                return 'low'
            elif h2s_range == 'high':
                return 'moderate'
            else:  # very_high
                return 'high'
        
        elif ph < 6.5:
            if h2s_range == 'low':
                return 'none'
            elif h2s_range == 'moderate':
                return 'low'
            elif h2s_range == 'high':
                return 'low'
            else:  # very_high
                return 'moderate'
        
        elif ph <= 7.6:
            if h2s_range in ['low', 'moderate']:
                return 'none'
            elif h2s_range == 'high':
                return 'low'
            else:  # very_high
                return 'moderate'
        
        else:  # pH > 7.6
            # Check cyanide effect
            if cyanide_ppm > 20 and h2s_range in ['moderate', 'high', 'very_high']:
                # Increase one category
                if h2s_range == 'moderate':
                    return 'moderate'
                else:
                    return 'high'
            
            if h2s_range in ['low', 'moderate']:
                return 'none'
            elif h2s_range == 'high':
                return 'moderate'
            else:  # very_high
                return 'high'
    
    def _step2_susceptibility(self, step1: Dict, data: SSCData) -> Dict:
        """
        Step 2: Determine susceptibility from Table 2.C.10.3
        Based on environmental severity, hardness, and PWHT
        """
        # Check for cracks first
        if data.cracks_present and not data.cracks_removed:
            return {
                'final_susceptibility': 'high',
                'reason': 'Cracks detected and not removed',
                'cracks_present': True
            }
        
        # Manual override
        if data.manual_susceptibility:
            return {
                'final_susceptibility': data.manual_susceptibility,
                'reason': 'Manual override',
                'manual': True
            }
        
        env_severity = step1['severity']
        hardness = data.max_brinell_hardness
        pwht = data.pwht_applied
        
        # Table 2.C.10.3 lookup
        susceptibility = self._lookup_susceptibility_table(env_severity, hardness, pwht)
        
        return {
            'final_susceptibility': susceptibility,
            'environmental_severity': env_severity,
            'max_hardness_bhn': hardness,
            'pwht_applied': pwht,
            'method': 'table_2.C.10.3'
        }
    
    def _lookup_susceptibility_table(self, severity: str, hardness: float, pwht: bool) -> str:
        """
        Lookup from Table 2.C.10.3: Susceptibility to SSC
        """
        if severity == 'none':
            return 'none'
        
        # Hardness categories
        if hardness < 200:
            hardness_cat = 'low'
        elif hardness <= 237:
            hardness_cat = 'medium'
        else:
            hardness_cat = 'high'
        
        # High environmental severity
        if severity == 'high':
            if pwht:
                if hardness_cat == 'low':
                    return 'none'
                elif hardness_cat == 'medium':
                    return 'low'
                else:  # high
                    return 'medium'
            else:  # as-welded
                if hardness_cat == 'low':
                    return 'low'
                elif hardness_cat == 'medium':
                    return 'medium'
                else:  # high
                    return 'high'
        
        # Moderate environmental severity
        elif severity == 'moderate':
            if pwht:
                if hardness_cat == 'low':
                    return 'none'
                elif hardness_cat == 'medium':
                    return 'none'
                else:  # high
                    return 'low'
            else:  # as-welded
                if hardness_cat == 'low':
                    return 'low'
                elif hardness_cat == 'medium':
                    return 'medium'
                else:  # high
                    return 'high'
        
        # Low environmental severity
        elif severity == 'low':
            if pwht:
                if hardness_cat == 'high':
                    return 'low'
                else:
                    return 'none'
            else:  # as-welded
                if hardness_cat == 'low':
                    return 'low'
                elif hardness_cat == 'medium':
                    return 'low'
                else:  # high
                    return 'medium'
        
        return 'none'
    
    def _step3_severity_index(self, susceptibility: str) -> Dict:
        """Step 3: Get severity index from Table 2.C.1.2"""
        svi = self.SEVERITY_INDEX[susceptibility]
        return {'svi': svi, 'susceptibility': susceptibility}
    
    def _step4_time_since_inspection(self, data: SSCData) -> Dict:
        """Step 4: Time in service since last SCC inspection"""
        age = max(data.age_since_inspection, 0.0)
        return {'age': age}
    
    def _step5_inspection_effectiveness(self, data: SSCData) -> Dict:
        """Step 5: Determine highest inspection effectiveness"""
        inspections = {
            'A': data.num_inspections_A,
            'B': data.num_inspections_B,
            'C': data.num_inspections_C,
            'D': data.num_inspections_D,
            'E': data.num_inspections_E
        }
        
        # Find highest effectiveness with inspections
        for level in ['A', 'B', 'C', 'D', 'E']:
            if inspections[level] > 0:
                return {
                    'highest_effectiveness': level,
                    'num_inspections': min(inspections[level], 3),
                    'all_inspections': inspections
                }
        
        return {
            'highest_effectiveness': 'E',
            'num_inspections': 0,
            'all_inspections': inspections
        }
    
    def _step6_base_df(self, step3: Dict, step5: Dict) -> Dict:
        """Step 6: Base DF from Table 2.C.1.3"""
        svi = step3['svi']
        effectiveness = step5['highest_effectiveness']
        num_insp = step5['num_inspections']
        
        # Get base DF from table
        if svi not in self.BASE_DF_TABLE:
            svi = min(self.BASE_DF_TABLE.keys(), key=lambda x: abs(x - svi))
        
        df_row = self.BASE_DF_TABLE[svi]
        
        if effectiveness == 'E':
            df_base = df_row['E']
        elif isinstance(df_row[effectiveness], dict):
            df_base = df_row[effectiveness].get(num_insp, df_row[effectiveness][3])
        else:
            df_base = df_row[effectiveness]
        
        return {'df_base': df_base, 'svi': svi, 'effectiveness': effectiveness}
    
    def _step7_final_df(self, step6: Dict, step4: Dict) -> Dict:
        """
        Step 7: Calculate final DF with time escalation
        Equation 2.C.9: DF = min(DF_base × max(age, 1.0)^1.1, 5000)
        """
        df_base = step6['df_base']
        age = step4['age']
        
        # Time escalation factor
        age_factor = max(age, 1.0) ** 1.1
        
        # Final DF with cap at 5000
        df_ssc = min(df_base * age_factor, 5000.0)
        
        return {
            'df_ssc': df_ssc,
            'df_base': df_base,
            'age_factor': age_factor,
            'capped': df_ssc >= 5000.0
        }


def calculate_ssc_df(ssc_data: SSCData) -> Dict:
    """Convenience function"""
    calculator = SSCCalculator()
    return calculator.calculate(ssc_data)
