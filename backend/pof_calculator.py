"""
API 581 Complete Probability of Failure (PoF) Calculator
Combines all damage mechanisms to calculate total PoF
"""

from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class GFFData:
    """Generic Failure Frequency data from Table 3.1"""
    component_type: str
    gff_small: float  # Small hole
    gff_medium: float  # Medium hole
    gff_large: float  # Large hole
    gff_rupture: float  # Rupture
    gff_total: float  # Total GFF


class GFFDatabase:
    """
    Generic Failure Frequency Database
    Data from API 581 Part 2, Table 3.1
    """
    
    # GFF values (failures/year) by component type and hole size
    GFF_TABLE = {
        'compressor': GFFData(
            component_type='COMPR',
            gff_small=8.00e-6,
            gff_medium=2.00e-5,
            gff_large=2.00e-6,
            gff_rupture=6.00e-7,
            gff_total=3.06e-5
        ),
        'heat_exchanger': GFFData(
            component_type='HEXSS',
            gff_small=8.00e-6,
            gff_medium=2.00e-5,
            gff_large=2.00e-6,
            gff_rupture=6.00e-7,
            gff_total=3.06e-5
        ),
        'pipe': GFFData(
            component_type='PIPE',
            gff_small=8.00e-6,
            gff_medium=2.00e-5,
            gff_large=2.00e-6,
            gff_rupture=6.00e-7,
            gff_total=3.06e-5
        ),
        'vessel': GFFData(
            component_type='VESSEL',
            gff_small=8.00e-6,
            gff_medium=2.00e-5,
            gff_large=2.00e-6,
            gff_rupture=6.00e-7,
            gff_total=3.06e-5
        ),
        'pump': GFFData(
            component_type='PUMP',
            gff_small=8.00e-6,
            gff_medium=2.00e-5,
            gff_large=2.00e-6,
            gff_rupture=6.00e-7,
            gff_total=3.06e-5
        ),
        'tank_bottom': GFFData(
            component_type='TANKBOTTOM',
            gff_small=7.20e-4,
            gff_medium=0.0,
            gff_large=0.0,
            gff_rupture=2.00e-6,
            gff_total=7.22e-4
        ),
        'tank_course': GFFData(
            component_type='COURSE',
            gff_small=7.00e-5,
            gff_medium=2.50e-5,
            gff_large=5.00e-6,
            gff_rupture=1.00e-7,
            gff_total=1.00e-4
        ),
        'finfan': GFFData(
            component_type='FINFAN',
            gff_small=8.00e-6,
            gff_medium=2.00e-5,
            gff_large=2.00e-6,
            gff_rupture=6.00e-7,
            gff_total=3.06e-5
        )
    }
    
    @classmethod
    def get_gff(cls, component_type: str) -> GFFData:
        """Get GFF data for a component type"""
        return cls.GFF_TABLE.get(component_type.lower(), cls.GFF_TABLE['vessel'])


@dataclass
class DamageFactors:
    """
    All damage factors for a component
    Each can be 0.0 if mechanism is not active
    """
    # Thinning
    df_thinning: float = 0.0
    thinning_type: str = "general"  # 'general' or 'localized'
    
    # External damage
    df_external: float = 0.0
    external_type: str = "general"  # 'general' or 'localized'
    
    # Stress Corrosion Cracking (9 types, use max)
    df_scc_caustic: float = 0.0
    df_scc_amine: float = 0.0
    df_scc_ssc: float = 0.0
    df_scc_hic_h2s: float = 0.0
    df_scc_acscc: float = 0.0
    df_scc_pascc: float = 0.0
    df_scc_clscc: float = 0.0
    df_scc_hsc_hf: float = 0.0
    df_scc_hic_hf: float = 0.0
    
    # High Temperature Hydrogen Attack
    df_htha: float = 0.0
    
    # Mechanical Fatigue (piping only)
    df_mfat: float = 0.0
    
    # Brittle Fracture
    df_brittle: float = 0.0


