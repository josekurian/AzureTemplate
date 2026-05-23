import React, {useEffect, useState} from 'react'
export default function Review(){
  const [items, setItems] = useState([])
  useEffect(()=>{fetch('/api/reviews/list').then(r=>r.json()).then(setItems).catch(()=>setItems([]))},[])
  return (
    <div>
      <h2>Review Queue</h2>
      <ul>{items.map((it,idx)=> <li key={idx}>{JSON.stringify(it)}</li>)}</ul>
    </div>
  )
}
