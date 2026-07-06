'use client'

import { useEffect, useState, useCallback, useRef, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { createClient } from '@/lib/supabase/client'
import type { Database } from '@/types/database'
import AppLayout from '@/components/layout/app-layout'
import { cn } from '@/utils/cn'
import { uploadPhoto } from '@/utils/photos'
import { toast } from 'sonner'
import {
  Search,
  CheckCircle,
  Loader2,
  Upload,
  Camera,
  ChevronDown,
  ChevronRight,
  X,
  Save,
  Send,
  Plus,
  Minus,
} from 'lucide-react'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type EquipmentRow = Database['public']['Tables']['equipment']['Row']
type ChecklistTemplateRow = Database['public']['Tables']['checklist_templates']['Row']
type CMLPointRow = Database['public']['Tables']['cml_points']['Row']
type ThicknessReadingRow = Database['public']['Tables']['thickness_readings']['Row']
type PlantAreaRow = Database['public']['Tables']['plant_areas']['Row']
type AppUserRow = Database['public']['Tables']['app_users']['Row']

interface ChecklistAnswer {
  item_code: string
  answer_rating: number | null
  notes: string
}

interface ThicknessReadingEntry {
  cml_point_id: string
  reading_mm: string
  is_representative: boolean
}

interface PhotoEntry {
  file: File | null
  preview: string
  caption: string
}

interface ChecklistSection {
  section: string
  items: ChecklistTemplateRow[]
}

type RiskBadge = {
  label: string
  className: string
}

const RISK_BADGES: Record<string, RiskBadge> = {
  low: { label: 'Low', className: 'bg-green-100 text-green-700 border-green-200' },
  medium: { label: 'Medium', className: 'bg-yellow-100 text-yellow-700 border-yellow-200' },
  high: { label: 'High', className: 'bg-orange-100 text-orange-700 border-orange-200' },
  critical: { label: 'Critical', className: 'bg-red-100 text-red-700 border-red-200' },
}

const RATING_LABELS = ['', 'Poor', 'Fair', 'Good', 'Very Good', 'Excellent']

const INSPECTION_TYPES = [
  { value: 'external', label: 'External' },
  { value: 'internal', label: 'Internal' },
  { value: 'visual', label: 'Visual' },
  { value: 'cui', label: 'CUI' },
  { value: 'utm', label: 'UTM' },
  { value: 'other', label: 'Other' },
]

function todayString(): string {
  const d = new Date()
  return d.toISOString().slice(0, 10)
}

// ---------------------------------------------------------------------------
// Page Component
// ---------------------------------------------------------------------------

export default function InspectionsNewPage() {
  return (
    <Suspense fallback={<div className="px-6 sm:px-8 py-8"><div className="animate-pulse h-8 w-48 bg-muted/20 rounded" /></div>}>
      <InspectionsNewPageInner />
    </Suspense>
  )
}

function InspectionsNewPageInner() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const supabase = createClient()
  const sb = supabase as any

  const DEMO_USER = {
    id: '3fca82af-b302-4d1e-8536-b89546ecfb15',
    company_id: 'c704d7e6-07fb-48a2-9152-564434d8653f',
    full_name: 'Dicki Wiryawan',
    role: 'super_admin',
  }

  // --- Auth / Profile ---
  const [appUser, setAppUser] = useState<AppUserRow | null>(null)
  const [loadingProfile, setLoadingProfile] = useState(true)

  // --- Step 1: Equipment Search ---
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<EquipmentRow[]>([])
  const [searching, setSearching] = useState(false)
  const [selectedEquipment, setSelectedEquipment] = useState<EquipmentRow & { area_name?: string | null } | null>(null)
  const [showResults, setShowResults] = useState(false)
  const searchRef = useRef<HTMLDivElement>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // --- Filter state ---
  const [areaFilter, setAreaFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [areas, setAreas] = useState<PlantAreaRow[]>([])
  const [autoLoaded, setAutoLoaded] = useState(false)

  // --- Step 2: Metadata ---
  const [inspectionType, setInspectionType] = useState('external')
  const [eventDate, setEventDate] = useState(todayString())
  const [weather, setWeather] = useState('')
  const [inspectionNotes, setInspectionNotes] = useState('')

  // --- Step 3: Checklist ---
  const [checklistItems, setChecklistItems] = useState<ChecklistTemplateRow[]>([])
  const [loadingChecklist, setLoadingChecklist] = useState(false)
  const [checklistAnswers, setChecklistAnswers] = useState<Record<string, ChecklistAnswer>>({})
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({})

  // --- Step 4: Thickness Readings ---
  const [cmlPoints, setCmlPoints] = useState<CMLPointRow[]>([])
  const [loadingCML, setLoadingCML] = useState(false)
  const [thicknessEntries, setThicknessEntries] = useState<Record<string, ThicknessReadingEntry>>({})
  const [previousReadings, setPreviousReadings] = useState<Record<string, number | null>>({})
  const [loadingPrevReadings, setLoadingPrevReadings] = useState(false)

  // --- Step 5: Photos ---
  const [photos, setPhotos] = useState<PhotoEntry[]>([])

  // --- Submit ---
  const [submitting, setSubmitting] = useState(false)

  // =========================================================================
  // Load current user profile
  // =========================================================================

  useEffect(() => {
    async function loadProfile() {
      try {
        setAppUser({
          id: DEMO_USER.id,
          company_id: DEMO_USER.company_id,
          full_name: DEMO_USER.full_name,
          role: DEMO_USER.role,
        } as AppUserRow)
      } catch (err) {
        console.error('Profile load error:', err)
      } finally {
        setLoadingProfile(false)
      }
    }

    loadProfile()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // =========================================================================
  // Click outside to close search results
  // =========================================================================

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setShowResults(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // =========================================================================
  // Load plant areas for filter dropdown
  // =========================================================================

  useEffect(() => {
    async function loadAreas() {
      try {
        const companyId = DEMO_USER.company_id
        if (!companyId) return
        const { data } = await sb
          .from('plant_areas')
          .select('*')
          .eq('company_id', companyId)
          .order('name')
        if (data) setAreas(data as PlantAreaRow[])
      } catch (err) {
        console.error('Load areas error:', err)
      }
    }
    loadAreas()
  }, [sb, supabase])

  // =========================================================================
  // Auto-select equipment from query param ?equipment_id=
  // =========================================================================

  useEffect(() => {
    const equipId = searchParams.get('equipment_id')
    if (!equipId || autoLoaded) return
    setAutoLoaded(true)

    async function loadAndSelect() {
      try {
        const { data } = await sb
          .from('equipment')
          .select('*, plant_areas(name)')
          .eq('id', equipId)
          .single()
        if (data) {
          const eq = {
            ...data,
            area_name: data.plant_areas?.name ?? null,
          } as EquipmentRow & { area_name?: string | null }
          setSelectedEquipment(eq)
        }
      } catch (err) {
        console.error('Auto-select equipment error:', err)
      }
    }
    loadAndSelect()
  }, [searchParams, sb, autoLoaded])

  // =========================================================================
  // Debounced equipment search
  // =========================================================================

  const doSearch = useCallback(
    async (q: string) => {
      if (!q.trim()) {
        setSearchResults([])
        setShowResults(false)
        return
      }

      setSearching(true)
      try {
        const companyId = DEMO_USER.company_id

        if (!companyId) {
          setSearchResults([])
          return
        }

        // Build query with optional filters
        let query = sb
          .from('equipment')
          .select('*, plant_areas!inner(name)')
          .eq('company_id', companyId)
          .ilike('tag', `%${q}%`)

        if (areaFilter) {
          query = query.eq('area_id', areaFilter)
        }
        if (typeFilter) {
          query = query.eq('type', typeFilter)
        }

        const { data } = await query
          .limit(10)
          .order('tag')

        if (data) {
          const results = (data as any[]).map((r) => ({
            ...r,
            area_name: r.plant_areas?.name ?? null,
          })) as (EquipmentRow & { area_name?: string | null })[]
          setSearchResults(results)
          setShowResults(results.length > 0)
        }
      } catch (err) {
        console.error('Search error:', err)
        setSearchResults([])
      } finally {
        setSearching(false)
      }
    },
    [sb, supabase, areaFilter, typeFilter],
  )

  const handleSearchChange = (value: string) => {
    setSearchQuery(value)
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => doSearch(value), 300)
  }

  // =========================================================================
  // Select / Change equipment
  // =========================================================================

  const handleSelectEquipment = (eq: EquipmentRow & { area_name?: string | null }) => {
    setSelectedEquipment(eq)
    setShowResults(false)
    setSearchQuery('')
    // Reset dependent data
    setChecklistItems([])
    setChecklistAnswers({})
    setCmlPoints([])
    setThicknessEntries({})
    setPreviousReadings({})
    setPhotos([])
    setInspectionType('external')
    setEventDate(todayString())
    setWeather('')
    setInspectionNotes('')
  }

  const handleChangeEquipment = () => {
    setSelectedEquipment(null)
    setChecklistItems([])
    setChecklistAnswers({})
    setCmlPoints([])
    setThicknessEntries({})
    setPreviousReadings({})
    setPhotos([])
    setInspectionType('external')
    setEventDate(todayString())
    setWeather('')
    setInspectionNotes('')
  }

  // =========================================================================
  // Fetch checklist templates when equipment selected
  // =========================================================================

  useEffect(() => {
    const equipment = selectedEquipment!
    if (!equipment) return

    async function fetchChecklist() {
      setLoadingChecklist(true)
      try {
        const { data } = await sb
          .from('checklist_templates')
          .select('*')
          .eq('equipment_type', equipment.type)
          .eq('is_active', true)
          .order('display_order', { ascending: true })

        if (data) {
          const items = data as ChecklistTemplateRow[]
          setChecklistItems(items)

          // Init answers
          const answers: Record<string, ChecklistAnswer> = {}
          items.forEach((item) => {
            answers[item.item_code] = {
              item_code: item.item_code,
              answer_rating: null,
              notes: '',
            }
          })
          setChecklistAnswers(answers)

          // Expand first section by default
          const sections = groupBySection(items)
          const expanded: Record<string, boolean> = {}
          sections.forEach((s, i) => {
            expanded[s.section] = i === 0
          })
          setExpandedSections(expanded)
        } else {
          setChecklistItems([])
          setChecklistAnswers({})
        }
      } catch (err) {
        console.error('Checklist fetch error:', err)
        setChecklistItems([])
      } finally {
        setLoadingChecklist(false)
      }
    }

    fetchChecklist()
  }, [selectedEquipment, sb])

  // =========================================================================
  // Fetch CML points when equipment selected
  // =========================================================================

  useEffect(() => {
    const equipment = selectedEquipment!
    if (!equipment) return

    async function fetchCML() {
      setLoadingCML(true)
      try {
        const { data } = await sb
          .from('cml_points')
          .select('*')
          .eq('equipment_id', equipment.id)
          .eq('is_active', true)
          .order('location_label', { ascending: true })

        if (data) {
          const points = data as CMLPointRow[]
          setCmlPoints(points)

          // Init thickness entries
          const entries: Record<string, ThicknessReadingEntry> = {}
          points.forEach((cml) => {
            entries[cml.id] = {
              cml_point_id: cml.id,
              reading_mm: '',
              is_representative: false,
            }
          })
          setThicknessEntries(entries)

          // Fetch previous readings
          fetchPreviousReadings(points)
        } else {
          setCmlPoints([])
          setThicknessEntries({})
          setPreviousReadings({})
        }
      } catch (err) {
        console.error('CML fetch error:', err)
        setCmlPoints([])
      } finally {
        setLoadingCML(false)
      }
    }

    fetchCML()
  }, [selectedEquipment, sb])

  // =========================================================================
  // Fetch previous thickness readings for each CML
  // =========================================================================

  async function fetchPreviousReadings(cmls: CMLPointRow[]) {
    if (cmls.length === 0) {
      setPreviousReadings({})
      return
    }

    setLoadingPrevReadings(true)
    try {
      const cmlIds = cmls.map((c) => c.id)
      const { data } = await sb
        .from('thickness_readings')
        .select('*')
        .in('cml_point_id', cmlIds)
        .order('reading_date', { ascending: false })

      if (data) {
        const readings = data as ThicknessReadingRow[]
        const latest: Record<string, number | null> = {}
        for (const cml of cmls) {
          const cmlReadings = readings.filter((r) => r.cml_point_id === cml.id)
          latest[cml.id] = cmlReadings.length > 0 ? cmlReadings[0].reading_mm : null
        }
        setPreviousReadings(latest)
      }
    } catch (err) {
      console.error('Previous readings fetch error:', err)
    } finally {
      setLoadingPrevReadings(false)
    }
  }

  // =========================================================================
  // Helpers
  // =========================================================================

  function groupBySection(items: ChecklistTemplateRow[]): ChecklistSection[] {
    const map = new Map<string, ChecklistTemplateRow[]>()
    items.forEach((item) => {
      const sec = item.section
      if (!map.has(sec)) map.set(sec, [])
      map.get(sec)!.push(item)
    })
    return Array.from(map.entries()).map(([section, items]) => ({ section, items }))
  }

  function countRated(): number {
    return Object.values(checklistAnswers).filter((a) => a.answer_rating !== null).length
  }

  function totalChecklistItems(): number {
    return checklistItems.length
  }

  function sectionRatedCount(items: ChecklistTemplateRow[]): number {
    return items.filter((item) => checklistAnswers[item.item_code]?.answer_rating !== null).length
  }

  function getRiskBadge(category: string | null | undefined): RiskBadge | null {
    if (!category) return null
    return RISK_BADGES[category.toLowerCase()] ?? null
  }

  // =========================================================================
  // Checklist handlers
  // =========================================================================

  function handleRating(itemCode: string, rating: number) {
    setChecklistAnswers((prev) => ({
      ...prev,
      [itemCode]: { ...prev[itemCode], answer_rating: rating },
    }))
  }

  function handleChecklistNote(itemCode: string, note: string) {
    setChecklistAnswers((prev) => ({
      ...prev,
      [itemCode]: { ...prev[itemCode], notes: note },
    }))
  }

  function toggleSection(section: string) {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }))
  }

  // =========================================================================
  // Thickness handlers
  // =========================================================================

  function handleReadingChange(cmlId: string, value: string) {
    // Allow empty string or positive numbers
    if (value !== '' && (isNaN(Number(value)) || Number(value) <= 0)) return
    setThicknessEntries((prev) => ({
      ...prev,
      [cmlId]: { ...prev[cmlId], reading_mm: value },
    }))
  }

  function handleRepresentativeChange(cmlId: string, checked: boolean) {
    setThicknessEntries((prev) => ({
      ...prev,
      [cmlId]: { ...prev[cmlId], is_representative: checked },
    }))
  }

  // =========================================================================
  // Photo handlers
  // =========================================================================
  // Photo handlers
  function handlePhotoFileSelect(index: number, file: File | null) {
    const prev = photos[index]
    // Revoke old preview if exists
    if (prev?.preview) URL.revokeObjectURL(prev.preview)

    const preview = file ? URL.createObjectURL(file) : ''
    setPhotos((prev) => {
      const updated = [...prev]
      updated[index] = { ...updated[index], file, preview }
      return updated
    })
  }

  function handlePhotoCaptionChange(index: number, caption: string) {
    setPhotos((prev) => {
      const updated = [...prev]
      updated[index] = { ...updated[index], caption }
      return updated
    })
  }

  function handleAddPhoto() {
    setPhotos((prev) => [...prev, { file: null, preview: '', caption: '' }])
  }

  function handleRemovePhoto(index: number) {
    const target = photos[index]
    if (target?.preview) URL.revokeObjectURL(target.preview)
    setPhotos((prev) => prev.filter((_, i) => i !== index))
  }

  // Cleanup object URLs on unmount
  useEffect(() => {
    return () => {
      photos.forEach((p) => {
        if (p.preview) URL.revokeObjectURL(p.preview)
      })
    }
  }, [])

  // =========================================================================
  // Submit
  // =========================================================================

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()

    if (!selectedEquipment || !appUser) {
      toast.error('Missing equipment selection or user profile')
      return
    }

    // Validation: ALL checklist items must be rated
    const totalItems = totalChecklistItems()
    const ratedCount = countRated()
    if (totalItems > 0 && ratedCount < totalItems) {
      toast.error(`Please rate all checklist items (${ratedCount}/${totalItems} completed)`)
      return
    }

    // Validation: ALL CML points must have a reading
    const thicknessValues = Object.values(thicknessEntries).filter((t) => t.reading_mm !== '')
    if (cmlPoints.length > 0 && thicknessValues.length < cmlPoints.length) {
      toast.error(`Please enter thickness readings for all CML points (${thicknessValues.length}/${cmlPoints.length} completed)`)
      return
    }

    // Validate readings > 0
    for (const entry of thicknessValues) {
      if (Number(entry.reading_mm) <= 0) {
        toast.error('Thickness readings must be greater than 0')
        return
      }
    }

    setSubmitting(true)

    try {
      // Get company ID from app user
      const companyId = appUser.company_id
      if (!companyId) {
        toast.error('No company associated with your account')
        setSubmitting(false)
        return
      }

      // 1. Create inspection_event
      const { data: eventData, error: eventError } = await sb
        .from('inspection_events')
        .insert({
          company_id: companyId,
          equipment_id: selectedEquipment.id,
          inspector_id: appUser.id,
          inspection_type: inspectionType,
          event_date: eventDate,
          status: 'submitted',
          notes: inspectionNotes || null,
          weather_condition: weather || null,
        })
        .select('id')
        .single()

      if (eventError) {
        console.error('Event insert error:', eventError)
        toast.error(eventError.message || 'Failed to create inspection event')
        setSubmitting(false)
        return
      }

      const eventId = (eventData as { id: string }).id

      // 2. Batch insert checklist_answers
      const answersToInsert = Object.values(checklistAnswers)
        .filter((a) => a.answer_rating !== null)

      if (answersToInsert.length > 0) {
        const answerRows = answersToInsert.map((a) => ({
          inspection_event_id: eventId,
          item_code: a.item_code,
          answer_rating: a.answer_rating,
          notes: a.notes || null,
        }))

        const { error: answersError } = await sb
          .from('checklist_answers')
          .insert(answerRows)

        if (answersError) {
          console.error('Answers insert error:', answersError)
          toast.error(answersError.message || 'Failed to save checklist answers')
          setSubmitting(false)
          return
        }
      }

      // 3. Batch insert thickness_readings
      const readingRows = thicknessValues.map((t) => ({
        company_id: companyId,
        cml_point_id: t.cml_point_id,
        inspection_event_id: eventId,
        reading_date: eventDate,
        reading_mm: Number(t.reading_mm),
        is_representative: t.is_representative,
      }))

      if (readingRows.length > 0) {
        const { error: readingsError } = await sb
          .from('thickness_readings')
          .insert(readingRows)

        if (readingsError) {
          console.error('Readings insert error:', readingsError)
          toast.error(readingsError.message || 'Failed to save thickness readings')
          setSubmitting(false)
          return
        }
      }

      // 4. Upload photos to Supabase Storage + insert into photos table
      const photoRows: any[] = []
      for (const p of photos) {
        if (!p.file) {
          continue
        }
        const storagePath = await uploadPhoto(p.file, companyId, eventId)
        if (!storagePath) {
          toast.error(`Failed to upload ${p.file.name}`)
          setSubmitting(false)
          return
        }
        photoRows.push({
          company_id: companyId,
          storage_path: storagePath,
          caption: p.caption || null,
          related_level: 'event' as const,
          related_id: eventId,
          is_critical: false,
        })
      }

      if (photoRows.length > 0) {
        const { error: photosError } = await sb
          .from('photos')
          .insert(photoRows)

        if (photosError) {
          console.error('Photos insert error:', photosError)
        }
      }

      toast.success('Inspection submitted successfully')
      router.push(`/inspections/${eventId}`)
    } catch (err) {
      console.error('Submit error:', err)
      toast.error('Unexpected error submitting inspection')
    } finally {
      setSubmitting(false)
    }
  }

  // =========================================================================
  // Loading state
  // =========================================================================

  if (loadingProfile) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center py-32">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </AppLayout>
    )
  }

  // =========================================================================
  // Grouped checklist sections
  // =========================================================================

  const checklistSections = groupBySection(checklistItems)
  const ratedCount = countRated()
  const totalItems = totalChecklistItems()

  // =========================================================================
  // Render
  // =========================================================================

  return (
    <AppLayout>
      <div className="px-8 py-8 max-w-4xl space-y-8">
        {/* ===== Header ===== */}
        <div>
          <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight">New Inspection</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Complete the inspection form and submit your findings
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-8">
          {/* ============================================================= */}
          {/* STEP 1: EQUIPMENT SEARCH */}
          {/* ============================================================= */}
          <section className="rounded-xl border border-border/70 p-6 space-y-4">
            <h2 className="text-base font-semibold flex items-center gap-2">
              <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-primary/10 text-primary text-xs font-bold">
                1
              </span>
              Select Equipment
            </h2>

            {!selectedEquipment ? (
              <div ref={searchRef} className="relative space-y-3">
                {/* Filter dropdowns */}
                <div className="flex gap-3">
                  <select
                    value={areaFilter}
                    onChange={(e) => { setAreaFilter(e.target.value); setShowResults(false); }}
                    className="flex-1 rounded-xl border border-border/70 bg-background px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 appearance-none"
                  >
                    <option value="">All Areas</option>
                    {areas.map((area) => (
                      <option key={area.id} value={area.id}>{area.name}</option>
                    ))}
                  </select>
                  <select
                    value={typeFilter}
                    onChange={(e) => { setTypeFilter(e.target.value); setShowResults(false); }}
                    className="flex-1 rounded-xl border border-border/70 bg-background px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 appearance-none"
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
                </div>
                {/* Search box */}
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => handleSearchChange(e.target.value)}
                    onFocus={() => {
                      if (searchResults.length > 0) setShowResults(true)
                    }}
                    placeholder="Search equipment by tag..."
                    className="w-full rounded-xl border border-border/70 bg-background pl-10 pr-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 transition-all"
                  />
                  {searching && (
                    <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 animate-spin text-muted-foreground" />
                  )}
                </div>

                {/* Search Results Dropdown */}
                {showResults && searchResults.length > 0 && (
                  <div className="absolute z-50 mt-2 w-full rounded-xl border border-border/70 bg-card shadow-lg overflow-hidden">
                    {searchResults.map((eq) => {
                      const badge = getRiskBadge(eq.risk_category)
                      return (
                        <button
                          key={eq.id}
                          type="button"
                          onClick={() => handleSelectEquipment(eq as EquipmentRow & { area_name?: string | null })}
                          className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-accent transition-colors border-b border-border/50 last:border-b-0"
                        >
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-sm">{eq.tag}</span>
                              <span className="text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded capitalize">
                                {eq.type}
                              </span>
                            </div>
                            <p className="text-xs text-muted-foreground truncate mt-0.5">
                              {(eq as any).area_name || 'No area'}
                            </p>
                          </div>
                          {badge && (
                            <span
                              className={cn(
                                'text-[11px] font-medium px-2 py-0.5 rounded-full border',
                                badge.className,
                              )}
                            >
                              {badge.label}
                            </span>
                          )}
                        </button>
                      )
                    })}
                  </div>
                )}

                {showResults && searchResults.length === 0 && !searching && searchQuery.trim() && (
                  <div className="absolute z-50 mt-2 w-full rounded-xl border border-border/70 bg-card shadow-lg p-4 text-center text-sm text-muted-foreground">
                    No equipment found matching &quot;{searchQuery}&quot;
                  </div>
                )}
              </div>
            ) : (
              /* Selected Equipment Card */
              <div className="flex items-center gap-4 p-4 rounded-xl border border-primary/20 bg-primary/[0.03]">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-base">{selectedEquipment.tag}</span>
                    <span className="text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded capitalize">
                      {selectedEquipment.type}
                    </span>
                    {(() => {
                      const badge = getRiskBadge(selectedEquipment.risk_category)
                      return badge ? (
                        <span
                          className={cn(
                            'text-[11px] font-medium px-2 py-0.5 rounded-full border',
                            badge.className,
                          )}
                        >
                          {badge.label}
                        </span>
                      ) : null
                    })()}
                  </div>
                  <p className="text-sm text-muted-foreground mt-0.5">
                    {selectedEquipment.area_name || 'No area assigned'}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={handleChangeEquipment}
                  className="text-xs text-primary hover:text-primary/80 font-medium whitespace-nowrap transition-colors"
                >
                  Change
                </button>
              </div>
            )}
          </section>

          {/* Only show rest if equipment selected */}
          {selectedEquipment && (
            <>
              {/* ========================================================= */}
              {/* STEP 2: INSPECTION METADATA */}
              {/* ========================================================= */}
              <section className="rounded-xl border border-border/70 p-6 space-y-4">
                <h2 className="text-base font-semibold flex items-center gap-2">
                  <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-primary/10 text-primary text-xs font-bold">
                    2
                  </span>
                  Inspection Details
                </h2>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-sm font-medium">Inspection Type</label>
                    <select
                      value={inspectionType}
                      onChange={(e) => setInspectionType(e.target.value)}
                      className="w-full rounded-xl border border-border/70 bg-background px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 transition-all"
                    >
                      {INSPECTION_TYPES.map((t) => (
                        <option key={t.value} value={t.value}>
                          {t.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-sm font-medium">Date</label>
                    <input
                      type="date"
                      value={eventDate}
                      onChange={(e) => setEventDate(e.target.value)}
                      className="w-full rounded-xl border border-border/70 bg-background px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 transition-all"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-sm font-medium">Weather Condition</label>
                    <input
                      type="text"
                      value={weather}
                      onChange={(e) => setWeather(e.target.value)}
                      placeholder="e.g., Sunny, Rainy, 30°C"
                      className="w-full rounded-xl border border-border/70 bg-background px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 transition-all"
                    />
                  </div>

                  <div className="space-y-1.5 sm:col-span-2">
                    <label className="text-sm font-medium">Notes</label>
                    <textarea
                      value={inspectionNotes}
                      onChange={(e) => setInspectionNotes(e.target.value)}
                      rows={3}
                      placeholder="General notes about this inspection..."
                      className="w-full rounded-xl border border-border/70 bg-background px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 transition-all resize-y"
                    />
                  </div>
                </div>
              </section>

              {/* ========================================================= */}
              {/* STEP 3: CHECKLIST SECTIONS */}
              {/* ========================================================= */}
              <section className="rounded-xl border border-border/70 p-6 space-y-4">
                <h2 className="text-base font-semibold flex items-center gap-2">
                  <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-primary/10 text-primary text-xs font-bold">
                    3
                  </span>
                  Inspection Checklist
                </h2>

                {loadingChecklist ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                    <span className="ml-2 text-sm text-muted-foreground">Loading checklist...</span>
                  </div>
                ) : checklistItems.length === 0 ? (
                  <div className="text-center py-8 text-sm text-muted-foreground">
                    No checklist items found for this equipment type.
                  </div>
                ) : (
                  <>
                    {/* Progress Bar */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">
                          {ratedCount} of {totalItems} items rated
                        </span>
                        <span className="font-medium text-primary">
                          {totalItems > 0 ? Math.round((ratedCount / totalItems) * 100) : 0}%
                        </span>
                      </div>
                      <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary rounded-full transition-all duration-500 ease-out"
                          style={{
                            width: `${totalItems > 0 ? (ratedCount / totalItems) * 100 : 0}%`,
                          }}
                        />
                      </div>
                    </div>

                    {/* Collapsible Sections */}
                    <div className="space-y-3">
                      {checklistSections.map((section) => {
                        const sectionRated = sectionRatedCount(section.items)
                        const isExpanded = expandedSections[section.section] ?? false

                        return (
                          <div
                            key={section.section}
                            className="rounded-xl border border-border/70 overflow-hidden"
                          >
                            {/* Section Header */}
                            <button
                              type="button"
                              onClick={() => toggleSection(section.section)}
                              className="w-full flex items-center gap-3 px-4 py-3 bg-muted/50 hover:bg-accent transition-colors text-left"
                            >
                              <ChevronDown
                                className={cn(
                                  'h-4 w-4 text-muted-foreground transition-transform duration-200',
                                  !isExpanded && '-rotate-90',
                                )}
                              />
                              <div className="flex-1 min-w-0">
                                <span className="text-sm font-semibold">
                                  {section.section} - {getSectionTitle(section.section)}
                                </span>
                              </div>
                              <span className="text-xs text-muted-foreground whitespace-nowrap">
                                {sectionRated}/{section.items.length} rated
                              </span>
                            </button>

                            {/* Section Body */}
                            {isExpanded && (
                              <div className="divide-y divide-border/50">
                                {section.items.map((item) => {
                                  const answer = checklistAnswers[item.item_code]
                                  const currentRating = answer?.answer_rating ?? null
                                  const noteValue = answer?.notes ?? ''

                                  return (
                                    <div key={item.id} className="px-4 py-3 space-y-3">
                                      {/* Item header */}
                                      <div className="flex items-start justify-between gap-4">
                                        <div className="flex-1 min-w-0">
                                          <div className="flex items-center gap-2">
                                            <span className="text-xs font-mono text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                                              {item.item_code}
                                            </span>
                                            {item.item_type !== 'rating' && (
                                              <span className="text-[10px] uppercase text-muted-foreground bg-muted px-1 rounded">
                                                {item.item_type}
                                              </span>
                                            )}
                                          </div>
                                          <p className="text-sm mt-1">{item.item_description}</p>
                                        </div>
                                      </div>

                                      {/* Rating selector (only for rating items) */}
                                      {item.item_type === 'rating' && (
                                        <div className="flex items-center gap-1.5">
                                          {[1, 2, 3, 4, 5].map((r) => (
                                            <button
                                              key={r}
                                              type="button"
                                              onClick={() => handleRating(item.item_code, r)}
                                              className={cn(
                                                'flex flex-col items-center justify-center w-14 h-12 rounded-lg text-xs font-medium border transition-all',
                                                currentRating === r
                                                  ? 'bg-primary text-primary-foreground border-primary shadow-sm'
                                                  : 'bg-background text-muted-foreground border-border/70 hover:border-primary/50 hover:bg-accent',
                                              )}
                                              title={RATING_LABELS[r]}
                                            >
                                              <span className="text-sm font-bold leading-none">{r}</span>
                                              <span className="text-[9px] mt-0.5 leading-tight">
                                                {RATING_LABELS[r]}
                                              </span>
                                            </button>
                                          ))}
                                        </div>
                                      )}

                                      {/* Notes per item */}
                                      <div>
                                        <input
                                          type="text"
                                          value={noteValue}
                                          onChange={(e) => handleChecklistNote(item.item_code, e.target.value)}
                                          placeholder="Optional notes for this item..."
                                          className="w-full rounded-lg border border-border/70 bg-background px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-primary/30 transition-all"
                                        />
                                      </div>
                                    </div>
                                  )
                                })}
                              </div>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  </>
                )}
              </section>

              {/* ========================================================= */}
              {/* STEP 4: THICKNESS READINGS */}
              {/* ========================================================= */}
              <section className="rounded-xl border border-border/70 p-6 space-y-4">
                <h2 className="text-base font-semibold flex items-center gap-2">
                  <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-primary/10 text-primary text-xs font-bold">
                    4
                  </span>
                  Thickness Readings
                </h2>

                {loadingCML ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                    <span className="ml-2 text-sm text-muted-foreground">Loading CML points...</span>
                  </div>
                ) : cmlPoints.length === 0 ? (
                  <div className="text-center py-8 text-sm text-muted-foreground">
                    No CML points found for this equipment.
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-border/70">
                          <th className="text-left py-2.5 px-3 font-medium text-muted-foreground text-xs uppercase tracking-wider">
                            Location Label
                          </th>
                          <th className="text-left py-2.5 px-3 font-medium text-muted-foreground text-xs uppercase tracking-wider">
                            Type
                          </th>
                          <th className="text-right py-2.5 px-3 font-medium text-muted-foreground text-xs uppercase tracking-wider">
                            Nominal (mm)
                          </th>
                          <th className="text-right py-2.5 px-3 font-medium text-muted-foreground text-xs uppercase tracking-wider">
                            T-Min (mm)
                          </th>
                          <th className="text-right py-2.5 px-3 font-medium text-muted-foreground text-xs uppercase tracking-wider">
                            Prev (mm)
                          </th>
                          <th className="text-right py-2.5 px-3 font-medium text-muted-foreground text-xs uppercase tracking-wider">
                            Reading (mm)
                          </th>
                          <th className="text-center py-2.5 px-3 font-medium text-muted-foreground text-xs uppercase tracking-wider">
                            Rep.
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {cmlPoints.map((cml) => {
                          const entry = thicknessEntries[cml.id]
                          const prevReading = previousReadings[cml.id]
                          const readingValue = entry?.reading_mm ?? ''

                          return (
                            <tr
                              key={cml.id}
                              className="border-b border-border/30 hover:bg-muted/30 transition-colors"
                            >
                              <td className="py-2.5 px-3 font-medium text-sm">
                                {cml.location_label}
                              </td>
                              <td className="py-2.5 px-3 text-sm text-muted-foreground uppercase">
                                {cml.cml_type}
                              </td>
                              <td className="py-2.5 px-3 text-right text-sm font-mono">
                                {cml.nominal_thickness.toFixed(2)}
                              </td>
                              <td className="py-2.5 px-3 text-right text-sm font-mono text-muted-foreground">
                                {cml.t_min !== null ? cml.t_min.toFixed(2) : '—'}
                              </td>
                              <td className="py-2.5 px-3 text-right text-sm font-mono">
                                {loadingPrevReadings ? (
                                  <Loader2 className="h-3 w-3 animate-spin inline-block text-muted-foreground" />
                                ) : prevReading !== null ? (
                                  <span className="text-muted-foreground">
                                    {prevReading.toFixed(2)}
                                  </span>
                                ) : (
                                  <span className="text-muted-foreground">—</span>
                                )}
                              </td>
                              <td className="py-2.5 px-3 text-right">
                                <input
                                  type="number"
                                  step="0.01"
                                  min="0"
                                  value={readingValue}
                                  onChange={(e) => handleReadingChange(cml.id, e.target.value)}
                                  placeholder="0.00"
                                  className={cn(
                                    'w-24 text-right rounded-lg border bg-background px-2.5 py-1.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary/30 transition-all',
                                    readingValue !== '' && Number(readingValue) > 0
                                      ? 'border-primary/40'
                                      : 'border-border/70',
                                  )}
                                />
                              </td>
                              <td className="py-2.5 px-3 text-center">
                                <input
                                  type="checkbox"
                                  checked={entry?.is_representative ?? false}
                                  onChange={(e) =>
                                    handleRepresentativeChange(cml.id, e.target.checked)
                                  }
                                  className="h-4 w-4 rounded border-border text-primary focus:ring-primary/30 cursor-pointer"
                                />
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </section>

              {/* ========================================================= */}
              {/* STEP 5: PHOTO UPLOAD */}
              {/* ========================================================= */}
              <section className="rounded-xl border border-border/70 p-6 space-y-4">
                <h2 className="text-base font-semibold flex items-center gap-2">
                  <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-primary/10 text-primary text-xs font-bold">
                    5
                  </span>
                  Photos
                  {photos.filter((p) => p.file).length > 0 && (
                    <span className="text-xs text-muted-foreground font-normal">
                      ({photos.filter((p) => p.file).length} selected)
                    </span>
                  )}
                </h2>

                <div className="space-y-3">
                  {photos.map((photo, index) => (
                    <div
                      key={index}
                      className="flex items-center gap-3 p-3 rounded-xl border border-border/70 bg-muted/30"
                    >
                      {photo.preview ? (
                        <img
                          src={photo.preview}
                          alt="Preview"
                          className="h-14 w-14 rounded-lg object-cover shrink-0 border border-border"
                          onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
                        />
                      ) : (
                        <div className="h-14 w-14 rounded-lg border border-dashed border-border/70 flex items-center justify-center shrink-0 bg-background">
                          <Camera className="h-5 w-5 text-muted-foreground" />
                        </div>
                      )}
                      <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-2">
                        <div>
                          <input
                            type="file"
                            accept="image/jpeg,image/png,image/webp,image/heic"
                            onChange={(e) =>
                              handlePhotoFileSelect(index, e.target.files?.[0] || null)
                            }
                            className="w-full text-sm file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-medium file:bg-primary/10 file:text-primary hover:file:bg-primary/20 transition-all cursor-pointer"
                          />
                        </div>
                        <input
                          type="text"
                          value={photo.caption}
                          onChange={(e) => handlePhotoCaptionChange(index, e.target.value)}
                          placeholder="Caption / description (optional)"
                          className="w-full rounded-lg border border-border/70 bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 transition-all"
                        />
                      </div>
                      <button
                        type="button"
                        onClick={() => handleRemovePhoto(index)}
                        className="shrink-0 p-1.5 rounded-lg hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  ))}

                  <button
                    type="button"
                    onClick={handleAddPhoto}
                    className="w-full flex items-center justify-center gap-2 py-3 rounded-xl border-2 border-dashed border-border/70 text-sm text-muted-foreground hover:border-primary/50 hover:text-primary transition-colors"
                  >
                    <Plus className="h-4 w-4" />
                    Add Photo
                  </button>

                  <p className="text-xs text-muted-foreground">
                    Photos are uploaded directly to Supabase Storage (max 10MB each, JPG/PNG/WebP/HEIC). Captions are optional.
                  </p>
                </div>
              </section>

              {/* ========================================================= */}
              {/* SUBMIT */}
              {/* ========================================================= */}
              <div className="flex items-center justify-between gap-3 pb-8">
                <div className="flex-1">
                  {(() => {
                    const tItems = totalChecklistItems()
                    const rCount = countRated()
                    const cmlCount = cmlPoints.length
                    const readingFilled = Object.values(thicknessEntries).filter(t => t.reading_mm !== '').length
                    const missingChecklist = tItems > 0 && rCount < tItems
                    const missingCML = cmlCount > 0 && readingFilled < cmlCount
                    if (missingChecklist || missingCML) {
                      return (
                        <p className="text-xs text-muted-foreground">
                          ⚠ Complete all fields to enable submit —&nbsp;
                          {missingChecklist && <span className="text-amber-600">{rCount}/{tItems} checklist items</span>}
                          {missingChecklist && missingCML && <span> · </span>}
                          {missingCML && <span className="text-amber-600">{readingFilled}/{cmlCount} CML readings</span>}
                        </p>
                      )
                    }
                    return <span />
                  })()}
                </div>
                <button
                  type="submit"
                  disabled={submitting || (totalChecklistItems() > 0 && countRated() < totalChecklistItems()) || (cmlPoints.length > 0 && Object.values(thicknessEntries).filter(t => t.reading_mm !== '').length < cmlPoints.length)}
                  className="inline-flex items-center gap-2 rounded-xl bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {submitting ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Send className="h-4 w-4" />
                  )}
                  {submitting ? 'Submitting...' : 'Submit Inspection'}
                </button>
                <button
                  type="button"
                  onClick={() => router.back()}
                  className="rounded-xl border border-border/70 px-6 py-2.5 text-sm font-medium text-muted-foreground hover:bg-accent transition-colors"
                >
                  Cancel
                </button>
              </div>
            </>
          )}
        </form>
      </div>
    </AppLayout>
  )
}

// ===========================================================================
// Section title helper
// ===========================================================================

function getSectionTitle(section: string): string {
  const titles: Record<string, string> = {
    A: 'General Information',
    B: 'External Visual Inspection',
    C: 'Internal Inspection',
    D: 'CUI Inspection',
    E: 'UTM Thickness Verification',
    F: 'Support & Structural',
    G: 'Valves & Fittings',
    H: 'Insulation & Cladding',
    I: 'Safety Devices',
    J: 'Coating & Painting',
  }
  return titles[section] || `Section ${section}`
}
