<script lang="ts">
  import { onMount } from 'svelte'
  import type { RoomEnterBlock, ContentBlock, RenderableBlock, ServerMessage } from './lib/types'
  import { connect, onMessage, send } from './lib/websocket.svelte'
  import { updateEntities, updateBehaviors, resolveEntityName, resolveEntityBehaviors } from './lib/entities.svelte'
  import { behaviorLabel, behaviorToTargetedCommand } from './lib/commands'

  import RoomHeader from './components/RoomHeader.svelte'
  import NarrativeStream from './components/NarrativeStream.svelte'
  import Sidebar from './components/Sidebar.svelte'
  import RightSidebar from './components/RightSidebar.svelte'
  import InputBar from './components/InputBar.svelte'
  import PeekTab from './components/PeekTab.svelte'
  import EntityPopover from './components/EntityPopover.svelte'

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

    // Stamp image side for focus/reveal blocks
    const renderable: RenderableBlock = { ...block }
    if (block.type === 'focus' || block.type === 'reveal') {
      renderable._side = (imageBlockIndex % 2 === 1) ? 'image-right' : 'image-left'
      imageBlockIndex++
    }

    blocks = [...blocks, renderable]
  }

  function handleCommand(command: string) {
    inputEnabled = false
    // Show command locally
    blocks = [...blocks, { type: 'command', text: command }]
    send({ type: 'command', text: command })
  }

  onMount(() => {
    onMessage(handleMessage)
    connect()
  })
</script>

<svelte:window onkeydown={(e) => { if (e.key === 'Escape' && targeting) { cancelTargeting(); e.preventDefault() } }} />

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
    onclose={() => popover = null}
  />
{/if}
