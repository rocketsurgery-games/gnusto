<script lang="ts">
  import { marked } from 'marked'
  import type { SystemMessageBlock } from '../../lib/types'

  interface Props {
    block: SystemMessageBlock
  }

  let { block }: Props = $props()

  let colorStyle = $derived(
    block.level === 'error' ? 'color: var(--accent-magenta)' :
    block.level === 'warning' ? 'color: var(--accent-yellow)' : ''
  )
</script>

<div class="block-system" style={colorStyle}>
  {@html marked.parse(block.text) as string}
</div>

<style>
  .block-system {
    color: var(--text-muted);
    font-size: 0.85rem;
    font-family: var(--font-ui);
  }

  .block-system :global(h1),
  .block-system :global(h2),
  .block-system :global(h3) {
    color: var(--accent-cyan);
    font-weight: normal;
    margin: 1rem 0 0.5rem 0;
  }

  .block-system :global(h1) { font-size: 1.1rem; }
  .block-system :global(h2) { font-size: 1rem; }
  .block-system :global(h3) { font-size: 0.9rem; }

  .block-system :global(p) {
    margin: 0.5rem 0;
  }

  .block-system :global(code) {
    background: #f0f0f0;
    padding: 0.1rem 0.3rem;
    border-radius: 3px;
    font-family: var(--font-mono);
    color: var(--accent-green);
  }

  .block-system :global(pre) {
    background: #f5f5f5;
    padding: 0.75rem;
    border-radius: 4px;
    overflow-x: auto;
    margin: 0.5rem 0;
  }

  .block-system :global(pre code) {
    background: none;
    padding: 0;
  }

  .block-system :global(ul),
  .block-system :global(ol) {
    margin: 0.5rem 0;
    padding-left: 1.5rem;
  }

  .block-system :global(li) {
    margin: 0.25rem 0;
  }
</style>
