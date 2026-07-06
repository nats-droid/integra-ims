'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { createClient } from '@/lib/supabase/client'
import type { Database } from '@/types/database'
import AppLayout from '@/components/layout/app-layout'
import { cn } from '@/utils/cn'
import { toast } from 'sonner'
import { runClientSideMatch, matchTokens, tokenizeRef, type DM, type DMResponse } from '@/lib/dm-screener'
import {
  ArrowLeft,
  Edit,
  Loader2,
  CircleDot,
  GitBranch,
  ClipboardList,
  Ruler,
  Wrench,
  Box,
  Thermometer,
  Gauge,
  Calendar,
  MapPin,
  Hash,
  Scale,
  Factory,
  FileText,
  CheckCircle,
  XCircle,
  Clock,
  FileX,
  FlaskConical,
  Shield,
  AlertTriangle,
  Info,
  RefreshCw,
  TrendingDown,
  Plus,
} from 'lucide-react'

type Equipment = Database['public']['Tables']['equipment']['Row']
type PlantArea = Database['public']['Tables']['plant_areas']['Row']
type Circuit = Database['public']['Tables']['circuits']['Row']
type CMLPoint = Database['public']['Tables']['cml_points']['Row']
type ThicknessReading = Database['public']['Tables']['thickness_readings']['Row']
type InspectionEvent = Database['public']['Tables']['inspection_events']['Row']
type MaintenanceLog = {
  id: string
  company_id: string
  equipment_id: string
  related_inspection_event_id: string | null
  log_date: string
  description: string
  log_type: 'finding' | 'repair' | 'replacement' | 'other'
  severity: 'minor' | 'major' | 'critical' | null
  created_at: string
}

type RLPrediction = {
  id: string
  cml_point_id: string
  predicted_rl_years: number | null
  confidence_low: number | null
  confidence_high: number | null
  model_version: string | null
  computed_at: string
}

function timeAgo(dateStr: string): string {
  const diffMs = Date.now() - new Date(dateStr).getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return 'just now'
  if (diffMin < 60) return `${diffMin} minute${diffMin > 1 ? 's' : ''} ago`
  const diffHr = Math.floor(diffMin / 60)
  if (diffHr < 24) return `${diffHr} hour${diffHr > 1 ? 's' : ''} ago`
  const diffDay = Math.floor(diffHr / 24)
  if (diffDay < 30) return `${diffDay} day${diffDay > 1 ? 's' : ''} ago`
  return new Date(dateStr).toLocaleDateString()
}

interface CircuitWithCMLs extends Circuit {
  cml_points: (CMLPoint & { readings: ThicknessReading[] })[]
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

const COMPLIANCE_ICONS: Record<string, React.ReactNode> = {
  compliant: <CheckCircle className="h-4 w-4" />,
  'non-compliant': <FileX className="h-4 w-4" />,
  pending: <Clock className="h-4 w-4" />,
}

const INSPECTION_STATUS_COLORS: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
  submitted: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  approved: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  rejected: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
}

type Tab = 'details' | 'circuits' | 'inspections' | 'readings' | 'damage_mechanisms'

interface EquipmentDetailData {
  equipment: Equipment
  area: PlantArea | null
  circuits: CircuitWithCMLs[]
  inspections: InspectionEvent[]
  readings: ThicknessReading[]
  maintenanceLog: MaintenanceLog[]
}

