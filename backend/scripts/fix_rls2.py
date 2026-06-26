import os, json, urllib.request
from dotenv import load_dotenv
load_dotenv('/root/integra/backend/.env')

api_key = os.environ.get('SUPABASE_SERVICE_KEY')
project_ref = 'enppairwpjtmrgrvzxio'

# Use Supabase Management API to run SQL
# Need an access token first
mgmt_url = 'https://api.supabase.com'

# Try management API with service key directly
sql = """
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

# Try using the project's postgREST raw SQL endpoint
url = os.environ['SUPABASE_URL']
data = json.dumps({"query": sql}).encode()

# Method 1: via Auth API admin function call
headers = {
    'apikey': api_key,
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json',
}

print("Attempting SQL execution...")

# Method: Use pgrst to execute raw SQL
# The Supabase REST API doesn't expose raw SQL execution directly
# But we can create a function first, then call it

# Let's try a different approach - create a wrapper function first
create_wrapper = """
create or replace function exec_sql(sql text)
returns void
language plpgsql security definer
as $$
begin
  execute sql;
end;
$$;
"""

try:
    # First, try creating the exec_sql wrapper via the API
    # This won't work via REST, but let's try the /rest/v1/rpc/ approach
    req = urllib.request.Request(
        f'{url}/rest/v1/rpc/exec_sql',
        data=json.dumps({"sql": "SELECT 1"}).encode(),
        headers=headers,
        method='POST'
    )
    urllib.request.urlopen(req)
    print("exec_sql already exists!")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    if '404' in str(e):
        print("exec_sql doesn't exist yet - need alternative approach")
    else:
        print(f"Other error: {e.code} {body[:200]}")
except Exception as e:
    print(f"Exception: {e}")

# Alternate approach: Try Supabase Management API SQL endpoint
print("\nTrying Supabase Management API...")
try:
    # Try project's management API SQL endpoint
    req2 = urllib.request.Request(
        f'{mgmt_url}/v1/projects/{project_ref}/database/query',
        data=json.dumps({"query": sql}).encode(),
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        },
        method='POST'
    )
    resp2 = urllib.request.urlopen(req2)
    print("Management API:", resp2.read().decode()[:200])
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"HTTP {e.code}: {body[:300]}")
except Exception as e:
    print(f"Exception: {e}")

# Alternate approach: Install psql and connect
print("\nChecking psql availability...")
import shutil
psql_path = shutil.which('psql')
if psql_path:
    print(f"psql at: {psql_path}")
else:
    print("psql not installed")
    
# Check if we can install it
try:
    result = os.system('apt-get install -y -qq postgresql-client 2>&1')
    print(f"Install result: {result}")
    if shutil.which('psql'):
        print("psql now available!")
except:
    print("Can't install psql")