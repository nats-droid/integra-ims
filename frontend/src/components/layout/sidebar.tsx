'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useEffect, useState } from 'react'
import { createClient } from '@/lib/supabase/client'
import {
  LayoutDashboard, Wrench, ClipboardList, CalendarCheck,
  FlaskConical, FileText, Settings, Activity, Gauge,
  Pipette, Layers, BarChart3, BarChart2, Brain, ChevronDown,
  ChevronRight, LogOut, User, MapPin, Shield, ClipboardCheck,
} from 'lucide-react'
import { cn } from '@/utils/cn'

const NAV = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard, color: 'text-indigo-500' },
  {
    label: 'Master Data', icon: Layers, color: 'text-violet-500',
    children: [
      { href: '/equipment', label: 'Equipment', icon: Wrench, color: 'text-violet-400' },
      { href: '/plant-areas', label: 'Plant Areas', icon: MapPin, color: 'text-violet-400' },
      { href: '/circuits', label: 'Circuits', icon: Activity, color: 'text-violet-400' },
      { href: '/cml-points', label: 'CML Points', icon: Pipette, color: 'text-violet-400' },
    ],
  },
  { href: '/inspections', label: 'Inspections', icon: ClipboardList, color: 'text-sky-500' },
  { href: '/plans', label: 'Inspection Plans', icon: CalendarCheck, color: 'text-cyan-500' },
  { href: '/campaigns', label: 'Campaigns', icon: FlaskConical, color: 'text-teal-500' },
  { href: '/checklist-builder', label: 'Checklist Builder', icon: ClipboardCheck, color: 'text-indigo-500', roles: ['supervisor', 'super_admin'] },
  { href: '/dm-screener', label: 'DM Screener', icon: Shield, color: 'text-amber-500' },
  { href: '/ai-insight', label: 'AI Insight', icon: Brain, color: 'text-purple-500' },
  { href: '/ml-analytics', label: 'ML Analytics', icon: BarChart3, color: 'text-blue-500' },
  { href: '/thickness-analytics', label: 'Thickness Analytics', icon: BarChart2, color: 'text-cyan-500' },
  { href: '/reports', label: 'Reports', icon: FileText, color: 'text-slate-500' },
  { href: '/settings', label: 'Settings', icon: Settings, color: 'text-slate-500' },
]

export default function Sidebar({ onClose }: { onClose?: () => void }) {
  const pathname = usePathname()
  const [masterOpen, setMasterOpen] = useState(false)
  const [user, setUser] = useState<{ name: string; role: string } | null>(null)
  const supabase = createClient()

  useEffect(() => {
    const masterPaths = ['/equipment', '/plant-areas', '/circuits', '/cml-points']
    if (masterPaths.some(p => pathname.startsWith(p))) setMasterOpen(true)
  }, [pathname])

  useEffect(() => {
    async function loadUser() {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) return
      const { data: profile } = await supabase
        .from('app_users')
        .select('full_name, role')
        .eq('auth_user_id', session.user.id)
        .single()
      if (profile) setUser({ name: (profile as any).full_name, role: (profile as any).role })
    }
    loadUser()
  }, [supabase])

  const isActive = (href: string) => pathname === href || pathname.startsWith(href + '/')

  return (
    <aside
      className="fixed left-0 top-0 h-screen w-64 flex flex-col z-30 border-r"
      style={{ background: 'var(--color-sidebar-bg)', borderColor: 'var(--color-sidebar-border)' }}
    >
      {/* Brand */}
      <div className="px-5 py-5 border-b" style={{ borderColor: 'var(--color-sidebar-border)' }}>
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
            <span className="text-white font-bold text-sm">IG</span>
          </div>
          <div>
            <p className="font-bold text-sm text-foreground">Integra</p>
            <p className="text-xs" style={{ color: 'var(--color-muted-foreground)' }}>Asset Integrity</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-0.5">
        {NAV.map((item) => {
          if ('roles' in item && item.roles && user && !item.roles.includes(user.role)) {
            return null
          }
          if ('children' in item) {
            const childActive = item.children!.some(c => isActive(c.href))
            const open = masterOpen || childActive
            return (
              <div key={item.label}>
                <button
                  onClick={() => setMasterOpen(o => !o)}
                  className={cn(
                    'sidebar-item w-full',
                    childActive && 'active'
                  )}
                >
                  <item.icon className={cn('h-4 w-4 flex-shrink-0', item.color)} />
                  <span className="flex-1 text-left">{item.label}</span>
                  {open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
                </button>
                {open && (
                  <div className="ml-4 mt-0.5 space-y-0.5 border-l pl-3" style={{ borderColor: 'var(--color-border)' }}>
                    {item.children!.map(child => (
                      <Link key={child.href} href={child.href}
                        onClick={() => onClose?.()}
                        className={cn('sidebar-item text-xs', isActive(child.href) && 'active')}
                      >
                        <child.icon className={cn('h-3.5 w-3.5 flex-shrink-0', child.color)} />
                        {child.label}
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            )
          }
          return (
            <Link key={item.href} href={item.href}
              onClick={() => onClose?.()}
              className={cn('sidebar-item', isActive(item.href) && 'active')}
            >
              <item.icon className={cn('h-4 w-4 flex-shrink-0', item.color)} />
              {item.label}
            </Link>
          )
        })}
      </nav>

      {/* User */}
      {user && (
        <div className="px-4 py-4 border-t" style={{ borderColor: 'var(--color-sidebar-border)' }}>
          <div className="flex items-center gap-3 mb-3">
            <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
              <User className="h-4 w-4 text-primary" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground truncate">{user.name}</p>
              <p className="text-xs capitalize" style={{ color: 'var(--color-muted-foreground)' }}>{user.role}</p>
            </div>
          </div>
          <button
            onClick={() => { onClose?.(); createClient().auth.signOut().then(() => window.location.href = '/auth/login') }}
            className="sidebar-item w-full text-xs"
          >
            <LogOut className="h-3.5 w-3.5 text-red-400" />
            Sign out
          </button>
        </div>
      )}
    </aside>
  )
}
