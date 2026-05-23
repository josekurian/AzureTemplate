import React, {useEffect, useState} from 'react'

export default function Episodes(){
  const [episodes, setEpisodes] = useState([])
  useEffect(()=>{fetch('/api/dashboard/episodes').then(r=>r.json()).then(setEpisodes).catch(()=>setEpisodes([]))},[])
  return (
    <div>
      <h2>Episodes</h2>
      <ul>
        {episodes.map(e=> <li key={e.id}><strong>{e.title}</strong> - {e.description} <button onClick={()=>run(e.id)}>Run</button></li>)}
      </ul>
    </div>
  )
}

async function run(id){
  const res = await fetch(`/api/dashboard/run/${id}`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({})})
  const j = await res.json()
  alert('Ran '+id+': '+JSON.stringify(j))
}
