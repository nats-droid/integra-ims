'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase/client'
import type { Database } from '@/types/database'
import AppLayout from '@/components/layout/app-layout'
import { cn } from '@/utils/cn'
import { toast } from 'sonner'
import { ArrowLeft, Save, Loader2 } from 'lucide-react'

type PlantArea = Database['public']['Tables']['plant_areas']['Row']
type EquipmentInsert = Database['public']['Tables']['equipment']['Insert']

const EQUIPMENT_TYPES: { value: EquipmentInsert['type']; label: string }[] = [
  { value: 'piping', label: 'Piping' },
  { value: 'vessel', label: 'Vessel' },
  { value: 'tank', label: 'Tank' },
  { value: 'heater', label: 'Heater' },
  { value: 'pump', label: 'Pump' },
  { value: 'compressor', label: 'Compressor' },
  { value: 'valve', label: 'Valve' },
  { value: 'other', label: 'Other' },
]

const RISK_CATEGORIES: { value: 'low' | 'medium' | 'high' | 'critical'; label: string }[] = [
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
  { value: 'critical', label: 'Critical' },
]

interface FormData {
  tag: string
  type: EquipmentInsert['type']
  fluid_service: string
  material: string
  area_id: string
  risk_category: string
  compliance_status: EquipmentInsert['compliance_status']
  size_or_dimension: string
  insulation_type: string
  manufacturer: string
  serial_number: string
  notes: string
  design_temp_min: string
  design_temp_max: string
  design_pressure: string
  pwht: boolean
  installation_date: string
}

const initialFormData: FormData = {
  tag: '',
  type: 'other',
  fluid_service: '',
  material: '',
  area_id: '',
  risk_category: '',
  compliance_status: 'pending',
  size_or_dimension: '',
  insulation_type: '',
  manufacturer: '',
  serial_number: '',
  notes: '',
  design_temp_min: '',
  design_temp_max: '',
  design_pressure: '',
  pwht: false,
  installation_date: '',
}

