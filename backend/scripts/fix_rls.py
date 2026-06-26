import os, json, urllib.request
from dotenv import load_dotenv
load_dotenv('/root/integra/backend/.env')

url = os.environ['SUPABASE_URL']
key = os.environ['SUPABASE_SERVICE_KEY']

# Read the updated function SQL
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

data = json.dumps({"query": sql}).encode()

req = urllib.request.Request(
    f'{url}/rest/v1/rpc/exec_sql',
    data=data,
    headers={
        'apikey': key,
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json',
    },
    method='POST',
)

try:
    resp = urllib.request.urlopen(req)
    print("SQL executed:", resp.read().decode()[:200])
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"HTTP {e.code}: {body[:500]}")
    
    # Try direct SQL endpoint
    try:
        import http.client
        conn = http.client.HTTPSConnection("enppairwpjtmrgrvzxio.supabase.co")
        conn.request("POST", "/rest/v1/sql", data, headers)
        resp2 = conn.getresponse()
        print("SQL endpoint:", resp2.read().decode()[:200])
    except Exception as e2:
        print(f"Direct SQL also failed: {e2}")
        
        # Last resort: use supabase-py rpc
        try:
            from supabase import create_client
            sb = create_client(url, key)
            # Try calling the function individually
            for func_sql in sql.split('create or replace')[1:]:
                func_sql = 'create or replace' + func_sql
                # Use raw SQL via supabase
                result = sb.rpc('exec_sql', {'query': func_sql}).execute()
                print(f"RPC result: {result}")
        except Exception as e3:
            print(f"RPC also failed: {e3}")