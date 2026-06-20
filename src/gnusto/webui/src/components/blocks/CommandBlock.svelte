<script lang="ts">
  import type { CommandBlock } from '../../lib/types'

  interface Props {
    block: CommandBlock
  }

  let { block }: Props = $props()
</script>

<!--
  The player's own command, rendered as an in-world CAPTION panel in the stream
  (gnusto-4ac5.8). Right-aligned mono "you" voice against the left-aligned
  narrator captions gives the strip a call-and-response cadence.
-->
<div class="block-command">{block.text}</div>

<style>
  .block-command {
    font-family: var(--font-mono);
    font-size: 0.9rem;
    color: var(--game-accent-glow);
    background: var(--panel-ink);
    border: 1px solid var(--border);
    border-left: 3px solid var(--game-accent);
    padding: 0.55rem 0.85rem;
    width: fit-content;
    max-width: 52ch;
    margin: 1.5rem 0 0 auto; /* right-aligned: the protagonist speaking */
    box-shadow: 0 6px 18px -10px #000;
  }

  .block-command::before {
    content: "› ";
    color: var(--game-accent);
  }
</style>
