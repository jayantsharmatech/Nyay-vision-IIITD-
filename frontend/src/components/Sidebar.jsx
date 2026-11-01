import React from 'react'
import { ShieldCheck, LayoutDashboard, ScanLine, History, BookOpen, Settings, CircleHelp, ChevronLeft, ChevronRight } from 'lucide-react'

export default function Sidebar({ active, setActive, collapsed, setCollapsed }) {
  const links = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard },
    { id: 'audit', label: 'New audit', icon: ScanLine },
    { id: 'history', label: 'Audit history', icon: History },
  ]
  return <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
    <div className="brand"><div className="brand-mark"><ShieldCheck size={21}/></div><div className="brand-copy"><b>Nyay Vision</b><span>METROLOGY GUARD AI</span></div></div>
    {collapsed&&<button className="rail-expand" onClick={()=>setCollapsed(false)} aria-label="Expand sidebar"><ChevronRight size={15}/></button>}
    <div className="workspace-label">WORKSPACE</div>
    <nav>{links.map(({id,label,icon:Icon}) => <button key={id} className={`nav-link ${active===id?'active':''}`} onClick={()=>setActive(id)} title={label}><Icon size={18}/><span>{label}</span>{id==='audit'&&<i className="nav-plus">+</i>}</button>)}</nav>
    <div className="sidebar-bottom"><div className="sidebar-divider"/><div className="workspace-label">RESOURCES</div>
      <button className="nav-link" onClick={()=>setActive('guidelines')}><BookOpen size={18}/><span>Compliance guide</span></button>
      <button className="nav-link" onClick={()=>setActive('help')}><CircleHelp size={18}/><span>Help & support</span></button>
      <button className="nav-link" onClick={()=>setActive('settings')}><Settings size={18}/><span>Settings</span></button>
      <div className="profile"><div className="avatar">NV</div><div className="profile-copy"><b>Compliance team</b><span>Workspace admin</span></div><button className="collapse-btn" onClick={()=>setCollapsed(!collapsed)} aria-label="Collapse sidebar"><ChevronLeft size={16}/></button></div>
    </div>
  </aside>
}