export default function EquipmentDetailPage() {
  const router = useRouter()
  const params = useParams()
  const id = params?.id as string
  const supabase = createClient()
  const sb = supabase as any

  const DEMO_USER = {
    id: '3fca82af-b302-4d1e-8536-b89546ecfb15',
    company_id: 'c704d7e6-07fb-48a2-9152-564434d8653f',
    full_name: 'Dicki Wiryawan',
    role: 'super_admin',
  }

  const [data, setData] = useState<EquipmentDetailData | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<Tab>('details')
  const [dmResult, setDmResult] = useState<DMResponse | null>(null)
  const [dmLoading, setDmLoading] = useState(false)
  const [userRole, setUserRole] = useState<string>('')
  const [editingCmlId, setEditingCmlId] = useState<string | null>(null)
  const [editValue, setEditValue] = useState<string>('')
  const [savingCmlId, setSavingCmlId] = useState<string | null>(null)
  const [rlPredictions, setRlPredictions] = useState<Record<string, RLPrediction>>({})
  const [recalculating, setRecalculating] = useState(false)
  const [dmValidation, setDmValidation] = useState<any | null>(null)
  const [dmValidationLoading, setDmValidationLoading] = useState(false)
  const [dmKnowledgeBase, setDmKnowledgeBase] = useState<any[]>([])

  const canEditTRequired = userRole === 'engineer' || userRole === 'supervisor' || userRole === 'super_admin'

  const fetchData = useCallback(async () => {
    if (!id) return

    try {
      setLoading(true)

      const { data: equipmentRaw, error: eqError } = await sb
        .from('equipment')
        .select('*')
        .eq('id', id)
        .single()

      const equipment = equipmentRaw as Equipment | null

      if (eqError || !equipment) {
        console.error('Equipment fetch error:', eqError)
        toast.error('Equipment not found')
        router.push('/equipment')
        return
      }

      let area: PlantArea | null = null
      if (equipment.area_id) {
        const { data: areaRaw } = await sb
          .from('plant_areas')
          .select('*')
          .eq('id', equipment.area_id)
          .single()
        area = (areaRaw as PlantArea | null)
      }

      const { data: circuitsRaw } = await sb
        .from('circuits')
        .select('*')
        .eq('equipment_id', id)
        .order('name')

      const circuits = (circuitsRaw || []) as Circuit[]
      const circuitsWithCMLs: CircuitWithCMLs[] = []

      for (const circuit of circuits) {
        const { data: cmlPointsRaw } = await sb
          .from('cml_points')
          .select('*')
          .eq('circuit_id', circuit.id)
          .eq('is_active', true)
          .order('location_label')

        const cmlPoints = (cmlPointsRaw || []) as CMLPoint[]
        const cmlsWithReadings: (CMLPoint & { readings: ThicknessReading[] })[] = []

        for (const cml of cmlPoints) {
          const { data: readingsRaw } = await sb
            .from('thickness_readings')
            .select('*')
            .eq('cml_point_id', cml.id)
            .order('reading_date', { ascending: false })
            .limit(50)

          cmlsWithReadings.push({
            ...cml,
            readings: (readingsRaw || []) as ThicknessReading[],
          })
        }

        circuitsWithCMLs.push({
          ...circuit,
          cml_points: cmlsWithReadings,
        })
      }

      // Fetch rl_predictions for all CML points
      const allCmlIds = circuitsWithCMLs.flatMap(c => c.cml_points.map(cml => cml.id))
      if (allCmlIds.length > 0) {
        const { data: rlData } = await sb
          .from('rl_predictions')
          .select('*')
          .in('cml_point_id', allCmlIds)

        const rlMap: Record<string, RLPrediction> = {}
        for (const pred of (rlData || []) as RLPrediction[]) {
          rlMap[pred.cml_point_id] = pred
        }
        setRlPredictions(rlMap)
      } else {
        setRlPredictions({})
      }

      const { data: inspectionsRaw } = await sb
        .from('inspection_events')
        .select('*')
        .eq('equipment_id', id)
        .order('event_date', { ascending: false })

      const inspections = (inspectionsRaw || []) as InspectionEvent[]

      const { data: cmlIdsRaw } = await sb
        .from('cml_points')
        .select('id')
        .eq('equipment_id', id)

      const cmlIds = (cmlIdsRaw || []) as { id: string }[]

      let readings: ThicknessReading[] = []
      if (cmlIds.length > 0) {
        const { data: readingData } = await sb
          .from('thickness_readings')
          .select('*')
          .in(
            'cml_point_id',
            cmlIds.map((c) => c.id),
          )
          .order('reading_date', { ascending: false })
          .limit(100)

        readings = (readingData || []) as ThicknessReading[]
      }

      const { data: maintenanceLogRaw } = await sb
        .from('maintenance_log')
        .select('*')
        .eq('equipment_id', id)
        .order('created_at', { ascending: false })
        .limit(20)

      const maintenanceLog = (maintenanceLogRaw || []) as MaintenanceLog[]

      setData({
        equipment,
        area,
        circuits: circuitsWithCMLs,
        inspections,
        readings,
        maintenanceLog,
      })
    } catch (err) {
      console.error('Error loading equipment detail:', err)
      toast.error('Failed to load equipment details')
    } finally {
      setLoading(false)
    }
  }, [id, sb, router])

  // Fetch user role for RBAC
  useEffect(() => {
    setUserRole(DEMO_USER.role)
  }, [])

  // Save t_required_manual for a CML point
  const saveTRequired = useCallback(async (cmlId: string, tMin: number | null) => {
    const val = parseFloat(editValue)
    if (isNaN(val) || val <= 0) {
      toast.error('Value must be a positive number')
      return
    }
    if (tMin != null && val >= tMin) {
      // Warning only, don't block
      const proceed = confirm(`t_required (${val} mm) >= t_min (${tMin} mm). This is unusual but may be valid if corrosion allowance is very small. Continue?`)
      if (!proceed) return
    }

    setSavingCmlId(cmlId)
    try {
      const { error } = await sb
        .from('cml_points')
        .update({ t_required_manual: val })
        .eq('id', cmlId)
      if (error) throw error

      // Update local state
      setData((prev) => {
        if (!prev) return prev
        return {
          ...prev,
          circuits: prev.circuits.map((c) => ({
            ...c,
            cml_points: c.cml_points.map((cml) =>
              cml.id === cmlId ? { ...cml, t_required_manual: val } : cml
            ),
          })),
        }
      })
      setEditingCmlId(null)
      setEditValue('')
      toast.success('t_required saved')
    } catch (err) {
      console.error('Save t_required error:', err)
      toast.error('Failed to save t_required')
    } finally {
      setSavingCmlId(null)
    }
  }, [editValue, sb])

  // Recalculate RL for all CML points in this equipment
  const handleRecalculate = useCallback(async () => {
    setRecalculating(true)
    try {
      const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const res = await fetch(`${backendUrl}/api/v1/rl-confidence/recalculate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Unknown error' }))
        toast.error(`Recalculate failed: ${err.detail || res.statusText}`)
        return
      }

      const result = await res.json()
      const skippedCount = Array.isArray(result.skipped) ? result.skipped.length : result.skipped
      toast.success(
        `Recalculate complete: ${result.calculated} calculated, ${skippedCount} skipped (missing t_required)`,
        { duration: 5000 }
      )

      // Refresh data to show new predictions
      fetchData()
    } catch (err) {
      console.error('Recalculate error:', err)
      toast.error('Failed to recalculate')
    } finally {
      setRecalculating(false)
    }
  }, [supabase, fetchData])

  const fetchDmResults = useCallback(async (eq: Equipment) => {
    if (!eq.material && !eq.fluid_service) return

    try {
      setDmLoading(true)
      const { data: kb } = await sb
        .from('dm_knowledge_base')
        .select('*')

      if (kb && kb.length > 0) {
        const result = runClientSideMatch(kb, {
          material: eq.material || '',
          fluid: eq.fluid_service || '',
          tempMin: eq.design_temp_min ?? NaN,
          tempMax: eq.design_temp_max ?? NaN,
          pwht: eq.pwht ?? null,
        })
        setDmResult(result)
      }
    } catch (err) {
      console.error('DM Screener error:', err)
    } finally {
      setDmLoading(false)
    }
  }, [sb, id])

  // Fetch validation data for Damage Mechanisms tab
  const fetchDmValidation = useCallback(async (eqId: string) => {
    setDmValidationLoading(true)
    try {
      const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const res = await fetch(`${backendUrl}/api/v1/analytics/dm-validation/${eqId}/latest`, {
        headers: { 'Content-Type': 'application/json' },
      })
      if (!res.ok) throw new Error('Failed to fetch validation')
      const data = await res.json()
      setDmValidation(data)
    } catch {
      setDmValidation(null)
    } finally {
      setDmValidationLoading(false)
    }
  }, [supabase])

  // Load DM knowledge base for name lookups
  useEffect(() => {
    sb.from('dm_knowledge_base').select('dm_code, dm_name').then(({ data }: any) => {
      if (data) setDmKnowledgeBase(data)
    })
  }, [sb])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  // Run DM calculation when equipment data is loaded
  useEffect(() => {
    if (data?.equipment) {
      fetchDmResults(data.equipment)
      fetchDmValidation(data.equipment.id)
    }
  }, [data, fetchDmResults, fetchDmValidation])

  if (loading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          <span className="ml-2 text-sm text-muted-foreground">Loading equipment details...</span>
        </div>
      </AppLayout>
    )
  }

  if (!data) {
    return (
      <AppLayout>
        <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
          <Box className="h-12 w-12 mb-2" />
          <p>Equipment not found</p>
          <button
            onClick={() => router.push('/equipment')}
            className="mt-4 text-sm text-primary hover:underline"
          >
            Back to equipment list
          </button>
        </div>
      </AppLayout>
    )
  }

  const { equipment, area, circuits, inspections, readings, maintenanceLog } = data

  const isPsv = (equipment.type as string) === 'psv'

  const tabs: { key: Tab; label: string; icon: React.ReactNode; badge?: number }[] = [
    { key: 'details', label: 'Details', icon: <CircleDot className="h-4 w-4" /> },
    {
      key: 'circuits',
      label: isPsv ? 'PSV Testing History' : 'Circuits',
      icon: isPsv ? <Gauge className="h-4 w-4" /> : <GitBranch className="h-4 w-4" />,
      badge: isPsv ? maintenanceLog.length : circuits.length,
    },
    { key: 'inspections', label: 'Inspection History', icon: <ClipboardList className="h-4 w-4" />, badge: inspections.length },
    {
      key: 'readings',
      label: isPsv ? 'Site Records' : 'Thickness Readings',
      icon: isPsv ? <MapPin className="h-4 w-4" /> : <Ruler className="h-4 w-4" />,
      badge: readings.length,
    },
    { key: 'damage_mechanisms', label: 'Damage Mechanisms', icon: <FlaskConical className="h-4 w-4" /> },
  ]

  const renderDetailsTab = () => (
    <div className="space-y-6">
      {/* Summary card */}
      <div className="rounded-xl border border-border/70 p-6">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <h2 className="text-2xl font-bold">{equipment.tag}</h2>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Wrench className="h-4 w-4" />
              <span className="capitalize">{equipment.type}</span>
              {equipment.fluid_service && (
                <>
                  <span className="text-muted-foreground/50">|</span>
                  <span>{equipment.fluid_service}</span>
                </>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            {equipment.risk_category && (
              <span
                className={cn(
                  'rounded-full px-3 py-1 text-xs font-medium capitalize',
                  RISK_COLORS[equipment.risk_category],
                )}
              >
                {equipment.risk_category}
              </span>
            )}
            <span
              className={cn(
                'inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium capitalize',
                COMPLIANCE_COLORS[equipment.compliance_status],
              )}
            >
              {COMPLIANCE_ICONS[equipment.compliance_status]}
              {equipment.compliance_status === 'non-compliant'
                ? 'Non-Compliant'
                : equipment.compliance_status}
            </span>
          </div>
        </div>
      </div>

      {/* Detail fields grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <DetailCard
          icon={<MapPin className="h-4 w-4 text-muted-foreground" />}
          label="Area"
          value={area?.name || '—'}
        />
        <DetailCard
          icon={<Wrench className="h-4 w-4 text-muted-foreground" />}
          label="Type"
          value={equipment.type.charAt(0).toUpperCase() + equipment.type.slice(1)}
        />
        <DetailCard
          icon={<FlaskConicalIcon className="h-4 w-4 text-muted-foreground" />}
          label="Fluid Service"
          value={equipment.fluid_service || '—'}
        />
        <DetailCard
          icon={<Box className="h-4 w-4 text-muted-foreground" />}
          label="Material"
          value={equipment.material || '—'}
        />
        <DetailCard
          icon={<Thermometer className="h-4 w-4 text-muted-foreground" />}
          label="Design Temp Range"
          value={
            equipment.design_temp_min != null || equipment.design_temp_max != null
              ? `${equipment.design_temp_min ?? '—'}°C / ${equipment.design_temp_max ?? '—'}°C`
              : '—'
          }
        />
        <DetailCard
          icon={<Gauge className="h-4 w-4 text-muted-foreground" />}
          label="Design Pressure"
          value={equipment.design_pressure != null ? `${equipment.design_pressure} bar` : '—'}
        />
        <DetailCard
          icon={<Hash className="h-4 w-4 text-muted-foreground" />}
          label="Size / Dimension"
          value={equipment.size_or_dimension || '—'}
        />
        <DetailCard
          icon={<Scale className="h-4 w-4 text-muted-foreground" />}
          label="Insulation"
          value={equipment.insulation_type || '—'}
        />
        <DetailCard
          icon={<Factory className="h-4 w-4 text-muted-foreground" />}
          label="Manufacturer"
          value={equipment.manufacturer || '—'}
        />
        <DetailCard
          icon={<Hash className="h-4 w-4 text-muted-foreground" />}
          label="Serial Number"
          value={equipment.serial_number || '—'}
        />
        <DetailCard
          icon={<Calendar className="h-4 w-4 text-muted-foreground" />}
          label="Installation Date"
          value={
            equipment.installation_date
              ? new Date(equipment.installation_date).toLocaleDateString()
              : '—'
          }
        />
        <DetailCard
          icon={<FileText className="h-4 w-4 text-muted-foreground" />}
          label="PWHT"
          value={equipment.pwht ? 'Yes' : 'No'}
        />
      </div>

      {equipment.notes && (
        <div className="rounded-xl border border-border/70 p-6">
          <h3 className="text-sm font-medium mb-2">Notes</h3>
          <p className="text-sm text-muted-foreground whitespace-pre-wrap">{equipment.notes}</p>
        </div>
      )}

      <div className="text-xs text-muted-foreground space-y-1">
        <p>Created: {new Date(equipment.created_at).toLocaleString()}</p>
        <p>Updated: {new Date(equipment.updated_at).toLocaleString()}</p>
      </div>
    </div>
  )

  const renderCircuitsTab = () => (
    <div className="space-y-6">
      {/* Recalculate button */}
      {canEditTRequired && circuits.some(c => c.cml_points.length > 0) && (
        <div className="flex items-center justify-between">
          <div />
          <button
            onClick={handleRecalculate}
            disabled={recalculating}
            className="inline-flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-medium hover:bg-accent transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${recalculating ? 'animate-spin' : ''}`} />
            {recalculating ? 'Recalculating...' : 'Recalculate Remaining Life'}
          </button>
        </div>
      )}

      {circuits.length === 0 ? (
        <div className="rounded-xl border border-border/70 p-8 text-center text-muted-foreground">
          <GitBranch className="h-8 w-8 mx-auto mb-2" />
          <p className="text-sm">No circuits defined for this equipment</p>
        </div>
      ) : (
        circuits.map((circuit) => (
          <div key={circuit.id} className="rounded-xl border border-border/70 overflow-hidden">
            <div className="px-6 py-4 border-b border-border">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <GitBranch className="h-4 w-4 text-muted-foreground" />
                  <h3 className="font-medium">{circuit.name}</h3>
                </div>
                <span className="text-xs text-muted-foreground">
                  {circuit.cml_points.length} CML point{circuit.cml_points.length !== 1 ? 's' : ''}
                </span>
              </div>
              {circuit.description && (
                <p className="text-xs text-muted-foreground mt-1 ml-6">
                  {circuit.description}
                </p>
              )}
            </div>

            {circuit.cml_points.length > 0 && (
              <div className="divide-y divide-border">
                {circuit.cml_points.map((cml) => {
                  const isEditing = editingCmlId === cml.id
                  const tReq = (cml as any).t_required_manual as number | null
                  const tMinVal = cml.t_min as number | null
                  const showWarning = isEditing && editValue && tMinVal != null && parseFloat(editValue) >= tMinVal
                  const pred = rlPredictions[cml.id]
                  const isLowConfidence = pred != null && (pred.confidence_low == null || pred.confidence_high == null)

                  return (
                    <div key={cml.id} className="px-6 py-3.5 hover:bg-muted/20">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <CircleDot className="h-3.5 w-3.5 text-muted-foreground" />
                          <span className="text-sm font-medium">{cml.location_label}</span>
                          <span className="text-xs text-muted-foreground capitalize">
                            ({cml.cml_type})
                          </span>
                        </div>
                        <div className="flex items-center gap-3 text-xs text-muted-foreground">
                          <span>
                            t_nom: {cml.nominal_thickness} mm
                            {cml.t_min != null && ` | t_min: ${cml.t_min} mm`}
                            {cml.readings.length > 0 && ` | Latest: ${cml.readings[0].reading_mm} mm`}
                          </span>
                        </div>
                      </div>
                      {/* Row 2: t_required_manual */}
                      <div className="mt-1.5 ml-6 flex items-center gap-2 text-xs">
                        <span className="text-muted-foreground">t_required:</span>
                        {isEditing ? (
                          <div className="flex items-center gap-1.5">
                            <input
                              type="number"
                              step="0.01"
                              min="0"
                              value={editValue}
                              onChange={(e) => setEditValue(e.target.value)}
                              className="w-20 rounded border border-input bg-background px-1.5 py-0.5 text-xs"
                              autoFocus
                              disabled={savingCmlId === cml.id}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') saveTRequired(cml.id, tMinVal)
                                if (e.key === 'Escape') { setEditingCmlId(null); setEditValue('') }
                              }}
                            />
                            <span className="text-muted-foreground">mm</span>
                            <button
                              onClick={() => saveTRequired(cml.id, tMinVal)}
                              disabled={savingCmlId === cml.id}
                              className="rounded bg-primary px-1.5 py-0.5 text-primary-foreground hover:opacity-90 disabled:opacity-50"
                            >
                              {savingCmlId === cml.id ? '...' : 'Save'}
                            </button>
                            <button
                              onClick={() => { setEditingCmlId(null); setEditValue('') }}
                              disabled={savingCmlId === cml.id}
                              className="rounded border border-border px-1.5 py-0.5 text-muted-foreground hover:bg-muted"
                            >
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <div className="flex items-center gap-1.5">
                            {tReq != null ? (
                              <span className="font-medium text-foreground">{tReq} mm</span>
                            ) : (
                              <span className="text-muted-foreground/60">— not set</span>
                            )}
                            {canEditTRequired && (
                              <button
                                onClick={() => {
                                  setEditingCmlId(cml.id)
                                  setEditValue(tReq != null ? String(tReq) : '')
                                }}
                                className="rounded border border-border px-1.5 py-0.5 text-muted-foreground hover:bg-muted"
                              >
                                {tReq != null ? 'Edit' : 'Set'}
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                      {/* Validation warning */}
                      {showWarning && (
                        <div className="ml-6 mt-1 text-xs text-yellow-600 dark:text-yellow-400">
                          Warning: t_required should typically be less than t_min ({tMinVal} mm)
                        </div>
                      )}
                      {/* Row 3: Remaining Life prediction */}
                      {tReq != null ? (
                        pred ? (
                          <div className="mt-2 ml-6 space-y-1">
                            <div className="flex items-center gap-2 text-xs">
                              <TrendingDown className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
                              <span className="text-muted-foreground">Remaining Life:</span>
                              <span className="font-semibold text-foreground">
                                {pred.predicted_rl_years != null ? `${pred.predicted_rl_years.toFixed(2)} years` : '—'}
                              </span>
                              {isLowConfidence && (
                                <span className="inline-flex items-center gap-1 rounded-full bg-yellow-100 dark:bg-yellow-900/30 px-2 py-0.5 text-[10px] font-medium text-yellow-800 dark:text-yellow-400">
                                  <AlertTriangle className="h-2.5 w-2.5" />
                                  Low Confidence
                                </span>
                              )}
                            </div>
                            {!isLowConfidence && pred.confidence_low != null && pred.confidence_high != null && (
                              <div className="flex items-center gap-2 text-xs text-muted-foreground ml-6">
                                <span>95% CI: {pred.confidence_low.toFixed(2)} — {pred.confidence_high.toFixed(2)} years</span>
                              </div>
                            )}
                            <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground/50 ml-6">
                              <Clock className="h-2.5 w-2.5" />
                              <span>Calculated {timeAgo(pred.computed_at)}</span>
                            </div>
                          </div>
                        ) : (
                          <div className="mt-1.5 ml-6 flex items-center gap-1.5 text-xs text-muted-foreground/60">
                            <TrendingDown className="h-3 w-3" />
                            <span>— Not calculated yet</span>
                          </div>
                        )
                      ) : (
                        <div className="mt-1.5 ml-6 flex items-center gap-1.5 text-xs text-muted-foreground/40">
                          <TrendingDown className="h-3 w-3" />
                          <span>— Set t_required to enable RL calculation</span>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        ))
      )}
    </div>
  )

  const renderInspectionsTab = () => (
    <div className="space-y-4">
      {/* Header row with title and New Inspection button */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-muted-foreground">
          {inspections.length} inspection{inspections.length !== 1 ? 's' : ''} recorded
        </h3>
        {userRole === 'inspector' && (
          <button
            onClick={() => router.push(`/inspections/new?equipment_id=${id}`)}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            <Plus className="h-4 w-4" />
            New Inspection
          </button>
        )}
      </div>
      {inspections.length === 0 ? (
        <div className="rounded-xl border border-border/70 p-8 text-center text-muted-foreground">
          <ClipboardList className="h-8 w-8 mx-auto mb-2" />
          <p className="text-sm">No inspection history</p>
        </div>
      ) : (
        <div className="rounded-xl border border-border overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="px-6 py-4 text-left font-medium text-muted-foreground text-xs uppercase tracking-wider">Date</th>
                <th className="px-6 py-4 text-left font-medium text-muted-foreground text-xs uppercase tracking-wider">Type</th>
                <th className="px-6 py-4 text-left font-medium text-muted-foreground text-xs uppercase tracking-wider">Status</th>
                <th className="px-6 py-4 text-left font-medium text-muted-foreground text-xs uppercase tracking-wider">Notes</th>
              </tr>
            </thead>
            <tbody>
              {inspections.map((insp) => (
                <tr key={insp.id} className="border-b border-border last:border-0">
                  <td className="px-6 py-3.5">
                    {new Date(insp.event_date).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-3.5 capitalize">{insp.inspection_type}</td>
                  <td className="px-6 py-3.5">
                    <span
                      className={cn(
                        'inline-block rounded-full px-2.5 py-0.5 text-xs font-medium capitalize',
                        INSPECTION_STATUS_COLORS[insp.status],
                      )}
                    >
                      {insp.status}
                    </span>
                  </td>
                  <td className="px-6 py-3.5 text-muted-foreground max-w-xs truncate">
                    {insp.notes || '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )

  const renderPsvTab = () => (
    <div className="space-y-4">
      {maintenanceLog.length === 0 ? (
        <div className="rounded-xl border border-border/70 p-8 text-center text-muted-foreground">
          <Gauge className="h-8 w-8 mx-auto mb-2" />
          <p className="text-sm">
            PSV testing records will appear here. For MVP, manual entry via maintenance log is used.
          </p>
        </div>
      ) : (
        <div className="rounded-xl border border-border overflow-hidden">
          <div className="px-6 py-4 border-b border-border">
            <h3 className="font-medium">Set Pressure Test History</h3>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="px-6 py-4 text-left font-medium text-muted-foreground text-xs uppercase tracking-wider">Date</th>
                <th className="px-6 py-4 text-left font-medium text-muted-foreground text-xs uppercase tracking-wider">Description</th>
                <th className="px-6 py-4 text-left font-medium text-muted-foreground text-xs uppercase tracking-wider">Type</th>
                <th className="px-6 py-4 text-left font-medium text-muted-foreground text-xs uppercase tracking-wider">Status</th>
              </tr>
            </thead>
            <tbody>
              {maintenanceLog.map((log) => (
                <tr key={log.id} className="border-b border-border last:border-0">
                  <td className="px-6 py-3.5">
                    {new Date(log.log_date).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-3.5 max-w-xs truncate">{log.description}</td>
                  <td className="px-6 py-3.5 capitalize">{log.log_type}</td>
                  <td className="px-6 py-3.5">
                    <span
                      className={cn(
                        'inline-block rounded-full px-2.5 py-0.5 text-xs font-medium capitalize',
                        log.severity === 'critical'
                          ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                          : log.severity === 'major'
                            ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400'
                            : log.severity === 'minor'
                              ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                              : 'bg-muted text-muted-foreground',
                      )}
                    >
                      {log.severity || '—'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )

  const renderReadingsTab = () => (
    <div className="space-y-4">
      {readings.length === 0 ? (
        <div className="rounded-xl border border-border/70 p-8 text-center text-muted-foreground">
          <Ruler className="h-8 w-8 mx-auto mb-2" />
          <p className="text-sm">No thickness readings recorded</p>
        </div>
      ) : (
        <div className="rounded-xl border border-border overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="px-6 py-4 text-left font-medium text-muted-foreground text-xs uppercase tracking-wider">Date</th>
                <th className="px-6 py-4 text-left font-medium text-muted-foreground text-xs uppercase tracking-wider">Reading (mm)</th>
                <th className="px-6 py-4 text-left font-medium text-muted-foreground text-xs uppercase tracking-wider">Representative</th>
                <th className="px-6 py-4 text-left font-medium text-muted-foreground text-xs uppercase tracking-wider">Notes</th>
              </tr>
            </thead>
            <tbody>
              {readings.map((reading) => (
                <tr key={reading.id} className="border-b border-border last:border-0">
                  <td className="px-6 py-3.5">
                    {new Date(reading.reading_date).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-3.5 font-medium tabular-nums">{reading.reading_mm}</td>
                  <td className="px-6 py-3.5">
                    <span
                      className={cn(
                        'rounded-full px-2 py-0.5 text-xs font-medium',
                        reading.is_representative
                          ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                          : 'bg-muted text-muted-foreground',
                      )}
                    >
                      {reading.is_representative ? 'Yes' : 'No'}
                    </span>
                  </td>
                  <td className="px-6 py-3.5 text-muted-foreground max-w-xs truncate">
                    {reading.notes || '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )

  const renderDamageMechanismsTab = () => {
    const inputMissing = !equipment.material && !equipment.fluid_service
    
    if (inputMissing) {
      return (
        <div className="rounded-xl border border-border/70 p-8 text-center text-muted-foreground">
          <FlaskConical className="h-8 w-8 mx-auto mb-2" />
          <p className="text-sm">Complete material and fluid service data</p>
          <p className="text-xs mt-1">Set equipment material and fluid service to enable DM screening</p>
        </div>
      )
    }

    if (dmLoading) {
      return (
        <div className="flex items-center justify-center py-16 text-muted-foreground">
          <Loader2 className="h-5 w-5 animate-spin" />
          <span className="ml-2 text-sm">Running DM screening...</span>
        </div>
      )
    }

    if (!dmResult) {
      return (
        <div className="rounded-xl border border-border/70 p-8 text-center text-muted-foreground">
          <FlaskConical className="h-8 w-8 mx-auto mb-2" />
          <p className="text-sm">Unable to run DM screening</p>
          <p className="text-xs mt-1">Check that dm_knowledge_base is populated</p>
        </div>
      )
    }

    const allDMs: (DM & { match_status: string })[] = [
      ...dmResult.active.map(d => ({ ...d, match_status: 'Active' as const })),
      ...dmResult.possible.map(d => ({ ...d, match_status: 'Possible' as const })),
      ...dmResult.related.map(d => ({ ...d, match_status: 'Related' as const })),
    ]

    const STATUS_COLORS: Record<string, string> = {
      Active: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
      Possible: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400',
      Related: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
    }

    const CATEGORY_COLORS: Record<string, string> = {
      Corrosion: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
      Cracking: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400',
      Metallurgical: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400',
      Mechanical: 'bg-teal-100 text-teal-800 dark:bg-teal-900/30 dark:text-teal-400',
    }

    return (
      <div className="space-y-6">
        {/* Summary cards */}
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-800/30 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-red-600 dark:text-red-400">
              {dmResult.active.length}
            </div>
            <div className="text-xs text-red-700 dark:text-red-300 mt-0.5">Active DMs</div>
            <div className="text-[10px] text-red-500/70">Strong evidence</div>
          </div>
          <div className="bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800/30 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-amber-600 dark:text-amber-400">
              {dmResult.possible.length}
            </div>
            <div className="text-xs text-amber-700 dark:text-amber-300 mt-0.5">Possible DMs</div>
            <div className="text-[10px] text-amber-500/70">Moderate likelihood</div>
          </div>
          <div className="bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-800/30 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
              {dmResult.related.length}
            </div>
            <div className="text-xs text-blue-700 dark:text-blue-300 mt-0.5">Related DMs</div>
            <div className="text-[10px] text-blue-500/70">Co-occurring</div>
          </div>
        </div>

        {/* Screening info */}
        <div className="bg-card border border-border rounded-xl p-4 flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm">
            <FlaskConical className="h-4 w-4 text-muted-foreground" />
            <span>{dmResult.total_matched} of {dmResult.total_screened} API 571 DMs matched</span>
          </div>
          <span className="text-xs text-muted-foreground">
            Based on: {equipment.material} · {equipment.fluid_service}
            {equipment.design_temp_min != null && ` · ${equipment.design_temp_min}–${equipment.design_temp_max}°C`}
            {equipment.pwht != null && ` · PWHT: ${equipment.pwht ? 'Yes' : 'No'}`}
          </span>
        </div>

        {/* DM Detail Table */}
        <div className="rounded-xl border border-border overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="px-5 py-3.5 text-left font-medium text-muted-foreground text-xs uppercase tracking-wider">DM Code</th>
                <th className="px-5 py-3.5 text-left font-medium text-muted-foreground text-xs uppercase tracking-wider">Name</th>
                <th className="px-5 py-3.5 text-left font-medium text-muted-foreground text-xs uppercase tracking-wider">Category</th>
                <th className="px-5 py-3.5 text-left font-medium text-muted-foreground text-xs uppercase tracking-wider">Status</th>
                <th className="px-5 py-3.5 text-left font-medium text-muted-foreground text-xs uppercase tracking-wider">Recommended NDE</th>
              </tr>
            </thead>
            <tbody>
              {allDMs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-5 py-8 text-center text-muted-foreground text-sm">
                    No credible DMs matched for this equipment configuration.
                  </td>
                </tr>
              ) : (
                allDMs.map((dm, idx) => (
                  <tr key={`${dm.dm_code}-${idx}`} className="border-b border-border last:border-0">
                    <td className="px-5 py-3.5 font-mono text-xs text-muted-foreground">{dm.dm_code}</td>
                    <td className="px-5 py-3.5 font-medium">
                      <div className="flex items-center gap-2">
                        {dm.dm_name}
                        {dm.pwht_concern && (
                          <span className="text-[10px] text-amber-600 dark:text-amber-400 whitespace-nowrap">
                            ⚠ No PWHT
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-5 py-3.5">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${CATEGORY_COLORS[dm.category] || 'bg-muted text-muted-foreground'}`}>
                        {dm.category}
                      </span>
                    </td>
                    <td className="px-5 py-3.5">
                      <span className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${STATUS_COLORS[dm.match_status]}`}>
                        {dm.match_status}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-xs text-muted-foreground">
                      {dm.nde?.length ? dm.nde.join(', ') : '—'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* NDE recommendation from top active */}
        {dmResult.active.length > 0 && (
          <div className="bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-800/30 rounded-xl p-4">
            <div className="flex items-start gap-3">
              <Info className="h-5 w-5 text-blue-600 dark:text-blue-400 shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-blue-800 dark:text-blue-300">
                  Recommended Inspection Method
                </p>
                <p className="text-xs text-blue-600 dark:text-blue-400 mt-1">
                  {dmResult.nde || 'UT Thickness (Baseline)'}
                </p>
                <p className="text-[10px] text-blue-500/70 mt-1">
                  Based on top active DM. Use as reference — final method determined by Engineer.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* ── Field Validation History ── */}
        {canEditTRequired && (
          <>
            {/* Divider */}
            <div className="border-t border-border pt-6 mt-2">
              <h3 className="text-sm font-medium flex items-center gap-2 mb-4">
                <CheckCircle className="h-4 w-4 text-primary" />
                Field Validation History
              </h3>

              {dmValidationLoading ? (
                <div className="animate-pulse space-y-3">
                  <div className="h-10 bg-muted rounded-lg" />
                  <div className="h-20 bg-muted rounded-lg" />
                </div>
              ) : !dmValidation ? (
                /* State 1 — no data */
                <div className="rounded-lg border border-dashed border-border p-6 text-center text-muted-foreground">
                  <CheckCircle className="h-6 w-6 mx-auto mb-2 opacity-40" />
                  <p className="text-sm">No validation data available.</p>
                  <p className="text-xs mt-1">
                    Run &apos;Validate All&apos; from the DM Screener page to compute field validation scores.
                  </p>
                </div>
              ) : (dmValidation.predicted_dm_codes || []).length === 0 ? (
                /* State 2 — no Active DMs */
                <div className="rounded-lg border border-dashed border-border p-6 text-center text-muted-foreground">
                  <Info className="h-6 w-6 mx-auto mb-2 opacity-40" />
                  <p className="text-sm">No Active DMs predicted for this equipment — field validation not applicable.</p>
                </div>
              ) : (
                /* State 3 — has validation data */
                <>
                  {/* Summary bar */}
                  <div className="flex items-center justify-between bg-card border border-border rounded-lg p-4 mb-4">
                    <div className="flex items-center gap-3">
                      {(() => {
                        const score = dmValidation.match_score * 100
                        let badgeColor = 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
                        if (score >= 70) badgeColor = 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
                        else if (score >= 40) badgeColor = 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400'
                        return (
                          <span className={`text-sm font-bold px-2.5 py-1 rounded-full ${badgeColor}`}>
                            {score.toFixed(0)}% Field Match
                          </span>
                        )
                      })()}
                      <span className="text-xs text-muted-foreground">
                        Last validated: {new Date(dmValidation.computed_at).toLocaleDateString('en-GB', {
                          day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit'
                        })}
                      </span>
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {(dmValidation.actual_finding_dm_codes || []).length} of {(dmValidation.predicted_dm_codes || []).length} Active DMs found in inspection notes
                    </span>
                  </div>

                  {/* Breakdown table */}
                  <div className="rounded-lg border border-border overflow-hidden">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-border bg-muted/50">
                          <th className="px-4 py-2.5 text-left font-medium text-muted-foreground text-xs uppercase tracking-wider w-10">Status</th>
                          <th className="px-4 py-2.5 text-left font-medium text-muted-foreground text-xs uppercase tracking-wider">DM Code</th>
                          <th className="px-4 py-2.5 text-left font-medium text-muted-foreground text-xs uppercase tracking-wider">Name</th>
                          <th className="px-4 py-2.5 text-left font-medium text-muted-foreground text-xs uppercase tracking-wider">Keyword Searched</th>
                        </tr>
                      </thead>
                      <tbody>
                        {dmValidation.predicted_dm_codes.map((dmCode: string, idx: number) => {
                          const found = (dmValidation.actual_finding_dm_codes || []).includes(dmCode)
                          const kbEntry = dmKnowledgeBase.find((k: any) => k.dm_code === dmCode)
                          const dmName = kbEntry?.dm_name || dmCode
                          // Extract keyword via same logic as backend
                          const parenMatch = dmName.match(/\(([^)]+)\)/)
                          const keyword = parenMatch && parenMatch[1].length <= 15 && !['Including','Excluding','Also'].some(w => parenMatch[1].startsWith(w))
                            ? parenMatch[1]
                            : (dmName.split(/[\s,-]+/).filter((w: string) => w.length > 1 && !['Corrosion','High','Low','Temperature','Stress','Damage','Attack','Cracking','Induced','And','Of','The','In','At','With','For','Under','Including','Assisted','Related','Enhanced'].includes(w))[0] || dmName.slice(0, 20))
                          return (
                            <tr key={dmCode} className="border-b border-border last:border-0">
                              <td className="px-4 py-2.5">
                                {found ? (
                                  <span className="inline-flex items-center gap-1 text-green-600 dark:text-green-400 text-xs">
                                    <CheckCircle className="h-3.5 w-3.5" /> Found in field notes
                                  </span>
                                ) : (
                                  <span className="inline-flex items-center gap-1 text-slate-400 dark:text-slate-500 text-xs">
                                    <XCircle className="h-3.5 w-3.5" /> Not yet observed
                                  </span>
                                )}
                              </td>
                              <td className="px-4 py-2.5 font-mono text-xs text-muted-foreground">{dmCode}</td>
                              <td className="px-4 py-2.5 text-sm">{dmName}</td>
                              <td className="px-4 py-2.5 text-xs text-muted-foreground font-mono">{keyword}</td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                </>
              )}
            </div>
          </>
        )}
      </div>
    )
  }

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Back button */}
        <button
          onClick={() => router.push('/equipment')}
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to equipment
        </button>

        {/* Action bar */}
        <div className="flex items-center justify-between">
          <div />
          <button
            onClick={() => router.push(`/equipment/${id}/edit`)}
            className="inline-flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-medium hover:bg-accent transition-colors"
          >
            <Edit className="h-4 w-4" />
            Edit Equipment
          </button>
        </div>

        {/* Tabs */}
        <div className="border-b border-border">
          <div className="flex gap-1">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={cn(
                  'flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors',
                  activeTab === tab.key
                    ? 'border-primary text-foreground'
                    : 'border-transparent text-muted-foreground hover:text-foreground',
                )}
              >
                {tab.icon}
                <span>{tab.label}</span>
                {tab.badge != null && tab.badge > 0 && (
                  <span className="inline-flex items-center justify-center rounded-full bg-muted px-2 py-0.5 text-xs tabular-nums">
                    {tab.badge}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Tab content */}
        {activeTab === 'details' && renderDetailsTab()}
        {activeTab === 'circuits' && (isPsv ? renderPsvTab() : renderCircuitsTab())}
        {activeTab === 'inspections' && renderInspectionsTab()}
        {activeTab === 'readings' && renderReadingsTab()}
        {activeTab === 'damage_mechanisms' && renderDamageMechanismsTab()}
      </div>
    </AppLayout>
  )
}

function DetailCard({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode
  label: string
  value: string
}) {
  return (
    <div className="rounded-xl border border-border/70 p-6">
      <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
        {icon}
        <span>{label}</span>
      </div>
      <p className="text-sm font-medium">{value}</p>
    </div>
  )
}

function FlaskConicalIcon({ className }: { className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M14 2v6a2 2 0 0 0 .245.96l5.51 10.08A2 2 0 0 1 18 22H6a2 2 0 0 1-1.755-2.96l5.51-10.08A2 2 0 0 0 10 8V2" />
      <path d="M6.453 15h11.094" />
      <path d="M8.5 2h7" />
    </svg>
  )
}