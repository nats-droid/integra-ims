'use client'

import { useState, useEffect, useCallback } from 'react'
import { Brain, AlertTriangle, CheckCircle, Info, Zap, Loader2, Settings, Send, BarChart3 } from 'lucide-react'
import AppLayout from '@/components/layout/app-layout'
import { createClient } from '@/lib/supabase/client'
import { toast } from 'sonner'

// ── Types ────────────────────────────────────────────────────────────────────
interface InsightMetric {
  label: string
  value: string
}

interface InsightCard {
  type: 'crit' | 'warn' | 'ok' | 'info'
  title: string
  body: string
  metrics?: InsightMetric[]
}

interface InsightResponse {
  rule_based: InsightCard[]
  ai_narrative: string | null
  context_summary: string
  computed_at: string
  error: string | null
}

interface StatusResponse {
  has_key: boolean
  provider: string | null
}

// ── Chip Questions ───────────────────────────────────────────────────────────
const CHIP_QUESTIONS = [
  'How many equipment are overdue?',
  'Which CML has highest corrosion rate?',
  'What is the fleet risk status?',
  'Which equipment needs immediate inspection?',
]

// ── Card Colors ──────────────────────────────────────────────────────────────
const TYPE_STYLES: Record<string, { border: string; bg: string; icon: string; badge: string }> = {
  crit: { border: 'border-l-red-500', bg: 'bg-red-50 dark:bg-red-950/20', icon: 'text-red-500', badge: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400' },
  warn: { border: 'border-l-amber-500', bg: 'bg-amber-50 dark:bg-amber-950/20', icon: 'text-amber-500', badge: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400' },
  ok:   { border: 'border-l-green-500', bg: 'bg-green-50 dark:bg-green-950/20', icon: 'text-green-500', badge: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' },
  info: { border: 'border-l-blue-500', bg: 'bg-blue-50 dark:bg-blue-950/20', icon: 'text-blue-500', badge: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400' },
}

const TYPE_ICONS: Record<string, typeof Brain> = {
  crit: AlertTriangle,
  warn: AlertTriangle,
  ok: CheckCircle,
  info: Info,
}

// ── Component ────────────────────────────────────────────────────────────────
export default function AIInsightPage() {
  const [companyId, setCompanyId] = useState<string | null>(null)
  const [userRole, setUserRole] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [status, setStatus] = useState<StatusResponse | null>(null)
  const [insights, setInsights] = useState<InsightResponse | null>(null)
  const [insightLoading, setInsightLoading] = useState(false)
  const [aiNarrative, setAiNarrative] = useState<string | null>(null)
  const [narrativeLoading, setNarrativeLoading] = useState(false)
  const [question, setQuestion] = useState('')
  const [qaAnswer, setQaAnswer] = useState<string | null>(null)
  const [qaLoading, setQaLoading] = useState(false)
  const [qaError, setQaError] = useState<string | null>(null)

  const supabase = createClient()
  const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  // Load user profile
  useEffect(() => {
    async function loadProfile() {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) return

      const { data } = await supabase
        .from('app_users')
        .select('company_id, role')
        .eq('auth_user_id', user.id)
        .single()

      if (data) {
        setCompanyId((data as Record<string, unknown>).company_id as string)
        setUserRole((data as Record<string, unknown>).role as string)
      }
    }
    loadProfile()
  }, [supabase])

  // Fetch AI status
  useEffect(() => {
    if (!companyId) return

    async function fetchStatus() {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) return

      try {
        const res = await fetch(`${backendUrl}/api/v1/ai/status/${companyId}`, {
          headers: { Authorization: `Bearer ${session.access_token}` },
        })
        if (res.ok) {
          setStatus(await res.json())
        }
      } catch {
        // silently fail
      } finally {
        setLoading(false)
      }
    }
    fetchStatus()
  }, [companyId, backendUrl, supabase])

  // Fetch insights
  const fetchInsights = useCallback(async () => {
    if (!companyId) return
    setInsightLoading(true)

    const { data: { session } } = await supabase.auth.getSession()
    if (!session) return

    try {
      const res = await fetch(`${backendUrl}/api/v1/ai/insight/${companyId}`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          'Content-Type': 'application/json',
        },
      })
      if (res.ok) {
        const data: InsightResponse = await res.json()
        setInsights(data)
        setAiNarrative(null)
      } else {
        toast.error('Failed to load insights')
      }
    } catch {
      toast.error('Network error loading insights')
    } finally {
      setInsightLoading(false)
    }
  }, [companyId, backendUrl, supabase])

  useEffect(() => {
    if (companyId && status !== null) {
      fetchInsights()
    }
  }, [companyId, status, fetchInsights])

  // Generate AI narrative
  const generateNarrative = async () => {
    if (!companyId || !status?.has_key) return
    setNarrativeLoading(true)

    const { data: { session } } = await supabase.auth.getSession()
    if (!session) return

    try {
      const res = await fetch(`${backendUrl}/api/v1/ai/insight/${companyId}`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          'Content-Type': 'application/json',
        },
      })
      if (res.ok) {
        const data: InsightResponse = await res.json()
        if (data.ai_narrative) {
          setAiNarrative(data.ai_narrative)
        } else if (data.error) {
          toast.error(`AI Error: ${data.error}`)
        }
      }
    } catch {
      toast.error('Failed to generate analysis')
    } finally {
      setNarrativeLoading(false)
    }
  }

  // Ask Q&A
  const askQuestion = async (q?: string) => {
    const query = q || question
    if (!companyId || !query.trim()) return
    setQaLoading(true)
    setQaAnswer(null)
    setQaError(null)

    const { data: { session } } = await supabase.auth.getSession()
    if (!session) return

    try {
      const res = await fetch(`${backendUrl}/api/v1/ai/qa/${companyId}`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ question: query }),
      })
      if (res.ok) {
        const data = await res.json()
        if (data.answer) {
          setQaAnswer(data.answer)
        } else {
          setQaError(data.error || 'No answer received')
        }
      }
    } catch {
      setQaError('Network error')
    } finally {
      setQaLoading(false)
    }
  }

  // ── Access Control ──────────────────────────────────────────────────────
  if (userRole && userRole === 'inspector') {
    return (
      <AppLayout>
        <div className="max-w-2xl mx-auto mt-20 text-center">
          <AlertTriangle className="w-12 h-12 text-amber-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold mb-2">Access Restricted</h2>
          <p className="text-muted-foreground">AI Insight is available for Engineer, Supervisor, and Super Admin roles only.</p>
        </div>
      </AppLayout>
    )
  }

  // ── Loading State ───────────────────────────────────────────────────────
  if (loading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center min-h-[400px]">
          <Loader2 className="w-6 h-6 animate-spin text-primary" />
        </div>
      </AppLayout>
    )
  }

  // ── Main Render ─────────────────────────────────────────────────────────
  return (
    <AppLayout>
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Brain className="w-6 h-6 text-primary" />
            <div>
              <h1 className="text-2xl font-bold">AI Insight</h1>
              <p className="text-sm text-muted-foreground">Asset integrity analysis powered by AI</p>
            </div>
          </div>
          {status?.has_key && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">
              <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
              {status.provider === 'gemini' ? 'Gemini' : status.provider === 'openai' ? 'OpenAI' : status.provider} configured
            </span>
          )}
        </div>

        {/* State 1: No API Key — Banner */}
        {status && !status.has_key && (
          <div className="bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4 flex items-start gap-3">
            <Settings className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-amber-800 dark:text-amber-300">
                Configure API key in Settings to enable AI analysis.
              </p>
              <a
                href="/settings"
                className="inline-block mt-2 text-sm font-medium text-amber-700 dark:text-amber-400 underline hover:no-underline"
              >
                Go to Settings →
              </a>
            </div>
          </div>
        )}

        {/* Insight Cards */}
        {insightLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-5 h-5 animate-spin text-primary mr-2" />
            <span className="text-sm text-muted-foreground">Loading insights...</span>
          </div>
        ) : insights?.rule_based ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {insights.rule_based.map((card, idx) => {
              const style = TYPE_STYLES[card.type] || TYPE_STYLES.info
              const Icon = TYPE_ICONS[card.type] || Info
              return (
                <div
                  key={idx}
                  className={`border-l-4 ${style.border} ${style.bg} rounded-r-lg p-4`}
                >
                  <div className="flex items-start gap-3">
                    <Icon className={`w-5 h-5 ${style.icon} flex-shrink-0 mt-0.5`} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="text-sm font-semibold">{card.title}</h3>
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium uppercase ${style.badge}`}>
                          {card.type}
                        </span>
                      </div>
                      <p className="text-sm text-muted-foreground mb-2">{card.body}</p>
                      {card.metrics && card.metrics.length > 0 && (
                        <div className="flex flex-wrap gap-3">
                          {card.metrics.map((m, mi) => (
                            <div key={mi} className="text-xs">
                              <span className="text-muted-foreground">{m.label}: </span>
                              <span className="font-medium">{m.value}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        ) : null}

        {/* AI Narrative Section */}
        {status?.has_key && (
          <div className="border rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold flex items-center gap-2">
                <Zap className="w-4 h-4 text-primary" />
                AI Analysis
              </h2>
              <button
                onClick={generateNarrative}
                disabled={narrativeLoading}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
              >
                {narrativeLoading ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Zap className="w-3.5 h-3.5" />
                )}
                {narrativeLoading ? 'Analyzing...' : 'Generate Analysis'}
              </button>
            </div>
            {aiNarrative ? (
              <div className="text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed">
                {aiNarrative}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground italic">
                Click &quot;Generate Analysis&quot; to get AI-powered narrative insights.
              </p>
            )}
          </div>
        )}

        {/* Context Summary */}
        {insights?.context_summary && (
          <details className="border rounded-lg">
            <summary className="px-4 py-3 text-sm font-medium cursor-pointer hover:bg-accent/50 transition-colors">
              <BarChart3 className="w-4 h-4 inline mr-2" />
              Context Summary (raw data sent to AI)
            </summary>
            <div className="px-4 pb-4">
              <pre className="text-xs text-muted-foreground whitespace-pre-wrap bg-muted/50 rounded p-3 overflow-x-auto">
                {insights.context_summary}
              </pre>
            </div>
          </details>
        )}

        {/* Q&A Section */}
        <div className="border rounded-lg p-4">
          <h2 className="text-sm font-semibold mb-3 flex items-center gap-2">
            <Send className="w-4 h-4 text-primary" />
            Ask a Question
          </h2>

          {!status?.has_key ? (
            <p className="text-sm text-muted-foreground italic">
              Configure API key in Settings to enable Q&A.
            </p>
          ) : (
            <>
              <div className="flex gap-2 mb-3">
                <input
                  type="text"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && askQuestion()}
                  placeholder="e.g., How many equipment are overdue?"
                  className="flex-1 px-3 py-2 text-sm border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
                <button
                  onClick={() => askQuestion()}
                  disabled={qaLoading || !question.trim()}
                  className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
                >
                  {qaLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                  Ask
                </button>
              </div>

              {/* Chips */}
              <div className="flex flex-wrap gap-2 mb-3">
                {CHIP_QUESTIONS.map((cq, i) => (
                  <button
                    key={i}
                    onClick={() => { setQuestion(cq); askQuestion(cq) }}
                    className="px-2.5 py-1 text-xs rounded-full border bg-muted/50 hover:bg-muted transition-colors"
                  >
                    {cq}
                  </button>
                ))}
              </div>

              {/* Answer */}
              {qaLoading && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Thinking...
                </div>
              )}
              {qaAnswer && (
                <div className="text-sm bg-muted/50 rounded p-3 whitespace-pre-wrap">
                  {qaAnswer}
                </div>
              )}
              {qaError && (
                <div className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/20 rounded p-3">
                  {qaError}
                </div>
              )}
            </>
          )}
        </div>

        {/* Timestamp */}
        {insights?.computed_at && (
          <p className="text-xs text-muted-foreground text-right">
            Last computed: {new Date(insights.computed_at).toLocaleString()}
          </p>
        )}
      </div>
    </AppLayout>
  )
}
