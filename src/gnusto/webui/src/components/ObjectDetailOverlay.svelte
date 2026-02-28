<script lang="ts">
  import { behaviorLabel, behaviorHasEntityArg, behaviorHasValueArg, behaviorToCommand } from '../lib/commands'
  import OverlayPanel from './OverlayPanel.svelte'

  interface Props {
    entityId: string
    entityName: string
    entityImage: string | null
    behaviors: string[]
    onclose: () => void
    oncommand: (cmd: string) => void
    onfill: (text: string) => void
    ontarget: (behavior: string) => void
  }

  let { entityId, entityName, entityImage, behaviors, onclose, oncommand, onfill, ontarget }: Props = $props()

  function handleAction(behavior: string) {
    if (behaviorHasEntityArg(behavior)) {
      ontarget(behavior)
      onclose()
    } else if (behaviorHasValueArg(behavior)) {
      const cmd = behaviorToCommand(behavior, entityName)
      onfill(cmd + ' ')
      onclose()
    } else {
      const cmd = behaviorToCommand(behavior, entityName)
      oncommand(cmd)
      onclose()
    }
  }
</script>

<OverlayPanel title={entityName} {onclose} width="400px">
  <div class="detail-content">
    {#if entityImage}
      <div class="image-container">
        <img class="entity-image" src={entityImage} alt={entityName} />
      </div>
    {:else}
      <div class="image-container">
        <div class="entity-placeholder">{entityName.charAt(0).toUpperCase()}</div>
      </div>
    {/if}

    {#if behaviors.length > 0}
      <section class="actions-section">
        <h3>Actions</h3>
        <div class="action-grid">
          {#each behaviors as b}
            <button class="action-btn" onclick={() => handleAction(b)}>
              {behaviorLabel(b)}{#if behaviorHasEntityArg(b)}<span class="arg-hint"> +</span>{:else if behaviorHasValueArg(b)}<span class="arg-hint"> ...</span>{/if}
            </button>
          {/each}
        </div>
      </section>
    {:else}
      <p class="no-actions">No actions available</p>
    {/if}
  </div>
</OverlayPanel>

<style>
  .detail-content {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .image-container {
    display: flex;
    justify-content: center;
  }

  .entity-image {
    width: 200px;
    height: 200px;
    border-radius: 12px;
    object-fit: cover;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  }

  .entity-placeholder {
    width: 200px;
    height: 200px;
    border-radius: 12px;
    background: var(--border);
    color: var(--text-muted);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 4rem;
    font-weight: 600;
    font-family: var(--font-ui);
  }

  .actions-section {
    margin-top: 0.5rem;
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

  .action-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
  }

  .action-btn {
    font-family: var(--font-ui);
    font-size: 0.85rem;
    color: var(--text-secondary);
    background: none;
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 0.4rem 0.75rem;
    cursor: pointer;
    transition: background 0.15s, border-color 0.15s;
  }

  .action-btn:hover {
    background: rgba(0, 0, 0, 0.05);
    border-color: var(--text-muted);
    color: var(--text-primary);
  }

  .arg-hint {
    color: var(--text-muted);
    font-style: italic;
  }

  .no-actions {
    font-family: var(--font-ui);
    font-size: 0.85rem;
    color: var(--text-muted);
    font-style: italic;
    margin: 0;
    text-align: center;
  }
</style>
