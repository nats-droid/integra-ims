"""
API 581 Thinning Damage Factor (DF) Calculation Module
Implements the 13-step procedure from API RP 581 4th Edition (2025)
Section 4: Thinning DF
"""

import math
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from scipy.stats import norm


@dataclass
class ComponentData:
    """Basic component data (Table 4.1, 4.2, 4.3)"""
    # Component identification
    tag_number: str
    component_type: str  # 'cylinder', 'sphere', 'head', 'rectangular'
    
    # Geometry
    diameter: float  # mm
    length: Optional[float] = None  # mm, for cylinders
    
    # Material properties
    yield_strength: float = 0.0  # MPa
    tensile_strength: float = 0.0  # MPa
    allowable_stress: float = 0.0  # MPa
    weld_joint_efficiency: float = 1.0  # E factor
    
    # Thickness data
    furnished_thickness: float = 0.0  # mm, original thickness
    design_pressure: float = 0.0  # MPa
    
    # Age
    installation_date: str = ""  # ISO date
    age: float = 0.0  # years since installation


@dataclass
class CorrosionData:
    """Corrosion rate and degradation data (Table 4.4)"""
    # Base material corrosion
    corrosion_rate_bm: float  # mm/year
    thinning_type: str  # 'general' or 'localized'
    
    # Cladding (if applicable)
    has_cladding: bool = False
    cladding_thickness: float = 0.0  # mm
    corrosion_rate_cm: float = 0.0  # mm/year
    
    # Internal liner (if applicable)
    has_liner: bool = False
    liner_type: str = ""  # from Table 4.7
    liner_age: float = 0.0  # years
    liner_expected_life: float = 0.0  # years
    liner_condition: str = "good"  # 'excellent', 'good', 'fair', 'poor'


@dataclass
class InspectionData:
    """Inspection history and effectiveness (Table 4.6)"""
    # Last inspection
    last_inspection_date: str = ""  # ISO date
    measured_thickness: float = 0.0  # mm, trdi
    age_since_inspection: float = 0.0  # years, agetk
    
    # Inspection counts by effectiveness level
    num_inspections_A: int = 0  # Highly effective
    num_inspections_B: int = 0  # Usually effective
    num_inspections_C: int = 0  # Fairly effective
    num_inspections_D: int = 0  # Poorly effective
    
    # Confidence level for corrosion rate
    confidence_level: str = "low"  # 'low', 'medium', 'high'


@dataclass
class AdjustmentFactors:
    """Adjustment factors for final DF (Section 4.5, Step 13)"""
    # Online monitoring
    has_online_monitoring: bool = False
    monitoring_effectiveness: str = "none"  # from Table 4.9
    
    # Injection/mix points
    has_injection_point: bool = False
    injection_inspected: bool = False
    
    # Dead legs
    has_deadleg: bool = False
    deadleg_inspected: bool = False
    
    # Liner monitoring
    has_liner_monitoring: bool = False


