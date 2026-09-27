"""
Reference Data Layer for API 581 4th Edition
Manages all reference tables, curves, and lookup functions
"""

import os
import json
import csv
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum


class LookupMethod(Enum):
    """Methods for table lookup"""
    EXACT = "exact"                    # Exact match required
    BAND = "band"                      # Value falls in range (min, max)
    LINEAR_INTERP = "linear_interp"    # Linear interpolation between points
    CONSERVATIVE = "conservative"      # Use conservative neighbor


class TableRegistry:
    """
    Central registry for all API 581 reference tables
    """
    def __init__(self, data_dir: str = "./refdata"):
        self.data_dir = data_dir
        self.tables: Dict[str, Dict] = {}
        self._register_tables()
    
    def _register_tables(self):
        """Register all API 581 tables with metadata"""
        
        # Part 2 - Damage Factor Tables
        self.register_table(
            table_id="2-1",
            name="Generic Damage Factor (GDF) - Inspection Effectiveness",
            file="api581_4ed/table_2_1_gdf.csv",
            lookup_method=LookupMethod.EXACT,
            key_columns=["inspection_category", "inspection_number"],
            value_column="gdf"
        )
        
        self.register_table(
            table_id="2-2",
            name="Thinning Damage Factor - Base Equation Coefficients",
            file="api581_4ed/table_2_2_thinning_coeffs.csv",
            lookup_method=LookupMethod.EXACT,
            key_columns=["component_type"],
            value_column=["C1", "C2", "C3"]
        )
        
        self.register_table(
            table_id="2-3",
            name="SCC Damage Factor - Caustic Cracking Susceptibility",
            file="api581_4ed/table_2_3_caustic_scc.csv",
            lookup_method=LookupMethod.EXACT,
            key_columns=["material", "caustic_concentration_pct", "temperature_f"],
            value_column="severity_index"
        )
        
        self.register_table(
            table_id="2-4",
            name="SCC Damage Factor - Chloride SCC Susceptibility",
            file="api581_4ed/table_2_4_chloride_scc.csv",
            lookup_method=LookupMethod.BAND,
            key_columns=["material", "chloride_ppm", "temperature_f"],
            value_column="severity_index"
        )
        
        self.register_table(
            table_id="2-5",
            name="External Damage - Coating Quality",
            file="api581_4ed/table_2_5_coating_quality.csv",
            lookup_method=LookupMethod.EXACT,
            key_columns=["coating_condition"],
            value_column="driver_factor"
        )
        
        # Part 3 - Material Properties
        self.register_table(
            table_id="3-1",
            name="Material Properties - Carbon Steel",
            file="api581_4ed/table_3_1_cs_properties.csv",
            lookup_method=LookupMethod.LINEAR_INTERP,
            key_columns=["temperature_f"],
            value_column=["allowable_stress_psi", "yield_strength_psi"]
        )
        
        self.register_table(
            table_id="3-2",
            name="Material Properties - Stainless Steel",
            file="api581_4ed/table_3_2_ss_properties.csv",
            lookup_method=LookupMethod.LINEAR_INTERP,
            key_columns=["temperature_f"],
            value_column=["allowable_stress_psi", "yield_strength_psi"]
        )
        
        # Figures (Digitized)
        self.register_table(
            table_id="fig-2-1",
            name="Nelson Curve - High Temperature Sulfidation",
            file="api581_4ed/fig_2_1_nelson_curve.csv",
            lookup_method=LookupMethod.CONSERVATIVE,
            key_columns=["temperature_f", "h2s_pct"],
            value_column="corrosion_rate_mpy"
        )
        
        self.register_table(
            table_id="fig-2-2",
            name="NACE Amine Corrosion Chart",
            file="api581_4ed/fig_2_2_amine_chart.csv",
            lookup_method=LookupMethod.CONSERVATIVE,
            key_columns=["amine_concentration_pct", "acid_gas_loading"],
            value_column="corrosion_rate_mpy"
        )
    
    def register_table(
        self,
        table_id: str,
        name: str,
        file: str,
        lookup_method: LookupMethod,
        key_columns: List[str],
        value_column: Any
    ):
        """Register a reference table"""
        self.tables[table_id] = {
            'id': table_id,
            'name': name,
            'file': file,
            'lookup_method': lookup_method,
            'key_columns': key_columns,
            'value_column': value_column,
            'loaded': False,
            'data': None
        }
    
    def load_table(self, table_id: str) -> List[Dict]:
        """Load table data from CSV"""
        if table_id not in self.tables:
            raise ValueError(f"Table {table_id} not registered")
        
        table = self.tables[table_id]
        
        if table['loaded']:
            return table['data']
        
        filepath = os.path.join(self.data_dir, table['file'])
        
        # Create directory if needed
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Load CSV
        if not os.path.exists(filepath):
            # Return empty for now (tables will be created separately)
            table['data'] = []
            table['loaded'] = True
            return []
        
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            data = list(reader)
        
        # Convert numeric columns
        for row in data:
            for key, value in row.items():
                try:
                    row[key] = float(value)
                except (ValueError, TypeError):
                    pass  # Keep as string
        
        table['data'] = data
        table['loaded'] = True
        
        return data
    
    def lookup(
        self,
        table_id: str,
        key_values: Dict[str, Any],
        allow_interpolation: bool = True
    ) -> Dict:
        """
        Lookup value from table
        
        Args:
            table_id: Table identifier
            key_values: {key_column: value} to lookup
            allow_interpolation: Allow linear interpolation if applicable
        
        Returns:
            {
                'value': result value(s),
                'method': lookup method used,
                'rows_used': list of row indices,
                'interpolated': bool
            }
        """
        table = self.tables[table_id]
        data = self.load_table(table_id)
        
        if not data:
            return {
                'value': None,
                'method': None,
                'rows_used': [],
                'interpolated': False,
                'error': f"Table {table_id} is empty"
            }
        
        lookup_method = table['lookup_method']
        
        if lookup_method == LookupMethod.EXACT:
            return self._lookup_exact(data, table, key_values)
        
        elif lookup_method == LookupMethod.BAND:
            return self._lookup_band(data, table, key_values)
        
        elif lookup_method == LookupMethod.LINEAR_INTERP and allow_interpolation:
            return self._lookup_linear_interp(data, table, key_values)
        
        elif lookup_method == LookupMethod.CONSERVATIVE:
            return self._lookup_conservative(data, table, key_values)
        
        else:
            return {
                'value': None,
                'method': None,
                'rows_used': [],
                'interpolated': False,
                'error': f"Lookup method {lookup_method} not implemented"
            }
    
    def _lookup_exact(self, data: List[Dict], table: Dict, key_values: Dict) -> Dict:
        """Exact match lookup"""
        for idx, row in enumerate(data):
            match = True
            for key, value in key_values.items():
                if row.get(key) != value:
                    match = False
                    break
            
            if match:
                value_col = table['value_column']
                if isinstance(value_col, list):
                    result = {col: row[col] for col in value_col}
                else:
                    result = row[value_col]
                
                return {
                    'value': result,
                    'method': 'exact',
                    'rows_used': [idx],
                    'interpolated': False
                }
        
        return {
            'value': None,
            'method': 'exact',
            'rows_used': [],
            'interpolated': False,
            'error': 'No exact match found'
        }
    
    def _lookup_band(self, data: List[Dict], table: Dict, key_values: Dict) -> Dict:
        """Band/range lookup"""
        # Assumes keys like "min_temperature", "max_temperature"
        for idx, row in enumerate(data):
            match = True
            for key, value in key_values.items():
                min_key = f"min_{key}"
                max_key = f"max_{key}"
                
                if min_key in row and max_key in row:
                    if not (row[min_key] <= value <= row[max_key]):
                        match = False
                        break
                elif row.get(key) != value:
                    match = False
                    break
            
            if match:
                value_col = table['value_column']
                result = row[value_col]
                
                return {
                    'value': result,
                    'method': 'band',
                    'rows_used': [idx],
                    'interpolated': False
                }
        
        return {
            'value': None,
            'method': 'band',
            'rows_used': [],
            'interpolated': False,
            'error': 'No matching band found'
        }
    
    def _lookup_linear_interp(self, data: List[Dict], table: Dict, key_values: Dict) -> Dict:
        """Linear interpolation (1D only for now)"""
        # Simplified: assumes single key column for interpolation
        key_col = table['key_columns'][0]
        value_col = table['value_column']
        
        if isinstance(value_col, list):
            # Multiple value columns - interpolate each
            results = {}
            for vcol in value_col:
                interp_result = self._interpolate_1d(data, key_col, vcol, key_values[key_col])
                if interp_result['value'] is not None:
                    results[vcol] = interp_result['value']
            
            return {
                'value': results,
                'method': 'linear_interpolation',
                'rows_used': interp_result['rows_used'],
                'interpolated': True
            }
        else:
            return self._interpolate_1d(data, key_col, value_col, key_values[key_col])
    
    def _interpolate_1d(self, data: List[Dict], key_col: str, value_col: str, x: float) -> Dict:
        """1D linear interpolation"""
        # Sort by key
        sorted_data = sorted(data, key=lambda row: row[key_col])
        
        # Find bracketing points
        x1, y1, idx1 = None, None, None
        x2, y2, idx2 = None, None, None
        
        for idx, row in enumerate(sorted_data):
            x_val = row[key_col]
            y_val = row[value_col]
            
            if x_val <= x:
                x1, y1, idx1 = x_val, y_val, idx
            
            if x_val >= x and x2 is None:
                x2, y2, idx2 = x_val, y_val, idx
                break
        
        # Exact match
        if x1 == x:
            return {
                'value': y1,
                'method': 'exact',
                'rows_used': [idx1],
                'interpolated': False
            }
        
        # Interpolate
        if x1 is not None and x2 is not None and x1 != x2:
            y = y1 + (y2 - y1) * (x - x1) / (x2 - x1)
            return {
                'value': y,
                'method': 'linear_interpolation',
                'rows_used': [idx1, idx2],
                'interpolated': True
            }
        
        # Extrapolation (use closest)
        if x1 is not None:
            return {
                'value': y1,
                'method': 'extrapolation_low',
                'rows_used': [idx1],
                'interpolated': False,
                'warning': 'Value below table range, using minimum'
            }
        
        if x2 is not None:
            return {
                'value': y2,
                'method': 'extrapolation_high',
                'rows_used': [idx2],
                'interpolated': False,
                'warning': 'Value above table range, using maximum'
            }
        
        return {
            'value': None,
            'method': None,
            'rows_used': [],
            'interpolated': False,
            'error': 'Cannot interpolate'
        }
    
    def _lookup_conservative(self, data: List[Dict], table: Dict, key_values: Dict) -> Dict:
        """Conservative neighbor lookup (use higher/worse value)"""
        # Find all candidates
        candidates = []
        for idx, row in enumerate(data):
            candidates.append({
                'idx': idx,
                'row': row,
                'distance': self._calculate_distance(row, key_values, table['key_columns'])
            })
        
        # Sort by distance
        candidates.sort(key=lambda c: c['distance'])
        
        # Return most conservative (typically highest value)
        if candidates:
            value_col = table['value_column']
            result = candidates[0]['row'][value_col]
            
            return {
                'value': result,
                'method': 'conservative_neighbor',
                'rows_used': [candidates[0]['idx']],
                'interpolated': False
            }
        
        return {
            'value': None,
            'method': 'conservative_neighbor',
            'rows_used': [],
            'interpolated': False,
            'error': 'No candidates found'
        }
    
    def _calculate_distance(self, row: Dict, key_values: Dict, key_columns: List[str]) -> float:
        """Calculate Euclidean distance for conservative lookup"""
        distance = 0.0
        for key in key_columns:
            if key in row and key in key_values:
                distance += (row[key] - key_values[key]) ** 2
        return distance ** 0.5


# Example usage
if __name__ == '__main__':
    print("=" * 70)
    print("REFERENCE DATA LAYER - TABLE REGISTRY")
    print("=" * 70)
    
    # Initialize registry
    registry = TableRegistry()
    
    # List all tables
    print(f"\nRegistered Tables: {len(registry.tables)}")
    for table_id, table in registry.tables.items():
        print(f"  [{table_id}] {table['name']}")
        print(f"      Method: {table['lookup_method'].value}")
        print(f"      Keys:   {', '.join(table['key_columns'])}")
    
    print("\n" + "=" * 70)
