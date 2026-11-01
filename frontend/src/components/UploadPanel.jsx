import { useRef, useState } from 'react'
import { Upload, Image as ImageIcon, X, ShieldCheck, Sparkles, Camera, ScanSearch } from 'lucide-react'

export default function UploadPanel({ onScan, busy, queuedCount }) {
  const inputRef = useRef(null), [files, setFiles] = useState([]), [dragging, setDragging] = useState(false)
  function addFiles(list) { setFiles(current => [...current, ...Array.from(list).filter(f => f.type.startsWith('image/')).slice(0, 10-current.length)]) }
  function removeFile(index) { setFiles(current => current.filter((_, i) => i !== index)) }
  return <div className="audit-layout"><section className="card upload-card"><div className="section-heading"><div><div className="eyebrow">START A NEW AUDIT</div><h2>Upload packaging images</h2><p>Capture the front and back panels for a more complete review.</p></div><div className="secure-pill"><ShieldCheck size={14}/> Private & secure</div></div>
    <div className={`dropzone ${dragging?'dragging':''}`} onDragOver={e=>{e.preventDefault();setDragging(true)}} onDragLeave={()=>setDragging(false)} onDrop={e=>{e.preventDefault();setDragging(false);addFiles(e.dataTransfer.files)}} onClick={()=>inputRef.current?.click()}>
      <input ref={inputRef} type="file" accept="image/png,image/jpeg,image/webp" multiple hidden onChange={e=>{addFiles(e.target.files);e.target.value=''}} />
      <div className="upload-icon"><Upload size={21}/></div><h3>Drop your images here, or <button className="browse-button" type="button">browse files</button></h3><p>PNG, JPG or WEBP · up to 12 MB per image · 10 images per batch</p>
      <button type="button" className="camera-hint" onClick={e=>{e.stopPropagation();inputRef.current?.click()}}><Camera size={14}/> Use a clear, well-lit photo</button>
    </div>
    {files.length>0&&<div className="file-list">{files.map((file,index)=><div className="file-item" key={`${file.name}-${index}`}><div className="file-thumb"><ImageIcon size={17}/></div><div className="file-meta"><b>{file.name}</b><span>{(file.size/1024/1024).toFixed(2)} MB · Ready to scan</span></div><button className="remove-file" onClick={()=>removeFile(index)} aria-label="Remove file"><X size={16}/></button></div>)}</div>}
    <div className="smart-category-note"><div className="smart-category-icon"><ScanSearch size={17}/></div><div><b>Automatic product classification</b><span>Vision identifies the product type and selects the relevant checks. Food safety rules will not be applied to general non-food items.</span></div></div>
    <div className="upload-footer"><div className="processing-note"><Sparkles size={15}/><span>AI-assisted review · Usually under 30 seconds</span></div><button className="primary-button" disabled={!files.length||busy} onClick={()=>onScan(files)}>{busy?<><span className="spinner"/>Analyzing…</>:<>Run compliance audit <span>→</span></>}</button></div>
    {queuedCount>0&&<div className="queued-note">{queuedCount} upload{queuedCount===1?'':'s'} queued on this device. They will sync when your connection is restored.</div>}
  </section><aside className="audit-side"><div className="info-card"><div className="info-icon"><ShieldCheck size={19}/></div><h3>Built for India’s packaging rules</h3><p>Review the declarations commonly required under the Legal Metrology (Packaged Commodities) Rules, 2011.</p><div className="info-separator"/><div className="law-ref"><span>RULE 6</span><span>Mandatory declarations</span></div><div className="law-ref"><span>SECTION 36</span><span>Non-standard packages</span></div><a href="https://consumeraffairs.gov.in/pages/legal-metrology-overview" target="_blank" rel="noreferrer">Explore legal metrology overview <span>↗</span></a></div>
    <div className="tip-card"><div className="tip-title"><Sparkles size={15}/> PHOTO TIPS</div><ul><li>Include the complete package panel</li><li>Avoid glare over printed declarations</li><li>Upload front and back for best results</li></ul></div>
    <div className="privacy-line"><ShieldCheck size={14}/> Images are processed securely through your OpenAI API connection.</div></aside></div>
}
