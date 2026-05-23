import React from 'react'
import { KeyValueTable, AudioPlayer } from './Results'

export default function AgentRunResult({event}){
  if(!event) return null
  const {response} = event
  return (
    <div>
      <h3>Run result</h3>
      <KeyValueTable obj={response} />
      {response.speech && <AudioPlayer audio={response.speech} />}
    </div>
  )
}
