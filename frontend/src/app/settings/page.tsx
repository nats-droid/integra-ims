'use client'

import { useState, useEffect } from 'react'
import { Settings, Brain, Save, Loader2, CheckCircle, AlertTriangle, Eye, EyeOff } from 'lucide-react'
import AppLayout from '@/components/layout/app-layout'
import { createClient } from '@/lib/supabase/client'
import { toast } from 'sonner'

// ── Types ────────────────────────────────────────────────────────────────────
interface AIConfigStatus {
  has_key: boolean
  provider: string | null
}

// ── Component ────────────────────────────────────────────────────────────────
export default function SettingsPage() {
  const [companyId, setCompanyId] = useState<string | null>(null)
  const [userRole, setUserRole] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)

  // AI Config form
  const [provider, setProvider] = useState<string>('gemini')
  const [apiKey, setApiKey] = useState('')
  const [showKey, setShowKey] = useState(false)
  const [configStatus, setConfigStatus] = useState<AIConfigStatus | null>(null)

  const supabase = createClient()
  const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  // Load user profile + AI config
  useEffect(() => {
    async function load() {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) return

      const { data: profile } = await supabase
        .from('app_users')
        .select('company_id, role')
        .eq('auth_user_id', user.id)
        .single()

      if (profile) {
        setCompanyId((profile as Record<string, unknown>).company_id as string)
        setUserRole((profile as Record<string, unknown>).role as string)

        // Fetch AI config status
        const { data: { session } } = await supabase.auth.getSession()
        if (session) {
          try {
            const res = await fetch(`${backendUrl}/api/v1/ai/status/${(profile as Record<string, unknown>).company_id}`, {
              headers: { Authorization: `Bearer ${session.access_token}` },
            })
            if (res.ok) {
              const status: AIConfigStatus = await res.json()
              setConfigStatus(status)
              if (status.provider) {
                setProvider(status.provider)
              }
            }
          } catch {
            // silently fail
          }
        }
      }
      setLoading(false)
    }
    load()
  }, [supabase, backendUrl])

  // Save AI config
  const handleSave = async () => {
    if (!companyId || !apiKey.trim()) {
      toast.error('Please enter an API key')
      return
    }
    setSaving(true)

    const { data: { session } } = await supabase.auth.getSession()
    if (!session) {
      toast.error('Not authenticated')
      setSaving(false)
      return
    }

    try {
      // Save to companies table directly via Supabase
      const { error } = await (supabase
        .from('companies') as unknown as { update: (data: Record<string, unknown>) => { eq: (col: string, val: string) => Promise<{ error: unknown }> } })
        .update({
          llm_provider: provider,
          llm_api_key: apiKey.trim(),
        })
        .eq('id', companyId)

      if (error) {
        toast.error(`Failed to save: ${(error as Error).message || 'Unknown error'}`)
      } else {
        toast.success('AI configuration saved')
        setConfigStatus({ has_key: true, provider })
        setApiKey('')
      }
    } catch {
      toast.error('Network error saving config')
    } finally {
      setSaving(false)
    }
  }

  // Test AI config
  const handleTest = async () => {
    if (!companyId) return
    setTesting(true)

    const { data: { session } } = await supabase.auth.getSession()
    if (!session) {
      toast.error('Not authenticated')
      setTesting(false)
      return
    }

    try {
      const res = await fetch(`${backendUrl}/api/v1/ai/insight/${companyId}`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          'Content-Type': 'application/json',
        },
      })
      if (res.ok) {
        const data = await res.json()
        if (data.ai_narrative) {
          toast.success('AI test passed — narrative generated')
        } else if (data.error) {
          toast.error(`AI test failed: ${data.error}`)
        } else {
          toast.success('AI test passed — rule-based insights generated')
        }
      } else {
        toast.error('AI test request failed')
      }
    } catch {
      toast.error('Network error testing AI')
    } finally {
      setTesting(false)
    }
  }

  // ── Loading ─────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center min-h-[400px]">
          <Loader2 className="w-6 h-6 animate-spin text-primary" />
        </div>
      </AppLayout>
    )
  }

  // ── Access Control ──────────────────────────────────────────────────────
  const allowedRoles = ['engineer', 'supervisor', 'super_admin']
  if (userRole && !allowedRoles.includes(userRole)) {
    return (
      <AppLayout>
        <div className="max-w-2xl mx-auto mt-20 text-center">
          <AlertTriangle className="w-12 h-12 text-amber-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold mb-2">Access Restricted</h2>
          <p className="text-muted-foreground">Settings are available for Engineer, Supervisor, and Super Admin roles.</p>
        </div>
      </AppLayout>
    )
  }

  // ── Main Render ─────────────────────────────────────────────────────────
  return (
    <AppLayout>
      <div className="max-w-3xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center gap-3">
          <Settings className="w-6 h-6 text-primary" />
          <div>
            <h1 className="text-2xl font-bold">Settings</h1>
            <p className="text-sm text-muted-foreground">Profile & company configuration</p>
          </div>
        </div>

        {/* AI Configuration Section */}
        <div className="border rounded-lg">
          <div className="px-6 py-4 border-b">
            <div className="flex items-center gap-2">
              <Brain className="w-5 h-5 text-primary" />
              <h2 className="text-base font-semibold">AI Configuration</h2>
            </div>
            <p className="text-sm text-muted-foreground mt-1">
              Configure LLM provider and API key for AI-powered insights.
            </p>
          </div>

          <div className="px-6 py-4 space-y-4">
            {/* Status Badge */}
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">Status:</span>
              {configStatus?.has_key ? (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">
                  <CheckCircle className="w-3.5 h-3.5" />
                  Configured: {configStatus.provider === 'gemini' ? 'Gemini' : configStatus.provider === 'openai' ? 'OpenAI' : configStatus.provider}
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  Not configured
                </span>
              )}
            </div>

            {/* Provider Dropdown */}
            <div>
              <label className="block text-sm font-medium mb-1.5">LLM Provider</label>
              <select
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
                className="w-full px-3 py-2 text-sm border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
              >
                <option value="gemini">Google Gemini</option>
                <option value="openai">OpenAI</option>
              </select>
            </div>

            {/* API Key */}
            <div>
              <label className="block text-sm font-medium mb-1.5">API Key</label>
              <div className="relative">
                <input
                  type={showKey ? 'text' : 'password'}
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder={configStatus?.has_key ? '••••••••••••••••••••••••' : 'Enter your API key'}
                  className="w-full px-3 py-2 pr-10 text-sm border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
                <button
                  type="button"
                  onClick={() => setShowKey(!showKey)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {provider === 'gemini'
                  ? 'Get your key at https://aistudio.google.com/apikey'
                  : 'Get your key at https://platform.openai.com/api-keys'}
              </p>
            </div>

            {/* Actions */}
            <div className="flex gap-3 pt-2">
              <button
                onClick={handleSave}
                disabled={saving || !apiKey.trim()}
                className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
              >
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                {saving ? 'Saving...' : 'Save'}
              </button>
              <button
                onClick={handleTest}
                disabled={testing || !configStatus?.has_key}
                className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-md border bg-background hover:bg-accent disabled:opacity-50 transition-colors"
              >
                {testing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Brain className="w-4 h-4" />}
                {testing ? 'Testing...' : 'Test'}
              </button>
            </div>
          </div>
        </div>

        {/* Placeholder for future sections */}
        <div className="border rounded-lg p-6">
          <h2 className="text-base font-semibold mb-2">Profile</h2>
          <p className="text-sm text-muted-foreground">Profile settings will be available in a future update.</p>
        </div>
      </div>
    </AppLayout>
  )
}
