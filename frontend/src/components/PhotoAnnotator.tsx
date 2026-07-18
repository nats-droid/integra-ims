'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import {
  MousePointer2,
  Square,
  Type,
  Hash,
  ZoomIn,
  ZoomOut,
  Undo2,
  Trash2,
  X,
  Save,
} from 'lucide-react'

// Dynamic fabric.js types — loaded at runtime
type FabricCanvas = any
type FabricObject = any

const COLORS = ['#EF4444', '#F59E0B', '#22C55E', '#3B82F6', '#8B5CF6', '#FFFFFF']

interface PhotoAnnotatorProps {
  photoUrl: string
  annotationJson: any
  onSave: (annotationJson: any, croppedUrl?: string) => void
  onClose: () => void
}

export default function PhotoAnnotator({
  photoUrl,
  annotationJson,
  onSave,
  onClose,
}: PhotoAnnotatorProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const fabricRef = useRef<FabricCanvas>(null)

  const [activeTool, setActiveTool] = useState<'select' | 'rect' | 'text' | 'number'>('select')
  const [activeColor, setActiveColor] = useState('#EF4444')
  const [numberCount, setNumberCount] = useState(1)
  const [zoom, setZoom] = useState(1)
  const [saving, setSaving] = useState(false)

  // Refs for mutable state used inside event handlers
  const toolRef = useRef(activeTool)
  const colorRef = useRef(activeColor)
  const countRef = useRef(numberCount)
  useEffect(() => { toolRef.current = activeTool }, [activeTool])
  useEffect(() => { colorRef.current = activeColor }, [activeColor])
  useEffect(() => { countRef.current = numberCount }, [numberCount])

  // ── Init fabric.js ───────────────────────────────────────────────
  useEffect(() => {
    let disposed = false
    ;(async () => {
      const fabric = await import('fabric')

      if (disposed || !canvasRef.current) return

      const canvas = new fabric.Canvas(canvasRef.current, {
        width: 800,
        height: 600,
        selection: true,
        backgroundColor: '#1e293b',
      })
      fabricRef.current = canvas

      // Load background photo
      fabric.Image.fromURL(photoUrl, { crossOrigin: 'anonymous' }).then((img: any) => {
        if (disposed) return
        const scale = Math.min(800 / (img.width || 1), 600 / (img.height || 1), 1)
        img.set({
          scaleX: scale,
          scaleY: scale,
          left: 0,
          top: 0,
          selectable: false,
          evented: false,
          hasControls: false,
        })
        canvas.backgroundImage = img
        canvas.renderAll()
      })

      // Load existing annotations
      if (annotationJson) {
        canvas.loadFromJSON(annotationJson).then(() => {
          canvas.renderAll()
        })
      }

      // ── Mouse handlers ──────────────────────────────────────────
      let startX = 0
      let startY = 0
      let drawing = false

      canvas.on('mouse:down', (opt: any) => {
        if (toolRef.current === 'rect') {
          const pointer = canvas.getScenePoint(opt.e)
          startX = pointer.x
          startY = pointer.y
          drawing = true
        }
      })

      canvas.on('mouse:up', (opt: any) => {
        if (toolRef.current === 'rect' && drawing) {
          const pointer = canvas.getScenePoint(opt.e)
          const w = Math.abs(pointer.x - startX)
          const h = Math.abs(pointer.y - startY)
          if (w > 5 && h > 5) {
            const rect = new fabric.Rect({
              left: Math.min(startX, pointer.x),
              top: Math.min(startY, pointer.y),
              width: w,
              height: h,
              fill: 'transparent',
              stroke: colorRef.current,
              strokeWidth: 2,
              hasControls: true,
              selectable: true,
            })
            canvas.add(rect)
          }
          drawing = false
        }
      })
    })()

    return () => {
      disposed = true
      if (fabricRef.current) {
        fabricRef.current.dispose()
        fabricRef.current = null
      }
    }
  }, [photoUrl, annotationJson])

  // ── Tool mode ───────────────────────────────────────────────────
  useEffect(() => {
    const canvas = fabricRef.current
    if (!canvas) return

    if (activeTool === 'select') {
      canvas.defaultCursor = 'default'
      canvas.selection = true
      canvas.forEachObject((obj: FabricObject) => {
        if (canvas.backgroundImage && obj === canvas.backgroundImage) return
        obj.selectable = true
        obj.evented = true
      })
    } else {
      canvas.defaultCursor = 'crosshair'
      canvas.selection = false
      canvas.discardActiveObject()
      canvas.forEachObject((obj: FabricObject) => {
        if (canvas.backgroundImage && obj === canvas.backgroundImage) return
        obj.selectable = false
        obj.evented = false
      })
    }
    canvas.renderAll()
  }, [activeTool])

  // ── Add Text ────────────────────────────────────────────────────
  const handleAddText = useCallback(async () => {
    const fabric = await import('fabric')
    const canvas = fabricRef.current
    if (!canvas) return

    const text = prompt('Enter annotation text:')
    if (!text) return

    const itext = new fabric.IText(text, {
      left: 100,
      top: 100,
      fontSize: 18,
      fontWeight: 'bold',
      fill: colorRef.current,
      editable: true,
    })
    canvas.add(itext)
    canvas.setActiveObject(itext)
    canvas.renderAll()
  }, [])

  // ── Add Number badge ────────────────────────────────────────────
  const handleAddNumber = useCallback(async () => {
    const fabric = await import('fabric')
    const canvas = fabricRef.current
    if (!canvas) return

    const n = countRef.current

    const circle = new fabric.Circle({
      radius: 16,
      fill: colorRef.current,
      originX: 'center',
      originY: 'center',
    })

    const text = new fabric.Text(String(n), {
      fontSize: 14,
      fontWeight: 'bold',
      fill: '#FFFFFF',
      originX: 'center',
      originY: 'center',
    })

    const group = new fabric.Group([circle, text], {
      left: 120,
      top: 120,
      hasControls: true,
      selectable: true,
    })

    canvas.add(group)
    canvas.setActiveObject(group)
    canvas.renderAll()

    setNumberCount(n + 1)
  }, [])

  // ── Zoom ────────────────────────────────────────────────────────
  const handleZoom = useCallback((delta: number) => {
    const canvas = fabricRef.current
    if (!canvas) return

    const next = Math.max(0.5, Math.min(zoom + delta, 3))
    setZoom(next)
    canvas.setZoom(next)
    canvas.renderAll()
  }, [zoom])

  // ── Undo (remove selected) ─────────────────────────────────────
  const handleUndo = useCallback(() => {
    const canvas = fabricRef.current
    if (!canvas) return

    const obj = canvas.getActiveObject()
    if (obj && obj !== canvas.backgroundImage) {
      canvas.remove(obj)
      canvas.discardActiveObject()
      canvas.renderAll()
    }
  }, [])

  // ── Clear all annotations ───────────────────────────────────────
  const handleClear = useCallback(() => {
    const canvas = fabricRef.current
    if (!canvas) return

    const bg = canvas.backgroundImage
    canvas.clear()
    canvas.backgroundColor = '#1e293b'
    if (bg) {
      canvas.backgroundImage = bg
    }
    canvas.renderAll()
    setNumberCount(1)
  }, [])

  // ── Save ────────────────────────────────────────────────────────
  const handleSave = useCallback(async () => {
    const canvas = fabricRef.current
    if (!canvas) return

    setSaving(true)
    try {
      const json = canvas.toJSON()

      // Temporarily hide background, export cropped annotation
      const bg = canvas.backgroundImage
      canvas.backgroundImage = undefined as any
      const dataUrl = canvas.toDataURL({ format: 'jpeg', quality: 0.9 })
      canvas.backgroundImage = bg

      // Upload to Supabase Storage
      let croppedUrl: string | undefined
      if (dataUrl) {
        try {
          const { createClient } = await import('@supabase/supabase-js')
          const sb = createClient(
            process.env.NEXT_PUBLIC_SUPABASE_URL!,
            process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
          )

          const base64ToBlob = (dataUrl: string): Blob => {
            const arr = dataUrl.split(',')
            const mime = arr[0].match(/:(.*?);/)?.[1] || 'image/jpeg'
            const bstr = atob(arr[1])
            const u8 = new Uint8Array(bstr.length)
            for (let i = 0; i < bstr.length; i++) u8[i] = bstr.charCodeAt(i)
            return new Blob([u8], { type: mime })
          }

          const blob = base64ToBlob(dataUrl)
          const path = `annotated/${Date.now()}_${Math.random().toString(36).slice(2, 8)}.jpg`

          const { error } = await sb.storage.from('inspection-photos').upload(path, blob)
          if (!error) {
            const { data } = sb.storage.from('inspection-photos').getPublicUrl(path)
            croppedUrl = data.publicUrl
          }
        } catch (uploadErr) {
          console.warn('Upload failed, saving annotation only:', uploadErr)
        }
      }

      onSave(json, croppedUrl)
    } finally {
      setSaving(false)
    }
  }, [onSave])

  // ── Render ──────────────────────────────────────────────────────
  const tools = [
    { id: 'select' as const, icon: MousePointer2, label: 'Select' },
    { id: 'rect' as const, icon: Square, label: 'Rectangle' },
    { id: 'text' as const, icon: Type, label: 'Text' },
    { id: 'number' as const, icon: Hash, label: 'Number' },
  ]

  return (
    <div className="fixed inset-0 z-50 bg-black/90 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-slate-900 border-b border-slate-700">
        <h2 className="text-white font-semibold text-sm">Photo Annotator</h2>
        <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
          <X className="h-5 w-5" />
        </button>
      </div>

      {/* Toolbar */}
      <div className="flex items-center gap-2 px-4 py-2 bg-slate-800 border-b border-slate-700">
        {/* Tools */}
        {tools.map((t) => {
          const Icon = t.icon
          const isSpecial = t.id === 'text' || t.id === 'number'
          return (
            <button
              key={t.id}
              title={t.label}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-medium transition-colors ${
                activeTool === t.id
                  ? 'bg-indigo-600 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
              onClick={() => {
                setActiveTool(t.id)
                if (t.id === 'text') handleAddText()
                if (t.id === 'number') handleAddNumber()
              }}
            >
              <Icon className="h-3.5 w-3.5" />
              {t.label}
            </button>
          )
        })}

        {/* Separator */}
        <div className="w-px h-6 bg-slate-600 mx-1" />

        {/* Colors */}
        {COLORS.map((c) => (
          <button
            key={c}
            title={c}
            className={`w-6 h-6 rounded-full border-2 transition-transform ${
              activeColor === c ? 'border-white scale-110' : 'border-slate-600 hover:scale-105'
            }`}
            style={{ backgroundColor: c }}
            onClick={() => setActiveColor(c)}
          />
        ))}

        {/* Separator */}
        <div className="w-px h-6 bg-slate-600 mx-1" />

        {/* Zoom */}
        <button
          onClick={() => handleZoom(-0.2)}
          className="p-1.5 rounded bg-slate-700 text-slate-300 hover:bg-slate-600"
          title="Zoom Out"
        >
          <ZoomOut className="h-3.5 w-3.5" />
        </button>
        <span className="text-xs text-slate-400 w-12 text-center">
          {Math.round(zoom * 100)}%
        </span>
        <button
          onClick={() => handleZoom(0.2)}
          className="p-1.5 rounded bg-slate-700 text-slate-300 hover:bg-slate-600"
          title="Zoom In"
        >
          <ZoomIn className="h-3.5 w-3.5" />
        </button>

        {/* Separator */}
        <div className="w-px h-6 bg-slate-600 mx-1" />

        <button
          onClick={handleUndo}
          className="p-1.5 rounded bg-slate-700 text-slate-300 hover:bg-slate-600"
          title="Undo (remove selected)"
        >
          <Undo2 className="h-3.5 w-3.5" />
        </button>
        <button
          onClick={handleClear}
          className="p-1.5 rounded bg-slate-700 text-slate-300 hover:bg-red-600 hover:text-white"
          title="Clear all annotations"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Save */}
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-indigo-600 text-white text-xs font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
        >
          <Save className="h-3.5 w-3.5" />
          {saving ? 'Saving…' : 'Save'}
        </button>
      </div>

      {/* Canvas area */}
      <div className="flex-1 overflow-auto flex items-center justify-center p-4">
        <div className="border border-slate-700 rounded-lg overflow-hidden shadow-2xl">
          <canvas ref={canvasRef} />
        </div>
      </div>
    </div>
  )
}
