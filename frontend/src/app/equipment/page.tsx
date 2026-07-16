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
  Download,
  Upload,
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
import { exportEquipmentExcel } from '@/lib/excel'

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

  const [equipment, setEquipment] = useState<EquipmentRow[]>([])
  const [areas, setAreas] = useState<PlantArea[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [riskFilter, setRiskFilter] = useState('')
  const [exporting, setExporting] = useState(false)
  const [importing, setImporting] = useState(false)
  const [importResult, setImportResult] = useState<{ success: number; errors: string[] } | null>(null)

  const fetchEquipment = useCallback(async () => {
    try {
      setLoading(true)
      const supabase = createClient()
      const sb = supabase as any

      const {
        data: { user },
      } = await supabase.auth.getUser()
      if (!user) {
        setEquipment([])
        return
      }

      const { data: appUser } = await sb
        .from('app_users')
        .select('*')
        .eq('auth_user_id', user.id)
        .single()

      const companyId = (appUser as { company_id: string } | null)?.company_id
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
        // Batch fetch CMLs
        let allCmls: {equipment_id: string, id: string}[] = []
        let cmlOffset = 0
        while (true) {
          const { data: batch } = await sb
            .from('cml_points')
            .select('equipment_id, id')
            .eq('company_id', companyId)
            .eq('is_active', true)
            .range(cmlOffset, cmlOffset + 999)
          if (!batch || batch.length === 0) break
          allCmls = [...allCmls, ...batch]
          if (batch.length < 1000) break
          cmlOffset += 1000
        }
        cmlCounts = allCmls.reduce<Record<string, number>>((acc, cml) => {
          acc[cml.equipment_id] = (acc[cml.equipment_id] || 0) + 1
          return acc
        }, {})

        // Batch fetch latest readings
        let allReadings: {reading_date: string, cml_point_id: string, cml_points: {equipment_id: string} | null}[] = []
        let rdOffset = 0
        while (true) {
          const { data: batch } = await (sb as any)
            .from('thickness_readings')
            .select('reading_date, cml_point_id, cml_points(equipment_id)')
            .eq('company_id', companyId)
            .order('reading_date', { ascending: false })
            .range(rdOffset, rdOffset + 999)
          if (!batch || batch.length === 0) break
          allReadings = [...allReadings, ...batch]
          if (batch.length < 1000) break
          rdOffset += 1000
        }
        const seen = new Set<string>()
        for (const r of allReadings) {
          const eqId = (r as any).cml_points?.equipment_id
          if (eqId && !seen.has(eqId)) {
            seen.add(eqId)
            latestReadings[eqId] = r.reading_date
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
      const {
        data: { user },
      } = await supabase.auth.getUser()
      if (!user) return

      const { data: appUser } = await sb
        .from('app_users')
        .select('*')
        .eq('auth_user_id', user.id)
        .single()

      const companyId = (appUser as { company_id: string } | null)?.company_id
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

  const handleExport = async () => {
    setExporting(true)
    try {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) throw new Error('Not authenticated')
      const { data: appUser } = await sb
        .from('app_users')
        .select('company_id')
        .eq('auth_user_id', user.id)
        .single()
      const companyId = (appUser as { company_id: string } | null)?.company_id
      if (!companyId) throw new Error('Company ID not found')

      const { data: eqData } = await supabase
        .from('equipment')
        .select('tag, type, area_id, fluid_service, material, design_pressure, design_temp_max, installation_date, insulation_type, notes, plant_areas(name)')
        .eq('company_id', companyId)
        .order('tag')

      const { data: cmlData } = await supabase
        .from('cml_points')
        .select('location_label, nominal_thickness, t_required_manual, t_min, cml_type, equipment(tag)')
        .eq('company_id', companyId)
        .order('equipment_id')

      const eqRows = (eqData || []).map((e: any) => ({
        tag: e.tag,
        type: e.type,
        area_name: e.plant_areas?.name || '',
        fluid_service: e.fluid_service || '',
        material: e.material || '',
        design_pressure: e.design_pressure,
        design_temp_max: e.design_temp_max,
        installation_date: e.installation_date,
        insulation_type: e.insulation_type || '',
        notes: e.notes || '',
      }))

      const cmlRows = (cmlData || []).map((c: any) => ({
        equipment_tag: c.equipment?.tag || '',
        location_label: c.location_label,
        nominal_thickness: c.nominal_thickness,
        t_required_manual: c.t_required_manual,
        t_min: c.t_min,
        cml_type: c.cml_type || '',
      }))

      exportEquipmentExcel(eqRows, cmlRows)
      toast.success('Export successful')
    } catch (err) {
      toast.error('Export failed')
    } finally {
      setExporting(false)
    }
  }

  const handleImport = async (file: File) => {
    setImporting(true); setImportResult(null)
    try {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) throw new Error('Not authenticated')
      const { data: appUser } = await sb
        .from('app_users')
        .select('company_id')
        .eq('auth_user_id', user.id)
        .single()
      const companyId = (appUser as { company_id: string } | null)?.company_id
      if (!companyId) throw new Error('No company ID')

      const { parseImportExcel } = await import('@/lib/excel')
      const { equipment, cmls } = await parseImportExcel(file)
      let success = 0; const errors: string[] = []

      for (const eq of equipment) {
        try {
          const { data: area } = await sb.from('plant_areas').select('id').eq('company_id', companyId).eq('name', eq.area_name).single()
          await sb.from('equipment').upsert({
            company_id: companyId,
            tag: eq.tag,
            type: eq.type,
            area_id: area?.id || null,
            fluid_service: eq.fluid_service || null,
            material: eq.material || null,
            design_pressure: eq.design_pressure ? Number(eq.design_pressure) : null,
            design_temp_max: eq.design_temp_max ? Number(eq.design_temp_max) : null,
            installation_date: eq.installation_date || null,
            insulation_type: eq.insulation_type || null,
            notes: eq.notes || null,
            is_active: true,
          }, { onConflict: 'company_id,tag' })
          success++
        } catch (e: any) { errors.push(`Eq ${eq.tag}: ${e.message}`) }
      }

      for (const cml of cmls) {
        try {
          const { data: eq } = await sb.from('equipment').select('id').eq('company_id', companyId).eq('tag', cml.equipment_tag).single()
          if (!eq) { errors.push(`CML ${cml.location_label}: no eq`); continue }
          await sb.from('cml_points').upsert({
            company_id: companyId,
            equipment_id: eq.id,
            location_label: cml.location_label,
            nominal_thickness: Number(cml.nominal_thickness),
            t_required_manual: cml.t_required_manual ? Number(cml.t_required_manual) : null,
            t_min: cml.t_min ? Number(cml.t_min) : null,
            cml_type: cml.cml_type || 'standard',
            is_active: true,
          }, { onConflict: 'company_id,equipment_id,location_label' })
          success++
        } catch (e: any) { errors.push(`CML ${cml.location_label}: ${e.message}`) }
      }
      setImportResult({ success, errors })
      errors.length === 0 ? toast.success(`Imported: ${success}`) : toast.warning(`Sukses: ${success}, Error: ${errors.length}`)
      fetchEquipment()
    } catch (err: any) { toast.error(`Error: ${err.message}`) } finally { setImporting(false) }
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
          <div className="flex items-center gap-2">
            <button onClick={handleExport} disabled={exporting} className="inline-flex items-center gap-2 px-4 py-2 border rounded-lg text-sm hover:bg-muted disabled:opacity-50">
              <Download className="w-4 h-4" />{exporting ? '...' : 'Export'}
            </button>
            <label className="inline-flex items-center gap-2 px-4 py-2 border rounded-lg text-sm hover:bg-muted cursor-pointer">
              <Upload className="w-4 h-4" />{importing ? '...' : 'Import'}
              <input type="file" accept=".xlsx,.xls" className="hidden" onChange={(e) => e.target.files?.[0] && handleImport(e.target.files[0])} />
            </label>
            <button
              onClick={() => router.push('/equipment/new')}
              className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              <Plus className="h-4 w-4" />
              Add Equipment
            </button>
          </div>
        </div>

        {importResult?.errors.length ? (
          <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-xs text-red-600">
            <p className="font-medium text-red-700 mb-2">Errors:</p>
            <ul className="list-disc pl-4 space-y-1">
              {importResult.errors.slice(0,5).map((e,i)=><li key={i}>{e}</li>)}
              {importResult.errors.length>5 && <li>...+{importResult.errors.length-5} more</li>}
            </ul>
          </div>
        ) : null}

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
