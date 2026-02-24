<script lang="ts">
  import type { RoomEnterBlock } from '../lib/types'
  import { styleText } from '../lib/markdown'

  interface Props {
    room: RoomEnterBlock | null
  }

  let { room }: Props = $props()
</script>

<header class="header">
  {#if room}
    <div class="room-header">
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
    margin-left: var(--sidebar-width);
    margin-right: var(--sidebar-width);
    padding: 1rem 2rem;
    background: var(--bg-primary);
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
