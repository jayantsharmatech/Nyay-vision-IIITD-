const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const DIRECT_UPLOADS = import.meta.env.VITE_DIRECT_UPLOADS === 'true'

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
  if (DIRECT_UPLOADS) return submitS3Batch([file])
  const body = new FormData()
  body.append('file', file)
  return request('/scan', { method: 'POST', body })
}
export async function submitBatch(files) {
  if (DIRECT_UPLOADS) return submitS3Batch(files)
  const body = new FormData()
  files.forEach(file => body.append('files', file))
  return request('/scan-multi', { method: 'POST', body })
}
async function submitS3Batch(files) {
  const metadata = files.map(file => ({ filename: file.name, content_type: file.type || mimeFromName(file.name) }))
  const { uploads } = await request('/uploads/presign', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ files: metadata }),
  })
  await Promise.all(uploads.map(async (upload, index) => {
    const response = await fetch(upload.url, {
      method: 'PUT',
      headers: { 'Content-Type': upload.content_type },
      body: files[index],
    })
    if (!response.ok) throw new Error(`Could not upload ${files[index].name} to secure storage (${response.status}). Please retry.`)
  }))
  const job = await request('/scan-objects', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ files: uploads.map((upload, index) => ({ key: upload.key, filename: files[index].name, content_type: upload.content_type })) }),
  })
  for (let attempt = 0; attempt < 180; attempt += 1) {
    if (attempt) await new Promise(resolve => setTimeout(resolve, 2000))
    const status = await request(`/jobs/${encodeURIComponent(job.job_id)}`)
    if (status.status === 'completed') return request(`/scan/${encodeURIComponent(status.scan_id)}`)
    if (status.status === 'failed') throw new Error(status.error || 'Image analysis failed. Please retry.')
  }
  throw new Error('This scan is still processing. Refresh Audit history in a few moments before submitting it again.')
}
function mimeFromName(name) {
  const ext = name.toLowerCase().split('.').pop()
  return ({ png: 'image/png', jpg: 'image/jpeg', jpeg: 'image/jpeg', webp: 'image/webp' })[ext] || ''
}
export function reportUrl(id) { return `${API}/report/${id}` }
export function formatDate(value) { return new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) }
