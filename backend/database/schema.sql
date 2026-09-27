-- ============================================================================
-- API 581 RBI Database Schema for Integra IMS (Supabase/PostgreSQL)
-- ============================================================================
-- Version: 1.0
-- Date: 2026-09-27
-- Purpose: Complete RBI assessment storage with all 20 damage mechanisms
-- ============================================================================

-- ============================================================================
-- 1. RBI ASSESSMENTS (Main table)
-- ============================================================================
CREATE TABLE IF NOT EXISTS rbi_assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Equipment reference
    equipment_id UUID NOT NULL REFERENCES equipment(id) ON DELETE CASCADE,
    
    -- Assessment metadata
    assessment_date DATE NOT NULL DEFAULT CURRENT_DATE,
    assessment_type VARCHAR(20) DEFAULT 'full', -- 'full', 'screening', 'update'
    assessed_by UUID REFERENCES auth.users(id),
    approved_by UUID REFERENCES auth.users(id),
    status VARCHAR(20) DEFAULT 'draft', -- 'draft', 'completed', 'approved'
    
    -- Component data (snapshot at assessment time)
    component_type VARCHAR(50) NOT NULL, -- 'pipe', 'vessel', 'heat_exchanger', 'tank', 'filter'
    operating_pressure_psig DECIMAL(10,2),
    design_pressure_psig DECIMAL(10,2),
    operating_temp_f DECIMAL(10,2),
    diameter_inches DECIMAL(10,2),
    wall_thickness_inches DECIMAL(10,4),
    material VARCHAR(100),
    fluid_type VARCHAR(50), -- 'hydrocarbon', 'water', 'steam', 'chemical'
    phase VARCHAR(20), -- 'liquid', 'gas', 'two_phase'
    
    -- Management Systems Factor
    fms_factor DECIMAL(5,2) DEFAULT 1.0,
    
    -- PoF Results
    gff DECIMAL(12,8), -- Generic Failure Frequency
    total_df DECIMAL(12,2), -- Sum of all active damage factors
    pof_per_year DECIMAL(12,8), -- Probability of Failure per year
    pof_category INTEGER CHECK (pof_category BETWEEN 1 AND 5),
    
    -- CoF Results
    cof_financial DECIMAL(15,2), -- Financial consequence ($)
    cof_ca_cmd DECIMAL(12,2), -- Component damage area (ft²)
    cof_ca_flam DECIMAL(12,2), -- Flammable area (ft²)
    cof_ca_tox DECIMAL(12,2), -- Toxic area (ft²)
    cof_ca_env DECIMAL(12,2), -- Environmental area (ft²)
    cof_category VARCHAR(1) CHECK (cof_category IN ('A', 'B', 'C', 'D', 'E')),
    
    -- Risk Matrix
    risk_score DECIMAL(15,2), -- PoF × CoF
    risk_matrix_position VARCHAR(2), -- e.g., '5D', '3C'
    risk_level VARCHAR(20), -- 'High', 'Medium-High', 'Medium', 'Low'
    
    -- Inspection Recommendations
    inspection_interval_years INTEGER,
    inspection_effectiveness VARCHAR(1), -- 'A', 'B', 'C', 'D', 'E'
    inspection_priority VARCHAR(20), -- 'Critical', 'High', 'Medium', 'Low'
    next_inspection_date DATE,
    
    -- Audit trail
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Indexes for performance
    CONSTRAINT rbi_assessment_equipment_date UNIQUE (equipment_id, assessment_date)
);

CREATE INDEX idx_rbi_assessments_equipment ON rbi_assessments(equipment_id);
CREATE INDEX idx_rbi_assessments_date ON rbi_assessments(assessment_date);
CREATE INDEX idx_rbi_assessments_risk ON rbi_assessments(risk_level);
CREATE INDEX idx_rbi_assessments_next_inspection ON rbi_assessments(next_inspection_date);

