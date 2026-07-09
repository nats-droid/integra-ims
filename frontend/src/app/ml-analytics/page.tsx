'use client'

import { useEffect, useState, useCallback } from 'react'
import AppLayout from '@/components/layout/app-layout'
import { createClient } from '@/lib/supabase/client'
import {
  Loader2,
  Brain,
  Play,
  AlertTriangle,
  TrendingDown,
  Activity,
  Layers,
  BarChart3,
} from 'lucide-react'
import { toast } from 'sonner'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface MLRun {
  id: string
  started_at: string
  completed_at: string
  status: string
  equipment_count: number
  duration_seconds: number
  module_counts: Record<string, number>
}

interface RiskRow {
  equipment_id: string
  risk_score: number
  risk_level: string
  top_feature: string
  shap_values: number[]
  equipment?: { tag: string; type: string; area_id: string }
}

interface ClusterRow {
  equipment_id: string
  cluster_id: number
  cluster_label: string
  pca_x: number
  pca_y: number
  equipment?: { tag: string; type: string }
}

interface RegressionRow {
  cml_point_id: string
  equipment_id: string
  r_squared: number
  projected_5yr: number
  projected_10yr: number
  t_required: number
  cml_points?: { location_label: string; equipment_id: string }
}

interface WeibullRow {
  equipment_id: string
  beta: number
  eta: number
  b10_years: number
  b50_years: number
  pof_curve: { t: number; pof: number }[]
  cml_points?: { location_label: string; equipment_id: string }
}

interface SurvivalRow {
  equipment_id: string
  median_survival: number
  ci_low: number
  ci_high: number
  survival_curve: { t: number; survival: number }[]
  cml_points?: { location_label: string; equipment_id: string }
}

interface AnomalyRow {
  id: string
  cml_point_id: string
  anomaly_score: number
  description: string
  detected_at: string
}

type TabId = 'risk' | 'clusters' | 'regression' | 'weibull' | 'survival' | 'anomaly'

const TABS: { id: TabId; label: string; icon: typeof Brain }[] = [
  { id: 'risk', label: 'Risk Scoring', icon: AlertTriangle },
  { id: 'clusters', label: 'Clustering', icon: Layers },
  { id: 'regression', label: 'Regression Trends', icon: TrendingDown },
  { id: 'weibull', label: 'Weibull', icon: BarChart3 },
  { id: 'survival', label: 'Survival', icon: Activity },
  { id: 'anomaly', label: 'Anomaly Detection', icon: AlertTriangle },
]

const RISK_COLORS: Record<string, string> = {
  critical: 'bg-red-100 text-red-700',
  high: 'bg-amber-100 text-amber-700',
  medium: 'bg-yellow-100 text-yellow-700',
  low: 'bg-green-100 text-green-700',
}

const CLUSTER_COLORS = [
  '#3b82f6', '#ef4444', '#22c55e', '#f59e0b', '#8b5cf6',
]

// ---------------------------------------------------------------------------
// Plotly loader
// ---------------------------------------------------------------------------

function ensurePlotly(): Promise<void> {
  return new Promise((resolve) => {
    if ((window as any).Plotly) return resolve()
    const script = document.createElement('script')
    script.src = 'https://cdn.plot.ly/plotly-2.35.2.min.js'
    script.onload = () => resolve()
    document.head.appendChild(script)
  })
}

// ---------------------------------------------------------------------------
// Page Component
// ---------------------------------------------------------------------------

