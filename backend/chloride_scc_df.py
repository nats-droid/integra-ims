"""
API 581 Chloride SCC (Stress Corrosion Cracking) Damage Factor Calculator
Section 2.C.5 - ClSCC in Austenitic Stainless Steel
"""

from typing import Dict, Optional
from dataclasses import dataclass
import math


@dataclass
class ChlorideSCCData:
    """Data specific to Chloride SCC assessment"""
    # Material and environment
    material: str = '300_series_ss'  # Austenitic stainless steel (304, 316, etc.)
    cl_concentration: float = 100.0  # ppm Cl- in water phase
    operating_temp: float = 80.0  # °C
    ph: float = 7.0  # pH of process water
    
    # Environmental modifiers
    oxygen_ppb: float = 200.0  # ppb O2
    has_deposits: bool = False  # Scale, deposits present?
    
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
    
    # Manual susceptibility override (if determined by expert)
    manual_susceptibility: Optional[str] = None  # 'high', 'medium', 'low', 'none'


class ChlorideSCCCalculator:
    """
    Chloride SCC Damage Factor Calculator
    API 581 Section 2.C.5 - 8 Step Procedure
    """
    
    # Table 2.C.1.2: Severity Index for ClSCC
    SEVERITY_INDEX = {
        'high': 5000,
        'medium': 500,
        'low': 50,
        'none': 0
    }
    
    # Table 2.C.1.3: Base DF by Severity Index and Inspection Effectiveness
    # (Same table as other SCC mechanisms - reused)
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
        50: {
            'E': 50,
            'D': {1: 40, 2: 30, 3: 20},
            'C': {1: 17, 2: 10, 3: 5},
            'B': {1: 5, 2: 2, 3: 1},
            'A': {1: 3, 2: 1, 3: 1}
        },
        100: {
            'E': 100,
            'D': {1: 80, 2: 60, 3: 40},
            'C': {1: 33, 2: 20, 3: 10},
            'B': {1: 10, 2: 4, 3: 2},
            'A': {1: 5, 2: 1, 3: 1}
        },
        500: {
            'E': 500,
            'D': {1: 400, 2: 300, 3: 200},
            'C': {1: 170, 2: 100, 3: 50},
            'B': {1: 50, 2: 20, 3: 10},
            'A': {1: 25, 2: 5, 3: 1}
        },
        1000: {
            'E': 1000,
            'D': {1: 800, 2: 600, 3: 400},
            'C': {1: 333, 2: 200, 3: 100},
            'B': {1: 100, 2: 40, 3: 20},
            'A': {1: 50, 2: 10, 3: 2}
        },
        5000: {
            'E': 5000,
            'D': {1: 4000, 2: 3000, 3: 2000},
            'C': {1: 1670, 2: 1000, 3: 500},
            'B': {1: 500, 2: 200, 3: 100},
            'A': {1: 250, 2: 50, 3: 10}
        }
    }
    
    # Table 2.C.5.2: Base Susceptibility by Temperature and pH
    # Simplified from full table
    def __init__(self):
        self.calculation_steps = []
    
    def calculate(self, scc_data: ChlorideSCCData) -> Dict:
        """
        Complete 8-step Chloride SCC DF calculation
        """
        self.calculation_steps = []
        
        # Step 1: Check for cracks
        step1 = self._step1_check_cracks(scc_data)
        self.calculation_steps.append(('Step 1', step1))
        
        if step1['cracks_present']:
            # Skip to Step 4 if cracks present
            susceptibility = 'high'
            step2 = {'skipped': True, 'reason': 'cracks_present'}
            step3 = {'skipped': True, 'reason': 'cracks_present'}
        else:
            # Step 2: Base susceptibility from table
            step2 = self._step2_base_susceptibility(scc_data)
            self.calculation_steps.append(('Step 2', step2))
            
            # Step 3: Apply modifiers
            step3 = self._step3_susceptibility_modifiers(step2, scc_data)
            self.calculation_steps.append(('Step 3', step3))
            
            susceptibility = step3['final_susceptibility']
        
        # Step 4: Get severity index
        step4 = self._step4_severity_index(susceptibility)
        self.calculation_steps.append(('Step 4', step4))
        
        # Step 5: Time since inspection
        step5 = self._step5_time_since_inspection(scc_data)
        self.calculation_steps.append(('Step 5', step5))
        
        # Step 6: Inspection effectiveness
        step6 = self._step6_inspection_effectiveness(scc_data)
        self.calculation_steps.append(('Step 6', step6))
        
        # Step 7: Base DF
        step7 = self._step7_base_df(step4, step6)
        self.calculation_steps.append(('Step 7', step7))
        
        # Step 8: Final DF with time escalation
        step8 = self._step8_final_df(step7, step5)
        self.calculation_steps.append(('Step 8', step8))
        
        return {
            'df_chloride_scc': step8['df_clscc'],
            'susceptibility': susceptibility,
            'severity_index': step4['svi'],
            'base_df': step7['df_base'],
            'age_since_inspection': step5['age'],
            'highest_inspection': step6['highest_effectiveness'],
            'all_steps': self.calculation_steps
        }
    
    def _step1_check_cracks(self, data: ChlorideSCCData) -> Dict:
        """Step 1: Check if cracks are present"""
        if data.cracks_present and not data.cracks_removed:
            return {
                'cracks_present': True,
                'reason': 'Cracks detected and not removed - automatic HIGH'
            }
        return {'cracks_present': False}
    
    def _step2_base_susceptibility(self, data: ChlorideSCCData) -> Dict:
        """
        Step 2: Determine base susceptibility from Table 2.C.5.2
        Based on temperature and pH
        """
        # Manual override
        if data.manual_susceptibility:
            return {
                'base_susceptibility': data.manual_susceptibility,
                'method': 'manual_override'
            }
        
        temp_f = data.operating_temp * 9/5 + 32
        ph = data.ph
        
        # Check if outside susceptible range
        if temp_f < 75 or temp_f > 345:
            return {
                'base_susceptibility': 'none',
                'method': 'temperature_out_of_range',
                'temp_f': temp_f,
                'ph': ph
            }
        
        if ph < 2.5:
            return {
                'base_susceptibility': 'none',
                'method': 'pitting_corrosion',
                'reason': 'pH < 2.5 → HCl corrosion, not ClSCC',
                'temp_f': temp_f,
                'ph': ph
            }
        
        if ph > 10.5:
            return {
                'base_susceptibility': 'none',
                'method': 'high_ph',
                'reason': 'pH > 10.5 → caustic cracking, not ClSCC',
                'temp_f': temp_f,
                'ph': ph
            }
        
        # Determine susceptibility from Table 2.C.5.2
        susceptibility = self._lookup_base_susceptibility(temp_f, ph)
        
        return {
            'base_susceptibility': susceptibility,
            'method': 'table_lookup',
            'temp_f': temp_f,
            'ph': ph
        }
    
    def _lookup_base_susceptibility(self, temp_f: float, ph: float) -> str:
        """
        Lookup base susceptibility from Table 2.C.5.2
        Simplified version of the full table
        """
        # Very simplified logic based on table patterns
        if temp_f < 75:
            return 'none'
        elif temp_f < 97.5:
            if ph < 4.5:
                return 'medium'
            elif ph < 6.0:
                return 'low'
            else:
                return 'none'
        elif temp_f < 120:
            if ph < 3.5:
                return 'high'
            elif ph < 5.0:
                return 'medium'
            elif ph < 8.5:
                return 'low'
            else:
                return 'none'
        elif temp_f < 165:
            if ph < 6.0:
                return 'high'
            elif ph < 9.5:
                return 'medium'
            elif ph < 10.5:
                return 'low'
            else:
                return 'none'
        else:  # 165-345°F
            if ph < 9.5:
                return 'high'
            elif ph < 10.5:
                return 'low'
            else:
                return 'none'
    
    def _step3_susceptibility_modifiers(self, step2: Dict, data: ChlorideSCCData) -> Dict:
        """
        Step 3: Apply susceptibility modifiers from Table 2.C.5.3
        Modifiers: Cl concentration, O2 level, deposits
        """
        base = step2['base_susceptibility']
        
        if base == 'none':
            return {
                'final_susceptibility': 'none',
                'modifier': 0,
                'reason': 'Base susceptibility is None - no modifiers applied'
            }
        
        modifier = 0
        reasons = []
        
        # Cl < 10 ppm: -1
        if data.cl_concentration < 10:
            modifier -= 1
            reasons.append('Cl < 10 ppm (-1)')
        
        # Oxygen < 90 ppb: -1
        if data.oxygen_ppb < 90:
            modifier -= 1
            reasons.append('O2 < 90 ppb (-1)')
        
        # Cl > 100 ppm: +1
        if data.cl_concentration > 100:
            modifier += 1
            reasons.append('Cl > 100 ppm (+1)')
        
        # Deposits: +1
        if data.has_deposits:
            modifier += 1
            reasons.append('Deposits present (+1)')
        
        # Apply modifier
        susceptibility_levels = ['none', 'low', 'medium', 'high']
        current_index = susceptibility_levels.index(base)
        new_index = max(0, min(3, current_index + modifier))
        final = susceptibility_levels[new_index]
        
        return {
            'base_susceptibility': base,
            'modifier': modifier,
            'final_susceptibility': final,
            'reasons': reasons
        }
    
    def _step4_severity_index(self, susceptibility: str) -> Dict:
        """Step 4: Get severity index from Table 2.C.1.2"""
        svi = self.SEVERITY_INDEX[susceptibility]
        return {'svi': svi, 'susceptibility': susceptibility}
    
    def _step5_time_since_inspection(self, data: ChlorideSCCData) -> Dict:
        """Step 5: Time in service since last SCC inspection"""
        age = max(data.age_since_inspection, 0.0)
        return {'age': age}
    
    def _step6_inspection_effectiveness(self, data: ChlorideSCCData) -> Dict:
        """Step 6: Determine highest inspection effectiveness"""
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
    
    def _step7_base_df(self, step4: Dict, step6: Dict) -> Dict:
        """Step 7: Base DF from Table 2.C.1.3"""
        svi = step4['svi']
        effectiveness = step6['highest_effectiveness']
        num_insp = step6['num_inspections']
        
        # Get base DF from table
        if svi not in self.BASE_DF_TABLE:
            # Find closest SVI
            svi = min(self.BASE_DF_TABLE.keys(), key=lambda x: abs(x - svi))
        
        df_row = self.BASE_DF_TABLE[svi]
        
        if effectiveness == 'E':
            df_base = df_row['E']
        elif isinstance(df_row[effectiveness], dict):
            df_base = df_row[effectiveness].get(num_insp, df_row[effectiveness][3])
        else:
            df_base = df_row[effectiveness]
        
        return {'df_base': df_base, 'svi': svi, 'effectiveness': effectiveness}
    
    def _step8_final_df(self, step7: Dict, step5: Dict) -> Dict:
        """
        Step 8: Calculate final DF with time escalation
        Equation 2.C.4: DF = min(DF_base × max(age, 1.0)^1.1, 5000)
        """
        df_base = step7['df_base']
        age = step5['age']
        
        # Time escalation factor
        age_factor = max(age, 1.0) ** 1.1
        
        # Final DF with cap at 5000
        df_clscc = min(df_base * age_factor, 5000.0)
        
        return {
            'df_clscc': df_clscc,
            'df_base': df_base,
            'age_factor': age_factor,
            'capped': df_clscc >= 5000.0
        }


def calculate_chloride_scc_df(scc_data: ChlorideSCCData) -> Dict:
    """Convenience function"""
    calculator = ChlorideSCCCalculator()
    return calculator.calculate(scc_data)
