'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase/client'
import AppLayout from '@/components/layout/app-layout'
import { cn } from '@/utils/cn'
import {
  ArrowLeft,
  Search,
  X,
  Check,
  ChevronDown,
  ChevronUp,
  Loader2,
} from 'lucide-react'

interface PlantArea { id: string; name: string }
interface EquipmentOption {
  id: string
  tag: string
  type: string
  fluid_service: string | null
  insulation_type: string | null
  risk_category: string | null
  area_id: string | null
  area_name?: string
  is_active: boolean
}

const CAMPAIGN_TYPES = [
  { value: 'cui', label: 'CUI' },
  { value: 'general', label: 'General' },
  { value: 'other', label: 'Other' },
]

const EQUIPMENT_TYPES = ['piping', 'vessel', 'tank', 'heater', 'pump', 'compressor', 'valve', 'exchanger', 'drum', 'column']
const INSULATION_TYPES = ['Ceramic fiber', 'Mineral wool', 'PUF', 'Rock wool', 'Calcium silicate']
const RISK_CATEGORIES = ['high', 'medium', 'low']
const FLUID_SERVICES = ['Steam', 'Ethylene', 'Propylene', 'Hydrocarbon', 'Water', 'Air', 'Nitrogen', 'Acid', 'Caustic']

