import os, json, urllib.request, http.client
from dotenv import load_dotenv
load_dotenv('/root/integra/backend/.env')

url = os.environ['SUPABASE_URL']
anon_key = 'sb_publishable_QnX7NGl1iseK__svt6670Q_9rBlVv36'

# Simulate the EXACT frontend login flow
# 1. Login
# 2. Immediately try to access protected pages via session cookie

# Step 1: Login as engineer1
print("═══ FULL LOGIN SIMULATION ═══")

data = json.dumps({
    "email": "engineer1@example.com",
    "password": "Integra2024!",
    "gotrue_meta_security": {}
}).encode()

conn = http.client.HTTPSConnection("enppairwpjtmrgrvzxio.supabase.co")
conn.request("POST", "/auth/v1/token?grant_type=password", data, {
    'apikey': anon_key,
    'Content-Type': 'application/json',
})
resp = conn.getresponse()
result = json.loads(resp.read().decode())

if 'access_token' not in result:
    print("❌ LOGIN FAILED")
    print(json.dumps(result, indent=2))
    exit(1)

token = result['access_token']
refresh = result['refresh_token']
user = result['user']
print(f"✅ Login: {user.get('email')}")
print(f"   User ID: {user.get('id')}")
print(f"   Token: {token[:40]}...")

# Step 2: Try auth.getUser() - what the dashboard layout does first
print(f"\n── Step 2: auth.getUser() (dashboard layout) ──")
conn2 = http.client.HTTPSConnection("enppairwpjtmrgrvzxio.supabase.co")
conn2.request("GET", "/auth/v1/user", headers={
    'apikey': anon_key,
    'Authorization': f'Bearer {token}',
})
resp2 = conn2.getresponse()
user_info = json.loads(resp2.read().decode())
print(f"   Result: {user_info.get('email')}")
print(f"   aud: {user_info.get('aud')}")
print(f"   role: {user_info.get('role')}")

# Step 3: Query app_users by auth_user_id - what dashboard layout does
print(f"\n── Step 3: Query app_users (same as frontend) ──")
conn3 = http.client.HTTPSConnection("enppairwpjtmrgrvzxio.supabase.co")
conn3.request("GET", f"/rest/v1/app_users?auth_user_id=eq.{user['id']}&select=id,role,full_name,company_id", headers={
    'apikey': anon_key,
    'Authorization': f'Bearer {token}',
})
resp3 = conn3.getresponse()
body3 = resp3.read().decode()
try:
    app_data = json.loads(body3)
    print(f"   Result: ✅ {json.dumps(app_data, indent=2)}")
except:
    print(f"   Error: {resp3.status} {body3[:300]}")

# Step 4: Try access /dashboard (check if session cookie is needed)
# Next.js uses Supabase SSR cookies - the session is stored in cookies
# Let's simulate by trying to access a restricted page

# Step 5: Check what errors the frontend might see
# The supabase-js library in the browser uses the gotrue-js client
# to set session cookies. Let's check if there's a cookie issue.

print(f"\n── Step 4: Check if Supabase gives valid session ──")
# Try refresh token
import http.client
refresh_data = json.dumps({"refresh_token": refresh}).encode()
conn4 = http.client.HTTPSConnection("enppairwpjtmrgrvzxio.supabase.co")
conn4.request("POST", "/auth/v1/token?grant_type=refresh_token", refresh_data, {
    'apikey': anon_key,
    'Content-Type': 'application/json',
})
resp4 = conn4.getresponse()
refresh_result = json.loads(resp4.read().decode())
if 'access_token' in refresh_result:
    print(f"   Refresh: ✅ Session still valid")
else:
    print(f"   Refresh: ❌ {refresh_result.get('error_description')}")

# Step 5: Test ALL 4 test users
print(f"\n── Step 5: Test all 4 users ──")
for email in ["supervisor@example.com", "engineer1@example.com", "inspector1@example.com", "inspector2@example.com"]:
    try:
        d = json.dumps({"email": email, "password": "Integra2024!"}).encode()
        r = urllib.request.Request(
            f'{url}/auth/v1/token?grant_type=password',
            data=d,
            headers={'apikey': anon_key, 'Content-Type': 'application/json'}
        )
        rsp = urllib.request.urlopen(r)
        res = json.loads(rsp.read().decode())
        
        tok = res['access_token']
        uid = res['user']['id']
        
        # Query app_users
        r2 = urllib.request.Request(
            f'{url}/rest/v1/app_users?auth_user_id=eq.{uid}&select=id,role,full_name',
            headers={'apikey': anon_key, 'Authorization': f'Bearer {tok}'}
        )
        rsp2 = urllib.request.urlopen(r2)
        prof = json.loads(rsp2.read().decode())
        profile = prof[0] if prof else "NOT FOUND"
        
        print(f"   ✅ {email} → {profile.get('full_name')} ({profile.get('role')})")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"   ❌ {email} → HTTP {e.code}: {body[:100]}")