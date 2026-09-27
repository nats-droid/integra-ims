# RBI API 581 Backend - Integration Guide for Integra IMS

**Purpose:** Backend API service for RBI calculations
**Integration:** Designed to be consumed by Integra IMS frontend (Next.js)
**Deployment:** Separate backend service (API-only)

---

## 🔗 INTEGRATION ARCHITECTURE

```
┌─────────────────────────┐
│  Integra IMS Frontend   │
│     (Next.js)           │
│  Port: 3000             │
└───────────┬─────────────┘
            │
            │ HTTP/REST API
            │
┌───────────▼─────────────┐
│  RBI Backend API        │
│     (FastAPI)           │
│  Port: 8000 / Vercel    │
└─────────────────────────┘
```

---

## 📡 API ENDPOINTS

### **Base URL:**
- Local: `http://localhost:8000`
- Production: `https://rbi-api.your-domain.com` (or Vercel URL)

### **Available Endpoints:**

**1. Health Check**
```
GET /health
Response: {"status": "ok", "version": "1.0.0"}
```

**2. Code Calculations**
```
POST /api/v1/calculate-tmin
Body: {
  "pressure_psig": 300,
  "diameter_inches": 6.625,
  "allowable_stress_psi": 20000,
  "joint_efficiency": 1.0,
  "corrosion_allowance": 0.125
}
Response: {
  "t_required": 0.164,
  "t_min": 0.289,
  "steps": [...],
  "code": "B31.3"
}
```

```
POST /api/v1/calculate-corrosion-rate
Body: {
  "thickness_history": [
    {"date": "2020-01-01", "thickness_inches": 0.500},
    {"date": "2023-01-01", "thickness_inches": 0.485}
  ]
}
Response: {
  "corrosion_rate_mpy": 5.0,
  "remaining_life_years": 8.2,
  "steps": [...]
}
```

```
POST /api/v1/calculate-next-date
Body: {
  "rbi_interval_years": 5.0,
  "code_interval_years": 4.0,
  "regulatory_cap_years": 5.0,
  "last_inspection_date": "2024-01-01"
}
Response: {
  "next_date": "2028-01-01",
  "governing": "code",
  "interval_years": 4.0
}
```

**3. FMS Audit**
```
POST /api/v1/calculate-fms
Body: {
  "audit_scores": {
    "management_inspection": 15,
    "site_management": 14,
    "moc": 11,
    "failure_investigation": 11,
    "process_safety": 11,
    "operating_procedures": 10
  }
}
Response: {
  "pscore": 72,
  "fms": 1.000,
  "interpretation": "Good management system"
}
```

**4. Timeline Planning**
```
POST /api/v1/calculate-timeline
Body: {
  "initial_pof": 0.001,
  "cof": 1000,
  "corrosion_rate_mpy": 5.0,
  "current_thickness_inches": 0.500,
  "years": 10
}
Response: {
  "timeline": [
    {"year": 0, "pof": 0.001, "risk": 1.0, "thickness": 0.500},
    {"year": 0.5, "pof": 0.00102, "risk": 1.02, "thickness": 0.4975},
    ...
  ]
}
```

**5. Inspection Equivalence**
```
POST /api/v1/calculate-equivalence
Body: {
  "inspections": [
    {"type": "B", "date": "2020-01-01"},
    {"type": "B", "date": "2022-01-01"},
    {"type": "C", "date": "2023-01-01"}
  ]
}
Response: {
  "total_credit": 1.25,
  "meets_type_a": true,
  "recommendation": "Sufficient credit"
}
```

**6. Complete RBI Assessment**
```
POST /api/v1/complete-rbi
Body: {
  "equipment_id": "P-101",
  "component_type": "pipe",
  "damage_mechanism": "thinning",
  "operating_pressure_psig": 300,
  "operating_temp_f": 600,
  // ... all required fields
}
Response: {
  "pof": 0.00125,
  "cof": 1500,
  "risk": 1.875,
  "risk_category": "Low",
  "next_inspection_date": "2028-01-01",
  "timeline": [...],
  "flags": [...],
  "steps": [...]
}
```

---

## 🔌 INTEGRATION METHODS

### **Method 1: Direct Fetch (Recommended for Next.js)**

