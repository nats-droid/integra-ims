#!/usr/bin/env python3
"""
Seed dm_knowledge_base from dm_screener_pro.html reference data.
Parses DM_KB array from the JS file — no manual transcription.
"""
import os, re, json
from dotenv import load_dotenv
load_dotenv(dotenv_path='/root/integra/backend/.env')
from supabase import create_client

sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_KEY'])

REF_FILE = os.path.expanduser("~/.hermes/cache/documents/doc_f220e3d1165e_dm_kb_and_screenAsset.txt")

with open(REF_FILE, 'r') as f:
    content = f.read()

# Find DM_KB array: starts at "const DM_KB = [" and ends near "];"
start = content.find("const DM_KB = [")
if start < 0:
    print("ERROR: Cannot find DM_KB array in reference file")
    exit(1)

# Extract array content between [ and matching ]
# Find the position after "["
arr_start = content.index("[", start) + 1
# Find the matching "];" — since objects are nested, we count brackets
depth = 1
i = arr_start
while i < len(content) and depth > 0:
    if content[i] == '[':
        depth += 1
    elif content[i] == ']':
        depth -= 1
    i += 1
arr_text = content[arr_start:i-1]  # without the closing ]

# Now parse individual objects from the array
# Each object starts with { and ends with },
objects = []
obj_start = 0
while True:
    # Find next { at top level
    brace_start = arr_text.find('{', obj_start)
    if brace_start < 0:
        break
    
    # Find matching }
    depth = 1
    j = brace_start + 1
    while j < len(arr_text) and depth > 0:
        if arr_text[j] == '{':
            depth += 1
        elif arr_text[j] == '}':
            depth -= 1
        j += 1
    
    obj_text = arr_text[brace_start:j]
    obj_start = j
    
    # Parse the JS object into a Python dict
    # Handle keys: id, name, cat, pwhtFlag, tempMin, tempMax, materials, fluids, inspection, mitigation
    entry = {}
    
    # Simple field extraction using regex
    # String values
    for key in ['id', 'name', 'cat', 'mitigation']:
        m = re.search(rf'{key}:\s*"([^"]*)"', obj_text)
        if m:
            entry[key] = m.group(1)
    
    # Boolean
    m = re.search(r'pwhtFlag:\s*(true|false)', obj_text)
    if m:
        entry['pwhtFlag'] = m.group(1) == 'true'
    
    # Numbers
    for key in ['tempMin', 'tempMax']:
        m = re.search(rf'{key}:\s*(-?\d+)', obj_text)
        if m:
            entry[key] = int(m.group(1))
    
    # Arrays: materials[...], fluids[...], inspection[...]
    for key in ['materials', 'fluids', 'inspection']:
        m = re.search(rf'{key}:\[([^\]]*)\]', obj_text)
        if m:
            items = re.findall(r'"([^"]*)"', m.group(1))
            entry[key] = items
    
    if 'id' in entry and 'name' in entry:
        objects.append(entry)
    elif entry:
        print(f"  Skipping partial entry: {entry.get('id', 'no-id')}")

print(f"Parsed {len(objects)} DM entries from reference file")

# Clear existing
count = sb.table('dm_knowledge_base').select('id', count='exact').execute()
if count.count and count.count > 0:
    print(f"Clearing existing {count.count} rows...")
    sb.table('dm_knowledge_base').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()

# Insert
inserted = 0
errors = 0
for dm in objects:
    try:
        # Map pwhtFlag (boolean) → pwht_flag (enum)
        if dm.get('pwhtFlag', False):
            pwht_flag = 'required'
        else:
            pwht_flag = 'not_required'
        
        # Build description from mitigation + inspection
        desc = dm.get('mitigation', '')
        inspection = dm.get('inspection', [])
        if inspection and desc:
            desc += '\nRecommended NDE: ' + ', '.join(inspection)
        elif inspection:
            desc = 'Recommended NDE: ' + ', '.join(inspection)
        
        record = {
            "dm_code": dm['id'],
            "dm_name": dm['name'],
            "category": dm.get('cat', 'Uncategorized'),
            "materials": dm.get('materials', []),
            "fluids": dm.get('fluids', []),
            "temp_min": dm.get('tempMin', -999),
            "temp_max": dm.get('tempMax', 999),
            "pwht_flag": pwht_flag,
            "recommended_nde": inspection,
            "description": desc,
        }
        sb.table("dm_knowledge_base").insert(record).execute()
        inserted += 1
    except Exception as e:
        print(f"  Error inserting {dm.get('id')}: {e}")
        errors += 1

final = sb.table('dm_knowledge_base').select('id', count='exact').execute()
print(f"\nDone: {inserted} inserted, {errors} errors. Total in DB: {final.count}")

# Verify CUI temp range
cui = sb.table('dm_knowledge_base').select('*').eq('dm_code', '3.22').single().execute()
if cui.data:
    print(f"\nSpot check 3.22 (CUI): temp_min={cui.data['temp_min']}, temp_max={cui.data['temp_max']} (ref: 60..177)")