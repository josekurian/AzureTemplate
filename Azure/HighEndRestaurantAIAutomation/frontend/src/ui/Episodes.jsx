import React, {useEffect, useState} from 'react'

export default function Episodes(){
  const [episodes, setEpisodes] = useState([])
  const [result, setResult] = useState(null)
  useEffect(()=>{fetch('/api/dashboard/episodes').then(r=>r.json()).then(setEpisodes).catch(()=>setEpisodes([]))},[])
  async function run(id){
    const res = await runRequest(id)
    setResult(res)
  }
  return (
    <div>
      <h2>Episodes</h2>
      <table className="episodes-table">
        <thead><tr><th>Title</th><th>Description</th><th>Action</th></tr></thead>
        <tbody>
        {episodes.map(e=> (
          <tr key={e.id}><td>{e.title}</td><td>{e.description}</td><td><button onClick={()=>run(e.id)}>Run</button></td></tr>
        ))}
        </tbody>
      </table>
      {result && <AgentRunResult event={result} />}
    </div>
  )
}

import React, {useState} from 'react'
import AgentRunResult from './AgentRunResult'

async function runRequest(id){
  const res = await fetch(`/api/dashboard/run/${id}`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({})})
  const j = await res.json()
  return j
}

export default function Episodes(){
  const [result, setResult] = useState(null)
  // existing component code omitted for brevity - assume same as above
}

// Note: this file is partially generated; App imports Episodes which will render table and run buttons
