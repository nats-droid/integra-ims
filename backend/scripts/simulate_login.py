import os, json, urllib.request
from supabase import create_client

url = 'https://enppairwpjtmrgrvzxio.supabase.co'
anon_key = 'sb_publishable_QnX7NGl1iseK__svt6670Q_9rBlVv36'
service_key = None

# Load service key from env
from dotenv import load_dotenv
load_dotenv('/root/integra/backend/.env')
service_key = os.environ.get('SUPABASE_SERVICE_KEY')

# 1. Test login with SUPABASE AUTH API (anon key - same as browser)
print("=== 1. AUTH API (anon key, same as browser) ===")
try:
    data = json.dumps({"email":"engineer1@example.com","password":"Integra2024!","gotrue_meta_security":{}}).encode()
    req = urllib.request.Request(
        f'{url}/auth/v1/token?grant_type=password',
        data=data,
        headers={
            'apikey': anon_key,
            'Content-Type': 'application/json',
        }
    )
    resp = urllib.request.urlopen(req)
    result = json.loads(resp.read().decode())
    print(f"  ✓ SUCCESS - user: {result.get('user',{}).get('email')}")
    token = result['access_token']
    
    # 2. Test fetching user profile from app_users
    print("\n=== 2. Fetch app_users profile ===")
    sb = create_client(url, anon_key)
    # Set auth token on the client
    sb.auth.set_session(token, result.get('refresh_token', ''))
    user_id = result['user']['id']
    print(f"  User ID: {user_id}")
    
    # Query app_users
    resp2 = sb.table('app_users').select('*').eq('auth_user_id', user_id).execute()
    if resp2.data:
        print(f"  ✓ PROFILE FOUND: {resp2.data[0].get('full_name')} (role: {resp2.data[0].get('role')})")
    else:
        print(f"  ✗ NO PROFILE - app_users empty for this user")
    
    # 3. Check RLS - can we access with anon key?
    print("\n=== 3. RLS check (anon key) ===")
    sb_anon = create_client(url, anon_key)
    resp3 = sb_anon.table('app_users').select('*').eq('auth_user_id', user_id).execute()
    if hasattr(resp3, 'data') and resp3.data:
        print(f"  ✓ RLS OK - can access with anon key")
    else:
        print(f"  ✗ RLS BLOCKED: {resp3}")
except urllib.error.HTTPError as e:
    print(f"  ✗ AUTH FAILED: {e.code} {e.reason}")
    body = e.read().decode()
    print(f"  Response: {body[:300]}")
except Exception as e:
    print(f"  ✗ ERROR: {e}")

# 4. Also test with service key (direct)
print("\n=== 4. Direct check (service key) ===")
if service_key:
    try:
        from supabase import create_client
        sb_svc = create_client(url, service_key)
        resp4 = sb_svc.table('app_users').select('id, auth_user_id, role, full_name').execute()
        print(f"  Total app_users: {len(resp4.data)}")
        for r in resp4.data:
            print(f"    {r['full_name']} (role={r['role']}) auth_user_id={str(r['auth_user_id'])[:8]}...")
    except Exception as e:
        print(f"  ERROR: {e}")

# 5. Check Supabase Auth settings (site URL, etc.)
print("\n=== 5. Auth settings ===")
try:
    req5 = urllib.request.Request(
        f'{url}/auth/v1/settings',
        headers={'apikey': anon_key}
    )
    resp5 = urllib.request.urlopen(req5)
    print(resp5.read().decode()[:500])
except urllib.error.HTTPError as e:
    body = e.read().decode()
    print(f"  HTTP {e.code}: {body[:200]}")
except Exception as e:
    print(f"  Error: {e}")