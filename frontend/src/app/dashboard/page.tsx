'use client'
export const dynamic = 'force-dynamic'

import { createClient } from '@/lib/supabase/client'
import { useEffect, useState, useCallback } from 'react'
import { cn } from '@/utils/cn'
import Link from 'next/link'
import {
  LayoutDashboard,
  ClipboardList,
  Clock,
  BarChart3,
  TrendingDown,
  AlertTriangle,
  ShieldAlert,
  UserCircle,
  CheckCircle2,
  ExternalLink,
  Inbox,
  RefreshCw,
} from 'lucide-react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import DrillDownTable from '@/components/DrillDownTable'

/* ── Types ─────────────────────────────────────────────────── */

type TabKey = 'overview' | 'worklist' | 'pending' | 'workload' | 'rl' | 'anomaly' | 'fleet'

interface KPI {
  label: string
  value: number
  icon: React.ReactNode
  color: string
  description: string
}

interface ChartBar {
  name: string
  value: number
  fill: string
}

interface WorklistItem {
  id: string
  equipment_tag: string
  inspection_type: string
  event_date: string
  status: string
}

interface WorkloadInspector {
  id: string
  full_name: string
  total: number
  done: number
  completionRate: number
  overdue: number
}

interface FilterState {
  plantArea: string
  fluidService: string
  riskCategory: string
}

/* ── RL prediction types ────────────────────────────────────── */

interface RLEquipmentRow {
  equipment_id?: string
  tag: string
  type: string
  area_name: string | null
  governing_cml: string | null
  governing_rl_years: number | null
  computed_at: string | null
}

/* ── Tab definitions ───────────────────────────────────────── */

const tabs: { key: TabKey; label: string; icon: React.ReactNode }[] = [
  { key: 'overview',  label: 'Overview',         icon: <LayoutDashboard className="h-4 w-4" /> },
  { key: 'worklist',  label: 'My Worklist',      icon: <ClipboardList className="h-4 w-4" /> },
  { key: 'pending',   label: 'Pending Approval',  icon: <Clock className="h-4 w-4" /> },
  { key: 'workload',  label: 'Workload',          icon: <BarChart3 className="h-4 w-4" /> },
  { key: 'rl',        label: 'Remaining Life',     icon: <TrendingDown className="h-4 w-4" /> },
  { key: 'anomaly',   label: 'Anomaly',            icon: <AlertTriangle className="h-4 w-4" /> },
  { key: 'fleet',     label: 'Fleet Risk',         icon: <ShieldAlert className="h-4 w-4" /> },
]

/* ── Date helpers ──────────────────────────────────────────── */

function todayISO(): string {
  return new Date().toISOString().split('T')[0]
}

function addDays(days: number): string {
  const d = new Date()
  d.setDate(d.getDate() + days)
  return d.toISOString().split('T')[0]
}

const ACRONYMS = new Set(['cui', 'utm', 'vt', 'pt', 'rt', 'ut', 'mt', 'pt', 'rfi', 'ndt'])

function formatInspectionType(type: string): string {
  if (!type) return '—'
  if (ACRONYMS.has(type.toLowerCase())) return type.toUpperCase()
  return type.charAt(0).toUpperCase() + type.slice(1)
}

/* ── Semantic chart colors ─────────────────────────────────── */

const CHART_COLORS = {
  safe:    '#22c55e',  // green-500
  due90:   '#fbbf24',  // amber-400
  due60:   '#f59e0b',  // amber-500
  due30:   '#ef4444',  // red-500
}

/* ── Component ─────────────────────────────────────────────── */

