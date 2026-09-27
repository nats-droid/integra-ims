"""
API 581 CUI (Corrosion Under Insulation) Damage Factor Calculator
Section 2.D.3 - CUI on Ferritic Components
"""

from typing import Dict, Optional
from dataclasses import dataclass
import math
from scipy.stats import norm


@dataclass
class CUIData:
    """Data specific to CUI (Corrosion Under Insulation) assessment"""
    # Environmental driver (same as external corrosion)
    driver_category: str  # 'severe', 'moderate', 'mild', 'dry'
    
    # Component data
    furnished_thickness: float  # mm
    age: float  # years
    operating_temp: float  # °C
    
    # Insulation specific
    insulation_type: str  # 'foam', 'mineral_wool', 'cellular_glass', 'calcium_silicate'
    insulation_condition: str  # 'above_average', 'average', 'below_average'
    complexity: str  # 'below_average', 'average', 'above_average'
    
    # Design factors
    allows_water_pooling: bool = False
    soil_water_interface: bool = False
    
    # Coating data
    coating_install_date: Optional[str] = None
    expected_coating_life: float = 0.0  # years
    coating_failed_at_inspection: bool = False
    
    # Measured data
    last_inspection_date: Optional[str] = None
    measured_thickness: float = 0.0  # mm
    measured_wall_loss: float = 0.0  # mm (Le - CUI wall loss)
    age_since_inspection: float = 0.0  # years
    
    # Inspection history
    num_inspections_A: int = 0
    num_inspections_B: int = 0
    num_inspections_C: int = 0
    num_inspections_D: int = 0
    confidence_level: str = "low"
    
    # Assigned rate (optional)
    assigned_corrosion_rate: Optional[float] = None  # mm/year


