# Database Integration Guide - API 581 RBI System

## Overview

Panduan lengkap untuk mengintegrasikan RBI calculation engine dengan database Integra IMS (Supabase/PostgreSQL).

---

## 1. Database Schema

### Tables Created

#### 1.1 `rbi_assessments` (Main table)
**Purpose:** Menyimpan hasil RBI assessment lengkap

**Key Fields:**
- `id` (UUID) - Primary key
- `equipment_id` (UUID) - Reference ke equipment table
- `assessment_date` (DATE) - Tanggal assessment
- `component_type` (VARCHAR) - pipe, vessel, heat_exchanger, tank, filter
- **PoF fields:** `gff`, `total_df`, `pof_per_year`, `pof_category`
- **CoF fields:** `cof_financial`, `cof_ca_*`, `cof_category`
- **Risk fields:** `risk_score`, `risk_matrix_position`, `risk_level`
- **Inspection fields:** `inspection_interval_years`, `inspection_effectiveness`, `next_inspection_date`

#### 1.2 `damage_factor_results`
**Purpose:** Detail DF untuk setiap mechanism yang aktif

**Key Fields:**
- `assessment_id` (UUID) - Parent assessment
- `mechanism_type` (VARCHAR) - thinning, cui, chloride_scc, etc.
- `df_value` (DECIMAL) - Calculated damage factor
- `susceptibility` (VARCHAR) - high, medium, low, none
- `calculation_steps` (JSONB) - Step-by-step calculation details

#### 1.3 `rbi_inspection_history`
**Purpose:** Track actual inspections performed

**Key Fields:**
- `equipment_id` (UUID)
- `inspection_date` (DATE)
- `inspection_type` (VARCHAR)
- `inspection_effectiveness` (VARCHAR) - A, B, C, D, E
- `measured_thickness_inches` (DECIMAL)
- `defects_found` (BOOLEAN)

#### 1.4 `rbi_configurations`
**Purpose:** System-wide settings (GFF table, risk matrix ranges)

**Pre-populated data:**
- GFF table (Table 3.1)
- PoF category ranges
- CoF category ranges
- Inspection interval recommendations

### Views

#### 1.5 `vw_rbi_current_risk`
**Purpose:** Latest risk status per equipment

```sql
SELECT 
    equipment_id,
    tag_no,
    risk_level,
    risk_matrix_position,
    next_inspection_date,
    active_mechanisms
FROM vw_rbi_current_risk
WHERE risk_level = 'High';
```

#### 1.6 `vw_rbi_high_risk_equipment`
**Purpose:** Equipment requiring priority inspection

```sql
SELECT * FROM vw_rbi_high_risk_equipment
WHERE inspection_status = 'OVERDUE';
```

#### 1.7 `vw_rbi_mechanism_summary`
**Purpose:** Damage mechanism statistics across facility

```sql
SELECT 
    mechanism_type,
    equipment_count,
    avg_df,
    high_susceptibility_count
FROM vw_rbi_mechanism_summary
ORDER BY equipment_count DESC;
```

---

## 2. Installation Steps

### Step 1: Run Schema Script

```bash
# Connect to Supabase/PostgreSQL
psql -h your-supabase-db.supabase.co -U postgres -d postgres

# Run schema
\i /tmp/rbi-581-calculator/database/schema.sql
```

**Or via Supabase Dashboard:**
1. Go to SQL Editor
2. Copy paste content dari `schema.sql`
3. Run

### Step 2: Verify Tables

```sql
-- Check tables created
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name LIKE 'rbi_%';

-- Expected output:
-- rbi_assessments
-- damage_factor_results
-- rbi_inspection_history
-- rbi_configurations

-- Check views
SELECT table_name 
FROM information_schema.views 
WHERE table_schema = 'public' 
  AND table_name LIKE 'vw_rbi_%';
```

### Step 3: Verify Default Configurations

```sql
SELECT config_key, config_category 
FROM rbi_configurations;

-- Expected:
-- gff_table         | gff
-- pof_ranges        | risk_matrix
-- cof_ranges        | risk_matrix
-- inspection_intervals | inspection
```

---

## 3. API Integration

### Step 1: Install Dependencies

```bash
pip install fastapi pydantic supabase-py python-dotenv
```

### Step 2: Setup Environment Variables

```bash
# .env file
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

### Step 3: Create Supabase Client

```python
# api/database.py
from supabase import create_client, Client
import os

supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

async def save_rbi_assessment(assessment_data: dict):
    """Save RBI assessment to database"""
    result = supabase.table('rbi_assessments').insert(assessment_data).execute()
    return result.data[0]

async def save_damage_factors(df_list: list):
    """Save damage factor results"""
    result = supabase.table('damage_factor_results').insert(df_list).execute()
    return result.data

