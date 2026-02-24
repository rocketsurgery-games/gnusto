import type { ServerMessage } from './types'

type ConnectionState = 'connecting' | 'connected' | 'disconnected'

let connectionState = $state<ConnectionState>('disconnected')
let ws: WebSocket | null = null
let messageHandler: ((msg: ServerMessage) => void) | null = null

export function getConnectionState(): ConnectionState {
  return connectionState
}

export function onMessage(handler: (msg: ServerMessage) => void) {
  messageHandler = handler
}

export function send(data: unknown) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(data))
  }
}

export function connect() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/ws`

  connectionState = 'connecting'
  ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    console.log('Connected to game server')
    connectionState = 'connected'
  }

  ws.onmessage = (event) => {
    const message: ServerMessage = JSON.parse(event.data)
    messageHandler?.(message)
  }

  ws.onclose = () => {
    console.log('Disconnected from game server')
    connectionState = 'disconnected'
    ws = null
    setTimeout(connect, 3000)
  }

  ws.onerror = (error) => {
    console.error('WebSocket error:', error)
  }
}

export function disconnect() {
  if (ws) {
    ws.close()
    ws = null
  }
}
