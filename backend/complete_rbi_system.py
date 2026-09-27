"""
Complete RBI System - All 20 Damage Mechanisms + CoF → Risk Matrix
API 581 4th Edition Full Implementation
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json

# Import all damage mechanism calculators
from thinning_df import ThinningData, calculate_thinning_df
from external_corrosion_df import ExternalCorrosionData, calculate_external_corrosion_df
from cui_df import CUIData, calculate_cui_df
from caustic_scc_df import CausticSCCData, calculate_caustic_scc_df
from amine_scc_df import AmineSCCData, calculate_amine_scc_df
from chloride_scc_df import ChlorideSCCData, calculate_chloride_scc_df
from ssc_df import SSCData, calculate_ssc_df
from hic_sohic_df import HICSOHICData, calculate_hic_sohic_df
from hic_sohic_hf_df import HICSOHICHFData, calculate_hic_sohic_hf_df
from generic_scc_df import GenericSCCData, calculate_generic_scc_df
from htha_df import HTHAData, calculate_htha_df
from brittle_fracture_df import BrittleFractureData, calculate_brittle_fracture_df
from embrittlement_df import EmbrittlementData, EmbrittlementCalculator
from fatigue_lining_df import MechanicalFatigueData, LiningDegradationData, calculate_mechanical_fatigue_df, calculate_lining_degradation_df
from pof_calculator import calculate_pof
from cof_calculator import calculate_cof, COFData


@dataclass
class ComponentData:
    """Complete component data for RBI assessment"""
    # Basic info
    component_id: str = 'COMP-001'
    component_type: str = 'pipe'  # 'pipe', 'vessel', 'heat_exchanger', 'tank'
    equipment_class: str = 'Class 2'
    
    # Process conditions
    fluid_type: str = 'hydrocarbon'
    phase: str = 'liquid'
    operating_pressure_psig: float = 300.0
    design_pressure_psig: float = 450.0
    operating_temp_f: float = 400.0
    
    # Material
    material: str = 'carbon_steel'
    diameter_inches: float = 12.0
    wall_thickness_inches: float = 0.375
    
    # Generic equipment factor for PoF
    fms: float = 1.0  # Management Systems Factor


class CompleteRBICalculator:
    """
    Complete RBI Calculator - All 20 Mechanisms
    Returns PoF × CoF → Risk Matrix
    """
    
    # 5×5 Risk Matrix
    RISK_MATRIX = {
        'categories': ['1', '2A', '2B', '2C', '3A', '3B', '3C', '4A', '4B', '4C', '5A', '5B', '5C', '5D', '5E'],
        'pof_ranges': {
            1: (0, 1e-6),
            2: (1e-6, 1e-5),
            3: (1e-5, 1e-4),
            4: (1e-4, 1e-3),
            5: (1e-3, float('inf'))
        },
        'cof_ranges': {
            'A': (0, 1e4),
            'B': (1e4, 1e5),
            'C': (1e5, 1e6),
            'D': (1e6, 1e7),
            'E': (1e7, float('inf'))
        }
    }
    
    def calculate_complete_rbi(self, component: ComponentData, active_mechanisms: Dict[str, Dict]) -> Dict:
        """
        Complete RBI calculation
        
        Args:
            component: Component data
            active_mechanisms: Dict of {mechanism_name: mechanism_data_dict}
        
        Returns:
            Complete RBI result with risk matrix position
        """
        results = {
            'component_id': component.component_id,
            'component_type': component.component_type,
            'damage_factors': {},
            'pof': None,
            'cof': None,
            'risk': None,
            'risk_matrix_position': None,
            'inspection_recommendation': None
        }
        
        # Step 1: Calculate all active damage factors
        df_results = self._calculate_all_damage_factors(active_mechanisms)
        results['damage_factors'] = df_results
        
        # Step 2: Calculate PoF (combines all DFs)
        pof_result = self._calculate_pof(component, df_results)
        results['pof'] = pof_result
        
        # Step 3: Calculate CoF
        cof_result = self._calculate_cof(component)
        results['cof'] = cof_result
        
        # Step 4: Risk Matrix position
        risk_result = self._determine_risk(pof_result, cof_result)
        results['risk'] = risk_result
        results['risk_matrix_position'] = f"{risk_result['pof_category']}{risk_result['cof_category']}"
        
        # Step 5: Inspection recommendation
        results['inspection_recommendation'] = self._recommend_inspection(risk_result)
        
        return results
    
    def _calculate_all_damage_factors(self, active_mechanisms: Dict[str, Dict]) -> Dict:
        """Calculate DF for all active mechanisms"""
        df_results = {}
        
        for mechanism, data in active_mechanisms.items():
            try:
                if mechanism == 'thinning':
                    result = calculate_thinning_df(ThinningData(**data))
                    df_results['thinning'] = result['df_thin']
                
                elif mechanism == 'external_corrosion':
                    result = calculate_external_corrosion_df(ExternalCorrosionData(**data))
                    df_results['external_corrosion'] = result['df_extcorr']
                
                elif mechanism == 'cui':
                    result = calculate_cui_df(CUIData(**data))
                    df_results['cui'] = result['df_cui']
                
                elif mechanism == 'caustic_scc':
                    result = calculate_caustic_scc_df(CausticSCCData(**data))
                    df_results['caustic_scc'] = result['df_caustic_scc']
                
                elif mechanism == 'amine_scc':
                    result = calculate_amine_scc_df(AmineSCCData(**data))
                    df_results['amine_scc'] = result['df_amine_scc']
                
                elif mechanism == 'chloride_scc':
                    result = calculate_chloride_scc_df(ChlorideSCCData(**data))
                    df_results['chloride_scc'] = result['df_chloride_scc']
                
                elif mechanism == 'ssc':
                    result = calculate_ssc_df(SSCData(**data))
                    df_results['ssc'] = result['df_ssc']
                
                elif mechanism == 'hic_sohic_h2s':
                    result = calculate_hic_sohic_df(HICSOHICData(**data))
                    df_results['hic_sohic_h2s'] = result['df_hic_sohic']
                
                elif mechanism == 'hic_sohic_hf':
                    result = calculate_hic_sohic_hf_df(HICSOHICHFData(**data))
                    df_results['hic_sohic_hf'] = result['df_hic_sohic_hf']
                
                elif mechanism in ['alkaline_carbonate_scc', 'carbonate_scc', 'pwscc', 'hsc_hf']:
                    result = calculate_generic_scc_df(GenericSCCData(**data))
                    df_results[mechanism] = result['df']
                
                elif mechanism == 'htha':
                    result = calculate_htha_df(HTHAData(**data))
                    df_results['htha'] = result['df_htha']
                
                elif mechanism == 'brittle_fracture':
                    result = calculate_brittle_fracture_df(BrittleFractureData(**data))
                    df_results['brittle_fracture'] = result['df_brittle_fracture']
                
                elif mechanism in ['sigma_phase', 'temper_embrittlement', '885f_embrittlement']:
                    result = EmbrittlementCalculator().calculate(EmbrittlementData(**data))
                    df_results[mechanism] = result['df_embrittlement']
                
                elif mechanism == 'mechanical_fatigue':
                    result = calculate_mechanical_fatigue_df(MechanicalFatigueData(**data))
                    df_results['mechanical_fatigue'] = result['df_fatigue']
                
                elif mechanism in ['lining_degradation', 'refractory_degradation']:
                    result = calculate_lining_degradation_df(LiningDegradationData(**data))
                    df_results[mechanism] = result['df_lining']
                
            except Exception as e:
                df_results[mechanism] = {'error': str(e)}
        
        return df_results
    
    def _calculate_pof(self, component: ComponentData, df_results: Dict) -> Dict:
        """Calculate PoF from all DFs"""
        # GFF (Generic Failure Frequency) from Table 3.1
        gff_table = {
            'pipe': 1.56e-4,
            'vessel': 3.06e-4,
            'heat_exchanger': 3.36e-4,
            'tank': 6.91e-6,
            'filter': 1.50e-3
        }
        
        gff = gff_table.get(component.component_type, 1.56e-4)
        
        # Total DF = sum of all individual DFs
        total_df = sum([v for v in df_results.values() if isinstance(v, (int, float))])
        
        # PoF = GFF × DF_total × FMS
        pof = gff * total_df * component.fms
        
        return {
            'pof_per_year': pof,
            'gff': gff,
            'total_df': total_df,
            'fms': component.fms,
            'active_mechanisms': len([k for k, v in df_results.items() if isinstance(v, (int, float)) and v > 0])
        }
    
    def _calculate_cof(self, component: ComponentData) -> Dict:
        """Calculate CoF (Level 1)"""
        cof_data = COFData(
            component_type=component.component_type,
            fluid_type=component.fluid_type,
            phase=component.phase,
            operating_pressure_psig=component.operating_pressure_psig,
            operating_temp_f=component.operating_temp_f,
            diameter_inches=component.diameter_inches,
            inventory_mass_lbs=1000.0,  # Placeholder
            release_rate_lbs_per_sec=10.0  # Placeholder
        )
        
        cof_result = calculate_cof(cof_data)
        
        return {
            'cof_financial': cof_result['cof_financial'],
            'ca_cmd': cof_result['ca_cmd'],
            'ca_flam': cof_result['ca_flam'],
            'ca_tox': cof_result['ca_tox'],
            'ca_env': cof_result['ca_env']
        }
    
    def _determine_risk(self, pof_result: Dict, cof_result: Dict) -> Dict:
        """Determine risk matrix position"""
        pof = pof_result['pof_per_year']
        cof = cof_result['cof_financial']
        
        # Determine PoF category (1-5)
        pof_cat = 5
        for cat, (low, high) in self.RISK_MATRIX['pof_ranges'].items():
            if low <= pof < high:
                pof_cat = cat
                break
        
        # Determine CoF category (A-E)
        cof_cat = 'E'
        for cat, (low, high) in self.RISK_MATRIX['cof_ranges'].items():
            if low <= cof < high:
                cof_cat = cat
                break
        
        # Risk score = PoF × CoF
        risk_score = pof * cof
        
        # Risk level
        if pof_cat >= 4 or cof_cat in ['D', 'E']:
            risk_level = 'High'
        elif pof_cat >= 3 or cof_cat in ['C']:
            risk_level = 'Medium-High'
        elif pof_cat >= 2:
            risk_level = 'Medium'
        else:
            risk_level = 'Low'
        
        return {
            'pof_category': pof_cat,
            'cof_category': cof_cat,
            'risk_score': risk_score,
            'risk_level': risk_level
        }
    
    def _recommend_inspection(self, risk_result: Dict) -> Dict:
        """Recommend inspection interval based on risk"""
        risk_level = risk_result['risk_level']
        
        recommendations = {
            'High': {
                'interval_years': 2,
                'effectiveness': 'A',
                'priority': 'Critical',
                'action': 'Immediate inspection required'
            },
            'Medium-High': {
                'interval_years': 4,
                'effectiveness': 'B',
                'priority': 'High',
                'action': 'Schedule inspection within 6 months'
            },
            'Medium': {
                'interval_years': 8,
                'effectiveness': 'C',
                'priority': 'Medium',
                'action': 'Schedule inspection within 1 year'
            },
            'Low': {
                'interval_years': 16,
                'effectiveness': 'D',
                'priority': 'Low',
                'action': 'Routine inspection acceptable'
            }
        }
        
        return recommendations.get(risk_level, recommendations['Medium'])


def print_complete_rbi_report(result: Dict):
    """Print comprehensive RBI report"""
    print("\n" + "="*100)
    print("COMPLETE RBI ASSESSMENT REPORT - API 581 4TH EDITION")
    print("="*100)
    
    print(f"\nCOMPONENT: {result['component_id']} ({result['component_type']})")
    print("-" * 100)
    
    # Damage Factors
    print("\nACTIVE DAMAGE MECHANISMS:")
    print("-" * 100)
    for mechanism, df_value in result['damage_factors'].items():
        if isinstance(df_value, (int, float)) and df_value > 0:
            print(f"  {mechanism:30s}: DF = {df_value:>10.2f}")
    
    # PoF
    print("\nPROBABILITY OF FAILURE (PoF):")
    print("-" * 100)
    pof = result['pof']
    print(f"  GFF (Generic Failure Frequency): {pof['gff']:.6e}")
    print(f"  Total DF (Sum of all mechanisms): {pof['total_df']:.2f}")
    print(f"  FMS (Management Systems Factor): {pof['fms']:.2f}")
    print(f"  PoF (per year): {pof['pof_per_year']:.6e}")
    print(f"  Active mechanisms: {pof['active_mechanisms']}")
    
    # CoF
    print("\nCONSEQUENCE OF FAILURE (CoF):")
    print("-" * 100)
    cof = result['cof']
    print(f"  Financial CoF: ${cof['cof_financial']:,.0f}")
    print(f"  Flammable Area: {cof['ca_flam']:.0f} ft²")
    print(f"  Toxic Area: {cof['ca_tox']:.0f} ft²")
    print(f"  Environmental Area: {cof['ca_env']:.0f} ft²")
    
    # Risk
    print("\nRISK ASSESSMENT:")
    print("-" * 100)
    risk = result['risk']
    print(f"  Risk Matrix Position: {result['risk_matrix_position']}")
    print(f"  PoF Category: {risk['pof_category']}")
    print(f"  CoF Category: {risk['cof_category']}")
    print(f"  Risk Score: {risk['risk_score']:.6e}")
    print(f"  Risk Level: {risk['risk_level']}")
    
    # Inspection Recommendation
    print("\nINSPECTION RECOMMENDATION:")
    print("-" * 100)
    insp = result['inspection_recommendation']
    print(f"  Interval: {insp['interval_years']} years")
    print(f"  Effectiveness Required: Level {insp['effectiveness']}")
    print(f"  Priority: {insp['priority']}")
    print(f"  Action: {insp['action']}")
    
    print("\n" + "="*100 + "\n")


# Example usage
if __name__ == "__main__":
    # Example: Pipe with multiple active mechanisms
    component = ComponentData(
        component_id='P-101',
        component_type='pipe',
        fluid_type='hydrocarbon',
        phase='liquid',
        operating_pressure_psig=500.0,
        operating_temp_f=450.0,
        material='carbon_steel',
        diameter_inches=16.0,
        wall_thickness_inches=0.5
    )
    
    # Active mechanisms
    active_mechanisms = {
        'thinning': {
            'furnished_thickness': 0.5,
            'required_thickness': 0.35,
            'corrosion_rate': 5.0,
            'age': 10.0,
            'inspection_effectiveness': 'C',
            'num_inspections': 2
        },
        'external_corrosion': {
            'driver_category': 'moderate',
            'furnished_thickness': 0.5,
            'operating_temp': 450.0,
            'coating_quality': 'good',
            'age_years': 10.0,
            'num_inspections_C': 1
        },
        'chloride_scc': {
            'material': 'austenitic_stainless',
            'temperature_f': 150.0,
            'chloride_ppm': 100.0,
            'ph': 6.0,
            'age_since_inspection': 5.0,
            'num_inspections_C': 1
        }
    }
    
    # Calculate complete RBI
    calculator = CompleteRBICalculator()
    result = calculator.calculate_complete_rbi(component, active_mechanisms)
    
    # Print report
    print_complete_rbi_report(result)
    
    # Export to JSON
    with open('/tmp/rbi-581-calculator/complete_rbi_example.json', 'w') as f:
        json.dump(result, f, indent=2)
    
    print("✓ Complete RBI result saved to: complete_rbi_example.json")