async def get_current_risk(equipment_id: str):
    """Get current risk status"""
    result = supabase.from_('vw_rbi_current_risk').select("*").eq('equipment_id', equipment_id).execute()
    return result.data[0] if result.data else None
```

### Step 4: Integrate with FastAPI Endpoint

```python
# api/rbi_endpoints.py (updated)
from api.database import save_rbi_assessment, save_damage_factors

@router.post("/assessment")
async def create_rbi_assessment(request: RBIAssessmentRequest):
    # ... calculation logic ...
    
    # Save to database
    assessment_data = {
        'id': str(assessment_id),
        'equipment_id': str(request.component.equipment_id),
        'assessment_date': assessment_date.isoformat(),
        'component_type': component_data['component_type'],
        'gff': result['pof']['gff'],
        'total_df': result['pof']['total_df'],
        'pof_per_year': result['pof']['pof_per_year'],
        'pof_category': result['risk']['pof_category'],
        'cof_financial': result['cof']['cof_financial'],
        'cof_category': result['risk']['cof_category'],
        'risk_matrix_position': result['risk_matrix_position'],
        'risk_level': result['risk']['risk_level'],
        'inspection_interval_years': interval_years,
        'next_inspection_date': next_inspection.isoformat(),
        'status': 'completed'
    }
    
    saved_assessment = await save_rbi_assessment(assessment_data)
    
    # Save damage factors
    df_records = []
    for mech in active_mechanisms_details:
        df_records.append({
            'assessment_id': str(assessment_id),
            'mechanism_type': mech['mechanism_type'],
            'is_active': True,
            'df_value': mech['df_value'],
            'input_data': mech['input_parameters'],
            'calculation_steps': mech.get('calculation_steps', [])
        })
    
    await save_damage_factors(df_records)
    
    return response
```

---

## 4. Usage Examples

### Example 1: Create New RBI Assessment

```python
# POST /api/rbi/assessment
{
    "component": {
        "equipment_id": "123e4567-e89b-12d3-a456-426614174000",
        "component_type": "pipe",
        "operating_pressure_psig": 800.0,
        "operating_temp_f": 600.0,
        "diameter_inches": 24.0,
        "fluid_type": "hydrocarbon",
        "fms_factor": 1.0
    },
    "damage_mechanisms": [
        {
            "mechanism_type": "thinning",
            "is_active": true,
            "input_parameters": {
                "df_value": 450.0,
                "age_since_inspection": 5.0,
                "corrosion_rate": 5.0
            }
        },
        {
            "mechanism_type": "external_corrosion",
            "is_active": true,
            "input_parameters": {
                "df_value": 120.0,
                "age_since_inspection": 5.0
            }
        }
    ],
    "assessment_date": "2026-09-27"
}
```

**Response:**
```json
{
    "assessment_id": "550e8400-e29b-41d4-a716-446655440000",
    "risk_matrix_position": "5D",
    "risk_level": "High",
    "pof_per_year": 0.2,
    "cof_financial": 2173625,
    "inspection_interval_years": 2,
    "next_inspection_date": "2028-09-27"
}
```

### Example 2: Query High-Risk Equipment

```sql
-- Get all high-risk equipment
SELECT 
    tag_no,
    description,
    risk_matrix_position,
    next_inspection_date,
    CASE 
        WHEN next_inspection_date < CURRENT_DATE THEN 'OVERDUE'
        ELSE 'SCHEDULED'
    END as status
FROM vw_rbi_high_risk_equipment
ORDER BY next_inspection_date;
```

### Example 3: Mechanism Analysis

```sql
-- Which mechanisms are most prevalent?
SELECT 
    mechanism_type,
    COUNT(*) as count,
    AVG(df_value) as avg_df
FROM damage_factor_results
WHERE is_active = true
GROUP BY mechanism_type
ORDER BY count DESC
LIMIT 10;
```

### Example 4: Risk Trending

```sql
-- Risk trend for specific equipment
SELECT 
    assessment_date,
    risk_matrix_position,
    pof_per_year,
    cof_financial,
    total_df
FROM rbi_assessments
WHERE equipment_id = '123e4567-e89b-12d3-a456-426614174000'
ORDER BY assessment_date DESC;
```

---

## 5. Frontend Integration (React/Next.js)

### Example: Risk Matrix Visualization

```typescript
// components/RiskMatrix.tsx
import { useQuery } from '@tanstack/react-query';

interface RiskMatrixData {
    equipment_positions: Array<{
        equipment_id: string;
        tag_no: string;
        risk_position: string; // e.g., "5D"
        pof_category: number;
        cof_category: string;
    }>;
}

