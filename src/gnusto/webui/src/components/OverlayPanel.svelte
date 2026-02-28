<script lang="ts">
  import { onMount } from 'svelte'

  interface Props {
    title: string
    onclose: () => void
    width?: string
    children: any
  }

  let { title, onclose, width = '480px', children }: Props = $props()

  let panelEl: HTMLDivElement | undefined = $state()

  onMount(() => {
    // Focus the panel for keyboard accessibility
    panelEl?.focus()
  })

  function handleBackdropClick(e: MouseEvent) {
    if (e.target === e.currentTarget) {
      onclose()
    }
  }
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="overlay-backdrop" onclick={handleBackdropClick} onkeydown={() => {}}>
  <div
    class="overlay-panel"
    bind:this={panelEl}
    style:width={width}
    tabindex="-1"
    role="dialog"
    aria-label={title}
  >
    <header class="overlay-header">
      <h2>{title}</h2>
      <button class="close-btn" onclick={onclose} aria-label="Close">&times;</button>
    </header>
    <div class="overlay-body">
      {@render children()}
    </div>
  </div>
</div>

<style>
  .overlay-backdrop {
    position: fixed;
    inset: 0;
    z-index: 60;
    background: rgba(0, 0, 0, 0.3);
    display: flex;
    justify-content: flex-end;
    animation: backdrop-fade 0.2s ease;
  }

  @keyframes backdrop-fade {
    from { opacity: 0; }
    to   { opacity: 1; }
  }

  .overlay-panel {
    height: 100%;
    max-width: 90vw;
    background: var(--bg-primary);
    box-shadow: -4px 0 20px rgba(0, 0, 0, 0.15);
    display: flex;
    flex-direction: column;
    outline: none;
    animation: panel-slide 0.25s ease;
  }

  @keyframes panel-slide {
    from { transform: translateX(100%); }
    to   { transform: translateX(0); }
  }

  .overlay-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1rem 1.25rem;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
  }

  .overlay-header h2 {
    font-family: var(--font-ui);
    font-size: 1rem;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0;
  }

  .close-btn {
    background: none;
    border: none;
    font-size: 1.5rem;
    line-height: 1;
    color: var(--text-muted);
    cursor: pointer;
    padding: 0 0.25rem;
  }

  .close-btn:hover {
    color: var(--text-primary);
  }

  .overlay-body {
    flex: 1;
    overflow-y: auto;
    padding: 1.25rem;
  }
</style>
