<script lang="ts">
  import type { RoomEnterBlock } from '../lib/types'
  import { styleText } from '../lib/markdown'

  interface Props {
    room: RoomEnterBlock | null
    onentityclick?: (entityId: string, anchorEl: HTMLElement) => void
  }

  let { room, onentityclick }: Props = $props()

  function handleClick(e: MouseEvent) {
    const target = (e.target as HTMLElement).closest('.ref[data-entity]') as HTMLElement | null
    if (target && onentityclick) {
      onentityclick(target.dataset.entity!, target)
    }
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter' || e.key === ' ') {
      const target = (e.target as HTMLElement).closest('.ref[data-entity]') as HTMLElement | null
      if (target && onentityclick) {
        e.preventDefault()
        onentityclick(target.dataset.entity!, target)
      }
    }
  }
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<header class="header" onclick={handleClick} onkeydown={handleKeydown}>
  {#if room}
    <div class="room-header">
      {#if room.preamble}
        <p class="preamble">{room.preamble}</p>
      {/if}
      {#if room.image}
        <img class="room-image" src={room.image} alt={room.name} />
      {/if}
      <h2>{room.name}</h2>
      <div class="room-desc">{@html styleText(room.description)}</div>
    </div>
  {:else}
    <h2>Gnusto</h2>
  {/if}
</header>

<style>
  .header {
    position: sticky;
    top: 0;
    z-index: 10;
    margin-right: var(--sidebar-width);
    padding: 1rem 2rem;
    background: var(--bg-primary);
  }

  .preamble {
    font-style: italic;
    color: var(--text-muted);
    font-size: 0.9rem;
    margin-bottom: 0.5rem;
  }

  h2 {
    color: var(--accent-cyan);
    font-size: 1.3rem;
    font-weight: normal;
    font-family: var(--font-ui);
    margin: 0 0 0.25rem 0;
  }

  .room-image {
    float: right;
    max-width: 280px;
    max-height: 280px;
    margin: -0.5rem 0 0.5rem 1rem;
  }

  .room-desc {
    color: var(--text-secondary);
    font-size: 0.95rem;
  }
</style>
