<script lang="ts">
  import { onMount } from 'svelte'
  import type { RoomEnterBlock, ContentBlock, RenderableBlock, ServerMessage } from './lib/types'
  import { connect, onMessage, send } from './lib/websocket.svelte'
  import { updateEntities } from './lib/entities.svelte'

  import RoomHeader from './components/RoomHeader.svelte'
  import NarrativeStream from './components/NarrativeStream.svelte'
  import Sidebar from './components/Sidebar.svelte'
  import RightSidebar from './components/RightSidebar.svelte'
  import InputBar from './components/InputBar.svelte'
  import PeekTab from './components/PeekTab.svelte'

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

<RoomHeader room={currentRoom} />
<Sidebar side="left" />
<RightSidebar room={currentRoom} oncommand={handleCommand} open={rightSidebarOpen}
  onclose={() => rightSidebarOpen = false} />
<NarrativeStream {blocks} />
<InputBar enabled={inputEnabled} {gameEnded} oncommand={handleCommand} />
<PeekTab side="left" />
<PeekTab side="right" ontoggle={() => rightSidebarOpen = !rightSidebarOpen} />
