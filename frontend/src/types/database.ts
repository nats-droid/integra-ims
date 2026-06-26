// =============================================================
// INTEGRA — Database TypeScript Types
// Auto-generated from PRD Section 4 schema
// =============================================================

export type Json = string | number | boolean | null | { [key: string]: Json | undefined } | Json[]

export interface Database {
  public: {
    Tables: {
      companies: {
        Row: {
          id: string
          name: string
          plan_tier: 'trial' | 'starter' | 'pro'
          max_equipment: number | null
          max_users: number | null
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          name: string
          plan_tier?: 'trial' | 'starter' | 'pro'
          max_equipment?: number | null
          max_users?: number | null
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          name?: string
          plan_tier?: 'trial' | 'starter' | 'pro'
          max_equipment?: number | null
          max_users?: number | null
          created_at?: string
          updated_at?: string
        }
      }
      app_users: {
        Row: {
          id: string
          auth_user_id: string
          company_id: string | null
          role: 'inspector' | 'engineer' | 'supervisor' | 'super_admin'
          full_name: string
          phone: string | null
          avatar_url: string | null
          is_active: boolean
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          auth_user_id: string
          company_id?: string | null
          role: 'inspector' | 'engineer' | 'supervisor' | 'super_admin'
          full_name: string
          phone?: string | null
          avatar_url?: string | null
          is_active?: boolean
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          auth_user_id?: string
          company_id?: string | null
          role?: 'inspector' | 'engineer' | 'supervisor' | 'super_admin'
          full_name?: string
          phone?: string | null
          avatar_url?: string | null
          is_active?: boolean
          created_at?: string
          updated_at?: string
        }
      }
      plant_areas: {
        Row: {
          id: string
          company_id: string
          name: string
          parent_area_id: string | null
          description: string | null
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          company_id: string
          name: string
          parent_area_id?: string | null
          description?: string | null
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          company_id?: string
          name?: string
          parent_area_id?: string | null
          description?: string | null
          created_at?: string
          updated_at?: string
        }
      }
      equipment: {
        Row: {
          id: string
          company_id: string
          tag: string
          type: 'piping' | 'vessel' | 'tank' | 'heater' | 'pump' | 'compressor' | 'valve' | 'other'
          fluid_service: string | null
          material: string | null
          area_id: string | null
          design_temp_min: number | null
          design_temp_max: number | null
          design_pressure: number | null
          pwht: boolean
          risk_category: 'low' | 'medium' | 'high' | 'critical' | null
          compliance_status: 'compliant' | 'non-compliant' | 'pending'
          size_or_dimension: string | null
          insulation_type: string | null
          installation_date: string | null
          manufacturer: string | null
          serial_number: string | null
          notes: string | null
          is_active: boolean
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          company_id: string
          tag: string
          type: 'piping' | 'vessel' | 'tank' | 'heater' | 'pump' | 'compressor' | 'valve' | 'other'
          fluid_service?: string | null
          material?: string | null
          area_id?: string | null
          design_temp_min?: number | null
          design_temp_max?: number | null
          design_pressure?: number | null
          pwht?: boolean
          risk_category?: 'low' | 'medium' | 'high' | 'critical' | null
          compliance_status?: 'compliant' | 'non-compliant' | 'pending'
          size_or_dimension?: string | null
          insulation_type?: string | null
          installation_date?: string | null
          manufacturer?: string | null
          serial_number?: string | null
          notes?: string | null
          is_active?: boolean
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          company_id?: string
          tag?: string
          type?: 'piping' | 'vessel' | 'tank' | 'heater' | 'pump' | 'compressor' | 'valve' | 'other'
          fluid_service?: string | null
          material?: string | null
          area_id?: string | null
          design_temp_min?: number | null
          design_temp_max?: number | null
          design_pressure?: number | null
          pwht?: boolean
          risk_category?: 'low' | 'medium' | 'high' | 'critical' | null
          compliance_status?: 'compliant' | 'non-compliant' | 'pending'
          size_or_dimension?: string | null
          insulation_type?: string | null
          installation_date?: string | null
          manufacturer?: string | null
          serial_number?: string | null
          notes?: string | null
          is_active?: boolean
          created_at?: string
          updated_at?: string
        }
      }
      circuits: {
        Row: {
          id: string
          company_id: string
          equipment_id: string
          name: string
          description: string | null
          governing_cr_cache: number | null
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          company_id: string
          equipment_id: string
          name: string
          description?: string | null
          governing_cr_cache?: number | null
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          company_id?: string
          equipment_id?: string
          name?: string
          description?: string | null
          governing_cr_cache?: number | null
          created_at?: string
          updated_at?: string
        }
      }
      cml_points: {
        Row: {
          id: string
          company_id: string
          circuit_id: string | null
          equipment_id: string
          location_label: string
          nominal_thickness: number
          t_min: number | null
          retirement_factor: number
          cml_type: 'ut' | 'rt' | 'manual'
          is_active: boolean
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          company_id: string
          circuit_id?: string | null
          equipment_id: string
          location_label: string
          nominal_thickness: number
          t_min?: number | null
          retirement_factor?: number
          cml_type?: 'ut' | 'rt' | 'manual'
          is_active?: boolean
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          company_id?: string
          circuit_id?: string | null
          equipment_id?: string
          location_label?: string
          nominal_thickness?: number
          t_min?: number | null
          retirement_factor?: number
          cml_type?: 'ut' | 'rt' | 'manual'
          is_active?: boolean
          created_at?: string
          updated_at?: string
        }
      }
      checklist_templates: {
        Row: {
          id: string
          equipment_type: string
          section: string
          item_code: string
          item_description: string
          item_type: 'rating' | 'yes_no' | 'text' | 'photo'
          display_order: number
          is_active: boolean
        }
        Insert: {
          id?: string
          equipment_type: string
          section: string
          item_code: string
          item_description: string
          item_type?: 'rating' | 'yes_no' | 'text' | 'photo'
          display_order?: number
          is_active?: boolean
        }
        Update: {
          id?: string
          equipment_type?: string
          section?: string
          item_code?: string
          item_description?: string
          item_type?: 'rating' | 'yes_no' | 'text' | 'photo'
          display_order?: number
          is_active?: boolean
        }
      }
      inspection_events: {
        Row: {
          id: string
          company_id: string
          equipment_id: string
          campaign_id: string | null
          inspector_id: string | null
          inspection_type: string
          event_date: string
          status: 'draft' | 'submitted' | 'approved' | 'rejected'
          notes: string | null
          weather_condition: string | null
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          company_id: string
          equipment_id: string
          campaign_id?: string | null
          inspector_id?: string | null
          inspection_type: string
          event_date?: string
          status?: 'draft' | 'submitted' | 'approved' | 'rejected'
          notes?: string | null
          weather_condition?: string | null
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          company_id?: string
          equipment_id?: string
          campaign_id?: string | null
          inspector_id?: string | null
          inspection_type?: string
          event_date?: string
          status?: 'draft' | 'submitted' | 'approved' | 'rejected'
          notes?: string | null
          weather_condition?: string | null
          created_at?: string
          updated_at?: string
        }
      }
      thickness_readings: {
        Row: {
          id: string
          company_id: string
          cml_point_id: string
          inspection_event_id: string | null
          reading_date: string
          reading_mm: number
          is_representative: boolean
          notes: string | null
          created_at: string
        }
        Insert: {
          id?: string
          company_id: string
          cml_point_id: string
          inspection_event_id?: string | null
          reading_date?: string
          reading_mm: number
          is_representative?: boolean
          notes?: string | null
          created_at?: string
        }
        Update: {
          id?: string
          company_id?: string
          cml_point_id?: string
          inspection_event_id?: string | null
          reading_date?: string
          reading_mm?: number
          is_representative?: boolean
          notes?: string | null
          created_at?: string
        }
      }
      inspection_plans: {
        Row: {
          id: string
          company_id: string
          equipment_id: string
          inspection_type: 'external' | 'internal'
          remaining_life_date: string | null
          rbi_date_manual: string | null
          disnaker_date: string | null
          final_due_date: string | null
          approval_status: 'pending' | 'approved' | 'rejected' | 'revised'
          approved_by: string | null
          approved_at: string | null
          approval_comment: string | null
          interval_override_years: number | null
          is_active: boolean
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          company_id: string
          equipment_id: string
          inspection_type: 'external' | 'internal'
          remaining_life_date?: string | null
          rbi_date_manual?: string | null
          disnaker_date?: string | null
          final_due_date?: string | null
          approval_status?: 'pending' | 'approved' | 'rejected' | 'revised'
          approved_by?: string | null
          approved_at?: string | null
          approval_comment?: string | null
          interval_override_years?: number | null
          is_active?: boolean
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          company_id?: string
          equipment_id?: string
          inspection_type?: 'external' | 'internal'
          remaining_life_date?: string | null
          rbi_date_manual?: string | null
          disnaker_date?: string | null
          final_due_date?: string | null
          approval_status?: 'pending' | 'approved' | 'rejected' | 'revised'
          approved_by?: string | null
          approved_at?: string | null
          approval_comment?: string | null
          interval_override_years?: number | null
          is_active?: boolean
          created_at?: string
          updated_at?: string
        }
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      get_user_company_id: {
        Args: Record<string, never>
        Returns: string | null
      }
      get_user_role: {
        Args: Record<string, never>
        Returns: string | null
      }
      is_super_admin: {
        Args: Record<string, never>
        Returns: boolean
      }
    }
    Enums: {
      [_ in never]: never
    }
  }
}

// =============================================================
// COMPOSITE / DOMAIN TYPES
// =============================================================

// User profile (app_users joined with auth)
export interface UserProfile {
  id: string
  auth_user_id: string
  company_id: string | null
  role: 'inspector' | 'engineer' | 'supervisor' | 'super_admin'
  full_name: string
  phone: string | null
  avatar_url: string | null
  is_active: boolean
  email?: string
}

// Equipment with related data
export interface EquipmentDetail {
  id: string
  tag: string
  type: string
  fluid_service: string | null
  material: string | null
  area_name: string | null
  area_id: string | null
  circuits: CircuitWithCML[]
  latest_inspection: InspectionEventRow | null
  risk_category: string | null
  compliance_status: string
}

export interface CircuitWithCML {
  id: string
  name: string
  cml_points: CMLPointWithReadings[]
}

export interface CMLPointWithReadings {
  id: string
  location_label: string
  nominal_thickness: number
  t_min: number | null
  readings: ThicknessReadingRow[]
}

export interface InspectionEventRow {
  id: string
  equipment_id: string
  inspector_name: string | null
  inspection_type: string
  event_date: string
  status: string
}

export interface ThicknessReadingRow {
  id: string
  reading_date: string
  reading_mm: number
  notes: string | null
}

// Dashboard KPIs
export interface DashboardKPI {
  total_equipment: number
  total_cml: number
  inspections_this_month: number
  overdue_plans: number
  pending_approvals: number
  non_compliant: number
  active_campaigns: number
}