```typescript
// frontend/src/lib/api/rbi.ts
const RBI_API_BASE = process.env.NEXT_PUBLIC_RBI_API_URL || 'http://localhost:8000';

export async function calculateTmin(data: TminRequest): Promise<TminResponse> {
  const response = await fetch(`${RBI_API_BASE}/api/v1/calculate-tmin`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
  
  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }
  
  return response.json();
}

export async function calculateFMS(data: FMSRequest): Promise<FMSResponse> {
  const response = await fetch(`${RBI_API_BASE}/api/v1/calculate-fms`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
  
  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }
  
  return response.json();
}

// Export all calculation functions
export const RBIApi = {
  calculateTmin,
  calculateFMS,
  calculateTimeline,
  calculateEquivalence,
  completeRBI,
};
```

### **Method 2: Axios Client**

```typescript
// frontend/src/lib/api/rbi-client.ts
import axios from 'axios';

const rbiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_RBI_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 seconds
});

// Request interceptor (add auth token if needed)
rbiClient.interceptors.request.use((config) => {
  // Add auth token if available
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor (error handling)
rbiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('RBI API Error:', error);
    return Promise.reject(error);
  }
);

export default rbiClient;

// Usage
import rbiClient from '@/lib/api/rbi-client';

const result = await rbiClient.post('/api/v1/calculate-tmin', {
  pressure_psig: 300,
  diameter_inches: 6.625,
  // ...
});
```

### **Method 3: React Query Hooks**

```typescript
// frontend/src/hooks/useRBI.ts
import { useMutation, useQuery } from '@tanstack/react-query';
import { RBIApi } from '@/lib/api/rbi';

export function useCalculateTmin() {
  return useMutation({
    mutationFn: RBIApi.calculateTmin,
    onSuccess: (data) => {
      console.log('Tmin calculated:', data);
    },
    onError: (error) => {
      console.error('Tmin calculation failed:', error);
    },
  });
}

export function useCalculateFMS() {
  return useMutation({
    mutationFn: RBIApi.calculateFMS,
  });
}

// Usage in component
import { useCalculateTmin } from '@/hooks/useRBI';

function RBICalculator() {
  const { mutate: calculateTmin, data, isLoading } = useCalculateTmin();
  
  const handleSubmit = (formData) => {
    calculateTmin(formData);
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

## 🔧 ENVIRONMENT VARIABLES

### **Integra IMS Frontend (.env.local)**

```bash
# RBI Backend API
NEXT_PUBLIC_RBI_API_URL=https://rbi-api.your-domain.com

# Or for local development
NEXT_PUBLIC_RBI_API_URL=http://localhost:8000

# Optional: API Key (if backend requires auth)
NEXT_PUBLIC_RBI_API_KEY=your_api_key_here
```

---

## 🚀 DEPLOYMENT SCENARIOS

### **Scenario 1: Vercel Backend + Vercel Frontend**
- Backend: `https://rbi-backend.vercel.app`
- Frontend: `https://integra-ims.vercel.app`
- CORS: Configure backend to allow frontend domain

### **Scenario 2: Vercel Backend + Custom Frontend**
- Backend: `https://rbi-api.your-domain.com`
- Frontend: `https://integra.your-domain.com`
- CORS: Configure backend to allow frontend domain

### **Scenario 3: Docker Backend + Next.js Frontend**
- Backend: `http://localhost:8000` or internal network
- Frontend: `http://localhost:3000`
- CORS: Allow localhost

---

## 🔐 CORS CONFIGURATION

Backend already configured with CORS middleware. Update if needed:

```python
# api/rbi_endpoints.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Local frontend
        "https://integra-ims.vercel.app",  # Production frontend
        "https://integra.your-domain.com",  # Custom domain
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 📦 TYPESCRIPT TYPES (for Frontend)

```typescript
// frontend/src/types/rbi.ts

export interface TminRequest {
  pressure_psig: number;
  diameter_inches: number;
  allowable_stress_psi: number;
  joint_efficiency?: number;
  corrosion_allowance?: number;
}

export interface TminResponse {
  t_required: number;
  t_min: number;
  steps: Array<{
    step: string;
    value: number;
    unit: string;
  }>;
  code: string;
}

export interface FMSRequest {
  audit_scores: {
    management_inspection: number;
    site_management: number;
    moc: number;
    failure_investigation: number;
    process_safety: number;
    operating_procedures: number;
  };
}

