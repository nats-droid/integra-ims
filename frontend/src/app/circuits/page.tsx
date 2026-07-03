'use client'
export const dynamic = 'force-dynamic'

import { createClient } from '@/lib/supabase/client'
import { useEffect, useState, useMemo, useCallback } from 'react'
import { Activity, Search, ChevronDown, ChevronRight, Gauge, Pipette, Ruler, Hash } from 'lucide-react'
import AppLayout from '@/components/layout/app-layout'
import { cn } from '@/utils/cn'
import type { Database } from '@/types/database'

type Circuit = Database['public']['Tables']['circuits']['Row']
type Equipment = Database['public']['Tables']['equipment']['Row']
type CMLPoint = Database['public']['Tables']['cml_points']['Row']
type ThicknessReading = Database['public']['Tables']['thickness_readings']['Row']

interface CircuitWithEquipment extends Circuit {
  equipment_tag: string | null
  equipment_type: string | null
}

interface CircuitWithCMLs extends CircuitWithEquipment {
  cmls: CMLPoint[]
}

export default function CircuitsPage() {
  const [circuits, setCircuits] = useState<CircuitWithCMLs[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const supabase = createClient()

  useEffect(() => {
    async function load() {
      try {
        // Get all circuits with equipment data
        const { data: circuitRows, error: circuitErr } = await supabase
          .from('circuits')
          .select('*')
          .order('name') as unknown as { data: Circuit[] | null; error: any }

        if (circuitErr) throw circuitErr
        if (!circuitRows) { setLoading(false); return }

        // Get equipment mapping
        const equipIds = [...new Set(circuitRows.map((c) => c.equipment_id))]
        const { data: equipRows } = await supabase
          .from('equipment')
          .select('id, tag, type')
          .in('id', equipIds) as unknown as { data: { id: string; tag: string; type: string }[] | null }

        const equipMap = new Map<string, { tag: string; type: string }>()
        if (equipRows) {
          for (const e of equipRows) {
            equipMap.set(e.id, { tag: e.tag, type: e.type })
          }
        }

        // Get all CML points grouped by circuit
        const { data: cmlRows } = await supabase
          .from('cml_points')
          .select('*')
          .order('location_label') as unknown as { data: CMLPoint[] | null }

        const cmlByCircuit = new Map<string, CMLPoint[]>()
        if (cmlRows) {
          for (const cml of cmlRows) {
            if (cml.circuit_id) {
              const list = cmlByCircuit.get(cml.circuit_id) || []
              list.push(cml)
              cmlByCircuit.set(cml.circuit_id, list)
            }
          }
        }

        const result: CircuitWithCMLs[] = (circuitRows as Circuit[]).map((c) => ({
          ...c,
          equipment_tag: equipMap.get(c.equipment_id)?.tag || null,
          equipment_type: equipMap.get(c.equipment_id)?.type || null,
          cmls: cmlByCircuit.get(c.id) || [],
        }))

        setCircuits(result)
      } catch (err) {
        console.error('Failed to load circuits:', err)
      }
      setLoading(false)
    }
    load()
  }, [supabase])

  const filtered = useMemo(() => {
    if (!search.trim()) return circuits
    const q = search.toLowerCase()
    return circuits.filter(
      (c) =>
        c.name.toLowerCase().includes(q) ||
        (c.equipment_tag && c.equipment_tag.toLowerCase().includes(q))
    )
  }, [circuits, search])

  const toggleExpand = useCallback((id: string) => {
    setExpandedId((prev) => (prev === id ? null : id))
  }, [])

  // Latest reading for a given CML
  const [readingsCache, setReadingsCache] = useState<Record<string, number | null>>({})

  const loadLatestReading = useCallback(
    async (cmlId: string) => {
      if (readingsCache[cmlId] !== undefined) return readingsCache[cmlId]
      try {
        const { data } = await supabase
          .from('thickness_readings')
          .select('reading_mm')
          .eq('cml_point_id', cmlId)
          .order('reading_date', { ascending: false })
          .limit(1) as unknown as { data: { reading_mm: number }[] | null }
        const val = data && data.length > 0 ? data[0].reading_mm : null
        setReadingsCache((prev) => ({ ...prev, [cmlId]: val }))
        return val
      } catch {
        return null
      }
    },
    [supabase, readingsCache]
  )

  // Auto-load latest reading when a circuit is expanded
  useEffect(() => {
    if (!expandedId) return
    const circuit = circuits.find((c) => c.id === expandedId)
    if (!circuit) return
    for (const cml of circuit.cmls) {
      if (readingsCache[cml.id] === undefined) {
        loadLatestReading(cml.id)
      }
    }
  }, [expandedId, circuits, readingsCache, loadLatestReading])

  return (
    <AppLayout>
    <div className="px-6 sm:px-8 py-8">
      <div className="mb-6">
        <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight">Circuits</h1>
        <p className="text-sm text-muted-foreground">Corrosion circuits — CML groups within a single equipment</p>
      </div>

      {/* Search */}
      <div className="relative mb-4 max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <input
          type="text"
          placeholder="Search by circuit name or equipment tag..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full rounded-lg border border-border bg-background pl-9 pr-4 py-2 text-sm placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary"
        />
      </div>

      {loading ? (
        <div className="bg-card border border-border/70 rounded-xl">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-12 border-b border-border/50 last:border-b-0 animate-pulse bg-muted/10" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="bg-card border border-border/70 rounded-xl p-8 text-center text-muted-foreground">
          <Activity className="h-8 w-8 mx-auto mb-2 opacity-40" />
          <p className="text-sm">{search ? 'No circuits match your search.' : 'No circuits yet.'}</p>
        </div>
      ) : (
        <div className="bg-card border border-border overflow-hidden rounded-xl">
          {/* Table header */}
          <div className="grid grid-cols-[2fr_1.5fr_1fr_2fr_1fr_auto] gap-4 px-6 py-4 text-xs font-medium text-muted-foreground uppercase tracking-wider border-b border-border">
            <span>Circuit Name</span>
            <span>Equipment Tag</span>
            <span>Equipment Type</span>
            <span>Description</span>
            <span>Governing CR</span>
            <span></span>
          </div>

          <div className="divide-y divide-border/50">
            {filtered.map((circuit) => {
              const isExpanded = expandedId === circuit.id
              return (
                <div key={circuit.id}>
                  {/* Circuit row */}
                  <button
                    onClick={() => toggleExpand(circuit.id)}
                    className="w-full grid grid-cols-[2fr_1.5fr_1fr_2fr_1fr_auto] gap-4 px-6 py-3.5 text-sm items-center text-left hover:bg-accent/20 transition-colors"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <Activity className="h-4 w-4 shrink-0 text-muted-foreground" />
                      <span className="font-medium truncate">{circuit.name}</span>
                    </div>
                    <div className="text-muted-foreground truncate font-mono text-xs">
                      {circuit.equipment_tag || <span className="italic text-muted-foreground/40">—</span>}
                    </div>
                    <div className="text-muted-foreground capitalize text-xs">
                      {circuit.equipment_type || <span className="italic text-muted-foreground/40">—</span>}
                    </div>
                    <div className="text-muted-foreground text-xs truncate">
                      {circuit.description || <span className="italic text-muted-foreground/40">—</span>}
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Gauge className="h-3.5 w-3.5 text-muted-foreground" />
                      <span className="font-mono text-sm tabular-nums">
                        {circuit.governing_cr_cache != null
                          ? `${circuit.governing_cr_cache.toFixed(2)} mm/y`
                          : <span className="text-muted-foreground/40 italic">—</span>}
                      </span>
                    </div>
                    <div className="flex items-center justify-end">
                      {isExpanded ? (
                        <ChevronDown className="h-4 w-4 text-muted-foreground" />
                      ) : (
                        <ChevronRight className="h-4 w-4 text-muted-foreground" />
                      )}
                    </div>
                  </button>

                  {/* Expanded CML list */}
                  {isExpanded && (
                    <div className="border-t border-border/50 bg-muted/10">
                      {circuit.cmls.length === 0 ? (
                        <div className="px-8 py-4 text-xs text-muted-foreground">
                          No CML points in this circuit.
                        </div>
                      ) : (
                        <div>
                          {/* CML header */}
                          <div className="grid grid-cols-[1.5fr_1fr_1fr_1fr_1.5fr] gap-3 px-8 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider border-b border-border/30">
                            <span>Location Label</span>
                            <span>Nominal Thickness</span>
                            <span>T-Min</span>
                            <span>Latest Reading</span>
                            <span>Type</span>
                          </div>
                          {circuit.cmls.map((cml) => (
                            <div
                              key={cml.id}
                              className="grid grid-cols-[1.5fr_1fr_1fr_1fr_1.5fr] gap-3 px-8 py-3.5 text-sm items-center border-b border-border/20 last:border-b-0 hover:bg-accent/20 transition-colors"
                            >
                              <div className="flex items-center gap-1.5 min-w-0">
                                <Pipette className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                                <span className="font-medium truncate">{cml.location_label}</span>
                              </div>
                              <div className="flex items-center gap-1.5">
                                <Ruler className="h-3.5 w-3.5 text-muted-foreground" />
                                <span className="font-mono text-xs tabular-nums">{cml.nominal_thickness} mm</span>
                              </div>
                              <div className="font-mono text-xs tabular-nums text-muted-foreground">
                                {cml.t_min != null ? `${cml.t_min} mm` : <span className="italic text-muted-foreground/40">—</span>}
                              </div>
                              <div className="font-mono text-xs tabular-nums">
                                <LatestReadingDisplay cmlId={cml.id} supabase={supabase} />
                              </div>
                              <div className="text-xs text-muted-foreground uppercase">
                                {cml.cml_type}
                              </div>
                            </div>
                          ))}
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

/** Inline component to fetch and display latest reading for a CML */
function LatestReadingDisplay({ cmlId, supabase }: { cmlId: string; supabase: ReturnType<typeof createClient> }) {
  const [reading, setReading] = useState<number | null | 'loading'>('loading')

  useEffect(() => {
    let cancelled = false
    async function fetchReading() {
      try {
        const { data } = await supabase
          .from('thickness_readings')
          .select('reading_mm')
          .eq('cml_point_id', cmlId)
          .order('reading_date', { ascending: false })
          .limit(1) as unknown as { data: { reading_mm: number }[] | null }
        if (!cancelled) {
          setReading(data && data.length > 0 ? data[0].reading_mm : null)
        }
      } catch {
        if (!cancelled) setReading(null)
      }
    }
    fetchReading()
    return () => { cancelled = true }
  }, [cmlId, supabase])

  if (reading === 'loading') {
    return <span className="text-muted-foreground/40 animate-pulse">...</span>
  }
  if (reading === null) {
    return <span className="italic text-muted-foreground/40">—</span>
  }
  return <span>{reading.toFixed(2)} mm</span>
}
