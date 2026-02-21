import './style.css'
import { marked } from 'marked'

// Configure marked for safe rendering
marked.setOptions({
  breaks: true,  // Convert \n to <br>
  gfm: true,     // GitHub Flavored Markdown
})

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

interface NarrateBlock {
  type: 'narrate'
  text: string
}

interface SpeakBlock {
  type: 'speak'
  text: string
  speaker: string | null
  manner: string | null
}

interface ThinkBlock {
  type: 'think'
  text: string
}

interface AmbientBlock {
  type: 'ambient'
  text: string
}

interface RevealBlock {
  type: 'reveal'
  text: string
  entity: string | null
}

interface FocusBlock {
  type: 'focus'
  text: string
  entity: string | null
}

interface ImageBlock {
  type: 'image'
  src: string
  alt: string
  layout: 'inline' | 'float-left' | 'float-right' | 'background'
  size: 'small' | 'medium' | 'large' | 'full'
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

interface DebugBlock {
  type: 'debug'
  label: string
  content: string
}

type ContentBlock = RoomEnterBlock | ActionResultBlock | NarrateBlock | SpeakBlock
  | ThinkBlock | AmbientBlock | RevealBlock | FocusBlock
  | ImageBlock | SystemMessageBlock | CommandBlock | DebugBlock

// Server messages
interface BlocksMessage {
  type: 'blocks'
  blocks: ContentBlock[]
}

interface TurnCompleteMessage {
  type: 'turn_complete'
}

interface ClearMessage {
  type: 'clear'
}

interface QuitMessage {
  type: 'quit'
}

interface SceneContextMessage {
  type: 'scene_context'
  entities: Record<string, { name: string; image: string | null }>
}

type ServerMessage = BlocksMessage | TurnCompleteMessage | ClearMessage | QuitMessage | SceneContextMessage

// Scene entity tracking
let sceneEntities: Record<string, { name: string; image: string | null }> = {}

function resolveEntityName(id: string): string {
  const entity = sceneEntities[id]
  if (entity) return entity.name
  // Fallback: strip @ and capitalize
  return id.replace(/^@/, '').replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function resolveEntityImage(id: string): string | null {
  return sceneEntities[id]?.image || null
}

function speakerInitial(name: string): string {
  const clean = name.replace(/^(the|a|an)\s+/i, '')
  return clean.charAt(0).toUpperCase()
}

// DOM elements
const content = document.getElementById('content')!
const inputArea = document.getElementById('input-area')!
const commandForm = document.getElementById('command-form')! as HTMLFormElement
const commandInput = document.getElementById('command-input')! as HTMLInputElement

// Track room blocks for fade effect
const roomBlocks: HTMLElement[] = []
const FADE_DISTANCE = 60 // pixels over which to fade

// Track image-bearing block count for left/right alternation
let imageBlockIndex = 0

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

function clearContent() {
  // Remove all blocks except input area
  while (content.firstChild && content.firstChild !== inputArea) {
    content.removeChild(content.firstChild)
  }
  // Clear room blocks tracking
  roomBlocks.length = 0
  imageBlockIndex = 0
}

function handleMessage(message: ServerMessage) {
  if (message.type === 'scene_context') {
    sceneEntities = message.entities
  } else if (message.type === 'blocks') {
    for (const block of message.blocks) {
      renderBlock(block)
    }
    scrollToBottom()
    updateRoomFades()
  } else if (message.type === 'turn_complete') {
    // Re-enable input only after turn is complete
    commandInput.disabled = false
    commandInput.focus()
    // Reset image alternation for next turn
    imageBlockIndex = 0
  } else if (message.type === 'clear') {
    clearContent()
  } else if (message.type === 'quit') {
    // Close connection gracefully
    if (ws) {
      ws.close()
    }
    commandInput.disabled = true
    commandInput.placeholder = 'Game ended. Refresh to restart.'
  }
}

function renderBlock(block: ContentBlock) {
  const el = document.createElement('div')
  el.className = 'block'

  switch (block.type) {
    case 'room_enter':
      el.className += ' block-room'

      // Build room meta info as separate lines
      const metaLines: string[] = []
      if (block.exits.length > 0) {
        metaLines.push(`<div>Exits: ${block.exits.join(', ')}</div>`)
      }
      if (block.objects.length > 0) {
        metaLines.push(`<div>You see: ${block.objects.join(', ')}</div>`)
      }
      if (block.inventory.length > 0) {
        metaLines.push(`<div>Carrying: ${block.inventory.join(', ')}</div>`)
      }

      // Build room content with optional image floated right
      const imageHtml = block.image
        ? `<img class="room-image" src="${escapeHtml(block.image)}" alt="${escapeHtml(block.name)}">`
        : ''

      el.innerHTML = `
        ${imageHtml}
        <h2>${escapeHtml(block.name)}</h2>
        <div class="room-desc">${styleText(block.description)}</div>
        ${metaLines.length > 0 ? `<div class="room-meta">${metaLines.join('')}</div>` : ''}
      `

      // Track room blocks for fade effect
      roomBlocks.push(el)
      break

    case 'action_result':
      el.className += ' block-action'
      el.innerHTML = styleText(block.text)
      break

    case 'narrate':
      el.className += ' block-narrate'
      el.innerHTML = styleNarrative(block.text)
      break

    case 'speak': {
      el.className += ' block-speak'
      const speakerId = block.speaker || 'unknown'
      const name = resolveEntityName(speakerId)
      const avatarImage = resolveEntityImage(speakerId)

      // Avatar
      if (avatarImage) {
        const img = document.createElement('img')
        img.className = 'speaker-avatar speaker-avatar-img'
        img.src = avatarImage
        img.alt = name
        img.onerror = () => {
          const ph = document.createElement('div')
          ph.className = 'speaker-avatar'
          ph.textContent = speakerInitial(name)
          img.replaceWith(ph)
        }
        el.appendChild(img)
      } else {
        const avatar = document.createElement('div')
        avatar.className = 'speaker-avatar'
        avatar.textContent = speakerInitial(name)
        el.appendChild(avatar)
      }

      // Speech bubble
      const bubble = document.createElement('div')
      bubble.className = 'speech-bubble'
      bubble.textContent = block.text
      if (block.manner) {
        const manner = document.createElement('span')
        manner.className = 'manner'
        manner.textContent = block.manner
        bubble.appendChild(manner)
      }
      el.appendChild(bubble)
      break
    }

    case 'think':
      el.className += ' block-think'
      el.textContent = block.text
      break

    case 'ambient':
      el.className += ' block-ambient'
      el.textContent = block.text
      break

    case 'focus': {
      const side = (imageBlockIndex % 2 === 1) ? 'image-right' : 'image-left'
      el.className += ` block-focus ${side}`

      const entityImage = block.entity ? resolveEntityImage(block.entity) : null
      if (entityImage) {
        const img = document.createElement('img')
        img.className = 'focus-image'
        img.src = entityImage
        img.alt = block.entity || ''
        img.onerror = () => img.remove()
        el.appendChild(img)
      }

      const body = document.createElement('div')
      body.className = 'focus-body'
      const focusText = document.createElement('div')
      focusText.className = 'focus-text'
      focusText.textContent = block.text
      body.appendChild(focusText)
      el.appendChild(body)

      imageBlockIndex++
      break
    }

    case 'reveal': {
      const revealSide = (imageBlockIndex % 2 === 1) ? 'image-right' : 'image-left'
      el.className += ` block-reveal ${revealSide}`

      const revealImage = block.entity ? resolveEntityImage(block.entity) : null
      if (revealImage) {
        const img = document.createElement('img')
        img.className = 'reveal-image'
        img.src = revealImage
        img.alt = block.entity || ''
        img.onerror = () => img.remove()
        el.appendChild(img)
      }

      const revealText = document.createElement('div')
      revealText.className = 'reveal-text'
      revealText.textContent = block.text
      el.appendChild(revealText)

      imageBlockIndex++
      break
    }

    case 'image':
      el.className += ` block-image image-${block.layout} image-${block.size}`
      el.innerHTML = `<img src="${escapeHtml(block.src)}" alt="${escapeHtml(block.alt)}">`
      break

    case 'system':
      el.className += ' block-system'
      if (block.level === 'error') {
        el.style.color = 'var(--accent-magenta)'
      } else if (block.level === 'warning') {
        el.style.color = 'var(--accent-yellow)'
      }
      // Render markdown for system messages (debug output, help, etc.)
      el.innerHTML = marked.parse(block.text) as string
      break

    case 'command':
      el.className += ' block-command'
      el.innerHTML = `&gt; ${escapeHtml(block.text)}`
      break

    case 'debug':
      el.className += ' block-debug'
      el.innerHTML = `<div class="debug-label">${escapeHtml(block.label)}</div><pre class="debug-content">${escapeHtml(block.content)}</pre>`
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

  // Style @references (magenta)
  html = html.replace(/@[\w-]+/g, '<span class="ref">$&</span>')

  // Convert remaining newlines to <br> for proper display
  html = html.replace(/\n/g, '<br>')

  return html
}

function styleNarrative(text: string): string {
  // Use marked to parse markdown (handles images, paragraphs, etc.)
  let html = marked.parse(text) as string

  // Apply custom styling to text content only (between > and <)
  // This avoids breaking HTML attributes
  html = html.replace(/>([^<]+)</g, (_, textContent) => {
    let styled = textContent
    // Style @references (magenta)
    styled = styled.replace(/@[\w-]+/g, '<span class="ref">$&</span>')
    return '>' + styled + '<'
  })

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
