'use client'

import { useState, useEffect, useCallback } from 'react'
import { createClient } from '@/lib/supabase/client'
import { ChevronRight, Home } from 'lucide-react'
import { cn } from '@/utils/cn'

/* ── Types ─────────────────────────────────────────────────── */

type Level = 1 | 2 | 3 | 4

interface BreadcrumbEntry {
  level: Level
  label: string
  areaId?: string
  equipId?: string
  circuitId?: string
}

interface DataRow {
  id: string
  [key: string]: unknown
}

interface Column {
  key: string
  label: string
  className?: string
}

/* ── Component ─────────────────────────────────────────────── */

export default function DrillDownTable() {
  const supabase = createClient()
  const [level, setLevel] = useState<Level>(1)
  const [breadcrumbs, setBreadcrumbs] = useState<BreadcrumbEntry[]>([
    { level: 1, label: 'Home' },
  ])
  const [rows, setRows] = useState<DataRow[]>([])
  const [columns, setColumns] = useState<Column[]>([])
  const [loading, setLoading] = useState(false)

  /* ── Load data for current level ──────────────────────────── */

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) { setLoading(false); return }

      const { data: appUser } = await supabase
        .from('app_users')
        .select('company_id')
        .eq('auth_user_id', user.id)
        .maybeSingle() as unknown as { data: { company_id: string } | null }

      if (!appUser?.company_id) { setLoading(false); return }

      const cid = appUser.company_id
      const current = breadcrumbs[breadcrumbs.length - 1]

      if (level === 1) {
        // Level 1: Plant Areas with equipment count
        const { data: areas } = await (supabase as any)
          .from('plant_areas')
          .select('id, name, description')
          .eq('company_id', cid)
          .order('name')

        if (!areas) { setRows([]); setLoading(false); return }

        // Count equipment per area
        const rowsWithCount = await Promise.all(
          areas.map(async (area: { id: string; name: string; description: string | null }) => {
            const { count } = await (supabase as any)
              .from('equipment')
              .select('id', { count: 'exact', head: true })
              .eq('company_id', cid)
              .eq('area_id', area.id)
            return { ...area, equipment_count: count ?? 0 }
          })
        )

        setColumns([
          { key: 'name', label: 'Area Name' },
          { key: 'description', label: 'Description' },
          { key: 'equipment_count', label: 'Equipment Count', className: 'text-right' },
        ])
        setRows(rowsWithCount)
      }

      if (level === 2 && current.areaId) {
        // Level 2: Equipment in selected area
        const { data: equips } = await (supabase as any)
          .from('equipment')
          .select('id, tag, type, fluid_service, risk_category, compliance_status')
          .eq('company_id', cid)
          .eq('area_id', current.areaId)
          .order('tag')

        setColumns([
          { key: 'tag', label: 'Tag' },
          { key: 'type', label: 'Type' },
          { key: 'fluid_service', label: 'Fluid Service' },
          { key: 'risk_category', label: 'Risk', className: 'capitalize' },
          { key: 'compliance_status', label: 'Compliance', className: 'capitalize' },
        ])
        setRows(equips || [])
      }

      if (level === 3 && current.equipId) {
        // Level 3: Circuits for selected equipment
        const { data: circuits } = await (supabase as any)
          .from('circuits')
          .select('id, name, description, governing_cr_cache')
          .eq('company_id', cid)
          .eq('equipment_id', current.equipId)
          .order('name')

        setColumns([
          { key: 'name', label: 'Circuit Name' },
          { key: 'description', label: 'Description' },
          { key: 'governing_cr_cache', label: 'Governing CR (mm/yr)', className: 'text-right tabular-nums' },
        ])
        setRows(circuits || [])
      }

      if (level === 4 && current.circuitId) {
        // Level 4: CML Points for selected circuit
        const { data: cmls } = await (supabase as any)
          .from('cml_points')
          .select('id, location_label, nominal_thickness, t_min, retirement_factor, cml_type, is_active')
          .eq('company_id', cid)
          .eq('circuit_id', current.circuitId)
          .order('location_label')

        setColumns([
          { key: 'location_label', label: 'Location' },
          { key: 'cml_type', label: 'Type', className: 'uppercase' },
          { key: 'nominal_thickness', label: 'Nominal (mm)', className: 'text-right tabular-nums' },
          { key: 't_min', label: 'T-min (mm)', className: 'text-right tabular-nums' },
          { key: 'retirement_factor', label: 'RF', className: 'text-right tabular-nums' },
          { key: 'is_active', label: 'Active' },
        ])
        setRows(cmls || [])
      }

    } catch (err) {
      console.error('Drill-down load error:', err)
    } finally {
      setLoading(false)
    }
  }, [supabase, level, breadcrumbs])

  useEffect(() => { loadData() }, [loadData])

  /* ── Navigation ───────────────────────────────────────────── */

  const drillToLevel = (targetLevel: Level, row: DataRow) => {
    if (targetLevel === 2) {
      // Clicked area → go to equipment
      setBreadcrumbs([
        { level: 1, label: 'Home' },
        { level: 2, label: row.name as string, areaId: row.id },
      ])
      setLevel(2)
    } else if (targetLevel === 3) {
      // Clicked equipment → go to circuits
      const current = breadcrumbs[breadcrumbs.length - 1]
      setBreadcrumbs([
        { level: 1, label: 'Home' },
        { level: 2, label: current.label, areaId: current.areaId },
        { level: 3, label: row.tag as string, equipId: row.id },
      ])
      setLevel(3)
    } else if (targetLevel === 4) {
      // Clicked circuit → go to CML points
      const prev = breadcrumbs[breadcrumbs.length - 2]
      setBreadcrumbs([
        { level: 1, label: 'Home' },
        { level: 2, label: prev.label, areaId: prev.areaId },
        { level: 3, label: breadcrumbs[breadcrumbs.length - 1].label, equipId: breadcrumbs[breadcrumbs.length - 1].equipId },
        { level: 4, label: row.name as string, circuitId: row.id },
      ])
      setLevel(4)
    }
  }

  const navigateToCrumb = (targetIndex: number) => {
    const crumb = breadcrumbs[targetIndex]
    setBreadcrumbs(breadcrumbs.slice(0, targetIndex + 1))
    setLevel(crumb.level)
  }

  /* ── Row click handler ────────────────────────────────────── */

  const handleRowClick = (row: DataRow) => {
    if (level < 4) {
      drillToLevel((level + 1) as Level, row)
    }
  }

  /* ── Render ───────────────────────────────────────────────── */

  return (
    <div className="rounded-xl border border-border bg-card">
      {/* Breadcrumb */}
      <div className="flex items-center gap-1.5 px-4 py-3 border-b border-border text-sm">
        {breadcrumbs.map((crumb, idx) => (
          <span key={idx} className="flex items-center gap-1.5">
            {idx > 0 && <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />}
            {idx === 0 ? (
              <Home className="h-3.5 w-3.5 text-muted-foreground" />
            ) : null}
            {idx < breadcrumbs.length - 1 ? (
              <button
                onClick={() => navigateToCrumb(idx)}
                className="text-primary hover:underline cursor-pointer"
              >
                {crumb.label}
              </button>
            ) : (
              <span className="text-foreground font-medium">{crumb.label}</span>
            )}
          </span>
        ))}
      </div>

      {/* Table */}
      {loading ? (
        <div className="p-8 text-center">
          <span className="inline-block h-5 w-5 animate-spin rounded-full border-2 border-muted-foreground border-t-transparent" />
        </div>
      ) : rows.length === 0 ? (
        <div className="p-8 text-center text-sm text-muted-foreground">
          No data found
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                {columns.map((col) => (
                  <th
                    key={col.key}
                    className={cn(
                      'px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider',
                      col.className,
                    )}
                  >
                    {col.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr
                  key={row.id}
                  onClick={() => level < 4 ? handleRowClick(row) : undefined}
                  className={cn(
                    'border-b border-border last:border-0 transition-colors',
                    level < 4 && 'cursor-pointer hover:bg-accent/50',
                    level === 4 && 'cursor-default',
                  )}
                >
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      className={cn('px-4 py-3', col.className)}
                    >
                      {col.key === 'is_active'
                        ? (row[col.key] ? '✅ Yes' : '— No')
                        : col.key === 'governing_cr_cache'
                          ? (row[col.key] != null ? Number(row[col.key]).toFixed(4) : '—')
                          : col.key === 'nominal_thickness' || col.key === 't_min' || col.key === 'retirement_factor'
                            ? (row[col.key] != null ? Number(row[col.key]).toFixed(2) : '—')
                            : (row[col.key] as string ?? '—')}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Footer hint */}
      {level < 4 && rows.length > 0 && (
        <div className="px-4 py-2 text-xs text-muted-foreground border-t border-border">
          Click a row to drill down
        </div>
      )}
    </div>
  )
}