export default function MLAnalyticsPage() {
  const supabase = createClient()

  // Auth
  const [companyId, setCompanyId] = useState<string>('')
  const [userRole, setUserRole] = useState<string>('')
  const [loading, setLoading] = useState(true)

  // ML state
  const [mlStatus, setMlStatus] = useState<MLRun | null>(null)
  const [running, setRunning] = useState(false)
  const [activeTab, setActiveTab] = useState<TabId>('risk')

  // Data
  const [riskData, setRiskData] = useState<RiskRow[]>([])
  const [clusterData, setClusterData] = useState<ClusterRow[]>([])
  const [regressionData, setRegressionData] = useState<RegressionRow[]>([])
  const [weibullData, setWeibullData] = useState<WeibullRow[]>([])
  const [survivalData, setSurvivalData] = useState<SurvivalRow[]>([])
  const [anomalyData, setAnomalyData] = useState<AnomalyRow[]>([])

  // Filters
  const [selectedEquipment, setSelectedEquipment] = useState<string>('')

  // -----------------------------------------------------------------------
  // Auth & init
  // -----------------------------------------------------------------------

  useEffect(() => {
    const init = async () => {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) {
        setLoading(false)
        return
      }

      const { data: profile } = await (supabase
        .from('app_users')
        .select('company_id, role') as any)
        .eq('auth_user_id', session.user.id)
        .single()

      if (profile) {
        setCompanyId(profile.company_id)
        setUserRole(profile.role)
      }

      setLoading(false)
    }
    init()

    // Inject Plotly
    if (!(window as any).Plotly) {
      const script = document.createElement('script')
      script.src = 'https://cdn.plot.ly/plotly-2.35.2.min.js'
      document.head.appendChild(script)
    }
  }, [])

  // -----------------------------------------------------------------------
  // Data loaders
  // -----------------------------------------------------------------------

  const loadStatus = useCallback(async () => {
    if (!companyId) return
    try {
      const { data: { session } } = await supabase.auth.getSession()
      const res = await fetch(`/api/backend/api/v1/ml/status/${companyId}`, {
        headers: { Authorization: `Bearer ${session?.access_token}` },
      })
      const json = await res.json()
      setMlStatus(json.last_run || null)
    } catch {
      /* ignore */
    }
  }, [companyId])

  const loadRisk = useCallback(async () => {
    if (!companyId) return
    try {
      const { data: { session } } = await supabase.auth.getSession()
      const res = await fetch(`/api/backend/api/v1/ml/risk/${companyId}`, {
        headers: { Authorization: `Bearer ${session?.access_token}` },
      })
      const json = await res.json()
      setRiskData(json.data || [])
    } catch {
      toast.error('Failed to load risk data')
    }
  }, [companyId])

  const loadClusters = useCallback(async () => {
    if (!companyId) return
    try {
      const { data: { session } } = await supabase.auth.getSession()
      const res = await fetch(`/api/backend/api/v1/ml/clusters/${companyId}`, {
        headers: { Authorization: `Bearer ${session?.access_token}` },
      })
      const json = await res.json()
      setClusterData(json.data || [])
    } catch {
      toast.error('Failed to load cluster data')
    }
  }, [companyId])

  const loadRegression = useCallback(async () => {
    if (!companyId) return
    try {
      const { data: { session } } = await supabase.auth.getSession()
      const res = await fetch(`/api/backend/api/v1/ml/regression/${companyId}`, {
        headers: { Authorization: `Bearer ${session?.access_token}` },
      })
      const json = await res.json()
      setRegressionData(json.data || [])
    } catch {
      toast.error('Failed to load regression data')
    }
  }, [companyId])

  const loadWeibull = useCallback(async () => {
    if (!companyId) return
    try {
      const { data: { session } } = await supabase.auth.getSession()
      const res = await fetch(`/api/backend/api/v1/ml/weibull/${companyId}`, {
        headers: { Authorization: `Bearer ${session?.access_token}` },
      })
      const json = await res.json()
      setWeibullData(json.data || [])
    } catch {
      toast.error('Failed to load Weibull data')
    }
  }, [companyId])

  const loadSurvival = useCallback(async () => {
    if (!companyId) return
    try {
      const { data: { session } } = await supabase.auth.getSession()
      const res = await fetch(`/api/backend/api/v1/ml/survival/${companyId}`, {
        headers: { Authorization: `Bearer ${session?.access_token}` },
      })
      const json = await res.json()
      setSurvivalData(json.data || [])
    } catch {
      toast.error('Failed to load survival data')
    }
  }, [companyId])

  const loadAnomalies = useCallback(async () => {
    if (!companyId) return
    try {
      const { data } = await supabase
        .from('corrosion_anomalies')
        .select('id, cml_point_id, anomaly_score, description, detected_at')
        .eq('company_id', companyId)
        .order('anomaly_score')
        .limit(200)
      setAnomalyData(data || [])
    } catch {
      toast.error('Failed to load anomaly data')
    }
  }, [companyId])

  // -----------------------------------------------------------------------
  // Tab data loader
  // -----------------------------------------------------------------------

  const loadTabData = useCallback(
    (tab: TabId) => {
      switch (tab) {
        case 'risk':
          return loadRisk()
        case 'clusters':
          return loadClusters()
        case 'regression':
          return loadRegression()
        case 'weibull':
          return loadWeibull()
        case 'survival':
          return loadSurvival()
        case 'anomaly':
          return loadAnomalies()
      }
    },
    [loadRisk, loadClusters, loadRegression, loadWeibull, loadSurvival, loadAnomalies],
  )

  // Load status + tab data on mount / company change
  useEffect(() => {
    if (companyId) {
      loadStatus()
      loadTabData(activeTab)
    }
  }, [companyId, activeTab, loadStatus, loadTabData])

  // -----------------------------------------------------------------------
  // Run ML pipeline
  // -----------------------------------------------------------------------

  const runML = async () => {
    if (!companyId) {
      toast.error('Profile not loaded yet. Please wait and try again.')
      return
    }
    setRunning(true)
    toast.info('Running ML pipeline...')

    try {
      const { data: { session } } = await supabase.auth.getSession()
      const res = await fetch(`/api/backend/api/v1/ml/run/${companyId}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${session?.access_token}` },
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.error || 'ML pipeline failed')
      }

      const result = await res.json()
      toast.success(
        `ML done in ${result.duration_seconds || '?'}s — ${result.equipment_count || 0} equipment`,
      )

      // Reload everything
      await loadStatus()
      await loadTabData(activeTab)
    } catch (e: any) {
      toast.error(`ML failed: ${e.message}`)
    } finally {
      setRunning(false)
    }
  }

  // -----------------------------------------------------------------------
  // Plotly chart effects
  // -----------------------------------------------------------------------

  // Clusters scatter
  useEffect(() => {
    if (activeTab !== 'clusters' || !clusterData.length) return
    const Plotly = (window as any).Plotly
    if (!Plotly) return

    const labels = [...new Set(clusterData.map((c) => c.cluster_label))]
    const traces = labels.map((label, i) => {
      const pts = clusterData.filter((c) => c.cluster_label === label)
      return {
        x: pts.map((p) => p.pca_x),
        y: pts.map((p) => p.pca_y),
        text: pts.map(
          (p) => `${p.equipment?.tag || p.equipment_id}<br>${label}`,
        ),
        mode: 'markers' as const,
        type: 'scatter' as const,
        name: label,
        marker: {
          color: CLUSTER_COLORS[i % CLUSTER_COLORS.length],
          size: 8,
          opacity: 0.7,
        },
      }
    })

    Plotly.newPlot(
      'cluster-plot',
      traces,
      {
        title: 'Equipment Clusters (PCA)',
        xaxis: { title: 'PC1' },
        yaxis: { title: 'PC2' },
        paper_bgcolor: 'white',
        plot_bgcolor: 'white',
        margin: { t: 40, r: 20, b: 50, l: 50 },
      },
      { responsive: true },
    )
  }, [activeTab, clusterData])

  // Regression chart
  useEffect(() => {
    if (activeTab !== 'regression' || !regressionData.length) return
    const Plotly = (window as any).Plotly
    if (!Plotly) return

    const eqIds = [
      ...new Set(regressionData.map((r) => r.equipment_id)),
    ]
    if (!selectedEquipment && eqIds.length) {
      setSelectedEquipment(eqIds[0])
      return
    }

    const cmls = regressionData.filter(
      (r) => r.equipment_id === selectedEquipment,
    )
    if (!cmls.length) return

    const traces: any[] = cmls.map((cml) => ({
      x: ['5yr projection', '10yr projection'],
      y: [cml.projected_5yr, cml.projected_10yr],
      mode: 'lines+markers',
      type: 'scatter',
      name: cml.cml_points?.location_label || cml.cml_point_id.slice(0, 8),
    }))

    // Add t_required line
    const tReq = cmls[0]?.t_required || 0
    if (tReq > 0) {
      traces.push({
        x: ['5yr projection', '10yr projection'],
        y: [tReq, tReq],
        mode: 'lines',
        type: 'scatter',
        name: 't_required',
        line: { dash: 'dash', color: 'red' },
      })
    }

    const avgR2 =
      cmls.reduce((s, c) => s + c.r_squared, 0) / cmls.length

    Plotly.newPlot(
      'regression-plot',
      traces,
      {
        title: `Regression Trends — R²=${avgR2.toFixed(3)}`,
        yaxis: { title: 'Thickness (mm)' },
        paper_bgcolor: 'white',
        plot_bgcolor: 'white',
        margin: { t: 40, r: 20, b: 50, l: 60 },
      },
      { responsive: true },
    )
  }, [activeTab, regressionData, selectedEquipment])

  // Weibull PoF chart
  useEffect(() => {
    if (activeTab !== 'weibull' || !weibullData.length) return
    const Plotly = (window as any).Plotly
    if (!Plotly) return

    const eqIds = [...new Set(weibullData.map((w) => w.equipment_id))]
    if (!selectedEquipment && eqIds.length) {
      setSelectedEquipment(eqIds[0])
      return
    }

    const row = weibullData.find((w) => w.equipment_id === selectedEquipment)
    if (!row?.pof_curve?.length) return

    const trace = {
      x: row.pof_curve.map((p) => p.t),
      y: row.pof_curve.map((p) => p.pof * 100),
      mode: 'lines',
      type: 'scatter',
      name: 'PoF',
      line: { color: '#ef4444', width: 2 },
    }

    const annotations = [
      {
        x: row.b10_years,
        y: 10,
        text: `B10: ${row.b10_years.toFixed(1)}yr`,
        showarrow: true,
        arrowhead: 2,
        ax: 40,
        ay: -30,
      },
      {
        x: row.b50_years,
        y: 50,
        text: `B50: ${row.b50_years.toFixed(1)}yr`,
        showarrow: true,
        arrowhead: 2,
        ax: 40,
        ay: -30,
      },
    ]

    Plotly.newPlot(
      'weibull-plot',
      [trace],
      {
        title: `Weibull PoF — β=${row.beta.toFixed(2)}, η=${row.eta.toFixed(1)}`,
        xaxis: { title: 'Time (years)' },
        yaxis: { title: 'PoF (%)', range: [0, 100] },
        annotations,
        paper_bgcolor: 'white',
        plot_bgcolor: 'white',
        margin: { t: 40, r: 20, b: 50, l: 60 },
      },
      { responsive: true },
    )
  }, [activeTab, weibullData, selectedEquipment])

  // Survival chart
  useEffect(() => {
    if (activeTab !== 'survival' || !survivalData.length) return
    const Plotly = (window as any).Plotly
    if (!Plotly) return

    const eqIds = [...new Set(survivalData.map((s) => s.equipment_id))]
    if (!selectedEquipment && eqIds.length) {
      setSelectedEquipment(eqIds[0])
      return
    }

    const row = survivalData.find(
      (s) => s.equipment_id === selectedEquipment,
    )
    if (!row?.survival_curve?.length) return

    const times = row.survival_curve.map((p) => p.t)
    const survival = row.survival_curve.map((p) => p.survival * 100)

    // CI band
    const ciBand = {
      x: [...times, ...times.slice().reverse()],
      y: [
        ...survival.map(() => row.ci_low * 100),
        ...survival
          .slice()
          .reverse()
          .map(() => row.ci_high * 100),
      ],
      fill: 'toself',
      fillcolor: 'rgba(59,130,246,0.15)',
      type: 'scatter' as const,
      mode: 'none' as const,
      name: '95% CI',
      showlegend: true,
    }

    const mainLine = {
      x: times,
      y: survival,
      mode: 'lines',
      type: 'scatter' as const,
      name: 'Survival',
      line: { color: '#3b82f6', width: 2 },
    }

    Plotly.newPlot(
      'survival-plot',
      [ciBand, mainLine],
      {
        title: `Kaplan-Meier — Median: ${row.median_survival.toFixed(1)}yr`,
        xaxis: { title: 'Time (years)' },
        yaxis: { title: 'Survival (%)', range: [0, 105] },
        paper_bgcolor: 'white',
        plot_bgcolor: 'white',
        margin: { t: 40, r: 20, b: 50, l: 60 },
      },
      { responsive: true },
    )
  }, [activeTab, survivalData, selectedEquipment])

  // -----------------------------------------------------------------------
  // Helpers
  // -----------------------------------------------------------------------

  const canRun = userRole === 'supervisor' || userRole === 'super_admin'

  const equipmentTags = useCallback(() => {
    const map = new Map<string, string>()
    for (const r of riskData) {
      if (r.equipment) map.set(r.equipment_id, r.equipment.tag)
    }
    for (const c of clusterData) {
      if (c.equipment) map.set(c.equipment_id, c.equipment.tag)
    }
    return map
  }, [riskData, clusterData])

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------

  if (loading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        </div>
      </AppLayout>
    )
  }

  return (
    <AppLayout>
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <Brain className="h-6 w-6 text-blue-600" />
          <h1 className="text-2xl font-bold text-gray-900">ML Analytics</h1>
          {mlStatus ? (
            <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
              Last run: {new Date(mlStatus.started_at).toLocaleString()}
            </span>
          ) : (
            <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-1 rounded">
              Never run
            </span>
          )}
        </div>
      </div>

      {(
        <div className="flex justify-start">
          <button
            onClick={runML}
            disabled={running}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {running ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Play className="h-4 w-4" />
            )}
            {running ? 'Running...' : 'Run ML Pipeline'}
          </button>
        </div>
      )}

      {/* Warning if no data */}
      {!mlStatus && !running && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6 flex items-center gap-3">
          <AlertTriangle className="h-5 w-5 text-yellow-600" />
          <p className="text-yellow-800 text-sm">
            No ML results yet. Click{' '}
            <strong>Run ML Pipeline</strong> to start.
          </p>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b overflow-x-auto">
        {TABS.map((tab) => {
          const Icon = tab.icon
          return (
            <button
              key={tab.id}
              onClick={() => {
                setActiveTab(tab.id)
                setSelectedEquipment('')
              }}
              className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                activeTab === tab.id
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* Equipment filter (shared for regression/weibull/survival) */}
      {(activeTab === 'regression' ||
        activeTab === 'weibull' ||
        activeTab === 'survival') && (
        <div className="mb-4">
          <label className="text-sm font-medium text-gray-700 mr-2">
            Equipment:
          </label>
          <select
            value={selectedEquipment}
            onChange={(e) => setSelectedEquipment(e.target.value)}
            className="border border-gray-300 rounded px-3 py-1.5 text-sm"
          >
            <option value="">— Select —</option>
            {[...new Set(
              activeTab === 'regression'
                ? regressionData.map((r) => r.equipment_id)
                : activeTab === 'weibull'
                  ? weibullData.map((w) => w.equipment_id)
                  : survivalData.map((s) => s.equipment_id),
            )].map((eqId) => (
              <option key={eqId} value={eqId}>
                {equipmentTags().get(eqId) || eqId.slice(0, 8)}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* ── Tab: Risk Scoring ──────────────────────────────────────────── */}
      {activeTab === 'risk' && (
        <div className="overflow-x-auto">
          {riskData.length === 0 ? (
            <p className="text-gray-500 text-sm py-8 text-center">
              No risk data. Run ML pipeline first.
            </p>
          ) : (
            <table className="min-w-full text-sm">
              <thead>
                <tr className="bg-gray-50">
                  <th className="text-left px-4 py-2 font-medium text-gray-600">
                    Tag
                  </th>
                  <th className="text-left px-4 py-2 font-medium text-gray-600">
                    Type
                  </th>
                  <th className="text-left px-4 py-2 font-medium text-gray-600">
                    Risk Level
                  </th>
                  <th className="text-left px-4 py-2 font-medium text-gray-600">
                    Risk Score
                  </th>
                  <th className="text-left px-4 py-2 font-medium text-gray-600">
                    Top Feature
                  </th>
                </tr>
              </thead>
              <tbody>
                {riskData.map((row) => (
                  <tr
                    key={row.equipment_id}
                    className="border-t hover:bg-gray-50"
                  >
                    <td className="px-4 py-2 font-mono text-xs">
                      {row.equipment?.tag || row.equipment_id.slice(0, 8)}
                    </td>
                    <td className="px-4 py-2 text-gray-600">
                      {row.equipment?.type || '—'}
                    </td>
                    <td className="px-4 py-2">
                      <span
                        className={`px-2 py-0.5 rounded text-xs font-medium ${
                          RISK_COLORS[row.risk_level] || 'bg-gray-100 text-gray-600'
                        }`}
                      >
                        {row.risk_level}
                      </span>
                    </td>
                    <td className="px-4 py-2">
                      <div className="flex items-center gap-2">
                        <div className="w-20 h-2 bg-gray-200 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              row.risk_score > 0.7
                                ? 'bg-red-500'
                                : row.risk_score > 0.4
                                  ? 'bg-amber-500'
                                  : 'bg-green-500'
                            }`}
                            style={{ width: `${row.risk_score * 100}%` }}
                          />
                        </div>
                        <span className="text-xs text-gray-600">
                          {(row.risk_score * 100).toFixed(1)}%
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-2 text-gray-600">
                      {row.top_feature?.replace(/_/g, ' ') || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* ── Tab: Clustering ────────────────────────────────────────────── */}
      {activeTab === 'clusters' && (
        <div>
          {clusterData.length === 0 ? (
            <p className="text-gray-500 text-sm py-8 text-center">
              No cluster data. Run ML pipeline first.
            </p>
          ) : (
            <>
              <div id="cluster-plot" style={{ width: '100%', height: 500 }} />
              <div className="mt-4 flex flex-wrap gap-3">
                {CLUSTER_COLORS.map((color, i) => (
                  <div key={i} className="flex items-center gap-1.5 text-xs">
                    <span
                      className="w-3 h-3 rounded-full inline-block"
                      style={{ backgroundColor: color }}
                    />
                    <span className="text-gray-600">
                      {['Low CR Stable', 'Medium CR Active', 'High CR Critical', 'Repaired History', 'Outlier'][i]}
                    </span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {/* ── Tab: Regression Trends ─────────────────────────────────────── */}
      {activeTab === 'regression' && (
        <div>
          {regressionData.length === 0 ? (
            <p className="text-gray-500 text-sm py-8 text-center">
              No regression data. Run ML pipeline first.
            </p>
          ) : selectedEquipment ? (
            <div id="regression-plot" style={{ width: '100%', height: 500 }} />
          ) : (
            <p className="text-gray-400 text-sm py-8 text-center">
              Select equipment above.
            </p>
          )}
        </div>
      )}

      {/* ── Tab: Weibull ───────────────────────────────────────────────── */}
      {activeTab === 'weibull' && (
        <div>
          {weibullData.length === 0 ? (
            <p className="text-gray-500 text-sm py-8 text-center">
              No Weibull data. Run ML pipeline first.
            </p>
          ) : selectedEquipment ? (
            <div id="weibull-plot" style={{ width: '100%', height: 500 }} />
          ) : (
            <p className="text-gray-400 text-sm py-8 text-center">
              Select equipment above.
            </p>
          )}
        </div>
      )}

      {/* ── Tab: Survival ──────────────────────────────────────────────── */}
      {activeTab === 'survival' && (
        <div>
          {survivalData.length === 0 ? (
            <p className="text-gray-500 text-sm py-8 text-center">
              No survival data. Run ML pipeline first.
            </p>
          ) : selectedEquipment ? (
            <div id="survival-plot" style={{ width: '100%', height: 500 }} />
          ) : (
            <p className="text-gray-400 text-sm py-8 text-center">
              Select equipment above.
            </p>
          )}
        </div>
      )}

      {/* ── Tab: Anomaly Detection ─────────────────────────────────────── */}
      {activeTab === 'anomaly' && (
        <div className="overflow-x-auto">
          {anomalyData.length === 0 ? (
            <p className="text-gray-500 text-sm py-8 text-center">
              No anomaly data. Run ML pipeline first.
            </p>
          ) : (
            <table className="min-w-full text-sm">
              <thead>
                <tr className="bg-gray-50">
                  <th className="text-left px-4 py-2 font-medium text-gray-600">
                    CML Point
                  </th>
                  <th className="text-left px-4 py-2 font-medium text-gray-600">
                    Anomaly Score
                  </th>
                  <th className="text-left px-4 py-2 font-medium text-gray-600">
                    Type
                  </th>
                  <th className="text-left px-4 py-2 font-medium text-gray-600">
                    Description
                  </th>
                  <th className="text-left px-4 py-2 font-medium text-gray-600">
                    Detected
                  </th>
                </tr>
              </thead>
              <tbody>
                {anomalyData.map((row) => (
                  <tr
                    key={row.id}
                    className="border-t hover:bg-gray-50"
                  >
                    <td className="px-4 py-2 font-mono text-xs">
                      {row.cml_point_id.slice(0, 8)}
                    </td>
                    <td className="px-4 py-2">
                      {row.anomaly_score?.toFixed(3) || '—'}
                    </td>
                    <td className="px-4 py-2">
                      <span
                        className={`px-2 py-0.5 rounded text-xs font-medium ${
                          row.description?.includes('Isolation')
                            ? 'bg-purple-100 text-purple-700'
                            : 'bg-blue-100 text-blue-700'
                        }`}
                      >
                        {row.description?.includes('Isolation')
                          ? 'IF Anomaly'
                          : 'Z-Score Anomaly'}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-gray-600 text-xs">
                      {row.description || '—'}
                    </td>
                    <td className="px-4 py-2 text-gray-500 text-xs">
                      {new Date(row.detected_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </AppLayout>
  )
}
