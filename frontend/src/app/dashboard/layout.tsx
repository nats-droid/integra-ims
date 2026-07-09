'use client'
export const dynamic = 'force-dynamic'

import { createClient } from '@/lib/supabase/client'
import { useRouter } from 'next/navigation'
import { useEffect, useState, useRef, useCallback } from 'react'
import AppLayout from '@/components/layout/app-layout'
import { Bell, CheckCheck } from 'lucide-react'
import { cn } from '@/utils/cn'

interface Notification {
  id: string
  type: string
  title: string
  message: string
  is_read: boolean
  related_id: string | null
  equipment_id: string | null
  created_at: string
}

const ZONE_ICONS: Record<string, string> = {
  overdue: '⚠️', due_7: '🔴', due_30: '🟠', due_60: '🟡', due_90: '📅',
}

function relativeTime(isoDate: string): string {
  const diff = Math.floor((Date.now() - new Date(isoDate).getTime()) / 1000)
  if (diff < 60) return 'Just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  if (diff < 172800) return 'Yesterday'
  return new Date(isoDate).toLocaleDateString()
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const supabase = createClient()
  const [loading, setLoading] = useState(true)
  const [companyId, setCompanyId] = useState<string | null>(null)
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const [markingAllRead, setMarkingAllRead] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  const fetchNotifications = useCallback(async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) return
      const res = await fetch('/api/backend/api/v1/notifications/me', {
        headers: { Authorization: `Bearer ${session.access_token}` },
      })
      if (!res.ok) return
      const data = await res.json()
      const notifs: Notification[] = data.notifications || []
      setNotifications(notifs)
      setUnreadCount(notifs.filter(n => !n.is_read).length)
    } catch { /* silent */ }
  }, [supabase])

  // Auth guard + profile load
  useEffect(() => {
    async function init() {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) { router.push('/auth/login'); return }
      const { data: profile } = await supabase
        .from('app_users')
        .select('company_id')
        .eq('auth_user_id', user.id)
        .single()
      if (profile) setCompanyId((profile as any).company_id)
      setLoading(false)
      fetchNotifications()
    }
    init()
  }, [supabase, router, fetchNotifications])

  // Polling every 5 min
  useEffect(() => {
    const interval = setInterval(fetchNotifications, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [fetchNotifications])

  // Click outside dropdown
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  const markAsRead = async (notif: Notification) => {
    if (!notif.is_read) {
      const { data: { session } } = await supabase.auth.getSession()
      if (session) {
        await fetch(`/api/backend/api/v1/notifications/${notif.id}/read`, {
          method: 'PATCH',
          headers: { Authorization: `Bearer ${session.access_token}` },
        })
        await fetchNotifications()
      }
    }
    setDropdownOpen(false)
    if (notif.equipment_id) router.push(`/equipment/${notif.equipment_id}`)
  }

  const markAllRead = async () => {
    setMarkingAllRead(true)
    const { data: { session } } = await supabase.auth.getSession()
    if (session) {
      await Promise.all(
        notifications.filter(n => !n.is_read).map(n =>
          fetch(`/api/backend/api/v1/notifications/${n.id}/read`, {
            method: 'PATCH',
            headers: { Authorization: `Bearer ${session.access_token}` },
          })
        )
      )
      await fetchNotifications()
    }
    setMarkingAllRead(false)
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-muted-foreground">Loading...</p>
        </div>
      </div>
    )
  }

  // Notification bell widget
  const NotificationBell = (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setDropdownOpen(o => !o)}
        className="relative p-2 rounded-lg hover:bg-muted transition-colors"
      >
        <Bell className="h-5 w-5 text-muted-foreground" />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-destructive text-white text-[10px] font-bold rounded-full flex items-center justify-center">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {dropdownOpen && (
        <div className="absolute right-0 top-10 w-80 bg-card border border-border rounded-xl shadow-lg z-50 overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-border">
            <span className="text-sm font-semibold text-foreground">Notifications</span>
            {unreadCount > 0 && (
              <button
                onClick={markAllRead}
                disabled={markingAllRead}
                className="flex items-center gap-1.5 text-xs text-primary hover:underline"
              >
                <CheckCheck className="h-3.5 w-3.5" />
                Mark all read
              </button>
            )}
          </div>
          <div className="max-h-80 overflow-y-auto divide-y divide-border">
            {notifications.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">No notifications</p>
            ) : notifications.slice(0, 10).map(n => (
              <button
                key={n.id}
                onClick={() => markAsRead(n)}
                className={cn(
                  'w-full text-left px-4 py-3 hover:bg-muted transition-colors',
                  !n.is_read && 'bg-primary/5'
                )}
              >
                <div className="flex items-start gap-2.5">
                  <span className="text-base mt-0.5">{ZONE_ICONS[n.type] || '🔔'}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-semibold text-foreground truncate">{n.title}</p>
                    <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{n.message}</p>
                    <p className="text-[10px] text-muted-foreground mt-1">{relativeTime(n.created_at)}</p>
                  </div>
                  {!n.is_read && <div className="w-1.5 h-1.5 rounded-full bg-primary mt-1.5 flex-shrink-0" />}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )

  return (
    <AppLayout topbarRight={NotificationBell}>
      {children}
    </AppLayout>
  )
}
