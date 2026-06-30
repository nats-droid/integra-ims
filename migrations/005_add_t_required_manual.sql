-- Migration 005: Add t_required_manual to cml_points
-- Purpose: Separate t_required (Barlow design calc) from t_min (retirement thickness)
-- t_required_manual: engineer-filled, from pressure design calculation (PD/2SE)
-- t_min: remains unchanged, still used by /plans logic
-- 
-- Run in Supabase SQL Editor (Dashboard > SQL Editor)

ALTER TABLE cml_points ADD COLUMN IF NOT EXISTS t_required_manual numeric NULL;

COMMENT ON COLUMN cml_points.t_required_manual IS 
  'Minimum required thickness from pressure design calc (Barlow: PD/2SE), WITHOUT corrosion allowance. 
   Input manually by engineer from datasheet/calculation sheet.
   Used by rl_confidence module for accurate Remaining Life calculation.';
