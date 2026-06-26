-- =============================================================
-- MIGRATION: Fix RLS recursion on app_users
-- =============================================================
-- PROBLEM: get_user_company_id() and friends query app_users,
-- but they are called FROM app_users RLS policy → infinite recursion
-- "stack depth limit exceeded"
--
-- FIX: Mark all 3 helper functions as SECURITY DEFINER so they
-- bypass RLS when called from policy checks

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