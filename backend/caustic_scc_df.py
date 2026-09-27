"""
API 581 Caustic SCC (Stress Corrosion Cracking) Damage Factor Calculator
Section 2.C.4 - Caustic Cracking in Carbon Steel
"""

from typing import Dict, Optional
from dataclasses import dataclass
import math


@dataclass
class CausticSCCData:
    """Data specific to Caustic SCC assessment"""
    # Material and environment
    material: str = 'carbon_steel'  # 'carbon_steel' or 'low_alloy_steel'
    naoh_concentration: float = 0.0  # wt% NaOH
    max_process_temp: float = 25.0  # °C
    
    # Fabrication and treatment
    stress_relieved: bool = False  # PWHT performed?
    heat_traced: bool = False  # Steam traced?
    steamed_out: bool = False  # Steamed out before water flush?
    
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


class CausticSCCCalculator:
    """
    Caustic SCC Damage Factor Calculator
    API 581 Section 2.C.4 - 6 Step Procedure
    """
    
    # Table 2.C.1.2: Severity Index for Caustic SCC
    SEVERITY_INDEX = {
        'high': 1000,
        'medium': 100,
        'low': 10,
        'none': 0
    }
    
    # Table 2.C.1.3: Base DF by Severity Index and Inspection Effectiveness
    # Format: {SVI: {inspection_effectiveness: {num_inspections: DF}}}
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
    
    def __init__(self):
        self.calculation_steps = []
    
    def calculate(self, scc_data: CausticSCCData) -> Dict:
        """
        Complete 6-step Caustic SCC DF calculation
        """
        self.calculation_steps = []
        
        # Step 1: Determine susceptibility
        step1 = self._step1_determine_susceptibility(scc_data)
        self.calculation_steps.append(('Step 1', step1))
        
        # Step 2: Get severity index
        step2 = self._step2_severity_index(step1)
        self.calculation_steps.append(('Step 2', step2))
        
        # Step 3: Time since inspection
        step3 = self._step3_time_since_inspection(scc_data)
        self.calculation_steps.append(('Step 3', step3))
        
        # Step 4: Inspection effectiveness
        step4 = self._step4_inspection_effectiveness(scc_data)
        self.calculation_steps.append(('Step 4', step4))
        
        # Step 5: Base DF
        step5 = self._step5_base_df(step2, step4)
        self.calculation_steps.append(('Step 5', step5))
        
        # Step 6: Final DF with time escalation
        step6 = self._step6_final_df(step5, step3)
        self.calculation_steps.append(('Step 6', step6))
        
        return {
            'df_caustic_scc': step6['df_caustic'],
            'susceptibility': step1['susceptibility'],
            'severity_index': step2['svi'],
            'base_df': step5['df_base'],
            'age_since_inspection': step3['age'],
            'highest_inspection': step4['highest_effectiveness'],
            'all_steps': self.calculation_steps
        }
    
    def _step1_determine_susceptibility(self, data: CausticSCCData) -> Dict:
        """
        Step 1: Determine susceptibility using Figure 2.C.4.1 logic
        """
        # Manual override by expert
        if data.manual_susceptibility:
            return {
                'susceptibility': data.manual_susceptibility,
                'method': 'manual_override'
            }
        
        # Cracks present?
        if data.cracks_present and not data.cracks_removed:
            return {
                'susceptibility': 'high',
                'method': 'cracks_present',
                'reason': 'Cracks detected and not removed'
            }
        
        # Not carbon/low-alloy steel or no NaOH
        if data.naoh_concentration == 0:
            return {
                'susceptibility': 'none',
                'method': 'screening',
                'reason': 'No NaOH present'
            }
        
        # Stress relieved?
        if data.stress_relieved:
            return {
                'susceptibility': 'none',
                'method': 'stress_relief',
                'reason': 'PWHT performed (stress relieved)'
            }
        
        # Figure 2.C.4.1 - NACE Caustic Soda Service Graph
        temp_f = data.max_process_temp * 9/5 + 32  # Convert to °F
        conc = data.naoh_concentration
        
        # Below 46°C (115°F) - not susceptible
        if temp_f < 115:
            return {
                'susceptibility': 'none',
                'method': 'temperature',
                'reason': f'Temperature {temp_f:.1f}°F < 115°F threshold'
            }
        
        # Determine area from graph
        area = self._determine_caustic_area(temp_f, conc)
        
        # Area A: No stress relief necessary
        if area == 'A':
            # But check for heat tracing or steam out
            if data.heat_traced or data.steamed_out:
                return {
                    'susceptibility': 'medium',
                    'method': 'graph_area_A_with_heating',
                    'reason': 'Area A but heat traced or steamed out',
                    'temp_f': temp_f,
                    'concentration': conc,
                    'area': area
                }
            else:
                # Low concentration check
                if conc < 5.0:
                    return {
                        'susceptibility': 'low',
                        'method': 'graph_area_A_low_conc',
                        'reason': 'Area A with <5% NaOH',
                        'temp_f': temp_f,
                        'concentration': conc,
                        'area': area
                    }
                else:
                    return {
                        'susceptibility': 'medium',
                        'method': 'graph_area_A',
                        'reason': 'Area A, no stress relief necessary',
                        'temp_f': temp_f,
                        'concentration': conc,
                        'area': area
                    }
        
        # Area B: Stress relieve welds & bends
        elif area == 'B':
            if data.heat_traced or data.steamed_out:
                return {
                    'susceptibility': 'high',
                    'method': 'graph_area_B_with_heating',
                    'reason': 'Area B with heat tracing/steam out',
                    'temp_f': temp_f,
                    'concentration': conc,
                    'area': area
                }
            else:
                return {
                    'susceptibility': 'medium',
                    'method': 'graph_area_B',
                    'reason': 'Area B - stress relief recommended',
                    'temp_f': temp_f,
                    'concentration': conc,
                    'area': area
                }
        
        # Area C: Consider nickel alloys
        else:  # area == 'C'
            return {
                'susceptibility': 'high',
                'method': 'graph_area_C',
                'reason': 'Area C - high severity, nickel alloys recommended',
                'temp_f': temp_f,
                'concentration': conc,
                'area': area
            }
    
    def _determine_caustic_area(self, temp_f: float, conc: float) -> str:
        """
        Determine area (A/B/C) from NACE Caustic Soda Service Graph
        Figure 2.C.4.1
        """
        # Simplified boundaries from graph
        # Area A: Low risk (< 140°F for most concentrations)
        # Area B: Medium risk (140-200°F)
        # Area C: High risk (> 200°F or high concentration)
        
        if temp_f < 140:
            return 'A'
        elif temp_f < 200:
            if conc < 20:
                return 'A'
            elif conc < 40:
                return 'B'
            else:
                return 'C'
        else:  # temp >= 200°F
            if conc < 10:
                return 'B'
            else:
                return 'C'
    
    def _step2_severity_index(self, step1: Dict) -> Dict:
        """Step 2: Get severity index from Table 2.C.1.2"""
        susceptibility = step1['susceptibility']
        svi = self.SEVERITY_INDEX[susceptibility]
        return {'svi': svi, 'susceptibility': susceptibility}
    
    def _step3_time_since_inspection(self, data: CausticSCCData) -> Dict:
        """Step 3: Time in service since last SCC inspection"""
        age = max(data.age_since_inspection, 0.0)
        return {'age': age}
    
    def _step4_inspection_effectiveness(self, data: CausticSCCData) -> Dict:
        """
        Step 4: Determine highest inspection effectiveness
        Combine multiple inspections per Part 2, Section 3.4.3
        """
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
                    'num_inspections': min(inspections[level], 3),  # Table caps at 3
                    'all_inspections': inspections
                }
        
        # No inspections
        return {
            'highest_effectiveness': 'E',
            'num_inspections': 0,
            'all_inspections': inspections
        }
    
    def _step5_base_df(self, step2: Dict, step4: Dict) -> Dict:
        """Step 5: Base DF from Table 2.C.1.3"""
        svi = step2['svi']
        effectiveness = step4['highest_effectiveness']
        num_insp = step4['num_inspections']
        
        # Get base DF from table
        if svi not in self.BASE_DF_TABLE:
            # Find closest SVI
            svi = min(self.BASE_DF_TABLE.keys(), key=lambda x: abs(x - svi))
        
        df_row = self.BASE_DF_TABLE[svi]
        
        if effectiveness == 'E':
            df_base = df_row['E']
        elif isinstance(df_row[effectiveness], dict):
            # Table has different values for 1/2/3+ inspections
            df_base = df_row[effectiveness].get(num_insp, df_row[effectiveness][3])
        else:
            # Single value for all inspection counts
            df_base = df_row[effectiveness]
        
        return {'df_base': df_base, 'svi': svi, 'effectiveness': effectiveness}
    
    def _step6_final_df(self, step5: Dict, step3: Dict) -> Dict:
        """
        Step 6: Calculate final DF with time escalation
        Equation 2.C.3: DF = min(DF_base × max(age, 1.0)^1.1, 5000)
        """
        df_base = step5['df_base']
        age = step3['age']
        
        # Time escalation factor
        age_factor = max(age, 1.0) ** 1.1
        
        # Final DF with cap at 5000
        df_caustic = min(df_base * age_factor, 5000.0)
        
        return {
            'df_caustic': df_caustic,
            'df_base': df_base,
            'age_factor': age_factor,
            'capped': df_caustic >= 5000.0
        }


def calculate_caustic_scc_df(scc_data: CausticSCCData) -> Dict:
    """Convenience function"""
    calculator = CausticSCCCalculator()
    return calculator.calculate(scc_data)
