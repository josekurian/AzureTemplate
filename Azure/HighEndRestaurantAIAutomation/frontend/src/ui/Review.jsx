import React, {useEffect, useState} from 'react'
export default function Review(){
  const [items, setItems] = useState([])
  useEffect(()=>{fetch('/api/reviews/list').then(r=>r.json()).then(setItems).catch(()=>setItems([]))},[])
  return (
    <div>
      <h2>Review Queue</h2>
      <table className="reviews-table">
        <thead><tr><th>#</th><th>Item</th></tr></thead>
        <tbody>{items.map((it,idx)=> <tr key={idx}><td>{idx+1}</td><td><pre style={{whiteSpace:'pre-wrap'}}>{JSON.stringify(it,null,2)}</pre></td></tr>)}</tbody>
      </table>
    </div>
  )
}
