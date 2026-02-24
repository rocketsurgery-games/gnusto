<script lang="ts">
  import type { AmbientBlock } from '../../lib/types'

  interface Props {
    block: AmbientBlock
  }

  let { block }: Props = $props()
</script>

<div class="block-ambient">{block.text}</div>

<style>
  .block-ambient {
    padding: 0.25rem 0;
    color: var(--ambient-color);
    font-size: 0.9rem;
    font-style: italic;
    line-height: 1.6;
  }
</style>
