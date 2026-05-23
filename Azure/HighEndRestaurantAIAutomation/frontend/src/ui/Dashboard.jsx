import React, {useEffect, useState} from 'react'

export default function Dashboard(){
  const [summary, setSummary] = useState(null)
  useEffect(()=>{fetch('/api/dashboard/summary').then(r=>r.json()).then(setSummary).catch(()=>setSummary(null))},[])
  if(!summary) return <div>Loading...</div>
  return (
    <div>
      <h2>Overview</h2>
      <p>Service: {summary.service}</p>
      <p>Mock mode: {String(summary.mock_mode)}</p>
      <p>Episodes: {summary.episodes}</p>
      <p>Agents: {summary.agents}</p>
      <p>Workflows: {summary.workflows}</p>
    </div>
  )
}
