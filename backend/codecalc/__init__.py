"""
Code Calculations Module
API 570, API 510, API 653, B31.3, ASME VIII-1

Pre-RBI calculations for:
- Required thickness (tmin)
- Corrosion rates (LT/ST)
- Remaining life
- Code intervals
- MAWP
- Next inspection date
"""

from .tmin_calculator import (
    calculate_tmin_piping,
    calculate_tmin_vessel,
    calculate_tmin_tank_shell
)
from .corrosion_rate import (
    calculate_corrosion_rate,
    calculate_remaining_life
)
from .code_interval import (
    calculate_code_interval_piping,
    calculate_code_interval_vessel,
    calculate_mawp
)
from .next_date import (
    calculate_next_inspection_date,
    get_regulatory_interval
)

__all__ = [
    'calculate_tmin_piping',
    'calculate_tmin_vessel',
    'calculate_tmin_tank_shell',
    'calculate_corrosion_rate',
    'calculate_remaining_life',
    'calculate_code_interval_piping',
    'calculate_code_interval_vessel',
    'calculate_mawp',
    'calculate_next_inspection_date',
    'get_regulatory_interval'
]

__version__ = '1.0.0'
