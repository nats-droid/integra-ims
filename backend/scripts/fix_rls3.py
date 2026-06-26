import os, json, urllib.request
from dotenv import load_dotenv
load_dotenv('/root/integra/backend/.env')

url = os.environ['SUPABASE_URL']
key = os.environ['SUPABASE_SERVICE_KEY']
anon_key = 'sb_publishable_QnX7NGl1iseK__svt6670Q_9rBlVv36'

# The issue: RLS recursion on app_users table
# get_user_company_id() queries app_users but is used in app_users RLS policy
# Fix: security definer

# Use Supabase SQL via REST API - create a migration
# Actually, let's use the supabase-py to call the REST API with raw SQL

# The trick: Use PostgREST's /rpc/ endpoint with a built-in function
# Supabase has pg_catalog functions we can use

# OR: Use the project's database URL directly
# Database URL pattern: postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres

print("=== Project Info ===")
print(f"URL: {url}")
print(f"Ref: enppairwpjtmrgrvzxio")

# Try to get DB connection info via management API
# The service key has the ability to call the database via PostgREST

# Actually, let me try a different approach:
# The `is_super_admin` function already queries app_users.
# Instead of modifying it with security definer, let's use a different check
# that doesn't query app_users - use JWT claims instead.

# Option 1: Add the role to JWT claims
# Option 2: Use a separate settings table
# Option 3: Modify the RLS policy to not use these functions

# Actually the easiest fix: Add a role column to the auth.users metadata
# But that requires auth admin API

# Let me try: Use the Supabase Management REST API
# https://supabase.com/docs/reference/api/database-run-query

import http.client

# The service key can create SQL functions via the REST API
# Use: POST /rest/v1/ with a special Prefer header

conn = http.client.HTTPSConnection("enppairwpjtmrgrvzxio.supabase.co")

# Create a temp function using raw SQL via pg_catalog
# pg_catalog.pg_xxx functions are available via REST
# Actually, we can use the "create function" via the standard REST API!

# Let me try executing via the PostgREST API directly
# PostgREST supports calling functions via /rpc/ but not arbitrary SQL

# Method: Use the database's "sql" function (if it exists)
# Or: Use the Supabase "graphql" endpoint

# Let's check if GraphQL is enabled
conn.request("POST", "/graphql/v1", json.dumps({
    "query": "query { __schema { queryType { name } } }"
}).encode(), {
    'apikey': key,
    'Authorization': f'Bearer {key}',
    'Content-Type': 'application/json',
})
resp = conn.getresponse()
print(f"\nGraphQL status: {resp.status}")
if resp.status == 200:
    print("GraphQL enabled!")
else:
    print(f"GraphQL response: {resp.read().decode()[:200]}")

# Method: Use the "Run Query" endpoint
# Supabase Pro plan has a SQL editor API
# POST https://api.supabase.com/v1/projects/{ref}/database/query
print("\nTrying Management API with service key as PAT...")
conn2 = http.client.HTTPSConnection("api.supabase.com")
conn2.request("POST", f"/v1/projects/enppairwpjtmrgrvzxio/database/query", json.dumps({
    "query": "SELECT 1 as test"
}).encode(), {
    'Authorization': f'Bearer {key}',
    'Content-Type': 'application/json',
})
resp2 = conn2.getresponse()
body2 = resp2.read().decode()
print(f"Status: {resp2.status}")
print(f"Body: {body2[:500]}")