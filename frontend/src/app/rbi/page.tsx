'use client'

import { useState, useCallback } from 'react'
import { Calculator, AlertTriangle, TrendingUp, Shield, Clock, Award } from 'lucide-react'
import AppLayout from '@/components/layout/app-layout'
import { createClient } from '@/lib/supabase/client'
import { toast } from 'sonner'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

// ── Types ────────────────────────────────────────────────────────────────────
interface TminResult {
  t_pressure?: number
  t_structural?: number
  t_circumferential?: number
  t_longitudinal?: number
  t_required_base: number
  governing: string
  code: string
}

interface CorrosionRateResult {
  CR_LT: number
  CR_ST: number
  governing: string
  governing_rate: number
  n_readings: number
}

interface FMSResult {
  fms: number
  pscore: number
  interpretation: string
  risk_level: string
}

interface TimelinePoint {
  years_from_assessment: number
  risk: number
  pof: number
  thickness: number
  risk_category: string
}

interface EquivalenceResult {
  equivalent_count: number
  meets_requirement: boolean
  total_inspections: number
}

interface CompleteRBIResult {
  component_id: string
  pof: { pof_per_year: number; fms: number }
  cof: { cof_financial: number }
  risk: { pof_category: number; cof_category: string; risk_score: number; risk_level: string }
  risk_matrix_position: string
  inspection_recommendation: { interval_years: number; effectiveness: string; priority: string }
}

