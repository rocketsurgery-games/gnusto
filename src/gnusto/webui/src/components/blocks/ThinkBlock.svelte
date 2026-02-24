<script lang="ts">
  import type { ThinkBlock } from '../../lib/types'

  interface Props {
    block: ThinkBlock
  }

  let { block }: Props = $props()
</script>

<div class="block-think">{block.text}</div>

<style>
  .block-think {
    padding: 0.5rem 0.75rem;
    background: var(--think-bg);
    border-left: 2px solid var(--think-border);
    border-radius: 0 var(--panel-radius) var(--panel-radius) 0;
    font-style: italic;
    color: var(--think-text);
    font-size: 0.9rem;
    line-height: 1.7;
  }
</style>
