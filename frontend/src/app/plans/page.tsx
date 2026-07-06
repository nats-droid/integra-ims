'use client'
export const dynamic = 'force-dynamic'

import { useEffect, useState, useMemo, useRef, useCallback } from 'react'
import { createClient } from '@/lib/supabase/client'
import type { Database } from '@/types/database'
import AppLayout from '@/components/layout/app-layout'
import { cn } from '@/utils/cn'
import { toast } from 'sonner'
import {
  Search,
  AlertTriangle,
  CheckCircle,
  XCircle,
  RefreshCw,
  Calendar,
  Hourglass,
  ChevronRight,
  X,
  Clock,
  ShieldAlert,
  ClipboardList,
  Loader2,
  Eye,
} from 'lucide-react'

type InspectionPlan = Database['public']['Tables']['inspection_plans']['Row']
type Equipment = Database['public']['Tables']['equipment']['Row']
type AppUser = Database['public']['Tables']['app_users']['Row']

type PlanApprovalStatus = 'pending' | 'approved' | 'rejected' | 'revised'

interface PlanRow {
  id: string
  equipment_id: string
  equipment_tag: string
  equipment_type: string
  risk_category: string | null
  inspection_type: string
  remaining_life_date: string | null
  rbi_date_manual: string | null
  disnaker_date: string | null
  final_due_date: string | null
  approval_status: PlanApprovalStatus
  approved_by: string | null
  approved_by_name: string | null
  approved_at: string | null
  approval_comment: string | null
  equipment_material: string | null
  equipment_fluid: string | null
}

const STATUS_CONFIG: Record<string, { label: string; className: string }> = {
  pending: {
    label: 'Pending',
    className: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  },
  approved: {
    label: 'Approved',
    className: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  },
  rejected: {
    label: 'Rejected',
    className: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  },
  revised: {
    label: 'Revised',
    className: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  },
}

