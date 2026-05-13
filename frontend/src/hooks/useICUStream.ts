import { useEffect, useRef, useState } from 'react'

export interface PatientRecord {
  subject_id: string
  timestamp: string
  heart_rate: number
  spo2: number
  systolic_bp: number
  diastolic_bp: number
  mean_bp: number
  state: string
  warning: number
  dismissed: boolean
  risk_score: number    // ← add this line only
}

export type PatientMap = Map<string, PatientRecord[]>

export function useICUStream() {
  const [patients, setPatients] = useState<PatientMap>(new Map())
  const [connected, setConnected] = useState(false)
  const ws = useRef<WebSocket | null>(null)

  useEffect(() => {
    function connect() {
      ws.current = new WebSocket('ws://localhost:8000/ws')

      ws.current.onopen = () => {
        console.log('Connected to ICU stream')
        setConnected(true)
      }

      ws.current.onmessage = (event) => {
        const record: PatientRecord = JSON.parse(event.data)

        setPatients(prev => {
          const updated = new Map(prev)
          const history = updated.get(record.subject_id) ?? []
          // Keep last 20 readings per patient for the chart
          const trimmed = [...history, record].slice(-20)
          updated.set(record.subject_id, trimmed)
          return updated
        })
      }

      ws.current.onclose = () => {
        console.log('Disconnected — retrying in 2s')
        setConnected(false)
        // Auto reconnect after 2 seconds
        setTimeout(connect, 2000)
      }

      ws.current.onerror = (err) => {
        console.error('WebSocket error', err)
        ws.current?.close()
      }
    }

    connect()
    return () => ws.current?.close()
  }, [])

  const dismissAlarm = async (subjectId: string) => {
    await fetch(
      `http://localhost:8000/dismiss/${encodeURIComponent(subjectId)}`,
      { method: 'POST' }
    )
  }

  return { patients, connected, dismissAlarm }
}