class CUIDFCalculator:
    """
    CUI Damage Factor Calculator
    API 581 Section 2.D.3 - 17 Step Procedure
    """
    
    # Table 2.D.3.2: CUI Base Corrosion Rates (mm/year) by Driver and Temperature
    # CUI is most aggressive in 77-110°C range
    BASE_CORROSION_RATES = {
        'severe': {
            '<0': 0.15,
            '0-50': 0.40,
            '50-100': 0.75,  # Peak range
            '100-150': 0.50,
            '150-200': 0.20,
            '>200': 0.05
        },
        'moderate': {
            '<0': 0.08,
            '0-50': 0.20,
            '50-100': 0.40,
            '100-150': 0.25,
            '150-200': 0.10,
            '>200': 0.03
        },
        'mild': {
            '<0': 0.04,
            '0-50': 0.10,
            '50-100': 0.20,
            '100-150': 0.13,
            '150-200': 0.05,
            '>200': 0.02
        },
        'dry': {
            '<0': 0.02,
            '0-50': 0.04,
            '50-100': 0.08,
            '100-150': 0.05,
            '150-200': 0.02,
            '>200': 0.01
        }
    }
    
    # Table 2.D.3.3: Insulation Type Factors
    INSULATION_FACTORS = {
        'foam': 0.5,  # Closed cell foam - low water retention
        'cellular_glass': 0.75,  # Low water retention
        'mineral_wool': 1.5,  # High water retention
        'calcium_silicate': 2.0,  # Highest water retention
        'other': 1.0
    }
    
    # Prior probabilities (Part 2, Table 4.5)
    PRIOR_PROBABILITIES = {
        'low': {'Prp1': 0.25, 'Prp2': 0.50, 'Prp3': 0.25},
        'medium': {'Prp1': 0.50, 'Prp2': 0.35, 'Prp3': 0.15},
        'high': {'Prp1': 0.70, 'Prp2': 0.25, 'Prp3': 0.05}
    }
    
    # Conditional probabilities for localized CUI (Part 2, Table 4.6)
    CONDITIONAL_PROBABILITIES = {
        'A': {'Cop1': 0.95, 'Cop2': 0.70, 'Cop3': 0.30},
        'B': {'Cop1': 0.85, 'Cop2': 0.50, 'Cop3': 0.20},
        'C': {'Cop1': 0.70, 'Cop2': 0.40, 'Cop3': 0.10},
        'D': {'Cop1': 0.50, 'Cop2': 0.30, 'Cop3': 0.05}
    }
    
    # Coefficients of variance
    COV_DELTA_T = 0.20
    COV_SF = 0.20
    COV_P = 0.05
    
    # Damage states
    DS1 = 1.0
    DS2 = 2.0
    DS3 = 4.0
    
    def __init__(self):
        self.calculation_steps = []
    
    def calculate(
        self,
        cui_data: CUIData,
        component_data: Dict
    ) -> Dict:
        """
        Complete 17-step CUI DF calculation
        """
        self.calculation_steps = []
        
        # Step 1: Furnished thickness and age
        step1 = self._step1_thickness_age(cui_data)
        self.calculation_steps.append(('Step 1', step1))
        
        # Step 2: Check if rate assigned
        step2 = self._step2_check_assigned_rate(cui_data)
        self.calculation_steps.append(('Step 2', step2))
        
        if step2['rate_assigned']:
            Cr = step2['assigned_rate']
            step3 = {'skipped': True}
            step4 = {'skipped': True}
        else:
            # Step 3: Base corrosion rate
            step3 = self._step3_base_corrosion_rate(cui_data)
            self.calculation_steps.append(('Step 3', step3))
            
            # Step 4: Final corrosion rate with CUI-specific adjustments
            step4 = self._step4_final_corrosion_rate(step3, cui_data)
            self.calculation_steps.append(('Step 4', step4))
            
            Cr = step4['Cr']
        
        # Steps 5-17 are identical to external corrosion
        step5 = self._step5_inspection_time(cui_data, step1)
        self.calculation_steps.append(('Step 5', step5))
        
        step6 = self._step6_coating_time(cui_data)
        self.calculation_steps.append(('Step 6', step6))
        
        step7 = self._step7_expected_coating_age(cui_data)
        self.calculation_steps.append(('Step 7', step7))
        
        step8 = self._step8_coating_adjustment(step5, step6, step7, cui_data)
        self.calculation_steps.append(('Step 8', step8))
        
        step9 = self._step9_effective_age(step5, step8)
        self.calculation_steps.append(('Step 9', step9))
        
        step10 = self._step10_tmin(component_data)
        self.calculation_steps.append(('Step 10', step10))
        
        step11 = self._step11_art(Cr, step9, step5)
        self.calculation_steps.append(('Step 11', step11))
        
        step12 = self._step12_flow_stress(component_data)
        self.calculation_steps.append(('Step 12', step12))
        
        step13 = self._step13_strength_ratio(component_data, step5, step10, step12)
        self.calculation_steps.append(('Step 13', step13))
        
        step14 = self._step14_inspection_counts(cui_data)
        self.calculation_steps.append(('Step 14', step14))
        
        step15 = self._step15_inspection_effectiveness(cui_data, step14)
        self.calculation_steps.append(('Step 15', step15))
        
        step16 = self._step16_posterior_probabilities(step15)
        self.calculation_steps.append(('Step 16', step16))
        
        step17 = self._step17_beta_parameters(step11, step13)
        self.calculation_steps.append(('Step 17', step17))
        
        step18 = self._step18_final_df(step16, step17)
        self.calculation_steps.append(('Step 18', step18))
        
        return {
            'df_cui': step18['df_cui'],
            'corrosion_rate': Cr,
            'art': step11['Art'],
            'strength_ratio': step13['SRp_cui'],
            'effective_age': step9['age'],
            'insulation_factor': step4.get('F_INS', 1.0) if not step2['rate_assigned'] else 1.0,
            'all_steps': self.calculation_steps
        }
    
    def _step1_thickness_age(self, data: CUIData) -> Dict:
        """Step 1"""
        return {'t': data.furnished_thickness, 'age': data.age}
    
    def _step2_check_assigned_rate(self, data: CUIData) -> Dict:
        """Step 2"""
        if data.assigned_corrosion_rate is not None:
            return {'rate_assigned': True, 'assigned_rate': data.assigned_corrosion_rate}
        return {'rate_assigned': False}
    
    def _step3_base_corrosion_rate(self, data: CUIData) -> Dict:
        """Step 3: CUI base rate from table"""
        driver = data.driver_category
        temp = data.operating_temp
        
        if temp < 0:
            temp_range = '<0'
        elif temp < 50:
            temp_range = '0-50'
        elif temp < 100:
            temp_range = '50-100'
        elif temp < 150:
            temp_range = '100-150'
        elif temp < 200:
            temp_range = '150-200'
        else:
            temp_range = '>200'
        
        CrB = self.BASE_CORROSION_RATES[driver][temp_range]
        
        return {'CrB': CrB, 'driver': driver, 'temp_range': temp_range}
    
    def _step4_final_corrosion_rate(self, step3: Dict, data: CUIData) -> Dict:
        """Step 4: CUI-specific adjustment factors (Equation 2.D.14)"""
        CrB = step3['CrB']
        
        # F_INS: Insulation type factor (Table 2.D.3.3)
        F_INS = self.INSULATION_FACTORS.get(data.insulation_type, 1.0)
        
        # F_CM: Complexity factor
        if data.complexity == 'below_average':
            F_CM = 0.75
        elif data.complexity == 'above_average':
            F_CM = 1.25
        else:
            F_CM = 1.0
        
        # F_IC: Insulation condition factor
        if data.insulation_condition == 'below_average':
            F_IC = 1.25
        elif data.insulation_condition == 'above_average':
            F_IC = 0.75
        else:
            F_IC = 1.0
        
        # F_EQ: Equipment design factor
        F_EQ = 2.0 if data.allows_water_pooling else 1.0
        
        # F_IF: Interface factor
        F_IF = 2.0 if data.soil_water_interface else 1.0
        
        # Equation 2.D.14
        Cr = CrB * F_INS * F_CM * F_IC * max(F_EQ, F_IF)
        
        return {
            'Cr': Cr,
            'CrB': CrB,
            'F_INS': F_INS,
            'F_CM': F_CM,
            'F_IC': F_IC,
            'F_EQ': F_EQ,
            'F_IF': F_IF
        }
    
    def _step5_inspection_time(self, data: CUIData, step1: Dict) -> Dict:
        """Step 5"""
        if data.measured_thickness > 0:
            trde = data.measured_thickness
            if data.measured_wall_loss > 0:
                trde = step1['t'] - data.measured_wall_loss
            age_tke = data.age_since_inspection
        else:
            trde = step1['t']
            age_tke = step1['age']
        return {'trde': trde, 'age_tke': age_tke}
    
    def _step6_coating_time(self, data: CUIData) -> Dict:
        """Step 6"""
        age_coat = data.age if data.coating_install_date else 0.0
        return {'age_coat': age_coat}
    
    def _step7_expected_coating_age(self, data: CUIData) -> Dict:
        """Step 7"""
        return {'C_age': data.expected_coating_life}
    
    def _step8_coating_adjustment(self, step5, step6, step7, data: CUIData) -> Dict:
        """Step 8"""
        age_tke = step5['age_tke']
        age_coat = step6['age_coat']
        C_age = step7['C_age']
        
        if age_tke >= age_coat:
            Coat_adj = min(C_age, age_coat)
        else:
            if data.coating_failed_at_inspection:
                Coat_adj = 0.0
            else:
                Coat_adj = min(C_age, age_coat) - min(C_age, age_coat - age_tke)
        
        return {'Coat_adj': Coat_adj}
    
    def _step9_effective_age(self, step5, step8) -> Dict:
        """Step 9"""
        age = step5['age_tke'] - step8['Coat_adj']
        return {'age': max(age, 0.0)}
    
    def _step10_tmin(self, component_data: Dict) -> Dict:
        """Step 10"""
        P = component_data.get('design_pressure', 0.0)
        D = component_data.get('diameter', 1000.0)
        S = component_data.get('allowable_stress', 138.0)
        E = component_data.get('weld_joint_efficiency', 1.0)
        
        if (2 * S * E - P) > 0:
            tmin = (P * D) / (2 * S * E - P)
        else:
            tmin = component_data.get('furnished_thickness', 10.0) * 0.5
        
        return {'tmin': tmin, 'tc': tmin}
    
    def _step11_art(self, Cr: float, step9, step5) -> Dict:
        """Step 11"""
        age = step9['age']
        trde = step5['trde']
        Art = (Cr * age) / trde if trde > 0 else 0.0
        return {'Art': Art}
    
    def _step12_flow_stress(self, component_data: Dict) -> Dict:
        """Step 12"""
        YS = component_data.get('yield_strength', 240.0)
        TS = component_data.get('tensile_strength', 400.0)
        E = component_data.get('weld_joint_efficiency', 1.0)
        FS_cui = ((YS + TS) / 2.0) * E * 1.1
        return {'FS_cui': FS_cui}
    
    def _step13_strength_ratio(self, component_data, step5, step10, step12) -> Dict:
        """Step 13"""
        P = component_data.get('design_pressure', 0.0)
        D = component_data.get('diameter', 1000.0)
        FS_cui = step12['FS_cui']
        trde = step5['trde']
        
        component_type = component_data.get('component_type', 'cylinder')
        alpha = 2.0 if component_type == 'cylinder' else (4.0 if component_type == 'sphere' else 1.13)
        
        SRp_cui = (P * D) / (alpha * FS_cui * trde) if FS_cui > 0 and trde > 0 else 0.5
        return {'SRp_cui': SRp_cui, 'alpha': alpha}
    
    def _step14_inspection_counts(self, data: CUIData) -> Dict:
        """Step 14"""
        return {
            'N_A': data.num_inspections_A,
            'N_B': data.num_inspections_B,
            'N_C': data.num_inspections_C,
            'N_D': data.num_inspections_D
        }
    
    def _step15_inspection_effectiveness(self, data: CUIData, step14) -> Dict:
        """Step 15"""
        priors = self.PRIOR_PROBABILITIES[data.confidence_level]
        Prp1, Prp2, Prp3 = priors['Prp1'], priors['Prp2'], priors['Prp3']
        
        cond_probs = self.CONDITIONAL_PROBABILITIES
        N_A, N_B, N_C, N_D = step14['N_A'], step14['N_B'], step14['N_C'], step14['N_D']
        
        I1 = Prp1 * (cond_probs['A']['Cop1'] ** N_A) * (cond_probs['B']['Cop1'] ** N_B) * \
             (cond_probs['C']['Cop1'] ** N_C) * (cond_probs['D']['Cop1'] ** N_D)
        
        I2 = Prp2 * (cond_probs['A']['Cop2'] ** N_A) * (cond_probs['B']['Cop2'] ** N_B) * \
             (cond_probs['C']['Cop2'] ** N_C) * (cond_probs['D']['Cop2'] ** N_D)
        
        I3 = Prp3 * (cond_probs['A']['Cop3'] ** N_A) * (cond_probs['B']['Cop3'] ** N_B) * \
             (cond_probs['C']['Cop3'] ** N_C) * (cond_probs['D']['Cop3'] ** N_D)
        
        return {'I1': I1, 'I2': I2, 'I3': I3}
    
    def _step16_posterior_probabilities(self, step15) -> Dict:
        """Step 16"""
        I1, I2, I3 = step15['I1'], step15['I2'], step15['I3']
        I_sum = I1 + I2 + I3
        
        if I_sum > 0:
            Pop1, Pop2, Pop3 = I1 / I_sum, I2 / I_sum, I3 / I_sum
        else:
            Pop1, Pop2, Pop3 = 0.33, 0.33, 0.34
        
        return {'Pop1': Pop1, 'Pop2': Pop2, 'Pop3': Pop3}
    
    def _step17_beta_parameters(self, step11, step13) -> Dict:
        """Step 17"""
        Art = step11['Art']
        SRp = step13['SRp_cui']
        
        def calc_beta(DS):
            numerator = 1 - DS * Art - SRp
            denom_sq = (DS * Art * self.COV_DELTA_T) ** 2 + \
                       ((1 - DS * Art) * self.COV_SF) ** 2 + \
                       (SRp * self.COV_P) ** 2
            return numerator / math.sqrt(denom_sq) if denom_sq > 0 else 0.0
        
        return {
            'beta1': calc_beta(self.DS1),
            'beta2': calc_beta(self.DS2),
            'beta3': calc_beta(self.DS3)
        }
    
    def _step18_final_df(self, step16, step17) -> Dict:
        """Step 18"""
        Pop1, Pop2, Pop3 = step16['Pop1'], step16['Pop2'], step16['Pop3']
        beta1, beta2, beta3 = step17['beta1'], step17['beta2'], step17['beta3']
        
        term1 = Pop1 * norm.cdf(-beta1)
        term2 = Pop2 * norm.cdf(-beta2)
        term3 = Pop3 * norm.cdf(-beta3)
        
        df_cui = (term1 + term2 + term3) / 1.56e-4
        
        return {'df_cui': df_cui, 'term1': term1, 'term2': term2, 'term3': term3}


def calculate_cui_df(cui_data: CUIData, component_data: Dict) -> Dict:
    """Convenience function"""
    calculator = CUIDFCalculator()
    return calculator.calculate(cui_data, component_data)
