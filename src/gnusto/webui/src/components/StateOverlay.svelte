<script lang="ts">
  import { styleNarrative } from '../lib/markdown'
  import OverlayPanel from './OverlayPanel.svelte'

  interface Props {
    content: string | null
    onclose: () => void
  }

  let { content, onclose }: Props = $props()
</script>

<OverlayPanel title="Game State" {onclose}>
  {#if content}
    <div class="state-content">
      {@html styleNarrative(content)}
    </div>
  {:else}
    <p class="loading">Loading...</p>
  {/if}
</OverlayPanel>

<style>
  .state-content {
    font-family: var(--font-ui);
    font-size: 0.85rem;
    color: var(--text-secondary);
    line-height: 1.6;
  }

  .state-content :global(h2) {
    font-family: var(--font-ui);
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin: 1.25rem 0 0.5rem 0;
  }

  .state-content :global(h2:first-child) {
    margin-top: 0;
  }

  .state-content :global(p) {
    margin: 0.3rem 0;
  }

  .state-content :global(strong) {
    color: var(--text-primary);
    font-weight: 600;
  }

  .state-content :global(ul) {
    margin: 0.25rem 0;
    padding-left: 1.25rem;
  }

  .state-content :global(li) {
    margin-bottom: 0.15rem;
  }

  .state-content :global(code) {
    font-family: var(--font-mono);
    font-size: 0.8rem;
    background: rgba(0, 0, 0, 0.04);
    padding: 0.1rem 0.3rem;
    border-radius: 3px;
  }

  .loading {
    font-family: var(--font-ui);
    font-size: 0.85rem;
    color: var(--text-muted);
    font-style: italic;
    margin: 0;
  }
</style>
