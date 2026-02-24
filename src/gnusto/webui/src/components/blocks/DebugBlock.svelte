<script lang="ts">
  import type { DebugBlock } from '../../lib/types'

  interface Props {
    block: DebugBlock
  }

  let { block }: Props = $props()
</script>

<div class="block-debug">
  <div class="debug-label">{block.label}</div>
  <pre class="debug-content">{block.content}</pre>
</div>

<style>
  .block-debug {
    font-family: var(--font-mono);
    font-size: 0.8rem;
    color: var(--text-muted);
  }

  .debug-label {
    color: var(--accent-cyan);
    margin-bottom: 0.15rem;
  }

  .debug-content {
    background: #f5f5f5;
    padding: 0.4rem 0.6rem;
    border-radius: 4px;
    margin: 0;
    white-space: pre-wrap;
    line-height: 1.4;
  }
</style>
