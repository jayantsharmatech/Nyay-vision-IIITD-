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
  const db = await openDb()
  return new Promise((resolve, reject) => {
    const tx = db.transaction('uploads', 'readwrite')
    tx.objectStore('uploads').add({ file, name: file.name, type: file.type, queuedAt: new Date().toISOString() })
    tx.oncomplete = () => resolve()
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
