<script lang="ts">
  import type { SfxBlock } from '../../lib/types'

  interface Props {
    block: SfxBlock
  }

  let { block }: Props = $props()
</script>

<!-- Onomatopoeia lettering — a comic sound-effect panel (gnusto-4ac5.5) -->
<div class="block-sfx">{block.text}</div>

<style>
  .block-sfx {
    font-family: var(--font-letter);
    font-style: italic;
    font-size: clamp(2.2rem, 11vw, 4.5rem);
    line-height: 0.9;
    color: var(--game-warm);
    text-transform: uppercase;
    letter-spacing: -0.02em;
    transform: rotate(-4deg);
    text-shadow:
      3px 3px 0 #000,
      0 0 26px rgba(230, 164, 92, 0.45);
    margin: 0.4rem 0 0.4rem 0.2rem;
    width: fit-content;
  }
</style>
