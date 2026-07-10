// Single source of truth for all data visualization colors
export const CHART = {
  primary: '#4F6EF7',
  primaryLight: '#818CF8',
  primaryDark: '#3B4FD6',
  // Indigo family palette for multi-series (donut, clusters)
  palette: [
    '#4F6EF7', '#818CF8', '#6366F1', '#A5B4FC',
    '#4338CA', '#7C3AED', '#6D28D9', '#8B5CF6',
    '#4F46E5', '#C4B5FD', '#5B21B6', '#3730A3',
    '#A78BFA', '#312E81', '#9333EA',
  ],
  // Severity — only when semantic meaning required, still muted
  danger: '#EF4444',
  warning: '#F59E0B',
  success: '#22C55E',
  neutral: '#94A3B8',
  // Chart chrome
  grid: '#F1F5F9',
  axisLine: '#E2E8F0',
  text: '#64748B',
  title: '#1E293B',
  bg: 'transparent',
}

// Base Plotly layout — spread into every newPlot layout
export const plotlyBase = (title: string) => ({
  title: { text: title, font: { size: 13, color: CHART.title, family: 'Inter, system-ui, sans-serif' } },
  paper_bgcolor: CHART.bg,
  plot_bgcolor: CHART.bg,
  font: { size: 11, color: CHART.text, family: 'Inter, system-ui, sans-serif' },
  xaxis: { gridcolor: CHART.grid, linecolor: CHART.axisLine, tickfont: { size: 10 }, zeroline: false },
  yaxis: { gridcolor: CHART.grid, linecolor: CHART.axisLine, tickfont: { size: 10 }, zeroline: false },
})

export const plotlyConfig = { responsive: true, displayModeBar: false }

// Cluster colors — indigo shades
export const CLUSTER_COLORS = CHART.palette
