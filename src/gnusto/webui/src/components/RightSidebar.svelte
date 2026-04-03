<script lang="ts">
  import { slide } from 'svelte/transition'
  import type { RoomEnterBlock } from '../lib/types'
  import { resolveEntityImage } from '../lib/entities.svelte'

  interface Props {
    room: RoomEnterBlock | null
    oncommand: (cmd: string) => void
    onentityclick: (entityId: string, anchorEl: HTMLElement) => void
    open?: boolean
    onclose?: () => void
  }

  let { room, oncommand, onentityclick, open = false, onclose }: Props = $props()

  const dirArrows: Record<string, string> = {
    north: '↑', south: '↓', east: '→', west: '←',
    up: '⬆', down: '⬇',
    northeast: '↗', northwest: '↖', southeast: '↘', southwest: '↙',
  }

  function handleExitClick(direction: string) {
    oncommand(`go ${direction}`)
    onclose?.()
  }
</script>

<aside class="sidebar sidebar-right" class:mobile-open={open}>
  {#if open}
    <button class="close-btn" onclick={onclose}>&times;</button>
  {/if}
  {#if room}
    <!-- Exits -->
    <section class="panel">
      <h3 class="panel-header">Exits</h3>
      {#if room.exits.length > 0}
        <ul class="entity-list">
          {#each room.exits as exit (exit.direction)}
            <li transition:slide={{ duration: 150 }}>
              <button class="exit-btn" onclick={() => handleExitClick(exit.direction)}>
                <span class="exit-arrow">{dirArrows[exit.direction.toLowerCase()] || '•'}</span>
                <span class="exit-dir">{exit.direction}</span>
                <span class="exit-dest">{exit.destination}</span>
              </button>
            </li>
          {/each}
        </ul>
      {:else}
        <p class="empty">No exits</p>
      {/if}
    </section>

    <!-- Visible objects -->
    <section class="panel">
      <h3 class="panel-header">Here</h3>
      {#if room.objects.length > 0}
        <ul class="entity-list">
          {#each room.objects as obj (obj.id)}
            {@const img = resolveEntityImage(obj.id)}
            <li transition:slide={{ duration: 150 }}>
              <button class="entity-btn" onclick={(e: MouseEvent) => onentityclick(obj.id, e.currentTarget as HTMLElement)}>
                {#if img}
                  <img class="entity-thumb" src={img} alt={obj.name} />
                {:else}
                  <span class="entity-initial">{(obj.name || '?').charAt(0).toUpperCase()}</span>
                {/if}
                <span class="entity-name">{obj.name || obj.id}</span>
              </button>
            </li>
          {/each}
        </ul>
      {:else}
        <p class="empty">Nothing here</p>
      {/if}
    </section>

    <!-- Inventory -->
    <section class="panel">
      <h3 class="panel-header">Inventory</h3>
      {#if room.inventory.length > 0}
        <ul class="entity-list">
          {#each room.inventory as item (item.id)}
            {@const img = resolveEntityImage(item.id)}
            <li transition:slide={{ duration: 150 }}>
              <button class="entity-btn" onclick={(e: MouseEvent) => onentityclick(item.id, e.currentTarget as HTMLElement)}>
                {#if img}
                  <img class="entity-thumb" src={img} alt={item.name} />
                {:else}
                  <span class="entity-initial">{(item.name || '?').charAt(0).toUpperCase()}</span>
                {/if}
                <span class="entity-name">{item.name || item.id}</span>
              </button>
            </li>
          {/each}
        </ul>
      {:else}
        <p class="empty">Empty-handed</p>
      {/if}
    </section>
  {/if}
</aside>

<style>
  .sidebar {
    position: fixed;
    top: 0;
    bottom: var(--input-height);
    width: var(--sidebar-width);
    padding: 1rem 0.75rem;
    color: var(--text-muted);
    font-size: 0.85rem;
    font-family: var(--font-ui);
    overflow-y: auto;
    z-index: 5;
  }

  .sidebar-right {
    right: 0;
  }

  .panel {
    margin-bottom: 1.25rem;
  }

  .panel-header {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-muted);
    margin: 0 0 0.5rem 0;
    font-family: var(--font-ui);
  }

  .entity-list {
    list-style: none;
    margin: 0;
    padding: 0;
  }

  .entity-list li {
    margin-bottom: 0.25rem;
  }

  .entity-btn {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    width: 100%;
    background: none;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 0.25rem 0.4rem;
    cursor: pointer;
    font-family: var(--font-ui);
    text-align: left;
    transition: border-color 0.15s, background 0.15s;
  }

  .entity-btn:hover {
    border-color: var(--border);
    background: rgba(0, 0, 0, 0.03);
  }

  .entity-thumb {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    object-fit: cover;
    flex-shrink: 0;
  }

  .entity-initial {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: var(--border);
    color: var(--text-secondary);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.75rem;
    font-weight: 600;
    flex-shrink: 0;
  }

  .entity-name {
    color: var(--text-secondary);
    font-size: 0.8rem;
  }

  .exit-btn {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    width: 100%;
    background: none;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 0.25rem 0.4rem;
    cursor: pointer;
    font-family: var(--font-ui);
    text-align: left;
    transition: border-color 0.15s, background 0.15s;
  }

  .exit-btn:hover {
    border-color: var(--border);
    background: rgba(0, 0, 0, 0.03);
  }

  .exit-arrow {
    font-size: 0.9rem;
    color: var(--accent-cyan);
    flex-shrink: 0;
    width: 1rem;
    text-align: center;
  }

  .exit-dir {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    color: var(--accent-cyan);
    min-width: 1.8rem;
  }

  .exit-dest {
    color: var(--text-secondary);
    font-size: 0.8rem;
  }

  .empty {
    color: var(--text-muted);
    font-style: italic;
    font-size: 0.8rem;
    margin: 0;
  }

  .close-btn {
    position: absolute;
    top: 0.5rem;
    right: 0.5rem;
    background: none;
    border: none;
    font-size: 1.2rem;
    color: var(--text-muted);
    cursor: pointer;
    padding: 0.25rem;
    line-height: 1;
  }

  .close-btn:hover {
    color: var(--text-primary);
  }

  @media (max-width: 768px) {
    .sidebar {
      transform: translateX(100%);
      transition: transform 0.25s ease;
      width: 220px;
      background: var(--bg-primary);
      box-shadow: -2px 0 8px rgba(0, 0, 0, 0.15);
      z-index: 30;
    }

    .sidebar.mobile-open {
      transform: translateX(0);
    }
  }
</style>