-- ============================================================================
-- 2. DAMAGE FACTOR RESULTS (Individual mechanism results)
-- ============================================================================
CREATE TABLE IF NOT EXISTS damage_factor_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Parent assessment
    assessment_id UUID NOT NULL REFERENCES rbi_assessments(id) ON DELETE CASCADE,
    
    -- Mechanism identification
    mechanism_type VARCHAR(50) NOT NULL, -- 'thinning', 'external_corrosion', 'cui', 'caustic_scc', etc.
    mechanism_category VARCHAR(20), -- 'corrosion', 'scc', 'high_temp', 'low_temp', 'embrittlement', 'fatigue'
    
    -- Results
    is_active BOOLEAN DEFAULT true, -- Is this mechanism applicable?
    df_value DECIMAL(12,2), -- Calculated damage factor
    susceptibility VARCHAR(20), -- 'high', 'medium', 'low', 'none'
    severity_index INTEGER, -- 1000, 100, 10, 0
    base_df DECIMAL(12,2),
    
    -- Inspection data used
    age_since_inspection DECIMAL(10,2), -- years
    inspection_effectiveness VARCHAR(1), -- 'A', 'B', 'C', 'D', 'E'
    num_inspections INTEGER,
    
    -- Detailed calculation data (JSONB for flexibility)
    input_data JSONB, -- All input parameters
    calculation_steps JSONB, -- Step-by-step calculation details
    
    -- Key factors (for quick filtering/analysis)
    corrosion_rate DECIMAL(10,4), -- For thinning/external
    temperature_f DECIMAL(10,2), -- For temperature-dependent mechanisms
    pressure_psia DECIMAL(10,2), -- For pressure-dependent mechanisms
    material_grade VARCHAR(50), -- For material-dependent mechanisms
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT df_assessment_mechanism UNIQUE (assessment_id, mechanism_type)
);

CREATE INDEX idx_df_results_assessment ON damage_factor_results(assessment_id);
CREATE INDEX idx_df_results_mechanism ON damage_factor_results(mechanism_type);
CREATE INDEX idx_df_results_active ON damage_factor_results(is_active) WHERE is_active = true;
CREATE INDEX idx_df_results_susceptibility ON damage_factor_results(susceptibility);

-- GIN index for JSONB queries
CREATE INDEX idx_df_results_calculation_steps ON damage_factor_results USING GIN(calculation_steps);

-- ============================================================================
-- 3. INSPECTION HISTORY (Track actual inspections performed)
-- ============================================================================
CREATE TABLE IF NOT EXISTS rbi_inspection_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Equipment reference
    equipment_id UUID NOT NULL REFERENCES equipment(id) ON DELETE CASCADE,
    
    -- Inspection details
    inspection_date DATE NOT NULL,
    inspection_type VARCHAR(50), -- 'visual', 'ultrasonic', 'radiographic', 'magnetic_particle', etc.
    inspection_effectiveness VARCHAR(1), -- 'A', 'B', 'C', 'D', 'E'
    
    -- Findings
    findings TEXT,
    defects_found BOOLEAN DEFAULT false,
    defect_type VARCHAR(50), -- 'crack', 'corrosion', 'erosion', 'deformation', etc.
    defect_severity VARCHAR(20), -- 'minor', 'moderate', 'severe', 'critical'
    
    -- Measurements (for thickness monitoring)
    measured_thickness_inches DECIMAL(10,4),
    min_measured_thickness_inches DECIMAL(10,4),
    measurement_location VARCHAR(100),
    
    -- Actions taken
    repair_required BOOLEAN DEFAULT false,
    repair_date DATE,
    repair_description TEXT,
    
    -- Performed by
    inspector_name VARCHAR(100),
    inspector_certification VARCHAR(50),
    inspected_by UUID REFERENCES auth.users(id),
    
    -- Related assessment (if triggered by RBI recommendation)
    rbi_assessment_id UUID REFERENCES rbi_assessments(id),
    
    -- Audit trail
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_inspection_history_equipment ON rbi_inspection_history(equipment_id);
CREATE INDEX idx_inspection_history_date ON rbi_inspection_history(inspection_date);
CREATE INDEX idx_inspection_history_findings ON rbi_inspection_history(defects_found);

-- ============================================================================
-- 4. RBI CONFIGURATIONS (System-wide settings)
-- ============================================================================
CREATE TABLE IF NOT EXISTS rbi_configurations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Configuration key
    config_key VARCHAR(50) UNIQUE NOT NULL,
    config_category VARCHAR(30), -- 'gff', 'inspection', 'risk_matrix', 'general'
    
    -- Configuration value (JSONB for flexibility)
    config_value JSONB NOT NULL,
    
    -- Metadata
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    
    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by UUID REFERENCES auth.users(id)
);

