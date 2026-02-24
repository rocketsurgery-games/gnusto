<script lang="ts">
  import type { CommandBlock } from '../../lib/types'

  interface Props {
    block: CommandBlock
  }

  let { block }: Props = $props()
</script>

<div class="block-command">&gt; {block.text}</div>

<style>
  .block-command {
    color: var(--accent-green);
    font-family: var(--font-mono);
    font-size: 0.95rem;
    margin-top: 2rem;
  }
</style>
