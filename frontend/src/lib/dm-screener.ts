/**
 * DM Screener — Shared matching engine (client-side)
 * Exact port of screenAsset() from dm_screener_pro.html
 * Used by: /dm-screener (standalone), /equipment/[id] (auto)
 */

export interface DM {
  dm_code: string
  dm_name: string
  category: string
  confidence: string
  pwht_concern?: boolean
  nde?: string[]
  mitigation?: string
  match_status?: 'Active' | 'Possible' | 'Related'
}

export interface DMResponse {
  status: string
  active: DM[]
  possible: DM[]
  related: DM[]
  total_matched: number
  total_screened: number
  nde?: string
}

export interface MatchInput {
  material: string
  fluid: string
  tempMin: number
  tempMax: number
  pwht: boolean | null
}

export function tokenizeRef(text: string): string[] {
  if (!text) return []
  return text.toLowerCase()
    .split(/\s+/)
    .filter(t => t.length > 1)
}

export function matchTokens(dmKeywords: string[], inputTokens: string[]): boolean {
  if (!inputTokens.length) return false
  return dmKeywords.some(keyword => {
    const kwTokens = tokenizeRef(keyword)
    return kwTokens.some(k => inputTokens.includes(k) || inputTokens.some(t => t.includes(k)))
  })
}

export function runClientSideMatch(kb: any[], input: MatchInput): DMResponse {
  const matTokens = tokenizeRef(input.material)
  const fluidTokens = tokenizeRef(input.fluid)
  const tmin = isNaN(input.tempMin) ? 0 : input.tempMin
  const tmax = isNaN(input.tempMax) ? 100 : input.tempMax
  const hasTempData = !isNaN(input.tempMin) && !isNaN(input.tempMax)

  const active: DM[] = []
  const possible: DM[] = []
  const related: DM[] = []

  for (const dm of kb) {
    const matMatch = matchTokens(dm.materials || [], matTokens)
    const fluidMatch = matchTokens(dm.fluids || [], fluidTokens)
    const dmTempMin = dm.temp_min ?? -999
    const dmTempMax = dm.temp_max ?? 999
    const tempMatch = tmax >= dmTempMin && tmin <= dmTempMax
    const score = (matMatch ? 1 : 0) + (fluidMatch ? 1 : 0) + (tempMatch ? 1 : 0)

    // Classification — exact order from screenAsset()
    if (matMatch && fluidMatch && (tempMatch || !hasTempData)) {
      active.push({
        dm_code: dm.dm_code,
        dm_name: dm.dm_name,
        category: dm.category,
        confidence: 'high',
        nde: (dm.recommended_nde || []).slice(0, 2),
        mitigation: (dm.description || '').split(';')[0].trim(),
        match_status: 'Active',
      })
    } else if (score >= 2) {
      possible.push({
        dm_code: dm.dm_code,
        dm_name: dm.dm_name,
        category: dm.category,
        confidence: 'medium',
        nde: (dm.recommended_nde || []).slice(0, 2),
        match_status: 'Possible',
      })
    } else if (matMatch && fluidMatch) {
      related.push({
        dm_code: dm.dm_code,
        dm_name: dm.dm_name,
        category: dm.category,
        confidence: 'low',
        match_status: 'Related',
      })
    }
  }

  // PWHT Boost: exact from reference
  if (input.pwht === false || input.pwht === null) {
    for (const dm of kb) {
      if (dm.pwht_flag !== 'required') continue
      const matMatch = matchTokens(dm.materials || [], matTokens)
      const fluidMatch = matchTokens(dm.fluids || [], fluidTokens)
      if (matMatch && fluidMatch && !active.find(a => a.dm_code === dm.dm_code) && !possible.find(p => p.dm_code === dm.dm_code)) {
        possible.push({
          dm_code: dm.dm_code,
          dm_name: dm.dm_name + ' (No PWHT — elevated risk)',
          category: dm.category,
          confidence: 'medium',
          pwht_concern: true,
          nde: (dm.recommended_nde || []).slice(0, 2),
          match_status: 'Possible',
        })
      }
    }
  }

  // NDE from top active DM
  const topDM = active.length > 0 ? kb.find((k: any) => k.dm_code === active[0].dm_code) : null
  const nde = topDM && topDM.recommended_nde ? topDM.recommended_nde.slice(0, 2).join(', ') : 'UT Thickness (Baseline)'

  return {
    status: 'ok',
    active: active.slice(0, 6),
    possible: possible.slice(0, 4),
    related: related.slice(0, 4),
    total_matched: active.length + possible.length + related.length,
    total_screened: kb.length,
    nde,
  }
}