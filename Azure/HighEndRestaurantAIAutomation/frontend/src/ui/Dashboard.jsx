import React, {useEffect, useState} from 'react'

export default function Dashboard(){
  const [summary, setSummary] = useState(null)
  useEffect(()=>{fetch('/api/dashboard/summary').then(r=>r.json()).then(setSummary).catch(()=>setSummary(null))},[])
  if(!summary) return <div>Loading...</div>
  return (
    <div>
      <h2>Overview</h2>
      <div className="card">
        <div><strong>Service</strong>: {summary.service}</div>
        <div><strong>Mock mode</strong>: {String(summary.mock_mode)}</div>
        <div><strong>Episodes</strong>: {summary.episodes}</div>
        <div><strong>Agents</strong>: {summary.agents}</div>
        <div><strong>Workflows</strong>: {summary.workflows}</div>
      </div>
    </div>
  )
}
