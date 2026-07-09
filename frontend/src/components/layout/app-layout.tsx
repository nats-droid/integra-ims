'use client'

import { useState } from 'react'
import Sidebar from './sidebar'
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

      {/* Sidebar */}
      <div className={`fixed left-0 top-0 h-screen z-30 transition-transform duration-200 lg:translate-x-0 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <Sidebar onClose={() => setSidebarOpen(false)} />
      </div>

      {/* Main */}
      <main className="flex-1 min-h-screen lg:ml-64">
        {/* Topbar */}
        <div className="sticky top-0 z-10 flex items-center justify-between px-4 py-3 bg-card border-b border-border">
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 rounded-lg hover:bg-muted lg:hidden"
          >
            <Menu className="h-5 w-5 text-foreground" />
          </button>
          <span className="font-bold text-sm text-foreground lg:hidden">Integra</span>
          <div className="ml-auto flex items-center gap-2">
            {topbarRight}
          </div>
        </div>

        <div className="p-4 lg:p-6">
          {children}
        </div>
      </main>
    </div>
  )
}
