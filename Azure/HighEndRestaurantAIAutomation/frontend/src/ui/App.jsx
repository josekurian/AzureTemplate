import React, {useEffect, useState} from 'react'
import Dashboard from './Dashboard'
import Episodes from './Episodes'
import Agents from './Agents'
import Search from './Search'
import Ingest from './Ingest'
import Review from './Review'

export default function App(){
  const [view, setView] = useState('overview')
  return (
    <div className="app-root">
      <nav className="top-nav">
        <button onClick={()=>setView('overview')}>Overview</button>
        <button onClick={()=>setView('episodes')}>Episodes</button>
        <button onClick={()=>setView('agents')}>Agents</button>
        <button onClick={()=>setView('workflows')}>Workflows</button>
        <button onClick={()=>setView('search')}>Search</button>
        <button onClick={()=>setView('ingest')}>Ingest</button>
        <button onClick={()=>setView('review')}>Review</button>
      </nav>
      <main>
        {view==='overview' && <Dashboard />}
        {view==='episodes' && <Episodes />}
        {view==='agents' && <Agents />}
        {view==='workflows' && <div>Workflows view coming soon</div>}
        {view==='search' && <Search />}
        {view==='ingest' && <Ingest />}
        {view==='review' && <Review />}
      </main>
    </div>
  )
}
