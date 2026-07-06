'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { createClient } from '@/lib/supabase/client'
import AppLayout from '@/components/layout/app-layout'
import {
  ArrowLeft,
  Calendar,
  Target,
  Trash2,
  AlertTriangle,
  X,
} from 'lucide-react'

interface Campaign {
  id: string
  company_id: string
  name: string
  description: string | null
  campaign_type: string
  start_date: string
  end_date: string
  target_count: number
  selection_criteria: Record<string, unknown>
  checklist_mode: string
  status: string
  created_at: string
}

interface CampaignEquipmentRow {
  id: string
  equipment_id: string
  selection_status: string
  inspection_event_id: string | null
  tag: string
  type: string
  area_name: string
}

const TYPE_LABELS: Record<string, string> = { cui: 'CUI', general: 'General', other: 'Other' }
const TYPE_COLORS: Record<string, string> = {
  cui: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  general: 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400',
  other: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400',
}

function getDateStatus(start: string, end: string): { label: string; color: string } {
  const today = new Date(); today.setHours(0,0,0,0)
  const s = new Date(start); s.setHours(0,0,0,0)
  const e = new Date(end); e.setHours(0,0,0,0)
  if (s > today) return { label: 'Upcoming', color: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300' }
  if (e < today) return { label: 'Ended', color: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400' }
  return { label: 'Active', color: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' }
}

function readableCriteria(criteria: Record<string, unknown>): string[] {
  const parts: string[] = []
  if (criteria.area_id) parts.push(`Area: ${criteria.area_id}`)
  if (criteria.type) parts.push(`Type: ${criteria.type}`)
  if (criteria.insulation_type) parts.push(`Insulation: ${criteria.insulation_type}`)
  if (criteria.risk_category) parts.push(`Risk: ${criteria.risk_category}`)
  if (criteria.fluid_service) parts.push(`Fluid: ${criteria.fluid_service}`)
  return parts
}

export default function CampaignDetailPage() {
  const router = useRouter()
  const params = useParams()
  const campaignId = params.id as string

  const [campaign, setCampaign] = useState<Campaign | null>(null)
  const [equipment, setEquipment] = useState<CampaignEquipmentRow[]>([])
  const [loading, setLoading] = useState(true)
  const [userRole, setUserRole] = useState<string | null>(null)
  const [showDelete, setShowDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      const supabase = createClient()
      const sb = supabase as any
      const DEMO_USER = {
        id: '3fca82af-b302-4d1e-8536-b89546ecfb15',
        company_id: 'c704d7e6-07fb-48a2-9152-564434d8653f',
        full_name: 'Dicki Wiryawan',
        role: 'super_admin',
      }
      const { data: appUser } = { data: DEMO_USER }
      if (!appUser?.company_id) return
      setUserRole(appUser.role)

      const { data: camp } = await sb.from('inspection_campaigns').select('*').eq('id', campaignId).single()
      if (!camp) { setLoading(false); return }
      setCampaign(camp)

      // Get campaign_equipment with joined data
      const { data: ceData } = await sb.from('campaign_equipment')
        .select('id, equipment_id, selection_status, inspection_event_id')
        .eq('campaign_id', campaignId)

      if (ceData && ceData.length > 0) {
        const eqIds = ceData.map((r: { equipment_id: string }) => r.equipment_id)
        const { data: eqData } = await sb.from('equipment')
          .select('id, tag, type, area_id')
          .in('id', eqIds)

        const { data: areaData } = await sb.from('plant_areas').select('id, name').eq('company_id', appUser.company_id)
        const areaMap: Map<string, string> = new Map((areaData || []).map((a: { id: string; name: string }) => [a.id, a.name] as const))
        const eqMap: Map<string, { id: string; tag: string; type: string; area_id: string }> = new Map((eqData || []).map((e: { id: string; tag: string; type: string; area_id: string }) => [e.id, e] as const))

        const rows: CampaignEquipmentRow[] = ceData.map((ce: { id: string; equipment_id: string; selection_status: string; inspection_event_id: string | null }) => {
          const eq = eqMap.get(ce.equipment_id)
          return {
            id: ce.id,
            equipment_id: ce.equipment_id,
            selection_status: ce.selection_status,
            inspection_event_id: ce.inspection_event_id,
            tag: eq?.tag || '—',
            type: eq?.type || '—',
            area_name: areaMap.get(eq?.area_id || '') || '—',
          }
        })
        setEquipment(rows)
      }
    } catch (err) {
      console.error('Error fetching campaign:', err)
    } finally {
      setLoading(false)
    }
  }, [campaignId])

  useEffect(() => { fetchData() }, [fetchData])

  const handleDelete = async () => {
    setDeleting(true)
    try {
      const supabase = createClient()
      const sb = supabase as any

      // Delete campaign_equipment first
      await sb.from('campaign_equipment').delete().eq('campaign_id', campaignId)
      // Delete campaign
      await sb.from('inspection_campaigns').delete().eq('id', campaignId)

      router.push('/campaigns')
    } catch (err) {
      console.error('Delete error:', err)
      alert('Failed to delete campaign.')
      setDeleting(false)
      setShowDelete(false)
    }
  }

  const canDelete = userRole === 'engineer' || userRole === 'supervisor' || userRole === 'super_admin'

  if (loading) {
    return (
      <AppLayout>
        <div className="p-6">
          <div className="h-8 w-48 rounded bg-card animate-pulse mb-4" />
          <div className="h-64 rounded-xl border border-border bg-card animate-pulse" />
        </div>
      </AppLayout>
    )
  }

  if (!campaign) {
    return (
      <AppLayout>
        <div className="p-6 text-center">
          <p className="text-muted-foreground">Campaign not found.</p>
          <button onClick={() => router.push('/campaigns')} className="mt-2 text-sm text-primary hover:underline">Back to campaigns</button>
        </div>
      </AppLayout>
    )
  }

  const dateStatus = getDateStatus(campaign.start_date, campaign.end_date)
  const completedCount = equipment.filter(e => e.inspection_event_id).length
  const progress = campaign.target_count > 0 ? Math.round((completedCount / campaign.target_count) * 100) : 0
  const startDate = new Date(campaign.start_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  const endDate = new Date(campaign.end_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  const criteria = readableCriteria(campaign.selection_criteria || {})

  return (
    <AppLayout>
      <div className="p-6 max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <button onClick={() => router.push('/campaigns')} className="p-1 hover:bg-accent rounded">
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-semibold">{campaign.name}</h1>
              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${TYPE_COLORS[campaign.campaign_type] || TYPE_COLORS.other}`}>
                {TYPE_LABELS[campaign.campaign_type] || campaign.campaign_type}
              </span>
              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${dateStatus.color}`}>
                {dateStatus.label}
              </span>
            </div>
            <p className="text-sm text-muted-foreground mt-0.5">
              <Calendar className="inline h-3 w-3 mr-1" />
              {startDate} — {endDate}
            </p>
          </div>
          {canDelete && (
            <button
              onClick={() => setShowDelete(true)}
              className="px-3 py-2 rounded-lg border border-red-300 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 text-sm inline-flex items-center gap-2"
            >
              <Trash2 className="h-4 w-4" /> Delete
            </button>
          )}
        </div>

        {/* Info Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1"><Target className="h-3 w-3" /> Progress</div>
            <div className="flex items-center gap-3">
              <div className="flex-1 h-2.5 rounded-full bg-secondary overflow-hidden">
                <div className={`h-full rounded-full transition-all ${progress >= 100 ? 'bg-green-500' : progress > 0 ? 'bg-blue-500' : 'bg-gray-300'}`} style={{ width: `${Math.min(progress, 100)}%` }} />
              </div>
              <span className="text-sm font-medium">{progress}%</span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">{completedCount} of {campaign.target_count} inspected</p>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs text-muted-foreground mb-1">Description</p>
            <p className="text-sm">{campaign.description || '—'}</p>
          </div>
          <div className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs text-muted-foreground mb-1">Selection Criteria</p>
            {criteria.length > 0 ? (
              <ul className="text-xs space-y-0.5">
                {criteria.map((c, i) => <li key={i}>{c}</li>)}
              </ul>
            ) : (
              <p className="text-xs text-muted-foreground">Manual selection (no filters)</p>
            )}
          </div>
        </div>

        {/* Equipment Table */}
        <div className="rounded-xl border border-border bg-card overflow-hidden">
          <div className="px-5 py-3 border-b border-border">
            <h2 className="text-sm font-medium">Campaign Equipment ({equipment.length})</h2>
          </div>
          {equipment.length === 0 ? (
            <div className="p-8 text-center text-sm text-muted-foreground">No equipment linked.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/50">
                  <tr className="text-xs text-muted-foreground">
                    <th className="text-left px-5 py-2.5 font-medium">Tag</th>
                    <th className="text-left px-5 py-2.5 font-medium">Area</th>
                    <th className="text-left px-5 py-2.5 font-medium">Type</th>
                    <th className="text-left px-5 py-2.5 font-medium">Selection</th>
                    <th className="text-left px-5 py-2.5 font-medium">Inspection</th>
                  </tr>
                </thead>
                <tbody>
                  {equipment.map(eq => (
                    <tr key={eq.id} className="border-t border-border/50 hover:bg-accent/50">
                      <td className="px-5 py-2.5 font-mono text-xs">{eq.tag}</td>
                      <td className="px-5 py-2.5">{eq.area_name}</td>
                      <td className="px-5 py-2.5">{eq.type}</td>
                      <td className="px-5 py-2.5">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                          'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300'
                        }`}>
                          {eq.selection_status}
                        </span>
                      </td>
                      <td className="px-5 py-2.5">
                        {eq.inspection_event_id ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">
                            Done
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400">
                            Not Started
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Delete Dialog */}
        {showDelete && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => !deleting && setShowDelete(false)}>
            <div className="bg-card rounded-xl border border-border p-6 max-w-md w-full mx-4" onClick={e => e.stopPropagation()}>
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 rounded-full bg-red-100 dark:bg-red-900/30">
                  <AlertTriangle className="h-5 w-5 text-red-600" />
                </div>
                <div>
                  <h3 className="font-medium">Delete Campaign</h3>
                  <p className="text-sm text-muted-foreground">This action cannot be undone.</p>
                </div>
              </div>
              <p className="text-sm mb-4">
                Deletes campaign and equipment links. Inspection events are <strong>NOT</strong> deleted.
              </p>
              <div className="flex justify-end gap-2">
                <button onClick={() => setShowDelete(false)} disabled={deleting} className="px-4 py-2 rounded-lg border border-input text-sm hover:bg-accent disabled:opacity-50">Cancel</button>
                <button onClick={handleDelete} disabled={deleting} className="px-4 py-2 rounded-lg bg-red-600 text-white text-sm hover:bg-red-700 disabled:opacity-50 inline-flex items-center gap-2">
                  {deleting ? 'Deleting...' : 'Delete Campaign'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  )
}
