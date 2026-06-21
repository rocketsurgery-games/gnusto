<script lang="ts">
  import { onMount } from 'svelte'
  import type { RoomEnterBlock, ContentBlock, RenderableBlock, ServerMessage } from './lib/types'
  import { connect, onMessage, send } from './lib/websocket.svelte'
  import { updateEntities, resolveEntityName } from './lib/entities.svelte'

  import PagedStream from './components/PagedStream.svelte'
  import RightSidebar from './components/RightSidebar.svelte'
  import InputBar from './components/InputBar.svelte'
  import PeekTab from './components/PeekTab.svelte'
  import SatchelOverlay from './components/SatchelOverlay.svelte'
  import HelpOverlay from './components/HelpOverlay.svelte'
  import StateOverlay from './components/StateOverlay.svelte'
  import SettingsOverlay from './components/SettingsOverlay.svelte'
  import SaveLoadOverlay from './components/SaveLoadOverlay.svelte'
  import KnowledgeOverlay from './components/KnowledgeOverlay.svelte'

  // Live room state — feeds the affordance sidebar. The establishing image is
  // no longer pinned here; it enters the stream as a frozen panel (4ac5.1).
  let currentRoom = $state<RoomEnterBlock | null>(null)

  // Narrative blocks — the panel stream (establishing panels included)
  let blocks = $state<RenderableBlock[]>([])

  // Image alternation counter
  let imageBlockIndex = 0

  // Input enabled state
  let inputEnabled = $state(false)

  // Game ended state
  let gameEnded = $state(false)

  // Mobile sidebar state
  let rightSidebarOpen = $state(false)

  // Whether the reader is on the LIVE page (vs a history page). The live
  // ground-truth frame + summons only show here (gnusto-4ac5.2).
  let viewingLive = $state(true)

  // Prefill text for the input bar (clicking an entity types its name; the
  // player phrases the intent and the LLM interprets it — no action menus).
  let inputPrefill = $state<string | null>(null)

  // Debug mode (tracked from server responses)
  let debugMode = $state(false)

  // State overlay content (from backend)
  let stateContent = $state<string | null>(null)

  // Knowledge overlay content (from backend)
  let kgContent = $state<string | null>(null)

  // Save/load overlay state
  let savesList = $state<{ slot: string; timestamp: string }[]>([])
  let savesLoading = $state(true)
  let savesStatus = $state<string | null>(null)
  let savesStatusError = $state(false)

  // Active overlay panel (null = none)
  let activeOverlay = $state<string | null>(null)

  function closeOverlay() {
    activeOverlay = null
  }

  // Clicking an entity (in the stream or the live frame) is a narrow QoL
  // affordance only: it types the entity's name into the input for the player
  // to phrase an intent. We deliberately do NOT enumerate actions — the LLM
  // interprets free text, which keeps internal/easter-egg verbs out of the UI.
  function handleEntityClick(entityId: string) {
    inputPrefill = resolveEntityName(entityId)
  }

  function handleMessage(message: ServerMessage) {
    if (message.type === 'theme') {
      applyTheme(message.swatches)
    } else if (message.type === 'scene_context') {
      updateEntities(message.entities)
    } else if (message.type === 'blocks') {
      for (const block of message.blocks) {
        addBlock(block)
      }
    } else if (message.type === 'turn_complete') {
      inputEnabled = true
    } else if (message.type === 'clear') {
      blocks = []
      currentRoom = null
      imageBlockIndex = 0
    } else if (message.type === 'state_update') {
      if (currentRoom) {
        currentRoom = { ...currentRoom,
          exits: message.exits,
          objects: message.objects,
          inventory: message.inventory,
        }
      }
    } else if (message.type === 'quit') {
      gameEnded = true
      inputEnabled = false
    } else if (message.type === 'state-context') {
      stateContent = message.content
    } else if (message.type === 'kg-context') {
      kgContent = message.content
    } else if (message.type === 'saves-list') {
      savesList = message.saves
      savesLoading = false
    } else if (message.type === 'save-result') {
      savesStatus = message.message
      savesStatusError = !message.success
      if (message.success) {
        send({ type: 'list-saves' })
      }
    } else if (message.type === 'load-result') {
      if (message.success) {
        closeOverlay()
      } else {
        savesStatus = message.message
        savesStatusError = true
      }
    }
  }

  // Apply the game's declared palette swatches as --game-* CSS vars. This is the
  // single source (world :visual-style :swatches) that also keys the art, so the
  // chrome and the generated art can't drift (gnusto-4ac5.9).
  function applyTheme(swatches: Record<string, string>) {
    const root = document.documentElement
    for (const [token, hex] of Object.entries(swatches)) {
      root.style.setProperty(`--game-${token}`, hex)
    }
  }

  function addBlock(block: ContentBlock) {
    // RoomEnter → a frozen establishing panel enters the stream, AND we update
    // the live room state that feeds the affordance sidebar (4ac5.1).
    if (block.type === 'room_enter') {
      currentRoom = block
      blocks = [...blocks, { ...block }]
      return
    }

    // Track debug mode from system messages
    if (block.type === 'system' && block.text.startsWith('Debug mode: ')) {
      debugMode = block.text === 'Debug mode: on'
    }

    // Stamp image side for focus/reveal blocks
    const renderable: RenderableBlock = { ...block }
    if (block.type === 'focus' || block.type === 'reveal') {
      renderable._side = (imageBlockIndex % 2 === 1) ? 'image-right' : 'image-left'
      imageBlockIndex++
    }

    blocks = [...blocks, renderable]
  }

  function handleCommand(command: string) {
    // Intercept client-side commands
    const normalized = command.replace(/^\//, '').toLowerCase()
    if (normalized === 'help' || normalized === 'h' || normalized === '?') {
      blocks = [...blocks, { type: 'command', text: command }]
      activeOverlay = 'help'
      return
    }
    if (normalized === 'state' || normalized === 's') {
      blocks = [...blocks, { type: 'command', text: command }]
      stateContent = null
      activeOverlay = 'state'
      send({ type: 'get-state' })
      return
    }
    if (normalized === 'settings') {
      blocks = [...blocks, { type: 'command', text: command }]
      activeOverlay = 'settings'
      return
    }
    if (normalized === 'saves' || normalized.startsWith('save') || normalized.startsWith('load')) {
      const parts = normalized.split(/\s+/)
      const cmd = parts[0]
      const slot = parts[1] || ''

      if (cmd === 'saves' || cmd === 'save' || cmd === 'load') {
        blocks = [...blocks, { type: 'command', text: command }]
        savesLoading = true
        savesStatus = null
        savesStatusError = false
        activeOverlay = 'saves'
        send({ type: 'list-saves' })
        // Auto-trigger save/load if a slot was specified
        if (cmd === 'save' && slot) {
          send({ type: 'save', slot })
        } else if (cmd === 'load' && slot) {
          send({ type: 'load', slot })
        }
        return
      }
    }

    if (normalized === 'kg' || normalized.startsWith('kg ')) {
      const arg = normalized.slice(2).trim()
      blocks = [...blocks, { type: 'command', text: command }]
      kgContent = null
      activeOverlay = 'kg'
      send({ type: 'get-kg', arg })
      return
    }

    inputEnabled = false
    // Show command locally
    blocks = [...blocks, { type: 'command', text: command }]
    send({ type: 'command', text: command })
  }

  onMount(() => {
    // Per-game theme chrome (gnusto-4ac5.9): pull in the active game's optional
    // theme.css (fonts/SFX lettering, panel chrome). Appended to <head> AFTER
    // the bundled styles so equal-specificity game overrides win; colours stay
    // single-sourced from Grue via the inline --game-* vars (which beat any
    // stylesheet). The backend always 200s this route (empty when absent).
    const themeLink = document.createElement('link')
    themeLink.rel = 'stylesheet'
    themeLink.href = '/game/theme.css'
    document.head.appendChild(themeLink)

    // Restore persisted font size
    const savedSize = localStorage.getItem('gnusto-font-size')
    if (savedSize) {
      document.documentElement.style.fontSize = `${savedSize}px`
    }

    onMessage(handleMessage)
    connect()
  })
</script>

<svelte:window onkeydown={(e) => {
  if (e.key === 'Escape' && activeOverlay) { closeOverlay(); e.preventDefault() }
}} />

<div class="game-content">
  <PagedStream {blocks} onentityclick={handleEntityClick}
    onfollowingchange={(f: boolean) => viewingLive = f} />
</div>
<RightSidebar room={currentRoom} visible={viewingLive}
  onprefill={(t: string) => inputPrefill = t}
  open={rightSidebarOpen} onclose={() => rightSidebarOpen = false} />
<InputBar enabled={inputEnabled} {gameEnded} prefill={inputPrefill}
  oncommand={handleCommand} onprefillconsumed={() => inputPrefill = null} />
{#if viewingLive}
  <PeekTab side="right" ontoggle={() => rightSidebarOpen = !rightSidebarOpen} />

  <!-- Journal summon (gnusto-4ac5.2): opens the satchel; the map joins as a tab
       once the auto-map lands (gnusto-4ac5.2.1). Live-page only. -->
  <button class="journal-fab" onclick={() => activeOverlay = 'satchel'} title="Open your satchel">
    <span class="journal-glyph" aria-hidden="true">◈</span>
    <span class="journal-label">Satchel</span>
    {#if (currentRoom?.inventory.length ?? 0) > 0}
      <span class="journal-count">{currentRoom?.inventory.length}</span>
    {/if}
  </button>
{/if}

{#if activeOverlay === 'help'}
  <HelpOverlay onclose={closeOverlay} />
{:else if activeOverlay === 'state'}
  <StateOverlay content={stateContent} onclose={closeOverlay} />
{:else if activeOverlay === 'settings'}
  <SettingsOverlay {debugMode} onclose={closeOverlay} oncommand={handleCommand} />
{:else if activeOverlay === 'saves'}
  <SaveLoadOverlay
    saves={savesList}
    loading={savesLoading}
    statusMessage={savesStatus}
    statusError={savesStatusError}
    onclose={closeOverlay}
    onsave={(slot: string) => {
      savesStatus = null
      send({ type: 'save', slot })
    }}
    onload={(slot: string) => {
      savesStatus = null
      send({ type: 'load', slot })
    }}
  />
{:else if activeOverlay === 'kg'}
  <KnowledgeOverlay content={kgContent} onclose={closeOverlay} />
{:else if activeOverlay === 'satchel'}
  <SatchelOverlay
    items={currentRoom?.inventory ?? []}
    onclose={closeOverlay}
    onpick={handleEntityClick}
  />
{/if}

<style>
  /* persistent journal summon — a small inked stamp, not a desktop toolbar.
     (slice 3 will gate frame/affordance visibility to the live page.) */
  .journal-fab {
    position: fixed;
    left: 1rem;
    bottom: calc(var(--input-height) + 0.85rem);
    z-index: 20;
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    padding: 0.4rem 0.7rem;
    font-family: var(--font-ui);
    font-size: 0.72rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--game-accent-glow);
    background: var(--game-panel);
    border: 1px solid var(--game-line);
    border-radius: 3px;
    box-shadow: 0 6px 18px -10px #000;
    cursor: pointer;
    opacity: 0.85;
    transition: opacity 0.15s, border-color 0.15s, transform 0.12s;
  }
  .journal-fab:hover {
    opacity: 1;
    border-color: var(--game-accent);
    transform: translateY(-1px);
  }
  .journal-glyph {
    color: var(--game-accent);
    font-size: 0.85rem;
  }
  .journal-count {
    min-width: 1.1rem;
    padding: 0 0.25rem;
    text-align: center;
    color: var(--game-ink);
    background: var(--game-accent);
    border-radius: 999px;
    font-size: 0.66rem;
    font-weight: 700;
  }

  @media (max-width: 768px) {
    .journal-label {
      display: none;
    }
  }
</style>
