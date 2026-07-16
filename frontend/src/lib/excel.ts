import * as XLSX from 'xlsx'

export function exportEquipmentExcel(equipment: any[], cmls: any[]) {
  const wb = XLSX.utils.book_new()
  const eqSheet = XLSX.utils.json_to_sheet(equipment)
  eqSheet['!cols'] = [
    {wch:15},{wch:15},{wch:20},{wch:20},{wch:20},
    {wch:12},{wch:12},{wch:15},{wch:15},{wch:30},
  ]
  XLSX.utils.book_append_sheet(wb, eqSheet, 'Equipment')
  const cmlSheet = XLSX.utils.json_to_sheet(cmls)
  cmlSheet['!cols'] = [
    {wch:15},{wch:15},{wch:18},{wch:18},{wch:12},{wch:12},
  ]
  XLSX.utils.book_append_sheet(wb, cmlSheet, 'CML Points')
  XLSX.writeFile(wb, `integra_master_data_${new Date().toISOString().slice(0,10)}.xlsx`)
}

export function parseImportExcel(file: File): Promise<{equipment: any[], cmls: any[]}> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const data = new Uint8Array(e.target?.result as ArrayBuffer)
        const wb = XLSX.read(data, {type: 'array'})
        const eqSheet = wb.Sheets['Equipment']
        const cmlSheet = wb.Sheets['CML Points']
        if (!eqSheet || !cmlSheet) {
          reject(new Error('File must have "Equipment" and "CML Points" sheets'))
          return
        }
        resolve({
          equipment: XLSX.utils.sheet_to_json(eqSheet),
          cmls: XLSX.utils.sheet_to_json(cmlSheet),
        })
      } catch (err) { reject(err) }
    }
    reader.readAsArrayBuffer(file)
  })
}

export function exportRLExcel(rows: any[]) {
  const XLSX = require('xlsx')
  const data = rows.map(r => ({
    'Equipment Tag': r.tag,
    'Type': r.type,
    'Area': r.area_name || '—',
    'Governing CML': r.governing_cml || '—',
    'Remaining Life (yr)': r.governing_rl_years !== null ? Number(r.governing_rl_years.toFixed(2)) : null,
    'Risk Level': r.governing_rl_years === null ? '—' : r.governing_rl_years < 2 ? 'Critical' : r.governing_rl_years < 5 ? 'Monitor' : 'Adequate',
    'Last Computed': r.computed_at ? new Date(r.computed_at).toLocaleDateString() : '—',
  }))
  const wb = XLSX.utils.book_new()
  const ws = XLSX.utils.json_to_sheet(data)
  ws['!cols'] = [{wch:15},{wch:12},{wch:20},{wch:18},{wch:18},{wch:12},{wch:15}]
  XLSX.utils.book_append_sheet(wb, ws, 'Remaining Life')
  XLSX.writeFile(wb, `integra_remaining_life_${new Date().toISOString().slice(0,10)}.xlsx`)
}
