<script lang="ts">
  import type { NarrateBlock } from '../../lib/types'
  import { styleNarrative } from '../../lib/markdown'

  interface Props {
    block: NarrateBlock
  }

  let { block }: Props = $props()
</script>

<div class="block-narrate">
  {@html styleNarrative(block.text)}
</div>

<style>
  .block-narrate {
    font-style: italic;
    color: var(--text-secondary);
    font-size: 0.95rem;
    line-height: 1.7;
    margin-top: 0.75rem;
  }

  .block-narrate :global(p) {
    margin: 0.5rem 0;
  }

  .block-narrate :global(img) {
    display: block;
    max-width: 100%;
    max-height: 300px;
    margin: 1rem auto;
    border-radius: 4px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }
</style>
