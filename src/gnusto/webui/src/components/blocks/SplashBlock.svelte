<script lang="ts">
  import type { SplashBlock } from '../../lib/types'
  import { resolveEntityImage } from '../../lib/entities.svelte'

  interface Props {
    block: SplashBlock
  }

  let { block }: Props = $props()

  let art = $derived(block.entity ? resolveEntityImage(block.entity) : null)
  let hasArt = $state(true)
</script>

<!--
  SPLASH (gnusto-4ac5.5): a full-bleed dramatic panel for a big beat. With a
  resolvable asset it bleeds the art behind dramatic lettering; with none it
  degrades to a TYPOGRAPHIC splash (gnusto-4ac5.6) — a legit comic device.
-->
{#if art && hasArt}
  <section class="splash splash--art">
    <img src={art} alt={block.entity || ''} onerror={() => (hasArt = false)} />
    <div class="splash-fold" aria-hidden="true"></div>
    <p class="splash-caption">{block.text}</p>
  </section>
{:else}
  <section class="splash splash--type">
    <p class="splash-lettering">{block.text}</p>
  </section>
{/if}

<style>
  .splash {
    position: relative;
    border-radius: var(--panel-radius);
    overflow: hidden;
    box-shadow:
      0 0 0 1px #000,
      0 14px 34px -16px #000;
  }

  .splash--art img {
    display: block;
    width: 100%;
    height: auto;
  }

  /* page-turn fold over the top of the splash */
  .splash-fold {
    position: absolute;
    inset: 0;
    pointer-events: none;
    background: linear-gradient(180deg, rgba(0, 0, 0, 0.55), transparent 22%);
  }

  .splash-caption {
    position: absolute;
    left: 16px;
    bottom: 16px;
    margin: 0;
    max-width: 42ch;
    font-family: var(--font-body);
    font-size: 1.02rem;
    line-height: 1.45;
    color: var(--paper-ink);
    background: linear-gradient(180deg, var(--paper), #d8d0ba);
    border: 1px solid #000;
    box-shadow: 3px 3px 0 0 rgba(0, 0, 0, 0.5);
    padding: 11px 14px;
  }

  /* typographic splash fallback: full-bleed dramatic lettering on dark ground */
  .splash--type {
    display: grid;
    place-items: center;
    min-height: 38vh;
    padding: 2.5rem 1.5rem;
    background: radial-gradient(
      120% 120% at 50% 30%,
      var(--game-panel-2),
      var(--game-ink) 72%
    );
  }

  .splash-lettering {
    margin: 0;
    text-align: center;
    font-family: var(--font-letter);
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.01em;
    line-height: 0.98;
    font-size: clamp(1.8rem, 8vw, 3.6rem);
    color: var(--game-text);
    text-shadow:
      2px 2px 0 #000,
      0 0 30px rgba(143, 224, 106, 0.22);
  }
</style>
