'use client'
export const dynamic = 'force-dynamic'

import { createClient } from '@/lib/supabase/client'
import { useEffect, useState } from 'react'

interface KPI {
  label: string
  value: string | number
  subtext?: string
  color?: string
}

export default function DashboardPage() {
  const [kpis, setKpis] = useState<KPI[]>([])
  const [loading, setLoading] = useState(true)
  const supabase = createClient()

  useEffect(() => {
    async function loadKPI() {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) return

      const { data: appUser } = await supabase
        .from('app_users')
        .select('company_id')
        .eq('auth_user_id', user.id)
        .maybeSingle() as unknown as { data: { company_id: string } | null }

      if (!appUser?.company_id) {
        setLoading(false)
        return
      }

      const companyId = appUser.company_id

      // Fetch data — wrapped to handle missing Supabase config gracefully
      const fetchCount = async (table: string, filters: Record<string, any> = {}) => {
        try {
          let query = supabase.from(table as any).select('id', { count: 'exact', head: true } as any)
          for (const [key, val] of Object.entries(filters)) {
            query = (query as any).eq(key, val)
          }
          return (await query).count ?? 0
        } catch {
          return 0
        }
      }

      const [equipResult, plansPending, plansActive, cmResult] = await Promise.all([
        fetchCount('equipment', { company_id: companyId }),
        fetchCount('inspection_plans', { company_id: companyId, approval_status: 'pending' }),
        fetchCount('inspection_plans', { company_id: companyId, approval_status: 'approved' }),
        fetchCount('cml_points', { company_id: companyId }),
      ])

      setKpis([
        { label: 'Total Equipment', value: equipResult, color: 'blue' },
        { label: 'Total CML Points', value: cmResult, color: 'indigo' },
        { label: 'Pending Approval', value: plansPending, color: 'amber' },
        { label: 'Active Plans', value: plansActive, color: 'green' },
      ])
      setLoading(false)
    }
    loadKPI()
  }, [supabase])

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-xl font-semibold">Dashboard</h1>
        <p className="text-sm text-muted-foreground">Asset inspection & integrity overview</p>
      </div>

      {/* KPI Cards */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="h-24 bg-card border border-border rounded-lg animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {kpis.map((kpi) => (
            <div key={kpi.label} className="bg-card border border-border rounded-lg p-4">
              <p className="text-sm text-muted-foreground">{kpi.label}</p>
              <p className="text-2xl font-bold mt-1">{kpi.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Placeholder sections */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-card border border-border rounded-lg p-6">
          <h2 className="text-sm font-medium mb-4">Quick Actions</h2>
          <div className="space-y-2">
            <button className="w-full text-left px-3 py-2 rounded-md text-sm hover:bg-accent transition-colors">
              ➕ New Equipment
            </button>
            <button className="w-full text-left px-3 py-2 rounded-md text-sm hover:bg-accent transition-colors">
              📋 New Inspection
            </button>
            <button className="w-full text-left px-3 py-2 rounded-md text-sm hover:bg-accent transition-colors">
              📅 View Approval Schedule
            </button>
          </div>
        </div>

        <div className="bg-card border border-border rounded-lg p-6">
          <h2 className="text-sm font-medium mb-4">Status Overview</h2>
          <div className="space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Equipment Aktif</span>
              <span className="font-medium">—</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Non-Compliant</span>
              <span className="font-medium">—</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Overdue Inspection</span>
              <span className="font-medium">—</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
