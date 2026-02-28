<script lang="ts">
  import { onMount } from 'svelte'
  import type { RoomEnterBlock, ContentBlock, RenderableBlock, ServerMessage } from './lib/types'
  import { connect, onMessage, send } from './lib/websocket.svelte'
  import { updateEntities, updateBehaviors, resolveEntityName, resolveEntityImage, resolveEntityBehaviors } from './lib/entities.svelte'
  import { behaviorLabel, behaviorToTargetedCommand } from './lib/commands'

  import RoomHeader from './components/RoomHeader.svelte'
  import NarrativeStream from './components/NarrativeStream.svelte'
  import Sidebar from './components/Sidebar.svelte'
  import RightSidebar from './components/RightSidebar.svelte'
  import InputBar from './components/InputBar.svelte'
  import PeekTab from './components/PeekTab.svelte'
  import EntityPopover from './components/EntityPopover.svelte'
  import HelpOverlay from './components/HelpOverlay.svelte'
  import StateOverlay from './components/StateOverlay.svelte'
  import SettingsOverlay from './components/SettingsOverlay.svelte'
  import ObjectDetailOverlay from './components/ObjectDetailOverlay.svelte'
  import SaveLoadOverlay from './components/SaveLoadOverlay.svelte'

  // Current room header data
  let currentRoom = $state<RoomEnterBlock | null>(null)

  // Narrative blocks for the current room
  let blocks = $state<RenderableBlock[]>([])

  // Archived blocks from previous rooms (kept for future history feature d4ui.5)
  let _archive: RenderableBlock[][] = []

  // Image alternation counter
  let imageBlockIndex = 0

  // Input enabled state
  let inputEnabled = $state(false)

  // Game ended state
  let gameEnded = $state(false)

  // Mobile sidebar state
  let rightSidebarOpen = $state(false)

  // Prefill text for input bar (from popover "fill" actions)
  let inputPrefill = $state<string | null>(null)

  // Debug mode (tracked from server responses)
  let debugMode = $state(false)

  // Object detail overlay state
  let detailEntity = $state<{
    id: string
    name: string
    image: string | null
    behaviors: string[]
  } | null>(null)

  // State overlay content (from backend)
  let stateContent = $state<string | null>(null)

  // Save/load overlay state
  let savesList = $state<{ slot: string; timestamp: string }[]>([])
  let savesLoading = $state(true)
  let savesStatus = $state<string | null>(null)
  let savesStatusError = $state(false)

  // Active overlay panel (null = none)
  let activeOverlay = $state<string | null>(null)

  function closeOverlay() {
    activeOverlay = null
    detailEntity = null
  }

  function openDetailOverlay(entityId: string) {
    detailEntity = {
      id: entityId,
      name: resolveEntityName(entityId),
      image: resolveEntityImage(entityId),
      behaviors: resolveEntityBehaviors(entityId),
    }
    activeOverlay = 'object-detail'
  }

  // Entity popover state
  let popover = $state<{
    entityId: string
    entityName: string
    behaviors: string[]
    anchorRect: DOMRect
  } | null>(null)

  // Targeting mode state
  let targeting = $state<{
    sourceEntityId: string
    sourceEntityName: string
    behavior: string
    prompt: string
  } | null>(null)

  // Toggle body class for CSS cascade
  $effect(() => {
    document.body.classList.toggle('targeting', !!targeting)
  })

  function openPopover(entityId: string, anchorEl: HTMLElement) {
    const name = resolveEntityName(entityId)
    const behaviors = resolveEntityBehaviors(entityId)
    popover = {
      entityId,
      entityName: name,
      behaviors,
      anchorRect: anchorEl.getBoundingClientRect(),
    }
  }

  function handleEntityClick(entityId: string, anchorEl: HTMLElement) {
    if (targeting) {
      completeTargeting(entityId)
    } else {
      openPopover(entityId, anchorEl)
    }
  }

  function enterTargetingMode(sourceEntityId: string, sourceEntityName: string, behavior: string) {
    const label = behaviorLabel(behavior).toLowerCase()
    targeting = {
      sourceEntityId,
      sourceEntityName,
      behavior,
      prompt: `${label} the ${sourceEntityName}... click a target`,
    }
  }

  function completeTargeting(targetEntityId: string) {
    if (!targeting) return
    const targetName = resolveEntityName(targetEntityId)
    const cmd = behaviorToTargetedCommand(
      targeting.behavior,
      targeting.sourceEntityName,
      targetName,
    )
    targeting = null
    handleCommand(cmd)
  }

  function cancelTargeting() {
    targeting = null
  }

  function handleMessage(message: ServerMessage) {
    if (message.type === 'scene_context') {
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
      updateBehaviors([...message.objects, ...message.inventory])
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

  function addBlock(block: ContentBlock) {
    // RoomEnter → header, not stream
    if (block.type === 'room_enter') {
      // Archive current blocks and start fresh
      if (blocks.length > 0) {
        _archive.push([...blocks])
      }
      blocks = []
      imageBlockIndex = 0
      currentRoom = block
      updateBehaviors([...block.objects, ...block.inventory])
      targeting = null
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

    inputEnabled = false
    // Show command locally
    blocks = [...blocks, { type: 'command', text: command }]
    send({ type: 'command', text: command })
  }

  onMount(() => {
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
  if (e.key === 'Escape') {
    if (activeOverlay) { closeOverlay(); e.preventDefault() }
    else if (targeting) { cancelTargeting(); e.preventDefault() }
  }
}} />

<RoomHeader room={currentRoom} onentityclick={handleEntityClick} />
<Sidebar side="left" />
<RightSidebar room={currentRoom} oncommand={handleCommand} onentityclick={handleEntityClick}
  open={rightSidebarOpen} onclose={() => rightSidebarOpen = false} />
<NarrativeStream {blocks} onentityclick={handleEntityClick} />
<InputBar enabled={inputEnabled} {gameEnded} prefill={inputPrefill}
  targetingPrompt={targeting?.prompt}
  oncommand={handleCommand} onprefillconsumed={() => inputPrefill = null}
  oncanceltargeting={cancelTargeting} />
<PeekTab side="left" />
<PeekTab side="right" ontoggle={() => rightSidebarOpen = !rightSidebarOpen} />

{#if popover}
  <EntityPopover
    entityName={popover.entityName}
    behaviors={popover.behaviors}
    anchorRect={popover.anchorRect}
    oncommand={handleCommand}
    onfill={(text: string) => inputPrefill = text}
    ontarget={(behavior: string) => {
      if (popover) enterTargetingMode(popover.entityId, popover.entityName, behavior)
    }}
    ondetail={() => { if (popover) openDetailOverlay(popover.entityId) }}
    onclose={() => popover = null}
  />
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
{:else if activeOverlay === 'object-detail' && detailEntity}
  <ObjectDetailOverlay
    entityId={detailEntity.id}
    entityName={detailEntity.name}
    entityImage={detailEntity.image}
    behaviors={detailEntity.behaviors}
    onclose={closeOverlay}
    oncommand={handleCommand}
    onfill={(text: string) => inputPrefill = text}
    ontarget={(behavior: string) => {
      if (detailEntity) enterTargetingMode(detailEntity.id, detailEntity.name, behavior)
    }}
  />
{/if}
