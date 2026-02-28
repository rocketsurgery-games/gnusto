<script lang="ts">
  import type { RoomEnterBlock } from '../lib/types'
  import { resolveEntityImage } from '../lib/entities.svelte'
  import { behaviorLabel } from '../lib/commands'
  import OverlayPanel from './OverlayPanel.svelte'

  interface Props {
    room: RoomEnterBlock | null
    onclose: () => void
    onentityclick: (entityId: string, anchorEl: HTMLElement) => void
  }

  let { room, onclose, onentityclick }: Props = $props()

  function handleEntityClick(entityId: string, e: MouseEvent) {
    onentityclick(entityId, e.currentTarget as HTMLElement)
    onclose()
  }
</script>

<OverlayPanel title="Game State" {onclose}>
  {#if room}
    <!-- Location -->
    <section class="state-section">
      <h3>Location</h3>
      <div class="room-name">{room.name}</div>
      <div class="room-desc">{room.description}</div>
    </section>

    <!-- Exits -->
    <section class="state-section">
      <h3>Exits</h3>
      {#if room.exits.length > 0}
        <ul class="state-list">
          {#each room.exits as exit}
            <li class="exit-item">
              <span class="exit-dir">{exit.direction}</span>
              <span class="exit-dest">{exit.destination}</span>
            </li>
          {/each}
        </ul>
      {:else}
        <p class="empty">No exits</p>
      {/if}
    </section>

    <!-- Here -->
    <section class="state-section">
      <h3>Here</h3>
      {#if room.objects.length > 0}
        <ul class="state-list">
          {#each room.objects as obj}
            {@const img = resolveEntityImage(obj.id)}
            <li>
              <button class="entity-row" onclick={(e: MouseEvent) => handleEntityClick(obj.id, e)}>
                {#if img}
                  <img class="entity-thumb" src={img} alt={obj.name} />
                {:else}
                  <span class="entity-initial">{obj.name.charAt(0).toUpperCase()}</span>
                {/if}
                <span class="entity-info">
                  <span class="entity-name">{obj.name}</span>
                  {#if obj.behaviors.length > 0}
                    <span class="entity-behaviors">{obj.behaviors.map(behaviorLabel).join(', ')}</span>
                  {/if}
                </span>
              </button>
            </li>
          {/each}
        </ul>
      {:else}
        <p class="empty">Nothing here</p>
      {/if}
    </section>

    <!-- Inventory -->
    <section class="state-section">
      <h3>Inventory</h3>
      {#if room.inventory.length > 0}
        <ul class="state-list">
          {#each room.inventory as item}
            {@const img = resolveEntityImage(item.id)}
            <li>
              <button class="entity-row" onclick={(e: MouseEvent) => handleEntityClick(item.id, e)}>
                {#if img}
                  <img class="entity-thumb" src={img} alt={item.name} />
                {:else}
                  <span class="entity-initial">{item.name.charAt(0).toUpperCase()}</span>
                {/if}
                <span class="entity-info">
                  <span class="entity-name">{item.name}</span>
                  {#if item.behaviors.length > 0}
                    <span class="entity-behaviors">{item.behaviors.map(behaviorLabel).join(', ')}</span>
                  {/if}
                </span>
              </button>
            </li>
          {/each}
        </ul>
      {:else}
        <p class="empty">Empty-handed</p>
      {/if}
    </section>
  {:else}
    <p class="empty">No game state available.</p>
  {/if}
</OverlayPanel>

<style>
  .state-section {
    margin-bottom: 1.25rem;
  }

  .state-section:last-child {
    margin-bottom: 0;
  }

  h3 {
    font-family: var(--font-ui);
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.5rem;
  }

  .room-name {
    font-family: var(--font-body);
    font-size: 1rem;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 0.35rem;
  }

  .room-desc {
    font-family: var(--font-body);
    font-size: 0.9rem;
    color: var(--text-secondary);
    line-height: 1.5;
  }

  .state-list {
    list-style: none;
    margin: 0;
    padding: 0;
  }

  .state-list li {
    margin-bottom: 0.25rem;
  }

  .exit-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.3rem 0;
    border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  }

  .exit-dir {
    font-family: var(--font-ui);
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    color: var(--accent-cyan);
    min-width: 2rem;
  }

  .exit-dest {
    font-family: var(--font-ui);
    font-size: 0.85rem;
    color: var(--text-secondary);
  }

  .entity-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    width: 100%;
    background: none;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 0.3rem 0.4rem;
    cursor: pointer;
    font-family: var(--font-ui);
    text-align: left;
    transition: border-color 0.15s, background 0.15s;
  }

  .entity-row:hover {
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

  .entity-info {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  .entity-name {
    font-size: 0.85rem;
    color: var(--text-secondary);
  }

  .entity-behaviors {
    font-size: 0.7rem;
    color: var(--text-muted);
    font-style: italic;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .empty {
    font-family: var(--font-ui);
    font-size: 0.85rem;
    color: var(--text-muted);
    font-style: italic;
    margin: 0;
  }
</style>
