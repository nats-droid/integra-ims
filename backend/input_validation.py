"""
Input Validation and Flag System
Tracks missing data, assumptions, and data quality for audit trail
"""

from enum import Enum
from datetime import datetime
from typing import Any, Optional, Dict, List, Tuple


class InputFlag(Enum):
    """
    Data quality flags for RBI assessment audit trail
    """
    MISSING = "MISSING"           # Blank, no default exists → module skipped, result incomplete
    BLOCKING = "BLOCKING"         # Required, no default → component not calculated
    DEFAULT_581 = "DEFAULT_581"   # API 581 default used (e.g. Cl⁻ > 1000 ppm)
    ASSUMED = "ASSUMED"           # Conservative engine assumption (e.g. PWHT = No)
    LCI_OVERRIDE = "LCI_OVERRIDE" # LCI table/value replaced 581 example
    ENGINEER = "ENGINEER"         # Value entered/changed by engineer (name + date)
    VALID = "VALID"               # Valid user input, no issues


class ValidationResult:
    """
    Result of input validation for a single field
    """
    def __init__(
        self,
        field_name: str,
        value: Any,
        flag: Optional[InputFlag] = None,
        message: str = "",
        source: str = "user_input",
        engineer_name: Optional[str] = None
    ):
        self.field_name = field_name
        self.value = value
        self.flag = flag
        self.message = message
        self.source = source
        self.engineer_name = engineer_name
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'field_name': self.field_name,
            'value': self.value,
            'flag': self.flag.value if self.flag else None,
            'message': self.message,
            'source': self.source,
            'engineer_name': self.engineer_name,
            'timestamp': self.timestamp.isoformat()
        }
    
    def __repr__(self):
        flag_str = f" [{self.flag.value}]" if self.flag else ""
        return f"ValidationResult({self.field_name}={self.value}{flag_str})"


def validate_input(
    field_name: str,
    value: Any,
    required: bool = False,
    default_581: Any = None,
    assumed: Any = None,
    data_type: Optional[type] = None,
    value_range: Optional[Tuple] = None,
    allowed_values: Optional[List] = None,
    engineer_name: Optional[str] = None
) -> ValidationResult:
    """
    Validate single input field with flag assignment
    
    Args:
        field_name: Name of the field
        value: Input value
        required: True if field is required (BLOCKING if missing)
        default_581: API 581 default value
        assumed: Conservative assumption if no default
        data_type: Expected data type (int, float, str, bool)
        value_range: (min, max) for numeric validation
        allowed_values: List of allowed values (for enums)
        engineer_name: Engineer who entered/modified the value
    
    Returns:
        ValidationResult with appropriate flag
    """
    # Check if value exists
    if value is None or value == "" or (isinstance(value, str) and value.strip() == ""):
        # Missing value
        if required:
            return ValidationResult(
                field_name=field_name,
                value=None,
                flag=InputFlag.BLOCKING,
                message=f"{field_name} is required but missing. Component cannot be calculated.",
                source="validation"
            )
        elif default_581 is not None:
            return ValidationResult(
                field_name=field_name,
                value=default_581,
                flag=InputFlag.DEFAULT_581,
                message=f"{field_name} missing. Using API 581 default: {default_581}",
                source="API_581_default"
            )
        elif assumed is not None:
            return ValidationResult(
                field_name=field_name,
                value=assumed,
                flag=InputFlag.ASSUMED,
                message=f"{field_name} missing. Conservative assumption: {assumed}",
                source="engine_assumption"
            )
        else:
            return ValidationResult(
                field_name=field_name,
                value=None,
                flag=InputFlag.MISSING,
                message=f"{field_name} is missing. Module may be skipped.",
                source="validation"
            )
    
    # Type validation
    if data_type:
        if not isinstance(value, data_type):
            try:
                value = data_type(value)
            except (ValueError, TypeError):
                return ValidationResult(
                    field_name=field_name,
                    value=None,
                    flag=InputFlag.BLOCKING,
                    message=f"{field_name} has invalid type. Expected {data_type.__name__}, got {type(value).__name__}",
                    source="validation"
                )
    
    # Range validation (for numeric types)
    if value_range and isinstance(value, (int, float)):
        min_val, max_val = value_range
        if not (min_val <= value <= max_val):
            return ValidationResult(
                field_name=field_name,
                value=None,
                flag=InputFlag.BLOCKING,
                message=f"{field_name} out of valid range [{min_val}, {max_val}]. Value: {value}",
                source="validation"
            )
    
    # Allowed values validation (for enums)
    if allowed_values and value not in allowed_values:
        return ValidationResult(
            field_name=field_name,
            value=None,
            flag=InputFlag.BLOCKING,
            message=f"{field_name} must be one of {allowed_values}. Got: {value}",
            source="validation"
        )
    
    # Valid input
    flag = InputFlag.ENGINEER if engineer_name else InputFlag.VALID
    
    return ValidationResult(
        field_name=field_name,
        value=value,
        flag=flag,
        message="" if flag == InputFlag.VALID else f"Entered by {engineer_name}",
        source="user_input" if flag == InputFlag.VALID else "engineer",
        engineer_name=engineer_name
    )