class ThinningDFCalculator:
    """
    API 581 Thinning Damage Factor Calculator
    Implements 13-step calculation procedure from Section 4.5
    """
    
    # Table 4.5: Prior probabilities for damage states based on confidence level
    PRIOR_PROBABILITIES = {
        'low': {
            'Prp1': 0.25,  # Damage State 1 (1x expected rate)
            'Prp2': 0.50,  # Damage State 2 (2x expected rate)
            'Prp3': 0.25   # Damage State 3 (4x expected rate)
        },
        'medium': {
            'Prp1': 0.50,
            'Prp2': 0.35,
            'Prp3': 0.15
        },
        'high': {
            'Prp1': 0.70,
            'Prp2': 0.25,
            'Prp3': 0.05
        }
    }
    
    # Table 4.6: Conditional probabilities for inspection effectiveness
    CONDITIONAL_PROBABILITIES = {
        'general': {
            'A': {'Cop1': 0.99, 'Cop2': 0.85, 'Cop3': 0.40},
            'B': {'Cop1': 0.95, 'Cop2': 0.70, 'Cop3': 0.30},
            'C': {'Cop1': 0.85, 'Cop2': 0.50, 'Cop3': 0.20},
            'D': {'Cop1': 0.70, 'Cop2': 0.40, 'Cop3': 0.10}
        },
        'localized': {
            'A': {'Cop1': 0.95, 'Cop2': 0.70, 'Cop3': 0.30},
            'B': {'Cop1': 0.85, 'Cop2': 0.50, 'Cop3': 0.20},
            'C': {'Cop1': 0.70, 'Cop2': 0.40, 'Cop3': 0.10},
            'D': {'Cop1': 0.50, 'Cop2': 0.30, 'Cop3': 0.05}
        }
    }
    
    # Table 4.7: Liner expected life (simplified)
    LINER_EXPECTED_LIFE = {
        'organic_coating': 15.0,
        'refractory': 20.0,
        'alloy_strip': 30.0,
        'glass_lining': 25.0,
        'rubber_lining': 20.0
    }
    
    # Table 4.8: Liner condition adjustment factors
    LINER_CONDITION_FACTORS = {
        'excellent': 1.0,
        'good': 0.8,
        'fair': 0.5,
        'poor': 0.2
    }
    
    # Table 4.9: Online monitoring factors (simplified)
    ONLINE_MONITORING_FACTORS = {
        'none': 1.0,
        'corrosion_coupon': 0.5,
        'corrosion_probe': 0.3,
        'process_monitoring': 0.7,
        'highly_effective': 0.1
    }
    
    # Coefficients of Variance (Section 4.5.7, Step 11)
    COV_DELTA_T = 0.20  # Thickness COV (conservative)
    COV_SF = 0.20       # Flow stress COV
    COV_P = 0.05        # Pressure COV
    
    # Damage state factors
    DS1 = 1.0
    DS2 = 2.0
    DS3 = 4.0
    
    def __init__(self):
        self.calculation_steps = []  # Store intermediate results
    
    def calculate(
        self,
        component: ComponentData,
        corrosion: CorrosionData,
        inspection: InspectionData,
        adjustments: AdjustmentFactors
    ) -> Dict:
        """
        Main calculation function - executes all 13 steps
        Returns: Dictionary with DF result and all intermediate values
        """
        self.calculation_steps = []
        
        # Step 1: Determine furnished thickness and age
        step1 = self._step1_thickness_age(component, corrosion, inspection)
        self.calculation_steps.append(('Step 1', step1))
        
        # Step 2: Determine corrosion rates
        step2 = self._step2_corrosion_rates(corrosion)
        self.calculation_steps.append(('Step 2', step2))
        
        # Step 3: Determine time in service and last known thickness
        step3 = self._step3_service_time(component, corrosion, inspection, step2)
        self.calculation_steps.append(('Step 3', step3))
        
        # Step 4: Determine minimum required thickness (tmin)
        step4 = self._step4_tmin(component)
        self.calculation_steps.append(('Step 4', step4))
        
        # Step 5: Calculate Art parameter (wall loss fraction)
        step5 = self._step5_art(step2, step3)
        self.calculation_steps.append(('Step 5', step5))
        
        # Step 6: Calculate flow stress
        step6 = self._step6_flow_stress(component)
        self.calculation_steps.append(('Step 6', step6))
        
        # Step 7: Calculate strength ratio parameter
        step7 = self._step7_strength_ratio(component, step3, step4, step6)
        self.calculation_steps.append(('Step 7', step7))
        
        # Step 8: Determine inspection counts
        step8 = self._step8_inspection_counts(inspection)
        self.calculation_steps.append(('Step 8', step8))
        
        # Step 9: Calculate inspection effectiveness factors
        step9 = self._step9_inspection_effectiveness(inspection, corrosion, step8)
        self.calculation_steps.append(('Step 9', step9))
        
        # Step 10: Calculate posterior probabilities
        step10 = self._step10_posterior_probabilities(step9)
        self.calculation_steps.append(('Step 10', step10))
        
        # Step 11: Calculate beta parameters
        step11 = self._step11_beta_parameters(step5, step7)
        self.calculation_steps.append(('Step 11', step11))
        
        # Step 12: Calculate base DF
        step12 = self._step12_base_df(step10, step11)
        self.calculation_steps.append(('Step 12', step12))
        
        # Step 13: Apply adjustment factors and get final DF
        step13 = self._step13_final_df(step12, adjustments, corrosion)
        self.calculation_steps.append(('Step 13', step13))
        
        # Compile results
        result = {
            'df_thinning': step13['df_final'],
            'df_base': step12['df_base'],
            'art': step5['Art'],
            'strength_ratio': step7['SRp_thin'],
            'adjustment_factors': step13['factors'],
            'all_steps': self.calculation_steps,
            'pof_category': self._get_pof_category(step13['df_final'])
        }
        
        return result
    
    def _step1_thickness_age(
        self,
        component: ComponentData,
        corrosion: CorrosionData,
        inspection: InspectionData
    ) -> Dict:
        """Step 1: Determine furnished thickness, age, cladding, liner"""
        t = component.furnished_thickness
        age = component.age
        
        tcm = corrosion.cladding_thickness if corrosion.has_cladding else 0.0
        age_liner = corrosion.liner_age if corrosion.has_liner else 0.0
        
        return {
            't': t,
            'age': age,
            'tcm': tcm,
            'age_liner': age_liner
        }
    
    def _step2_corrosion_rates(self, corrosion: CorrosionData) -> Dict:
        """Step 2: Determine base material and cladding corrosion rates"""
        cr_bm = corrosion.corrosion_rate_bm
        cr_cm = corrosion.corrosion_rate_cm if corrosion.has_cladding else 0.0
        
        return {
            'Cr_bm': cr_bm,
            'Cr_cm': cr_cm
        }
    
    def _step3_service_time(
        self,
        component: ComponentData,
        corrosion: CorrosionData,
        inspection: InspectionData,
        step2: Dict
    ) -> Dict:
        """Step 3: Determine time in service since last inspection"""
        # If no measured thickness available, use furnished thickness
        if inspection.measured_thickness > 0:
            trdi = inspection.measured_thickness
            age_tk = inspection.age_since_inspection
        else:
            trdi = component.furnished_thickness
            age_tk = component.age
        
        # Calculate remaining life of cladding (Equation 2.10)
        age_rc = 0.0
        if corrosion.has_cladding and step2['Cr_cm'] > 0:
            age_rc = max(corrosion.cladding_thickness / step2['Cr_cm'], 0.0)
        
        # Calculate remaining life of internal liner (Equation 2.11)
        if corrosion.has_liner:
            RL_exp = corrosion.liner_expected_life
            age_liner = corrosion.liner_age
            FLC = self.LINER_CONDITION_FACTORS.get(corrosion.liner_condition, 0.8)
            F_liner_OM = 0.1 if hasattr(inspection, 'has_liner_monitoring') else 1.0
            
            age_rc = max((RL_exp - age_liner) / FLC * F_liner_OM, 0.0)
        
        return {
            'trdi': trdi,
            'age_tk': age_tk,
            'age_rc': age_rc
        }
    
    def _step4_tmin(self, component: ComponentData) -> Dict:
        """Step 4: Determine minimum required thickness (tmin)"""
        # Simplified calculation using pressure vessel code formula
        # For cylinder: t = PD / (2SE - P)
        # This should be replaced with actual code calculations
        
        P = component.design_pressure
        D = component.diameter
        S = component.allowable_stress
        E = component.weld_joint_efficiency
        
        if component.component_type == 'cylinder':
            # Circumferential stress
            if (2 * S * E - P) > 0:
                tmin = (P * D) / (2 * S * E - P)
            else:
                tmin = component.furnished_thickness * 0.5  # Fallback
        elif component.component_type == 'sphere':
            # Sphere formula: t = PD / (4SE - P)
            if (4 * S * E - P) > 0:
                tmin = (P * D) / (4 * S * E - P)
            else:
                tmin = component.furnished_thickness * 0.5
        else:
            # Conservative estimate for other shapes
            tmin = component.furnished_thickness * 0.5
        
        # Add corrosion allowance consideration if needed
        tc = tmin  # Structural thickness (simplified)
        
        return {
            'tmin': tmin,
            'tc': tc
        }
    
    def _step5_art(self, step2: Dict, step3: Dict) -> Dict:
        """Step 5: Calculate Art parameter (Equation 2.12)"""
        Cr_bm = step2['Cr_bm']
        age_tk = step3['age_tk']
        age_rc = step3['age_rc']
        trdi = step3['trdi']
        
        # Equation 2.12
        if trdi > 0:
            Art = max((Cr_bm * (age_tk - age_rc)) / trdi, 0.0)
        else:
            Art = 0.0
        
        return {
            'Art': Art
        }
    
    def _step6_flow_stress(self, component: ComponentData) -> Dict:
        """Step 6: Calculate flow stress (Equation 2.13)"""
        YS = component.yield_strength
        TS = component.tensile_strength
        E = component.weld_joint_efficiency
        
        # Equation 2.13
        FS_thin = ((YS + TS) / 2.0) * E * 1.1
        
        return {
            'FS_thin': FS_thin
        }
    
    def _step7_strength_ratio(
        self,
        component: ComponentData,
        step3: Dict,
        step4: Dict,
        step6: Dict
    ) -> Dict:
        """Step 7: Calculate strength ratio parameter (Equation 2.14 or 2.15)"""
        # Using Equation 2.15 for simplicity (pressure hoop stress)
        P = component.design_pressure
        D = component.diameter
        FS_thin = step6['FS_thin']
        trdi = step3['trdi']
        
        # Determine alpha (shape factor)
        if component.component_type == 'cylinder':
            alpha = 2.0
        elif component.component_type == 'sphere':
            alpha = 4.0
        elif component.component_type == 'head':
            alpha = 1.13
        else:
            alpha = 2.0  # Default to cylinder
        
        # Equation 2.15
        if FS_thin > 0 and trdi > 0:
            SRp_thin = (P * D) / (alpha * FS_thin * trdi)
        else:
            SRp_thin = 0.5  # Default conservative value
        
        return {
            'SRp_thin': SRp_thin,
            'alpha': alpha
        }
    
    def _step8_inspection_counts(self, inspection: InspectionData) -> Dict:
        """Step 8: Determine number of inspections for each effectiveness level"""
        return {
            'N_A': inspection.num_inspections_A,
            'N_B': inspection.num_inspections_B,
            'N_C': inspection.num_inspections_C,
            'N_D': inspection.num_inspections_D
        }
    
    def _step9_inspection_effectiveness(
        self,
        inspection: InspectionData,
        corrosion: CorrosionData,
        step8: Dict
    ) -> Dict:
        """Step 9: Calculate inspection effectiveness factors (Equation 2.16)"""
        # Get prior probabilities based on confidence level
        confidence = inspection.confidence_level
        priors = self.PRIOR_PROBABILITIES[confidence]
        Prp1 = priors['Prp1']
        Prp2 = priors['Prp2']
        Prp3 = priors['Prp3']
        
        # Get conditional probabilities based on thinning type
        thinning_type = corrosion.thinning_type
        cond_probs = self.CONDITIONAL_PROBABILITIES[thinning_type]
        
        # Inspection counts
        N_A = step8['N_A']
        N_B = step8['N_B']
        N_C = step8['N_C']
        N_D = step8['N_D']
        
        # Calculate I1, I2, I3 using Equation 2.16
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
        
        return {
            'I1': I1,
            'I2': I2,
            'I3': I3,
            'Prp1': Prp1,
            'Prp2': Prp2,
            'Prp3': Prp3
        }
    
    def _step10_posterior_probabilities(self, step9: Dict) -> Dict:
        """Step 10: Calculate posterior probabilities (Equation 2.17)"""
        I1 = step9['I1']
        I2 = step9['I2']
        I3 = step9['I3']
        
        I_sum = I1 + I2 + I3
        
        if I_sum > 0:
            Pop1 = I1 / I_sum
            Pop2 = I2 / I_sum
            Pop3 = I3 / I_sum
        else:
            # Fallback to prior probabilities if calculation fails
            Pop1 = step9['Prp1']
            Pop2 = step9['Prp2']
            Pop3 = step9['Prp3']
        
        return {
            'Pop1': Pop1,
            'Pop2': Pop2,
            'Pop3': Pop3
        }
    
    def _step11_beta_parameters(self, step5: Dict, step7: Dict) -> Dict:
        """Step 11: Calculate beta parameters (Equation 2.18)"""
        Art = step5['Art']
        SRp_thin = step7['SRp_thin']
        
        # Damage state factors
        DS1 = self.DS1
        DS2 = self.DS2
        DS3 = self.DS3
        
        # Coefficients of variance
        COV_dt = self.COV_DELTA_T
        COV_sf = self.COV_SF
        COV_p = self.COV_P
        
        # Calculate beta1 (Equation 2.18)
        numerator1 = 1 - DS1 * Art - SRp_thin
        denominator1_sq = \
            (DS1 * Art * COV_dt) ** 2 + \
            ((1 - DS1 * Art) * COV_sf) ** 2 + \
            (SRp_thin * COV_p) ** 2
        
        if denominator1_sq > 0:
            beta1 = numerator1 / math.sqrt(denominator1_sq)
        else:
            beta1 = 0.0
        
        # Calculate beta2
        numerator2 = 1 - DS2 * Art - SRp_thin
        denominator2_sq = \
            (DS2 * Art * COV_dt) ** 2 + \
            ((1 - DS2 * Art) * COV_sf) ** 2 + \
            (SRp_thin * COV_p) ** 2
        
        if denominator2_sq > 0:
            beta2 = numerator2 / math.sqrt(denominator2_sq)
        else:
            beta2 = 0.0
        
        # Calculate beta3
        numerator3 = 1 - DS3 * Art - SRp_thin
        denominator3_sq = \
            (DS3 * Art * COV_dt) ** 2 + \
            ((1 - DS3 * Art) * COV_sf) ** 2 + \
            (SRp_thin * COV_p) ** 2
        
        if denominator3_sq > 0:
            beta3 = numerator3 / math.sqrt(denominator3_sq)
        else:
            beta3 = 0.0
        
        return {
            'beta1': beta1,
            'beta2': beta2,
            'beta3': beta3
        }
    
    def _step12_base_df(self, step10: Dict, step11: Dict) -> Dict:
        """Step 12: Calculate base DF (Equation 2.19)"""
        Pop1 = step10['Pop1']
        Pop2 = step10['Pop2']
        Pop3 = step10['Pop3']
        
        beta1 = step11['beta1']
        beta2 = step11['beta2']
        beta3 = step11['beta3']
        
        # Use scipy.stats.norm.cdf for standard normal CDF (NORMSDIST in Excel)
        # Equation 2.19
        term1 = Pop1 * norm.cdf(-beta1)
        term2 = Pop2 * norm.cdf(-beta2)
        term3 = Pop3 * norm.cdf(-beta3)
        
        df_base = (term1 + term2 + term3) / 1.56e-4
        
        return {
            'df_base': df_base,
            'term1': term1,
            'term2': term2,
            'term3': term3
        }
    
    def _step13_final_df(
        self,
        step12: Dict,
        adjustments: AdjustmentFactors,
        corrosion: CorrosionData
    ) -> Dict:
        """Step 13: Apply adjustment factors and get final DF (Equation 2.20)"""
        df_base = step12['df_base']
        
        # Adjustment for online monitoring (Table 4.9)
        if adjustments.has_online_monitoring:
            F_OM = self.ONLINE_MONITORING_FACTORS.get(
                adjustments.monitoring_effectiveness,
                1.0
            )
        else:
            F_OM = 1.0
        
        # Check for liner monitoring
        if corrosion.has_liner and adjustments.has_liner_monitoring:
            F_OM = min(F_OM, 0.1)
        
        # Adjustment for injection/mix points
        if adjustments.has_injection_point:
            F_IP = 1.0 if adjustments.injection_inspected else 3.0
        else:
            F_IP = 1.0
        
        # Adjustment for dead legs
        if adjustments.has_deadleg:
            F_DL = 1.0 if adjustments.deadleg_inspected else 3.0
        else:
            F_DL = 1.0
        
        # Equation 2.20
        df_final = max((df_base * F_IP * F_DL) / F_OM, 0.1)
        
        return {
            'df_final': df_final,
            'factors': {
                'F_OM': F_OM,
                'F_IP': F_IP,
                'F_DL': F_DL
            }
        }
    
    def _get_pof_category(self, df: float) -> int:
        """
        Convert DF to PoF category (1-5)
        Based on typical API 581 ranges (may need calibration)
        """
        if df < 1.0:
            return 1
        elif df < 10.0:
            return 2
        elif df < 100.0:
            return 3
        elif df < 1000.0:
            return 4
        else:
            return 5
    
    def print_calculation_report(self, result: Dict) -> str:
        """Generate a human-readable calculation report"""
        report = []
        report.append("=" * 80)
        report.append("API 581 THINNING DAMAGE FACTOR CALCULATION REPORT")
        report.append("=" * 80)
        report.append("")
        
        report.append(f"Final DF (Thinning):        {result['df_thinning']:.6f}")
        report.append(f"Base DF:                     {result['df_base']:.6f}")
        report.append(f"PoF Category:                {result['pof_category']}")
        report.append("")
        
        report.append("Key Parameters:")
        report.append(f"  Art (Wall Loss Fraction):  {result['art']:.4f}")
        report.append(f"  Strength Ratio:            {result['strength_ratio']:.4f}")
        report.append("")
        
        report.append("Adjustment Factors:")
        factors = result['adjustment_factors']
        report.append(f"  F_OM (Online Monitoring):  {factors['F_OM']:.2f}")
        report.append(f"  F_IP (Injection Point):    {factors['F_IP']:.2f}")
        report.append(f"  F_DL (Dead Leg):           {factors['F_DL']:.2f}")
        report.append("")
        
        report.append("-" * 80)
        report.append("DETAILED CALCULATION STEPS:")
        report.append("-" * 80)
        
        for step_name, step_data in result['all_steps']:
            report.append(f"\n{step_name}:")
            for key, value in step_data.items():
                if isinstance(value, float):
                    report.append(f"  {key}: {value:.6f}")
                else:
                    report.append(f"  {key}: {value}")
        
        report.append("")
        report.append("=" * 80)
        
        return "\n".join(report)


# Convenience function for quick calculation
def calculate_thinning_df(
    component: ComponentData,
    corrosion: CorrosionData,
    inspection: InspectionData,
    adjustments: AdjustmentFactors
) -> Dict:
    """
    Convenience function to calculate Thinning DF
    
    Returns:
        Dictionary with calculation results including final DF and all steps
    """
    calculator = ThinningDFCalculator()
    return calculator.calculate(component, corrosion, inspection, adjustments)