export interface FMSResponse {
  pscore: number;
  fms: number;
  interpretation: string;
}

export interface TimelineRequest {
  initial_pof: number;
  cof: number;
  corrosion_rate_mpy: number;
  current_thickness_inches: number;
  years: number;
}

export interface TimelinePoint {
  year: number;
  pof: number;
  risk: number;
  thickness: number;
}

export interface TimelineResponse {
  timeline: TimelinePoint[];
}
```

---

## 🧪 TESTING INTEGRATION

### **Test from Integra IMS Frontend:**

```typescript
// Test connection
async function testRBIConnection() {
  try {
    const response = await fetch(`${process.env.NEXT_PUBLIC_RBI_API_URL}/health`);
    const data = await response.json();
    console.log('RBI API Status:', data);
    return data.status === 'ok';
  } catch (error) {
    console.error('RBI API not reachable:', error);
    return false;
  }
}

// Test calculation
async function testTminCalculation() {
  const result = await RBIApi.calculateTmin({
    pressure_psig: 300,
    diameter_inches: 6.625,
    allowable_stress_psi: 20000,
    joint_efficiency: 1.0,
    corrosion_allowance: 0.125,
  });
  
  console.log('Tmin:', result.t_min);
  console.log('Required:', result.t_required);
}
```

---

## 📊 EXAMPLE INTEGRA IMS PAGES

### **1. RBI Dashboard Page**

```typescript
// frontend/src/app/(dashboard)/rbi/page.tsx
'use client';

import { useState } from 'react';
import { useCalculateTmin } from '@/hooks/useRBI';

export default function RBIPage() {
  const { mutate: calculateTmin, data, isLoading } = useCalculateTmin();
  
  const handleSubmit = (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    calculateTmin({
      pressure_psig: parseFloat(formData.get('pressure')),
      diameter_inches: parseFloat(formData.get('diameter')),
      allowable_stress_psi: parseFloat(formData.get('stress')),
    });
  };
  
  return (
    <div className="p-6">
      <h1>RBI Calculator</h1>
      
      <form onSubmit={handleSubmit}>
        <input name="pressure" type="number" placeholder="Pressure (psig)" />
        <input name="diameter" type="number" placeholder="Diameter (in)" />
        <input name="stress" type="number" placeholder="Stress (psi)" />
        <button type="submit" disabled={isLoading}>
          {isLoading ? 'Calculating...' : 'Calculate'}
        </button>
      </form>
      
      {data && (
        <div className="mt-4">
          <h2>Results:</h2>
          <p>Required thickness: {data.t_required} in</p>
          <p>Minimum thickness: {data.t_min} in</p>
        </div>
      )}
    </div>
  );
}
```

---

## 🔄 DEPLOYMENT WORKFLOW

### **1. Deploy Backend**
```bash
cd /tmp/rbi-581-calculator
./setup_github.sh  # Push to GitHub
vercel --prod      # Deploy backend
# Note the URL: https://rbi-backend.vercel.app
```

### **2. Update Frontend Environment**
```bash
# In Integra IMS frontend
echo "NEXT_PUBLIC_RBI_API_URL=https://rbi-backend.vercel.app" >> .env.local
```

### **3. Add API Client to Frontend**
```bash
# Copy API client code (from this guide)
# Update CORS in backend if needed
```

### **4. Test Integration**
```bash
# Run frontend locally
npm run dev

# Test RBI endpoints from frontend
```

---

## ✅ CHECKLIST

**Backend:**
- [ ] Push to GitHub
- [ ] Deploy to Vercel
- [ ] Note API URL
- [ ] Configure CORS for frontend domain
- [ ] Test health endpoint

**Frontend:**
- [ ] Add NEXT_PUBLIC_RBI_API_URL to .env
- [ ] Create API client functions
- [ ] Add TypeScript types
- [ ] Create React Query hooks (optional)
- [ ] Test from frontend

---

## 📞 SUPPORT

**Backend URL:** To be determined after deployment
**API Docs:** `{BASE_URL}/docs` (auto-generated)
**Health Check:** `{BASE_URL}/health`

---

**Ready for integration with Integra IMS!** 🚀

Deploy backend first, then integrate with frontend using the methods above.
