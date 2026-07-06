'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase/client'
import AppLayout from '@/components/layout/app-layout'
import {
  Plus,
  ChevronRight,
  Search,
  Calendar,
  Target,
  Layers,
  Activity,
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

interface CampaignWithProgress extends Campaign {
  completed_count: number
}

const TYPE_COLORS: Record<string, string> = {
  cui: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  general: 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400',
  other: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400',
}

const TYPE_LABELS: Record<string, string> = {
  cui: 'CUI',
  general: 'General',
  other: 'Other',
}

function getDateStatus(start: string, end: string): { label: string; color: string } {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const startDate = new Date(start)
  startDate.setHours(0, 0, 0, 0)
  const endDate = new Date(end)
  endDate.setHours(0, 0, 0, 0)

  if (startDate > today) {
    return { label: 'Upcoming', color: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300' }
  }
  if (endDate < today) {
    return { label: 'Ended', color: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400' }
  }
  return { label: 'Active', color: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' }
}

export default function CampaignsPage() {
  const router = useRouter()
  const [campaigns, setCampaigns] = useState<CampaignWithProgress[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [userRole, setUserRole] = useState<string | null>(null)

  const fetchCampaigns = useCallback(async () => {
    try {
      setLoading(true)
      const supabase = createClient()
      const sb = supabase as any

      const { data: { user } } = await supabase.auth.getUser()
      if (!user) { setCampaigns([]); return }

      const { data: appUser } = await sb.from('app_users').select('company_id, role').eq('auth_user_id', user.id).single()
      if (!appUser?.company_id) { setCampaigns([]); return }
      setUserRole(appUser.role)

      const { data: campaignData } = await sb
        .from('inspection_campaigns')
        .select('*')
        .eq('company_id', appUser.company_id)
        .order('created_at', { ascending: false })

      if (!campaignData || campaignData.length === 0) {
        setCampaigns([])
        return
      }

      // Get progress: count completed equipment per campaign
      const campaignIds = campaignData.map((c: Campaign) => c.id)
      const { data: eqData } = await sb
        .from('campaign_equipment')
        .select('campaign_id, inspection_event_id')
        .in('campaign_id', campaignIds)

      const progressMap: Record<string, number> = {}
      if (eqData) {
        for (const eq of eqData) {
          if (eq.inspection_event_id) {
            progressMap[eq.campaign_id] = (progressMap[eq.campaign_id] || 0) + 1
          }
        }
      }

      const result: CampaignWithProgress[] = campaignData.map((c: Campaign) => ({
        ...c,
        completed_count: progressMap[c.id] || 0,
      }))

      setCampaigns(result)
    } catch (err) {
      console.error('Error fetching campaigns:', err)
      setCampaigns([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchCampaigns() }, [fetchCampaigns])

  const canCreate = userRole === 'engineer' || userRole === 'supervisor' || userRole === 'super_admin'

  const filtered = campaigns.filter(c =>
    c.name.toLowerCase().includes(search.toLowerCase()) ||
    (c.description || '').toLowerCase().includes(search.toLowerCase())
  )

  return (
    <AppLayout>
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-xl font-semibold">Campaigns</h1>
            <p className="text-sm text-muted-foreground">Thematic inspections (CUI, Turn Around, etc.)</p>
          </div>
          {canCreate && (
            <button
              onClick={() => router.push('/campaigns/new')}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors text-sm font-medium"
            >
              <Plus className="h-4 w-4" />
              New Campaign
            </button>
          )}
        </div>

        {/* Search */}
        <div className="relative mb-4">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search campaigns..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 rounded-lg border border-input bg-background text-sm"
          />
        </div>

        {/* List */}
        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-24 rounded-xl border border-border bg-card animate-pulse" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="rounded-xl border border-border bg-card p-8 text-center">
            <Layers className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              {search ? 'No campaigns match your search' : 'No campaigns yet'}
            </p>
            {canCreate && !search && (
              <button
                onClick={() => router.push('/campaigns/new')}
                className="mt-3 inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 text-sm"
              >
                <Plus className="h-4 w-4" /> Create First Campaign
              </button>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            {filtered.map(c => {
              const dateStatus = getDateStatus(c.start_date, c.end_date)
              const progress = c.target_count > 0 ? Math.round((c.completed_count / c.target_count) * 100) : 0
              const startDate = new Date(c.start_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
              const endDate = new Date(c.end_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })

              return (
                <div
                  key={c.id}
                  onClick={() => router.push(`/campaigns/${c.id}`)}
                  className="rounded-xl border border-border bg-card p-5 hover:bg-accent/50 cursor-pointer transition-colors"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-medium text-sm truncate">{c.name}</h3>
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${TYPE_COLORS[c.campaign_type] || TYPE_COLORS.other}`}>
                          {TYPE_LABELS[c.campaign_type] || c.campaign_type}
                        </span>
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${dateStatus.color}`}>
                          {dateStatus.label}
                        </span>
                      </div>
                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        <span className="inline-flex items-center gap-1">
                          <Calendar className="h-3 w-3" />
                          {startDate} — {endDate}
                        </span>
                        <span className="inline-flex items-center gap-1">
                          <Target className="h-3 w-3" />
                          {c.target_count} target
                        </span>
                      </div>
                      {/* Progress bar */}
                      <div className="mt-3 flex items-center gap-3">
                        <div className="flex-1 h-2 rounded-full bg-secondary overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all ${progress >= 100 ? 'bg-green-500' : progress > 0 ? 'bg-blue-500' : 'bg-gray-300'}`}
                            style={{ width: `${Math.min(progress, 100)}%` }}
                          />
                        </div>
                        <span className="text-xs text-muted-foreground w-10 text-right">{progress}%</span>
                      </div>
                    </div>
                    <ChevronRight className="h-4 w-4 text-muted-foreground flex-shrink-0 mt-1" />
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </AppLayout>
  )
}
