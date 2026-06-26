'use client'
export const dynamic = 'force-dynamic'

import { createClient } from '@/lib/supabase/client'
import { useEffect, useState, useMemo, useCallback } from 'react'
import {
  Pipette, Search, Filter, Calendar, ChevronDown, ChevronRight,
  Ruler, Hash, Activity, Gauge, Eye
} from 'lucide-react'
import AppLayout from '@/components/layout/app-layout'
import { cn } from '@/utils/cn'
import type { Database } from '@/types/database'

type CMLPoint = Database['public']['Tables']['cml_points']['Row']
type Circuit = Database['public']['Tables']['circuits']['Row']
type Equipment = Database['public']['Tables']['equipment']['Row']
type ThicknessReading = Database['public']['Tables']['thickness_readings']['Row']

interface CMLWithMeta extends CMLPoint {
  equipment_tag: string | null
  circuit_name: string | null
  latest_reading: number | null
  latest_reading_date: string | null
  readings: ThicknessReading[]
}

export default function CMLPointsPage() {
  const [cmls, setCmls] = useState<CMLWithMeta[]>([])
  const [circuits, setCircuits] = useState<Circuit[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [circuitFilter, setCircuitFilter] = useState('')
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const supabase = createClient()

  useEffect(() => {
    async function load() {
      try {
        // Fetch circuits for filter dropdown
        const { data: circuitRows } = await supabase
          .from('circuits')
          .select('*')
          .order('name') as unknown as { data: Circuit[] | null }

        // Fetch all CML points
        const { data: cmlRows, error: cmlErr } = await supabase
          .from('cml_points')
          .select('*')
          .order('location_label') as unknown as { data: CMLPoint[] | null; error: any }

        if (cmlErr) throw cmlErr
        if (!cmlRows) { setLoading(false); return }

        // Get equipment mapping
        const equipIds = [...new Set(cmlRows.map((c) => c.equipment_id))]
        const { data: equipRows } = await supabase
          .from('equipment')
          .select('id, tag')
          .in('id', equipIds) as unknown as { data: { id: string; tag: string }[] | null }

        const equipMap = new Map<string, string>()
        if (equipRows) {
          for (const e of equipRows as Equipment[]) {
            equipMap.set(e.id, e.tag)
          }
        }

        // Get circuit mapping
        const circuitMap = new Map<string, string>()
        if (circuitRows) {
          setCircuits(circuitRows as Circuit[])
          for (const c of circuitRows as Circuit[]) {
            circuitMap.set(c.id, c.name)
          }
        }

        // Get latest reading for each CML — batch query
        const cmlIds = cmlRows.map((c) => c.id)
        const { data: readingRows } = await supabase
          .from('thickness_readings')
          .select('cml_point_id, reading_mm, reading_date')
          .in('cml_point_id', cmlIds)
          .order('reading_date', { ascending: false }) as unknown as { data: { cml_point_id: string; reading_mm: number; reading_date: string }[] | null }

        // Find latest reading per CML
        const latestReadingMap = new Map<string, { reading_mm: number; reading_date: string }>()
        if (readingRows) {
          const seen = new Set<string>()
          for (const r of readingRows) {
            if (!seen.has(r.cml_point_id)) {
              seen.add(r.cml_point_id)
              latestReadingMap.set(r.cml_point_id, {
                reading_mm: r.reading_mm,
                reading_date: r.reading_date,
              })
            }
          }
        }

        const result: CMLWithMeta[] = (cmlRows as CMLPoint[]).map((cml) => ({
          ...cml,
          equipment_tag: equipMap.get(cml.equipment_id) || null,
          circuit_name: cml.circuit_id ? circuitMap.get(cml.circuit_id) || null : null,
          latest_reading: latestReadingMap.get(cml.id)?.reading_mm ?? null,
          latest_reading_date: latestReadingMap.get(cml.id)?.reading_date ?? null,
          readings: [],
        }))

        setCmls(result)
      } catch (err) {
        console.error('Failed to load CML points:', err)
      }
      setLoading(false)
    }
    load()
  }, [supabase])

  const filtered = useMemo(() => {
    let result = cmls
    // Apply circuit filter
    if (circuitFilter) {
      result = result.filter((c) => c.circuit_id === circuitFilter)
    }
    // Apply search
    if (search.trim()) {
      const q = search.toLowerCase()
      result = result.filter(
        (c) =>
          c.location_label.toLowerCase().includes(q) ||
          (c.equipment_tag && c.equipment_tag.toLowerCase().includes(q))
      )
    }
    return result
  }, [cmls, search, circuitFilter])

  const toggleExpand = useCallback(async (id: string) => {
    if (expandedId === id) {
      setExpandedId(null)
      return
    }

    // Find the CML
    const cml = cmls.find((c) => c.id === id)
    if (!cml) return

    // Load readings if not already loaded
    if (cml.readings.length === 0) {
      try {
        const { data } = await supabase
          .from('thickness_readings')
          .select('*')
          .eq('cml_point_id', id)
          .order('reading_date', { ascending: false }) as unknown as { data: ThicknessReading[] | null }

        if (data) {
          setCmls((prev) =>
            prev.map((c) =>
              c.id === id ? { ...c, readings: data } : c
            )
          )
        }
      } catch (err) {
        console.error('Failed to load readings:', err)
      }
    }

    setExpandedId(id)
  }, [expandedId, cmls, supabase])

  return (
    <AppLayout>
    <div className="px-6 sm:px-8 py-8">
      <div className="mb-6">
        <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight">CML Points</h1>
        <p className="text-sm text-muted-foreground">Condition Monitoring Locations — titik ukur ketebalan</p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3 mb-4">
        {/* Search */}
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search by location label or equipment tag..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-border bg-background pl-9 pr-4 py-2 text-sm placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>

        {/* Circuit filter */}
        <div className="relative min-w-[160px]">
          <Filter className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <select
            value={circuitFilter}
            onChange={(e) => setCircuitFilter(e.target.value)}
            className="w-full rounded-lg border border-border bg-background pl-9 pr-8 py-2 text-sm appearance-none focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value="">All Circuits</option>
            {circuits.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
        </div>

        {circuitFilter && (
          <button
            onClick={() => setCircuitFilter('')}
            className="text-xs text-muted-foreground hover:text-foreground underline"
          >
            Clear filter
          </button>
        )}
      </div>

      {loading ? (
        <div className="bg-card border border-border/70 rounded-xl">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-12 border-b border-border/50 last:border-b-0 animate-pulse bg-muted/10" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="bg-card border border-border/70 rounded-xl p-8 text-center text-muted-foreground">
          <Pipette className="h-8 w-8 mx-auto mb-2 opacity-40" />
          <p className="text-sm">{search || circuitFilter ? 'No CML points match your criteria.' : 'No CML points yet.'}</p>
        </div>
      ) : (
        <div className="bg-card border border-border overflow-hidden rounded-xl">
          {/* Table header */}
          <div className="grid grid-cols-[2fr_1.5fr_1.5fr_1fr_1fr_1.5fr_auto] gap-3 px-6 py-4 text-xs font-medium text-muted-foreground uppercase tracking-wider border-b border-border">
            <span>Location Label</span>
            <span>Equipment Tag</span>
            <span>Circuit Name</span>
            <span>Nominal Thickness</span>
            <span>T-Min</span>
            <span>Latest Reading</span>
            <span></span>
          </div>

          <div className="divide-y divide-border/50">
            {filtered.map((cml) => {
              const isExpanded = expandedId === cml.id
              return (
                <div key={cml.id}>
                  {/* CML row */}
                  <button
                    onClick={() => toggleExpand(cml.id)}
                    className="w-full grid grid-cols-[2fr_1.5fr_1.5fr_1fr_1fr_1.5fr_auto] gap-3 px-6 py-3.5 text-sm items-center text-left hover:bg-accent/20 transition-colors"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <Pipette className="h-4 w-4 shrink-0 text-muted-foreground" />
                      <span className="font-medium truncate">{cml.location_label}</span>
                    </div>
                    <div className="text-muted-foreground truncate font-mono text-xs">
                      {cml.equipment_tag || <span className="italic text-muted-foreground/40">—</span>}
                    </div>
                    <div className="text-muted-foreground truncate text-xs flex items-center gap-1">
                      <Activity className="h-3 w-3 shrink-0" />
                      {cml.circuit_name || <span className="italic text-muted-foreground/40">—</span>}
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Ruler className="h-3.5 w-3.5 text-muted-foreground" />
                      <span className="font-mono text-xs tabular-nums">{cml.nominal_thickness} mm</span>
                    </div>
                    <div className="font-mono text-xs tabular-nums text-muted-foreground">
                      {cml.t_min != null ? `${cml.t_min} mm` : <span className="italic text-muted-foreground/40">—</span>}
                    </div>
                    <div className="flex items-center gap-1.5">
                      {(cml.latest_reading != null) ? (
                        <>
                          <Gauge className={cn(
                            'h-3.5 w-3.5',
                            cml.latest_reading > (cml.t_min ?? 0) ? 'text-green-500' : 'text-amber-500'
                          )} />
                          <span className="font-mono text-xs tabular-nums">
                            {cml.latest_reading.toFixed(2)} mm
                          </span>
                          {cml.latest_reading_date && (
                            <span className="text-[10px] text-muted-foreground/50 ml-1">
                              {new Date(cml.latest_reading_date).toLocaleDateString()}
                            </span>
                          )}
                        </>
                      ) : (
                        <span className="italic text-muted-foreground/40">—</span>
                      )}
                    </div>
                    <div className="flex items-center justify-end">
                      {isExpanded ? (
                        <ChevronDown className="h-4 w-4 text-muted-foreground" />
                      ) : (
                        <ChevronRight className="h-4 w-4 text-muted-foreground" />
                      )}
                    </div>
                  </button>

                  {/* Expanded readings history */}
                  {isExpanded && (
                    <div className="border-t border-border/50 bg-muted/10">
                      {cml.readings.length === 0 ? (
                        <div className="px-8 py-4 text-xs text-muted-foreground">
                          Loading readings...
                        </div>
                      ) : (
                        <div className="p-4">
                          <div className="flex items-center gap-2 mb-3">
                            <Calendar className="h-4 w-4 text-muted-foreground" />
                            <span className="text-xs font-medium text-muted-foreground">
                              Thickness Readings History ({cml.readings.length})
                            </span>
                          </div>

                          {/* Readings table */}
                          <div className="border border-border/50 rounded-lg overflow-hidden">
                            <div className="grid grid-cols-[1.5fr_1.5fr_1fr_1.5fr] gap-3 px-6 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider border-b border-border/50">
                              <span>Date</span>
                              <span>Reading (mm)</span>
                              <span>Representative</span>
                              <span>Notes</span>
                            </div>
                            {cml.readings.map((r) => (
                              <div
                                key={r.id}
                                className="grid grid-cols-[1.5fr_1.5fr_1fr_1.5fr] gap-3 px-6 py-3.5 text-sm items-center border-b border-border/30 last:border-b-0 hover:bg-accent/20 transition-colors"
                              >
                                <div className="font-mono text-xs">
                                  {new Date(r.reading_date).toLocaleDateString('en-GB', {
                                    day: '2-digit', month: 'short', year: 'numeric'
                                  })}
                                </div>
                                <div className="font-mono text-xs tabular-nums font-medium">
                                  {r.reading_mm.toFixed(2)} mm
                                </div>
                                <div>
                                  {r.is_representative ? (
                                    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-green-500/10 text-green-600">
                                      Yes
                                    </span>
                                  ) : (
                                    <span className="text-muted-foreground/40 text-[10px]">—</span>
                                  )}
                                </div>
                                <div className="text-xs text-muted-foreground truncate">
                                  {r.notes || <span className="italic text-muted-foreground/40">—</span>}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
    </AppLayout>
  )
}
