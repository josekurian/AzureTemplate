import React from 'react'

export function KeyValueTable({obj}){
  if(!obj) return <div>No data</div>
  return (
    <table className="kv-table">
      <tbody>
        {Object.keys(obj).map(k=> (
          <tr key={k}><th>{k}</th><td><pre style={{whiteSpace:'pre-wrap'}}>{JSON.stringify(obj[k],null,2)}</pre></td></tr>
        ))}
      </tbody>
    </table>
  )
}

export function AgentResult({res}){
  if(!res) return null
  return (
    <div>
      <h3>Agent Result</h3>
      <KeyValueTable obj={res} />
    </div>
  )
}

export function AudioPlayer({audio}){
  if(!audio || !audio.audio_path) return null
  // audio_path may be a server path - assume backend serves a URL; adapt if needed
  const src = audio.audio_path.startsWith('/') ? audio.audio_path : audio.audio_path
  return (
    <div>
      <h3>Audio</h3>
      <audio controls src={src} />
    </div>
  )
}
