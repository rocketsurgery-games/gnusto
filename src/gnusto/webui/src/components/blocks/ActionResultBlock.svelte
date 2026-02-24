<script lang="ts">
  import type { ActionResultBlock } from '../../lib/types'
  import { styleText } from '../../lib/markdown'

  interface Props {
    block: ActionResultBlock
  }

  let { block }: Props = $props()
</script>

<div class="block-action">{@html styleText(block.text)}</div>

<style>
  .block-action {
    color: var(--text-muted);
    font-style: italic;
    font-size: 0.9rem;
  }
</style>
