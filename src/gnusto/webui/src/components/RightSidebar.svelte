<script lang="ts">
  import { slide } from 'svelte/transition'
  import type { RoomEnterBlock } from '../lib/types'
  import { resolveEntityImage } from '../lib/entities.svelte'

  interface Props {
    room: RoomEnterBlock | null
    // Live ground-truth frame is shown ONLY on the live page; on history pages
    // it hides so current state isn't mixed with frozen content (gnusto-4ac5.2).
    visible?: boolean
    // Clicks prefill the input (no action menus): objects -> their name,
    // exits -> "go <dir>". The player phrases intent; the LLM interprets.
    onprefill: (text: string) => void
    open?: boolean
    onclose?: () => void
  }

  let { room, visible = true, onprefill, open = false, onclose }: Props = $props()

  const dirArrows: Record<string, string> = {
    north: '↑', south: '↓', east: '→', west: '←',
    up: '⬆', down: '⬇',
    northeast: '↗', northwest: '↖', southeast: '↘', southwest: '↙',
  }
  // Spatial reading order so the ways out feel like a compass, not a list.
  const dirOrder: Record<string, number> = {
    north: 0, northeast: 1, east: 2, southeast: 3,
    south: 4, southwest: 5, west: 6, northwest: 7,
    up: 8, down: 9, in: 10, out: 11,
  }
  let exits = $derived(
    [...(room?.exits ?? [])].sort(
      (a, b) => (dirOrder[a.direction.toLowerCase()] ?? 99) - (dirOrder[b.direction.toLowerCase()] ?? 99),
    ),
  )

  function pickExit(direction: string) {
    onprefill(`go ${direction}`)
    onclose?.()
  }
  function pickObject(name: string) {
    onprefill(name)
    onclose?.()
  }
</script>

{#if visible && room}
  <aside class="frame-rail" class:mobile-open={open}>
    {#if open}
      <button class="close-btn" onclick={onclose}>&times;</button>
    {/if}

    <!-- LOCATOR: a persistent "you are here" stamp (we lacked a room-name
         affordance outside the establishing panel). -->
    <div class="locator">{room.name}</div>

    <!-- EXITS — spatial ways out; click prefills "go <dir>" -->
    <section class="block">
      <h3 class="block-header">Ways out</h3>
      {#if exits.length > 0}
        <ul class="exit-list">
          {#each exits as exit (exit.direction)}
            <li transition:slide={{ duration: 150 }}>
              <button class="exit" onclick={() => pickExit(exit.direction)}>
                <span class="arrow">{dirArrows[exit.direction.toLowerCase()] || '•'}</span>
                <span class="dir">{exit.direction}</span>
                <span class="dest">{exit.destination}</span>
              </button>
            </li>
          {/each}
        </ul>
      {:else}
        <p class="empty">No obvious way out</p>
      {/if}
    </section>

    <!-- HERE — visible objects as small specimen cards; click prefills the name -->
    <section class="block">
      <h3 class="block-header">Here</h3>
      {#if room.objects.length > 0}
        <ul class="prop-list">
          {#each room.objects as obj (obj.id)}
            {@const img = resolveEntityImage(obj.id)}
            <li transition:slide={{ duration: 150 }}>
              <button class="prop" onclick={() => pickObject(obj.name || obj.id)}>
                {#if img}
                  <img class="prop-thumb" src={img} alt={obj.name} />
                {:else}
                  <span class="prop-thumb prop-thumb--noart">{(obj.name || '?').charAt(0).toUpperCase()}</span>
                {/if}
                <span class="prop-name">{obj.name || obj.id}</span>
              </button>
            </li>
          {/each}
        </ul>
      {:else}
        <p class="empty">Nothing of note</p>
      {/if}
    </section>
  </aside>
{/if}

<style>
  .frame-rail {
    position: fixed;
    top: 0;
    bottom: var(--input-height);
    right: 0;
    width: var(--sidebar-width);
    padding: 1rem 0.75rem;
    color: var(--text-muted);
    font-family: var(--font-ui);
    overflow-y: auto;
    z-index: 5;
  }

  /* location stamp — inked, embedded identity (echoes the establishing locandum) */
  .locator {
    font-size: 0.8rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--game-accent-glow);
    border-left: 3px solid var(--game-accent);
    padding: 4px 0 4px 9px;
    margin-bottom: 1.25rem;
    text-shadow: 0 0 8px rgba(143, 224, 106, 0.4);
  }

  .block {
    margin-bottom: 1.25rem;
  }
  .block-header {
    font-size: 0.65rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-muted);
    margin: 0 0 0.5rem 0;
  }

  .exit-list,
  .prop-list {
    list-style: none;
    margin: 0;
    padding: 0;
  }
  .exit-list li,
  .prop-list li {
    margin-bottom: 0.3rem;
  }

  .exit,
  .prop {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    width: 100%;
    background: none;
    border: 1px solid transparent;
    border-radius: 3px;
    padding: 0.25rem 0.4rem;
    cursor: pointer;
    font-family: var(--font-ui);
    text-align: left;
    transition: border-color 0.15s, background 0.15s;
  }
  .exit:hover,
  .prop:hover {
    border-color: var(--game-line);
    background: rgba(255, 255, 255, 0.04);
  }

  .arrow {
    font-size: 0.9rem;
    color: var(--accent-cyan);
    width: 1rem;
    text-align: center;
    flex-shrink: 0;
  }
  .dir {
    font-size: 0.68rem;
    font-weight: 600;
    text-transform: uppercase;
    color: var(--accent-cyan);
    min-width: 1.8rem;
  }
  .dest {
    color: var(--text-secondary);
    font-size: 0.78rem;
  }

  /* objects as small inked specimen cards (same visual language as the satchel) */
  .prop-thumb {
    width: 34px;
    height: 34px;
    object-fit: cover;
    border-radius: 2px;
    border: 1px solid #000;
    background: #f4eede;
    flex-shrink: 0;
  }
  .prop-thumb--noart {
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--game-panel-2);
    border: 1px dashed var(--game-line);
    color: var(--text-secondary);
    font-size: 0.8rem;
    font-weight: 600;
  }
  .prop-name {
    color: var(--text-secondary);
    font-size: 0.78rem;
  }

  .empty {
    color: var(--text-muted);
    font-style: italic;
    font-size: 0.78rem;
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
    line-height: 1;
  }
  .close-btn:hover {
    color: var(--text-primary);
  }

  @media (max-width: 768px) {
    .frame-rail {
      transform: translateX(100%);
      transition: transform 0.25s ease;
      background: var(--bg-primary);
      box-shadow: -2px 0 8px rgba(0, 0, 0, 0.15);
      z-index: 30;
    }
    .frame-rail.mobile-open {
      transform: translateX(0);
    }
  }
</style>
