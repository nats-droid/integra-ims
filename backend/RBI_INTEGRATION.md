# RBI Integration Guide - Integra IMS

**Date:** September 27, 2026
**Status:** ✅ Integrated & Working
**Location:** `~/integra/backend/`

---

## 🎉 INTEGRATION COMPLETE

RBI API 581 (9 modules) telah berhasil diintegrasikan ke dalam Integra IMS backend.

---

## 📡 AVAILABLE ENDPOINTS

**Base URL:** `http://localhost:8000` (local) or your deployed URL

### **1. Health Check**
```
GET /api/v1/rbi/health
```

**Response:**
```json
{
  "status": "ok",
  "module": "RBI API 581",
  "version": "1.0.0",
  "features": [
    "Code calculations (API 570/510/653)",
    "FMS audit (72-item)",
    "Risk timeline (10-year)",
    "Inspection equivalence (2B=1A)",
    "Complete RBI assessment"
  ]
}
```

---

### **2. Calculate Required Thickness (Tmin)**
```
POST /api/v1/rbi/calculate-tmin
```

**Request Body:**
```json
{
  "design_code": "B31.3",
  "equipment_type": "pipe",
  "pressure": 20.0,
  "diameter": 168.3,
  "design_temp": 150.0,
  "material": "Carbon Steel",
  "corrosion_allowance": 3.0,
  "joint_efficiency": 1.0,
  "unit_system": "SI"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "t_required": 2.5,
    "t_min": 5.5,
    "structural_tmin": 4.0,
    "code": "B31.3",
    "steps": [...]
  },
  "timestamp": "2026-09-27T05:05:00Z"
}
```

---

### **3. Calculate Corrosion Rate**
```
POST /api/v1/rbi/calculate-corrosion-rate
```

**Request Body:**
```json
{
  "thickness_history": [
    {"date": "2020-01-01", "thickness": 20.0},
    {"date": "2022-01-01", "thickness": 18.0},
    {"date": "2024-01-01", "thickness": 16.0}
  ],
  "tmin": 10.0,
  "design_life": 20.0
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "LT_rate": 1.0,
    "ST_rate": 1.0,
    "remaining_life": 6.0,
    "trend": "stable"
  },
  "timestamp": "2026-09-27T05:05:00Z"
}
```

---

### **4. Calculate FMS (Management Systems Factor)**
```
POST /api/v1/rbi/calculate-fms
```

**Request Body:**
```json
{
  "audit_scores": {
    "management_inspection": 15,
    "site_management": 14,
    "moc": 11,
    "failure_investigation": 11,
    "process_safety": 11,
    "operating_procedures": 10
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "pscore": 72,
    "fms": 1.00,
    "interpretation": "Good management system",
    "category_scores": {...}
  },
  "timestamp": "2026-09-27T05:05:00Z"
}
```

---

### **5. Calculate Risk Timeline**
```
POST /api/v1/rbi/calculate-timeline
```

**Request Body:**
```json
{
  "equipment_id": "P-101",
  "initial_pof": 0.001,
  "cof": 1000,
  "corrosion_rate": 0.5,
  "current_thickness": 12.0,
  "years": 10
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "timeline": [
      {"year": 0, "pof": 0.001, "risk": 1.0, "thickness": 12.0},
      {"year": 0.5, "pof": 0.00102, "risk": 1.02, "thickness": 11.75},
      ...
    ],
    "recommended_dates": ["2027-01-01", "2029-06-01"],
    "trajectory": "increasing"
  },
  "equipment_id": "P-101",
  "timestamp": "2026-09-27T05:05:00Z"
}
```

---

### **6. Calculate Inspection Equivalence**
```
POST /api/v1/rbi/calculate-equivalence
```

**Request Body:**
```json
{
  "inspections": [
    {"type": "B", "date": "2020-01-01", "effectiveness": 0.8},
    {"type": "B", "date": "2022-01-01", "effectiveness": 0.8},
    {"type": "C", "date": "2023-01-01", "effectiveness": 0.6}
  ],
  "damage_mechanism": "thinning"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "total_credit": 1.25,
    "meets_requirement": true,
    "recommendation": "Sufficient credit - next Type B in 2 years"
  },
  "timestamp": "2026-09-27T05:05:00Z"
}
```

---

### **7. Complete RBI Assessment**
```
POST /api/v1/rbi/complete-rbi
```

**Request Body:**
```json
{
  "equipment_id": "P-101",
  "equipment_type": "pipe",
  "damage_mechanism": "thinning",
  "operating_pressure": 20.0,
  "operating_temp": 150.0,
  "diameter": 168.3,
  "thickness_current": 12.0,
  "material": "Carbon Steel"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "pof": 0.00125,
    "cof": 1500,
    "risk": 1.875,
    "risk_category": "Low",
    "next_inspection_date": "2028-01-01",
    "timeline": [...],
    "flags": ["ASSUMED: FMS = 1.0"],
    "steps": [...]
  },
  "equipment_id": "P-101",
  "timestamp": "2026-09-27T05:05:00Z"
}
```

---

## 🎯 FRONTEND INTEGRATION

### **Method 1: Direct Fetch**