class ComponentValidator:
    """
    Validates complete component data for RBI assessment
    """
    def __init__(self):
        self.flags: List[ValidationResult] = []
        self.blocking_flags: List[ValidationResult] = []
        self.warnings: List[ValidationResult] = []
    
    def validate_component(self, component_data: Dict) -> Dict:
        """
        Validate all required fields for RBI assessment
        
        Returns:
            {
                'valid': bool,
                'validated_data': dict,
                'flags': list of ValidationResult,
                'blocking': list of blocking flags,
                'warnings': list of warning flags,
                'summary': dict
            }
        """
        validated = {}
        
        # === CRITICAL FIELDS (BLOCKING) ===
        
        # Equipment ID
        result = validate_input(
            'equipment_id',
            component_data.get('equipment_id'),
            required=True
        )
        validated['equipment_id'] = result.value
        self._add_flag(result)
        
        # Component type
        result = validate_input(
            'component_type',
            component_data.get('component_type'),
            required=True,
            allowed_values=['pipe', 'vessel', 'heat_exchanger', 'tank', 'filter']
        )
        validated['component_type'] = result.value
        self._add_flag(result)
        
        # Operating pressure
        result = validate_input(
            'operating_pressure_psig',
            component_data.get('operating_pressure_psig'),
            required=True,
            data_type=float,
            value_range=(0, 10000)
        )
        validated['operating_pressure_psig'] = result.value
        self._add_flag(result)
        
        # Operating temperature
        result = validate_input(
            'operating_temp_f',
            component_data.get('operating_temp_f'),
            required=True,
            data_type=float,
            value_range=(-50, 1200)
        )
        validated['operating_temp_f'] = result.value
        self._add_flag(result)
        
        # Diameter
        result = validate_input(
            'diameter_inches',
            component_data.get('diameter_inches'),
            required=True,
            data_type=float,
            value_range=(0.5, 300)
        )
        validated['diameter_inches'] = result.value
        self._add_flag(result)
        
        # === OPTIONAL FIELDS WITH DEFAULTS ===
        
        # Fluid type
        result = validate_input(
            'fluid_type',
            component_data.get('fluid_type'),
            default_581='hydrocarbon'
        )
        validated['fluid_type'] = result.value
        self._add_flag(result)
        
        # FMS
        result = validate_input(
            'fms',
            component_data.get('fms'),
            default_581=1.0,
            data_type=float,
            value_range=(0.5, 2.0)
        )
        validated['fms'] = result.value
        self._add_flag(result)
        
        # PWHT (Post-Weld Heat Treatment)
        result = validate_input(
            'pwht',
            component_data.get('pwht'),
            assumed=False,
            data_type=bool
        )
        validated['pwht'] = result.value
        self._add_flag(result)
        
        # Chloride concentration (for SCC)
        result = validate_input(
            'chloride_ppm',
            component_data.get('chloride_ppm'),
            default_581=1000,  # API 581 default for unknown
            data_type=float,
            value_range=(0, 100000)
        )
        validated['chloride_ppm'] = result.value
        self._add_flag(result)
        
        # Corrosion allowance
        result = validate_input(
            'corrosion_allowance',
            component_data.get('corrosion_allowance'),
            default_581=0.125,
            data_type=float,
            value_range=(0, 1.0)
        )
        validated['corrosion_allowance'] = result.value
        self._add_flag(result)
        
        # === SUMMARY ===
        summary = {
            'total_fields': len(validated),
            'blocking_count': len(self.blocking_flags),
            'warning_count': len([f for f in self.flags if f.flag in [InputFlag.MISSING, InputFlag.ASSUMED]]),
            'default_count': len([f for f in self.flags if f.flag == InputFlag.DEFAULT_581]),
            'engineer_count': len([f for f in self.flags if f.flag == InputFlag.ENGINEER]),
            'valid_count': len([f for f in self.flags if f.flag == InputFlag.VALID])
        }
        
        return {
            'valid': len(self.blocking_flags) == 0,
            'validated_data': validated,
            'flags': [f.to_dict() for f in self.flags],
            'blocking': [f.to_dict() for f in self.blocking_flags],
            'warnings': [f.to_dict() for f in self.warnings],
            'summary': summary
        }
    
    def _add_flag(self, result: ValidationResult):
        """Add validation result to appropriate list"""
        self.flags.append(result)
        
        if result.flag == InputFlag.BLOCKING:
            self.blocking_flags.append(result)
        elif result.flag in [InputFlag.MISSING, InputFlag.ASSUMED]:
            self.warnings.append(result)


