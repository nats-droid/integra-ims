"""
Test Reference Data Layer - Lookup Functions
"""

import sys
sys.path.append('..')

from refdata.table_registry import TableRegistry

print("=" * 70)
print("REFERENCE DATA LAYER - LOOKUP TESTS")
print("=" * 70)

# Initialize registry
registry = TableRegistry(data_dir="/tmp/rbi-581-calculator/refdata")

# Test 1: Exact lookup (GDF table)
print("\n1. EXACT LOOKUP - GDF Table")
print("   Looking up: inspection_category='A', inspection_number=3")
result = registry.lookup(
    table_id="2-1",
    key_values={'inspection_category': 'A', 'inspection_number': 3}
)
print(f"   Result: GDF = {result['value']}")
print(f"   Method: {result['method']}")
print(f"   Rows used: {result['rows_used']}")

# Test 2: Exact lookup with multiple value columns
print("\n2. EXACT LOOKUP - Thinning Coefficients")
print("   Looking up: component_type='pipe'")
result = registry.lookup(
    table_id="2-2",
    key_values={'component_type': 'pipe'}
)
print(f"   Result: {result['value']}")
print(f"   Method: {result['method']}")

# Test 3: Linear interpolation
print("\n3. LINEAR INTERPOLATION - Material Properties")
print("   Looking up: temperature_f=550°F (between 500 and 600)")
result = registry.lookup(
    table_id="3-1",
    key_values={'temperature_f': 550}
)
print(f"   Result: {result['value']}")
print(f"   Method: {result['method']}")
print(f"   Interpolated: {result['interpolated']}")
print(f"   Rows used: {result['rows_used']}")

# Test 4: Exact match (no interpolation needed)
print("\n4. EXACT MATCH - Material Properties at exact temperature")
print("   Looking up: temperature_f=600°F (exact match)")
result = registry.lookup(
    table_id="3-1",
    key_values={'temperature_f': 600}
)
print(f"   Result: {result['value']}")
print(f"   Method: {result['method']}")
print(f"   Interpolated: {result['interpolated']}")

# Test 5: Multiple lookups (GDF for different inspection effectiveness)
print("\n5. MULTIPLE LOOKUPS - GDF Progression")
print("   Category A (Highly Effective) - 0 to 5 inspections:")
for n in range(6):
    result = registry.lookup(
        table_id="2-1",
        key_values={'inspection_category': 'A', 'inspection_number': n}
    )
    print(f"   Inspection #{n}: GDF = {result['value']}")

# Test 6: Error handling - missing key
print("\n6. ERROR HANDLING - Non-existent component type")
result = registry.lookup(
    table_id="2-2",
    key_values={'component_type': 'reactor'}
)
print(f"   Result: {result.get('value')}")
if 'error' in result:
    print(f"   Error: {result['error']}")

print("\n" + "=" * 70)
