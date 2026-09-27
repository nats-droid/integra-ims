#!/usr/bin/env python3
"""
Test RBI Integration in Integra Backend
"""

import sys
sys.path.insert(0, '/root/integra/backend')

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

print("=" * 70)
print("TESTING RBI INTEGRATION IN INTEGRA BACKEND")
print("=" * 70)

# Test 1: RBI Health Check
print("\n1. RBI Health Check")
response = client.get("/api/v1/rbi/health")
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")

# Test 2: Calculate Tmin
print("\n2. Calculate Tmin (Code Calculation)")
response = client.post("/api/v1/rbi/calculate-tmin", json={
    "design_code": "B31.3",
    "equipment_type": "pipe",
    "pressure": 20.0,
    "diameter": 168.3,
    "design_temp": 150.0,
    "material": "Carbon Steel",
    "corrosion_allowance": 3.0,
    "joint_efficiency": 1.0,
    "unit_system": "SI"
})
print(f"Status: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    print(f"Success: {result['success']}")
    print(f"Tmin: {result['data'].get('t_min', 'N/A')} mm")
else:
    print(f"Error: {response.text}")

# Test 3: Calculate FMS
print("\n3. Calculate FMS (Management Systems Factor)")
response = client.post("/api/v1/rbi/calculate-fms", json={
    "audit_scores": {
        "management_inspection": 15,
        "site_management": 14,
        "moc": 11,
        "failure_investigation": 11,
        "process_safety": 11,
        "operating_procedures": 10
    }
})
print(f"Status: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    print(f"Success: {result['success']}")
    print(f"FMS: {result['data'].get('fms', 'N/A')}")
    print(f"Interpretation: {result['data'].get('interpretation', 'N/A')}")
else:
    print(f"Error: {response.text}")

# Test 4: API Documentation
print("\n4. Check API Documentation")
response = client.get("/docs")
print(f"Status: {response.status_code}")
print(f"API Docs: {'✓ Available' if response.status_code == 200 else '✗ Not available'}")

print("\n" + "=" * 70)
print("INTEGRATION TEST COMPLETE")
print("=" * 70)
print("\nRBI endpoints available at:")
print("  - GET  /api/v1/rbi/health")
print("  - POST /api/v1/rbi/calculate-tmin")
print("  - POST /api/v1/rbi/calculate-corrosion-rate")
print("  - POST /api/v1/rbi/calculate-fms")
print("  - POST /api/v1/rbi/calculate-timeline")
print("  - POST /api/v1/rbi/calculate-equivalence")
print("  - POST /api/v1/rbi/complete-rbi")
print("\nAPI Documentation: http://localhost:8000/docs")
print("=" * 70)