export function RiskMatrix() {
    const { data } = useQuery<RiskMatrixData>({
        queryKey: ['risk-matrix'],
        queryFn: () => fetch('/api/rbi/risk-matrix').then(r => r.json())
    });
    
    // Group by position
    const grouped = data?.equipment_positions.reduce((acc, eq) => {
        acc[eq.risk_position] = (acc[eq.risk_position] || 0) + 1;
        return acc;
    }, {} as Record<string, number>);
    
    return (
        <div className="grid grid-cols-5 gap-1">
            {/* 5×5 grid */}
            {[5,4,3,2,1].map(pof => (
                ['A','B','C','D','E'].map(cof => {
                    const position = `${pof}${cof}`;
                    const count = grouped?.[position] || 0;
                    const riskColor = getRiskColor(pof, cof);
                    
                    return (
                        <div 
                            key={position}
                            className={`p-4 rounded ${riskColor}`}
                        >
                            <div className="text-xs">{position}</div>
                            <div className="text-2xl font-bold">{count}</div>
                        </div>
                    );
                })
            ))}
        </div>
    );
}

function getRiskColor(pof: number, cof: string): string {
    if (pof >= 4 || ['D','E'].includes(cof)) return 'bg-red-500';
    if (pof >= 3 || cof === 'C') return 'bg-orange-500';
    if (pof >= 2) return 'bg-yellow-500';
    return 'bg-green-500';
}
```

---

## 6. Testing

### Unit Tests

```python
# tests/test_rbi_database.py
import pytest
from api.database import save_rbi_assessment

@pytest.mark.asyncio
async def test_save_rbi_assessment():
    data = {
        'equipment_id': 'test-id',
        'component_type': 'pipe',
        'pof_per_year': 0.001,
        'risk_level': 'Medium'
    }
    
    result = await save_rbi_assessment(data)
    assert result['id'] is not None
    assert result['risk_level'] == 'Medium'
```

### Integration Tests

```bash
# Run full workflow test
python tests/test_integration.py

# Test sequence:
# 1. Create RBI assessment via API
# 2. Verify data in database
# 3. Query risk matrix
# 4. Update inspection history
```

---

## 7. Performance Optimization

### Indexes Created

```sql
-- Already in schema.sql:
CREATE INDEX idx_rbi_assessments_equipment ON rbi_assessments(equipment_id);
CREATE INDEX idx_rbi_assessments_risk ON rbi_assessments(risk_level);
CREATE INDEX idx_df_results_mechanism ON damage_factor_results(mechanism_type);
```

### Query Optimization Tips

1. **Use views** untuk common queries (current risk, high-risk equipment)
2. **JSONB indexing** untuk calculation_steps search
3. **Partition tables** by assessment_date untuk large datasets
4. **Materialized views** untuk complex aggregations

---

## 8. Backup & Maintenance

### Daily Backup

```bash
# Automated backup script
pg_dump -h host -U user -d dbname -t rbi_* > backup_$(date +%Y%m%d).sql
```

### Cleanup Old Assessments

```sql
-- Archive assessments older than 5 years
DELETE FROM rbi_assessments 
WHERE assessment_date < CURRENT_DATE - INTERVAL '5 years'
  AND status != 'approved';
```

---

## 9. Migration Checklist

- [ ] Run schema.sql in Supabase
- [ ] Verify all tables created
- [ ] Check default configurations loaded
- [ ] Test views return data
- [ ] Setup Supabase client in API
- [ ] Update FastAPI endpoints with database calls
- [ ] Test POST /api/rbi/assessment
- [ ] Test GET /api/rbi/equipment/{id}/assessments
- [ ] Test risk matrix endpoint
- [ ] Build React components
- [ ] Deploy to staging
- [ ] User acceptance testing
- [ ] Deploy to production

---

## 10. Next Steps

### Phase 2A: Complete API Implementation (2-3 days)
- [ ] Implement all database CRUD operations
- [ ] Add Supabase RLS policies
- [ ] Error handling & validation
- [ ] API documentation (OpenAPI/Swagger)

### Phase 2B: Frontend Development (4-5 days)
- [ ] Equipment selector component
- [ ] Assessment wizard (multi-step form)
- [ ] Risk matrix visualization
- [ ] Historical trending charts
- [ ] PDF report generation

### Phase 3: Advanced Features (3-4 days)
- [ ] What-if analysis
- [ ] Bulk facility assessment
- [ ] Automated email notifications
- [ ] Integration with AIMS Inspection data

---

**Document Version:** 1.0  
**Last Updated:** September 27, 2026  
**Status:** Ready for Implementation  
**Estimated Time:** Phase 1 complete, Phase 2-3: 10-14 days
