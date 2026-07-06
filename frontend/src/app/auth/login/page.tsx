'use client'
export const dynamic = 'force-dynamic'

import { createClient } from '@/lib/supabase/client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'

// Demo credentials (public — this is a demo instance)
const DEMO_EMAIL = 'supervisor@example.com'
const DEMO_PASSWORD = 'Integra2024!'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [autoLoginAttempted, setAutoLoginAttempted] = useState(false)
  const router = useRouter()
  const supabase = createClient()

  // Auto-login on mount
  useEffect(() => {
    let cancelled = false

    async function tryAutoLogin() {
      // 1. Check existing session
      const { data: { session } } = await supabase.auth.getSession()
      if (cancelled) return

      if (session) {
        // Already logged in — redirect immediately
        router.push('/dashboard')
        return
      }

      // 2. No session — attempt demo login
      const { error: loginError } = await supabase.auth.signInWithPassword({
        email: DEMO_EMAIL,
        password: DEMO_PASSWORD,
      })
      if (cancelled) return

      if (loginError) {
        // Auto-login failed — show form, don't retry
        setAutoLoginAttempted(true)
        return
      }

      // 3. Success — redirect
      router.push('/dashboard')
    }

    tryAutoLogin()

    return () => { cancelled = true }
  }, [router, supabase])

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    })

    if (error) {
      setError(error.message)
      setLoading(false)
      return
    }

    router.push('/dashboard')
  }

  // Show loading state while auto-login is in progress
  if (!autoLoginAttempted) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <h1 className="text-2xl font-bold tracking-tight">Integra</h1>
          <p className="text-muted-foreground mt-2 text-sm">Loading demo…</p>
        </div>
      </div>
    )
  }

  // Auto-login done (failed) — show manual form
  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="w-full max-w-sm mx-auto p-6">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold tracking-tight">Integra</h1>
          <p className="text-muted-foreground mt-1">
            Inspection & Asset Integrity Platform
          </p>
        </div>

        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium mb-1">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2 border border-input rounded-lg bg-card text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder="name@company.com"
              required
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium mb-1">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 border border-input rounded-lg bg-card text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder="••••••••"
              required
            />
          </div>

          {error && (
            <div className="text-sm text-destructive bg-destructive/10 px-3 py-2 rounded-lg">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 px-4 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:opacity-90 disabled:opacity-50 transition-opacity"
          >
            {loading ? 'Processing...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  )
}
