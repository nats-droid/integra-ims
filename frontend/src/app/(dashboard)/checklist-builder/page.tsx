'use client'

import { useState, useEffect, useCallback } from 'react'
import { createClient } from '@/lib/supabase/client'
import { useRouter } from 'next/navigation'
import AppLayout from '@/components/layout/app-layout'
import { ClipboardList, Plus, X, ChevronUp, ChevronDown, Trash2, Save } from 'lucide-react'
import { cn } from '@/utils/cn'
import { toast } from 'sonner'

// ── Types ────────────────────────────────────────────────────────────────────
interface ChecklistTemplate {
  id: string
  equipment_type: string
  section: string
  item_code: string
  item_description: string
  item_type: string
  display_order: number
  is_active: boolean
  company_id: string | null
  unit: string | null
  is_required: boolean | null
  inspection_scope: string | null
}

interface EditableItem extends ChecklistTemplate {
  _deleted?: boolean
  _isNew?: boolean
}

interface TemplateGroup {
  key: string
  equipment_type: string
  inspection_scope: string
  count: number
  is_global: boolean
}

interface Section {
  name: string
  items: EditableItem[]
}

// ── Labels ───────────────────────────────────────────────────────────────────
const EQUIPMENT_LABELS: Record<string, string> = {
  piping: 'Piping',
  pressure_vessel: 'Pressure Vessel',
  heat_exchanger: 'Heat Exchanger',
  storage_tank_fixed: 'Storage Tank (Fixed Roof)',
  storage_tank_float: 'Storage Tank (Floating Roof)',
}

const SCOPE_LABELS: Record<string, string> = {
  external: 'External',
  internal: 'Internal',
  general: 'General',
}

const ITEM_TYPE_LABELS: Record<string, string> = {
  yes_no_na: 'Yes/No/NA',
  yes_no: 'Yes/No',
  rating: 'Rating',
  pass_fail: 'Pass/Fail',
  numeric: 'Numeric',
  text: 'Text',
}

const EQUIPMENT_OPTIONS = [
  'piping',
  'pressure_vessel',
  'heat_exchanger',
  'storage_tank_fixed',
  'storage_tank_float',
] as const

const SCOPE_OPTIONS = ['external', 'internal', 'general'] as const

// Print RLS policies to console
console.log(`
============================================================
SUPABASE RLS POLICIES FOR checklist_templates
Run these in Supabase Dashboard SQL Editor:
============================================================

ALTER TABLE checklist_templates ENABLE ROW LEVEL SECURITY;

CREATE POLICY "allow_read_checklist_templates"
ON checklist_templates FOR SELECT TO authenticated
USING (company_id IS NULL OR company_id = (
  SELECT company_id FROM app_users 
  WHERE auth_user_id = auth.uid()));

CREATE POLICY "supervisor_insert_checklist"
ON checklist_templates FOR INSERT TO authenticated
WITH CHECK (company_id = (SELECT company_id FROM app_users 
  WHERE auth_user_id = auth.uid())
  AND (SELECT role FROM app_users 
  WHERE auth_user_id = auth.uid()) = 'supervisor');

CREATE POLICY "supervisor_update_checklist"
ON checklist_templates FOR UPDATE TO authenticated
USING (company_id = (SELECT company_id FROM app_users 
  WHERE auth_user_id = auth.uid())
  AND (SELECT role FROM app_users 
  WHERE auth_user_id = auth.uid()) = 'supervisor');

CREATE POLICY "supervisor_delete_checklist"
ON checklist_templates FOR DELETE TO authenticated
USING (company_id = (SELECT company_id FROM app_users 
  WHERE auth_user_id = auth.uid())
  AND (SELECT role FROM app_users 
  WHERE auth_user_id = auth.uid()) = 'supervisor');

============================================================
`)