class PofCalculator:
    """
    Complete Probability of Failure Calculator
    Equation 2.1: Pf(t) = gff_total × Df(t) × FMS
    """
    
    def __init__(self):
        self.gff_db = GFFDatabase()
    
    def calculate_total_df(self, df: DamageFactors) -> Dict:
        """
        Calculate total damage factor
        Equation 2.2 and 2.3
        """
        # Governing thinning DF (Equation 2.4)
        df_thinning_gov = df.df_thinning
        
        # Governing external DF (Equation 2.6)
        df_external_gov = df.df_external
        
        # Governing SCC DF (Equation 2.5) - max of all SCC types
        df_scc_gov = max(
            df.df_scc_caustic,
            df.df_scc_amine,
            df.df_scc_ssc,
            df.df_scc_hic_h2s,
            df.df_scc_acscc,
            df.df_scc_pascc,
            df.df_scc_clscc,
            df.df_scc_hsc_hf,
            df.df_scc_hic_hf
        )
        
        # Governing brittle fracture DF (Equation 2.7)
        # Note: Set to zero if DF <= 1.0 (inactive)
        df_brittle_gov = df.df_brittle if df.df_brittle > 1.0 else 0.0
        
        # Determine if thinning and external should be summed or maxed
        # Equation 2.3: If either is general, or both are general, sum them
        # Equation 2.2: If both are localized, take max
        both_localized = (df.thinning_type == "localized" and 
                         df.external_type == "localized")
        
        if both_localized:
            # Equation 2.2: Use max when both are localized
            df_thin_ext = max(df_thinning_gov, df_external_gov)
            df_total = df_thin_ext + df_scc_gov + df.df_htha + df_brittle_gov + df.df_mfat
        else:
            # Equation 2.3: Sum when either is general
            df_total = (df_thinning_gov + df_external_gov + df_scc_gov + 
                       df.df_htha + df_brittle_gov + df.df_mfat)
        
        return {
            'df_total': df_total,
            'df_thinning_gov': df_thinning_gov,
            'df_external_gov': df_external_gov,
            'df_scc_gov': df_scc_gov,
            'df_htha': df.df_htha,
            'df_brittle_gov': df_brittle_gov,
            'df_mfat': df.df_mfat,
            'combination_method': 'max' if both_localized else 'sum'
        }
    
    def calculate_pof(
        self,
        component_type: str,
        damage_factors: DamageFactors,
        fms: float = 1.0
    ) -> Dict:
        """
        Calculate complete PoF
        Equation 2.1: Pf(t) = gff_total × Df(t) × FMS
        
        Args:
            component_type: Type of component (from GFF table)
            damage_factors: All damage factors for the component
            fms: Management Systems Factor (default 1.0)
        
        Returns:
            Dictionary with PoF results for all hole sizes and category
        """
        # Get GFF for component type
        gff = self.gff_db.get_gff(component_type)
        
        # Calculate total DF
        df_result = self.calculate_total_df(damage_factors)
        df_total = df_result['df_total']
        
        # Calculate PoF for each hole size (Equation 2.1)
        pof_small = gff.gff_small * df_total * fms
        pof_medium = gff.gff_medium * df_total * fms
        pof_large = gff.gff_large * df_total * fms
        pof_rupture = gff.gff_rupture * df_total * fms
        pof_total = gff.gff_total * df_total * fms
        
        # Determine PoF category (1-5)
        pof_category = self._get_pof_category(pof_total)
        
        return {
            'component_type': component_type,
            'gff': {
                'gff_small': gff.gff_small,
                'gff_medium': gff.gff_medium,
                'gff_large': gff.gff_large,
                'gff_rupture': gff.gff_rupture,
                'gff_total': gff.gff_total
            },
            'damage_factors': df_result,
            'fms': fms,
            'pof': {
                'pof_small': pof_small,
                'pof_medium': pof_medium,
                'pof_large': pof_large,
                'pof_rupture': pof_rupture,
                'pof_total': pof_total
            },
            'pof_category': pof_category,
            'pof_category_label': self._get_pof_label(pof_category)
        }
    
    def _get_pof_category(self, pof_total: float) -> int:
        """
        Convert total PoF to category (1-5)
        Based on typical API 581 thresholds
        """
        if pof_total < 1e-6:
            return 1
        elif pof_total < 1e-5:
            return 2
        elif pof_total < 1e-4:
            return 3
        elif pof_total < 1e-3:
            return 4
        else:
            return 5
    
    def _get_pof_label(self, category: int) -> str:
        """Get descriptive label for PoF category"""
        labels = {
            1: "Very Low",
            2: "Low",
            3: "Medium",
            4: "Medium-High",
            5: "High"
        }
        return labels.get(category, "Unknown")
    
    def print_pof_report(self, result: Dict) -> str:
        """Generate human-readable PoF report"""
        report = []
        report.append("=" * 80)
        report.append("API 581 PROBABILITY OF FAILURE (POF) REPORT")
        report.append("=" * 80)
        report.append("")
        
        report.append(f"Component Type: {result['component_type'].upper()}")
        report.append(f"Management Systems Factor (FMS): {result['fms']:.2f}")
        report.append("")
        
        report.append("-" * 80)
        report.append("GENERIC FAILURE FREQUENCIES (GFF)")
        report.append("-" * 80)
        gff = result['gff']
        report.append(f"  Small hole:     {gff['gff_small']:.2e} failures/year")
        report.append(f"  Medium hole:    {gff['gff_medium']:.2e} failures/year")
        report.append(f"  Large hole:     {gff['gff_large']:.2e} failures/year")
        report.append(f"  Rupture:        {gff['gff_rupture']:.2e} failures/year")
        report.append(f"  Total GFF:      {gff['gff_total']:.2e} failures/year")
        report.append("")
        
        report.append("-" * 80)
        report.append("DAMAGE FACTORS")
        report.append("-" * 80)
        df = result['damage_factors']
        report.append(f"  Thinning (governing):   {df['df_thinning_gov']:.4f}")
        report.append(f"  External (governing):   {df['df_external_gov']:.4f}")
        report.append(f"  SCC (governing):        {df['df_scc_gov']:.4f}")
        report.append(f"  HTHA:                   {df['df_htha']:.4f}")
        report.append(f"  Brittle Fracture:       {df['df_brittle_gov']:.4f}")
        report.append(f"  Mechanical Fatigue:     {df['df_mfat']:.4f}")
        report.append(f"  ---")
        report.append(f"  Total DF:               {df['df_total']:.4f}")
        report.append(f"  Combination method:     {df['combination_method']}")
        report.append("")
        
        report.append("-" * 80)
        report.append("PROBABILITY OF FAILURE (PoF = GFF × DF × FMS)")
        report.append("-" * 80)
        pof = result['pof']
        report.append(f"  Small hole:     {pof['pof_small']:.2e} failures/year")
        report.append(f"  Medium hole:    {pof['pof_medium']:.2e} failures/year")
        report.append(f"  Large hole:     {pof['pof_large']:.2e} failures/year")
        report.append(f"  Rupture:        {pof['pof_rupture']:.2e} failures/year")
        report.append(f"  ---")
        report.append(f"  Total PoF:      {pof['pof_total']:.2e} failures/year")
        report.append("")
        
        report.append("=" * 80)
        report.append(f"POF CATEGORY: {result['pof_category']} ({result['pof_category_label']})")
        report.append("=" * 80)
        report.append("")
        
        return "\n".join(report)


# Convenience function
def calculate_pof(
    component_type: str,
    damage_factors: DamageFactors,
    fms: float = 1.0
) -> Dict:
    """
    Convenience function to calculate PoF
    
    Returns:
        Dictionary with complete PoF results
    """
    calculator = PofCalculator()
    return calculator.calculate(component_type, damage_factors, fms)
