'use client'

import { useState } from 'react'
import Sidebar from './sidebar'
import { Menu, X } from 'lucide-react'

export default function AppLayout({ children }: { children: React.ReactNode }) {
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

      {/* Sidebar — hidden on mobile unless open */}
      <div className={`fixed left-0 top-0 h-screen z-30 transition-transform duration-200 lg:translate-x-0 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <Sidebar onClose={() => setSidebarOpen(false)} />
      </div>

      {/* Main content */}
      <main className="flex-1 min-h-screen lg:ml-64">
        {/* Mobile topbar */}
        <div className="sticky top-0 z-10 flex items-center gap-3 px-4 py-3 bg-card border-b border-border lg:hidden">
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 rounded-lg hover:bg-muted"
          >
            <Menu className="h-5 w-5 text-foreground" />
          </button>
          <span className="font-bold text-sm text-foreground">Integra</span>
        </div>

        <div className="p-4 lg:p-6 max-w-screen-2xl">
          {children}
        </div>
      </main>
    </div>
  )
}
