'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase/client'
import type { Database } from '@/types/database'
import AppLayout from '@/components/layout/app-layout'
import { cn } from '@/utils/cn'
import { toast } from 'sonner'
import {
  Search,
  Plus,
  ChevronRight,
  X,
  Wrench,
  FlaskConical,
  CheckCircle,
  Clock,
  FileX,
  Gauge,
  Box,
} from 'lucide-react'

type Equipment = Database['public']['Tables']['equipment']['Row']
type PlantArea = Database['public']['Tables']['plant_areas']['Row']

interface EquipmentRow extends Equipment {
  plant_area_name?: string | null
  cml_count?: number
  latest_reading_date?: string | null
}

const RISK_COLORS: Record<string, string> = {
  critical: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  high: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
  medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
  low: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
}

const COMPLIANCE_COLORS: Record<string, string> = {
  compliant: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
  'non-compliant': 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
}

const TYPE_ICONS: Record<string, React.ReactNode> = {
  piping: <Gauge className="h-4 w-4" />,
  vessel: <Box className="h-4 w-4" />,
  tank: <Box className="h-4 w-4" />,
  heater: <FlaskConical className="h-4 w-4" />,
  pump: <Wrench className="h-4 w-4" />,
  compressor: <Wrench className="h-4 w-4" />,
  valve: <Wrench className="h-4 w-4" />,
  other: <Wrench className="h-4 w-4" />,
}

