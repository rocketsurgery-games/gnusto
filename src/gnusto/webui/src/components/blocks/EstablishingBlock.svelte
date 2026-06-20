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
  <!-- scene-break: a new establishing panel reads as a beat change (4ac5.3).
       Pure CSS, no state plumbing — continuity is automatic in the stream. -->
  <div class="scene-divider" aria-hidden="true"><span class="mark">◆</span></div>

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
  /* extra air above the panel so a new scene reads as a beat change */
  .establishing {
    margin-top: 2.25rem;
  }

  /* a faded chapter rule with a small center mark */
  .scene-divider {
    display: flex;
    align-items: center;
    gap: 0.85rem;
    margin-bottom: 1.15rem;
  }
  .scene-divider::before,
  .scene-divider::after {
    content: "";
    height: 1px;
    flex: 1;
    background: linear-gradient(90deg, transparent, var(--border), transparent);
  }
  .scene-divider .mark {
    color: var(--game-accent);
    font-size: 0.7rem;
    opacity: 0.7;
    text-shadow: 0 0 8px rgba(143, 224, 106, 0.5);
  }

  /* full-bleed scene art shown at its NATIVE aspect (rooms are generated wide,
     e.g. 2:1, via :visual-style :kinds). The room art already carries a baked
     inked border, so we frame with shadow, not a 2nd border (webtoon-mock
     spike finding). Older square art still displays fine, just taller. */
  .stage {
    position: relative;
    border-radius: var(--panel-radius);
    overflow: hidden;
    box-shadow:
      0 0 0 1px #000,
      0 14px 34px -16px #000;
  }

  /* page-turn feel: a soft fold-shadow across the top of the new scene */
  .stage::before {
    content: "";
    position: absolute;
    inset: 0;
    z-index: 1;
    pointer-events: none;
    background: linear-gradient(180deg, rgba(0, 0, 0, 0.5), transparent 16%);
  }

  .stage img {
    display: block;
    width: 100%;
    height: auto;
  }

  /* location label — embedded identity, not chrome */
  .locandum {
    position: absolute;
    z-index: 2; /* above the page-turn fold */
    top: 12px;
    left: 12px;
    font-family: var(--font-ui);
    font-size: 0.78rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--game-accent-glow);
    background: rgba(4, 7, 10, 0.72);
    border-left: 3px solid var(--game-accent);
    padding: 5px 10px;
    text-shadow: 0 0 8px rgba(143, 224, 106, 0.5);
  }

  /* no-art fallback: a typographic location title on a dark plate */
  .stage--noart {
    aspect-ratio: 5 / 2;
    display: grid;
    place-items: center;
    background: radial-gradient(120% 120% at 50% 30%, var(--game-panel-2), var(--game-ink) 70%);
    text-align: center;
    padding: 1.5rem;
  }

  .locandum-big {
    font-family: var(--font-ui);
    font-size: clamp(1.3rem, 5vw, 2.2rem);
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--game-text);
    text-shadow: 0 0 26px rgba(143, 224, 106, 0.25);
  }

  .desc {
    margin-top: 0.75rem;
    color: var(--text-secondary);
    font-size: 0.98rem;
    line-height: 1.6;
  }
</style>
