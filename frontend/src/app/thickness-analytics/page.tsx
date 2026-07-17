'use client'
import { useEffect, useState, useCallback, useRef, Suspense } from 'react'
import AppLayout from '@/components/layout/app-layout'
import { createClient } from '@/lib/supabase/client'
import { Loader2, Download, Search } from 'lucide-react'
import { toast } from 'sonner'
import { CHART } from '@/lib/chart-theme'
import ThkTabContent from '@/components/ThkTabContent'
import { useSearchParams } from 'next/navigation'

// ── Types ─────────────────────────────────────────────────────────────────
interface ThkRow {
  cml_id: string
  plant: string
  equipment_tag: string
  equipment_type: string
  iso_number: string
  fluid: string
  object_type: string
  part: string
  no_cml: string
  location_deg: number | null
  nominal_thk: number
  measured_thk: number
  t_min: number
  thk_loss_pct: number
  cr_mm_yr: number
  remaining_life_yr: number
  priority: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | '—'
  status_thk: 'RETIRE' | 'WARNING' | 'OK' | '—'
  latest_date: string
}

type TabId = 'overview' | 'location' | 'priority' | 'trend' | 'master'
type EqType = 'piping' | 'equipment'

const PRIO_COLORS: Record<string, string> = {
  CRITICAL: '#EF4444', HIGH: '#F59E0B', MEDIUM: '#EAB308', LOW: '#22C55E',
}
const STATUS_COLORS: Record<string, string> = {
  RETIRE: '#EF4444', WARNING: '#F59E0B', OK: '#22C55E',
}

function ensurePlotly(): Promise<void> {
  return new Promise(resolve => {
    if ((window as any).Plotly) return resolve()
    const s = document.createElement('script')
    s.src = 'https://cdn.plot.ly/plotly-2.35.2.min.js'
    s.onload = () => resolve()
    document.head.appendChild(s)
  })
}

