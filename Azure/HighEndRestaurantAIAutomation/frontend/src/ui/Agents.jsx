import React, {useEffect, useState} from 'react'
export default function Agents(){
  const [agents, setAgents] = useState([])
  useEffect(()=>{fetch('/api/dashboard/agents').then(r=>r.json()).then(setAgents).catch(()=>setAgents([]))},[])
  return (
    <div>
      <h2>Agents</h2>
      <ul>{agents.map(a=> <li key={a.id}>{a.name} — {a.type}</li>)}</ul>
    </div>
  )
}
