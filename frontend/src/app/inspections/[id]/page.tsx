'use client'

import { useEffect, useState, useCallback, use } from 'react'
import { useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase/client'
import AppLayout from '@/components/layout/app-layout'
import { cn } from '@/utils/cn'
import { toast } from 'sonner'
import {
  ChevronRight,
  FileText,
  CheckCircle,
  XCircle,
  Loader2,
  Download,
  Camera,
} from 'lucide-react'
import { getEventPhotos } from '@/utils/photos'
import jsPDF from 'jspdf'
import html2canvas from 'html2canvas'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface InspectionDetail {
  id: string
  equipment_id: string
  inspector_id: string | null
  event_date: string
  inspection_type: string
  status: 'draft' | 'submitted' | 'approved' | 'rejected'
  notes: string | null
  weather: string | null
  company_id: string
}

interface EquipmentInfo {
  id: string
  tag: string
  type: string
  area_id: string | null
  area_name: string | null
}

interface InspectorInfo {
  id: string
  full_name: string
}

interface ChecklistAnswerRow {
  id: string
  item_code: string
  answer_rating: number | null
  answer_boolean: boolean | null
  answer_text: string | null
  notes: string | null
}

interface ChecklistTemplateRow {
  item_code: string
  item_description: string
  section: string
  item_type: string
  display_order: number
}

interface ChecklistDisplayItem {
  item_code: string
  description: string
  rating: number | null
  notes: string
}

interface ChecklistSection {
  section: string
  items: ChecklistDisplayItem[]
}

interface ThicknessReadingRow {
  id: string
  cml_point_id: string
  reading_mm: number
  reading_date: string
  is_representative: boolean
  notes: string | null
}

interface CMLPointRow {
  id: string
  location_label: string
  nominal_thickness: number
}

interface ThicknessDisplayRow {
  cml_location: string
  reading_mm: number
  nominal_mm: number
  previous_mm: number | null
  reading_date: string
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const STATUS_CONFIG: Record<string, { label: string; className: string }> = {
  draft: { label: 'Draft', className: 'bg-gray-100 text-gray-700' },
  submitted: { label: 'Submitted', className: 'bg-blue-100 text-blue-700' },
  approved: { label: 'Approved', className: 'bg-green-100 text-green-700' },
  rejected: { label: 'Rejected', className: 'bg-red-100 text-red-700' },
}

const RATING_LABELS: Record<number, { text: string; className: string }> = {
  1: { text: 'Poor', className: 'bg-red-100 text-red-700' },
  2: { text: 'Fair', className: 'bg-red-100 text-red-700' },
  3: { text: 'Good', className: 'bg-amber-100 text-amber-700' },
  4: { text: 'Very Good', className: 'bg-green-100 text-green-700' },
  5: { text: 'Excellent', className: 'bg-green-100 text-green-700' },
}

const SECTION_LABELS: Record<string, string> = {
  B: 'External Visual Inspection',
  C: 'Internal Visual Inspection',
  D: 'Thickness Measurements',
  E: 'NDT Examination',
  F: 'Weld Inspection',
  G: 'Corrosion Assessment',
  H: 'Support & Hangers',
  I: 'Insulation & Coating',
  J: 'Safety Devices',
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(dateStr: string): string {
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

function formatDateISO(dateStr: string): string {
  return new Date(dateStr).toISOString().slice(0, 10)
}

// ---------------------------------------------------------------------------
// Page Component
// ---------------------------------------------------------------------------

export default function InspectionDetailPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = use(params)
  const router = useRouter()
  const supabase = createClient()
  const sb = supabase as any

  const [loading, setLoading] = useState(true)
  const [inspection, setInspection] = useState<InspectionDetail | null>(null)
  const [equipment, setEquipment] = useState<EquipmentInfo | null>(null)
  const [inspector, setInspector] = useState<InspectorInfo | null>(null)
  const [checklistSections, setChecklistSections] = useState<
    ChecklistSection[]
  >([])
  const [thicknessRows, setThicknessRows] = useState<ThicknessDisplayRow[]>([])
  const [userRole, setUserRole] = useState<string>('')
  const [pdfGenerating, setPdfGenerating] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)
  const [photos, setPhotos] = useState<any[]>([])
  const [lightbox, setLightbox] = useState<string | null>(null)
  const [pdfPhotos, setPdfPhotos] = useState<{base64: string; caption: string}[]>([])

  // =========================================================================
  // Fetch all data
  // =========================================================================

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)

      // 1. Get current user role
      const {
        data: { user },
      } = await supabase.auth.getUser()
      if (!user) {
        router.push('/auth/login')
        return
      }

      const { data: appUser } = await sb
        .from('app_users')
        .select('id, role, company_id')
        .eq('auth_user_id', user.id)
        .single()

      if (appUser) setUserRole((appUser as { role: string }).role)

      // 2. Fetch inspection event
      const { data: eventData, error: eventErr } = await sb
        .from('inspection_events')
        .select('*')
        .eq('id', id)
        .single()

      if (eventErr || !eventData) {
        toast.error('Inspection not found')
        router.push('/inspections')
        return
      }

      const ev = eventData as InspectionDetail
      setInspection(ev)

      // 3. Fetch equipment
      const { data: eqData } = await sb
        .from('equipment')
        .select('id, tag, type, area_id, plant_areas(name)')
        .eq('id', ev.equipment_id)
        .single()

      if (eqData) {
        const eq = eqData as any
        setEquipment({
          id: eq.id,
          tag: eq.tag,
          type: eq.type,
          area_id: eq.area_id,
          area_name: eq.plant_areas?.name ?? null,
        })
      }

      // 4. Fetch inspector
      if (ev.inspector_id) {
        const { data: inspData } = await sb
          .from('app_users')
          .select('id, full_name')
          .eq('id', ev.inspector_id)
          .single()

        if (inspData) setInspector(inspData as InspectorInfo)
      }

      // 5. Fetch checklist answers + templates
      const { data: answersData } = await sb
        .from('checklist_answers')
        .select('id, item_code, answer_rating, answer_boolean, answer_text, notes')
        .eq('inspection_event_id', id)

      const answers = (answersData || []) as ChecklistAnswerRow[]

      // Fetch templates for this equipment type
      if (eqData) {
        const eqType = (eqData as any).type
        const { data: templatesData } = await sb
          .from('checklist_templates')
          .select('item_code, item_description, section, item_type, display_order')
          .eq('equipment_type', eqType)
          .eq('is_active', true)
          .order('display_order')

        const templates = (templatesData || []) as ChecklistTemplateRow[]

        // Build answer map
        const answerMap = new Map<string, ChecklistAnswerRow>()
        for (const a of answers) {
          answerMap.set(a.item_code, a)
        }

        // Group by section
        const sectionMap = new Map<string, ChecklistDisplayItem[]>()
        for (const t of templates) {
          const ans = answerMap.get(t.item_code)
          const item: ChecklistDisplayItem = {
            item_code: t.item_code,
            description: t.item_description,
            rating: ans?.answer_rating ?? null,
            notes: ans?.notes ?? '',
          }
          if (!sectionMap.has(t.section)) {
            sectionMap.set(t.section, [])
          }
          sectionMap.get(t.section)!.push(item)
        }

        const sections: ChecklistSection[] = []
        for (const [section, items] of sectionMap) {
          sections.push({ section, items })
        }
        setChecklistSections(sections)
      }

      // 6. Fetch thickness readings + CML points
      const { data: readingsData } = await sb
        .from('thickness_readings')
        .select('id, cml_point_id, reading_mm, reading_date, is_representative, notes')
        .eq('inspection_event_id', id)
        .order('reading_date', { ascending: false })

      const readings = (readingsData || []) as ThicknessReadingRow[]

      if (readings.length > 0) {
        const cmlIds = [...new Set(readings.map((r) => r.cml_point_id))]
        const { data: cmlData } = await sb
          .from('cml_points')
          .select('id, location_label, nominal_thickness')
          .in('id', cmlIds)

        const cmlMap = new Map<string, CMLPointRow>()
        for (const c of (cmlData || []) as CMLPointRow[]) {
          cmlMap.set(c.id, c)
        }

        // Get previous readings for each CML point
        const prevMap = new Map<string, number | null>()
        for (const cmlId of cmlIds) {
          const currentReading = readings.find((r) => r.cml_point_id === cmlId)
          if (currentReading) {
            const { data: prevData } = await sb
              .from('thickness_readings')
              .select('reading_mm')
              .eq('cml_point_id', cmlId)
              .lt('reading_date', currentReading.reading_date)
              .order('reading_date', { ascending: false })
              .limit(1)

            prevMap.set(
              cmlId,
              prevData && prevData.length > 0
                ? (prevData[0] as { reading_mm: number }).reading_mm
                : null,
            )
          }
        }

        const displayRows: ThicknessDisplayRow[] = readings.map((r) => {
          const cml = cmlMap.get(r.cml_point_id)
          return {
            cml_location: cml?.location_label ?? 'Unknown',
            reading_mm: r.reading_mm,
            nominal_mm: cml?.nominal_thickness ?? 0,
            previous_mm: prevMap.get(r.cml_point_id) ?? null,
            reading_date: r.reading_date,
          }
        })

        setThicknessRows(displayRows)
      }

      // Fetch photos
      const photoResults = await getEventPhotos(id)
      setPhotos(photoResults)
    } catch (err) {
      console.error('Load inspection detail error:', err)
      toast.error('Failed to load inspection details')
    } finally {
      setLoading(false)
    }
  }, [id, sb, supabase, router])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  // =========================================================================
  // Approve / Reject
  // =========================================================================

  const handleStatusChange = async (newStatus: 'approved' | 'rejected') => {
    if (!inspection) return
    setActionLoading(true)
    try {
      const { error } = await sb
        .from('inspection_events')
        .update({ status: newStatus })
        .eq('id', inspection.id)

      if (error) {
        toast.error(`Failed to ${newStatus} inspection`)
        return
      }

      setInspection({ ...inspection, status: newStatus })
      toast.success(`Inspection ${newStatus}`)
    } catch (err) {
      console.error('Status change error:', err)
      toast.error('Unexpected error')
    } finally {
      setActionLoading(false)
    }
  }

  // =========================================================================
  // Generate PDF
  // =========================================================================

  const toBase64 = async (url: string): Promise<string> => {
    try {
      const res = await fetch(url)
      const blob = await res.blob()
      return new Promise((resolve, reject) => {
        const reader = new FileReader()
        reader.onloadend = () => resolve(reader.result as string)
        reader.onerror = reject
        reader.readAsDataURL(blob)
      })
    } catch {
      return ''
    }
  }

  const handleGeneratePDF = async () => {
    if (!inspection || !equipment) return
    setPdfGenerating(true)
    try {
      // Convert photos to base64
      const base64Photos = await Promise.all(
        photos.map(async (p) => ({
          base64: await toBase64(p.signedUrl),
          caption: p.caption || '',
        }))
      )
      setPdfPhotos(base64Photos)
      await new Promise(r => setTimeout(r, 500)) // wait for re-render

      const el = document.getElementById('pdf-content')
      if (!el) {
        toast.error('PDF template not found')
        return
      }

      // Show element off-screen
      el.style.position = 'absolute'
      el.style.left = '0'
      el.style.top = '0'
      el.style.zIndex = '-9999'
      el.style.display = 'block'

      await new Promise((r) => setTimeout(r, 100))

      const canvas = await html2canvas(el, {
        scale: 1.5,
        useCORS: true,
        backgroundColor: '#ffffff',
      })

      const pdf = new jsPDF('p', 'mm', 'a4')
      const imgData = canvas.toDataURL('image/jpeg', 0.85)
      const pdfWidth = 210
      const pdfHeight = (canvas.height * pdfWidth) / canvas.width

      pdf.addImage(imgData, 'PNG', 0, 0, pdfWidth, Math.min(pdfHeight, 297))

      const tag = equipment.tag || 'unknown'
      const date = formatDateISO(inspection.event_date)
      pdf.save(`Report_${tag}_${date}.pdf`)

      // Hide element
      el.style.display = 'none'

      toast.success('PDF downloaded')
    } catch (err) {
      console.error('PDF generation error:', err)
      toast.error('Failed to generate PDF')
    } finally {
      setPdfGenerating(false)
    }
  }

  // =========================================================================
  // Role checks
  // =========================================================================

  const canGeneratePDF =
    ['engineer', 'supervisor', 'super_admin'].includes(userRole) &&
    (inspection?.status === 'submitted' || inspection?.status === 'approved')

  const canApproveReject =
    (userRole === 'engineer' || userRole === 'supervisor' || userRole === 'super_admin') && inspection?.status === 'submitted'

  // =========================================================================
  // Render
  // =========================================================================

  if (loading) {
    return (
      <AppLayout>
        <div className="px-8 py-8">
          <div className="animate-pulse space-y-4">
            <div className="h-8 w-64 bg-muted/20 rounded" />
            <div className="h-4 w-48 bg-muted/20 rounded" />
            <div className="h-64 bg-muted/10 rounded-xl" />
          </div>
        </div>
      </AppLayout>
    )
  }

  if (!inspection) {
    return (
      <AppLayout>
        <div className="px-8 py-8 text-center text-muted-foreground">
          Inspection not found.
        </div>
      </AppLayout>
    )
  }

  const statusCfg =
    STATUS_CONFIG[inspection.status] || STATUS_CONFIG.draft

  return (
    <AppLayout>
      <div className="px-8 py-8 space-y-6">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <button
            onClick={() => router.push('/inspections')}
            className="hover:text-foreground transition-colors"
          >
            Inspections
          </button>
          <ChevronRight className="h-4 w-4" />
          <span className="text-foreground font-medium">
            {equipment?.tag || 'Unknown'} —{' '}
            {formatDate(inspection.event_date)}
          </span>
        </div>

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              Inspection Detail
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              {equipment?.tag} • {formatDate(inspection.event_date)}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span
              className={cn(
                'inline-block rounded-full px-3 py-1 text-sm font-medium',
                statusCfg.className,
              )}
            >
              {statusCfg.label}
            </span>
            {canApproveReject && (
              <>
                <button
                  onClick={() => handleStatusChange('approved')}
                  disabled={actionLoading}
                  className="inline-flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 transition-colors disabled:opacity-50"
                >
                  {actionLoading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <CheckCircle className="h-4 w-4" />
                  )}
                  Approve
                </button>
                <button
                  onClick={() => handleStatusChange('rejected')}
                  disabled={actionLoading}
                  className="inline-flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 transition-colors disabled:opacity-50"
                >
                  {actionLoading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <XCircle className="h-4 w-4" />
                  )}
                  Reject
                </button>
              {lightbox && (
        <div
          className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center p-4"
          onClick={() => setLightbox(null)}
        >
          <div className="relative max-w-4xl max-h-full">
            <button
              onClick={() => setLightbox(null)}
              className="absolute -top-10 right-0 text-white text-sm hover:text-gray-300"
            >
              ✕ Close
            </button>
            <img
              src={lightbox}
              alt="Full size"
              className="max-w-full max-h-[85vh] object-contain rounded-lg"
              onClick={e => e.stopPropagation()}
            />
          </div>
        </div>
      )}

      </>
            )}
            {canGeneratePDF && (
              <button
                onClick={handleGeneratePDF}
                disabled={pdfGenerating}
                className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
              >
                {pdfGenerating ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Download className="h-4 w-4" />
                )}
                {pdfGenerating ? 'Generating...' : 'Generate PDF'}
              </button>
            )}
          </div>
        </div>

        {/* Section 1 — Inspection Info */}
        <div className="rounded-xl border border-border/70 p-6">
          <h2 className="text-lg font-semibold mb-4">Inspection Info</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <InfoCard label="Equipment Tag" value={equipment?.tag ?? '—'} />
            <InfoCard label="Type" value={equipment?.type ?? '—'} />
            <InfoCard
              label="Area"
              value={equipment?.area_name ?? '—'}
            />
            <InfoCard
              label="Inspector"
              value={inspector?.full_name ?? '—'}
            />
            <InfoCard
              label="Date"
              value={formatDate(inspection.event_date)}
            />
            <InfoCard
              label="Inspection Type"
              value={inspection.inspection_type}
            />
          </div>
          {inspection.notes && (
            <div className="mt-4">
              <p className="text-xs text-muted-foreground mb-1">Notes</p>
              <p className="text-sm">{inspection.notes}</p>
            </div>
          )}
        </div>

        {/* Section 2 — Checklist Results */}
        <div className="rounded-xl border border-border/70 p-6">
          <h2 className="text-lg font-semibold mb-4">Checklist Results</h2>
          {checklistSections.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No checklist data recorded.
            </p>
          ) : (
            <div className="space-y-6">
              {checklistSections.map((sec) => (
                <div key={sec.section}>
                  <h3 className="text-sm font-semibold mb-3 text-muted-foreground uppercase tracking-wider">
                    {sec.section} —{' '}
                    {SECTION_LABELS[sec.section] || `Section ${sec.section}`}
                  </h3>
                  <div className="overflow-x-auto rounded-lg border border-border/50">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-border/70 bg-muted/10">
                          <th className="text-xs uppercase tracking-wider px-4 py-3 text-left font-medium text-muted-foreground">
                            Item Code
                          </th>
                          <th className="text-xs uppercase tracking-wider px-4 py-3 text-left font-medium text-muted-foreground">
                            Description
                          </th>
                          <th className="text-xs uppercase tracking-wider px-4 py-3 text-left font-medium text-muted-foreground">
                            Rating
                          </th>
                          <th className="text-xs uppercase tracking-wider px-4 py-3 text-left font-medium text-muted-foreground">
                            Notes
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {sec.items.map((item) => {
                          const rating = item.rating
                            ? RATING_LABELS[item.rating]
                            : null
                          return (
                            <tr
                              key={item.item_code}
                              className="border-b border-border/30 last:border-b-0"
                            >
                              <td className="px-4 py-3 font-mono text-xs">
                                {item.item_code}
                              </td>
                              <td className="px-4 py-3">
                                {item.description}
                              </td>
                              <td className="px-4 py-3">
                                {rating ? (
                                  <span
                                    className={cn(
                                      'inline-block rounded-full px-2.5 py-0.5 text-xs font-medium',
                                      rating.className,
                                    )}
                                  >
                                    {item.rating} — {rating.text}
                                  </span>
                                ) : (
                                  <span className="text-muted-foreground/40 italic">
                                    —
                                  </span>
                                )}
                              </td>
                              <td className="px-4 py-3 text-muted-foreground text-xs max-w-[200px] truncate">
                                {item.notes || '—'}
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Section 3 — Thickness Readings */}
        <div className="rounded-xl border border-border/70 p-6">
          <h2 className="text-lg font-semibold mb-4">Thickness Readings</h2>
          {thicknessRows.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No thickness readings recorded.
            </p>
          ) : (
            <div className="overflow-x-auto rounded-lg border border-border/50">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border/70 bg-muted/10">
                    <th className="text-xs uppercase tracking-wider px-4 py-3 text-left font-medium text-muted-foreground">
                      CML Location
                    </th>
                    <th className="text-xs uppercase tracking-wider px-4 py-3 text-right font-medium text-muted-foreground">
                      Reading (mm)
                    </th>
                    <th className="text-xs uppercase tracking-wider px-4 py-3 text-right font-medium text-muted-foreground">
                      Nominal (mm)
                    </th>
                    <th className="text-xs uppercase tracking-wider px-4 py-3 text-right font-medium text-muted-foreground">
                      Previous (mm)
                    </th>
                    <th className="text-xs uppercase tracking-wider px-4 py-3 text-left font-medium text-muted-foreground">
                      Date
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {thicknessRows.map((row, i) => (
                    <tr
                      key={i}
                      className="border-b border-border/30 last:border-b-0"
                    >
                      <td className="px-4 py-3 font-medium">
                        {row.cml_location}
                      </td>
                      <td className="px-4 py-3 text-right font-mono">
                        {row.reading_mm.toFixed(2)}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-muted-foreground">
                        {row.nominal_mm.toFixed(2)}
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-muted-foreground">
                        {row.previous_mm !== null
                          ? row.previous_mm.toFixed(2)
                          : '—'}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">
                        {formatDate(row.reading_date)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Section 4 — Photos */}
        <div className="rounded-xl border border-border/70 p-6">
          <h2 className="text-lg font-semibold mb-4">Photos</h2>
          {photos.length === 0 ? (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Camera className="h-5 w-5" />
              <p className="text-sm">No photos recorded.</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
              {photos.map((photo) => (
                <div key={photo.id} className="relative group rounded-lg overflow-hidden border border-border aspect-square">
                  <img
                    src={photo.signedUrl}
                    alt={photo.caption || 'Inspection photo'}
                    className="w-full h-full object-cover"
                  />
                  {photo.caption && (
                    <div className="absolute bottom-0 left-0 right-0 bg-black/60 text-white text-xs p-1.5 truncate">
                      {photo.caption}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Hidden PDF template */}
      <div id="pdf-content" style={{ display: 'none', width: '794px' }}>
        <div
          style={{
            fontFamily: 'Arial, sans-serif',
            color: '#1e293b',
            padding: '0',
            fontSize: '12px',
            lineHeight: '1.5',
            background: '#ffffff',
          }}
        >
          {/* PDF Header */}
          <div
            style={{
              background: '#1e293b',
              color: '#ffffff',
              padding: '24px 32px',
            }}
          >
            <h1
              style={{
                margin: '0 0 4px 0',
                fontSize: '22px',
                fontWeight: '700',
              }}
            >
              INTEGRA IMS — Inspection Report
            </h1>
            <p style={{ margin: '0', fontSize: '13px', opacity: 0.8 }}>
              PT Integra Petrochemical
            </p>
          </div>

          {/* PDF Equipment Info */}
          <div
            style={{
              padding: '16px 32px',
              borderBottom: '1px solid #e2e8f0',
            }}
          >
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <tbody>
                <tr>
                  <td style={{ padding: '4px 0', width: '50%' }}>
                    <strong>Equipment:</strong> {equipment?.tag ?? '—'}
                  </td>
                  <td style={{ padding: '4px 0' }}>
                    <strong>Type:</strong> {equipment?.type ?? '—'}
                  </td>
                </tr>
                <tr>
                  <td style={{ padding: '4px 0' }}>
                    <strong>Date:</strong>{' '}
                    {formatDate(inspection.event_date)}
                  </td>
                  <td style={{ padding: '4px 0' }}>
                    <strong>Inspector:</strong>{' '}
                    {inspector?.full_name ?? '—'}
                  </td>
                </tr>
                <tr>
                  <td style={{ padding: '4px 0' }}>
                    <strong>Inspection Type:</strong>{' '}
                    {inspection.inspection_type}
                  </td>
                  <td style={{ padding: '4px 0' }}>
                    <strong>Status:</strong> {statusCfg.label}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* PDF Checklist */}
          {checklistSections.length > 0 && (
            <div style={{ padding: '16px 32px' }}>
              <h2
                style={{
                  background: '#334155',
                  color: '#ffffff',
                  padding: '8px 12px',
                  fontSize: '14px',
                  fontWeight: '600',
                  margin: '0 0 12px 0',
                }}
              >
                CHECKLIST RESULTS
              </h2>
              {checklistSections.map((sec) => (
                <div key={sec.section} style={{ marginBottom: '16px' }}>
                  <h3
                    style={{
                      fontSize: '13px',
                      fontWeight: '600',
                      marginBottom: '8px',
                      color: '#475569',
                    }}
                  >
                    {sec.section} —{' '}
                    {SECTION_LABELS[sec.section] || `Section ${sec.section}`}
                  </h3>
                  <table
                    style={{
                      width: '100%',
                      borderCollapse: 'collapse',
                      fontSize: '11px',
                    }}
                  >
                    <thead>
                      <tr style={{ background: '#f1f5f9' }}>
                        <th
                          style={{
                            border: '1px solid #e2e8f0',
                            padding: '6px 8px',
                            textAlign: 'left',
                          }}
                        >
                          Code
                        </th>
                        <th
                          style={{
                            border: '1px solid #e2e8f0',
                            padding: '6px 8px',
                            textAlign: 'left',
                          }}
                        >
                          Description
                        </th>
                        <th
                          style={{
                            border: '1px solid #e2e8f0',
                            padding: '6px 8px',
                            textAlign: 'left',
                          }}
                        >
                          Rating
                        </th>
                        <th
                          style={{
                            border: '1px solid #e2e8f0',
                            padding: '6px 8px',
                            textAlign: 'left',
                          }}
                        >
                          Notes
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {sec.items.map((item, idx) => (
                        <tr
                          key={item.item_code}
                          style={{
                            background:
                              idx % 2 === 0 ? '#ffffff' : '#f8fafc',
                          }}
                        >
                          <td
                            style={{
                              border: '1px solid #e2e8f0',
                              padding: '6px 8px',
                            }}
                          >
                            {item.item_code}
                          </td>
                          <td
                            style={{
                              border: '1px solid #e2e8f0',
                              padding: '6px 8px',
                            }}
                          >
                            {item.description}
                          </td>
                          <td
                            style={{
                              border: '1px solid #e2e8f0',
                              padding: '6px 8px',
                            }}
                          >
                            {item.rating
                              ? `${item.rating} — ${RATING_LABELS[item.rating]?.text ?? ''}`
                              : '—'}
                          </td>
                          <td
                            style={{
                              border: '1px solid #e2e8f0',
                              padding: '6px 8px',
                            }}
                          >
                            {item.notes || '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ))}
            </div>
          )}

          {/* PDF Thickness */}
          {thicknessRows.length > 0 && (
            <div style={{ padding: '16px 32px' }}>
              <h2
                style={{
                  background: '#334155',
                  color: '#ffffff',
                  padding: '8px 12px',
                  fontSize: '14px',
                  fontWeight: '600',
                  margin: '0 0 12px 0',
                }}
              >
                THICKNESS READINGS
              </h2>
              <table
                style={{
                  width: '100%',
                  borderCollapse: 'collapse',
                  fontSize: '9px',
                }}
              >
                <thead>
                  <tr style={{ background: '#f1f5f9' }}>
                    <th
                      style={{
                        border: '1px solid #e2e8f0',
                        padding: '4px 6px',
                        textAlign: 'left',
                      }}
                    >
                      CML Location
                    </th>
                    <th
                      style={{
                        border: '1px solid #e2e8f0',
                        padding: '4px 6px',
                        textAlign: 'right',
                      }}
                    >
                      Reading (mm)
                    </th>
                    <th
                      style={{
                        border: '1px solid #e2e8f0',
                        padding: '4px 6px',
                        textAlign: 'right',
                      }}
                    >
                      Nominal (mm)
                    </th>
                    <th
                      style={{
                        border: '1px solid #e2e8f0',
                        padding: '4px 6px',
                        textAlign: 'right',
                      }}
                    >
                      Previous (mm)
                    </th>
                    <th
                      style={{
                        border: '1px solid #e2e8f0',
                        padding: '4px 6px',
                        textAlign: 'left',
                      }}
                    >
                      Date
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {thicknessRows.map((row, idx) => (
                    <tr
                      key={idx}
                      style={{
                        background:
                          idx % 2 === 0 ? '#ffffff' : '#f8fafc',
                      }}
                    >
                      <td
                        style={{
                          border: '1px solid #e2e8f0',
                          padding: '4px 6px',
                        }}
                      >
                        {row.cml_location}
                      </td>
                      <td
                        style={{
                          border: '1px solid #e2e8f0',
                          padding: '4px 6px',
                          textAlign: 'right',
                        }}
                      >
                        {row.reading_mm.toFixed(2)}
                      </td>
                      <td
                        style={{
                          border: '1px solid #e2e8f0',
                          padding: '4px 6px',
                          textAlign: 'right',
                        }}
                      >
                        {row.nominal_mm.toFixed(2)}
                      </td>
                      <td
                        style={{
                          border: '1px solid #e2e8f0',
                          padding: '4px 6px',
                          textAlign: 'right',
                        }}
                      >
                        {row.previous_mm !== null
                          ? row.previous_mm.toFixed(2)
                          : '—'}
                      </td>
                      <td
                        style={{
                          border: '1px solid #e2e8f0',
                          padding: '4px 6px',
                        }}
                      >
                        {formatDate(row.reading_date)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {pdfPhotos.length > 0 && (
            <div style={{ padding: '16px 32px' }}>
              <h2 style={{ background: '#334155', color: '#ffffff', padding: '8px 12px', fontSize: '14px', fontWeight: '600', margin: '0 0 12px 0' }}>
                INSPECTION PHOTOS
              </h2>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px' }}>
                {pdfPhotos.filter(p => p.base64).map((p, i) => (
                  <div key={i} style={{ border: '1px solid #e2e8f0', borderRadius: '4px', overflow: 'hidden' }}>
                    <img src={p.base64} alt={p.caption} style={{ width: '100%', height: '150px', objectFit: 'cover' }} />
                    {p.caption && <p style={{ margin: '4px 8px', fontSize: '10px', color: '#64748b' }}>{p.caption}</p>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* PDF Footer */}
          <div
            style={{
              padding: '16px 32px',
              borderTop: '1px solid #e2e8f0',
              textAlign: 'center',
              fontSize: '10px',
              color: '#94a3b8',
            }}
          >
            Generated by Integra IMS |{' '}
            {new Date().toLocaleString('en-GB')}
          </div>
        </div>
      </div>
    </AppLayout>
  )
}

// ---------------------------------------------------------------------------
// Info Card Component
// ---------------------------------------------------------------------------

function InfoCard({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground mb-1">{label}</p>
      <p className="text-sm font-medium">{value}</p>
    </div>
  )
}
