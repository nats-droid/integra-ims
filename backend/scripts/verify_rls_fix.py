import os, json, urllib.request, http.client
from dotenv import load_dotenv
load_dotenv('/root/integra/backend/.env')

url = os.environ['SUPABASE_URL']
anon_key = 'sb_publishable_QnX7NGl1iseK__svt6670Q_9rBlVv36'
service_key = os.environ.get('SUPABASE_SERVICE_KEY')

# ── 1. Check if functions are SECURITY DEFINER ──
# Use PostgREST raw SQL via the service key
# pg_proc is in pg_catalog, not exposed via REST
# But we can call information_schema.routines which IS exposed

print("═══ 1. CEK STATUS FUNCTION ═══")
try:
    # Try to query information_schema.routines
    conn = http.client.HTTPSConnection("enppairwpjtmrgrvzxio.supabase.co")
    # PostgREST raw SQL endpoint
    raw_sql = "SELECT routine_name, security_type FROM information_schema.routines WHERE routine_name IN ('get_user_company_id','get_user_role','is_super_admin')"
    
    conn.request("GET", f"/rest/v1/rpc/", json.dumps({"query": raw_sql}).encode(), {
        'apikey': service_key,
        'Authorization': f'Bearer {service_key}',
        'Content-Type': 'application/json',
    })
    resp = conn.getresponse()
    print(f"RPC info_schema: {resp.status} {resp.read().decode()[:200]}")
except Exception as e:
    print(f"RPC query error: {e}")

# Alternative: Call each function and see if it works now
print("\n── Test get_user_company_id() via REST (service key) ──")
try:
    # First authenticate as engineer1
    data = json.dumps({"email":"engineer1@example.com","password":"Integra2024!"}).encode()
    req = urllib.request.Request(
        f'{url}/auth/v1/token?grant_type=password',
        data=data,
        headers={'apikey': anon_key, 'Content-Type': 'application/json'}
    )
    resp = urllib.request.urlopen(req)
    auth_result = json.loads(resp.read().decode())
    token = auth_result['access_token']
    print(f"  Login: ✅ engineer1@example.com")
    
    # Now call get_user_company_id() via REST with this user's token
    req2 = urllib.request.Request(
        f'{url}/rest/v1/rpc/get_user_company_id',
        data=b'{}',
        headers={
            'apikey': anon_key,
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
    )
    resp2 = urllib.request.urlopen(req2)
    company_id = resp2.read().decode()
    print(f"  get_user_company_id(): ✅ {company_id[:30]}...")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"  ERROR: HTTP {e.code}")
    print(f"  Body: {body[:300]}")
except Exception as e:
    print(f"  EXCEPTION: {e}")

# ── 2. Full login flow ──
print(f"\n═══ 2. FULL LOGIN FLOW (FRONTEND SIMULATION) ═══")
try:
    # Step 1: Login
    data = json.dumps({"email":"engineer1@example.com","password":"Integra2024!","gotrue_meta_security":{}}).encode()
    req = urllib.request.Request(
        f'{url}/auth/v1/token?grant_type=password',
        data=data,
        headers={'apikey': anon_key, 'Content-Type': 'application/json'}
    )
    resp = urllib.request.urlopen(req)
    auth_result = json.loads(resp.read().decode())
    token = auth_result['access_token']
    user_id = auth_result['user']['id']
    email = auth_result['user']['email']
    print(f"  Step 1 - Login: ✅ {email} (uid={user_id[:8]}...)")

    # Step 2: Query app_users with user JWT (anon key) - like the frontend does
    print(f"\n  Step 2 - Query app_users (anon key + JWT, same as browser):")
    try:
        req3 = urllib.request.Request(
            f'{url}/rest/v1/app_users?auth_user_id=eq.{user_id}&select=id,role,full_name',
            headers={
                'apikey': anon_key,
                'Authorization': f'Bearer {token}',
            }
        )
        resp3 = urllib.request.urlopen(req3)
        app_user_data = json.loads(resp3.read().decode())
        print(f"    Result: ✅ {json.dumps(app_user_data, indent=2)}")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"    ERROR: HTTP {e.code}")
        print(f"    Body: {body[:500]}")
    
    # Step 3: Also try querying equipment table (to test broader RLS)
    print(f"\n  Step 3 - Query equipment (anon key + JWT):")
    try:
        req4 = urllib.request.Request(
            f'{url}/rest/v1/equipment?select=id,tag_number,equipment_type&limit=3',
            headers={
                'apikey': anon_key,
                'Authorization': f'Bearer {token}',
            }
        )
        resp4 = urllib.request.urlopen(req4)
        eq_data = json.loads(resp4.read().decode())
        print(f"    Result: ✅ {len(eq_data)} rows")
        for r in eq_data:
            print(f"      {r.get('tag_number')} ({r.get('equipment_type')})")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"    ERROR: HTTP {e.code}")
        print(f"    Body: {body[:300]}")

except Exception as e:
    print(f"  EXCEPTION: {e}")

# ── 3. Also try calling the function directly ──
print(f"\n═══ 3. DIRECT RPC CALLS (as engineer1) ═══")
for func_name in ['get_user_company_id', 'get_user_role', 'is_super_admin']:
    try:
        req = urllib.request.Request(
            f'{url}/rest/v1/rpc/{func_name}',
            data=b'{}',
            headers={
                'apikey': anon_key,
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
            }
        )
        resp = urllib.request.urlopen(req)
        result = resp.read().decode()
        print(f"  {func_name}(): ✅ {result[:80]}")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  {func_name}(): ❌ HTTP {e.code} - {body[:150]}")