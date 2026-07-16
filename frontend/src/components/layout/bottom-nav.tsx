'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useState } from 'react'
import {
  LayoutDashboard, ClipboardList, Wrench,
  Shield, Grid3x3, X, ChevronRight,
  Brain, BarChart3, BarChart2, CalendarCheck, FlaskConical,
  FileText, Settings, Layers, Activity, Pipette, MapPin,
} from 'lucide-react'
import { cn } from '@/utils/cn'

const MAIN_NAV = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/inspections', label: 'Inspections', icon: ClipboardList },
  { href: '/equipment', label: 'Equipment', icon: Wrench },
  { href: '/dm-screener', label: 'DM Screener', icon: Shield },
]

const MORE_ITEMS = [
  { href: '/plans', label: 'Inspection Plans', icon: CalendarCheck },
  { href: '/campaigns', label: 'Campaigns', icon: FlaskConical },
  { href: '/ai-insight', label: 'AI Insight', icon: Brain },
  { href: '/ml-analytics', label: 'ML Analytics', icon: BarChart3 },
  { href: '/thickness-analytics', label: 'Thickness', icon: BarChart2 },
  { href: '/reports', label: 'Reports', icon: FileText },
  { href: '/settings', label: 'Settings', icon: Settings },
  {
    label: 'Master Data', icon: Layers,
    children: [
      { href: '/plant-areas', label: 'Plant Areas', icon: MapPin },
      { href: '/circuits', label: 'Circuits', icon: Activity },
      { href: '/cml-points', label: 'CML Points', icon: Pipette },
    ]
  },
]

export default function BottomNav() {
  const pathname = usePathname()
  const [moreOpen, setMoreOpen] = useState(false)
  const [masterOpen, setMasterOpen] = useState(false)

  const isActive = (href: string) => pathname === href || pathname.startsWith(href + '/')

  return (
    <>
      {/* More drawer overlay */}
      {moreOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/40 lg:hidden"
          onClick={() => { setMoreOpen(false); setMasterOpen(false) }}
        />
      )}

      {/* More drawer */}
      {moreOpen && (
        <div className="fixed bottom-16 left-0 right-0 z-50 bg-card border-t border-border rounded-t-2xl shadow-xl lg:hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-border">
            <span className="text-sm font-semibold text-foreground">More</span>
            <button
              onClick={() => { setMoreOpen(false); setMasterOpen(false) }}
              className="p-1.5 rounded-lg hover:bg-muted"
            >
              <X className="h-4 w-4 text-muted-foreground" />
            </button>
          </div>
          <div className="px-3 py-2 max-h-80 overflow-y-auto">
            {MORE_ITEMS.map((item) => {
              if ('children' in item) {
                return (
                  <div key={item.label}>
                    <button
                      onClick={() => setMasterOpen(o => !o)}
                      className="flex items-center gap-3 w-full px-3 py-3 rounded-xl hover:bg-muted transition-colors"
                    >
                      <div className="w-8 h-8 rounded-lg bg-violet-100 flex items-center justify-center">
                        <item.icon className="h-4 w-4 text-violet-600" />
                      </div>
                      <span className="flex-1 text-sm font-medium text-foreground text-left">{item.label}</span>
                      <ChevronRight className={cn('h-4 w-4 text-muted-foreground transition-transform', masterOpen && 'rotate-90')} />
                    </button>
                    {masterOpen && (
                      <div className="ml-4 pl-3 border-l border-border">
                        {item.children!.map(child => (
                          <Link
                            key={child.href}
                            href={child.href}
                            onClick={() => { setMoreOpen(false); setMasterOpen(false) }}
                            className="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-muted transition-colors"
                          >
                            <child.icon className="h-4 w-4 text-muted-foreground" />
                            <span className="text-sm text-foreground">{child.label}</span>
                          </Link>
                        ))}
                      </div>
                    )}
                  </div>
                )
              }
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setMoreOpen(false)}
                  className={cn(
                    'flex items-center gap-3 px-3 py-3 rounded-xl hover:bg-muted transition-colors',
                    isActive(item.href) && 'bg-primary/10'
                  )}
                >
                  <div className={cn(
                    'w-8 h-8 rounded-lg flex items-center justify-center',
                    isActive(item.href) ? 'bg-primary' : 'bg-muted'
                  )}>
                    <item.icon className={cn('h-4 w-4', isActive(item.href) ? 'text-white' : 'text-muted-foreground')} />
                  </div>
                  <span className={cn('text-sm font-medium', isActive(item.href) ? 'text-primary' : 'text-foreground')}>
                    {item.label}
                  </span>
                </Link>
              )
            })}
          </div>
        </div>
      )}

      {/* Bottom nav bar */}
      <nav className="fixed bottom-0 left-0 right-0 z-40 bg-card border-t border-border lg:hidden">
        <div className="flex items-center justify-around px-2 py-1 safe-area-pb">
          {MAIN_NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="flex flex-col items-center gap-0.5 px-3 py-2 min-w-[60px]"
            >
              <div className={cn(
                'w-8 h-8 rounded-xl flex items-center justify-center transition-all',
                isActive(item.href) ? 'bg-primary' : 'bg-transparent'
              )}>
                <item.icon className={cn(
                  'h-5 w-5 transition-colors',
                  isActive(item.href) ? 'text-white' : 'text-muted-foreground'
                )} />
              </div>
              <span className={cn(
                'text-[10px] font-medium transition-colors',
                isActive(item.href) ? 'text-primary' : 'text-muted-foreground'
              )}>
                {item.label}
              </span>
            </Link>
          ))}

          {/* More button */}
          <button
            onClick={() => setMoreOpen(o => !o)}
            className="flex flex-col items-center gap-0.5 px-3 py-2 min-w-[60px]"
          >
            <div className={cn(
              'w-8 h-8 rounded-xl flex items-center justify-center transition-all',
              moreOpen ? 'bg-primary' : 'bg-transparent'
            )}>
              <Grid3x3 className={cn('h-5 w-5', moreOpen ? 'text-white' : 'text-muted-foreground')} />
            </div>
            <span className={cn('text-[10px] font-medium', moreOpen ? 'text-primary' : 'text-muted-foreground')}>
              More
            </span>
          </button>
        </div>
      </nav>
    </>
  )
}