const RISK_CONFIG: Record<string, { className: string }> = {
  critical: { className: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' },
  high: { className: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400' },
  medium: { className: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400' },
  low: { className: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' },
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—'
  try {
    const d = new Date(dateStr)
    return d.toLocaleDateString('en-GB', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    })
  } catch {
    return '—'
  }
}

function isCappedDate(dateStr: string | null): boolean {
  if (!dateStr) return false
  try {
    const capDate = new Date()
    capDate.setFullYear(capDate.getFullYear() + 30)
    const d = new Date(dateStr)
    return d.getFullYear() === capDate.getFullYear() && d >= capDate
  } catch {
    return false
  }
}

function formatRemainingLifeDate(dateStr: string | null): { display: string; capped: boolean } {
  if (!dateStr) return { display: '—', capped: false }
  if (isCappedDate(dateStr)) return { display: '30+ years', capped: true }
  return { display: formatDate(dateStr), capped: false }
}

function formatDateInput(dateStr: string | null): string {
  if (!dateStr) return ''
  try {
    const d = new Date(dateStr)
    return d.toISOString().split('T')[0]
  } catch {
    return ''
  }
}

function computeFinalDueDate(
  remaining_life_date: string | null,
  rbi_date_manual: string | null,
  disnaker_date: string | null,
): string | null {
  const dates = [remaining_life_date, rbi_date_manual, disnaker_date]
    .filter((d): d is string => d !== null && d !== '')
    .map((d) => new Date(d).getTime())
  if (dates.length === 0) return null
  return new Date(Math.min(...dates)).toISOString().split('T')[0]
}

/** ── Side Panel ──────────────────────────────────────────── */
interface SidePanelProps {
  plan: PlanRow | null
  open: boolean
  onClose: () => void
  userId: string | null
  onUpdate: (planId: string, updates: Partial<PlanRow>) => void
  initialAction?: 'approved' | 'rejected' | 'revised' | null
}

function PlanSidePanel({ plan, open, onClose, userId, onUpdate, initialAction }: SidePanelProps) {
  const [comment, setComment] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [action, setAction] = useState<'approved' | 'rejected' | 'revised' | null>(initialAction || null)
  const sb = (createClient() as any)

  useEffect(() => {
    if (open) {
      setComment('')
      setError('')
      setAction(null)
      setSubmitting(false)
    }
  }, [open])

  if (!open || !plan) return null

  const isPending = plan.approval_status === 'pending'
  const dateLabels = [
    {
      key: 'Remaining Life' as const,
      field: 'remaining_life_date' as const,
      value: plan.remaining_life_date,
      editable: false,
    },
    {
      key: 'RBI Date (Manual)' as const,
      field: 'rbi_date_manual' as const,
      value: plan.rbi_date_manual,
      editable: true,
    },
    {
      key: 'DISNAKER Date' as const,
      field: 'disnaker_date' as const,
      value: plan.disnaker_date,
      editable: true,
    },
  ]

  // Most urgent logic
  const dateEntries = dateLabels
    .map((d) => ({ label: d.key, field: d.field, value: d.value }))
    .filter((d) => d.value !== null && d.value !== '')

  const earliestLabel = (() => {
    if (dateEntries.length === 0) return null
    if (dateEntries.length === 1) return dateEntries[0].label
    const sorted = [...dateEntries].sort(
      (a, b) => new Date(a.value!).getTime() - new Date(b.value!).getTime(),
    )
    return sorted[0].label
  })()

  // Handle inline RBI/Disnaker date edit
  const handleInlineDate = async (field: 'rbi_date_manual' | 'disnaker_date', value: string) => {
    const oldValue = plan[field]
    const newFinalDue = computeFinalDueDate(
      plan.remaining_life_date,
      field === 'rbi_date_manual' ? value : plan.rbi_date_manual,
      field === 'disnaker_date' ? value : plan.disnaker_date,
    )

    // Optimistic update
    onUpdate(plan.id, { [field]: value || null, final_due_date: newFinalDue } as any)

    try {
      const payload: Record<string, any> = { [field]: value || null }
      if (newFinalDue !== plan.final_due_date) payload.final_due_date = newFinalDue

      const { error } = await sb
        .from('inspection_plans')
        .update(payload)
        .eq('id', plan.id)

      if (error) {
        onUpdate(plan.id, { [field]: oldValue, final_due_date: plan.final_due_date } as any)
        toast.error(error.message || 'Failed to save date')
      } else {
        toast.success('Date saved successfully.')
      }
    } catch {
      onUpdate(plan.id, { [field]: oldValue, final_due_date: plan.final_due_date } as any)
      toast.error('Failed to save date')
    }
  }

  // 1-click approve direct (without comment)
  const handleApproveInside = async () => {
    setSubmitting(true)
    try {
      const { error } = await sb
        .from('inspection_plans')
        .update({
          approval_status: 'approved',
          approved_by: userId,
          approved_at: new Date().toISOString(),
        })
        .eq('id', plan.id)

      if (error) throw error

      onUpdate(plan.id, {
        approval_status: 'approved',
        approved_by: userId,
        approved_by_name: null,
        approved_at: new Date().toISOString(),
        approval_comment: null,
      } as any)

      toast.success('Plan approved successfully.')
      onClose()
    } catch (err: any) {
      toast.error(err.message || 'Failed to approve')
    } finally {
      setSubmitting(false)
    }
  }

  // Submit approval (Reject/Revise with comment)
  const handleSubmit = async () => {
    if (!action) return
    if ((action === 'rejected' || action === 'revised') && !comment.trim()) {
      setError('Reason/comment is required.')
      return
    }
    setError('')
    setSubmitting(true)

    try {
      if (action === 'approved') {
        const { error } = await sb
          .from('inspection_plans')
          .update({
            approval_status: 'approved',
            approved_by: userId,
            approved_at: new Date().toISOString(),
          })
          .eq('id', plan.id)

        if (error) throw error

        onUpdate(plan.id, {
          approval_status: 'approved',
          approved_by: userId,
          approved_by_name: null,
          approved_at: new Date().toISOString(),
          approval_comment: null,
        } as any)

        toast.success('Plan approved successfully.')
        onClose()
      } else {
        const newStatus = action
        const { error } = await sb
          .from('inspection_plans')
          .update({
            approval_status: newStatus,
            approval_comment: comment.trim(),
            approved_by: userId,
            approved_at: new Date().toISOString(),
          })
          .eq('id', plan.id)

        if (error) throw error

        onUpdate(plan.id, {
          approval_status: newStatus,
          approval_comment: comment.trim(),
          approved_by: userId,
          approved_by_name: null,
          approved_at: new Date().toISOString(),
        } as any)

        toast.success(newStatus === 'rejected' ? 'Plan rejected.' : 'Plan revised.')
        onClose()
      }
    } catch (err: any) {
      toast.error(err.message || 'Failed to update status')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex">
      {/* Backdrop */}
      <div className="flex-1 bg-black/30" onClick={onClose} />

      {/* Panel */}
      <div className="w-full max-w-2xl bg-card border-l border-border shadow-2xl overflow-y-auto animate-in slide-in-from-right">
        {/* Header */}
        <div className="sticky top-0 bg-card border-b border-border z-10">
          <div className="flex items-center justify-between px-6 py-4">
            <div>
              <h2 className="text-lg font-semibold">{plan.equipment_tag}</h2>
              <p className="text-xs text-muted-foreground capitalize">
                {plan.inspection_type} inspection · {plan.equipment_type}
              </p>
            </div>
            <button
              onClick={onClose}
              className="rounded-lg p-1.5 text-muted-foreground hover:bg-accent transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        <div className="p-6 space-y-6">
          {/* ── 3 Date Cards Side-by-Side ── */}
          <div>
            <h3 className="text-sm font-medium mb-3">Due Date Comparison</h3>
            <div className="grid grid-cols-3 gap-3">
              {dateLabels.map((item) => {
                const isEarliest = earliestLabel === item.key
                const isEmpty = !item.value

                return (
                  <div
                    key={item.key}
                    className={cn(
                      'rounded-xl border p-4 relative',
                      isEarliest && !isEmpty
                        ? 'border-red-300 dark:border-red-700 bg-red-50 dark:bg-red-900/10'
                        : 'border-border/70',
                    )}
                  >
                    {/* Label */}
                    <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">
                      {item.key}
                    </p>

                    {/* Value or Input */}
                    {isEmpty ? (
                      <p className="text-xs text-muted-foreground italic">— Not filled</p>
                    ) : item.editable && isPending ? (
                      <input
                        type="date"
                        defaultValue={formatDateInput(item.value)}
                        onBlur={(e) => {
                          // item.field is always editable here (guarded by item.editable)
                          handleInlineDate(item.field as 'rbi_date_manual' | 'disnaker_date', e.target.value)
                        }}
                        className="w-full rounded-md border border-border bg-background px-2 py-1 text-xs font-mono focus:outline-none focus:ring-1 focus:ring-primary"
                      />
                    ) : (
                      <p className="text-sm font-mono font-medium tabular-nums">
                        {item.field === 'remaining_life_date'
                          ? formatRemainingLifeDate(item.value).display
                          : formatDate(item.value)}
                      </p>
                    )}

                    {/* Most urgent badge */}
                    {isEarliest && !isEmpty && (
                      <span className="absolute -top-2 right-3 inline-flex items-center gap-1 rounded-full bg-red-100 dark:bg-red-900/30 px-2 py-0.5 text-[10px] font-medium text-red-700 dark:text-red-400">
                        <AlertTriangle className="h-3 w-3" />
                        Most Urgent
                      </span>
                    )}

                    {/* Capped badge for RL */}
                    {item.field === 'remaining_life_date' && !isEmpty && isCappedDate(item.value) && (
                      <span className="inline-flex items-center gap-1 mt-1 rounded-full bg-yellow-100 dark:bg-yellow-900/30 px-2 py-0.5 text-[10px] font-medium text-yellow-700 dark:text-yellow-400">
                        <Hourglass className="h-3 w-3" />
                        30+ years
                      </span>
                    )}
                  </div>
                )
              })}
            </div>

            {/* Final due date summary */}
            {plan.final_due_date && (
              <div className="mt-3 flex items-center justify-between text-xs text-muted-foreground bg-card border border-border/50 rounded-lg px-4 py-2.5">
                <span className="flex items-center gap-1.5">
                  <ChevronRight className="h-3.5 w-3.5" />
                  Final Due Date (earliest of above):
                </span>
                <span className="font-mono font-semibold tabular-nums">
                  {formatDate(plan.final_due_date)}
                </span>
              </div>
            )}
          </div>

          {/* ── Status / Info ── */}
          <div className="border-t border-border pt-4">
            <div className="flex items-center gap-2 text-sm mb-3">
              <span className={cn('rounded-full px-2.5 py-0.5 text-xs font-medium', STATUS_CONFIG[plan.approval_status].className)}>
                {STATUS_CONFIG[plan.approval_status].label}
              </span>
              {plan.risk_category && (
                <span className={cn('rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase', RISK_CONFIG[plan.risk_category].className)}>
                  {plan.risk_category}
                </span>
              )}
            </div>
            {plan.approved_by_name && (
              <p className="text-xs text-muted-foreground">
                <span className="font-medium">Approved by:</span> {plan.approved_by_name}
                {plan.approved_at && ` · ${formatDate(plan.approved_at)}`}
              </p>
            )}
            {plan.approval_comment && (
              <div className="mt-2 rounded-lg bg-muted/40 px-3 py-2">
                <p className="text-xs text-muted-foreground italic">"{plan.approval_comment}"</p>
              </div>
            )}
          </div>

          {/* ── Approval Form ── */}
          {isPending && (
            <div className="border-t border-border pt-4 space-y-4">
              <h3 className="text-sm font-medium">Approval Action</h3>

              {/* 1-click Approve — submit directly after viewing 3 cards */}
              <button
                onClick={handleApproveInside}
                disabled={submitting}
                className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-green-600 hover:bg-green-700 text-white px-4 py-3 text-sm font-semibold transition-colors disabled:opacity-50"
              >
                {submitting ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <CheckCircle className="h-5 w-5" />
                )}
                Approve This Plan
              </button>

              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-border" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-card px-2 text-muted-foreground">OR reject / revise</span>
                </div>
              </div>

              {/* Reject/Revise selection (without Approve) */}
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => setAction('rejected')}
                  className={cn(
                    'flex flex-col items-center gap-1 rounded-xl border-2 p-3 transition-all text-sm',
                    action === 'rejected'
                      ? 'border-red-400 bg-red-50 dark:bg-red-900/10 text-red-700 dark:text-red-300'
                      : 'border-border/70 hover:border-red-200 hover:bg-red-50/50 dark:hover:bg-red-900/5 text-muted-foreground',
                  )}
                >
                  <XCircle className="h-5 w-5" />
                  Reject
                </button>
                <button
                  onClick={() => setAction('revised')}
                  className={cn(
                    'flex flex-col items-center gap-1 rounded-xl border-2 p-3 transition-all text-sm',
                    action === 'revised'
                      ? 'border-blue-400 bg-blue-50 dark:bg-blue-900/10 text-blue-700 dark:text-blue-300'
                      : 'border-border/70 hover:border-blue-200 hover:bg-blue-50/50 dark:hover:bg-blue-900/5 text-muted-foreground',
                  )}
                >
                  <RefreshCw className="h-5 w-5" />
                  Revise
                </button>
              </div>

              {/* Comment input for Reject/Revise) */}
              {(action === 'rejected' || action === 'revised') && (
                <div>
                  <textarea
                    value={comment}
                    onChange={(e) => {
                      setComment(e.target.value)
                      if (error && e.target.value.trim()) setError('')
                    }}
                    placeholder={
                      action === 'rejected'
                        ? 'Rejection reason...'
                        : 'Revision notes...'
                    }
                    rows={3}
                    className={cn(
                      'w-full rounded-lg border bg-background px-3 py-2 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-primary',
                      error ? 'border-destructive' : 'border-border',
                    )}
                  />
                  {error && (
                    <p className="text-xs text-destructive mt-1">{error}</p>
                  )}
                </div>
              )}

              {/* Submit for Reject/Revise */}
              {(action === 'rejected' || action === 'revised') && (
                <div className="flex items-center justify-end gap-2">
                  <button
                    onClick={() => setAction(null)}
                    disabled={submitting}
                    className="rounded-lg border border-border px-3.5 py-1.5 text-sm text-muted-foreground hover:bg-accent transition-colors disabled:opacity-50"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSubmit}
                    disabled={submitting}
                    className="inline-flex items-center gap-1.5 rounded-lg px-3.5 py-1.5 text-sm font-medium text-white transition-colors disabled:opacity-50 bg-destructive hover:bg-destructive/90"
                  >
                    {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
                    {action === 'rejected' ? 'Reject' : 'Submit Revision'}
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

/** ── Main Page ───────────────────────────────────────────── */
export default function PlansPage() {
  const supabase = createClient()
  const sb = supabase as any

  const DEMO_USER = {
    id: '3fca82af-b302-4d1e-8536-b89546ecfb15',
    company_id: 'c704d7e6-07fb-48a2-9152-564434d8653f',
    full_name: 'Dicki Wiryawan',
    role: 'super_admin',
  }

  const [rows, setRows] = useState<PlanRow[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('')
  const [search, setSearch] = useState('')
  const [currentUserId, setCurrentUserId] = useState<string | null>(null)

  // Side panel state
  const [sidePanelPlan, setSidePanelPlan] = useState<PlanRow | null>(null)
  const [sidePanelOpen, setSidePanelOpen] = useState(false)
  const [actionForPanel, setActionForPanel] = useState<'approved' | 'rejected' | 'revised' | null>(null)

  // Helper to update a row after side panel action
  const updateRow = useCallback((planId: string, updates: Partial<PlanRow>) => {
    setRows((prev) => prev.map((r) => (r.id === planId ? { ...r, ...updates } : r)))
  }, [])

  // Close side panel
  const closeSidePanel = useCallback(() => {
    setSidePanelOpen(false)
    setSidePanelPlan(null)
  }, [])

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        setLoading(true)

        const { data: { user } } = { data: { user: DEMO_USER } }
        if (!user) {
          if (!cancelled) setRows([])
          return
        }

        const appUserRow = DEMO_USER
        const companyId = DEMO_USER.company_id
        if (!companyId) {
          if (!cancelled) setRows([])
          return
        }

        if (!cancelled) setCurrentUserId(DEMO_USER.id)

        // Fetch plans for this company
        const { data: plansRaw, error: plansErr } = await sb
          .from('inspection_plans')
          .select('*')
          .eq('company_id', companyId)
          .order('approval_status', { ascending: true })
          .order('remaining_life_date', { ascending: true, nullsFirst: false })

        if (plansErr) {
          console.error('Fetch plans error:', plansErr)
          toast.error('Failed to load inspection plans')
          return
        }

        const plans = (plansRaw || []) as InspectionPlan[]
        if (plans.length === 0) {
          if (!cancelled) setRows([])
          return
        }

        // Build equipment map
        const equipIds = [...new Set(plans.map((p) => p.equipment_id))]
        const { data: equipRaw } = await sb
          .from('equipment')
          .select('id, tag, type, risk_category, material, fluid_service')
          .in('id', equipIds)

        const equipRows = (equipRaw || []) as (Equipment & { material?: string; fluid_service?: string })[]
        const equipMap = new Map<string, { tag: string; type: string; risk_category: string | null; material: string | null; fluid: string | null }>()
        for (const eq of equipRows) {
          equipMap.set(eq.id, {
            tag: eq.tag,
            type: eq.type,
            risk_category: eq.risk_category,
            material: eq.material || null,
            fluid: eq.fluid_service || null,
          })
        }

        // Build approver name map
        const approverIds = [...new Set(plans.map((p) => p.approved_by).filter(Boolean))] as string[]
        const approverMap = new Map<string, string>()
        if (approverIds.length > 0) {
          const { data: approverRaw } = await sb
            .from('app_users')
            .select('id, full_name')
            .in('id', approverIds)

          if (approverRaw) {
            for (const u of approverRaw as { id: string; full_name: string }[]) {
              approverMap.set(u.id, u.full_name)
            }
          }
        }

        // Build result rows
        const result: PlanRow[] = plans.map((plan) => {
          const eq = equipMap.get(plan.equipment_id)
          return {
            id: plan.id,
            equipment_id: plan.equipment_id,
            equipment_tag: eq?.tag || '',
            equipment_type: eq?.type || '',
            risk_category: eq?.risk_category || null,
            inspection_type: plan.inspection_type,
            remaining_life_date: plan.remaining_life_date,
            rbi_date_manual: plan.rbi_date_manual,
            disnaker_date: plan.disnaker_date,
            final_due_date: plan.final_due_date,
            approval_status: plan.approval_status as PlanApprovalStatus,
            approved_by: plan.approved_by,
            approved_by_name: plan.approved_by ? approverMap.get(plan.approved_by) || null : null,
            approved_at: plan.approved_at,
            approval_comment: plan.approval_comment,
            equipment_material: eq?.material || null,
            equipment_fluid: eq?.fluid || null,
          }
        })

        if (!cancelled) setRows(result)
      } catch (err) {
        console.error('Error loading plans:', err)
        toast.error('Unexpected error loading plans')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => { cancelled = true }
  }, [supabase, sb])

  const filtered = useMemo(() => {
    let result = rows

    if (statusFilter) {
      result = result.filter((r) => r.approval_status === statusFilter)
    }

    if (search.trim()) {
      const q = search.toLowerCase()
      result = result.filter((r) => r.equipment_tag.toLowerCase().includes(q))
    }

    return result
  }, [rows, statusFilter, search])

  const hasActiveFilters = !!statusFilter || !!search
  const clearFilters = () => {
    setStatusFilter('')
    setSearch('')
  }

  // Open side panel for a plan row
  const openSidePanel = (row: PlanRow, action?: 'approved' | 'rejected' | 'revised') => {
    setSidePanelPlan(row)
    setActionForPanel(action || null)
    setSidePanelOpen(true)
  }

  return (
    <AppLayout>
      <div className="px-8 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight">
              Planning & Approval
            </h1>
            <p className="text-sm text-muted-foreground">
              Inspection planning & due date approval
            </p>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3 mb-6">
          {/* Search */}
          <div className="relative flex-1 min-w-[200px] max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search equipment tag..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded-lg border border-border bg-background pl-9 pr-4 py-2 text-sm placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          {/* Status filter */}
          <div className="relative min-w-[150px]">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm appearance-none focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
              <option value="revised">Revised</option>
            </select>
          </div>

          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="inline-flex items-center gap-1 rounded-lg border border-border px-3 py-2 text-sm text-muted-foreground hover:bg-accent transition-colors"
            >
              Clear filters
            </button>
          )}
        </div>

        {/* Loading state */}
        {loading ? (
          <div className="rounded-xl border border-border/70 overflow-hidden">
            {[1, 2, 3, 4, 5].map((i) => (
              <div
                key={i}
                className="h-16 border-b border-border/50 last:border-b-0 animate-pulse bg-muted/10"
              />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          /* Empty state */
          <div className="rounded-xl border border-border/70 p-12 text-center text-muted-foreground">
            <Calendar className="h-10 w-10 mx-auto mb-3 opacity-40" />
            <p className="text-sm font-medium">
              {hasActiveFilters
                ? 'No plans match your filter.'
                : 'No inspection plan yet.'}
            </p>
            {hasActiveFilters && (
              <button
                onClick={clearFilters}
                className="mt-2 text-sm text-primary hover:underline"
              >
                Clear filters
              </button>
            )}
          </div>
        ) : (
          /* Table */
          <div className="rounded-xl border border-border/70 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border/70">
                    <th className="text-xs uppercase tracking-wider px-4 py-4 text-left font-medium text-muted-foreground min-w-[100px]">
                      Equipment
                    </th>
                    <th className="text-xs uppercase tracking-wider px-4 py-4 text-left font-medium text-muted-foreground min-w-[80px]">
                      Type
                    </th>
                    <th className="text-xs uppercase tracking-wider px-4 py-4 text-left font-medium text-muted-foreground min-w-[70px]">
                      Risk
                    </th>
                    <th className="text-xs uppercase tracking-wider px-4 py-4 text-left font-medium text-muted-foreground min-w-[120px]">
                      Remaining Life Date
                    </th>
                    <th className="text-xs uppercase tracking-wider px-4 py-4 text-left font-medium text-muted-foreground min-w-[120px]">
                      RBI Date (Manual)
                    </th>
                    <th className="text-xs uppercase tracking-wider px-4 py-4 text-left font-medium text-muted-foreground min-w-[120px]">
                      DISNAKER Date
                    </th>
                    <th className="text-xs uppercase tracking-wider px-4 py-4 text-left font-medium text-muted-foreground min-w-[120px]">
                      Final Due Date
                    </th>
                    <th className="text-xs uppercase tracking-wider px-4 py-4 text-left font-medium text-muted-foreground min-w-[90px]">
                      Status
                    </th>
                    <th className="text-xs uppercase tracking-wider px-4 py-4 text-left font-medium text-muted-foreground min-w-[180px]">
                      Actions / Info
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((row) => {
                    const statusCfg = STATUS_CONFIG[row.approval_status] || STATUS_CONFIG.pending
                    const riskCfg = row.risk_category
                      ? RISK_CONFIG[row.risk_category]
                      : null
                    const isPending = row.approval_status === 'pending'

                    return (
                      <tr
                        key={row.id}
                        onClick={() => openSidePanel(row)}
                        className={cn(
                          'border-b border-border/50 last:border-b-0 transition-colors cursor-pointer',
                          isPending ? 'hover:bg-muted/15' : 'hover:bg-muted/5',
                        )}
                      >
                        {/* Equipment */}
                        <td className="px-4 py-3.5 font-medium">
                          {row.equipment_tag}
                        </td>

                        {/* Type */}
                        <td className="px-4 py-3.5 text-muted-foreground capitalize">
                          {row.inspection_type}
                        </td>

                        {/* Risk */}
                        <td className="px-4 py-3.5">
                          {riskCfg ? (
                            <span
                              className={cn(
                                'inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase',
                                riskCfg.className,
                              )}
                            >
                              {row.risk_category}
                            </span>
                          ) : (
                            <span className="text-muted-foreground/40">—</span>
                          )}
                        </td>

                        {/* Remaining Life Date (read-only) */}
                        <td className="px-4 py-3.5">
                          {(() => {
                            const { display, capped } = formatRemainingLifeDate(row.remaining_life_date)
                            return capped ? (
                              <span className="inline-flex items-center gap-1 rounded-full bg-yellow-100 px-2.5 py-0.5 text-xs font-medium text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400">
                                <Hourglass className="h-3 w-3" />
                                {display}
                              </span>
                            ) : (
                              <span className="font-mono text-xs tabular-nums">{display}</span>
                            )
                          })()}
                        </td>

                        {/* RBI Date (manual, editable if pending) */}
                        <td className="px-4 py-3.5">
                          {isPending ? (
                            <input
                              type="date"
                              defaultValue={formatDateInput(row.rbi_date_manual)}
                              onClick={(e) => e.stopPropagation()}
                              onBlur={(e) => {
                                // Update in DB, then refresh rows
                                const oldVal = row.rbi_date_manual
                                const newFinal = computeFinalDueDate(
                                  row.remaining_life_date,
                                  e.target.value,
                                  row.disnaker_date,
                                )
                                updateRow(row.id, { rbi_date_manual: e.target.value || null, final_due_date: newFinal } as any)
                                const sb2 = (createClient() as any)
                                const payload: Record<string, any> = { rbi_date_manual: e.target.value || null }
                                if (newFinal !== row.final_due_date) payload.final_due_date = newFinal
                                sb2.from('inspection_plans').update(payload).eq('id', row.id).then((res: any) => {
                                  if (res.error) {
                                    updateRow(row.id, { rbi_date_manual: oldVal, final_due_date: row.final_due_date } as any)
                                    toast.error(res.error.message || 'Failed to save')
                                  }
                                })
                              }}
                              className="w-full rounded-md border border-border bg-background px-2 py-1 text-xs font-mono focus:outline-none focus:ring-1 focus:ring-primary"
                            />
                          ) : (
                            <span className="font-mono text-xs tabular-nums">
                              {formatDate(row.rbi_date_manual)}
                            </span>
                          )}
                        </td>

                        {/* DISNAKER Date (manual, editable if pending) */}
                        <td className="px-4 py-3.5">
                          {isPending ? (
                            <input
                              type="date"
                              defaultValue={formatDateInput(row.disnaker_date)}
                              onClick={(e) => e.stopPropagation()}
                              onBlur={(e) => {
                                const oldVal = row.disnaker_date
                                const newFinal = computeFinalDueDate(
                                  row.remaining_life_date,
                                  row.rbi_date_manual,
                                  e.target.value,
                                )
                                updateRow(row.id, { disnaker_date: e.target.value || null, final_due_date: newFinal } as any)
                                const sb2 = (createClient() as any)
                                const payload: Record<string, any> = { disnaker_date: e.target.value || null }
                                if (newFinal !== row.final_due_date) payload.final_due_date = newFinal
                                sb2.from('inspection_plans').update(payload).eq('id', row.id).then((res: any) => {
                                  if (res.error) {
                                    updateRow(row.id, { disnaker_date: oldVal, final_due_date: row.final_due_date } as any)
                                    toast.error(res.error.message || 'Failed to save')
                                  }
                                })
                              }}
                              className="w-full rounded-md border border-border bg-background px-2 py-1 text-xs font-mono focus:outline-none focus:ring-1 focus:ring-primary"
                            />
                          ) : (
                            <span className="font-mono text-xs tabular-nums">
                              {formatDate(row.disnaker_date)}
                            </span>
                          )}
                        </td>

                        {/* Final Due Date (read-only) */}
                        <td className="px-4 py-3.5 font-mono text-xs tabular-nums font-semibold">
                          {formatDate(row.final_due_date)}
                        </td>

                        {/* Status */}
                        <td className="px-4 py-3.5">
                          <span
                            className={cn(
                              'inline-block rounded-full px-2.5 py-0.5 text-xs font-medium',
                              statusCfg.className,
                            )}
                          >
                            {statusCfg.label}
                          </span>
                        </td>

                        {/* Actions / Info */}
                        <td className="px-4 py-3.5" onClick={(e) => e.stopPropagation()}>
                          {isPending ? (
                            <div className="flex items-center gap-1.5">
                              <button
                                onClick={(e) => { e.stopPropagation(); openSidePanel(row); }}
                                title="Review before approving"
                                className="inline-flex items-center gap-1 rounded-lg border border-border/70 bg-card px-2.5 py-1 text-xs font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
                              >
                                <Eye className="h-3.5 w-3.5" />
                                Review
                              </button>
                              <button
                                onClick={(e) => { e.stopPropagation(); openSidePanel(row, 'rejected'); }}
                                title="Reject"
                                className="inline-flex items-center gap-1 rounded-lg border border-transparent bg-red-100 px-2.5 py-1 text-xs font-medium text-red-700 hover:bg-red-200 transition-colors dark:bg-red-900/30 dark:text-red-400 dark:hover:bg-red-900/50"
                              >
                                <XCircle className="h-3.5 w-3.5" />
                                Reject
                              </button>
                              <button
                                onClick={(e) => { e.stopPropagation(); openSidePanel(row, 'revised'); }}
                                title="Revise"
                                className="inline-flex items-center gap-1 rounded-lg border border-transparent bg-blue-100 px-2.5 py-1 text-xs font-medium text-blue-700 hover:bg-blue-200 transition-colors dark:bg-blue-900/30 dark:text-blue-400 dark:hover:bg-blue-900/50"
                              >
                                <RefreshCw className="h-3.5 w-3.5" />
                                Revise
                              </button>
                            </div>
                          ) : (
                            <div className="text-xs text-muted-foreground space-y-0.5">
                              {row.approved_by_name && (
                                <p>
                                  <span className="font-medium">By:</span>{' '}
                                  {row.approved_by_name}
                                </p>
                              )}
                              {row.approved_at && (
                                <p>
                                  <span className="font-medium">At:</span>{' '}
                                  {formatDate(row.approved_at)}
                                </p>
                              )}
                              {row.approval_comment && (
                                <p className="italic max-w-[160px] truncate" title={row.approval_comment}>
                                  "{row.approval_comment}"
                                </p>
                              )}
                            </div>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Side Panel (replaces old ActionModal) */}
      <PlanSidePanel
        plan={sidePanelPlan}
        open={sidePanelOpen}
        onClose={closeSidePanel}
        userId={currentUserId}
        onUpdate={updateRow}
        initialAction={actionForPanel}
      />
    </AppLayout>
  )
}