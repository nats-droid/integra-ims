"""
API 581 Consequence of Failure (CoF) Calculator
Simplified Level 1 methodology for financial consequence
"""

from typing import Dict, Optional
from dataclasses import dataclass
import math


@dataclass
class FluidData:
    """Fluid properties for consequence calculation"""
    fluid_type: str  # 'flammable', 'toxic', 'nonflammable', 'steam'
    phase: str  # 'liquid', 'gas', 'two_phase'
    
    # Physical properties
    molecular_weight: float = 0.0  # kg/kmol
    liquid_density: float = 0.0  # kg/m³
    vapor_density: float = 0.0  # kg/m³
    boiling_point: float = 0.0  # °C
    
    # Flammability
    is_flammable: bool = False
    autoignition_temp: float = 0.0  # °C
    heat_of_combustion: float = 0.0  # kJ/kg
    
    # Toxicity
    is_toxic: bool = False
    lc50: float = 0.0  # ppm (lethal concentration 50%)
    idlh: float = 0.0  # ppm (immediately dangerous to life or health)
    
    # Process conditions
    operating_temp: float = 25.0  # °C
    operating_pressure: float = 1.0  # bara
    inventory_mass: float = 0.0  # kg


@dataclass
class ConsequenceModifiers:
    """Modifiers for consequence calculation"""
    # Detection and isolation
    has_detection: bool = False
    has_isolation: bool = False
    isolation_time: float = 0.0  # minutes
    
    # Mitigation systems
    has_deluge_system: bool = False
    has_foam_system: bool = False
    has_blast_walls: bool = False
    
    # Population density
    population_density: str = "low"  # 'low', 'medium', 'high'
    
    # Environmental sensitivity
    environmental_factor: float = 1.0  # 1.0 = normal, >1.0 = sensitive area


