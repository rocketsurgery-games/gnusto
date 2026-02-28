<script lang="ts">
  import { onMount } from 'svelte'
  import { behaviorLabel, behaviorToCommand, behaviorHasEntityArg, behaviorHasValueArg } from '../lib/commands'

  interface Props {
    entityName: string
    behaviors: string[]
    anchorRect: DOMRect
    oncommand: (cmd: string) => void
    onfill: (text: string) => void
    ontarget: (behavior: string) => void
    ondetail: () => void
    onclose: () => void
  }

  let { entityName, behaviors, anchorRect, oncommand, onfill, ontarget, ondetail, onclose }: Props = $props()

  let popoverEl: HTMLDivElement | undefined = $state()

  // Position: below anchor, flipped above if near viewport bottom
  let style = $derived.by(() => {
    const top = anchorRect.bottom + 4
    const left = anchorRect.left
    const spaceBelow = window.innerHeight - anchorRect.bottom
    if (spaceBelow < 200) {
      return `bottom: ${window.innerHeight - anchorRect.top + 4}px; left: ${left}px;`
    }
    return `top: ${top}px; left: ${left}px;`
  })

  function handleAction(behavior: string) {
    if (behaviorHasEntityArg(behavior)) {
      // Single entity arg → enter targeting mode
      ontarget(behavior)
      onclose()
    } else if (behaviorHasValueArg(behavior)) {
      // Value arg → fill input for user to type
      const cmd = behaviorToCommand(behavior, entityName)
      onfill(cmd + ' ')
      onclose()
    } else {
      // No args → execute immediately
      const cmd = behaviorToCommand(behavior, entityName)
      oncommand(cmd)
      onclose()
    }
  }

  onMount(() => {
    // Delayed click-outside listener (one tick to avoid catching the opening click)
    const timer = setTimeout(() => {
      window.addEventListener('pointerdown', onClickOutside, true)
    }, 0)
    return () => {
      clearTimeout(timer)
      window.removeEventListener('pointerdown', onClickOutside, true)
    }
  })

  function onClickOutside(e: PointerEvent) {
    if (popoverEl && !popoverEl.contains(e.target as Node)) {
      onclose()
    }
  }
</script>

<div class="popover" bind:this={popoverEl} {style}>
  <div class="popover-header">{entityName}</div>
  {#if behaviors.length > 0}
    <div class="popover-actions">
      {#each behaviors as b}
        <button class="action-btn" onclick={() => handleAction(b)}>
          {behaviorLabel(b)}{#if behaviorHasEntityArg(b)}<span class="arg-hint"> +</span>{:else if behaviorHasValueArg(b)}<span class="arg-hint"> ...</span>{/if}
        </button>
      {/each}
    </div>
  {:else}
    <div class="popover-empty">No actions available</div>
  {/if}
  <div class="popover-footer">
    <button class="detail-btn" onclick={() => { ondetail(); onclose() }}>Details</button>
  </div>
</div>

<style>
  .popover {
    position: fixed;
    z-index: 50;
    min-width: 140px;
    max-width: 220px;
    background: var(--bg-primary);
    border: 1px solid var(--border);
    border-radius: 6px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    font-family: var(--font-ui);
    padding: 0.4rem 0;
  }

  .popover-header {
    padding: 0.3rem 0.75rem;
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.03em;
    border-bottom: 1px solid var(--border);
    margin-bottom: 0.2rem;
  }

  .popover-actions {
    display: flex;
    flex-direction: column;
  }

  .action-btn {
    display: block;
    width: 100%;
    background: none;
    border: none;
    padding: 0.35rem 0.75rem;
    text-align: left;
    font-family: var(--font-ui);
    font-size: 0.85rem;
    color: var(--text-secondary);
    cursor: pointer;
  }

  .action-btn:hover {
    background: rgba(0, 0, 0, 0.05);
    color: var(--text-primary);
  }

  .arg-hint {
    color: var(--text-muted);
    font-style: italic;
  }

  .popover-empty {
    padding: 0.35rem 0.75rem;
    font-size: 0.8rem;
    color: var(--text-muted);
    font-style: italic;
  }

  .popover-footer {
    border-top: 1px solid var(--border);
    margin-top: 0.2rem;
    padding-top: 0.2rem;
  }

  .detail-btn {
    display: block;
    width: 100%;
    background: none;
    border: none;
    padding: 0.35rem 0.75rem;
    text-align: left;
    font-family: var(--font-ui);
    font-size: 0.8rem;
    color: var(--text-muted);
    cursor: pointer;
  }

  .detail-btn:hover {
    background: rgba(0, 0, 0, 0.05);
    color: var(--text-primary);
  }
</style>