-- Insert default configurations
INSERT INTO rbi_configurations (config_key, config_category, config_value, description) VALUES
('gff_table', 'gff', '{
    "pipe": 0.000156,
    "vessel": 0.000306,
    "heat_exchanger": 0.000336,
    "tank": 0.00000691,
    "filter": 0.0015
}'::jsonb, 'Generic Failure Frequencies (Table 3.1)'),

('pof_ranges', 'risk_matrix', '{
    "1": {"min": 0, "max": 0.000001},
    "2": {"min": 0.000001, "max": 0.00001},
    "3": {"min": 0.00001, "max": 0.0001},
    "4": {"min": 0.0001, "max": 0.001},
    "5": {"min": 0.001, "max": 999999}
}'::jsonb, 'PoF Category Ranges'),

('cof_ranges', 'risk_matrix', '{
    "A": {"min": 0, "max": 10000},
    "B": {"min": 10000, "max": 100000},
    "C": {"min": 100000, "max": 1000000},
    "D": {"min": 1000000, "max": 10000000},
    "E": {"min": 10000000, "max": 999999999}
}'::jsonb, 'CoF Category Ranges'),

('inspection_intervals', 'inspection', '{
    "High": {"years": 2, "effectiveness": "A", "priority": "Critical"},
    "Medium-High": {"years": 4, "effectiveness": "B", "priority": "High"},
    "Medium": {"years": 8, "effectiveness": "C", "priority": "Medium"},
    "Low": {"years": 16, "effectiveness": "D", "priority": "Low"}
}'::jsonb, 'Inspection Interval Recommendations');

-- ============================================================================
-- 5. EXTEND EQUIPMENT TABLE (if not already extended)
-- ============================================================================
-- Add RBI-specific columns to existing equipment table
ALTER TABLE equipment ADD COLUMN IF NOT EXISTS rbi_component_type VARCHAR(50);
ALTER TABLE equipment ADD COLUMN IF NOT EXISTS rbi_fms_factor DECIMAL(5,2) DEFAULT 1.0;
ALTER TABLE equipment ADD COLUMN IF NOT EXISTS rbi_last_assessment_date DATE;
ALTER TABLE equipment ADD COLUMN IF NOT EXISTS rbi_next_inspection_date DATE;
ALTER TABLE equipment ADD COLUMN IF NOT EXISTS rbi_current_risk_level VARCHAR(20);
ALTER TABLE equipment ADD COLUMN IF NOT EXISTS rbi_current_risk_position VARCHAR(2);

-- ============================================================================
-- 6. VIEWS FOR REPORTING
-- ============================================================================

-- View: Current Risk Status (Latest assessment per equipment)
CREATE OR REPLACE VIEW vw_rbi_current_risk AS
SELECT DISTINCT ON (e.id)
    e.id as equipment_id,
    e.tag_no,
    e.description,
    a.assessment_date,
    a.risk_level,
    a.risk_matrix_position,
    a.pof_per_year,
    a.cof_financial,
    a.inspection_interval_years,
    a.next_inspection_date,
    a.inspection_priority,
    -- Active damage mechanisms count
    (SELECT COUNT(*) FROM damage_factor_results dfr 
     WHERE dfr.assessment_id = a.id AND dfr.is_active = true) as active_mechanisms,
    -- Total DF
    a.total_df
FROM equipment e
LEFT JOIN rbi_assessments a ON a.equipment_id = e.id AND a.status = 'approved'
ORDER BY e.id, a.assessment_date DESC;

-- View: High Risk Equipment (Risk level High or Medium-High)
CREATE OR REPLACE VIEW vw_rbi_high_risk_equipment AS
SELECT 
    equipment_id,
    tag_no,
    description,
    risk_level,
    risk_matrix_position,
    next_inspection_date,
    inspection_priority,
    CASE 
        WHEN next_inspection_date < CURRENT_DATE THEN 'OVERDUE'
        WHEN next_inspection_date < CURRENT_DATE + INTERVAL '30 days' THEN 'DUE_SOON'
        ELSE 'SCHEDULED'
    END as inspection_status
