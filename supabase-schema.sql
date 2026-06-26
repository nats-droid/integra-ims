-- =============================================================
-- INTEGRA — Full Database Schema
-- Product: Inspection & Asset Integrity Management Platform
-- Based on PRD Section 4 (Data Model)
-- =============================================================

-- 0. EXTENSIONS
create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";

-- =============================================================
-- 4.2 MASTER DATA
-- =============================================================

-- Companies (tenants)
create table companies (
  id uuid primary key default uuid_generate_v4(),
  name text not null,
  plan_tier text not null default 'trial' check (plan_tier in ('trial', 'starter', 'pro')),
  max_equipment int,
  max_users int,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- App users (extends Supabase Auth)
create table app_users (
  id uuid primary key default uuid_generate_v4(),
  auth_user_id uuid references auth.users not null unique,
  company_id uuid references companies(id) on delete cascade,
  role text not null check (role in ('inspector', 'engineer', 'supervisor', 'super_admin')),
  full_name text not null,
  phone text,
  avatar_url text,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  -- Super Admin has company_id = null
  constraint super_admin_no_company check (
    (role = 'super_admin' and company_id is null) or
    (role != 'super_admin' and company_id is not null)
  )
);

-- Plant areas (hierarchical: Area → Unit, self-referencing)
create table plant_areas (
  id uuid primary key default uuid_generate_v4(),
  company_id uuid references companies(id) on delete cascade not null,
  name text not null,
  parent_area_id uuid references plant_areas(id) on delete set null,
  description text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(company_id, name, parent_area_id)
);

-- Equipment master
create table equipment (
  id uuid primary key default uuid_generate_v4(),
  company_id uuid references companies(id) on delete cascade not null,
  tag text not null,
  type text not null check (type in ('piping', 'vessel', 'tank', 'heater', 'pump', 'compressor', 'valve', 'psv', 'other')),
  fluid_service text,
  material text,
  area_id uuid references plant_areas(id) on delete set null,
  design_temp_min numeric,
  design_temp_max numeric,
  design_pressure numeric,
  pwht boolean default false,
  risk_category text check (risk_category in ('low', 'medium', 'high', 'critical')),
  compliance_status text default 'compliant' check (compliance_status in ('compliant', 'non-compliant', 'pending')),
  size_or_dimension text,
  insulation_type text,
  installation_date date,
  manufacturer text,
  serial_number text,
  notes text,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(company_id, tag)
);

-- Circuits (Corrosion Loop grouping per API 570)
create table circuits (
  id uuid primary key default uuid_generate_v4(),
  company_id uuid references companies(id) on delete cascade not null,
  equipment_id uuid references equipment(id) on delete cascade not null,
  name text not null,
  description text,
  governing_cr_cache numeric,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(company_id, equipment_id, name)
);

-- CML Points (Thickness Measurement Locations)
create table cml_points (
  id uuid primary key default uuid_generate_v4(),
  company_id uuid references companies(id) on delete cascade not null,
  circuit_id uuid references circuits(id) on delete cascade,
  equipment_id uuid references equipment(id) on delete cascade not null,
  location_label text not null,
  nominal_thickness numeric not null,
  t_min numeric, -- calculated: nominal_thickness * retirement_factor
  retirement_factor numeric default 0.875,
  cml_type text default 'ut' check (cml_type in ('ut', 'rt', 'manual')),
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(company_id, equipment_id, location_label)
);

-- Checklist templates (global, per equipment type)
create table checklist_templates (
  id uuid primary key default uuid_generate_v4(),
  equipment_type text not null check (equipment_type in ('piping', 'vessel', 'tank', 'heater', 'pump', 'compressor', 'valve', 'other')),
  section text not null,
  item_code text not null,
  item_description text not null,
  item_type text default 'rating' check (item_type in ('rating', 'yes_no', 'text', 'photo')),
  display_order int not null default 0,
  is_active boolean not null default true,
  unique(equipment_type, item_code)
);

-- Inspection interval rules (default auto-suggest)
create table inspection_interval_rules (
  id uuid primary key default uuid_generate_v4(),
  equipment_type text not null,
  inspection_type text not null check (inspection_type in ('external', 'internal')),
  risk_category text not null check (risk_category in ('low', 'medium', 'high', 'critical')),
  interval_years numeric not null,
  unique(equipment_type, inspection_type, risk_category)
);

-- DM Knowledge Base (API 571 — global, same for all tenants)
create table dm_knowledge_base (
  id uuid primary key default uuid_generate_v4(),
  dm_code text not null unique,
  dm_name text not null,
  category text,
  materials text[] default '{}',
  fluids text[] default '{}',
  temp_min numeric,
  temp_max numeric,
  pwht_flag text check (pwht_flag in ('required', 'not_required', 'any')),
  recommended_nde text[] default '{}',
  description text,
  created_at timestamptz not null default now()
);

-- =============================================================
-- 4.3 TRANSACTIONAL DATA
-- =============================================================

-- Inspection events (header per visit/submission)
-- NOTE: FK to inspection_campaigns is added via ALTER after that table is created
create table inspection_events (
  id uuid primary key default uuid_generate_v4(),
  company_id uuid references companies(id) on delete cascade not null,
  equipment_id uuid references equipment(id) on delete cascade not null,
  campaign_id uuid,
  inspector_id uuid references app_users(id) on delete set null,
  inspection_type text not null check (inspection_type in ('external', 'internal', 'visual', 'cui', 'utm', 'other')),
  event_date date not null default current_date,
  status text not null default 'draft' check (status in ('draft', 'submitted', 'approved', 'rejected')),
  notes text,
  weather_condition text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Checklist answers (1 row per item per inspection)
create table checklist_answers (
  id uuid primary key default uuid_generate_v4(),
  inspection_event_id uuid references inspection_events(id) on delete cascade not null,
  item_code text not null,
  answer_rating int check (answer_rating between 1 and 5),
  answer_boolean boolean,
  answer_text text,
  notes text,
  created_at timestamptz not null default now()
);

-- Thickness readings (TML / CML)
create table thickness_readings (
  id uuid primary key default uuid_generate_v4(),
  company_id uuid references companies(id) on delete cascade not null,
  cml_point_id uuid references cml_points(id) on delete cascade not null,
  inspection_event_id uuid references inspection_events(id) on delete set null,
  reading_date date not null default current_date,
  reading_mm numeric not null,
  is_representative boolean default true,
  notes text,
  created_at timestamptz not null default now(),
  unique(company_id, cml_point_id, reading_date)
);

-- Maintenance log (chronological findings/repairs)
create table maintenance_log (
  id uuid primary key default uuid_generate_v4(),
  company_id uuid references companies(id) on delete cascade not null,
  equipment_id uuid references equipment(id) on delete cascade not null,
  related_inspection_event_id uuid references inspection_events(id) on delete set null,
  log_date date not null default current_date,
  description text not null,
  log_type text default 'finding' check (log_type in ('finding', 'repair', 'replacement', 'other')),
  severity text check (severity in ('minor', 'major', 'critical')),
  created_at timestamptz not null default now()
);

-- Photos (stored in Supabase Storage)
create table photos (
  id uuid primary key default uuid_generate_v4(),
  company_id uuid references companies(id) on delete cascade not null,
  storage_path text not null,
  caption text,
  related_level text not null check (related_level in ('event', 'checklist_item', 'cml_point', 'maintenance_log')),
  related_id uuid not null,
  is_critical boolean not null default false,
  file_size int,
  mime_type text,
  created_at timestamptz not null default now()
);

-- =============================================================
-- 4.4 PLANNING & RESOURCING
-- =============================================================

-- Inspection plans (due date comparison & approval)
create table inspection_plans (
  id uuid primary key default uuid_generate_v4(),
  company_id uuid references companies(id) on delete cascade not null,
  equipment_id uuid references equipment(id) on delete cascade not null,
  inspection_type text not null check (inspection_type in ('external', 'internal')),
  remaining_life_date date,
  rbi_date_manual date,
  disnaker_date date,
  final_due_date date,
  approval_status text not null default 'pending' check (approval_status in ('pending', 'approved', 'rejected', 'revised')),
  approved_by uuid references app_users(id) on delete set null,
  approved_at timestamptz,
  approval_comment text,
  interval_override_years numeric,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(company_id, equipment_id, inspection_type)
);

-- Constraint: approval_comment wajib diisi saat status rejected atau revised
alter table inspection_plans
  add constraint approval_comment_required
  check (approval_status not in ('rejected', 'revised')
         or (approval_comment is not null and approval_comment != ''));

-- Plan assignments (many-to-many: plan → inspectors)
create table plan_assignments (
  id uuid primary key default uuid_generate_v4(),
  plan_id uuid references inspection_plans(id) on delete cascade not null,
  inspector_id uuid references app_users(id) on delete cascade not null,
  role_in_plan text default 'inspector' check (role_in_plan in ('lead', 'assistant')),
  unique(plan_id, inspector_id)
);

-- Inspection campaigns (thematic)
create table inspection_campaigns (
  id uuid primary key default uuid_generate_v4(),
  company_id uuid references companies(id) on delete cascade not null,
  name text not null,
  description text,
  campaign_type text check (campaign_type in ('cui', 'small_bore', 'turn_around', 'general', 'other')),
  start_date date not null,
  end_date date,
  target_count int,
  selection_criteria jsonb,
  checklist_mode text default 'full' check (checklist_mode in ('full', 'simplified', 'custom')),
  status text not null default 'active' check (status in ('active', 'completed', 'cancelled')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Campaign-equipment mapping
create table campaign_equipment (
  id uuid primary key default uuid_generate_v4(),
  campaign_id uuid references inspection_campaigns(id) on delete cascade not null,
  equipment_id uuid references equipment(id) on delete cascade not null,
  selection_status text default 'auto' check (selection_status in ('auto', 'manual_add', 'manual_exclude')),
  inspection_event_id uuid references inspection_events(id) on delete set null,
  unique(campaign_id, equipment_id)
);

-- Add FK from inspection_events to inspection_campaigns (forward reference resolved)
alter table inspection_events
  add constraint fk_inspection_events_campaign
  foreign key (campaign_id) references inspection_campaigns(id)
  on delete set null;

-- =============================================================
-- 4.5 AUDIT & NOTIFICATIONS
-- =============================================================

-- Audit log
create table audit_log (
  id uuid primary key default uuid_generate_v4(),
  company_id uuid references companies(id) on delete cascade,
  user_id uuid references app_users(id) on delete set null,
  table_name text not null,
  record_id uuid,
  field_name text,
  old_value text,
  new_value text,
  action text not null check (action in ('create', 'update', 'delete', 'approve', 'reject', 'login', 'impersonate')),
  ip_address text,
  created_at timestamptz not null default now()
);

-- Notifications (in-app)
create table notifications (
  id uuid primary key default uuid_generate_v4(),
  company_id uuid references companies(id) on delete cascade,
  user_id uuid references app_users(id) on delete cascade not null,
  type text not null check (type in ('due_date_soon', 'overdue', 'approval_required', 'approval_result', 'campaign', 'system')),
  related_id uuid,
  title text not null,
  message text,
  is_read boolean not null default false,
  created_at timestamptz not null default now()
);

-- =============================================================
-- 4.6 ANALYTICS RESULTS TABLES (written by FastAPI)
-- =============================================================

-- Remaining Life predictions
create table rl_predictions (
  id uuid primary key default uuid_generate_v4(),
  company_id uuid references companies(id) on delete cascade not null,
  cml_point_id uuid references cml_points(id) on delete cascade not null,
  predicted_rl_years numeric,
  confidence_low numeric,
  confidence_high numeric,
  model_version text,
  computed_at timestamptz not null default now(),
  unique(company_id, cml_point_id, computed_at)
);

-- Corrosion anomalies
create table corrosion_anomalies (
  id uuid primary key default uuid_generate_v4(),
  company_id uuid references companies(id) on delete cascade not null,
  cml_point_id uuid references cml_points(id) on delete cascade not null,
  anomaly_score numeric,
  description text,
  detected_at timestamptz not null default now()
);

-- Fleet risk snapshots
create table fleet_risk_snapshots (
  id uuid primary key default uuid_generate_v4(),
  company_id uuid references companies(id) on delete cascade not null,
  area_id uuid references plant_areas(id) on delete cascade,
  risk_summary jsonb,
  computed_at timestamptz not null default now()
);

-- DM Screener validation results
create table dm_validation_results (
  id uuid primary key default uuid_generate_v4(),
  company_id uuid references companies(id) on delete cascade not null,
  equipment_id uuid references equipment(id) on delete cascade not null,
  predicted_dm_codes text[] default '{}',
  actual_finding_dm_codes text[] default '{}',
  match_score numeric,
  computed_at timestamptz not null default now(),
  unique(company_id, equipment_id, computed_at)
);

-- =============================================================
-- 4.7 SUBSCRIPTION/BILLING PLACEHOLDER
-- Already included: companies.plan_tier, companies.max_equipment, companies.max_users

-- =============================================================
-- 4.9 AI CONFIG (BYOK — Bring Your Own Key)
-- =============================================================

create table company_ai_config (
  id uuid primary key default uuid_generate_v4(),
  company_id uuid references companies(id) on delete cascade not null unique,
  llm_provider text default 'openai' check (llm_provider in ('openai', 'anthropic', 'google')),
  api_key_encrypted text,
  is_enabled boolean not null default false,
  updated_at timestamptz not null default now()
);

-- Encryption is done at application level (FastAPI + Fernet, see backend/app/api/ai_config.py)
-- API key stored here is ALREADY encrypted before reaching the database
-- RLS blocks direct write from frontend (select-only policy)

-- Constraint: api_key wajib diisi kalau is_enabled = true
alter table company_ai_config
  add constraint api_key_required_if_enabled
  check (not is_enabled or (api_key_encrypted is not null and api_key_encrypted != ''));

-- =============================================================
-- INDEXES
-- =============================================================

-- Performance indexes for multi-tenant queries
create index idx_app_users_auth on app_users(auth_user_id);
create index idx_app_users_company on app_users(company_id);
create index idx_equipment_company on equipment(company_id);
create index idx_equipment_area on equipment(area_id);
create index idx_equipment_type on equipment(company_id, type);
create index idx_circuits_equipment on circuits(equipment_id);
create index idx_cml_points_circuit on cml_points(circuit_id);
create index idx_cml_points_equipment on cml_points(equipment_id);
create index idx_inspection_events_equipment on inspection_events(equipment_id);
create index idx_inspection_events_campaign on inspection_events(campaign_id);
create index idx_inspection_events_inspector on inspection_events(inspector_id);
create index idx_inspection_events_company on inspection_events(company_id);
create index idx_thickness_readings_cml on thickness_readings(cml_point_id);
create index idx_thickness_readings_company on thickness_readings(company_id);
create index idx_thickness_readings_date on thickness_readings(reading_date);
create index idx_checklist_answers_event on checklist_answers(inspection_event_id);
create index idx_inspection_plans_equipment on inspection_plans(equipment_id);
create index idx_inspection_plans_company on inspection_plans(company_id);
create index idx_inspection_plans_approval on inspection_plans(approval_status);
create index idx_plan_assignments_plan on plan_assignments(plan_id);
create index idx_plan_assignments_inspector on plan_assignments(inspector_id);
create index idx_campaign_equipment_campaign on campaign_equipment(campaign_id);
create index idx_maintenance_log_equipment on maintenance_log(equipment_id);
create index idx_photos_related on photos(related_level, related_id);
create index idx_audit_log_company on audit_log(company_id);
create index idx_audit_log_table on audit_log(table_name, record_id);
create index idx_notifications_user on notifications(user_id, is_read);
create index idx_rl_predictions_cml on rl_predictions(cml_point_id);
create index idx_corrosion_anomalies_cml on corrosion_anomalies(cml_point_id);

-- =============================================================
-- UPDATED AT TRIGGER (auto-set updated_at)
-- =============================================================

create or replace function set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

-- Apply to tables with updated_at
create trigger trg_companies_updated_at before update on companies
  for each row execute function set_updated_at();
create trigger trg_app_users_updated_at before update on app_users
  for each row execute function set_updated_at();
create trigger trg_plant_areas_updated_at before update on plant_areas
  for each row execute function set_updated_at();
create trigger trg_equipment_updated_at before update on equipment
  for each row execute function set_updated_at();
create trigger trg_circuits_updated_at before update on circuits
  for each row execute function set_updated_at();
create trigger trg_cml_points_updated_at before update on cml_points
  for each row execute function set_updated_at();
create trigger trg_inspection_events_updated_at before update on inspection_events
  for each row execute function set_updated_at();
create trigger trg_inspection_plans_updated_at before update on inspection_plans
  for each row execute function set_updated_at();
create trigger trg_inspection_campaigns_updated_at before update on inspection_campaigns
  for each row execute function set_updated_at();
create trigger trg_company_ai_config_updated_at before update on company_ai_config
  for each row execute function set_updated_at();
