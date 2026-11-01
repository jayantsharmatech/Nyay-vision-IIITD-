const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export async function getHealth() {
  const response = await fetch(`${API}/health`)
  if (!response.ok) throw new Error('API unavailable')
  return response.json()
}
export async function getHistory() {
  const response = await fetch(`${API}/history`)
  if (!response.ok) throw new Error('Could not load scan history')
  return (await response.json()).items
}
export async function submitScan(file) {
  const body = new FormData()
  body.append('file', file)
  const response = await fetch(`${API}/scan`, { method: 'POST', body })
  const result = await response.json()
  if (!response.ok) throw new Error(result.detail || 'Scan failed')
  return result
}
export async function submitBatch(files) {
  const body = new FormData()
  files.forEach(file => body.append('files', file))
  const response = await fetch(`${API}/scan-multi`, { method: 'POST', body })
  const result = await response.json()
  if (!response.ok) throw new Error(result.detail || 'Batch scan failed')
  return result
}
export function reportUrl(id) { return `${API}/report/${id}` }
export function formatDate(value) { return new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) }