export default function EquipmentListPage() {
  const router = useRouter()
  const supabase = createClient()
  const sb = supabase as any

  const DEMO_USER = {
    id: '3fca82af-b302-4d1e-8536-b89546ecfb15',
    company_id: 'c704d7e6-07fb-48a2-9152-564434d8653f',
    full_name: 'Dicki Wiryawan',
    role: 'super_admin',
  }

  const [equipment, setEquipment] = useState<EquipmentRow[]>([])
  const [areas, setAreas] = useState<PlantArea[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [riskFilter, setRiskFilter] = useState('')

  const fetchEquipment = useCallback(async () => {
    try {
      setLoading(true)
      const supabase = createClient()
      const sb = supabase as any

      const companyId = DEMO_USER.company_id
      if (!companyId) {
        setEquipment([])
        return
      }

      let query = sb
        .from('equipment')
        .select(
          `
          *,
          plant_area:plant_areas!equipment_area_id_fkey(name)
        `
        )
        .eq('company_id', companyId)
        .order('created_at', { ascending: false })

      if (search) {
        query = query.ilike('tag', `%${search}%`)
      }
      if (typeFilter) {
        query = query.eq('type', typeFilter)
      }
      if (riskFilter) {
        query = query.eq('risk_category', riskFilter)
      }

      const { data: equipData, error: equipError } = await query

      if (equipError) {
        console.error('Fetch equipment error:', equipError)
        toast.error('Failed to load equipment')
        return
      }

      const equipmentList = (equipData || []) as (Equipment & {
        plant_area: { name: string } | null
      })[]
      const equipmentIds = equipmentList.map((e) => e.id)
      let cmlCounts: Record<string, number> = {}
      let latestReadings: Record<string, string | null> = {}

      if (equipmentIds.length > 0) {
        const { data: cmlData } = await sb
          .from('cml_points')
          .select('equipment_id, id')
          .in('equipment_id', equipmentIds)
          .eq('is_active', true)

        if (cmlData) {
          const cmlRows = cmlData as { equipment_id: string; id: string }[]
          cmlCounts = cmlRows.reduce<Record<string, number>>((acc, cml) => {
            acc[cml.equipment_id] = (acc[cml.equipment_id] || 0) + 1
            return acc
          }, {} as Record<string, number>)
        }

        const { data: readingData } = await sb
          .from('thickness_readings')
          .select(
            `
            reading_date,
            cml_point:cml_points!thickness_readings_cml_point_id_fkey(equipment_id)
          `
          )
          .in('cml_point.equipment_id', equipmentIds)
          .order('reading_date', { ascending: false })

        if (readingData) {
          const readings = readingData as {
            reading_date: string
            cml_point: { equipment_id: string } | null
          }[]
          const seen = new Set<string>()
          for (const r of readings) {
            const eqId = r.cml_point?.equipment_id
            if (eqId && !seen.has(eqId)) {
              seen.add(eqId)
              latestReadings[eqId] = r.reading_date
            }
          }
        }
      }

      const rows: EquipmentRow[] = equipmentList.map((e) => ({
        ...e,
        plant_area_name: e.plant_area?.name || null,
        cml_count: cmlCounts[e.id] || 0,
        latest_reading_date: latestReadings[e.id] || null,
      }))

      setEquipment(rows)
    } catch (err) {
      console.error('Error fetching equipment:', err)
      toast.error('Unexpected error loading equipment')
    } finally {
      setLoading(false)
    }
  }, [search, typeFilter, riskFilter])

  useEffect(() => {
    fetchEquipment()
  }, [fetchEquipment])

  useEffect(() => {
    async function loadAreas() {
      const companyId = DEMO_USER.company_id
      if (!companyId) return

      const { data: areaData } = await sb
        .from('plant_areas')
        .select('*')
        .eq('company_id', companyId)
        .order('name')

      if (areaData) setAreas(areaData as PlantArea[])
    }
    loadAreas()
  }, [supabase, sb])

  const clearFilters = () => {
    setSearch('')
    setTypeFilter('')
    setRiskFilter('')
  }

  const hasActiveFilters = search || typeFilter || riskFilter

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight">Equipment</h1>
            <p className="text-sm text-muted-foreground">
              Manage your plant equipment and inspection data
            </p>
          </div>
          <button
            onClick={() => router.push('/equipment/new')}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            <Plus className="h-4 w-4" />
            Add Equipment
          </button>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[240px] max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search by tag..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded-lg border border-border bg-background py-2 pl-10 pr-4 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
            />
          </div>

          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
          >
            <option value="">All Types</option>
            <option value="piping">Piping</option>
            <option value="vessel">Vessel</option>
            <option value="tank">Tank</option>
            <option value="heater">Heater</option>
            <option value="pump">Pump</option>
            <option value="compressor">Compressor</option>
            <option value="valve">Valve</option>
            <option value="other">Other</option>
          </select>

          <select
            value={riskFilter}
            onChange={(e) => setRiskFilter(e.target.value)}
            className="rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
          >
            <option value="">All Risk Categories</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>

          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="inline-flex items-center gap-1 rounded-lg border border-border px-3 py-2 text-sm text-muted-foreground hover:bg-accent transition-colors"
            >
              <X className="h-3.5 w-3.5" />
              Clear
            </button>
          )}
        </div>

        {/* Table */}
        <div className="rounded-xl border border-border overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="px-6 py-4 text-left font-medium text-muted-foreground text-xs uppercase tracking-wider">Tag</th>
                  <th className="px-6 py-4 text-left font-medium text-muted-foreground text-xs uppercase tracking-wider">Type</th>
                  <th className="px-6 py-4 text-left font-medium text-muted-foreground text-xs uppercase tracking-wider">Fluid Service</th>
                  <th className="px-6 py-4 text-left font-medium text-muted-foreground text-xs uppercase tracking-wider">Area</th>
                  <th className="px-6 py-4 text-left font-medium text-muted-foreground text-xs uppercase tracking-wider">Risk</th>
                  <th className="px-6 py-4 text-left font-medium text-muted-foreground text-xs uppercase tracking-wider">Compliance</th>
                  <th className="px-6 py-4 text-left font-medium text-muted-foreground text-xs uppercase tracking-wider">Latest Reading</th>
                  <th className="px-6 py-4 text-center font-medium text-muted-foreground text-xs uppercase tracking-wider">CMLs</th>
                  <th className="px-6 py-4 w-10"></th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={9} className="px-6 py-12 text-center text-muted-foreground">
                      Loading equipment data...
                    </td>
                  </tr>
                ) : equipment.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="px-6 py-12 text-center text-muted-foreground">
                      <div className="flex flex-col items-center gap-2">
                        <Box className="h-8 w-8 text-muted-foreground/50" />
                        <p>No equipment found</p>
                        {hasActiveFilters && (
                          <button
                            onClick={clearFilters}
                            className="text-sm text-primary hover:underline"
                          >
                            Clear filters
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ) : (
                  equipment.map((eq) => (
                    <tr
                      key={eq.id}
                      onClick={() => router.push(`/equipment/${eq.id}`)}
                      className="border-b border-border hover:bg-muted/20 cursor-pointer transition-colors"
                    >
                      <td className="px-6 py-3.5 font-medium">{eq.tag}</td>
                      <td className="px-6 py-3.5">
                        <div className="flex items-center gap-1.5 capitalize">
                          {TYPE_ICONS[eq.type] || TYPE_ICONS.other}
                          <span>{eq.type}</span>
                        </div>
                      </td>
                      <td className="px-6 py-3.5 text-muted-foreground">
                        {eq.fluid_service || '—'}
                      </td>
                      <td className="px-6 py-3.5 text-muted-foreground">
                        {eq.plant_area_name || '—'}
                      </td>
                      <td className="px-6 py-3.5">
                        {eq.risk_category ? (
                          <span
                            className={cn(
                              'inline-block rounded-full px-2.5 py-0.5 text-xs font-medium capitalize',
                              RISK_COLORS[eq.risk_category],
                            )}
                          >
                            {eq.risk_category}
                          </span>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </td>
                      <td className="px-6 py-3.5">
                        <span
                          className={cn(
                            'inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium capitalize',
                            COMPLIANCE_COLORS[eq.compliance_status],
                          )}
                        >
                          {eq.compliance_status === 'compliant' ? (
                            <CheckCircle className="h-3 w-3" />
                          ) : eq.compliance_status === 'non-compliant' ? (
                            <FileX className="h-3 w-3" />
                          ) : (
                            <Clock className="h-3 w-3" />
                          )}
                          {eq.compliance_status === 'non-compliant'
                            ? 'Non-Compliant'
                            : eq.compliance_status}
                        </span>
                      </td>
                      <td className="px-6 py-3.5 text-muted-foreground text-xs">
                        {eq.latest_reading_date
                          ? new Date(eq.latest_reading_date).toLocaleDateString()
                          : '—'}
                      </td>
                      <td className="px-6 py-3.5 text-center">
                        <span className="inline-flex items-center justify-center rounded-full bg-muted px-2 py-0.5 text-xs font-medium tabular-nums">
                          {eq.cml_count}
                        </span>
                      </td>
                      <td className="px-6 py-3.5">
                        <ChevronRight className="h-4 w-4 text-muted-foreground" />
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </AppLayout>
  )
}