export default function EquipmentNewPage() {
  const router = useRouter()
  const supabase = createClient()
  const sb = supabase as any

  const [areas, setAreas] = useState<PlantArea[]>([])
  const [form, setForm] = useState<FormData>(initialFormData)
  const [submitting, setSubmitting] = useState(false)
  const [companyId, setCompanyId] = useState<string | null>(null)

  useEffect(() => {
    async function loadData() {
      const {
        data: { user },
      } = await supabase.auth.getUser()
      if (!user) {
        toast.error('You must be logged in')
        router.push('/auth/login')
        return
      }

      const { data: appUser } = await sb
        .from('app_users')
        .select('*')
        .eq('auth_user_id', user.id)
        .single()

      const cId = (appUser as { company_id: string } | null)?.company_id
      if (!cId) {
        toast.error('No company found for your account')
        return
      }

      setCompanyId(cId)

      const { data: areaData } = await sb
        .from('plant_areas')
        .select('*')
        .eq('company_id', cId)
        .order('name')

      if (areaData) setAreas(areaData as PlantArea[])
    }

    loadData()
  }, [supabase, sb, router])

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>,
  ) => {
    const { name, value, type } = e.target
    if (type === 'checkbox') {
      const checked = (e.target as HTMLInputElement).checked
      setForm((prev) => ({ ...prev, [name]: checked }))
    } else {
      setForm((prev) => ({ ...prev, [name]: value }))
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!companyId) {
      toast.error('Company context not found')
      return
    }

    if (!form.tag.trim()) {
      toast.error('Tag is required')
      return
    }

    setSubmitting(true)

    try {
      const payload = {
        company_id: companyId,
        tag: form.tag.trim(),
        type: form.type,
        fluid_service: form.fluid_service || null,
        material: form.material || null,
        area_id: form.area_id || null,
        risk_category: form.risk_category || null,
        compliance_status: form.compliance_status,
        size_or_dimension: form.size_or_dimension || null,
        insulation_type: form.insulation_type || null,
        manufacturer: form.manufacturer || null,
        serial_number: form.serial_number || null,
        notes: form.notes || null,
        design_temp_min: form.design_temp_min ? parseFloat(form.design_temp_min) : null,
        design_temp_max: form.design_temp_max ? parseFloat(form.design_temp_max) : null,
        design_pressure: form.design_pressure ? parseFloat(form.design_pressure) : null,
        pwht: form.pwht,
        installation_date: form.installation_date || null,
        is_active: true,
      }

      const { data, error } = await sb
        .from('equipment')
        .insert(payload)
        .select('id')
        .single()

      if (error) {
        console.error('Insert error:', error)
        toast.error(error.message || 'Failed to create equipment')
        return
      }

      const result = data as { id: string }
      toast.success('Equipment created successfully')
      router.push(`/equipment/${result.id}`)
    } catch (err) {
      console.error('Submit error:', err)
      toast.error('Unexpected error creating equipment')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AppLayout>
      <div className="space-y-6 max-w-3xl">
        {/* Header */}
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.back()}
            className="inline-flex items-center justify-center rounded-lg border border-border p-2 text-muted-foreground hover:bg-accent transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          <div>
            <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight">Add Equipment</h1>
            <p className="text-sm text-muted-foreground">
              Register new equipment in your plant
            </p>
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Basic Information */}
          <section className="rounded-xl border border-border/70 p-6 space-y-4">
            <h2 className="text-lg font-semibold">Basic Information</h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-sm font-medium">
                  Tag <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  name="tag"
                  value={form.tag}
                  onChange={handleChange}
                  placeholder="e.g., V-101"
                  required
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-medium">Type</label>
                <select
                  name="type"
                  value={form.type}
                  onChange={handleChange}
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
                >
                  {EQUIPMENT_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-medium">Fluid Service</label>
                <input
                  type="text"
                  name="fluid_service"
                  value={form.fluid_service}
                  onChange={handleChange}
                  placeholder="e.g., Hydrocarbon, Steam, Water"
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-medium">Material</label>
                <input
                  type="text"
                  name="material"
                  value={form.material}
                  onChange={handleChange}
                  placeholder="e.g., CS, SS316, SA-516 Gr.70"
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-medium">Area</label>
                <select
                  name="area_id"
                  value={form.area_id}
                  onChange={handleChange}
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
                >
                  <option value="">Select area...</option>
                  {areas.map((area) => (
                    <option key={area.id} value={area.id}>
                      {area.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-medium">Risk Category</label>
                <select
                  name="risk_category"
                  value={form.risk_category || ''}
                  onChange={handleChange}
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
                >
                  <option value="">Select risk...</option>
                  {RISK_CATEGORIES.map((rc) => (
                    <option key={rc.value} value={rc.value}>
                      {rc.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-medium">Compliance Status</label>
                <select
                  name="compliance_status"
                  value={form.compliance_status}
                  onChange={handleChange}
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
                >
                  <option value="compliant">Compliant</option>
                  <option value="non-compliant">Non-Compliant</option>
                  <option value="pending">Pending</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-medium">Installation Date</label>
                <input
                  type="date"
                  name="installation_date"
                  value={form.installation_date}
                  onChange={handleChange}
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
                />
              </div>
            </div>
          </section>

          {/* Design Specifications */}
          <section className="rounded-xl border border-border/70 p-6 space-y-4">
            <h2 className="text-lg font-semibold">Design Specifications</h2>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-1.5">
                <label className="text-sm font-medium">Design Temp Min (°C)</label>
                <input
                  type="number"
                  name="design_temp_min"
                  value={form.design_temp_min}
                  onChange={handleChange}
                  placeholder="e.g., -10"
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-medium">Design Temp Max (°C)</label>
                <input
                  type="number"
                  name="design_temp_max"
                  value={form.design_temp_max}
                  onChange={handleChange}
                  placeholder="e.g., 350"
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-medium">Design Pressure (bar)</label>
                <input
                  type="number"
                  name="design_pressure"
                  value={form.design_pressure}
                  onChange={handleChange}
                  placeholder="e.g., 15.5"
                  step="0.1"
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
                />
              </div>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                name="pwht"
                id="pwht"
                checked={form.pwht}
                onChange={handleChange}
                className="h-4 w-4 rounded border-border text-primary focus:ring-primary/30"
              />
              <label htmlFor="pwht" className="text-sm font-medium">
                Post-Weld Heat Treatment (PWHT)
              </label>
            </div>
          </section>

          {/* Physical & Manufacturing */}
          <section className="rounded-xl border border-border/70 p-6 space-y-4">
            <h2 className="text-lg font-semibold">Physical &amp; Manufacturing</h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-sm font-medium">Size / Dimension</label>
                <input
                  type="text"
                  name="size_or_dimension"
                  value={form.size_or_dimension}
                  onChange={handleChange}
                  placeholder='e.g., 24" x 12" x 10mm'
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-medium">Insulation Type</label>
                <input
                  type="text"
                  name="insulation_type"
                  value={form.insulation_type}
                  onChange={handleChange}
                  placeholder="e.g., Mineral Wool, CWI"
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-medium">Manufacturer</label>
                <input
                  type="text"
                  name="manufacturer"
                  value={form.manufacturer}
                  onChange={handleChange}
                  placeholder="e.g., Babcock & Wilcox"
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-medium">Serial Number</label>
                <input
                  type="text"
                  name="serial_number"
                  value={form.serial_number}
                  onChange={handleChange}
                  placeholder="e.g., SN-2024-001"
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
                />
              </div>
            </div>
          </section>

          {/* Notes */}
          <section className="rounded-xl border border-border/70 p-6 space-y-4">
            <h2 className="text-lg font-semibold">Notes</h2>

            <div className="space-y-1.5">
              <textarea
                name="notes"
                value={form.notes}
                onChange={handleChange}
                rows={4}
                placeholder="Additional notes about this equipment..."
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 resize-y"
              />
            </div>
          </section>

          {/* Submit */}
          <div className="flex items-center gap-3 pb-8">
            <button
              type="submit"
              disabled={submitting}
              className="inline-flex items-center gap-2 rounded-lg bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {submitting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Save className="h-4 w-4" />
              )}
              {submitting ? 'Saving...' : 'Save Equipment'}
            </button>
            <button
              type="button"
              onClick={() => router.back()}
              className="rounded-lg border border-border px-6 py-2.5 text-sm font-medium text-muted-foreground hover:bg-accent transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </AppLayout>
  )
}
