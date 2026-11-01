const DB_NAME = 'nyay-vision-offline'
function openDb() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1)
    request.onupgradeneeded = () => request.result.createObjectStore('uploads', { keyPath: 'id', autoIncrement: true })
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}
export async function queueUpload(file) {
  return queueUploads([file])
}
export async function queueUploads(files) {
  const db = await openDb()
  const groupId = crypto.randomUUID()
  return new Promise((resolve, reject) => {
    const tx = db.transaction('uploads', 'readwrite')
    const store = tx.objectStore('uploads')
    files.forEach(file => store.add({ file, name: file.name, type: file.type, groupId, queuedAt: new Date().toISOString() }))
    tx.oncomplete = () => resolve(groupId)
    tx.onerror = () => reject(tx.error)
  })
}
export async function readQueue() {
  const db = await openDb()
  return new Promise((resolve, reject) => {
    const request = db.transaction('uploads').objectStore('uploads').getAll()
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}
export async function removeQueued(id) {
  const db = await openDb()
  return new Promise((resolve, reject) => {
    const tx = db.transaction('uploads', 'readwrite')
    tx.objectStore('uploads').delete(id)
    tx.oncomplete = resolve
    tx.onerror = () => reject(tx.error)
  })
}
