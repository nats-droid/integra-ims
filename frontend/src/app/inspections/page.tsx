'use client'

import { useEffect, useState, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase/client'
import type { Database } from '@/types/database'
import AppLayout from '@/components/layout/app-layout'
import { cn } from '@/utils/cn'
import { toast } from 'sonner'
import { Search, Plus, ClipboardCheck, ChevronRight } from 'lucide-react'

type InspectionEvent = Database['public']['Tables']['inspection_events']['Row']
type Equipment = Database['public']['Tables']['equipment']['Row']
type PlantArea = Database['public']['Tables']['plant_areas']['Row']
type AppUser = Database['public']['Tables']['app_users']['Row']

interface InspectionRow {
  id: string
  event_date: string
  equipment_tag: string | null
  equipment_type: string | null
  equipment_area: string | null
  inspection_type: string
  inspector_name: string | null
  status: 'draft' | 'submitted' | 'approved' | 'rejected'
  notes: string | null
}

const STATUS_CONFIG: Record<string, { label: string; className: string }> = {
  draft: {
    label: 'Draft',
    className:
      'bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400',
  },
  submitted: {
    label: 'Submitted',
    className:
      'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  },
  approved: {
    label: 'Approved',
    className:
      'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  },
  rejected: {
    label: 'Rejected',
    className:
      'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  },
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

function notesPreview(notes: string | null, maxLen = 48): string {
  if (!notes) return '—'
  return notes.length > maxLen ? notes.slice(0, maxLen) + '…' : notes
}

export default function InspectionsPage() {
  const router = useRouter()
  const supabase = createClient()
  const sb = supabase as any

  const [rows, setRows] = useState<InspectionRow[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('')
  const [search, setSearch] = useState('')

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        setLoading(true)

        // 1. Fetch current user's company
        const {
          data: { user },
        } = await supabase.auth.getUser()
        if (!user) {
          if (!cancelled) setRows([])
          return
        }

        const { data: appUser } = await sb
          .from('app_users')
          .select('*')
          .eq('auth_user_id', user.id)
          .single()

        const companyId = (appUser as { company_id: string } | null)?.company_id
        if (!companyId) {
          if (!cancelled) setRows([])
          return
        }

        // 2. Fetch inspection events for this company
        const { data: eventsRaw, error: eventsErr } = await sb
          .from('inspection_events')
          .select('*')
          .eq('company_id', companyId)
          .order('event_date', { ascending: false })

        if (eventsErr) {
          console.error('Fetch inspections error:', eventsErr)
          toast.error('Failed to load inspections')
          return
        }

        const events = (eventsRaw || []) as InspectionEvent[]
        if (events.length === 0) {
          if (!cancelled) setRows([])
          return
        }

        // 3. Build equipment map (tag, type, area_id)
        const equipIds = [...new Set(events.map((e) => e.equipment_id))]
        const { data: equipRaw } = await sb
          .from('equipment')
          .select('*')
          .in('id', equipIds)

        const equipRows = (equipRaw || []) as Equipment[]
        const equipMap = new Map<string, { tag: string; type: string; area_id: string | null }>()
        for (const eq of equipRows) {
          equipMap.set(eq.id, { tag: eq.tag, type: eq.type, area_id: eq.area_id })
        }

        // 4. Build area name map
        const areaIds = [...new Set(equipRows.map((e) => e.area_id).filter(Boolean))] as string[]
        const areaNameMap = new Map<string, string>()
        if (areaIds.length > 0) {
          const { data: areaRaw } = await sb
            .from('plant_areas')
            .select('id, name')
            .in('id', areaIds)

          if (areaRaw) {
            for (const a of areaRaw as { id: string; name: string }[]) {
              areaNameMap.set(a.id, a.name)
            }
          }
        }

        // 5. Build inspector name map
        const inspectorIds = [...new Set(events.map((e) => e.inspector_id).filter(Boolean))] as string[]
        const inspectorMap = new Map<string, string>()
        if (inspectorIds.length > 0) {
          const { data: inspectorRaw } = await sb
            .from('app_users')
            .select('id, full_name')
            .in('id', inspectorIds)

          if (inspectorRaw) {
            for (const u of inspectorRaw as { id: string; full_name: string }[]) {
              inspectorMap.set(u.id, u.full_name)
            }
          }
        }

        // 6. Build result rows
        const result: InspectionRow[] = events.map((ev) => {
          const eq = equipMap.get(ev.equipment_id)
          return {
            id: ev.id,
            event_date: ev.event_date,
            equipment_tag: eq?.tag || null,
            equipment_type: eq?.type || null,
            equipment_area: eq?.area_id ? areaNameMap.get(eq.area_id) || null : null,
            inspection_type: ev.inspection_type,
            inspector_name: ev.inspector_id ? inspectorMap.get(ev.inspector_id) || null : null,
            status: ev.status,
            notes: ev.notes,
          }
        })

        if (!cancelled) setRows(result)
      } catch (err) {
        console.error('Error loading inspections:', err)
        toast.error('Unexpected error loading inspections')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [supabase, sb])

  const filtered = useMemo(() => {
    let result = rows

    if (statusFilter) {
      result = result.filter((r) => r.status === statusFilter)
    }

    if (search.trim()) {
      const q = search.toLowerCase()
      result = result.filter(
        (r) =>
          (r.equipment_tag && r.equipment_tag.toLowerCase().includes(q)) ||
          r.inspection_type.toLowerCase().includes(q)
      )
    }

    return result
  }, [rows, statusFilter, search])

  const hasActiveFilters = statusFilter || search
  const clearFilters = () => {
    setStatusFilter('')
    setSearch('')
  }

  return (
    <AppLayout>
      <div className="px-8 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight">
              Inspections
            </h1>
            <p className="text-sm text-muted-foreground">
              Inspection events and checklist records
            </p>
          </div>
          <button
            onClick={() => router.push('/inspections/new')}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            <Plus className="h-4 w-4" />
            New Inspection
          </button>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3 mb-6">
          {/* Search */}
          <div className="relative flex-1 min-w-[200px] max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search by equipment tag..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded-lg border border-border bg-background pl-9 pr-4 py-2 text-sm placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          {/* Status filter */}
          <div className="relative min-w-[140px]">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm appearance-none focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="">All Statuses</option>
              <option value="draft">Draft</option>
              <option value="submitted">Submitted</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
            </select>
          </div>

          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="inline-flex items-center gap-1 rounded-lg border border-border px-3 py-2 text-sm text-muted-foreground hover:bg-accent transition-colors"
            >
              Clear filters
            </button>
          )}
        </div>

        {/* Loading state */}
        {loading ? (
          <div className="rounded-xl border border-border/70 overflow-hidden">
            {[1, 2, 3, 4, 5].map((i) => (
              <div
                key={i}
                className="h-14 border-b border-border/50 last:border-b-0 animate-pulse bg-muted/10"
              />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          /* Empty state */
          <div className="rounded-xl border border-border/70 p-12 text-center text-muted-foreground">
            <ClipboardCheck className="h-10 w-10 mx-auto mb-3 opacity-40" />
            <p className="text-sm font-medium">
              {hasActiveFilters
                ? 'No inspections match your criteria.'
                : 'No inspections recorded yet.'}
            </p>
            {hasActiveFilters && (
              <button
                onClick={clearFilters}
                className="mt-2 text-sm text-primary hover:underline"
              >
                Clear filters
              </button>
            )}
          </div>
        ) : (
          /* Table */
          <div className="rounded-xl border border-border/70 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border/70">
                    <th className="text-xs uppercase tracking-wider px-6 py-4 text-left font-medium text-muted-foreground">
                      Date
                    </th>
                    <th className="text-xs uppercase tracking-wider px-6 py-4 text-left font-medium text-muted-foreground">
                      Equipment Tag
                    </th>
                    <th className="text-xs uppercase tracking-wider px-6 py-4 text-left font-medium text-muted-foreground">
                      Equipment Type
                    </th>
                    <th className="text-xs uppercase tracking-wider px-6 py-4 text-left font-medium text-muted-foreground">
                      Inspection Type
                    </th>
                    <th className="text-xs uppercase tracking-wider px-6 py-4 text-left font-medium text-muted-foreground">
                      Inspector
                    </th>
                    <th className="text-xs uppercase tracking-wider px-6 py-4 text-left font-medium text-muted-foreground">
                      Status
                    </th>
                    <th className="text-xs uppercase tracking-wider px-6 py-4 text-left font-medium text-muted-foreground">
                      Notes
                    </th>
                    <th className="px-6 py-4 w-10"></th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((row) => {
                    const statusCfg = STATUS_CONFIG[row.status] || STATUS_CONFIG.draft
                    return (
                      <tr
                        key={row.id}
                        onClick={() =>
                          window.open(`/inspections/${row.id}`, '_blank')
                        }
                        className="border-b border-border/50 last:border-b-0 hover:bg-muted/20 cursor-pointer transition-colors"
                      >
                        <td className="px-6 py-3.5 font-mono text-xs tabular-nums">
                          {formatDate(row.event_date)}
                        </td>
                        <td className="px-6 py-3.5 font-medium">
                          {row.equipment_tag || (
                            <span className="italic text-muted-foreground/40">
                              —
                            </span>
                          )}
                        </td>
                        <td className="px-6 py-3.5 text-muted-foreground capitalize">
                          {row.equipment_type || (
                            <span className="italic text-muted-foreground/40">
                              —
                            </span>
                          )}
                        </td>
                        <td className="px-6 py-3.5">
                          {row.inspection_type}
                        </td>
                        <td className="px-6 py-3.5 text-muted-foreground">
                          {row.inspector_name || (
                            <span className="italic text-muted-foreground/40">
                              —
                            </span>
                          )}
                        </td>
                        <td className="px-6 py-3.5">
                          <span
                            className={cn(
                              'inline-block rounded-full px-2.5 py-0.5 text-xs font-medium',
                              statusCfg.className
                            )}
                          >
                            {statusCfg.label}
                          </span>
                        </td>
                        <td className="px-6 py-3.5 text-muted-foreground text-xs max-w-[200px] truncate">
                          {notesPreview(row.notes)}
                        </td>
                        <td className="px-6 py-3.5">
                          <ChevronRight className="h-4 w-4 text-muted-foreground" />
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  )
}
