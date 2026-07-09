'use client'

import { useState } from 'react'
import Sidebar from './sidebar'
import BottomNav from './bottom-nav'
import { Menu } from 'lucide-react'

interface AppLayoutProps {
  children: React.ReactNode
  topbarRight?: React.ReactNode
}

export default function AppLayout({ children, topbarRight }: AppLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="flex min-h-screen bg-background">

      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar desktop — always visible */}
      <div className="hidden lg:block fixed left-0 top-0 h-screen w-64 z-30">
        <Sidebar onClose={() => setSidebarOpen(false)} />
      </div>

      {/* Sidebar mobile — drawer */}
      <div className={`lg:hidden fixed left-0 top-0 h-screen w-64 z-30 transition-transform duration-200 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <Sidebar onClose={() => setSidebarOpen(false)} />
      </div>

      {/* Main content */}
      <main className="flex-1 min-h-screen lg:ml-64 pb-16 lg:pb-0">
        {/* Topbar */}
        <div className="sticky top-0 z-10 flex items-center justify-between px-4 py-3 bg-card border-b border-border">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(true)}
              className="p-2 rounded-lg hover:bg-muted lg:hidden"
            >
              <Menu className="h-5 w-5 text-foreground" />
            </button>
            <div className="flex items-center gap-2 lg:hidden">
              <div className="w-6 h-6 rounded-md bg-primary flex items-center justify-center">
                <span className="text-white font-bold text-xs">IG</span>
              </div>
              <span className="font-bold text-sm text-foreground">Integra</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {topbarRight}
          </div>
        </div>

        <div className="p-4 lg:p-6">
          {children}
        </div>
      </main>

      {/* Bottom nav mobile only */}
      <BottomNav />
    </div>
  )
}
