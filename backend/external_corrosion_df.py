"""
API 581 External Corrosion Damage Factor Calculator
Section 2.D.2 - External Corrosion on Ferritic Components
"""

from typing import Dict, Optional
from dataclasses import dataclass
import math
from scipy.stats import norm


@dataclass
class ExternalCorrosionData:
    """Data specific to external corrosion assessment"""
    # Environmental driver
    driver_category: str  # 'severe', 'moderate', 'mild', 'dry'
    
    # Component data
    furnished_thickness: float  # mm
    age: float  # years
    operating_temp: float  # °C
    
    # Design factors
    allows_water_pooling: bool = False  # Poor drainage design
    soil_water_interface: bool = False  # Enters soil or water
    
    # Coating data
    coating_install_date: Optional[str] = None  # ISO date or None if no coating
    expected_coating_life: float = 0.0  # years, 0 = no coating
    coating_failed_at_inspection: bool = False
    
    # Measured data (if available)
    last_inspection_date: Optional[str] = None
    measured_thickness: float = 0.0  # mm, 0 if not measured
    measured_wall_loss: float = 0.0  # mm, Le - external corrosion loss
    age_since_inspection: float = 0.0  # years
    
    # Inspection history
    num_inspections_A: int = 0
    num_inspections_B: int = 0
    num_inspections_C: int = 0
    num_inspections_D: int = 0
    confidence_level: str = "low"  # 'low', 'medium', 'high'
    
    # If corrosion rate is known/assigned
    assigned_corrosion_rate: Optional[float] = None  # mm/year


