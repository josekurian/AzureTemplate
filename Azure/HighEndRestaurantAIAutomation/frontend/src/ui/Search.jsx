import React, {useState} from 'react'
export default function Search(){
  const [q, setQ] = useState('')
  const [res, setRes] = useState(null)
  async function doSearch(){
    const r = await fetch(`/api/search?q=${encodeURIComponent(q)}`)
    const j = await r.json()
    setRes(j)
  }
  return (
    <div>
      <h2>Search</h2>
      <input value={q} onChange={e=>setQ(e.target.value)} placeholder="query" />
      <button onClick={doSearch}>Search</button>
      <pre>{res ? JSON.stringify(res, null, 2) : 'No results'}</pre>
    </div>
  )
}
