<script lang="ts">
  import type { CaptionBlock } from '../../lib/types'
  import { styleText } from '../../lib/markdown'

  interface Props {
    block: CaptionBlock
  }

  let { block }: Props = $props()
</script>

<!--
  Narrator CAPTION (gnusto-4ac5.5). The out-of-world authorial voice over the
  panel — rendered as the classic comic parchment caption box, distinct from
  in-world NARRATE prose.
-->
<div class="block-caption">{@html styleText(block.text)}</div>

<style>
  .block-caption {
    font-family: var(--font-body);
    font-size: 1.02rem;
    line-height: 1.5;
    color: var(--paper-ink);
    background: linear-gradient(180deg, var(--paper), #d8d0ba);
    border: 1px solid #000;
    box-shadow: 3px 3px 0 0 rgba(0, 0, 0, 0.5);
    padding: 12px 15px;
    max-width: 44ch;
    width: fit-content;
  }
</style>