```typescript
// frontend/src/lib/api/rbi.ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function calculateTmin(data: TminRequest) {
  const response = await fetch(`${API_BASE}/api/v1/rbi/calculate-tmin`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${getAuthToken()}`, // If auth required
    },
    body: JSON.stringify(data),
  });
  
  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }
  
  return response.json();
}

export async function calculateFMS(data: FMSRequest) {
  const response = await fetch(`${API_BASE}/api/v1/rbi/calculate-fms`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  
  return response.json();
}
```

---

### **Method 2: React Query Hooks**

```typescript
// frontend/src/hooks/useRBI.ts
import { useMutation } from '@tanstack/react-query';
import { calculateTmin, calculateFMS } from '@/lib/api/rbi';

export function useCalculateTmin() {
  return useMutation({
    mutationFn: calculateTmin,
    onSuccess: (data) => {
      console.log('Tmin calculated:', data);
    },
  });
}

export function useCalculateFMS() {
  return useMutation({
    mutationFn: calculateFMS,
  });
}

// Usage in component
function RBICalculator() {
  const { mutate: calculate, data, isLoading } = useCalculateTmin();
  
  const handleSubmit = (formData) => {
    calculate(formData);
  };
  
  return (
    <div>
      {isLoading && <Spinner />}
      {data && <Result data={data} />}
    </div>
  );
}
```

---

## 🧪 TESTING

### **Test Script:**
```bash
cd ~/integra/backend
python3 test_rbi_integration.py
```

### **Manual Test (curl):**
```bash
# Health check
curl http://localhost:8000/api/v1/rbi/health

# Calculate Tmin
curl -X POST http://localhost:8000/api/v1/rbi/calculate-tmin \
  -H "Content-Type: application/json" \
  -d '{
    "design_code": "B31.3",
    "equipment_type": "pipe",
    "pressure": 20.0,
    "diameter": 168.3,
    "design_temp": 150.0,
    "material": "Carbon Steel",
    "corrosion_allowance": 3.0,
    "joint_efficiency": 1.0,
    "unit_system": "SI"
  }'
```

---

## 🚀 DEPLOYMENT

### **Local Development:**
```bash
cd ~/integra/backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

### **Production (Vercel/Docker):**
- Same as existing Integra backend deployment
- RBI modules included automatically

---

## 📁 FILES STRUCTURE

```
~/integra/backend/
├── app/
│   ├── main.py                  # Updated - added RBI router
│   └── api/
│       ├── rbi.py              # NEW - RBI endpoints
│       ├── analytics.py        # Existing
│       ├── remaining_life.py   # Existing
│       └── ...
├── codecalc/                    # NEW - Code calculations
│   ├── __init__.py
│   ├── tmin_calculator.py
│   ├── corrosion_rate.py
│   └── ...
├── fms_audit.py                # NEW - FMS calculator
├── timeline_planning.py        # NEW - Risk timeline
├── inspection_equivalence.py   # NEW - 2B=1A equivalence
└── test_rbi_integration.py     # NEW - Integration tests
```

---

## ✅ VERIFICATION CHECKLIST

**Backend:**
- [x] RBI modules copied to backend
- [x] Router added to main.py
- [x] Endpoints working
- [x] Health check passing
- [x] Tests passing

**Frontend (TODO):**
- [ ] API client created
- [ ] RBI pages created
- [ ] Charts/visualizations added
- [ ] End-to-end testing

---

## 🎯 NEXT STEPS

### **1. Create Frontend Pages:**

**RBI Calculator Page:**
- Location: `frontend/src/app/(dashboard)/rbi/calculator/page.tsx`
- Features: Tmin, corrosion rate, FMS forms

**Risk Timeline Page:**
- Location: `frontend/src/app/(dashboard)/rbi/timeline/page.tsx`
- Features: 10-year risk chart, inspection planning

**FMS Audit Page:**
- Location: `frontend/src/app/(dashboard)/rbi/audit/page.tsx`
- Features: 72-item audit form, score tracking

### **2. Add to Navigation:**
```typescript
// frontend/src/components/navigation/sidebar.tsx
{
  title: "RBI",
  icon: ShieldCheck,
  children: [
    { title: "Calculator", href: "/rbi/calculator" },
    { title: "Timeline", href: "/rbi/timeline" },
    { title: "FMS Audit", href: "/rbi/audit" },
  ]
}
```

---

## 📞 SUPPORT

**Integration working!** ✅

**Issues?**
- Check backend logs: `uvicorn app.main:app --reload`
- Test endpoints: Visit `/docs`
- Run tests: `python3 test_rbi_integration.py`

---

## 🎉 SUMMARY

**RBI API 581 fully integrated into Integra IMS:**
- ✅ 9 modules working
- ✅ 7 endpoints available
- ✅ API documentation ready
- ✅ Tests passing
- ✅ Ready for frontend development

**From separate backend → Fully integrated in 30 minutes!** 🚀

**Next:** Build frontend UI to consume RBI endpoints! 💪

---

**Documentation:** `~/integra/backend/RBI_INTEGRATION.md`
**Test Script:** `~/integra/backend/test_rbi_integration.py`
**API Docs:** `http://localhost:8000/docs`