export default function DashboardPage() {
  const supabase = createClient()
  const [activeTab, setActiveTab] = useState<TabKey>('overview')
  const [kpis, setKpis] = useState<KPI[]>([])
  const [chartData, setChartData] = useState<ChartBar[]>([])
  const [loading, setLoading] = useState(true)
  const [userName, setUserName] = useState('')
  const [userRole, setUserRole] = useState<string>('')
  const [appUserId, setAppUserId] = useState<string>('')
  const [companyId, setCompanyId] = useState<string>('')

  // My Worklist state
  const [worklist, setWorklist] = useState<WorklistItem[]>([])
  const [worklistLoading, setWorklistLoading] = useState(false)

  // Pending Approval state
  const [pendingCount, setPendingCount] = useState(0)
  const [pendingLoading, setPendingLoading] = useState(false)

  // Workload state
  const [workload, setWorkload] = useState<WorkloadInspector[]>([])
  const [workloadLoading, setWorkloadLoading] = useState(false)

  // Inspector Quality state
  const [inspectorQuality, setInspectorQuality] = useState<any[]>([])
  const [qualityLoading, setQualityLoading] = useState(false)

  // Anomaly state
  const [anomalies, setAnomalies] = useState<any[]>([])
  const [anomaliesLoading, setAnomaliesLoading] = useState(false)
  const [recalculating, setRecalculating] = useState(false)

  // Fleet Risk state
  const [fleetRiskData, setFleetRiskData] = useState<any>(null)
  const [fleetRiskLoading, setFleetRiskLoading] = useState(false)
  const [fleetRecalculating, setFleetRecalculating] = useState(false)
  const [fleetLastComputed, setFleetLastComputed] = useState<string | null>(null)

  // Remaining Life state
  const [rlData, setRlData] = useState<RLEquipmentRow[]>([])
  const [rlNoData, setRlNoData] = useState<RLEquipmentRow[]>([])
  const [rlLoading, setRlLoading] = useState(false)
  const [rlLastComputed, setRlLastComputed] = useState<string | null>(null)

  // Filter state
  const [filters, setFilters] = useState<FilterState>({
    plantArea: '',
    fluidService: '',
    riskCategory: '',
  })

  // Filter options (loaded once)
  const [plantAreas, setPlantAreas] = useState<string[]>([])
  const [fluidServices, setFluidServices] = useState<string[]>([])
  const [riskCategories, setRiskCategories] = useState<string[]>([])

  /* ── Load filter options on mount ──────────────────────────── */

  useEffect(() => {
    async function loadFilters() {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) return

      const { data: appUser } = await supabase
        .from('app_users')
        .select('company_id')
        .eq('auth_user_id', user.id)
        .maybeSingle() as unknown as { data: { company_id: string } | null }

      if (!appUser?.company_id) return

      const cid = appUser.company_id

      // Plant areas
      const { data: areas } = await (supabase as any)
        .from('plant_areas')
        .select('name')
        .eq('company_id', cid)
        .order('name')

      if (areas) {
        setPlantAreas([...new Set(areas.map((a: { name: string }) => a.name))] as string[])
      }

      // Fluid services (distinct from equipment)
      const { data: equips } = await (supabase as any)
        .from('equipment')
        .select('fluid_service, risk_category')
        .eq('company_id', cid)

      if (equips) {
        const fluids = [...new Set(equips.map((e: { fluid_service: string | null }) => e.fluid_service).filter(Boolean))] as string[]
        const risks = [...new Set(equips.map((e: { risk_category: string | null }) => e.risk_category).filter(Boolean))] as string[]
        setFluidServices(fluids.sort())
        setRiskCategories(risks.sort())
      }
    }
    loadFilters()
  }, [supabase])

  /* ── Load KPIs + Chart data (re-run when filters change) ──── */

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) { setLoading(false); return }

      const { data: appUser } = await supabase
        .from('app_users')
        .select('id, company_id, full_name, role')
        .eq('auth_user_id', user.id)
        .maybeSingle() as unknown as { data: { id: string; company_id: string; full_name: string; role: string } | null }

      const isSuperAdmin = appUser?.role === 'super_admin'

      // Super Admin: fetch first company as effective company
      if (!appUser?.company_id && isSuperAdmin) {
        const { data: firstCompany } = await (supabase as any)
          .from('companies')
          .select('id')
          .order('created_at', { ascending: true })
          .limit(1)
          .single()
        if (firstCompany?.id) {
          appUser.company_id = firstCompany.id
        }
      }

      if (!appUser?.company_id) { setLoading(false); return }

      setUserName(appUser.full_name || 'User')
      setUserRole(appUser.role || '')
      setAppUserId(appUser.id || '')
      setCompanyId(appUser.company_id || '')
      const cid = appUser.company_id
      const today = todayISO()
      const d90 = addDays(90)
      const d60 = addDays(60)
      const d30 = addDays(30)

      // Build equipment filter query
      let equipQuery = (supabase as any)
        .from('equipment')
        .select('id')
        .eq('company_id', cid)

      if (filters.plantArea) {
        // Get area_id from plant_areas name
        const { data: areaRow } = await (supabase as any)
          .from('plant_areas')
          .select('id')
          .eq('company_id', cid)
          .eq('name', filters.plantArea)
          .maybeSingle()
        if (areaRow) {
          equipQuery = equipQuery.eq('area_id', areaRow.id)
        } else {
          // No matching area — empty result
          setKpis(kpiZeros())
          setChartData(chartZeros())
          setLoading(false)
          return
        }
      }
      if (filters.fluidService) {
        equipQuery = equipQuery.eq('fluid_service', filters.fluidService)
      }
      if (filters.riskCategory) {
        equipQuery = equipQuery.eq('risk_category', filters.riskCategory)
      }

      const { data: filteredEquips } = await equipQuery
      const equipIds = (filteredEquips || []).map((e: { id: string }) => e.id)

      // Total Equipment count
      const totalEquip = equipIds.length

      // If no equipment match filter, short-circuit
      if (totalEquip === 0) {
        setKpis(kpiZeros())
        setChartData(chartZeros())
        setLoading(false)
        return
      }

      // Get plans for filtered equipment
      let plansQuery = (supabase as any)
        .from('inspection_plans')
        .select('id, equipment_id, final_due_date, is_active')
        .eq('company_id', cid)
        .eq('is_active', true)
        .in('equipment_id', equipIds)

      const { data: plans } = await plansQuery as { data: { id: string; equipment_id: string; final_due_date: string | null; is_active: boolean }[] | null }

      // Count KPIs from plans
      let due90 = 0, due60 = 0, due30 = 0, overdueCount = 0
      const overdueEquipSet = new Set<string>()

      // Chart categories — count EQUIPMENT (not plans), deduplicate
      const safeSet = new Set<string>()
      const due90Set = new Set<string>()
      const due60Set = new Set<string>()
      const due30OverdueSet = new Set<string>()

      for (const plan of plans || []) {
        const eid = plan.equipment_id

        if (!plan.final_due_date) {
          // Null final_due_date → Safe
          safeSet.add(eid)
          continue
        }

        const due = plan.final_due_date.slice(0, 10)

        if (due < today) {
          overdueCount++
          overdueEquipSet.add(eid)
          due30OverdueSet.add(eid)
        } else if (due <= d30) {
          due30++
          due30OverdueSet.add(eid)
        } else if (due <= d60) {
          due60++
          due60Set.add(eid)
        } else if (due <= d90) {
          due90++
          due90Set.add(eid)
        } else {
          safeSet.add(eid)
        }
      }

      // Equipment with plans that have dates, but also null-date plans → still safe
      // Equipment with no plans at all → safe
      const equipWithPlan = new Set(plans?.map(p => p.equipment_id) || [])
      for (const eid of equipIds) {
        if (!equipWithPlan.has(eid)) {
          safeSet.add(eid)
        }
      }

      // Non-compliant: distinct equipment with overdue plan
      const nonCompliant = overdueEquipSet.size

      setKpis([
        {
          label: 'Total Equipment',
          value: totalEquip,
          icon: <LayoutDashboard className="h-5 w-5" />,
          color: 'blue',
          description: 'All registered equipment across all types',
        },
        {
          label: 'Due ≤ 90 Days',
          value: due90,
          icon: <Clock className="h-5 w-5" />,
          color: 'amber',
          description: 'Active plans with due date within 90 days',
        },
        {
          label: 'Due ≤ 60 Days',
          value: due60,
          icon: <Clock className="h-5 w-5" />,
          color: 'orange',
          description: 'Active plans with due date within 60 days',
        },
        {
          label: 'Due ≤ 30 Days',
          value: due30,
          icon: <AlertTriangle className="h-5 w-5" />,
          color: 'red',
          description: 'Active plans with due date within 30 days',
        },
        {
          label: 'Overdue',
          value: overdueCount,
          icon: <AlertTriangle className="h-5 w-5" />,
          color: 'destructive',
          description: 'Active plans past their due date',
        },
        {
          label: 'Non-Compliant',
          value: nonCompliant,
          icon: <ShieldAlert className="h-5 w-5" />,
          color: 'destructive',
          description: 'Equipment with at least 1 overdue plan',
        },
      ])

      // Chart data (equipment counts per zone)
      setChartData([
        { name: 'Safe',           value: safeSet.size,        fill: CHART_COLORS.safe },
        { name: 'Due 90 Days',    value: due90Set.size,       fill: CHART_COLORS.due90 },
        { name: 'Due 60 Days',    value: due60Set.size,       fill: CHART_COLORS.due60 },
        { name: 'Due 30 & Overdue', value: due30OverdueSet.size, fill: CHART_COLORS.due30 },
      ])

    } catch (err) {
      console.error('Dashboard load error:', err)
    } finally {
      setLoading(false)
    }
  }, [supabase, filters])

  useEffect(() => { loadData() }, [loadData])

  /* ── Load My Worklist (inspector only) ─────────────────── */

  useEffect(() => {
    if (activeTab !== 'worklist' || !appUserId || !companyId) return
    async function load() {
      setWorklistLoading(true)
      try {
        // Get inspection_events for this inspector
        const { data: events } = await (supabase as any)
          .from('inspection_events')
          .select('id, equipment_id, inspection_type, event_date, status')
          .eq('company_id', companyId)
          .eq('inspector_id', appUserId)
          .order('event_date', { ascending: false })

        if (!events || events.length === 0) {
          setWorklist([])
          setWorklistLoading(false)
          return
        }

        // Get equipment tags
        const equipIds = [...new Set(events.map((e: any) => e.equipment_id))]
        const { data: equips } = await (supabase as any)
          .from('equipment')
          .select('id, tag')
          .in('id', equipIds)

        const tagMap: Record<string, string> = {}
        for (const eq of equips || []) {
          tagMap[eq.id] = eq.tag
        }

        setWorklist(
          events.map((ev: any) => ({
            id: ev.id,
            equipment_tag: tagMap[ev.equipment_id] || ev.equipment_id,
            inspection_type: ev.inspection_type || '—',
            event_date: ev.event_date || '—',
            status: ev.status || 'draft',
          }))
        )
      } catch (err) {
        console.error('Worklist load error:', err)
      } finally {
        setWorklistLoading(false)
      }
    }
    load()
  }, [activeTab, appUserId, companyId, supabase])

  /* ── Load Pending Approval count ───────────────────────── */

  useEffect(() => {
    if (activeTab !== 'pending' || !companyId) return
    async function load() {
      setPendingLoading(true)
      try {
        const { count } = await (supabase as any)
          .from('inspection_plans')
          .select('id', { count: 'exact', head: true })
          .eq('company_id', companyId)
          .eq('approval_status', 'pending')
          .eq('is_active', true)

        setPendingCount(count || 0)
      } catch (err) {
        console.error('Pending count error:', err)
      } finally {
        setPendingLoading(false)
      }
    }
    load()
  }, [activeTab, companyId, supabase])

  /* ── Load Workload (supervisor only) ───────────────────── */

  useEffect(() => {
    if (activeTab !== 'workload' || !companyId) return
    async function load() {
      setWorkloadLoading(true)
      try {
        // Get all inspectors in this company
        const { data: inspectors } = await (supabase as any)
          .from('app_users')
          .select('id, full_name')
          .eq('company_id', companyId)
          .eq('role', 'inspector')
          .eq('is_active', true)
          .order('full_name')

        if (!inspectors || inspectors.length === 0) {
          setWorkload([])
          setWorkloadLoading(false)
          return
        }

        const today = todayISO()
        const results: WorkloadInspector[] = []

        for (const insp of inspectors) {
          // Total events assigned
          const { count: total } = await (supabase as any)
            .from('inspection_events')
            .select('id', { count: 'exact', head: true })
            .eq('company_id', companyId)
            .eq('inspector_id', insp.id)

          // Done (approved)
          const { count: done } = await (supabase as any)
            .from('inspection_events')
            .select('id', { count: 'exact', head: true })
            .eq('company_id', companyId)
            .eq('inspector_id', insp.id)
            .eq('status', 'approved')

          // Overdue (event_date < today AND status NOT approved)
          const { count: overdue } = await (supabase as any)
            .from('inspection_events')
            .select('id', { count: 'exact', head: true })
            .eq('company_id', companyId)
            .eq('inspector_id', insp.id)
            .neq('status', 'approved')
            .lt('event_date', today)

          const t = total || 0
          const d = done || 0

          results.push({
            id: insp.id,
            full_name: insp.full_name,
            total: t,
            done: d,
            completionRate: t > 0 ? Math.round((d / t) * 100) : 0,
            overdue: overdue || 0,
          })
        }

        setWorkload(results)
      } catch (err) {
        console.error('Workload load error:', err)
      } finally {
        setWorkloadLoading(false)
      }
    }
    load()
  }, [activeTab, companyId, supabase])

  /* ── Load Inspector Quality (supervisor only) ────────────── */

  useEffect(() => {
    if (activeTab !== 'workload' || !companyId) return
    if (userRole !== 'supervisor' && userRole !== 'super_admin') return
    async function loadQuality() {
      setQualityLoading(true)
      try {
        const { data: { session } } = await supabase.auth.getSession()
        if (!session?.access_token) {
          setQualityLoading(false)
          return
        }

        const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
        const res = await fetch(`${backendUrl}/api/v1/analytics/inspector-quality/${companyId}`, {
          headers: { 'Authorization': `Bearer ${session.access_token}` },
        })

        if (!res.ok) {
          setInspectorQuality([])
          setQualityLoading(false)
          return
        }

        const data = await res.json()
        setInspectorQuality(data.inspectors || [])
      } catch (err) {
        console.error('Inspector quality load error:', err)
      } finally {
        setQualityLoading(false)
      }
    }
    loadQuality()
  }, [activeTab, companyId, supabase, userRole])

  /* ── Load Anomalies ────────────────────────────────────── */

  useEffect(() => {
    if (activeTab !== 'anomaly' || !companyId) return
    async function load() {
      setAnomaliesLoading(true)
      try {
        // Fetch anomalies with CML join
        const { data: anomalyRows } = await (supabase as any)
          .from('corrosion_anomalies')
          .select('*, cml_points!inner(location_label, equipment_id)')
          .eq('company_id', companyId)
          .order('anomaly_score', { ascending: false })

        if (!anomalyRows || anomalyRows.length === 0) {
          setAnomalies([])
          setAnomaliesLoading(false)
          return
        }

        // Get equipment tags for unique equipment IDs
        const equipIds = [...new Set(anomalyRows.map((a: any) => a.cml_points?.equipment_id).filter(Boolean))]
        const { data: equips } = await (supabase as any)
          .from('equipment')
          .select('id, tag')
          .in('id', equipIds)

        const tagMap: Record<string, string> = {}
        for (const eq of equips || []) {
          tagMap[eq.id] = eq.tag
        }

        // Build display rows
        const rows = anomalyRows.map((a: any) => {
          const desc = a.description || ''
          const rateMatch = desc.match(/rate ([\d.]+) mm/)
          return {
            id: a.id,
            cml_point_id: a.cml_point_id,
            equipment_id: a.cml_points?.equipment_id,
            location_label: a.cml_points?.location_label || '—',
            equipment_tag: tagMap[a.cml_points?.equipment_id] || '—',
            anomaly_score: a.anomaly_score,
            rate_mm_year: rateMatch ? parseFloat(rateMatch[1]) : null,
            detected_at: a.detected_at,
          }
        })

        setAnomalies(rows)
      } catch (err) {
        console.error('Anomaly load error:', err)
        setAnomalies([])
      } finally {
        setAnomaliesLoading(false)
      }
    }
    load()
  }, [activeTab, companyId, supabase])

  /* ── Load fleet risk snapshot ─────────────────────────────── */

  useEffect(() => {
    if (activeTab !== 'fleet' || !companyId) return
    async function load() {
      setFleetRiskLoading(true)
      try {
        const { data: snapshots } = await (supabase as any)
          .from('fleet_risk_snapshots')
          .select('risk_summary, computed_at')
          .eq('company_id', companyId)
          .order('computed_at', { ascending: false })
          .limit(1)

        if (snapshots && snapshots.length > 0) {
          const snap = snapshots[0]
          setFleetRiskData(snap.risk_summary)
          setFleetLastComputed(snap.computed_at)
        } else {
          setFleetRiskData(null)
          setFleetLastComputed(null)
        }
      } catch (err) {
        console.error('Fleet risk load error:', err)
        setFleetRiskData(null)
      } finally {
        setFleetRiskLoading(false)
      }
    }
    load()
  }, [activeTab, companyId, supabase])

  /* ── Load Remaining Life data ────────────────────────────── */

  useEffect(() => {
    if (activeTab !== 'rl' || !companyId) return
    async function load() {
      setRlLoading(true)
      try {
        // 1. Fetch all RL predictions (latest per CML)
        const { data: rlRows } = await (supabase as any)
          .from('rl_predictions')
          .select('id, cml_point_id, confidence_low, confidence_high, predicted_rl_years, computed_at')
          .eq('company_id', companyId)
          .order('computed_at', { ascending: false })

        // 2. Fetch all equipment + plant areas
        const { data: allEquips } = await (supabase as any)
          .from('equipment')
          .select('id, tag, type, area_id, plant_areas(name)')
          .eq('company_id', companyId)

        // 3. Fetch CML points
        const cmlIds = [...new Set((rlRows || []).map((r: any) => r.cml_point_id).filter(Boolean))]
        const { data: cmls } = cmlIds.length > 0
          ? await (supabase as any).from('cml_points').select('id, location_label, equipment_id').in('id', cmlIds)
          : { data: [] }

        const cmlMap: Record<string, any> = {}
        for (const c of cmls || []) {
          cmlMap[c.id] = c
        }

        // 4. Deduplicate RL rows per CML (latest computed_at)
        const seenCml = new Set<string>()
        const rlByEquip: Record<string, { confidence_low: number; location_label: string; computed_at: string }> = {}
        let latestComputed: string | null = null

        for (const r of rlRows || []) {
          if (!r.cml_point_id || seenCml.has(r.cml_point_id)) continue
          seenCml.add(r.cml_point_id)

          const cml = cmlMap[r.cml_point_id]
          const eqId = cml?.equipment_id
          if (!eqId) continue

          // Track latest computed_at overall
          if (r.computed_at && (!latestComputed || r.computed_at > latestComputed)) {
            latestComputed = r.computed_at
          }

          // Track min confidence_low per equipment (governing RL)
          const rlVal = r.confidence_low ?? r.predicted_rl_years
          if (rlVal === null && rlVal === undefined) continue

          if (!rlByEquip[eqId] || rlVal < rlByEquip[eqId].confidence_low) {
            rlByEquip[eqId] = {
              confidence_low: rlVal,
              location_label: cml.location_label || '—',
              computed_at: r.computed_at,
            }
          }
        }

        setRlLastComputed(latestComputed)

        // 5. Build table rows
        const withData: RLEquipmentRow[] = []
        const withoutData: RLEquipmentRow[] = []

        for (const eq of allEquips || []) {
          const rl = rlByEquip[eq.id]
          const row: RLEquipmentRow = {
            equipment_id: eq.id,
            tag: eq.tag || eq.id.slice(0, 8),
            type: eq.type || '',
            area_name: eq.plant_areas?.name || null,
            governing_cml: rl?.location_label ?? null,
            governing_rl_years: rl?.confidence_low ?? null,
            computed_at: rl?.computed_at ?? null,
          }
          if (rl) {
            withData.push(row)
          } else {
            withoutData.push(row)
          }
        }

        // Sort by governing_rl_years ascending (nulls last)
        withData.sort((a, b) => {
          if (a.governing_rl_years === null) return 1
          if (b.governing_rl_years === null) return -1
          return a.governing_rl_years - b.governing_rl_years
        })

        setRlData(withData)
        setRlNoData(withoutData)
      } catch (err) {
        console.error('RL load error:', err)
        setRlData([])
        setRlNoData([])
      } finally {
        setRlLoading(false)
      }
    }
    load()
  }, [activeTab, companyId, supabase])

  /* ── Recalculate anomalies ─────────────────────────────── */

  const handleRecalculate = useCallback(async () => {
    if (recalculating) return
    setRecalculating(true)
    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session?.access_token) {
        console.error('No auth session')
        return
      }

      const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const res = await fetch(`${backendUrl}/api/v1/analytics/anomalies/recalculate`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json',
        },
      })

      if (!res.ok) {
        console.error('Recalculate error:', res.status, await res.text())
        return
      }

      const result = await res.json()
      console.log('Recalculate result:', result)

      // Reload anomalies
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) return
      const { data: appUser } = await (supabase as any)
        .from('app_users')
        .select('company_id')
        .eq('auth_user_id', user.id)
        .maybeSingle()

      if (appUser?.company_id) {
        const { data: anomalyRows } = await (supabase as any)
          .from('corrosion_anomalies')
          .select('*, cml_points!inner(location_label, equipment_id)')
          .eq('company_id', appUser.company_id)
          .order('anomaly_score', { ascending: false })

        if (anomalyRows) {
          const equipIds = [...new Set(anomalyRows.map((a: any) => a.cml_points?.equipment_id).filter(Boolean))]
          const { data: equips } = await (supabase as any)
            .from('equipment')
            .select('id, tag')
            .in('id', equipIds)
          const tagMap: Record<string, string> = {}
          for (const eq of equips || []) tagMap[eq.id] = eq.tag

          setAnomalies(anomalyRows.map((a: any) => {
            const rateMatch = (a.description || '').match(/rate ([\d.]+) mm/)
            return {
              id: a.id,
              cml_point_id: a.cml_point_id,
              equipment_id: a.cml_points?.equipment_id,
              location_label: a.cml_points?.location_label || '—',
              equipment_tag: tagMap[a.cml_points?.equipment_id] || '—',
              anomaly_score: a.anomaly_score,
              rate_mm_year: rateMatch ? parseFloat(rateMatch[1]) : null,
              detected_at: a.detected_at,
            }
          }))
        }
      }
    } catch (err) {
      console.error('Recalculate error:', err)
    } finally {
      setRecalculating(false)
    }
  }, [supabase, recalculating])

  /* ── Recalculate fleet risk ─────────────────────────────── */

  const handleFleetRecalculate = useCallback(async () => {
    if (fleetRecalculating) return
    setFleetRecalculating(true)
    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session?.access_token) {
        console.error('No auth session')
        return
      }

      const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const res = await fetch(`${backendUrl}/api/v1/analytics/fleet-risk/${companyId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json',
        },
      })

      if (!res.ok) {
        console.error('Fleet risk recalculate error:', res.status, await res.text())
        return
      }

      const result = await res.json()
      setFleetRiskData(result)
      setFleetLastComputed(result.computed_at)
    } catch (err) {
      console.error('Fleet risk recalculate error:', err)
    } finally {
      setFleetRecalculating(false)
    }
  }, [companyId, fleetRecalculating, supabase])

  /* ── Helpers ──────────────────────────────────────────────── */

  function kpiZeros(): KPI[] {
    return [
      { label: 'Total Equipment', value: 0, icon: <LayoutDashboard className="h-5 w-5" />, color: 'blue', description: 'All registered equipment across all types' },
      { label: 'Due ≤ 90 Days', value: 0, icon: <Clock className="h-5 w-5" />, color: 'amber', description: 'Active plans with due date within 90 days' },
      { label: 'Due ≤ 60 Days', value: 0, icon: <Clock className="h-5 w-5" />, color: 'orange', description: 'Active plans with due date within 60 days' },
      { label: 'Due ≤ 30 Days', value: 0, icon: <AlertTriangle className="h-5 w-5" />, color: 'red', description: 'Active plans with due date within 30 days' },
      { label: 'Overdue', value: 0, icon: <AlertTriangle className="h-5 w-5" />, color: 'destructive', description: 'Active plans past their due date' },
      { label: 'Non-Compliant', value: 0, icon: <ShieldAlert className="h-5 w-5" />, color: 'destructive', description: 'Equipment with at least 1 overdue plan' },
    ]
  }

  function chartZeros(): ChartBar[] {
    return [
      { name: 'Safe', value: 0, fill: CHART_COLORS.safe },
      { name: 'Due 90 Days', value: 0, fill: CHART_COLORS.due90 },
      { name: 'Due 60 Days', value: 0, fill: CHART_COLORS.due60 },
      { name: 'Due 30 & Overdue', value: 0, fill: CHART_COLORS.due30 },
    ]
  }

  /* ── Color mapping ─────────────────────────────────────── */

  const colorMap: Record<string, { bg: string; text: string; border: string; iconBg: string }> = {
    blue:       { bg: 'bg-blue-50 dark:bg-blue-950/30',   text: 'text-blue-700 dark:text-blue-300',   border: 'border-blue-200 dark:border-blue-800',   iconBg: 'bg-blue-100 dark:bg-blue-900/40' },
    amber:      { bg: 'bg-amber-50 dark:bg-amber-950/30',  text: 'text-amber-700 dark:text-amber-300',  border: 'border-amber-200 dark:border-amber-800',  iconBg: 'bg-amber-100 dark:bg-amber-900/40' },
    orange:     { bg: 'bg-orange-50 dark:bg-orange-950/30', text: 'text-orange-700 dark:text-orange-300', border: 'border-orange-200 dark:border-orange-800', iconBg: 'bg-orange-100 dark:bg-orange-900/40' },
    red:        { bg: 'bg-red-50 dark:bg-red-950/30',     text: 'text-red-700 dark:text-red-300',     border: 'border-red-200 dark:border-red-800',     iconBg: 'bg-red-100 dark:bg-red-900/40' },
    destructive:{ bg: 'bg-red-50 dark:bg-red-950/30',     text: 'text-red-700 dark:text-red-300',     border: 'border-red-200 dark:border-red-800',     iconBg: 'bg-red-100 dark:bg-red-900/40' },
  }

  /* ── Render ─────────────────────────────────────────────── */

  return (
    <div className="px-8 py-8">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground mt-1">
          {userName ? `Welcome back, ${userName}` : 'Asset inspection & integrity overview'}
        </p>
      </div>

      {/* Tabs */}
      <div className="border-b border-border mb-6">
        <div className="flex gap-1 overflow-x-auto">
          {tabs.filter(tab => tab.key !== 'fleet' || ['supervisor', 'super_admin'].includes(userRole)).filter(tab => tab.key !== 'rl' || ['supervisor', 'super_admin'].includes(userRole)).map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={cn(
                'flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap',
                activeTab === tab.key
                  ? 'border-primary text-foreground'
                  : 'border-transparent text-muted-foreground hover:text-foreground',
              )}
            >
              {tab.icon}
              <span>{tab.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content — Overview */}
      {activeTab === 'overview' && (
        <>
          {/* Filter Bar */}
          <div className="flex flex-wrap items-center gap-3 mb-6">
            {/* Plant Area */}
            <div className="relative min-w-[180px]">
              <select
                value={filters.plantArea}
                onChange={(e) => setFilters(prev => ({ ...prev, plantArea: e.target.value }))}
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm appearance-none focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="">All Areas</option>
                {plantAreas.map(a => <option key={a} value={a}>{a}</option>)}
              </select>
            </div>

            {/* Fluid Service */}
            <div className="relative min-w-[180px]">
              <select
                value={filters.fluidService}
                onChange={(e) => setFilters(prev => ({ ...prev, fluidService: e.target.value }))}
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm appearance-none focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="">All Fluids</option>
                {fluidServices.map(f => <option key={f} value={f}>{f}</option>)}
              </select>
            </div>

            {/* Risk Category */}
            <div className="relative min-w-[180px]">
              <select
                value={filters.riskCategory}
                onChange={(e) => setFilters(prev => ({ ...prev, riskCategory: e.target.value }))}
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm appearance-none focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="">All Risk Categories</option>
                {riskCategories.map(r => <option key={r} value={r} className="capitalize">{r}</option>)}
              </select>
            </div>

            {/* Clear */}
            {(filters.plantArea || filters.fluidService || filters.riskCategory) && (
              <button
                onClick={() => setFilters({ plantArea: '', fluidService: '', riskCategory: '' })}
                className="inline-flex items-center gap-1 rounded-lg border border-border px-3 py-2 text-sm text-muted-foreground hover:bg-accent transition-colors"
              >
                Clear filters
              </button>
            )}
          </div>

          {/* KPI Cards */}
          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[1, 2, 3, 4, 5, 6].map(i => (
                <div key={i} className="h-32 bg-card border border-border rounded-xl animate-pulse" />
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {kpis.map((kpi) => {
                const c = colorMap[kpi.color] || colorMap.blue
                return (
                  <div
                    key={kpi.label}
                    className={cn(
                      'rounded-xl border p-5 transition-colors',
                      c.bg, c.border,
                    )}
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className={cn('rounded-lg p-2', c.iconBg)}>
                        <span className={c.text}>{kpi.icon}</span>
                      </div>
                    </div>
                    <p className={cn('text-3xl font-bold tabular-nums', c.text)}>
                      {kpi.value}
                    </p>
                    <p className="text-sm font-medium mt-1">{kpi.label}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">{kpi.description}</p>
                  </div>
                )
              })}
            </div>
          )}

          {/* Chart — Due Date Distribution */}
          {!loading && (
            <div className="mt-8">
              <div className="rounded-xl border border-border bg-card p-6">
                <h2 className="text-sm font-medium mb-1">Due Date Distribution</h2>
                <p className="text-xs text-muted-foreground mb-4">
                  Equipment count by due date zone
                </p>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
                      <CartesianGrid strokeDasharray="3 3" className="stroke-border/50" />
                      <XAxis
                        dataKey="name"
                        tick={{ fontSize: 12 }}
                        className="text-muted-foreground"
                      />
                      <YAxis
                        allowDecimals={false}
                        tick={{ fontSize: 12 }}
                        className="text-muted-foreground"
                      />
                      <Tooltip
                        contentStyle={{
                          fontSize: 12,
                          borderRadius: 8,
                          border: '1px solid var(--border)',
                          background: 'var(--card)',
                        }}
                        formatter={(value: any) => [`${value} equipment`, '']}
                      />
                      <Bar dataKey="value" radius={[6, 6, 0, 0]} maxBarSize={80}>
                        {chartData.map((entry, index) => (
                          <Cell key={index} fill={entry.fill} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          )}

          {/* Drill-Down Table */}
          <div className="mt-8">
            <h2 className="text-sm font-medium mb-1">Equipment Explorer</h2>
            <p className="text-xs text-muted-foreground mb-3">
              Click a row to drill down: Area → Equipment → Circuit → CML Point
            </p>
            <DrillDownTable />
          </div>

          {/* Refresh */}
          <div className="mt-6 flex items-center gap-3">
            <button
              onClick={loadData}
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-medium hover:bg-accent transition-colors disabled:opacity-50"
            >
              {loading ? (
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-muted-foreground border-t-transparent" />
              ) : (
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/></svg>
              )}
              Refresh
            </button>
            <span className="text-xs text-muted-foreground">
              Real-time data — no cache
            </span>
          </div>
        </>
      )}

      {/* Tab Content — My Worklist */}
      {activeTab === 'worklist' && (
        <div>
          <div className="mb-4">
            <h2 className="text-sm font-medium mb-1">My Inspection Worklist</h2>
            <p className="text-xs text-muted-foreground">
              {userRole === 'inspector'
                ? 'Inspections assigned to you — sorted by date (newest first)'
                : 'This view is for Inspector role'}
            </p>
          </div>

          {userRole !== 'inspector' ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <div className="rounded-full bg-muted p-4 mb-4">
                <Inbox className="h-6 w-6 text-muted-foreground" />
              </div>
              <h3 className="text-base font-medium text-muted-foreground mb-1">
                No worklist
              </h3>
              <p className="text-sm text-muted-foreground/60">
                This view is for Inspector role
              </p>
            </div>
          ) : worklistLoading ? (
            <div className="space-y-2">
              {[1, 2, 3, 4, 5].map(i => (
                <div key={i} className="h-12 bg-card border border-border rounded-lg animate-pulse" />
              ))}
            </div>
          ) : worklist.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <div className="rounded-full bg-muted p-4 mb-4">
                <CheckCircle2 className="h-6 w-6 text-green-500" />
              </div>
              <h3 className="text-base font-medium text-muted-foreground mb-1">
                All clear
              </h3>
              <p className="text-sm text-muted-foreground/60">
                No inspections assigned to you at this time
              </p>
            </div>
          ) : (
            <div className="rounded-xl border border-border overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-muted/50">
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Equipment Tag</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Inspection Type</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Event Date</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {worklist.map((item) => {
                    const statusConfig: Record<string, { bg: string; text: string; label: string }> = {
                      approved:  { bg: 'bg-green-100 dark:bg-green-900/30', text: 'text-green-700 dark:text-green-300', label: 'Approved' },
                      submitted: { bg: 'bg-amber-100 dark:bg-amber-900/30', text: 'text-amber-700 dark:text-amber-300', label: 'Submitted' },
                      draft:     { bg: 'bg-gray-100 dark:bg-gray-800',      text: 'text-gray-600 dark:text-gray-400',   label: 'Draft' },
                      rejected:  { bg: 'bg-red-100 dark:bg-red-900/30',     text: 'text-red-700 dark:text-red-300',     label: 'Rejected' },
                    }
                    const sc = statusConfig[item.status] || statusConfig.draft
                    return (
                      <tr key={item.id} className="border-t border-border hover:bg-muted/30 transition-colors">
                        <td className="px-4 py-3 font-medium">{item.equipment_tag}</td>
                        <td className="px-4 py-3">{formatInspectionType(item.inspection_type)}</td>
                        <td className="px-4 py-3 tabular-nums">{item.event_date}</td>
                        <td className="px-4 py-3">
                          <span className={cn('inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium', sc.bg, sc.text)}>
                            {sc.label}
                          </span>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
              <div className="px-4 py-2 bg-muted/30 border-t border-border text-xs text-muted-foreground">
                {worklist.length} inspection{worklist.length !== 1 ? 's' : ''} assigned
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab Content — Pending Approval */}
      {activeTab === 'pending' && (
        <div>
          <div className="mb-6">
            <h2 className="text-sm font-medium mb-1">Pending Approvals</h2>
            <p className="text-xs text-muted-foreground">
              Inspection plans awaiting engineer approval
            </p>
          </div>

          {pendingLoading ? (
            <div className="h-48 bg-card border border-border rounded-xl animate-pulse" />
          ) : (
            <div className="flex flex-col items-center py-8">
              <div className="rounded-2xl border border-border bg-card p-8 text-center max-w-md w-full">
                <div className="rounded-full bg-amber-50 dark:bg-amber-950/30 p-4 w-fit mx-auto mb-4">
                  <Clock className="h-8 w-8 text-amber-600 dark:text-amber-400" />
                </div>
                <p className="text-5xl font-bold tabular-nums text-amber-600 dark:text-amber-400 mb-2">
                  {pendingCount}
                </p>
                <p className="text-base font-medium text-muted-foreground mb-1">
                  Pending Approval{pendingCount !== 1 ? 's' : ''}
                </p>
                <p className="text-sm text-muted-foreground/60 mb-6">
                  {pendingCount === 0
                    ? 'All plans have been reviewed — great job!'
                    : 'Plans waiting for engineer review and approval'}
                </p>
                <Link
                  href="/plans"
                  className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground hover:opacity-90 transition-opacity"
                >
                  Go to Planning & Approval
                  <ExternalLink className="h-4 w-4" />
                </Link>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab Content — Workload */}
      {activeTab === 'workload' && (
        <div>
          <div className="mb-4">
            <h2 className="text-sm font-medium mb-1">Inspector Workload</h2>
            <p className="text-xs text-muted-foreground">
              {userRole === 'supervisor' || userRole === 'super_admin'
                ? 'Inspection completion overview by inspector'
                : 'This view is for Supervisor role'}
            </p>
          </div>

          {userRole !== 'supervisor' && userRole !== 'super_admin' ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <div className="rounded-full bg-muted p-4 mb-4">
                <Inbox className="h-6 w-6 text-muted-foreground" />
              </div>
              <h3 className="text-base font-medium text-muted-foreground mb-1">
                No access
              </h3>
              <p className="text-sm text-muted-foreground/60">
                This view is for Supervisor role
              </p>
            </div>
          ) : workloadLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[1, 2, 3].map(i => (
                <div key={i} className="h-48 bg-card border border-border rounded-xl animate-pulse" />
              ))}
            </div>
          ) : workload.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <div className="rounded-full bg-muted p-4 mb-4">
                <UserCircle className="h-6 w-6 text-muted-foreground" />
              </div>
              <h3 className="text-base font-medium text-muted-foreground mb-1">
                No inspectors
              </h3>
              <p className="text-sm text-muted-foreground/60">
                No active inspectors found in your company
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {workload.map((insp) => (
                <div
                  key={insp.id}
                  className="rounded-xl border border-border bg-card p-5 transition-colors hover:border-primary/30"
                >
                  <div className="flex items-center gap-3 mb-4">
                    <div className="rounded-full bg-blue-100 dark:bg-blue-900/40 p-2">
                      <UserCircle className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                    </div>
                    <div>
                      <p className="font-medium text-sm">{insp.full_name}</p>
                      <p className="text-xs text-muted-foreground">Inspector</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3 mb-4">
                    <div>
                      <p className="text-2xl font-bold tabular-nums">{insp.total}</p>
                      <p className="text-xs text-muted-foreground">Total Assigned</p>
                    </div>
                    <div>
                      <p className="text-2xl font-bold tabular-nums text-green-600 dark:text-green-400">{insp.done}</p>
                      <p className="text-xs text-muted-foreground">Completed</p>
                    </div>
                  </div>

                  {/* Completion rate bar */}
                  <div className="mb-3">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-muted-foreground">Completion Rate</span>
                      <span className="text-xs font-medium tabular-nums">{insp.completionRate}%</span>
                    </div>
                    <div className="h-2 rounded-full bg-muted overflow-hidden">
                      <div
                        className={cn(
                          'h-full rounded-full transition-all',
                          insp.completionRate >= 80 ? 'bg-green-500' :
                          insp.completionRate >= 50 ? 'bg-amber-500' : 'bg-red-500'
                        )}
                        style={{ width: `${insp.completionRate}%` }}
                      />
                    </div>
                  </div>

                  {insp.overdue > 0 && (
                    <div className="flex items-center gap-1.5 rounded-lg bg-red-50 dark:bg-red-950/30 px-3 py-1.5">
                      <AlertTriangle className="h-3.5 w-3.5 text-red-500" />
                      <span className="text-xs font-medium text-red-700 dark:text-red-300">
                        {insp.overdue} overdue
                      </span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Data Quality Scores — supervisor/super_admin only */}
          {(userRole === 'supervisor' || userRole === 'super_admin') && (
            <div className="mt-8">
              <div className="mb-4">
                <h2 className="text-sm font-medium mb-1">Data Quality Scores</h2>
                <p className="text-xs text-muted-foreground">
                  Based on anomaly detection per inspector (Supervisor view only)
                </p>
              </div>

              {qualityLoading ? (
                <div className="rounded-xl border border-border">
                  {[1, 2, 3].map(i => (
                    <div key={i} className="h-14 bg-card border-b border-border animate-pulse last:border-b-0" />
                  ))}
                </div>
              ) : inspectorQuality.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <div className="rounded-full bg-muted p-4 mb-4">
                    <CheckCircle2 className="h-6 w-6 text-muted-foreground" />
                  </div>
                  <h3 className="text-base font-medium text-muted-foreground mb-1">
                    No quality data
                  </h3>
                  <p className="text-sm text-muted-foreground/60">
                    No inspector quality metrics available yet
                  </p>
                </div>
              ) : (
                <div className="rounded-xl border border-border overflow-hidden">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-muted/50">
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">Inspector</th>
                        <th className="text-right px-4 py-3 font-medium text-muted-foreground">Total Readings</th>
                        <th className="text-right px-4 py-3 font-medium text-muted-foreground">Anomalies Flagged</th>
                        <th className="text-right px-4 py-3 font-medium text-muted-foreground">Quality Score</th>
                        <th className="text-center px-4 py-3 font-medium text-muted-foreground">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {inspectorQuality.map((iq: any) => (
                        <tr key={iq.inspector_id} className="border-t border-border hover:bg-muted/30">
                          <td className="px-4 py-3 font-medium">{iq.full_name}</td>
                          <td className="px-4 py-3 text-right tabular-nums">{iq.total_readings === 0 ? '—' : iq.total_readings}</td>
                          <td className={cn(
                            'px-4 py-3 text-right tabular-nums font-medium',
                            iq.anomaly_count > 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'
                          )}>
                            {iq.anomaly_count}
                          </td>
                          <td className="px-4 py-3 text-right tabular-nums font-medium">
                            {iq.quality_score !== null ? `${iq.quality_score}%` : '—'}
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className={cn(
                              'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
                              iq.badge === 'good' && 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
                              iq.badge === 'fair' && 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
                              iq.badge === 'needs_review' && 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300',
                              iq.badge === 'no_data' && 'bg-gray-100 text-gray-800 dark:bg-gray-900/40 dark:text-gray-300',
                            )}>
                              {iq.badge === 'good' && 'Good'}
                              {iq.badge === 'fair' && 'Fair'}
                              {iq.badge === 'needs_review' && 'Needs Review'}
                              {iq.badge === 'no_data' && 'No Data'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Tab Content — Anomaly Detection */}
      {activeTab === 'anomaly' && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-medium mb-1">Corrosion Anomaly Detection</h2>
              <p className="text-xs text-muted-foreground">
                Readings flagged as anomalous by z-score analysis — sorted by severity
              </p>
            </div>
            <button
              onClick={handleRecalculate}
              disabled={recalculating}
              className="inline-flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-medium hover:bg-accent transition-colors disabled:opacity-50"
            >
              <RefreshCw className={cn('h-4 w-4', recalculating && 'animate-spin')} />
              {recalculating ? 'Recalculating...' : 'Recalculate'}
            </button>
          </div>

          {anomaliesLoading ? (
            <div className="rounded-xl border border-border">
              {[1, 2, 3].map(i => (
                <div key={i} className="h-16 bg-card border-b border-border animate-pulse last:border-b-0" />
              ))}
            </div>
          ) : anomalies.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <div className="rounded-full bg-muted p-4 mb-4">
                <AlertTriangle className="h-6 w-6 text-muted-foreground" />
              </div>
              <h3 className="text-base font-medium text-muted-foreground mb-1">
                No anomalies detected yet
              </h3>
              <p className="text-sm text-muted-foreground/60 max-w-sm">
                Click Recalculate to run z-score anomaly detection across all CML points
              </p>
            </div>
          ) : (
            <div className="rounded-xl border border-border overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-muted/50">
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Equipment Tag</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">CML Location</th>
                    <th className="text-right px-4 py-3 font-medium text-muted-foreground">Anomaly Score</th>
                    <th className="text-right px-4 py-3 font-medium text-muted-foreground">Rate (mm/yr)</th>
                    <th className="text-left px-4 py-3 font-medium text-muted-foreground">Detected</th>
                  </tr>
                </thead>
                <tbody>
                  {anomalies.map((a: any) => (
                    <tr
                      key={a.id}
                      onClick={() => {
                        if (a.equipment_id) {
                          window.location.href = `/equipment/${a.equipment_id}`
                        }
                      }}
                      className="border-t border-border hover:bg-muted/30 transition-colors cursor-pointer"
                    >
                      <td className="px-4 py-3 font-medium">{a.equipment_tag}</td>
                      <td className="px-4 py-3 text-muted-foreground">{a.location_label}</td>
                      <td className="px-4 py-3 text-right">
                        <span className="inline-flex items-center rounded-full bg-red-100 dark:bg-red-900/30 px-2.5 py-0.5 text-xs font-medium text-red-700 dark:text-red-300">
                          {Number(a.anomaly_score).toFixed(2)}σ
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums">
                        {a.rate_mm_year ? `${a.rate_mm_year.toFixed(4)}` : '—'}
                      </td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">
                        {a.detected_at ? new Date(a.detected_at).toLocaleDateString('en-GB', {
                          day: 'numeric', month: 'short', year: 'numeric',
                        }) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="px-4 py-2 bg-muted/30 border-t border-border text-xs text-muted-foreground">
                {anomalies.length} anomaly{anomalies.length !== 1 ? 'ies' : 'y'} found — sorted by severity
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab Content — Remaining Life */}
      {activeTab === 'rl' && (
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold">Remaining Life Overview</h2>
              <p className="text-sm text-muted-foreground mt-0.5">
                Governing RL per equipment based on most critical CML (confidence_low threshold)
              </p>
            </div>
            {rlLastComputed && (
              <div className="shrink-0 text-right">
                <p className="text-xs text-muted-foreground">
                  Last computed: {new Date(rlLastComputed).toLocaleDateString('en-GB', {
                    day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
                  })}
                </p>
              </div>
            )}
            {!rlLastComputed && !rlLoading && (
              <div className="shrink-0 text-right">
                <p className="text-xs text-muted-foreground">Not yet computed</p>
              </div>
            )}
          </div>

          {rlLoading ? (
            <div className="rounded-xl border border-border">
              {[1, 2, 3, 4].map(i => (
                <div key={i} className="h-14 bg-card border-b border-border animate-pulse last:border-b-0" />
              ))}
            </div>
          ) : rlData.length === 0 && rlNoData.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <div className="rounded-full bg-muted p-4 mb-4">
                <TrendingDown className="h-6 w-6 text-muted-foreground" />
              </div>
              <h3 className="text-base font-medium text-muted-foreground mb-1">
                No equipment data found
              </h3>
              <p className="text-sm text-muted-foreground/60 max-w-sm">
                Run Remaining Life calculation from an equipment detail page to populate RL predictions.
              </p>
            </div>
          ) : (
            <>
              {/* ── Summary Cards ── */}
              <div className="grid grid-cols-4 gap-4">
                {([
                  { label: 'Total Equipment', value: rlData.length + rlNoData.length, color: 'text-foreground', bg: 'bg-card', icon: <LayoutDashboard className="h-5 w-5" /> },
                  { label: 'Critical (< 2 yr)', value: rlData.filter(r => r.governing_rl_years !== null && r.governing_rl_years < 2).length, color: 'text-red-600', bg: 'bg-red-50 dark:bg-red-950/20', icon: <AlertTriangle className="h-5 w-5" /> },
                  { label: 'Monitor (2-5 yr)', value: rlData.filter(r => r.governing_rl_years !== null && r.governing_rl_years >= 2 && r.governing_rl_years <= 5).length, color: 'text-amber-600', bg: 'bg-amber-50 dark:bg-amber-950/20', icon: <Clock className="h-5 w-5" /> },
                  { label: 'Adequate (> 5 yr)', value: rlData.filter(r => r.governing_rl_years !== null && r.governing_rl_years > 5).length, color: 'text-green-600', bg: 'bg-green-50 dark:bg-green-950/20', icon: <CheckCircle2 className="h-5 w-5" /> },
                ] as const).map((card, i) => (
                  <div key={i} className={`${card.bg} border border-border/70 rounded-xl p-4 flex items-center gap-3`}>
                    <div className={card.color}>{card.icon}</div>
                    <div>
                      <p className="text-2xl font-bold tabular-nums">{card.value}</p>
                      <p className="text-xs text-muted-foreground">{card.label}</p>
                    </div>
                  </div>
                ))}
              </div>

              {/* ── Main Table ── */}
              {rlData.length > 0 && (
                <div className="rounded-xl border border-border overflow-hidden">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border bg-muted/30">
                        <th className="px-4 py-3 text-left font-medium text-muted-foreground text-xs uppercase tracking-wider">Equipment Tag</th>
                        <th className="px-4 py-3 text-left font-medium text-muted-foreground text-xs uppercase tracking-wider">Area</th>
                        <th className="px-4 py-3 text-left font-medium text-muted-foreground text-xs uppercase tracking-wider">Governing CML</th>
                        <th className="px-4 py-3 text-left font-medium text-muted-foreground text-xs uppercase tracking-wider">Remaining Life</th>
                        <th className="px-4 py-3 text-left font-medium text-muted-foreground text-xs uppercase tracking-wider">Risk</th>
                        <th className="px-4 py-3 text-left font-medium text-muted-foreground text-xs uppercase tracking-wider">Last Computed</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rlData.map((row) => {
                        const rl = row.governing_rl_years
                        const riskLevel = rl !== null && rl < 2 ? 'critical' : rl !== null && rl <= 5 ? 'monitor' : 'adequate'
                        const barColor = riskLevel === 'critical' ? '#ef4444' : riskLevel === 'monitor' ? '#f59e0b' : '#22c55e'
                        const barWidth = rl !== null ? Math.min(Math.max((rl / 20) * 100, 5), 100) : 0
                        return (
                          <tr key={row.equipment_id || row.tag} className="border-b border-border last:border-0 hover:bg-muted/20 transition-colors">
                            <td className="px-4 py-3">
                              <Link href={`/equipment/${row.equipment_id}`} className="font-medium text-primary hover:underline">
                                {row.tag}
                              </Link>
                            </td>
                            <td className="px-4 py-3 text-muted-foreground">{row.area_name || '—'}</td>
                            <td className="px-4 py-3 text-muted-foreground">{row.governing_cml || '—'}</td>
                            <td className="px-4 py-3">
                              <div className="flex items-center gap-2">
                                <span className="tabular-nums font-medium min-w-[3.5rem]">
                                  {rl !== null ? `${rl.toFixed(1)} yr` : '—'}
                                </span>
                                <div className="flex-1 max-w-[100px] h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                                  <div
                                    className="h-full rounded-full transition-all"
                                    style={{ width: `${barWidth}%`, backgroundColor: barColor }}
                                  />
                                </div>
                              </div>
                            </td>
                            <td className="px-4 py-3">
                              {rl !== null ? (
                                <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${
                                  riskLevel === 'critical' ? 'bg-red-100 text-red-700 dark:bg-red-950/40 dark:text-red-400' :
                                  riskLevel === 'monitor' ? 'bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400' :
                                  'bg-green-100 text-green-700 dark:bg-green-950/40 dark:text-green-400'
                                }`}>
                                  {riskLevel === 'critical' ? 'Critical' : riskLevel === 'monitor' ? 'Monitor' : 'Adequate'}
                                </span>
                              ) : (
                                <span className="text-xs text-muted-foreground">—</span>
                              )}
                            </td>
                            <td className="px-4 py-3 text-xs text-muted-foreground">
                              {row.computed_at ? new Date(row.computed_at).toLocaleDateString('en-GB', {
                                day: 'numeric', month: 'short', year: 'numeric',
                              }) : '—'}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                  <div className="px-4 py-2 bg-muted/30 border-t border-border text-xs text-muted-foreground">
                    {rlData.length} equipment{rlData.length !== 1 ? 's' : ''} with RL data — sorted by remaining life ascending
                  </div>
                </div>
              )}

              {/* ── No RL Data Section ── */}
              {rlNoData.length > 0 && (
                <div className="space-y-3">
                  <h3 className="text-sm font-medium text-muted-foreground">Equipment Without RL Data</h3>
                  <div className="rounded-xl border border-border overflow-hidden">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-border bg-muted/30">
                          <th className="px-4 py-3 text-left font-medium text-muted-foreground text-xs uppercase tracking-wider">Tag</th>
                          <th className="px-4 py-3 text-left font-medium text-muted-foreground text-xs uppercase tracking-wider">Area</th>
                          <th className="px-4 py-3 text-left font-medium text-muted-foreground text-xs uppercase tracking-wider">Reason</th>
                        </tr>
                      </thead>
                      <tbody>
                        {rlNoData.map((row) => (
                          <tr key={row.equipment_id || row.tag} className="border-b border-border last:border-0 hover:bg-muted/20 transition-colors">
                            <td className="px-4 py-3">
                              <Link href={`/equipment/${row.equipment_id}`} className="font-medium text-muted-foreground hover:text-primary hover:underline">
                                {row.tag}
                              </Link>
                            </td>
                            <td className="px-4 py-3 text-muted-foreground">{row.area_name || '—'}</td>
                            <td className="px-4 py-3">
                              <span className="inline-flex items-center gap-1.5 rounded-full bg-muted px-2.5 py-0.5 text-xs text-muted-foreground">
                                No RL data
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    <div className="px-4 py-2 bg-muted/30 border-t border-border text-xs text-muted-foreground">
                      {rlNoData.length} equipment{rlNoData.length !== 1 ? 's' : ''} without RL predictions — run calculation per equipment
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Tab Content — Fleet Risk */}
      {activeTab === 'fleet' && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-medium mb-1">Fleet-Wide Risk Heatmap</h2>
              <p className="text-xs text-muted-foreground">
                Combines physical condition (RL proximity) and material vulnerability (DM Screener) per area
              </p>
            </div>
            <button
              onClick={handleFleetRecalculate}
              disabled={fleetRecalculating}
              className="inline-flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-medium hover:bg-accent transition-colors disabled:opacity-50"
            >
              <RefreshCw className={cn('h-4 w-4', fleetRecalculating && 'animate-spin')} />
              {fleetRecalculating ? 'Recalculating...' : 'Recalculate Fleet Risk'}
            </button>
          </div>

          {fleetRiskLoading ? (
            <div className="rounded-xl border border-border">
              {[1, 2, 3].map(i => (
                <div key={i} className="h-16 bg-card border-b border-border animate-pulse last:border-b-0" />
              ))}
            </div>
          ) : !fleetRiskData || !fleetRiskData.areas || fleetRiskData.areas.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <div className="rounded-full bg-muted p-4 mb-4">
                <ShieldAlert className="h-6 w-6 text-muted-foreground" />
              </div>
              <h3 className="text-base font-medium text-muted-foreground mb-1">
                No fleet risk data yet
              </h3>
              <p className="text-sm text-muted-foreground/60 max-w-sm">
                Click Recalculate Fleet Risk to compute risk scores across all plant areas.
              </p>
            </div>
          ) : (() => {
            const areas = fleetRiskData.areas as any[]
            const allInsufficient = areas.every((a: any) => a.insufficient_data)
            const criticalCount = areas.filter(a => a.risk_level === 'critical').length
            const highCount = areas.filter(a => a.risk_level === 'high').length
            const insufficientCount = areas.filter(a => a.insufficient_data).length

            if (allInsufficient) {
              return (
                <div className="flex flex-col items-center justify-center py-20 text-center">
                  <div className="rounded-full bg-muted p-4 mb-4">
                    <ShieldAlert className="h-6 w-6 text-muted-foreground" />
                  </div>
                  <h3 className="text-base font-medium text-muted-foreground mb-1">
                    All areas lack sufficient data
                  </h3>
                  <p className="text-sm text-muted-foreground/60 max-w-sm">
                    All areas lack sufficient RL or DM data to compute risk scores.
                  </p>
                </div>
              )
            }

            const riskBadge = (level: string | null) => {
              if (!level) return 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
              if (level === 'critical') return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
              if (level === 'high') return 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300'
              if (level === 'medium') return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300'
              return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
            }

            const barColor = (level: string | null) => {
              if (!level || level === 'low') return 'bg-green-500'
              if (level === 'medium') return 'bg-yellow-500'
              if (level === 'high') return 'bg-amber-500'
              return 'bg-red-500'
            }

            return (
              <>
                {/* Summary Cards */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
                  <div className="rounded-xl border border-border bg-card p-4">
                    <p className="text-xs text-muted-foreground mb-1">Total Areas</p>
                    <p className="text-2xl font-bold tabular-nums">{areas.length}</p>
                  </div>
                  <div className="rounded-xl border border-border bg-card p-4">
                    <p className="text-xs text-muted-foreground mb-1">Critical</p>
                    <p className="text-2xl font-bold tabular-nums text-red-600 dark:text-red-400">{criticalCount}</p>
                  </div>
                  <div className="rounded-xl border border-border bg-card p-4">
                    <p className="text-xs text-muted-foreground mb-1">High</p>
                    <p className="text-2xl font-bold tabular-nums text-amber-600 dark:text-amber-400">{highCount}</p>
                  </div>
                  <div className="rounded-xl border border-border bg-card p-4">
                    <p className="text-xs text-muted-foreground mb-1">Insufficient Data</p>
                    <p className="text-2xl font-bold tabular-nums text-slate-500">{insufficientCount}</p>
                  </div>
                </div>

                {/* Area Table */}
                <div className="rounded-xl border border-border overflow-hidden">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-muted/50">
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">Area Name</th>
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">Risk Level</th>
                        <th className="text-right px-4 py-3 font-medium text-muted-foreground">Score</th>
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">Physical Signal</th>
                        <th className="text-left px-4 py-3 font-medium text-muted-foreground">DM Signal</th>
                        <th className="text-right px-4 py-3 font-medium text-muted-foreground">CML w/ RL</th>
                        <th className="text-right px-4 py-3 font-medium text-muted-foreground">Equip w/ DM</th>
                      </tr>
                    </thead>
                    <tbody>
                      {areas.map((area: any, idx: number) => (
                        <tr
                          key={area.area_id || idx}
                          className={cn(
                            'border-t border-border transition-colors',
                            area.insufficient_data ? 'opacity-50' : 'hover:bg-muted/30'
                          )}
                        >
                          <td className="px-4 py-3 font-medium">{area.area_name}</td>
                          <td className="px-4 py-3">
                            <span className={cn(
                              'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
                              area.insufficient_data
                                ? 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
                                : riskBadge(area.risk_level)
                            )}>
                              {area.insufficient_data ? 'Insufficient Data' : (area.risk_level ? area.risk_level.charAt(0).toUpperCase() + area.risk_level.slice(1) : '—')}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right tabular-nums">
                            {area.risk_score != null ? area.risk_score.toFixed(1) : '—'}
                          </td>
                          <td className="px-4 py-3">
                            {area.insufficient_data ? (
                              <span className="text-muted-foreground">—</span>
                            ) : (
                              <div className="flex items-center gap-2">
                                <div className="w-20 h-2 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
                                  <div
                                    className={cn('h-full rounded-full', barColor(area.risk_level))}
                                    style={{ width: `${Math.round((area.physical_signal || 0) * 100)}%` }}
                                  />
                                </div>
                                <span className="text-xs tabular-nums w-8 text-right">
                                  {Math.round((area.physical_signal || 0) * 100)}%
                                </span>
                              </div>
                            )}
                          </td>
                          <td className="px-4 py-3">
                            {area.insufficient_data ? (
                              <span className="text-muted-foreground">—</span>
                            ) : (
                              <div className="flex items-center gap-2">
                                <div className="w-20 h-2 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
                                  <div
                                    className={cn('h-full rounded-full', barColor(area.risk_level))}
                                    style={{ width: `${Math.round((area.dm_signal || 0) * 100)}%` }}
                                  />
                                </div>
                                <span className="text-xs tabular-nums w-8 text-right">
                                  {Math.round((area.dm_signal || 0) * 100)}%
                                </span>
                              </div>
                            )}
                          </td>
                          <td className="px-4 py-3 text-right tabular-nums">
                            {area.cml_count_with_rl ?? '—'}
                          </td>
                          <td className="px-4 py-3 text-right tabular-nums">
                            {area.equipment_count_with_dm ?? '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <div className="px-4 py-2 bg-muted/30 border-t border-border text-xs text-muted-foreground flex items-center justify-between">
                    <span>{areas.length} area{areas.length !== 1 ? 's' : ''} assessed</span>
                    {fleetLastComputed && (
                      <span>Last computed: {new Date(fleetLastComputed).toLocaleString('en-GB', {
                        day: 'numeric', month: 'short', year: 'numeric',
                        hour: '2-digit', minute: '2-digit',
                      })}</span>
                    )}
                  </div>
                </div>
              </>
            )
          })()}
        </div>
      )}
    </div>
  )
}
