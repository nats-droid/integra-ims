'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard, Wrench, ClipboardList, CalendarCheck,
  FlaskConical, FileText, Settings,
  Activity, Gauge, Pipette, Layers,
} from 'lucide-react'
import { cn } from '@/utils/cn'

const NAV_ITEMS = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  {
    label: 'Master Data',
    icon: Layers,
    children: [
      { href: '/equipment', label: 'Equipment', icon: Wrench },
      { href: '/plant-areas', label: 'Plant Areas', icon: Layers },
      { href: '/circuits', label: 'Circuits', icon: Activity },
      { href: '/cml-points', label: 'CML Points', icon: Pipette },
    ],
  },
  { href: '/inspections', label: 'Inspections', icon: ClipboardList },
  { href: '/plans', label: 'Inspection Plans', icon: CalendarCheck },
  { href: '/campaigns', label: 'Campaigns', icon: FlaskConical },
  { href: '/dm-screener', label: 'DM Screener', icon: Gauge },
  { href: '/reports', label: 'Reports', icon: FileText },
  { href: '/settings', label: 'Settings', icon: Settings },
]

export default function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-64 border-r border-border bg-white dark:bg-gray-950">
      {/* Logo — clean, minimal */}
      <div className="flex h-14 items-center gap-2.5 px-6 border-b border-border/50">
        <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-xs font-semibold text-primary-foreground tracking-tight">
          IG
        </div>
        <span className="text-sm font-semibold tracking-tight">Integra</span>
      </div>

      {/* Navigation — lots of whitespace, no heavy borders */}
      <nav className="flex flex-col gap-0.5 p-4 overflow-y-auto h-[calc(100vh-3.5rem)]">
        {NAV_ITEMS.map((item) => {
          if ('children' in item && item.children) {
            const isActive = item.children.some((c) => pathname.startsWith(c.href))
            return (
              <div key={item.label}>
                <div
                  className={cn(
                    'flex items-center gap-2.5 rounded-md px-3 py-2 text-xs font-medium transition-colors',
                    isActive
                      ? 'text-primary'
                      : 'text-muted-foreground hover:text-foreground'
                  )}
                >
                  <item.icon className="h-4 w-4" />
                  {item.label}
                </div>
                <div className="ml-3 mt-0.5 flex flex-col gap-0.5 border-l border-border/40 pl-3">
                  {item.children.map((child) => {
                    const active = pathname === child.href || pathname.startsWith(child.href + '/')
                    return (
                      <Link
                        key={child.href}
                        href={child.href}
                        className={cn(
                          'flex items-center gap-2.5 rounded-md px-3 py-1.5 text-xs transition-colors',
                          active
                            ? 'text-primary font-medium'
                            : 'text-muted-foreground hover:text-foreground'
                        )}
                      >
                        {active && <span className="absolute left-0 h-4 w-0.5 rounded-r bg-primary" />}
                        <child.icon className="h-3.5 w-3.5" />
                        {child.label}
                      </Link>
                    )
                  })}
                </div>
              </div>
            )
          }
          const active = pathname === item.href || pathname.startsWith(item.href + '/')
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex items-center gap-2.5 rounded-md px-3 py-2 text-xs font-medium transition-colors',
                active
                  ? 'text-primary'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              {active && <span className="absolute -ml-3 h-4 w-0.5 rounded-r bg-primary" />}
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          )
        })}
      </nav>
    </aside>
  )
}
