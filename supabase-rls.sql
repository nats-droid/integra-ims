-- =============================================================
-- INTEGRA — Row Level Security (RLS) Policies
-- Based on PRD Section 3.1, 3.3, 3.4
-- =============================================================

-- Enable RLS on all tables
do $$
declare
  tbl text;
begin
  for tbl in
    select tablename from pg_tables
    where schemaname = 'public' and tablename not in ('companies', 'checklist_templates', 'inspection_interval_rules', 'dm_knowledge_base')
  loop
    execute format('alter table %I enable row level security;', tbl);
  end loop;
end $$;

-- Enable RLS on global-reference tables too (with different policies)
alter table companies enable row level security;
alter table checklist_templates enable row level security;
alter table inspection_interval_rules enable row level security;
alter table dm_knowledge_base enable row level security;

-- =============================================================
-- HELPER FUNCTION: Get current user's company_id and role
-- =============================================================

create or replace function get_user_company_id()
returns uuid
language sql stable security definer
as $$
  select company_id from app_users where auth_user_id = auth.uid();
$$;

create or replace function get_user_role()
returns text
language sql stable security definer
as $$
  select role from app_users where auth_user_id = auth.uid();
$$;

create or replace function is_super_admin()
returns boolean
language sql stable security definer
as $$
  select exists (
    select 1 from app_users
    where auth_user_id = auth.uid() and role = 'super_admin'
  );
$$;

-- =============================================================
-- POLICY TEMPLATE: tenant-isolated tables (most tables)
-- Users can only see rows with their company_id,
-- Super Admins can see everything
-- =============================================================

-- Apply to: plant_areas, equipment, circuits, cml_points,
-- inspection_events, checklist_answers, thickness_readings,
-- maintenance_log, photos, inspection_plans, plan_assignments,
-- inspection_campaigns, campaign_equipment, audit_log,
-- notifications, rl_predictions, corrosion_anomalies,
-- fleet_risk_snapshots, dm_validation_results, company_ai_config

-- 1. Companies (tenants)
create policy "Companies: select own or super_admin"
  on companies for select
  using (
    id = get_user_company_id()
    or is_super_admin()
  );

create policy "Companies: super_admin can insert"
  on companies for insert
  with check (is_super_admin());

create policy "Companies: super_admin can update"
  on companies for update
  using (is_super_admin());

create policy "Companies: super_admin can delete"
  on companies for delete
  using (is_super_admin());

-- 2. App Users
create policy "App users: select own company or super_admin"
  on app_users for select
  using (
    company_id = get_user_company_id()
    or auth_user_id = auth.uid()
    or is_super_admin()
  );

create policy "App users: insert own"
  on app_users for insert
  with check (auth_user_id = auth.uid());

create policy "App users: update own or super_admin"
  on app_users for update
  using (
    auth_user_id = auth.uid()
    or is_super_admin()
  );

-- 3. Generic tenant-isolated tables
-- Plant Areas
create policy "Plant areas: tenant isolation"
  on plant_areas for all
  using (
    company_id = get_user_company_id()
    or is_super_admin()
  );

-- Equipment
create policy "Equipment: tenant isolation"
  on equipment for all
  using (
    company_id = get_user_company_id()
    or is_super_admin()
  );

-- Circuits
create policy "Circuits: tenant isolation"
  on circuits for all
  using (
    company_id = get_user_company_id()
    or is_super_admin()
  );

-- CML Points
create policy "CML points: tenant isolation"
  on cml_points for all
  using (
    company_id = get_user_company_id()
    or is_super_admin()
  );

-- Inspection Events
create policy "Inspection events: tenant isolation"
  on inspection_events for all
  using (
    company_id = get_user_company_id()
    or is_super_admin()
  );

-- Checklist Answers (no direct company_id, inherited via event)
create policy "Checklist answers: tenant isolation"
  on checklist_answers for all
  using (
    exists (
      select 1 from inspection_events ie
      where ie.id = checklist_answers.inspection_event_id
      and (ie.company_id = get_user_company_id() or is_super_admin())
    )
  );

-- Thickness Readings
create policy "Thickness readings: tenant isolation"
  on thickness_readings for all
  using (
    company_id = get_user_company_id()
    or is_super_admin()
  );

-- Maintenance Log
create policy "Maintenance log: tenant isolation"
  on maintenance_log for all
  using (
    company_id = get_user_company_id()
    or is_super_admin()
  );

-- Photos
create policy "Photos: tenant isolation"
  on photos for all
  using (
    company_id = get_user_company_id()
    or is_super_admin()
  );

