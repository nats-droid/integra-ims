-- Migration: Add 'psv' equipment type
-- Run in Supabase Dashboard → SQL Editor
-- Date: 2026-06-23

-- Step 1: Drop the old check constraint (auto-named by postgres)
ALTER TABLE equipment DROP CONSTRAINT IF EXISTS equipment_type_check;

-- Step 2: Re-create with 'psv' added
ALTER TABLE equipment ADD CONSTRAINT equipment_type_check
  CHECK (type IN ('piping', 'vessel', 'tank', 'heater', 'pump', 'compressor', 'valve', 'psv', 'other'));

-- Step 3: Verify
SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint
  WHERE conrelid = 'equipment'::regclass AND contype = 'c';