class CofCalculator:
    """
    Simplified Consequence of Failure Calculator
    Based on API 581 Part 3 Level 1 methodology
    """
    
    # Financial consequence constants (USD)
    COST_PER_SQ_FT = {
        'low': 50,
        'medium': 150,
        'high': 500
    }
    
    # Business interruption cost (USD/day)
    BUSINESS_INTERRUPTION = {
        'low': 10000,
        'medium': 100000,
        'high': 1000000
    }
    
    # Environmental cleanup cost per kg released
    ENV_COST_PER_KG = {
        'nonhazardous': 1,
        'hazardous': 10,
        'toxic': 100
    }
    
    def __init__(self):
        pass
    
    def calculate_release_rate(
        self,
        hole_size: str,
        fluid: FluidData,
        vessel_diameter: float = 1000.0  # mm
    ) -> Dict:
        """
        Calculate theoretical release rate
        Simplified calculation
        
        Args:
            hole_size: 'small' (6mm), 'medium' (25mm), 'large' (100mm), 'rupture'
            fluid: Fluid properties
            vessel_diameter: Vessel diameter in mm
        
        Returns:
            Release rate data
        """
        # Hole diameters (mm)
        hole_diameters = {
            'small': 6.35,      # 1/4 inch
            'medium': 25.4,     # 1 inch
            'large': 101.6,     # 4 inch
            'rupture': vessel_diameter  # Full bore rupture
        }
        
        d_hole = hole_diameters[hole_size]  # mm
        area_hole = math.pi * (d_hole / 2000.0) ** 2  # m²
        
        # Simplified liquid release rate (kg/s)
        # Q = Cd × A × sqrt(2 × rho × delta_P)
        # Very simplified: assume atmospheric discharge
        
        if fluid.phase == 'liquid':
            Cd = 0.61  # Discharge coefficient
            rho = fluid.liquid_density  # kg/m³
            delta_P = (fluid.operating_pressure - 1.0) * 100000  # Pa
            
            if delta_P > 0:
                velocity = math.sqrt(2 * delta_P / rho)  # m/s
                release_rate = Cd * area_hole * rho * velocity  # kg/s
            else:
                release_rate = 0.0
        else:
            # Gas release (simplified ideal gas)
            release_rate = area_hole * fluid.vapor_density * 100.0  # Very simplified
        
        return {
            'hole_size': hole_size,
            'hole_diameter_mm': d_hole,
            'hole_area_m2': area_hole,
            'release_rate_kg_s': release_rate,
            'release_rate_kg_hr': release_rate * 3600
        }
    
    def calculate_flammable_consequence(
        self,
        release_rate: float,  # kg/s
        fluid: FluidData,
        duration: float = 600.0  # seconds (10 min default)
    ) -> Dict:
        """
        Calculate flammable consequence area
        Very simplified - should use proper dispersion modeling
        """
        if not fluid.is_flammable:
            return {
                'consequence_area_ft2': 0.0,
                'consequence_area_m2': 0.0,
                'event_type': 'none'
            }
        
        # Total mass released
        total_mass = release_rate * duration  # kg
        
        # Simplified consequence area calculation
        # Area ~ mass^(2/3) for vapor cloud
        # This is VERY simplified - real calculation needs dispersion modeling
        
        if fluid.phase == 'liquid':
            # Pool fire scenario
            pool_radius = math.sqrt(total_mass / (math.pi * fluid.liquid_density * 0.01))  # m
            thermal_radius = pool_radius * 3.0  # Simplified thermal radiation reach
            area_m2 = math.pi * thermal_radius ** 2
            event_type = 'pool_fire'
        else:
            # Vapor cloud explosion scenario
            cloud_radius = (total_mass / fluid.vapor_density) ** (1/3) * 5  # Simplified
            area_m2 = math.pi * cloud_radius ** 2
            event_type = 'vapor_cloud'
        
        area_ft2 = area_m2 * 10.764  # Convert to ft²
        
        return {
            'consequence_area_ft2': area_ft2,
            'consequence_area_m2': area_m2,
            'event_type': event_type,
            'total_mass_released_kg': total_mass
        }
    
    def calculate_toxic_consequence(
        self,
        release_rate: float,  # kg/s
        fluid: FluidData,
        duration: float = 600.0
    ) -> Dict:
        """
        Calculate toxic consequence area
        Very simplified - needs proper dispersion modeling
        """
        if not fluid.is_toxic:
            return {
                'consequence_area_ft2': 0.0,
                'consequence_area_m2': 0.0
            }
        
        total_mass = release_rate * duration
        
        # Simplified toxic cloud dispersion
        # Area ~ mass / concentration_threshold
        # This needs proper Gaussian dispersion model
        
        toxic_threshold = fluid.idlh if fluid.idlh > 0 else fluid.lc50
        
        if toxic_threshold > 0:
            # Very simplified area calculation
            area_m2 = (total_mass * 1000) / toxic_threshold  # Simplified
            area_m2 = min(area_m2, 100000)  # Cap at reasonable value
        else:
            area_m2 = 0.0
        
        area_ft2 = area_m2 * 10.764
        
        return {
            'consequence_area_ft2': area_ft2,
            'consequence_area_m2': area_m2,
            'total_mass_released_kg': total_mass
        }
    
    def calculate_financial_consequence(
        self,
        consequence_area_ft2: float,
        fluid: FluidData,
        modifiers: ConsequenceModifiers
    ) -> Dict:
        """
        Calculate financial consequence
        Includes equipment damage, business interruption, environmental
        """
        # Equipment damage cost based on affected area
        damage_cost = consequence_area_ft2 * self.COST_PER_SQ_FT[modifiers.population_density]
        
        # Business interruption (assume proportional to consequence)
        if consequence_area_ft2 > 10000:
            interruption_days = 30
            severity = 'high'
        elif consequence_area_ft2 > 1000:
            interruption_days = 7
            severity = 'medium'
        else:
            interruption_days = 1
            severity = 'low'
        
        interruption_cost = interruption_days * self.BUSINESS_INTERRUPTION[severity]
        
        # Environmental cost
        if fluid.is_toxic:
            env_category = 'toxic'
        elif fluid.is_flammable:
            env_category = 'hazardous'
        else:
            env_category = 'nonhazardous'
        
        env_cost = (fluid.inventory_mass * self.ENV_COST_PER_KG[env_category] * 
                   modifiers.environmental_factor)
        
        # Total financial consequence
        total_cost = damage_cost + interruption_cost + env_cost
        
        # Apply mitigation credits
        if modifiers.has_detection:
            total_cost *= 0.9
        if modifiers.has_isolation:
            total_cost *= 0.8
        if modifiers.has_deluge_system or modifiers.has_foam_system:
            total_cost *= 0.7
        
        # Determine CoF category (A-E) based on cost
        cof_category = self._get_cof_category(total_cost)
        
        return {
            'damage_cost_usd': damage_cost,
            'interruption_cost_usd': interruption_cost,
            'environmental_cost_usd': env_cost,
            'total_financial_consequence_usd': total_cost,
            'cof_category': cof_category,
            'cof_category_label': self._get_cof_label(cof_category)
        }
    
    def calculate_cof(
        self,
        hole_size: str,
        fluid: FluidData,
        modifiers: ConsequenceModifiers,
        vessel_diameter: float = 1000.0
    ) -> Dict:
        """
        Complete CoF calculation for a given hole size
        
        Returns:
            Complete CoF results
        """
        # Step 1: Calculate release rate
        release = self.calculate_release_rate(hole_size, fluid, vessel_diameter)
        
        # Determine release duration based on isolation
        if modifiers.has_isolation and modifiers.isolation_time > 0:
            duration = modifiers.isolation_time * 60  # Convert minutes to seconds
        else:
            duration = 600.0  # 10 minutes default
        
        # Step 2: Calculate consequence areas
        flammable_cons = self.calculate_flammable_consequence(
            release['release_rate_kg_s'],
            fluid,
            duration
        )
        
        toxic_cons = self.calculate_toxic_consequence(
            release['release_rate_kg_s'],
            fluid,
            duration
        )
        
        # Use larger of flammable or toxic consequence
        max_area_ft2 = max(
            flammable_cons['consequence_area_ft2'],
            toxic_cons['consequence_area_ft2']
        )
        
        # Step 3: Calculate financial consequence
        financial = self.calculate_financial_consequence(
            max_area_ft2,
            fluid,
            modifiers
        )
        
        return {
            'hole_size': hole_size,
            'release': release,
            'flammable_consequence': flammable_cons,
            'toxic_consequence': toxic_cons,
            'max_consequence_area_ft2': max_area_ft2,
            'financial_consequence': financial,
            'cof_category': financial['cof_category']
        }
    
    def _get_cof_category(self, total_cost: float) -> str:
        """Convert financial consequence to category (A-E)"""
        if total_cost < 10000:
            return 'A'
        elif total_cost < 100000:
            return 'B'
        elif total_cost < 1000000:
            return 'C'
        elif total_cost < 10000000:
            return 'D'
        else:
            return 'E'
    
    def _get_cof_label(self, category: str) -> str:
        """Get descriptive label for CoF category"""
        labels = {
            'A': 'Very Low',
            'B': 'Low',
            'C': 'Medium',
            'D': 'Medium-High',
            'E': 'High'
        }
        return labels.get(category, 'Unknown')
    
    def print_cof_report(self, result: Dict) -> str:
        """Generate human-readable CoF report"""
        report = []
        report.append("=" * 80)
        report.append("API 581 CONSEQUENCE OF FAILURE (COF) REPORT")
        report.append("=" * 80)
        report.append("")
        
        report.append(f"Hole Size: {result['hole_size'].upper()}")
        report.append("")
        
        report.append("-" * 80)
        report.append("RELEASE CHARACTERISTICS")
        report.append("-" * 80)
        rel = result['release']
        report.append(f"  Hole diameter:        {rel['hole_diameter_mm']:.2f} mm")
        report.append(f"  Hole area:            {rel['hole_area_m2']:.6f} m²")
        report.append(f"  Release rate:         {rel['release_rate_kg_s']:.2f} kg/s")
        report.append(f"                        {rel['release_rate_kg_hr']:.2f} kg/hr")
        report.append("")
        
        report.append("-" * 80)
        report.append("CONSEQUENCE AREAS")
        report.append("-" * 80)
        flam = result['flammable_consequence']
        tox = result['toxic_consequence']
        report.append(f"  Flammable consequence: {flam['consequence_area_ft2']:.0f} ft²")
        if flam['consequence_area_ft2'] > 0:
            report.append(f"    Event type:          {flam['event_type']}")
            report.append(f"    Mass released:       {flam['total_mass_released_kg']:.0f} kg")
        report.append(f"  Toxic consequence:     {tox['consequence_area_ft2']:.0f} ft²")
        report.append(f"  Maximum area:          {result['max_consequence_area_ft2']:.0f} ft²")
        report.append("")
        
        report.append("-" * 80)
        report.append("FINANCIAL CONSEQUENCE")
        report.append("-" * 80)
        fin = result['financial_consequence']
        report.append(f"  Equipment damage:      ${fin['damage_cost_usd']:,.0f}")
        report.append(f"  Business interruption: ${fin['interruption_cost_usd']:,.0f}")
        report.append(f"  Environmental:         ${fin['environmental_cost_usd']:,.0f}")
        report.append(f"  ---")
        report.append(f"  Total consequence:     ${fin['total_financial_consequence_usd']:,.0f}")
        report.append("")
        
        report.append("=" * 80)
        report.append(f"COF CATEGORY: {result['cof_category']} ({fin['cof_category_label']})")
        report.append("=" * 80)
        report.append("")
        
        return "\n".join(report)


# Convenience function
def calculate_cof(
    hole_size: str,
    fluid: FluidData,
    modifiers: ConsequenceModifiers,
    vessel_diameter: float = 1000.0
) -> Dict:
    """
    Convenience function to calculate CoF
    
    Returns:
        Complete CoF results
    """
    calculator = CofCalculator()
    return calculator.calculate_cof(hole_size, fluid, modifiers, vessel_diameter)
