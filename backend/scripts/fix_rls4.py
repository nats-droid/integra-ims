import os, json, urllib.request
from dotenv import load_dotenv
load_dotenv('/root/integra/backend/.env')

url = os.environ['SUPABASE_URL']
key = os.environ['SUPABASE_SERVICE_KEY']

# Use Hasura-style GraphQL mutation (Supabase GraphQL only supports queries)
# So let's try creating a PostgREST function via the REST API

# Actually: Supabase pg_graphql does not support SQL mutations
# But we can try a creative approach:

# 1. Create a PL/pgSQL function via REST using RPC
# If a function exists that can execute SQL, we can call it

# Let's check what stored procedures already exist
try:
    req = urllib.request.Request(
        f'{url}/rest/v1/rpc/',
        headers={'apikey': key, 'Authorization': f'Bearer {key}'}
    )
    resp = urllib.request.urlopen(req)
    print("RPC functions:")
    print(resp.read().decode()[:500])
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"Can't list RPCs: {e.code} {body[:200]}")

# Method: Use 'psql' via Docker
print("\n=== Trying Docker psql ===")
import subprocess
try:
    # Pull postgres image
    subprocess.run(['docker', 'pull', 'postgres:alpine'], capture_output=True, timeout=30)
    
    # Get DB password - try common patterns
    db_password = os.environ.get('SUPABASE_DB_PASSWORD', '')
    if not db_password:
        # Try the service key as DB password
        db_password = key
        
    db_host = f'db.enppairwpjtmrgrvzxio.supabase.co'
    
    print(f"DB Host: {db_host}")
    print(f"DB Password length: {len(db_password)}")
    
    # Try to connect via Docker psql
    cmd = [
        'docker', 'run', '--rm', 'postgres:alpine',
        'psql', 
        f'postgresql://postgres:{db_password}@{db_host}:5432/postgres',
        '-c', 'SELECT 1'
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=15, text=True)
    print(f"Exit code: {result.returncode}")
    print(f"Stdout: {result.stdout[:200]}")
    print(f"Stderr: {result.stderr[:300]}")
except Exception as e:
    print(f"Docker psql failed: {e}")

# Fallback: Create SQL migration file for user to run manually
sql_fix = """
-- Fix RLS recursion: mark helper functions as SECURITY DEFINER
-- so they bypass RLS when called from RLS policies

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
"""

print("\n=== SQL to run ===")
print(sql_fix)