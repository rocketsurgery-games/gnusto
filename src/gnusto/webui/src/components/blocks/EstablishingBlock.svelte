<script lang="ts">
  import type { RoomEnterBlock } from '../../lib/types'
  import { styleText } from '../../lib/markdown'

  interface Props {
    block: RoomEnterBlock
  }

  let { block }: Props = $props()
</script>

<!--
  Frozen ESTABLISHING panel (gnusto-4ac5.1). A point-in-time snapshot of the
  room as the player entered: stage art (full-bleed) + location label + the
  room description. It does NOT track live state afterwards — re-entering a
  room emits a fresh establishing panel. Live affordances live elsewhere.
-->
<section class="establishing">
  {#if block.image}
    <div class="stage">
      <img src={block.image} alt={block.name} onerror={(e) => (e.target as HTMLImageElement).remove()} />
      <span class="locandum">{block.name}</span>
    </div>
  {:else}
    <!-- no stage art → typographic establishing (degrade, don't break) -->
    <div class="stage stage--noart">
      <span class="locandum-big">{block.name}</span>
    </div>
  {/if}

  {#if block.description}
    <div class="desc">{@html styleText(block.description)}</div>
  {/if}
</section>

<style>
  .establishing {
    margin: 0;
  }

  /* full-bleed scene art, cropped to a slightly cinematic ratio. The room art
     already carries a baked inked border, so we frame with shadow, not a 2nd
     border (see the webtoon-mock spike findings). */
  .stage {
    position: relative;
    border-radius: var(--panel-radius);
    overflow: hidden;
    box-shadow:
      0 0 0 1px #000,
      0 14px 34px -16px #000;
  }

  .stage img {
    display: block;
    width: 100%;
    aspect-ratio: 5 / 4;
    object-fit: cover;
  }

  /* location label — embedded identity, not chrome */
  .locandum {
    position: absolute;
    top: 12px;
    left: 12px;
    font-family: var(--font-ui);
    font-size: 0.78rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #c4ff8a;
    background: rgba(4, 7, 10, 0.72);
    border-left: 3px solid #8fe06a;
    padding: 5px 10px;
    text-shadow: 0 0 8px rgba(143, 224, 106, 0.5);
  }

  /* no-art fallback: a typographic location title on a dark plate */
  .stage--noart {
    aspect-ratio: 5 / 2;
    display: grid;
    place-items: center;
    background: radial-gradient(120% 120% at 50% 30%, #16262d, #04070a 70%);
    text-align: center;
    padding: 1.5rem;
  }

  .locandum-big {
    font-family: var(--font-ui);
    font-size: clamp(1.3rem, 5vw, 2.2rem);
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #dbe6e3;
    text-shadow: 0 0 26px rgba(143, 224, 106, 0.25);
  }

  .desc {
    margin-top: 0.75rem;
    color: var(--text-secondary);
    font-size: 0.98rem;
    line-height: 1.6;
  }
</style>