export default function NewCampaignPage() {
  const router = useRouter()
  const [companyId, setCompanyId] = useState<string | null>(null)
  const [areas, setAreas] = useState<PlantArea[]>([])
  const [allEquipment, setAllEquipment] = useState<EquipmentOption[]>([])
  const [showFilters, setShowFilters] = useState(true)
  const [saving, setSaving] = useState(false)

  // Form fields
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [campaignType, setCampaignType] = useState('cui')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [targetCount, setTargetCount] = useState(0)

  // Filters
  const [filterArea, setFilterArea] = useState('')
  const [filterType, setFilterType] = useState('')
  const [filterInsulation, setFilterInsulation] = useState('')
  const [filterRisk, setFilterRisk] = useState('')
  const [filterFluid, setFilterFluid] = useState('')

  // Selection state
  const [suggested, setSuggested] = useState<EquipmentOption[]>([])
  const [excluded, setExcluded] = useState<Set<string>>(new Set())
  const [added, setAdded] = useState<EquipmentOption[]>([])
  const [manualSearch, setManualSearch] = useState('')
  const [previewDone, setPreviewDone] = useState(false)

  // Load initial data
  useEffect(() => {
    const load = async () => {
      const supabase = createClient()
      const sb = supabase as any
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) return

      const { data: appUser } = await sb.from('app_users').select('company_id').eq('auth_user_id', user.id).single()
      if (!appUser?.company_id) return
      setCompanyId(appUser.company_id)

      const { data: areaData } = await sb.from('plant_areas').select('id, name').eq('company_id', appUser.company_id).order('name')
      setAreas(areaData || [])

      const { data: eqData } = await sb.from('equipment')
        .select('id, tag, type, fluid_service, insulation_type, risk_category, area_id, is_active')
        .eq('company_id', appUser.company_id)
        .eq('is_active', true)
        .order('tag')

      if (eqData) {
        const areaMap = new Map((areaData || []).map((a: PlantArea) => [a.id, a.name]))
        const enriched = eqData.map((e: EquipmentOption) => ({
          ...e,
          area_name: areaMap.get(e.area_id || '') || '—',
        }))
        setAllEquipment(enriched)
      }
    }
    load()
  }, [])

  // Run filter preview
  const runPreview = useCallback(() => {
    let filtered = allEquipment.filter(e => e.is_active)
    if (filterArea) filtered = filtered.filter(e => e.area_id === filterArea)
    if (filterType) filtered = filtered.filter(e => e.type === filterType)
    if (filterInsulation) filtered = filtered.filter(e => e.insulation_type === filterInsulation)
    if (filterRisk) filtered = filtered.filter(e => e.risk_category === filterRisk)
    if (filterFluid) filtered = filtered.filter(e => e.fluid_service === filterFluid)

    setSuggested(filtered)
    setExcluded(new Set())
    setAdded([])
    setTargetCount(filtered.length)
    setPreviewDone(true)
  }, [allEquipment, filterArea, filterType, filterInsulation, filterRisk, filterFluid])

  // Manual add
  const manualMatches = manualSearch.length >= 2
    ? allEquipment.filter(e =>
        e.tag.toLowerCase().includes(manualSearch.toLowerCase()) &&
        !suggested.some(s => s.id === e.id) &&
        !added.some(a => a.id === e.id) &&
        !excluded.has(e.id)
      ).slice(0, 10)
    : []

  const toggleExclude = (id: string) => {
    setExcluded(prev => {
      const next = new Set(prev)
      if (next.has(id)) { next.delete(id) } else { next.add(id) }
      return next
    })
  }

  const addManual = (eq: EquipmentOption) => {
    setAdded(prev => [...prev, eq])
    setManualSearch('')
    setTargetCount(prev => prev + 1)
  }

  const removeManual = (id: string) => {
    setAdded(prev => prev.filter(a => a.id !== id))
    setTargetCount(prev => Math.max(0, prev - 1))
  }

  // Final selected = (suggested - excluded) + added
  const selectedEquipment = [
    ...suggested.filter(s => !excluded.has(s.id)),
    ...added,
  ]

  const handleSave = async () => {
    if (!name.trim() || !companyId || !startDate || !endDate) return
    setSaving(true)
    try {
      const supabase = createClient()
      const sb = supabase as any

      const selectionCriteria: Record<string, unknown> = {}
      if (filterArea) selectionCriteria.area_id = filterArea
      if (filterType) selectionCriteria.type = filterType
      if (filterInsulation) selectionCriteria.insulation_type = filterInsulation
      if (filterRisk) selectionCriteria.risk_category = filterRisk
      if (filterFluid) selectionCriteria.fluid_service = filterFluid

      const { data: campaign, error: cErr } = await sb.from('inspection_campaigns').insert({
        company_id: companyId,
        name: name.trim(),
        description: description.trim() || null,
        campaign_type: campaignType,
        start_date: startDate,
        end_date: endDate,
        target_count: selectedEquipment.length,
        selection_criteria: selectionCriteria,
        checklist_mode: 'custom',
        status: 'active',
      }).select('id').single()

      if (cErr) throw cErr

      // Insert campaign_equipment
      if (selectedEquipment.length > 0 && campaign) {
        const rows = selectedEquipment.map(eq => ({
          campaign_id: campaign.id,
          equipment_id: eq.id,
          selection_status: 'auto',
        }))

        // Batch insert (max 50 per call for safety)
        for (let i = 0; i < rows.length; i += 50) {
          const batch = rows.slice(i, i + 50)
          const { error: eErr } = await sb.from('campaign_equipment').insert(batch)
          if (eErr) throw eErr
        }
      }

      router.push(`/campaigns/${campaign.id}`)
    } catch (err) {
      console.error('Save error:', err)
      alert('Failed to create campaign. Check console for details.')
    } finally {
      setSaving(false)
    }
  }

  const dateError = startDate && endDate && endDate < startDate

  return (
    <AppLayout>
      <div className="p-6 max-w-3xl mx-auto">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <button onClick={() => router.push('/campaigns')} className="p-1 hover:bg-accent rounded">
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <h1 className="text-xl font-semibold">New Campaign</h1>
            <p className="text-sm text-muted-foreground">Create a thematic inspection campaign</p>
          </div>
        </div>

        {/* Basic Info */}
        <div className="rounded-xl border border-border bg-card p-5 mb-4">
          <h2 className="text-sm font-medium mb-4">Campaign Details</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium mb-1">Name *</label>
              <input
                type="text"
                value={name}
                onChange={e => setName(e.target.value)}
                placeholder="e.g. CUI Inspection 2026 Q3"
                className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">Description</label>
              <textarea
                value={description}
                onChange={e => setDescription(e.target.value)}
                placeholder="Optional description..."
                rows={2}
                className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm resize-none"
              />
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-medium mb-1">Type *</label>
                <select
                  value={campaignType}
                  onChange={e => setCampaignType(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm"
                >
                  {CAMPAIGN_TYPES.map(t => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium mb-1">Start Date *</label>
                <input
                  type="date"
                  value={startDate}
                  onChange={e => setStartDate(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium mb-1">End Date *</label>
                <input
                  type="date"
                  value={endDate}
                  onChange={e => setEndDate(e.target.value)}
                  className={cn(
                    'w-full px-3 py-2 rounded-lg border bg-background text-sm',
                    dateError ? 'border-red-500' : 'border-input'
                  )}
                />
                {dateError && <p className="text-xs text-red-500 mt-1">End date must be after start date</p>}
              </div>
            </div>
          </div>
        </div>

        {/* Filter Builder */}
        <div className="rounded-xl border border-border bg-card p-5 mb-4">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="flex items-center justify-between w-full"
          >
            <h2 className="text-sm font-medium">Selection Filters</h2>
            {showFilters ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>
          {showFilters && (
            <div className="mt-4 space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium mb-1">Area</label>
                  <select value={filterArea} onChange={e => setFilterArea(e.target.value)} className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm">
                    <option value="">All Areas</option>
                    {areas.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium mb-1">Equipment Type</label>
                  <select value={filterType} onChange={e => setFilterType(e.target.value)} className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm">
                    <option value="">All Types</option>
                    {EQUIPMENT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium mb-1">Insulation Type</label>
                  <select value={filterInsulation} onChange={e => setFilterInsulation(e.target.value)} className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm">
                    <option value="">Any Insulation</option>
                    {INSULATION_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium mb-1">Risk Category</label>
                  <select value={filterRisk} onChange={e => setFilterRisk(e.target.value)} className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm">
                    <option value="">All Risk</option>
                    {RISK_CATEGORIES.map(r => <option key={r} value={r}>{r}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium mb-1">Fluid Service</label>
                  <select value={filterFluid} onChange={e => setFilterFluid(e.target.value)} className="w-full px-3 py-2 rounded-lg border border-input bg-background text-sm">
                    <option value="">All Fluids</option>
                    {FLUID_SERVICES.map(f => <option key={f} value={f}>{f}</option>)}
                  </select>
                </div>
              </div>
              <button
                onClick={runPreview}
                className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 text-sm font-medium"
              >
                Preview Selection
              </button>
            </div>
          )}
        </div>

        {/* Preview Results */}
        {previewDone && (
          <div className="rounded-xl border border-border bg-card p-5 mb-4">
            <h2 className="text-sm font-medium mb-3">
              Preview — {suggested.length} equipment match{suggested.length !== 1 && 'es'}
            </h2>
            {suggested.length === 0 ? (
              <p className="text-sm text-muted-foreground">No equipment matches the current filters. Adjust filters or add equipment manually below.</p>
            ) : (
              <div className="max-h-64 overflow-y-auto">
                <table className="w-full text-sm">
                  <thead className="text-xs text-muted-foreground border-b">
                    <tr>
                      <th className="text-left py-2 pr-2">Tag</th>
                      <th className="text-left py-2 pr-2">Area</th>
                      <th className="text-left py-2 pr-2">Type</th>
                      <th className="text-center py-2">Include</th>
                    </tr>
                  </thead>
                  <tbody>
                    {suggested.map(eq => (
                      <tr key={eq.id} className={cn('border-b border-border/50', excluded.has(eq.id) && 'opacity-40')}>
                        <td className="py-1.5 pr-2 font-mono text-xs">{eq.tag}</td>
                        <td className="py-1.5 pr-2">{eq.area_name || '—'}</td>
                        <td className="py-1.5 pr-2">{eq.type}</td>
                        <td className="py-1.5 text-center">
                          <button onClick={() => toggleExclude(eq.id)} className={cn('p-0.5 rounded', excluded.has(eq.id) ? 'text-muted-foreground' : 'text-green-600')}>
                            {excluded.has(eq.id) ? <X className="h-4 w-4" /> : <Check className="h-4 w-4" />}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Manual add */}
            <div className="mt-4 pt-3 border-t border-border">
              <label className="block text-xs font-medium mb-1">Add Equipment Manually</label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                <input
                  type="text"
                  value={manualSearch}
                  onChange={e => setManualSearch(e.target.value)}
                  placeholder="Search by tag..."
                  className="w-full pl-9 pr-3 py-1.5 rounded-lg border border-input bg-background text-sm"
                />
              </div>
              {manualMatches.length > 0 && (
                <div className="mt-1 border border-border rounded-lg bg-background max-h-40 overflow-y-auto">
                  {manualMatches.map(eq => (
                    <button
                      key={eq.id}
                      onClick={() => addManual(eq)}
                      className="w-full text-left px-3 py-1.5 text-xs hover:bg-accent flex items-center justify-between"
                    >
                      <span className="font-mono">{eq.tag} — {eq.area_name || '—'} — {eq.type}</span>
                      <span className="text-muted-foreground text-[10px]">+ Add</span>
                    </button>
                  ))}
                </div>
              )}
              {added.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {added.map(eq => (
                    <span key={eq.id} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-blue-100 text-blue-800 text-xs dark:bg-blue-900/30 dark:text-blue-400">
                      {eq.tag}
                      <button onClick={() => removeManual(eq.id)} className="hover:text-red-500"><X className="h-3 w-3" /></button>
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Target + Save */}
        <div className="rounded-xl border border-border bg-card p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Target Count: {selectedEquipment.length}</p>
              <p className="text-xs text-muted-foreground">{selectedEquipment.filter(e => suggested.some(s => s.id === e.id)).length} suggested + {added.length} added − {excluded.size} excluded</p>
            </div>
            <div className="flex gap-2">
              <button onClick={() => router.push('/campaigns')} className="px-4 py-2 rounded-lg border border-input text-sm hover:bg-accent">Cancel</button>
              <button
                onClick={handleSave}
                disabled={!name.trim() || !startDate || !endDate || !!dateError || saving || selectedEquipment.length === 0}
                className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center gap-2"
              >
                {saving && <Loader2 className="h-4 w-4 animate-spin" />}
                Create Campaign
              </button>
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  )
}
