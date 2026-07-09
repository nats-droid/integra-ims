'use client'
import { useEffect, useRef } from 'react'

interface Props {
  crData: {area: string, avg_cr: number}[]
  dmData: {area: string, dm_count: number}[]
  fluidData: {fluid: string, count: number}[]
  rlData: {area: string, avg_rl: number}[]
}

function ensurePlotly(): Promise<void> {
  return new Promise((resolve) => {
    if ((window as any).Plotly) return resolve()
    const s = document.createElement('script')
    s.src = 'https://cdn.plot.ly/plotly-2.35.2.min.js'
    s.onload = () => resolve()
    document.head.appendChild(s)
  })
}

export default function PlantOverviewCharts({ crData, dmData, fluidData, rlData }: Props) {
  const crRef = useRef<HTMLDivElement>(null)
  const dmRef = useRef<HTMLDivElement>(null)
  const fluidRef = useRef<HTMLDivElement>(null)
  const rlRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!crData.length && !dmData.length && !fluidData.length && !rlData.length) return
    ensurePlotly().then(() => {
      const P = (window as any).Plotly
      const layout = (title: string) => ({
        title, paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
        font: { size: 11 }, margin: { t: 40, b: 80, l: 60, r: 20 },
        height: 320,
      })

      // CR per area
      if (crRef.current && crData.length) {
        P.newPlot(crRef.current, [{
          type: 'bar', x: crData.map(d => d.area), y: crData.map(d => d.avg_cr),
          marker: { color: crData.map(d => d.avg_cr > 0.5 ? '#EF4444' : d.avg_cr > 0.2 ? '#F59E0B' : '#22C55E') },
          text: crData.map(d => d.avg_cr.toFixed(3)), textposition: 'outside',
        }], { ...layout('Average Corrosion Rate by Area (mm/yr)'), xaxis: { tickangle: -30 } }, { responsive: true, displayModeBar: false })
      }

      // DM per area
      if (dmRef.current && dmData.length) {
        P.newPlot(dmRef.current, [{
          type: 'bar', x: dmData.map(d => d.area), y: dmData.map(d => d.dm_count),
          marker: { color: '#4F6EF7' },
          text: dmData.map(d => d.dm_count), textposition: 'outside',
        }], { ...layout('Active Damage Mechanisms by Area'), xaxis: { tickangle: -30 } }, { responsive: true, displayModeBar: false })
      }

      // Fluid donut
      if (fluidRef.current && fluidData.length) {
        P.newPlot(fluidRef.current, [{
          type: 'pie', hole: 0.45,
          labels: fluidData.map(d => d.fluid),
          values: fluidData.map(d => d.count),
          textinfo: 'label+percent',
        }], { ...layout('Fluid Service Distribution'), height: 340, margin: { t: 40, b: 20, l: 20, r: 20 } }, { responsive: true, displayModeBar: false })
      }

      // RL per area
      if (rlRef.current && rlData.length) {
        P.newPlot(rlRef.current, [{
          type: 'bar', x: rlData.map(d => d.area), y: rlData.map(d => d.avg_rl),
          marker: { color: rlData.map(d => d.avg_rl < 2 ? '#EF4444' : d.avg_rl < 5 ? '#F59E0B' : '#22C55E') },
          text: rlData.map(d => d.avg_rl.toFixed(1) + ' yr'), textposition: 'outside',
        }], { ...layout('Average Remaining Life by Area (years)'), xaxis: { tickangle: -30 } }, { responsive: true, displayModeBar: false })
      }
    })
  }, [crData, dmData, fluidData, rlData])

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="border rounded-lg p-4 bg-card"><div ref={crRef} /></div>
      <div className="border rounded-lg p-4 bg-card"><div ref={dmRef} /></div>
      <div className="border rounded-lg p-4 bg-card"><div ref={fluidRef} /></div>
      <div className="border rounded-lg p-4 bg-card"><div ref={rlRef} /></div>
    </div>
  )
}
