'use client'
export const dynamic = 'force-dynamic'

import { createClient } from '@/lib/supabase/client'
import { useEffect, useState } from 'react'
import { Layers, ChevronRight, Minus, Hash } from 'lucide-react'
import AppLayout from '@/components/layout/app-layout'
import { cn } from '@/utils/cn'
import type { Database } from '@/types/database'
type PlantArea = Database['public']['Tables']['plant_areas']['Row']

interface AreaWithMeta extends PlantArea {
  parent_name: string | null
  equipment_count: number
  children: AreaWithMeta[]
}

export default function PlantAreasPage() {
  const [areas, setAreas] = useState<AreaWithMeta[]>([])
  const [loading, setLoading] = useState(true)
  const supabase = createClient()

  useEffect(() => {
    async function load() {
      try {
        // Get all plant areas
        const { data: areaRows, error: areaErr } = await supabase
          .from('plant_areas')
          .select('*')
          .order('name') as unknown as { data: PlantArea[] | null; error: any }

        if (areaErr) throw areaErr
        if (!areaRows) { setLoading(false); return }

        // Get equipment counts per area
        const { data: equipRows } = await supabase
          .from('equipment')
          .select('area_id, id', { count: 'exact' }) as unknown as { data: { area_id: string | null; id: string }[] | null }

        // Build count map
        const countMap: Record<string, number> = {}
        if (equipRows) {
          for (const e of equipRows as { area_id: string | null }[]) {
            if (e.area_id) {
              countMap[e.area_id] = (countMap[e.area_id] || 0) + 1
            }
          }
        }

        // Map to AreaWithMeta
        const areaMap = new Map<string, AreaWithMeta>()
        for (const a of areaRows as PlantArea[]) {
          areaMap.set(a.id, {
            ...a,
            parent_name: null,
            equipment_count: countMap[a.id] || 0,
            children: [],
          })
        }

        // Set parent names and build children
        const topLevel: AreaWithMeta[] = []
        for (const a of areaMap.values()) {
          if (a.parent_area_id && areaMap.has(a.parent_area_id)) {
            const parent = areaMap.get(a.parent_area_id)!
            a.parent_name = parent.name
            parent.children.push(a)
          } else {
            a.parent_name = null
          }
        }

        // Collect top-level only (children are nested)
        for (const a of areaMap.values()) {
          if (!a.parent_area_id || !areaMap.has(a.parent_area_id)) {
            topLevel.push(a)
          }
        }

        // Sort top level by name
        topLevel.sort((a, b) => a.name.localeCompare(b.name))

        setAreas(topLevel)
      } catch (err) {
        console.error('Failed to load plant areas:', err)
      }
      setLoading(false)
    }
    load()
  }, [supabase])

  function renderArea(area: AreaWithMeta, depth: number = 0) {
    const hasChildren = area.children.length > 0
    return (
      <div key={area.id}>
        <div
          className={cn(
            'grid grid-cols-[1fr_1fr_2fr_1fr] gap-4 px-6 py-3.5 text-sm items-center border-b border-border/50 hover:bg-accent/20 transition-colors',
            depth > 0 && ''
          )}
        >
          {/* Name with indentation */}
          <div className="flex items-center gap-1.5 min-w-0">
            {depth > 0 && (
              <span style={{ width: depth * 20 }} className="shrink-0 flex items-center justify-center">
                <ChevronRight className="h-3 w-3 text-muted-foreground/40" />
              </span>
            )}
            <Layers className="h-4 w-4 shrink-0 text-muted-foreground" />
            <span className="font-medium truncate">{area.name}</span>
          </div>

          {/* Parent Area */}
          <div className="text-muted-foreground truncate">
            {area.parent_name || (
              <span className="text-xs text-muted-foreground/50 flex items-center gap-1">
                <Minus className="h-3 w-3" /> Top Level
              </span>
            )}
          </div>

          {/* Description */}
          <div className="text-muted-foreground truncate text-xs">
            {area.description || <span className="italic text-muted-foreground/40">—</span>}
          </div>

          {/* Equipment Count */}
          <div className="flex items-center gap-1.5">
            <Hash className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="font-mono text-sm tabular-nums">{area.equipment_count}</span>
          </div>
        </div>

        {/* Render children recursively */}
        {hasChildren && area.children.map((child) => renderArea(child, depth + 1))}
      </div>
    )
  }

  return (
    <AppLayout>
    <div className="px-6 sm:px-8 py-8">
      <div className="mb-6">
        <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight">Plant Areas</h1>
        <p className="text-sm text-muted-foreground">Master data area / unit pabrik</p>
      </div>

      {loading ? (
        <div className="bg-card border border-border/70 rounded-xl">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-12 border-b border-border/50 last:border-b-0 animate-pulse bg-muted/10" />
          ))}
        </div>
      ) : areas.length === 0 ? (
        <div className="bg-card border border-border/70 rounded-xl p-8 text-center text-muted-foreground">
          <Layers className="h-8 w-8 mx-auto mb-2 opacity-40" />
          <p className="text-sm">No plant areas yet. Add a new area to get started.</p>
        </div>
      ) : (
        <div className="bg-card border border-border overflow-hidden rounded-xl">
          {/* Header */}
          <div className="grid grid-cols-[1fr_1fr_2fr_1fr] gap-4 px-6 py-4 text-xs font-medium text-muted-foreground uppercase tracking-wider border-b border-border">
            <span>Name</span>
            <span>Parent Area</span>
            <span>Description</span>
            <span>Equipment</span>
          </div>

          {/* Rows */}
          <div className="divide-y divide-border/50">
            {areas.map((area) => renderArea(area))}
          </div>
        </div>
      )}
    </div>
    </AppLayout>
  )
}
