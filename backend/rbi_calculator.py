"""
API 581 Complete RBI Calculator
Combines PoF and CoF to calculate Risk
"""

from typing import Dict, List
from dataclasses import dataclass

from pof_calculator import PofCalculator, DamageFactors
from cof_calculator import CofCalculator, FluidData, ConsequenceModifiers
from thinning_df import ThinningDFCalculator, ComponentData, CorrosionData, InspectionData, AdjustmentFactors


@dataclass
class RiskMatrixCell:
    """Single cell in risk matrix"""
    pof_category: int  # 1-5
    cof_category: str  # A-E
    risk_level: str  # 'Low', 'Medium-Low', 'Medium', 'Medium-High', 'High'
    risk_score: float  # Numerical risk score
    color: str  # Color code for visualization


class RiskMatrix:
    """
    API 581 Risk Matrix (5x5)
    PoF categories (1-5) × CoF categories (A-E)
    """
    
    # Risk matrix definition
    # Rows: PoF category (1-5, top to bottom)
    # Cols: CoF category (A-E, left to right)
    RISK_MATRIX = {
        5: {'A': 'Medium-Low', 'B': 'Medium', 'C': 'Medium-High', 'D': 'High', 'E': 'High'},
        4: {'A': 'Low', 'B': 'Medium-Low', 'C': 'Medium', 'D': 'Medium-High', 'E': 'High'},
        3: {'A': 'Low', 'B': 'Low', 'C': 'Medium-Low', 'D': 'Medium', 'E': 'Medium-High'},
        2: {'A': 'Low', 'B': 'Low', 'C': 'Low', 'D': 'Medium-Low', 'E': 'Medium'},
        1: {'A': 'Low', 'B': 'Low', 'C': 'Low', 'D': 'Low', 'E': 'Medium-Low'}
    }
    
    # Risk scores for numerical ranking
    RISK_SCORES = {
        'Low': 1,
        'Medium-Low': 2,
        'Medium': 3,
        'Medium-High': 4,
        'High': 5
    }
    
    # Color coding
    RISK_COLORS = {
        'Low': 'green',
        'Medium-Low': 'yellow',
        'Medium': 'orange',
        'Medium-High': 'red',
        'High': 'darkred'
    }
    
    @classmethod
    def get_risk_level(cls, pof_category: int, cof_category: str) -> str:
        """Get risk level from PoF and CoF categories"""
        return cls.RISK_MATRIX.get(pof_category, {}).get(cof_category, 'Unknown')
    
    @classmethod
    def get_risk_score(cls, risk_level: str) -> float:
        """Get numerical risk score"""
        return cls.RISK_SCORES.get(risk_level, 0)
    
    @classmethod
    def get_risk_color(cls, risk_level: str) -> str:
        """Get color for risk level"""
        return cls.RISK_COLORS.get(risk_level, 'gray')