def generate_flag_report(validation_result: Dict) -> str:
    """
    Generate human-readable flag report
    
    Args:
        validation_result: Output from ComponentValidator.validate_component()
    
    Returns:
        str: Formatted report
    """
    lines = []
    lines.append("=" * 70)
    lines.append("INPUT VALIDATION REPORT")
    lines.append("=" * 70)
    
    summary = validation_result['summary']
    lines.append(f"\nSummary:")
    lines.append(f"  Total Fields:       {summary['total_fields']}")
    lines.append(f"  Valid:              {summary['valid_count']}")
    lines.append(f"  Blocking Errors:    {summary['blocking_count']}")
    lines.append(f"  Warnings:           {summary['warning_count']}")
    lines.append(f"  API 581 Defaults:   {summary['default_count']}")
    lines.append(f"  Engineer Entries:   {summary['engineer_count']}")
    
    if validation_result['blocking']:
        lines.append(f"\n❌ BLOCKING ERRORS (Component cannot be calculated):")
        for flag in validation_result['blocking']:
            lines.append(f"  • {flag['field_name']}: {flag['message']}")
    
    if validation_result['warnings']:
        lines.append(f"\n⚠️  WARNINGS (Using defaults/assumptions):")
        for flag in validation_result['warnings']:
            lines.append(f"  • {flag['field_name']}: {flag['message']}")
    
    lines.append("\n" + "=" * 70)
    
    return "\n".join(lines)


# Example usage
if __name__ == '__main__':
    print("=" * 70)
    print("INPUT VALIDATION & FLAG SYSTEM - EXAMPLE CALCULATIONS")
    print("=" * 70)
    
    # Example 1: Complete valid data
    print("\n1. COMPLETE VALID DATA")
    complete_data = {
        'equipment_id': 'P-101',
        'component_type': 'pipe',
        'operating_pressure_psig': 300.0,
        'operating_temp_f': 600.0,
        'diameter_inches': 6.625,
        'fluid_type': 'hydrocarbon',
        'fms': 1.0,
        'pwht': True,
        'chloride_ppm': 50.0,
        'corrosion_allowance': 0.125
    }
    
    validator1 = ComponentValidator()
    result1 = validator1.validate_component(complete_data)
    
    print(f"  Valid: {result1['valid']}")
    print(f"  Blocking errors: {result1['summary']['blocking_count']}")
    print(f"  Warnings: {result1['summary']['warning_count']}")
    
    # Example 2: Missing critical field
    print("\n2. MISSING CRITICAL FIELD (equipment_id)")
    incomplete_data = {
        'component_type': 'pipe',
        'operating_pressure_psig': 300.0,
        'operating_temp_f': 600.0,
        'diameter_inches': 6.625
    }
    
    validator2 = ComponentValidator()
    result2 = validator2.validate_component(incomplete_data)
    
    print(f"  Valid: {result2['valid']}")
    print(f"  Blocking errors: {result2['summary']['blocking_count']}")
    if result2['blocking']:
        print(f"  Error: {result2['blocking'][0]['message']}")
    
    # Example 3: Using defaults and assumptions
    print("\n3. USING DEFAULTS AND ASSUMPTIONS")
    partial_data = {
        'equipment_id': 'V-201',
        'component_type': 'vessel',
        'operating_pressure_psig': 150.0,
        'operating_temp_f': 400.0,
        'diameter_inches': 48.0
        # Missing: fluid_type, fms, pwht, chloride_ppm, corrosion_allowance
    }
    
    validator3 = ComponentValidator()
    result3 = validator3.validate_component(partial_data)
    
    print(f"  Valid: {result3['valid']}")
    print(f"  Warnings: {result3['summary']['warning_count']}")
    print(f"  API 581 defaults: {result3['summary']['default_count']}")
    print(f"\n  Defaults used:")
    for flag in result3['flags']:
        if flag['flag'] == 'DEFAULT_581':
            print(f"    • {flag['field_name']}: {flag['value']}")
    
    # Example 4: Full report
    print("\n4. FULL VALIDATION REPORT")
    report = generate_flag_report(result3)
    print(report)
    
    print("\n" + "=" * 70)
