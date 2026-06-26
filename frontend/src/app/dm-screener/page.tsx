'use client'

import { useState, useCallback } from 'react'
import { Search, Shield, AlertTriangle, Info, FlaskConical, Zap, Thermometer, Wrench, BookOpen, Loader2 } from 'lucide-react'
import AppLayout from '@/components/layout/app-layout'

// ── Types ────────────────────────────────────────────────────────────────────
interface DM {
  dm_code: string
  dm_name: string
  category: string
  confidence: string
  pwht_concern?: boolean
  nde?: string[]
  mitigation?: string
}

interface DMResponse {
  status: string
  active: DM[]
  possible: DM[]
  related: DM[]
  total_matched: number
  total_screened: number
}

// ── Risk Matrix Config ──────────────────────────────────────────────────────
const RISK_DATA: Record<string, { prob: string; conseq: string; color: string }> = {
  high: { prob: 'Likely (>30%)', conseq: 'Severe — shutdown/failure', color: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400' },
  medium: { prob: 'Possible (10–30%)', conseq: 'Moderate — repair needed', color: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400' },
  low: { prob: 'Unlikely (<10%)', conseq: 'Minor — monitor only', color: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400' },
}

const CATEGORY_COLORS: Record<string, string> = {
  Corrosion: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  Cracking: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400',
  Metallurgical: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400',
  Mechanical: 'bg-teal-100 text-teal-800 dark:bg-teal-900/30 dark:text-teal-400',
}

// ── Equipment Type Options ──────────────────────────────────────────────────
const EQ_TYPES = ['piping', 'vessel', 'tank', 'heater', 'pump', 'compressor', 'valve', 'other']
const MATERIALS = ['Carbon Steel', 'Low Alloy', 'Cr-Mo', '300 SS', '400 SS', 'Duplex SS', 'Nickel Alloy', 'Copper Alloy', 'Titanium']
const FLUIDS = ['Sour Hydrocarbon', 'Sweet Hydrocarbon', 'Amine', 'Caustic (NaOH/KOH)', 'Hydrogen (H2)', 'Sour Water', 'CO2', 'Ammonia', 'HF Acid', 'Sulfuric Acid', 'Atmospheric', 'Water/Cooling Water', 'Steam/Condensate', 'CUI/Insulation', 'Buried/Soil']

// ── DM Card Component ──────────────────────────────────────────────────────
function DmCard({ dm, label, icon }: { dm: DM; label: string; icon: React.ReactNode }) {
  const risk = RISK_DATA[dm.confidence] || RISK_DATA.low
  const catColor = CATEGORY_COLORS[dm.category] || 'bg-gray-100 text-gray-800'
  return (
    <div className="bg-card border border-border rounded-lg p-4 space-y-2">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <div className="shrink-0">{icon}</div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-mono text-muted-foreground">{dm.dm_code}</span>
              <span className={`text-xs px-1.5 py-0.5 rounded-full ${CATEGORY_COLORS[dm.category] || 'bg-gray-100 text-gray-800'}`}>
                {dm.category}
              </span>
            </div>
            <p className="font-medium text-sm leading-tight mt-0.5">{dm.dm_name}</p>
          </div>
        </div>
        <span className={`text-xs px-2 py-1 rounded-full shrink-0 ${risk.color}`}>{dm.confidence.toUpperCase()}</span>
      </div>

      {dm.pwht_concern && (
        <div className="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 px-2 py-1 rounded">
          ⚠ No PWHT — elevated risk
        </div>
      )}

      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-muted-foreground border-t border-border pt-2 mt-1">
        <div>
          <span className="font-medium text-foreground">Probability: </span>{risk.prob}
        </div>
        <div>
          <span className="font-medium text-foreground">Consequence: </span>{risk.conseq}
        </div>
        {dm.nde && dm.nde.length > 0 && (
          <div className="col-span-2">
            <span className="font-medium text-foreground">Recommended NDE: </span>
            {dm.nde.join(', ')}
          </div>
        )}
        {dm.mitigation && (
          <div className="col-span-2">
            <span className="font-medium text-foreground">Mitigation: </span>
            {dm.mitigation}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Main Page ──────────────────────────────────────────────────────────────
export default function DmScreenerPage() {
  const [material, setMaterial] = useState('')
  const [fluid, setFluid] = useState('')
  const [tempMin, setTempMin] = useState('')
  const [tempMax, setTempMax] = useState('')
  const [hasPwht, setHasPwht] = useState<boolean | null>(null)
  const [eqType, setEqType] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<DMResponse | null>(null)
  const [error, setError] = useState('')

  // Quick sample assets (from reference dm_screener_pro.html)
  const samples = [
    { label: 'Caustic (NaOH) Piping', mat: 'Carbon Steel', fluid: 'Caustic (NaOH/KOH)', tmin: '6', tmax: '80', pwht: true },
    { label: 'Sour Hydrocarbon Line', mat: 'Carbon Steel', fluid: 'Sour Hydrocarbon', tmin: '20', tmax: '320', pwht: false },
    { label: 'H2 Service Exchanger', mat: 'Low Alloy', fluid: 'Hydrogen (H2)', tmin: '40', tmax: '380', pwht: true },
  ]

  const loadSample = useCallback((s: typeof samples[0]) => {
    setMaterial(s.mat)
    setFluid(s.fluid)
    setTempMin(s.tmin)
    setTempMax(s.tmax)
    setHasPwht(s.pwht)
  }, [])

  const runScreening = useCallback(async () => {
    if (!material || !fluid) {
      setError('Material and Fluid Service are required')
      return
    }
    setLoading(true)
    setError('')
    setResult(null)

    try {
      const params = new URLSearchParams({ material, fluid_service: fluid })
      if (tempMin) params.set('temp_min', tempMin)
      if (tempMax) params.set('temp_max', tempMax)
      if (hasPwht !== null) params.set('has_pwht', String(hasPwht))

      // Try backend API first
      const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const res = await fetch(`${backendUrl}/api/dm-screener/query?${params}`, { cache: 'no-store' })

      if (!res.ok) {
        // Fallback: direct Supabase KB match
        const { createClient } = await import('@/lib/supabase/client')
        const supabase = createClient()
        const { data: kb } = await supabase.from('dm_knowledge_base').select('*')
        if (!kb) throw new Error('No DM KB data')
        setResult(runClientSideMatch(kb, { material, fluid, tempMin: parseFloat(tempMin) || 0, tempMax: parseFloat(tempMax) || 100, pwht: hasPwht }))
      } else {
        const data = await res.json()
        setResult(data)
      }
    } catch (e: any) {
      // Try client-side fallback
      try {
        const { createClient } = await import('@/lib/supabase/client')
        const supabase = createClient()
        const { data: kb } = await supabase.from('dm_knowledge_base').select('*')
        if (kb) {
          setResult(runClientSideMatch(kb, { material, fluid, tempMin: parseFloat(tempMin) || 0, tempMax: parseFloat(tempMax) || 100, pwht: hasPwht }))
          setError('')
        } else {
          setError(e?.message || 'Failed to connect to backend and KB unavailable')
        }
      } catch {
        setError(e?.message || 'Failed to run screening')
      }
    } finally {
      setLoading(false)
    }
  }, [material, fluid, tempMin, tempMax, hasPwht])

  return (
    <AppLayout>
      <div className="p-6 max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-xl font-semibold flex items-center gap-2">
              <FlaskConical className="h-5 w-5 text-primary" />
              DM Screener
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Rule-based damage mechanism identification — API 571 compliant
            </p>
          </div>
          <div className="flex items-center gap-1 text-xs text-muted-foreground bg-muted px-3 py-1.5 rounded-full">
            <BookOpen className="h-3.5 w-3.5" />
            {result ? `${result.total_matched} / ${result.total_screened} DM matched` : '67 API 571 DMs'}
          </div>
        </div>

        {/* Screening Form */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: Form */}
          <div className="lg:col-span-1 space-y-4">
            <div className="bg-card border border-border rounded-lg p-4 space-y-4">
              <h2 className="text-sm font-medium flex items-center gap-2">
                <Search className="h-4 w-4 text-muted-foreground" />
                Manual Screening
              </h2>

              {/* Material */}
              <div>
                <label className="text-xs font-medium text-muted-foreground block mb-1">Material</label>
                <select
                  value={material}
                  onChange={e => setMaterial(e.target.value)}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                >
                  <option value="">— Select —</option>
                  {MATERIALS.map(m => <option key={m} value={m}>{m}</option>)}
                  <option value="user">Other (type below)</option>
                </select>
                {material === 'user' && (
                  <input
                    type="text"
                    placeholder="Custom material..."
                    value={material === 'user' ? '' : material}
                    onChange={e => setMaterial(e.target.value)}
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm mt-1"
                  />
                )}
              </div>

              {/* Fluid */}
              <div>
                <label className="text-xs font-medium text-muted-foreground block mb-1">Fluid Service</label>
                <select
                  value={fluid}
                  onChange={e => setFluid(e.target.value)}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                >
                  <option value="">— Select —</option>
                  {FLUIDS.map(f => <option key={f} value={f}>{f}</option>)}
                  <option value="user">Other (type below)</option>
                </select>
                {fluid === 'user' && (
                  <input
                    type="text"
                    placeholder="Custom fluid..."
                    onChange={e => setFluid(e.target.value === 'user' ? 'user' : e.target.value)}
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm mt-1"
                  />
                )}
              </div>

              {/* Temp range */}
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-xs font-medium text-muted-foreground block mb-1">Temp Min (°C)</label>
                  <input
                    type="number"
                    value={tempMin}
                    onChange={e => setTempMin(e.target.value)}
                    placeholder="e.g. 20"
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-muted-foreground block mb-1">Temp Max (°C)</label>
                  <input
                    type="number"
                    value={tempMax}
                    onChange={e => setTempMax(e.target.value)}
                    placeholder="e.g. 320"
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  />
                </div>
              </div>

              {/* PWHT */}
              <div>
                <label className="text-xs font-medium text-muted-foreground block mb-2">PWHT Applied</label>
                <div className="flex gap-2">
                  {[
                    { label: 'Yes', value: true },
                    { label: 'No', value: false },
                    { label: 'Unknown', value: null as boolean | null },
                  ].map(opt => (
                    <button
                      key={String(opt.value)}
                      onClick={() => setHasPwht(opt.value)}
                      className={`px-3 py-1.5 text-xs rounded-md border transition-colors ${
                        hasPwht === opt.value
                          ? 'bg-primary text-primary-foreground border-primary'
                          : 'bg-background text-muted-foreground border-input hover:border-primary'
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Run */}
              <button
                onClick={runScreening}
                disabled={loading || !material || !fluid}
                className="w-full flex items-center justify-center gap-2 bg-primary text-primary-foreground rounded-md px-4 py-2.5 text-sm font-medium hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? (
                  <><Loader2 className="h-4 w-4 animate-spin" /> Screening...</>
                ) : (
                  <><Zap className="h-4 w-4" /> Run Screening</>
                )}
              </button>

              {error && <p className="text-xs text-red-500">{error}</p>}
            </div>

            {/* Quick Sample Assets */}
            <div className="bg-card border border-border rounded-lg p-4 space-y-2">
              <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Quick Load Sample</h3>
              {samples.map((s, i) => (
                <button
                  key={i}
                  onClick={() => loadSample(s)}
                  className="w-full text-left text-xs p-2 rounded border border-border hover:border-primary hover:bg-accent/50 transition-colors"
                >
                  <span className="font-medium">{s.label}</span>
                  <span className="text-muted-foreground block">{s.mat} · {s.fluid}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Results */}
          <div className="lg:col-span-2 space-y-4">
            {!result && !loading && (
              <div className="bg-card border border-border rounded-lg p-12 text-center text-muted-foreground">
                <FlaskConical className="h-10 w-10 mx-auto mb-3 opacity-40" />
                <p className="text-sm">Enter equipment details and click Run Screening</p>
                <p className="text-xs mt-1">Results will show Active, Possible, and Related DMs</p>
              </div>
            )}

            {loading && (
              <div className="bg-card border border-border rounded-lg p-12 text-center text-muted-foreground">
                <Loader2 className="h-8 w-8 mx-auto mb-3 animate-spin" />
                <p className="text-sm">Running rule engine against 67 API 571 DMs...</p>
              </div>
            )}

            {result && !loading && (
              <>
                {/* Summary */}
                <div className="grid grid-cols-3 gap-3">
                  <div className="bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-800/30 rounded-lg p-3 text-center">
                    <div className="text-2xl font-bold text-red-600 dark:text-red-400">{result.active.length}</div>
                    <div className="text-xs text-red-700 dark:text-red-300 mt-0.5">Active DMs</div>
                    <div className="text-[10px] text-red-500/70">High confidence</div>
                  </div>
                  <div className="bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800/30 rounded-lg p-3 text-center">
                    <div className="text-2xl font-bold text-amber-600 dark:text-amber-400">{result.possible.length}</div>
                    <div className="text-xs text-amber-700 dark:text-amber-300 mt-0.5">Possible DMs</div>
                    <div className="text-[10px] text-amber-500/70">More data needed</div>
                  </div>
                  <div className="bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-800/30 rounded-lg p-3 text-center">
                    <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">{result.related.length}</div>
                    <div className="text-xs text-blue-700 dark:text-blue-300 mt-0.5">Related DMs</div>
                    <div className="text-[10px] text-blue-500/70">Co-occurring</div>
                  </div>
                </div>

                {/* Active DMs */}
                {result.active.length > 0 && (
                  <div>
                    <h3 className="text-sm font-medium flex items-center gap-2 mb-3">
                      <Shield className="h-4 w-4 text-red-500" />
                      Active DMs — Strong evidence
                    </h3>
                    <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
                      {result.active.map(dm => (
                        <DmCard key={dm.dm_code} dm={dm} label="Active" icon={<Shield className="h-4 w-4 text-red-500" />} />
                      ))}
                    </div>
                  </div>
                )}

                {/* Possible DMs */}
                {result.possible.length > 0 && (
                  <div>
                    <h3 className="text-sm font-medium flex items-center gap-2 mb-3">
                      <AlertTriangle className="h-4 w-4 text-amber-500" />
                      Possible DMs — Moderate likelihood
                    </h3>
                    <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
                      {result.possible.map(dm => (
                        <DmCard key={dm.dm_code} dm={dm} label="Possible" icon={<AlertTriangle className="h-4 w-4 text-amber-500" />} />
                      ))}
                    </div>
                  </div>
                )}

                {/* Related DMs */}
                {result.related.length > 0 && (
                  <div>
                    <h3 className="text-sm font-medium flex items-center gap-2 mb-3">
                      <Info className="h-4 w-4 text-blue-500" />
                      Related DMs — May act together
                    </h3>
                    <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
                      {result.related.map(dm => (
                        <DmCard key={dm.dm_code} dm={dm} label="Related" icon={<Info className="h-4 w-4 text-blue-500" />} />
                      ))}
                    </div>
                  </div>
                )}

                {result.active.length === 0 && result.possible.length === 0 && result.related.length === 0 && (
                  <div className="bg-card border border-border rounded-lg p-8 text-center text-muted-foreground">
                    <p className="text-sm">No credible DMs matched for these inputs.</p>
                    <p className="text-xs mt-1">Review material and fluid service — try different keywords or check spelling.</p>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </AppLayout>
  )
}

// ── Client-side Fallback Matcher ─────────────────────────────────────────────
// Exact port of screenAsset() from dm_screener_pro.html
interface MatchInput {
  material: string
  fluid: string
  tempMin: number
  tempMax: number
  pwht: boolean | null
}

function tokenizeRef(text: string): string[] {
  if (!text) return []
  return text.toLowerCase()
    .split(/\s+/)
    .filter(t => t.length > 1)
}

function matchTokens(dmKeywords: string[], inputTokens: string[]): boolean {
  if (!inputTokens.length) return false
  return dmKeywords.some(keyword => {
    const kwTokens = tokenizeRef(keyword)
    return kwTokens.some(k => inputTokens.includes(k) || inputTokens.some(t => t.includes(k)))
  })
}

function runClientSideMatch(kb: any[], input: MatchInput): DMResponse {
  const matTokens = tokenizeRef(input.material)
  const fluidTokens = tokenizeRef(input.fluid)
  const tmin = isNaN(input.tempMin) ? 0 : input.tempMin
  const tmax = isNaN(input.tempMax) ? 100 : input.tempMax
  const hasTempData = !isNaN(input.tempMin) && !isNaN(input.tempMax)

  const active: DM[] = []
  const possible: DM[] = []
  const related: DM[] = []

  for (const dm of kb) {
    const matMatch = matchTokens(dm.materials || [], matTokens)
    const fluidMatch = matchTokens(dm.fluids || [], fluidTokens)
    const dmTempMin = dm.temp_min ?? -999
    const dmTempMax = dm.temp_max ?? 999
    const tempMatch = tmax >= dmTempMin && tmin <= dmTempMax
    const score = (matMatch ? 1 : 0) + (fluidMatch ? 1 : 0) + (tempMatch ? 1 : 0)

    // Classification — exact order from screenAsset()
    if (matMatch && fluidMatch && (tempMatch || !hasTempData)) {
      active.push({
        dm_code: dm.dm_code,
        dm_name: dm.dm_name,
        category: dm.category,
        confidence: 'high',
        nde: (dm.recommended_nde || []).slice(0, 2),
        mitigation: (dm.description || '').split(';')[0].trim(),
      })
    } else if (score >= 2) {
      possible.push({
        dm_code: dm.dm_code,
        dm_name: dm.dm_name,
        category: dm.category,
        confidence: 'medium',
        nde: (dm.recommended_nde || []).slice(0, 2),
      })
    } else if (matMatch && fluidMatch) {
      related.push({
        dm_code: dm.dm_code,
        dm_name: dm.dm_name,
        category: dm.category,
        confidence: 'low',
      })
    }
  }

  // PWHT Boost: exact from reference
  if (input.pwht === false) {
    for (const dm of kb) {
      if (dm.pwht_flag !== 'required') continue
      const matMatch = matchTokens(dm.materials || [], matTokens)
      const fluidMatch = matchTokens(dm.fluids || [], fluidTokens)
      if (matMatch && fluidMatch && !active.find(a => a.dm_code === dm.dm_code) && !possible.find(p => p.dm_code === dm.dm_code)) {
        possible.push({
          dm_code: dm.dm_code,
          dm_name: dm.dm_name + ' (No PWHT — elevated risk)',
          category: dm.category,
          confidence: 'medium',
          pwht_concern: true,
          nde: (dm.recommended_nde || []).slice(0, 2),
        })
      }
    }
  }

  // NDE from top active DM
  const topDM = active.length > 0 ? kb.find((k: any) => k.dm_code === active[0].dm_code) : null
  const nde = topDM && topDM.recommended_nde ? topDM.recommended_nde.slice(0, 2).join(', ') : 'UT Thickness (Baseline)'

  return {
    status: 'ok',
    active: active.slice(0, 6),
    possible: possible.slice(0, 4),
    related: related.slice(0, 4),
    total_matched: active.length + possible.length + related.length,
    total_screened: kb.length,
  } as DMResponse
}