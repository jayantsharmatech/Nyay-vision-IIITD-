import { Search, Download, FileSearch, ChevronRight } from 'lucide-react'
import { formatDate, reportUrl } from '../lib/api'
import { useState } from 'react'
export default function HistoryPanel({items,onOpen}) {
 const [query,setQuery]=useState('')
 const rows=items.filter(x=>(x.extraction?.product_name||x.filename||'').toLowerCase().includes(query.toLowerCase()))
 return <section className="card history-card"><div className="history-heading"><div><div className="eyebrow">AUDIT LOG</div><h2>Audit history</h2><p>Review completed inspections and download their reports.</p></div><div className="history-search"><Search size={16}/><input placeholder="Search product or file" value={query} onChange={e=>setQuery(e.target.value)}/></div></div>
  {rows.length?<div className="history-table-wrap"><table className="history-table"><thead><tr><th>PRODUCT / FILE</th><th>DATE</th><th>CATEGORY</th><th>SCORE</th><th>OUTCOME</th><th/></tr></thead><tbody>{rows.map(row=><tr key={row.scan_id} onClick={()=>onOpen(row)}><td><div className="product-cell"><span className="product-icon"><FileSearch size={17}/></span><span><b>{row.extraction?.product_name||row.filename}</b><small>#{row.scan_id.slice(0,8)}</small></span></div></td><td>{formatDate(row.created_at)}</td><td>{row.category}</td><td><b>{row.audit.score}</b><span className="score-outof"> / 100</span></td><td><span className={`outcome-pill ${row.audit.status}`}>{row.audit.status.replaceAll('_',' ')}</span></td><td><div className="row-actions" onClick={e=>e.stopPropagation()}><a href={reportUrl(row.scan_id)} target="_blank" rel="noreferrer" aria-label="Download report"><Download size={16}/></a><ChevronRight size={16}/></div></td></tr>)}</tbody></table></div>:<div className="empty-history"><div className="empty-icon"><FileSearch size={24}/></div><h3>{query?'No matching audits':'No audits yet'}</h3><p>{query?'Try another search term.':'Your completed package audits will appear here.'}</p></div>}
 </section>
}
