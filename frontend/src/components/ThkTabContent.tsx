'use client'
import { useEffect, useState, useRef } from 'react'
import { CHART } from '@/lib/chart-theme'

// ── Types ─────────────────────────────────────────────────────────────────
export interface ThkRow {
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

export type TabId = 'overview' | 'location' | 'priority' | 'trend' | 'master'
export type EqType = 'piping' | 'equipment'

const PRIO_COLORS: Record<string, string> = {
  CRITICAL: '#EF4444', HIGH: '#F59E0B', MEDIUM: '#EAB308', LOW: '#22C55E',
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

// ── Component ──────────────────────────────────────────────────────────────
export default function ThkTabContent({
  activeTab,
  filtered,
  eqType,
}: {
  activeTab: TabId
  filtered: ThkRow[]
  eqType: EqType
}) {
  const ovRef = useRef<HTMLDivElement>(null)
  const locRef1 = useRef<HTMLDivElement>(null)
  const locRef2 = useRef<HTMLDivElement>(null)
  const [trendSearch, setTrendSearch] = useState('')
  const [trendCML, setTrendCML] = useState<string>('')
  const [trendYears, setTrendYears] = useState(10)

  const BASE_LAYOUT = {
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: { size: 11, color: '#64748B', family: 'Inter, system-ui, sans-serif' },
    margin: { t: 10, b: 50, l: 50, r: 14 },
  }
  const CFG = { responsive: true, displayModeBar: false }
  const PRIO_ORDER = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']
  const PRIO_COL: Record<string, string> = {
    CRITICAL: '#EF4444',
    HIGH: '#F59E0B',
    MEDIUM: '#EAB308',
    LOW: '#22C55E',
  }

  // ── Overview charts ──────────────────────────────────────────────────────
  useEffect(() => {
    if (activeTab !== 'overview' || !filtered.length) return
    ensurePlotly().then(() => {
      const P = (window as any).Plotly

      // Status donut
      const statusGroups: Record<string, number> = { OK: 0, WARNING: 0, RETIRE: 0 }
      filtered.forEach(r => {
        if (r.status_thk in statusGroups) {
          statusGroups[r.status_thk as 'OK' | 'WARNING' | 'RETIRE']++
        }
      })
      P.newPlot('thk-status', [{
        type: 'pie', hole: 0.45,
        labels: Object.keys(statusGroups),
        values: Object.values(statusGroups),
        marker: { colors: ['#22C55E', '#F59E0B', '#EF4444'] },
        textinfo: 'label+value',
      }], { ...BASE_LAYOUT, height: 280, margin: { t: 10, b: 10, l: 10, r: 10 } }, CFG)

      // Priority donut
      const prioGroups: Record<string, number> = {}
      PRIO_ORDER.forEach(p => { prioGroups[p] = filtered.filter(r => r.priority === p).length })
      const pLabels = PRIO_ORDER.filter(p => prioGroups[p] > 0)
      P.newPlot('thk-prio', [{
        type: 'pie', hole: 0.45,
        labels: pLabels,
        values: pLabels.map(p => prioGroups[p]),
        marker: { colors: pLabels.map(p => PRIO_COL[p]) },
        textinfo: 'label+value',
      }], { ...BASE_LAYOUT, height: 280, margin: { t: 10, b: 10, l: 10, r: 10 } }, CFG)

      // Top 15 CR bar
      const top15 = [...filtered]
        .filter(r => r.cr_mm_yr > 0)
        .sort((a, b) => b.cr_mm_yr - a.cr_mm_yr)
        .slice(0, 15)
        .reverse()
      P.newPlot('thk-cr', [{
        type: 'bar', orientation: 'h',
        y: top15.map(r => ((r.object_type || '') + ' ' + r.no_cml).trim()),
        x: top15.map(r => r.cr_mm_yr),
        text: top15.map(r => r.cr_mm_yr.toFixed(3)),
        textposition: 'outside',
        marker: {
          color: top15.map(r =>
            r.cr_mm_yr > 0.5 ? '#EF4444' : r.cr_mm_yr > 0.25 ? '#F59E0B' : '#22C55E'
          ),
        },
      }], { ...BASE_LAYOUT, height: 400, margin: { t: 10, b: 30, l: 160, r: 60 } }, CFG)

      // Heatmap Plant x Object
      const plants = [...new Set(filtered.map(r => r.plant))].sort() as string[]
      const objects = [...new Set(filtered.map(r => r.object_type).filter(Boolean))].sort() as string[]
      if (plants.length && objects.length) {
        const z = plants.map(plant =>
          objects.map(obj => {
            const rows = filtered.filter(r => r.plant === plant && r.object_type === obj)
            return rows.length
              ? +(rows.reduce((s, r) => s + r.thk_loss_pct, 0) / rows.length).toFixed(1)
              : null
          })
        )
        P.newPlot('thk-heatmap', [{
          type: 'heatmap', z, x: objects, y: plants,
          colorscale: [[0, '#22C55E'], [0.5, '#EAB308'], [1, '#EF4444']],
          text: z.map((row: (number | null)[]) => row.map(v => (v == null ? '' : v.toFixed(1)))),
          texttemplate: '%{text}', textfont: { size: 10 },
          showscale: true, hoverongaps: false,
        }], {
          ...BASE_LAYOUT, height: Math.max(260, plants.length * 40),
          margin: { t: 10, b: 80, l: 120, r: 14 },
        }, CFG)
      }

      // Histogram loss %
      P.newPlot('thk-hist', [{
        type: 'histogram',
        x: filtered.map(r => r.thk_loss_pct),
        nbinsx: 40,
        marker: { color: CHART.primary },
      }], {
        ...BASE_LAYOUT, height: 280,
        shapes: [{
          type: 'line', x0: 12.5, x1: 12.5, y0: 0, y1: 1,
          yref: 'paper', line: { color: '#F59E0B', dash: 'dash', width: 2 },
        }],
        xaxis: { title: 'Loss %', gridcolor: '#F1F5F9' },
        yaxis: { title: 'Count', gridcolor: '#F1F5F9' },
      }, CFG)
    })
  }, [activeTab, filtered])

  // ── Location charts ──────────────────────────────────────────────────────
  useEffect(() => {
    if (activeTab !== 'location') return
    const withLoc = filtered.filter(r => r.location_deg != null)
    if (!withLoc.length) return
    ensurePlotly().then(() => {
      const P = (window as any).Plotly
      const degGroups: Record<number, number[]> = {}
      withLoc.forEach(r => {
        const d = r.location_deg!
        if (!degGroups[d]) degGroups[d] = []
        degGroups[d].push(r.thk_loss_pct)
      })
      const degs = Object.keys(degGroups).map(Number).sort((a, b) => a - b)
      const avgByDeg = degs.map(d =>
        +(degGroups[d].reduce((s, v) => s + v, 0) / degGroups[d].length).toFixed(2)
      )

      P.newPlot('thk-loc-bar', [{
        type: 'bar',
        x: degs.map(d => d + '\u00B0'),
        y: avgByDeg,
        text: avgByDeg.map(v => v.toFixed(1)),
        textposition: 'outside',
        marker: {
          color: avgByDeg.map(v =>
            v > 15 ? '#EF4444' : v > 10 ? '#F59E0B' : CHART.primary
          ),
        },
      }], {
        ...BASE_LAYOUT, height: 300,
        xaxis: { title: 'Position', gridcolor: '#F1F5F9' },
        yaxis: { title: 'Avg Loss %', gridcolor: '#F1F5F9' },
      }, CFG)

      P.newPlot('thk-loc-polar', [{
        type: 'barpolar', r: avgByDeg, theta: degs,
        marker: {
          color: avgByDeg,
          colorscale: [[0, '#22C55E'], [0.5, '#EAB308'], [1, '#EF4444']],
        },
        width: degs.map(() => 70),
      }], {
        ...BASE_LAYOUT, height: 320,
        margin: { t: 30, b: 30, l: 30, r: 30 },
        polar: {
          angularaxis: {
            rotation: 90, direction: 'clockwise',
            tickmode: 'array', tickvals: degs,
            ticktext: degs.map(d => d + '\u00B0'),
          },
          radialaxis: { showticklabels: true },
        },
      }, CFG)
    })
  }, [activeTab, filtered])

  // ── Priority & RL charts ─────────────────────────────────────────────────
  useEffect(() => {
    if (activeTab !== 'priority' || !filtered.length) return
    ensurePlotly().then(() => {
      const P = (window as any).Plotly

      const rlRows = filtered.filter(r => r.remaining_life_yr < 99)
      P.newPlot('thk-rl-hist', PRIO_ORDER.map(p => ({
        type: 'histogram', name: p,
        x: rlRows.filter(r => r.priority === p).map(r => r.remaining_life_yr),
        marker: { color: PRIO_COL[p] }, nbinsx: 20,
      })), {
        ...BASE_LAYOUT, barmode: 'stack', height: 300,
        showlegend: true, legend: { orientation: 'h', y: -0.3 },
        xaxis: { title: 'Remaining Life (yr)', gridcolor: '#F1F5F9' },
        yaxis: { gridcolor: '#F1F5F9' },
      }, CFG)

      const plants = [...new Set(filtered.map(r => r.plant))].sort() as string[]
      P.newPlot('thk-plant-prio', [
        {
          type: 'bar', name: 'CRITICAL', x: plants,
          y: plants.map(p => filtered.filter(r => r.plant === p && r.priority === 'CRITICAL').length),
          marker: { color: '#EF4444' },
        },
        {
          type: 'bar', name: 'HIGH', x: plants,
          y: plants.map(p => filtered.filter(r => r.plant === p && r.priority === 'HIGH').length),
          marker: { color: '#F59E0B' },
        },
      ], {
        ...BASE_LAYOUT, barmode: 'group', height: 300,
        showlegend: true, legend: { orientation: 'h', y: -0.3 },
        xaxis: { tickangle: -30, gridcolor: '#F1F5F9' },
        yaxis: { gridcolor: '#F1F5F9' },
      }, CFG)

      const sc = filtered.filter(r => r.remaining_life_yr < 99)
      P.newPlot('thk-scatter', PRIO_ORDER.map(p => {
        const d = sc.filter(r => r.priority === p)
        return {
          type: 'scatter', mode: 'markers', name: p,
          x: d.map(r => r.thk_loss_pct),
          y: d.map(r => r.remaining_life_yr),
          marker: { color: PRIO_COL[p], size: 6, opacity: 0.7 },
          text: d.map(r => r.object_type + ' ' + r.no_cml),
        }
      }), {
        ...BASE_LAYOUT, height: 340,
        showlegend: true, legend: { orientation: 'h', y: -0.3 },
        xaxis: { title: 'Loss %', gridcolor: '#F1F5F9' },
        yaxis: { title: 'Rem.Life (yr)', gridcolor: '#F1F5F9' },
        shapes: [
          { type: 'line', x0: 12.5, x1: 12.5, y0: 0, y1: 1, yref: 'paper', line: { color: '#F59E0B', dash: 'dash' } },
          { type: 'line', x0: 0, x1: 1, xref: 'paper', y0: 2, y1: 2, line: { color: '#EF4444', dash: 'dash' } },
        ],
      }, CFG)
    })
  }, [activeTab, filtered])

  // ── Trend chart ──────────────────────────────────────────────────────────
  const trendCMLs = filtered.filter(r => r.cr_mm_yr > 0)
  const trendFiltered = trendSearch
    ? trendCMLs.filter(r =>
        (r.iso_number + ' ' + r.no_cml + ' ' + r.object_type)
          .toLowerCase()
          .includes(trendSearch.toLowerCase())
      )
    : trendCMLs

  useEffect(() => {
    if (activeTab !== 'trend') return
    if (trendFiltered.length && !trendCML) setTrendCML(trendFiltered[0]?.cml_id || '')
  }, [activeTab, trendFiltered.length, trendFiltered, trendCML])

  useEffect(() => {
    if (activeTab !== 'trend' || !trendCML) return
    const r = trendCMLs.find(x => x.cml_id === trendCML)
    if (!r) return
    ensurePlotly().then(() => {
      const P = (window as any).Plotly
      const xs = Array.from({ length: trendYears + 1 }, (_, i) => i)
      const ys = xs.map(y => r.measured_thk - r.cr_mm_yr * y)
      const crossY = r.cr_mm_yr > 0 ? (r.measured_thk - r.t_min) / r.cr_mm_yr : null

      const annotations: any[] = []
      if (crossY != null && crossY <= trendYears) {
        annotations.push({
          x: crossY, y: r.t_min,
          text: 'Reach t_min: ' + crossY.toFixed(1) + ' yr',
          showarrow: true, arrowcolor: '#EF4444',
          font: { color: '#EF4444', size: 11 },
        })
      }

      P.newPlot('thk-trend-plot', [
        {
          type: 'scatter', mode: 'lines+markers',
          x: xs, y: ys, name: 'Projection',
          line: { color: CHART.primary },
        },
        {
          type: 'scatter', mode: 'lines',
          x: [0, trendYears], y: [r.t_min, r.t_min],
          name: 't_min', line: { color: '#EF4444', dash: 'dash' },
        },
        {
          type: 'scatter', mode: 'lines',
          x: [0, trendYears], y: [r.nominal_thk, r.nominal_thk],
          name: 'Nominal', line: { color: '#22C55E', dash: 'dot' },
        },
      ], {
        ...BASE_LAYOUT, height: 360,
        xaxis: { title: 'Years from now', gridcolor: '#F1F5F9' },
        yaxis: { title: 'Thickness (mm)', gridcolor: '#F1F5F9' },
        showlegend: true, legend: { orientation: 'h', y: -0.25 },
        annotations,
      }, CFG)
    })
  }, [activeTab, trendCML, trendYears, trendCMLs])

  // ── Render sections ──────────────────────────────────────────────────────
  if (activeTab === 'overview') {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="bg-card border border-border rounded-xl p-4 shadow-sm">
            <h3 className="text-sm font-semibold mb-2 text-foreground">Status Distribution</h3>
            <div id="thk-status" />
          </div>
          <div className="bg-card border border-border rounded-xl p-4 shadow-sm">
            <h3 className="text-sm font-semibold mb-2 text-foreground">Priority Distribution</h3>
            <div id="thk-prio" />
          </div>
        </div>
        <div className="bg-card border border-border rounded-xl p-4 shadow-sm">
          <h3 className="text-sm font-semibold mb-2 text-foreground">Top 15 — Corrosion Rate (mm/yr)</h3>
          <p className="text-xs text-muted-foreground mb-2">CMLs with highest corrosion rate</p>
          <div id="thk-cr" />
        </div>
        <div className="bg-card border border-border rounded-xl p-4 shadow-sm">
          <h3 className="text-sm font-semibold mb-2 text-foreground">Avg Thickness Loss % — Plant x Object</h3>
          <div id="thk-heatmap" />
        </div>
        <div className="bg-card border border-border rounded-xl p-4 shadow-sm">
          <h3 className="text-sm font-semibold mb-2 text-foreground">Histogram — Thickness Loss %</h3>
          <p className="text-xs text-muted-foreground mb-2">Dashed line = 12.5% threshold</p>
          <div id="thk-hist" />
        </div>
      </div>
    )
  }

  if (activeTab === 'location') {
    const withLoc = filtered.filter(r => r.location_deg != null)
    if (!withLoc.length) {
      return (
        <div className="bg-card border border-border rounded-xl p-8 text-center text-muted-foreground text-sm">
          No location degree data available for {eqType}.
        </div>
      )
    }
    const worst20 = [...filtered]
      .filter(r => r.thk_loss_pct > 0)
      .sort((a, b) => b.thk_loss_pct - a.thk_loss_pct)
      .slice(0, 20)
    return (
      <div className="space-y-4">
        <div className="bg-primary/5 border border-primary/20 rounded-xl p-3 text-xs text-primary">
          i Position 270\u00B0 (bottom of pipe) typically has highest corrosion due to moisture accumulation.
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="bg-card border border-border rounded-xl p-4 shadow-sm">
            <h3 className="text-sm font-semibold mb-2 text-foreground">Avg Loss % per Position</h3>
            <div id="thk-loc-bar" />
          </div>
          <div className="bg-card border border-border rounded-xl p-4 shadow-sm">
            <h3 className="text-sm font-semibold mb-2 text-foreground">Polar — Avg Loss % per Position</h3>
            <div id="thk-loc-polar" />
          </div>
        </div>
        <div className="bg-card border border-border rounded-xl p-4 shadow-sm">
          <h3 className="text-sm font-semibold mb-3 text-foreground">Top 20 CML — Highest Loss</h3>
          <div className="overflow-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border">
                  {['Plant', 'Tag', 'Object', 'CML', 'Pos', 'Nominal', 'Measured', '% Loss', 'Priority'].map(h => (
                    <th key={h} className="text-left py-2 px-3 text-muted-foreground font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {worst20.map((r, i) => (
                  <tr key={i} className="border-b border-border/50 hover:bg-muted/50">
                    <td className="py-2 px-3">{r.plant}</td>
                    <td className="py-2 px-3">{r.equipment_tag}</td>
                    <td className="py-2 px-3">{r.object_type}</td>
                    <td className="py-2 px-3">{r.no_cml}</td>
                    <td className="py-2 px-3">{r.location_deg != null ? r.location_deg + '\u00B0' : '—'}</td>
                    <td className="py-2 px-3">{r.nominal_thk.toFixed(2)}</td>
                    <td className="py-2 px-3">{r.measured_thk.toFixed(2)}</td>
                    <td className="py-2 px-3">{r.thk_loss_pct}%</td>
                    <td className="py-2 px-3">
                      <span
                        className="px-2 py-0.5 rounded-full text-white text-[10px] font-bold"
                        style={{ background: PRIO_COL[r.priority] || '#94A3B8' }}
                      >
                        {r.priority}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    )
  }

  if (activeTab === 'priority') {
    const critHigh = [...filtered]
      .filter(r => r.priority === 'CRITICAL' || r.priority === 'HIGH')
      .sort((a, b) => a.remaining_life_yr - b.remaining_life_yr)
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="bg-card border border-border rounded-xl p-4 shadow-sm">
            <h3 className="text-sm font-semibold mb-2 text-foreground">Remaining Life Distribution</h3>
            <div id="thk-rl-hist" />
          </div>
          <div className="bg-card border border-border rounded-xl p-4 shadow-sm">
            <h3 className="text-sm font-semibold mb-2 text-foreground">CRITICAL + HIGH per Plant</h3>
            <div id="thk-plant-prio" />
          </div>
        </div>
        <div className="bg-card border border-border rounded-xl p-4 shadow-sm">
          <h3 className="text-sm font-semibold mb-2 text-foreground">Scatter — Loss % vs Remaining Life</h3>
          <div id="thk-scatter" />
        </div>
        <div className="bg-card border border-border rounded-xl p-4 shadow-sm">
          <h3 className="text-sm font-semibold mb-3 text-foreground text-red-600">Priority List — CRITICAL & HIGH</h3>
          {!critHigh.length ? (
            <p className="text-center text-green-600 py-4 text-sm">
              No CRITICAL/HIGH CMLs for current filter.
            </p>
          ) : (
            <div className="overflow-auto max-h-96">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-border">
                    {['Plant', 'Tag', 'Object', 'CML', 'Measured', 't_min', 'CR mm/yr', 'Rem.Life', 'Priority'].map(h => (
                      <th key={h} className="text-left py-2 px-3 text-muted-foreground font-medium">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {critHigh.slice(0, 100).map((r, i) => (
                    <tr key={i} className="border-b border-border/50 hover:bg-muted/50">
                      <td className="py-2 px-3">{r.plant}</td>
                      <td className="py-2 px-3">{r.equipment_tag}</td>
                      <td className="py-2 px-3">{r.object_type}</td>
                      <td className="py-2 px-3">{r.no_cml}</td>
                      <td className="py-2 px-3">{r.measured_thk.toFixed(2)}</td>
                      <td className="py-2 px-3">{r.t_min.toFixed(2)}</td>
                      <td className="py-2 px-3">{r.cr_mm_yr.toFixed(3)}</td>
                      <td className="py-2 px-3">{r.remaining_life_yr.toFixed(1)} yr</td>
                      <td className="py-2 px-3">
                        <span
                          className="px-2 py-0.5 rounded-full text-white text-[10px] font-bold"
                          style={{ background: PRIO_COL[r.priority] }}
                        >
                          {r.priority}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    )
  }

  if (activeTab === 'trend') {
    return (
      <div className="bg-card border border-border rounded-xl p-4 shadow-sm space-y-3">
        <p className="text-xs text-muted-foreground">
          Projection based on current CR. Total {trendCMLs.length} CMLs available.
        </p>
        <div className="flex flex-wrap gap-3 items-end">
          <div className="flex-1 min-w-48">
            <label className="text-xs font-medium text-muted-foreground block mb-1">Search CML</label>
            <input
              type="text"
              value={trendSearch}
              onChange={e => setTrendSearch(e.target.value)}
              placeholder="Filter by tag / CML / object..."
              className="w-full px-3 py-1.5 text-sm border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
          </div>
          <div className="flex-1 min-w-48">
            <label className="text-xs font-medium text-muted-foreground block mb-1">Select CML</label>
            <select
              value={trendCML}
              onChange={e => setTrendCML(e.target.value)}
              className="w-full px-3 py-1.5 text-sm border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
            >
              {trendFiltered.slice(0, 500).map(r => (
                <option key={r.cml_id} value={r.cml_id}>
                  {r.iso_number} | {r.no_cml} | {r.object_type}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground block mb-1">Projection (years)</label>
            <select
              value={trendYears}
              onChange={e => setTrendYears(Number(e.target.value))}
              className="px-3 py-1.5 text-sm border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
            >
              {[5, 10, 15, 20].map(y => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </div>
        </div>
        <div id="thk-trend-plot" />
      </div>
    )
  }

  if (activeTab === 'master') {
    const cols = eqType === 'piping'
      ? ['Plant', 'ISO', 'Fluid', 'Object', 'CML', 'Nominal', 'Measured', 't_min', '% Loss', 'CR mm/yr', 'Rem.Life', 'Priority', 'Status']
      : ['Plant', 'Tag', 'Part', 'Object', 'CML', 'Nominal', 'Measured', 't_min', '% Loss', 'CR mm/yr', 'Rem.Life', 'Priority', 'Status']
    return (
      <div className="bg-card border border-border rounded-xl shadow-sm overflow-hidden">
        <div className="p-4 border-b border-border flex items-center justify-between">
          <h3 className="text-sm font-semibold text-foreground">
            Master Table — {filtered.length.toLocaleString()} CMLs
          </h3>
        </div>
        <div className="overflow-auto max-h-[600px]">
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-muted">
              <tr>
                {cols.map(h => (
                  <th key={h} className="text-left py-2 px-3 text-muted-foreground font-medium whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[...filtered]
                .sort((a, b) => b.cr_mm_yr - a.cr_mm_yr)
                .slice(0, 500)
                .map((r, i) => (
                  <tr key={i} className="border-b border-border/50 hover:bg-muted/50">
                    <td className="py-1.5 px-3 whitespace-nowrap">{r.plant}</td>
                    {eqType === 'piping' ? (
                      <td className="py-1.5 px-3 whitespace-nowrap">{r.iso_number}</td>
                    ) : (
                      <td className="py-1.5 px-3 whitespace-nowrap">{r.equipment_tag}</td>
                    )}
                    {eqType === 'piping' ? (
                      <td className="py-1.5 px-3">{r.fluid}</td>
                    ) : (
                      <td className="py-1.5 px-3">{r.part}</td>
                    )}
                    <td className="py-1.5 px-3">{r.object_type}</td>
                    <td className="py-1.5 px-3">{r.no_cml}</td>
                    <td className="py-1.5 px-3">{r.nominal_thk.toFixed(2)}</td>
                    <td className="py-1.5 px-3">{r.measured_thk.toFixed(2)}</td>
                    <td className="py-1.5 px-3">{r.t_min.toFixed(2)}</td>
                    <td className="py-1.5 px-3">{r.thk_loss_pct}%</td>
                    <td className="py-1.5 px-3">{r.cr_mm_yr.toFixed(3)}</td>
                    <td className="py-1.5 px-3">
                      {r.remaining_life_yr < 99 ? r.remaining_life_yr.toFixed(1) + ' yr' : '—'}
                    </td>
                    <td className="py-1.5 px-3">
                      <span
                        className="px-2 py-0.5 rounded-full text-white text-[10px] font-bold"
                        style={{ background: PRIO_COL[r.priority] || '#94A3B8' }}
                      >
                        {r.priority}
                      </span>
                    </td>
                    <td className="py-1.5 px-3">
                      <span
                        className="px-2 py-0.5 rounded-full text-white text-[10px] font-bold"
                        style={{
                          background:
                            r.status_thk === 'RETIRE'
                              ? '#EF4444'
                              : r.status_thk === 'WARNING'
                              ? '#F59E0B'
                              : '#22C55E',
                        }}
                      >
                        {r.status_thk}
                      </span>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>
    )
  }

  return null
}