FROM vw_rbi_current_risk
WHERE risk_level IN ('High', 'Medium-High')
ORDER BY 
    CASE risk_level 
        WHEN 'High' THEN 1 
        WHEN 'Medium-High' THEN 2 
    END,
    next_inspection_date;

-- View: Damage Mechanism Summary
CREATE OR REPLACE VIEW vw_rbi_mechanism_summary AS
SELECT 
    dfr.mechanism_type,
    dfr.mechanism_category,
    COUNT(*) as equipment_count,
    AVG(dfr.df_value) as avg_df,
    MAX(dfr.df_value) as max_df,
    COUNT(*) FILTER (WHERE dfr.susceptibility = 'high') as high_susceptibility_count,
    COUNT(*) FILTER (WHERE dfr.susceptibility = 'medium') as medium_susceptibility_count
FROM damage_factor_results dfr
INNER JOIN rbi_assessments a ON a.id = dfr.assessment_id
WHERE dfr.is_active = true 
  AND a.status = 'approved'
  AND a.assessment_date = (
      SELECT MAX(assessment_date) 
      FROM rbi_assessments 
      WHERE equipment_id = a.equipment_id
  )
GROUP BY dfr.mechanism_type, dfr.mechanism_category
ORDER BY equipment_count DESC;

-- ============================================================================
-- 7. FUNCTIONS
-- ============================================================================

-- Function: Calculate next inspection date
CREATE OR REPLACE FUNCTION calculate_next_inspection_date(
    assessment_date DATE,
    interval_years INTEGER
) RETURNS DATE AS $$
BEGIN
    RETURN assessment_date + (interval_years || ' years')::INTERVAL;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function: Update equipment RBI fields after new assessment
CREATE OR REPLACE FUNCTION update_equipment_rbi_fields()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'approved' THEN
        UPDATE equipment
        SET 
            rbi_last_assessment_date = NEW.assessment_date,
            rbi_next_inspection_date = NEW.next_inspection_date,
            rbi_current_risk_level = NEW.risk_level,
            rbi_current_risk_position = NEW.risk_matrix_position
        WHERE id = NEW.equipment_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger: Auto-update equipment RBI fields
CREATE TRIGGER trg_update_equipment_rbi
    AFTER INSERT OR UPDATE ON rbi_assessments
    FOR EACH ROW
    EXECUTE FUNCTION update_equipment_rbi_fields();

-- Function: Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
CREATE TRIGGER trg_rbi_assessments_updated_at
    BEFORE UPDATE ON rbi_assessments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_inspection_history_updated_at
    BEFORE UPDATE ON rbi_inspection_history
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 8. ROW LEVEL SECURITY (RLS) - Optional, enable if using Supabase Auth
-- ============================================================================

-- Enable RLS
ALTER TABLE rbi_assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE damage_factor_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE rbi_inspection_history ENABLE ROW LEVEL SECURITY;

-- Policies (example - adjust based on your auth setup)
CREATE POLICY "Users can view all RBI assessments"
    ON rbi_assessments FOR SELECT
    USING (true);

CREATE POLICY "Users can insert RBI assessments"
    ON rbi_assessments FOR INSERT
    WITH CHECK (auth.uid() IS NOT NULL);

CREATE POLICY "Users can update their own assessments"
    ON rbi_assessments FOR UPDATE
    USING (assessed_by = auth.uid() OR auth.uid() IN (SELECT id FROM auth.users WHERE raw_user_meta_data->>'role' = 'admin'));

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================

-- Comments for documentation
COMMENT ON TABLE rbi_assessments IS 'Main RBI assessment records with PoF, CoF, and risk matrix results';
COMMENT ON TABLE damage_factor_results IS 'Individual damage factor calculations for each active mechanism';
COMMENT ON TABLE rbi_inspection_history IS 'Historical record of all inspections performed';
COMMENT ON TABLE rbi_configurations IS 'System-wide RBI configuration parameters (GFF, risk matrix ranges, etc.)';
COMMENT ON VIEW vw_rbi_current_risk IS 'Latest risk status for each equipment';
COMMENT ON VIEW vw_rbi_high_risk_equipment IS 'High-risk equipment requiring priority inspection';