// ── Main Component ───────────────────────────────────────────────────────────
export default function RBIPage() {
  const [activeTab, setActiveTab] = useState<'complete' | 'tmin' | 'corrosion' | 'fms' | 'timeline' | 'equivalence'>('complete')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // Complete RBI state
  const [componentId, setComponentId] = useState('COMP-001')
  const [componentType, setComponentType] = useState('pipe')
  const [fluidType, setFluidType] = useState('hydrocarbon')
  const [pressureBar, setPressureBar] = useState('20')
  const [tempC, setTempC] = useState('150')
  const [diameterMm, setDiameterMm] = useState('168.3')
  const [fms, setFms] = useState('1.0')
  const [completeResult, setCompleteResult] = useState<CompleteRBIResult | null>(null)

  // Tmin state
  const [tminEquipType, setTminEquipType] = useState<'pipe' | 'vessel'>('pipe')
  const [tminPressureBar, setTminPressureBar] = useState('20')
  const [allowableStressMpa, setAllowableStressMpa] = useState('138')
  const [jointEfficiency, setJointEfficiency] = useState('1.0')
  const [corrosionAllowanceMm, setCorrosionAllowanceMm] = useState('3.0')
  const [designTempC, setDesignTempC] = useState('150')
  const [odMm, setOdMm] = useState('168.3')
  const [npsIn, setNpsIn] = useState('6')
  const [idMm, setIdMm] = useState('2000')
  const [tminResult, setTminResult] = useState<TminResult | null>(null)

  // Corrosion Rate state
  const [readings, setReadings] = useState([
    { date: '2020-01-01', thickness_mm: '10.5' },
    { date: '2022-01-01', thickness_mm: '10.1' },
    { date: '2024-01-01', thickness_mm: '9.7' }
  ])
  const [corrosionResult, setCorrosionResult] = useState<CorrosionRateResult | null>(null)

  // FMS state
  const [managementInspection, setManagementInspection] = useState('85')
  const [siteManagement, setSiteManagement] = useState('78')
  const [managementOfChange, setManagementOfChange] = useState('82')
  const [failureInvestigation, setFailureInvestigation] = useState('88')
  const [processSafety, setProcessSafety] = useState('75')
  const [operatingProcedures, setOperatingProcedures] = useState('80')
  const [fmsResult, setFmsResult] = useState<FMSResult | null>(null)

  // Timeline state
  const [pof0, setPof0] = useState('0.0001')
  const [cof, setCof] = useState('50000')
  const [corrosionRateMmYr, setCorrosionRateMmYr] = useState('0.2')
  const [tActualMm, setTActualMm] = useState('10.0')
  const [tRequiredMm, setTRequiredMm] = useState('7.5')
  const [horizonYears, setHorizonYears] = useState('10')
  const [timelineResult, setTimelineResult] = useState<TimelinePoint[] | null>(null)

  // Equivalence state
  const [inspections, setInspections] = useState([
    { date: '2020-06-01', effectiveness: 'A', inspection_type: 'internal' },
    { date: '2022-06-01', effectiveness: 'B', inspection_type: 'online' }
  ])
  const [equivalenceResult, setEquivalenceResult] = useState<EquivalenceResult | null>(null)

  // ── API Calls ──────────────────────────────────────────────────────────────
  const callRBIEndpoint = useCallback(async (endpoint: string, body: any, setResult: (data: any) => void) => {
    setLoading(true)
    setError('')
    try {
      const supabase = createClient()
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) throw new Error('Not authenticated')

      const res = await fetch(`/api/backend/api/v1/rbi/${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`
        },
        body: JSON.stringify(body)
      })

      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.detail || 'Request failed')
      }

      const data = await res.json()
      setResult(data.data)
      toast.success('Calculation complete')
    } catch (e: any) {
      setError(e.message)
      toast.error(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  const calculateComplete = useCallback(() => {
    callRBIEndpoint('complete-rbi', {
      component_id: componentId,
      component_type: componentType,
      fluid_type: fluidType,
      pressure_bar: parseFloat(pressureBar),
      temp_c: parseFloat(tempC),
      diameter_mm: parseFloat(diameterMm),
      fms: parseFloat(fms),
      damage_factors: { thinning: 0.5, external_corrosion: 0.3, cui: 0.2 }
    }, setCompleteResult)
  }, [componentId, componentType, fluidType, pressureBar, tempC, diameterMm, fms, callRBIEndpoint])

  const calculateTmin = useCallback(() => {
    const body: any = {
      equipment_type: tminEquipType,
      pressure_bar: parseFloat(tminPressureBar),
      allowable_stress_mpa: parseFloat(allowableStressMpa),
      joint_efficiency: parseFloat(jointEfficiency),
      corrosion_allowance_mm: parseFloat(corrosionAllowanceMm),
      design_temp_c: parseFloat(designTempC)
    }
    if (tminEquipType === 'pipe') {
      body.od_mm = parseFloat(odMm)
      body.nps_in = parseFloat(npsIn)
    } else {
      body.id_mm = parseFloat(idMm)
    }
    callRBIEndpoint('calculate-tmin', body, setTminResult)
  }, [tminEquipType, tminPressureBar, allowableStressMpa, jointEfficiency, corrosionAllowanceMm, designTempC, odMm, npsIn, idMm, callRBIEndpoint])

  const calculateCorrosion = useCallback(() => {
    callRBIEndpoint('calculate-corrosion-rate', { readings }, setCorrosionResult)
  }, [readings, callRBIEndpoint])

  const calculateFMS = useCallback(() => {
    callRBIEndpoint('calculate-fms', {
      management_inspection: parseFloat(managementInspection),
      site_management: parseFloat(siteManagement),
      management_of_change: parseFloat(managementOfChange),
      failure_investigation: parseFloat(failureInvestigation),
      process_safety: parseFloat(processSafety),
      operating_procedures: parseFloat(operatingProcedures)
    }, setFmsResult)
  }, [managementInspection, siteManagement, managementOfChange, failureInvestigation, processSafety, operatingProcedures, callRBIEndpoint])

  const calculateTimeline = useCallback(() => {
    callRBIEndpoint('calculate-timeline', {
      pof_0: parseFloat(pof0),
      cof: parseFloat(cof),
      corrosion_rate_mm_yr: parseFloat(corrosionRateMmYr),
      t_actual_mm: parseFloat(tActualMm),
      t_required_mm: parseFloat(tRequiredMm),
      horizon_years: parseInt(horizonYears)
    }, setTimelineResult)
  }, [pof0, cof, corrosionRateMmYr, tActualMm, tRequiredMm, horizonYears, callRBIEndpoint])

  const calculateEquivalence = useCallback(() => {
    callRBIEndpoint('calculate-equivalence', { inspections }, setEquivalenceResult)
  }, [inspections, callRBIEndpoint])

  // ── Risk Matrix ────────────────────────────────────────────────────────────
  const RiskMatrix = ({ position }: { position: string }) => {
    const pofCat = parseInt(position[0])
    const cofCat = position[1]
    const cofIndex = ['A', 'B', 'C', 'D', 'E'].indexOf(cofCat)

    return (
      <div className="space-y-2">
        <p className="text-sm font-medium">Risk Matrix (5×5)</p>
        <div className="grid grid-cols-6 gap-1 text-xs">
          <div></div>
          {['A', 'B', 'C', 'D', 'E'].map(c => (
            <div key={c} className="text-center font-medium">{c}</div>
          ))}
          {[5, 4, 3, 2, 1].map(p => (
            <>
              <div key={p} className="flex items-center justify-end pr-2 font-medium">{p}</div>
              {[0, 1, 2, 3, 4].map(c => {
                const isTarget = p === pofCat && c === cofIndex
                const riskLevel = p * (c + 1)
                const bgColor = riskLevel >= 15 ? 'bg-red-500' : riskLevel >= 8 ? 'bg-orange-500' : riskLevel >= 4 ? 'bg-yellow-500' : 'bg-green-500'
                return (
                  <div
                    key={`${p}-${c}`}
                    className={`h-10 border ${isTarget ? 'border-4 border-indigo-600' : 'border-gray-300'} ${bgColor} ${isTarget ? 'animate-pulse' : ''}`}
                  />
                )
              })}
            </>
          ))}
        </div>
      </div>
    )
  }

  return (
    <AppLayout>
      <div className="p-6 max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <Calculator className="text-indigo-500" />
            Risk-Based Inspection (API 581)
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Calculate POF, COF, and risk-based inspection intervals
          </p>
        </div>

        {/* Beta Warning */}
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 flex items-start gap-3">
          <AlertTriangle className="text-yellow-600 dark:text-yellow-400 shrink-0 mt-0.5" size={20} />
          <div className="text-sm text-yellow-800 dark:text-yellow-200">
            <strong>Beta</strong> — calculation engine under validation. Consequence of Failure uses a simplified model, not API 581 Level 1. Do not use results for inspection decisions.
          </div>
        </div>

        {/* Tabs */}
        <div className="border-b border-border">
          <div className="flex gap-1 overflow-x-auto">
            {[
              { key: 'complete', label: 'Complete RBI', icon: Shield },
              { key: 'tmin', label: 't-min', icon: Calculator },
              { key: 'corrosion', label: 'Corrosion Rate', icon: TrendingUp },
              { key: 'fms', label: 'FMS', icon: Award },
              { key: 'timeline', label: 'Risk Timeline', icon: Clock },
              { key: 'equivalence', label: 'Inspection Equivalence', icon: Shield }
            ].map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                onClick={() => setActiveTab(key as any)}
                className={`px-4 py-2 text-sm font-medium flex items-center gap-2 border-b-2 transition-colors whitespace-nowrap ${
                  activeTab === key
                    ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                    : 'border-transparent text-muted-foreground hover:text-foreground'
                }`}
              >
                <Icon size={16} />
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 text-sm text-red-800 dark:text-red-200">
            {error}
          </div>
        )}

        {/* Complete RBI Tab */}
        {activeTab === 'complete' && (
          <div className="space-y-6">
            <div className="bg-card border border-border rounded-lg p-6 space-y-4">
              <h2 className="font-semibold text-lg">Complete RBI Assessment</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Component ID</label>
                  <input
                    type="text"
                    value={componentId}
                    onChange={e => setComponentId(e.target.value)}
                    className="w-full px-3 py-2 border border-border rounded-md bg-background"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Component Type</label>
                  <select
                    value={componentType}
                    onChange={e => setComponentType(e.target.value)}
                    className="w-full px-3 py-2 border border-border rounded-md bg-background"
                  >
                    <option value="pipe">Pipe</option>
                    <option value="vessel">Vessel</option>
                    <option value="tank">Tank</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Fluid Type</label>
                  <input
                    type="text"
                    value={fluidType}
                    onChange={e => setFluidType(e.target.value)}
                    className="w-full px-3 py-2 border border-border rounded-md bg-background"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Pressure (bar)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={pressureBar}
                    onChange={e => setPressureBar(e.target.value)}
                    className="w-full px-3 py-2 border border-border rounded-md bg-background"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Temperature (°C)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={tempC}
                    onChange={e => setTempC(e.target.value)}
                    className="w-full px-3 py-2 border border-border rounded-md bg-background"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Diameter (mm)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={diameterMm}
                    onChange={e => setDiameterMm(e.target.value)}
                    className="w-full px-3 py-2 border border-border rounded-md bg-background"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">FMS Factor</label>
                  <input
                    type="number"
                    step="0.1"
                    value={fms}
                    onChange={e => setFms(e.target.value)}
                    className="w-full px-3 py-2 border border-border rounded-md bg-background"
                  />
                </div>
              </div>
              <button
                onClick={calculateComplete}
                disabled={loading}
                className="w-full px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Calculating...' : 'Calculate Complete RBI'}
              </button>
            </div>

            {completeResult && (
              <div className="bg-card border border-border rounded-lg p-6 space-y-4">
                <h3 className="font-semibold text-lg">Results</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg">
                    <p className="text-xs text-muted-foreground">POF (per year)</p>
                    <p className="text-2xl font-bold">{completeResult.pof.pof_per_year.toExponential(3)}</p>
                  </div>
                  <div className="bg-orange-50 dark:bg-orange-900/20 p-4 rounded-lg">
                    <p className="text-xs text-muted-foreground">COF (financial)</p>
                    <p className="text-2xl font-bold">${completeResult.cof.cof_financial.toFixed(0)}</p>
                  </div>
                  <div className="bg-red-50 dark:bg-red-900/20 p-4 rounded-lg">
                    <p className="text-xs text-muted-foreground">Risk Score</p>
                    <p className="text-2xl font-bold">{completeResult.risk.risk_score.toFixed(1)}</p>
                    <p className="text-xs text-red-600 dark:text-red-400">{completeResult.risk.risk_level}</p>
                  </div>
                </div>
                <RiskMatrix position={completeResult.risk_matrix_position} />
                <div className="bg-indigo-50 dark:bg-indigo-900/20 p-4 rounded-lg">
                  <p className="text-sm font-medium mb-2">Inspection Recommendation</p>
                  <p className="text-sm">Interval: <strong>{completeResult.inspection_recommendation.interval_years} years</strong></p>
                  <p className="text-sm">Effectiveness: <strong>{completeResult.inspection_recommendation.effectiveness}</strong></p>
                  <p className="text-sm">Priority: <strong>{completeResult.inspection_recommendation.priority}</strong></p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tmin Tab */}
        {activeTab === 'tmin' && (
          <div className="space-y-6">
            <div className="bg-card border border-border rounded-lg p-6 space-y-4">
              <h2 className="font-semibold text-lg">Required Thickness Calculation</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Equipment Type</label>
                  <select
                    value={tminEquipType}
                    onChange={e => setTminEquipType(e.target.value as any)}
                    className="w-full px-3 py-2 border border-border rounded-md bg-background"
                  >
                    <option value="pipe">Pipe</option>
                    <option value="vessel">Vessel</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Pressure (bar)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={tminPressureBar}
                    onChange={e => setTminPressureBar(e.target.value)}
                    className="w-full px-3 py-2 border border-border rounded-md bg-background"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Allowable Stress (MPa)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={allowableStressMpa}
                    onChange={e => setAllowableStressMpa(e.target.value)}
                    className="w-full px-3 py-2 border border-border rounded-md bg-background"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Joint Efficiency</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    max="1"
                    value={jointEfficiency}
                    onChange={e => setJointEfficiency(e.target.value)}
                    className="w-full px-3 py-2 border border-border rounded-md bg-background"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Corrosion Allowance (mm)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={corrosionAllowanceMm}
                    onChange={e => setCorrosionAllowanceMm(e.target.value)}
                    className="w-full px-3 py-2 border border-border rounded-md bg-background"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Design Temperature (°C)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={designTempC}
                    onChange={e => setDesignTempC(e.target.value)}
                    className="w-full px-3 py-2 border border-border rounded-md bg-background"
                  />
                </div>
                {tminEquipType === 'pipe' && (
                  <>
                    <div>
                      <label className="block text-sm font-medium mb-1">OD (mm)</label>
                      <input
                        type="number"
                        step="0.1"
                        value={odMm}
                        onChange={e => setOdMm(e.target.value)}
                        className="w-full px-3 py-2 border border-border rounded-md bg-background"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">NPS (inches)</label>
                      <input
                        type="number"
                        step="0.1"
                        value={npsIn}
                        onChange={e => setNpsIn(e.target.value)}
                        className="w-full px-3 py-2 border border-border rounded-md bg-background"
                      />
                    </div>
                  </>
                )}
                {tminEquipType === 'vessel' && (
                  <div>
                    <label className="block text-sm font-medium mb-1">ID (mm)</label>
                    <input
                      type="number"
                      step="0.1"
                      value={idMm}
                      onChange={e => setIdMm(e.target.value)}
                      className="w-full px-3 py-2 border border-border rounded-md bg-background"
                    />
                  </div>
                )}
              </div>
              <button
                onClick={calculateTmin}
                disabled={loading}
                className="w-full px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Calculating...' : 'Calculate t-min'}
              </button>
            </div>

            {tminResult && (
              <div className="bg-card border border-border rounded-lg p-6 space-y-4">
                <h3 className="font-semibold text-lg">Results</h3>
                <div className="space-y-2 text-sm">
                  <p><strong>Code:</strong> {tminResult.code}</p>
                  <p><strong>Required Thickness:</strong> {tminResult.t_required_base.toFixed(2)} mm</p>
                  <p><strong>Governing:</strong> {tminResult.governing}</p>
                  {tminResult.t_pressure && <p><strong>t-pressure:</strong> {tminResult.t_pressure.toFixed(2)} mm</p>}
                  {tminResult.t_structural && <p><strong>t-structural:</strong> {tminResult.t_structural.toFixed(2)} mm</p>}
                  {tminResult.t_circumferential && <p><strong>t-circumferential:</strong> {tminResult.t_circumferential.toFixed(2)} mm</p>}
                  {tminResult.t_longitudinal && <p><strong>t-longitudinal:</strong> {tminResult.t_longitudinal.toFixed(2)} mm</p>}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Corrosion Rate Tab */}
        {activeTab === 'corrosion' && (
          <div className="space-y-6">
            <div className="bg-card border border-border rounded-lg p-6 space-y-4">
              <h2 className="font-semibold text-lg">Corrosion Rate from Thickness History</h2>
              <div className="space-y-2">
                {readings.map((r, i) => (
                  <div key={i} className="grid grid-cols-2 gap-4">
                    <input
                      type="date"
                      value={r.date}
                      onChange={e => {
                        const newReadings = [...readings]
                        newReadings[i].date = e.target.value
                        setReadings(newReadings)
                      }}
                      className="px-3 py-2 border border-border rounded-md bg-background"
                    />
                    <input
                      type="number"
                      step="0.01"
                      placeholder="Thickness (mm)"
                      value={r.thickness_mm}
                      onChange={e => {
                        const newReadings = [...readings]
                        newReadings[i].thickness_mm = e.target.value
                        setReadings(newReadings)
                      }}
                      className="px-3 py-2 border border-border rounded-md bg-background"
                    />
                  </div>
                ))}
              </div>
              <button
                onClick={() => setReadings([...readings, { date: '', thickness_mm: '' }])}
                className="text-sm text-indigo-600 hover:underline"
              >
                + Add Reading
              </button>
              <button
                onClick={calculateCorrosion}
                disabled={loading}
                className="w-full px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Calculating...' : 'Calculate Corrosion Rate'}
              </button>
            </div>

            {corrosionResult && (
              <div className="bg-card border border-border rounded-lg p-6 space-y-4">
                <h3 className="font-semibold text-lg">Results</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg">
                    <p className="text-xs text-muted-foreground">Long-Term Rate</p>
                    <p className="text-2xl font-bold">{corrosionResult.CR_LT.toFixed(3)} mm/yr</p>
                  </div>
                  <div className="bg-orange-50 dark:bg-orange-900/20 p-4 rounded-lg">
                    <p className="text-xs text-muted-foreground">Short-Term Rate</p>
                    <p className="text-2xl font-bold">{corrosionResult.CR_ST.toFixed(3)} mm/yr</p>
                  </div>
                </div>
                <p className="text-sm"><strong>Governing:</strong> {corrosionResult.governing} ({corrosionResult.governing_rate.toFixed(3)} mm/yr)</p>
              </div>
            )}
          </div>
        )}

        {/* FMS Tab */}
        {activeTab === 'fms' && (
          <div className="space-y-6">
            <div className="bg-card border border-border rounded-lg p-6 space-y-4">
              <h2 className="font-semibold text-lg">Facility Management Score (FMS)</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {[
                  { label: 'Management of Inspection', value: managementInspection, setter: setManagementInspection },
                  { label: 'Site Management', value: siteManagement, setter: setSiteManagement },
                  { label: 'Management of Change', value: managementOfChange, setter: setManagementOfChange },
                  { label: 'Failure Investigation', value: failureInvestigation, setter: setFailureInvestigation },
                  { label: 'Process Safety', value: processSafety, setter: setProcessSafety },
                  { label: 'Operating Procedures', value: operatingProcedures, setter: setOperatingProcedures }
                ].map(({ label, value, setter }) => (
                  <div key={label}>
                    <label className="block text-sm font-medium mb-1">{label} (0-100)</label>
                    <input
                      type="number"
                      min="0"
                      max="100"
                      value={value}
                      onChange={e => setter(e.target.value)}
                      className="w-full px-3 py-2 border border-border rounded-md bg-background"
                    />
                  </div>
                ))}
              </div>
              <button
                onClick={calculateFMS}
                disabled={loading}
                className="w-full px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Calculating...' : 'Calculate FMS'}
              </button>
            </div>

            {fmsResult && (
              <div className="bg-card border border-border rounded-lg p-6 space-y-4">
                <h3 className="font-semibold text-lg">Results</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-indigo-50 dark:bg-indigo-900/20 p-4 rounded-lg">
                    <p className="text-xs text-muted-foreground">FMS Factor</p>
                    <p className="text-2xl font-bold">{fmsResult.fms.toFixed(2)}</p>
                  </div>
                  <div className="bg-purple-50 dark:bg-purple-900/20 p-4 rounded-lg">
                    <p className="text-xs text-muted-foreground">P-Score</p>
                    <p className="text-2xl font-bold">{fmsResult.pscore.toFixed(0)}</p>
                  </div>
                </div>
                <p className="text-sm"><strong>Interpretation:</strong> {fmsResult.interpretation}</p>
                <p className="text-sm"><strong>Risk Level:</strong> {fmsResult.risk_level}</p>
              </div>
            )}
          </div>
        )}

        {/* Timeline Tab */}
        {activeTab === 'timeline' && (
          <div className="space-y-6">
            <div className="bg-card border border-border rounded-lg p-6 space-y-4">
              <h2 className="font-semibold text-lg">Risk Timeline Projection</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Initial POF (per year)</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={pof0}
                    onChange={e => setPof0(e.target.value)}
                    className="w-full px-3 py-2 border border-border rounded-md bg-background"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">COF (financial)</label>
                  <input
                    type="number"
                    step="1000"
                    value={cof}
                    onChange={e => setCof(e.target.value)}
                    className="w-full px-3 py-2 border border-border rounded-md bg-background"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Corrosion Rate (mm/yr)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={corrosionRateMmYr}
                    onChange={e => setCorrosionRateMmYr(e.target.value)}
                    className="w-full px-3 py-2 border border-border rounded-md bg-background"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Actual Thickness (mm)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={tActualMm}
                    onChange={e => setTActualMm(e.target.value)}
                    className="w-full px-3 py-2 border border-border rounded-md bg-background"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Required Thickness (mm)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={tRequiredMm}
                    onChange={e => setTRequiredMm(e.target.value)}
                    className="w-full px-3 py-2 border border-border rounded-md bg-background"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Horizon (years)</label>
                  <input
                    type="number"
                    min="1"
                    max="30"
                    value={horizonYears}
                    onChange={e => setHorizonYears(e.target.value)}
                    className="w-full px-3 py-2 border border-border rounded-md bg-background"
                  />
                </div>
              </div>
              <button
                onClick={calculateTimeline}
                disabled={loading}
                className="w-full px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Calculating...' : 'Calculate Timeline'}
              </button>
            </div>

            {timelineResult && (
              <div className="bg-card border border-border rounded-lg p-6 space-y-4">
                <h3 className="font-semibold text-lg">Risk Trajectory</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={timelineResult}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="years_from_assessment" label={{ value: 'Years', position: 'insideBottom', offset: -5 }} />
                    <YAxis label={{ value: 'Risk', angle: -90, position: 'insideLeft' }} />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="risk" stroke="#4F6EF7" strokeWidth={2} name="Risk Score" />
                    <Line type="monotone" dataKey="pof" stroke="#F97316" strokeWidth={2} name="POF" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        )}

        {/* Equivalence Tab */}
        {activeTab === 'equivalence' && (
          <div className="space-y-6">
            <div className="bg-card border border-border rounded-lg p-6 space-y-4">
              <h2 className="font-semibold text-lg">Inspection Equivalence (2B = 1A)</h2>
              <div className="space-y-2">
                {inspections.map((insp, i) => (
                  <div key={i} className="grid grid-cols-3 gap-4">
                    <input
                      type="date"
                      value={insp.date}
                      onChange={e => {
                        const newInsp = [...inspections]
                        newInsp[i].date = e.target.value
                        setInspections(newInsp)
                      }}
                      className="px-3 py-2 border border-border rounded-md bg-background"
                    />
                    <select
                      value={insp.effectiveness}
                      onChange={e => {
                        const newInsp = [...inspections]
                        newInsp[i].effectiveness = e.target.value
                        setInspections(newInsp)
                      }}
                      className="px-3 py-2 border border-border rounded-md bg-background"
                    >
                      <option value="A">A - Highly Effective</option>
                      <option value="B">B - Usually Effective</option>
                      <option value="C">C - Fairly Effective</option>
                      <option value="D">D - Poorly Effective</option>
                      <option value="E">E - Ineffective</option>
                    </select>
                    <select
                      value={insp.inspection_type}
                      onChange={e => {
                        const newInsp = [...inspections]
                        newInsp[i].inspection_type = e.target.value
                        setInspections(newInsp)
                      }}
                      className="px-3 py-2 border border-border rounded-md bg-background"
                    >
                      <option value="internal">Internal</option>
                      <option value="external">External</option>
                      <option value="online">Online</option>
                      <option value="nde">NDE</option>
                    </select>
                  </div>
                ))}
              </div>
              <button
                onClick={() => setInspections([...inspections, { date: '', effectiveness: 'B', inspection_type: 'online' }])}
                className="text-sm text-indigo-600 hover:underline"
              >
                + Add Inspection
              </button>
              <button
                onClick={calculateEquivalence}
                disabled={loading}
                className="w-full px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Calculating...' : 'Calculate Equivalence'}
              </button>
            </div>

            {equivalenceResult && (
              <div className="bg-card border border-border rounded-lg p-6 space-y-4">
                <h3 className="font-semibold text-lg">Results</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-green-50 dark:bg-green-900/20 p-4 rounded-lg">
                    <p className="text-xs text-muted-foreground">Equivalent A Credit</p>
                    <p className="text-2xl font-bold">{equivalenceResult.equivalent_count.toFixed(1)}</p>
                  </div>
                  <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg">
                    <p className="text-xs text-muted-foreground">Total Inspections</p>
                    <p className="text-2xl font-bold">{equivalenceResult.total_inspections}</p>
                  </div>
                </div>
                <p className="text-sm">
                  <strong>Meets Requirement:</strong>{' '}
                  {equivalenceResult.meets_requirement ? (
                    <span className="text-green-600 dark:text-green-400">✓ Yes</span>
                  ) : (
                    <span className="text-red-600 dark:text-red-400">✗ No</span>
                  )}
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </AppLayout>
  )
}
