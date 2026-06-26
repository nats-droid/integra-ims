import os, json, urllib.request
from dotenv import load_dotenv
load_dotenv('/root/integra/backend/.env')

url = os.environ['SUPABASE_URL']
key = os.environ['SUPABASE_SERVICE_KEY']

# 1. Check auth.users
req = urllib.request.Request(
    f'{url}/rest/v1/rpc/get_auth_users',
    headers={'apikey': key, 'Authorization': f'Bearer {key}'}
)
try:
    resp = urllib.request.urlopen(req)
    print("=== auth.users ===")
    print(resp.read().decode()[:500])
except Exception as e:
    print("RPC get_auth_users failed:", e)
    # Try direct auth admin API
    try:
        admin_req = urllib.request.Request(
            f'{url}/auth/v1/admin/users',
            headers={'apikey': key, 'Authorization': f'Bearer {key}'}
        )
        admin_resp = urllib.request.urlopen(admin_req)
        data = json.loads(admin_resp.read().decode())
        print("=== auth.users (admin API) ===")
        for u in data.get('users', []):
            print(f"  id={u['id'][:8]}... email={u.get('email')}")
    except Exception as e2:
        print("Admin API also failed:", e2)

# 2. Check app_users via direct SQL
from supabase import create_client
sb = create_client(url, key)
try:
    resp = sb.table('app_users').select('id,email,role').execute()
    print("=== app_users ===")
    for r in resp.data:
        print(f"  id={r['id']} email={r.get('email','?')} role={r.get('role','?')}")
except Exception as e:
    print("app_users query failed:", e)

# 3. Try auth API directly
anon_key = os.environ.get('SUPABASE_ANON_KEY', key)
try:
    data = json.dumps({"email":"engineer1@example.com","password":"Integra2024!","gotrue_meta_security":{}}).encode()
    auth_req = urllib.request.Request(
        f'{url}/auth/v1/token?grant_type=password',
        data=data,
        headers={
            'apikey': anon_key,
            'Content-Type': 'application/json',
        }
    )
    auth_resp = urllib.request.urlopen(auth_req)
    auth_result = json.loads(auth_resp.read().decode())
    print("=== Auth API Test (engineer1) ===")
    print(f"  Success! user: {auth_result.get('user',{}).get('email')}")
except Exception as e:
    print("=== Auth API Test (engineer1) ===")
    print(f"  FAILED:", e)
    if hasattr(e, 'read'):
        print(f"  Response: {e.read().decode()[:500]}")