class ExternalCorrosionDFCalculator:
    """
    External Corrosion Damage Factor Calculator
    API 581 Section 2.D.2 - 18 Step Procedure
    """
    
    # Table 2.C.2.2: Base Corrosion Rates (mm/year) by Driver and Temperature
    BASE_CORROSION_RATES = {
        'severe': {
            '<0': 0.10,
            '0-50': 0.30,
            '50-100': 0.50,
            '100-150': 0.30,
            '150-200': 0.15,
            '>200': 0.05
        },
        'moderate': {
            '<0': 0.05,
            '0-50': 0.15,
            '50-100': 0.25,
            '100-150': 0.15,
            '150-200': 0.08,
            '>200': 0.03
        },
        'mild': {
            '<0': 0.03,
            '0-50': 0.08,
            '50-100': 0.13,
            '100-150': 0.08,
            '150-200': 0.04,
            '>200': 0.02
        },
        'dry': {
            '<0': 0.01,
            '0-50': 0.03,
            '50-100': 0.05,
            '100-150': 0.03,
            '150-200': 0.02,
            '>200': 0.01
        }
    }
    
    # Prior probabilities (from Part 2, Table 4.5)
    PRIOR_PROBABILITIES = {
        'low': {'Prp1': 0.25, 'Prp2': 0.50, 'Prp3': 0.25},
        'medium': {'Prp1': 0.50, 'Prp2': 0.35, 'Prp3': 0.15},
        'high': {'Prp1': 0.70, 'Prp2': 0.25, 'Prp3': 0.05}
    }
    
    # Conditional probabilities for general external corrosion (from Part 2, Table 4.6)
    CONDITIONAL_PROBABILITIES = {
        'A': {'Cop1': 0.99, 'Cop2': 0.85, 'Cop3': 0.40},
        'B': {'Cop1': 0.95, 'Cop2': 0.70, 'Cop3': 0.30},
        'C': {'Cop1': 0.85, 'Cop2': 0.50, 'Cop3': 0.20},
        'D': {'Cop1': 0.70, 'Cop2': 0.40, 'Cop3': 0.10}
    }
    
    # Coefficients of variance
    COV_DELTA_T = 0.20
    COV_SF = 0.20
    COV_P = 0.05
    
    # Damage state factors
    DS1 = 1.0
    DS2 = 2.0
    DS3 = 4.0
    
    def __init__(self):
        self.calculation_steps = []
    
    def calculate(
        self,
        ext_corr_data: ExternalCorrosionData,
        component_data: Dict,  # Same as thinning: diameter, pressure, YS, TS, etc.
    ) -> Dict:
        """
        Complete 18-step external corrosion DF calculation
        """
        self.calculation_steps = []
        
        # Step 1: Furnished thickness and age
        step1 = self._step1_thickness_age(ext_corr_data)
        self.calculation_steps.append(('Step 1', step1))
        
        # Step 2: Check if rate is assigned
        step2 = self._step2_check_assigned_rate(ext_corr_data)
        self.calculation_steps.append(('Step 2', step2))
        
        if step2['rate_assigned']:
            # Skip to Step 5 if rate is assigned
            Cr = step2['assigned_rate']
            step3 = {'skipped': True}
            step4 = {'skipped': True}
        else:
            # Step 3: Determine base corrosion rate
            step3 = self._step3_base_corrosion_rate(ext_corr_data)
            self.calculation_steps.append(('Step 3', step3))
            
            # Step 4: Calculate final corrosion rate with adjustments
            step4 = self._step4_final_corrosion_rate(step3, ext_corr_data)
            self.calculation_steps.append(('Step 4', step4))
            
            Cr = step4['Cr']
        
        # Step 5: Time since last known inspection
        step5 = self._step5_inspection_time(ext_corr_data, step1)
        self.calculation_steps.append(('Step 5', step5))
        
        # Step 6: Coating installation time
        step6 = self._step6_coating_time(ext_corr_data)
        self.calculation_steps.append(('Step 6', step6))
        
        # Step 7: Expected coating age
        step7 = self._step7_expected_coating_age(ext_corr_data)
        self.calculation_steps.append(('Step 7', step7))
        
        # Step 8: Coating adjustment
        step8 = self._step8_coating_adjustment(step5, step6, step7, ext_corr_data)
        self.calculation_steps.append(('Step 8', step8))
        
        # Step 9: Effective in-service time
        step9 = self._step9_effective_age(step5, step8)
        self.calculation_steps.append(('Step 9', step9))
        
        # Step 10: Minimum required thickness
        step10 = self._step10_tmin(component_data)
        self.calculation_steps.append(('Step 10', step10))
        
        # Step 11: Art parameter
        step11 = self._step11_art(Cr, step9, step5)
        self.calculation_steps.append(('Step 11', step11))
        
        # Step 12: Flow stress
        step12 = self._step12_flow_stress(component_data)
        self.calculation_steps.append(('Step 12', step12))
        
        # Step 13: Strength ratio
        step13 = self._step13_strength_ratio(component_data, step5, step10, step12)
        self.calculation_steps.append(('Step 13', step13))
        
        # Step 14: Inspection counts
        step14 = self._step14_inspection_counts(ext_corr_data)
        self.calculation_steps.append(('Step 14', step14))
        
        # Step 15: Inspection effectiveness factors
        step15 = self._step15_inspection_effectiveness(ext_corr_data, step14)
        self.calculation_steps.append(('Step 15', step15))
        
        # Step 16: Posterior probabilities
        step16 = self._step16_posterior_probabilities(step15)
        self.calculation_steps.append(('Step 16', step16))
        
        # Step 17: Beta parameters
        step17 = self._step17_beta_parameters(step11, step13)
        self.calculation_steps.append(('Step 17', step17))
        
        # Step 18: Final DF
        step18 = self._step18_final_df(step16, step17)
        self.calculation_steps.append(('Step 18', step18))
        
        return {
            'df_external': step18['df_extcor'],
            'corrosion_rate': Cr,
            'art': step11['Art'],
            'strength_ratio': step13['SRp_extcor'],
            'effective_age': step9['age'],
            'coating_adjustment': step8['Coat_adj'],
            'all_steps': self.calculation_steps
        }
    
    def _step1_thickness_age(self, data: ExternalCorrosionData) -> Dict:
        """Step 1: Determine furnished thickness and age"""
        return {
            't': data.furnished_thickness,
            'age': data.age
        }
    
    def _step2_check_assigned_rate(self, data: ExternalCorrosionData) -> Dict:
        """Step 2: Check if corrosion rate is assigned by specialist"""
        if data.assigned_corrosion_rate is not None:
            return {
                'rate_assigned': True,
                'assigned_rate': data.assigned_corrosion_rate
            }
        else:
            return {'rate_assigned': False}
    
    def _step3_base_corrosion_rate(self, data: ExternalCorrosionData) -> Dict:
        """Step 3: Determine base corrosion rate from table"""
        driver = data.driver_category
        temp = data.operating_temp
        
        # Determine temperature range
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
        
        return {
            'CrB': CrB,
            'driver': driver,
            'temp_range': temp_range
        }
    
    def _step4_final_corrosion_rate(
        self,
        step3: Dict,
        data: ExternalCorrosionData
    ) -> Dict:
        """Step 4: Calculate final corrosion rate with adjustment factors"""
        CrB = step3['CrB']
        
        # Adjustment for equipment design (Equation 2.D.1)
        F_EQ = 2.0 if data.allows_water_pooling else 1.0
        
        # Adjustment for interface with soil/water
        F_IF = 2.0 if data.soil_water_interface else 1.0
        
        # Final rate
        Cr = CrB * max(F_EQ, F_IF)
        
        return {
            'Cr': Cr,
            'CrB': CrB,
            'F_EQ': F_EQ,
            'F_IF': F_IF
        }
    
    def _step5_inspection_time(
        self,
        data: ExternalCorrosionData,
        step1: Dict
    ) -> Dict:
        """Step 5: Time since last known inspection thickness"""
        if data.measured_thickness > 0:
            # Has inspection data
            trde = data.measured_thickness
            
            # If wall loss measured, calculate trde from it
            if data.measured_wall_loss > 0:
                trde = step1['t'] - data.measured_wall_loss
            
            age_tke = data.age_since_inspection
        else:
            # No inspection data
            trde = step1['t']
            age_tke = step1['age']
        
        return {
            'trde': trde,
            'age_tke': age_tke
        }
    
    def _step6_coating_time(self, data: ExternalCorrosionData) -> Dict:
        """Step 6: Time since coating installed"""
        if data.coating_install_date is None:
            age_coat = 0.0
        else:
            # Simplified - should parse dates properly
            age_coat = data.age  # Assumes coating as old as equipment if not specified
        
        return {'age_coat': age_coat}
    
    def _step7_expected_coating_age(self, data: ExternalCorrosionData) -> Dict:
        """Step 7: Expected coating life"""
        return {'C_age': data.expected_coating_life}
    
    def _step8_coating_adjustment(
        self,
        step5: Dict,
        step6: Dict,
        step7: Dict,
        data: ExternalCorrosionData
    ) -> Dict:
        """Step 8: Calculate coating adjustment (Equations 2.D.4, 2.D.5)"""
        age_tke = step5['age_tke']
        age_coat = step6['age_coat']
        C_age = step7['C_age']
        
        if age_tke >= age_coat:
            # Equation 2.D.4
            Coat_adj = min(C_age, age_coat)
        else:
            # age_tke < age_coat
            if data.coating_failed_at_inspection:
                Coat_adj = 0.0
            else:
                # Equation 2.D.5 (note: equation reference seems wrong in doc)
                Coat_adj = min(C_age, age_coat) - min(C_age, age_coat - age_tke)
        
        return {'Coat_adj': Coat_adj}
    
    def _step9_effective_age(self, step5: Dict, step8: Dict) -> Dict:
        """Step 9: Effective in-service time (Equation 2.D.6)"""
        age = step5['age_tke'] - step8['Coat_adj']
        return {'age': max(age, 0.0)}
    
    def _step10_tmin(self, component_data: Dict) -> Dict:
        """Step 10: Minimum required thickness"""
        # Simplified calculation (same as thinning)
        P = component_data.get('design_pressure', 0.0)
        D = component_data.get('diameter', 1000.0)
        S = component_data.get('allowable_stress', 138.0)
        E = component_data.get('weld_joint_efficiency', 1.0)
        
        if (2 * S * E - P) > 0:
            tmin = (P * D) / (2 * S * E - P)
        else:
            tmin = component_data.get('furnished_thickness', 10.0) * 0.5
        
        tc = tmin
        
        return {'tmin': tmin, 'tc': tc}
    
    def _step11_art(self, Cr: float, step9: Dict, step5: Dict) -> Dict:
        """Step 11: Calculate Art parameter (Equation 2.D.7)"""
        age = step9['age']
        trde = step5['trde']
        
        if trde > 0:
            Art = (Cr * age) / trde
        else:
            Art = 0.0
        
        return {'Art': Art}
    
    def _step12_flow_stress(self, component_data: Dict) -> Dict:
        """Step 12: Calculate flow stress (Equation 2.D.8)"""
        YS = component_data.get('yield_strength', 240.0)
        TS = component_data.get('tensile_strength', 400.0)
        E = component_data.get('weld_joint_efficiency', 1.0)
        
        FS_extcor = ((YS + TS) / 2.0) * E * 1.1
        
        return {'FS_extcor': FS_extcor}
    
    def _step13_strength_ratio(
        self,
        component_data: Dict,
        step5: Dict,
        step10: Dict,
        step12: Dict
    ) -> Dict:
        """Step 13: Calculate strength ratio (Equation 2.D.9 or 2.D.10)"""
        P = component_data.get('design_pressure', 0.0)
        D = component_data.get('diameter', 1000.0)
        FS_extcor = step12['FS_extcor']
        trde = step5['trde']
        
        # Use simplified formula (Equation 2.D.10)
        component_type = component_data.get('component_type', 'cylinder')
        
        if component_type == 'cylinder':
            alpha = 2.0
        elif component_type == 'sphere':
            alpha = 4.0
        elif component_type == 'head':
            alpha = 1.13
        else:
            alpha = 2.0
        
        if FS_extcor > 0 and trde > 0:
            SRp_extcor = (P * D) / (alpha * FS_extcor * trde)
        else:
            SRp_extcor = 0.5
        
        return {'SRp_extcor': SRp_extcor, 'alpha': alpha}
    
    def _step14_inspection_counts(self, data: ExternalCorrosionData) -> Dict:
        """Step 14: Inspection counts by effectiveness"""
        return {
            'N_A': data.num_inspections_A,
            'N_B': data.num_inspections_B,
            'N_C': data.num_inspections_C,
            'N_D': data.num_inspections_D
        }
    
    def _step15_inspection_effectiveness(
        self,
        data: ExternalCorrosionData,
        step14: Dict
    ) -> Dict:
        """Step 15: Calculate inspection effectiveness factors (Equation 2.D.11)"""
        priors = self.PRIOR_PROBABILITIES[data.confidence_level]
        Prp1 = priors['Prp1']
        Prp2 = priors['Prp2']
        Prp3 = priors['Prp3']
        
        cond_probs = self.CONDITIONAL_PROBABILITIES
        
        N_A = step14['N_A']
        N_B = step14['N_B']
        N_C = step14['N_C']
        N_D = step14['N_D']
        
        I1 = Prp1 * \
             (cond_probs['A']['Cop1'] ** N_A) * \
             (cond_probs['B']['Cop1'] ** N_B) * \
             (cond_probs['C']['Cop1'] ** N_C) * \
             (cond_probs['D']['Cop1'] ** N_D)
        
        I2 = Prp2 * \
             (cond_probs['A']['Cop2'] ** N_A) * \
             (cond_probs['B']['Cop2'] ** N_B) * \
             (cond_probs['C']['Cop2'] ** N_C) * \
             (cond_probs['D']['Cop2'] ** N_D)
        
        I3 = Prp3 * \
             (cond_probs['A']['Cop3'] ** N_A) * \
             (cond_probs['B']['Cop3'] ** N_B) * \
             (cond_probs['C']['Cop3'] ** N_C) * \
             (cond_probs['D']['Cop3'] ** N_D)
        
        return {'I1': I1, 'I2': I2, 'I3': I3}
    
    def _step16_posterior_probabilities(self, step15: Dict) -> Dict:
        """Step 16: Calculate posterior probabilities (Equation 2.D.12)"""
        I1 = step15['I1']
        I2 = step15['I2']
        I3 = step15['I3']
        
        I_sum = I1 + I2 + I3
        
        if I_sum > 0:
            Pop1 = I1 / I_sum
            Pop2 = I2 / I_sum
            Pop3 = I3 / I_sum
        else:
            Pop1 = 0.33
            Pop2 = 0.33
            Pop3 = 0.34
        
        return {'Pop1': Pop1, 'Pop2': Pop2, 'Pop3': Pop3}
    
    def _step17_beta_parameters(self, step11: Dict, step13: Dict) -> Dict:
        """Step 17: Calculate beta parameters (Equation 2.D.13)"""
        Art = step11['Art']
        SRp = step13['SRp_extcor']
        
        # Same formula as thinning
        numerator1 = 1 - self.DS1 * Art - SRp
        denominator1_sq = \
            (self.DS1 * Art * self.COV_DELTA_T) ** 2 + \
            ((1 - self.DS1 * Art) * self.COV_SF) ** 2 + \
            (SRp * self.COV_P) ** 2
        
        beta1 = numerator1 / math.sqrt(denominator1_sq) if denominator1_sq > 0 else 0.0
        
        numerator2 = 1 - self.DS2 * Art - SRp
        denominator2_sq = \
            (self.DS2 * Art * self.COV_DELTA_T) ** 2 + \
            ((1 - self.DS2 * Art) * self.COV_SF) ** 2 + \
            (SRp * self.COV_P) ** 2
        
        beta2 = numerator2 / math.sqrt(denominator2_sq) if denominator2_sq > 0 else 0.0
        
        numerator3 = 1 - self.DS3 * Art - SRp
        denominator3_sq = \
            (self.DS3 * Art * self.COV_DELTA_T) ** 2 + \
            ((1 - self.DS3 * Art) * self.COV_SF) ** 2 + \
            (SRp * self.COV_P) ** 2
        
        beta3 = numerator3 / math.sqrt(denominator3_sq) if denominator3_sq > 0 else 0.0
        
        return {'beta1': beta1, 'beta2': beta2, 'beta3': beta3}
    
    def _step18_final_df(self, step16: Dict, step17: Dict) -> Dict:
        """Step 18: Calculate final DF (Equation 2.D.14)"""
        Pop1 = step16['Pop1']
        Pop2 = step16['Pop2']
        Pop3 = step16['Pop3']
        
        beta1 = step17['beta1']
        beta2 = step17['beta2']
        beta3 = step17['beta3']
        
        term1 = Pop1 * norm.cdf(-beta1)
        term2 = Pop2 * norm.cdf(-beta2)
        term3 = Pop3 * norm.cdf(-beta3)
        
        df_extcor = (term1 + term2 + term3) / 1.56e-4
        
        return {
            'df_extcor': df_extcor,
            'term1': term1,
            'term2': term2,
            'term3': term3
        }


def calculate_external_corrosion_df(
    ext_corr_data: ExternalCorrosionData,
    component_data: Dict
) -> Dict:
    """
    Convenience function to calculate External Corrosion DF
    """
    calculator = ExternalCorrosionDFCalculator()
    return calculator.calculate(ext_corr_data, component_data)
