import './style.css'

// Content block types (matching Python render.py)
interface RoomEnterBlock {
  type: 'room_enter'
  room_id: string
  name: string
  description: string
  exits: string[]
  objects: string[]
  inventory: string[]
  image: string | null
}

interface ActionResultBlock {
  type: 'action_result'
  text: string
}

interface NarrativeBlock {
  type: 'narrative'
  text: string
}

interface ImageBlock {
  type: 'image'
  src: string
  alt: string
}

interface SystemMessageBlock {
  type: 'system'
  text: string
  level: 'info' | 'warning' | 'error'
}

interface CommandBlock {
  type: 'command'
  text: string
}

type ContentBlock = RoomEnterBlock | ActionResultBlock | NarrativeBlock | ImageBlock | SystemMessageBlock | CommandBlock

// Server messages
interface BlocksMessage {
  type: 'blocks'
  blocks: ContentBlock[]
}

interface TurnCompleteMessage {
  type: 'turn_complete'
}

type ServerMessage = BlocksMessage | TurnCompleteMessage

// DOM elements
const content = document.getElementById('content')!
const inputArea = document.getElementById('input-area')!
const commandForm = document.getElementById('command-form')! as HTMLFormElement
const commandInput = document.getElementById('command-input')! as HTMLInputElement

// Track room blocks for fade effect
const roomBlocks: HTMLElement[] = []
const FADE_DISTANCE = 60 // pixels over which to fade

// WebSocket connection
let ws: WebSocket | null = null

function connect() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/ws`

  ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    console.log('Connected to game server')
    commandInput.disabled = false
    commandInput.placeholder = 'What do you want to do?'
    commandInput.focus()
  }

  ws.onmessage = (event) => {
    const message: ServerMessage = JSON.parse(event.data)
    handleMessage(message)
  }

  ws.onclose = () => {
    console.log('Disconnected from game server')
    commandInput.disabled = true
    commandInput.placeholder = 'Disconnected. Refresh to reconnect.'
    setTimeout(connect, 3000)
  }

  ws.onerror = (error) => {
    console.error('WebSocket error:', error)
  }
}

function handleMessage(message: ServerMessage) {
  if (message.type === 'blocks') {
    for (const block of message.blocks) {
      renderBlock(block)
    }
    scrollToBottom()
    updateRoomFades()
  } else if (message.type === 'turn_complete') {
    // Re-enable input only after turn is complete
    commandInput.disabled = false
    commandInput.focus()
  }
}

function renderBlock(block: ContentBlock) {
  const el = document.createElement('div')
  el.className = 'block'

  switch (block.type) {
    case 'room_enter':
      el.className += ' block-room'

      // Build room meta info
      const metaParts: string[] = []
      if (block.exits.length > 0) {
        metaParts.push(`<span>Exits: ${block.exits.join(', ')}</span>`)
      }
      if (block.objects.length > 0) {
        metaParts.push(`<span>You see: ${block.objects.join(', ')}</span>`)
      }
      if (block.inventory.length > 0) {
        metaParts.push(`<span>Carrying: ${block.inventory.join(', ')}</span>`)
      }

      el.innerHTML = `
        <h2>${escapeHtml(block.name)}</h2>
        <div class="room-desc">${styleText(block.description)}</div>
        ${metaParts.length > 0 ? `<div class="room-meta">${metaParts.join('')}</div>` : ''}
      `

      // Show image if present (insert before the room block)
      if (block.image) {
        const imgEl = document.createElement('div')
        imgEl.className = 'block block-image'
        imgEl.innerHTML = `<img src="${escapeHtml(block.image)}" alt="${escapeHtml(block.name)}">`
        content.insertBefore(imgEl, inputArea)
      }

      // Track room blocks for fade effect
      roomBlocks.push(el)
      break

    case 'action_result':
      el.className += ' block-action'
      el.innerHTML = styleText(block.text)
      break

    case 'narrative':
      el.className += ' block-narrative'
      el.innerHTML = styleText(block.text)
      break

    case 'image':
      el.className += ' block-image'
      el.innerHTML = `<img src="${escapeHtml(block.src)}" alt="${escapeHtml(block.alt)}">`
      break

    case 'system':
      el.className += ' block-system'
      if (block.level === 'error') {
        el.style.color = 'var(--accent-magenta)'
      } else if (block.level === 'warning') {
        el.style.color = 'var(--accent-yellow)'
      }
      el.innerHTML = escapeHtml(block.text)
      break

    case 'command':
      el.className += ' block-command'
      el.innerHTML = `&gt; ${escapeHtml(block.text)}`
      break
  }

  // Insert before the input area to keep it at the bottom
  content.insertBefore(el, inputArea)
}

function escapeHtml(text: string): string {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

function styleText(text: string): string {
  // Escape HTML first
  let html = escapeHtml(text)

  // Style @references
  html = html.replace(/@[\w-]+/g, '<span class="ref">$&</span>')

  // Style "dialogue"
  html = html.replace(/"[^"]*"/g, '<span class="dialogue">$&</span>')

  return html
}

function scrollToBottom() {
  // Scroll so the input is visible
  inputArea.scrollIntoView({ behavior: 'smooth', block: 'end' })
}

function sendCommand(command: string) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    // Disable input while waiting for response
    commandInput.disabled = true

    // Show the command locally
    renderBlock({ type: 'command', text: command })
    scrollToBottom()

    ws.send(JSON.stringify({
      type: 'command',
      text: command
    }))
  }
}

// Handle form submission
commandForm.onsubmit = (e) => {
  e.preventDefault()
  const command = commandInput.value.trim()
  if (command) {
    sendCommand(command)
    commandInput.value = ''
  }
}

// Handle scroll for fading room panels
function updateRoomFades() {
  if (roomBlocks.length < 2) return

  for (let i = 0; i < roomBlocks.length - 1; i++) {
    const current = roomBlocks[i]
    const next = roomBlocks[i + 1]

    const nextRect = next.getBoundingClientRect()

    // Fade based on how close the next room is to the viewport top
    // When next room hits top (nextRect.top <= 0), current should be invisible
    // Start fading when next room is within FADE_DISTANCE of top
    if (nextRect.top <= 0) {
      current.style.opacity = '0'
    } else if (nextRect.top <= FADE_DISTANCE) {
      const opacity = nextRect.top / FADE_DISTANCE
      current.style.opacity = String(opacity)
    } else {
      current.style.opacity = '1'
    }
  }

  // Last room is always fully visible
  if (roomBlocks.length > 0) {
    roomBlocks[roomBlocks.length - 1].style.opacity = '1'
  }
}

window.addEventListener('scroll', updateRoomFades, { passive: true })

// Start connection
connect()
