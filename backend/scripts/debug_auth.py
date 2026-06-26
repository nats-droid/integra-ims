import os, json, urllib.request
from dotenv import load_dotenv
load_dotenv('/root/integra/backend/.env')

url = os.environ['SUPABASE_URL']
key = os.environ['SUPABASE_SERVICE_KEY']
anon_key = os.environ.get('SUPABASE_ANON_KEY', key)

from supabase import create_client
sb = create_client(url, key)

# 1. Check auth.users (admin API)
admin_req = urllib.request.Request(
    f'{url}/auth/v1/admin/users',
    headers={'apikey': key, 'Authorization': f'Bearer {key}'}
)
admin_resp = urllib.request.urlopen(admin_req)
data = json.loads(admin_resp.read().decode())
print("=== auth.users (admin API) ===")
for u in data.get('users', []):
    print(f"  id={u['id']} email={u.get('email')}")

# 2. Check app_users schema
print("\n=== app_users schema ===")
resp = sb.table('app_users').select('*').limit(5).execute()
if resp.data and len(resp.data) > 0:
    cols = list(resp.data[0].keys())
    print(f"  Columns: {cols}")
    for r in resp.data:
        print(f"  id={r['id']} auth_user_id={str(r.get('auth_user_id','?'))[:8]}... role={r.get('role','?')} full_name={r.get('full_name','?')}")
else:
    print(f"  Empty or error: {resp}")

# 3. Try to update app_users - does it have email?
# Check if maybe it has a different column name
try:
    resp2 = sb.table('app_users').select('*').execute()
    if resp2.data:
        print("\n=== ALL app_users columns ===")
        for k in resp2.data[0].keys():
            print(f"  {k}")
except Exception as e:
    print(f"  Error: {e}")

# 4. Find how the frontend gets user profile
# Check login page or auth context
print("\n=== Checking frontend auth flow ===")
import glob
# Find auth-related files
for f in glob.glob('/root/integra/frontend/src/**/*auth*', recursive=True):
    print(f"  {f}")
for f in glob.glob('/root/integra/frontend/src/**/*login*', recursive=True):
    print(f"  {f}")
for f in glob.glob('/root/integra/frontend/src/**/*layout*', recursive=True):
    print(f"  {f}")