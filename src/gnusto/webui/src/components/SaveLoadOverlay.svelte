<script lang="ts">
  import OverlayPanel from './OverlayPanel.svelte'

  interface Props {
    saves: { slot: string; timestamp: string }[]
    loading: boolean
    statusMessage: string | null
    statusError: boolean
    onclose: () => void
    onsave: (slot: string) => void
    onload: (slot: string) => void
  }

  let { saves, loading, statusMessage, statusError, onclose, onsave, onload }: Props = $props()

  let newSlotName = $state('')

  function handleSave() {
    const slot = newSlotName.trim() || 'default'
    onsave(slot)
  }
</script>

<OverlayPanel title="Save / Load" {onclose}>
  {#if statusMessage}
    <div class="status" class:error={statusError}>{statusMessage}</div>
  {/if}

  <!-- Save -->
  <section class="sl-section">
    <h3>Save Game</h3>
    <form class="save-form" onsubmit={(e) => { e.preventDefault(); handleSave() }}>
      <input
        class="slot-input"
        type="text"
        bind:value={newSlotName}
        placeholder="default"
      />
      <button class="sl-btn save-btn" type="submit">Save</button>
    </form>
  </section>

  <!-- Saved games list -->
  <section class="sl-section">
    <h3>Saved Games</h3>
    {#if loading}
      <p class="empty">Loading...</p>
    {:else if saves.length === 0}
      <p class="empty">No saved games</p>
    {:else}
      <ul class="saves-list">
        {#each saves as save}
          <li class="save-item">
            <div class="save-info">
              <span class="save-slot">{save.slot}</span>
              <span class="save-time">{save.timestamp}</span>
            </div>
            <button class="sl-btn load-btn" onclick={() => onload(save.slot)}>Load</button>
          </li>
        {/each}
      </ul>
    {/if}
  </section>
</OverlayPanel>

<style>
  .status {
    font-family: var(--font-ui);
    font-size: 0.85rem;
    padding: 0.5rem 0.75rem;
    border-radius: 4px;
    margin-bottom: 1rem;
    background: rgba(26, 122, 138, 0.1);
    color: var(--accent-cyan);
  }

  .status.error {
    background: rgba(142, 58, 142, 0.1);
    color: var(--accent-magenta);
  }

  .sl-section {
    margin-bottom: 1.25rem;
  }

  .sl-section:last-child {
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

  .save-form {
    display: flex;
    gap: 0.5rem;
  }

  .slot-input {
    flex: 1;
    font-family: var(--font-mono);
    font-size: 0.85rem;
    padding: 0.4rem 0.6rem;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: var(--bg-primary);
    color: var(--text-primary);
    outline: none;
  }

  .slot-input:focus {
    border-color: var(--accent-cyan);
  }

  .sl-btn {
    font-family: var(--font-ui);
    font-size: 0.8rem;
    font-weight: 500;
    padding: 0.4rem 0.75rem;
    border: 1px solid var(--border);
    border-radius: 4px;
    cursor: pointer;
    transition: background 0.15s, border-color 0.15s;
    white-space: nowrap;
  }

  .save-btn {
    background: var(--accent-cyan);
    color: white;
    border-color: var(--accent-cyan);
  }

  .save-btn:hover {
    background: #15697a;
    border-color: #15697a;
  }

  .load-btn {
    background: none;
    color: var(--text-secondary);
  }

  .load-btn:hover {
    background: rgba(0, 0, 0, 0.05);
    border-color: var(--text-muted);
  }

  .saves-list {
    list-style: none;
    margin: 0;
    padding: 0;
  }

  .save-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.5rem 0;
    border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  }

  .save-item:last-child {
    border-bottom: none;
  }

  .save-info {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
  }

  .save-slot {
    font-family: var(--font-mono);
    font-size: 0.85rem;
    color: var(--text-primary);
    font-weight: 500;
  }

  .save-time {
    font-family: var(--font-ui);
    font-size: 0.7rem;
    color: var(--text-muted);
  }

  .empty {
    font-family: var(--font-ui);
    font-size: 0.85rem;
    color: var(--text-muted);
    font-style: italic;
    margin: 0;
  }
</style>
