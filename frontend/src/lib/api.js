const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function request(path, options) {
  let response
  try {
    response = await fetch(`${API}${path}`, options)
  } catch {
    throw new Error(`Could not reach the Nyay Vision backend at ${API}. Start the backend locally or set VITE_API_URL to its deployed address.`)
  }
  let result
  try { result = await response.json() } catch {
    throw new Error(`The backend returned an unreadable response (${response.status}). Check that the updated backend is running at ${API}.`)
  }
  if (!response.ok) throw new Error(result.detail || `Request failed (${response.status})`)
  return result
}

export async function getHealth() {
  return request('/health')
}
export async function getHistory() {
  return (await request('/history')).items
}
export async function submitScan(file) {
  const body = new FormData()
  body.append('file', file)
  return request('/scan', { method: 'POST', body })
}
export async function submitBatch(files) {
  const body = new FormData()
  files.forEach(file => body.append('files', file))
  return request('/scan-multi', { method: 'POST', body })
}
export function reportUrl(id) { return `${API}/report/${id}` }
export function formatDate(value) { return new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) }
