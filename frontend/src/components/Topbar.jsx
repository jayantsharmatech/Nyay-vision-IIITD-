import React from 'react'
import { Bell, Search, Wifi, WifiOff, ChevronDown } from 'lucide-react'
export default function Topbar({ online, apiReachable, apiReady }) {
  const status = !online ? 'Offline mode' : !apiReachable ? 'Backend unavailable' : !apiReady ? 'OpenAI key required' : 'Systems operational'
  return <header className="topbar"><div className="breadcrumbs"><span>Workspace</span><b>/</b><strong>Metrology Guard</strong></div><div className="topbar-actions"><div className={`service-status ${online&&apiReachable&&apiReady?'connected':'disconnected'}`}><span className="status-dot"/>{status}</div><button className="icon-button" aria-label="Search"><Search size={18}/></button><button className="icon-button notification" aria-label="Notifications"><Bell size={18}/><i/></button><div className="top-avatar">AJ</div><ChevronDown size={15} className="chevron"/></div></header>
  }