class RBICalculator:
    """
    Complete Risk-Based Inspection Calculator
    Combines PoF and CoF calculations
    """
    
    def __init__(self):
        self.pof_calc = PofCalculator()
        self.cof_calc = CofCalculator()
        self.thinning_calc = ThinningDFCalculator()
        self.risk_matrix = RiskMatrix()
    
    def calculate_complete_rbi(
        self,
        # Component identification
        tag_number: str,
        component_type: str,
        
        # For thinning DF calculation
        component_data: ComponentData,
        corrosion_data: CorrosionData,
        inspection_data: InspectionData,
        adjustment_factors: AdjustmentFactors,
        
        # For other damage mechanisms
        damage_factors: DamageFactors,
        
        # For CoF calculation
        fluid_data: FluidData,
        consequence_modifiers: ConsequenceModifiers,
        
        # Management systems factor
        fms: float = 1.0
    ) -> Dict:
        """
        Complete RBI calculation workflow
        
        Returns:
            Complete RBI results with PoF, CoF, and Risk
        """
        
        # Step 1: Calculate Thinning DF
        thinning_result = self.thinning_calc.calculate(
            component_data,
            corrosion_data,
            inspection_data,
            adjustment_factors
        )
        
        # Update damage factors with calculated thinning DF
        damage_factors.df_thinning = thinning_result['df_thinning']
        damage_factors.thinning_type = corrosion_data.thinning_type
        
        # Step 2: Calculate total PoF
        pof_result = self.pof_calc.calculate_pof(
            component_type,
            damage_factors,
            fms
        )
        
        # Step 3: Calculate CoF for all hole sizes
        cof_results = {}
        for hole_size in ['small', 'medium', 'large', 'rupture']:
            cof_results[hole_size] = self.cof_calc.calculate_cof(
                hole_size,
                fluid_data,
                consequence_modifiers,
                component_data.diameter
            )
        
        # Use the governing (worst case) CoF
        # Typically rupture or large hole
        governing_cof = cof_results['rupture']
        
        # Step 4: Calculate Risk
        risk_result = self._calculate_risk(pof_result, governing_cof)
        
        # Compile complete results
        return {
            'tag_number': tag_number,
            'component_type': component_type,
            'thinning_calculation': thinning_result,
            'pof_calculation': pof_result,
            'cof_calculations': cof_results,
            'governing_cof': governing_cof,
            'risk_assessment': risk_result,
            'inspection_priority': self._get_inspection_priority(risk_result['risk_score'])
        }
    
    def _calculate_risk(self, pof_result: Dict, cof_result: Dict) -> Dict:
        """
        Calculate risk from PoF and CoF
        Risk = PoF × CoF (conceptually)
        But categorized using risk matrix
        """
        pof_category = pof_result['pof_category']
        cof_category = cof_result['cof_category']
        
        # Get risk level from matrix
        risk_level = self.risk_matrix.get_risk_level(pof_category, cof_category)
        risk_score = self.risk_matrix.get_risk_score(risk_level)
        risk_color = self.risk_matrix.get_risk_color(risk_level)
        
        # Numerical risk (for ranking)
        pof_total = pof_result['pof']['pof_total']
        cof_financial = cof_result['financial_consequence']['total_financial_consequence_usd']
        numerical_risk = pof_total * cof_financial
        
        return {
            'pof_category': pof_category,
            'pof_category_label': pof_result['pof_category_label'],
            'cof_category': cof_category,
            'cof_category_label': cof_result['financial_consequence']['cof_category_label'],
            'risk_level': risk_level,
            'risk_score': risk_score,
            'risk_color': risk_color,
            'numerical_risk': numerical_risk,
            'pof_value': pof_total,
            'cof_value': cof_financial
        }
    
    def _get_inspection_priority(self, risk_score: float) -> str:
        """Determine inspection priority based on risk score"""
        if risk_score >= 5:
            return "CRITICAL - Immediate action required"
        elif risk_score >= 4:
            return "HIGH - Inspection within 6 months"
        elif risk_score >= 3:
            return "MEDIUM - Inspection within 2 years"
        elif risk_score >= 2:
            return "LOW - Inspection within 5 years"
        else:
            return "VERY LOW - Inspection within 10 years"
    
    def print_complete_report(self, result: Dict) -> str:
        """Generate comprehensive RBI report"""
        report = []
        
        report.append("*" * 80)
        report.append("API 581 RISK-BASED INSPECTION (RBI) ASSESSMENT REPORT")
        report.append("*" * 80)
        report.append("")
        report.append(f"Equipment Tag:     {result['tag_number']}")
        report.append(f"Component Type:    {result['component_type']}")
        report.append("")
        
        # Thinning calculation summary
        report.append("=" * 80)
        report.append("THINNING DAMAGE FACTOR")
        report.append("=" * 80)
        thin = result['thinning_calculation']
        report.append(f"  Thinning DF:           {thin['df_thinning']:.4f}")
        report.append(f"  Art (wall loss):       {thin['art']:.4f}")
        report.append(f"  Strength ratio:        {thin['strength_ratio']:.4f}")
        report.append("")
        
        # PoF summary
        report.append("=" * 80)
        report.append("PROBABILITY OF FAILURE (POF)")
        report.append("=" * 80)
        pof = result['pof_calculation']
        report.append(f"  Total DF:              {pof['damage_factors']['df_total']:.4f}")
        report.append(f"  Total PoF:             {pof['pof']['pof_total']:.2e} failures/year")
        report.append(f"  PoF Category:          {pof['pof_category']} ({pof['pof_category_label']})")
        report.append("")
        
        # CoF summary
        report.append("=" * 80)
        report.append("CONSEQUENCE OF FAILURE (COF)")
        report.append("=" * 80)
        cof = result['governing_cof']
        fin = cof['financial_consequence']
        report.append(f"  Governing scenario:    {cof['hole_size'].upper()}")
        report.append(f"  Consequence area:      {cof['max_consequence_area_ft2']:.0f} ft²")
        report.append(f"  Financial impact:      ${fin['total_financial_consequence_usd']:,.0f}")
        report.append(f"  CoF Category:          {cof['cof_category']} ({fin['cof_category_label']})")
        report.append("")
        
        # Risk assessment
        report.append("=" * 80)
        report.append("RISK ASSESSMENT")
        report.append("=" * 80)
        risk = result['risk_assessment']
        report.append(f"  PoF Category:          {risk['pof_category']} ({risk['pof_category_label']})")
        report.append(f"  CoF Category:          {risk['cof_category']} ({risk['cof_category_label']})")
        report.append(f"  Risk Level:            {risk['risk_level']}")
        report.append(f"  Risk Score:            {risk['risk_score']}/5")
        report.append(f"  Numerical Risk:        {risk['numerical_risk']:.2e}")
        report.append("")
        
        # Inspection priority
        report.append("*" * 80)
        report.append(f"INSPECTION PRIORITY: {result['inspection_priority']}")
        report.append("*" * 80)
        report.append("")
        
        # Risk matrix visualization
        report.append(self._print_risk_matrix(risk['pof_category'], risk['cof_category']))
        
        return "\n".join(report)
    
    def _print_risk_matrix(self, current_pof: int, current_cof: str) -> str:
        """Print risk matrix with current position highlighted"""
        matrix = []
        
        matrix.append("=" * 80)
        matrix.append("RISK MATRIX POSITION")
        matrix.append("=" * 80)
        matrix.append("")
        matrix.append("     CoF Category →")
        matrix.append("PoF    A          B          C          D          E")
        matrix.append("↓")
        
        for pof in [5, 4, 3, 2, 1]:
            row = f"{pof}  "
            for cof in ['A', 'B', 'C', 'D', 'E']:
                risk = self.risk_matrix.get_risk_level(pof, cof)
                score = self.risk_matrix.get_risk_score(risk)
                
                # Highlight current position
                if pof == current_pof and cof == current_cof:
                    cell = f"[{score}*]"
                else:
                    cell = f" {score}  "
                
                row += cell + "  "
            
            matrix.append(row)
        
        matrix.append("")
        matrix.append("Legend: 1=Low, 2=Med-Low, 3=Medium, 4=Med-High, 5=High")
        matrix.append("        * = Current equipment position")
        matrix.append("")
        
        return "\n".join(matrix)


def calculate_complete_rbi(
    tag_number: str,
    component_type: str,
    component_data: ComponentData,
    corrosion_data: CorrosionData,
    inspection_data: InspectionData,
    adjustment_factors: AdjustmentFactors,
    damage_factors: DamageFactors,
    fluid_data: FluidData,
    consequence_modifiers: ConsequenceModifiers,
    fms: float = 1.0
) -> Dict:
    """
    Convenience function for complete RBI calculation
    """
    calculator = RBICalculator()
    return calculator.calculate_complete_rbi(
        tag_number,
        component_type,
        component_data,
        corrosion_data,
        inspection_data,
        adjustment_factors,
        damage_factors,
        fluid_data,
        consequence_modifiers,
        fms
    )