// ── Component (inner — wrapped w/ Suspense for useSearchParams) ────────────
function ThicknessAnalyticsInner() {
  const supabase = createClient()
  const [companyId, setCompanyId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState<ThkRow[]>([])
  const [activeTab, setActiveTab] = useState<TabId>('overview')
  const [eqType, setEqType] = useState<EqType>('piping')
  const [filterPlant, setFilterPlant] = useState('All')
  const [filterPriority, setFilterPriority] = useState('All')
  const [filterTag, setFilterTag] = useState('')
  const [filterFluid, setFilterFluid] = useState('All')
  const [searchText, setSearchText] = useState('')

  // Load profile
  useEffect(() => {
    async function init() {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) return
      const { data: profile } = await (supabase as any)
        .from('app_users')
        .select('company_id')
        .eq('auth_user_id', user.id)
        .single()
      if (profile) setCompanyId(profile.company_id)
    }
    init()
  }, [supabase])

  // Read ?tag= from URL
  const searchParams = useSearchParams()
  useEffect(() => {
    const tag = searchParams.get('tag')
    if (tag) setFilterTag(tag)
  }, [searchParams])

  // Fetch thickness data
  const fetchData = useCallback(async () => {
    if (!companyId) return
    setLoading(true)
    try {
      const { data: { session } } = await supabase.auth.getSession()
      const res = await fetch(`/api/backend/api/v1/thickness/data/${companyId}`, {
        headers: { Authorization: `Bearer ${session?.access_token}` },
      })
      const json = await res.json()
      setData(json.data || [])
    } catch {
      toast.error('Failed to load thickness data')
    } finally {
      setLoading(false)
    }
  }, [companyId, supabase])

  useEffect(() => {
    if (companyId) fetchData()
  }, [companyId, fetchData])

  // Filtered data
  const filtered = data.filter(r => {
    const matchType = eqType === 'piping'
      ? r.equipment_type === 'piping'
      : r.equipment_type !== 'piping'
    const matchPlant = filterPlant === 'All' || r.plant === filterPlant
    const matchPriority = filterPriority === 'All' || r.priority === filterPriority
    const matchFluid = filterFluid === 'All' || r.fluid === filterFluid
    const matchTag = !filterTag || r.equipment_tag === filterTag
    const matchSearch = !searchText ||
      r.iso_number?.toLowerCase().includes(searchText.toLowerCase()) ||
      r.no_cml?.toLowerCase().includes(searchText.toLowerCase()) ||
      r.object_type?.toLowerCase().includes(searchText.toLowerCase()) ||
      r.equipment_tag?.toLowerCase().includes(searchText.toLowerCase())
    return matchType && matchPlant && matchPriority && matchFluid && matchTag && matchSearch
  })

  // KPI counts
  const total = filtered.length
  const critical = filtered.filter(r => r.priority === 'CRITICAL').length
  const high = filtered.filter(r => r.priority === 'HIGH').length
  const retire = filtered.filter(r => r.status_thk === 'RETIRE').length
  const avgLoss = filtered.length ? (filtered.reduce((s, r) => s + r.thk_loss_pct, 0) / filtered.length).toFixed(1) + '%' : 'N/A'
  const rls = filtered.filter(r => r.remaining_life_yr < 99)
  const avgRL = rls.length ? (rls.reduce((s, r) => s + r.remaining_life_yr, 0) / rls.length).toFixed(1) + ' yr' : 'N/A'

  // Unique plants & fluids
  const plants = ['All', ...Array.from(new Set(data.map(r => r.plant))).sort()]
  const fluids = ['All', ...Array.from(new Set(data.map(r => r.fluid).filter(Boolean))).sort()]

  const TABS: { id: TabId; label: string }[] = [
    { id: 'overview', label: '📋 Overview' },
    { id: 'location', label: '🧭 Location' },
    { id: 'priority', label: '⚠️ Priority & RL' },
    { id: 'trend', label: '📉 Trend & Projection' },
    { id: 'master', label: '📑 Master Table' },
  ]

  if (loading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <span className="ml-3 text-muted-foreground">Loading {data.length > 0 ? data.length + ' CMLs...' : 'thickness data...'}</span>
        </div>
      </AppLayout>
    )
  }

  return (
    <AppLayout>
      <div className="space-y-4">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Thickness Analytics</h1>
            <p className="text-sm text-muted-foreground">UT Measurement — API 570 / API 510</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setEqType('piping')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${eqType === 'piping' ? 'bg-primary text-white' : 'border border-border hover:bg-muted'}`}
            >Piping</button>
            <button
              onClick={() => setEqType('equipment')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${eqType === 'equipment' ? 'bg-primary text-white' : 'border border-border hover:bg-muted'}`}
            >Equipment</button>
          </div>
        </div>

        {/* Section label */}
        <div className="text-xs font-bold uppercase tracking-widest text-muted-foreground border-b border-border pb-2">
          {eqType === 'piping' ? 'Piping' : 'Equipment'} Thickness Health
        </div>

        {/* KPI Cards */}
        <div className="flex gap-3 overflow-x-auto pb-1">
          {[
            { label: 'Total CML', value: total.toLocaleString(), color: CHART.primary },
            { label: '🔴 CRITICAL', value: critical.toLocaleString(), sub: 'RL ≤ 2yr', color: '#EF4444' },
            { label: '🟠 HIGH', value: high.toLocaleString(), sub: 'RL 2-5yr', color: '#F59E0B' },
            { label: 'Retire', value: retire.toLocaleString(), sub: '≤ t_min', color: '#EF4444' },
            { label: 'Avg Loss', value: avgLoss, color: '#EAB308' },
            { label: 'CR > 0.5', value: filtered.filter(r => r.cr_mm_yr > 0.5).length.toLocaleString(), color: '#EF4444' },
            { label: 'Avg Rem.Life', value: avgRL, color: '#22C55E' },
          ].map(kpi => (
            <div key={kpi.label} className="flex-shrink-0 min-w-[140px] bg-card border border-border rounded-xl p-3 shadow-sm" style={{ borderLeftWidth: '3px', borderLeftColor: kpi.color }}>
              <p className="text-xs text-muted-foreground">{kpi.label}</p>
              {kpi.sub && <p className="text-[10px] text-muted-foreground">{kpi.sub}</p>}
              <p className="text-xl font-bold mt-1" style={{ color: kpi.color }}>{kpi.value}</p>
            </div>
          ))}
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-2 items-center">
          <div className="relative flex-1 min-w-48">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input type="text" value={searchText} onChange={e => setSearchText(e.target.value)}
              placeholder="Search ISO, CML, Object, Tag..."
              className="w-full pl-9 pr-3 py-1.5 text-sm border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50" />
          </div>
          <select value={filterPlant} onChange={e => setFilterPlant(e.target.value)}
            className="px-3 py-1.5 text-sm border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50">
            {plants.map(p => <option key={p} value={p}>{p === 'All' ? 'All Plants' : p}</option>)}
          </select>
          <select value={filterFluid} onChange={e => setFilterFluid(e.target.value)}
            className="px-3 py-1.5 text-sm border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50">
            {fluids.map(f => <option key={f} value={f}>{f === 'All' ? 'All Fluids' : f}</option>)}
          </select>
          <select value={filterPriority} onChange={e => setFilterPriority(e.target.value)}
            className="px-3 py-1.5 text-sm border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50">
            {['All','CRITICAL','HIGH','MEDIUM','LOW'].map(p => <option key={p} value={p}>{p === 'All' ? 'All Priorities' : p}</option>)}
          </select>
          {(filterTag || filterFluid !== 'All' || filterPlant !== 'All' || filterPriority !== 'All' || searchText) && (
            <button onClick={() => { setFilterTag(''); setFilterFluid('All'); setFilterPlant('All'); setFilterPriority('All'); setSearchText('') }}
              className="px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground border border-border rounded-lg hover:bg-muted transition-colors">
              Clear filters
            </button>
          )}
          {filterTag && (
            <span className="px-3 py-1 text-xs bg-primary/10 text-primary rounded-full font-medium">
              Filtered: {filterTag}
            </span>
          )}
        </div>

        {/* Tabs */}
        <div className="flex gap-1 border-b border-border overflow-x-auto">
          {TABS.map(tab => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2.5 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${activeTab === tab.id ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}`}>
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <ThkTabContent activeTab={activeTab} filtered={filtered} eqType={eqType} />
      </div>
    </AppLayout>
  )
}

// ── Exported page (Suspense wrapper for useSearchParams) ───────────────────
export default function ThicknessAnalyticsPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center h-64"><Loader2 className="h-8 w-8 animate-spin text-primary" /></div>}>
      <ThicknessAnalyticsInner />
    </Suspense>
  )
}


