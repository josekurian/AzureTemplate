import React, {useState} from 'react'
export default function Ingest(){
  const [file, setFile] = useState(null)
  const [res, setRes] = useState(null)
  async function upload(){
    if(!file) return alert('Choose a file')
    const fd = new FormData()
    fd.append('file', file)
    const r = await fetch('/api/ingest/upload', {method:'POST', body: fd})
    const j = await r.json()
    setRes(j)
  }
  return (
    <div>
      <h2>Ingest (upload)</h2>
      <input type="file" onChange={e=>setFile(e.target.files[0])} />
      <button onClick={upload}>Upload</button>
      <pre>{res ? JSON.stringify(res, null, 2) : 'No result yet'}</pre>
    </div>
  )
}