-- Inspection Plans
create policy "Inspection plans: tenant isolation"
  on inspection_plans for all
  using (
    company_id = get_user_company_id()
    or is_super_admin()
  );

-- Plan Assignments (no direct company_id)
create policy "Plan assignments: tenant isolation"
  on plan_assignments for all
  using (
    exists (
      select 1 from inspection_plans ip
      where ip.id = plan_assignments.plan_id
      and (ip.company_id = get_user_company_id() or is_super_admin())
    )
  );

-- Inspection Campaigns
create policy "Inspection campaigns: tenant isolation"
  on inspection_campaigns for all
  using (
    company_id = get_user_company_id()
    or is_super_admin()
  );

-- Campaign Equipment
create policy "Campaign equipment: tenant isolation"
  on campaign_equipment for all
  using (
    exists (
      select 1 from inspection_campaigns ic
      where ic.id = campaign_equipment.campaign_id
      and (ic.company_id = get_user_company_id() or is_super_admin())
    )
  );

-- Audit Log
create policy "Audit log: tenant isolation"
  on audit_log for all
  using (
    company_id = get_user_company_id()
    or is_super_admin()
  );

-- Notifications
create policy "Notifications: tenant isolation"
  on notifications for all
  using (
    company_id = get_user_company_id()
    or is_super_admin()
  );

-- RL Predictions
create policy "RL predictions: tenant isolation"
  on rl_predictions for all
  using (
    company_id = get_user_company_id()
    or is_super_admin()
  );

-- Corrosion Anomalies
create policy "Corrosion anomalies: tenant isolation"
  on corrosion_anomalies for all
  using (
    company_id = get_user_company_id()
    or is_super_admin()
  );

-- Fleet Risk Snapshots
create policy "Fleet risk snapshots: tenant isolation"
  on fleet_risk_snapshots for all
  using (
    company_id = get_user_company_id()
    or is_super_admin()
  );

-- DM Validation Results
create policy "DM validation results: tenant isolation"
  on dm_validation_results for all
  using (
    company_id = get_user_company_id()
    or is_super_admin()
  );

-- Company AI Config
-- SELECT: user dari tenant sendiri atau super_admin bisa lihat
-- INSERT/UPDATE/DELETE: TIDAK ADA policy → default-deny untuk authenticated users
-- Hanya service_role (FastAPI) yang bisa nulis, karena bypass RLS
create policy "AI config: select own tenant"
  on company_ai_config for select
  using (
    company_id = get_user_company_id()
    or is_super_admin()
  );

-- =============================================================
-- GLOBAL REFERENCE TABLES (readable by all, writable by super_admin)
-- =============================================================

-- Checklist Templates
create policy "Checklist templates: all can read"
  on checklist_templates for select
  using (true);

create policy "Checklist templates: super_admin write"
  on checklist_templates for insert
  with check (is_super_admin());

create policy "Checklist templates: super_admin update"
  on checklist_templates for update
  using (is_super_admin());

-- Inspection Interval Rules
create policy "Inspection interval rules: all can read"
  on inspection_interval_rules for select
  using (true);

create policy "Inspection interval rules: super_admin write"
  on inspection_interval_rules for insert
  with check (is_super_admin());

-- DM Knowledge Base
create policy "DM knowledge base: all can read"
  on dm_knowledge_base for select
  using (true);

create policy "DM knowledge base: super_admin write"
  on dm_knowledge_base for insert
  with check (is_super_admin());

-- =============================================================
-- STORAGE — inspection-photos bucket policies (private, tenant-isolated)
-- =============================================================
-- Helper: extract company_id from storage path (format: company_id/event_id/file)
-- storage.foldername(name) returns text[], 1-indexed in PostgreSQL
-- Policy: upload only allowed if company_id in path matches user's company

create policy "insp_photos_upload"
  on storage.objects for insert
  to authenticated
  with check (
    bucket_id = 'inspection-photos'
    and (storage.foldername(name))[1] = (
      select company_id::text from app_users where auth_user_id = auth.uid()
    )
  );

-- Policy: select only for same-company users or super_admin
create policy "insp_photos_select"
  on storage.objects for select
  to authenticated
  using (
    bucket_id = 'inspection-photos'
    and (
      (storage.foldername(name))[1] = (
        select company_id::text from app_users where auth_user_id = auth.uid()
      )
      or exists (
        select 1 from app_users
        where auth_user_id = auth.uid() and role = 'super_admin'
      )
    )
  );

-- NOTE: No public policy. Bucket is PRIVATE.
-- Frontend must use supabase.storage.from('inspection-photos').createSignedUrl() for display.