// ── Main Component ───────────────────────────────────────────────────────────
export default function ChecklistBuilderPage() {
  const router = useRouter()
  const supabase = createClient()

  const [loading, setLoading] = useState(true)
  const [companyId, setCompanyId] = useState<string | null>(null)
  const [groups, setGroups] = useState<TemplateGroup[]>([])
  const [selectedGroup, setSelectedGroup] = useState<TemplateGroup | null>(null)
  const [templates, setTemplates] = useState<ChecklistTemplate[]>([])
  const [editableSections, setEditableSections] = useState<Section[]>([])
  const [itemsLoading, setItemsLoading] = useState(false)
  const [cloning, setCloning] = useState(false)
  const [saving, setSaving] = useState(false)
  const [showNewModal, setShowNewModal] = useState(false)
  const [newEqType, setNewEqType] = useState<string>('pressure_vessel')
  const [newScope, setNewScope] = useState<string>('external')
  const [creating, setCreating] = useState(false)

  // ── Role Guard + profile ───────────────────────────────────────────────────
  useEffect(() => {
    async function checkRole() {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) {
        router.push('/auth/login')
        return
      }

      const { data: profile } = await supabase
        .from('app_users')
        .select('role, company_id')
        .eq('auth_user_id', user.id)
        .single()

      if (!profile) {
        router.push('/dashboard')
        return
      }

      const role = (profile as { role: string }).role
      const cid = (profile as { company_id: string }).company_id
      setCompanyId(cid)

      if (role !== 'supervisor' && role !== 'super_admin') {
        router.push('/dashboard')
        return
      }

      setLoading(false)
    }
    checkRole()
  }, [supabase, router])

  // ── Load Template Groups ───────────────────────────────────────────────────
  const loadGroups = useCallback(async () => {
    if (!companyId) return

    const { data, error } = await supabase
      .from('checklist_templates')
      .select('equipment_type, inspection_scope, company_id')
      .or(`company_id.is.null,company_id.eq.${companyId}`)

    if (error || !data) {
      toast.error('Failed to load templates')
      return
    }

    const groupMap = new Map<string, TemplateGroup>()
    data.forEach((row: { equipment_type: string; inspection_scope: string | null; company_id: string | null }) => {
      const isGlobal = row.company_id === null
      const scope = row.inspection_scope || 'general'
      const key = `${row.equipment_type}|${scope}|${isGlobal ? 'global' : 'company'}`
      if (!groupMap.has(key)) {
        groupMap.set(key, {
          key,
          equipment_type: row.equipment_type,
          inspection_scope: scope,
          count: 0,
          is_global: isGlobal,
        })
      }
      groupMap.get(key)!.count++
    })

    const sorted = Array.from(groupMap.values()).sort((a, b) => {
      if (a.equipment_type !== b.equipment_type) {
        return a.equipment_type.localeCompare(b.equipment_type)
      }
      if (a.inspection_scope !== b.inspection_scope) {
        return a.inspection_scope.localeCompare(b.inspection_scope)
      }
      return a.is_global === b.is_global ? 0 : a.is_global ? -1 : 1
    })

    setGroups(sorted)
  }, [supabase, companyId])

  useEffect(() => {
    if (companyId) loadGroups()
  }, [companyId, loadGroups])

  // ── Build sections from templates ──────────────────────────────────────────
  const buildSections = (items: ChecklistTemplate[]): Section[] => {
    const map = new Map<string, EditableItem[]>()
    const order: string[] = []
    items
      .slice()
      .sort((a, b) => a.display_order - b.display_order)
      .forEach((t) => {
        if (!map.has(t.section)) {
          map.set(t.section, [])
          order.push(t.section)
        }
        map.get(t.section)!.push({ ...t })
      })
    return order.map((name) => ({ name, items: map.get(name)! }))
  }

  // ── Load Templates for Selected Group ──────────────────────────────────────
  useEffect(() => {
    if (!selectedGroup || !companyId) return

    async function loadTemplates() {
      setItemsLoading(true)
      let query = supabase
        .from('checklist_templates')
        .select(
          'id, equipment_type, section, item_code, item_description, item_type, display_order, is_active, company_id, unit, is_required, inspection_scope'
        )
        .eq('equipment_type', selectedGroup!.equipment_type)
        .eq('inspection_scope', selectedGroup!.inspection_scope)
        .order('display_order')

      if (selectedGroup!.is_global) {
        query = query.is('company_id', null)
      } else {
        query = query.eq('company_id', companyId!)
      }

      const { data, error } = await query
      if (error) {
        toast.error('Failed to load items')
        setTemplates([])
        setEditableSections([])
      } else {
        const rows = (data || []) as ChecklistTemplate[]
        setTemplates(rows)
        if (!selectedGroup!.is_global) {
          setEditableSections(buildSections(rows))
        } else {
          setEditableSections([])
        }
      }
      setItemsLoading(false)
    }

    loadTemplates()
  }, [supabase, selectedGroup, companyId])

  // ── Recalculate codes & display_order ──────────────────────────────────────
  const renumber = (sections: Section[]): Section[] => {
    let globalOrder = 1
    return sections.map((sec, sIdx) => {
      let visible = 0
      const items = sec.items.map((item) => {
        if (item._deleted) return item
        visible++
        return {
          ...item,
          item_code: `${sIdx + 1}.${visible}`,
          display_order: globalOrder++,
          section: sec.name,
        }
      })
      return { ...sec, items }
    })
  }

  // ── Editable helpers ───────────────────────────────────────────────────────
  const updateSectionName = (sIdx: number, name: string) => {
    setEditableSections((prev) => {
      const next = prev.map((s, i) => (i === sIdx ? { ...s, name } : s))
      return renumber(next)
    })
  }

  const addItem = (sIdx: number) => {
    if (!selectedGroup || !companyId) return
    setEditableSections((prev) => {
      const next = prev.map((s, i) => {
        if (i !== sIdx) return s
        const newItem: EditableItem = {
          id: `new-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
          equipment_type: selectedGroup.equipment_type,
          section: s.name,
          item_code: '0.0',
          item_description: '',
          item_type: 'yes_no_na',
          display_order: 0,
          is_active: true,
          company_id: companyId,
          unit: '',
          is_required: true,
          inspection_scope: selectedGroup.inspection_scope,
          _isNew: true,
        }
        return { ...s, items: [...s.items, newItem] }
      })
      return renumber(next)
    })
  }

  const deleteSection = (sIdx: number) => {
    setEditableSections((prev) => {
      const sec = prev[sIdx]
      const activeItems = sec.items.filter((i) => !i._deleted)
      if (activeItems.length > 0) return prev
      return renumber(prev.filter((_, i) => i !== sIdx))
    })
  }

  const addSection = () => {
    if (!selectedGroup || !companyId) return
    setEditableSections((prev) => {
      const n = prev.length + 1
      return renumber([
        ...prev,
        {
          name: `${n}. New Section`,
          items: [],
        },
      ])
    })
  }

  const updateItem = (sIdx: number, iIdx: number, patch: Partial<EditableItem>) => {
    setEditableSections((prev) => {
      const next = prev.map((s, si) => {
        if (si !== sIdx) return s
        return {
          ...s,
          items: s.items.map((it, ii) => (ii === iIdx ? { ...it, ...patch } : it)),
        }
      })
      return renumber(next)
    })
  }

  const markDeleted = (sIdx: number, iIdx: number) => {
    setEditableSections((prev) => {
      const next = prev.map((s, si) => {
        if (si !== sIdx) return s
        return {
          ...s,
          items: s.items.map((it, ii) =>
            ii === iIdx ? { ...it, _deleted: !it._deleted } : it
          ),
        }
      })
      return renumber(next)
    })
  }

  const moveItem = (sIdx: number, iIdx: number, dir: -1 | 1) => {
    setEditableSections((prev) => {
      const next = prev.map((s, si) => {
        if (si !== sIdx) return s
        const items = [...s.items]
        const j = iIdx + dir
        if (j < 0 || j >= items.length) return s
        ;[items[iIdx], items[j]] = [items[j], items[iIdx]]
        return { ...s, items }
      })
      return renumber(next)
    })
  }

  // ── Clone Global Template ───────────────────────────────────────────────────
  const cloneToCompany = async () => {
    if (!selectedGroup || !companyId || !selectedGroup.is_global) return
    setCloning(true)
    try {
      const newItems = templates.map((t) => ({
        equipment_type: t.equipment_type,
        section: t.section,
        item_code: t.item_code,
        item_description: t.item_description,
        item_type: t.item_type,
        display_order: t.display_order,
        is_active: t.is_active,
        company_id: companyId,
        unit: t.unit,
        is_required: t.is_required ?? true,
        inspection_scope: t.inspection_scope,
      }))

      const { error } = await supabase.from('checklist_templates').insert(newItems as never)
      if (error) {
        toast.error(error.message || 'Clone failed')
      } else {
        toast.success(`Cloned ${newItems.length} items to My Templates`)
        await loadGroups()
        setSelectedGroup({
          key: `${selectedGroup.equipment_type}|${selectedGroup.inspection_scope}|company`,
          equipment_type: selectedGroup.equipment_type,
          inspection_scope: selectedGroup.inspection_scope,
          count: newItems.length,
          is_global: false,
        })
      }
    } finally {
      setCloning(false)
    }
  }

  // ── Create New Template (company-owned seed row) ────────────────────────────
  const createNewTemplate = async () => {
    if (!companyId) return
    setCreating(true)
    try {
      const { error } = await supabase.from('checklist_templates').insert({
        equipment_type: newEqType,
        section: '1. External Appearance',
        item_code: '1.1',
        item_description: 'New checklist item',
        item_type: 'yes_no_na',
        display_order: 1,
        is_active: true,
        company_id: companyId,
        unit: '',
        is_required: true,
        inspection_scope: newScope,
      } as never)

      if (error) {
        toast.error(error.message || 'Create failed')
      } else {
        toast.success('Template created')
        setShowNewModal(false)
        await loadGroups()
        setSelectedGroup({
          key: `${newEqType}|${newScope}|company`,
          equipment_type: newEqType,
          inspection_scope: newScope,
          count: 1,
          is_global: false,
        })
      }
    } finally {
      setCreating(false)
    }
  }

  // ── Save All Changes ───────────────────────────────────────────────────────
  const saveAllChanges = async () => {
    if (!selectedGroup || !companyId || selectedGroup.is_global) return
    setSaving(true)
    try {
      const sections = renumber(editableSections)
      const toDelete: string[] = []
      const toUpsert: Record<string, unknown>[] = []

      sections.forEach((sec) => {
        sec.items.forEach((item) => {
          if (item._deleted) {
            if (!item._isNew) toDelete.push(item.id)
            return
          }
          const row: Record<string, unknown> = {
            equipment_type: selectedGroup.equipment_type,
            section: sec.name,
            item_code: item.item_code,
            item_description: item.item_description,
            item_type: item.item_type,
            display_order: item.display_order,
            is_active: item.is_active,
            company_id: companyId,
            unit: item.item_type === 'numeric' ? item.unit || '' : '',
            is_required: item.is_required ?? true,
            inspection_scope: selectedGroup.inspection_scope,
          }
          if (!item._isNew) {
            row.id = item.id
          }
          toUpsert.push(row)
        })
      })

      if (toDelete.length > 0) {
        const { error } = await supabase
          .from('checklist_templates')
          .delete()
          .in('id', toDelete)
        if (error) throw error
      }

      if (toUpsert.length > 0) {
        const { error } = await supabase
          .from('checklist_templates')
          .upsert(toUpsert as never)
        if (error) throw error
      }

      toast.success('Template saved')
      await loadGroups()

      // re-fetch items
      const { data } = await supabase
        .from('checklist_templates')
        .select(
          'id, equipment_type, section, item_code, item_description, item_type, display_order, is_active, company_id, unit, is_required, inspection_scope'
        )
        .eq('equipment_type', selectedGroup.equipment_type)
        .eq('inspection_scope', selectedGroup.inspection_scope)
        .eq('company_id', companyId)
        .order('display_order')

      const rows = (data || []) as ChecklistTemplate[]
      setTemplates(rows)
      setEditableSections(buildSections(rows))
      setSelectedGroup((g) => (g ? { ...g, count: rows.length } : g))
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Save failed'
      toast.error(msg)
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <AppLayout>
        <div className="flex min-h-[60vh] items-center justify-center">
          <div className="flex flex-col items-center gap-3">
            <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            <p className="text-sm text-muted-foreground">Loading...</p>
          </div>
        </div>
      </AppLayout>
    )
  }

  return (
    <AppLayout>
      <div className="flex h-[calc(100vh-4rem)] -m-6 overflow-hidden bg-background">
        {/* Left Panel */}
        <div className="w-72 border-r border-border overflow-y-auto flex flex-col">
          <div className="px-4 py-3 border-b border-border">
            <h2 className="text-sm font-semibold text-foreground">Checklist Templates</h2>
          </div>

          <div className="flex-1 p-2 space-y-0.5 overflow-y-auto">
            {groups.length === 0 ? (
              <p className="text-xs text-muted-foreground px-3 py-4">No templates found</p>
            ) : (
              groups.map((group) => {
                const isSelected = selectedGroup?.key === group.key
                return (
                  <button
                    key={group.key}
                    onClick={() => setSelectedGroup(group)}
                    className={cn(
                      'w-full text-left px-3 py-2.5 rounded-lg text-sm transition-colors border-l-2',
                      isSelected
                        ? 'bg-indigo-50 border-indigo-600 text-indigo-900 dark:bg-indigo-950/40 dark:text-indigo-100'
                        : 'border-transparent hover:bg-muted'
                    )}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <p className="font-medium truncate">
                          {EQUIPMENT_LABELS[group.equipment_type] || group.equipment_type}
                          {' — '}
                          {SCOPE_LABELS[group.inspection_scope] || group.inspection_scope}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {group.count} items
                        </p>
                      </div>
                      {group.is_global && (
                        <span className="px-1.5 py-0.5 text-[10px] font-medium bg-gray-100 text-gray-600 rounded dark:bg-gray-800 dark:text-gray-300 flex-shrink-0">
                          Global
                        </span>
                      )}
                    </div>
                  </button>
                )
              })
            )}
          </div>

          <div className="p-2 border-t border-border">
            <button
              onClick={() => setShowNewModal(true)}
              className="w-full flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium text-indigo-600 border border-indigo-600 rounded-lg hover:bg-indigo-50 dark:hover:bg-indigo-950/30 transition-colors"
            >
              <Plus className="h-4 w-4" />
              New Template
            </button>
          </div>
        </div>

        {/* Right Panel */}
        <div className="flex-1 overflow-y-auto">
          {!selectedGroup ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center text-muted-foreground">
                <ClipboardList className="h-12 w-12 mx-auto mb-3 opacity-30" />
                <p className="text-sm">Select a template from the left panel</p>
              </div>
            </div>
          ) : itemsLoading ? (
            <div className="flex items-center justify-center h-full">
              <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            </div>
          ) : selectedGroup.is_global ? (
            <div className="p-6">
              <div className="flex items-center justify-between mb-6 gap-4 flex-wrap">
                <div>
                  <h3 className="text-lg font-semibold text-foreground">
                    {EQUIPMENT_LABELS[selectedGroup.equipment_type] || selectedGroup.equipment_type}
                    {' — '}
                    {SCOPE_LABELS[selectedGroup.inspection_scope] || selectedGroup.inspection_scope}
                  </h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    {templates.length} items · Global (read-only)
                  </p>
                </div>
                <button
                  onClick={cloneToCompany}
                  disabled={cloning || templates.length === 0}
                  className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50"
                >
                  {cloning ? 'Cloning…' : 'Clone to My Templates'}
                </button>
              </div>

              <div className="space-y-2">
                {templates.map((t) => (
                  <div key={t.id} className="px-4 py-3 bg-card border border-border rounded-lg">
                    <div className="flex items-start gap-3">
                      <span className="text-xs font-mono text-muted-foreground mt-0.5 w-10 flex-shrink-0">
                        {t.item_code}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-foreground">{t.item_description}</p>
                        <p className="text-xs text-muted-foreground mt-1">{t.section}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="p-6">
              {/* Header */}
              <div className="flex items-center justify-between mb-6 gap-4 flex-wrap">
                <div>
                  <h3 className="text-lg font-semibold text-foreground">
                    {EQUIPMENT_LABELS[selectedGroup.equipment_type] || selectedGroup.equipment_type}
                    {' — '}
                    <span className="px-2 py-0.5 text-xs bg-indigo-100 text-indigo-700 rounded dark:bg-indigo-900/30 dark:text-indigo-300">
                      {SCOPE_LABELS[selectedGroup.inspection_scope] || selectedGroup.inspection_scope}
                    </span>
                  </h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    {editableSections.reduce((sum, s) => sum + s.items.filter(i => !i._deleted).length, 0)} items · Company template (editable)
                  </p>
                </div>
                <button
                  onClick={saveAllChanges}
                  disabled={saving}
                  className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50"
                >
                  <Save className="h-4 w-4" />
                  {saving ? 'Saving…' : 'Save All Changes'}
                </button>
              </div>

              {/* Sections */}
              <div className="space-y-4">
                {editableSections.map((section, sIdx) => (
                  <div key={sIdx} className="border border-border rounded-lg overflow-hidden">
                    {/* Section Header */}
                    <div className="bg-gray-50 dark:bg-gray-900/30 px-4 py-2 flex items-center justify-between gap-3 border-b border-border">
                      <input
                        type="text"
                        value={section.name}
                        onChange={(e) => updateSectionName(sIdx, e.target.value)}
                        className="flex-1 font-medium text-sm bg-transparent border-none focus:outline-none focus:ring-1 focus:ring-indigo-500 rounded px-1"
                      />
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => addItem(sIdx)}
                          className="text-xs text-indigo-600 hover:text-indigo-700 font-medium"
                        >
                          Add Item
                        </button>
                        <button
                          onClick={() => deleteSection(sIdx)}
                          disabled={section.items.filter(i => !i._deleted).length > 0}
                          className="text-xs text-gray-500 hover:text-gray-700 disabled:opacity-30 disabled:cursor-not-allowed"
                        >
                          Delete Section
                        </button>
                      </div>
                    </div>

                    {/* Section Items */}
                    <div className="divide-y divide-border">
                      {section.items.map((item, iIdx) => (
                        <div
                          key={item.id}
                          className={cn(
                            'px-4 py-2 flex items-center gap-2',
                            item._deleted && 'opacity-40 bg-red-50 dark:bg-red-900/10'
                          )}
                        >
                          {/* Move buttons */}
                          <div className="flex flex-col gap-0.5">
                            <button
                              onClick={() => moveItem(sIdx, iIdx, -1)}
                              disabled={iIdx === 0 || item._deleted}
                              className="p-0.5 rounded hover:bg-muted disabled:opacity-30"
                            >
                              <ChevronUp className="h-3 w-3" />
                            </button>
                            <button
                              onClick={() => moveItem(sIdx, iIdx, 1)}
                              disabled={iIdx === section.items.length - 1 || item._deleted}
                              className="p-0.5 rounded hover:bg-muted disabled:opacity-30"
                            >
                              <ChevronDown className="h-3 w-3" />
                            </button>
                          </div>

                          {/* Item code */}
                          <span className={cn(
                            'text-xs text-gray-400 w-12 flex-shrink-0 font-mono',
                            item._deleted && 'line-through'
                          )}>
                            {item.item_code}
                          </span>

                          {/* Description */}
                          <input
                            type="text"
                            value={item.item_description}
                            onChange={(e) => updateItem(sIdx, iIdx, { item_description: e.target.value })}
                            disabled={item._deleted}
                            className={cn(
                              'flex-1 text-sm border border-border rounded px-2 py-1 bg-background',
                              item._deleted && 'line-through'
                            )}
                            placeholder="Item description"
                          />

                          {/* Item type */}
                          <select
                            value={item.item_type}
                            onChange={(e) => updateItem(sIdx, iIdx, { item_type: e.target.value })}
                            disabled={item._deleted}
                            className="w-36 text-xs border border-border rounded px-2 py-1 bg-background"
                          >
                            {Object.entries(ITEM_TYPE_LABELS).map(([key, label]) => (
                              <option key={key} value={key}>
                                {label}
                              </option>
                            ))}
                          </select>

                          {/* Unit (only for numeric) */}
                          {item.item_type === 'numeric' && (
                            <input
                              type="text"
                              value={item.unit || ''}
                              onChange={(e) => updateItem(sIdx, iIdx, { unit: e.target.value })}
                              disabled={item._deleted}
                              className="w-16 text-xs border border-border rounded px-2 py-1 bg-background"
                              placeholder="Unit"
                            />
                          )}

                          {/* Required checkbox */}
                          <label className="flex items-center gap-1.5 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={item.is_required ?? true}
                              onChange={(e) => updateItem(sIdx, iIdx, { is_required: e.target.checked })}
                              disabled={item._deleted}
                              className="rounded border-gray-300"
                            />
                            <span className="text-xs text-muted-foreground">Req</span>
                          </label>

                          {/* Delete button */}
                          <button
                            onClick={() => markDeleted(sIdx, iIdx)}
                            className={cn(
                              'p-1 rounded hover:bg-muted',
                              item._deleted ? 'text-green-600' : 'text-red-500'
                            )}
                            title={item._deleted ? 'Restore' : 'Delete'}
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}

                {/* Add Section */}
                <button
                  onClick={addSection}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium text-indigo-600 border border-indigo-600 border-dashed rounded-lg hover:bg-indigo-50 dark:hover:bg-indigo-950/30 transition-colors"
                >
                  <Plus className="h-4 w-4" />
                  Add Section
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* New Template Modal */}
      {showNewModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-card border border-border rounded-xl p-6 w-full max-w-md shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-foreground">New Template</h3>
              <button
                onClick={() => setShowNewModal(false)}
                className="p-1 rounded-lg hover:bg-muted"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1.5">
                  Equipment Type
                </label>
                <select
                  value={newEqType}
                  onChange={(e) => setNewEqType(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background"
                >
                  {EQUIPMENT_OPTIONS.map((eq) => (
                    <option key={eq} value={eq}>
                      {EQUIPMENT_LABELS[eq]}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-muted-foreground mb-1.5">
                  Inspection Scope
                </label>
                <select
                  value={newScope}
                  onChange={(e) => setNewScope(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background"
                >
                  {SCOPE_OPTIONS.map((s) => (
                    <option key={s} value={s}>
                      {SCOPE_LABELS[s]}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex gap-2 mt-6 justify-end">
              <button
                onClick={() => setShowNewModal(false)}
                className="px-4 py-2 text-sm rounded-lg border border-border hover:bg-muted"
              >
                Cancel
              </button>
              <button
                onClick={createNewTemplate}
                disabled={creating}
                className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50"
              >
                {creating ? 'Creating…' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}
    </AppLayout>
  )
}
