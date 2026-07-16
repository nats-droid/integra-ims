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
